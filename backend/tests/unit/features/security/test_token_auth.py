from app.features.security.token_auth import TokenAuth


def test_token_matches():
    assert TokenAuth.matches(None, None)            # auth disabled
    assert TokenAuth.matches("s3cret", "s3cret")
    assert not TokenAuth.matches("s3cret", "nope")
    assert not TokenAuth.matches("s3cret", None)
    assert not TokenAuth.matches("s3cret", "")


def test_bearer_token():
    assert TokenAuth.bearer_token("Bearer abc") == "abc"
    assert TokenAuth.bearer_token("bearer abc") == "abc"
    assert TokenAuth.bearer_token("Basic abc") is None
    assert TokenAuth.bearer_token(None) is None
