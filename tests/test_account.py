import pytest
from vivintpy.account import Account
from vivintpy.models import AuthUserData

class DummyApi:
    """Stub API for testing Account."""
    async def connect(self):
        # Return dummy AuthUserData model
        raw = {"u": [], "is_read_only": True, "keep_signed_in": False}
        return AuthUserData.model_validate(raw)

    async def disconnect(self):
        pass

@pytest.mark.asyncio
async def test_connect_triggers_sub_and_refresh(monkeypatch):
    dummy_api = DummyApi()
    account = Account(username="u", password="p", stream=None)
    account._api = dummy_api

    called_sub = False
    called_refresh = False

    async def fake_subscribe(auth):
        nonlocal called_sub
        called_sub = True

    async def fake_refresh(auth=None):
        nonlocal called_refresh
        called_refresh = True

    monkeypatch.setattr(account, "subscribe_for_realtime_updates", fake_subscribe)
    monkeypatch.setattr(account, "refresh", fake_refresh)

    auth = await account.connect(load_devices=True, subscribe_for_realtime_updates=True)
    assert isinstance(auth, AuthUserData)
    assert called_sub, "subscribe_for_realtime_updates should be called"
    assert called_refresh, "refresh should be called"
