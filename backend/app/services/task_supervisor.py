"""Runs background loops forever and restarts them on a crash."""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from ..features.observability.metrics import Metrics

log = logging.getLogger("robot_console.supervisor")


class TaskSupervisor:
    def __init__(self, metrics: Metrics, restart_delay: float = 1.0):
        self._metrics = metrics
        self._delay = restart_delay
        self._tasks: list[asyncio.Task] = []

    def start(self, name: str, fn: Callable[[], Awaitable[None]]) -> None:
        """A crash is logged and the loop restarts, so one bad sample can never
        silently freeze the dashboard."""
        async def runner() -> None:
            while True:
                try:
                    await fn()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    self._metrics.task_restarts += 1
                    log.exception("background task %s crashed, restarting in %ss", name, self._delay)
                    await asyncio.sleep(self._delay)
        self._tasks.append(asyncio.create_task(runner(), name=name))

    @property
    def healthy(self) -> bool:
        return not any(t.done() for t in self._tasks)

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
