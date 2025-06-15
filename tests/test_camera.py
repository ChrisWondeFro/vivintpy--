"""Unit tests for the `Camera` device class."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, List

import pytest

from vivintpy.const import CameraAttribute as CamAttr
from vivintpy.enums import DeviceType
from vivintpy.models import PanelCredentialsData
from vivintpy.devices.camera import (
    Camera,
    DOORBELL_DING,
    MOTION_DETECTED,
    THUMBNAIL_READY,
    VIDEO_READY,
    RtspUrlType,
)


# -----------------------------------------------------------------------------
# Stubs
# -----------------------------------------------------------------------------


class _DummyApi:  # pylint: disable=too-few-public-methods
    """A very small stub of the real ``VivintSkyApi``.

    It simply records which method was invoked together with positional args so
    that tests can assert helper functions proxy to the API correctly.
    """

    def __init__(self) -> None:  # noqa: D401 – simple stub
        self.calls: List[tuple[str, Any]] = []

    # --- Camera helpers ------------------------------------------------------
    async def request_camera_thumbnail(self, panel_id: int, partition_id: int, device_id: int) -> None:  # noqa: D401 – stub
        self.calls.append(("request_camera_thumbnail", panel_id, partition_id, device_id))

    async def get_camera_thumbnail_url(
        self,
        panel_id: int,
        partition_id: int,
        device_id: int,
        timestamp: int,
    ) -> str:  # noqa: D401 – stub
        self.calls.append(("get_camera_thumbnail_url", panel_id, partition_id, device_id, timestamp))
        return f"https://dummy/{device_id}/{timestamp}"

    async def reboot_camera(self, panel_id: int, device_id: int, device_type: str) -> None:  # noqa: D401 – stub
        self.calls.append(("reboot_camera", panel_id, device_id, device_type))

    async def set_camera_as_doorbell_chime_extender(self, panel_id: int, device_id: int, state: bool) -> None:  # noqa: D401 – stub
        self.calls.append(("set_camera_as_doorbell_chime_extender", panel_id, device_id, state))

    async def set_camera_privacy_mode(self, panel_id: int, device_id: int, state: bool) -> None:  # noqa: D401 – stub
        self.calls.append(("set_camera_privacy_mode", panel_id, device_id, state))

    async def set_camera_deter_mode(self, panel_id: int, device_id: int, state: bool) -> None:  # noqa: D401 – stub
        self.calls.append(("set_camera_deter_mode", panel_id, device_id, state))

    # --- Panel helpers -------------------------------------------------------
    async def get_panel_credentials(self, panel_id: int):  # noqa: D401 – stub
        self.calls.append(("get_panel_credentials", panel_id))
        raw = {"n": "paneluser", "pswd": "panelpass"}
        return PanelCredentialsData.model_validate(raw)


class _DummySystem:  # pylint: disable=too-few-public-methods
    """Bare-minimum ``System`` replacement exposing ``api`` & admin flag."""

    def __init__(self, api: _DummyApi, is_admin: bool = True):
        self.api = api
        self.is_admin = is_admin


class _DummyPanel:  # pylint: disable=too-few-public-methods
    """Lightweight stand-in for an ``AlarmPanel`` instance."""

    id = 1
    partition_id = 1

    def __init__(self, api: _DummyApi):
        self.system = _DummySystem(api)
        self.credentials: PanelCredentialsData | None = None

    async def get_panel_credentials(self, refresh: bool = False):  # noqa: D401 – stub
        self.credentials = await self.system.api.get_panel_credentials(self.id)
        return self.credentials


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _make_camera_payload() -> dict[str, Any]:  # noqa: D401 – helper
    """Return a minimal but *functional* raw payload for a camera."""

    thumbnail_dt = datetime.utcnow().replace(microsecond=0)

    return {
        CamAttr.ID: 201,
        CamAttr.PANEL_ID: 1,
        CamAttr.TYPE: DeviceType.CAMERA.value,
        CamAttr.ACTUAL_TYPE: "vivint_odc350_camera_device",
        CamAttr.CAMERA_DIRECT_AVAILABLE: True,
        CamAttr.CAMERA_DIRECT_STREAM_PATH: "stream_hd",
        CamAttr.CAMERA_DIRECT_STREAM_PATH_STANDARD: "stream_sd",
        CamAttr.USERNAME: "user",
        CamAttr.PASSWORD: "pass",
        CamAttr.CAMERA_IP_ADDRESS: "192.168.1.50",
        CamAttr.CAMERA_IP_PORT: 554,
        CamAttr.CAPTURE_CLIP_ON_MOTION: True,
        CamAttr.CAMERA_MAC: "AA:BB:CC:DD:EE:FF",
        CamAttr.DETER_ON_DUTY: False,
        CamAttr.CAMERA_PRIVACY: False,
        CamAttr.ONLINE: True,
        CamAttr.WIRELESS_SIGNAL_STRENGTH: 78,
        CamAttr.CAMERA_THUMBNAIL_DATE: thumbnail_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        # RTSP URL templates (panel/internal = "ciu[s]", external = "ceu[s]")
        "ceus": ["rtsp://externalhost/live"],
    }


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture()
def camera_and_api():
    """Return a `(Camera, _DummyApi)` tuple fully wired."""

    api = _DummyApi()
    panel = _DummyPanel(api)
    cam_raw = _make_camera_payload()
    camera = Camera(cam_raw, alarm_panel=panel)
    # Pydantic model dump strips unknown keys such as "ceus"; restore it on raw data
    camera.update_data({"ceus": ["rtsp://externalhost/live"]})
    return camera, api


# -----------------------------------------------------------------------------
# Tests – basic properties & helpers
# -----------------------------------------------------------------------------


def test_basic_properties(camera_and_api):
    camera, _ = camera_and_api

    assert camera.is_online is True
    assert camera.ip_address == "192.168.1.50"
    assert camera.mac_address == "AA:BB:CC:DD:EE:FF"
    assert camera.capture_clip_on_motion is True
    assert camera.wireless_signal_strength == 78


@pytest.mark.asyncio
async def test_async_helpers(camera_and_api):
    camera, api = camera_and_api

    # Camera-specific helpers --------------------------------------------------
    await camera.request_thumbnail()
    await camera.get_thumbnail_url()
    await camera.reboot()
    await camera.set_as_doorbell_chime_extender(True)
    await camera.set_privacy_mode(True)
    await camera.set_deter_mode(True)
    # Also fetch an RTSP URL to trigger panel credential retrieval
    await camera.get_rtsp_url(internal=False, hd=False)

    # Ensure *some* of the API methods above were invoked
    method_names = {c[0] for c in api.calls}
    expected = {
        "request_camera_thumbnail",
        "get_camera_thumbnail_url",
        "reboot_camera",
        "set_camera_as_doorbell_chime_extender",
        "set_camera_privacy_mode",
        "set_camera_deter_mode",
        "get_panel_credentials",
    }
    assert expected.issubset(method_names)


@pytest.mark.asyncio
async def test_rtsp_url_helpers(camera_and_api):
    camera, _ = camera_and_api

    # Direct/local (should embed user/pass directly)
    direct = await camera.get_direct_rtsp_url(hd=True)
    assert direct == "rtsp://user:pass@192.168.1.50:554/stream_hd"

    # External/cloud (should embed *panel* credentials)
    external = await camera.get_rtsp_url(internal=False, hd=False)
    assert external and external.startswith("rtsp://paneluser:panelpass@")


def test_pubnub_event_routing(camera_and_api):
    camera, _ = camera_and_api

    # Register listeners ------------------------------------------------------
    events: dict[str, bool] = {}

    camera.on(THUMBNAIL_READY, lambda _d: events.setdefault(THUMBNAIL_READY, True))
    camera.on(VIDEO_READY, lambda _d: events.setdefault(VIDEO_READY, True))
    camera.on(MOTION_DETECTED, lambda _d: events.setdefault(MOTION_DETECTED, True))

    # 1. Thumbnail ready ------------------------------------------------------
    camera.handle_pubnub_message({CamAttr.CAMERA_THUMBNAIL_DATE: "2025-01-01T00:00:00.000Z"})
    # 2. Video ready ----------------------------------------------------------
    camera.handle_pubnub_message({CamAttr.ID: 201, CamAttr.TYPE: DeviceType.CAMERA.value})
    # 3. Motion (variant 1) ---------------------------------------------------
    camera.handle_pubnub_message({CamAttr.ID: 201, CamAttr.ACTUAL_TYPE: "foo", CamAttr.STATE: 1})

    assert events == {
        THUMBNAIL_READY: True,
        VIDEO_READY: True,
        MOTION_DETECTED: True,
    }

