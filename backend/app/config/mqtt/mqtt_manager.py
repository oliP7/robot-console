"""MQTT connection manager: implements TelemetrySource and CommandPublisher.

paho runs its own network thread. The callback does the minimum possible work:
append the raw (topic, payload) to a bounded deque. All parsing and state updates
happen in the asyncio loop in batches (see services/telemetry_ingestor.py), which
is much cheaper per message than waking the loop for every sample.

The inbox is bounded and drops the OLDEST sample when full. For telemetry that is
the right policy: the newest sample supersedes older ones.
"""
from __future__ import annotations

import logging
import uuid
from collections import deque

import paho.mqtt.client as mqtt

from ...exceptions.broker_unavailable import BrokerUnavailable
from ...features.observability.metrics import Metrics
from ...protocols.robot_protocol import RobotProtocol
from ..settings import Settings

log = logging.getLogger("robot_console.mqtt")


class MqttManager:
    def __init__(self, settings: Settings, metrics: Metrics):
        self._s = settings
        self._metrics = metrics
        self.inbox: deque[tuple[str, bytes]] = deque(maxlen=settings.inbox_max)

        # Unique client id: two clients with the same id evict each other on the broker.
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"robot-console-{uuid.uuid4().hex[:8]}",
            clean_session=True,
        )
        if settings.mqtt_username:
            self._client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        if settings.mqtt_tls:
            self._client.tls_set(ca_certs=settings.mqtt_ca_file)
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    # ---- lifecycle --------------------------------------------------------
    def start(self) -> None:
        # connect_async + loop_start retries in the background, so the service
        # starts (and reports "not ready") even if the broker is not up yet.
        self._client.connect_async(self._s.mqtt_host, self._s.mqtt_port, keepalive=30)
        self._client.loop_start()
        log.info("mqtt connecting to %s:%s", self._s.mqtt_host, self._s.mqtt_port)

    def stop(self) -> None:
        self._client.disconnect()
        self._client.loop_stop()

    @property
    def connected(self) -> bool:
        return self._client.is_connected()

    # ---- paho callbacks (run in paho's thread) ----------------------------
    def _on_connect(self, client, _userdata, _flags, reason_code, _properties):
        if reason_code.is_failure:
            log.error("mqtt connect refused: %s", reason_code)
            return
        # Subscribing here (not once at startup) restores the subscription after
        # every reconnect, because we use a clean session.
        client.subscribe(RobotProtocol.TELEMETRY_FILTER, qos=0)
        log.info("mqtt connected, subscribed to %s", RobotProtocol.TELEMETRY_FILTER)

    def _on_disconnect(self, _client, _userdata, _flags, reason_code, _properties):
        log.warning("mqtt disconnected: %s (auto-reconnect active)", reason_code)

    def _on_message(self, _client, _userdata, msg):
        if len(self.inbox) == self.inbox.maxlen:
            self._metrics.msgs_dropped += 1
        self.inbox.append((msg.topic, msg.payload))
        self._metrics.msgs_in += 1

    # ---- TelemetrySource ----------------------------------------------------
    def drain(self, max_items: int) -> list[tuple[str, bytes]]:
        n = min(len(self.inbox), max_items)
        pop = self.inbox.popleft
        return [pop() for _ in range(n)]

    # ---- CommandPublisher ---------------------------------------------------
    def publish(self, topic: str, payload: bytes) -> None:
        """Publish a command with QoS 1. Fails fast when the broker is unreachable."""
        if not self._client.is_connected():
            raise BrokerUnavailable("broker not connected")
        info = self._client.publish(topic, payload, qos=1)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise BrokerUnavailable(f"publish failed: {mqtt.error_string(info.rc)}")
