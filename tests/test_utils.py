"""Unit tests for vivintpy.utils helper functions."""

from __future__ import annotations

import asyncio
import re
import warnings
from typing import Any

import pytest

from vivintpy.utils import (
    add_async_job,
    first_or_none,
    generate_code_challenge,
    generate_state,
    send_deprecation_warning,
)


def test_first_or_none() -> None:
    data = [1, 2, 3, 4]
    assert first_or_none(data, lambda x: x % 2 == 0) == 2
    assert first_or_none(data, lambda x: x > 10) is None


@pytest.mark.asyncio
async def test_add_async_job_with_coroutine() -> None:
    async def coro(x: int) -> int:  # type: ignore[return-value]
        await asyncio.sleep(0)
        return x * 2

    task = add_async_job(coro(3))
    assert isinstance(task, asyncio.Future)
    result = await task
    assert result == 6


@pytest.mark.asyncio
async def test_add_async_job_with_function() -> None:
    def sync_func(x: int, y: int) -> int:
        return x + y

    task = add_async_job(sync_func, 3, 5)
    assert isinstance(task, asyncio.Future)
    # run_in_executor returns a Future; await for result
    result = await task
    assert result == 8


def test_send_deprecation_warning_and_logging(caplog: Any) -> None:
    # Capture warnings and logs
    with warnings.catch_warnings(record=True) as w, caplog.at_level("WARNING"):
        warnings.simplefilter("always", DeprecationWarning)
        send_deprecation_warning("old", "new")

        # One DeprecationWarning captured
        assert any(issubclass(item.category, DeprecationWarning) for item in w)

        # Logger warning emitted
        assert any("old has been deprecated" in record.message for record in caplog.records)


def test_generate_code_challenge_uniqueness_and_format() -> None:
    verifier1, challenge1 = generate_code_challenge()
    verifier2, challenge2 = generate_code_challenge()

    # All are str and non-empty
    assert all(isinstance(x, str) and x for x in (verifier1, verifier2, challenge1, challenge2))

    # Verifier should be URL safe (alphanumeric only)
    regex = re.compile(r"^[A-Za-z0-9]+$")
    assert regex.match(verifier1)
    assert regex.match(verifier2)

    # Challenges should not contain padding '='
    assert "=" not in challenge1
    assert "=" not in challenge2

    # Subsequent calls produce different strings (entropy)
    assert verifier1 != verifier2 or challenge1 != challenge2


def test_generate_state_entropy() -> None:
    state1 = generate_state()
    state2 = generate_state()

    assert isinstance(state1, str) and isinstance(state2, str)
    assert state1 != state2
