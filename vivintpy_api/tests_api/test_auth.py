import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import timedelta

from fastapi import status
from jose import jwt

from vivintpy_api.main import app
from vivintpy_api.config import settings
from vivintpy import VivintSkyApiAuthenticationError, VivintSkyApiMfaRequiredError
from vivintpy.account import Account
from vivintpy_api import deps
from vivintpy_api.deps import create_refresh_token
import redis.asyncio as aioredis

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def mock_redis_client():
    mock = AsyncMock(spec=aioredis.Redis)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    return mock

@pytest_asyncio.fixture
async def client(mock_redis_client: AsyncMock):
    app.dependency_overrides[deps.get_redis_client] = lambda: mock_redis_client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture
def mock_vivint_account_no_mfa():
    mock_account = AsyncMock(spec=Account)
    mock_account.username = "testuser"
    mock_account.password = "testpassword"
    mock_account.api = AsyncMock()
    mock_account.api.refresh_token = "fake_vivint_refresh_token_no_mfa"
    mock_account.is_connected = True
    
    async def mock_connect():
        mock_account.is_connected = True
        mock_account.systems = {}
        mock_account.devices = {}
        return True
    
    mock_account.connect = AsyncMock(side_effect=mock_connect)
    mock_account.disconnect = AsyncMock()
    return mock_account

@pytest.fixture
def mock_vivint_account_mfa_required():
    mock_account = AsyncMock(spec=Account)
    mock_account.username = "testuser_mfa"
    mock_account.password = "testpassword_mfa"
    mock_account.api = AsyncMock()
    
    async def mock_connect_mfa():
        raise VivintSkyApiMfaRequiredError("MFA Code Required")
    
    mock_account.connect = AsyncMock(side_effect=mock_connect_mfa)
    
    async def mock_verify_mfa(code: str):
        if code == "123456":
            mock_account.api.refresh_token = "fake_vivint_refresh_token_after_mfa"
            mock_account.is_connected = True
            mock_account.systems = {}
            mock_account.devices = {}
            return True
        raise VivintSkyApiAuthenticationError("Invalid MFA code")

    mock_account.verify_mfa = AsyncMock(side_effect=mock_verify_mfa)
    mock_account.disconnect = AsyncMock()
    return mock_account

async def test_login_success_no_mfa(client: AsyncClient, mock_vivint_account_no_mfa: MagicMock, mock_redis_client: AsyncMock):
    with patch("vivintpy_api.routers.auth.Account", return_value=mock_vivint_account_no_mfa):
        with patch("vivintpy_api.main.Account", return_value=mock_vivint_account_no_mfa):
            app.state.vivint_account = mock_vivint_account_no_mfa
            
            response = await client.post(
                "/auth/login",
                data={"username": "testuser", "password": "testpassword"}
            )
            assert response.status_code == status.HTTP_200_OK
            token_data = response.json()
            assert "access_token" in token_data
            assert token_data["token_type"] == "bearer"
            
            assert "refresh_token" in token_data

            access_payload = jwt.decode(token_data["access_token"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            assert access_payload["sub"] == "testuser"
            assert access_payload["vivint_refresh_token"] == "fake_vivint_refresh_token_no_mfa"
            assert access_payload["token_type"] == "access"

            refresh_payload = jwt.decode(token_data["refresh_token"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            assert refresh_payload["sub"] == "testuser"
            assert refresh_payload["token_type"] == "refresh"
            
            mock_vivint_account_no_mfa.connect.assert_called_once()

            assert mock_redis_client.set.call_count == 2
            
            vivint_refresh_token_key = f"user:{mock_vivint_account_no_mfa.username}:vivint_refresh_token"
            api_refresh_token_key = f"user:{mock_vivint_account_no_mfa.username}:api_refresh_token"
            
            mock_redis_client.set.assert_any_call(
                vivint_refresh_token_key,
                mock_vivint_account_no_mfa.api.refresh_token,
                ex=90 * 24 * 60 * 60
            )
            
            mock_redis_client.set.assert_any_call(
                api_refresh_token_key,
                token_data["refresh_token"],
                ex=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            )

async def test_login_mfa_required(client: AsyncClient, mock_vivint_account_mfa_required: MagicMock, mock_redis_client: AsyncMock):
    with patch("vivintpy_api.routers.auth.Account", return_value=mock_vivint_account_mfa_required):
        with patch("vivintpy_api.main.Account", return_value=mock_vivint_account_mfa_required):
            app.state.vivint_account = mock_vivint_account_mfa_required

            response = await client.post(
                "/auth/login",
                data={"username": "testuser_mfa", "password": "testpassword_mfa"}
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            error_data = response.json()
            assert error_data["detail"]["message"] == "MFA_REQUIRED"
            assert "mfa_session_id" in error_data["detail"]
            assert "mfa_method_preference" in error_data["detail"]
            
            mock_vivint_account_mfa_required.connect.assert_called_once()

            assert mock_redis_client.set.call_count == 2
            mfa_username_key = f"mfa_session:{error_data['detail']['mfa_session_id']}:username"
            mfa_password_key = f"mfa_session:{error_data['detail']['mfa_session_id']}:password"
            mfa_session_ttl = 5 * 60  

            mock_redis_client.set.assert_any_call(
                mfa_username_key,
                mock_vivint_account_mfa_required.username,
                ex=mfa_session_ttl
            )
            mock_redis_client.set.assert_any_call(
                mfa_password_key,
                mock_vivint_account_mfa_required.password,
                ex=mfa_session_ttl
            )

async def test_verify_mfa_success(client: AsyncClient, mock_vivint_account_mfa_required: MagicMock, mock_redis_client: AsyncMock):
    mfa_session_id = "test_mfa_session_id"
    mfa_code = "123456"
    expected_username = mock_vivint_account_mfa_required.username
    expected_password = mock_vivint_account_mfa_required.password
    expected_vivint_refresh_token = "fake_vivint_refresh_token_after_mfa"

    mock_redis_client.get.side_effect = lambda key: {
        f"mfa_session:{mfa_session_id}:username": expected_username,
        f"mfa_session:{mfa_session_id}:password": expected_password
    }.get(key)

    with patch("vivintpy_api.routers.auth.Account", return_value=mock_vivint_account_mfa_required) as mock_account_constructor:
        async def mock_verify_mfa_local(code_param: str):
            if code_param == mfa_code:
                mock_vivint_account_mfa_required.api.refresh_token = expected_vivint_refresh_token
                mock_vivint_account_mfa_required.is_connected = True
                return True
            raise VivintSkyApiAuthenticationError("Invalid MFA code from mock")
        mock_vivint_account_mfa_required.verify_mfa = AsyncMock(side_effect=mock_verify_mfa_local)
        mock_vivint_account_mfa_required.disconnect = AsyncMock()

        response = await client.post(
            "/auth/verify-mfa",
            json={"mfa_session_id": mfa_session_id, "mfa_code": mfa_code}
        )

        assert response.status_code == status.HTTP_200_OK
        token_data = response.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "bearer"

        mock_account_constructor.assert_called_once_with(username=expected_username, password=expected_password)
        mock_vivint_account_mfa_required.verify_mfa.assert_called_once_with(mfa_code)

        access_payload = jwt.decode(token_data["access_token"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert access_payload["sub"] == expected_username
        assert access_payload["vivint_refresh_token"] == expected_vivint_refresh_token
        assert access_payload["token_type"] == "access"

        refresh_payload = jwt.decode(token_data["refresh_token"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert refresh_payload["sub"] == expected_username
        assert refresh_payload["token_type"] == "refresh"

        mock_redis_client.get.assert_any_call(f"mfa_session:{mfa_session_id}:username")
        mock_redis_client.get.assert_any_call(f"mfa_session:{mfa_session_id}:password")
        
        vivint_token_redis_key = f"user:{expected_username}:vivint_refresh_token"
        api_token_redis_key = f"user:{expected_username}:api_refresh_token"
        
        mock_redis_client.set.assert_any_call(
            vivint_token_redis_key,
            expected_vivint_refresh_token,
            ex=90 * 24 * 60 * 60
        )
        mock_redis_client.set.assert_any_call(
            api_token_redis_key,
            token_data["refresh_token"],
            ex=int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds())
        )

        mock_redis_client.delete.assert_any_call(f"mfa_session:{mfa_session_id}:username")
        mock_redis_client.delete.assert_any_call(f"mfa_session:{mfa_session_id}:password")

async def test_login_invalid_credentials(client: AsyncClient):
    mock_account_auth_error = AsyncMock(spec=Account)
    mock_account_auth_error.connect = AsyncMock(side_effect=VivintSkyApiAuthenticationError("Invalid credentials"))
    
    with patch("vivintpy_api.routers.auth.Account", return_value=mock_account_auth_error):
        with patch("vivintpy_api.main.Account", return_value=mock_account_auth_error):
             app.state.vivint_account = mock_account_auth_error
             
             response = await client.post(
                "/auth/login",
                data={"username": "wronguser", "password": "wrongpassword"}
            )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        error_data = response.json()
        assert error_data["detail"] == "Incorrect username or password"

async def test_verify_mfa_invalid_code(client: AsyncClient, mock_vivint_account_mfa_required: MagicMock, mock_redis_client: AsyncMock):
    mfa_session_id = "test_mfa_session_invalid_code"
    invalid_mfa_code = "wrongcode"
    expected_username = "user_for_invalid_mfa"
    expected_password = "pass_for_invalid_mfa"

    mock_redis_client.get.side_effect = lambda key: {
        f"mfa_session:{mfa_session_id}:username": expected_username,
        f"mfa_session:{mfa_session_id}:password": expected_password
    }.get(key)

    mock_vivint_account_mfa_required.verify_mfa = AsyncMock(side_effect=VivintSkyApiAuthenticationError("Invalid MFA code from mock"))
    mock_vivint_account_mfa_required.username = expected_username
    mock_vivint_account_mfa_required.password = expected_password

    with patch("vivintpy_api.routers.auth.Account", return_value=mock_vivint_account_mfa_required) as mock_account_constructor:
        response = await client.post(
            "/auth/verify-mfa",
            json={"mfa_session_id": mfa_session_id, "mfa_code": invalid_mfa_code}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        error_data = response.json()
        assert error_data["detail"] == "Invalid MFA code."

        mock_account_constructor.assert_called_once_with(username=expected_username, password=expected_password)
        mock_vivint_account_mfa_required.verify_mfa.assert_called_once_with(invalid_mfa_code)

        mock_redis_client.get.assert_any_call(f"mfa_session:{mfa_session_id}:username")
        mock_redis_client.get.assert_any_call(f"mfa_session:{mfa_session_id}:password")
        
        mock_redis_client.delete.assert_not_called()

async def test_verify_mfa_session_id_not_found(client: AsyncClient, mock_redis_client: AsyncMock):
    non_existent_mfa_session_id = "non_existent_mfa_session_id"

    mock_redis_client.get.side_effect = None
    mock_redis_client.get.return_value = None
    
    response = await client.post(
        "/auth/verify-mfa",
        json={"mfa_session_id": non_existent_mfa_session_id, "mfa_code": "123456"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error_data = response.json()
    assert error_data["detail"] == "No MFA session pending for this ID or session expired. Please login again."

    mock_redis_client.get.assert_any_call(f"mfa_session:{non_existent_mfa_session_id}:username")
    mock_redis_client.delete.assert_not_called()

async def test_refresh_token_success(client: AsyncClient, mock_redis_client: AsyncMock):
    username = "testuser_refresh"
    original_vivint_refresh_token = "original_vivint_refresh_token_for_refresh_test"
    
    initial_api_refresh_token_data = {"sub": username, "token_type": "refresh"}
    initial_api_refresh_token = create_refresh_token(data=initial_api_refresh_token_data)

    mock_redis_client.get.side_effect = lambda key: {
        f"user:{username}:api_refresh_token": initial_api_refresh_token,
        f"user:{username}:vivint_refresh_token": original_vivint_refresh_token
    }.get(key)

    response = await client.post(
        "/auth/refresh-token",
        json={"refresh_token": initial_api_refresh_token}
    )

    assert response.status_code == status.HTTP_200_OK
    token_data = response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    new_api_refresh_token = token_data["refresh_token"]
    assert new_api_refresh_token != initial_api_refresh_token

    access_payload = jwt.decode(token_data["access_token"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert access_payload["sub"] == username
    assert access_payload["vivint_refresh_token"] == original_vivint_refresh_token
    assert access_payload["token_type"] == "access"

    new_refresh_payload = jwt.decode(new_api_refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert new_refresh_payload["sub"] == username
    assert new_refresh_payload["token_type"] == "refresh"

    mock_redis_client.get.assert_any_call(f"user:{username}:api_refresh_token")
    mock_redis_client.get.assert_any_call(f"user:{username}:vivint_refresh_token")
    
    mock_redis_client.set.assert_called_once_with(
        f"user:{username}:api_refresh_token",
        new_api_refresh_token,
        ex=int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds())
    )

async def test_refresh_token_invalid_conditions(client: AsyncClient, mock_redis_client: AsyncMock):
    username = "testuser_invalid_refresh"
    valid_vivint_refresh_token = "valid_vivint_refresh_token_for_invalid_test"
    
    # Scenario 1: Token not found in Redis
    api_refresh_token_key = f"user:{username}:api_refresh_token"
    vivint_refresh_token_key = f"user:{username}:vivint_refresh_token"
    
    # Ensure Redis returns None for the API refresh token, but a valid Vivint refresh token
    mock_redis_client.get.side_effect = lambda key: {
        vivint_refresh_token_key: valid_vivint_refresh_token
    }.get(key) # api_refresh_token_key will default to None from fixture setup

    some_generated_token = create_refresh_token(data={"sub": username, "token_type": "refresh"})
    response = await client.post(
        "/auth/refresh-token",
        json={"refresh_token": some_generated_token}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid or expired refresh token. (Not found in store or mismatch)"
    mock_redis_client.delete.assert_not_called() # Should not delete if token not found initially

    # Scenario 2: Token mismatch (token in Redis is different)
    different_token_in_store = create_refresh_token(data={"sub": username, "token_type": "refresh", "nonce": "different"})
    mock_redis_client.get.side_effect = lambda key: {
        api_refresh_token_key: different_token_in_store,
        vivint_refresh_token_key: valid_vivint_refresh_token
    }.get(key)
    
    response = await client.post(
        "/auth/refresh-token",
        json={"refresh_token": some_generated_token} # Submitting a token different from store
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid or expired refresh token. (Not found in store or mismatch)"
    # Important: If a mismatch occurs, the token in Redis SHOULD be deleted
    mock_redis_client.delete.assert_called_once_with(api_refresh_token_key)
    mock_redis_client.delete.reset_mock() # Reset for next assertion

    # Scenario 3: Vivint refresh token not found in Redis (should ideally not happen if API token is there)
    valid_api_refresh_token = create_refresh_token(data={"sub": username, "token_type": "refresh"})
    mock_redis_client.get.side_effect = lambda key: {
        api_refresh_token_key: valid_api_refresh_token,
        # vivint_refresh_token_key will return None
    }.get(key)

    response = await client.post(
        "/auth/refresh-token",
        json={"refresh_token": valid_api_refresh_token}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    # This implies an issue with the underlying session, so the API refresh token might be cleared
    assert response.json()["detail"] == "Could not validate credentials" # Or more specific error
    # Depending on implementation, the API token might be deleted here too.
    # Current router code for /refresh-token doesn't explicitly delete on vivint_refresh_token lookup failure,
    # but the subsequent get_current_user in a protected route would fail.
    # For refresh endpoint, it's more about the API refresh token itself.
    # Let's assume the detail from JWTError due to missing vivint_refresh_token in new access token creation

    # Scenario 4: Malformed/Expired JWT
    # Reset Redis mock to a clean state for this sub-test
    mock_redis_client.get.side_effect = None
    mock_redis_client.get.return_value = None # Default to not found
    mock_redis_client.set.reset_mock()
    mock_redis_client.delete.reset_mock()

    response = await client.post(
        "/auth/refresh-token",
        json={"refresh_token": "a.b.c"} # Malformed token
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Could not validate credentials"

    expired_token = create_refresh_token(data={"sub": username, "token_type": "refresh"}, expires_delta=timedelta(seconds=-3600))
    response = await client.post(
        "/auth/refresh-token",
        json={"refresh_token": expired_token}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Could not validate credentials"

# Test for get_current_user dependency's Redis validation
async def test_get_current_user_redis_validation(client: AsyncClient, mock_redis_client: AsyncMock):
    from fastapi import FastAPI, Depends, HTTPException
    from vivintpy_api.models.auth import TokenData # Assuming TokenData is the return type of get_current_user
    from vivintpy_api.deps import get_current_user # The dependency to test

    # Create a dummy app and a protected route for testing get_current_user
    dummy_app = FastAPI()

    @dummy_app.get("/protected-route")
    async def protected_route(current_user: TokenData = Depends(get_current_user)):
        return {"username": current_user.username, "message": "Access granted"}

    # Override dependencies for the dummy app's client
    dummy_app.dependency_overrides[deps.get_redis_client] = lambda: mock_redis_client
    
    # Use a new AsyncClient for the dummy_app
    # Note: The main 'client' fixture is for the main app, we need a new one for dummy_app
    async with AsyncClient(transport=ASGITransport(app=dummy_app), base_url="http://test") as dummy_client:
        username = "testuser_get_current"
        jwt_vivint_refresh_token = "jwt_vivint_refresh_token_value"
        redis_vivint_refresh_token_key = f"user:{username}:vivint_refresh_token"

        # Scenario A: Success - JWT vivint_refresh_token matches Redis
        access_token_A_data = {
            "sub": username, 
            "token_type": "access", 
            "vivint_refresh_token": jwt_vivint_refresh_token
        }
        access_token_A = deps.create_access_token(data=access_token_A_data)
        
        mock_redis_client.get.side_effect = None # Clear previous side effects
        mock_redis_client.get.return_value = jwt_vivint_refresh_token.encode('utf-8') # Match

        response_A = await dummy_client.get("/protected-route", headers={"Authorization": f"Bearer {access_token_A}"})
        assert response_A.status_code == status.HTTP_200_OK
        assert response_A.json() == {"username": username, "message": "Access granted"}
        mock_redis_client.get.assert_called_once_with(redis_vivint_refresh_token_key)
        mock_redis_client.get.reset_mock()

        # Scenario B: Failure - JWT vivint_refresh_token MISMATCHES Redis
        access_token_B_data = {
            "sub": username, 
            "token_type": "access", 
            "vivint_refresh_token": jwt_vivint_refresh_token # This is what JWT claims
        }
        access_token_B = deps.create_access_token(data=access_token_B_data)
        
        mock_redis_client.get.return_value = b"different_vivint_refresh_token_in_redis" # Mismatch

        response_B = await dummy_client.get("/protected-route", headers={"Authorization": f"Bearer {access_token_B}"})
        assert response_B.status_code == status.HTTP_401_UNAUTHORIZED
        assert response_B.json()["detail"] == "Vivint session changed or revoked. Please log in again."
        mock_redis_client.get.assert_called_once_with(redis_vivint_refresh_token_key)
        mock_redis_client.get.reset_mock()

        # Scenario C: Failure - Vivint_refresh_token NOT FOUND in Redis
        access_token_C_data = {
            "sub": username, 
            "token_type": "access", 
            "vivint_refresh_token": jwt_vivint_refresh_token
        }
        access_token_C = deps.create_access_token(data=access_token_C_data)
        
        mock_redis_client.get.return_value = None # Not found in Redis

        response_C = await dummy_client.get("/protected-route", headers={"Authorization": f"Bearer {access_token_C}"})
        assert response_C.status_code == status.HTTP_401_UNAUTHORIZED
        assert response_C.json()["detail"] == "Vivint session changed or revoked. Please log in again."
        mock_redis_client.get.assert_called_once_with(redis_vivint_refresh_token_key)
        mock_redis_client.get.reset_mock()

        # Scenario D: Failure - Malformed token (e.g., missing vivint_refresh_token claim in JWT)
        access_token_D_data = {"sub": username, "token_type": "access"} # Missing vivint_refresh_token
        access_token_D = deps.create_access_token(data=access_token_D_data)

        response_D = await dummy_client.get("/protected-route", headers={"Authorization": f"Bearer {access_token_D}"})
        assert response_D.status_code == status.HTTP_401_UNAUTHORIZED
        # This specific detail comes from the JWT decoding part of get_current_user
        assert response_D.json()["detail"] == "Could not validate credentials"
        # mock_redis_client.get should not have been called for this case as JWT validation fails first
        mock_redis_client.get.assert_not_called()
