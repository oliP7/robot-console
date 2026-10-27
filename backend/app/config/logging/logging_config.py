"""Process-wide logging setup."""
from __future__ import annotations

import logging

FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


class LoggingConfig:
    @staticmethod
    def configure(level: str) -> None:
        logging.basicConfig(level=level, format=FORMAT)
