"""Renders metrics in the Prometheus text exposition format."""
from __future__ import annotations

from ...interfaces.command_publisher import CommandPublisher
from ...repositories.robot_registry import RobotRegistry
from .metrics import Metrics
from .process_stats import ProcessStats


class PrometheusExporter:
    def __init__(self, metrics: Metrics, state: RobotRegistry, broker: CommandPublisher):
        self._m = metrics
        self._state = state
        self._broker = broker

    def render(self) -> str:
        m, st = self._m, self._state
        rows = [
            ("robot_console_robots", "gauge", len(st.robots)),
            ("robot_console_robots_online", "gauge", st.online_count),
            ("robot_console_mqtt_connected", "gauge", int(self._broker.connected)),
            ("robot_console_ws_clients", "gauge", m.ws_clients),
            ("robot_console_ingest_rate", "gauge", round(m.ingest_rate, 1)),
            ("robot_console_event_loop_lag_ms", "gauge", round(m.loop_lag_ms, 2)),
            ("robot_console_telemetry_messages_total", "counter", m.msgs_in),
            ("robot_console_telemetry_dropped_total", "counter", m.msgs_dropped),
            ("robot_console_telemetry_invalid_total", "counter", m.telemetry_invalid),
            ("robot_console_commands_sent_total", "counter", m.commands_sent),
            ("robot_console_commands_rejected_total", "counter", m.commands_rejected),
            ("robot_console_ws_frames_sent_total", "counter", m.frames_sent),
            ("robot_console_ws_clients_dropped_total", "counter", m.clients_dropped),
            ("robot_console_robots_rejected_total", "counter", st.rejected),
            ("robot_console_task_restarts_total", "counter", m.task_restarts),
            ("process_cpu_seconds_total", "counter", round(ProcessStats.cpu_seconds(), 3)),
            ("process_resident_memory_bytes", "gauge", ProcessStats.rss_bytes()),
        ]
        out = []
        for name, kind, value in rows:
            out.append(f"# TYPE {name} {kind}")
            out.append(f"{name} {value}")
        return "\n".join(out) + "\n"
