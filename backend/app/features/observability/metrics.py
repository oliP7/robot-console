"""In-process counters and gauges. Rendering lives in prometheus_exporter.py."""
from __future__ import annotations

import time


class Metrics:
    def __init__(self) -> None:
        self.msgs_in = 0            # telemetry messages received from the broker
        self.msgs_dropped = 0       # dropped because the bounded inbox was full
        self.telemetry_invalid = 0  # bad topic, bad JSON or failed validation
        self.commands_sent = 0
        self.commands_rejected = 0
        self.ws_clients = 0
        self.frames_sent = 0
        self.clients_dropped = 0    # slow or broken clients disconnected by the server
        self.task_restarts = 0      # background task crashes recovered by the supervisor
        self.ingest_rate = 0.0      # msgs/s, refreshed about once per second
        self.loop_lag_ms = 0.0      # worst event-loop scheduling delay in the last window
        self._lag_window = 0.0
        self._last_count = 0
        self._last_time = time.monotonic()

    def observe_lag(self, seconds: float) -> None:
        if seconds > self._lag_window:
            self._lag_window = seconds

    def roll(self) -> None:
        """Called once per second: refresh rates and reset the lag window."""
        now = time.monotonic()
        dt = now - self._last_time
        if dt > 0:
            self.ingest_rate = (self.msgs_in - self._last_count) / dt
        self._last_count, self._last_time = self.msgs_in, now
        self.loop_lag_ms = self._lag_window * 1000
        self._lag_window = 0.0
