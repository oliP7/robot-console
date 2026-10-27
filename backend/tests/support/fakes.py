"""Test doubles. No broker and no network are needed for unit tests."""
from __future__ import annotations

import asyncio

from app.exceptions.broker_unavailable import BrokerUnavailable


class FakeBroker:
    """Implements the MessageBroker port: records publishes, can simulate an outage."""

    def __init__(self):
        self.inbox: list[tuple[str, bytes]] = []
        self.published: list[tuple[str, bytes]] = []
        self.connected = True

    def start(self):
        pass

    def stop(self):
        pass

    def drain(self, max_items):
        out, self.inbox = self.inbox[:max_items], self.inbox[max_items:]
        return out

    def publish(self, topic, payload):
        if not self.connected:
            raise BrokerUnavailable("broker not connected")
        self.published.append((topic, payload))


class FakeWS:
    """Minimal WebSocket double for the client writer. `block` makes send_text hang."""

    def __init__(self, block: bool = False):
        self.sent: list[str] = []
        self.block = block
        self.closed_code: int | None = None

    async def send_text(self, text: str):
        if self.block:
            await asyncio.Event().wait()  # never completes: a stalled client
        self.sent.append(text)

    async def close(self, code: int = 1000):
        self.closed_code = code
