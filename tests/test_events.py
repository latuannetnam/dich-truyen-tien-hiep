"""Tests for the event pub/sub system."""

import asyncio

import pytest

from dich_truyen.services.events import EventBus, PipelineEvent


def test_event_bus_subscribe_and_emit():
    """Synchronous callback receives events."""
    received = []
    bus = EventBus()
    bus.subscribe(lambda event: received.append(event))
    bus.emit(PipelineEvent(type="test", data={"key": "value"}))
    assert len(received) == 1
    assert received[0].type == "test"
    assert received[0].data["key"] == "value"


def test_event_bus_multiple_subscribers():
    """Multiple subscribers each get a copy of the event."""
    count = {"a": 0, "b": 0}
    bus = EventBus()
    bus.subscribe(lambda _: count.__setitem__("a", count["a"] + 1))
    bus.subscribe(lambda _: count.__setitem__("b", count["b"] + 1))
    bus.emit(PipelineEvent(type="test", data={}))
    assert count["a"] == 1
    assert count["b"] == 1


def test_event_bus_unsubscribe():
    """Unsubscribed callback no longer receives events."""
    received = []
    bus = EventBus()
    callback = lambda event: received.append(event)
    sub_id = bus.subscribe(callback)
    bus.emit(PipelineEvent(type="first", data={}))
    bus.unsubscribe(sub_id)
    bus.emit(PipelineEvent(type="second", data={}))
    assert len(received) == 1
    assert received[0].type == "first"


def test_pipeline_event_to_dict():
    """Event serializes to dict for WebSocket JSON transport."""
    event = PipelineEvent(
        type="chapter_translated",
        data={"chapter": 5, "worker": 1, "total": 100},
        job_id="abc-123",
    )
    d = event.to_dict()
    assert d["type"] == "chapter_translated"
    assert d["job_id"] == "abc-123"
    assert d["data"]["chapter"] == 5
    assert "timestamp" in d
