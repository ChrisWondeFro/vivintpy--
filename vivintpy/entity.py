"""Module that implements the Entity class."""

from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar, Optional

from pydantic import BaseModel

UPDATE = "update"

TModel = TypeVar("TModel", bound=BaseModel)


class Entity(Generic[TModel]):
    """Describe a Vivint entity backed by an optional Pydantic model.

    Subclasses can gradually migrate to typed models by passing a ``BaseModel``
    instance instead of a raw ``dict``.  Until then, ``_data_model`` remains
    ``None`` and behaviour is identical to the legacy dict‐only implementation.
    """

    def __init__(self, data: TModel | dict):
        """Initialize an entity.

        Parameters
        ----------
        data : BaseModel | dict
            Either a Pydantic model (preferred) or the legacy raw payload.
        """
        if isinstance(data, BaseModel):
            # store typed model and keep raw in sync
            self._data_model: Optional[TModel] = data  # type: ignore[assignment]
            # Use `round_trip=True` so that **all** original input keys—including
            # those not explicitly defined on the Pydantic model—are preserved in
            # the raw ``__data`` mapping.  Some higher-level helpers (e.g.
            # ``VivintDevice.serial_number``) still rely on these extra keys
            # being available.
            self.__data: dict = data.model_dump(by_alias=True, round_trip=True)
        else:
            self._data_model = None  # type: ignore[assignment]
            self.__data = data  # legacy raw dict
        self._listeners: dict[str, list[Callable]] = {}

    @property
    def data(self) -> dict:
        """Return entity's raw data (authoritative)."""
        return self.__data

    @property
    def model(self) -> Optional[TModel]:
        """Return the typed model if available."""
        return self._data_model

    def update_data(self, new_val: dict, override: bool = False) -> None:
        """Update entity's raw and typed representation.

        Parameters
        ----------
        new_val : dict
            Partial or full update from PubNub/API.
        override : bool, default ``False``
            If ``True`` replace the entire payload; otherwise merge.
        """
        if override:
            self.__data = new_val
        else:
            self.__data.update(new_val)

        # Keep typed model in sync if we have one available
        if self._data_model is not None:
            try:
                self._data_model = self._data_model.model_validate(self.__data)  # type: ignore[assignment]
            except Exception:  # noqa: BLE001 – ignore validation errors for forward-compat
                pass

        self.emit(UPDATE, {"data": new_val})

    def handle_pubnub_message(self, message: dict) -> None:
        """Handle a pubnub message directed to this entity.

        Default behaviour is to treat the message as a partial update.
        Subclasses can override for device-specific semantics.
        """
        self.update_data(message)

    def on(  # pylint: disable=invalid-name
        self, event_name: str, callback: Callable
    ) -> Callable:
        """Register an event callback."""
        listeners: list = self._listeners.setdefault(event_name, [])
        listeners.append(callback)

        def unsubscribe() -> None:
            """Unsubscribe listeners."""
            if callback in listeners:
                listeners.remove(callback)

        return unsubscribe

    def emit(self, event_name: str, data: dict) -> None:
        """Run all callbacks for an event."""
        for listener in self._listeners.get(event_name, []):
            try:
                listener(data)
            except:  # noqa E722 # pylint: disable=bare-except
                pass
