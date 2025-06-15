"""Additional tests for VivintSkyApi action / mutating endpoints
covering reboot helpers, switch state, and error paths not yet exercised.
"""

from __future__ import annotations

import pytest

from vivintpy.api import VivintSkyApi, VivintSkyApiError


# -----------------------------------------------------------------------------
# Shared dummy factories -------------------------------------------------------
# -----------------------------------------------------------------------------

def _dummy_post_factory(return_value):
    async def _dummy_post(path, **kwargs):  # pylint: disable=unused-argument
        return return_value

    return _dummy_post


def _dummy_put_factory(return_value):
    async def _dummy_put(path, **kwargs):  # pylint: disable=unused-argument
        return return_value

    return _dummy_put


# -----------------------------------------------------------------------------
# reboot helpers ---------------------------------------------------------------
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reboot_panel_success_and_failure(monkeypatch):
    """reboot_panel should pass on truthy response and raise on falsy."""

    api = VivintSkyApi(username="u", password="p")

    # success path: __post returns non-empty json ⇒ no exception
    monkeypatch.setattr(api, "_VivintSkyApi__post", _dummy_post_factory({"ok": True}))
    await api.reboot_panel(1)

    # failure path: __post returns None ⇒ VivintSkyApiError
    monkeypatch.setattr(api, "_VivintSkyApi__post", _dummy_post_factory(None))
    with pytest.raises(VivintSkyApiError):
        await api.reboot_panel(1)


@pytest.mark.asyncio
async def test_reboot_camera_delegates_to_grpc(monkeypatch):
    """reboot_camera should call _send_grpc exactly once with a callback."""

    api = VivintSkyApi(username="u", password="p")

    called: dict[str, int] = {"count": 0}

    async def _dummy_send(callback):  # pylint:disable=unused-argument
        called["count"] += 1

    monkeypatch.setattr(api, "_send_grpc", _dummy_send)

    await api.reboot_camera(1, 55, "doorbell")

    assert called["count"] == 1


# -----------------------------------------------------------------------------
# set_switch_state -------------------------------------------------------------
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs",
    [
        {},  # neither on nor level supplied
        {"on": None, "level": None},  # explicit None equivalents
        {"level": -1},  # invalid low
        {"level": 101},  # invalid high
    ],
)
async def test_set_switch_state_validation_errors(monkeypatch, kwargs):
    """Invalid arguments should raise VivintSkyApiError before any HTTP call."""

    api = VivintSkyApi(username="u", password="p")

    # Patch __put with sentinel that will raise if invoked – to ensure validation happens first
    async def _fail_if_called(*_args, **_kw):  # pragma: no cover
        raise AssertionError("__put should not be called for invalid input")

    monkeypatch.setattr(api, "_VivintSkyApi__put", _fail_if_called)

    with pytest.raises(VivintSkyApiError):
        await api.set_switch_state(1, 0, 99, **kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call_kwargs",
    [
        {"on": True},  # binary on/off
        {"level": 50},  # multilevel
    ],
)
async def test_set_switch_state_success_and_failure(monkeypatch, call_kwargs):
    """set_switch_state should succeed on truthy response and raise on falsy."""

    api = VivintSkyApi(username="u", password="p")

    # success path
    monkeypatch.setattr(api, "_VivintSkyApi__put", _dummy_put_factory({}))
    await api.set_switch_state(1, 0, 99, **call_kwargs)

    # failure path ⇒ None
    monkeypatch.setattr(api, "_VivintSkyApi__put", _dummy_put_factory(None))
    with pytest.raises(VivintSkyApiError):
        await api.set_switch_state(1, 0, 99, **call_kwargs)


# -----------------------------------------------------------------------------
# Error paths for model-returning GET helpers ----------------------------------
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,args",
    [
        ("get_system_update", (1,)),
        ("get_device_data", (1, 2)),
    ],
)
async def test_get_helpers_raise_on_none(monkeypatch, method: str, args: tuple):
    """When underlying __get returns None these helpers should raise."""

    api = VivintSkyApi(username="u", password="p")
    monkeypatch.setattr(api, "_VivintSkyApi__get", _dummy_post_factory(None))  # type: ignore

    with pytest.raises(VivintSkyApiError):
        await getattr(api, method)(*args)
