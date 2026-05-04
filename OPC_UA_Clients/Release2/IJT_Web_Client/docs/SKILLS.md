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
├── index.py                # Python WebSocket backend (asyncio + websockets, port 8001)
├── config.js               # Shared JS config (WS_PORT, endpoints, timeouts)
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
│   │   └── live/                   # Needs real OPC UA server on :40451 (marker: live)
│   │       ├── test_opcua_methods.py   # 70 method tests (asyncua monkey-patch)
│   │       └── test_opcua_live.py      # Event subscription tests
│   ├── js/unit/                    # Vitest JS unit tests (25 files, 570 tests in the current full JS run)
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
Network-backed advisory tools fail fast: pip-audit uses the PyPI JSON endpoint preflight, local cache, spinner disabled, and short timeouts; Semgrep uses the real `p/default` rules endpoint. `mypy` scans explicit Python source roots instead of `.` so runner temp/state directories cannot break local checks on Windows.
Runner-managed `npm install` uses `--no-audit --no-fund` to keep repeated local/CI logs readable; JS CVEs are still checked by the separate explicit `npm audit` step.

| Tool | What it checks |
|------|---------------|
| `ruff` | Python lint + formatting |
| `mypy` | Static type checking |
| `bandit` | Python security (SAST) |
| `pip-audit` | CVE scan of Python dependencies |
| `semgrep` | Static analysis + security rules |
| `pyright` | Strict type checking (stricter than mypy) |
| `detect-secrets` | Hardcoded secrets/tokens |
| `eslint` | JS lint |
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

- **Never hardcode `"joint1"`** — the real server joint ID is `"Joint_1"` (capital J, underscore).
- **Always call `GetJointList(ProductInstanceUri)` first** to get actual joint IDs from the server.
- Extract `JointId` from returned objects: `getattr(joint, "JointId", None) or getattr(joint, "Id", None)`.
- `GetJoint(ProductInstanceUri, JointId)` returns Uncertain/error for non-existent IDs (acceptable — just catch).
- `SelectJoint` joint ID configurable via `REGRESSION_JOINT_1` / `REGRESSION_JOINT_2` env vars; defaults: `"Joint_1"`, `"Joint_2"`.
- IJT Console Client: pass `--joint-id Joint_1` (not `joint1`) when calling `select_joint`.

---

## Docker Configuration

### Key Facts
- Base image: `nikolaik/python-nodejs:python3.14-nodejs24`
- Runs as **non-root `appuser`** (uid/gid 1001)
- Packages pre-installed globally via `RUN pip install ...` (no venv needed in container)
- `IS_DOCKER=true` env var controls venv skip logic

### Venv Skip Pattern (in `setup_project.py` at project root)
```python
IS_DOCKER = os.getenv("IS_DOCKER") == "true"

def _get_python_path():
    if IS_DOCKER:
        return Path(sys.executable)  # system Python, already set up
    return VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")

# In _is_runtime_ready():
venv_ok = True if IS_DOCKER else VENV_DIR.exists()

# In main setup flow:
if not IS_DOCKER:
    _create_virtualenv(latest_cmd)
```

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
(Live OPC UA tests in `tests/python/live/test_opcua_methods.py` require a running server on `opc.tcp://localhost:40451`.)

---

## Common Mistakes to Avoid

1. **Never** create `network_utils.py` at project root — it lives in `src/python/`. `setup_project.py` and `run_docker_setup.py` are **canonical at project root** (the Makefile invokes them there; never add duplicates to `scripts/`).
2. **Never** use `from network_utils import ...` in test files — use `from python.network_utils import ...`.
3. **Never** use `venv\Scripts\python.exe` in docs/scripts — use `python` (venv activated by `run_all_tests.py`).
4. **Never** subscribe events on individual method nodes — always use the Server node.
5. **Never** use raw string connection states in JS — use `CONNECTION_STATES` enum.
6. **Never** change linked-value object shape `{ type, value, link }`.
7. Treat `scripts/create_structure.py` as scaffolding only; do not run it as part of normal development.


## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPCUA_TEST_ENDPOINT` | `opc.tcp://localhost:40451` | OPC UA server endpoint for live tests |
| `OPCUA_SERVER_URL` | `opc.tcp://localhost:40451` | Runtime OPC UA server override; when set, auto-launch is skipped |
| `WS_PORT` | `8001` | WebSocket backend port |
| `IS_DOCKER` | (unset) | Set to `true` inside Docker containers; skips venv creation |
| `OPCUA_SIMULATOR_EXE` | (unset) | Path to simulator binary for auto-launch |

### Server Auto-Launch & Port Isolation

This client's test runner auto-launches a dedicated server instance on port **40463** (copy-and-patch
mechanism — copies the binary, patches `server_configuration.json`, and manages the full lifecycle).
Port 40451 is never used by this test runner.

For the full port assignment table, auto-launch mechanics, and venv rationale, see
[`docs/TEST_TIERS.md`](../../../../docs/TEST_TIERS.md).
