"""Module defining event stream interface and implementations."""
from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Protocol, Callable

from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub_asyncio import PubNubAsyncio
from pubnub.callbacks import SubscribeCallback
from pubnub.models.consumer.common import PNStatus
from pubnub.models.consumer.pubsub import PNMessageResult

from .api import VivintSkyApi
from .models import AuthUserData

# PubNub constants
PN_SUBSCRIBE_KEY = "sub-c-6fb03d68-6a78-11e2-ae8f-12313f022c90"
PN_CHANNEL = "PlatformChannel"

_LOGGER = logging.getLogger(__name__)


class EventStream(Protocol):
    """Protocol for event stream implementations."""
    async def connect(self) -> None:
        """Establish underlying connection."""
        ...

    async def subscribe(
        self, authuser_data: AuthUserData | dict, callback: Callable[[dict], None]
    ) -> None:
        """Subscribe to events and set callback."""
        ...

    async def disconnect(self) -> None:
        """Tear down the connection."""
        ...


class _VivintPubNubSubscribeListener(SubscribeCallback):
    """Internal PubNub callback that dispatches messages."""
    def __init__(
        self, message_received_callback: Callable[[dict], None]
    ) -> None:
        super().__init__()
        self.__message_received = message_received_callback

    def presence(self, pubnub: PubNubAsyncio, presence: object) -> None:
        _LOGGER.debug("Received presence: %s", presence)

    def status(self, pubnub: PubNubAsyncio, status: PNStatus) -> None:
        op = status.operation.name if isinstance(status.operation, Enum) else status.operation
        cat = status.category.name if isinstance(status.category, Enum) else status.category
        if status.is_error():
            _LOGGER.error(
                "PubNub status error - operation: %s, category: %s, error: %s",
                op,
                cat,
                status.error_data.information,
            )
        else:
            _LOGGER.debug(
                "PubNub status update - operation: %s, category: %s",
                op,
                cat,
            )

    def message(self, pubnub: PubNubAsyncio, message: PNMessageResult) -> None:
        self.__message_received(message.message)


class PubNubStream:
    """EventStream implementation using PubNub."""
    def __init__(self, api: VivintSkyApi) -> None:
        self._api = api
        self._pubnub: PubNubAsyncio | None = None
        self._listener: _VivintPubNubSubscribeListener | None = None

    async def connect(self) -> None:
        """No-op: PubNub connection is started at subscribe."""
        return

    async def subscribe(
        self, authuser_data: AuthUserData | dict, callback: Callable[[dict], None]
    ) -> None:
        # Ensure we have a typed model
        if isinstance(authuser_data, AuthUserData):
            auth_model = authuser_data
        else:
            auth_model = AuthUserData.model_validate(authuser_data)
        if not auth_model.users:
            _LOGGER.error("No users present in AuthUser data; cannot subscribe")
            return
        user = auth_model.users[0]
        mbc = user.message_broadcast_channel
        uid = user.id
        if not mbc:
            _LOGGER.error("Missing message broadcast channel in AuthUser data; skipping subscribe")
            return
        if not uid:
            _LOGGER.error("Missing user ID in AuthUser data; skipping subscribe")
            return
        # configure PubNub
        pnconfig = PNConfiguration()
        pnconfig.subscribe_key = PN_SUBSCRIBE_KEY
        pnconfig.user_id = f"pn-{uid.upper()}"
        self._pubnub = PubNubAsyncio(pnconfig)
        self._listener = _VivintPubNubSubscribeListener(callback)
        self._pubnub.add_listener(self._listener)
        pn_channel = f"{PN_CHANNEL}#{mbc}"
        self._pubnub.subscribe().channels(pn_channel).with_presence().execute()

    async def disconnect(self) -> None:
        """Clean up PubNub listener and stop."""
        if not self._pubnub or not self._listener:
            return
        try:
            self._pubnub.remove_listener(self._listener)
            self._pubnub.unsubscribe_all()
            # wait for leave helper tasks
            tasks = [
                task for task in asyncio.all_tasks()
                if getattr(getattr(task.get_coro(), "cr_code", None), "co_name", None)
                == "_send_leave_helper"
            ]
            if tasks:
                await asyncio.gather(*tasks)
            await self._pubnub.stop()
        except Exception as e:
            _LOGGER.error("Error during PubNub disconnect: %s", e)


class MqttStream:
    """Placeholder EventStream for MQTT."""
    def __init__(self, api: VivintSkyApi) -> None:
        self._api = api

    async def connect(self) -> None:
        raise NotImplementedError("MQTT stream not implemented")

    async def subscribe(
        self, authuser_data: AuthUserData | dict, callback: Callable[[dict], None]
    ) -> None:
        raise NotImplementedError("MQTT stream not implemented")

    async def disconnect(self) -> None:
        raise NotImplementedError("MQTT stream not implemented")


def get_default_stream(api: VivintSkyApi) -> EventStream:
    """Return default EventStream implementation."""
    return PubNubStream(api)
