from dataclasses import fields

import pytest

from app.config.environment.environment import Environment
from app.config.settings import Settings


def test_secret_from_file_wins_and_is_stripped(tmp_path, monkeypatch):
    f = tmp_path / "token"
    f.write_text("from-file\n")
    monkeypatch.setenv("AUTH_TOKEN", "from-env")
    monkeypatch.setenv("AUTH_TOKEN_FILE", str(f))
    assert Environment.get_secret("AUTH_TOKEN") == "from-file"


def test_unreadable_secret_file_fails_fast(monkeypatch):
    monkeypatch.setenv("AUTH_TOKEN_FILE", "/nonexistent/token")
    with pytest.raises(RuntimeError, match="AUTH_TOKEN_FILE"):
        Environment.get_secret("AUTH_TOKEN")


def test_typed_readers(monkeypatch):
    monkeypatch.setenv("X_NUM", "2.5")
    monkeypatch.setenv("X_BOOL", "Yes")
    monkeypatch.setenv("X_LIST", " a, ,b ")
    assert Environment.get_float("X_NUM", 1) == 2.5
    assert Environment.get_bool("X_BOOL") is True
    assert Environment.get_list("X_LIST") == ("a", "b")
    assert Environment.get_str("X_MISSING", "d") == "d"
    monkeypatch.setenv("X_NUM", "abc")
    with pytest.raises(ValueError, match="X_NUM"):
        Environment.get_float("X_NUM", 1)


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("MQTT_PORT", "8883")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.example,https://b.example")
    s = Settings.from_env()
    assert s.mqtt_port == 8883 and s.allowed_origins == ("https://a.example", "https://b.example")


def test_integer_reader_rejects_fractions(monkeypatch):
    monkeypatch.setenv("X_INT", "1883")
    assert Environment.get_int("X_INT", 1) == 1883
    monkeypatch.setenv("X_INT", "1883.5")
    with pytest.raises(ValueError, match="X_INT"):
        Environment.get_int("X_INT", 1)


def test_from_env_defaults_match_field_defaults(monkeypatch):
    # Guards the single source of truth: with no env vars, from_env() == Settings().
    for f in fields(Settings):
        monkeypatch.delenv(f.name.upper(), raising=False)
        monkeypatch.delenv(f"{f.name.upper()}_FILE", raising=False)
    assert Settings.from_env() == Settings()
