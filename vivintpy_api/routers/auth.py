from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
import logging # For logging errors

from .. import deps
from ..config import settings
from vivintpy import Account, VivintSkyApiMfaRequiredError, VivintSkyApiAuthenticationError
from ..models.token import Token

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

# This dictionary will temporarily store Account instances for users pending MFA.
# Key: username, Value: Account instance
# In a production scenario, this should be a more robust cache (e.g., Redis)
# with appropriate TTLs to avoid memory leaks and handle distributed environments.
mfa_pending_accounts: dict[str, Account] = {}

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login with username and password.
    If MFA is required, an error will be returned, and /verify-mfa should be called.
    """
    username = form_data.username
    password = form_data.password
    
    # For simplicity in this example, we create a new Account instance per login attempt.
    # In a real application, you might manage a pool of accounts or a shared one
    # if the Vivint API and your use case support it.
    # However, user-specific login implies user-specific Account objects initially.
    account = Account(username=username, password=password)
    
    try:
        logger.info(f"Attempting to connect for user: {username}")
        await account.connect()
        logger.info(f"Successfully connected for user: {username} without MFA.")
        
        # If connect is successful without MFA, generate token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = deps.create_access_token(
            data={"sub": username, "vivint_refresh_token": account.api.refresh_token}, # Store Vivint refresh token if needed
            expires_delta=access_token_expires
        )
        
        # Clean up any stale MFA pending account for this user
        if username in mfa_pending_accounts:
            del mfa_pending_accounts[username]
            
        return {"access_token": access_token, "token_type": "bearer"}

    except VivintSkyApiMfaRequiredError:
        logger.info(f"MFA required for user: {username}")
        # Store the account instance for MFA verification
        mfa_pending_accounts[username] = account
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # Or a custom status code like 428 Precondition Required
            detail="MFA_REQUIRED", # Send a clear code for the client
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

@router.post("/verify-mfa", response_model=Token)
async def verify_mfa_endpoint(username: str = Body(...), mfa_code: str = Body(...)):
    """
    Verify MFA code after /login indicated MFA_REQUIRED.
    """
    logger.info(f"Attempting MFA verification for user: {username}")
    if username not in mfa_pending_accounts:
        logger.warning(f"No pending MFA session found for user: {username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No MFA session pending for this user or session expired. Please login again.",
        )

    account = mfa_pending_accounts[username]
    
    try:
        await account.verify_mfa(mfa_code)
        logger.info(f"MFA verification successful for user: {username}")
        
        # MFA successful, generate token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = deps.create_access_token(
            data={"sub": username, "vivint_refresh_token": account.api.refresh_token},
            expires_delta=access_token_expires
        )
        
        # Clean up: remove account from pending MFA
        del mfa_pending_accounts[username]
        
        # Store this authenticated account in app.state to be used by other endpoints
        # This assumes a single "active" user model for the API for now.
        # A multi-user system would require more sophisticated session management.
        # request.app.state.vivint_account = account # This needs access to 'request' or app
        # For now, we assume that subsequent calls will use the token, and the Account
        # object might be re-created using a refresh token stored in the JWT or a secure cookie.
        # Or, if the API is meant for a single Vivint account, this `account` could be stored globally.
        # The `get_shared_vivint_account` in `deps.py` expects it in `request.app.state.vivint_account`.
        # This part needs to be wired up in main.py's lifespan or a middleware.
        
        return {"access_token": access_token, "token_type": "bearer"}

    except VivintSkyApiAuthenticationError as e:
        logger.error(f"MFA authentication error for user {username}: {e}")
        # Don't remove from mfa_pending_accounts, user might want to retry with a new code
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code.",
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during MFA verification for {username}: {e}", exc_info=True)
        # Clean up to be safe
        if username in mfa_pending_accounts:
            del mfa_pending_accounts[username]
        if account.api and account.api.client_session and not account.api.client_session.closed:
             await account.api.disconnect()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during MFA verification.",
        )

# Placeholder for /auth/refresh if we implement API-managed refresh tokens
# @router.post("/refresh", response_model=Token)
# async def refresh_access_token(current_user: dict = Depends(deps.get_current_user_from_refresh_token)):
#    pass
