"""Response DTO for one robot."""
from __future__ import annotations

from pydantic import BaseModel

from ..entities.robot import Robot


class RobotResponse(BaseModel):
    id: str
    battery: float
    charge: str
    mode: str
    online: bool
    ts: str

    @classmethod
    def from_entity(cls, r: Robot) -> "RobotResponse":
        return cls(**r.to_dict())
