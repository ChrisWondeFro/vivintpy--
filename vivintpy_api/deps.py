from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone # Added timezone
from pydantic import ValidationError # For catching Pydantic validation errors

from vivintpy_api.config import settings
from vivintpy import Account # Assuming vivintpy is installed and accessible
from vivintpy_api.models.token import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Function to create access token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15) # Default expiry
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

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
async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str | None = payload.get("sub")
        vivint_refresh_token: str | None = payload.get("vivint_refresh_token") # Extract refresh token
        if username is None:
            raise credentials_exception
        # Create TokenData, including the Vivint refresh token
        token_data = TokenData(username=username, vivint_refresh_token=vivint_refresh_token)
    except JWTError:
        raise credentials_exception
    except ValidationError: # Catch Pydantic validation errors for TokenData
        raise credentials_exception
    return token_data

# Example of a dependency for an active user (similar to get_current_user but could add more checks)
async def get_current_active_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    # In a real app, you might check if the user is active in a database here.
    # For now, just returns the user from token.
    # if current_user.disabled: # If you had a 'disabled' field in TokenData/User model
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
