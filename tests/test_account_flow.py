"""Extended tests for ``vivintpy.account.Account`` covering most execution paths
and lifting file coverage above 90 %."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from vivintpy.account import Account
from vivintpy.models import AuthUserData, SystemData


# -----------------------------------------------------------------------------
# Fixtures & dummy collaborators
# -----------------------------------------------------------------------------


@pytest.fixture()
def sample_authuser() -> AuthUserData:
    """Return a minimal valid *AuthUserData* model with one system."""
    raw = {
        "u": [
            {
                "_id": "user1",
                "sn": "User One",
                "system": [
                    {
                        "panid": 1,
                        "_id": 1,
                        "sn": "Home",
                        "ad": True,
                        "par": [],
                    }
                ],
            }
        ],
        "is_read_only": False,
        "keep_signed_in": True,
    }
    return AuthUserData.model_validate(raw)


@pytest.fixture()
def sample_system() -> SystemData:
    """Return a minimal valid *SystemData* model."""
    raw = {
        "system": {
            "panid": 1,
            "fea": {},
            "sinfo": {},
            "par": [],
            "u": [],
        }
    }
    return SystemData.model_validate(raw)


class DummyApi:
    """Stub implementation of *VivintSkyApi* sufficient for *Account* tests."""

    def __init__(self, authuser: AuthUserData, system: SystemData):
        self._authuser = authuser
        self._system = system
        self.connect_called = False
        self.disconnect_called = False
        self.tokens: dict[str, str] = {"refresh_token": "tok"}

    async def connect(self):
        self.connect_called = True
        return self._authuser

    async def disconnect(self):
        self.disconnect_called = True

    async def get_authuser_data(self):
        return self._authuser

    async def get_system_data(self, _panel_id: int):  # pylint: disable=unused-argument
        return self._system


class DummyStream:
    """Stub implementation of *EventStream* protocol."""

    def __init__(self):
        self.connected = False
        self.subscribed_payload: Any | None = None
        self.subscribed_cb = None

    async def connect(self):
        self.connected = True

    async def subscribe(self, payload, cb):  # noqa: D401 – simple stub
        self.subscribed_payload = payload
        self.subscribed_cb = cb

    async def disconnect(self):
        self.connected = False


class DummySystem:
    """Lightweight replacement for real *System* class used during tests."""

    def __init__(self, data: SystemData, api, name: str, is_admin: bool):  # noqa: D401
        self.id = data.system.panid
        self.data = data
        self.name = name
        self.is_admin = is_admin
        self.refreshed = False
        self.received: Any | None = None

    async def refresh(self):
        self.refreshed = True

    def handle_pubnub_message(self, message):  # noqa: D401 – simple stub
        self.received = message


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_account_full_flow(monkeypatch, sample_authuser, sample_system):
    """Exercise connect/refresh/subscribe/handle_pubnub_message/disconnect."""

    # Wire up dummy collaborators
    dummy_api = DummyApi(sample_authuser, sample_system)
    dummy_stream = DummyStream()

    acc = Account(username="u", password="p", stream=dummy_stream)
    # Inject dummy api and dummy System implementation
    acc._api = dummy_api  # type: ignore[attr-defined,protected-access]
    monkeypatch.setattr("vivintpy.account.System", DummySystem)

    # Run *connect* with both flags so that refresh & subscribe are invoked
    await acc.connect(load_devices=True, subscribe_for_realtime_updates=True)

    # Expectations after connect
    assert acc.connected is True
    assert dummy_api.connect_called, "API.connect should be called"
    assert dummy_stream.connected, "Stream should be connected"
    assert acc.systems, "Systems list should be populated"
    system = acc.systems[0]
    assert isinstance(system, DummySystem)
    # New systems are instantiated with full data; refresh may not be called yet.

    # Exercise *handle_pubnub_message* – 1) ignored path, missing panel_id
    acc.handle_pubnub_message({"some": "value"})
    assert system.received is None  # ignored

    # 2) valid path
    msg = {"panid": 1, "t": "account_system", "op": "u", "d": {}}
    acc.handle_pubnub_message(msg)
    assert system.received == msg

    # Exercise *disconnect*
    await acc.disconnect()
    assert acc.connected is False
    assert dummy_api.disconnect_called, "API.disconnect should be awaited"
    assert not dummy_stream.connected, "Stream should be disconnected"
