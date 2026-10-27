"""End-to-end test against the real stack: Mosquitto, the backend, nginx and
unmodified robot.py containers. No mocks anywhere on the path.

Proves: a command sent through the client API (REST) reaches a robot, the robot
changes state, and the change is observed by TWO independent WebSocket clients,
both directly on the backend and through the nginx front door.
"""
from __future__ import annotations

import asyncio
import json
import os
import time

import httpx
import pytest
import websockets

BACKEND = os.environ.get("BACKEND_URL", "http://backend:8000")
WEB = os.environ.get("WEB_URL", "http://web:8080")
TOKEN_FILE = os.environ.get("TOKEN_FILE", "/run/robot-console-secrets/api.token")
TIMEOUT = 10.0


def ws_url(base: str) -> str:
    return base.replace("http://", "ws://") + "/ws"


@pytest.fixture(scope="session")
def token() -> str:
    try:
        with open(TOKEN_FILE, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError as exc:
        pytest.fail(f"cannot read API token from {TOKEN_FILE}: {exc}")


@pytest.fixture(scope="session")
def robots(token) -> list[dict]:
    """Wait until the real robot containers are online."""
    deadline = time.time() + 45
    last = None
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BACKEND}/api/robots", headers={"Authorization": f"Bearer {token}"}, timeout=3)
            last = r.status_code
            online = [x for x in r.json().get("robots", []) if x["online"]] if r.status_code == 200 else []
            if len(online) >= 2:
                return online
        except httpx.HTTPError as exc:
            last = repr(exc)
        time.sleep(0.5)
    pytest.fail(f"robots never came online (last response: {last})")


class Watcher:
    """One live client: authenticates, watches one robot, records what it sees."""

    def __init__(self, name: str, base: str, token: str, robot_id: str):
        self.name, self.base, self.token, self.robot_id = name, base, token, robot_id
        self.latest: dict | None = None
        self.changed = asyncio.Event()
        self.ws = None
        self.task: asyncio.Task | None = None

    async def __aenter__(self):
        self.ws = await websockets.connect(ws_url(self.base), open_timeout=TIMEOUT)
        await self.ws.send(json.dumps({"t": "auth", "token": self.token}))
        hello = json.loads(await asyncio.wait_for(self.ws.recv(), TIMEOUT))
        assert hello["t"] == "hello", hello
        await self.ws.send(json.dumps({"t": "view", "ids": [self.robot_id]}))
        self.task = asyncio.create_task(self._read())
        await self.wait_for(lambda r: True)  # initial state of the watched robot
        return self

    async def __aexit__(self, *exc):
        if self.task:
            self.task.cancel()
        await self.ws.close()

    async def _read(self):
        async for raw in self.ws:
            frame = json.loads(raw)
            if frame["t"] == "delta":
                for r in frame["robots"]:
                    if r["id"] == self.robot_id:
                        self.latest = r
                        self.changed.set()

    async def wait_for(self, pred, timeout: float = TIMEOUT) -> dict:
        deadline = asyncio.get_running_loop().time() + timeout
        while not (self.latest and pred(self.latest)):
            self.changed.clear()
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise AssertionError(f"{self.name}: condition not met, last state {self.latest}")
            try:
                await asyncio.wait_for(self.changed.wait(), remaining)
            except TimeoutError:
                pass
        return self.latest


async def roundtrip(base: str, token: str, robot_id: str, label: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    async with Watcher("A", base, token, robot_id) as a, Watcher("B", base, token, robot_id) as b:
        async with httpx.AsyncClient(base_url=base, headers=headers, timeout=TIMEOUT) as http:
            # 1) set_mode to a mode the robot is NOT in, so a change must happen.
            target = next(m for m in ("working", "error", "idle") if m != a.latest["mode"])
            t0 = time.perf_counter()
            r = await http.post(f"/api/robots/{robot_id}/commands", json={"cmd": "set_mode", "value": target})
            assert r.status_code == 202, r.text
            seen = await asyncio.gather(a.wait_for(lambda s: s["mode"] == target),
                                        b.wait_for(lambda s: s["mode"] == target))
            ms = (time.perf_counter() - t0) * 1000
            assert all(s["mode"] == target and s["online"] for s in seen)
            print(f"\n[{label}] set_mode={target}: both clients saw the robot report it after {ms:.0f} ms")

            # 2) toggle_charge: the robot flips its charge state.
            before = a.latest["charge"]
            t0 = time.perf_counter()
            r = await http.post(f"/api/robots/{robot_id}/commands", json={"cmd": "toggle_charge"})
            assert r.status_code == 202, r.text
            await asyncio.gather(a.wait_for(lambda s: s["charge"] != before),
                                 b.wait_for(lambda s: s["charge"] != before))
            ms = (time.perf_counter() - t0) * 1000
            print(f"[{label}] toggle_charge from {before}: both clients saw it after {ms:.0f} ms")


@pytest.mark.parametrize("base,label", [(BACKEND, "backend direct"), (WEB, "through nginx")])
def test_command_reaches_robot_and_all_clients_see_it(base, label, token, robots):
    asyncio.run(roundtrip(base, token, robots[0]["id"], label))


def test_rest_rejects_missing_or_wrong_token(robots):
    rid = robots[0]["id"]
    for headers in ({}, {"Authorization": "Bearer wrong"}):
        r = httpx.post(f"{WEB}/api/robots/{rid}/commands", json={"cmd": "kick"}, headers=headers, timeout=5)
        assert r.status_code == 401


def test_websocket_rejects_wrong_token():
    async def go():
        async with websockets.connect(ws_url(WEB)) as ws:
            await ws.send(json.dumps({"t": "auth", "token": "wrong"}))
            with pytest.raises(websockets.ConnectionClosed) as exc:
                await asyncio.wait_for(ws.recv(), TIMEOUT)
            assert exc.value.rcvd.code == 4401
    asyncio.run(go())


def test_websocket_rejects_foreign_origin_through_nginx():
    async def go():
        with pytest.raises(websockets.InvalidStatus) as exc:
            async with websockets.connect(ws_url(WEB), origin="https://evil.example"):
                pass
        assert exc.value.response.status_code == 403
    asyncio.run(go())


def test_nginx_security_headers_and_no_internal_endpoints():
    r = httpx.get(f"{WEB}/", timeout=5)
    assert r.status_code == 200
    csp = r.headers["content-security-policy"]
    assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    # /metrics is internal: nginx does not proxy it (the SPA fallback answers instead).
    assert "robot_console_robots" not in httpx.get(f"{WEB}/metrics", timeout=5).text


def test_unknown_robot_and_invalid_command(token, robots):
    h = {"Authorization": f"Bearer {token}"}
    assert httpx.post(f"{WEB}/api/robots/nope/commands", json={"cmd": "kick"}, headers=h, timeout=5).status_code == 404
    bad = httpx.post(f"{WEB}/api/robots/{robots[0]['id']}/commands", json={"cmd": "rm -rf"}, headers=h, timeout=5)
    assert bad.status_code == 422
