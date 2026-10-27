from app.repositories.change_tracker import ChangeTracker


def test_take_returns_and_resets():
    ct = ChangeTracker()
    ct.dirty("a")
    ct.added("a")
    assert ct.has_changes()
    assert ct.take() == ({"a"}, ["a"], [])
    assert not ct.has_changes()


def test_add_then_remove_cancels_out_and_clears_dirty():
    ct = ChangeTracker()
    ct.added("a")
    ct.dirty("a")
    ct.removed("a")
    assert ct.take() == (set(), [], [])


def test_remove_then_add_cancels_out():
    ct = ChangeTracker()
    ct.removed("a")
    ct.added("a")
    assert ct.take() == (set(), [], [])
