"""Shared-token authentication."""
from __future__ import annotations

import hmac

_BEARER = "bearer "


class TokenAuth:
    @staticmethod
    def matches(expected: str | None, supplied: str | None) -> bool:
        """Constant-time comparison. With no configured token, auth is disabled."""
        if not expected:
            return True
        if not supplied:
            return False
        return hmac.compare_digest(expected.encode(), supplied.encode())

    @staticmethod
    def bearer_token(authorization: str | None) -> str | None:
        """Extract the token from an `Authorization: Bearer <token>` header."""
        if authorization and authorization.lower().startswith(_BEARER):
            return authorization[len(_BEARER):]
        return None
