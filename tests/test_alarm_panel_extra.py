"""Additional AlarmPanel tests covering admin-check branches and software update helpers."""

from __future__ import annotations

from typing import Any

import pytest

from vivintpy.const import AlarmPanelAttribute as Attr
from vivintpy.enums import ArmedState
from vivintpy.exceptions import VivintSkyApiError
from vivintpy.models import SystemData
from vivintpy.system import System


class DummyApi:  # pylint: disable=too-few-public-methods
    """Stub that records calls and simulates failures."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._system_model: SystemData | None = None

    # Called by AlarmPanel.update_software when is_admin == True
    async def update_panel_software(self, _panel_id: int) -> None:  # noqa: D401 – stub
        self.calls.append("update_panel_software")
        raise VivintSkyApiError("fail")

    async def reboot_panel(self, _panel_id: int) -> None:  # noqa: D401 – stub
        self.calls.append("reboot_panel")

    # Not used but AlarmPanel accesses it when refreshing devices
    async def get_device_data(self, *_args, **_kwargs):  # noqa: D401 – stub
        raise VivintSkyApiError("not implemented")


@pytest.fixture()
def non_admin_panel():
    """Return an AlarmPanel instance attached to a non-admin system."""

    raw: dict[str, Any] = {
        "system": {
            "panid": 22,
            "par": [
                {
                    "panid": 22,
                    "parid": 1,
                    "s": ArmedState.DISARMED,
                    Attr.DEVICES: [],
                    Attr.UNREGISTERED: [],
                }
            ],
            "fea": {},
            "sinfo": {},
            "u": [],
        }
    }
    model = SystemData.model_validate(raw)
    api = DummyApi()
    api._system_model = model  # type: ignore[attr-defined]
    system = System(data=model, api=api, name="NA", is_admin=False)
    panel = system.alarm_panels[0]
    return panel, api


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_software_update_details_fallback(non_admin_panel):
    panel, _ = non_admin_panel

    details = await panel.get_software_update_details()

    # When user is not admin, `available` flag should be False as it returns fallback.
    assert details.available is False
    assert details.available_version == ""


@pytest.mark.asyncio
async def test_update_software_non_admin(non_admin_panel):
    panel, api = non_admin_panel

    assert await panel.update_software() is False
    # Because is_admin is False, the API method should *not* be called.
    assert "update_panel_software" not in api.calls


@pytest.mark.asyncio
async def test_reboot_non_admin(non_admin_panel):
    panel, api = non_admin_panel

    await panel.reboot()
    # Because is_admin is False, reboot should be a no-op.
    assert "reboot_panel" not in api.calls
