"""Module that implements the Thermostat class."""

from __future__ import annotations

import logging
from typing import Any

from ..const import ThermostatAttribute as Attribute
from ..enums import DeviceType, FanMode, HoldMode, OperatingMode, OperatingState
from ..models import ThermostatData
from . import VivintDevice
from .alarm_panel import AlarmPanel

_LOGGER = logging.getLogger(__name__)


class Thermostat(VivintDevice):
    """Represents a Vivint thermostat device."""

    def __init__(self, data: dict, alarm_panel: AlarmPanel):
        """Initialize a thermostat."""
        super().__init__(data, alarm_panel)
        # Store validated data model for typed access
        self._data_model: ThermostatData = ThermostatData.model_validate(data)

        if self._data_model.actual_type == DeviceType.POD_NEST_THERMOSTAT.value:
            self._manufacturer, self._model = "Google", "Nest"

    @property
    def cool_set_point(self) -> float | None:
        """Return the cool set point of the thermostat."""
        return self._data_model.cool_set_point

    @property
    def fan_mode(self) -> FanMode:
        """Return the fan mode of the thermostat."""
        return FanMode(self._data_model.fan_mode)  # type: ignore[arg-type]

    @property
    def heat_set_point(self) -> float | None:
        """Return the heat set point of the thermostat."""
        return self._data_model.heat_set_point

    @property
    def hold_mode(self) -> HoldMode:
        """Return the hold mode of the thermostat."""
        return HoldMode(self._data_model.hold_mode)  # type: ignore[arg-type]

    @property
    def humidity(self) -> int | None:
        """Return the humidity of the thermostat."""
        return self._data_model.humidity

    @property
    def is_fan_on(self) -> bool:
        """Return `True` if the thermostat fan is on."""
        return self._data_model.fan_state == 1

    @property
    def is_on(self) -> bool:
        """Return `True` if the thermostat is on."""
        return self.operating_state != OperatingState.IDLE

    @property
    def maximum_temperature(self) -> float | None:
        """Return the maximum temperature of the thermostat."""
        return self._data_model.maximum_temperature

    @property
    def minimum_temperature(self) -> float | None:
        """Return the minimum temperature of the thermostat."""
        return self._data_model.minimum_temperature

    @property
    def operating_mode(self) -> OperatingMode:
        """Return the operating mode of the thermostat."""
        return OperatingMode(self._data_model.operating_mode)  # type: ignore[arg-type]

    @property
    def operating_state(self) -> OperatingState:
        """Return the operating state of the thermostat."""
        return OperatingState(self._data_model.operating_state)  # type: ignore[arg-type]

    @property
    def temperature(self) -> float | None:
        """Return the temperature of the thermostat."""
        return self._data_model.current_temperature

    @staticmethod
    def celsius_to_fahrenheit(celsius: float) -> int:
        """Convert Celsius to Fahrenheit."""
        return round(celsius * 1.8 + 32)

    async def set_state(self, **kwargs: Any) -> None:
        """Set arbitrary state parameters on the thermostat via VivintSkyApi."""
        assert self.alarm_panel
        await self.api.set_thermostat_state(
            self.alarm_panel.id, self.alarm_panel.partition_id, self.id, **kwargs
        )

    # ------------------------------------------------------------------
    # Convenience helpers used by FastAPI router
    # ------------------------------------------------------------------
    async def set_cool_setpoint(self, setpoint: float) -> None:
        """Set the cool set-point (°F)."""
        await self.set_state(cool_set_point=setpoint)

    async def set_heat_setpoint(self, setpoint: float) -> None:
        """Set the heat set-point (°F)."""
        await self.set_state(heat_set_point=setpoint)

    async def set_fan_mode(self, mode: FanMode | int) -> None:
        """Set thermostat fan mode."""
        mode_val = mode.value if isinstance(mode, FanMode) else mode
        await self.set_state(fan_mode=mode_val)

    async def set_mode(self, mode: OperatingMode | int) -> None:
        """Set thermostat operating mode (COOL/HEAT/AUTO/OFF)."""
        mode_val = mode.value if isinstance(mode, OperatingMode) else mode
        await self.set_state(operating_mode=mode_val)
