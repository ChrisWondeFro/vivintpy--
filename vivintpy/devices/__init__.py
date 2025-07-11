"""This package contains the various devices attached to a Vivint system."""

from __future__ import annotations

from typing import TYPE_CHECKING, Type, cast

from pydantic import BaseModel

from ..api import VivintSkyApi
from ..const import VivintDeviceAttribute as Attribute
from ..entity import Entity
from ..enums import (
    CapabilityCategoryType,
    CapabilityType,
    DeviceType,
    FeatureType,
    ZoneBypass,
)
from ..zjs_device_config_db import get_zwave_device_info

if TYPE_CHECKING:
    from .alarm_panel import AlarmPanel

DEVICE = "device"


def get_device_class(device_type: str) -> Type[VivintDevice]:
    """Map a device_type string to the class that implements that device."""
    # pylint: disable=import-outside-toplevel,cyclic-import
    from .camera import Camera
    from .door_lock import DoorLock
    from .garage_door import GarageDoor
    from .switch import BinarySwitch, MultilevelSwitch
    from .thermostat import Thermostat
    from .wireless_sensor import WirelessSensor

    mapping: dict[DeviceType, Type[VivintDevice]] = {
        DeviceType.BINARY_SWITCH: BinarySwitch,
        DeviceType.CAMERA: Camera,
        DeviceType.DOOR_LOCK: DoorLock,
        DeviceType.GARAGE_DOOR: GarageDoor,
        DeviceType.MULTI_LEVEL_SWITCH: MultilevelSwitch,
        DeviceType.THERMOSTAT: Thermostat,
        DeviceType.PANEL: VivintDevice,
        DeviceType.WIRELESS_SENSOR: WirelessSensor,
    }

    return mapping.get(DeviceType(device_type), UnknownDevice)


class VivintDevice(Entity):
    """Class to implement a generic vivint device."""

    def __init__(self, data: BaseModel | dict, alarm_panel: AlarmPanel | None = None) -> None:  # type: ignore[name-defined]
        """Initialize a device.

        ``data`` may be either the raw dict payload **or** a validated Pydantic
        model.  Passing a model gives the generic ``Entity`` class enough
        information to keep both the model and its raw‐dict representation in
        sync, which lets subclasses gradually move to typed access without
        breaking legacy behaviour.
        """
        super().__init__(data)
        self.alarm_panel = alarm_panel
        self._manufacturer: str | None = None
        self._model: str | None = None

        # Work exclusively with the canonical raw dict copy maintained by
        # Entity so this logic works regardless of what was passed in.
        raw = self.data

        self._capabilities = (
            {
                CapabilityCategoryType(cat.get(Attribute.TYPE)): [
                    CapabilityType(cap) for cap in cat.get(Attribute.CAPABILITY)
                ]
                for cat in caca
            }
            if (caca := raw.get(Attribute.CAPABILITY_CATEGORY)) is not None
            else None
        )
        self._features = (
            [FeatureType(feature) for feature in feats if feats.get(feature) is True]
            if (feats := raw.get(Attribute.FEATURES)) is not None
            else None
        )
        self._parent: VivintDevice | None = None

    def __repr__(self) -> str:
        """Return custom __repr__ of device."""
        return f"<{self.__class__.__name__} {self.id}, {self.name}>"

    @property
    def api(self) -> VivintSkyApi:
        """Return the API."""
        assert self.alarm_panel, """no alarm panel set for this device"""
        return self.alarm_panel.system.api

    @property
    def id(self) -> int:  # pylint: disable=invalid-name
        """Device's id."""
        return int(self.data[Attribute.ID])

    @property
    def is_valid(self) -> bool:
        """Return `True` if the device is valid."""
        return True

    @property
    def name(self) -> str:
        """Device's name. Guaranteed to be non-empty.

        If the underlying data does not include a user-defined name, we fall
        back to a synthesized value like "Camera 1234" so that the FastAPI
        `DeviceResponse` model (which requires a non-null `name`) always
        validates successfully.
        """
        raw_name = self.data.get(Attribute.NAME)
        if raw_name not in (None, ""):
            return str(raw_name)
        # Fallback – generate a friendly name from the device type and id.
        return f"{self.device_type.name.title()} {self.id}"

    @property
    def battery_level(self) -> int | None:
        """Return the device's battery level."""
        if not self.has_battery:
            return None
        if (battery_level := self.data.get(Attribute.BATTERY_LEVEL)) not in (None, ""):
            return battery_level
        return 0 if self.low_battery else 100

    @property
    def online(self) -> bool:
        """Return True if the device reports as online.

        This unified property is required by the public `DeviceResponse`
        Pydantic model.  Concrete device classes in *vivintpy* already expose
        an `is_online` property – we reuse that when present.  For other
        devices we fall back to the raw `ol` field in the payload.  If neither
        source is available we assume the device is offline.
        """
        # First preference: subclasses often implement `is_online` (property)
        is_online_attr = getattr(self, "is_online", None)
        if isinstance(is_online_attr, bool):
            return is_online_attr
        if callable(is_online_attr):
            try:
                return bool(is_online_attr())  # type: ignore[arg-type]
            except Exception:  # pragma: no cover
                pass
        # Fallback: use the raw data field if present (1/0 or True/False)
        raw_online = self.data.get(Attribute.ONLINE)
        return bool(raw_online)

    @property
    def capabilities(
        self,
    ) -> dict[CapabilityCategoryType, list[CapabilityType]] | None:
        """Device capabilities."""
        return self._capabilities

    @property
    def device_type(self) -> DeviceType:
        """Return the device type."""
        return DeviceType(self.data.get(Attribute.TYPE))

    @property
    def features(self) -> list[FeatureType] | None:
        """Device Features."""
        return self._features

    @property
    def has_battery(self) -> bool:
        """Return `True` if the device has battery details."""
        return (
            self.data.get(Attribute.BATTERY_LEVEL) is not None
            or self.data.get(Attribute.LOW_BATTERY) is not None
        )

    @property
    def is_subdevice(self) -> bool:
        """Return if this device is a subdevice."""
        return self._parent is not None

    @property
    def low_battery(self) -> bool | None:
        """Return `True` if the device's battery level is low."""
        return self.data.get(Attribute.LOW_BATTERY, False) if self.has_battery else None

    @property
    def manufacturer(self) -> str | None:
        """Return the manufacturer for this device."""
        if not self._manufacturer and self.data.get("zpd"):
            self.get_zwave_details()
        return self._manufacturer

    @property
    def model(self) -> str | None:
        """Return the model for this device."""
        if not self._model and self.data.get("zpd"):
            self.get_zwave_details()
        return self._model

    @property
    def panel_id(self) -> int:
        """Return the id of the panel this device is associated to."""
        return int(self.data[Attribute.PANEL_ID])

    @property
    def parent(self) -> VivintDevice | None:
        """Return the parent device, if any."""
        return self._parent

    @property
    def serial_number(self) -> str | None:
        """Return the serial number for this device as a string.

        The raw value can be an `int` or `str`, depending on the device.  We
        normalise to `str` (or `None`) so that Pydantic validation in the
        public API never fails because of a type mismatch.
        """
        serial = (
            self.data.get(Attribute.SERIAL_NUMBER_32_BIT)
            or self.data.get(Attribute.SERIAL_NUMBER)
        )
        return str(serial) if serial not in (None, "") else None

    @property
    def software_version(self) -> str | None:
        """Return the software or firmware version as a string.

        Vivint devices report version information in several different
        formats (e.g., an int, a list of ints, or a list of lists).  This
        accessor converts all of those representations into a human-friendly
        dotted string (e.g., ``"3.1.0"``) so that the FastAPI
        ``DeviceResponse`` model always receives a `str | None` value.
        """
        csv = self.data.get(Attribute.CURRENT_SOFTWARE_VERSION)
        if csv not in (None, ""):
            return str(csv)

        fwv = self.data.get(Attribute.FIRMWARE_VERSION)
        if fwv in (None, ""):
            return None

        # If it's already an int (e.g., 15) just convert directly.
        if isinstance(fwv, int):
            return str(fwv)

        # If we get a flat list of ints (e.g., [3, 1, 0]) join them.
        if isinstance(fwv, (list, tuple)) and all(isinstance(p, int) for p in fwv):
            return ".".join(str(p) for p in fwv)

        # If we get a list of lists (e.g., [[3], [1], [0]]) flatten first.
        if isinstance(fwv, (list, tuple)) and all(
            isinstance(p, (list, tuple)) for p in fwv
        ):
            flattened: list[int] = [item for sub in fwv for item in sub]
            return ".".join(str(p) for p in flattened)

        # Fallback – ensure we always return a string.
        return str(fwv)

    def get_zwave_details(self) -> None:
        """Get Z-Wave details."""
        if self.data.get("zpd") is None:
            return

        result = get_zwave_device_info(
            self.data.get("manid"),
            self.data.get("prtid"),
            self.data.get("prid"),
        )

        self._manufacturer = result.get("manufacturer", "Unknown")

        label = result.get("label")
        description = result.get("description")

        if label and description:
            self._model = f"{description} ({label})"
        elif label:
            self._model = label
        elif description:
            self._model = description
        else:
            self._model = "Unknown"

    def emit(self, event_name: str, data: dict) -> None:
        """Add device data and then send to parent."""
        if data.get(DEVICE) is None:
            data.update({DEVICE: self})

        super().emit(event_name, data)


class BypassTamperDevice(VivintDevice):
    """Class for devices that can be bypassed and tampered."""

    @property
    def is_bypassed(self) -> bool:
        """Return True if the device is bypassed (handles missing fields safely)."""
        val = self.data.get(Attribute.BYPASSED)
        if val is None:
            return False
        try:
            return int(val) != ZoneBypass.UNBYPASSED
        except (TypeError, ValueError):
            # Fallback: treat unparsable value as not bypassed
            return False

    @property
    def is_tampered(self) -> bool:
        """Return True if the device is reporting as tampered."""
        return bool(self.data.get(Attribute.TAMPER))


class UnknownDevice(VivintDevice):
    """Describe an unknown/unsupported vivint device."""

    def __repr__(self) -> str:
        """Return custom __repr__ of device."""
        return f"<{self.__class__.__name__}|{self.data[Attribute.TYPE]} {self.id}, {self.name}>"


Device = VivintDevice  # Alias VivintDevice to Device for easier import
