"""Port: a buffered source of raw telemetry messages (MQTT in production)."""
from __future__ import annotations

from typing import Protocol


class TelemetrySource(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def drain(self, max_items: int) -> list[tuple[str, bytes]]:
        """Return up to max_items (topic, payload) pairs, oldest first."""
        ...
