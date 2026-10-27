"""Builds the 1 Hz robot summary frame."""
from __future__ import annotations

import time

from ...repositories.robot_registry import RobotRegistry
from ..observability.metrics import Metrics
from .frame_encoder import FrameEncoder


class SummaryBuilder:
    def __init__(self, state: RobotRegistry, metrics: Metrics):
        self._state = state
        self._metrics = metrics

    def build(self, clients: int) -> str:
        data = self._state.summary()
        data.update(
            ingest_per_s=round(self._metrics.ingest_rate),
            lag_ms=round(self._metrics.loop_lag_ms, 1),
            clients=clients,
            server_ts=time.time(),
        )
        return FrameEncoder.summary(data)
