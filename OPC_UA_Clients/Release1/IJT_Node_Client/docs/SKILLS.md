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
```

Unit tests live in `tests/js/unit/` and use Vitest with jsdom.
E2E tests live in `tests/e2e/` and use Playwright (requires running server).

### Zero-Escape Testing Tools (run_all_tests.py Phase 1, auto-detected)

`eslint` (lint), `prettier` (format), `npm audit` (CVE scan), `depcheck` (unused deps),
`semgrep` (AI security rules), `detect-secrets` (hardcoded secrets).

## OPC UA Endpoint

Default: `opc.tcp://localhost:40451` (Release 1 server)
