"""JSON encoding and decoding, in one place (orjson everywhere)."""
from __future__ import annotations

from typing import Any

import orjson


class JsonUtils:
    @staticmethod
    def to_str(obj: Any) -> str:
        return orjson.dumps(obj).decode()

    @staticmethod
    def to_bytes(obj: Any) -> bytes:
        return orjson.dumps(obj)

    @staticmethod
    def parse(data: str | bytes) -> Any:
        """Decode JSON. Raises ValueError on invalid input."""
        return orjson.loads(data)
