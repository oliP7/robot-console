"""Maps business errors to HTTP responses, in one place."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ...exceptions.app_error import AppError
from ...exceptions.broker_unavailable import BrokerUnavailable
from ...exceptions.rate_limited import RateLimited
from ...exceptions.robot_not_found import RobotNotFound
from ...exceptions.robot_offline import RobotOffline


class ErrorHandlerManager:
    # error type -> (HTTP status, extra headers). The message comes from the error class.
    STATUS: dict[type[AppError], tuple[int, dict[str, str]]] = {
        RobotNotFound: (404, {}),
        RobotOffline: (409, {}),
        RateLimited: (429, {"Retry-After": "1"}),
        BrokerUnavailable: (503, {}),
    }

    def __init__(self, app: FastAPI):
        self._app = app

    def register(self) -> None:
        self._app.add_exception_handler(AppError, self._handle)

    @classmethod
    async def _handle(cls, _request: Request, exc: Exception) -> JSONResponse:
        status, headers = cls.STATUS.get(type(exc), (500, {}))
        detail = exc.detail if isinstance(exc, AppError) else "internal error"
        return JSONResponse({"detail": detail}, status_code=status, headers=headers)
