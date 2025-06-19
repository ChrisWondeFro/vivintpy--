from __future__ import annotations

from pydantic import BaseModel, Field

from vivintpy.enums import (
    DeviceType,
    FanMode,
    GarageDoorState,
    OperatingMode,
    SensorType,
)


class DeviceResponse(BaseModel):
    """Pydantic model for representing a generic device in API responses."""

    id: int = Field(..., description="Device ID")
    name: str = Field(..., description="Device name")
    device_type: DeviceType = Field(
        ..., 
        validation_alias="device_type",
        serialization_alias="type",
        description="Type of the device",
    )
    manufacturer: str | None = Field(None, description="Device manufacturer")
    model: str | None = Field(None, description="Device model")
    serial_number: str | None = Field(None, description="Device serial number")
    software_version: str | None = Field(None, description="Device software version")
    firmware_version: str | None = Field(None, description="Device firmware version")
    online: bool = Field(..., description="Device online status")
    low_battery: bool | None = Field(None, description="Device low battery status (if applicable)")
    battery_level: int | None = Field(None, description="Device battery level (if applicable)")

    class Config:
        from_attributes = True
        populate_by_name = True


class BypassTamperDeviceResponse(DeviceResponse):
    """A device that can be bypassed and/or tampered."""

    is_bypassed: bool = Field(..., description="True if the device is bypassed.")
    is_tampered: bool = Field(..., description="True if the device is tampered.")


class DoorLockResponse(BypassTamperDeviceResponse):
    """Pydantic model for Door Lock devices."""

    is_locked: bool = Field(..., description="True if the lock is locked, False if unlocked.")


class GarageDoorResponse(DeviceResponse):
    """Pydantic model for Garage Door devices."""

    state: GarageDoorState = Field(..., description="Current state of the garage door.")


class SwitchResponse(DeviceResponse):
    """Base Pydantic model for Switch devices."""

    is_on: bool = Field(..., description="True if the switch is on.")


class BinarySwitchResponse(SwitchResponse):
    """Pydantic model for a binary (on/off) switch."""

    pass


class MultilevelSwitchResponse(SwitchResponse):
    """Pydantic model for a multilevel (dimmer) switch."""

    level: int = Field(..., description="The brightness level of the switch (1-100).")


class ThermostatResponse(DeviceResponse):
    """Pydantic model for Thermostat devices."""

    fan_mode: FanMode = Field(..., description="Fan mode of the thermostat.")
    operating_mode: OperatingMode = Field(..., description="Current operating mode.")
    cool_setpoint: float = Field(..., description="Cooling setpoint temperature.")
    heat_setpoint: float = Field(..., description="Heating setpoint temperature.")
    temperature: float = Field(..., description="Current temperature.")
    heating: bool = Field(..., description="True if the thermostat is currently heating.")
    cooling: bool = Field(..., description="True if the thermostat is currently cooling.")
    fan: bool = Field(..., description="True if the fan is currently active.")


class CameraResponse(DeviceResponse):
    """Pydantic model for Camera devices."""

    is_in_privacy_mode: bool = Field(..., description="True if the camera is in privacy mode.")
    thumbnail_url: str | None = Field(None, description="URL for a recent thumbnail image.")


class WirelessSensorResponse(BypassTamperDeviceResponse):
    """Pydantic model for Wireless Sensor devices."""

    is_on: bool = Field(
        ...,
        description="Current state of the sensor (e.g., True if a contact sensor is open, or motion is detected).",
    )
    sensor_type: SensorType = Field(..., description="Type of the wireless sensor.") 


# This can be used as a fallback or if a device doesn't match a more specific response model.
GenericDeviceResponse = DeviceResponse
