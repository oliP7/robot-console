"""The global or per-robot command rate limit was exceeded."""
from __future__ import annotations

from .app_error import AppError


class RateLimited(AppError):
    result = "rate_limited"
    detail = "too many commands"
