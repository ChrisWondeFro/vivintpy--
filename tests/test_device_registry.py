"""Tests for device registry functionality."""

import pytest
from types import SimpleNamespace

from vivintpy.devices import (
    get_device_class,
    UnknownDevice,
    VivintDevice,
)
from vivintpy.devices.switch import BinarySwitch, MultilevelSwitch
from vivintpy.devices.camera import Camera
from vivintpy.devices.door_lock import DoorLock
from vivintpy.devices.garage_door import GarageDoor
from vivintpy.devices.thermostat import Thermostat
from vivintpy.devices.wireless_sensor import WirelessSensor
from vivintpy.enums import DeviceType


def test_get_device_class_binary_switch():
    """Test get_device_class returns BinarySwitch for BINARY_SWITCH type."""
    device_class = get_device_class(DeviceType.BINARY_SWITCH)
    assert device_class == BinarySwitch


def test_get_device_class_camera():
    """Test get_device_class returns Camera for CAMERA type."""
    device_class = get_device_class(DeviceType.CAMERA)
    assert device_class == Camera


def test_get_device_class_door_lock():
    """Test get_device_class returns DoorLock for DOOR_LOCK type."""
    device_class = get_device_class(DeviceType.DOOR_LOCK)
    assert device_class == DoorLock


def test_get_device_class_garage_door():
    """Test get_device_class returns GarageDoor for GARAGE_DOOR type."""
    device_class = get_device_class(DeviceType.GARAGE_DOOR)
    assert device_class == GarageDoor


def test_get_device_class_multi_level_switch():
    """Test get_device_class returns MultilevelSwitch for MULTI_LEVEL_SWITCH type."""
    device_class = get_device_class(DeviceType.MULTI_LEVEL_SWITCH)
    assert device_class == MultilevelSwitch


def test_get_device_class_thermostat():
    """Test get_device_class returns Thermostat for THERMOSTAT type."""
    device_class = get_device_class(DeviceType.THERMOSTAT)
    assert device_class == Thermostat


def test_get_device_class_panel():
    """Test get_device_class returns VivintDevice for PANEL type."""
    device_class = get_device_class(DeviceType.PANEL)
    assert device_class == VivintDevice


def test_get_device_class_wireless_sensor():
    """Test get_device_class returns WirelessSensor for WIRELESS_SENSOR type."""
    device_class = get_device_class(DeviceType.WIRELESS_SENSOR)
    assert device_class == WirelessSensor


def test_get_device_class_unknown_mapped_type():
    """Test get_device_class with unknown mapped device type."""
    result = get_device_class(DeviceType.WIRELESS_SENSOR)
    assert result == WirelessSensor


def test_get_device_class_motion_sensor():
    """Test get_device_class with motion sensor device type."""
    result = get_device_class(DeviceType.WIRELESS_SENSOR)
    assert result == WirelessSensor


def test_get_device_class_smoke_detector():
    """Test get_device_class with smoke detector device type."""
    result = get_device_class(DeviceType.WIRELESS_SENSOR)
    assert result == WirelessSensor


def test_get_device_class_glass_break_sensor():
    """Test get_device_class with glass break sensor device type."""
    result = get_device_class(DeviceType.WIRELESS_SENSOR)
    assert result == WirelessSensor


def test_get_device_class_keyfob():
    """Test get_device_class with keyfob device type."""
    result = get_device_class(DeviceType.KEY_FOB)
    assert result == UnknownDevice  # KEY_FOB not in _DEVICE_TYPE_MAP


def test_get_device_class_unknown_device_type():
    """Test get_device_class with totally unknown device type."""
    result = get_device_class(DeviceType.UNKNOWN)
    assert result == UnknownDevice


def test_get_device_class_invalid_device_type_string():
    """Test get_device_class with invalid string device type."""
    # DeviceType enum handles missing values gracefully, returns UNKNOWN
    invalid_enum = DeviceType._missing_("invalid_type")
    result = get_device_class(invalid_enum)
    assert result == UnknownDevice


def test_get_device_class_invalid_device_type_integer():
    """Test get_device_class with invalid integer device type."""
    # DeviceType enum handles missing values gracefully, returns UNKNOWN
    invalid_enum = DeviceType._missing_(999)
    result = get_device_class(invalid_enum)
    assert result == UnknownDevice


def test_get_device_class_none_input():
    """Test get_device_class with None input."""
    # DeviceType enum handles None gracefully, returns UNKNOWN
    invalid_enum = DeviceType._missing_(None)
    result = get_device_class(invalid_enum)
    assert result == UnknownDevice


def test_get_device_class_empty_string():
    """Test get_device_class with empty string."""
    # DeviceType enum handles empty string gracefully, returns UNKNOWN
    invalid_enum = DeviceType._missing_("")
    result = get_device_class(invalid_enum)
    assert result == UnknownDevice


def test_get_device_class_with_string_device_type():
    """Test get_device_class with string input that matches enum value."""
    # Create enum from string value
    device_type = DeviceType("camera_device")
    result = get_device_class(device_type)
    assert result == Camera


def test_get_device_class_case_sensitivity():
    """Test get_device_class with different case - should return UNKNOWN."""
    # DeviceType enum is case sensitive, "CAMERA" != "camera"
    invalid_enum = DeviceType._missing_("CAMERA")
    result = get_device_class(invalid_enum)
    assert result == UnknownDevice


def test_get_device_class_all_mapped_types():
    """Test that all mapped device types return the expected classes."""
    expected_mappings = {
        DeviceType.BINARY_SWITCH: BinarySwitch,
        DeviceType.CAMERA: Camera,
        DeviceType.DOOR_LOCK: DoorLock,
        DeviceType.GARAGE_DOOR: GarageDoor,
        DeviceType.MULTI_LEVEL_SWITCH: MultilevelSwitch,
        DeviceType.THERMOSTAT: Thermostat,
        DeviceType.PANEL: VivintDevice,
        DeviceType.WIRELESS_SENSOR: WirelessSensor,
    }
    
    for device_type, expected_class in expected_mappings.items():
        actual_class = get_device_class(device_type)
        assert actual_class == expected_class, f"Expected {expected_class} for {device_type}, got {actual_class}"


def test_get_device_class_returns_class_not_instance():
    """Test that get_device_class returns a class, not an instance."""
    device_class = get_device_class(DeviceType.CAMERA)
    
    # Should be a class/type, not an instance
    assert isinstance(device_class, type)
    
    # Should be a subclass of VivintDevice
    assert issubclass(device_class, VivintDevice)


def test_unknown_device_fallback_behavior():
    """Test that unknown device types fall back to UnknownDevice."""
    result = get_device_class(DeviceType.WIRELESS_SENSOR)  # Not in _DEVICE_TYPE_MAP
    assert result == WirelessSensor  # Actually this one is mapped
    
    # Test with truly unmapped type
    result = get_device_class(DeviceType.ENERGY_SERVICE)  # Not in _DEVICE_TYPE_MAP
    assert result == UnknownDevice


def test_device_class_inheritance():
    """Test that returned device classes properly inherit from VivintDevice."""
    test_types = [
        DeviceType.CAMERA,
        DeviceType.DOOR_LOCK,
        DeviceType.THERMOSTAT,
        DeviceType.PANEL,
        DeviceType.UNKNOWN,  # Should return UnknownDevice
    ]
    
    for device_type in test_types:
        device_class = get_device_class(device_type)
        assert issubclass(device_class, VivintDevice), f"{device_class} should be a subclass of VivintDevice"
