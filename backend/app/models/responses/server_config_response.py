"""Response DTO for GET /api/config (public, read by the UI before sign-in)."""
from __future__ import annotations

from pydantic import BaseModel


class ServerConfigResponse(BaseModel):
    auth_required: bool
    modes: list[str]
    max_watch: int
    flush_ms: int
