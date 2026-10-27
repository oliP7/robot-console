"""Facts about the caller of an HTTP request."""
from __future__ import annotations

from fastapi import Request


class RequestUtils:
    @staticmethod
    def client_ip(request: Request) -> str:
        # X-Real-IP is set by our nginx from the TCP peer (not client-controlled).
        # The backend is only reachable through nginx in the compose stack.
        return request.headers.get("x-real-ip") or (request.client.host if request.client else "-")
