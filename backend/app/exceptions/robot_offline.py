"""The robot is offline, so a command would be lost (robots use clean sessions)."""
from __future__ import annotations

from .app_error import AppError


class RobotOffline(AppError):
    result = "robot_offline"
    detail = "robot is offline"
