"""The push loop: decides WHEN the hub flushes.

Flushes are throttled on the leading edge: the first change after a quiet period
is pushed at once (an operator's command shows up in milliseconds), and under
sustained load there is at most one flush per FLUSH_INTERVAL (batching). Once per
second it also runs the liveness sweep, rolls metrics and emits the summary.
"""
from __future__ import annotations

import asyncio
import time

from ...config.settings import Settings
from ...repositories.robot_registry import RobotRegistry
from ..observability.metrics import Metrics
from .hub import Hub


class FlushLoop:
    def __init__(self, hub: Hub, state: RobotRegistry, metrics: Metrics, settings: Settings):
        self._hub = hub
        self._state = state
        self._metrics = metrics
        self._interval = settings.flush_interval
        self._kick = asyncio.Event()

    def kick(self) -> None:
        """Signal that state changed. Cheap and idempotent; called by the ingestor."""
        self._kick.set()

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        next_second = loop.time() + 1.0
        while True:
            wait = next_second - loop.time()
            if wait > 0 and not self._kick.is_set():
                try:
                    await asyncio.wait_for(self._kick.wait(), wait)
                except TimeoutError:
                    pass
            self._kick.clear()
            summary = None
            if loop.time() >= next_second:
                next_second = loop.time() + 1.0
                self._state.sweep(time.monotonic())
                self._metrics.roll()
                summary = self._hub.summaries.build(len(self._hub.clients))
            self._hub.flush(summary)
            # Throttle: changes arriving now are batched into the next flush.
            await asyncio.sleep(self._interval)
