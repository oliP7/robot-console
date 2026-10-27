"""Response DTO for an accepted (published) command."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CommandAcceptedResponse(BaseModel):
    command_id: str
    robot_id: str
    status: Literal["published"] = "published"
