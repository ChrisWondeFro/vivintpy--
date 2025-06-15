"""Tests for `vivintpy.devices.__init__` helpers and generic `VivintDevice` logic.

These aim to lift coverage for the shared device layer by exercising:

1. `get_device_class` – verify mapping for known types & fallback.
2. `VivintDevice` battery helpers (`battery_level`, `low_battery`, `has_battery`).
3. Z-Wave details lookup path that sets `manufacturer` & `model`.
4. `BypassTamperDevice` convenience flags (`is_bypassed`, `is_tampered`).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Type

import pytest

import vivintpy.devices as dev_mod
from vivintpy.const import VivintDeviceAttribute as Attr
from vivintpy.enums import DeviceType, ZoneBypass


# -----------------------------------------------------------------------------
# 1. get_device_class mapping --------------------------------------------------
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "device_type, expected_cls_name",
    [
        (DeviceType.BINARY_SWITCH.value, "BinarySwitch"),
        (DeviceType.CAMERA.value, "Camera"),
        (DeviceType.DOOR_LOCK.value, "DoorLock"),
        ("unknown_type", "UnknownDevice"),
    ],
)
def test_get_device_class_mapping(device_type: str, expected_cls_name: str):
    cls: Type[dev_mod.VivintDevice] = dev_mod.get_device_class(device_type)
    assert cls.__name__ == expected_cls_name


# -----------------------------------------------------------------------------
# Helpers to create minimal raw device dicts -----------------------------------
# -----------------------------------------------------------------------------

def _make_raw_device(**extra) -> dict[str, Any]:
    base: dict[str, Any] = {
        Attr.ID: 1,
        Attr.TYPE: DeviceType.CAMERA.value,
        Attr.PANEL_ID: 42,
    }
    base.update(extra)
    return base


# -----------------------------------------------------------------------------
# 2. Battery helpers -----------------------------------------------------------
# -----------------------------------------------------------------------------

def test_battery_level_helpers():
    raw = _make_raw_device(**{Attr.BATTERY_LEVEL: 55, Attr.LOW_BATTERY: False})
    dev = dev_mod.VivintDevice(raw)

    assert dev.has_battery is True
    assert dev.battery_level == 55
    assert dev.low_battery is False

    # No battery fields ⇒ helpers yield None/False appropriately
    dev2 = dev_mod.VivintDevice(_make_raw_device())
    assert dev2.has_battery is False
    assert dev2.battery_level is None
    assert dev2.low_battery is None


# -----------------------------------------------------------------------------
# 3. Z-Wave details – manufacturer & model route -------------------------------
# -----------------------------------------------------------------------------

def test_zwave_details(monkeypatch):
    # Patch the db lookup to return custom label/description
    def _fake_lookup(_man, _prt, _pid):
        return {
            "manufacturer": "ACME",
            "label": "ModelX",
            "description": "Super Sensor",
        }

    monkeypatch.setattr(dev_mod, "get_zwave_device_info", _fake_lookup, raising=True)

    raw = _make_raw_device(zpd=True, manid=1, prtid=2, prid=3)
    dev = dev_mod.VivintDevice(raw)

    # Access manufacturer/model properties which trigger the lookup
    assert dev.manufacturer == "ACME"
    assert dev.model == "Super Sensor (ModelX)"


# -----------------------------------------------------------------------------
# 4. Bypass/Tamper helpers -----------------------------------------------------
# -----------------------------------------------------------------------------

def test_bypass_tamper_flags():
    raw = _make_raw_device(**{
        Attr.BYPASSED: ZoneBypass.MANUALLY_BYPASSED,
        Attr.TAMPER: True,
    })
    bdev = dev_mod.BypassTamperDevice(raw)

    assert bdev.is_bypassed is True
    assert bdev.is_tampered is True
