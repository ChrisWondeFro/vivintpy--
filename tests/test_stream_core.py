"""Additional tests for vivintpy.stream focusing on edge cases and early-return
branches that were still uncovered after the happy-path tests in
`test_stream_pubnub.py`.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from vivintpy.stream import PubNubStream
from vivintpy.api import VivintSkyApi


@pytest.mark.asyncio
async def test_pubnub_disconnect_without_subscribe():
    """`disconnect` should silently return when no listener/pubnub was created."""

    api = VivintSkyApi(username="u", password="p")
    stream = PubNubStream(api)

    # This must not raise – underlying attributes are still None.
    await stream.disconnect()
    # _pubnub and _listener are expected to remain None.
    assert stream._pubnub is None  # type: ignore[attr-defined]
    assert stream._listener is None  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# subscribe() validation branches --------------------------------------------
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "auth_payload, reason",
    [
        ({"u": [], "is_read_only": False}, "no_users"),
        (
            {
                "u": [{"_id": "user1", "system": [], "mbc": None}],
                "is_read_only": False,
            },
            "missing_mbc",
        ),
        (
            {
                "u": [{"_id": "", "system": [], "mbc": "ABC"}],
                "is_read_only": False,
            },
            "missing_uid",
        ),
    ],
)
async def test_pubnub_subscribe_validation(monkeypatch, auth_payload: dict[str, Any], reason: str):
    """When validation fails no PubNub instance should be created."""

    api = VivintSkyApi(username="u", password="p")
    stream = PubNubStream(api)

    # Ensure we *fail* if PubNubAsyncio is accidentally instantiated.
    def _fail_if_called(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("PubNubAsyncio should not be instantiated for %s" % reason)

    import vivintpy.stream as stream_mod  # late import to patch

    monkeypatch.setattr(stream_mod, "PubNubAsyncio", _fail_if_called, raising=True)

    await stream.subscribe(auth_payload, callback=lambda _m: None)

    # Validation path ⇒ no pubnub/listener created
    assert stream._pubnub is None  # type: ignore[attr-defined]
    assert stream._listener is None  # type: ignore[attr-defined]
