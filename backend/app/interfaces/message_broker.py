"""Port: the broker connection as a whole (both directions)."""
from __future__ import annotations

from typing import Protocol

from .command_publisher import CommandPublisher
from .telemetry_source import TelemetrySource


class MessageBroker(TelemetrySource, CommandPublisher, Protocol):
    pass
