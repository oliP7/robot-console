import pytest

from app.models.entities.telemetry_sample import TelemetrySample
from tests.support.samples import payload


def test_valid_payload_is_converted_to_tenths():
    s = TelemetrySample.from_payload(payload(42.55, "charging", "working"))
    assert s is not None
    assert (s.battery10, s.charge, s.mode) == (426, "charging", "working")


@pytest.mark.parametrize("bad", [
    {"battery_pct": True, "charge_state": "charging", "mode": "idle"},
    {"battery_pct": "50", "charge_state": "charging", "mode": "idle"},
    {"battery_pct": -1, "charge_state": "charging", "mode": "idle"},
    {"battery_pct": 100.1, "charge_state": "charging", "mode": "idle"},
    {"battery_pct": 50, "charge_state": "exploding", "mode": "idle"},
    {"battery_pct": 50, "charge_state": "charging", "mode": "dancing"},
    {"battery_pct": 50, "charge_state": "charging"},
    {},
    [1, 2, 3],
    None,
])
def test_invalid_payloads_are_rejected(bad):
    assert TelemetrySample.from_payload(bad) is None


def test_oversized_timestamp_is_dropped_not_stored():
    s = TelemetrySample.from_payload(payload(ts="x" * 500))
    assert s is not None and s.ts == ""
