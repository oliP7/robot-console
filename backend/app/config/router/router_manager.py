"""Registers every router on the app, from one registry."""
from __future__ import annotations

from fastapi import Depends, FastAPI

from ...routers import health, live, robots, server_config
from ...routers.dependencies.auth_dependency import require_auth
from .route_spec import RouteSpec


class RouterManager:
    # The whole URL map. To add a router, add one line here (nothing else to keep in sync).
    # /ws authenticates inside the socket (first message), so it is not `auth` here.
    ROUTES: tuple[RouteSpec, ...] = (
        RouteSpec(health, tags=("operations",)),
        RouteSpec(server_config, prefix="/api", tags=("config",)),
        RouteSpec(robots, prefix="/api/robots", tags=("robots",), auth=True),
        RouteSpec(live, tags=("live",)),
    )

    def __init__(self, app: FastAPI):
        self._app = app

    def register(self) -> None:
        for spec in self.ROUTES:
            self._app.include_router(
                spec.module.router,
                prefix=spec.prefix,
                tags=list(spec.tags),
                dependencies=[Depends(require_auth)] if spec.auth else [],
            )
