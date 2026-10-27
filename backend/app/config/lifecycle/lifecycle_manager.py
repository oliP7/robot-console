"""Application startup and shutdown."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from ..container.container import Container

logger = logging.getLogger("robot_console.lifecycle")


class LifecycleManager:
    """Starts the broker connection and the supervised background loops, and
    stops them in reverse order.

    It holds its container as an instance (not a global) so tests can build
    several apps side by side, each with its own fake broker.
    """

    def __init__(self, container: Container):
        self._c = container

    @asynccontextmanager
    async def lifespan(self, _: FastAPI) -> AsyncGenerator[None, None]:
        c = self._c
        # Startup. The MQTT connection is made in the background, so the service starts
        # (and reports "not ready" on /readyz) even if the broker is not up yet.
        c.broker.start()
        c.supervisor.start("ingest", c.ingestor.run)
        c.supervisor.start("flush", c.flush_loop.run)
        logger.info("started: ingest and flush loops running")
        try:
            yield
        finally:
            # Shutdown
            await c.supervisor.stop()
            c.broker.stop()
            logger.info("stopped")
