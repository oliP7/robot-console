#!/usr/bin/env python3
"""Robot simulator: many robots per MQTT connection, for load testing.

robot.py runs one process and one connection per robot, which cannot produce
tens of thousands of robots on a laptop. This tool speaks the SAME protocol
(robots/<id>/telemetry out, robots/<id>/cmd in, same JSON fields, telemetry
emitted immediately after a command) but multiplexes many robots over one MQTT
connection per worker process.

Note: real robots each hold their own connection. This tool therefore measures
the bridge and the backend (message rate), not the broker's connection scaling.

    python tools/robot_sim.py --broker broker:1883 --robots 5000 --rate 1 --procs 4 --duration 30
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import random
import signal
import sys
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MODES = ("idle", "working", "error")
TICK = 0.01  # publish in 10 ms slices so the load is smooth, not bursty


def worker(idx: int, ids: list[str], host: str, port: int, rate: float, duration: float,
           sent: mp.Value, cmds: mp.Value, stop: mp.Event) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # the parent coordinates shutdown
    rnd = random.Random(idx)
    state = {rid: [round(rnd.uniform(20, 95), 1), "discharging", "idle"] for rid in ids}
    mine = set(ids)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"robot-sim-{idx}-{rnd.getrandbits(32):08x}")

    def payload(rid: str, ts: str) -> bytes:
        b, c, m = state[rid]
        return (f'{{"id":"{rid}","ts":"{ts}","battery_pct":{b},'
                f'"charge_state":"{c}","mode":"{m}"}}').encode()

    def on_connect(cl, _u, _f, rc, _p):
        if rc.is_failure:
            sys.stderr.write(f"[sim {idx}] connect refused: {rc}\n")
            return
        cl.subscribe("robots/+/cmd", qos=1)

    def on_message(cl, _u, msg):
        rid = msg.topic.split("/")[1]
        if rid not in mine:
            return
        try:
            cmd = json.loads(msg.payload)
        except ValueError:
            return
        s = state[rid]
        kind = cmd.get("cmd") if isinstance(cmd, dict) else None
        if kind == "toggle_charge":
            s[1] = "charging" if s[1] == "discharging" else "discharging"
        elif kind == "set_mode" and cmd.get("value") in MODES:
            s[2] = cmd["value"]
        elif kind == "kick":
            s[0] = min(100.0, round(s[0] + 5.0, 1))
        else:
            return
        with cmds.get_lock():
            cmds.value += 1
        cl.publish(f"robots/{rid}/telemetry", payload(rid, iso_now()), qos=0)

    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(host, port, keepalive=30)
    except OSError as exc:
        sys.stderr.write(f"[sim {idx}] cannot connect to {host}:{port}: {exc}\n")
        return
    client.loop_start()

    per_tick = len(ids) * rate * TICK  # fractional; carried over between ticks
    carry, cursor, local = 0.0, 0, 0
    topics = [f"robots/{rid}/telemetry" for rid in ids]
    deadline = time.monotonic() + duration
    next_t = time.monotonic()
    try:
        while not stop.is_set() and time.monotonic() < deadline:
            carry += per_tick
            n, carry = int(carry), carry - int(carry)
            ts = iso_now()
            for _ in range(n):
                rid = ids[cursor]
                s = state[rid]
                # battery drifts like robot.py, so most samples are real changes
                if s[1] == "charging":
                    s[0] = min(100.0, round(s[0] + rnd.uniform(0.4, 1.2), 1))
                else:
                    s[0] = max(0.0, round(s[0] - rnd.uniform(0.1, 0.6), 1))
                client.publish(topics[cursor], payload(rid, ts), qos=0)
                cursor = (cursor + 1) % len(ids)
            local += n
            if local >= 500:
                with sent.get_lock():
                    sent.value += local
                local = 0
            next_t += TICK
            delay = next_t - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            else:
                next_t = time.monotonic()  # cannot keep up: do not try to "catch up" in a burst
    finally:
        with sent.get_lock():
            sent.value += local
        client.loop_stop()
        client.disconnect()


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class RobotSimulator:
    """Starts and stops the worker processes; exposes counters to the caller."""

    def __init__(self, host: str, port: int, robots: int, rate: float, procs: int,
                 duration: float, prefix: str = "sim"):
        procs = max(1, min(procs, robots))
        ids = [f"{prefix}-{i:06d}" for i in range(robots)]
        self.sent = mp.Value("q", 0)
        self.cmds = mp.Value("q", 0)
        self.stop_event = mp.Event()
        self.ids = ids
        self.procs = [
            mp.Process(target=worker, daemon=True,
                       args=(i, ids[i::procs], host, port, rate, duration, self.sent, self.cmds, self.stop_event))
            for i in range(procs)
        ]

    def start(self) -> "RobotSimulator":
        for p in self.procs:
            p.start()
        return self

    def stop(self) -> None:
        self.stop_event.set()
        for p in self.procs:
            p.join(timeout=10)
            if p.is_alive():
                p.terminate()


def parse_broker(url: str) -> tuple[str, int]:
    url = url.split("://", 1)[-1]
    host, _, port = url.partition(":")
    return host, int(port or 1883)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--broker", default="localhost:1883")
    ap.add_argument("--robots", type=int, default=1000)
    ap.add_argument("--rate", type=float, default=1.0, help="telemetry Hz per robot")
    ap.add_argument("--procs", type=int, default=max(1, mp.cpu_count() // 2))
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--prefix", default="sim")
    a = ap.parse_args()
    host, port = parse_broker(a.broker)
    sim = RobotSimulator(host, port, a.robots, a.rate, a.procs, a.duration, a.prefix).start()
    print(f"simulating {a.robots} robots at {a.rate} Hz = {a.robots * a.rate:.0f} msg/s "
          f"over {len(sim.procs)} connections", flush=True)
    t0, last = time.monotonic(), 0
    try:
        while any(p.is_alive() for p in sim.procs):
            time.sleep(1)
            now_sent = sim.sent.value
            print(f"  t={time.monotonic() - t0:5.1f}s  sent/s={now_sent - last:7d}  commands={sim.cmds.value}",
                  flush=True)
            last = now_sent
    except KeyboardInterrupt:
        pass
    finally:
        sim.stop()


if __name__ == "__main__":
    main()
