"""Base class of the business errors.

Services raise these without knowing about HTTP; config/error_handling maps them
to status codes in one place.
"""
from __future__ import annotations


class AppError(Exception):
    result = "error"           # stable machine-readable code, used in the audit log
    detail = "request failed"  # fixed client-facing message (never the internal one)

    def __init__(self, message: str | None = None):
        # `message` is for logs only, e.g. the broker's error string.
        super().__init__(message or self.detail)
