"""Unit tests for the generic ``Entity`` base class."""
from __future__ import annotations

from typing import Any, List

import pytest
from pydantic import BaseModel

from vivintpy.entity import Entity, UPDATE


# -----------------------------------------------------------------------------
# Dummy helpers
# -----------------------------------------------------------------------------


class _DummyModel(BaseModel):
    """Simple Pydantic model to validate Entity model-handling logic."""

    foo: int
    bar: str


class _RecordingEntity(Entity[_DummyModel]):
    """Entity subclass that records ``update_data`` calls for inspection."""

    def __init__(self, data: _DummyModel | dict):  # type: ignore[override]
        super().__init__(data)
        self.recorded_updates: List[tuple[dict, bool]] = []

    # pylint: disable=arguments-differ
    def update_data(self, new_val: dict, override: bool = False) -> None:  # type: ignore[override]
        self.recorded_updates.append((new_val, override))
        super().update_data(new_val, override)


# -----------------------------------------------------------------------------
# Tests – construction & model access
# -----------------------------------------------------------------------------


def test_entity_construction_with_model() -> None:
    """When constructed from a Pydantic model, ``Entity.model`` should return it and ``data`` should match the model's dump."""

    model = _DummyModel(foo=1, bar="baz")
    entity = Entity(model)  # type: ignore[type-var]

    assert entity.model == model
    assert entity.data == {"foo": 1, "bar": "baz"}


def test_entity_construction_with_raw_dict() -> None:
    """When constructed from a raw ``dict``, ``Entity.model`` should be ``None`` and ``data`` should preserve the payload."""

    payload = {"foo": 10, "bar": "spam"}
    entity = Entity(payload)  # type: ignore[type-var]

    assert entity.model is None
    assert entity.data == payload


# -----------------------------------------------------------------------------
# Tests – update_data behaviour
# -----------------------------------------------------------------------------


def test_update_data_merging() -> None:
    """``update_data`` should merge partial updates by default and refresh the typed model."""

    model = _DummyModel(foo=1, bar="baz")
    entity = Entity(model)  # type: ignore[type-var]

    entity.update_data({"bar": "qux"})

    # Raw dict was merged
    assert entity.data == {"foo": 1, "bar": "qux"}
    # Typed model was re-validated
    assert entity.model is not None and entity.model.bar == "qux"


def test_update_data_override() -> None:
    """With ``override=True`` the payload should be replaced and model validation errors ignored."""

    model = _DummyModel(foo=1, bar="baz")
    entity = Entity(model)  # type: ignore[type-var]

    # Override with an invalid payload (missing required fields)
    entity.update_data({"baz": 123}, override=True)

    # Raw data replaced entirely
    assert entity.data == {"baz": 123}
    # Model validation fails, so previous model should remain unchanged
    assert entity.model == model


# -----------------------------------------------------------------------------
# Tests – event subscription & emission
# -----------------------------------------------------------------------------


def test_on_emit_unsubscribe_pattern() -> None:
    """Callbacks registered via ``on`` should receive emitted events and can be unsubscribed."""

    entity = Entity({})  # type: ignore[type-var]
    received: List[Any] = []

    def _listener(payload: dict) -> None:  # noqa: D401 – callback
        received.append(payload)

    unsubscribe = entity.on("something", _listener)
    entity.emit("something", {"value": 42})

    assert received == [{"value": 42}]

    # After unsubscribe, callback should no longer fire
    unsubscribe()
    entity.emit("something", {"value": 43})

    assert received == [{"value": 42}]


# -----------------------------------------------------------------------------
# Tests – handle_pubnub_message default implementation
# -----------------------------------------------------------------------------


def test_handle_pubnub_message_delegates_to_update() -> None:
    """Default ``handle_pubnub_message`` should call ``update_data`` with the given message."""

    entity = _RecordingEntity({})  # type: ignore[type-var]
    message = {"alpha": 1}

    entity.handle_pubnub_message(message)

    # One update recorded with override=False
    assert entity.recorded_updates == [(message, False)]
    # The UPDATE event should have been emitted too
    assert entity.data["alpha"] == 1  # merged into raw dict

    # Ensure UPDATE event emitted by listening once
    updates: List[Any] = []
    entity.on(UPDATE, lambda d: updates.append(d))
    another_msg = {"beta": 2}
    entity.handle_pubnub_message(another_msg)
    assert len(updates) == 1 and updates[0]["data"] == another_msg
