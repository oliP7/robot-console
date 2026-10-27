import logging

import orjson
import pytest

from app.exceptions.broker_unavailable import BrokerUnavailable
from app.exceptions.rate_limited import RateLimited
from app.exceptions.robot_not_found import RobotNotFound
from app.exceptions.robot_offline import RobotOffline
from app.features.observability.metrics import Metrics
from app.features.security.command_limiter import CommandLimiter
from app.repositories.robot_registry import RobotRegistry
from app.services.audit_log import AuditLog
from app.services.command_service import CommandService
from tests.support.fakes import FakeBroker
from tests.support.samples import sample


@pytest.fixture
def svc():
    st, broker, m = RobotRegistry(offline_after=5), FakeBroker(), Metrics()
    st.apply("r1", sample(), now=0)
    return CommandService(st, broker, CommandLimiter(1000, 1), AuditLog(), m), st, broker, m


def test_publishes_with_command_id(svc):
    service, _, broker, m = svc
    cid = service.send("r1", "set_mode", "working", ip="10.0.0.1")
    topic, raw = broker.published[-1]
    assert topic == "robots/r1/cmd"
    assert orjson.loads(raw) == {"cmd": "set_mode", "cid": cid, "value": "working"}
    assert m.commands_sent == 1


def test_business_errors(svc):
    service, st, broker, m = svc
    with pytest.raises(RobotNotFound):
        service.send("nope", "kick", None, ip="-")
    service.send("r1", "kick", None, ip="-")
    service.send("r1", "kick", None, ip="-")
    with pytest.raises(RateLimited):
        service.send("r1", "kick", None, ip="-")
    assert m.commands_rejected == 1
    broker.connected = False
    st.apply("r2", sample(), now=0)
    with pytest.raises(BrokerUnavailable):
        service.send("r2", "kick", None, ip="-")
    st.sweep(now=100)
    with pytest.raises(RobotOffline):
        service.send("r2", "kick", None, ip="-")


def test_every_attempt_is_audited(svc, caplog):
    service, *_ = svc
    with caplog.at_level(logging.INFO, logger="robot_console.audit"):
        service.send("r1", "kick", None, ip="10.0.0.9")
        with pytest.raises(RobotNotFound):
            service.send("ghost", "kick", None, ip="10.0.0.9")
    lines = [orjson.loads(r.getMessage()) for r in caplog.records if r.name == "robot_console.audit"]
    assert [x["result"] for x in lines] == ["published", "unknown_robot"]
    assert all(x["ip"] == "10.0.0.9" and x["actor"] == "operator" for x in lines)
