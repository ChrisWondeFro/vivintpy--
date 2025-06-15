"""Unit tests for the AlarmPanel device class.
These tests exercise the public API as well as internal PubNub-routing logic so that the
module achieves near-full statement coverage.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from vivintpy.const import (
    AlarmPanelAttribute as Attr,
    PubNubMessageAttribute as MsgAttr,
    PubNubOperatorAttribute as OpAttr,
    SystemAttribute as SysAttr,
)
from vivintpy.enums import ArmedState, DeviceType
from vivintpy.models import SystemData
from vivintpy.system import System


class DummyApi:
    """A very small stub of the real `VivintSkyApi` used by `AlarmPanel`."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        # populated later in tests so that `get_system_data` can return it
        self._system_model: SystemData | None = None

    # --- Alarm / Panel actions -------------------------------------------------
    async def set_alarm_state(self, panel_id: int, partition_id: int, state: int) -> None:  # noqa: D401 – stub
        self.calls.append(("set_alarm_state", panel_id, partition_id, state))

    async def trigger_alarm(self, panel_id: int, partition_id: int) -> None:  # noqa: D401 – stub
        self.calls.append(("trigger_alarm", panel_id, partition_id))

    # --- System helpers -------------------------------------------------------
    async def get_system_data(self, panel_id: int):  # noqa: D401 – stub
        assert self._system_model, "system model not initialised"
        return self._system_model

    async def get_device_data(self, panel_id: int, device_id: int):  # noqa: D401 – stub
        # Return an *empty* SystemData payload – AlarmPanel only needs the wrapper.
        raw: dict[str, Any] = {
            "system": {
                "panid": panel_id,
                "fea": {},
                "sinfo": {},
                "par": [
                    {
                        "panid": panel_id,
                        "parid": 1,
                        Attr.DEVICES: [],
                        Attr.UNREGISTERED: [],
                    }
                ],
                "u": [],
            }
        }
        return SystemData.model_validate(raw)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture()
def system_and_panel():
    """Return a `(System, AlarmPanel)` tuple wired to a `DummyApi`."""

    # Minimal raw payload representing a System with a single panel/partition
    raw: dict[str, Any] = {
        "system": {
            "panid": 1,
            "fea": {},
            "sinfo": {},
            "par": [
                {
                    "panid": 1,
                    "parid": 1,
                    # state 0 ⇒ disarmed
                    "s": ArmedState.DISARMED,
                    Attr.DEVICES: [],
                    Attr.UNREGISTERED: [],
                }
            ],
            "u": [],
        }
    }

    model = SystemData.model_validate(raw)
    dummy_api = DummyApi()
    dummy_api._system_model = model  # type: ignore[attr-defined] – test wiring

    system = System(data=model, api=dummy_api, name="Test System", is_admin=True)
    panel = system.alarm_panels[0]
    return system, panel, dummy_api


# -----------------------------------------------------------------------------
# Tests – basic panel properties & helpers
# -----------------------------------------------------------------------------


def test_basic_properties(system_and_panel):
    _, panel, _ = system_and_panel
    assert panel.id == 1
    assert panel.partition_id == 1
    assert panel.is_disarmed
    assert panel.state == ArmedState.DISARMED
    # With no physical panel device discovered the model falls back to Smart Hub
    assert panel.model == "Smart Hub"


@pytest.mark.asyncio
async def test_arming_helpers(system_and_panel):
    _, panel, api = system_and_panel

    await panel.disarm()
    await panel.arm_stay()
    await panel.arm_away()
    await panel.trigger_alarm()

    # 4 calls should have been recorded: 3 × set_alarm_state and 1 × trigger_alarm
    set_calls = [c for c in api.calls if c[0] == "set_alarm_state"]
    trig_calls = [c for c in api.calls if c[0] == "trigger_alarm"]

    assert len(set_calls) == 3
    assert len(trig_calls) == 1


def _make_device(dev_id: int) -> dict[str, Any]:
    """Return a minimal device payload for tests."""

    return {
        "_id": dev_id,
        "panid": 1,
        "t": DeviceType.CAMERA.value,
    }


def test_refresh_adds_new_device(system_and_panel):
    _, panel, _ = system_and_panel

    dev = _make_device(99)
    panel.refresh({Attr.DEVICES: [dev]}, new_device=True)

    assert len(panel.devices) == 1
    assert panel.devices[0].id == 99


def test_pubnub_delete_removes_device(system_and_panel):
    _, panel, _ = system_and_panel

    # First, add the device
    dev = _make_device(42)
    panel.refresh({Attr.DEVICES: [dev]}, new_device=True)
    assert any(d.id == 42 for d in panel.devices)

    # Now craft a PubNub delete message for that device
    message = {
        MsgAttr.TYPE: "account_partition",
        MsgAttr.OPERATION: OpAttr.DELETE,
        MsgAttr.PANEL_ID: 1,
        MsgAttr.PARTITION_ID: 1,
        MsgAttr.DATA: {MsgAttr.DEVICES: [{"_id": 42}]},
    }

    panel.handle_pubnub_message(message)

    # Device should be gone and moved to `unregistered_devices`
    assert all(d.id != 42 for d in panel.devices)
    assert 42 in panel.unregistered_devices
