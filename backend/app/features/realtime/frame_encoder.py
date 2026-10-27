"""Builds the JSON frames of the WebSocket protocol (see frontend shared/models/server-frame.ts).

Robot JSON is pre-serialized and cached by RobotRegistry, so delta frames are
assembled by string concatenation instead of re-encoding every robot.
"""
from __future__ import annotations

from ...utils.json_utils import JsonUtils


class FrameEncoder:
    @staticmethod
    def hello(modes: tuple[str, ...], max_watch: int) -> str:
        return JsonUtils.to_str({"t": "hello", "modes": list(modes), "max_watch": max_watch})

    @staticmethod
    def full_index(sorted_ids: list[str]) -> str:
        return '{"t":"index","full":true,"ids":' + JsonUtils.to_str(sorted_ids) + "}"

    @staticmethod
    def index_diff(added: set[str], removed: set[str]) -> str:
        return JsonUtils.to_str({"t": "index", "add": list(added), "rm": list(removed)})

    @staticmethod
    def delta(robot_json: list[str]) -> str:
        return '{"t":"delta","robots":[' + ",".join(robot_json) + "]}"

    @staticmethod
    def summary(data: dict) -> str:
        return JsonUtils.to_str({**data, "t": "summary"})
