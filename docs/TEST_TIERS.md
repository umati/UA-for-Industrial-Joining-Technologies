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
| `server-smoke-windows` | OPC UA binary smoke — 10 checks, Windows native |
| `docker-smoke` | Web Client Docker build · HTTP readiness · WebSocket port |
| `actionlint` | GHA workflow lint (local runner also checks `*.yml` action-pin versions) |

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
| `server-smoke-docker` | Linux Release2 server: Docker image build · Dockerfile lint (hadolint) · smoke tests |
| `webclient-docker` | Web Client Docker: test-target (Python + Vitest inside container) · prod-target (HTTP health on port 3000) |
| `int-testclient` | Windows: OPC UA server + Test Client full suite (runs in parallel with `int-live-others`) |
| `int-live-others` | Windows: Web Client integration + Console live tests (runs in parallel with `int-testclient`) |
| `zizmor` *(optional)* | GitHub Actions workflow security audit — findings uploaded as SARIF to GitHub Code Scanning (Security tab); job never fails CI; skipped on fork PRs (no `security-events: write` in fork context) |

### Triggers

- **Nightly** at 2am UTC
- **Manual dispatch** (`workflow_dispatch`)
- **Push / PR** touching server/client code paths **or any `.github/workflows/` file** (see path filters in `ci-extended.yml`)

### Skip budget: allowed, but auditable

Extended skips are acceptable when server/tool/environment is not available.
Each skip still needs: reason, and a documented condition to unskip.

### Known expected skips in ci-extended

| Test | Reason | Condition to unskip |
|------|--------|---------------------|
| Console `TestMethods` × 7 | `ProductInstanceUri not configured on server — method requires tool identity` | Configure the demo server with a real tool identity |
| Test Client conformance × 6 | Demo server does not implement optional interfaces (`IControllerType`, `IToolType`, `AssociatedWith` references) | Reference server is minimal by design — not a defect |
| Test Client × 20 `xfail` | Known unimplemented optional features in demo server | Correctly decorated `@pytest.mark.xfail` — expected and not a defect |
| Web Client `TestBackendWebSocket` × 14 | WebSocket backend not running in this test phase | Start the backend process before running this test class |
| `zizmor` job | SARIF upload to Code Scanning — see Security → Code scanning alerts | No action needed; job always passes (skipped on fork PRs). Review alerts in Security tab. |

---

## Skip Marker Standards

Every skip must be explicit and auditable.

### Python (pytest)

```python
# Structured skip — reason and condition are clear:
@pytest.mark.skipif(not OPCUA_UP, reason="OPC UA server not reachable at port 40451")
pytest.skip("ProductInstanceUri not configured on server — method requires tool identity")
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
