"""Tests for `vivintpy.zjs_device_config_db.get_zwave_device_info`."""

from __future__ import annotations

from typing import Any

import importlib

import pytest

MODULE_PATH = "vivintpy.zjs_device_config_db"


@pytest.fixture()
def fake_db(monkeypatch) -> dict[str, Any]:  # noqa: D401 – fixture
    """Inject a small, deterministic DB mapping into the module under test."""

    mapping = {
        "0x0123:0x4567:0x89ab": {
            "manufacturer": "Acme",
            "model": "FooSensor",
        }
    }

    # Import (or reload) module so we can patch its global.
    mod = importlib.import_module(MODULE_PATH)
    monkeypatch.setattr(mod, "ZJS_DEVICE_DB", mapping, raising=True)

    return mapping





@pytest.mark.parametrize("ids, expected", [((0x0123, 0x4567, 0x89AB), True), ((0x9999, 0x9999, 0x9999), False)])
def test_get_zwave_device_info(fake_db, ids, expected):
    mod = importlib.import_module(MODULE_PATH)
    manufacturer_id, product_type, product_id = ids

    result = mod.get_zwave_device_info(manufacturer_id, product_type, product_id)

    if expected:
        assert result == fake_db["0x0123:0x4567:0x89ab"]
    else:
        assert result == {}


def test_handles_none_inputs(fake_db):
    mod = importlib.import_module(MODULE_PATH)

    # If any component is None, we expect empty dict (formatting would raise otherwise)
    assert mod.get_zwave_device_info(None, 0x4567, 0x89AB) == {}
    assert mod.get_zwave_device_info(0x0123, None, 0x89AB) == {}
    assert mod.get_zwave_device_info(0x0123, 0x4567, None) == {}
