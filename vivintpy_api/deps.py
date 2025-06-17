from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone # Added timezone
from pydantic import ValidationError # For catching Pydantic validation errors

from vivintpy_api.config import settings
from vivintpy import Account # Assuming vivintpy is installed and accessible
from vivintpy_api.models.token import TokenData
import redis.asyncio as aioredis

# Global Redis connection pool
_redis_pool = None

async def get_redis_client() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
            password=settings.REDIS_PASSWORD,
            decode_responses=True # Decode responses to strings by default
        )
    return aioredis.Redis(connection_pool=_redis_pool)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Function to create access token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Default to ACCESS_TOKEN_EXPIRE_MINUTES from settings
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "token_type": "access"}) # Add token_type claim
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

# Function to create refresh token
def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Default to REFRESH_TOKEN_EXPIRE_DAYS from settings
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "token_type": "refresh"}) # Add token_type claim
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt





# User authentication helpers
# ---------------------------------

# Dependency to get the current user from JWT token (moved up to satisfy forward references)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    redis_client: aioredis.Redis = Depends(get_redis_client),
) -> TokenData:
    """Validate the incoming JWT access token and ensure the associated Vivint refresh token
    stored in Redis still matches, otherwise reject the request.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str | None = payload.get("sub")
        token_type: str | None = payload.get("token_type")
        vivint_refresh_token_from_jwt: str | None = payload.get("vivint_refresh_token")
        if username is None or token_type != "access" or vivint_refresh_token_from_jwt is None:
            raise credentials_exception
        stored_vivint_refresh_token = await redis_client.get(f"user:{username}:vivint_refresh_token")
        if not stored_vivint_refresh_token or stored_vivint_refresh_token != vivint_refresh_token_from_jwt:
            raise credentials_exception
        return TokenData(username=username, vivint_refresh_token=vivint_refresh_token_from_jwt)
    except (JWTError, ValidationError):
        raise credentials_exception

# Placeholder for additional user checks (e.g., disabled flag)
async def get_current_active_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    return current_user

# Dependency to get a Vivint Account for the current user (built from JWT + Redis)
async def get_user_account(
    current_user: TokenData = Depends(get_current_active_user),
    redis_client: aioredis.Redis = Depends(get_redis_client),
):
    """Create a temporary `vivintpy.Account` for the authenticated user based on the
    Vivint refresh token stored in Redis. This avoids relying on the optional
    shared account and ensures each request can interact with the user’s own
    systems. The account is disconnected automatically after the request.
    """
    username = current_user.username
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user in token")

    vivint_refresh_token = await redis_client.get(f"user:{username}:vivint_refresh_token")
    if not vivint_refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No Vivint session found. Please re-authenticate.")
    if isinstance(vivint_refresh_token, bytes):
        vivint_refresh_token = vivint_refresh_token.decode()

    account = Account(username=username, refresh_token=vivint_refresh_token)
    try:
        await account.connect(load_devices=True)
    except Exception:
        # Token likely expired; signal client to re-login
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Vivint session expired. Please log in again.")

    try:
        yield account
    finally:
        await account.disconnect()

# Dependency to get the shared Vivint Account instance
async def get_shared_vivint_account(request: Request) -> Account:
    if not hasattr(request.app.state, 'vivint_account') or request.app.state.vivint_account is None:
        # This indicates the account wasn't initialized properly during startup,
        # or it's not being managed per request as intended.
        # For a shared global account, this check is crucial.
        # If accounts are per-user and created on login, this dependency might work differently.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vivint Account not initialized or available.",
        )
    return request.app.state.vivint_account

# Dependency to get the current user from JWT token
async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    redis_client: aioredis.Redis = Depends(get_redis_client) # Inject Redis client
) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str | None = payload.get("sub")
        token_type: str | None = payload.get("token_type") # Check token_type
        vivint_refresh_token_from_jwt: str | None = payload.get("vivint_refresh_token")
        
        if username is None or token_type != "access" or vivint_refresh_token_from_jwt is None:
            # If essential claims are missing or it's not an access token, it's invalid.
            raise credentials_exception
            
        # Validate Vivint refresh token against Redis to ensure session is still active
        stored_vivint_refresh_token = await redis_client.get(f"user:{username}:vivint_refresh_token")
        
        if not stored_vivint_refresh_token or stored_vivint_refresh_token != vivint_refresh_token_from_jwt:
            # If the token is not in Redis, or if it doesn't match the one from the JWT,
            # the underlying Vivint session is considered invalid or has changed.
            # This effectively revokes the access token if the Vivint session changes.
            raise credentials_exception

        # Create TokenData, including the Vivint refresh token
        token_data = TokenData(username=username, vivint_refresh_token=vivint_refresh_token_from_jwt)
    except JWTError:
        raise credentials_exception
    except ValidationError: # Catch Pydantic validation errors for TokenData
        raise credentials_exception
    return token_data

# Dependency to ensure the current user is active (extend with DB checks if needed)
async def get_current_active_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """For now, simply return the authenticated user. Add extra checks (e.g., disabled) here."""
    return current_user


