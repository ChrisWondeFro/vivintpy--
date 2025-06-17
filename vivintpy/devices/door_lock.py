"""Module that implements the DoorLock class."""

from __future__ import annotations

from typing import cast

from ..const import LockAttribute
from ..const import ZWaveDeviceAttribute as Attribute
from ..models import DoorLockData
from . import BypassTamperDevice


class DoorLock(BypassTamperDevice):
    """Represents a vivint door lock device."""

    def __init__(self, data: dict | DoorLockData, alarm_panel):  # type: ignore[override]
        # Ensure typed model
        if isinstance(data, DoorLockData):
            model = data
        else:
            model = DoorLockData.model_validate(data)
        super().__init__(model, alarm_panel)
        # Store typed model for safe attribute access without shadowing base _model
        self._data_model: DoorLockData = model

    # ---------------------------------------------------------------------
    # Typed attribute helpers
    # ---------------------------------------------------------------------
    @property
    def is_locked(self) -> bool:
        """Return True if the door lock is locked."""
        return bool(self._data_model.state)

    @property
    def is_online(self) -> bool:
        """Return True if the door lock is online."""
        return bool(self._data_model.online)

    @property
    def user_code_list(self) -> list[int]:
        """Return the user code list."""
        return self._data_model.user_code_list

    async def set_state(self, locked: bool) -> None:
        """Set door lock's state."""
        assert self.alarm_panel
        await self.api.set_lock_state(
            self.alarm_panel.id, self.alarm_panel.partition_id, self.id, locked
        )

    async def lock(self) -> None:
        """Lock the door lock."""
        await self.set_state(True)

    async def unlock(self) -> None:
        """Unlock the door lock."""
        await self.set_state(False)
