"""Drains the telemetry inbox in batches and applies samples to the robot registry."""
from __future__ import annotations

import asyncio
import time
from typing import Callable

from ..features.observability.metrics import Metrics
from ..interfaces.telemetry_source import TelemetrySource
from ..repositories.robot_registry import RobotRegistry
from .telemetry_parser import TelemetryParser

CHUNK = 4000  # max messages processed before yielding to the loop


class TelemetryIngestor:
    def __init__(self, source: TelemetrySource, state: RobotRegistry, metrics: Metrics,
                 interval: float, on_change: Callable[[], None] = lambda: None,
                 parser: TelemetryParser | None = None):
        self._source = source
        self._state = state
        self._metrics = metrics
        self._interval = interval
        self._on_change = on_change
        self._parser = parser or TelemetryParser()

    def process(self, topic: str, payload: bytes, now: float) -> None:
        parsed = self._parser.parse(topic, payload)
        if parsed is None:
            self._metrics.telemetry_invalid += 1
            return
        self._state.apply(parsed[0], parsed[1], now)

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            t0 = loop.time()
            await asyncio.sleep(self._interval)
            self._metrics.observe_lag(max(0.0, loop.time() - t0 - self._interval))
            while True:
                batch = self._source.drain(CHUNK)
                if not batch:
                    break
                now = time.monotonic()
                for topic, payload in batch:
                    self.process(topic, payload, now)
                if self._state.has_changes():
                    self._on_change()  # wake the flush loop (leading-edge push)
                await asyncio.sleep(0)  # let HTTP/WebSocket handlers run between chunks
