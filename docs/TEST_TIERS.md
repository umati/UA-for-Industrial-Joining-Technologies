# Test Tiers Policy

## Overview

All tests in this repository are classified into two tiers:

| Tier | Workflow | Blocking | Runs on |
|------|----------|----------|---------|
| **ci-required** | `ci-required.yml` | ✅ Blocks every PR and push | Every commit |
| **ci-extended** | `ci-extended.yml` | ℹ️ Non-blocking — tracked, not blocking | Nightly · Manual · Path-triggered |

---

## ci-required (`ci-required.yml`)

Fast and deterministic on GitHub-hosted runners. **Must pass before any merge.**
Most jobs are fully environment-independent; `csharp-client` is the exception — it auto-launches the Windows OPC UA server binary on the runner.

### Jobs

| Job | What it checks |
|-----|----------------|
| `web-client` | Python unit tests · Vitest · ESLint · Bandit · Ruff · mypy · npm audit |
| `console-client` | Python unit tests · Bandit · Ruff · mypy |
| `node-client` | Vitest · ESLint · npm audit |
| `csharp-client` | dotnet build (zero warnings) · phase1: unit/static only (`IJT_PHASE1_ONLY=true`, live tests skip) · phase2: xUnit live tests against auto-launched Windows server (`--blame-hang 60s` catches hangs) · format check |
| `test-client` | pytest collect-only · Bandit · Ruff · mypy |
| `server-smoke-windows` | OPC UA binary smoke — 10 checks, Windows native, JUnit XML |
| `docker-smoke` | Web Client Docker build · HTTP readiness · WebSocket port |
| `actionlint` | GHA workflow lint (local runner also checks `*.yml` action-pin versions) |
| `report` | Downloads all artifacts · publishes dorny/test-reporter Checks tab (per-test drill-down) · writes summary table to job summary with full pass · fail · skip counts · artifact sanity gate · `continue-on-error` on all dorny steps (fork PR safe) |

### Skip budget: **0 unexpected skips**

Every skip in this tier must have:
- An explicit `reason=` (pytest) / message string (xUnit `Skip.IfNot`) / `skipIf` condition (Vitest)
- A documented condition to unskip (see table below)

### Known expected skips in ci-required

| Test | Reason | Condition to unskip |
|------|--------|---------------------|
| C# `LiveIntegrationTests` × 15 | `IJT_PHASE1_ONLY=true` suppresses server auto-launch in the unit-test CI phase | These same tests **pass** in the `csharp-client` CI job where the server is launched |
| Vitest `source-coverage` git check | `git` unavailable in bare zip-export environments | Not applicable in CI — git is always present; this protects zip-distribution consumers |

---

## ci-extended (`ci-extended.yml`)

Live, integration, Docker, and optional security checks.
**Failures and skips are tracked but do not block merges.**

### Jobs

| Job | What it checks |
|-----|----------------|
| `server-smoke-docker` | Linux Release2 server: Docker image build · Dockerfile lint (hadolint) · smoke tests (10 checks, JUnit XML) |
| `webclient-docker` | Web Client Docker: test-target (Python + Vitest inside container) · prod-target (HTTP health on port 3000) |
| `int-testclient` | Windows: OPC UA server + Test Client full suite (runs in parallel with `int-live-others`) — pytest-live.xml (+ pytest-unit.xml when phase1 runs) + smoke-sanity.xml collected flat before artifact upload |
| `int-live-others` | Windows: Web Client integration + Console live tests (runs in parallel with `int-testclient`) |
| `zizmor` *(optional)* | GitHub Actions workflow security audit — findings uploaded as SARIF to GitHub Code Scanning (Security tab); job never fails CI; skipped on fork PRs (no `security-events: write` in fork context) |
| `report` | Downloads all artifacts · publishes dorny/test-reporter Checks tab (per-test drill-down) · writes summary table to job summary with full pass · fail · skip counts · artifact sanity gate warns on missing XMLs · zizmor-aware overall status |

### Triggers

- **Nightly** at 2am UTC
- **Manual dispatch** (`workflow_dispatch`)
- **Push / PR** touching server/client code paths **or any `.github/workflows/` file** (see path filters in `ci-extended.yml`)

### Zero-skip policy for live/integration tests

Live and integration tests use **auto-start session fixtures** (conftest.py) — not
module-level `skipif` port checks. If a required server cannot be started, the session
fails with `pytest.fail()` (loud, never silent). This applies to:

- `IJT_Web_Client/tests/python/live/` — both OPC UA server and WebSocket backend
- `IJT_Web_Client/tests/python/integration/` — both servers
- `IJT_Console_Client/tests/live/` — OPC UA server

### Known expected non-skip conditions in ci-extended

| Test | Status | Reason |
|------|--------|--------|
| Console `TestMethods` × 7 | `xfail` | `ProductInstanceUri` is NULL on demo server — tool identity not configured. Uses `pytest.xfail()` so the test runs and is reported as expected-failure, not silently skipped. |
| Test Client conformance × 6 | skip | Demo server does not implement optional interfaces (`IControllerType`, `IToolType`, `AssociatedWith` references) — reference server is minimal by design |
| Test Client × 20 | `xfail` | Known unimplemented optional features in demo server — correctly decorated `@pytest.mark.xfail` |
| Test Client asset sub-type folders (controllers, tools, etc.) | skip | Individual asset category folders are optional per IJT spec — a conformant server may implement a subset |
| `zizmor` job | pass | SARIF upload to Code Scanning — see Security → Code scanning alerts. No action needed; job always passes (skipped on fork PRs). |

---

## Skip Marker Standards

Every skip must be explicit and auditable. Prefer `pytest.fail()` over `pytest.skip()`
for infrastructure checks — missing servers, wrong paths, missing packages. Reserve
`pytest.skip()` only for genuine "this feature is not available on this server/platform"
conditions. Use `pytest.xfail()` for known server limitations that are expected to change.

### Python (pytest)

```python
# Infrastructure missing → fail loudly, never skip silently:
pytest.fail("OPC UA server did not start within 60 s — check EXE output")

# Server capability genuinely unavailable → xfail (runs but expected to fail):
pytest.xfail("ProductInstanceUri is NULL on this server — tool identity not configured")

# Test depends on optional feature known to be absent → skip with reason:
pytest.skip("Server does not implement IControllerType (optional interface)")
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

### Port Assignment

| Client             | Test Port | venv         | Notes                                   |
|--------------------|-----------|--------------|------------------------------------------|
| IJT_CSharp_Client  | 40451     | N/A (.NET)   | Uses server's native port — no copy needed |
| IJT_Console_Client | 40461     | `.venv_test` | Per-port isolated launch                |
| IJT_Test_Client    | 40462     | `.venv_test` | Per-port isolated launch                |
| IJT_Web_Client     | 40463     | `.venv_test` | Per-port isolated launch                |
| IJT_Node_Client    | **40451** (fixed) | N/A (Node) | **Release 1 legacy** — server port is hardcoded, dynamic isolation not supported |
| Server native port | 40451     | —            | Built-in default (from `server_configuration.json`) |

### How `server_configuration.json` Copy Mechanism Works

The OPC UA server binary always starts on port 40451 (its built-in `server_configuration.json`).
To run a second instance on a different port, `run_all_tests.py` in each client:

1. Copies the **entire binary directory** (`shutil.copytree`) to `tmp/server_instance_{port}/`
2. Patches `serverConfigurationData.serverEndpointTCPPort` in the **copy's** `server_configuration.json`
3. Launches the binary **with `cwd=tmp/server_instance_{port}/`** so it reads the patched config
4. Waits up to 30 s for `localhost:{port}` to become reachable
5. Sets `OPCUA_SERVER_URL=opc.tcp://localhost:{port}` for the test session
6. On teardown: terminates the process, then removes the temp dir (`shutil.rmtree`)

The temp dir lives inside the client's own `tmp/` folder (e.g.
`IJT_Console_Client/tmp/server_instance_40461/`) for easy manual cleanup.

### `.venv_test` Isolation Pattern

Python clients use **two separate virtual environments**:

| venv | Purpose | Created by |
|------|---------|-----------|
| `.venv` | Runtime-only — production dependencies | `setup_client.py` / `setup_project.py` |
| `.venv_test` | Test runner + dev tools (`pytest`, `ruff`, `mypy`, …) | `run_all_tests.py` (first run) |

Keeping them separate ensures that installing test tooling never alters the production
environment, and vice versa.

### `OPCUA_SERVER_URL` Override

Set `OPCUA_SERVER_URL=opc.tcp://myserver:40451` (or the Web Client's `OPCUA_TEST_ENDPOINT`)
to point all clients at a shared server. Auto-launch is skipped entirely when this variable
is present — this is the path used by the root-level `run_all_tests.py` and CI workflows.

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
