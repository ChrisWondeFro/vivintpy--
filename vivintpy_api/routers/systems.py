from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List
from pydantic import BaseModel # Added for request body models

from .. import deps
from ..models.system import SystemResponse # Import the Pydantic model for system responses
from ..models.alarm_panel import AlarmPanelResponse # Import the Pydantic model for alarm panel responses
from vivintpy import Account, System 
from vivintpy.devices.alarm_panel import AlarmPanel
from vivintpy.enums import ArmedState, EmergencyType
from vivintpy.exceptions import VivintSkyApiError # For handling API call errors

router = APIRouter(
    prefix="/systems",
    tags=["Systems & Panels"],
    dependencies=[Depends(deps.get_current_active_user)], # Secure all endpoints in this router
)

# --- Pydantic models for request bodies ---
class DisarmPayload(BaseModel):
    pin: str

class TriggerEmergencyPayload(BaseModel):
    emergency_type: EmergencyType



# Helper
def _get_system(account: Account, system_id: int) -> System | None:
    """Return the System with matching ID from the account or None."""
    for sys in account.systems:
        if sys.id == system_id:
            return sys
    return None

# --- System Endpoints ---
@router.get("/", response_model=List[SystemResponse])
async def list_systems(
    account: Account = Depends(deps.get_user_account)
):
    """
    List all systems associated with the configured Vivint account.
    The vivintpy.Account object should have its `systems` attribute populated after `connect()`.
    """
    if not account.systems:
        # This could mean systems haven't loaded or there are none.
        # connect() should populate this.
        return []
    # Convert vivintpy.System objects to SystemResponse objects
    return [SystemResponse(id=sys.id, name=sys.name) for sys in account.systems]

@router.get("/{system_id}", response_model=SystemResponse)
async def get_system_details(
    system_id: int,
    account: Account = Depends(deps.get_user_account)
):
    """
    Get detailed information for a specific system by its ID.
    """
    system = _get_system(account, system_id)
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System with ID {system_id} not found."
        )
    # Convert vivintpy.System object to SystemResponse object
    return SystemResponse(id=system.id, name=system.name)

# --- Alarm Panel Endpoints ---
@router.get("/{system_id}/panel", response_model=AlarmPanelResponse)
async def get_alarm_panel_details(
    system_id: int,
    account: Account = Depends(deps.get_user_account)
):
    """
    Get detailed information for the alarm panel of a specific system.
    """
    system = _get_system(account, system_id)
    if not system:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"System with ID {system_id} not found.")
    
    alarm_panel = (system.alarm_panels[0] if system.alarm_panels else None)
    if not alarm_panel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alarm panel not found for system ID {system_id}.")
    
    return AlarmPanelResponse(
        id=alarm_panel.id,
        name=alarm_panel.name,
        state=alarm_panel.state,
        mac_address=alarm_panel.mac_address,
        manufacturer=alarm_panel.manufacturer,
        model=alarm_panel.model,
        software_version=alarm_panel.software_version
    )

@router.post("/{system_id}/panel/arm-stay", response_model=AlarmPanelResponse)
async def arm_stay_panel(
    system_id: int,
    account: Account = Depends(deps.get_user_account)
):
    """Arm the system's panel to 'Stay' mode."""
    system = _get_system(account, system_id)
    if not system or not (system.alarm_panels[0] if system.alarm_panels else None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System or alarm panel not found.")
    alarm_panel = (system.alarm_panels[0] if system.alarm_panels else None)
    try:
        await alarm_panel.set_armed_state(ArmedState.STAY)
        return AlarmPanelResponse(
            id=alarm_panel.id,
            name=alarm_panel.name,
            state=alarm_panel.state,
            mac_address=alarm_panel.mac_address,
            manufacturer=alarm_panel.manufacturer,
            model=alarm_panel.model,
            software_version=alarm_panel.software_version
        )
    except VivintSkyApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to arm panel to stay: {e}")

@router.post("/{system_id}/panel/arm-away", response_model=AlarmPanelResponse)
async def arm_away_panel(
    system_id: int,
    account: Account = Depends(deps.get_user_account)
):
    """Arm the system's panel to 'Away' mode."""
    system = _get_system(account, system_id)
    if not system or not (system.alarm_panels[0] if system.alarm_panels else None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System or alarm panel not found.")
    alarm_panel = (system.alarm_panels[0] if system.alarm_panels else None)
    try:
        await alarm_panel.set_armed_state(ArmedState.AWAY)
        return AlarmPanelResponse(
            id=alarm_panel.id,
            name=alarm_panel.name,
            state=alarm_panel.state,
            mac_address=alarm_panel.mac_address,
            manufacturer=alarm_panel.manufacturer,
            model=alarm_panel.model,
            software_version=alarm_panel.software_version
        )
    except VivintSkyApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to arm panel to away: {e}")

@router.post("/{system_id}/panel/disarm", response_model=AlarmPanelResponse)
async def disarm_panel(
    system_id: int,
    payload: DisarmPayload,
    account: Account = Depends(deps.get_user_account)
):
    """Disarm the system's panel using a PIN."""
    system = _get_system(account, system_id)
    if not system or not (system.alarm_panels[0] if system.alarm_panels else None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System or alarm panel not found.")
    alarm_panel = (system.alarm_panels[0] if system.alarm_panels else None)
    try:
        await alarm_panel.disarm(payload.pin)
        return AlarmPanelResponse(
            id=alarm_panel.id,
            name=alarm_panel.name,
            state=alarm_panel.state,
            mac_address=alarm_panel.mac_address,
            manufacturer=alarm_panel.manufacturer,
            model=alarm_panel.model,
            software_version=alarm_panel.software_version
        )
    except VivintSkyApiError as e: # Catch specific errors for invalid PIN if available
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to disarm panel: {e}")

@router.post("/{system_id}/panel/trigger-emergency", status_code=status.HTTP_202_ACCEPTED)
async def trigger_emergency_alarm_panel(
    system_id: int,
    payload: TriggerEmergencyPayload,
    account: Account = Depends(deps.get_user_account)
):
    """Trigger an emergency alarm on the panel (e.g., panic, fire, medical)."""
    system = _get_system(account, system_id)
    if not system or not (system.alarm_panels[0] if system.alarm_panels else None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System or alarm panel not found.")
    try:
        await (system.alarm_panels[0] if system.alarm_panels else None).trigger_emergency_alarm(payload.emergency_type)
        return {"message": f"Emergency alarm ({payload.emergency_type.name}) triggered successfully."}
    except AttributeError:
         raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Emergency trigger functionality not available on the alarm panel object.")
    except VivintSkyApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to trigger emergency alarm: {e}")

@router.post("/{system_id}/panel/reboot", status_code=status.HTTP_202_ACCEPTED)
async def reboot_alarm_panel( 
    system_id: int,
    account: Account = Depends(deps.get_user_account)
):
    """Reboot the system's alarm panel."""
    system = _get_system(account, system_id)
    if not system or not (system.alarm_panels[0] if system.alarm_panels else None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System or alarm panel not found.")
    try:
        await (system.alarm_panels[0] if system.alarm_panels else None).reboot()
        return {"message": "Panel reboot command sent successfully."}
    except AttributeError:
         raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Reboot functionality not available on the alarm panel object.")
    except VivintSkyApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to reboot panel: {e}")
