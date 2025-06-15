"""Module that implements the User class."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from .const import UserAttribute as Attribute
from .entity import Entity
from .models import SystemUserData

if TYPE_CHECKING:
    from .system import System

ADD_LOCK = f"{Attribute.LOCK_IDS}.1"


class User(Entity):
    """Describe a Vivint user backed by a typed Pydantic model."""

    def __init__(self, data: SystemUserData | dict, system: System):
        """Initialize a user.

        Parameters
        ----------
        data : SystemUserData | dict
            Either a pre-validated `SystemUserData` model or the raw dict from the API.
        system : System
            Parent system instance.
        """
        if isinstance(data, SystemUserData):
            model = data
        else:
            model = SystemUserData.model_validate(data)
        self._data_model: SystemUserData = model
        # Initialize Entity with typed model (Entity keeps raw dict in sync)
        super().__init__(model)
        self._system = system

    def __repr__(self) -> str:
        """Return custom __repr__ of user."""
        return f"<{self.__class__.__name__} {self.id}, {self.name}{' (admin)' if self.is_admin else ''}>"

    @property
    def has_lock_pin(self) -> bool:
        """Return True if the user has pins."""
        return bool(self._data_model.has_lock_pin) if self._data_model.has_lock_pin is not None else False

    @property
    def has_panel_pin(self) -> bool:
        """Return True if the user has pins."""
        return bool(self._data_model.has_panel_pin) if self._data_model.has_panel_pin is not None else False

    @property
    def has_pins(self) -> bool:
        """Return True if the user has pins."""
        return bool(self._data_model.has_pins) if self._data_model.has_pins is not None else False

    @property
    def has_remote_access(self) -> bool:
        """Return True if the user has remote access."""
        return bool(self._data_model.remote_access) if self._data_model.remote_access is not None else False

    @property
    def id(self) -> int:  # pylint: disable=invalid-name
        """User's id."""
        return int(self._data_model.id)

    @property
    def is_admin(self) -> bool:
        """Return True if the user is an admin."""
        return bool(self._data_model.admin) if self._data_model.admin is not None else False

    @property
    def is_registered(self) -> bool:
        """Return True if the user is registered."""
        return bool(self._data_model.registered) if self._data_model.registered is not None else False

    @property
    def lock_ids(self) -> list[int]:
        """User's lock ids."""
        return self._data_model.lock_ids

    @property
    def name(self) -> str:
        """User's name."""
        return str(self._data_model.name) if self._data_model.name is not None else ""

    def update_data(self, new_val: dict, override: bool = False) -> None:  # type: ignore[override]
        """Update raw data then refresh typed model."""
        super().update_data(new_val, override=override)
        self._data_model = SystemUserData.model_validate(self.data)

    def handle_pubnub_message(self, message: dict) -> None:
        """Handle a pubnub message addressed to this user."""
        if ADD_LOCK in message:
            message[Attribute.LOCK_IDS] = self.lock_ids + [message[ADD_LOCK]]
            del message[ADD_LOCK]
        self.update_data(message)
