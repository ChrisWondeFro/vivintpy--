"""Tests for AlarmPanel battery/tamper/bypass helpers and update flow."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from vivintpy.const import AlarmPanelAttribute as Attribute, VivintDeviceAttribute
from vivintpy.devices import VivintDevice, BypassTamperDevice
from vivintpy.devices.alarm_panel import AlarmPanel
from vivintpy.enums import ZoneBypass, DeviceType, ArmedState
from vivintpy.models import AlarmPanelData


class MockDevice(VivintDevice):
    """Mock device for testing."""
    pass


class MockBypassTamperDevice(BypassTamperDevice):
    """Mock device with bypass/tamper capabilities."""
    pass


@pytest.fixture()
def mock_system():
    """Create a mock system."""
    system = SimpleNamespace()
    system.api = MagicMock()
    system.name = "Test System"
    return system


@pytest.fixture()
def basic_panel_data():
    """Basic panel data for creating alarm panels."""
    return {
        "panid": 123,
        "parid": 1,
        "pmac": "AA:BB:CC:DD:EE:FF",
        "s": ArmedState.DISARMED,
        "d": [],
        "ureg": []
    }


@pytest.fixture()
def panel_with_devices(mock_system, basic_panel_data):
    """Create an alarm panel with mock devices."""
    # Add devices to panel data
    basic_panel_data["d"] = [
        {
            "_id": 1,
            "t": DeviceType.WIRELESS_SENSOR,
            "n": "Door Sensor",
            "bl": 85,  # battery level
            "lb": False,  # low battery
            "b": ZoneBypass.UNBYPASSED,  # bypassed
            "ta": False,  # tamper
            "panid": 123,  # panel ID
        },
        {
            "_id": 2,
            "t": DeviceType.WIRELESS_SENSOR,
            "n": "Motion Sensor",
            "lb": True,  # low battery
            "b": ZoneBypass.MANUALLY_BYPASSED,  # bypassed
            "ta": True,  # tamper
            "panid": 123,  # panel ID
        },
        {
            "_id": 3,  # Panel device
            "t": DeviceType.PANEL,
            "n": "Main Panel",
            "pant": 1,  # Sky Control
            "panid": 123,  # panel ID
        }
    ]
    
    return AlarmPanel(basic_panel_data, mock_system)


def test_device_battery_level_with_explicit_level():
    """Test battery_level returns explicit battery level when available."""
    data = {"bl": 75, "lb": False}
    device = MockDevice(data)
    
    assert device.battery_level == 75


def test_device_battery_level_low_battery_true():
    """Test battery_level returns 0 when low_battery is True."""
    data = {"lb": True}
    device = MockDevice(data)
    
    assert device.battery_level == 0


def test_device_battery_level_low_battery_false():
    """Test battery_level returns 100 when low_battery is False."""
    data = {"lb": False}
    device = MockDevice(data)
    
    assert device.battery_level == 100


def test_device_battery_level_no_battery():
    """Test battery_level returns None when device has no battery info."""
    data = {}
    device = MockDevice(data)
    
    assert device.battery_level is None


def test_device_has_battery_with_level():
    """Test has_battery returns True when battery_level is present."""
    data = {"bl": 50}
    device = MockDevice(data)
    
    assert device.has_battery is True


def test_device_has_battery_with_low_battery():
    """Test has_battery returns True when low_battery is present."""
    data = {"lb": False}
    device = MockDevice(data)
    
    assert device.has_battery is True


def test_device_has_battery_false():
    """Test has_battery returns False when no battery info present."""
    data = {}
    device = MockDevice(data)
    
    assert device.has_battery is False


def test_device_low_battery_true():
    """Test low_battery returns True when device reports low battery."""
    data = {"lb": True}
    device = MockDevice(data)
    
    assert device.low_battery is True


def test_device_low_battery_false():
    """Test low_battery returns False when device battery is not low."""
    data = {"lb": False}
    device = MockDevice(data)
    
    assert device.low_battery is False


def test_device_low_battery_no_battery():
    """Test low_battery returns None when device has no battery."""
    data = {}
    device = MockDevice(data)
    
    assert device.low_battery is None


@pytest.fixture()
def mock_account():
    """Mock account for testing."""
    return SimpleNamespace()


@pytest.fixture()
def mock_system_data():
    """Mock system data for testing."""
    return SimpleNamespace()


def test_bypass_tamper_device_is_bypassed_true(mock_account, mock_system_data):
    """Test BypassTamperDevice.is_bypassed when device is bypassed."""
    device_data = {
        "_id": 789,
        "name": "Test Bypass Device",
        "type": DeviceType.WIRELESS_SENSOR,
        "b": ZoneBypass.MANUALLY_BYPASSED,  # Use correct attribute key 'b'
    }
    device = MockBypassTamperDevice(data=device_data)

    assert device.is_bypassed is True


def test_bypass_tamper_device_is_bypassed_false(mock_account, mock_system_data):
    """Test BypassTamperDevice.is_bypassed when device is not bypassed."""
    device_data = {
        "_id": 789,
        "name": "Test Bypass Device",
        "type": DeviceType.WIRELESS_SENSOR,
        "b": ZoneBypass.UNBYPASSED,  # Use correct attribute key 'b'
    }
    device = MockBypassTamperDevice(data=device_data)

    assert device.is_bypassed is False


def test_bypass_tamper_device_is_tampered_true(mock_account, mock_system_data):
    """Test BypassTamperDevice.is_tampered when device is tampered."""
    device_data = {
        "_id": 789,
        "name": "Test Tamper Device",
        "type": DeviceType.WIRELESS_SENSOR,
        "ta": 1,  # Use correct attribute key 'ta' for tamper
    }
    device = MockBypassTamperDevice(data=device_data)

    assert device.is_tampered


def test_bypass_tamper_device_is_tampered_false(mock_account, mock_system_data):
    """Test BypassTamperDevice.is_tampered when device is not tampered."""
    device_data = {
        "_id": 789,
        "name": "Test Tamper Device",
        "type": DeviceType.WIRELESS_SENSOR,
        "ta": 0,  # Use correct attribute key 'ta' for tamper
    }
    device = MockBypassTamperDevice(data=device_data)

    assert not device.is_tampered


def test_alarm_panel_update_data_override_true(panel_with_devices):
    """Test AlarmPanel.update_data with override=True replaces all data."""
    new_data = {
        "panid": 123,
        "parid": 1,
        "pmac": "FF:EE:DD:CC:BB:AA",
        "s": ArmedState.ARMED_AWAY,
        "d": [],
        "ureg": []
    }
    
    # Store original data for comparison
    original_mac = panel_with_devices.mac_address
    
    panel_with_devices.update_data(new_data, override=True)
    
    # Verify data was updated
    assert panel_with_devices.mac_address != original_mac
    assert panel_with_devices.mac_address == "FF:EE:DD:CC:BB:AA"
    assert panel_with_devices.state == ArmedState.ARMED_AWAY


def test_alarm_panel_update_data_override_false(panel_with_devices):
    """Test AlarmPanel.update_data with override=False merges data."""
    # Store original values
    original_mac = panel_with_devices.mac_address
    original_state = panel_with_devices.state
    
    new_data = {
        "pmac": "FF:EE:DD:CC:BB:AA",
        # Intentionally not including state to test partial update
    }
    
    panel_with_devices.update_data(new_data, override=False)
    
    # MAC should be updated, state should remain the same
    assert panel_with_devices.mac_address == "FF:EE:DD:CC:BB:AA"
    assert panel_with_devices.state == original_state


def test_alarm_panel_update_data_model_sync(panel_with_devices):
    """Test AlarmPanel.update_data keeps _data_model in sync."""
    new_data = {
        "panid": 123,
        "parid": 2,  # Change partition
        "pmac": "FF:EE:DD:CC:BB:AA",
        "s": ArmedState.ARMED_STAY,
        "d": [],
        "ureg": []
    }
    
    panel_with_devices.update_data(new_data, override=True)
    
    # Verify model is in sync
    assert panel_with_devices._data_model.partition_id == 2


@pytest.mark.asyncio
async def test_alarm_panel_refresh_new_device_false(panel_with_devices):
    """Test AlarmPanel.refresh with new_device=False."""
    refresh_data = {
        "panid": 123,
        "parid": 1,
        "pmac": "AA:BB:CC:DD:EE:FF",
        "s": ArmedState.ARMED_AWAY,
        "d": [
            {
                "_id": 1,
                "t": DeviceType.WIRELESS_SENSOR,
                "n": "Updated Door Sensor",
                "bl": 90,  # Updated battery level
                "panid": 123,  # Panel ID
            }
        ],
        "ureg": []
    }
    
    original_device_count = len(panel_with_devices.devices)
    original_device = panel_with_devices.devices[0]
    
    panel_with_devices.refresh(refresh_data, new_device=False)
    
    # Device count should remain the same
    assert len(panel_with_devices.devices) == original_device_count

    # Device should be updated
    updated_device = panel_with_devices.devices[0]
    assert updated_device.name == "Updated Door Sensor"
    assert updated_device.battery_level == 90


@pytest.mark.asyncio
async def test_alarm_panel_refresh_new_device_true(panel_with_devices):
    """Test AlarmPanel.refresh with new_device=True adds new devices."""
    refresh_data = {
        "panid": 123,
        "parid": 1,
        "pmac": "AA:BB:CC:DD:EE:FF",
        "s": ArmedState.DISARMED,
        "d": [
            # Existing device
            {
                "_id": 1,
                "t": DeviceType.WIRELESS_SENSOR,
                "n": "Door Sensor",
                "bl": 85,
                "panid": 123,
            },
            # New device
            {
                "_id": 4,
                "t": DeviceType.WIRED_SENSOR,  # Use valid enum
                "n": "Glass Break Sensor",
                "bl": 100,
                "panid": 123,
            }
        ],
        "ureg": []
    }
    
    original_device_count = len(panel_with_devices.devices)
    
    panel_with_devices.refresh(refresh_data, new_device=True)
    
    # Device count should increase by 1
    assert len(panel_with_devices.devices) == original_device_count + 1

    # Find the new device
    new_device = next((d for d in panel_with_devices.devices if d.id == 4), None)
    assert new_device is not None
    assert new_device.name == "Glass Break Sensor"


def test_alarm_panel_refresh_unregistered_devices(panel_with_devices):
    """Test AlarmPanel.refresh handles unregistered devices."""
    refresh_data = {
        "panid": 123,
        "parid": 1,
        "pmac": "AA:BB:CC:DD:EE:FF",
        "s": ArmedState.DISARMED,
        "d": [],
        "ureg": [
            {
                "_id": 99,
                "n": "Unregistered Device",
                "t": DeviceType.UNKNOWN,
            }
        ]
    }

    panel_with_devices.refresh(refresh_data, new_device=False)

    # Check unregistered devices were parsed
    assert 99 in panel_with_devices.unregistered_devices
    device_info = panel_with_devices.unregistered_devices[99]
    assert device_info[0] == "Unregistered Device"  # name
    assert device_info[1] == DeviceType.UNKNOWN     # type


@pytest.mark.asyncio
async def test_alarm_panel_handle_pubnub_delete_device(panel_with_devices):
    """Test AlarmPanel.handle_pubnub_message with device deletion."""
    # Ensure we have a device to delete
    assert len(panel_with_devices.devices) >= 1
    device_to_delete = panel_with_devices.devices[0]
    device_id = device_to_delete.id
    
    delete_message = {
        "op": "d",  # delete operation
        "da": {
            "d": [
                {
                    "_id": device_id,
                    "op": "d",  # delete operation
                }
            ]
        }
    }
    
    original_device_count = len(panel_with_devices.devices)
    
    # Mock the emit method to capture events
    emitted_events = []
    panel_with_devices.emit = lambda event, data: emitted_events.append((event, data))
    
    panel_with_devices.handle_pubnub_message(delete_message)
    
    # Device should be removed
    assert len(panel_with_devices.devices) == original_device_count - 1

    # Device should be in unregistered devices
    assert device_id in panel_with_devices.unregistered_devices

    # Check that an event was emitted
    assert len(emitted_events) == 1
    assert emitted_events[0][0] == "device_deleted"


@pytest.mark.asyncio
async def test_alarm_panel_handle_pubnub_ignore_unknown_device(panel_with_devices):
    """Test AlarmPanel.handle_pubnub_message ignores unknown device operations."""
    unknown_device_message = {
        "op": "u",  # update operation
        "da": {
            "d": [
                {
                    "_id": 999,  # Unknown device ID
                    "op": "u",
                    "some_property": "new_value"
                }
            ]
        }
    }
    
    original_device_count = len(panel_with_devices.devices)
    
    panel_with_devices.handle_pubnub_message(unknown_device_message)
    
    # Device count should remain the same
    assert len(panel_with_devices.devices) == original_device_count


@pytest.mark.asyncio
async def test_alarm_panel_handle_pubnub_create_device(panel_with_devices, monkeypatch):
    """Test AlarmPanel.handle_pubnub_message with device creation."""
    create_message = {
        "op": "c",  # create operation
        "da": {
            "panid": 123,
            "parid": 1,
            "pmac": "AA:BB:CC:DD:EE:FF",
            "s": ArmedState.DISARMED,
            "d": [
                # Existing devices
                {
                    "_id": 1,
                    "t": DeviceType.WIRELESS_SENSOR,
                    "n": "Door Sensor",
                    "bl": 85,
                    "panid": 123,
                },
                {
                    "_id": 2,
                    "t": DeviceType.WIRELESS_SENSOR,
                    "n": "Motion Sensor",
                    "bl": 90,
                    "panid": 123,
                },
                {
                    "_id": 3,
                    "t": DeviceType.PANEL,
                    "n": "Main Panel",
                    "panid": 123,
                },
                # New device
                {
                    "_id": 5,
                    "op": "c",  # create operation
                    "t": DeviceType.BINARY_SWITCH,
                    "n": "New Device",
                    "panid": 123,
                }
            ],
            "ureg": []
        }
    }

    original_device_count = len(panel_with_devices.devices)

    # Mock get_device_class to return a simple device
    def mock_get_device_class(device_type):
        from vivintpy.devices.switch import BinarySwitch
        return BinarySwitch

    monkeypatch.setattr("vivintpy.devices.get_device_class", mock_get_device_class)

    panel_with_devices.handle_pubnub_message(create_message)

    # Device count should increase by 1
    assert len(panel_with_devices.devices) == original_device_count + 1

    # Find the new device
    new_device = next((d for d in panel_with_devices.devices if d.id == 5), None)
    assert new_device is not None
    assert new_device.name == "New Device"
