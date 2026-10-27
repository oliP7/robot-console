"""Request DTO for POST /api/robots/{id}/commands."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from ...protocols.robot_protocol import Command, Mode


class CommandRequest(BaseModel):
    """Allowlisted command vocabulary (see RobotProtocol). Anything else is a 422."""
    model_config = ConfigDict(extra="forbid")
    cmd: Command
    value: Mode | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.cmd == "set_mode" and self.value is None:
            raise ValueError("set_mode requires a value")
        if self.cmd != "set_mode" and self.value is not None:
            raise ValueError(f"{self.cmd} takes no value")
        return self
