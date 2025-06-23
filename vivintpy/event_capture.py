"""Doorbell media capture helper.

Listens for motion/person events emitted by ``Camera`` instances and saves a
fresh snapshot (and optional audio clip) to disk under
``MEDIA_ROOT/{system_id}/{device_id}/{timestamp}.jpg`` (and ``.m4a``).

The helper emits a ``capture_saved`` event on the originating ``Camera``
instance once the snapshot (and optional audio) has been persisted.  Other
components (e.g. the FastAPI WebSocket router) can subscribe to this event to
forward notifications to clients.

Set the ``MEDIA_ROOT`` environment variable to override the default ``media``
folder.

The helper is entirely self-contained: just instantiate with a connected
``Account`` and call :py:meth:`start`.  Call :py:meth:`stop` before shutting
 down the application to avoid leaked tasks.
"""
from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path

from .event_bus import publish as bus_publish
from typing import Callable, Dict, List, Set

import aiofiles

from .account import Account
from .devices.camera import Camera, DOORBELL_DING, MOTION_DETECTED

_LOGGER = logging.getLogger(__name__)

DEFAULT_MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "media"))

# Polling timeout for snapshot URL (seconds)
SNAPSHOT_TIMEOUT = 10.0
POLL_INTERVAL = 0.5

# Event name emitted when media capture completes.
CAPTURE_SAVED = "capture_saved"


class DoorbellCaptureManager:  # pylint: disable=too-many-instance-attributes
    """Capture snapshots/audio on doorbell activity events."""

    def __init__(self, account: Account, media_root: Path | str | None = None):
        self._account = account
        self._media_root = Path(media_root) if media_root else DEFAULT_MEDIA_ROOT
        self._semaphores: Dict[int, asyncio.Semaphore] = {}
        self._tasks: Set[asyncio.Task] = set()
        self._unsubscribes: List[Callable[[], None]] = []
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        """Register listeners on all doorbell cameras and begin capture."""
        if not self._account.connected:
            raise RuntimeError("Account must be connected before starting capture")

        # Ensure devices are loaded so that we can iterate cameras.
        if not self._account.systems:
            await self._account.refresh()

        for system in self._account.systems:
            for device in system.device_map.values():
                if isinstance(device, Camera):
                    self._register_camera(device)

        _LOGGER.info(
            "DoorbellCaptureManager started – listening on %s cameras, media_root=%s",
            len(self._semaphores),
            self._media_root,
        )

    async def stop(self) -> None:
        """Cancel in-flight tasks and unsubscribe callbacks."""
        self._stopped.set()
        for unsub in self._unsubscribes:
            unsub()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        _LOGGER.info("DoorbellCaptureManager stopped")

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _register_camera(self, camera: Camera) -> None:
        sem = self._semaphores.setdefault(camera.id, asyncio.Semaphore(1))

        async def _callback_wrapper(event_payload: dict) -> None:  # noqa: D401
            # Run the heavy work in a background task so we don't block the
            # PubNub thread – capture tasks can run concurrently (limited per
            # camera by semaphore).
            task = asyncio.create_task(self._process_event(camera, event_payload, sem))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

        # Register for both motion & ding events
        self._unsubscribes.append(camera.on(MOTION_DETECTED, _callback_wrapper))
        self._unsubscribes.append(camera.on(DOORBELL_DING, _callback_wrapper))

    async def _process_event(
        self, camera: Camera, payload: dict, sem: asyncio.Semaphore
    ) -> None:
        if self._stopped.is_set():
            return
        async with sem:
            _LOGGER.debug("Processing doorbell event for camera %s", camera.id)
            try:
                await camera.request_snapshot()
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Snapshot request failed for %s: %s", camera.id, exc)
                return

            # Poll for snapshot URL becoming available.
            deadline = asyncio.get_event_loop().time() + SNAPSHOT_TIMEOUT
            snapshot_url = None
            while asyncio.get_event_loop().time() < deadline:
                snapshot_url = camera.get_thumbnail_url()
                if snapshot_url:
                    break
                await asyncio.sleep(POLL_INTERVAL)

            if not snapshot_url:
                _LOGGER.warning("Timeout waiting for snapshot for camera %s", camera.id)
                return

            # Download snapshot
            try:
                jpg_bytes = await self._account.api._raw_get(snapshot_url)  # pylint: disable=protected-access
            except Exception as exc:  # noqa: BLE001
                _LOGGER.error("Failed to download snapshot %s: %s", snapshot_url, exc)
                return

            # Persist to media folder
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            target_dir = (
                self._media_root
                / str(camera.alarm_panel.system.id)
                / str(camera.id)
            )
            target_dir.mkdir(parents=True, exist_ok=True)
            jpg_path = target_dir / f"{timestamp}.jpg"
            audio_path: Path | None = None
            async with aiofiles.open(jpg_path, "wb") as fp:
                await fp.write(jpg_bytes)
            _LOGGER.info("Saved snapshot to %s", jpg_path)

            # Handle optional audio clip
            clip_url: str | None = None
            raw_msg = payload.get("message", {}) if isinstance(payload, dict) else {}
            if isinstance(raw_msg, dict):
                clip_url = (
                    raw_msg.get("clipUrl")
                    or raw_msg.get("clipURL")
                    or raw_msg.get("clip_url")
                )

            if clip_url:
                try:
                    audio_bytes = await self._account.api._raw_get(clip_url)  # pylint: disable=protected-access
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning("Failed to download audio clip %s: %s", clip_url, exc)
                else:
                    ext = mimetypes.guess_extension(
                        raw_msg.get("contentType", "audio/m4a")
                    ) or ".m4a"
                    audio_path = target_dir / f"{timestamp}{ext}"
                    async with aiofiles.open(audio_path, "wb") as fp:
                        await fp.write(audio_bytes)
                    _LOGGER.info("Saved audio clip to %s", audio_path)

            # Notify listeners that the capture has been persisted so that other
            # parts of the application (e.g. websocket relay) can react.
            camera.emit(
                CAPTURE_SAVED,
                {
                    "snapshot_path": str(jpg_path),
                    "audio_path": str(audio_path) if audio_path else None,
                    "system_id": camera.alarm_panel.system.id,
                    "device_id": camera.id,
                    "timestamp": timestamp,
                },
            )

            # Broadcast to application-wide event bus so other components (e.g.
            # WebSocket relays) can react.
            await bus_publish(
                CAPTURE_SAVED,
                {
                    "snapshot_path": str(jpg_path),
                    "audio_path": str(audio_path) if audio_path else None,
                    "system_id": camera.alarm_panel.system.id,
                    "device_id": camera.id,
                    "timestamp": timestamp,
                },
            )
