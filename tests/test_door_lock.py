"""Unit tests for the `DoorLock` device class."""

from __future__ import annotations

from typing import Any

import pytest

from vivintpy.devices.door_lock import DoorLock
from vivintpy.enums import DeviceType


class _DummyApi:  # pylint: disable=too-few-public-methods
    """Very small stub that records calls to `set_lock_state`."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def set_lock_state(
        self, panel_id: int, partition_id: int, device_id: int, locked: bool
    ) -> None:  # noqa: D401 – simple stub
        self.calls.append(("set_lock_state", panel_id, partition_id, device_id, locked))


def _make_panel(api: _DummyApi):  # noqa: D401 – helper
    """Return a minimal stub of an AlarmPanel instance wired to *api*."""

    class _DummySystem:  # pylint: disable=too-few-public-methods
        def __init__(self, _api):
            self.api = _api

    class _DummyPanel:  # pylint: disable=too-few-public-methods
        id = 1
        partition_id = 1

        def __init__(self, _api):
            self.system = _DummySystem(_api)

    return _DummyPanel(api)


@pytest.mark.asyncio
async def test_door_lock_properties_and_actions():
    """Exercise `DoorLock` properties plus `lock`/`unlock` helpers."""

    api = _DummyApi()
    panel = _make_panel(api)

    raw = {
        "_id": 101,
        "panid": 1,
        "t": DeviceType.DOOR_LOCK.value,
        "ol": True,  # online
        "s": 1,  # locked
        "ucl": [1234, 5678],  # user codes
    }

    lock = DoorLock(raw, alarm_panel=panel)

    # --- basic typed helpers --------------------------------------------------
    assert lock.is_locked is True
    assert lock.is_online is True
    assert lock.user_code_list == [1234, 5678]

    # --- async helpers (ensure they proxy to the API) -------------------------
    await lock.unlock()
    await lock.lock()

    # Two calls should have been recorded: False then True
    assert (
        "set_lock_state",
        1,
        1,
        101,
        False,
    ) in api.calls
    assert (
        "set_lock_state",
        1,
        1,
        101,
        True,
    ) in api.calls
