"""Unit tests for the `WirelessSensor` device class."""

from __future__ import annotations

from typing import Any, List

import pytest

from vivintpy.const import (
    VivintDeviceAttribute as Attr,
    WirelessSensorAttribute as WsAttr,
)
from vivintpy.devices.wireless_sensor import WirelessSensor
from vivintpy.enums import DeviceType, EquipmentCode, EquipmentType, SensorType

# -----------------------------------------------------------------------------
# Stubs
# -----------------------------------------------------------------------------


class _DummyApi:  # pylint: disable=too-few-public-methods
    """Record set_sensor_state calls."""

    def __init__(self):
        self.calls: List[tuple[str, Any]] = []

    async def set_sensor_state(
        self, panel_id: int, partition_id: int, device_id: int, bypass: bool
    ) -> None:  # noqa: D401 – stub
        self.calls.append(("set_sensor_state", panel_id, partition_id, device_id, bypass))


class _DummySystem:  # pylint: disable=too-few-public-methods
    def __init__(self, api: _DummyApi):
        self.api = api


class _DummyPanel:  # pylint: disable=too-few-public-methods
    id = 1
    partition_id = 1

    def __init__(self, api: _DummyApi):
        self.system = _DummySystem(api)
        self.devices: List[Any] = []  # populated later


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _make_payload(hidden: bool = False) -> dict[str, Any]:
    return {
        Attr.ID: 601,
        Attr.PANEL_ID: 1,
        Attr.TYPE: DeviceType.WIRELESS_SENSOR.value,
        Attr.STATE: 1,
        Attr.SERIAL_NUMBER: "ABC123",
        WsAttr.EQUIPMENT_CODE: EquipmentCode.SMKE1_SMOKE.value,
        WsAttr.EQUIPMENT_TYPE: EquipmentType.CONTACT.value,
        WsAttr.SENSOR_TYPE: SensorType.AUDIBLE_ALARM.value,
        WsAttr.SENSOR_FIRMWARE_VERSION: "1.0.0",
        WsAttr.HIDDEN: hidden,
    }


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture()
def sensor_and_api():
    api = _DummyApi()
    panel = _DummyPanel(api)
    sensor = WirelessSensor(_make_payload(), alarm_panel=panel)
    panel.devices.append(sensor)  # ensure back-reference list exists
    return sensor, api


# -----------------------------------------------------------------------------
# Tests – properties & validity
# -----------------------------------------------------------------------------


def test_sensor_properties(sensor_and_api):
    sensor, _ = sensor_and_api

    assert sensor.model == EquipmentCode.SMKE1_SMOKE.name
    assert sensor.software_version == "1.0.0"
    assert sensor.equipment_code == EquipmentCode.SMKE1_SMOKE
    assert sensor.equipment_type == EquipmentType.CONTACT
    assert sensor.sensor_type == SensorType.AUDIBLE_ALARM
    assert sensor.is_on is True
    assert sensor.is_valid is True

    # After marking UNUSED, validity should flip --------------------------------
    sensor.update_data({WsAttr.SENSOR_TYPE: SensorType.UNUSED.value})
    assert sensor.is_valid is False


# -----------------------------------------------------------------------------
# Tests – async helpers
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bypass_helpers(sensor_and_api):
    sensor, api = sensor_and_api

    await sensor.bypass()
    await sensor.unbypass()

    # Expect two calls ---------------------------------------------------------
    assert len(api.calls) == 2
    (method1, panid, parid, dev_id, bypass1) = api.calls[0]
    (method2, _, _, _, bypass2) = api.calls[1]

    assert method1 == method2 == "set_sensor_state"
    assert (panid, parid, dev_id) == (1, 1, sensor.id)
    assert bypass1 is True and bypass2 is False
