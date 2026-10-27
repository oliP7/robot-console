"""Process resource usage, dependency-free."""
from __future__ import annotations

import os
import time

_PAGE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096


class ProcessStats:
    @staticmethod
    def cpu_seconds() -> float:
        """CPU of the whole process (event loop plus the paho network thread)."""
        return time.process_time()

    @staticmethod
    def rss_bytes() -> int:
        """Resident memory from /proc (Linux). 0 where /proc is unavailable."""
        try:
            with open("/proc/self/statm", encoding="ascii") as fh:
                return int(fh.read().split()[1]) * _PAGE
        except (OSError, ValueError, IndexError):
            return 0
