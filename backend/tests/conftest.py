"""Shared fixtures. Helpers live in tests/support."""
from __future__ import annotations

import pytest

from app.config.settings import Settings
from app.features.observability.metrics import Metrics


@pytest.fixture
def settings():
    return Settings(flush_interval=0.01, send_timeout=0.2, max_watch=50)


@pytest.fixture
def metrics():
    return Metrics()
