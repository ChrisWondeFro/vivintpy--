import pytest

from vivintpy.models import PanelCredentialsData, PanelUpdateData, SystemBody
from vivintpy.const import PanelCredentialAttribute, PanelUpdateAttribute


def test_panel_credentials_data_roundtrip():
    raw = {
        PanelCredentialAttribute.NAME: "user123",
        PanelCredentialAttribute.PASSWORD: "pass123",
    }
    model = PanelCredentialsData.model_validate(raw)
    dumped = model.model_dump(by_alias=True)
    assert dumped == raw


def test_panel_update_data_roundtrip():
    raw = {
        PanelUpdateAttribute.AVAILABLE: True,
        PanelUpdateAttribute.AVAILABLE_VERSION: "2.0.1",
        PanelUpdateAttribute.CURRENT_VERSION: "2.0.0",
        PanelUpdateAttribute.UPDATE_REASON: "Maintenance",
    }
    model = PanelUpdateData.model_validate(raw)
    dumped = model.model_dump(by_alias=True)
    assert dumped == raw


def test_systembody_validators_coerce_to_list():
    raw = {"panid": 1, "fea": {}, "sinfo": {}, "par": {"key": "value"}, "u": {"id": 2}}
    body = SystemBody.model_validate(raw)
    assert isinstance(body.par, list) and len(body.par) == 1
    assert isinstance(body.users, list) and len(body.users) == 1


def test_systembody_empty_defaults():
    raw = {"panid": 2}
    body = SystemBody.model_validate(raw)
    assert body.par == []
    assert body.users == []
