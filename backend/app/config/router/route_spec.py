"""One entry of the RouterManager registry."""
from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType


@dataclass(frozen=True)
class RouteSpec:
    module: ModuleType      # a routers/ module exposing `router`
    prefix: str = ""
    tags: tuple[str, ...] = ()
    auth: bool = False      # require the bearer token on every route of the module
