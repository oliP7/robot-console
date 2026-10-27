"""Response DTO for errors (same shape as FastAPI's HTTPException body)."""
from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str
