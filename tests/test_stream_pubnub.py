"""Tests for ``vivintpy.stream`` PubNub and MQTT implementations.

These unit-tests monkey-patch the PubNub SDK classes with ultra-lightweight
stubs so that *no* network traffic occurs.  They exercise:

1. ``PubNubStream.subscribe`` – verifies correct channel construction and
   PNConfiguration.user_id as well as the *subscribe* call-chain.
2. ``PubNubStream.disconnect`` – ensures listener is removed and underlying
   client is stopped cleanly.
3. ``MqttStream`` placeholder – confirms all public coroutines raise
   ``NotImplementedError``.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Callable

import pytest

from vivintpy.stream import PubNubStream, MqttStream, PN_CHANNEL
from vivintpy import stream as stream_mod  # module reference for monkeypatching
from vivintpy.api import VivintSkyApi

# -----------------------------------------------------------------------------
# Dummy PubNub SDK replacements
# -----------------------------------------------------------------------------


class DummyPNConfiguration:  # pylint:disable=too-few-public-methods
    """Bare-minimum stand-in for ``pubnub.pnconfiguration.PNConfiguration``."""

    def __init__(self) -> None:
        # Attributes are later assigned dynamically by code under test.
        self.subscribe_key: str | None = None
        self.user_id: str | None = None


class _DummySubscribeChain:  # pylint:disable=too-few-public-methods
    """Imitates fluent subscribe().channels().with_presence().execute() chain."""

    def __init__(self, parent: "DummyPubNub") -> None:  # noqa: D401 – docstring OK
        self._parent = parent
        self._channel: str | None = None
        self._presence: bool = False

    # The real SDK returns *self* so we do the same for fluent API.
    def channels(self, channel: str):  # type: ignore[override]
        self._channel = channel
        return self

    def with_presence(self):  # type: ignore[override]
        self._presence = True
        return self

    def execute(self):  # type: ignore[override]
        # Record what was requested for later assertions.
        self._parent.executed = True
        self._parent.channel = self._channel
        self._parent.with_presence = self._presence
        return None


class DummyPubNub:  # pylint:disable=too-few-public-methods
    """Extremely simplified replacement for ``PubNubAsyncio``."""

    def __init__(self, config: DummyPNConfiguration):  # noqa: D401 – simple init
        self.config = config
        self.listener = None
        self.executed = False
        self.channel: str | None = None
        self.with_presence: bool | None = None
        # flags for disconnect path
        self.removed_listener = False
        self.unsub_called = False
        self.stopped = False

    # ------------------------------------------------------------------
    # Methods required by PubNubStream
    # ------------------------------------------------------------------

    def add_listener(self, listener):  # type: ignore[override]
        self.listener = listener

    def subscribe(self):  # type: ignore[override]
        return _DummySubscribeChain(self)

    def remove_listener(self, listener):  # type: ignore[override]
        # Record removal for assertions.
        if listener is self.listener:
            self.removed_listener = True

    def unsubscribe_all(self):  # type: ignore[override]
        self.unsub_called = True

    async def stop(self):  # type: ignore[override]
        # Simulate async cleanup.
        await asyncio.sleep(0)  # yield control to loop
        self.stopped = True


# -----------------------------------------------------------------------------
# Fixtures / helpers
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_pubnub(monkeypatch):
    """Automatically patch PubNub SDK objects for all tests in this module."""

    monkeypatch.setattr(stream_mod, "PNConfiguration", DummyPNConfiguration, raising=True)
    monkeypatch.setattr(stream_mod, "PubNubAsyncio", DummyPubNub, raising=True)
    yield  # test(s) run


# -----------------------------------------------------------------------------
# Test cases
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pubnub_subscribe_and_disconnect():
    """Happy path: subscribe builds correct channel and disconnect cleans up."""

    api = VivintSkyApi(username="u", password="p")
    stream = PubNubStream(api)

    # Minimal *authuser* payload – dict form to verify validation branch.
    authuser_data: dict[str, Any] = {
        "u": [{"_id": "user1", "mbc": "abc123", "system": []}],
        "is_read_only": False,
    }

    # Subscribe – should instantiate our DummyPubNub and invoke subscribe chain.
    await stream.subscribe(authuser_data, callback=lambda _msg: None)

    # Assertions on the DummyPubNub internals.
    dummy = stream._pubnub  # type: ignore[attr-defined]
    assert isinstance(dummy, DummyPubNub)
    assert dummy.executed is True  # subscribe().execute() was called
    assert dummy.channel == f"{PN_CHANNEL}#abc123"
    # user_id should be prefixed with "pn-" and uppercase uid
    assert dummy.config.user_id == "pn-USER1"

    # Now exercise disconnect path.
    await stream.disconnect()
    assert dummy.removed_listener is True
    assert dummy.unsub_called is True
    assert dummy.stopped is True


@pytest.mark.asyncio
async def test_mqtt_stream_not_implemented():
    """MQTT placeholder should raise NotImplementedError on all methods."""

    mqtt = MqttStream(api=SimpleNamespace())  # api is unused

    with pytest.raises(NotImplementedError):
        await mqtt.connect()

    with pytest.raises(NotImplementedError):
        await mqtt.subscribe({}, lambda _m: None)

    with pytest.raises(NotImplementedError):
        await mqtt.disconnect()
