#!/usr/bin/env python3
"""
Mock robot — coding-challenge handout.

Simulates one robot. Connects to an MQTT broker, publishes telemetry on
`robots/<id>/telemetry`, and listens for commands on `robots/<id>/cmd`.

Run one instance per robot. Run as many as you like in parallel.

Typical use:

    python3 robot.py --broker tcp://localhost:1883
    python3 robot.py --broker tcp://localhost:1883 --rate 2.0
    python3 robot.py --broker tcp://broker.local:1883 --id robot-bench-01

Telemetry payload (JSON, published every tick on `robots/<id>/telemetry`):

    {
      "id": "<id>",
      "ts": "<ISO8601 UTC>",
      "battery_pct": 73.4,            // number, 0..100, drifts up/down with charge_state
      "charge_state": "discharging",  // string: "charging" | "discharging"
      "mode": "idle"                  // string: "idle" | "working" | "error"
    }

Command vocabulary (JSON, sent to `robots/<id>/cmd`):

    {"cmd": "toggle_charge"}                 // flip charge_state
    {"cmd": "set_mode", "value": "working"}  // set mode to one of the known values
    {"cmd": "kick"}                          // bump battery by +5% (silly demo command)

The robot acks by emitting its next telemetry message — there is no separate
ack channel. Commands that the robot does not understand are ignored.

Dependencies: paho-mqtt. Install with `pip install paho-mqtt`.
"""

import argparse
import json
import random
import signal
import sys
import threading
import time
import uuid
from datetime import datetime, timezone

try:
    import paho.mqtt.client as mqtt
except ImportError:
    sys.stderr.write("error: paho-mqtt is required.  pip install paho-mqtt\n")
    sys.exit(1)


VALID_MODES = {"idle", "working", "error"}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class Robot:
    def __init__(self, robot_id: str, broker_url: str, rate_hz: float):
        self.id = robot_id
        self.broker_url = broker_url
        self.period = 1.0 / max(rate_hz, 0.0001)
        self.battery_pct = round(random.uniform(40.0, 90.0), 1)
        self.charge_state = "discharging"
        self.mode = "idle"
        self._stop = threading.Event()
        self._lock = threading.Lock()

        self.telemetry_topic = f"robots/{self.id}/telemetry"
        self.cmd_topic = f"robots/{self.id}/cmd"

        host, port = self._parse_broker(broker_url)
        self.client = mqtt.Client(client_id=f"robot-{self.id}", clean_session=True)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(host, port, keepalive=30)
        self.client.loop_start()

    @staticmethod
    def _parse_broker(url: str):
        # Accept "tcp://host:port", "host:port", "host"
        if "://" in url:
            url = url.split("://", 1)[1]
        if ":" in url:
            host, port = url.rsplit(":", 1)
            return host, int(port)
        return url, 1883

    def _on_connect(self, client, _userdata, _flags, rc):
        if rc == 0:
            sys.stderr.write(f"[robot {self.id}] connected to {self.broker_url}\n")
            client.subscribe(self.cmd_topic, qos=1)
        else:
            sys.stderr.write(f"[robot {self.id}] connect failed rc={rc}\n")

    def _on_message(self, _client, _userdata, msg):
        try:
            cmd = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            sys.stderr.write(f"[robot {self.id}] ignoring malformed command\n")
            return
        self._handle_command(cmd)

    def _handle_command(self, cmd: dict):
        with self._lock:
            kind = cmd.get("cmd")
            if kind == "toggle_charge":
                self.charge_state = "charging" if self.charge_state == "discharging" else "discharging"
                sys.stderr.write(f"[robot {self.id}] toggle_charge -> {self.charge_state}\n")
            elif kind == "set_mode":
                value = cmd.get("value")
                if value in VALID_MODES:
                    self.mode = value
                    sys.stderr.write(f"[robot {self.id}] set_mode -> {self.mode}\n")
            elif kind == "kick":
                self.battery_pct = min(100.0, round(self.battery_pct + 5.0, 1))
                sys.stderr.write(f"[robot {self.id}] kick -> battery {self.battery_pct}\n")
            else:
                sys.stderr.write(f"[robot {self.id}] unknown command: {cmd!r}\n")
        # Emit immediately so the change is observable straight away.
        self._tick()

    def _drift(self):
        with self._lock:
            if self.charge_state == "charging":
                self.battery_pct = min(100.0, round(self.battery_pct + random.uniform(0.4, 1.2), 1))
                if self.battery_pct >= 100.0:
                    self.charge_state = "discharging"
            else:
                self.battery_pct = max(0.0, round(self.battery_pct - random.uniform(0.1, 0.6), 1))
                if self.battery_pct <= 5.0:
                    self.charge_state = "charging"

    def _payload(self) -> bytes:
        with self._lock:
            evt = {
                "id": self.id,
                "ts": iso_now(),
                "battery_pct": self.battery_pct,
                "charge_state": self.charge_state,
                "mode": self.mode,
            }
        return json.dumps(evt).encode("utf-8")

    def _tick(self):
        try:
            self.client.publish(self.telemetry_topic, self._payload(), qos=0, retain=False)
        except Exception as e:
            sys.stderr.write(f"[robot {self.id}] publish failed: {e}\n")

    def run(self):
        sys.stderr.write(f"[robot {self.id}] publishing on {self.telemetry_topic} every {self.period:.2f}s\n")
        next_tick = time.monotonic()
        while not self._stop.is_set():
            self._drift()
            self._tick()
            next_tick += self.period
            sleep = next_tick - time.monotonic()
            if sleep > 0:
                self._stop.wait(timeout=sleep)
            else:
                next_tick = time.monotonic()

    def stop(self):
        self._stop.set()
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--broker", default="tcp://localhost:1883",
                   help="MQTT broker URL, e.g. tcp://localhost:1883 (default: %(default)s)")
    p.add_argument("--id", default=None,
                   help="Robot id. If omitted, a short random id is generated.")
    p.add_argument("--rate", type=float, default=1.0,
                   help="Telemetry publish rate in Hz (default: %(default)s)")
    p.add_argument("--seed", type=int, default=None, help="Random seed for reproducible runs")
    return p.parse_args()


def main():
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    robot_id = args.id or f"r-{uuid.uuid4().hex[:6]}"
    robot = Robot(robot_id=robot_id, broker_url=args.broker, rate_hz=args.rate)

    def stop(_sig, _frm):
        sys.stderr.write(f"[robot {robot.id}] stopping\n")
        robot.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    robot.run()


if __name__ == "__main__":
    main()
