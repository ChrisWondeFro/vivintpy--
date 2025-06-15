"""Focused tests for vivintpy.devices.camera async helpers."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from vivintpy.devices.camera import Camera


class DummyApi:
    async def get_camera_thumbnail_url(
        self,
        panel_id: int,
        partition_id: int,
        device_id: int,
        timestamp: str | None,
    ) -> str:  # noqa: D401
        # Return a predictable URL containing identifiers
        return f"https://example.test/{panel_id}/{partition_id}/{device_id}/{timestamp or 'none'}"


class DummyAccount:
    def __init__(self) -> None:
        self.api = DummyApi()


class DummySystem:
    is_admin = True

    def __init__(self) -> None:
        self.api = DummyApi()
        self.account = DummyAccount()



class DummyAlarmPanel:
    id = 1
    partition_id = 0

    def __init__(self) -> None:
        self.system = DummySystem()
        # simple creds object with name/password attributes
        self._creds = SimpleNamespace(name="user", password="pass")

    @property
    def credentials(self):  # noqa: D401
        return self._creds

    async def get_panel_credentials(self):  # noqa: D401
        return self._creds


@pytest.fixture(name="camera")
def camera_fixture() -> Camera:  # type: ignore[return-value]
    # Minimal camera payload covering attributes used in tests
    data = {
        "_id": 27,  # alias: id
        "panid": 1,  # alias: panel_id
        "t": "camera_device",  # alias: type
        "un": "camuser",  # alias: username
        "pswd": "campass",  # alias: password
        "caip": "192.168.1.10",  # alias: camera_ip_address
        "cap": 7447,  # alias: camera_ip_port
        "cda": False,  # alias: camera_direct_available
        # external standard rtsp url list
        "ceus": [
            "rtsp://192.0.2.1/stream"
        ],
        "ctd": "2025-01-01T00:00:00.000Z",  # alias: camera_thumbnail_date
    }
    alarm_panel = DummyAlarmPanel()
    cam = Camera(data, alarm_panel)  # type: ignore[arg-type]
    # Inject DummyApi (bypasses internals that pull from nested account)
    cam._api = alarm_panel.system.api  # type: ignore[attr-defined,protected-access]
    # Restore external-standard URL list lost during model validation
    cam.data["ceus"] = ["rtsp://192.0.2.1/stream"]
    return cam


@pytest.mark.asyncio
async def test_get_thumbnail_url(camera: Camera) -> None:
    url = await camera.get_thumbnail_url()
    assert url.startswith("https://example.test/1/0/27/")
    # Ensure last path component is a digits-only timestamp in ms
    timestamp_part = url.rsplit("/", 1)[-1]
    assert timestamp_part.isdigit()


@pytest.mark.asyncio
async def test_get_rtsp_url_external_standard(camera: Camera) -> None:
    # Uses external (internal=False) & standard (hd=False)
    rtsp = await camera.get_rtsp_url(internal=False, hd=False)
    # Should inject credentials into URL
    assert rtsp.startswith("rtsp://user:pass@")
    assert "/stream" in rtsp
