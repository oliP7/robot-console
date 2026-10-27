import asyncio

import orjson

from app.features.realtime.flush_loop import FlushLoop
from app.features.realtime.hub import Hub
from app.repositories.robot_registry import RobotRegistry
from tests.support.fakes import FakeWS
from tests.support.samples import sample


def frames(ws, kind):
    return [f for f in map(orjson.loads, ws.sent) if f["t"] == kind]


def test_flush_loop_pushes_first_change_immediately(settings, metrics):
    """Leading-edge throttle: a lone change is not held for the flush interval."""
    async def go():
        st = RobotRegistry()
        st.apply("a", sample(1), now=0)
        s = settings.__class__(flush_interval=0.5, send_timeout=1)
        hub = Hub(st, s, metrics)
        ws = FakeWS()
        c = hub.add_client(ws)
        hub.set_watch(c, ["a"])
        flush = FlushLoop(hub, st, metrics, s)
        runner = asyncio.create_task(flush.run())
        writer = asyncio.create_task(hub.writer(c))
        await asyncio.sleep(0.6)  # past the first throttle window
        ws.sent.clear()
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        st.apply("a", sample(2), now=0)
        flush.kick()
        while not frames(ws, "delta"):
            await asyncio.sleep(0.005)
        assert loop.time() - t0 < 0.1  # well under the 0.5 s interval
        runner.cancel()
        writer.cancel()
    asyncio.run(go())
