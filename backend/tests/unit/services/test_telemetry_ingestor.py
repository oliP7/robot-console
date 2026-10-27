import asyncio

from app.features.observability.metrics import Metrics
from app.repositories.robot_registry import RobotRegistry
from app.services.telemetry_ingestor import TelemetryIngestor
from tests.support.fakes import FakeBroker
from tests.support.samples import encoded


def test_invalid_messages_are_counted_and_ignored():
    st, m = RobotRegistry(), Metrics()
    ing = TelemetryIngestor(FakeBroker(), st, m, 0.01)
    ing.process("robots/r1/telemetry", b"{not json", now=0)
    ing.process("robots/r1/other", encoded(), now=0)
    assert m.telemetry_invalid == 2 and not st.robots


def test_run_drains_the_source_and_signals_changes():
    async def go():
        broker, st = FakeBroker(), RobotRegistry()
        kicks = []
        broker.inbox = [(f"robots/r{i}/telemetry", encoded()) for i in range(3)]
        ing = TelemetryIngestor(broker, st, Metrics(), 0.001, on_change=lambda: kicks.append(1))
        task = asyncio.create_task(ing.run())
        while len(st.robots) < 3:
            await asyncio.sleep(0.005)
        task.cancel()
        assert sorted(st.robots) == ["r0", "r1", "r2"] and kicks and broker.inbox == []
    asyncio.run(go())
