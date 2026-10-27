"""Public client configuration, read by the UI before sign-in."""
from __future__ import annotations

from fastapi import APIRouter

from ..models.responses.server_config_response import ServerConfigResponse
from ..protocols.robot_protocol import RobotProtocol
from .dependencies.container_dependency import ContainerDep

router = APIRouter()


@router.get("/config", response_model=ServerConfigResponse)
async def get_config(c: ContainerDep) -> ServerConfigResponse:
    s = c.settings
    return ServerConfigResponse(auth_required=bool(s.auth_token), modes=list(RobotProtocol.MODES),
                                max_watch=s.max_watch, flush_ms=int(s.flush_interval * 1000))
