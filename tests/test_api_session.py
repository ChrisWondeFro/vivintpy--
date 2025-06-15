"""Tests for VivintSkyApi authentication/session helpers and internal HTTP wrapper."""

from __future__ import annotations

import types
from typing import Any

import asyncio
import importlib
from types import SimpleNamespace

import pytest

import jwt
from vivintpy.api import VivintSkyApi
from vivintpy.exceptions import (
    VivintSkyApiAuthenticationError,
    VivintSkyApiError,
)

# ---------------------------------------------------------------------------
# Helper: fake aiohttp response/context manager
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(
        self,
        status: int = 200,
        json_data: Any | None = None,
        text_data: str | None = None,
        content_type: str = "application/json",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._json_data = json_data or {}
        self._text_data = text_data or ""
        self.content_type = content_type
        self.headers = headers or {}

    async def json(self, encoding: str = "utf-8") -> Any:  # noqa: D401 – stub
        return self._json_data

    async def text(self) -> str:  # noqa: D401 – stub
        return self._text_data

    async def __aenter__(self):  # noqa: D401 – context
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: D401 – context
        pass

    def raise_for_status(self):  # noqa: D401 – stub
        pass


# ---------------------------------------------------------------------------
# Fixtures & stubs
# ---------------------------------------------------------------------------


@pytest.fixture()
def api(monkeypatch) -> VivintSkyApi:  # noqa: D401 – fixture
    """Return API instance with patched session and valid token."""

    dummy_session = SimpleNamespace(closed=False)

    monkeypatch.setattr(
        VivintSkyApi,
        "_VivintSkyApi__get_new_client_session",
        lambda self: dummy_session,
        raising=True,
    )

    instance = VivintSkyApi("user", password="pw", client_session=dummy_session)
    # Ensure is_session_valid passes by default by faking jwt.decode
    monkeypatch.setattr(jwt, "decode", lambda *a, **k: {}, raising=True)
    instance._VivintSkyApi__token = {"access_token": "xyz", "id_token": "abc"}
    return instance


# ---------------------------------------------------------------------------
# is_session_valid tests
# ---------------------------------------------------------------------------


def test_is_session_valid_true(monkeypatch, api):
    """jwt.decode succeeds => valid session."""

    monkeypatch.setattr(jwt, "decode", lambda *a, **k: {})
    assert api.is_session_valid() is True


def test_is_session_valid_expired(monkeypatch, api):
    """Expired token => invalid session."""

    class _Expired(jwt.ExpiredSignatureError):
        pass

    def _raise(*_a, **_k):
        raise _Expired("expired")

    monkeypatch.setattr(jwt, "decode", _raise)
    assert api.is_session_valid() is False


# ---------------------------------------------------------------------------
# __call via __post helper – various HTTP status branches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status, json_data, headers, expected",
    [
        (200, {"ok": True}, None, {"ok": True}),
        (302, None, {"Location": "/foo"}, {"location": "/foo"}),
    ],
)
@pytest.mark.asyncio
async def test_call_success_branches(monkeypatch, api, status, json_data, headers, expected):
    """Cover 200 and 302 branches of __call."""

    resp = _FakeResponse(status=status, json_data=json_data, headers=headers or {})

    async def _return_resp(*_args, **_kwargs):  # noqa: D401 – stub
        return resp

    dummy_session = SimpleNamespace(post=_return_resp, closed=False)
    monkeypatch.setattr(api, "_VivintSkyApi__client_session", dummy_session, raising=True)

    result = await api._VivintSkyApi__post("dummy")  # type: ignore[attr-defined]
    assert result == expected


@pytest.mark.asyncio
async def test_call_401_non_auth(monkeypatch, api):
    """Non-AUTH 401 should raise VivintSkyApiError with message extracted."""

    resp = _FakeResponse(status=401, json_data={"message": "nope"})

    async def _return_resp(*_a, **_kw):
        return resp

    dummy_session = SimpleNamespace(post=_return_resp, closed=False)
    monkeypatch.setattr(api, "_VivintSkyApi__client_session", dummy_session, raising=True)

    with pytest.raises(VivintSkyApiError):
        await api._VivintSkyApi__post("dummy")  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_call_401_auth(monkeypatch, api):
    """AUTH endpoint 401 should raise VivintSkyApiAuthenticationError."""

    resp = _FakeResponse(status=401, json_data={"message": "bad creds"})

    async def _return_resp(*_a, **_kw):
        return resp

    dummy_session = SimpleNamespace(post=_return_resp, closed=False)
    monkeypatch.setattr(api, "_VivintSkyApi__client_session", dummy_session, raising=True)

    with pytest.raises(VivintSkyApiAuthenticationError):
        # Prepend AUTH_ENDPOINT to hit auth-error branch
        await api._VivintSkyApi__post("https://id.vivint.com/whatever")  # type: ignore[attr-defined]
