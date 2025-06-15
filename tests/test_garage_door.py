"""Unit tests for the `GarageDoor` device class."""

from __future__ import annotations

from typing import Any, List

import pytest

from vivintpy.const import VivintDeviceAttribute as Attr
from vivintpy.devices.garage_door import GarageDoor
from vivintpy.enums import DeviceType, GarageDoorState

# -----------------------------------------------------------------------------
# Stubs
# -----------------------------------------------------------------------------


class _DummyApi:  # pylint: disable=too-few-public-methods
    """A minimal stub that records method calls."""

    def __init__(self):  # noqa: D401 – simple stub
        self.calls: List[tuple[str, Any]] = []

    async def set_garage_door_state(
        self, panel_id: int, partition_id: int, device_id: int, state: int
    ) -> None:  # noqa: D401 – stub
        self.calls.append(
            ("set_garage_door_state", panel_id, partition_id, device_id, state)
        )


class _DummySystem:  # pylint: disable=too-few-public-methods
    """Bare-minimum replacement exposing `api`."""

    def __init__(self, api: _DummyApi):
        self.api = api


class _DummyPanel:  # pylint: disable=too-few-public-methods
    """Very small stand-in for an `AlarmPanel` instance."""

    id = 1
    partition_id = 1

    def __init__(self, api: _DummyApi):
        self.system = _DummySystem(api)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _make_payload(state: GarageDoorState = GarageDoorState.CLOSED) -> dict[str, Any]:
    """Return a minimal but valid garage-door payload."""

    return {
        Attr.ID: 301,
        Attr.PANEL_ID: 1,
        Attr.TYPE: DeviceType.GARAGE_DOOR.value,
        Attr.STATE: state.value,
        Attr.ONLINE: True,
    }


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture()
def door_and_api():
    api = _DummyApi()
    panel = _DummyPanel(api)
    door = GarageDoor(_make_payload(), alarm_panel=panel)
    return door, api


# -----------------------------------------------------------------------------
# Tests – properties
# -----------------------------------------------------------------------------


def test_basic_state_properties(door_and_api):
    door, _ = door_and_api

    assert door.is_closed is True
    assert door.is_closing is False
    assert door.is_opening is False
    assert door.is_online is True

    # Unknown state should result in None for `is_closed`
    door.update_data({Attr.STATE: GarageDoorState.UNKNOWN.value})
    assert door.is_closed is None


# -----------------------------------------------------------------------------
# Tests – async helpers
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_state_helpers(door_and_api):
    door, api = door_and_api

    await door.open()
    await door.close()

    # Verify API interactions --------------------------------------------------
    calls = api.calls
    assert calls[0] == ("set_garage_door_state", 1, 1, door.id, GarageDoorState.OPENING)
    assert calls[1] == ("set_garage_door_state", 1, 1, door.id, GarageDoorState.CLOSING)
    assert len(calls) == 2
