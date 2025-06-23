import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from .. import deps
from vivintpy import Account
from vivintpy.event_bus import subscribe as bus_subscribe, unsubscribe as bus_unsubscribe
# from vivintpy.devices import Device # For more specific type hinting if needed for event_data

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Real-time Events"],
)

@router.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket):
    """Authenticated WebSocket that streams Vivint events.

    Because browsers cannot set custom headers on WebSocket requests, the JWT
    access token must be supplied via a `token` query-string parameter. This
    handler manually validates the token and creates a per-user Vivint Account
    instance instead of relying on normal FastAPI dependencies that expect an
    `Authorization` header.
    """

    # ------------------------- Auth Handshake -------------------------
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token query param")
        return

    # Validate JWT & retrieve Redis-backed Vivint refresh token
    redis_client = await deps.get_redis_client()
    try:
        current_user = await deps.get_current_user(token=token, redis_client=redis_client)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        return

    # Build Vivint Account from stored refresh token
    vivint_refresh_token = await redis_client.get(f"user:{current_user.username}:vivint_refresh_token")
    if not vivint_refresh_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="No Vivint session; re-authenticate")
        return
    if isinstance(vivint_refresh_token, bytes):
        vivint_refresh_token = vivint_refresh_token.decode()

    account = Account(username=current_user.username, refresh_token=vivint_refresh_token)
    try:
        await account.connect(load_devices=True)
        # Prepare PubNub EventStream for real-time updates (vivintpy >=0.3)
        stream = getattr(account, "_stream", None)
        if stream is None:
            raise RuntimeError("Vivint Account missing _stream implementation – cannot stream events")
        # Ensure PubNub connection is up and subscribed using the primary user's AuthUserData
        authuser_data = await account.api.get_authuser_data()
        await stream.connect()
        # We will subscribe later after websocket.accept because we need event_queue ready
    except Exception as exc:
        logger.error("Failed to connect Vivint account for WS: %s", exc, exc_info=True)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Vivint connect failed")
        return
    await websocket.accept()
    logger.info("WebSocket connection accepted for user: %s", current_user.username)

    # Subscribe to global event bus for capture_saved notifications
    bus_queue = bus_subscribe("capture_saved")
    bus_task: asyncio.Task | None = None

    async def _bus_listener() -> None:  # noqa: D401
        while True:
            payload = await bus_queue.get()
            # Optional filtering by system/device as query params
            if system_id_filter and payload.get("system_id") != system_id_filter:
                continue
            if device_id_filter and payload.get("device_id") != device_id_filter:
                continue
            try:
                event_queue.put_nowait({
                    "event_name": "capture_saved",
                    **payload,
                })
            except asyncio.QueueFull:
                logger.warning("WebSocket queue full for capture_saved event; closing.")
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Client too slow to consume events.")
                break
    bus_task = asyncio.create_task(_bus_listener())

    # Optional per-client filtering based on query parameters
    query_params = websocket.query_params
    system_id_filter = int(query_params.get("system_id")) if query_params.get("system_id") else None
    device_id_filter = int(query_params.get("device_id")) if query_params.get("device_id") else None



    # Queue with back-pressure protection (max 1000 messages).
    # If client lags and the queue overflows we will close the connection.
    event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)

    # Callback invoked by PubNubStream (signature: message: dict)
    def pubnub_callback(message: dict):
        """Callback from Vivint EventStream.

        Applies optional system/device filtering and enqueues the payload.
        If the queue is full, close the WebSocket with code 1011.
        """
        # First, let the account update its state
        try:
            account.handle_pubnub_message(message)
        except Exception:  # noqa: BLE001
            logger.debug("Error forwarding PubNub message to account handler", exc_info=True)

        # Derive high-level event info
        event_type = message.get("t")  # PubNubMessageAttribute.TYPE alias
        operation = message.get("op")  # create/update/etc.
        panel_id = message.get("panid")
        device_id = None
        if (data := message.get("da")) and isinstance(data, dict):
            # For device events, try to extract _id
            if (devs := data.get("d")) and isinstance(devs, list) and devs:
                device_id = devs[0].get("_id")
            else:
                device_id = data.get("_id")
        # Basic filtering
        if system_id_filter is not None and panel_id != system_id_filter:
            return
        if device_id_filter is not None and device_id != device_id_filter:
            return

        payload = {
            "event_name": f"{event_type}:{operation}" if operation else event_type,
            "panel_id": panel_id,
            "device_id": device_id,
            "raw": message,
        }
        try:
            event_queue.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning("WebSocket queue full for user %s; closing connection.", current_user.username)
            asyncio.create_task(
                websocket.close(
                    code=status.WS_1011_INTERNAL_ERROR,
                    reason="Client too slow to consume events.",
                )
            )

    # Subscribe to PubNub stream so we receive realtime events
    try:
        await stream.subscribe(authuser_data, pubnub_callback)
        logger.info("PubNub stream subscribed for WebSocket client: %s", current_user.username)
    except Exception as e:
        logger.error("User %s - Failed to subscribe to PubNub stream: %s", current_user.username, e, exc_info=True)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Failed to subscribe to Vivint events.")
        return

    try:
        while True:
            try:
                # Wait up to 30 s for the next event; otherwise send heartbeat
                event_to_send = await asyncio.wait_for(event_queue.get(), timeout=30)
                await websocket.send_json(event_to_send)
                logger.debug(f"Sent event to WebSocket client {current_user.username}: {event_to_send.get('event_name')}")
                event_queue.task_done()
            except asyncio.TimeoutError:
                # Idle – send heartbeat ping
                await websocket.send_json({"event_name": "ping"})
    except WebSocketDisconnect:
        logger.info(f"WebSocket client {current_user.username} disconnected.")
    except asyncio.CancelledError:
        logger.info(f"WebSocket task for {current_user.username} was cancelled.")
        # Propagate cancellation if needed, or just clean up
    except Exception as e:
        logger.error(f"Error in WebSocket loop for {current_user.username}: {e}", exc_info=True)
        # Attempt to close gracefully if not already disconnected
        if websocket.client_state != WebSocketDisconnect:
            try:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="An unexpected server error occurred.")
            except RuntimeError: # Handle cases where websocket is already closing
                pass
    finally:
        # Cancel bus listener and unsubscribe
        if bus_task:
            bus_task.cancel()
            await asyncio.gather(bus_task, return_exceptions=True)
            await bus_unsubscribe("capture_saved", bus_queue)

        # Unregister the event handler from the Vivint EventStream
        if stream:
            try:
                await stream.disconnect()
                logger.info("PubNub stream disconnected for %s", current_user.username)
            except Exception as e:
                logger.error("Error disconnecting PubNub stream for %s: %s", current_user.username, e, exc_info=True)

        # Drain outstanding events before shutdown
        try:
            await asyncio.wait_for(event_queue.join(), timeout=3)
        except asyncio.TimeoutError:
            pass

        # Close EventStream then Account session
        try:
            if hasattr(account, "disconnect_stream"):
                await account.disconnect_stream()
        except Exception:
            pass
        try:
            await account.disconnect()
        except Exception:
            pass

        # Ensure the websocket is closed if not already handled
        if websocket.client_state != WebSocketDisconnect:
            try:
                await websocket.close()
            except RuntimeError:
                pass
        logger.info("WebSocket connection cleanup complete for %s", current_user.username)
    #     print(f"WebSocket error: {e}")
    # finally:
        # Unsubscribe, cleanup
        # print("Cleaning up WebSocket connection")
    

