"""Composition root: builds every service once and wires the dependencies.

This is the only place that knows concrete classes; everything else depends on
what it is handed (constructor injection), which is what lets the tests swap the
MQTT connection for a fake.
"""
from __future__ import annotations

from dataclasses import dataclass

from ...features.observability.metrics import Metrics
from ...features.observability.prometheus_exporter import PrometheusExporter
from ...features.realtime.flush_loop import FlushLoop
from ...features.realtime.hub import Hub
from ...features.realtime.live_session import LiveSessionHandler
from ...features.security.command_limiter import CommandLimiter
from ...interfaces.message_broker import MessageBroker
from ...repositories.robot_registry import RobotRegistry
from ...services.audit_log import AuditLog
from ...services.command_service import CommandService
from ...services.robot_query_service import RobotQueryService
from ...services.task_supervisor import TaskSupervisor
from ...services.telemetry_ingestor import TelemetryIngestor
from ..mqtt.mqtt_manager import MqttManager
from ..settings import Settings


@dataclass(frozen=True)
class Container:
    settings: Settings
    metrics: Metrics
    registry: RobotRegistry
    broker: MessageBroker
    hub: Hub
    flush_loop: FlushLoop
    ingestor: TelemetryIngestor
    supervisor: TaskSupervisor
    commands: CommandService
    robots: RobotQueryService
    exporter: PrometheusExporter
    live: LiveSessionHandler

    @classmethod
    def build(cls, s: Settings, broker: MessageBroker | None = None) -> "Container":
        metrics = Metrics()
        registry = RobotRegistry(s.offline_after, s.forget_after, s.max_robots)
        broker = broker or MqttManager(s, metrics)
        hub = Hub(registry, s, metrics)
        flush_loop = FlushLoop(hub, registry, metrics, s)
        return cls(
            settings=s,
            metrics=metrics,
            registry=registry,
            broker=broker,
            hub=hub,
            flush_loop=flush_loop,
            ingestor=TelemetryIngestor(broker, registry, metrics, s.drain_interval, on_change=flush_loop.kick),
            supervisor=TaskSupervisor(metrics),
            commands=CommandService(registry, broker, CommandLimiter(s.cmd_rate_global, s.cmd_rate_robot),
                                    AuditLog(), metrics),
            robots=RobotQueryService(registry),
            exporter=PrometheusExporter(metrics, registry, broker),
            live=LiveSessionHandler(hub, s),
        )
