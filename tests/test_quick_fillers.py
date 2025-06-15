"""Quick filler tests for small helper functions / paths to boost coverage.

These focus on:
1. `vivintpy.devices.__init__.get_device_class` mapping logic.
2. `vivintpy.system.System.handle_pubnub_message` user-update path.
3. `vivintpy.user.User` convenience/flag helpers and PubNub *add-lock* logic.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from vivintpy.const import (
    PubNubMessageAttribute as MsgAttr,
    SystemAttribute as SysAttr,
    UserAttribute as UserAttr,
)
from vivintpy.devices import get_device_class
from vivintpy.devices.camera import Camera
from vivintpy.devices.door_lock import DoorLock
from vivintpy.devices.garage_door import GarageDoor
from vivintpy.devices.switch import BinarySwitch, MultilevelSwitch
from vivintpy.devices.thermostat import Thermostat
from vivintpy.devices.wireless_sensor import WirelessSensor
from vivintpy.devices import UnknownDevice
from vivintpy.enums import DeviceType
from vivintpy.models import SystemData
from vivintpy.system import System
from vivintpy.user import User, ADD_LOCK


# -----------------------------------------------------------------------------
# 1. get_device_class
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "device_type,expected_cls",
    [
        (DeviceType.CAMERA.value, Camera),
        (DeviceType.DOOR_LOCK.value, DoorLock),
        (DeviceType.GARAGE_DOOR.value, GarageDoor),
        (DeviceType.BINARY_SWITCH.value, BinarySwitch),
        (DeviceType.MULTI_LEVEL_SWITCH.value, MultilevelSwitch),
        (DeviceType.THERMOSTAT.value, Thermostat),
        (DeviceType.WIRELESS_SENSOR.value, WirelessSensor),
        ("non_existent_type", UnknownDevice),
    ],
)
def test_get_device_class_mapping(device_type: str, expected_cls):
    """Ensure `get_device_class` returns the correct implementation class."""

    assert get_device_class(device_type) is expected_cls


# -----------------------------------------------------------------------------
# Helpers – minimal stubs & factories used by the subsequent tests
# -----------------------------------------------------------------------------
class _DummyApi:  # pragma: no cover – tiny test helper
    """Extremely small stub of the real `VivintSkyApi` required by `System`."""

    async def get_system_data(self, panel_id: int):  # noqa: D401 – stub
        # Not used in these tests – present only for interface completeness
        raise RuntimeError("Should not be called in quick-filler tests")


@pytest.fixture()
def minimal_system() -> System:
    """Return a *very* small `System` instance backed by dummy API + data."""

    raw: dict[str, Any] = {
        "system": {
            "panid": 1,
            "fea": {},
            "sinfo": {},
            "par": [
                {
                    "panid": 1,
                    "parid": 1,
                    "s": 0,  # disarmed
                    "d": [],
                    "ureg": [],
                }
            ],
            "u": [
                {
                    UserAttr.ID: 42,
                    UserAttr.NAME: "Original",
                    UserAttr.ADMIN: False,
                    UserAttr.REMOTE_ACCESS: False,
                    UserAttr.HAS_LOCK_PIN: False,
                    UserAttr.HAS_PANEL_PIN: False,
                    UserAttr.HAS_PINS: False,
                    UserAttr.LOCK_IDS: [],
                }
            ],
        }
    }

    model = SystemData.model_validate(raw)
    api = _DummyApi()
    system = System(data=model, api=api, name="Quick-Fill Test SYS", is_admin=True)
    return system


# -----------------------------------------------------------------------------
# 2. System.handle_pubnub_message – user-update flow
# -----------------------------------------------------------------------------

def test_system_pubnub_user_update(minimal_system: System):
    """Verify that a user payload inside an *account_system* PubNub message
    updates the corresponding `User` instance in place.
    """

    user = minimal_system.users[0]
    assert user.name == "Original"

    message = {
        MsgAttr.TYPE: "account_system",
        MsgAttr.OPERATION: "u",
        MsgAttr.DATA: {
            SysAttr.USERS: [
                {
                    UserAttr.ID: 42,
                    UserAttr.NAME: "Updated Name",
                    UserAttr.REMOTE_ACCESS: True,
                }
            ]
        },
    }

    minimal_system.handle_pubnub_message(message)

    # Name and remote-access flag should now reflect the update
    assert user.name == "Updated Name"
    assert user.has_remote_access is True


# -----------------------------------------------------------------------------
# 3. User helpers & ADD_LOCK pubnub handling
# -----------------------------------------------------------------------------

def _make_user(system, lock_ids=None, **overrides):  # helper factory
    data = {
        UserAttr.ID: 7,
        UserAttr.NAME: "Locky",
        UserAttr.ADMIN: True,
        UserAttr.HAS_LOCK_PIN: True,
        UserAttr.HAS_PANEL_PIN: False,
        UserAttr.HAS_PINS: True,
        UserAttr.REMOTE_ACCESS: True,
        UserAttr.LOCK_IDS: lock_ids or [],
        **overrides,
    }
    user = User(data, system)
    return user


def test_user_flag_helpers(minimal_system: System):
    """Exercise boolean helper properties and lock-ids mutation path."""

    user = _make_user(minimal_system, lock_ids=[1, 2])

    assert user.has_lock_pin is True
    assert user.has_panel_pin is False
    assert user.has_pins is True
    assert user.has_remote_access is True
    assert user.is_admin is True
    assert user.is_registered is False  # default when not set

    # Simulate PubNub *add-lock* message – should append id 99 to lock_ids.
    add_lock_message = {ADD_LOCK: 99}
    user.handle_pubnub_message(add_lock_message)
    assert 99 in user.lock_ids
