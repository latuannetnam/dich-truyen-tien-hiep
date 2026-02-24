"""Event pub/sub system for pipeline progress.

Enables decoupled communication between pipeline execution and display layers:
- CLI subscribes → Rich console output (future refactor)
- Web subscribes → WebSocket → React state updates
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class PipelineEvent:
    """A single pipeline event."""

    type: str
    data: dict = field(default_factory=dict)
    job_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Serialize for WebSocket JSON transport."""
        return {
            "type": self.type,
            "data": self.data,
            "job_id": self.job_id,
            "timestamp": self.timestamp,
        }


class EventBus:
    """Simple synchronous event bus.

    Subscribers receive events synchronously in the emitter's thread.
    For WebSocket delivery, the subscriber puts events into an asyncio.Queue.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, Callable[[PipelineEvent], None]] = {}

    def subscribe(self, callback: Callable[[PipelineEvent], None]) -> str:
        """Register a callback. Returns subscription ID for unsubscribe."""
        sub_id = str(uuid.uuid4())
        self._subscribers[sub_id] = callback
        return sub_id

    def unsubscribe(self, sub_id: str) -> None:
        """Remove a subscriber by ID."""
        self._subscribers.pop(sub_id, None)

    def emit(self, event: PipelineEvent) -> None:
        """Send event to all subscribers."""
        for callback in list(self._subscribers.values()):
            try:
                callback(event)
            except Exception:
                pass  # Never let a bad subscriber crash the emitter
