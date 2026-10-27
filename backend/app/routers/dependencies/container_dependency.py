"""Gives endpoints the app's services (the container built by AppFactory)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from starlette.requests import HTTPConnection

from ...config.container.container import Container


def get_container(conn: HTTPConnection) -> Container:
    # HTTPConnection covers both HTTP requests and WebSockets.
    return conn.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]
