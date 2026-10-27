"""Telemetry builders for tests."""
from __future__ import annotations

import orjson

from app.models.entities.telemetry_sample import TelemetrySample


def payload(battery=50.0, charge="discharging", mode="idle", ts="2026-01-01T00:00:00Z") -> dict:
    """A raw telemetry payload, as robot.py sends it."""
    return {"battery_pct": battery, "charge_state": charge, "mode": mode, "ts": ts}


def sample(battery=50.0, charge="discharging", mode="idle", ts="2026-01-01T00:00:00Z") -> TelemetrySample:
    """A validated sample, as the repository receives it."""
    s = TelemetrySample.from_payload(payload(battery, charge, mode, ts))
    assert s is not None
    return s


def encoded(**kw) -> bytes:
    return orjson.dumps(payload(**kw))
