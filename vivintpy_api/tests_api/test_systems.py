import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from starlette import status
from jose import jwt, JWTError

from vivintpy_api.main import app
from vivintpy_api import deps
from vivintpy_api.config import settings
from vivintpy_api.deps import get_current_active_user, TokenData
from vivintpy.account import Account
from vivintpy.system import System
from vivintpy.devices.alarm_panel import AlarmPanel
from vivintpy.exceptions import VivintSkyApiError

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

# --- Test Fixtures ---

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac

@pytest.fixture
def mock_user_token_data() -> TokenData:
    return TokenData(username="testuser", vivint_refresh_token="fake_vivint_refresh_token")

@pytest.fixture
def mock_auth_token(mock_user_token_data: TokenData) -> str:
    to_encode = mock_user_token_data.model_dump()
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

@pytest.fixture
def mock_alarm_panel() -> MagicMock:
    panel = AsyncMock(spec=AlarmPanel)
    panel.id = 98765
    panel.name = "Main Panel"
    panel.state = "disarmed"
    panel.is_disarmed = True
    panel.is_armed_stay = False
    panel.is_armed_away = False
    # Add other relevant attributes and methods to mock
    panel.arm_stay = AsyncMock()
    panel.arm_away = AsyncMock()
    panel.disarm = AsyncMock()
    panel.trigger_emergency = AsyncMock()
    panel.reboot = AsyncMock()
    panel.model_dump = MagicMock(return_value={"id": panel.id, "name": panel.name, "state": panel.state})
    return panel

@pytest.fixture
def mock_system(mock_alarm_panel: MagicMock) -> MagicMock:
    system = AsyncMock(spec=System)
    system.id = 12345
    system.name = "Home System"
    system.alarm_panel = mock_alarm_panel
    system.get_alarm_panel = AsyncMock(return_value=mock_alarm_panel)
    # Add other relevant attributes and methods to mock
    system.model_dump = MagicMock(return_value={"id": system.id, "name": system.name, "panel_id": mock_alarm_panel.id})
    return system

@pytest.fixture
def mock_vivint_account(mock_system: MagicMock) -> MagicMock:
    account = AsyncMock(spec=Account)
    account.username = "testuser"
    account.is_connected = True
    account.systems = {mock_system.id: mock_system}
    account.get_system = MagicMock(return_value=mock_system) # Default to returning the mock system
    
    async def get_system_by_id(system_id: int):
        return account.systems.get(system_id)
    
    account.get_system.side_effect = get_system_by_id
    return account

# --- Dependency Override ---

async def override_get_current_active_user(
    token_data: TokenData = TokenData(username="testuser", vivint_refresh_token="test_refresh")
) -> TokenData:
    # This override will be used by tests that need an authenticated user
    # For tests checking unauthenticated access, this won't be hit if no token is provided.
    return token_data

async def override_get_shared_vivint_account(
    mock_account_fixture: MagicMock # This will be parameterized in tests
) -> MagicMock:
    return mock_account_fixture


# --- Test Cases ---

async def test_list_systems_unauthenticated(client: AsyncClient):
    response = await client.get("/systems/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

async def test_list_systems_success(client: AsyncClient, mock_auth_token: str, mock_vivint_account: MagicMock, mock_system: MagicMock, mock_user_token_data: TokenData):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user_token_data
    app.dependency_overrides[deps.get_shared_vivint_account] = lambda: mock_vivint_account
    
    response = await client.get("/systems/", headers={"Authorization": f"Bearer {mock_auth_token}"})
    
    assert response.status_code == status.HTTP_200_OK
    systems_list = response.json()
    assert len(systems_list) == 1
    assert systems_list[0]["id"] == mock_system.id
    assert systems_list[0]["name"] == mock_system.name
    
    # Clean up overrides
    app.dependency_overrides = {}

async def test_get_system_detail_success(client: AsyncClient, mock_auth_token: str, mock_vivint_account: MagicMock, mock_system: MagicMock, mock_user_token_data: TokenData):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user_token_data
    app.dependency_overrides[deps.get_shared_vivint_account] = lambda: mock_vivint_account

    response = await client.get(f"/systems/{mock_system.id}", headers={"Authorization": f"Bearer {mock_auth_token}"})
    
    assert response.status_code == status.HTTP_200_OK
    system_data = response.json()
    assert system_data["id"] == mock_system.id
    assert system_data["name"] == mock_system.name
    
    app.dependency_overrides = {}

async def test_get_system_detail_not_found(client: AsyncClient, mock_auth_token: str, mock_vivint_account: MagicMock, mock_user_token_data: TokenData):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user_token_data
    app.dependency_overrides[deps.get_shared_vivint_account] = lambda: mock_vivint_account # Account has no system with ID 999

    response = await client.get("/systems/999", headers={"Authorization": f"Bearer {mock_auth_token}"})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "System with ID 999 not found."
    
    app.dependency_overrides = {}

async def test_get_panel_detail_success(client: AsyncClient, mock_auth_token: str, mock_vivint_account: MagicMock, mock_system: MagicMock, mock_alarm_panel: MagicMock, mock_user_token_data: TokenData):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user_token_data
    app.dependency_overrides[deps.get_shared_vivint_account] = lambda: mock_vivint_account

    response = await client.get(f"/systems/{mock_system.id}/panel", headers={"Authorization": f"Bearer {mock_auth_token}"})
    
    assert response.status_code == status.HTTP_200_OK
    panel_data = response.json()
    assert panel_data["id"] == mock_alarm_panel.id
    assert panel_data["name"] == mock_alarm_panel.name
    
    app.dependency_overrides = {}

async def test_get_panel_detail_system_not_found(client: AsyncClient, mock_auth_token: str, mock_vivint_account: MagicMock, mock_user_token_data: TokenData):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user_token_data
    app.dependency_overrides[deps.get_shared_vivint_account] = lambda: mock_vivint_account
    
    response = await client.get("/systems/999/panel", headers={"Authorization": f"Bearer {mock_auth_token}"})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "System with ID 999 not found."
    
    app.dependency_overrides = {}

async def test_get_panel_detail_panel_not_found(client: AsyncClient, mock_auth_token: str, mock_vivint_account: MagicMock, mock_system: MagicMock, mock_user_token_data: TokenData):
    mock_system_no_panel = AsyncMock(spec=System)
    mock_system_no_panel.id = mock_system.id
    mock_system_no_panel.name = "System Without Panel"
    mock_system_no_panel.alarm_panel = None # Simulate no panel
    mock_system_no_panel.get_alarm_panel = AsyncMock(return_value=None)
    mock_vivint_account.systems = {mock_system_no_panel.id: mock_system_no_panel} # Override account's systems
    
    app.dependency_overrides[get_current_active_user] = lambda: mock_user_token_data
    app.dependency_overrides[deps.get_shared_vivint_account] = lambda: mock_vivint_account

    response = await client.get(f"/systems/{mock_system_no_panel.id}/panel", headers={"Authorization": f"Bearer {mock_auth_token}"})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == f"Alarm panel not found for system ID {mock_system_no_panel.id}."
    
    app.dependency_overrides = {}
    # Reset mock_vivint_account systems for other tests
    mock_vivint_account.systems = {mock_system.id: mock_system}


# Panel Action Tests (Arm Stay, Arm Away, Disarm, Trigger, Reboot)
# These will follow a similar pattern: mock panel method, call endpoint, assert status and mock calls.

@pytest.mark.parametrize("action, panel_method_name", [
    ("arm-stay", "arm_stay"),
    ("arm-away", "arm_away"),
])
async def test_panel_arm_actions_success(
    client: AsyncClient, mock_auth_token: str, mock_vivint_account: MagicMock, 
    mock_system: MagicMock, mock_alarm_panel: MagicMock, mock_user_token_data: TokenData,
    action: str, panel_method_name: str
):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user_token_data
    app.dependency_overrides[deps.get_shared_vivint_account] = lambda: mock_vivint_account
    
    panel_method_mock = getattr(mock_alarm_panel, panel_method_name)
    panel_method_mock.reset_mock() # Ensure clean state for assertion

    response = await client.post(f"/systems/{mock_system.id}/panel/{action}", headers={"Authorization": f"Bearer {mock_auth_token}"})
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == f"Panel successfully commanded to {action.replace('-', ' ')}."
    panel_method_mock.assert_called_once()
    
    app.dependency_overrides = {}

async def test_panel_disarm_success(client: AsyncClient, mock_auth_token: str, mock_vivint_account: MagicMock, mock_system: MagicMock, mock_alarm_panel: MagicMock, mock_user_token_data: TokenData):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user_token_data
    app.dependency_overrides[deps.get_shared_vivint_account] = lambda: mock_vivint_account
    mock_alarm_panel.disarm.reset_mock()

    pin = "1234"
    response = await client.post(
        f"/systems/{mock_system.id}/panel/disarm", 
        headers={"Authorization": f"Bearer {mock_auth_token}"},
        json={"pin_code": pin}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Panel successfully commanded to disarm."
    mock_alarm_panel.disarm.assert_called_once_with(pin)
    
    app.dependency_overrides = {}

async def test_panel_trigger_emergency_success(client: AsyncClient, mock_auth_token: str, mock_vivint_account: MagicMock, mock_system: MagicMock, mock_alarm_panel: MagicMock, mock_user_token_data: TokenData):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user_token_data
    app.dependency_overrides[deps.get_shared_vivint_account] = lambda: mock_vivint_account
    mock_alarm_panel.trigger_emergency.reset_mock()

    response = await client.post(f"/systems/{mock_system.id}/panel/trigger-emergency", headers={"Authorization": f"Bearer {mock_auth_token}"})
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Panel successfully commanded to trigger emergency."
    mock_alarm_panel.trigger_emergency.assert_called_once()
    
    app.dependency_overrides = {}

async def test_panel_reboot_success(client: AsyncClient, mock_auth_token: str, mock_vivint_account: MagicMock, mock_system: MagicMock, mock_alarm_panel: MagicMock, mock_user_token_data: TokenData):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user_token_data
    app.dependency_overrides[deps.get_shared_vivint_account] = lambda: mock_vivint_account
    mock_alarm_panel.reboot.reset_mock()

    response = await client.post(f"/systems/{mock_system.id}/panel/reboot", headers={"Authorization": f"Bearer {mock_auth_token}"})
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Panel successfully commanded to reboot."
    mock_alarm_panel.reboot.assert_called_once()
    
    app.dependency_overrides = {}

# Test for VivintSkyApiError during panel action
@pytest.mark.parametrize("action_path, panel_method_name, request_body", [
    ("arm-stay", "arm_stay", None),
    ("arm-away", "arm_away", None),
    ("disarm", "disarm", {"pin_code": "1234"}),
    ("trigger-emergency", "trigger_emergency", None),
    ("reboot", "reboot", None),
])
async def test_panel_action_vivint_error(
    client: AsyncClient, mock_auth_token: str, mock_vivint_account: MagicMock, 
    mock_system: MagicMock, mock_alarm_panel: MagicMock, mock_user_token_data: TokenData,
    action_path: str, panel_method_name: str, request_body: Dict[str, Any]
):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user_token_data
    app.dependency_overrides[deps.get_shared_vivint_account] = lambda: mock_vivint_account
    
    panel_method_mock = getattr(mock_alarm_panel, panel_method_name)
    panel_method_mock.side_effect = VivintSkyApiError("Vivint API Error")
    panel_method_mock.reset_mock()

    if request_body:
        response = await client.post(
            f"/systems/{mock_system.id}/panel/{action_path}", 
            headers={"Authorization": f"Bearer {mock_auth_token}"},
            json=request_body
        )
    else:
        response = await client.post(
            f"/systems/{mock_system.id}/panel/{action_path}", 
            headers={"Authorization": f"Bearer {mock_auth_token}"}
        )
            
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.json()["detail"] == "Vivint API Error"
    
    if panel_method_name == "disarm":
         panel_method_mock.assert_called_once_with(request_body["pin_code"])
    else:
        panel_method_mock.assert_called_once()
    
    app.dependency_overrides = {}
    panel_method_mock.side_effect = None # Reset side effect
