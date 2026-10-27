"""No telemetry has been seen from this robot id."""
from __future__ import annotations

from .app_error import AppError


class RobotNotFound(AppError):
    result = "unknown_robot"
    detail = "unknown robot"
