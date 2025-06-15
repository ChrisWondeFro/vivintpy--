"""Module that implements the AlarmPanel class."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Type

from ..api import VivintSkyApi
from ..const import AlarmPanelAttribute as Attribute
from ..const import (
    PanelUpdateAttribute,
    PubNubMessageAttribute,
    PubNubOperatorAttribute,
    SystemAttribute,
)
from ..enums import ArmedState, DeviceType
from ..exceptions import VivintSkyApiError
from ..models import PanelCredentialsData, PanelUpdateData, AlarmPanelData
from ..utils import add_async_job, first_or_none
from . import VivintDevice, get_device_class

if TYPE_CHECKING:
    from ..system import System

_LOGGER = logging.getLogger(__name__)

DEVICE_DELETED = "device_deleted"
DEVICE_DISCOVERED = "device_discovered"


class AlarmPanel(VivintDevice):
    """Describe a Vivint alarm panel."""

    def __init__(self, data: dict | AlarmPanelData, system: System):
        """Initialize an alarm panel."""
        self.system = system
        if isinstance(data, AlarmPanelData):
            model = data
        else:
            model = AlarmPanelData.model_validate(data)
        # Pass typed model to generic base so raw dict stays in sync.
        super().__init__(model)
        self._data_model: AlarmPanelData = model
        self.devices: list[VivintDevice] = []
        self.unregistered_devices: dict[int, tuple] = {}

        self.__parse_data(data=data, init=True)

        # store a reference to the physical panel device
        self.__panel_credentials: PanelCredentialsData | None = None
        self.__panel = first_or_none(
            self.devices,
            lambda device: DeviceType(device.data.get(Attribute.TYPE))
            == DeviceType.PANEL,
        )

    def __repr__(self) -> str:
        """Return custom __repr__ of device."""
        return f"<{self.__class__.__name__} {self.id}, {self.name}: {self.state.name}>"

    @property
    def api(self) -> VivintSkyApi:
        """Return the API."""
        return self.system.api

    @property
    def id(self) -> int:
        """Panel's id."""
        return int(self._data_model.panel_id)

    @property
    def name(self) -> str:
        """Panel's name."""
        return self.system.name

    @property
    def mac_address(self) -> str:
        """Panel's MAC Address."""
        return str(self._data_model.mac_address)

    @property
    def manufacturer(self) -> str:
        """Return Vivint as the manufacturer of this panel."""
        return "Vivint"

    @property
    def model(self) -> str:
        """Return the model of the physical panel."""
        return (
            "Sky Control"
            if self.__panel and self.__panel.data["pant"] == 1
            else "Smart Hub"
        )

    @property
    def software_version(self) -> str | None:
        """Return the software version of the panel."""
        return self.__panel.software_version if self.__panel else None

    @property
    def partition_id(self) -> int:
        """Panel's partition id."""
        return int(self._data_model.partition_id)

    @property
    def is_disarmed(self) -> bool:
        """Return True if alarm is disarmed."""
        return self.state == ArmedState.DISARMED

    @property
    def is_armed_away(self) -> bool:
        """Return True if alarm is in armed away state."""
        return self.state == ArmedState.ARMED_AWAY

    @property
    def is_armed_stay(self) -> bool:
        """Return True if alarm is in armed stay state."""
        return self.state == ArmedState.ARMED_STAY

    @property
    def state(self) -> ArmedState:
        """Return the panel's armed state.

        The raw payloads in older APIs and the test fixtures sometimes encode
        the state as a *string* (e.g. "disarmed") instead of the numeric value
        expected by :class:`~vivintpy.enums.ArmedState`.  Handle both.
        """
        raw_state = self._data_model.state  # type: ignore[attr-defined]
        # Convert textual representation to enum if needed
        if isinstance(raw_state, str):
            try:
                return ArmedState[raw_state.upper()]
            except KeyError:
                return ArmedState.UNKNOWN
        try:
            return ArmedState(int(raw_state))  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001 – fallback for None/invalid
            return ArmedState.UNKNOWN

    @property
    def credentials(self) -> PanelCredentialsData | None:
        """Return the panel credentials."""
        return self.__panel_credentials

    async def set_armed_state(self, state: int) -> None:
        """Set the armed state for a panel."""
        _LOGGER.debug("Setting %s to %s", self.name, ArmedState(state).name)
        await self.api.set_alarm_state(self.id, self.partition_id, state)

    async def trigger_alarm(self) -> None:
        """Trigger an alarm."""
        _LOGGER.debug("Triggering an alarm on %s", self.name)
        await self.api.trigger_alarm(self.id, self.partition_id)

    async def disarm(self) -> None:
        """Disarm the alarm."""
        await self.set_armed_state(ArmedState.DISARMED)

    async def arm_stay(self) -> None:
        """Set the alarm to armed stay."""
        await self.set_armed_state(ArmedState.ARMED_STAY)

    async def arm_away(self) -> None:
        """Set the alarm to armed away."""
        await self.set_armed_state(ArmedState.ARMED_AWAY)

    async def get_panel_credentials(self, refresh: bool = False) -> PanelCredentialsData:
        """Get the panel credentials."""
        if refresh or self.__panel_credentials is None:
            self.__panel_credentials = await self.api.get_panel_credentials(self.id)
        return self.__panel_credentials

    async def get_software_update_details(self) -> PanelUpdateData:
        """Get the software update details."""
        if not self.system.is_admin:
            _LOGGER.warning(
                "%s - Cannot get software update details as user is not an admin",
                self.name,
            )
            raw = {
                PanelUpdateAttribute.AVAILABLE: False,
                PanelUpdateAttribute.AVAILABLE_VERSION: "",
                PanelUpdateAttribute.CURRENT_VERSION: "",
                PanelUpdateAttribute.UPDATE_REASON: "",
            }
            return PanelUpdateData.model_validate(raw)
        return await self.api.get_system_update(self.id)

    async def update_software(self) -> bool:
        """Update the panel software version."""
        if not self.system.is_admin:
            _LOGGER.warning(
                "%s - Cannot update software as user is not an admin", self.name
            )
            return False
        try:
            await self.api.update_panel_software(self.id)
        except VivintSkyApiError as err:
            _LOGGER.error("%s - %s", self.name, err)
            return False
        return True

    async def reboot(self) -> None:
        """Reboot the panel."""
        if not self.system.is_admin:
            _LOGGER.warning(
                "%s - Cannot reboot panel as user is not an admin", self.name
            )
            return
        await self.api.reboot_panel(self.id)

    def get_devices(
        self, device_types: set[Type[VivintDevice]] | None = None
    ) -> list[VivintDevice]:
        """Get a list of associated devices."""
        devices: list[VivintDevice] = []

        if device_types:
            devices = [
                device for device in self.devices if device.__class__ in device_types
            ]
        else:
            devices = self.devices

        return devices

    def update_data(self, new_val: dict, override: bool = False) -> None:  # type: ignore[override]
        """Update panel raw data then refresh typed model."""
        super().update_data(new_val=new_val, override=override)
        self._data_model = AlarmPanelData.model_validate(self.data)

    def refresh(self, data: dict, new_device: bool = False) -> None:
        """Refresh the alarm panel."""
        if not new_device:
            # Update raw dict first to preserve existing device update logic
            self.update_data(data, override=True)
        else:
            # Extend typed and raw lists consistently, handling either key style
            new_devices = data.get(Attribute.DEVICES) or data.get("devices") or []
            self._data_model.devices.extend(new_devices)
            # Ensure raw list exists before extending
            self.data.setdefault(Attribute.DEVICES, []).extend(new_devices)

        self.__parse_data(data)
        # Re-validate data model after refresh
        self._data_model = AlarmPanelData.model_validate(self.data)

    def handle_pubnub_message(self, message: dict) -> None:
        """Handle a pubnub message."""
        operation = message.get(PubNubMessageAttribute.OPERATION)
        data = message.get(PubNubMessageAttribute.DATA)
        # `data` may legally be an *empty* dict (heartbeat/update with no changes).
        # Treat it as missing *only* when the key itself is absent or explicitly
        # set to ``None`` so that empty payloads reach the device-update logic.
        if data is None:
            _LOGGER.debug(
                "Ignoring account partition message for panel %s, partition %s (no data provided): %s",
                self.id,
                self.partition_id,
                message,
            )
            return

        if not data.get(PubNubMessageAttribute.DEVICES):
            # this message is for the panel itself
            self.update_data(data)
        else:
            # this is a message for one (or more) of the attached devices
            devices_data = data[PubNubMessageAttribute.DEVICES]

            for device_data in devices_data:
                device_id = device_data.get("_id")
                if not device_id:
                    _LOGGER.debug("No device id")
                    continue

                if operation == PubNubOperatorAttribute.CREATE:
                    self.refresh(data=data, new_device=True)
                    add_async_job(self.handle_new_device, device_id)
                else:
                    device = first_or_none(
                        self.devices,
                        lambda device, device_id=device_id: device.id == device_id,  # type: ignore
                    )
                    if not device:
                        _LOGGER.debug(
                            "Ignoring message for device %s (device not found)",
                            device_id,
                        )
                        continue

                    # for the sake of consistency, we also need to update the panel's raw data
                    raw_device_data = first_or_none(
                        self._data_model.devices,
                        lambda raw_device_data,  # type: ignore
                        device_data=device_data: raw_device_data["_id"]
                        == device_data["_id"],
                    )

                    if operation == PubNubOperatorAttribute.DELETE:
                        self.devices.remove(device)
                        if raw_device_data is not None:
                            self._data_model.devices.remove(raw_device_data)
                        self.unregistered_devices[device.id] = (
                            device.name,
                            device.device_type,
                        )
                        self.emit(DEVICE_DELETED, {"device": device})
                    else:
                        device.handle_pubnub_message(device_data)
                        if raw_device_data:
                            raw_device_data.update(device_data)

    async def handle_new_device(self, device_id: int) -> None:
        """Handle a new device."""
        try:
            device = first_or_none(self.devices, lambda device: device.id == device_id)
            assert device
            while not device.is_valid:
                await asyncio.sleep(1)
                if device.id in self.unregistered_devices:
                    return
            # Fetch and unpack the SystemData model
            resp_model = await self.api.get_device_data(self.id, device_id)
            # Extract panel data from the Pydantic model
            panel_body = resp_model.system
            data = panel_body.par[0]
            self.refresh(data, new_device=True)
            self.emit(DEVICE_DISCOVERED, {"device": device})
        except VivintSkyApiError:
            _LOGGER.error("Error getting new device data for device %s", device_id)

    def __parse_data(self, data: dict, init: bool = False) -> None:
        """Parse the alarm panel data."""
        # Normalize fixture keys ("devices", "unregistered") to the compact
        # aliases used internally so that downstream logic can rely on them.
        if Attribute.DEVICES not in data and "devices" in data:
            data[Attribute.DEVICES] = data["devices"]
        if Attribute.UNREGISTERED not in data and "unregistered" in data:
            data[Attribute.UNREGISTERED] = data["unregistered"]

        for device_data in data.get(Attribute.DEVICES, []):
            device: VivintDevice | None = None
            if not init:
                device = first_or_none(
                    self.devices,
                    lambda device, device_data=device_data: device.id  # type: ignore
                    == device_data[Attribute.ID],
                )
            if device:
                device.update_data(device_data, override=True)
            else:
                self.__parse_device_data(device_data=device_data)

        if data.get(Attribute.UNREGISTERED):
            self.unregistered_devices = {
                device[Attribute.ID]: (
                    device[Attribute.NAME],
                    DeviceType(device[Attribute.TYPE]),
                )
                for device in data[Attribute.UNREGISTERED]
            }

    def __parse_device_data(self, device_data: dict) -> None:
        """Parse device data and optionally emit a device discovered event."""
        device_class = get_device_class(device_data[Attribute.TYPE])
        device = device_class(device_data, self)
        self.devices.append(device)
