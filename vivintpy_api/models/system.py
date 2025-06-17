from __future__ import annotations

from pydantic import BaseModel, Field

from vivintpy.enums import ArmedState

from .device import DeviceResponse


class SystemResponse(BaseModel):
    """Pydantic model for a Vivint system."""

    id: int = Field(..., description="System ID")
    name: str = Field(..., description="System name")

    class Config:
        from_attributes = True


class AlarmPanelResponse(DeviceResponse):
    """Pydantic model for an Alarm Panel device."""

    state: ArmedState = Field(..., description="Current arming state of the panel.")
    can_arm_stay: bool = Field(
        ..., description="Indicates if the panel can be armed in 'stay' mode."
    )
    can_arm_away: bool = Field(
        ..., description="Indicates if the panel can be armed in 'away' mode."
    )
