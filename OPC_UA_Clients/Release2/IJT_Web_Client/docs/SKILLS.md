# IJT Web Client — Developer Reference

---

## Project Identity

| Item | Value |
|------|-------|
| **Location** | `OPC_UA_Clients/Release2/IJT_Web_Client/` |
| **Purpose** | Reference OPC UA IJT client: Python WebSocket backend + Node.js browser frontend |
| **Stack** | Python 3.14+, asyncua ≥1.2b2, Node.js 24+, Vite/Vitest, ESLint |
| **OPC UA Spec** | OPC UA for Industrial Joining Technologies (IJT) |
| **Docker** | Container healthy on HTTP:3000 + WS:8001 (non-root `appuser`) |

---

## Project Root File Map

```
IJT_Web_Client/
├── index.html              # Browser entry point — loads src/javascripts/ijt-support/ijt-support.mjs
├── index.py                # Python WebSocket backend (asyncio + websockets, default port 8001)
├── config.js               # Browser runtime WS config (window.__IJT_RUNTIME__ / query params)
├── run_all_tests.py        # PRIMARY TEST RUNNER — one command for everything
├── pyproject.toml          # pytest settings: asyncio_mode=auto, timeout=30 (+ ruff, coverage, bandit, mypy)
├── vitest.config.mjs       # Vitest config for JS unit tests
├── eslint.config.mjs       # ESLint flat config
├── requirements.txt        # Python runtime deps
├── requirements-dev.txt    # Pinned: pytest~=9.0, pytest-asyncio~=1.3, pyfakefs~=6.1, and tooling
├── package.json            # Node deps + scripts (lint, test:unit:js, start)
├── Dockerfile              # FROM nikolaik/python-nodejs:python3.14-nodejs24; CMD setup_project.py
├── docker-compose.yaml     # Service: ijt_web_client; ports 3000+8001; command: setup_project.py
├── Makefile                # make setup|test|lint|docker|clean
├── .env / .env.example     # OPCUA_TEST_ENDPOINT, WS_PORT, etc.
│
├── scripts/                # All helper scripts
│   ├── test_live_ops.py    # Standalone live OPC UA smoke test (asyncio.run)
│   ├── run_docker_tests.py # Docker smoke + build + compose tests
│   ├── run_cross_client_regression.py  # cross-client regression runner
│   ├── run_regression.py   # WS regression test runner
│   ├── bootstrap_wsl.sh    # WSL Ubuntu dependency installer
│   ├── venv_bootstrap.py   # Venv utilities
│   └── _browse_methods.py  # OPC UA address space debug helper
│
├── src/python/             # Python backend modules
│   ├── connection.py       # OPC UA connection with asyncio.wait_for timeouts
│   ├── event_handler.py    # Event subscription (subscribes on Server node, no custom filters)
│   ├── result_event_handler.py  # Tightening result WebSocket relay
│   ├── ijt_interface.py    # OPC UA method calls
│   ├── call_structure.py   # Method call builder
│   ├── serialize_data.py   # OPC UA → JSON serialisation
│   ├── network_utils.py    # endpoint_reachable(), parse_endpoint_host_port()
│   └── utils.py            # Shared helpers
│
├── src/javascripts/
│   ├── ijt-support/        # Core client library (see docs/guides/ijt-support-guide.md)
│   │   ├── ijt-support.mjs         # Barrel export
│   │   ├── connection/             # WebSocketManager, ConnectionManager, SocketHandler
│   │   ├── models/                 # ModelManager, IJTBaseModel, domain models
│   │   ├── results/                # ResultManager
│   │   ├── events/                 # EventManager (Queue maxSize=500)
│   │   ├── methods/                # MethodManager
│   │   ├── assets/                 # AssetManager
│   │   ├── entity-cache/           # EntityManager
│   │   ├── joints/                 # JointManager
│   │   └── settings/               # App config helpers
│   └── views/              # UI screens (see docs/guides/views-guide.md)
│       ├── servers/
│       ├── tab-setup/
│       ├── methods/
│       ├── trace/ events/ standard-demo/ complex-result/
│       ├── assets/ entities/ joints/
│       └── graphic-support/  # TabGenerator, BasicScreen base
│
├── tests/
│   ├── conftest.py                 # Shared fixtures (OPC UA client, event loop, sys.path)
│   ├── python/
│   │   ├── unit/                   # Pure unit tests — no server needed
│   │   │   ├── test_call_structure.py
│   │   │   ├── test_ijt_interface.py
│   │   │   ├── test_serialize_data.py
│   │   │   ├── test_web_event_handler.py
│   │   │   ├── test_web_result_event_handler.py
│   │   │   ├── test_shared_python_module_contracts.py
│   │   │   └── test_serialization_and_filters.py
│   │   ├── integration/            # Needs WS backend (marker: integration)
│   │   │   ├── test_opcua_integration.py
│   │   │   ├── test_shared_client_contract.py
│   │   │   └── test_index_handler.py
│   │   └── live/                   # Needs OPC UA server; runner injects OPCUA_TEST_ENDPOINT (marker: live)
│   │       ├── test_opcua_methods.py   # 70 method tests (asyncua monkey-patch)
│   │       └── test_opcua_live.py      # Event subscription tests
│   ├── js/unit/                    # Vitest JS unit tests (26 files, 577 tests in the current full JS run)
│   ├── e2e/                        # Playwright E2E specs
│   ├── shared_opcua/               # Shared OPC UA adapters (cross-client contracts)
│   └── legacy/                     # Compatibility test material only
│
├── src/resources/
│   └── css/nodeStyle.css   # Main stylesheet (referenced by index.html directly)
│
├── docs/
│   ├── skills/                    # task-specific reference guides
│   │   ├── associated-entities-interpreter.md
│   │   ├── endpointgraphics-tab-adder.md
│   │   └── simulate-single-result-caller.md
│   ├── DEVELOPMENT_GUIDE.md
│
└── .github/workflows/             # CI workflows (at repo root .github/, not here)
```

---

## Test Commands

```bash
# Install dev dependencies (includes pyfakefs for unit test isolation)
pip install -r requirements-dev.txt

# Full suite — OPC UA server auto-launched if needed
python run_all_tests.py

# Python unit tests only (no server)
python -m pytest tests/python/unit/ -v

# JS unit only
npx vitest run

# ESLint
npx eslint src/javascripts config.js --config eslint.config.mjs --max-warnings 0

# Live OPC UA tests (server must be running at endpoint)
set OPCUA_TEST_ENDPOINT=opc.tcp://localhost:40451
python -m pytest tests/python/live/test_opcua_methods.py tests/python/live/test_opcua_live.py --timeout=120 -v

# Docker tests (no live container needed)
python scripts/run_docker_tests.py

# Docker live build+run test
python scripts/run_docker_tests.py --live-docker
```

## Zero-Escape Testing Tools (run_all_tests.py Phase 1)

All auto-detected — present=run, absent=skip with install hint.
Network-backed advisory tools fail fast: pip-audit uses the PyPI JSON endpoint preflight, local cache, spinner disabled, and short timeouts; Semgrep uses the real `p/default` rules endpoint. Network/TLS/timeout outcomes are advisory skips, but fixable `pip-audit` CVEs fail the Python lane and advisory-only CVEs pass with an explicit note. `mypy` scans explicit Python source roots instead of `.` so runner temp/state directories cannot break local checks on Windows.
Runner-managed and Dockerfile `npm install` / `npm ci` commands use `--no-audit --no-fund`, disable the npm update notifier, and keep direct runner npm subprocesses on project `tmp/npm-cache` so repeated local/CI logs stay readable; JS CVEs are still checked by the separate explicit `npm audit` step.

| Tool | What it checks |
|------|---------------|
| `ruff` | Python lint + formatting |
| `mypy` | Static type checking |
| `bandit` | Python security (SAST) |
| `pip-audit` | CVE scan of Python dependencies |
| `semgrep` | Static analysis + security rules |
| `pyright` | Strict type checking (stricter than mypy) |
| `detect-secrets` | Hardcoded secrets/tokens |
| `eslint` | JS lint, including the scoped guard that forbids `Math.random()` in `connection-manager.mjs` and future auth/token/nonce modules |
| `prettier` | JS formatting |
| `npm audit` | CVE scan of JS dependencies |
| `depcheck` | Unused JS dependencies |
| `hadolint` | Dockerfile lint |
| `yamllint` | YAML validation |

---

## Known asyncua Bugs & Workarounds

### 1. `UaClient.call()` hardcoded 1-second timeout
**File:** `tests/python/live/test_opcua_methods.py` lines 34–75
**Fix:** Monkey-patch `_send_request` to use `self._timeout` (set to 60s):
```python
import asyncua.client.ua_client as _ua_client_mod
original_send = _ua_client_mod.UaClient._send_request
async def _patched_send(self, request, timeout=None, message_type=None):
    return await original_send(self, request, self._timeout, message_type)
_ua_client_mod.UaClient._send_request = _patched_send
```
This is applied globally in `conftest.py` or the test module setup.

### 2. `create_subscription()` rejects `max_notif_per_publish` kwarg
**Fix:** Use explicit parameters object:
```python
params = ua.CreateSubscriptionParameters(MaxNotificationsPerPublish=3)
sub = await client.create_subscription(params, handler)
```

### 3. `BadTooManyOperations` on SimulateBulkResults
**Root cause:** Server flag `BULK_RESULTS_IN_PROGRESS` blocks concurrent calls.
**Fix:** Retry loop (5 attempts, 1s sleep) in `test_bulk`:
```python
for attempt in range(5):
    try:
        result = await client.call_method(...)
        break
    except ua.UaStatusCodeError as e:
        if e.code == ua.StatusCodes.BadTooManyOperations and attempt < 4:
            await asyncio.sleep(1.0)
            continue
        raise
```

### 4. `BadNoSubscription` kills subscription during tree traversal
**Root cause:** Hundreds of rapid OPC UA reads trigger server to drop subscription.
**Fix in `tests/python/live/test_opcua_live.py`:** Use direct NodeIds (not tree traversal) + dedicated client per test:
```python
sim_node = client.get_node('ns=1;s=TighteningSystem/Simulations/SimulateResults')
```

---

## Event Subscription Rules

- **Subscribe on the Server node** (`client.get_node(ua.ObjectIds.Server)`), not individual method nodes.
- **Enable all filters by default** — no custom EventFilter needed; the event payload contains the full `ResultDataType` structure.
- `SimulateBulkResults` and `SimulateJobResult` both run in **detached threads** — the method returns `OpcUa_Good` immediately before any events fire. Use `_wait_events` with a quiescence phase (see `_wait_events` in `test_opcua_methods.py`) to ensure all async events are collected before asserting on `events[-1]`.
- `IsSimulated=True` only when Simulate* methods are called. When connecting to a real controller, `IsSimulated=False`.

## Joint Management Rules

- **Never hardcode joint IDs in live tests** — `Joint_1` / `Joint_2` are simulator defaults only.
- **Never hardcode the test tool path as the primary ProductInstanceUri source** — browse `AssetManagement/Assets/Tools/*/Identification/ProductInstanceUri` first; simulator string paths are fallback only.
- **Always call `GetJointList(ProductInstanceUri)` first** to get actual joint IDs from the server.
- Joint Demo treats bundled sample `ProductInstanceUri` values as display fallback only; `SelectJoint` and `StartSelectedJoining` require a selected server row, an explicit non-sample Settings value, or a server-detected URI before sending a method call.
- Joint Demo prefers server-discovered `GetJointList` IDs for its two buttons and falls back to Settings only when discovery is unavailable.
- Extract `JointId` from returned objects: `getattr(joint, "JointId", None) or getattr(joint, "Id", None)`.
- `GetJoint(ProductInstanceUri, JointId)` returns Uncertain/error for non-existent IDs (acceptable — just catch).
- IJT Console Client live tests also discover IDs via `GetJointList`; manual CLI calls may still pass `--joint-id` explicitly.

---

## Docker Configuration

### Key Facts
- Base image: `nikolaik/python-nodejs:python3.14-nodejs24`
- Runs as **non-root `appuser`** (uid/gid 1001)
- Packages pre-installed globally via `RUN pip install ...` (no venv needed in container)
- `IS_DOCKER=true` and `GITHUB_ACTIONS=true` mark Python as pre-isolated

### Venv Skip Pattern (in `setup_project.py` at project root)
```python
IS_DOCKER = os.getenv("IS_DOCKER") == "true"
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
_ENV_IS_PRE_ISOLATED = IS_DOCKER or IS_GITHUB_ACTIONS

def _get_python_path():
    if _ENV_IS_PRE_ISOLATED:
        return Path(sys.executable)  # environment-provided isolated Python
    return VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")

# In _is_runtime_ready():
venv_ok = True if _ENV_IS_PRE_ISOLATED else VENV_DIR.exists()

# In main setup flow:
if not _ENV_IS_PRE_ISOLATED:
    _create_virtualenv(latest_cmd)
```

Local `run_all_tests.py --ci-mode` uses `.venv_ci`. It must not fall back to the
developer's global Python.

### Ports
- HTTP frontend: 3000
- WebSocket backend: 8001

---

## Python Import Pattern (after scripts/ move)

Any file in `scripts/` that imports from `src/python/` must add project root to `sys.path`:
```python
from pathlib import Path
import sys
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from python.network_utils import endpoint_reachable, parse_endpoint_host_port
```
Same pattern applies to test files outside the package root.

---

## CI/CD Workflow

**File:** `.github/workflows/ci.yml` (blocking) / `.github/workflows/integration.yml` (non-blocking extended)

| Step | Command |
|------|---------|
| Python unit | `python -m pytest tests/python/unit/` |
| Python integration | `python -m pytest tests/python/integration -m integration` |
| Python live (needs server) | `python -m pytest tests/python/live -m live` |
| JS unit | `npm run test:unit:js` |

Repository-checkout hygiene tests are marked `checkout_hygiene`. They run in
normal checkout CI but are excluded from the Docker unit job because the Docker
test image intentionally contains the Web Client project without the repository
root `.git` metadata and root-level files.
| Action versions | `actions/checkout@v6`, `setup-python@v6`, `setup-node@v6` (all current) |
| Python version | `3.14` (stable in actions manifest) |
| asyncua | `asyncua>=1.2b2` — pip resolves pre-release when specifier explicitly includes it |

---

## JS Architecture Key Points

### WebSocket Protocol (Python ↔ Browser)
Commands sent as JSON over WS. Key message shapes:
- `{ action: "connect", endpoint: "opc.tcp://..." }`
- `{ action: "browse", nodeId: "..." }`
- `{ action: "read", nodeId: "..." }`
- `{ action: "methodcall", methodId: "...", args: [...] }`
- `{ action: "subscribe_events" }`

### Model Layer (`src/javascripts/ijt-support/models/`)
- `model-manager.mjs` — factory routing by `ResultMetaData.Classification`:
  - `1` → `TighteningDataType`, `3` → `BatchDataModel`, `4` → `JobDataModel`
- `ijt-base-model.mjs` — recursive property casting engine
- Linked-value contract: `{ type: 'linkedValue', value, link }` — **never change shape**

### Connection States (`connection-manager.mjs`)
Uses `CONNECTION_STATES` enum — not raw strings. Always import the enum when checking state.

### Event Queue (`event-manager.mjs`)
`maxSize=500` — oldest events dropped when full.

### View Level Constants (`views/tab-setup/endpoint-graphics.mjs`)
```js
const DEFAULT_VIEW_LEVEL = 3;  // Detailed (Basic=1, Simple=2, Detailed=3, Specialized=4, Settings=5)
```

---

## File Organisation Rules

### Root Level (keep clean — 20 files max)
Only standard files at root: `index.html`, `index.py`, `config.js`, `run_all_tests.py`,
`setup_project.py`, `run_docker_setup.py`,
`pyproject.toml`, `vitest.config.mjs`, `eslint.config.mjs`, `Dockerfile`, `docker-compose.yaml`,
`Makefile`, `package.json`, `package-lock.json`, `playwright.config.mjs`,
`requirements.txt`, `requirements-dev.txt`, `README.md`, `.env`, `.env.example`, `.gitignore`

### Root Directories
`.state/`, `docs/`, `logs/` (includes `logs/results/`), `scripts/`, `src/`, `tests/`

> **`.state/`** — pure runtime state (gitignored). Contains process JSON, locks, temp venvs. No code changes ever needed here.

### Root Placement Guardrails
- `scripts/create_structure.py` is the only scaffolding script location; do not add a root-level copy.
- `src/python/network_utils.py` is the only network helper location; do not add root-level import shims.
- `src/resources/css/nodeStyle.css` is the stylesheet location used by `index.html`.
- Do not add a root `conftest.py`; pytest fixtures live under `tests/`.
- Do not add root shell/bootstrap runners; use project-root `run_all_tests.py`.
- Do not add `scripts/run_tests.py` or `scripts/run_all_tests_bootstrap.py`; use project-root `run_all_tests.py`.
- Do not add a `Pytest/` directory; compatibility test material belongs under `tests/legacy/` when needed.

---

## Reference Files

| File | Covers |
|------|--------|
| `docs/SKILLS.md` ← **this file** | Full project map, rules, common mistakes, health check |
| `docs/DEVELOPMENT_GUIDE.md` | Development workflow, guardrails, prompt templates |
| `docs/skills/associated-entities-interpreter.md` | Interpreting `ResultMetaData.AssociatedEntities` |
| `docs/skills/endpointgraphics-tab-adder.md` | Adding new UI tabs (manager + view pattern) |
| `docs/skills/simulate-single-result-caller.md` | Wiring `SimulateSingleResult` method invocation |
| `docs/guides/ijt-support-guide.md` | JS core library map and contracts |
| `docs/guides/models-guide.md` | Model layer: parsing, casting, side effects |
| `docs/guides/result-model-guide.md` | Result model hierarchy and helpers |
| `docs/guides/views-guide.md` | UI layer: screens, tabs, styling |

---

## Health Check

Run these before and after code changes:

```bash
npx eslint src/javascripts config.js --config eslint.config.mjs --max-warnings 0
python -m pip check
python index.py
```

Expected results:
- ESLint exits with code 0, 0 warnings.
- `pip check` reports no broken requirements.
- Backend starts and logs WebSocket startup on port `8001`.
- Frontend responds on `http://localhost:3000`.

### Quick Full Test Run
```bash
python run_all_tests.py
```
Runs Python unit + integration tests, JS unit tests, ESLint, Bandit, mypy, pip-audit.
For CI lane parity, run `python run_all_tests.py --phase1-python` for the
Python/static lane and `python run_all_tests.py --phase1-js` for the
JavaScript/static lane. The original `--phase1` flag still runs both lanes
together for local convenience.
Every runner invocation writes `test-results/timing-latest.json` and
`test-results/timing-history.jsonl`, then appends the same payload to
`.state/timing-history.jsonl`. Use those files for Phase 1 drift analysis
instead of guessing from wall-clock totals.
Root Phase 2 no longer delegates one broad Web Client live suite. It invokes
separate Web Client suites for Python OPC UA, Python WebSocket backend, Python
WebSocket lifecycle, Playwright smoke, Playwright features, Playwright
regression, and Docker smoke. Each live/browser suite owns its own OPC UA,
WebSocket, and UI ports, so failures are localized to one test type and service
lifecycle.
At the root-runner level, `web-client-docker-smoke` is prechecked like the server
Docker smoke: missing Docker or a stopped daemon is reported as a skipped suite.
Calling this Web runner directly with `--docker-only` remains an explicit Docker
validation request and fails if Docker cannot run.
The Playwright feature suite runs with `IJT_PLAYWRIGHT_FEATURE_WORKERS=4`
locally and defaults to two feature workers in CI. Each worker gets a dedicated
WebSocket backend and OPC UA simulator by offsetting the base `WS_TEST_URL` and
`OPCUA_TEST_ENDPOINT` ports; the browser URL carries the worker-specific
WebSocket port through query parameters. `IJT_PLAYWRIGHT_WORKERS` is the only
environment variable consumed by `playwright.config.mjs`; the runner sets it
when it launches a Playwright project.
Local browser install prerequisites live in `README.md`; corporate/offline
users need the documented `HTTPS_PROXY`, `PLAYWRIGHT_DOWNLOAD_HOST`, or
`PLAYWRIGHT_BROWSERS_PATH` path before running local Playwright installs.

Focused live-suite commands used by the root runner:

```bash
python run_all_tests.py --python-opcua-only
python run_all_tests.py --python-backend-only
python run_all_tests.py --python-lifecycle-only
python run_all_tests.py --playwright-smoke-only
python run_all_tests.py --playwright-features-only
python run_all_tests.py --playwright-regression-only
python run_all_tests.py --compatibility-smoke-only
python run_all_tests.py --docker-only
```

GitHub `ci.yml` runs this runner in two Phase 1 lanes: `web-client-python`
delegates to `--phase1-python`, and `web-client-js` delegates to
`--phase1-js`. The workflow no longer duplicates the individual pytest,
Vitest, ESLint, mypy, Bandit, and audit commands, and the split gives each
language stack its own timing and failure surface. GitHub `integration.yml`
runs the same root-runner Web Client live/e2e suites as local validation, split
by execution surface. `web-client-live-*` suites stay on `windows-latest` with
the Windows simulator package. Every `web-client-e2e-*` suite runs inside the
owned `ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci`
image, resolved from the reviewed
`.github/docker/ijt-browser-ci/image-pin.json` digest, then started with
`docker run --network=none`; Chromium, its Linux system dependencies, the
locked `@playwright/test` version, Python 3.14, and Node 24 are all baked into
the image. The host runner never executes
`npx playwright install chromium --with-deps`. No job-level `container:`
image is used —
container-job images are pulled by GitHub before any step runs, so a
registry outage would take the whole job down with no in-job retry,
fallback, or diagnostics. Browser Features keeps two Playwright shards
and each suite receives an isolated `IJT_WEB_TEST_RESULTS_DIR`, so
JUnit, coverage, Playwright, and timing artifacts cannot overwrite another
suite's files.
Web Client — Browser Compatibility Smoke is deliberately outside the bulk
browser logic lane. `python run_all_tests.py --compatibility-smoke-only` uses
default ports OPC UA 40468, WebSocket 8004, and HTTP 3007 unless explicit
endpoint/env overrides are provided. It runs
`playwright.compatibility-smoke.config.mjs`,
launches the configured real browser channel, and executes only the two
audit-derived specs under `tests/e2e-compatibility-smoke/`: Result bundle import
through the visible file chooser and Result bundle JSON export through browser
download handling. The GitHub workflow
`.github/workflows/web-client-compatibility-smoke.yml` is schedule/manual only
and opens or closes the stable issue key
`[Web Client Compatibility Smoke] windows-latest / msedge` from real red/green
results.

If the checked-in simulator binary directory is absent in CI, the runner
extracts the Release 2 platform-specific simulator ZIP from
`OPC_UA_Servers/Release2` before launching owned live-suite servers. Linux hosts
prefer `OPC_UA_IJT_Server_Simulator_Linux.zip`; Windows hosts prefer
`OPC_UA_IJT_Server_Simulator.zip`.

### Browser Runtime WebSocket Config

`config.js` must not hardcode service port `8001`. The hosting page supplies
the production default through `window.__IJT_RUNTIME__`, and tests can override
`wsHost`, `wsPort`, or `wsProtocol` through the page URL. This is required for
the Playwright feature worker pool; do not replace it with static service ports.

### Web Test Backend Manager

`tests/test_infra/backend_manager.py` is the foundation for managed live-suite
service ownership. It fails on already-open managed ports instead of silently
adopting shared services, emits backend lifecycle events, and probes health
through the full WebSocket -> OPC UA contract: handshake, `connect to`,
`namespaces` envelope validation, and `terminate connection`. The current root
split already applies owned ports at the runner level; future work can migrate
per-test lifecycle internals to this manager without returning to a monolithic
suite.

### Playwright Endpoint Readiness

Endpoint tab buttons expose durable readiness attributes:
`data-opcua-connection-state` and `data-opcua-subscription-state`.
Playwright helpers must wait on those attributes becoming `connected`.
Browser WebSocket disconnects mark existing endpoint tabs disconnected; when
the WebSocket reconnects, active endpoint managers reissue their OPC UA connect
request and drive the same attributes back to `connected` after the backend
confirms connection and subscription.
Do not use visual CSS classes such as `.onColor` as connection readiness
signals; those classes are presentation details for the status display.
Joint Demo Playwright actions must also wait until the active
`ProductInstanceUri` label is resolved from server discovery, a selected server
tool, or an explicit non-sample Settings value before clicking `SelectJoint` or
`StartSelectedJoining`; bundled sample fallback labels do not satisfy this
readiness contract.

### Playwright Selector Contracts

Use semantic selectors for controls that can move inside reusable header
widgets. The Consolidated Result dropdowns expose
`data-ijt-result-control="type"`, `"result"`, and `"view"`; Playwright tests
must use those hooks instead of positional selectors such as
`.resultheader select:first-of-type`.

Use the rendered tab label exactly. The address-space tab is `Address Space`
with a space, not `AddressSpace`.
Address-space expansion tests must use stable node identity metadata:
`data-opcua-node-id`, `data-opcua-browse-name`, and normalized
`data-opcua-node-class`. The first visible tree button may already be open or
may be a leaf, so treating the first button click as "expand" is incorrect.
Use explicit browse-name/node-id helpers such as `expandByBrowseName(['Server'])`
and assert named children such as `ServerStatus`.

Direct backend WebSocket E2E tests validate the backend response envelope. The
`namespaces` command returns `data.namespaces`; the `browse` command returns
`data.nodes`. Do not assert that `resp.data` itself is the array.
Namespace assertions must use real namespace URIs such as
`http://opcfoundation.org/UA/`, `http://opcfoundation.org/UA/IJT/Base/`, and
`http://opcfoundation.org/UA/IJT/Tightening/`; do not assert the non-URI token
`OpcUa`.

Simulator method buttons must render valid default values for required numeric
arguments. `SimulateEvents` and `SimulateConditions` default to event type `1`,
and `SimulateBulkEvents` defaults to event type `1` and count `3`.

---

## Common Mistakes to Avoid

1. **Never** create `network_utils.py` at project root — it lives in `src/python/`. `setup_project.py` and `run_docker_setup.py` are **canonical at project root** (the Makefile invokes them there; never add duplicates to `scripts/`).
2. **Never** use `from network_utils import ...` in test files — use `from python.network_utils import ...`.
3. **Never** use `venv\Scripts\python.exe` in docs/scripts — use `python` (venv activated by `run_all_tests.py`).
4. **Never** subscribe events on individual method nodes — always use the Server node.
5. **Never** use raw string connection states in JS — use `CONNECTION_STATES` enum.
6. **Never** change linked-value object shape `{ type, value, link }`.
7. Treat `scripts/create_structure.py` as scaffolding only; do not run it as part of normal development.
8. **Never** use visual CSS classes such as `.onColor` as Playwright endpoint readiness; use endpoint tab `data-opcua-*` state attributes.
9. **Never** use positional result-header selectors in Playwright; use `data-ijt-result-control`.
10. **Never** assert raw arrays for backend WS `namespaces` / `browse`; assert `data.namespaces` / `data.nodes`.
11. **Never** send empty numeric simulator method arguments from the Web UI; define a valid default or require user input before calling.
12. **Never** include local virtualenvs or generated test artifacts in Docker build context; keep `.venv/`, `.venv_test/`, `.venv_ci/`, `node_modules/`, `test-results/`, and `tmp/` ignored by `.dockerignore`.
13. **Never** reintroduce a broad root Web Client live suite; add or adjust the narrow live/browser suite that owns the affected test type and service lifecycle.


## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPCUA_TEST_ENDPOINT` | `opc.tcp://localhost:40451` | OPC UA server endpoint for direct live tests; runner auto-launch uses `opc.tcp://localhost:40463` |
| `OPCUA_SERVER_URL` | `opc.tcp://localhost:40451` | Runtime OPC UA server override; when set, auto-launch is skipped |
| `WS_PORT` | `8001` | WebSocket backend port |
| `WS_TEST_URL` | `ws://localhost:8001` | Test WebSocket URL; root split suites override this per suite |
| `UI_TEST_PORT` | `3000` | Playwright static UI server port; root split suites override this per browser suite |
| `UI_TEST_BASE_URL` | `http://127.0.0.1:3000` | Playwright base URL; root split suites override this per browser suite |
| `IJT_PLAYWRIGHT_WORKERS` | `2` in CI, `1` in direct local Playwright config | Playwright worker count consumed by `playwright.config.mjs`; the runner sets it for project-specific runs |
| `IS_DOCKER` | (unset) | Set to `true` inside Docker containers; uses container-provided Python |
| `GITHUB_ACTIONS` | (unset) | Set by GitHub Actions; uses runner-provided Python |
| `CI` | (unset) | Enables CI behavior; local `--ci-mode` still uses `.venv_ci` |
| `OPCUA_SIMULATOR_EXE` | (unset) | Path to simulator binary for auto-launch |
| `IJT_SIMULATOR_INSTANCE_ROOT` | `{RUNNER_TEMP or temp}/ijt-sim` | Optional short root for runner-owned simulator copies; each port gets its own child directory |
| `IJT_DOCKER_BUILD_TIMEOUT` | `1200` | Docker image build timeout in seconds |
| `IJT_DOCKER_TIMEOUT` | `90` | Docker HTTP readiness timeout in seconds |

### Server Auto-Launch & Port Isolation

This client's split live suites auto-launch dedicated server instances on
assigned root-runner ports (starting at **40463**) through the copy-and-patch
mechanism: copy the binary, patch `server_configuration.json`, and manage the
process lifecycle. Port 40451 is never used by this test runner.
When the runner sets `OPCUA_TEST_ENDPOINT`, the WebSocket backend serves that endpoint as the browser
`LOCAL` connection point for Playwright so UI tests connect to the same isolated server as direct tests.
`OPCUA_SERVER_URL` follows the same runtime override path for local validation; leave it unset for normal
production/browser use unless you intentionally want to replace the served `LOCAL` endpoint.

Runner-owned OPC UA simulator launches write `opcua-server-<port>.out.log` and
`opcua-server-<port>.err.log` under `test-results/` (or `IJT_WEB_TEST_RESULTS_DIR`
when set). The runner also exports `IJT_OPCUA_PRESTARTED_PORT=<port>` after an
owned simulator reaches OPC UA protocol readiness. Live/integration pytest fixtures use that
marker to fail fast with the captured log paths if the runner-owned port closes
before fixture startup; they do not spawn a fallback EXE on a different,
unpatched port. Fixtures also run OPC UA protocol probes and a backend-only
WebSocket JSON dispatch probe after TCP ports open so first tests do not consume
the simulator/backend warmup window. The WebSocket readiness probe must remain
non-mutating; direct OPC UA readiness owns the simulator protocol check.
Runner-side simulator failure extraction lives in `tests/python/_live_server_readiness.py`.
The bounded startup retry is capped by `MAX_SIMULATOR_LAUNCH_ATTEMPTS` and only
matches `SIMULATOR_RETRY_TRIGGERS`; never generalize it to retry unknown
readiness failures.

On Windows, runner-owned simulator copies live under a short temp root
(`RUNNER_TEMP\ijt-sim\<port>` on GitHub Actions, the system temp fallback, or
`<SystemDrive>\ijt-sim\<port>` if the temp root is still too long) instead of
`tmp\server_instance_<port>` inside the repository. The simulator generates
long PKI certificate filenames and rejects install paths that exceed its own
safe path-length threshold. Logs stay under `test-results/` so CI artifacts
still capture startup failures; only the short-lived simulator copy moves to
temp.

For the full port assignment table, auto-launch mechanics, and venv rationale, see
[`docs/TEST_TIERS.md`](../../../../docs/TEST_TIERS.md).
