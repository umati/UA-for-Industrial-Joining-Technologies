# Test Tiers Policy

## Overview

All tests in this repository are classified into three tiers:

| Tier | Workflow | Blocking | Runs on |
|------|----------|----------|---------|
| **ci** | `ci.yml` | ✅ Blocks every PR and push | Every commit |
| **integration** | `integration.yml` | ℹ️ Non-blocking — tracked, not blocking | Nightly · Manual · Path-triggered |
| **e2e** | Local only | ℹ️ Non-blocking — dev machine only | Local when server running |

---

## CI (`ci.yml`)

Fast and deterministic on GitHub-hosted runners. **Must pass before any merge.**
`csharp-unit` runs build, format, vuln scan, and all non-live xUnit tests.
`csharp-live` runs the 110 live xUnit tests on a dedicated server instance (port 40464) — part of the `ci.yml` live job.

### Jobs

For full job descriptions, test baselines, and toolchain versions, see the **CI/CD** section in [`docs/SKILLS.md`](../docs/SKILLS.md).

### Skip budget: **0 unexpected skips**

Every skip in this tier must have:
- An explicit `reason=` (pytest) / message string (xUnit `Skip.IfNot`) / `skipIf` condition (Vitest)
- A documented condition to unskip (see table below)

### Known expected skips in ci

| Test | Reason | Condition to unskip |
|------|--------|---------------------|
| C# `LiveIntegrationTests` × 15 | `IJT_PHASE1_ONLY=true` suppresses server auto-launch in the unit-test CI phase (`csharp-unit`) | These same tests **pass** in the `csharp-live` CI job where the server is launched on port 40464 |
| Vitest `source-coverage` git check | `git` unavailable in bare zip-export environments | Not applicable in CI — git is always present; this protects zip-distribution consumers |

---

## Integration (`integration.yml`)

Live, integration, Docker, and optional security checks.
**Failures and skips are tracked but do not block merges.**

### Jobs

For full job descriptions, test baselines, and toolchain versions, see the **CI/CD** section in [`docs/SKILLS.md`](../docs/SKILLS.md).

### Triggers

- **Nightly** at 2am UTC
- **Manual dispatch** (`workflow_dispatch`)
- **Push / PR** touching server/client code paths **or any `.github/workflows/` file** (see path filters in `integration.yml`)

### Zero-skip policy for live/integration tests

Live and integration tests use **auto-start session fixtures** (conftest.py) — not
module-level `skipif` port checks. If a required server cannot be started, the session
fails with `pytest.fail()` (loud, never silent). This applies to:

- `IJT_Web_Client/tests/python/live/` — both OPC UA server and WebSocket backend
- `IJT_Web_Client/tests/python/integration/` — both servers
- `IJT_Console_Client/tests/live/` — OPC UA server

### Known expected non-skip conditions in integration

| Test | Status | Reason |
|------|--------|--------|
| Console `TestMethods` × 7 | `xfail` | `ProductInstanceUri` is NULL on demo server — tool identity not configured. Uses `pytest.xfail()` so the test runs and is reported as expected-failure, not silently skipped. |
| Test Client conformance (unsupported-result APIs) | skip/fail-by-design checks | Server profile intentionally does not implement `GetResultIdListFiltered`, `ReleaseResultHandle`, `AcknowledgeResults`, `RequestUnacknowledgedResults`; tests assert absence or Bad-status rejection |
| Test Client asset sub-type folders (controllers, tools, etc.) | pass | All asset category folders are required in the current server configuration; tests assert presence and fail on missing nodes |
| `zizmor` job | promoted to ci | SARIF upload to Code Scanning (Security → Code scanning alerts). Skipped on fork PRs. Now **blocking** in ci. |

---

## Skip Marker Standards

Every skip must be explicit and auditable. Prefer `pytest.fail()` over `pytest.skip()`
for infrastructure checks — missing servers, wrong paths, missing packages. Reserve
`pytest.skip()` only for genuine "this feature is not available on this server/platform"
conditions. Use `pytest.xfail()` only for short-lived regressions; remove markers as soon as behavior is implemented.

### Python (pytest)

```python
# Infrastructure missing → fail loudly, never skip silently:
pytest.fail("OPC UA server did not start within 60 s — check EXE output")

# Method is optional per spec and absent on this server → skip with reason:
pytest.skip("SetCalibration method not present — optional per spec")

# Method is present but unsupported by server profile → run the test, assert rejection:
# (do NOT skip — the test runs and asserts a Bad status response)
assert response_status.name.startswith("Bad"), (
    "AcknowledgeResults should return Bad status on this server profile"
)

# Test depends on optional feature known to be absent → skip with reason:
pytest.skip("GetIdentifiers requires additional arguments on this server (see GAP-004)")
```

### C# (xUnit + `SkippableFact`)

```csharp
// Clear message explains what is missing and why:
Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
Skip.IfNot(!simMethodId.IsNullNodeId,
    "SimulateSingleResult method not found — server may not expose simulation nodes");
```

### JavaScript (Vitest)

```js
// Condition guard with clear reason:
it.skipIf(!gitAvailable, 'git not available — skip source-coverage checks (zip export or no git)')
```

---

## Per-Client Server Isolation

Each Python client runner reserves a dedicated server port so that multiple clients can
run their live/integration tests in parallel without port conflicts.

> **Root runner Phase 2:** The root-level `run_all_tests.py` runs all 4 client suites
> **simultaneously** via `ThreadPoolExecutor` — not sequentially. Each sub-runner
> auto-launches its own server on its dedicated port.

### Port Assignment

| Client             | Test Port | venv         | Notes                                   |
|--------------------|-----------|--------------|------------------------------------------|
| IJT_CSharp_Client  | **40464** | N/A (.NET)   | Dedicated port — copy-patch mechanism in `OpcUaServerFixture.cs` |
| IJT_Console_Client | 40461     | `.venv_test` | Per-port isolated launch via `run_all_tests.py` |
| IJT_Test_Client    | 40462     | `.venv_test` | Per-port isolated launch via `run_all_tests.py` |
| IJT_Web_Client     | 40463     | `.venv_test` | Per-port isolated launch via `run_all_tests.py` |
| IJT_Node_Client    | **40451** (fixed) | N/A (Node) | **Release 1 legacy** — server port is hardcoded, dynamic isolation not supported |
| Server native/default | 40451  | —            | Built-in default (from `server_configuration.json`) — freed for direct dev + monorepo tests |

> **Rule:** Release 2 clients MUST NOT use port 40451. That port is reserved as the server's native
> default and must remain free for direct development work and monorepo tests.
> Server self-tests (smoke tests) may use 40451 because they test the server in its native configuration.

### How `server_configuration.json` Copy Mechanism Works

The OPC UA server binary always starts on port 40451 (its built-in `server_configuration.json`).
To run on a different port, the copy-patch mechanism:

1. Copies the **entire binary directory** to a temp location
2. Patches `serverConfigurationData.serverEndpointTCPPort` in the **copy's** `server_configuration.json`
3. Launches the binary **with `cwd=<copied dir>/`** so it reads the patched config
4. Waits up to 30–60 s for `localhost:{port}` to become reachable
5. Sets `OPCUA_SERVER_URL=opc.tcp://localhost:{port}` for the test session
6. On teardown: terminates the process, then removes the temp dir

**Python clients** (`run_all_tests.py`): temp dir in `{client}/tmp/server_instance_{port}/`

**C# client** (`OpcUaServerFixture.cs`): temp dir in `{TEMP}/opcua_csharp_{port}_{guid}/`
- Triggered automatically when `OPCUA_SERVER_PORT != 40451`
- Cleaned up in `Dispose()` — works for both local dev and CI

- **CI** (`scripts/start_server_on_port.py`): temp dir in `tmp/server_{port}/`
- Cross-platform Python script that handles copy, patch, start, port-wait, and GITHUB_ENV export
- Used in all Windows live test jobs in `ci.yml` and `integration.yml`

### `.venv_test` Isolation Pattern

Python clients use **two separate virtual environments**:

| venv | Purpose | Created by |
|------|---------|-----------|
| `.venv` | Runtime-only — production dependencies | `setup_client.py` / `setup_project.py` |
| `.venv_test` | Test runner + dev tools (`pytest`, `ruff`, `mypy`, …) | `run_all_tests.py` (first run) |

Keeping them separate ensures that installing test tooling never alters the production
environment, and vice versa.

### `OPCUA_SERVER_URL` Override

Set `OPCUA_SERVER_URL` to point a client at a specific server; auto-launch is skipped when
this variable is present. CI workflows set this per-job. The root-level `run_all_tests.py`
does NOT set this for Python sub-runners — each auto-launches on its dedicated port. Only
the C# runner receives `OPCUA_SERVER_PORT=40464` from the root runner.

---

## E2E (`tests/e2e/` — Local Dev Only)

Playwright browser-automation tests for the Node Client UI. **Not run in CI** — they
require a running HTTP server (`node index.js`) and installed browser binaries.

### Node Client E2E

| Spec | Tests | OPC UA required? | Notes |
|------|-------|-----------------|-------|
| `servers.spec.mjs` | 7 | No | Servers tab always visible; tests Add/Save/Delete buttons, row management |
| `connection.spec.mjs` | 4 | No | Connection form always visible |
| `events.spec.mjs` | 3 | Optional | Tab skips gracefully if not connected |
| `methods.spec.mjs` | 3 | Optional | Tab skips gracefully if not connected |
| `address-space.spec.mjs` | 3 | Optional | Tab skips gracefully if not connected |
| `trace.spec.mjs` | 3 | Optional | Tab skips gracefully if not connected |
| `assets.spec.mjs` | 4 | Optional | Tab skips gracefully if not connected |

### How skip guard works

All specs use `e2e-fixtures.mjs` which checks `http://localhost:3000` before any test:
```js
if (!await isServerRunning()) {
  test.skip(true, 'IJT Node Client not running — start with: node index.js')
}
```
This means **zero tests fail in CI** — they all skip cleanly when no server is running.
The fixtures module imports from `playwright/test` (the `playwright` npm package exposes
this, equivalent to `@playwright/test`).

### Running E2E locally

```sh
# Start server
node OPC_UA_Clients/Release1/IJT_Node_Client/index.js

# Install browsers once
cd OPC_UA_Clients/Release1/IJT_Node_Client
npx playwright install chromium

# Run all E2E tests
npx playwright test --project=views

# Or via run_all_tests.py Phase 2
python run_all_tests.py --phase2
```

### Playwright configuration

`playwright.config.mjs` defines three projects:
- `smoke` — matches `smoke.spec.mjs` (future smoke specs)
- `regression` — matches `regression-no-server.spec.mjs` (future no-server regression)
- `views` — matches all current view specs (servers, connection, events, methods, assets, address-space, trace)

---

## Promotion Checklist (extended → required)

Promote a test from extended to required when all of the following are true:

- [ ] Runs in < 5 minutes end-to-end
- [ ] Requires no live server or external service unavailable in CI
- [ ] Has passed without flaky failures for 10+ consecutive extended runs
- [ ] Skip rate is 0% (no conditional skips needed)

---

## Rationale

Environment-dependent tests (live server, Docker, security tools) cannot be made
deterministic without heavyweight infrastructure that slows every PR.
Separating them into an extended tier:

1. Keeps fast CI **deterministic and contributor-friendly**
2. Makes skips **visible and auditable** — not silently ignored
3. Allows **gradual promotion** of extended tests to required as infrastructure matures
4. Matches industry standard: smoke/unit = blocking; integration/e2e/security = non-blocking but tracked
