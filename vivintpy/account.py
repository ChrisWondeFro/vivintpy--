"""Module that implements the Vivint class."""

from __future__ import annotations

import asyncio
import inspect
import logging

import aiohttp
from aiohttp.client_exceptions import ClientConnectionError
from .api import VivintSkyApi
from .const import (
    AuthUserAttribute,
    PubNubMessageAttribute,
    SystemAttribute,
    UserAttribute,
)
from .exceptions import VivintSkyApiError
from .stream import EventStream, get_default_stream
from .models import AuthUserData
from .system import System
from .utils import first_or_none

_LOGGER = logging.getLogger(__name__)


class Account:
    """Class for interacting with VivintSky API using asyncio."""

    def __init__(
        self,
        username: str,
        password: str | None = None,
        refresh_token: str | None = None,
        client_session: aiohttp.ClientSession | None = None,
        stream: EventStream | None = None,
    ):
        """Initialize an account."""
        self.__connected = False
        self.__load_devices = False
        self._api = VivintSkyApi(
            username=username,
            password=password,
            refresh_token=refresh_token,
            client_session=client_session,
        )
        self.systems: list[System] = []
        self._stream: EventStream = stream if stream is not None else get_default_stream(self._api)

    @property
    def api(self) -> VivintSkyApi:
        """Return the API."""
        return self._api

    @property
    def connected(self) -> bool:
        """Return True if connected."""
        return self.__connected

    @property
    def refresh_token(self) -> str | None:
        """Return the refresh token."""
        return self.api.tokens.get("refresh_token")

    async def connect(
        self, load_devices: bool = False, subscribe_for_realtime_updates: bool = False
    ) -> AuthUserData:
        """Connect to the VivintSky API."""
        _LOGGER.debug("Connecting to VivintSky")

        self.__load_devices = load_devices

        # initialize the vivintsky cloud session
        authuser_data = await self.api.connect()
        self.__connected = True

        # subscribe to pubnub for realtime updates
        if subscribe_for_realtime_updates:
            _LOGGER.debug("Subscribing for realtime updates")
            await self.subscribe_for_realtime_updates(authuser_data)

        # load all systems, panels and devices
        if self.__load_devices:
            _LOGGER.debug("Loading devices")
            await self.refresh(authuser_data)
        return authuser_data

    async def disconnect(self) -> None:
        """Disconnect from the API."""
        _LOGGER.debug("Disconnecting from VivintSky")
        if self.connected:
            await self._stream.disconnect()
        await self.api.disconnect()
        self.__connected = False

    async def verify_mfa(self, code: str) -> None:
        """Verify multi-factor authentication with the VivintSky API."""
        await self.api.verify_mfa(code)

        # load all systems, panels and devices
        if self.__load_devices:
            _LOGGER.debug("Loading devices")
            await self.refresh()

    async def refresh(self, authuser_data: AuthUserData | dict | None = None) -> None:
        """Refresh the account."""
        # ensure AuthUserData model
        if authuser_data is None:
            try:
                authuser_data = await self.api.get_authuser_data()
            except (ClientConnectionError, VivintSkyApiError):
                _LOGGER.error("Unable to refresh system(s)")
                return
        elif isinstance(authuser_data, dict):
            authuser_data = AuthUserData.model_validate(authuser_data)

        # use first user only
        if not authuser_data.users:
            return
        user = authuser_data.users[0]
        for auth_system in user.systems:
            # find existing system by panel id
            system = first_or_none(
                self.systems,
                lambda sys, auth_system=auth_system: sys.id == auth_system.panid,
            )
            if system:
                await system.refresh()
            else:
                full_system_data = await self.api.get_system_data(auth_system.panid)
                self.systems.append(
                    System(
                        data=full_system_data,
                        api=self.api,
                        name=auth_system.sn or "",
                        is_admin=auth_system.ad or False,
                    )
                )
        _LOGGER.debug("Refreshed %s system(s)", len(user.systems))

    async def subscribe_for_realtime_updates(
        self, authuser_data: AuthUserData | dict | None = None
    ) -> None:
        """Subscribe for realtime updates via EventStream."""
        # ensure raw authuser_data for stream
        if authuser_data is None:
            result = self.api.get_authuser_data()
            if inspect.isawaitable(result):
                authuser_data = await result
            else:
                authuser_data = result
        if isinstance(authuser_data, AuthUserData):
            raw = authuser_data.model_dump(by_alias=True)
        else:
            raw = authuser_data
        await self._stream.connect()
        await self._stream.subscribe(raw, self.handle_pubnub_message)

    def handle_pubnub_message(self, message: dict) -> None:
        """Handle a pubnub message."""
        panel_id = message.get(PubNubMessageAttribute.PANEL_ID)
        if not panel_id:
            _LOGGER.debug(
                "PubNub message ignored (no panel id specified): %s",
                message,
            )
            return

        system = first_or_none(self.systems, lambda system: system.id == panel_id)
        if not system:
            _LOGGER.debug("No system found with id %s: %s", panel_id, message)
            return

        system.handle_pubnub_message(message)
