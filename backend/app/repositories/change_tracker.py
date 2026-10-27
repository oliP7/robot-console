"""Changes since the last flush: dirty robots and index additions/removals.

An add and a remove of the same id inside one window cancel out, so clients
never see a robot that appeared and vanished between two flushes.
"""
from __future__ import annotations


class ChangeTracker:
    def __init__(self) -> None:
        self._dirty: set[str] = set()
        self._added: dict[str, None] = {}    # dicts keep insertion order
        self._removed: dict[str, None] = {}

    def dirty(self, rid: str) -> None:
        self._dirty.add(rid)

    def added(self, rid: str) -> None:
        if rid in self._removed:
            del self._removed[rid]
        else:
            self._added[rid] = None

    def removed(self, rid: str) -> None:
        self._dirty.discard(rid)
        if rid in self._added:
            del self._added[rid]
        else:
            self._removed[rid] = None

    def has_changes(self) -> bool:
        return bool(self._dirty or self._added or self._removed)

    def take(self) -> tuple[set[str], list[str], list[str]]:
        """Return and reset (dirty ids, index additions, index removals)."""
        dirty, added, removed = self._dirty, list(self._added), list(self._removed)
        self._dirty = set()
        self._added = {}
        self._removed = {}
        return dirty, added, removed
