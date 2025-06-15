"""Unit tests for System.handle_pubnub_message routing logic.

Scenarios covered:
1. `account_system` update path – verifies user-update delegation and raw data update.
2. `account_partition` without `parid` – ignored.
3. `account_partition` missing data payload – ignored.
4. Successful dispatch to an `AlarmPanel` stub when both `parid` and `da` present.
"""

from __future__ import annotations

import types
from typing import Any

import pytest

from vivintpy.const import PubNubMessageAttribute as MsgAttr
from vivintpy.const import SystemAttribute as SysAttr
from vivintpy.models import SystemData
from vivintpy.system import System


class _StubApi:  # minimal stand-in so System.refresh is never called
    pass


@pytest.fixture()
def minimal_system() -> System:
    """Return a System instance with bare-minimum typed data."""

    raw: dict[str, Any] = {
        "system": {
            "panid": 123,
            "par": [],  # no partitions so we can inject our own later
            "u": [],
        }
    }
    model = SystemData.model_validate(raw)
    # name/is_admin don't matter for routing
    return System(model, _StubApi(), name="Home", is_admin=True)


def test_account_system_update(monkeypatch, minimal_system):
    """Ensure *account_system* updates users via update_user_data and raw data."""

    called: dict[str, Any] = {}

    def _mock_update(self: System, users: list[dict]):  # noqa: D401 – helper
        called["users"] = users

    monkeypatch.setattr(System, "update_user_data", _mock_update, raising=True)

    msg_users = [{"_id": 1, "n": "Bob"}]
    msg = {
        MsgAttr.TYPE: "account_system",
        MsgAttr.OPERATION: "u",
        MsgAttr.DATA: {
            SysAttr.ADMIN: True,
            SysAttr.USERS: msg_users,
        },
    }

    minimal_system.handle_pubnub_message(msg)

    # delegated correctly
    assert called["users"] == msg_users
    # raw data update path preserved (admin flag ends up in System.data)
    assert minimal_system.data[SysAttr.ADMIN] is True


def test_account_partition_no_partition_id(minimal_system, caplog):
    """Missing *parid* yields early exit with no changes."""

    msg = {MsgAttr.TYPE: "account_partition"}
    minimal_system.handle_pubnub_message(msg)

    # Nothing should have changed (still default raw data)
    assert SysAttr.PARTITION not in minimal_system.data


def test_account_partition_no_data(minimal_system):
    """Heartbeat message without *da* is ignored."""

    msg = {MsgAttr.TYPE: "account_partition", MsgAttr.PARTITION_ID: 1}
    minimal_system.handle_pubnub_message(msg)
    assert SysAttr.PARTITION not in minimal_system.data


def test_account_partition_dispatch(monkeypatch, minimal_system):
    """Valid partition message is dispatched to matching AlarmPanel."""

    class _StubPanel:
        def __init__(self):
            self.id = 123  # same as system panid
            self.partition_id = 1
            self.seen: list[dict] = []

        def handle_pubnub_message(self, message: dict) -> None:  # noqa: D401 – stub
            self.seen.append(message)

    panel = _StubPanel()
    minimal_system.alarm_panels.append(panel)  # type: ignore[arg-type]

    msg = {
        MsgAttr.TYPE: "account_partition",
        MsgAttr.PARTITION_ID: 1,
        MsgAttr.DATA: {"foo": "bar"},
    }

    minimal_system.handle_pubnub_message(msg)

    assert panel.seen == [msg]
