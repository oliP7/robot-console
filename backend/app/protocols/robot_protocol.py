"""Vocabulary of the robot MQTT protocol (mirrors robot.py). Defined once here."""
from __future__ import annotations

import re
from typing import Final, Literal, get_args

Mode = Literal["idle", "working", "error"]
ChargeState = Literal["charging", "discharging"]
Command = Literal["toggle_charge", "set_mode", "kick"]


class RobotProtocol:
    MODES: Final[tuple[str, ...]] = get_args(Mode)
    CHARGE_STATES: Final[tuple[str, ...]] = get_args(ChargeState)
    COMMANDS: Final[tuple[str, ...]] = get_args(Command)

    ID_MAX_LEN: Final = 64
    ID_PATTERN: Final = rf"^[A-Za-z0-9_-]{{1,{ID_MAX_LEN}}}$"
    ID_RE: Final = re.compile(ID_PATTERN)

    LOW_BATTERY_TENTHS: Final = 200  # below 20.0 percent
    TELEMETRY_FILTER: Final = "robots/+/telemetry"

    @staticmethod
    def command_topic(robot_id: str) -> str:
        return f"robots/{robot_id}/cmd"

    @staticmethod
    def is_valid_id(robot_id: object) -> bool:
        return isinstance(robot_id, str) and RobotProtocol.ID_RE.fullmatch(robot_id) is not None
