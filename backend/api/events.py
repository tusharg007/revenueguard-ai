"""Redis-backed WebSocket event fan-out."""

from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket


EVENT_CHANNEL = "recovery_events"


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, event: dict[str, Any]) -> None:
        disconnected: list[WebSocket] = []
        for websocket in self.connections:
            try:
                await websocket.send_json(event)
            except Exception:
                disconnected.append(websocket)
        for websocket in disconnected:
            self.disconnect(websocket)


async def publish_event(redis_client: Any | None, event: dict[str, Any]) -> bool:
    """Publish an event for all API processes to relay to WebSocket clients."""
    if redis_client is None:
        return False
    try:
        await redis_client.publish(EVENT_CHANNEL, json.dumps(event, default=str))
        return True
    except Exception:
        return False


async def relay_redis_events(redis_client: Any, manager: ConnectionManager) -> None:
    """Relay Redis pub/sub messages to the local WebSocket connections."""
    pubsub = redis_client.pubsub()
    try:
        await pubsub.subscribe(EVENT_CHANNEL)
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            raw = message.get("data")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            try:
                event = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(event, dict):
                await manager.broadcast(event)
    finally:
        await pubsub.aclose()
