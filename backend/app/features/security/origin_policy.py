"""WebSocket Origin check."""
from __future__ import annotations

from urllib.parse import urlsplit


class OriginPolicy:
    @staticmethod
    def allowed(origin: str | None, host: str | None, extra_allowed: tuple[str, ...]) -> bool:
        """Browser WebSockets are not covered by CORS, so check Origin ourselves.

        No Origin header means a non-browser client (CLI, tests); those cannot be
        tricked by a malicious page, and the token is the control that applies to them.
        """
        if origin is None:
            return True
        if origin in extra_allowed:
            return True
        return bool(host) and urlsplit(origin).netloc == host
