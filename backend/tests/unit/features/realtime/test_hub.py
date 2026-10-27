import asyncio

import orjson

from app.features.realtime.hub import Hub
from app.repositories.robot_registry import RobotRegistry
from tests.support.fakes import FakeWS
from tests.support.samples import sample


def frames(ws, kind):
    return [f for f in map(orjson.loads, ws.sent) if f["t"] == kind]


async def settle():
    for _ in range(5):
        await asyncio.sleep(0)


def run(coro):
    return asyncio.run(coro)


def test_new_client_gets_full_index_and_summary_immediately(settings, metrics):
    async def go():
        st = RobotRegistry()
        st.apply("b", sample(), now=0)
        st.apply("a", sample(), now=0)
        hub = Hub(st, settings, metrics)
        ws = FakeWS()
        c = hub.add_client(ws)
        w = asyncio.create_task(hub.writer(c))
        await settle()
        w.cancel()
        assert frames(ws, "index")[0] == {"t": "index", "full": True, "ids": ["a", "b"]}
        assert frames(ws, "summary")[0]["total"] == 2
        assert frames(ws, "delta") == []  # nothing watched, nothing sent
    run(go())


def test_viewport_filtering_only_watched_robots_are_sent(settings, metrics):
    async def go():
        st = RobotRegistry()
        for rid in ("a", "b", "c"):
            st.apply(rid, sample(), now=0)
        hub = Hub(st, settings, metrics)
        ws = FakeWS()
        c = hub.add_client(ws)
        w = asyncio.create_task(hub.writer(c))
        await settle()
        hub.set_watch(c, ["b"])
        await settle()
        assert [r["id"] for f in frames(ws, "delta") for r in f["robots"]] == ["b"]
        hub.flush()  # drain the initial adds
        await settle()
        ws.sent.clear()
        st.apply("a", sample(10), now=1)
        st.apply("c", sample(10), now=1)
        hub.flush()
        await settle()
        assert frames(ws, "delta") == []  # a and c changed, but b is the only one in view
        st.apply("b", sample(10), now=1)
        hub.flush()
        await settle()
        assert [r["id"] for f in frames(ws, "delta") for r in f["robots"]] == ["b"]
        w.cancel()
    run(go())


def test_coalescing_many_updates_one_frame_latest_wins(settings, metrics):
    async def go():
        st = RobotRegistry()
        st.apply("a", sample(1), now=0)
        hub = Hub(st, settings, metrics)
        ws = FakeWS()
        c = hub.add_client(ws)
        hub.set_watch(c, ["a"])
        hub.flush()
        for b in range(2, 50):
            st.apply("a", sample(b), now=0)
            hub.flush()  # flushes before the writer gets to run
        w = asyncio.create_task(hub.writer(c))
        await settle()
        w.cancel()
        deltas = frames(ws, "delta")
        assert len(deltas) == 1
        assert deltas[0]["robots"] == [orjson.loads(st.json_of("a"))]
        assert deltas[0]["robots"][0]["battery"] == 49.0
    run(go())


def test_watch_list_is_capped(settings, metrics):
    st = RobotRegistry()
    hub = Hub(st, settings, metrics)
    c = hub.add_client(FakeWS())
    hub.set_watch(c, [f"r{i}" for i in range(1000)] + [123, None, "x" * 100])
    assert len(c.watch) == settings.max_watch
    hub.set_watch(c, "not-a-list")
    assert len(c.watch) == settings.max_watch  # ignored


def test_index_diffs_after_full_index(settings, metrics):
    async def go():
        st = RobotRegistry(offline_after=1, forget_after=1)
        st.apply("a", sample(), now=0)
        hub = Hub(st, settings, metrics)
        ws = FakeWS()
        c = hub.add_client(ws)
        w = asyncio.create_task(hub.writer(c))
        await settle()
        hub.flush()
        await settle()
        # "a" was pending when the client connected: it is in the full index AND
        # in the next diff. Index ops are idempotent set operations by contract.
        assert frames(ws, "index")[-1] == {"t": "index", "add": ["a"], "rm": []}
        ws.sent.clear()
        st.apply("b", sample(), now=0)
        hub.flush()
        await settle()
        st.sweep(now=1.5)
        st.sweep(now=3)  # a and b forgotten
        hub.flush()
        await settle()
        w.cancel()
        idx = frames(ws, "index")
        assert idx[0] == {"t": "index", "add": ["b"], "rm": []}
        assert sorted(idx[1]["rm"]) == ["a", "b"] and idx[1]["add"] == []
    run(go())


def test_slow_client_is_dropped_and_does_not_block_others(settings, metrics):
    async def go():
        st = RobotRegistry()
        st.apply("a", sample(1), now=0)
        hub = Hub(st, settings, metrics)
        slow_ws, fast_ws = FakeWS(block=True), FakeWS()
        slow, fast = hub.add_client(slow_ws), hub.add_client(fast_ws)
        for c in (slow, fast):
            hub.set_watch(c, ["a"])
        tasks = [asyncio.create_task(hub.writer(c)) for c in (slow, fast)]
        hub.flush()
        # While the slow client is stuck, keep producing updates.
        for b in range(2, 30):
            st.apply("a", sample(b), now=0)
            hub.flush()
            await asyncio.sleep(0.005)
            # Bounded: the stalled client's pending work never exceeds its watch list.
            assert len(slow.pending) <= len(slow.watch)
        await asyncio.sleep(settings.send_timeout + 0.1)
        assert slow not in hub.clients and slow_ws.closed_code == 1011
        assert metrics.clients_dropped == 1
        assert fast in hub.clients
        assert frames(fast_ws, "delta")[-1]["robots"][0]["battery"] == 29.0
        for t in tasks:
            t.cancel()
    run(go())
