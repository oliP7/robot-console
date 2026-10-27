"""Response DTO for health and readiness probes."""
from __future__ import annotations

from pydantic import BaseModel


class StatusResponse(BaseModel):
    status: str
