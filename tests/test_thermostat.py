"""Unit tests for the `Thermostat` device class."""

from __future__ import annotations

from typing import Any, List

import pytest

from vivintpy.const import VivintDeviceAttribute as Attr, ThermostatAttribute as ThAttr
from vivintpy.devices.thermostat import Thermostat
from vivintpy.enums import (
    DeviceType,
    FanMode,
    HoldMode,
    OperatingMode,
    OperatingState,
)

# -----------------------------------------------------------------------------
# Stubs
# -----------------------------------------------------------------------------


class _DummyApi:  # pylint: disable=too-few-public-methods
    """Tiny stub that records `set_thermostat_state` calls."""

    def __init__(self):  # noqa: D401 – simple stub
        self.calls: List[tuple[str, Any]] = []

    async def set_thermostat_state(
        self, panel_id: int, partition_id: int, device_id: int, **kwargs: Any
    ) -> None:  # noqa: D401 – stub
        self.calls.append(("set_thermostat_state", panel_id, partition_id, device_id, kwargs))


class _DummySystem:  # pylint: disable=too-few-public-methods
    def __init__(self, api: _DummyApi):
        self.api = api


class _DummyPanel:  # pylint: disable=too-few-public-methods
    id = 1
    partition_id = 1

    def __init__(self, api: _DummyApi):
        self.system = _DummySystem(api)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _make_payload() -> dict[str, Any]:
    """Return a minimal but valid thermostat payload."""

    return {
        Attr.ID: 501,
        Attr.PANEL_ID: 1,
        Attr.TYPE: DeviceType.THERMOSTAT.value,
        ThAttr.CURRENT_TEMPERATURE: 70,
        ThAttr.COOL_SET_POINT: 76,
        ThAttr.HEAT_SET_POINT: 68,
        ThAttr.FAN_MODE: FanMode.ON_LOW.value,
        ThAttr.FAN_STATE: 1,  # fan on
        ThAttr.HOLD_MODE: HoldMode.PERMANENT.value,
        ThAttr.OPERATING_MODE: OperatingMode.COOL.value,
        ThAttr.OPERATING_STATE: OperatingState.COOLING.value,
        ThAttr.HUMIDITY: 45,
        ThAttr.MAXIMUM_TEMPERATURE: 90,
        ThAttr.MINIMUM_TEMPERATURE: 50,
        ThAttr.ACTUAL_TYPE: DeviceType.POD_NEST_THERMOSTAT.value,
    }


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture()
def thermostat_and_api():
    api = _DummyApi()
    panel = _DummyPanel(api)
    payload = _make_payload()
    thermostat = Thermostat(payload, alarm_panel=panel)
    return thermostat, api


# -----------------------------------------------------------------------------
# Tests – properties & helpers
# -----------------------------------------------------------------------------


def test_thermostat_properties(thermostat_and_api):
    tstat, _ = thermostat_and_api

    assert tstat.temperature == 70
    assert tstat.cool_set_point == 76
    assert tstat.heat_set_point == 68
    assert tstat.humidity == 45
    assert tstat.maximum_temperature == 90
    assert tstat.minimum_temperature == 50

    assert tstat.fan_mode == FanMode.ON_LOW
    assert tstat.hold_mode == HoldMode.PERMANENT
    assert tstat.operating_mode == OperatingMode.COOL
    assert tstat.operating_state == OperatingState.COOLING

    assert tstat.is_fan_on is True
    assert tstat.is_on is True

    # Manufacturer/model derivation for nest type
    assert tstat.manufacturer == "Google"
    assert tstat.model == "Nest"

    # Static helper ----------------------------------------------------------------
    assert Thermostat.celsius_to_fahrenheit(0) == 32
    assert Thermostat.celsius_to_fahrenheit(37) == 99  # approx 98.6 becomes 99 after rounding


# -----------------------------------------------------------------------------
# Tests – async setter
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_state_helper(thermostat_and_api):
    tstat, api = thermostat_and_api

    await tstat.set_state(cool_set_point=72, fan_mode=FanMode.AUTO_LOW.value)

    assert api.calls and api.calls[0][0] == "set_thermostat_state"
    method, panid, parid, dev_id, kwargs = api.calls[0]

    assert (panid, parid, dev_id) == (1, 1, tstat.id)
    assert kwargs == {"cool_set_point": 72, "fan_mode": FanMode.AUTO_LOW.value}
