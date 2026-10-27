"""Response DTO for a page of robots."""
from __future__ import annotations

from pydantic import BaseModel

from .robot_response import RobotResponse


class RobotPageResponse(BaseModel):
    total: int
    robots: list[RobotResponse]
