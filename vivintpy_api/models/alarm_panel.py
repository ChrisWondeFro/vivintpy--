from pydantic import BaseModel
from typing import Optional
from vivintpy.enums import ArmedState


class AlarmPanelResponse(BaseModel):
    """Pydantic model for alarm panel response."""
    id: int
    name: str
    state: ArmedState
    mac_address: Optional[str] = None # mac_address can be None
    manufacturer: str
    model: Optional[str] = None # model can be None
    software_version: Optional[str] = None # software_version can be None

    class Config:
        orm_mode = True
        use_enum_values = True # Ensure enum values are used, not enum objects
