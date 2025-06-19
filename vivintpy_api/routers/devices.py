from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import StreamingResponse
import httpx
from typing import List, Union, Any
from pydantic import BaseModel

from .. import deps
from vivintpy.utils import first_or_none  # Utility helper for safe list access
from vivintpy import Account, System
from vivintpy.devices import Device # Base device model
# Import specific device types from vivintpy
from vivintpy.devices.camera import Camera
from vivintpy.devices.door_lock import DoorLock
from vivintpy.devices.garage_door import GarageDoor, GarageDoorState
from vivintpy.devices.switch import BinarySwitch, MultilevelSwitch # Ensure these are the correct Pydantic models from vivintpy
from vivintpy.devices.thermostat import Thermostat, FanMode
from vivintpy.utils import first_or_none
from vivintpy.devices.wireless_sensor import WirelessSensor
from vivintpy.enums import OperatingMode # Added OperatingMode
from ..models.device import (
    DeviceResponse,
    DoorLockResponse,
    GarageDoorResponse,
    SwitchResponse, # This will be a base for BinarySwitchResponse and MultilevelSwitchResponse if we make them distinct
    ThermostatResponse,
    CameraResponse,
    WirelessSensorResponse,
    GenericDeviceResponse # Fallback
)
from vivintpy.enums import DeviceType as VivintDeviceType # For mapping
# vivintpy.enums.DeviceType might be useful for checks, but direct isinstance is better
from vivintpy.exceptions import VivintSkyApiError

router = APIRouter(
    prefix="/systems/{system_id}/devices",
    tags=["Devices"],
    dependencies=[Depends(deps.get_current_active_user)], # Secure all endpoints in this router
)

# --- Helper Dependency to get System and Device ---
async def get_system_and_device(
    system_id: int,
    device_id: int,
    account: Account = Depends(deps.get_user_account),
) -> tuple[System, Device]:
    print(f"--- ROUTER get_system_and_device: Received account with systems: {bool(account.systems)} ---")
    system = first_or_none(account.systems, lambda s: s.id == system_id)
    if not system:
        print(f"--- ROUTER get_system_and_device: System {system_id} not found in account.systems ---")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="System not found"
        )
    
    print(f"--- ROUTER get_system_and_device: Found system id {id(system)}, devices={len(system.device_map)} ---")

    device = system.get_device(device_id)
    if not device:
        print(f"--- ROUTER get_system_and_device: Device {device_id} not found by system.get_device ---")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        )
    
    return system, device

# --- Pydantic models for request bodies ---
class LockPayload(BaseModel):
    locked: bool

class GarageDoorPayload(BaseModel):
    state: GarageDoorState # Uses vivintpy.devices.garage_door.GarageDoorState enum

class SwitchStatePayload(BaseModel):
    state: bool # True for ON, False for OFF

class SwitchLevelPayload(BaseModel):
    level: int # Typically 0-100 for multilevel/dimmer switches

class ThermostatSetpointPayload(BaseModel):
    cool_setpoint: float | None = None
    heat_setpoint: float | None = None

class ThermostatFanModePayload(BaseModel):
    fan_mode: FanMode # Uses vivintpy.devices.thermostat.FanMode enum

class ThermostatModePayload(BaseModel):
    mode: OperatingMode # Uses vivintpy.enums.OperatingMode enum


# --- Device Listing and Detail Endpoints ---
@router.get("/", response_model=List[DeviceResponse]) 
async def list_devices_in_system(
    system_id: int,
    account: Account = Depends(deps.get_user_account)
):
    """List all devices for a given system."""
    system = first_or_none(account.systems, lambda s: s.id == system_id)
    if not system:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"System with ID {system_id} not found.")
    # Convert VivintDevice objects to DeviceResponse objects
    # Pydantic's from_attributes will map attributes from VivintDevice to DeviceResponse
    return [DeviceResponse.model_validate(device) for device in system.device_map.values()]


# Union of specific Pydantic response models for OpenAPI schema
SpecificDeviceModelsResponse = Union[
    DoorLockResponse, 
    GarageDoorResponse, 
    SwitchResponse, # Later can be Union[BinarySwitchResponse, MultilevelSwitchResponse]
    ThermostatResponse, 
    CameraResponse, 
    WirelessSensorResponse, 
    GenericDeviceResponse # Fallback / base Device type
]

# Mapping from vivintpy device classes to Pydantic response models
# Note: VivintDeviceType is from vivintpy.enums
DEVICE_TO_RESPONSE_MODEL_MAP = {
    DoorLock: DoorLockResponse,
    GarageDoor: GarageDoorResponse,
    BinarySwitch: SwitchResponse, # Or a more specific BinarySwitchResponse
    MultilevelSwitch: SwitchResponse, # Or a more specific MultilevelSwitchResponse
    Thermostat: ThermostatResponse,
    Camera: CameraResponse,
    WirelessSensor: WirelessSensorResponse,
    Device: GenericDeviceResponse, # Fallback for generic Device or unknown types
}

@router.get("/{device_id}", response_model=SpecificDeviceModelsResponse)
async def get_device_details(
    system_and_device: tuple[System, Device] = Depends(get_system_and_device)
):
    """Get detailed information for a specific device. The response model will be the specific device type."""
    _, device_obj = system_and_device

    # Determine the Pydantic response model based on the type of the vivintpy device object
    response_model_class = GenericDeviceResponse # Default to generic
    for vivint_class, pydantic_class in DEVICE_TO_RESPONSE_MODEL_MAP.items():
        if isinstance(device_obj, vivint_class):
            response_model_class = pydantic_class
            break
    
    # Convert the vivintpy device object to the Pydantic response model
    # Pydantic's from_attributes=True (set in DeviceResponse.Config) handles this.
    return response_model_class.model_validate(device_obj)

# --- Device Action Endpoints ---

# Door Lock Actions
@router.post("/{device_id}/lock", response_model=DoorLockResponse)
async def set_door_lock_state(
    payload: LockPayload,
    system_and_device: tuple[System, Device] = Depends(get_system_and_device)
):
    """Lock or unlock a door."""
    _, device = system_and_device
    if not isinstance(device, DoorLock):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device is not a DoorLock.")
    try:
        await device.set_locked(payload.locked)
        return device
    except VivintSkyApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to set lock state: {e}")

# Garage Door Actions
@router.post("/{device_id}/garage-door", response_model=GarageDoorResponse)
async def set_garage_door_state(
    payload: GarageDoorPayload,
    system_and_device: tuple[System, Device] = Depends(get_system_and_device)
):
    """Open or close a garage door."""
    _, device = system_and_device
    if not isinstance(device, GarageDoor):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device is not a GarageDoor.")
    try:
        await device.set_state(payload.state)
        return device
    except VivintSkyApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to set garage door state: {e}")

# Switch Actions (Binary: On/Off)
@router.post("/{device_id}/switch/state", response_model=SwitchResponse) # Multilevel might also support on/off
async def set_switch_on_off_state(
    payload: SwitchStatePayload,
    system_and_device: tuple[System, Device] = Depends(get_system_and_device)
):
    """Turn a switch on or off."""
    _, device = system_and_device
    if not (isinstance(device, BinarySwitch) or isinstance(device, MultilevelSwitch)) or not hasattr(device, 'set_state'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device is not a switch or does not support on/off state.")
    try:
        await device.set_state(payload.state)
        return device
    except VivintSkyApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to set switch state: {e}")

# Switch Actions (Multilevel: Dimmer)
@router.post("/{device_id}/switch/level", response_model=SwitchResponse)
async def set_switch_dimmer_level(
    payload: SwitchLevelPayload,
    system_and_device: tuple[System, Device] = Depends(get_system_and_device)
):
    """Set the level of a multilevel switch (dimmer)."""
    _, device = system_and_device
    if not isinstance(device, MultilevelSwitch) or not hasattr(device, 'set_level'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device is not a multilevel switch or does not support setting level.")
    try:
        await device.set_level(payload.level)
        return device
    except VivintSkyApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to set switch level: {e}")

# Thermostat Actions
@router.post("/{device_id}/thermostat/setpoints", response_model=ThermostatResponse)
async def set_thermostat_setpoints(
    payload: ThermostatSetpointPayload,
    system_and_device: tuple[System, Device] = Depends(get_system_and_device)
):
    """Set cool and/or heat setpoints for a thermostat."""
    _, device = system_and_device
    if not isinstance(device, Thermostat):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device is not a Thermostat.")
    try:
        if payload.cool_setpoint is not None:
            await device.set_cool_setpoint(payload.cool_setpoint)
        if payload.heat_setpoint is not None:
            await device.set_heat_setpoint(payload.heat_setpoint)
        return device # vivintpy device objects update in-place
    except VivintSkyApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to set thermostat setpoints: {e}")

@router.post("/{device_id}/thermostat/fan-mode", response_model=ThermostatResponse)
async def set_thermostat_fan_mode(
    payload: ThermostatFanModePayload,
    system_and_device: tuple[System, Device] = Depends(get_system_and_device)
):
    """Set the fan mode for a thermostat."""
    _, device = system_and_device
    if not isinstance(device, Thermostat):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device is not a Thermostat.")
    try:
        await device.set_fan_mode(payload.fan_mode)
        return device
    except VivintSkyApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to set thermostat fan mode: {e}")

@router.post("/{device_id}/thermostat/mode", response_model=ThermostatResponse)
async def set_thermostat_mode(
    payload: ThermostatModePayload,
    system_and_device: tuple[System, Device] = Depends(get_system_and_device)
):
    """Set the operating mode for a thermostat (e.g., COOL, HEAT, OFF, AUTO)."""
    _, device = system_and_device
    if not isinstance(device, Thermostat):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device is not a Thermostat.")
    try:
        await device.set_mode(payload.mode)
        return device
    except VivintSkyApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to set thermostat mode: {e}")

# Camera Actions
@router.post("/{device_id}/camera/request-snapshot", response_model=CameraResponse)
async def request_camera_snapshot(
    system_and_device: tuple[System, Device] = Depends(get_system_and_device),
):
    """
    Request a new snapshot from a camera. 
    The camera's `snapshot_url` attribute may update after this call, often signaled via PubNub.
    """
    _, device = system_and_device
    if not isinstance(device, Camera):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device is not a Camera.")
    
    # Use unified request_thumbnail helper provided by vivintpy
    if not hasattr(device, 'request_thumbnail'):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Snapshot request not supported for this camera.")

    try:
        await device.request_thumbnail()
        # The device object itself is updated by vivintpy, so returning it reflects its current state.
        # The actual snapshot URL update might be asynchronous.
        return device
    except VivintSkyApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to request camera snapshot: {e}")

# ----------------------------------------------------------------------
# GET /snapshot – returns latest (or freshly requested) camera image
# ----------------------------------------------------------------------
@router.get("/{device_id}/snapshot", response_class=StreamingResponse)
async def get_camera_snapshot(
    refresh: bool = False,
    system_and_device: tuple[System, Device] = Depends(get_system_and_device),
):
    """Return the latest camera snapshot as JPEG.

    If `refresh=true` is supplied, the API first requests a new snapshot and
    then immediately returns the current thumbnail URL (most cameras refresh
    within a second; clients can re-try if they still see the old image).
    """
    _, device = system_and_device
    if not isinstance(device, Camera):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device is not a Camera.")

    # Always attempt to obtain a thumbnail URL, optionally triggering a refresh first
    attempts_left = 12  # up to ~6 seconds
    url: str | None = None

    if refresh:
        try:
            await device.request_thumbnail()
        except VivintSkyApiError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to request new snapshot: {exc}") from exc

    # Initial fetch
    url = await device.get_thumbnail_url()

    while url is None and attempts_left > 0:
        await asyncio.sleep(0.5)
        url = await device.get_thumbnail_url()
        attempts_left -= 1

    if url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot URL unavailable.")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            # Disable downstream caching so browsers always fetch fresh images
            headers = {"Cache-Control": "no-store"}
            return StreamingResponse(resp.aiter_bytes(), media_type="image/jpeg", headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to fetch snapshot: {exc}") from exc
