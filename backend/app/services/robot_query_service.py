"""Read use cases for the REST API (debugging, tests, non-live consumers)."""
from __future__ import annotations

from ..exceptions.robot_not_found import RobotNotFound
from ..models.entities.robot import Robot
from ..repositories.robot_registry import RobotRegistry


class RobotQueryService:
    def __init__(self, state: RobotRegistry):
        self._state = state

    def page(self, limit: int, offset: int) -> tuple[int, list[Robot]]:
        ids = self._state.sorted_ids()[offset: offset + limit]
        return len(self._state.robots), [self._state.robots[i] for i in ids]

    def get(self, robot_id: str) -> Robot:
        r = self._state.get(robot_id)
        if r is None:
            raise RobotNotFound()
        return r
