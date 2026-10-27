# Robot Console

Live dashboard for MQTT robots: Mosquitto, a Python (FastAPI)
bridge, and a React + TypeScript web client. Operators see every robot's live
state and send commands; when one operator sends a command, the robot changes
state and **every** open client sees it within tens of milliseconds.

The production design (Part 1) is in [docs/DESIGN.md](docs/DESIGN.md).
Design choices, trade-offs, the history plan and next steps are
[below](#design-choices).

## Quick start

Requirements: Docker Engine with Compose v2.24+ and `make` on Linux. Nothing
else is installed on the host; every dependency is pinned and resolved inside
the images.

| What | Command |
|---|---|
| Build and run everything | `make up` (or `docker compose up --build`) |
| Open the dashboard | http://localhost:8080 |
| Debug the backend | `make debug`, then attach to `127.0.0.1:5678` |
| Run all tests | `make test` |
| Throughput benchmark | `make load` |
| Stop | `make down` (`make clean` also deletes the generated secrets) |

`make up` starts the broker, the backend, nginx with the web client, and 3
replicas of the provided `robot.py` (unmodified). More robots, either way:

```sh
ROBOTS=10 make up                                    # more robot containers
python3 robot/robot.py --broker tcp://localhost:1883  # from the host (needs paho-mqtt<2)
```

Ports are bound to `127.0.0.1` only: 8080 (UI) and 1883 (MQTT, so robots can be
started on the host). The backend port is not published.

**Authentication** is off by default for local use. To turn it on:

```sh
AUTH_TOKEN_FILE=/run/robot-console-secrets/api.token make up
make token        # prints the generated token; paste it into the UI
```

The test suite always runs with authentication on.

**Debugging the backend.** `make debug` starts the same stack, but the backend
runs under debugpy (debug image only, never in the runtime image) and listens on
`127.0.0.1:5678`, with `LOG_LEVEL=DEBUG`. Your local `backend/app` is mounted
into the container, so breakpoints match the files you edit; after a code change
run `docker compose -p robot-console restart backend`. In VS Code, start the debug
configuration "Backend: attach (make debug)" (`.vscode/launch.json`). Any client
that speaks the Debug Adapter Protocol works the same way. `make up` returns to
the normal image. The debug port allows code execution, so it is bound to
localhost and meant for developer machines only.

### Backend configuration

All settings are environment variables, read and validated once at startup
(`backend/app/config/settings.py`); an invalid value stops the service with a
clear message. Secrets also accept a `NAME_FILE` path (Docker secrets); the
file wins and its content is never logged.

| Variable | Default | Meaning |
|---|---|---|
| `MQTT_HOST`, `MQTT_PORT` | `localhost`, `1883` | Broker address |
| `MQTT_USERNAME`, `MQTT_PASSWORD(_FILE)` | unset | Broker credentials (compose sets the `backend` user) |
| `MQTT_TLS`, `MQTT_CA_FILE` | off, unset | TLS to the broker |
| `AUTH_TOKEN(_FILE)` | unset (auth off) | Shared token for REST and WebSocket |
| `ALLOWED_ORIGINS` | empty | Extra browser origins for `/ws` (same origin is always allowed) |
| `CMD_RATE_GLOBAL`, `CMD_RATE_ROBOT` | `200`, `10` | Commands per second: whole service, per robot |
| `OFFLINE_AFTER`, `FORGET_AFTER` | `6`, `600` | Seconds of silence until offline; until forgotten |
| `FLUSH_INTERVAL`, `DRAIN_INTERVAL` | `0.05`, `0.02` | Push batching; inbox drain period (seconds) |
| `MAX_ROBOTS`, `MAX_WATCH`, `INBOX_MAX` | `200000`, `400`, `200000` | Capacity guards |
| `SEND_TIMEOUT` | `5` | A WebSocket client that cannot take a frame this long is dropped |
| `LOG_LEVEL` | `INFO` | `DEBUG` under `make debug` |
| `DISABLE_DOCS` | off | Hide `/api/docs` and `/api/openapi.json` |

## What is in the box

```
broker/      Mosquitto config + ACL, secret generator (init container)
backend/     FastAPI: MQTT ingest, in-memory state, WebSocket hub, REST commands
frontend/    React + TS (Vite), own windowing, external store; nginx config
robot/       robot.py as provided (unmodified) + its image (paho-mqtt 1.6.1)
tests/       integration tests (run in compose against the real stack)
tools/       robot_sim.py (many robots per connection), loadtest.py
docs/        DESIGN.md: production design on AWS and scale strategy```

### Code structure

Both apps are layered, with one class, service or component per file. Dependencies
point inward: routes and components call services, services depend on ports
(interfaces), and only the composition root (`config/container/container.py`) knows concrete classes.

```
backend/app/
  main.py              entry point only: create_app() calls AppFactory
  config/              everything that configures and starts the app, one class per file
    app_factory.py     AppFactory: builds the FastAPI app from the pieces below
    settings.py        Settings: all runtime configuration
    environment/       Environment: typed env reads, *_FILE secrets
    container/         Container: the composition root, the only place that knows concrete classes
    lifecycle/         LifecycleManager: startup and shutdown (MQTT, background loops)
    router/            RouterManager: one registry of prefix, tags and auth per router
    error_handling/    ErrorHandlerManager: business error to HTTP status, in one place
    logging/           LoggingConfig
    mqtt/              MqttManager: the broker connection (implements the broker interfaces)
  protocols/           RobotProtocol: modes, commands, id rules, topics (defined once)
  models/              entities/ (Robot, TelemetrySample), requests/ and responses/ (DTOs)
  exceptions/          AppError and one file per business error
  interfaces/          abstractions (typing.Protocol): TelemetrySource, CommandPublisher, MessageBroker
  repositories/        RobotRegistry plus RobotCounters (O(1) summary) and ChangeTracker
  routers/             thin controllers (health, server_config, robots incl. commands, live);
                       dependencies/ (ContainerDep, require_auth), one per file
  services/            CommandService, RobotQueryService, TelemetryParser, TelemetryIngestor,
                       TaskSupervisor, AuditLog
  features/            capabilities with several parts
    realtime/          Hub, ClientSession, ClientWriter, FlushLoop, SummaryBuilder, FrameEncoder,
                       LiveSessionHandler (WebSocket handshake)
    security/          TokenAuth, OriginPolicy, TokenBucket, CommandLimiter
    observability/     Metrics, PrometheusExporter, ProcessStats
  utils/               JsonUtils, RequestUtils (shared helpers, grouped in classes)
backend/tests/         unit/<folder>/ mirrors app/, api/ for HTTP and WebSocket tests, support/ for fakes

frontend/src/
  main.tsx               entry only
  styles/                CSS split by concern, imported in cascade order from index.css
  app/                   the whole application
    App.tsx              root component: boot, auth gate, picks the page
    pages/               one folder per page; a page composes features (dashboard/DashboardPage)
    layout/              page chrome shared by all pages (AppHeader)
    hooks/, providers/   wiring hooks (store, live connection, session) and the store provider
    core/                app-wide singletons, created once
      config/            constants (timeouts, row heights, storage keys, backoff)
      http/              HttpClient, ApiError, the shared client and its interceptor registration
      http/interceptors/ auth header, error-to-message mapping, 401 sign-out
      auth/              token storage (memory, mirrored to sessionStorage)
      api/               one module per backend endpoint (auth, commands, config)
      realtime/          live connection (reconnect, stale detection), frame parser, backoff
      store/             RobotStore facade over RobotIndex, WatchSet, PendingCommands, Notifier; hooks
    shared/              stateless building blocks
      models/            wire protocol and UI types, one per file
      lib/               pure logic (command confirmation rules)
    features/            auth, connection, summary, robots: components, hooks, utils per feature
```

The frontend dependency direction is enforced by ESLint (`eslint.config.js`,
`import-x/no-restricted-paths`), and lint runs first in `make test`:
`shared <- core <- features <- app shell` (all under `src/app/`). Inside `core/` the direction is
`config <- auth <- http <- api`, with `realtime` and `store` beside `api` (the
store does no I/O). Features never import each other, pages never import each other, and barrel files
(`export *`) are rejected (they hurt Vite tree shaking). The React hooks rules
run too.

All HTTP errors go through the interceptor chain in `core/http/interceptors/`: components never inspect
status codes, they show `ApiError.message`. A 401 anywhere signs the user out
through one registered handler.

## Tests

`make test` runs everything in containers, with one command:

| Suite | What it covers | Count |
|---|---|---|
| Backend unit (pytest) | RobotRegistry: counters vs a brute-force oracle under random traffic, offline sweep, back online, forget, index diffs (including add/forget in one window), invalid input, capacity guard. Hub: viewport filtering, coalescing (latest wins), full index then diffs, slow client dropped without blocking others and with bounded pending, leading-edge flush. API: auth, every non-public route requires the token, WebSocket auth and origin, allowlist, content type, 404/409/422/429/503 (no internal error text), docs switch, ingest topic/payload validation. Config: env parsing, secrets from files, validation, defaults in one place. | 68 |
| Frontend lint + unit (ESLint, vitest) | Lint: folder boundaries, no barrels, no import cycles, React hooks rules. Store: index full/diffs/idempotence/large diffs, filter, watched-only retention and eviction, per-row notifications, rAF batching, reference-stable snapshots, pending lifecycle (no optimistic state, confirm before 202, timeout, failure, stays watched while pending). Connection: auth first, view after hello, reconnect with backoff, stale detection, 4401 stops retries, garbage frames. Backoff jitter, confirmation rules. | 47 |
| Integration (pytest, real stack) | Real `robot.py` containers, Mosquitto, backend, nginx, auth on. Two WebSocket clients watch a robot; a command is sent via REST; **both** clients must observe the robot report the new state; latency is printed. Run directly against the backend **and through nginx**, for `set_mode` and `toggle_charge`. Also: 401 without/with wrong token, WebSocket 4401, cross-origin WebSocket rejected (403) via nginx, security headers, `/metrics` not exposed via nginx, 404/422. | 7 |

Sample integration output (this machine, final run):

```
[backend direct] set_mode=working: both clients saw the robot report it after 21 ms
[backend direct] toggle_charge from discharging: both clients saw it after 57 ms
[through nginx] set_mode=error: both clients saw the robot report it after 96 ms
[through nginx] toggle_charge from charging: both clients saw it after 52 ms
```

Single samples vary with where the command lands in the 50 ms flush window.
Over 12 sequential commands on an idle stack: median 26 ms, maximum 66 ms.

## Design choices

- **The robot is the source of truth.** The UI never applies a command
  optimistically. A button shows "Waiting for robot" until the robot's own
  telemetry confirms the change, and every client sees that same telemetry.
- **Commands over REST, live data over WebSocket.** REST is easy to
  authenticate, validate (allowlist), rate limit and audit per request. The
  WebSocket only pushes data. `202` means "published to the broker", because
  robot.py has no ack channel.
- **Clients subscribe to what they see.** The client sends the ids of its
  visible rows. The server pushes deltas only for those ids (latest wins per
  client) plus a 1 Hz summary, so per-client traffic is bounded by the
  viewport, not the fleet size.
- **Batched ingest, in-memory state.** paho's thread only appends to a bounded
  queue, and asyncio drains it every 20 ms. Counters are incremental, so the
  summary costs O(1). A restart rebuilds state within one telemetry period.
- **Mosquitto** (small, ACLs and password files built in), **Python + FastAPI**
  (same language as robot.py; measured at 50,000 msg/s on about half a core),
  **web app, not mobile** (zero install for evaluators; responsive layout
  works on phones), **React with no UI or table library** (two runtime
  dependencies, 75 KB gzip).

## Trade-offs knowingly skipped

- **No history persistence** (plan below).
- **One shared API token** instead of users and roles (production: OIDC + RBAC).
- **Anonymous robots on the broker**, because robot.py cannot authenticate. The
  ACL stops anonymous clients from sending commands, but production needs
  per-device X.509 identities.
- **No TLS locally**; production terminates TLS at the load balancer.
- **No command correlation**: robot.py does not echo a command id, so the
  client infers confirmation from the new state.
- **Single backend instance**, no HA. Scaling path:
  [DESIGN.md, Appendix A](docs/DESIGN.md#a-scale-strategy-100-to-5000-robots-vs-5000-to-50000-robots).
- **The integration test drives the client's API (REST + WebSocket), not a
  real browser.** The UI was checked manually in two tabs.

## History: how to add it without rebuilding

1. Add a sink at the single ingest point (`Ingestor.process`) that batches
   valid samples into TimescaleDB (a new compose service) through its own
   bounded queue, so the live path never waits on the database.
2. Add `GET /api/robots/{id}/history?from=&to=&step=` with server-side
   downsampling.
3. Add a detail drawer in the client with a battery chart and a mode timeline.

The protocol, the live store and the command path stay unchanged. Production
version: [DESIGN.md, Appendix B](docs/DESIGN.md#b-adding-history-without-rebuilding).

## Given another day

1. History (above), behind a feature flag.
2. Playwright end-to-end test of the real UI: two browsers, click, assert.
3. OIDC sign-in and roles; WebSocket ticket instead of a raw token.
4. Ask the robot team for a protocol change: echo the command id in
   telemetry, add an LWT and a heartbeat. Then remove the inference heuristics.
5. Server-side paging and filtering of the robot index.
6. Load test on a Linux host with production-sized CPU limits, plus a broker
   test with real per-robot connections.
