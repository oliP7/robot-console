"""Live channel: read-only push of index, deltas for watched robots, and summary."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket

from .dependencies.container_dependency import ContainerDep

router = APIRouter()


@router.websocket("/ws")
async def live(ws: WebSocket, c: ContainerDep) -> None:
    await c.live.handle(ws)
