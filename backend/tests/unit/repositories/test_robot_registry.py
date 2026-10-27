import random

from app.protocols.robot_protocol import RobotProtocol
from app.repositories.robot_registry import RobotRegistry
from tests.support.samples import sample


def recount(st: RobotRegistry) -> dict:
    """Brute-force O(n) recomputation, the oracle for the O(1) counters."""
    online = [r for r in st.robots.values() if r.online]
    return {
        "n_online": len(online),
        "by_mode": {m: sum(r.mode == m for r in online) for m in RobotProtocol.MODES},
        "charging": sum(r.charge == "charging" for r in online),
        "battery10_sum": sum(r.battery10 for r in online),
        "low_battery": sum(r.battery10 < 200 for r in online),
    }


def counters(st: RobotRegistry) -> dict:
    return {
        "n_online": st.counters.online,
        "by_mode": dict(st.counters.by_mode),
        "charging": st.counters.by_charge["charging"],
        "battery10_sum": st.counters.battery10_sum,
        "low_battery": st.counters.low_battery,
    }


def test_new_robot_is_counted_indexed_and_dirty():
    st = RobotRegistry()
    assert st.apply("r1", sample(42.5, mode="working"), now=0) is True
    dirty, added, removed = st.take_changes()
    assert dirty == {"r1"} and added == ["r1"] and removed == []
    assert st.summary()["modes"]["working"] == 1
    assert st.summary()["avg_battery"] == 42.5


def test_timestamp_only_change_refreshes_liveness_but_is_not_dirty():
    st = RobotRegistry(offline_after=5)
    st.apply("r1", sample(50), now=0)
    st.take_changes()
    assert st.apply("r1", sample(50, ts="later"), now=4) is False
    assert st.take_changes()[0] == set()
    st.sweep(now=8)  # last seen at 4, so still online at 8
    assert st.robots["r1"].online


def test_counters_match_brute_force_under_random_traffic():
    rnd = random.Random(7)
    st = RobotRegistry(offline_after=3, forget_after=10)
    for t in range(400):
        for _ in range(5):
            rid = f"r{rnd.randrange(30)}"
            st.apply(rid, sample(round(rnd.uniform(0, 100), 1), rnd.choice(["charging", "discharging"]),
                                 rnd.choice(RobotProtocol.MODES)), now=t)
        if t % 3 == 0:
            st.sweep(now=t)
        assert counters(st) == recount(st)


def test_offline_sweep_then_back_online():
    st = RobotRegistry(offline_after=5, forget_after=100)
    st.apply("a", sample(10), now=0)
    st.apply("b", sample(90), now=4)
    st.take_changes()
    assert st.sweep(now=6) == 1  # only "a" is stale
    assert not st.robots["a"].online and st.robots["b"].online
    assert st.take_changes()[0] == {"a"}
    assert st.summary()["online"] == 1 and st.summary()["offline"] == 1
    assert st.summary()["low_battery"] == 0  # offline robots are not counted
    # An identical sample brings it back and IS a visible change (online flag).
    assert st.apply("a", sample(10), now=7) is True
    assert st.robots["a"].online and st.online_count == 2
    assert counters(st) == recount(st)


def test_forget_after_removes_robot_and_emits_index_removal():
    st = RobotRegistry(offline_after=1, forget_after=10)
    st.apply("a", sample(), now=0)
    st.take_changes()
    st.sweep(now=2)       # offline since 2
    st.sweep(now=11)      # 9 s offline: kept
    assert "a" in st.robots
    st.sweep(now=12.5)    # 10.5 s offline: forgotten
    assert "a" not in st.robots
    _, added, removed = st.take_changes()
    assert removed == ["a"] and added == []
    assert st.json_of("a") is None


def test_add_then_forget_within_one_window_cancels_out():
    st = RobotRegistry(offline_after=1, forget_after=1)
    st.apply("ghost", sample(), now=0)
    st.sweep(now=1.5)
    st.sweep(now=3)
    _, added, removed = st.take_changes()
    assert added == [] and removed == []


def test_forget_then_reappear_within_one_window_is_not_a_removal():
    st = RobotRegistry(offline_after=1, forget_after=1)
    st.apply("a", sample(), now=0)
    st.take_changes()
    st.sweep(now=1.5)
    st.sweep(now=3)          # forgotten
    st.apply("a", sample(), now=3.1)  # back before any client saw the removal
    _, added, removed = st.take_changes()
    assert added == [] and removed == []
    assert "a" in st.sorted_ids()


def test_max_robots_guard():
    st = RobotRegistry(max_robots=2)
    for i in range(3):
        st.apply(f"r{i}", sample(), now=0)
    assert len(st.robots) == 2 and st.rejected == 1


def test_json_is_cached_until_change():
    st = RobotRegistry()
    st.apply("r1", sample(50), now=0)
    first = st.json_of("r1")
    assert st.json_of("r1") is first
    st.apply("r1", sample(51), now=1)
    assert '"battery":51.0' in st.json_of("r1")
    st.sweep(now=1 + st.offline_after + 1)  # going offline also invalidates the cache
    assert '"online":false' in st.json_of("r1")


def test_sorted_ids_cache_invalidated_on_add():
    st = RobotRegistry()
    st.apply("b", sample(), now=0)
    assert st.sorted_ids() == ["b"]
    st.apply("a", sample(), now=0)
    assert st.sorted_ids() == ["a", "b"]
