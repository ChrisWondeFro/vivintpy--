"""Module that implements the Camera class."""

from __future__ import annotations

import logging
from datetime import datetime
from enum import IntEnum
from typing import cast

from ..const import CameraAttribute as Attribute
from ..const import PanelCredentialAttribute
from ..models import CameraData
from . import VivintDevice
from .alarm_panel import AlarmPanel

_LOGGER = logging.getLogger(__name__)

# Some Vivint supported cameras may be connected directly to your local network
# and the Vivint API reports these as having direct access availiable (cda).
# Ping cameras (alpha_cs6022_camera_device) can be setup to connect to your own
# Wi-Fi via a complicated process involving removing and resetting the camera,
# initiating WPS on your Wi-Fi and the Ping camera, and then adding a new camera
# from the panel within a limited timeframe. The Ping camera, however, seems to
# still have a VPN connection with the panel that prevents direct access except
# on very rare occasions. As such, we want to skip this model from direct access.
SKIP_DIRECT = ["alpha_cs6022_camera_device"]

DOORBELL_DING = "doorbell_ding"
MOTION_DETECTED = "motion_detected"
THUMBNAIL_READY = "thumbnail_ready"
VIDEO_READY = "video_ready"

CAMERA_INFO_MAP = {
    "alpha_cs6022_camera_device": ("Vivint", "Indoor Camera (CS6022)"),
    "camera_device": (None, "Generic Camera Device"),
    "hd100_camera_device": ("LG", "HD 100 Camera"),
    "lgit_hd110_camera_device": ("LG", "HD 110 Camera"),
    "panel_camera_device": (None, "Panel Camera"),
    "touch_link_camera_device": (None, "Panel Camera"),
    "vivint_dbc300_camera_device": ("Vivint", "Doorbell Camera Pro Gen 1 (DBC300)"),
    "vivint_dbc301_camera_device": ("Vivint", "Doorbell Camera Pro Gen 1 (DBC301)"),
    "vivint_dbc350_camera_device": ("Vivint", "Doorbell Camera Pro Gen 2 (DBC350)"),
    "vivint_idc350_camera_device": ("Vivint", "Indoor Camera Pro (IDC350)"),
    "vivint_odc300_camera_device": ("Vivint", "Outdoor Camera Pro Gen 1 (ODC300)"),
    "vivint_odc350_camera_device": ("Vivint", "Outdoor Camera Pro Gen 2 (ODC350)"),
    "vivotek_520ir_camera_device": ("Vivotek", "Fixed Camera (V520IR)"),
    "vivotek_620pt_camera_device": ("Vivotek", "Pan and Tilt Camera (V620PT)"),
    "vivotek_720_camera_device": ("Vivotek", "Outdoor Camera (V720)"),
    "vivotek_720w_camera_device": ("Vivotek", "Wireless Outdoor Camera (V720W)"),
    "vivotek_721w_camera_device": ("Vivotek", "Wireless Outdoor Camera (V721W)"),
    "vivotek_cc8130_camera_device": ("Vivotek", "Dome Camera (CC8130)"),
    "vivotek_db8331w_camera_device": ("Vivotek", "Doorbell Camera (DB8331W)"),
    "vivotek_db8332_camera_device": ("Vivotek", "Doorbell Camera v2 (DB8332)"),
    "vivotek_db8332s1_camera_device": ("Vivotek", "Doorbell Camera 2S1 (DB8332S1)"),
    "vivotek_db8332sw_camera_device": ("Vivotek", "Doorbell Camera v2s (DB8332SW)"),
    "vivotek_fd8134v_camera_device": ("Vivotek", "Dome Camera (FD8134V)"),
    "vivotek_fd8151v_camera_device": ("Vivotek", "Dome Camera (FD8151V)"),
    "vivotek_hd400w_camera_device": ("Vivotek", "Outdoor Camera v2 (HD400W)"),
    "vivotek_hdp450_camera_device": ("Vivotek", "Outdoor Camera (HDP450)"),
}


class RtspUrlType(IntEnum):
    """Helper class for getting a specific RTSP URL.

    DIRECT - Local access through your router
    PANEL - Local access through your panel
    EXTERNAL - External access through the Vivint cloud
    """

    LOCAL = 0
    PANEL = 1
    EXTERNAL = 2


class Camera(VivintDevice):
    """Represents a Vivint camera."""

    alarm_panel: AlarmPanel

    def __init__(self, data: dict, alarm_panel: AlarmPanel):
        """Initialize a camera."""
        super().__init__(data, alarm_panel)
        self._data_model: CameraData = CameraData.model_validate(data)
        actual_type = self._data_model.actual_type or data.get(Attribute.ACTUAL_TYPE)
        if camera_info := CAMERA_INFO_MAP.get(actual_type):
            self._manufacturer = camera_info[0]
            self._model = camera_info[1]
        else:
            manufacturer_and_model = (actual_type or "").split("_")[0:2]
            self._manufacturer = manufacturer_and_model[0].title() if manufacturer_and_model else None
            self._model = manufacturer_and_model[1].upper() if len(manufacturer_and_model) > 1 else None

    @property
    def serial_number(self) -> str:
        """Return the camera's mac address as the serial number."""
        return self.mac_address

    @property
    def software_version(self) -> str | None:
        """Return the camera's software version as a string.

        Cameras report `software_version` as either an int or str.  Convert
        any numeric value to `str` to satisfy the FastAPI `DeviceResponse`
        validation requirement.
        """
        sv = self.data.get(Attribute.SOFTWARE_VERSION)
        return str(sv) if sv not in (None, "") else None

    @property
    def capture_clip_on_motion(self) -> bool:
        """Return True if capture clip on motion is active."""
        return bool(self._data_model.capture_clip_on_motion)

    @property
    def extend_chime_enabled(self) -> bool:
        """Return True if used as doorbell chime extender."""
        return cast(bool, self.data.get(Attribute.CAMERA_EXTEND_CHIME_ENABLED, False))

    @property
    def ip_address(self) -> str:
        """Camera's IP address."""
        return str(self._data_model.camera_ip_address) if self._data_model.camera_ip_address else ""

    @property
    def is_in_deter_mode(self) -> bool:
        """Return True if deter mode is active."""
        return bool(self._data_model.deter_on_duty)

    @property
    def mac_address(self) -> str:
        """Camera's MAC Address."""
        return str(self._data_model.camera_mac) if self._data_model.camera_mac else ""

    @property
    def is_in_privacy_mode(self) -> bool:
        """Return True if privacy mode is active."""
        return bool(self._data_model.camera_privacy)

    @property
    def is_online(self) -> bool:
        """Return True if camera is online."""
        return bool(self._data_model.online)

    @property
    def wireless_signal_strength(self) -> int:
        """Camera's wireless signal strength."""
        return int(self._data_model.wireless_signal_strength or 0)

    async def request_thumbnail(self) -> None:
        """Request a new thumbnail for the camera."""
        await self.api.request_camera_thumbnail(
            self.alarm_panel.id, self.alarm_panel.partition_id, self.id
        )

    # ------------------------------------------------------------------
    # Alias: request_snapshot
    # ------------------------------------------------------------------

    async def request_snapshot(self) -> None:  # pragma: no cover – thin alias
        """Request a fresh snapshot from the camera.

        This is an alias for :py:meth:`request_thumbnail` kept for backward
        compatibility with code paths and documentation that still refer to
        *snapshot* instead of *thumbnail*.
        """
        await self.request_thumbnail()

    async def get_thumbnail_url(self) -> str | None:
        """Return the latest camera thumbnail URL."""
        # Sometimes this date field comes back with a "Z" at the end
        # and sometimes it doesn't, so let's just safely remove it.
        camera_thumbnail_raw = (self._data_model.camera_thumbnail_date or "").replace("Z", "")
        camera_thumbnail_date = datetime.strptime(
            camera_thumbnail_raw,
            "%Y-%m-%dT%H:%M:%S.%f",
        )
        thumbnail_timestamp = int(camera_thumbnail_date.timestamp() * 1000)

        return await self.api.get_camera_thumbnail_url(
            self.alarm_panel.id,
            self.alarm_panel.partition_id,
            self.id,
            thumbnail_timestamp,
        )

    def get_rtsp_access_url(
        self, access_type: RtspUrlType = RtspUrlType.LOCAL, hd: bool = True
    ) -> str | None:
        """Return the rtsp URL for the camera."""
        if access_type == RtspUrlType.LOCAL:
            return (
                f"rtsp://{self.data[Attribute.USERNAME]}:{self.data[Attribute.PASSWORD]}@{self.ip_address}:{self.data[Attribute.CAMERA_IP_PORT]}/{self.data[Attribute.CAMERA_DIRECT_STREAM_PATH if hd else Attribute.CAMERA_DIRECT_STREAM_PATH_STANDARD]}"
                if self.data[Attribute.CAMERA_DIRECT_AVAILABLE]
                and self.data.get(Attribute.ACTUAL_TYPE) not in SKIP_DIRECT
                else None
            )
        if not (credentials := self.alarm_panel.credentials):
            _LOGGER.error(
                "You must call `get_panel_credentials` before getting the RTSP url via the panel or Vivint cloud."
            )
            return None
        _type = "i" if access_type == RtspUrlType.PANEL else "e"
        url = self.data[f"c{_type}u{'' if hd else 's'}"][0]
        return f"{url[:7]}{credentials.name}:{credentials.password}@{url[7:]}"

    async def get_rtsp_url(
        self,
        internal: bool = False,
        hd: bool = False,  # pylint: disable=invalid-name
    ) -> str | None:
        """Return the rtsp URL for the camera."""
        await self.alarm_panel.get_panel_credentials()
        access_type = RtspUrlType.PANEL if internal else RtspUrlType.EXTERNAL
        return self.get_rtsp_access_url(access_type, hd)

    async def get_direct_rtsp_url(
        self,
        hd: bool = False,  # pylint: disable=invalid-name
    ) -> str | None:
        """Return the direct rtsp url for this camera, in HD if requested, if any."""
        return self.get_rtsp_access_url(RtspUrlType.LOCAL, hd)

    async def reboot(self) -> None:
        """Reboot the camera."""
        await self.api.reboot_camera(
            self.alarm_panel.id, self.id, self.device_type.value
        )

    async def set_as_doorbell_chime_extender(self, state: bool) -> None:
        """Set use as doorbell chime extender."""
        await self.api.set_camera_as_doorbell_chime_extender(
            self.alarm_panel.id, self.id, state
        )

    async def set_privacy_mode(self, state: bool) -> None:
        """Set privacy mode."""
        if not self.alarm_panel.system.is_admin:
            _LOGGER.warning(
                "%s - Cannot set privacy mode as user is not an admin", self.name
            )
            return
        await self.api.set_camera_privacy_mode(self.alarm_panel.id, self.id, state)

    async def speak(self, audio: bytes, mime_type: str | None = None) -> None:
        """Play an audio clip through the camera speaker.

        Parameters
        ----------
        audio: bytes
            Raw audio payload (e.g. WAV/MP3). The clip should be short (\<= 10 s)
            to avoid request-size limits imposed by Vivint.
        mime_type: str | None, optional
            Content-Type to send. Defaults to ``audio/wav`` which is accepted by
            all Vivint camera models tested. Set this if you provide MP3 (e.g.
            ``audio/mpeg``).

        Raises
        ------
        VivintSkyApiError
            If the underlying HTTP call fails for any reason.
        """
        await self.api.upload_camera_audio(
            self.alarm_panel.id,
            self.alarm_panel.partition_id,
            self.id,
            audio,
            mime_type=mime_type,
        )

    async def set_deter_mode(self, state: bool) -> None:
        """Set deter mode."""
        if not self.alarm_panel.system.is_admin:
            _LOGGER.warning(
                "%s - Cannot set deter mode as user is not an admin", self.name
            )
            return
        await self.api.set_camera_deter_mode(self.alarm_panel.id, self.id, state)

    def handle_pubnub_message(self, message: dict) -> None:
        """Handle a pubnub message addressed to this camera."""
        super().handle_pubnub_message(message)

        event = None

        if message.get(Attribute.CAMERA_THUMBNAIL_DATE):
            event = THUMBNAIL_READY
        elif message.get(Attribute.DING_DONG):
            event = DOORBELL_DING
        elif message.keys() == set([Attribute.ID, Attribute.TYPE]):
            event = VIDEO_READY
        elif message.get(Attribute.VISITOR_DETECTED) or message.keys() in [
            set([Attribute.ID, Attribute.ACTUAL_TYPE, Attribute.STATE]),
            set([Attribute.ID, Attribute.DETER_ON_DUTY, Attribute.TYPE]),
        ]:
            event = MOTION_DETECTED

        if event is not None:
            self.emit(event, {"message": message})

        _LOGGER.debug("Message received by %s: %s", self.name, message)
