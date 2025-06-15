"""Tests for mutating / action endpoints on ``vivintpy.api.VivintSkyApi``.

These endpoints previously had minimal or no coverage.  The tests focus on
verifying that:

1. Successful HTTP / gRPC calls do **not** raise.
2. A ``None`` response from the underlying private HTTP helpers causes the
   public coroutine to raise ``VivintSkyApiError``.
3. gRPC-backed helpers delegate correctly to ``_send_grpc``.

Network traffic is stubbed out via ``monkeypatch`` so the tests run fully
offline.
"""

from __future__ import annotations

import types

import pytest

from vivintpy.api import VivintSkyApi, VivintSkyApiError

# -----------------------------------------------------------------------------
# Helper factories
# -----------------------------------------------------------------------------


def _dummy_put_factory(return_value):
    async def _dummy_put(path, **kwargs):  # pylint:disable=unused-argument
        return return_value

    return _dummy_put


def _dummy_post_factory(return_value):
    async def _dummy_post(path, **kwargs):  # pylint:disable=unused-argument
        return return_value

    return _dummy_post


# -----------------------------------------------------------------------------
# Tests for __put-backed endpoints
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,args",
    [
        ("set_lock_state", (1, 0, 42, True)),  # panel, partition, device, locked
        ("set_garage_door_state", (1, 0, 7, 0)),  # panel, partition, device, state
    ],
)
async def test_put_based_actions(monkeypatch, method: str, args: tuple):
    """Verify ``set_lock_state`` / ``set_garage_door_state`` success & failure."""

    api = VivintSkyApi(username="u", password="p")

    # Success path – private __put returns an empty dict => no exception.
    monkeypatch.setattr(api, "_VivintSkyApi__put", _dummy_put_factory({}))
    await getattr(api, method)(*args)  # should *not* raise

    # Failure path – private __put returns None => VivintSkyApiError expected.
    monkeypatch.setattr(api, "_VivintSkyApi__put", _dummy_put_factory(None))
    with pytest.raises(VivintSkyApiError):
        await getattr(api, method)(*args)


# -----------------------------------------------------------------------------
# Tests for __post-backed endpoints
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_panel_software(monkeypatch):
    """``update_panel_software`` should raise on falsy response."""

    api = VivintSkyApi(username="u", password="p")

    # Success path
    monkeypatch.setattr(api, "_VivintSkyApi__post", _dummy_post_factory({"ok": True}))
    await api.update_panel_software(1)

    # Failure path
    monkeypatch.setattr(api, "_VivintSkyApi__post", _dummy_post_factory(None))
    with pytest.raises(VivintSkyApiError):
        await api.update_panel_software(1)


# -----------------------------------------------------------------------------
# Tests for gRPC-backed endpoints – ensure they delegate to _send_grpc
# -----------------------------------------------------------------------------


_GRPC_METHODS: list[tuple[str, tuple]] = [
    ("set_camera_privacy_mode", (1, 55, True)),
    ("set_camera_deter_mode", (1, 55, True)),
    ("set_camera_as_doorbell_chime_extender", (1, 55, True)),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,args", _GRPC_METHODS)
async def test_grpc_based_actions(monkeypatch, method: str, args: tuple):
    """Ensure gRPC helpers invoke ``_send_grpc`` once with a callback."""

    api = VivintSkyApi(username="u", password="p")

    called: dict[str, bool | types.CoroutineType] = {"count": 0, "cb": None}

    async def _dummy_send(callback):  # pylint:disable=unused-argument
        # Store that we were invoked and capture the callback for inspection.
        called["count"] += 1
        called["cb"] = callback  # should be an async callable

    monkeypatch.setattr(api, "_send_grpc", _dummy_send)

    await getattr(api, method)(*args)

    assert called["count"] == 1
    assert callable(called["cb"])
