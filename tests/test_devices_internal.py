"""Unit tests for internal logic in vivintpy.devices package focusing on
VivintDevice property helpers and the ``get_device_class`` factory.

These tests exercise branches that are not touched by the public integration
suite but are important for maintaining backwards-compatibility and accurate
entity metadata.
"""

from __future__ import annotations

import types
from typing import Any

import pytest

from vivintpy.const import VivintDeviceAttribute as Attr
from vivintpy.devices import UnknownDevice, get_device_class
from vivintpy.enums import DeviceType


@pytest.mark.parametrize(
    "device_type,expected_cls_path",
    [
        (DeviceType.CAMERA.value, "vivintpy.devices.camera.Camera"),
        (DeviceType.DOOR_LOCK.value, "vivintpy.devices.door_lock.DoorLock"),
        ("nonexistent", "vivintpy.devices.UnknownDevice"),
    ],
)
def test_get_device_class_mapping(device_type: str, expected_cls_path: str) -> None:
    """Verify that ``get_device_class`` returns the correct class.

    This covers both the happy-path mapping for known types and the fallback
    to :class:`~vivintpy.devices.UnknownDevice` when an unmapped type is
    encountered.
    """
    cls = get_device_class(device_type)
    assert f"{cls.__module__}.{cls.__qualname__}" == expected_cls_path


@pytest.mark.parametrize(
    "battery_level,low_battery,expected_has_battery,expected_low_battery,expected_battery_level",
    [
        # battery_level, low_battery, has_battery?, low_batt flag, expected battery_level property
        (None, None, False, None, None),
        (42, None, True, False, 42),
        (None, True, True, True, 0),
    ],
)
def test_battery_level_and_low_battery_flags(
    battery_level: int | None,
    low_battery: bool | None,
    expected_has_battery: bool,
    expected_low_battery: bool | None,
    expected_battery_level: int | None,
) -> None:
    """Validate battery helper properties on :class:`VivintDevice`."""

    data: dict[str, Any] = {
        Attr.ID: 1,
        Attr.PANEL_ID: 1,
        Attr.TYPE: DeviceType.CAMERA.value,
    }
    if battery_level is not None:
        data[Attr.BATTERY_LEVEL] = battery_level
    if low_battery is not None:
        data[Attr.LOW_BATTERY] = low_battery

    device = UnknownDevice(data)  # UnknownDevice derives from VivintDevice

    assert device.has_battery is expected_has_battery
    assert device.battery_level == expected_battery_level
    assert device.low_battery == expected_low_battery


def test_serial_number_fallback() -> None:
    """Ensure ``serial_number`` property falls back to 16-bit key when 32-bit is missing."""
    data = {
        Attr.ID: 2,
        Attr.PANEL_ID: 99,
        Attr.TYPE: DeviceType.CAMERA.value,
        Attr.SERIAL_NUMBER: "SN16BIT",
    }
    device = UnknownDevice(data)
    assert device.serial_number == "SN16BIT"


def test_zwave_details_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify manufacturer/model are populated via Z-Wave DB helper.

    We monkey-patch the ``get_zwave_device_info`` helper so the test does not
    rely on the real DB file and remains fast/isolated.
    """

    # Late import so we can access the already-imported module object
    import vivintpy.devices as devices_module

    def fake_get_info(manid: int, prtid: int, prid: int) -> dict[str, str]:
        # Record that our stub was called with the expected identifiers
        fake_get_info.called_with = (manid, prtid, prid)  # type: ignore[attr-defined]
        return {
            "manufacturer": "Acme",
            "label": "ZSwitch",
            "description": "ACME Switch",
        }

    monkeypatch.setattr(devices_module, "get_zwave_device_info", fake_get_info, raising=True)

    data = {
        Attr.ID: 3,
        Attr.PANEL_ID: 3,
        Attr.TYPE: DeviceType.BINARY_SWITCH.value,
        "zpd": {"zwave": True},  # non-empty to trigger lookup
        "manid": 1,
        "prtid": 2,
        "prid": 3,
    }

    device = UnknownDevice(data)

    # Access properties to trigger lazy lookup
    assert device.manufacturer == "Acme"
    assert device.model == "ACME Switch (ZSwitch)"

    # Ensure our stub was invoked exactly once with the identifiers
    assert hasattr(fake_get_info, "called_with")
    assert fake_get_info.called_with == (1, 2, 3)
