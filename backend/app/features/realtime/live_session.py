"""One WebSocket connection: origin check, auth handshake, hello, then a
read-only push. The only client message after auth is {"t":"view","ids":[...]}."""
from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from ...config.settings import Settings
from ...protocols.robot_protocol import RobotProtocol
from ...utils.json_utils import JsonUtils
from ..security.origin_policy import OriginPolicy
from ..security.token_auth import TokenAuth
from .frame_encoder import FrameEncoder
from .hub import Hub

log = logging.getLogger("robot_console.ws")

CLOSE_FORBIDDEN = 4403
CLOSE_UNAUTHORIZED = 4401
AUTH_TIMEOUT_S = 5


class LiveSessionHandler:
    def __init__(self, hub: Hub, settings: Settings):
        self._hub = hub
        self._s = settings

    async def handle(self, ws: WebSocket) -> None:
        origin = ws.headers.get("origin")
        if not OriginPolicy.allowed(origin, ws.headers.get("host"), self._s.allowed_origins):
            log.warning("websocket rejected: origin %r not allowed", origin)
            await ws.close(code=CLOSE_FORBIDDEN)  # closing before accept rejects the handshake (HTTP 403)
            return
        await ws.accept()
        if self._s.auth_token and not await self._authenticate(ws):
            await ws.close(code=CLOSE_UNAUTHORIZED)
            return
        await ws.send_text(FrameEncoder.hello(RobotProtocol.MODES, self._s.max_watch))
        await self._serve(ws)

    async def _authenticate(self, ws: WebSocket) -> bool:
        """The token travels in the first message, not in the URL (URLs end up in logs)."""
        try:
            first = JsonUtils.parse(await asyncio.wait_for(ws.receive_text(), AUTH_TIMEOUT_S))
        except Exception:
            return False
        if not isinstance(first, dict) or first.get("t") != "auth":
            return False
        token = first.get("token")
        return TokenAuth.matches(self._s.auth_token, token if isinstance(token, str) else None)

    async def _serve(self, ws: WebSocket) -> None:
        hub = self._hub
        client = hub.add_client(ws)
        writer = asyncio.create_task(hub.writer(client))
        try:
            while not client.closed:
                try:
                    msg = JsonUtils.parse(await ws.receive_text())
                except ValueError:
                    continue
                if isinstance(msg, dict) and msg.get("t") == "view":
                    hub.set_watch(client, msg.get("ids"))
        except WebSocketDisconnect:
            pass  # normal: the client left
        except Exception:
            # A client dropped by the writer is already logged there; anything else
            # (protocol error, server bug) is unexpected: log it, then clean up.
            if not client.closed:
                log.warning("websocket session ended with an error", exc_info=True)
        finally:
            hub.remove_client(client)
            writer.cancel()
            await asyncio.gather(writer, return_exceptions=True)
