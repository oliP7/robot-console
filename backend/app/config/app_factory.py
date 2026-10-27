"""Creates and configures the FastAPI application."""
from __future__ import annotations

import logging

from fastapi import FastAPI

from ..interfaces.message_broker import MessageBroker
from .container.container import Container
from .error_handling.error_handler_manager import ErrorHandlerManager
from .lifecycle.lifecycle_manager import LifecycleManager
from .logging.logging_config import LoggingConfig
from .router.router_manager import RouterManager
from .settings import Settings

log = logging.getLogger("robot_console.app")


class AppFactory:
    def __init__(self, settings: Settings, broker: MessageBroker | None = None):
        self._settings = settings
        self._broker = broker  # tests pass a fake; production builds the MQTT manager

    def create(self) -> FastAPI:
        s = self._settings
        LoggingConfig.configure(s.log_level)
        if not s.auth_token:
            log.warning("AUTH_TOKEN is not set: API and WebSocket are open (development mode)")

        container = Container.build(s, self._broker)
        app = FastAPI(title="Robot Console", lifespan=LifecycleManager(container).lifespan,
                      redoc_url=None, **self._docs_urls())
        app.state.container = container  # read by routers.dependencies.get_container
        ErrorHandlerManager(app).register()
        RouterManager(app).register()
        return app

    def _docs_urls(self) -> dict[str, str | None]:
        if self._settings.disable_docs:
            return {"docs_url": None, "openapi_url": None}
        return {"docs_url": "/api/docs", "openapi_url": "/api/openapi.json"}
