"""Runtime configuration. Everything comes from environment variables (see environment/environment.py)."""
from __future__ import annotations

from dataclasses import dataclass

from .environment.environment import Environment as Env


@dataclass(frozen=True)
class Settings:
    # Broker connection
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_tls: bool = False
    mqtt_ca_file: str | None = None

    # Pipeline timings (seconds)
    flush_interval: float = 0.05     # min gap between two pushes (max 20 frames/s per client)
    drain_interval: float = 0.02     # how often the MQTT inbox is drained
    offline_after: float = 6.0       # robot is offline after this much silence
    forget_after: float = 600.0      # offline robots are dropped after this long

    # Capacity guards
    max_robots: int = 200_000        # refuse to track more distinct ids than this
    max_watch: int = 400             # max robots one client may watch at once
    inbox_max: int = 200_000         # bounded inbox, oldest sample dropped first
    send_timeout: float = 5.0        # a client that cannot take a frame is dropped

    # Security
    auth_token: str | None = None    # when unset, authentication is disabled
    # Extra browser origins allowed on the WebSocket. Same-origin is always allowed.
    allowed_origins: tuple[str, ...] = ()
    cmd_rate_global: float = 200.0   # commands per second, whole service
    cmd_rate_robot: float = 10.0     # commands per second, per robot

    log_level: str = "INFO"
    disable_docs: bool = False      # hide /api/docs and /api/openapi.json (production)

    def __post_init__(self) -> None:
        positive = ("flush_interval", "drain_interval", "offline_after", "forget_after",
                    "max_robots", "max_watch", "inbox_max", "send_timeout",
                    "cmd_rate_global", "cmd_rate_robot")
        for name in positive:
            if getattr(self, name) <= 0:
                raise ValueError(f"{name.upper()} must be > 0")
        if self.forget_after < self.offline_after:
            raise ValueError("FORGET_AFTER must be >= OFFLINE_AFTER")
        if not 1 <= self.mqtt_port <= 65535:
            raise ValueError("MQTT_PORT must be between 1 and 65535")

    @classmethod
    def from_env(cls) -> "Settings":
        # Defaults come from the field declarations above (one source of truth).
        return cls(
            mqtt_host=Env.get_str("MQTT_HOST", cls.mqtt_host) or cls.mqtt_host,
            mqtt_port=Env.get_int("MQTT_PORT", cls.mqtt_port),
            mqtt_username=Env.get_str("MQTT_USERNAME"),
            mqtt_password=Env.get_secret("MQTT_PASSWORD"),
            mqtt_tls=Env.get_bool("MQTT_TLS", cls.mqtt_tls),
            mqtt_ca_file=Env.get_str("MQTT_CA_FILE"),
            flush_interval=Env.get_float("FLUSH_INTERVAL", cls.flush_interval),
            drain_interval=Env.get_float("DRAIN_INTERVAL", cls.drain_interval),
            offline_after=Env.get_float("OFFLINE_AFTER", cls.offline_after),
            forget_after=Env.get_float("FORGET_AFTER", cls.forget_after),
            max_robots=Env.get_int("MAX_ROBOTS", cls.max_robots),
            max_watch=Env.get_int("MAX_WATCH", cls.max_watch),
            inbox_max=Env.get_int("INBOX_MAX", cls.inbox_max),
            send_timeout=Env.get_float("SEND_TIMEOUT", cls.send_timeout),
            auth_token=Env.get_secret("AUTH_TOKEN"),
            allowed_origins=Env.get_list("ALLOWED_ORIGINS"),
            cmd_rate_global=Env.get_float("CMD_RATE_GLOBAL", cls.cmd_rate_global),
            cmd_rate_robot=Env.get_float("CMD_RATE_ROBOT", cls.cmd_rate_robot),
            log_level=(Env.get_str("LOG_LEVEL", cls.log_level) or cls.log_level).upper(),
            disable_docs=Env.get_bool("DISABLE_DOCS", cls.disable_docs),
        )
