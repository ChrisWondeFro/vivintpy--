"""Tests for the devices API endpoints."""

from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from vivintpy.devices.camera import Camera
from vivintpy.devices.door_lock import DoorLock
from vivintpy.devices.garage_door import GarageDoor
from vivintpy.devices.switch import BinarySwitch
from vivintpy.devices.thermostat import Thermostat
from vivintpy.entity import Entity
from vivintpy.enums import ArmedState, DeviceType
from vivintpy.exceptions import VivintDeviceFeatureNotSupportedError, VivintSkyApiError
from vivintpy.system import System
from vivintpy.account import Account

from vivintpy_api.models.token import TokenData
from vivintpy_api import deps

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_user_token_data() -> TokenData:
    """Return a mock user token data."""
    return TokenData(
        username="test_user_id",  # Changed user_id to username
        vivint_refresh_token="test_vivint_refresh_token",
        is_mfa_verified=True,
    )


from jose import jwt
from vivintpy_api.config import settings

@pytest.fixture
def mock_auth_token(mock_user_token_data: TokenData) -> str:
    """Return a mock auth token string."""
    to_encode = mock_user_token_data.model_dump()
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def mock_lock_device() -> DoorLock:
    """Return a mock lock device."""
    mock_device = MagicMock(spec=DoorLock)
    mock_device.id = 1
    mock_device.name = "Front Door"
    mock_device.device_type = DeviceType.DOOR_LOCK
    mock_device.manufacturer = "MockManufacturer"
    mock_device.model = "MockModel"
    mock_device.serial_number = "MockSN123"
    mock_device.software_version = "1.0.0"
    mock_device.firmware_version = "1.0.0"
    mock_device.online = True
    mock_device.low_battery = False
    mock_device.battery_level = 90
    mock_device.is_locked = False
    mock_device.set_locked = AsyncMock()
    return mock_device


@pytest.fixture
def mock_binary_switch_device() -> BinarySwitch:
    """Return a mock binary switch device."""
    mock_device = MagicMock(spec=BinarySwitch)
    mock_device.id = 2
    mock_device.name = "Living Room Lamp"
    mock_device.device_type = DeviceType.BINARY_SWITCH
    mock_device.manufacturer = "MockManufacturer"
    mock_device.model = "MockModel"
    mock_device.serial_number = "MockSN002"
    mock_device.software_version = "1.0.1"
    mock_device.firmware_version = "1.0.1"
    mock_device.online = True
    mock_device.low_battery = False
    mock_device.battery_level = 95
    mock_device.is_on = False
    mock_device.set_state = AsyncMock()
    return mock_device


@pytest.fixture
def mock_thermostat_device() -> Thermostat:
    """Return a mock thermostat device."""
    mock_device = MagicMock(spec=Thermostat)
    mock_device.id = 3
    mock_device.name = "Main Thermostat"
    mock_device.device_type = DeviceType.THERMOSTAT
    mock_device.manufacturer = "MockManufacturer"
    mock_device.model = "MockThermostatModel"
    mock_device.serial_number = "MockSN003"
    mock_device.software_version = "2.0.0"
    mock_device.firmware_version = "2.0.0"
    mock_device.online = True
    mock_device.low_battery = None  # Thermostats might not have battery
    mock_device.battery_level = None # Thermostats might not have battery
    mock_device.set_state = AsyncMock()
    return mock_device


@pytest.fixture
def mock_camera_device() -> Camera:
    """Return a mock camera device."""
    mock_device = MagicMock(spec=Camera)
    mock_device.id = 4
    mock_device.name = "Driveway Camera"
    mock_device.device_type = DeviceType.CAMERA
    mock_device.manufacturer = "MockManufacturer"
    mock_device.model = "MockCameraModel"
    mock_device.serial_number = "MockSN004"
    mock_device.software_version = "3.0.0"
    mock_device.firmware_version = "3.0.0"
    mock_device.online = True
    mock_device.low_battery = False
    mock_device.battery_level = 80
    mock_device.get_snapshot_url = AsyncMock(return_value="http://snapshot.url")
    return mock_device


@pytest.fixture
def mock_garage_door_device() -> GarageDoor:
    """Return a mock garage door device."""
    mock_device = MagicMock(spec=GarageDoor)
    mock_device.id = 5
    mock_device.name = "Main Garage Door"
    mock_device.device_type = DeviceType.GARAGE_DOOR
    mock_device.manufacturer = "MockManufacturer"
    mock_device.model = "MockGarageModel"
    mock_device.serial_number = "MockSN005"
    mock_device.software_version = "1.5.0"
    mock_device.firmware_version = "1.5.0"
    mock_device.online = True
    mock_device.low_battery = True
    mock_device.battery_level = 20
    mock_device.set_state = AsyncMock()
    return mock_device


@pytest.fixture
def mock_system_with_devices(
    mock_lock_device: DoorLock,
    mock_binary_switch_device: BinarySwitch,
    mock_thermostat_device: Thermostat,
    mock_camera_device: Camera,
    mock_garage_door_device: GarageDoor,
) -> System:
    """Return a mock system with a variety of devices."""
    mock_system = MagicMock(spec=System)
    mock_system.id = 12345
    mock_system.panel = MagicMock()
    mock_system.panel.id = 54321

    _device_map_content = {
        mock_lock_device.id: mock_lock_device,
        mock_binary_switch_device.id: mock_binary_switch_device,
        mock_thermostat_device.id: mock_thermostat_device,
        mock_camera_device.id: mock_camera_device,
        mock_garage_door_device.id: mock_garage_door_device,
    }
    mock_system.device_map = _device_map_content

    # Mock the .devices property to return the device_map's content
    # This is needed because the router's list_devices_in_system accesses system.devices
    type(mock_system).devices = PropertyMock(return_value=_device_map_content)

    def _debug_get_device_direct(device_id_param):
        print(f"--- DEBUG DIRECT: _debug_get_device_direct called with d_id: {device_id_param} (type: {type(device_id_param)}) ---")
        print(f"--- DEBUG DIRECT: mock_system.device_map keys: {list(mock_system.device_map.keys())} ---")
        device = mock_system.device_map.get(device_id_param)
        print(f"--- DEBUG DIRECT: device found: {device is not None} ---")
        return device

    # Directly replace the method on the instance
    mock_system.get_device = _debug_get_device_direct
    print(f"--- MOCK_SYSTEM_WITH_DEVICES FIXTURE: mock_system id {id(mock_system)}, get_device is {mock_system.get_device} ({getattr(mock_system.get_device, '__name__', 'N/A')}) ---")
    
    return mock_system


@pytest.fixture
def mock_vivint_account_with_system_and_devices(mock_system_with_devices: System) -> MagicMock:
    """Return a mock Vivint account with a system and devices."""
    mock_account = MagicMock(spec=Account)
    mock_account.systems = [mock_system_with_devices]

    return mock_account


from typing import AsyncGenerator
from vivintpy_api.main import app # Ensure app is imported

@pytest_asyncio.fixture
async def client(
    mock_vivint_account_with_system_and_devices: Account,
    mock_auth_token: TokenData,
) -> AsyncGenerator[AsyncClient, None]:
    # Print info about the system instance being injected via the account mock
    if mock_vivint_account_with_system_and_devices.systems:
        injected_system = mock_vivint_account_with_system_and_devices.systems[0]
        print(f"--- CLIENT FIXTURE: Injected system id {id(injected_system)}, get_device is {getattr(injected_system, 'get_device', 'MISSING_GET_DEVICE')} ({getattr(getattr(injected_system, 'get_device', None), '__name__', 'N/A')}) ---")
    else:
        print("--- CLIENT FIXTURE: No systems found in mock_vivint_account_with_system_and_devices ---")

    app.dependency_overrides[deps.get_current_active_user] = lambda: mock_auth_token
    app.dependency_overrides[
        deps.get_shared_vivint_account
    ] = lambda: mock_vivint_account_with_system_and_devices
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

    app.dependency_overrides = {}


async def test_get_devices(
    client: AsyncClient, mock_system_with_devices: System
) -> None:
    """Test getting all devices for a system."""
    system_id_val = mock_system_with_devices.id
    url = f"/systems/{system_id_val}/devices/"
    response = await client.get(url)

    assert response.status_code == HTTPStatus.OK
    response_data = response.json()
    assert len(response_data) == len(mock_system_with_devices.devices)
    assert response_data[0]["id"] == 1
    assert response_data[0]["name"] == "Front Door"


async def test_get_device(
    client: AsyncClient, mock_system_with_devices: System, mock_lock_device: DoorLock
) -> None:
    """Test getting a specific device."""
    response = await client.get(
        f"/systems/{mock_system_with_devices.id}/devices/{mock_lock_device.id}"
    )

    assert response.status_code == HTTPStatus.OK
    response_data = response.json()
    assert response_data["id"] == mock_lock_device.id
    assert response_data["name"] == mock_lock_device.name


async def test_get_device_not_found(
    client: AsyncClient, mock_system_with_devices: System
) -> None:
    """Test getting a device that does not exist."""
    response = await client.get(f"/systems/{mock_system_with_devices.id}/devices/999")

    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_set_lock_state(
    client: AsyncClient,
    mock_system_with_devices: System,
    mock_lock_device: DoorLock,
) -> None:
    """Test setting the lock state of a door lock."""
    response = await client.put(
        f"/systems/{mock_system_with_devices.id}/devices/{mock_lock_device.id}/set-locked",
        json={"locked": True},
    )

    assert response.status_code == HTTPStatus.OK
    mock_lock_device.set_locked.assert_awaited_once_with(True)

    response = await client.put(
        f"/systems/{mock_system_with_devices.id}/devices/{mock_lock_device.id}/set-locked",
        json={"locked": False},
    )

    assert response.status_code == HTTPStatus.OK
    mock_lock_device.set_locked.assert_awaited_with(False)


async def test_set_switch_state(
    client: AsyncClient,
    mock_system_with_devices: System,
    mock_binary_switch_device: BinarySwitch,
) -> None:
    """Test setting the state of a binary switch."""
    response = await client.put(
        f"/systems/{mock_system_with_devices.id}/devices/{mock_binary_switch_device.id}/set-state",
        json={"on": True},
    )

    assert response.status_code == HTTPStatus.OK
    mock_binary_switch_device.set_state.assert_awaited_once_with(True)

    response = await client.put(
        f"/systems/{mock_system_with_devices.id}/devices/{mock_binary_switch_device.id}/set-state",
        json={"on": False},
    )

    assert response.status_code == HTTPStatus.OK
    mock_binary_switch_device.set_state.assert_awaited_with(False)


async def test_set_thermostat_state(
    client: AsyncClient,
    mock_system_with_devices: System,
    mock_thermostat_device: Thermostat,
) -> None:
    """Test setting the state of a thermostat."""
    thermostat_state = {
        "fan_mode": "auto",
        "hold_mode": "until_next_period",
        "cool_set_point": 24.0,
        "heat_set_point": 20.0,
    }
    response = await client.put(
        f"/systems/{mock_system_with_devices.id}/devices/{mock_thermostat_device.id}/set-state",
        json=thermostat_state,
    )

    assert response.status_code == HTTPStatus.OK
    mock_thermostat_device.set_state.assert_awaited_once_with(**thermostat_state)


async def test_get_camera_snapshot(
    client: AsyncClient,
    mock_system_with_devices: System,
    mock_camera_device: Camera,
) -> None:
    """Test getting a camera snapshot URL."""
    response = await client.get(
        f"/systems/{mock_system_with_devices.id}/devices/{mock_camera_device.id}/snapshot"
    )

    assert response.status_code == HTTPStatus.OK
    response_data = response.json()
    assert response_data["url"] == "http://snapshot.url"
    mock_camera_device.get_snapshot_url.assert_awaited_once()


async def test_set_garage_door_state(
    client: AsyncClient,
    mock_system_with_devices: System,
    mock_garage_door_device: GarageDoor,
) -> None:
    """Test setting the state of a garage door."""
    response = await client.put(
        f"/systems/{mock_system_with_devices.id}/devices/{mock_garage_door_device.id}/set-state",
        json={"open": True},
    )

    assert response.status_code == HTTPStatus.OK
    mock_garage_door_device.set_state.assert_awaited_once_with(True)

    response = await client.put(
        f"/systems/{mock_system_with_devices.id}/devices/{mock_garage_door_device.id}/set-state",
        json={"open": False},
    )

    assert response.status_code == HTTPStatus.OK
    mock_garage_door_device.set_state.assert_awaited_with(False)


async def test_device_action_vivint_sky_api_error(
    client: AsyncClient,
    mock_system_with_devices: System,
    mock_lock_device: DoorLock,
) -> None:
    """Test a device action that raises a VivintSkyApiError."""
    mock_lock_device.set_locked.side_effect = VivintSkyApiError("API Error")
    response = await client.put(
        f"/systems/{mock_system_with_devices.id}/devices/{mock_lock_device.id}/set-locked",
        json={"locked": True},
    )

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "VivintSkyApiError: API Error"}


async def test_device_action_not_supported(
    client: AsyncClient,
    mock_system_with_devices: System,
    mock_lock_device: DoorLock,
) -> None:
    """Test a device action that is not supported."""
    mock_lock_device.set_locked.side_effect = VivintDeviceFeatureNotSupportedError(
        "Not Supported"
    )
    response = await client.put(
        f"/systems/{mock_system_with_devices.id}/devices/{mock_lock_device.id}/set-locked",
        json={"locked": True},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "VivintDeviceFeatureNotSupportedError: Not Supported"}

