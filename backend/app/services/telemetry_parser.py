"""Turns a raw MQTT message into (robot id, validated sample)."""
from __future__ import annotations

from ..models.entities.telemetry_sample import TelemetrySample
from ..protocols.robot_protocol import RobotProtocol
from ..utils.json_utils import JsonUtils


class TelemetryParser:
    def parse(self, topic: str, payload: bytes) -> tuple[str, TelemetrySample] | None:
        """None means the message is invalid and must be ignored."""
        parts = topic.split("/")
        # The id comes from the TOPIC, never from the payload: in production the
        # broker ACL guarantees a robot can only publish on its own topic, while
        # the payload is untrusted content.
        if len(parts) != 3 or parts[2] != "telemetry" or not RobotProtocol.is_valid_id(parts[1]):
            return None
        try:
            data = JsonUtils.parse(payload)
        except ValueError:
            return None
        sample = TelemetrySample.from_payload(data)
        return (parts[1], sample) if sample is not None else None
