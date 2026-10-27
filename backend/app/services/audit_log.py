"""Audit trail: one JSON line per command attempt, accepted or denied."""
from __future__ import annotations

import logging

from ..utils.json_utils import JsonUtils

_audit = logging.getLogger("robot_console.audit")


class AuditLog:
    def command(self, *, cid: str, robot_id: str, cmd: str, value: str | None,
                ip: str, result: str) -> None:
        # With a single shared token the actor is "operator"; per-user identity comes with OIDC.
        _audit.info(JsonUtils.to_str({
            "event": "command", "cid": cid, "robot": robot_id, "cmd": cmd, "value": value,
            "actor": "operator", "ip": ip, "result": result,
        }))
