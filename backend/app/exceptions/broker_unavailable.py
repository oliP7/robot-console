"""The MQTT broker is not connected or rejected the publish."""
from __future__ import annotations

from .app_error import AppError


class BrokerUnavailable(AppError):
    result = "broker_unavailable"
    detail = "broker unavailable"
