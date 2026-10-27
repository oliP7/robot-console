from app.features.security.command_limiter import CommandLimiter
from app.features.security.token_bucket import TokenBucket


def test_token_bucket_refills_at_rate():
    b = TokenBucket(rate=2, burst=2)
    b.stamp = 0
    assert b.allow(0) and b.allow(0) and not b.allow(0)
    assert b.allow(0.5)        # one token after 0.5 s at 2/s
    assert not b.allow(0.5)


def test_per_robot_limit_does_not_starve_other_robots():
    lim = CommandLimiter(global_rate=1000, robot_rate=1)
    assert lim.allow("a") and lim.allow("a") and not lim.allow("a")
    assert lim.allow("b")
