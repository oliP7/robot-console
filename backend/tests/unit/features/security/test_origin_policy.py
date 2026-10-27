from app.features.security.origin_policy import OriginPolicy


def test_origin_rules():
    assert OriginPolicy.allowed(None, "localhost:8080", ())
    assert OriginPolicy.allowed("http://localhost:8080", "localhost:8080", ())
    assert not OriginPolicy.allowed("http://evil.example", "localhost:8080", ())
    assert OriginPolicy.allowed("https://app.example", "api.internal", ("https://app.example",))
    assert not OriginPolicy.allowed("http://localhost:8080", None, ())
