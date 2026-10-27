"""Command use case: checks, rate limit, publish, audit.

Success means published to the broker, not executed: robot.py has no ack, the
outcome is reported by the robot's own telemetry.
"""
from __future__ import annotations

import uuid

from ..exceptions.app_error import AppError
from ..exceptions.rate_limited import RateLimited
from ..exceptions.robot_not_found import RobotNotFound
from ..exceptions.robot_offline import RobotOffline
from ..features.observability.metrics import Metrics
from ..features.security.command_limiter import CommandLimiter
from ..interfaces.command_publisher import CommandPublisher
from ..protocols.robot_protocol import RobotProtocol
from ..repositories.robot_registry import RobotRegistry
from ..utils.json_utils import JsonUtils
from .audit_log import AuditLog


class CommandService:
    def __init__(self, state: RobotRegistry, publisher: CommandPublisher, limiter: CommandLimiter,
                 audit: AuditLog, metrics: Metrics):
        self._state = state
        self._publisher = publisher
        self._limiter = limiter
        self._audit = audit
        self._metrics = metrics

    def send(self, robot_id: str, cmd: str, value: str | None, ip: str) -> str:
        """Publish a command. Returns the command id or raises a AppError."""
        cid = uuid.uuid4().hex
        try:
            self._check(robot_id)
            payload: dict = {"cmd": cmd, "cid": cid}  # robot ignores unknown keys, cid is for tracing
            if value is not None:
                payload["value"] = value
            self._publisher.publish(RobotProtocol.command_topic(robot_id), JsonUtils.to_bytes(payload))
        except AppError as exc:
            self._audit.command(cid=cid, robot_id=robot_id, cmd=cmd, value=value, ip=ip, result=exc.result)
            raise
        self._metrics.commands_sent += 1
        self._audit.command(cid=cid, robot_id=robot_id, cmd=cmd, value=value, ip=ip, result="published")
        return cid

    def _check(self, robot_id: str) -> None:
        r = self._state.get(robot_id)
        if r is None:  # never publish to a topic we have not seen telemetry from
            raise RobotNotFound()
        if not r.online:  # robots use clean sessions: a command to an absent robot is lost
            raise RobotOffline()
        if not self._limiter.allow(robot_id):
            self._metrics.commands_rejected += 1
            raise RateLimited()
