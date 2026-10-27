"""Command rate limiting."""
from __future__ import annotations

import time

from .token_bucket import TokenBucket

_MAX_BUCKETS = 20_000
_IDLE_BUCKET_S = 30


class CommandLimiter:
    """One global bucket plus one bucket per robot (stops hammering a single robot)."""

    def __init__(self, global_rate: float, robot_rate: float):
        self._global = TokenBucket(global_rate, global_rate * 2)
        self._robot_rate = robot_rate
        self._robots: dict[str, TokenBucket] = {}

    def allow(self, robot_id: str) -> bool:
        if not self._global.allow():
            return False
        if len(self._robots) > _MAX_BUCKETS:  # prune idle buckets, bounds memory
            now = time.monotonic()
            self._robots = {k: b for k, b in self._robots.items() if now - b.stamp < _IDLE_BUCKET_S}
        bucket = self._robots.get(robot_id)
        if bucket is None:
            bucket = self._robots[robot_id] = TokenBucket(self._robot_rate, self._robot_rate * 2)
        return bucket.allow()
