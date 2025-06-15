import pytest
import asyncio

from vivintpy.stream import get_default_stream, PubNubStream, MqttStream
from vivintpy.api import VivintSkyApi
from vivintpy.account import Account


class DummyStream:
    """Fake EventStream for testing injection."""
    def __init__(self):
        self.calls = []  # record method names and args

    async def connect(self):
        self.calls.append("connect")

    async def subscribe(self, authuser_data, callback):
        self.calls.append(("subscribe", authuser_data, callback))

    async def disconnect(self):
        self.calls.append("disconnect")


@pytest.mark.asyncio
async def test_default_stream_returns_pubnub():
    api = VivintSkyApi(username="user", password="pass")
    stream = get_default_stream(api)
    assert isinstance(stream, PubNubStream)


@pytest.mark.asyncio
async def test_account_uses_injected_stream(monkeypatch):
    # Prepare dummy auth data
    dummy_auth = {"dummy": True}
    # Stub get_authuser_data to return dummy_auth
    dummy_stream = DummyStream()
    account = Account(username="u", password="p", refresh_token=None, stream=dummy_stream)
    monkeypatch.setattr(account.api, "get_authuser_data", lambda: dummy_auth)
    # Call subscribe, should use DummyStream
    await account.subscribe_for_realtime_updates()
    assert dummy_stream.calls[0] == "connect"
    assert dummy_stream.calls[1][0] == "subscribe"
    assert dummy_stream.calls[1][1] == dummy_auth
    assert callable(dummy_stream.calls[1][2])


@pytest.mark.asyncio
async def test_mqtt_stream_not_implemented():
    api = VivintSkyApi(username="u", password="p")
    mqtt = MqttStream(api)
    with pytest.raises(NotImplementedError):
        await mqtt.connect()
    with pytest.raises(NotImplementedError):
        await mqtt.subscribe({}, lambda x: x)
    with pytest.raises(NotImplementedError):
        await mqtt.disconnect()
