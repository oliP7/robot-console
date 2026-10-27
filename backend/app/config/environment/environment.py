"""Typed access to environment variables.

Secrets can be provided either directly (NAME) or as a file path (NAME_FILE),
which is the form Docker/Kubernetes secrets use. Nothing secret has a default.
"""
from __future__ import annotations

import os


class Environment:
    @staticmethod
    def get_str(name: str, default: str | None = None) -> str | None:
        value = os.environ.get(name)
        return value if value not in (None, "") else default

    @staticmethod
    def get_secret(name: str) -> str | None:
        path = Environment.get_str(f"{name}_FILE")
        if path:
            try:
                with open(path, encoding="utf-8") as fh:
                    return fh.read().strip() or None
            except OSError as exc:
                # Fail fast with a clear message; never echo the file content.
                raise RuntimeError(f"{name}_FILE={path!r} is not readable: {exc.strerror}") from exc
        return Environment.get_str(name)

    @staticmethod
    def get_list(name: str) -> tuple[str, ...]:
        raw = Environment.get_str(name)
        return tuple(x.strip() for x in raw.split(",") if x.strip()) if raw else ()

    @staticmethod
    def get_float(name: str, default: float) -> float:
        raw = Environment.get_str(name)
        if raw is None:
            return default
        try:
            return float(raw)
        except ValueError as exc:
            raise ValueError(f"{name} must be a number, got {raw!r}") from exc

    @staticmethod
    def get_int(name: str, default: int) -> int:
        raw = Environment.get_str(name)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer, got {raw!r}") from exc

    @staticmethod
    def get_bool(name: str, default: bool = False) -> bool:
        raw = Environment.get_str(name)
        return default if raw is None else raw.strip().lower() in {"1", "true", "yes", "on"}
