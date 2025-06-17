"""Global test fixtures for VivintPy test suite.

This autouse fixture tracks all aiohttp ClientSession objects created during each
pytest test case and ensures they are properly closed when the test finishes.

It eliminates ResourceWarning messages about unclosed client sessions without
requiring individual tests to manually close or disconnect the API objects that
create internal sessions.
"""
from __future__ import annotations

import asyncio
from typing import List

import aiohttp
import pytest


class _TrackingClientSession(aiohttp.ClientSession):
    """Subclass of ClientSession that registers every created instance."""

    # Class-level registry to hold references until they are explicitly closed
    _sessions: List[aiohttp.ClientSession] = []

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.__class__._sessions.append(self)


import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def ensure_client_sessions_closed(monkeypatch):  # type: ignore[missing-type-doc]
    """Autouse fixture that guarantees all ClientSession objects are closed.

    1. Monkey-patch ``aiohttp.ClientSession`` with a tracking subclass so every
       instantiation is recorded.
    2. After each test yields, iterate over any still-open sessions and close
       them to avoid ResourceWarning noise.
    """

    # Patch ClientSession *early* in the test before user code imports it.
    monkeypatch.setattr(aiohttp, "ClientSession", _TrackingClientSession)
    yield
    # After the test completes, close any lingering sessions.
    close_tasks = [sess.close() for sess in list(_TrackingClientSession._sessions) if not sess.closed]
    if close_tasks:
        # Use gather to close concurrently; suppress any exceptions since we are
        # running in teardown context where event loop is still active.
        await asyncio.gather(*close_tasks, return_exceptions=True)

    # Clear registry to avoid cross-test pollution.
    _TrackingClientSession._sessions.clear()
