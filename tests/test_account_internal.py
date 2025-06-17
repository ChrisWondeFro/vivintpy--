"""Unit tests targeting vivintpy.account.Account to raise coverage."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from vivintpy.account import Account


class _DummyAPI:  # noqa: D401 – lightweight stub matching VivintSkyApi surface
    def __init__(self):
        self.calls: Dict[str, Any] = {}
        self.tokens = {"refresh_token": "tok"}

    async def connect(self):  # noqa: D401
        self.calls["connect"] = True
        return {}

    async def disconnect(self):  # noqa: D401
        self.calls["disconnect"] = True

    async def verify_mfa(self, code):  # noqa: D401
        self.calls["verify_mfa"] = code

    async def get_authuser_data(self):  # noqa: D401
        # Minimal payload accepted by refresh() logic
        return {
            "u": [
                {
                    "_id": "user1",
                    "system": [
                        {
                            "panid": 123,
                            "sn": "My System",
                            "ad": True,
                            "par": [],
                        }
                    ],
                }
            ],
            "id_token": "tok",
            "is_read_only": False,
        }


class _DummyStream:  # noqa: D401 – stub for EventStream
    def __init__(self):
        self.calls: List[str] = []

    async def connect(self):  # noqa: D401
        self.calls.append("connect")

    async def subscribe(self, raw, handler):  # noqa: D401, ARG001
        self.calls.append("subscribe")

    async def disconnect(self):  # noqa: D401
        self.calls.append("disconnect")


@pytest.mark.asyncio
async def test_account_connect_verify_disconnect(monkeypatch):
    """Exercise connect → verify_mfa → disconnect happy-path."""

    # Patch out expensive dependencies
    monkeypatch.setattr("vivintpy.account.System", lambda *a, **kw: SimpleNamespace(refresh=lambda: asyncio.sleep(0)))
    monkeypatch.setattr("vivintpy.account.first_or_none", lambda seq, pred: None)

    dummy_stream = _DummyStream()
    acc = Account("user", "pass", stream=dummy_stream)
    # Replace internally-created API with stub
    dummy_api = _DummyAPI()
    acc._api = dummy_api  # type: ignore[attr-defined, protected-access]

    # Monkey-patch refresh to avoid deep recursion but mark it was invoked.
    called: Dict[str, bool] = {}

    async def _fake_refresh(*args, **kwargs):  # noqa: D401, ARG001
        called["refresh"] = True

    monkeypatch.setattr(acc, "refresh", _fake_refresh)

    # CONNECT (with both toggles True)
    await acc.connect(load_devices=True, subscribe_for_realtime_updates=True)
    assert dummy_api.calls.get("connect"), "API.connect should be called"
    assert "connect" in dummy_stream.calls and "subscribe" in dummy_stream.calls
    assert called.get("refresh"), "refresh() should be triggered when load_devices=True"
    assert acc.connected is True

    # VERIFY_MFA – should forward code and refresh again
    await acc.verify_mfa("123456")
    assert dummy_api.calls.get("verify_mfa") == "123456"

    # DISCONNECT – should close stream and api
    await acc.disconnect()
    assert "disconnect" in dummy_stream.calls
    assert dummy_api.calls.get("disconnect"), "API.disconnect should be called"
    assert acc.connected is False
