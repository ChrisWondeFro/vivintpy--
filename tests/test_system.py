import pytest
from vivintpy.system import System
from vivintpy.models import SystemData
from vivintpy.const import SystemAttribute as Attribute, PubNubMessageAttribute
from vivintpy.devices.alarm_panel import AlarmPanel


class DummyApi:
    def __init__(self, system_data):
        self.system_data = system_data
        self.calls = []

    async def get_system_data(self, panel_id):
        self.calls.append(panel_id)
        return self.system_data

@pytest.mark.asyncio
async def test_refresh_appends_and_updates_panel():
    raw = {'system': {'panid': 1, 'fea': {}, 'sinfo': {}, 'par': [{'panid': 1, 'parid': 2, 'd': [], 'ureg': []}], 'u': []}}
    model = SystemData.model_validate(raw)
    dummy_api = DummyApi(model)
    system = System(data=model, api=dummy_api, name='sys', is_admin=True)
    assert len(system.alarm_panels) == 1
    await system.refresh()
    assert dummy_api.calls == [1]
    assert len(system.alarm_panels) == 1

def test_update_user_data_calls_user_handle():
    raw = {'system': {'panid': 1, 'fea': {}, 'sinfo': {}, 'par': [{'panid': 1, 'parid': 2, 'd': [], 'ureg': []}], 'u': [{'_id': 99}]}}
    model = SystemData.model_validate(raw)
    dummy_api = DummyApi(model)
    system = System(data=model, api=dummy_api, name='sys', is_admin=False)
    user = system.users[0]
    called = False
    def fake_handle(msg):
        nonlocal called
        called = True
    user.handle_pubnub_message = fake_handle
    system.update_user_data([{'_id': 99}])
    assert called

def test_handle_pubnub_message_routes_messages():
    raw = {'system': {'panid': 1, 'fea': {}, 'sinfo': {}, 'par': [{'panid': 1, 'parid': 2, 'd': [], 'ureg': []}], 'u': []}}
    model = SystemData.model_validate(raw)
    dummy_api = DummyApi(model)
    system = System(data=model, api=dummy_api, name='sys', is_admin=False)
    panel = system.alarm_panels[0]
    handled = False
    def fake_panel(msg):
        nonlocal handled
        handled = True
    panel.handle_pubnub_message = fake_panel
    # account_partition without data should not call
    msg = {PubNubMessageAttribute.TYPE: 'account_partition', PubNubMessageAttribute.PANEL_ID: 1, PubNubMessageAttribute.PARTITION_ID: 2}
    system.handle_pubnub_message(msg)
    assert not handled
    # with data should call
    msg = {PubNubMessageAttribute.TYPE: 'account_partition', PubNubMessageAttribute.PANEL_ID: 1, PubNubMessageAttribute.PARTITION_ID: 2, PubNubMessageAttribute.DATA: {}}
    system.handle_pubnub_message(msg)
    assert handled
