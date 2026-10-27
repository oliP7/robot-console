"""WebSocket fan-out: client registry and routing of changes.

Core idea: clients subscribe to WHAT THEY SEE (the rows in their viewport), not to
all robots. Per-client traffic is therefore bounded by the viewport size and
is independent of the robot count. Every robot is serialized at most once per change
(see RobotRegistry.json_of), no matter how many clients watch it.
"""
from __future__ import annotations

from ...config.settings import Settings
from ...protocols.robot_protocol import RobotProtocol
from ...repositories.robot_registry import RobotRegistry
from ..observability.metrics import Metrics
from .client_session import ClientSession
from .client_writer import ClientWriter
from .summary_builder import SummaryBuilder


class Hub:
    def __init__(self, state: RobotRegistry, settings: Settings, metrics: Metrics,
                 summaries: SummaryBuilder | None = None):
        self.state = state
        self._max_watch = settings.max_watch
        self.metrics = metrics
        self.summaries = summaries or SummaryBuilder(state, metrics)
        self.clients: set[ClientSession] = set()
        self._writer = ClientWriter(state, settings, metrics, on_drop=self.remove_client)
        self._last_summary: str | None = None

    # ---- client management --------------------------------------------------
    def add_client(self, ws) -> ClientSession:
        c = ClientSession(ws)
        # A new client gets the latest summary right away, not up to 1 s later.
        c.summary = self._last_summary or self.summaries.build(len(self.clients))
        self.clients.add(c)
        self.metrics.ws_clients = len(self.clients)
        c.wake.set()  # triggers the initial full index
        return c

    def remove_client(self, c: ClientSession) -> None:
        c.closed = True
        self.clients.discard(c)
        self.metrics.ws_clients = len(self.clients)

    def set_watch(self, c: ClientSession, ids) -> None:
        """Replace the client's watch list; newly watched robots are sent immediately."""
        if not isinstance(ids, list):
            return
        new = {i for i in ids[: self._max_watch] if RobotProtocol.is_valid_id(i)}
        newly = new - c.watch
        c.watch = new
        if newly:
            c.pending |= newly & self.state.robots.keys()
            c.wake.set()

    async def writer(self, c: ClientSession) -> None:
        await self._writer.run(c)

    # ---- routing --------------------------------------------------------------
    def flush(self, summary: str | None = None) -> None:
        """Route pending state changes to the clients that watch them."""
        if summary is not None:
            self._last_summary = summary
        dirty, added, removed = self.state.take_changes()
        if not (dirty or added or removed or summary):
            return
        index_changed = bool(added or removed)
        for c in self.clients:
            woke = bool(dirty and c.watch) and c.queue_robots(dirty)
            if index_changed:
                c.queue_index(added, removed)
                woke = True
            if summary is not None:
                c.summary = summary
                woke = True
            if woke:
                c.wake.set()
