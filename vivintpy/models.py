from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from .const import PanelCredentialAttribute, PanelUpdateAttribute, UserAttribute


class AuthUserSystem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    panid: int = Field(alias="panid")
    id: Optional[int] = Field(None, alias="_id")  # changed to int to match API
    sn: Optional[str] = Field(None, alias="sn")
    ad: Optional[bool] = Field(None, alias="ad")
    par: Optional[List[dict]] = Field(None, alias="par")


class AuthUserUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(alias="_id")
    name: Optional[str] = Field(None, alias="n")
    message_broadcast_channel: Optional[str] = Field(None, alias="mbc")

    @field_validator("systems", mode="before")
    @classmethod
    def _ensure_list_systems(cls, v):
        # coerce single dict into list
        if v is None:
            return []
        if isinstance(v, dict):
            return [v]
        return v

    systems: List[AuthUserSystem] = Field(alias="system")


class AuthUserData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    @field_validator("users", mode="before")
    @classmethod
    def _ensure_list_users(cls, v):
        # coerce single dict into list
        if isinstance(v, dict):
            return [v]
        return v

    users: List[AuthUserUser] = Field(alias="u")
    id_token: Optional[str] = Field(None, alias="id_token")
    is_read_only: bool = Field(alias="is_read_only")
    keep_signed_in: Optional[bool] = Field(None, alias="keep_signed_in")


class SystemBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    panid: int = Field(alias="panid")
    fea: Optional[dict] = Field(None, alias="fea")
    sinfo: Optional[dict] = Field(None, alias="sinfo")
    par: List[dict] = Field(default_factory=list, alias="par")
    users: List[dict] = Field(default_factory=list, alias="u")

    @field_validator("par", "users", mode="before")
    @classmethod
    def _ensure_list_system_body(cls, v):
        # coerce single dict or None into list
        if v is None:
            return []
        if isinstance(v, dict):
            return [v]
        return v


class SystemUserData(BaseModel):
    """Typed payload for a user within a System payload."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(alias=UserAttribute.ID)
    name: str | None = Field(None, alias=UserAttribute.NAME)
    admin: bool | None = Field(None, alias=UserAttribute.ADMIN)
    has_lock_pin: bool | None = Field(None, alias=UserAttribute.HAS_LOCK_PIN)
    has_panel_pin: bool | None = Field(None, alias=UserAttribute.HAS_PANEL_PIN)
    has_pins: bool | None = Field(None, alias=UserAttribute.HAS_PINS)
    remote_access: bool | None = Field(None, alias=UserAttribute.REMOTE_ACCESS)
    registered: bool | None = Field(None, alias=UserAttribute.REGISTERED)

    lock_ids: list[int] = Field(default_factory=list, alias=UserAttribute.LOCK_IDS)

    @field_validator("lock_ids", mode="before")
    @classmethod
    def _ensure_list(cls, v):  # noqa: D401 – simple validator
        if v is None:
            return []
        if isinstance(v, int):
            return [v]
        return v


class SystemData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    system: SystemBody = Field(alias="system")


class PanelCredentialsData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(alias=PanelCredentialAttribute.NAME)
    password: str = Field(alias=PanelCredentialAttribute.PASSWORD)


class PanelUpdateData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    available: bool = Field(alias=PanelUpdateAttribute.AVAILABLE)
    available_version: str = Field(alias=PanelUpdateAttribute.AVAILABLE_VERSION)
    current_version: str = Field(alias=PanelUpdateAttribute.CURRENT_VERSION)
    update_reason: str = Field(alias=PanelUpdateAttribute.UPDATE_REASON)


# -----------------------------------------------------------------------------
# Device-level Pydantic models
# -----------------------------------------------------------------------------
from .const import (
    VivintDeviceAttribute as DevAttr,
    CameraAttribute as CamAttr,
    LockAttribute as LockAttr,
    SwitchAttribute as SwitchAttr,
    ThermostatAttribute as ThermAttr,
    WirelessSensorAttribute as WsAttr,
    AlarmPanelAttribute as PanelAttr,
)


class VivintDeviceData(BaseModel):
    """Common fields present on all Vivint devices."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(alias=DevAttr.ID)
    panel_id: int = Field(alias=DevAttr.PANEL_ID)
    device_type: str = Field(alias=DevAttr.TYPE)

    # Optional/common attributes
    name: str | None = Field(None, alias=DevAttr.NAME)
    state: int | str | bool | None = Field(None, alias=DevAttr.STATE)
    online: bool | None = Field(None, alias=DevAttr.ONLINE)
    # Serial numbers (may be 16- or 32-bit depending on device generation)
    serial_number_32_bit: str | int | None = Field(None, alias=DevAttr.SERIAL_NUMBER_32_BIT)
    serial_number: str | int | None = Field(None, alias=DevAttr.SERIAL_NUMBER)
    battery_level: int | None = Field(None, alias=DevAttr.BATTERY_LEVEL)
    low_battery: bool | None = Field(None, alias=DevAttr.LOW_BATTERY)
    bypassed: int | None = Field(None, alias=DevAttr.BYPASSED)
    tamper: bool | None = Field(None, alias=DevAttr.TAMPER)


class CameraData(VivintDeviceData):
    """Typed payload for camera devices."""

    actual_type: str | None = Field(None, alias=CamAttr.ACTUAL_TYPE)
    camera_direct_available: bool | None = Field(None, alias=CamAttr.CAMERA_DIRECT_AVAILABLE)
    camera_ip_address: str | None = Field(None, alias=CamAttr.CAMERA_IP_ADDRESS)
    camera_ip_port: int | None = Field(None, alias=CamAttr.CAMERA_IP_PORT)
    username: str | None = Field(None, alias=CamAttr.USERNAME)
    password: str | None = Field(None, alias=CamAttr.PASSWORD)
    camera_privacy: bool | None = Field(None, alias=CamAttr.CAMERA_PRIVACY)
    camera_direct_stream_path: str | None = Field(None, alias=CamAttr.CAMERA_DIRECT_STREAM_PATH)
    camera_direct_stream_path_std: str | None = Field(
        None, alias=CamAttr.CAMERA_DIRECT_STREAM_PATH_STANDARD
    )

    # Additional common attributes accessed by Camera class
    capture_clip_on_motion: bool | None = Field(None, alias=CamAttr.CAPTURE_CLIP_ON_MOTION)
    camera_mac: str | None = Field(None, alias=CamAttr.CAMERA_MAC)
    wireless_signal_strength: int | None = Field(None, alias=CamAttr.WIRELESS_SIGNAL_STRENGTH)
    camera_thumbnail_date: str | None = Field(None, alias=CamAttr.CAMERA_THUMBNAIL_DATE)
    deter_on_duty: bool | None = Field(None, alias=CamAttr.DETER_ON_DUTY)
    visitor_detected: bool | None = Field(None, alias=CamAttr.VISITOR_DETECTED)
    ding_dong: bool | None = Field(None, alias=CamAttr.DING_DONG)


class DoorLockData(VivintDeviceData):
    """Typed payload for door lock devices."""

    user_code_list: list[int] = Field(default_factory=list, alias=LockAttr.USER_CODE_LIST)

    @field_validator("user_code_list", mode="before")
    @classmethod
    def _ensure_list(cls, v):  # noqa: D401 – simple validator
        if v is None:
            return []
        if isinstance(v, int):
            return [v]
        return v


class SwitchData(VivintDeviceData):
    """Typed payload for both binary & multilevel switches."""

    value: int | bool | None = Field(None, alias=SwitchAttr.VALUE)


class ThermostatData(VivintDeviceData):
    """Typed payload for thermostat devices (subset of attributes)."""

    actual_type: str | None = Field(None, alias=ThermAttr.ACTUAL_TYPE)
    current_temperature: float | int | None = Field(
        None, alias=ThermAttr.CURRENT_TEMPERATURE
    )
    cool_set_point: float | int | None = Field(None, alias=ThermAttr.COOL_SET_POINT)
    heat_set_point: float | int | None = Field(None, alias=ThermAttr.HEAT_SET_POINT)
    operating_mode: int | None = Field(None, alias=ThermAttr.OPERATING_MODE)
    fan_mode: int | None = Field(None, alias=ThermAttr.FAN_MODE)
    fan_state: int | None = Field(None, alias=ThermAttr.FAN_STATE)
    hold_mode: int | None = Field(None, alias=ThermAttr.HOLD_MODE)
    humidity: int | None = Field(None, alias=ThermAttr.HUMIDITY)
    maximum_temperature: float | int | None = Field(
        None, alias=ThermAttr.MAXIMUM_TEMPERATURE
    )
    minimum_temperature: float | int | None = Field(
        None, alias=ThermAttr.MINIMUM_TEMPERATURE
    )
    operating_state: int | None = Field(None, alias=ThermAttr.OPERATING_STATE)


class GarageDoorData(VivintDeviceData):
    """Typed payload for garage door devices (inherits common attributes)."""

    # No additional fields yet; placeholder for future specific ones
    pass


class AlarmPanelData(VivintDeviceData):
    """Typed payload for alarm panel devices.

    Note: this model sets ``populate_by_name=True`` so that it will accept
    payloads using either the compact Vivint Sky alias keys (e.g. ``panid``,
    ``parid``) *or* the more descriptive field names (e.g. ``panel_id``,
    ``partition_id``) that appear in the test fixtures.
    """

    # Allow population via either field names or their aliases
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

        # Override base required fields to optional because panel payloads sometimes omit them
    # id field may come as "<panid>|<partition>" string in some payloads – accept str.
    id: int | str | None = Field(None, alias=DevAttr.ID)
    device_type: str | None = Field(None, alias=DevAttr.TYPE)

    devices: list[dict] = Field(default_factory=list, alias=PanelAttr.DEVICES)
    mac_address: str | None = Field(None, alias=PanelAttr.MAC_ADDRESS)
    partition_id: int = Field(alias=PanelAttr.PARTITION_ID)
    unregistered: list[dict] = Field(default_factory=list, alias=PanelAttr.UNREGISTERED)

    @field_validator("devices", "unregistered", mode="before")
    @classmethod
    def _ensure_list(cls, v):  # noqa: D401 – simple validator
        if v is None:
            return []
        if isinstance(v, dict):
            return [v]
        return v


class WirelessSensorData(VivintDeviceData):
    """Typed payload for wireless sensor devices."""

    sensor_type: int | None = Field(None, alias=WsAttr.SENSOR_TYPE)
    equipment_code: int | None = Field(None, alias=WsAttr.EQUIPMENT_CODE)
    equipment_type: int | None = Field(None, alias=WsAttr.EQUIPMENT_TYPE)
    firmware_version: str | int | None = Field(
        None, alias=WsAttr.SENSOR_FIRMWARE_VERSION
    )
    hidden: bool | None = Field(None, alias=WsAttr.HIDDEN)
