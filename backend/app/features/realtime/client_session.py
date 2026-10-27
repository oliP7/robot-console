"""Per-client state: what the client watches and what is waiting to be sent.

`pending` is a SET of robot ids, not a queue of events. If a client is slow, the
set simply stays the same size and the next frame carries the latest state.
There is no unbounded buffering and no stale replay (latest wins).
"""
from __future__ import annotations

import asyncio


class ClientSession:
    __slots__ = ("ws", "watch", "pending", "idx_add", "idx_rm", "summary",
                 "wake", "full_index", "closed")

    def __init__(self, ws):
        self.ws = ws
        self.watch: set[str] = set()
        self.pending: set[str] = set()
        self.idx_add: set[str] = set()
        self.idx_rm: set[str] = set()
        self.summary: str | None = None
        self.wake = asyncio.Event()
        self.full_index = True
        self.closed = False

    def queue_robots(self, ids: set[str]) -> bool:
        """Queue the watched subset of `ids`. Returns True if anything was queued."""
        hit = self.watch & ids
        if hit:
            self.pending |= hit
        return bool(hit)

    def queue_index(self, added: list[str], removed: list[str]) -> None:
        # The last operation on an id wins, so an add followed by a remove nets out.
        for rid in removed:
            self.idx_add.discard(rid)
            self.idx_rm.add(rid)
        for rid in added:
            self.idx_rm.discard(rid)
            self.idx_add.add(rid)
