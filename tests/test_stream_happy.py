"""Happy-path tests for `PubNubStream` and placeholder checks for `MqttStream`."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List

import pytest

from vivintpy.models import AuthUserData
from vivintpy.stream import PubNubStream, MqttStream
from vivintpy.api import VivintSkyApi


# -----------------------------------------------------------------------------
# Helpers – dummy PubNub replacement
# -----------------------------------------------------------------------------

class _DummySubscription:  # pylint: disable=too-few-public-methods
    """Fluent helper object returned by DummyPubNub.subscribe()."""

    def __init__(self, parent: "DummyPubNub") -> None:
        self._parent = parent

    def channels(self, *_channels):  # noqa: D401 – stub
        # record but ignore channels; we only need the call-chain
        return self

    def with_presence(self):  # noqa: D401 – stub
        return self

    def execute(self):  # noqa: D401 – stub
        self._parent._subscribed = True  # type: ignore[attr-defined]
        return None


class DummyPubNub:  # pylint: disable=too-few-public-methods
    """Extremely small subset mimicking PubNubAsyncio behaviour."""

    def __init__(self, _cfg: object) -> None:  # cfg is PNConfiguration
        self.listener = None
        self._subscribed = False
        self.removed_listener = False
        self.unsubscribed = False
        self.stopped = False

    # API used by PubNubStream -------------------------------------------------
    def add_listener(self, listener):  # noqa: D401 – stub
        self.listener = listener

    def remove_listener(self, listener):  # noqa: D401 – stub
        assert listener is self.listener
        self.removed_listener = True

    def unsubscribe_all(self):  # noqa: D401 – stub
        self.unsubscribed = True

    def subscribe(self):  # noqa: D401 – stub
        return _DummySubscription(self)

    async def stop(self):  # noqa: D401 – stub
        self.stopped = True


class DummyMessage:  # pylint: disable=too-few-public-methods
    """Mimic `PNMessageResult` with a `message` attribute."""

    def __init__(self, payload: dict) -> None:
        self.message = payload


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pubnub_happy_path(monkeypatch):
    """Subscribe, dispatch a message, then disconnect cleanly."""

    api = VivintSkyApi(username="u", password="p")
    stream = PubNubStream(api)

    # Patch SDK objects used by PubNubStream ----------------------------------
    import vivintpy.stream as stream_mod  # local import to monkey-patch

    monkeypatch.setattr(stream_mod, "PubNubAsyncio", DummyPubNub, raising=True)

    # Simple PNConfiguration substitute that accepts attr assignment
    class _Cfg(SimpleNamespace):
        pass

    monkeypatch.setattr(stream_mod, "PNConfiguration", lambda: _Cfg(), raising=True)

    # Capture callback invocations
    received: List[dict[str, Any]] = []

    # Build minimal AuthUserData with one user (id + mbc)
    raw_auth = {
        "u": [
            {
                "_id": "user42",
                "mbc": "XYZ",
                "system": [],
            }
        ],
        "is_read_only": False,
    }
    auth_model = AuthUserData.model_validate(raw_auth)

    await stream.subscribe(auth_model, callback=received.append)

    # Fake message dispatch ----------------------------------------------------
    assert isinstance(stream._listener, stream_mod._VivintPubNubSubscribeListener)  # type: ignore[attr-defined]
    dummy_payload = {"hello": "world"}
    stream._listener.message(None, DummyMessage(dummy_payload))  # type: ignore[attr-defined]

    assert received == [dummy_payload]

    # Now disconnect (should call our DummyPubNub helpers)
    await stream.disconnect()
    dummy_pn: DummyPubNub = stream._pubnub  # type: ignore[attr-defined]

    assert dummy_pn.removed_listener is True
    assert dummy_pn.unsubscribed is True
    assert dummy_pn.stopped is True


# -----------------------------------------------------------------------------
# MQTT placeholder ----------------------------------------------------------------
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mqtt_stream_unimplemented():
    api = VivintSkyApi(username="u", password="p")
    mqtt = MqttStream(api)

    with pytest.raises(NotImplementedError):
        await mqtt.connect()
    with pytest.raises(NotImplementedError):
        await mqtt.subscribe({}, lambda _m: None)
    with pytest.raises(NotImplementedError):
        await mqtt.disconnect()
