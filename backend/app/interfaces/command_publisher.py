"""Port: something that can deliver a command to a robot (MQTT in production)."""
from __future__ import annotations

from typing import Protocol


class CommandPublisher(Protocol):
    @property
    def connected(self) -> bool: ...

    def publish(self, topic: str, payload: bytes) -> None:
        """Deliver or raise exceptions.BrokerUnavailable."""
        ...
