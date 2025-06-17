import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.encoders import jsonable_encoder

from .. import deps
from vivintpy import Account
# from vivintpy.devices import Device # For more specific type hinting if needed for event_data

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Real-time Events"],
)

@router.websocket("/ws/events")
async def websocket_events_endpoint(
    websocket: WebSocket,
    current_user: deps.TokenData = Depends(deps.get_current_active_user),
    account: Account = Depends(deps.get_user_account)
):
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for user: {current_user.username}")

    if not account or not account.is_connected:
        logger.warning(f"Vivint account not available or not connected for user {current_user.username}. Closing WebSocket.")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Vivint service not available or not connected.")
        return
    
    # Check if event_stream is active (it should be if account.is_connected and lifespan manager worked)
    # The Account's add_event_listener should work regardless of the stream type, due to EventStream abstraction.
    if not account.event_stream or not account.event_stream.is_connected:
         logger.warning(f"Vivint event stream not available or not connected for user {current_user.username}. Closing WebSocket.")
         await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Vivint event stream not available.")
         return


    event_queue = asyncio.Queue()

    async def vivint_event_handler(event_name: str, event_data: Any):
        """
        Callback for vivintpy events. Puts event onto the client's queue.
        event_data can be a Pydantic model (e.g. a Device) or other data.
        """
        logger.debug(f"User {current_user.username} - Vivint event received: Name='{event_name}', Data='{type(event_data)}'")
        try:
            # Use jsonable_encoder to handle Pydantic models and other complex types
            payload = {"event_name": event_name, "data": jsonable_encoder(event_data)}
            await event_queue.put(payload)
        except Exception as e:
            logger.error(f"User {current_user.username} - Error processing or queueing Vivint event '{event_name}': {e}", exc_info=True)

    # Register the event handler with the shared Vivint Account
    try:
        account.add_event_listener(vivint_event_handler)
        logger.info(f"Vivint event listener added for WebSocket client: {current_user.username}")
    except Exception as e:
        logger.error(f"User {current_user.username} - Failed to add Vivint event listener: {e}", exc_info=True)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Failed to subscribe to Vivint events.")
        return

    try:
        while True:
            # Wait for an event from the queue and send it to the WebSocket client
            event_to_send = await event_queue.get()
            await websocket.send_json(event_to_send)
            logger.debug(f"Sent event to WebSocket client {current_user.username}: {event_to_send.get('event_name')}")
            event_queue.task_done()
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
        # Unregister the event handler from the shared Vivint Account
        try:
            account.remove_event_listener(vivint_event_handler)
            logger.info(f"Vivint event listener removed for WebSocket client: {current_user.username}")
        except Exception as e:
            logger.error(f"Error removing Vivint event listener for {current_user.username}: {e}", exc_info=True)
        
        # Ensure the websocket is closed if not already handled by WebSocketDisconnect
        if websocket.client_state != WebSocketDisconnect:
             try:
                await websocket.close()
             except RuntimeError:
                pass
        logger.info(f"WebSocket connection cleanup complete for {current_user.username}")
    #     print(f"WebSocket error: {e}")
    # finally:
        # Unsubscribe, cleanup
        # print("Cleaning up WebSocket connection")
    raise NotImplementedError("/ws/events not fully implemented")

