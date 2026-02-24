"""WebSocket handler for real-time pipeline events."""

import asyncio
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from dich_truyen.services.events import EventBus, PipelineEvent


router = APIRouter()


@router.websocket("/ws/pipeline/{job_id}")
async def pipeline_websocket(websocket: WebSocket, job_id: str) -> None:
    """Stream pipeline events for a specific job via WebSocket."""
    await websocket.accept()

    event_bus: EventBus = websocket.app.state.event_bus
    queue: asyncio.Queue[PipelineEvent] = asyncio.Queue()

    # Subscribe to events for this job
    def on_event(event: PipelineEvent) -> None:
        if event.job_id == job_id:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop events if client can't keep up

    sub_id = event_bus.subscribe(on_event)

    try:
        while True:
            try:
                # Wait for events with timeout to check connection
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(event.to_dict())
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await websocket.send_json({"type": "heartbeat"})
            except WebSocketDisconnect:
                break
    finally:
        event_bus.unsubscribe(sub_id)
