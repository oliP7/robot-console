"""Operational endpoints: liveness, readiness, metrics (not exposed via nginx)."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse

from ..models.responses.status_response import StatusResponse
from .dependencies.container_dependency import ContainerDep

router = APIRouter()


@router.get("/healthz", response_model=StatusResponse, responses={503: {"model": StatusResponse}})
async def healthz(c: ContainerDep):
    # Liveness: the process and its background loops are running.
    if not c.supervisor.healthy:
        return JSONResponse({"status": "background task stopped"}, status_code=503)
    return StatusResponse(status="ok")


@router.get("/readyz", response_model=StatusResponse, responses={503: {"model": StatusResponse}})
async def readyz(c: ContainerDep):
    # Readiness: able to serve live data (broker connected).
    if not c.broker.connected:
        return JSONResponse({"status": "broker_unavailable"}, status_code=503)
    return StatusResponse(status="ready")


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics(c: ContainerDep):
    return c.exporter.render()
