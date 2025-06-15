"""Module that implements the System class."""

from __future__ import annotations

import logging

from .api import VivintSkyApi
from .const import PubNubMessageAttribute
from .const import SystemAttribute as Attribute
from .devices.alarm_panel import AlarmPanel
from .entity import Entity
from .models import SystemData
from .user import User
from .utils import first_or_none

_LOGGER = logging.getLogger(__name__)


class System(Entity):
    """Describe a vivint system."""

    def __init__(self, data: SystemData, api: VivintSkyApi, *, name: str, is_admin: bool):
        """Initialize a system with typed SystemData."""
        # keep both typed and raw representations in sync
        self._data_model: SystemData = data
        super().__init__(data)
        self._api = api
        self._name = name
        self._is_admin = is_admin
        # Build nested entities using typed model
        self.alarm_panels: list[AlarmPanel] = [
            AlarmPanel(panel_data, self) for panel_data in self._data_model.system.par
        ]
        self.users = [
            User(user_data, self) for user_data in self._data_model.system.users
        ]

    @property
    def api(self) -> VivintSkyApi:
        """Return the API."""
        return self._api

    @property
    def id(self) -> int:  # pylint: disable=invalid-name
        """System's id."""
        return int(self._data_model.system.panid)

    @property
    def is_admin(self) -> bool:
        """Return True if the user is an admin for this system."""
        return self._is_admin

    @property
    def name(self) -> str:
        """System's name."""
        return self._name

    async def refresh(self) -> None:
        """Reload a system's data from the VivintSky API."""
        # Fetch an updated SystemData model and update internal views
        system_data = await self.api.get_system_data(self.id)
        self._data_model = system_data  # refresh typed model
        system_dict = system_data.model_dump(by_alias=True)
        # keep raw data (Entity) in sync for legacy consumers
        self.update_data(system_dict, override=True)

        for panel_data in system_dict[Attribute.SYSTEM][Attribute.PARTITION]:
            alarm_panel = first_or_none(
                self.alarm_panels,
                lambda panel, panel_data=panel_data: panel.id  # type: ignore
                == panel_data[Attribute.PANEL_ID]
                and panel.partition_id == panel_data[Attribute.PARTITION_ID],
            )
            if alarm_panel:
                alarm_panel.refresh(panel_data)
            else:
                self.alarm_panels.append(AlarmPanel(panel_data, self))

    def update_user_data(self, data: list[dict]) -> None:
        """Update user data."""
        for d in data:
            user = first_or_none(self.users, lambda user: user.id == d["_id"])
            if not user:
                _LOGGER.debug("User not found for system %s: %s", self.id, d)
                return
            user.handle_pubnub_message(d)

    def handle_pubnub_message(self, message: dict) -> None:
        """Handle a pubnub message."""
        if (message_type := message[PubNubMessageAttribute.TYPE]) == "account_system":
            # this is a system message
            operation = message.get(PubNubMessageAttribute.OPERATION)
            data = message.get(PubNubMessageAttribute.DATA)

            if data and operation == "u":
                if Attribute.USERS in data:
                    self.update_user_data(data[Attribute.USERS])
                    del data[Attribute.USERS]
                self.update_data(data)

        elif message_type == "account_partition":
            # this is a message for one of the devices attached to this system
            partition_id = message.get(PubNubMessageAttribute.PARTITION_ID)
            if not partition_id:
                _LOGGER.debug(
                    "Ignoring account partition message (no partition id specified for system %s): %s",
                    self.id,
                    message,
                )
                return

            # Only process if there is a data payload; otherwise ignore noisy heart-beat messages
            if PubNubMessageAttribute.DATA not in message:
                _LOGGER.debug(
                    "Ignoring account partition message (no data for system %s, partition %s): %s",
                    self.id,
                    partition_id,
                    message,
                )
                return

            alarm_panel = first_or_none(
                self.alarm_panels,
                lambda panel: panel.partition_id == partition_id,
            )

            if not alarm_panel:
                _LOGGER.debug(
                    "No alarm panel found for system %s, partition %s",
                    self.id,
                    partition_id,
                )
                return

            alarm_panel.handle_pubnub_message(message)
        else:
            _LOGGER.warning(
                "Unknown message received by system %s: %s", self.id, message
            )
