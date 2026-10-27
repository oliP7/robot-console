"""Robots API: read robots and send them commands.

Commands go over REST (easy to authenticate, validate, rate limit and audit); the
read endpoints serve debugging, tests and non-live consumers.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from ..models.requests.command_request import CommandRequest
from ..models.responses.command_accepted_response import CommandAcceptedResponse
from ..models.responses.error_response import ErrorResponse
from ..models.responses.robot_page_response import RobotPageResponse
from ..models.responses.robot_response import RobotResponse
from ..protocols.robot_protocol import RobotProtocol
from ..utils.request_utils import RequestUtils
from .dependencies.container_dependency import ContainerDep

router = APIRouter()

RobotId = Annotated[str, Path(pattern=RobotProtocol.ID_PATTERN)]


@router.get("", response_model=RobotPageResponse)
async def list_robots(c: ContainerDep, limit: int = Query(100, ge=1, le=500),
                      offset: int = Query(0, ge=0)) -> RobotPageResponse:
    total, robots = c.robots.page(limit, offset)
    return RobotPageResponse(total=total, robots=[RobotResponse.from_entity(r) for r in robots])


@router.get("/{robot_id}", response_model=RobotResponse, responses={404: {"model": ErrorResponse}})
async def get_robot(c: ContainerDep, robot_id: RobotId) -> RobotResponse:
    return RobotResponse.from_entity(c.robots.get(robot_id))


@router.post("/{robot_id}/commands", status_code=202, response_model=CommandAcceptedResponse,
             responses={s: {"model": ErrorResponse} for s in (404, 409, 429, 503)})
async def send_command(body: CommandRequest, request: Request, c: ContainerDep,
                       robot_id: RobotId) -> CommandAcceptedResponse:
    # 202: published to the broker, not executed. The robot's telemetry reports the outcome.
    cid = c.commands.send(robot_id, body.cmd, body.value, RequestUtils.client_ip(request))
    return CommandAcceptedResponse(command_id=cid, robot_id=robot_id)
