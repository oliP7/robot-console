"""Counters across all robots, maintained incrementally so the summary is O(1).

Only ONLINE robots are counted: a robot is added (+1) when it comes online or
changes, and removed (-1) before a change or when it goes offline.
"""
from __future__ import annotations

from ..models.entities.robot import Robot
from ..protocols.robot_protocol import RobotProtocol


class RobotCounters:
    def __init__(self) -> None:
        self.online = 0
        self.by_mode = {m: 0 for m in RobotProtocol.MODES}
        self.by_charge = {c: 0 for c in RobotProtocol.CHARGE_STATES}
        self.battery10_sum = 0
        self.low_battery = 0

    def add(self, r: Robot) -> None:
        self._account(r, +1)

    def remove(self, r: Robot) -> None:
        self._account(r, -1)

    def _account(self, r: Robot, sign: int) -> None:
        self.online += sign
        self.by_mode[r.mode] += sign
        self.by_charge[r.charge] += sign
        self.battery10_sum += sign * r.battery10
        if r.battery10 < RobotProtocol.LOW_BATTERY_TENTHS:
            self.low_battery += sign

    def summary(self, total: int) -> dict:
        n = self.online
        return {
            "total": total,
            "online": n,
            "offline": total - n,
            "modes": dict(self.by_mode),
            "charging": self.by_charge["charging"],
            "discharging": self.by_charge["discharging"],
            "avg_battery": round(self.battery10_sum / 10 / n, 1) if n else None,
            "low_battery": self.low_battery,
        }
