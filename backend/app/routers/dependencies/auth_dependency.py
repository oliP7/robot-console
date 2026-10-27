"""Bearer-token check for HTTP routes (RouterManager attaches it where auth=True)."""
from __future__ import annotations

from fastapi import Header, HTTPException

from ...features.security.token_auth import TokenAuth
from .container_dependency import ContainerDep


def require_auth(c: ContainerDep, authorization: str | None = Header(default=None)) -> None:
    if not TokenAuth.matches(c.settings.auth_token, TokenAuth.bearer_token(authorization)):
        raise HTTPException(401, "invalid or missing token", headers={"WWW-Authenticate": "Bearer"})
