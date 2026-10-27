"""The Robot entity: last reported state of one robot."""
from __future__ import annotations

from ...utils.json_utils import JsonUtils
from .telemetry_sample import TelemetrySample


class Robot:
    # _json caches the serialized form (serialize once, fan out to many clients).
    # Every state change goes through a method below, which clears it.
    __slots__ = ("id", "battery10", "charge", "mode", "ts", "online", "_json")

    def __init__(self, rid: str, battery10: int, charge: str, mode: str, ts: str):
        self.id = rid
        self.battery10 = battery10  # integer tenths of a percent, keeps sums exact
        self.charge = charge
        self.mode = mode
        self.ts = ts
        self.online = True
        self._json: str | None = None

    @classmethod
    def from_sample(cls, rid: str, s: TelemetrySample) -> "Robot":
        return cls(rid, s.battery10, s.charge, s.mode, s.ts)

    def same_state(self, s: TelemetrySample) -> bool:
        """True when the sample changes nothing visible (only the timestamp)."""
        return self.battery10 == s.battery10 and self.charge == s.charge and self.mode == s.mode

    def apply(self, s: TelemetrySample) -> None:
        """Take the sample's state; a robot that reports is online."""
        self.battery10, self.charge, self.mode, self.ts = s.battery10, s.charge, s.mode, s.ts
        self.online = True
        self._json = None

    def mark_offline(self) -> None:
        self.online = False
        self._json = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "battery": self.battery10 / 10,
            "charge": self.charge,
            "mode": self.mode,
            "online": self.online,
            "ts": self.ts,
        }

    def to_json(self) -> str:
        """Serialized form, cached until the next state change."""
        if self._json is None:
            self._json = JsonUtils.to_str(self.to_dict())
        return self._json
