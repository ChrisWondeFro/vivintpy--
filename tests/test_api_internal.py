"""Extra unit-tests focused on VivintSkyApi internals to lift coverage.

These tests exercise the private ``__call`` request wrapper and ``_send_grpc``
helper, which together account for ~120 lines of code previously uncovered.
They rely exclusively on monkey-patching and lightweight fakes; no real network
traffic is performed.
"""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

import pytest

import grpc
from vivintpy.proto import beam_pb2_grpc

from vivintpy.api import AUTH_ENDPOINT, API_ENDPOINT, VivintSkyApi


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------

class _FakeResponse:  # noqa: D101 – internal test helper
    def __init__(self, status: int = 200, data: Dict[str, Any] | None = None):
        self.status = status
        self._data: Dict[str, Any] = data or {}
        self.content_type = "application/json"
        self.headers: Dict[str, str] = {}

    async def json(self, encoding: str = "utf-8"):  # noqa: D401
        return self._data

    async def text(self):  # noqa: D401 – minimal impl
        return json.dumps(self._data)

    async def __aenter__(self):  # noqa: D401
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: D401 – nothing to clean-up
        return False

    def raise_for_status(self):  # noqa: D401 – never raises in tests
        if self.status >= 400:
            raise RuntimeError("unexpected status in test")


class _DummyChannel:  # noqa: D101 – minimal async context manager for grpc channel
    async def __aenter__(self):  # noqa: D401
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: D401
        return False


async def _tracking_secure_channel(*_args, **_kwargs):  # noqa: D401 – returns coroutine branch
    """Return a coroutine that yields a DummyChannel.

    This covers the code-path where ``grpc.aio.secure_channel`` returns a
    coroutine which must be awaited (common when patched by ``AsyncMock`` in
    production tests).
    """

    async def _inner():  # noqa: D401
        return _DummyChannel()

    return await _inner()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_injects_bearer_and_reauth(monkeypatch):
    """__call refreshes auth and injects Authorization header when needed."""

    # Arrange – create API with a *known* client session (doesn't need to work).
    api = VivintSkyApi("user", password="pass")

    # Pretend the existing JWT is expired so __call triggers reconnect.
    monkeypatch.setattr(api, "is_session_valid", lambda: False)

    # Track whether we invoked reconnect.
    called: List[bool] = []

    async def _fake_connect():  # noqa: D401
        called.append(True)

    monkeypatch.setattr(api, "connect", _fake_connect)

    # Fake token so Authorization header can be formed *after* reconnect.
    api._VivintSkyApi__token = {  # type: ignore[attr-defined]
        "access_token": "xyz",
        "id_token": "dummy.jwt.with.future.exp",
    }

    # Record arguments with which the HTTP method is called.
    record: Dict[str, Any] = {}

    async def _fake_get(path, headers=None, **kwargs):  # noqa: D401
        record.update(path=path, headers=headers, kwargs=kwargs)
        return _FakeResponse()

    # Act – invoke private __call.
    result = await api._VivintSkyApi__call(_fake_get, "foo/bar")  # type: ignore[attr-defined]

    # Assert – correct response parsing and header injection.
    assert result == {}, "Should return parsed JSON payload"
    assert called, "connect() should be called when session not valid"
    assert record["path"].startswith(f"{API_ENDPOINT}/foo/bar")
    assert record["headers"]["Authorization"] == "Bearer xyz"


@pytest.mark.asyncio
async def test_send_grpc_supports_coroutine_secure_channel(monkeypatch):
    """_send_grpc handles grpc.aio.secure_channel returning a coroutine."""

    api = VivintSkyApi("user", password="pass")

    # Stub session validity & tokens so _send_grpc pre-conditions pass.
    monkeypatch.setattr(api, "is_session_valid", lambda: True)
    api._VivintSkyApi__token = {  # type: ignore[attr-defined]
        "access_token": "xyz",
        "id_token": "dummy",
    }

    # Patch secure_channel to our coroutine-returning stub.
    monkeypatch.setattr(grpc.aio, "secure_channel", _tracking_secure_channel)

    # Patch BeamStub to a lightweight callable that ignores channel.
    monkeypatch.setattr(beam_pb2_grpc, "BeamStub", lambda channel: SimpleNamespace())

    # Capture arguments forwarded to callback.
    received: Dict[str, Any] = {}

    async def _callback(stub, metadata):  # noqa: D401 – simple capture
        received["stub"] = stub
        received["metadata"] = metadata
        return SimpleNamespace(msg="ok")

    # Act – should run without exception.
    await api._send_grpc(_callback)

    # Assert – callback got token metadata and stub instance.
    assert received["metadata"] == [("token", "xyz")]
    assert received["stub"] is not None
