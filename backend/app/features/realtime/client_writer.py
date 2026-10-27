"""Sends queued work to one client. A slow or broken client is dropped and never
blocks the others."""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from ...config.settings import Settings
from ...repositories.robot_registry import RobotRegistry
from ..observability.metrics import Metrics
from .client_session import ClientSession
from .frame_encoder import FrameEncoder

log = logging.getLogger("robot_console.ws")


class ClientWriter:
    def __init__(self, state: RobotRegistry, settings: Settings, metrics: Metrics,
                 on_drop: Callable[[ClientSession], None]):
        self._state = state
        self._timeout = settings.send_timeout
        self._metrics = metrics
        self._on_drop = on_drop

    async def run(self, c: ClientSession) -> None:
        try:
            while True:
                await c.wake.wait()
                c.wake.clear()
                for frame in self._collect(c):
                    await asyncio.wait_for(c.ws.send_text(frame), self._timeout)
                    self._metrics.frames_sent += 1
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Unregister first, so the hub stops accumulating work for a dead client.
            self._on_drop(c)
            self._metrics.clients_dropped += 1
            log.info("dropping client: %r", exc)
            try:
                await c.ws.close(code=1011)
            except Exception as close_exc:
                # Usually the socket is already gone; nothing else to do.
                log.debug("close after drop failed: %r", close_exc)

    def _collect(self, c: ClientSession) -> list[str]:
        """Take everything queued for the client and turn it into frames."""
        frames: list[str] = []
        if c.full_index:
            c.full_index = False
            c.idx_add.clear()
            c.idx_rm.clear()
            frames.append(FrameEncoder.full_index(self._state.sorted_ids()))
        elif c.idx_add or c.idx_rm:
            frames.append(FrameEncoder.index_diff(c.idx_add, c.idx_rm))
            c.idx_add, c.idx_rm = set(), set()
        if c.pending:
            ids, c.pending = c.pending, set()
            parts = [p for p in map(self._state.json_of, ids) if p is not None]
            if parts:
                frames.append(FrameEncoder.delta(parts))
        if c.summary is not None:
            frames.append(c.summary)
            c.summary = None
        return frames
