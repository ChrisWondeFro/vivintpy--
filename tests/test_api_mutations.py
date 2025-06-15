"""Tests for mutating endpoints in `vivintpy.api.VivintSkyApi`.

We monkey-patch the private helpers to avoid any I/O – no HTTP or gRPC calls
are actually performed. Both happy-path and error branches are covered.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Awaitable, Callable

import pytest

from vivintpy.api import VivintSkyApi, VivintSkyApiError


# ---------------------------------------------------------------------------
# Test fixture helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def api(monkeypatch) -> VivintSkyApi:  # noqa: D401 – fixture
    """Return an API instance with completely stubbed internals."""

    # Provide a minimal client session object so attribute access works.
    async def _ok(*_a, **_kw):  # noqa: D401 – async stub
        return {"ok": True}

    # Provide minimal aiohttp-like session with post/put to avoid AttributeError in helpers
    dummy_session = SimpleNamespace(post=_ok, put=_ok, closed=False)

    # Patch __get_new_client_session to avoid aiohttp usage when the ctor is
    # called without an explicit session (belt-and-suspenders).
    monkeypatch.setattr(
        VivintSkyApi,
        "_VivintSkyApi__get_new_client_session",
        lambda self: dummy_session,
        raising=True,
    )

    instance = VivintSkyApi("user", password="pw", client_session=dummy_session)

    # Monkeypatch __post/__put helpers to prevent AttributeError from __call
    async def _return_ok(*_a, **_kw):  # noqa: D401 – async stub
        return {"ok": True}

    monkeypatch.setattr(instance, "_VivintSkyApi__post", _return_ok, raising=True)
    monkeypatch.setattr(instance, "_VivintSkyApi__put", _return_ok, raising=True)

    return instance


# ---------------------------------------------------------------------------
# gRPC-based helpers
# ---------------------------------------------------------------------------

from vivintpy.enums import ArmedState, GarageDoorState


@pytest.mark.parametrize(
    "method_name, kwargs",
    [
        ("set_camera_deter_mode", {"panel_id": 1, "device_id": 2, "state": True}),
        (
            "set_camera_privacy_mode",
            {"panel_id": 1, "device_id": 2, "state": False},
        ),
        (
            "set_camera_as_doorbell_chime_extender",
            {"panel_id": 1, "device_id": 2, "state": True},
        ),
        (
            "reboot_camera",
            {"panel_id": 1, "device_id": 2, "device_type": "camera"},
        ),
    ],
)
@pytest.mark.asyncio
async def test_grpc_mutations_invoked(api: VivintSkyApi, monkeypatch, method_name: str, kwargs: dict):
    """Ensure each gRPC mutation calls `_send_grpc` exactly once."""

    calls: list[Callable[..., Awaitable[Any]]] = []

    async def fake_send_grpc(cb):  # noqa: D401 – small stub
        calls.append(cb)

    monkeypatch.setattr(api, "_send_grpc", fake_send_grpc, raising=True)

    # Dynamically fetch the method under test
    method = getattr(api, method_name)
    await method(**kwargs)

    assert len(calls) == 1  # exactly one gRPC send performed


# ---------------------------------------------------------------------------
# HTTP (REST)-based helper – panel update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_panel_software_success(api: VivintSkyApi, monkeypatch):
    """`update_panel_software` succeeds when underlying POST returns truthy."""

    async def fake_post(path: str, **_):  # noqa: D401 – stub
        # assert path contains expected endpoint for extra safety
        assert path.endswith("system-update")
        return {"ok": True}

    monkeypatch.setattr(api, "_VivintSkyApi__post", fake_post, raising=True)

    # Should run without exception
    await api.update_panel_software(panel_id=1)


@pytest.mark.asyncio
async def test_update_panel_software_error(api: VivintSkyApi, monkeypatch):
    """`update_panel_software` raises on falsy / None response."""

    async def fake_post(path: str, **_):  # noqa: D401 – stub
        return None  # triggers error path

    monkeypatch.setattr(api, "_VivintSkyApi__post", fake_post, raising=True)

    with pytest.raises(VivintSkyApiError):
        await api.update_panel_software(panel_id=1)
