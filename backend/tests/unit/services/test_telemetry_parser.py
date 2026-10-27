import orjson

from app.services.telemetry_parser import TelemetryParser
from tests.support.samples import encoded, payload


def test_id_comes_from_topic_not_payload():
    parsed = TelemetryParser().parse("robots/r1/telemetry", orjson.dumps(dict(payload(), id="someone-else")))
    assert parsed is not None and parsed[0] == "r1"


def test_rejects_bad_topics_and_payloads():
    p = TelemetryParser()
    for topic, raw in [
        ("robots/r1/other", encoded()),
        ("robots/a/b/telemetry", encoded()),
        ("robots/bad.id/telemetry", encoded()),
        ("robots/r1/telemetry", b"{not json"),
        ("robots/r1/telemetry", b"[1,2,3]"),
        ("robots/r1/telemetry", b"\xff\xfe"),
        ("robots/r1/telemetry", encoded(battery=101)),
    ]:
        assert p.parse(topic, raw) is None, topic
