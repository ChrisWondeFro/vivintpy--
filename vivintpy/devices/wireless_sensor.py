"""Module that implements the WirelessSensor class."""

from __future__ import annotations

import logging

from ..const import WirelessSensorAttribute as Attributes
from ..enums import EquipmentCode, EquipmentType, SensorType
from ..models import WirelessSensorData
from ..utils import first_or_none
from . import BypassTamperDevice, VivintDevice
from .alarm_panel import AlarmPanel

_LOGGER = logging.getLogger(__name__)


class WirelessSensor(BypassTamperDevice, VivintDevice):
    """Represents a Vivint wireless sensor device."""

    alarm_panel: AlarmPanel

    def __init__(self, data: dict | WirelessSensorData, alarm_panel: AlarmPanel | None = None) -> None:
        """Initialize a wireless sesnor."""
        if isinstance(data, WirelessSensorData):
            model = data
        else:
            model = WirelessSensorData.model_validate(data)
        super().__init__(model, alarm_panel)
        self._data_model: WirelessSensorData = model
        self.__update_parent()

    def __repr__(self) -> str:
        """Return custom __repr__ of wireless sensor."""
        return (
            f"<{self.__class__.__name__}|{self.equipment_type} {self.id}, {self.name}>"
        )

    @property
    def model(self) -> str:
        """Return the equipment_code as the model of this sensor."""
        return self.equipment_code.name

    @property
    def software_version(self) -> str | None:
        """Return the software version of this device, if any."""
        return self._data_model.firmware_version

    @property
    def equipment_code(self) -> EquipmentCode:
        """Return the equipment code of this sensor."""
        return EquipmentCode(self._data_model.equipment_code)  # type: ignore[arg-type]

    @property
    def equipment_type(self) -> EquipmentType:
        """Return the equipment type of this sensor."""
        return EquipmentType(self._data_model.equipment_type)  # type: ignore[arg-type]

    @property
    def sensor_type(self) -> SensorType:
        """Return the sensor type of this sensor."""
        return SensorType(self._data_model.sensor_type)  # type: ignore[arg-type]

    @property
    def is_on(self) -> bool:
        """Return `True` if the sensor's state is on."""
        return bool(self._data_model.state)

    @property
    def is_valid(self) -> bool:
        """Return `True` if the wireless sensor is valid.

        Serial number information may be stored under either the 32-bit or
        16-bit key depending on device generation.  If the generic
        ``serial_number`` property cannot resolve a value (e.g. because the
        raw payload was filtered), fall back to the typed model attributes.
        """
        serial = (
            self.serial_number
            or getattr(self._data_model, "serial_number", None)
            or getattr(self._data_model, "serial_number_32_bit", None)
        )
        return (
            serial is not None
            and self.equipment_code != EquipmentCode.OTHER
            and self.sensor_type != SensorType.UNUSED
        )

    def update_data(self, new_val: dict, override: bool = False) -> None:
        """Update entity's raw data."""
        super().update_data(new_val=new_val, override=override)
        # Refresh typed model after data update
        self._data_model = WirelessSensorData.model_validate(self.data)
        self.__update_parent()

    def __update_parent(self) -> None:
        if self._data_model.hidden and self._parent is None:
            self._parent = first_or_none(
                self.alarm_panel.devices,
                lambda parent: parent.serial_number == self.serial_number,
            )

    async def set_bypass(self, bypass: bool) -> None:
        """Bypass/unbypass the sensor."""
        await self.api.set_sensor_state(
            self.alarm_panel.id, self.alarm_panel.partition_id, self.id, bypass
        )

    async def bypass(self) -> None:
        """Bypass the sensor."""
        await self.set_bypass(True)

    async def unbypass(self) -> None:
        """Unbypass the sensor."""
        await self.set_bypass(False)
