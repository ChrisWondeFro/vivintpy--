"""Module that implements the Switch class."""

from __future__ import annotations

from ..const import SwitchAttribute as Attribute
from ..models import SwitchData
from . import VivintDevice


class Switch(VivintDevice):
    """Represents a Vivint switch device."""

    def __init__(self, data: dict | SwitchData, alarm_panel):  # type: ignore[override]
        # Ensure we have a typed model
        if isinstance(data, SwitchData):
            model = data
        else:
            model = SwitchData.model_validate(data)
        super().__init__(model, alarm_panel)
        self._data_model: SwitchData = model

    # ------------------------------------------------------------------
    # Typed attribute helpers
    # ------------------------------------------------------------------
    @property
    def is_on(self) -> bool:
        """Return True if switch is on."""
        return bool(self._data_model.state)

    @property
    def is_online(self) -> bool:
        """Return True if switch is online."""
        return bool(self._data_model.online)

    @property
    def level(self) -> int:
        """Return the level of the switch between 0..100."""
        # For binary switches, `value` might be bool; ensure int cast handles it
        val = self._data_model.value
        return int(val) if val is not None else 0

    async def set_state(
        self,
        on: bool | None = None,  # pylint: disable=invalid-name
        level: int | None = None,
    ) -> None:
        """Set switch's state."""
        assert self.alarm_panel
        await self.api.set_switch_state(
            self.alarm_panel.id, self.alarm_panel.partition_id, self.id, on, level
        )

    async def turn_on(self) -> None:
        """Turn on the switch."""
        await self.set_state(on=True)

    async def turn_off(self) -> None:
        """Turn off the switch."""
        await self.set_state(on=False)


class BinarySwitch(Switch):
    """Represents a Vivint binary switch device."""


class MultilevelSwitch(Switch):
    """Represents a Vivint multilevel switch device."""

    async def set_level(self, level: int) -> None:
        """Set the level of the switch between 0..100."""
        await self.set_state(level=level)
