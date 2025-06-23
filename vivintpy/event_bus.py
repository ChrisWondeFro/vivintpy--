"""Simple in-process event bus for broadcasting internal events.

This lightweight helper lets separate components communicate across the
application without tight coupling.

Subscribers receive events via an *``asyncio.Queue``* which they must consume
regularly; otherwise the queue will fill up and subsequent publishes will drop
messages for that subscriber.

Usage
-----
>>> from vivintpy.event_bus import subscribe, publish, unsubscribe
>>> q = subscribe("capture_saved")
>>> await publish("capture_saved", {"path": "..."})
>>> payload = await q.get()
>>> await unsubscribe("capture_saved", q)
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import DefaultDict, Dict, Set

_logger = logging.getLogger(__name__)

_MAX_QUEUE_SIZE = 100  # per-subscriber buffer

# Mapping of event_name -> set[asyncio.Queue]
_subscribers: DefaultDict[str, Set[asyncio.Queue]] = defaultdict(set)


def subscribe(event_name: str) -> asyncio.Queue:  # noqa: D401
    """Subscribe to *event_name* and receive an *asyncio.Queue* of payloads."""
    q: asyncio.Queue = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
    _subscribers[event_name].add(q)
    _logger.debug("Subscribed queue %s to event '%s'", id(q), event_name)
    return q


async def unsubscribe(event_name: str, queue: asyncio.Queue) -> None:
    """Remove *queue* from *event_name* subscriber list and drain it."""
    _subscribers[event_name].discard(queue)
    _logger.debug("Unsubscribed queue %s from event '%s'", id(queue), event_name)
    # Allow pending tasks to finish reading before closing
    try:
        while not queue.empty():
            queue.get_nowait()
            queue.task_done()
    except Exception:  # noqa: BLE001
        pass


async def publish(event_name: str, payload: dict) -> None:  # noqa: D401
    """Broadcast *payload* to all queues subscribed to *event_name*.

    If a subscriber's queue is full, the event is **dropped** for that
    subscriber to avoid blocking the publisher.  A warning is logged so the
    subscriber can increase its consumption rate if needed.
    """
    queues = list(_subscribers.get(event_name, set()))
    for q in queues:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            _logger.warning("Event bus queue full (event=%s, subscriber=%s) – dropping.", event_name, id(q))
