import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import status
from jose import jwt

from vivintpy_api.main import app  # Import your FastAPI app
from vivintpy_api.config import settings # For JWT settings
from vivintpy import VivintSkyApiAuthenticationError, VivintSkyApiMfaRequiredError
from vivintpy.account import Account # For type hinting mocks

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac

@pytest.fixture
def mock_vivint_account_no_mfa():
    mock_account = AsyncMock(spec=Account)
    mock_account.username = "testuser"
    mock_account.password = "testpassword"
    mock_account.api = AsyncMock()
    mock_account.api.refresh_token = "fake_vivint_refresh_token_no_mfa"
    mock_account.is_connected = True # Assume connect is successful
    
    async def mock_connect():
        mock_account.is_connected = True
        # Simulate loading systems and devices if your app expects it post-connect
        mock_account.systems = {} 
        mock_account.devices = {}
        return True # Indicate successful connection
    
    mock_account.connect = AsyncMock(side_effect=mock_connect)
    mock_account.disconnect = AsyncMock()
    return mock_account

@pytest.fixture
def mock_vivint_account_mfa_required():
    mock_account = AsyncMock(spec=Account)
    mock_account.username = "testuser_mfa"
    mock_account.password = "testpassword_mfa"
    mock_account.api = AsyncMock()
    # No refresh token initially, MFA will be required
    
    async def mock_connect_mfa():
        # Simulate MFA being required
        raise VivintSkyApiMfaRequiredError("MFA Code Required", user_id="test_user_id", panel_id=123)
    
    mock_account.connect = AsyncMock(side_effect=mock_connect_mfa)
    
    async def mock_verify_mfa(code: str):
        if code == "123456":
            mock_account.api.refresh_token = "fake_vivint_refresh_token_after_mfa"
            mock_account.is_connected = True
            # Simulate loading systems and devices
            mock_account.systems = {} 
            mock_account.devices = {}
            return True # MFA successful
        raise VivintSkyApiAuthenticationError("Invalid MFA code")

    mock_account.verify_mfa = AsyncMock(side_effect=mock_verify_mfa)
    mock_account.disconnect = AsyncMock()
    return mock_account

async def test_login_success_no_mfa(client: AsyncClient, mock_vivint_account_no_mfa: MagicMock):
    with patch("vivintpy_api.routers.auth.Account", return_value=mock_vivint_account_no_mfa):
        with patch("vivintpy_api.main.Account", return_value=mock_vivint_account_no_mfa): # For lifespan
            app.state.vivint_account = mock_vivint_account_no_mfa # Ensure lifespan uses the mock
            
            response = await client.post(
                "/auth/login",
                data={"username": "testuser", "password": "testpassword"}
            )
            assert response.status_code == status.HTTP_200_OK
            token_data = response.json()
            assert "access_token" in token_data
            assert token_data["token_type"] == "bearer"
            
            payload = jwt.decode(token_data["access_token"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            assert payload["sub"] == "testuser"
            assert payload["vivint_refresh_token"] == "fake_vivint_refresh_token_no_mfa"
            
            mock_vivint_account_no_mfa.connect.assert_called_once()
            # Ensure disconnect is called when client context manager exits if lifespan is active
            # This might need more sophisticated handling of app state for testing lifespan

async def test_login_mfa_required(client: AsyncClient, mock_vivint_account_mfa_required: MagicMock):
    with patch("vivintpy_api.routers.auth.Account", return_value=mock_vivint_account_mfa_required):
        with patch("vivintpy_api.main.Account", return_value=mock_vivint_account_mfa_required):
            app.state.vivint_account = mock_vivint_account_mfa_required

            response = await client.post(
                "/auth/login",
                data={"username": "testuser_mfa", "password": "testpassword_mfa"}
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED # Or a custom MFA status
            error_data = response.json()
            assert error_data["detail"] == "MFA_REQUIRED"
            assert "user_id" in error_data 
            assert error_data["user_id"] == "test_user_id" # From VivintSkyApiMfaRequiredError
            
            mock_vivint_account_mfa_required.connect.assert_called_once()

async def test_verify_mfa_success(client: AsyncClient, mock_vivint_account_mfa_required: MagicMock):
    # Simulate that the login attempt already happened and raised MFA required
    # The state of the account (e.g., user_id) would be set by the VivintSkyApiMfaRequiredError
    # For this test, we assume the Account instance is the same one that raised MFA.
    # In a real app, this state might be stored in a session or a temporary cache.
    # Here, we rely on the mock's state.
    
    # We need to ensure the same Account instance is used by get_mfa_account_dependency
    # This is tricky because the dependency creates a new Account instance.
    # For simplicity, we'll patch Account in deps.py for this specific test.
    # A more robust solution might involve a test-specific dependency override.
    
    # Mock the Account instance that verify_mfa will use
    # This mock will be used by the get_mfa_account_dependency
    app.state.pending_mfa_accounts = {"test_user_id": mock_vivint_account_mfa_required}

    with patch("vivintpy_api.deps.Account", return_value=mock_vivint_account_mfa_required):
        response = await client.post(
            "/auth/verify-mfa",
            json={"user_id": "test_user_id", "mfa_code": "123456"}
        )
        assert response.status_code == status.HTTP_200_OK
        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        
        payload = jwt.decode(token_data["access_token"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        # Username for JWT sub should come from the account after successful MFA
        assert payload["sub"] == mock_vivint_account_mfa_required.username 
        assert payload["vivint_refresh_token"] == "fake_vivint_refresh_token_after_mfa"
        
        mock_vivint_account_mfa_required.verify_mfa.assert_called_once_with("123456")
    
    # Clean up app state
    del app.state.pending_mfa_accounts["test_user_id"]


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

async def test_verify_mfa_invalid_code(client: AsyncClient, mock_vivint_account_mfa_required: MagicMock):
    app.state.pending_mfa_accounts = {"test_user_id": mock_vivint_account_mfa_required}

    with patch("vivintpy_api.deps.Account", return_value=mock_vivint_account_mfa_required):
        response = await client.post(
            "/auth/verify-mfa",
            json={"user_id": "test_user_id", "mfa_code": "wrongcode"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        error_data = response.json()
        assert error_data["detail"] == "Invalid MFA code or user ID."
        
        mock_vivint_account_mfa_required.verify_mfa.assert_called_once_with("wrongcode")

    del app.state.pending_mfa_accounts["test_user_id"]

async def test_verify_mfa_user_id_not_found(client: AsyncClient):
    # No user_id in app.state.pending_mfa_accounts
    app.state.pending_mfa_accounts = {} 
    
    response = await client.post(
        "/auth/verify-mfa",
        json={"user_id": "non_existent_user_id", "mfa_code": "123456"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error_data = response.json()
    assert error_data["detail"] == "MFA session not found or expired for this user ID."
