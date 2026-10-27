"""In-memory registry of all robots (the repository).

Design notes
- The event loop is the single owner of this structure, so there are no locks.
- Counters across all robots are maintained incrementally (see RobotCounters), so building
  the dashboard summary is O(1) regardless of the robot count.
- Samples that change nothing visible (only the timestamp) refresh liveness but are
  not marked dirty, which removes work for idle robots.
- Liveness uses two ordered maps (online by last seen, offline by time gone), so the
  periodic sweep only touches robots that actually changed state: O(changes), not O(robots).
"""
from __future__ import annotations

from collections import OrderedDict

from ..models.entities.robot import Robot
from ..models.entities.telemetry_sample import TelemetrySample
from .change_tracker import ChangeTracker
from .robot_counters import RobotCounters


class RobotRegistry:
    def __init__(self, offline_after: float = 6.0, forget_after: float = 600.0,
                 max_robots: int = 200_000):
        self.offline_after = offline_after
        self.forget_after = forget_after
        self.max_robots = max_robots

        self.robots: dict[str, Robot] = {}
        self._online_order: OrderedDict[str, float] = OrderedDict()   # id -> last seen
        self._offline_order: OrderedDict[str, float] = OrderedDict()  # id -> gone since
        self._sorted: list[str] | None = None

        self.counters = RobotCounters()
        self.changes = ChangeTracker()
        self.rejected = 0  # new robots refused by the max_robots guard

    # ---- writes -----------------------------------------------------------
    def apply(self, rid: str, s: TelemetrySample, now: float) -> bool:
        """Apply one validated sample. Returns True if visible state changed."""
        r = self.robots.get(rid)
        if r is None:
            if len(self.robots) >= self.max_robots:
                self.rejected += 1
                return False
            r = Robot.from_sample(rid, s)
            self.robots[rid] = r
            self._sorted = None
            self.changes.added(rid)
            self.counters.add(r)
            self._touch(rid, now)
            self.changes.dirty(rid)
            return True

        if r.online:
            self._touch(rid, now)
            if r.same_state(s):
                return False
            self.counters.remove(r)
        else:
            self._offline_order.pop(rid, None)
            self._touch(rid, now)

        r.apply(s)
        self.counters.add(r)
        self.changes.dirty(rid)
        return True

    def _touch(self, rid: str, now: float) -> None:
        od = self._online_order
        od[rid] = now
        od.move_to_end(rid)

    # ---- liveness ---------------------------------------------------------
    def sweep(self, now: float) -> int:
        """Mark silent robots offline, forget long-gone ones. Returns state changes."""
        changed = 0
        cutoff = now - self.offline_after
        online = self._online_order
        while online:
            rid, seen = next(iter(online.items()))
            if seen > cutoff:
                break
            online.popitem(last=False)
            r = self.robots[rid]
            self.counters.remove(r)
            r.mark_offline()
            self._offline_order[rid] = now
            self.changes.dirty(rid)
            changed += 1

        forget_cutoff = now - self.forget_after
        offline = self._offline_order
        while offline:
            rid, since = next(iter(offline.items()))
            if since > forget_cutoff:
                break
            offline.popitem(last=False)
            del self.robots[rid]
            self._sorted = None
            self.changes.removed(rid)
        return changed

    # ---- reads ------------------------------------------------------------
    def get(self, rid: str) -> Robot | None:
        return self.robots.get(rid)

    def json_of(self, rid: str) -> str | None:
        """Serialized robot, cached until it changes (serialize once, fan out to many)."""
        r = self.robots.get(rid)
        if r is None:
            return None
        return r.to_json()

    def sorted_ids(self) -> list[str]:
        if self._sorted is None:
            self._sorted = sorted(self.robots)
        return self._sorted

    @property
    def online_count(self) -> int:
        return self.counters.online

    def has_changes(self) -> bool:
        return self.changes.has_changes()

    def take_changes(self) -> tuple[set[str], list[str], list[str]]:
        return self.changes.take()

    def summary(self) -> dict:
        return self.counters.summary(len(self.robots))
