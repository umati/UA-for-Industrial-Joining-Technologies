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
`csharp-unit` runs build, format, and all non-live xUnit tests.
`csharp-vuln` runs the C# NuGet vulnerability scan as a separate CI gate.
Live C# coverage is tracked by the `csharp-live` integration job on a
dedicated server instance (port 40464).
The Web Client CI check is split into `web-client-python` and `web-client-js`.
Both delegate to `OPC_UA_Clients/Release2/IJT_Web_Client/run_all_tests.py`
(`--phase1-python` and `--phase1-js`) instead of duplicating pytest, Vitest,
ESLint, mypy, Bandit, and audit commands inside the workflow. The runner writes
the JUnit, coverage, JSON tool reports, and timing artifacts consumed by CI;
the split gives Python and JavaScript independent wall-clock timing and failure
isolation.
The Web JavaScript lint gate also owns the connection-layer randomness guard:
`Math.random()` is forbidden in `connection-manager.mjs` and future
`connection/auth/**`, `connection/token/**`, and `connection/nonce/**` modules.
Connection/session identifiers must use Web Crypto APIs such as
`crypto.randomUUID()` or `crypto.getRandomValues()`. Existing non-security uses
such as WebSocket retry jitter remain outside this guard.
The `pre-commit` CI job runs the repository hook configuration on all files and
is part of the required check set. It skips only npm-backed JavaScript hooks
because the dedicated Web and Node JavaScript jobs already run those checks
after a full `npm ci`.

### CI Jobs

For full job descriptions, test baselines, and toolchain versions, see the **CI/CD** section in [`docs/SKILLS.md`](../docs/SKILLS.md).

### Skip budget: **0 unexpected skips**

Every skip in this tier must have:
- An explicit `reason=` (pytest) / message string (xUnit `Skip.IfNot`) / `skipIf` condition (Vitest)
- A documented condition to unskip (see table below)

The CI report checks both the skip count and, where configured, the expected
skip test identities. A new skipped test or an expected skip that disappears
both produce a non-failing report warning so this table stays current.

### Known expected skips in ci

| Test | Reason | Condition to unskip |
|------|--------|---------------------|
| C# live integration tests | `IJT_PHASE1_ONLY=true` suppresses server auto-launch in the unit-test CI phase (`csharp-unit`) | These same tests **pass** in the `csharp-live` integration job where the server is launched on port 40464; the CI report tracks the expected skip identities |
| Vitest `source-coverage` git check | `git` unavailable in bare zip-export environments | Not Applicable in CI — git is always present; this protects zip-distribution consumers |

---

## Integration (`integration.yml`)

Live, integration, Docker, and optional security checks.
**Failures and skips are tracked but do not block merges.**
The `server-smoke-docker` job may restore Docker layer cache for speed, but
cache writes are limited to trusted `main` runs. The smoke-test Python
dependencies intentionally do not use `actions/setup-python` pip caching in
this artifact-producing job.

### Test-count baseline policy (schema v2)

The committed baseline (`tests/baselines/integration-test-counts.json`) uses
**minimum-floor semantics** with a suspicious-growth threshold:

| Condition | Behaviour |
|-----------|-----------|
| Actual < `min_tests` | ⚠️ Warning — tests may have disappeared |
| Actual > `min_tests` (normal growth) | Silent — no action needed |
| Actual > `min_tests` + max(50, 25%) | ⚠️ Warning — unusually large increase |
| Skipped > baseline + `skip_tolerance` | ⚠️ Warning — skip drift |

Re-anchor with `python tests/tools/update_integration_baseline.py --run <id> --suite <key>`
only when intentionally removing tests. Normal test additions need no baseline update.

### Integration Jobs

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
| Console live joint workflows | fail on missing tool identity | `ProductInstanceUri` is required for live method coverage. Tests browse the server tool list, call `GetJointList(ProductInstanceUri)`, and fail loudly if no usable `JointId` is exposed. |
| Test Client specification tests (optional/supplementary result APIs) | presence or skip/fail-by-design checks | `GetResultIdListFiltered` is optional/profile-dependent and is checked by node presence/Executable; `ReleaseResultHandle`, `AcknowledgeResults`, and `RequestUnacknowledgedResults` may be absent or return Bad-status in the simulator profile |
| Test Client asset sub-type folders (controllers, tools, etc.) | pass | All asset category folders are required in the current server configuration; tests assert presence and fail on missing nodes |
| `zizmor` job | promoted to ci | SARIF upload to Code Scanning (Security → Code scanning alerts). Skipped on fork PRs. The CI job runs with workflow-file changes, but Code Scanning alert merge-blocking still depends on repo branch-protection / Code Scanning check-failure settings. The local root runner parses current zizmor v1 finding exit codes (`13` and `14`) plus any parseable JSON findings output, and fails High/Critical findings instead of treating tool-version exit-code drift as a silent skip. |

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

> **Root runner Phase 2:** The root-level `run_all_tests.py` runs server smoke,
> client live suites, and dedicated Docker smoke suites **simultaneously** via `ThreadPoolExecutor` — not sequentially.
> The server smoke suite validates the native/default server package on port 40451.
> When Docker is running, the Linux package smoke suite also builds the server image
> from `OPC_UA_IJT_Server_Simulator_Linux.zip` and validates it on port 40465.
> Docker-dependent root suites are skipped when Docker is missing or the daemon
> is not running.
> Each client sub-runner auto-launches its own server on its dedicated port.
> Web Client live validation is split by test type: direct Python OPC UA,
> Python WebSocket backend, Python WebSocket lifecycle, Playwright smoke,
> Playwright features, and Playwright regression each run as separate root
> suites with their own service ports. Web Client Docker build/readiness stays
> in the separate `web-client-docker-smoke` suite.
> GitHub integration runs that same local root-runner suite matrix instead of
> a separate raw pytest-only Web integration command. The non-browser Web live
> suites stay on GitHub-hosted Windows runners. Every `web-client-e2e-*`
> Playwright suite runs inside the owned
> `ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci` image,
> resolved from the reviewed `.github/docker/ijt-browser-ci/image-pin.json`
> digest, then started as an immutable image with `docker run --network=none`.
> Chromium, its Linux system dependencies, the locked `@playwright/test` version,
> Python 3.14, and Node 24 are all baked into the image — the host runner never reaches
> `npx playwright install chromium --with-deps`. No job-level `container:`
> image is used:
> container-job images are pulled by GitHub before any step runs, so a
> registry outage would take the whole job down with no in-job retry,
> fallback, or diagnostics. Browser Features keeps two shards; CI
> defaults to two feature workers per shard, and local root validation
> defaults to four workers.
> Web Client — Browser Compatibility Smoke is intentionally separate from Integration:
> `.github/workflows/web-client-compatibility-smoke.yml` runs only at `04:30 UTC`
> or by manual dispatch, reuses the Web Client runner-owned Windows
> simulator/backend stack, and currently contains one matrix cell:
> `windows-latest` / `msedge`. It executes only the two audited browser file
> specs. It is a non-required detection workflow; failures stay red and
> create/update the stable issue key
> `[Web Client Compatibility Smoke] windows-latest / msedge`.
>
> **Local Playwright browser install:** local browser runs need Chromium
> from `https://cdn.playwright.dev` over HTTPS — the same path CI now uses.
> Corporate users should set `HTTPS_PROXY` or `PLAYWRIGHT_DOWNLOAD_HOST`;
> offline users should point `PLAYWRIGHT_BROWSERS_PATH` at a prepopulated
> browser mirror/cache. The failure signature is typically `Failed to
> download Chromium` with `getaddrinfo ENOTFOUND cdn.playwright.dev`.

### Port Assignment

| Client             | Test Port | venv         | Notes                                   |
|--------------------|-----------|--------------|------------------------------------------|
| IJT_CSharp_Client  | **40464** | N/A (.NET)   | Dedicated port — copy-patch mechanism in `OpcUaServerFixture.cs` |
| IJT_Console_Client | 40461     | `.venv_test` | Per-port isolated launch via `run_all_tests.py` |
| IJT_Test_Client    | 40462     | `.venv_test` | Per-port isolated launch via `run_all_tests.py` |
| Web Client Python OPC UA | 40463 | `.venv_test` | Direct OPC UA and method tests; no WebSocket backend |
| Web Client Python backend | OPC UA 40466 / WS 8002 | `.venv_test` | WebSocket backend contract and Python integration tests |
| Web Client Python lifecycle | OPC UA 40467 / WS 8003 | `.venv_test` | WebSocket connection lifecycle tests isolated from backend contract tests |
| Web Client Playwright smoke | HTTP 3004 | `.venv_test` + Playwright | Browser smoke project only |
| Web Client Playwright features | OPC UA 40469–40472 / WS 8005–8008 / HTTP 3005 | `.venv_test` + Playwright | Feature specs with four owned backend/server worker pairs |
| Web Client Playwright regression | OPC UA 40480 / WS 8010 / HTTP 3006 | `.venv_test` + Playwright | Regression spec with owned backend and UI ports |
| Web Client — Browser Compatibility Smoke | OPC UA 40468 / WS 8004 / HTTP 3007 | `.venv_test` + Playwright + real browser channel | Scheduled/manual smoke for audited browser file surfaces; current matrix runs `windows-latest` / `msedge` |
| Web Client Docker smoke | Standalone HTTP 3000 / WS 8001; root runner HTTP 3008 / WS 8011 | Docker | Builds the Web Client production image through `--docker-only`; root runner gives it isolated host ports and a scoped Compose project so it can run alongside live/browser suites; root runner skips when Docker is unavailable |
| IJT_Node_Client    | **40451** (fixed) | N/A (Node) | **Release 1 legacy** — server port is hardcoded, dynamic isolation not supported |
| Server smoke/native default | 40451  | —            | Built-in default (from `server_configuration.json`); root runner Phase 2 validates this package path |
| Server Linux package smoke | 40465  | Docker       | Builds the Docker image from the Linux ZIP package and runs `smoke_test.py` |

The root runner runs Phase 1 to completion before starting Phase 2. The Release 1
Node Client is included only in Phase 1 (`--phase1` delegated runner), so the
default root run does not overlap Node Client activity with `server-smoke` on
port 40451.

Set `IJT_DOCKER_BUILD_TIMEOUT` to raise the Linux package Docker build timeout
or Web Client Docker image build timeout when a cold Docker/network environment
needs more than the default 1200 seconds. Set `IJT_DOCKER_TIMEOUT` to raise the
Web Client Docker HTTP readiness wait when the container starts slowly.

> **Rule:** Release 2 clients MUST NOT use port 40451. That port is reserved as the server's native
> default and must remain free for direct development work and monorepo tests.
> Server self-tests (smoke tests) use 40451 because they test the server in its native configuration.

### How `server_configuration.json` Copy Mechanism Works

The OPC UA server binary always starts on port 40451 (its built-in `server_configuration.json`).
To run on a different port, the copy-patch mechanism:

1. Copies the **entire binary directory** to a temp location
2. Patches `serverConfigurationData.serverEndpointTCPPort` in the **copy's** `server_configuration.json`
3. Launches the binary **with `cwd=<copied dir>/`** so it reads the patched config
4. Captures simulator stdout/stderr to `test-results/opcua-server-<port>.out.log` and `.err.log`
5. Waits up to 30–60 s for `localhost:{port}` to become reachable
6. Sets the session endpoint (`OPCUA_TEST_ENDPOINT` or `OPCUA_SERVER_URL`, depending on runner)
7. Runs an OPC UA protocol probe before tests start, because a listening TCP port is not enough
8. On teardown: terminates the process, then removes the temp dir

**Web Client runner-owned servers** (`OPC_UA_Clients/Release2/IJT_Web_Client/run_all_tests.py`):
temp dir in `{RUNNER_TEMP or system temp}/ijt-sim/{port}/` (override with
`IJT_SIMULATOR_INSTANCE_ROOT`; on Windows the runner falls back to
`<SystemDrive>/ijt-sim/{port}/` if the temp root is still too long). This
intentionally keeps the Windows simulator copy path short; the simulator
creates long PKI certificate filenames and rejects install roots above its own
safe path-length threshold.

**C# client** (`OpcUaServerFixture.cs`): temp dir in `{TEMP}/opcua_csharp_{port}_{guid}/`
- Triggered automatically when `OPCUA_SERVER_PORT != 40451`
- Phase 2 passes `IJT_PHASE1_ONLY=false`; an all-skipped managed live run is a failure, not accepted as a valid live result
- If the resolved port is already open, the fixture probes OPC UA readiness first and reuses the server when it is ready; runner-managed mode kills and relaunches only when that readiness probe fails.
- Native and Docker launch paths both require an OPC UA readiness probe after TCP opens, so tests do not start against a listener whose OPC UA stack is still initialising.
- Cleaned up in `Dispose()` — works for both local dev and CI

- **CI non-Web live jobs** (`scripts/start_server_on_port.py`): temp dir in `{RUNNER_TEMP or system temp}/ijt-sim/server_{port}/`
- Cross-platform Python script that handles copy, patch, start, port-wait, and GITHUB_ENV export
- Used by the Test Client, Console Client, and C# Windows live jobs in `integration.yml`
- The short default copy root avoids depending on the repository checkout depth for simulator PKI/certificate path headroom

**Web Client runner-owned servers** also export
`IJT_OPCUA_PRESTARTED_PORT=<port>` after successful startup. The Web Client
live/integration pytest fixtures treat a matching marker plus a closed port as a
runner-owned server failure and fail with the `opcua-server-<port>` log paths
instead of starting the packaged default-port EXE as a fallback. WebSocket live
fixtures run a backend-only JSON dispatch probe after the backend port opens,
so the first test command is not racing backend startup. OPC UA reachability is
checked separately through the direct simulator protocol probe; the WebSocket
readiness probe must not open OPC UA sessions.

### `.venv_test` Isolation Pattern

Python clients use separate virtual environments for runtime, tests, and local CI-mode:

| venv | Purpose | Created by |
|------|---------|-----------|
| `.venv` | Runtime-only — production dependencies | `setup_client.py` / `setup_project.py` |
| `.venv_test` | Test runner + dev tools (`pytest`, `ruff`, `mypy`, …) | `run_all_tests.py` (first run) |
| `.venv_ci` | Local `--ci-mode` test mirror | `run_all_tests.py --ci-mode` (first local CI-mode run) |

Keeping them separate ensures that installing test tooling never alters the production
environment, and vice versa.
Local `--ci-mode` uses `.venv_ci` so global developer packages cannot affect CI-mode
results. Real GitHub Actions and Docker jobs are already isolated and may use their
provided Python directly.

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

Environment-dependent tests (live server and full Docker integration) cannot be made
deterministic without heavyweight infrastructure that slows every PR.
Separating them into an extended tier:

1. Keeps fast CI **deterministic and contributor-friendly**
2. Makes skips **visible and auditable** — not silently ignored
3. Allows **gradual promotion** of extended tests to required as infrastructure matures
4. Matches industry standard: smoke/unit and fast security gates are blocking; live integration/e2e remains tracked outside the required tier
