import time

import orjson
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.config.settings import Settings
from app.main import create_app
from tests.support.fakes import FakeBroker
from tests.support.samples import sample

TOKEN = "test-token-not-a-secret"


def build(**overrides):
    broker = FakeBroker()
    app = create_app(Settings(**overrides), broker=broker)
    return app, broker


@pytest.fixture
def api():
    app, broker = build(cmd_rate_robot=2)
    with TestClient(app) as client:
        app.state.container.registry.apply("r1", sample(), now=time.monotonic())
        yield client, app, broker


def test_health_ready_and_config(api):
    client, _, broker = api
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 200
    broker.connected = False
    assert client.get("/readyz").status_code == 503
    assert client.get("/api/config").json()["auth_required"] is False
    assert "process_cpu_seconds_total" in client.get("/metrics").text


def test_command_is_published_with_202(api):
    client, _, broker = api
    r = client.post("/api/robots/r1/commands", json={"cmd": "set_mode", "value": "working"})
    assert r.status_code == 202 and r.json()["status"] == "published"
    topic, payload = broker.published[-1]
    body = orjson.loads(payload)
    assert topic == "robots/r1/cmd"
    assert body["cmd"] == "set_mode" and body["value"] == "working" and body["cid"] == r.json()["command_id"]


@pytest.mark.parametrize("body", [
    {"cmd": "self_destruct"},
    {"cmd": "set_mode"},
    {"cmd": "set_mode", "value": "turbo"},
    {"cmd": "kick", "value": "x"},
    {"cmd": "kick", "extra": 1},
])
def test_command_allowlist(api, body):
    client, _, broker = api
    assert client.post("/api/robots/r1/commands", json=body).status_code == 422
    assert broker.published == []


def test_non_json_content_type_is_rejected(api):
    """A cross-site form or text/plain POST (no CORS preflight) must not work."""
    client, _, broker = api
    r = client.post("/api/robots/r1/commands", content=b'{"cmd":"kick"}',
                    headers={"content-type": "text/plain"})
    assert r.status_code == 422 and broker.published == []


def test_unknown_offline_invalid_robot(api):
    client, app, _ = api
    assert client.post("/api/robots/nope/commands", json={"cmd": "kick"}).status_code == 404
    assert client.post("/api/robots/bad.id/commands", json={"cmd": "kick"}).status_code == 422
    app.state.container.registry.sweep(time.monotonic() + 3600)
    assert client.post("/api/robots/r1/commands", json={"cmd": "kick"}).status_code == 409


def test_rate_limit_per_robot(api):
    client, _, _ = api
    codes = [client.post("/api/robots/r1/commands", json={"cmd": "kick"}).status_code for _ in range(6)]
    assert codes[:4] == [202] * 4 and 429 in codes  # burst = 2 x rate


def test_broker_down_gives_503(api):
    client, _, broker = api
    broker.connected = False
    r = client.post("/api/robots/r1/commands", json={"cmd": "kick"})
    # The fixed client message, never the broker's internal error string.
    assert r.status_code == 503 and r.json() == {"detail": "broker unavailable"}


def test_auth_required_for_rest_when_token_set():
    app, broker = build(auth_token=TOKEN)
    with TestClient(app) as client:
        app.state.container.registry.apply("r1", sample(), now=time.monotonic())
        assert client.get("/api/config").json()["auth_required"] is True
        assert client.get("/api/robots").status_code == 401
        bad = client.post("/api/robots/r1/commands", json={"cmd": "kick"},
                          headers={"Authorization": "Bearer wrong"})
        assert bad.status_code == 401 and broker.published == []
        ok = client.post("/api/robots/r1/commands", json={"cmd": "kick"},
                         headers={"Authorization": f"Bearer {TOKEN}"})
        assert ok.status_code == 202


PUBLIC_API = {"/api/config"}


def test_every_api_route_except_public_ones_requires_the_token():
    # Guards the RouterManager registry: a new router without auth=True fails here.
    app, _ = build(auth_token=TOKEN)
    # The OpenAPI schema is the public list of every registered HTTP route.
    paths = {p: ops for p, ops in app.openapi()["paths"].items()
             if p.startswith("/api") and p not in PUBLIC_API}
    assert {"/api/robots", "/api/robots/{robot_id}", "/api/robots/{robot_id}/commands"} <= paths.keys()
    with TestClient(app) as client:
        for path, ops in paths.items():
            for method in ops:
                url = path.replace("{robot_id}", "r1")
                assert client.request(method, url).status_code == 401, (method, url)


def test_docs_can_be_disabled():
    app, _ = build(disable_docs=True)
    with TestClient(app) as client:
        assert client.get("/api/docs").status_code == 404
        assert client.get("/api/openapi.json").status_code == 404


def test_websocket_requires_auth_message_when_token_set():
    app, _ = build(auth_token=TOKEN)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_text('{"t":"auth","token":"wrong"}')
            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_text()
            assert exc.value.code == 4401
        with client.websocket_connect("/ws") as ws:
            ws.send_text(orjson.dumps({"t": "auth", "token": TOKEN}).decode())
            assert orjson.loads(ws.receive_text())["t"] == "hello"


def test_websocket_stream_index_then_delta_for_watched(api):
    client, app, _ = api
    with client.websocket_connect("/ws") as ws:
        assert orjson.loads(ws.receive_text())["t"] == "hello"
        seen = {}
        ws.send_text('{"t":"view","ids":["r1"]}')
        while "delta" not in seen:
            f = orjson.loads(ws.receive_text())
            seen[f["t"]] = f
        assert seen["index"]["ids"] == ["r1"]
        assert seen["delta"]["robots"][0]["id"] == "r1"


def test_websocket_rejects_foreign_origin(api):
    client, _, _ = api
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws", headers={"origin": "https://evil.example"}) as ws:
            ws.receive_text()
    assert exc.value.code == 4403


def test_settings_validation():
    with pytest.raises(ValueError):
        Settings(flush_interval=0)
    with pytest.raises(ValueError):
        Settings(offline_after=10, forget_after=5)
    with pytest.raises(ValueError, match="MQTT_PORT"):
        Settings(mqtt_port=70000)
