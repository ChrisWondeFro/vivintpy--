import pytest
from vivintpy.api import VivintSkyApi
from vivintpy.models import (
    PanelCredentialsData,
    SystemData,
    PanelUpdateData,
    AuthUserData,
)


def _dummy_get_factory(return_value):
    async def _dummy_get(path, **kwargs):  # pylint: disable=unused-argument
        return return_value
    return _dummy_get


def _dummy_put_factory(return_value):
    async def _dummy_put(path, **kwargs):  # pylint: disable=unused-argument
        return return_value
    return _dummy_put


def _dummy_post_factory(return_value):
    async def _dummy_post(path, **kwargs):  # pylint: disable=unused-argument
        return return_value
    return _dummy_post


@pytest.mark.asyncio
async def test_get_panel_credentials_returns_model(monkeypatch):
    api = VivintSkyApi(username="u", password="p")
    dummy = {"n": "user", "pswd": "pass"}
    monkeypatch.setattr(api, "_VivintSkyApi__get", _dummy_get_factory(dummy))
    cred = await api.get_panel_credentials(123)
    assert isinstance(cred, PanelCredentialsData)
    assert cred.name == "user"
    assert cred.password == "pass"


@pytest.mark.asyncio
async def test_get_system_data_returns_model(monkeypatch):
    api = VivintSkyApi(username="u", password="p")
    raw = {"system": {"panid": 1, "fea": {}, "sinfo": {}, "par": [], "u": []}}
    monkeypatch.setattr(api, "_VivintSkyApi__get", _dummy_get_factory(raw))
    model = await api.get_system_data(1)
    assert isinstance(model, SystemData)
    assert model.system.panid == 1


@pytest.mark.asyncio
async def test_get_system_update_returns_model(monkeypatch):
    api = VivintSkyApi(username="u", password="p")
    raw = {"av": True, "asv": "v2", "csv": "v1", "rsn": "reason"}
    monkeypatch.setattr(api, "_VivintSkyApi__get", _dummy_get_factory(raw))
    update = await api.get_system_update(1)
    assert isinstance(update, PanelUpdateData)
    assert update.available is True
    assert update.available_version == "v2"
    assert update.current_version == "v1"
    assert update.update_reason == "reason"


@pytest.mark.asyncio
async def test_get_device_data_returns_model(monkeypatch):
    api = VivintSkyApi(username="u", password="p")
    raw = {"system": {"panid": 1, "fea": {}, "sinfo": {}, "par": [], "u": []}}
    monkeypatch.setattr(api, "_VivintSkyApi__get", _dummy_get_factory(raw))
    model = await api.get_device_data(1, 2)
    assert isinstance(model, SystemData)
    assert model.system.panid == 1


@pytest.mark.asyncio
async def test_get_camera_thumbnail_url_success(monkeypatch):
    api = VivintSkyApi(username="u", password="p")
    monkeypatch.setattr(
        api,
        "_VivintSkyApi__get",
        _dummy_get_factory({"location": "https://cdn.example.com/t.jpg"}),
    )
    url = await api.get_camera_thumbnail_url(1, 0, 2, 123456)
    assert url == "https://cdn.example.com/t.jpg"


@pytest.mark.asyncio
async def test_set_alarm_state(monkeypatch):
    api = VivintSkyApi(username="u", password="p")
    # success path
    monkeypatch.setattr(api, "_VivintSkyApi__put", _dummy_put_factory({}))
    await api.set_alarm_state(1, 0, 3)  # should not raise
    # error path -> None triggers VivintSkyApiError
    monkeypatch.setattr(api, "_VivintSkyApi__put", _dummy_put_factory(None))
    with pytest.raises(Exception):
        await api.set_alarm_state(1, 0, 3)


@pytest.mark.asyncio
async def test_trigger_alarm(monkeypatch):
    api = VivintSkyApi(username="u", password="p")
    monkeypatch.setattr(api, "_VivintSkyApi__post", _dummy_post_factory({"ok": True}))
    await api.trigger_alarm(1, 0)
    monkeypatch.setattr(api, "_VivintSkyApi__post", _dummy_post_factory(None))
    with pytest.raises(Exception):
        await api.trigger_alarm(1, 0)


@pytest.mark.asyncio
async def test_get_authuser_data_returns_model(monkeypatch):
    api = VivintSkyApi(username="u", password="p")
    raw = {"u": {"_id": "user1", "system": {"panid": 1, "fea": {}, "sinfo": {}, "par": [], "u": []}},
           "is_read_only": False, "keep_signed_in": True}
    monkeypatch.setattr(api, "_VivintSkyApi__get", _dummy_get_factory(raw))
    model = await api.get_authuser_data()
    assert isinstance(model, AuthUserData)
    assert len(model.users) == 1
    assert model.users[0].id == "user1"
