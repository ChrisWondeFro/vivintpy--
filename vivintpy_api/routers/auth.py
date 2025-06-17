from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
import logging
import json

import aiohttp
from .. import deps
from ..config import settings
from vivintpy import Account, VivintSkyApiMfaRequiredError, VivintSkyApiAuthenticationError
from ..models.token import Token
from ..models.auth import RefreshTokenRequest
import uuid
import redis.asyncio as aioredis
from jose import JWTError, jwt

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Define TTLs for Redis keys
VIVINT_REFRESH_TOKEN_TTL_SECONDS = 90 * 24 * 60 * 60  # 90 days
MFA_SESSION_TTL_SECONDS = 5 * 60  # 5 minutes

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

# The mfa_pending_accounts dictionary is removed as state is now managed in Redis.

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), redis_client: aioredis.Redis = Depends(deps.get_redis_client)):
    """
    Login with username and password.
    If MFA is required, an error will be returned, and /verify-mfa should be called.
    """
    username = form_data.username
    password = form_data.password
    
    # 1. Try to use an existing Vivint refresh token so the user isn’t prompted for MFA every time
    stored_rt = await redis_client.get(f"user:{username}:vivint_refresh_token")
    account: Account | None = None

    try:
        if stored_rt:
            if isinstance(stored_rt, bytes):
                stored_rt = stored_rt.decode()
            account = Account(username=username, refresh_token=stored_rt)
            logger.info(f"Attempting refresh-token login for user: {username}")
            try:
                await account.connect()
                logger.info(f"Refresh-token login succeeded for {username} .")
            except VivintSkyApiAuthenticationError:
                logger.info(
                    f"Stored refresh token invalid/expired for {username}. Falling back to password login.")
                await account.disconnect()
                account = None

        # 2. Password + PKCE login (may trigger MFA) if no valid refresh token login succeeded
        if account is None:
            account = Account(username=username, password=password)
            logger.info(f"Attempting password login for user: {username}")
            await account.connect()
            logger.info(f"Password login succeeded for {username} (no MFA).")

        # 3. Persist (possibly new) Vivint refresh token in Redis
        vivint_refresh_token = account.refresh_token
        await redis_client.set(
            f"user:{username}:vivint_refresh_token",
            vivint_refresh_token,
            ex=VIVINT_REFRESH_TOKEN_TTL_SECONDS,
        )

        # 4. Issue our own JWT access & API refresh tokens
        access_token = deps.create_access_token(
            data={"sub": username, "vivint_refresh_token": vivint_refresh_token}
        )
        api_refresh_token = deps.create_refresh_token(data={"sub": username})

        await redis_client.set(
            f"user:{username}:api_refresh_token",
            api_refresh_token,
            ex=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": api_refresh_token,
        }

    except VivintSkyApiMfaRequiredError:
        logger.info(f"MFA required for user: {username}. Storing MFA session details in Redis.")
        mfa_session_id = str(uuid.uuid4())

        # Extract cookies and code_verifier from the session for storage
        cookies = account.api.get_session_cookies()
        code_verifier = account.api.code_verifier

        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.set(
                f"mfa_session:{mfa_session_id}:session_data",
                json.dumps(
                    {
                        "username": username,
                        "password": password,
                        "cookies": cookies,
                        "code_verifier": code_verifier,
                    }
                ),
                ex=MFA_SESSION_TTL_SECONDS,
            )
            await pipe.execute()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "MFA_REQUIRED", "mfa_session_id": mfa_session_id},
        )
    except VivintSkyApiAuthenticationError as e:
        logger.error(f"Authentication error for user {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during login for {username}: {e}", exc_info=True)
        # Ensure the account session is closed if it was opened by vivintpy's Account
        if account.api and account.api.client_session and not account.api.client_session.closed:
             await account.api.disconnect()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login.",
        )
    finally:
        if account:
            await account.disconnect()

@router.post("/verify-mfa", response_model=Token)
async def verify_mfa_endpoint(mfa_session_id: str = Body(...), mfa_code: str = Body(...), redis_client: aioredis.Redis = Depends(deps.get_redis_client)):
    """
    Verify MFA code after /login indicated MFA_REQUIRED.
    """
    session_data_key = f"mfa_session:{mfa_session_id}:session_data"

    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.get(session_data_key)
        session_data = await pipe.execute()

    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA session not found or expired.",
        )

    try:
        session_data = json.loads(session_data[0])
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore session state.",
        )

    username = session_data.get("username")
    password = session_data.get("password")
    cookies = session_data.get("cookies")
    code_verifier = session_data.get("code_verifier")

    if not all([username, password, cookies, code_verifier]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA session not found or expired.",
        )

    cookie_jar = aiohttp.CookieJar()
    try:
        for cookie_data in cookies:
            cookie_jar.update_cookies({cookie_data["name"]: cookie_data["value"]}, aiohttp.helpers.URL(f"https://{cookie_data['domain']}{cookie_data['path']}"))
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore session state.",
        )

    client_session = aiohttp.ClientSession(cookie_jar=cookie_jar)
    account = Account(
        username=username,
        password=password,
        client_session=client_session,
        code_verifier=code_verifier,
    )

    try:
        logger.info(f"Verifying MFA for session ID: {mfa_session_id}")
        await account.verify_mfa(mfa_code)
        logger.info(f"MFA verification successful for session ID: {mfa_session_id}")

        # Extract the Vivint refresh token value from the authenticated account
        vivint_refresh_token = account.refresh_token

        logger.info(f"Storing Vivint refresh token for user {username} in Redis post-MFA.")
        await redis_client.set(
            f"user:{username}:vivint_refresh_token",
            vivint_refresh_token,
            ex=VIVINT_REFRESH_TOKEN_TTL_SECONDS,
        )

        access_token = deps.create_access_token(
            data={"sub": username, "vivint_refresh_token": vivint_refresh_token}
        )
        api_refresh_token = deps.create_refresh_token(data={"sub": username})

        await redis_client.set(
            f"user:{username}:api_refresh_token",
            api_refresh_token,
            ex=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": api_refresh_token,
        }

    except VivintSkyApiAuthenticationError as e:
        logger.error(f"MFA verification failed for session ID {mfa_session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA code is incorrect or expired.",
        )
    finally:
        logger.info(f"Deleting MFA session keys for session ID: {mfa_session_id} from Redis.")
        await redis_client.delete(session_data_key)
        if account:
            await account.disconnect()
        if client_session and not client_session.closed:
            await client_session.close()

@router.post("/refresh-token", response_model=Token)
async def refresh_api_token(
    refresh_request: RefreshTokenRequest = Body(...), 
    redis_client: aioredis.Redis = Depends(deps.get_redis_client)
):
    """
    Refresh API access token using an API refresh token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token invalid",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_not_found_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token not found, expired, or already used",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            refresh_request.refresh_token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str | None = payload.get("sub")
        token_type: str | None = payload.get("token_type")

        if username is None or token_type != "refresh":
            logger.warning(f"Invalid refresh token payload for user: {username}, type: {token_type}")
            raise credentials_exception

    except JWTError as e:
        logger.error(f"JWTError while decoding refresh token: {e}")
        raise credentials_exception

    stored_refresh_token_key = f"user:{username}:api_refresh_token"
    stored_refresh_token = await redis_client.get(stored_refresh_token_key)

    if not stored_refresh_token:
        logger.warning(f"API refresh token for user {username} not found in Redis.")
        raise token_not_found_exception
    
    if stored_refresh_token != refresh_request.refresh_token:
        logger.warning(f"Submitted API refresh token does not match stored token for user {username}. Potential reuse or compromise.")
        # Security measure: If a token mismatch occurs, invalidate the stored token to prevent further use.
        await redis_client.delete(stored_refresh_token_key)
        raise credentials_exception

    # Token is valid, issue new tokens (implementing token rotation)
    logger.info(f"Valid API refresh token for user {username}. Issuing new access and refresh tokens.")

    # Fetch Vivint refresh token to include in the new access token
    vivint_refresh_token = await redis_client.get(f"user:{username}:vivint_refresh_token")
    if not vivint_refresh_token:
        logger.error(f"Vivint refresh token not found in Redis for user {username} during API token refresh. This indicates an inconsistent state.")
        # This is a critical internal error, as this token should exist if the API refresh token is valid.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Essential session data missing."
        )

    new_access_token = deps.create_access_token(
        data={"sub": username, "vivint_refresh_token": vivint_refresh_token}
    )
    new_api_refresh_token = deps.create_refresh_token(data={"sub": username})

    # Store the new API refresh token in Redis, effectively rotating the token
    await redis_client.set(
        stored_refresh_token_key, # Use the same key to overwrite
        new_api_refresh_token,
        ex=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "refresh_token": new_api_refresh_token
    }
