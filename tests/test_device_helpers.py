"""Unit tests for generic device helper properties in vivintpy.devices.

Covers:
* VivintDevice.battery_level / low_battery fall-backs
* VivintDevice.has_battery flag
* BypassTamperDevice.is_bypassed & .is_tampered helpers
"""

from __future__ import annotations

import pytest

from vivintpy.const import VivintDeviceAttribute as Attr
from vivintpy.devices import BypassTamperDevice, VivintDevice
from vivintpy.enums import ZoneBypass

# ---------------------------------------------------------------------------
# Helper: fabricate minimal raw payloads (dict) for a generic device.
# We intentionally avoid hitting the network or AlarmPanel logic.
# ---------------------------------------------------------------------------

def _make_device(raw: dict) -> VivintDevice:
    """Create a generic :class:`VivintDevice` instance with *raw* data."""

    # Every device needs at least an ID; use 1 by default.
    payload = {Attr.ID: 1, **raw}
    return VivintDevice(payload)  # type: ignore[arg-type]


def _make_bypass_device(raw: dict) -> BypassTamperDevice:
    """Create a :class:`BypassTamperDevice` with *raw* data."""

    payload = {Attr.ID: 2, **raw}
    return BypassTamperDevice(payload)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# battery_level / low_battery / has_battery
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    (
        "battery_level_field",
        "low_battery_field",
        "expected_level",
        "expected_low",
        "expected_has",
    ),
    [
        # Explicit battery value takes precedence.
        (80, False, 80, False, True),
        # Empty string => fall-back to 100 when not low battery.
        ("", False, 100, False, True),
        # Missing battery value & low_battery flag => 0 level.
        (None, True, 0, True, True),
        # No battery related fields at all => None / None / False.
        (None, None, None, None, False),
    ],
)
def test_battery_helpers(battery_level_field, low_battery_field, expected_level, expected_low, expected_has):
    raw: dict = {}
    if battery_level_field is not None:
        raw[Attr.BATTERY_LEVEL] = battery_level_field
    if low_battery_field is not None:
        raw[Attr.LOW_BATTERY] = low_battery_field

    dev = _make_device(raw)

    assert dev.has_battery is expected_has
    assert dev.battery_level == expected_level
    assert dev.low_battery == expected_low


# ---------------------------------------------------------------------------
# Bypass / Tamper helpers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bypass_value, expected",
    [
        (ZoneBypass.FORCE_BYPASSED, True),
        (ZoneBypass.UNBYPASSED, False),
        (None, False),  # default value
    ],
)
def test_is_bypassed(bypass_value, expected):
    raw: dict = {}
    if bypass_value is not None:
        raw[Attr.BYPASSED] = int(bypass_value)

    dev = _make_bypass_device(raw)
    assert dev.is_bypassed is expected


@pytest.mark.parametrize("tamper_value", [True, False])
def test_is_tampered(tamper_value):
    raw = {Attr.TAMPER: tamper_value}
    dev = _make_bypass_device(raw)
    assert dev.is_tampered is tamper_value
