"""Module that implements the GarageDoor class."""

from __future__ import annotations

from typing import Any

from ..const import ZWaveDeviceAttribute as Attribute
from ..enums import GarageDoorState
from ..models import GarageDoorData
from .alarm_panel import AlarmPanel
from . import VivintDevice


class GarageDoor(VivintDevice):
    """Represents a vivint garage door device."""

    def __init__(self, data: dict | GarageDoorData, alarm_panel: AlarmPanel | None = None):  # type: ignore[override]
        if isinstance(data, GarageDoorData):
            model = data
        else:
            model = GarageDoorData.model_validate(data)
        super().__init__(model, alarm_panel)
        self._data_model: GarageDoorData = model

    """Represents a vivint garage door device."""

    @property
    def is_closed(self) -> bool | None:
        """Return True if garage dooor is closed and None if unknown."""
        if self.state_enum == GarageDoorState.UNKNOWN:
            return None
        return self.state_enum == GarageDoorState.CLOSED

    @property
    def is_closing(self) -> bool:
        """Return True if garage dooor is closing."""
        return self.state_enum == GarageDoorState.CLOSING

    @property
    def is_online(self) -> bool:
        """Return True if switch is online."""
        return bool(self._data_model.online)

    @property
    def is_opening(self) -> bool:
        """Return True if garage dooor is opening."""
        return self.state_enum == GarageDoorState.OPENING

    @property
    def state_enum(self) -> GarageDoorState:
        """Return the garage door's state as enum."""
        return GarageDoorState(self._data_model.state)  # type: ignore[arg-type]

    def get_state(self) -> Any:
        """Return raw state value from model."""
        return self._data_model.state

    def update_data(self, new_val: dict, override: bool = False) -> None:  # type: ignore[override]
        """Update entity data and refresh typed model."""
        super().update_data(new_val=new_val, override=override)
        self._data_model = GarageDoorData.model_validate(self.data)

    async def set_state(self, state: int) -> None:
        """Set garage door's state."""
        assert self.alarm_panel
        await self.api.set_garage_door_state(
            self.alarm_panel.id, self.alarm_panel.partition_id, self.id, state
        )

    async def close(self) -> None:
        """Close the garage door."""
        await self.set_state(GarageDoorState.CLOSING)

    async def open(self) -> None:
        """Open the garage door."""
        await self.set_state(GarageDoorState.OPENING)
