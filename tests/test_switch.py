"""Unit tests for `Switch`, `BinarySwitch` and `MultilevelSwitch`."""

from __future__ import annotations

from typing import Any, List, Tuple, Type

import pytest

from vivintpy.const import VivintDeviceAttribute as Attr, SwitchAttribute as SwAttr
from vivintpy.devices.switch import BinarySwitch, MultilevelSwitch, Switch
from vivintpy.enums import DeviceType

# -----------------------------------------------------------------------------
# Stubs
# -----------------------------------------------------------------------------


class _DummyApi:  # pylint: disable=too-few-public-methods
    """Record invocations for verification."""

    def __init__(self):  # noqa: D401 – simple stub
        self.calls: List[Tuple[Any, ...]] = []

    async def set_switch_state(
        self,
        panel_id: int,
        partition_id: int,
        device_id: int,
        on: bool | None,
        level: int | None,
    ) -> None:  # noqa: D401 – stub
        self.calls.append(
            (
                "set_switch_state",
                panel_id,
                partition_id,
                device_id,
                on,
                level,
            )
        )


class _DummySystem:  # pylint: disable=too-few-public-methods
    def __init__(self, api: _DummyApi):
        self.api = api


class _DummyPanel:  # pylint: disable=too-few-public-methods
    id = 1
    partition_id = 1

    def __init__(self, api: _DummyApi):
        self.system = _DummySystem(api)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _make_payload(binary: bool = True, value: int | bool = 0) -> dict[str, Any]:
    """Return a minimal payload for a switch device."""

    payload = {
        Attr.ID: 401 if binary else 402,
        Attr.PANEL_ID: 1,
        Attr.TYPE: DeviceType.BINARY_SWITCH.value if binary else DeviceType.HSB_SWITCH.value,
        Attr.STATE: bool(value),
        Attr.ONLINE: True,
        SwAttr.VALUE: value,
    }
    return payload


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture(params=[BinarySwitch, MultilevelSwitch])
def switch_and_api(request):
    """Return instantiated switch & api for the given class."""

    cls: Type[Switch] = request.param
    api = _DummyApi()
    panel = _DummyPanel(api)
    payload = _make_payload(binary=cls is BinarySwitch, value=55 if cls is MultilevelSwitch else 1)
    sw = cls(payload, alarm_panel=panel)  # type: ignore[arg-type]
    return sw, api


# -----------------------------------------------------------------------------
# Tests – properties
# -----------------------------------------------------------------------------


def test_switch_properties(switch_and_api):
    sw, _ = switch_and_api

    assert sw.is_online is True
    # Binary vs multilevel expectations
    if isinstance(sw, MultilevelSwitch):
        assert sw.level == 55
        assert sw.is_on is True  # because state=1
    else:  # BinarySwitch
        assert sw.level in (0, 1)  # cast bool to int
        assert sw.is_on is True


# -----------------------------------------------------------------------------
# Tests – async helpers
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_switch_async_helpers(switch_and_api):
    sw, api = switch_and_api

    # Toggle power ------------------------------------------------------------
    await sw.turn_off()
    await sw.turn_on()

    # Multilevel: adjust level -------------------------------------------------
    if isinstance(sw, MultilevelSwitch):
        await sw.set_level(42)

    # Validate API call recording ---------------------------------------------
    method_names = {c[0] for c in api.calls}
    assert method_names == {"set_switch_state"}

    # Expect at least two calls (off, on) and maybe one extra for set_level
    assert len(api.calls) >= 2

    # Spot-check arguments of first call (turn_off) ---------------------------
    first = api.calls[0]
    assert first[0] == "set_switch_state"
    assert first[1:4] == (1, 1, sw.id)
    # on arg False for turn_off, level None
    assert first[4] is False
    assert first[5] is None

    # Spot-check last call -----------------------------------------------------
    last = api.calls[-1]
    if isinstance(sw, MultilevelSwitch):
        # set_level call
        assert last[4] is None
        assert last[5] == 42
    else:
        # turn_on call
        assert last[4] is True
        assert last[5] is None
