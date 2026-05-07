# IJT Node Client — Skills Reference

## Architecture

- **Express** HTTP server (`index.js`) serves `index.html` and static assets
- **Socket.io** bridges browser ↔ Node.js server ↔ OPC UA server
- **node-opcua** handles all OPC UA protocol work server-side
- **`javascripts/ijt-support/`** contains all shared logic (no DOM imports)
- **`javascripts/views/`** contains DOM rendering components

## Module System

All source files use ES modules (`.mjs`, `"type": "module"` in package.json).

The `ijt-support` path alias (configured in `vitest.config.mjs`) maps:
```
ijt-support/... → javascripts/ijt-support/...
```

## Core Classes

| Class | File | Purpose |
|---|---|---|
| `SocketHandler` | `socket-handler/socket-handler.mjs` | Low-level socket emit/on wrappers with promise-based call tracking |
| `ConnectionManager` | `connection/connection-manager.mjs` | Manages OPC UA session lifecycle events |
| `AddressSpace` | `address-space/address-space.mjs` | Caches and navigates the OPC UA node tree |
| `EventManager` | `events/event-manager.mjs` | Subscribes to and dispatches OPC UA events |
| `ResultManager` | `results/result-manager.mjs` | Collects tightening results from events |
| `MethodManager` | `methods/method-manager.mjs` | Discovers and invokes OPC UA methods |
| `AssetManager` | `assets/asset-manager.mjs` | Loads asset hierarchy from the address space |
| `ModelManager` | `models/model-manager.mjs` | Factory for deserializing OPC UA data types |

## Data Models

All models extend `IJTBaseModel` which auto-maps constructor parameters to instance properties.

| Model | Maps to OPC UA IJT type |
|---|---|
| `TighteningResultDataType` | Tightening result with step results |
| `StepResultDataType` | Individual step result |
| `TighteningTraceDataType` | Trace with step traces |
| `StepTraceDataType` | Individual step trace |
| `ResultValueDataType` | Measured value (torque, angle, etc.) |
| `ErrorInformationDataType` | Error detail |
| `ProcessingTimesDataType` | Start/end timestamps |
| `TagDataType` | Location/identifier tag |

## Socket Message Protocol

### Client → Server

| Event | Args | Description |
|---|---|---|
| `connect to` | endpointUrl | Initiate OPC UA connection |
| `terminate connection` | endpointUrl | Close connection |
| `browse` | endpointUrl, callId, nodeId, details | Browse a node |
| `read` | endpointUrl, callId, nodeId, attribute | Read a node attribute |
| `pathtoid` | endpointUrl, callId, nodeId, path | Resolve a relative path to a nodeId |
| `methodcall` | endpointUrl, callId, objectNode, methodNode, inputArguments | Invoke an OPC UA method |
| `subscribe event` | endpointUrl, fields, subscriberDetails | Subscribe to events |

### Server → Client

| Event | Description |
|---|---|
| `connection established` | OPC UA connection succeeded |
| `session established` | OPC UA session created |
| `subscription created` | Event subscription active |
| `session closed` | Session closed |
| `browseresult` | Response to `browse` |
| `readresult` | Response to `read` |
| `pathtoidresult` | Response to `pathtoid` |
| `callresult` | Response to `methodcall` |
| `subscribed event` | Incoming OPC UA event |
| `namespaces` | Namespace array from server |
| `datatypes` | DataType enumeration from server |

## Testing

```bash
# Full suite (lint + unit tests + coverage)
python run_all_tests.py

# Unit tests only
npx vitest run

# With coverage
npx vitest run --coverage

# Verbose output
npx vitest --reporter=verbose

# E2E tests (Playwright — requires running server + installed browsers)
node index.js &                          # start Node Client HTTP server on :3000
npx playwright install chromium          # first-time browser install
npx playwright test                      # all E2E specs (views project)
npx playwright test --project=views      # UI view tests
npx playwright test tests/e2e/servers.spec.mjs  # single spec
npx playwright show-report               # open HTML report after a run
```

Unit tests live in `tests/js/unit/` and use Vitest with jsdom.
E2E tests live in `tests/e2e/` and use Playwright (requires running server).
Vitest enforces a 95% line-coverage threshold for the unit suite; the runner also
reports an advisory 95% ratchet floor and a 100% aspirational goal.

### E2E Test Architecture

All E2E specs use `e2e-fixtures.mjs` which **skips all tests gracefully** when
`http://localhost:3000` is not reachable. This means:
- E2E tests **never fail** in CI (server not started in CI)
- E2E tests **run locally** when `node index.js` is running

Spec overview:

| Spec | Tests | OPC UA required? |
|------|-------|-----------------|
| `servers.spec.mjs` | 7 | No — Servers tab always visible |
| `connection.spec.mjs` | 4 | No — connection form always visible |
| `events.spec.mjs` | 3 | Optional — tab skips if not connected |
| `methods.spec.mjs` | 3 | Optional — tab skips if not connected |
| `address-space.spec.mjs` | 3 | Optional — tab skips if not connected |
| `trace.spec.mjs` | 3 | Optional — tab skips if not connected |
| `assets.spec.mjs` | 4 | Optional — tab skips if not connected |

Run `python run_all_tests.py --phase2` to execute Playwright E2E as part of
the full Phase 2 suite (server auto-launched if binary is present).

### Zero-Escape Testing Tools (run_all_tests.py Phase 1, auto-detected)

Runner-managed `npm ci` uses `--no-audit --no-fund` to keep repeated local/CI
logs readable; JS CVEs are still checked by the separate explicit `npm audit`
step.
Runner-owned npm subprocesses use the project-local `tmp/npm-cache` and set
`npm_config_update_notifier=false` so standalone and root-delegated runs do not
print npm update notices.

`eslint` (lint), `prettier` (format), `npm audit` (CVE scan), `depcheck` (unused deps),
`semgrep` (AI security rules), `detect-secrets` (hardcoded secrets).

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPCUA_SERVER_URL` | `opc.tcp://localhost:40451` | OPC UA server endpoint override (Release 1 server cannot change its own port) |

## OPC UA Endpoint

Default: `opc.tcp://localhost:40451` (Release 1 server — fixed, not configurable)

### Server Port — Legacy Fixed Port (Release 1)

The Release 1 Node client and its companion Release 1 OPC UA server simulator use a
**fixed port (40451)**. The Release 1 server does **not** read `server_configuration.json`
for the TCP port; the port is hardcoded into the binary.

> **Port isolation does not apply here.** Dynamic per-client port assignment via
> `server_configuration.json` copy-and-patch is a Release 2 feature only.

To run the live tests, start the Release 1 server manually (or let `run_all_tests.py`
auto-launch it) on port **40451**, then run the tests. Setting `OPCUA_SERVER_URL` to a
different server is supported as an override, but the Release 1 server itself cannot be
started on an arbitrary port.
