"""Unit tests for vivintpy.stream module (lightweight, no real PubNub network)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List

import pytest

from vivintpy.stream import (
    MqttStream,
    PubNubStream,
    _VivintPubNubSubscribeListener,
    get_default_stream,
)


class DummyApi:  # minimal stand-in for VivintSkyApi
    pass


def test_get_default_stream_returns_pubnub() -> None:
    api = DummyApi()
    stream = get_default_stream(api)  # type: ignore[arg-type]
    assert isinstance(stream, PubNubStream)


@pytest.mark.asyncio
async def test_mqtt_stream_unimplemented() -> None:
    api = DummyApi()
    mqtt = MqttStream(api)  # type: ignore[arg-type]

    for call in (
        mqtt.connect(),
        mqtt.subscribe({}, lambda _: None),  # type: ignore[arg-type]
        mqtt.disconnect(),
    ):
        with pytest.raises(NotImplementedError):
            await call


@pytest.mark.asyncio
async def test_pubnub_listener_dispatch() -> None:
    # Collect messages passed to callback
    received: List[Any] = []
    listener = _VivintPubNubSubscribeListener(received.append)

    # Simulate status updates (non-error and error paths)
    class DummyStatus:
        def __init__(self, error: bool) -> None:
            self.operation = "TestOp"
            self.category = "TestCat"
            self._error = error
            self.error_data = SimpleNamespace(information="fail")

        def is_error(self) -> bool:  # noqa: D401
            return self._error

    # Ensure both branches execute without raising
    listener.status(None, DummyStatus(error=False))  # type: ignore[arg-type]
    listener.status(None, DummyStatus(error=True))  # type: ignore[arg-type]

    # Simulate message delivery
    dummy_msg = SimpleNamespace(message={"foo": "bar"})
    listener.message(None, dummy_msg)  # type: ignore[arg-type]

    assert received == [{"foo": "bar"}]
