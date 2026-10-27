"""A validated telemetry sample (value object)."""
from __future__ import annotations

from dataclasses import dataclass

from ...protocols.robot_protocol import RobotProtocol

_MODE_SET = frozenset(RobotProtocol.MODES)
_CHARGE_SET = frozenset(RobotProtocol.CHARGE_STATES)
_MAX_TS_LEN = 40


@dataclass(frozen=True, slots=True)
class TelemetrySample:
    battery10: int   # integer tenths of a percent
    charge: str
    mode: str
    ts: str

    @classmethod
    def from_payload(cls, data: object) -> "TelemetrySample | None":
        """Validate an untrusted decoded payload. None means invalid."""
        if not isinstance(data, dict):
            return None
        battery = data.get("battery_pct")
        charge = data.get("charge_state")
        mode = data.get("mode")
        if (
            isinstance(battery, bool)
            or not isinstance(battery, (int, float))
            or not 0 <= battery <= 100
            or charge not in _CHARGE_SET
            or mode not in _MODE_SET
        ):
            return None
        ts = data.get("ts")
        # An oversized timestamp is dropped, not stored.
        ts = ts if isinstance(ts, str) and len(ts) <= _MAX_TS_LEN else ""
        return cls(int(round(battery * 10)), charge, mode, ts)
