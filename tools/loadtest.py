#!/usr/bin/env python3
"""Throughput benchmark for the backend: `make load`.

For each stage (target msg/s, robots at 1 Hz each) it:
  1. starts tools/robot_sim.py workers publishing through Mosquitto,
  2. keeps 10 WebSocket clients connected, each watching a 100-robot viewport,
  3. after a warm-up, samples the backend's /metrics once per second, and
  4. sends commands to simulated robots and times the round trip
     (REST -> MQTT -> robot -> telemetry -> backend -> WebSocket).

Everything is measured, nothing is estimated. Numbers depend on the host: the
simulator, the broker and the backend share the same machine.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import statistics
import sys
import time

import httpx
import websockets

sys.path.insert(0, os.path.dirname(__file__))
from robot_sim import RobotSimulator, parse_broker  # noqa: E402

BACKEND = os.environ.get("BACKEND_URL", "http://backend:8000")
BROKER = os.environ.get("MQTT_BROKER", "broker:1883")
WS_CLIENTS = 10
VIEWPORT = 100


def metrics(http: httpx.Client) -> dict[str, float]:
    out = {}
    for line in http.get(f"{BACKEND}/metrics", timeout=5).text.splitlines():
        if line and not line.startswith("#"):
            k, v = line.split()
            out[k] = float(v)
    return out


async def ws_client(ids: list[str], stats: dict, stop: asyncio.Event) -> None:
    async with websockets.connect(BACKEND.replace("http", "ws") + "/ws", max_size=2**24) as ws:
        await ws.send(json.dumps({"t": "view", "ids": ids}))
        while not stop.is_set():
            try:
                raw = await asyncio.wait_for(ws.recv(), 0.5)
            except TimeoutError:
                continue
            stats["frames"] += 1
            stats["bytes"] += len(raw)


async def command_rtt(http: httpx.AsyncClient, rid: str, n: int) -> list[float]:
    """Round trip of set_mode on one simulated robot, observed over a WebSocket."""
    latest: dict = {}
    changed = asyncio.Event()
    async with websockets.connect(BACKEND.replace("http", "ws") + "/ws", max_size=2**24) as ws:
        await ws.send(json.dumps({"t": "view", "ids": [rid]}))

        async def reader():
            async for raw in ws:
                f = json.loads(raw)
                if f["t"] == "delta":
                    for r in f["robots"]:
                        if r["id"] == rid:
                            latest.update(r)
                            changed.set()

        task = asyncio.create_task(reader())
        out = []
        try:
            await asyncio.wait_for(changed.wait(), 10)
            for i in range(n):
                target = ("working", "error", "idle")[i % 3]
                if latest.get("mode") == target:
                    target = "idle" if target != "idle" else "working"
                t0 = time.perf_counter()
                r = await http.post(f"/api/robots/{rid}/commands", json={"cmd": "set_mode", "value": target})
                if r.status_code != 202:
                    print(f"    command rejected: {r.status_code} {r.text}", flush=True)
                    continue
                while latest.get("mode") != target:
                    changed.clear()
                    await asyncio.wait_for(changed.wait(), 10)
                out.append((time.perf_counter() - t0) * 1000)
                await asyncio.sleep(0.3)
        except TimeoutError:
            print("    command round trip timed out", flush=True)
        finally:
            task.cancel()
        return out


def pct(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    return s[min(len(s) - 1, math.ceil(p / 100 * len(s)) - 1)]


async def run_stage(rate: int, warmup: float, window: float) -> dict:
    host, port = parse_broker(BROKER)
    robots = rate  # 1 Hz per robot: the realistic shape (robot count == msg/s)
    procs = max(1, min(10, math.ceil(rate / 6000)))
    sim = RobotSimulator(host, port, robots, 1.0, procs, warmup + window + 30, prefix=f"s{rate}").start()
    stop = asyncio.Event()
    ws_stats = {"frames": 0, "bytes": 0}
    http = httpx.Client()
    try:
        await asyncio.sleep(warmup)
        views = [sim.ids[i * VIEWPORT:(i + 1) * VIEWPORT] for i in range(WS_CLIENTS)]
        clients = [asyncio.create_task(ws_client(v, ws_stats, stop)) for v in views]
        await asyncio.sleep(1)
        m0, s0, t0 = metrics(http), sim.sent.value, time.monotonic()
        f0, b0 = ws_stats["frames"], ws_stats["bytes"]
        lags, rates = [], []
        async with httpx.AsyncClient(base_url=BACKEND, timeout=10) as ahttp:
            rtt_task = asyncio.create_task(command_rtt(ahttp, sim.ids[-1], 10))
            while time.monotonic() - t0 < window:
                await asyncio.sleep(1)
                m = metrics(http)
                lags.append(m["robot_console_event_loop_lag_ms"])
                rates.append(m["robot_console_ingest_rate"])
            rtts = await rtt_task
        m1, s1, t1 = metrics(http), sim.sent.value, time.monotonic()
        dt = t1 - t0
        stop.set()
        await asyncio.gather(*clients, return_exceptions=True)
        received = m1["robot_console_telemetry_messages_total"] - m0["robot_console_telemetry_messages_total"]
        sent = s1 - s0
        return {
            "target": rate,
            "sim_sent_per_s": sent / dt,
            "ingest_per_s": received / dt,
            "delivered_pct": 100 * received / sent if sent else float("nan"),
            "inbox_dropped": m1["robot_console_telemetry_dropped_total"] - m0["robot_console_telemetry_dropped_total"],
            "cpu_pct": 100 * (m1["process_cpu_seconds_total"] - m0["process_cpu_seconds_total"]) / dt,
            "rss_mb": m1.get("process_resident_memory_bytes", 0) / 2**20,
            "lag_p50_ms": statistics.median(lags) if lags else float("nan"),
            "lag_max_ms": max(lags) if lags else float("nan"),
            "robots_tracked": m1["robot_console_robots"],
            "ws_frames_per_s": (ws_stats["frames"] - f0) / dt,
            "ws_kib_per_s_per_client": (ws_stats["bytes"] - b0) / dt / 1024 / WS_CLIENTS,
            "cmd_rtt_p50_ms": statistics.median(rtts) if rtts else float("nan"),
            "cmd_rtt_p95_ms": pct(rtts, 95),
            "cmd_samples": len(rtts),
        }
    finally:
        stop.set()
        sim.stop()
        http.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stages", default="1000,5000,20000,50000", help="comma-separated msg/s targets")
    ap.add_argument("--warmup", type=float, default=8)
    ap.add_argument("--window", type=float, default=15)
    a = ap.parse_args()
    try:
        stages = [int(x) for x in a.stages.split(",") if x.strip()]
    except ValueError:
        sys.exit(f"--stages must be integers, got {a.stages!r}")
    print(f"host CPUs visible to the load container: {os.cpu_count()}", flush=True)
    results = []
    for rate in stages:
        print(f"\n== stage {rate} msg/s ({rate} robots at 1 Hz)", flush=True)
        try:
            r = asyncio.run(run_stage(rate, a.warmup, a.window))
        except (httpx.HTTPError, OSError) as exc:
            print(f"   stage failed: {exc!r}", flush=True)
            continue
        results.append(r)
        print("   " + json.dumps({k: round(v, 1) if isinstance(v, float) else v for k, v in r.items()}), flush=True)
        time.sleep(3)

    cols = [("target", "target/s"), ("sim_sent_per_s", "sent/s"), ("ingest_per_s", "ingested/s"),
            ("delivered_pct", "deliv%"), ("cpu_pct", "cpu%"), ("rss_mb", "rss MB"),
            ("lag_p50_ms", "lag p50"), ("lag_max_ms", "lag max"),
            ("ws_kib_per_s_per_client", "KiB/s/client"),
            ("cmd_rtt_p50_ms", "cmd p50 ms"), ("cmd_rtt_p95_ms", "cmd p95 ms")]
    print("\n| " + " | ".join(c[1] for c in cols) + " |")
    print("|" + "---|" * len(cols))
    for r in results:
        print("| " + " | ".join(f"{r[k]:.0f}" if k != "delivered_pct" else f"{r[k]:.1f}" for k, _ in cols) + " |")


if __name__ == "__main__":
    main()
