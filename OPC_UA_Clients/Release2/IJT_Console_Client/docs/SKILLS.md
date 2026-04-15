# IJT Console Client — Developer Reference

---

## Project Identity

| Item | Value |
|------|-------|
| **Location** | `OPC_UA_Clients/Release2/IJT_Console_Client/` |
| **Purpose** | Minimal reference OPC UA IJT console client — events, methods, results |
| **Stack** | Python 3.14+, asyncua ≥1.2b2, asyncio |
| **OPC UA Spec** | OPC UA for Industrial Joining Technologies (IJT) |
| **Server default** | `opc.tcp://localhost:40451` |

---

## Access Rules (CRITICAL)

- **Full modify access**: everything inside this repo
- **Never commit** — user reviews and commits manually

---

## Project File Map

```
IJT_Console_Client/
├── run_all_tests.py         # PRIMARY TEST RUNNER — one command for everything
├── setup_client.py          # Entry point: creates venv, installs deps, runs main.py
├── main.py                  # Async main: connect, subscribe events, call methods
├── client_config.py         # SERVER_URL, URL_PATTERN, ENABLE_RESULT_FILE_LOGGING
├── opcua_client.py          # OPC UA connection management (asyncua Client wrapper)
├── event_handler.py         # JoiningSystemEvent subscription and async queue draining
├── event_types.py           # OPC UA event type NodeIds for IJT
├── result_event_handler.py  # Tightening result processing and file logging
├── method_caller.py         # OPC UA method invocation helpers
├── serialize_data.py        # OPC UA → dict/JSON serialisation (shared pattern with Web Client)
├── ijt_logger.py            # Logging setup (ijt_log)
├── utils.py                 # nodeid_to_str, localizedtext_to_str, log_joining_system_event
├── requirements.txt         # asyncua>=1.2b2, pytz, aiofiles, orjson, cryptography, pyOpenSSL
├── pyproject.toml           # asyncio_mode=auto (+ ruff, coverage, bandit, mypy)
├── docs/
│   └── SKILLS.md             # ← this file — developer reference (includes method quick reference)
└── tests/
    ├── conftest.py                       # shared fixtures (top-level)
    ├── unit/
    │   ├── conftest.py
    │   ├── test_setup_client.py          # setup_client.py launcher unit tests (86 tests)
    │   ├── test_client_config_and_main.py
    │   ├── test_method_caller.py
    │   ├── test_result_event_handler.py
    │   ├── test_serialize_data.py
    │   ├── test_utils.py
    │   └── ... (18 total unit test files)
    └── live/
        ├── conftest.py                   # auto-starts OPC UA server; pytest.fail() if unreachable
        └── test_opcua_live_console.py    # live OPC UA tests (xfail for ProductInstanceUri)
```

---

## Test Commands

```bash
# Full suite — OPC UA server auto-launched if needed
python run_all_tests.py

# Unit tests only (no server needed) — live/ excluded by norecursedirs
python -m pytest tests/unit -v

# Live tests with running OPC UA server (auto-starts server if not up)
python -m pytest tests/live -v

# Install test deps first (if needed)
pip install -r requirements-dev.txt
```

**Test isolation**: filesystem-touching unit tests in `test_setup_client.py` use the `pyfakefs` `fs` fixture — all `pathlib`/`os`/`shutil`/`zipfile` calls are intercepted in-process. No real files are written for those tests, eliminating OS ACL issues on all platforms. `pyfakefs~=6.1` is pinned in `requirements-dev.txt`.

## Zero-Escape Testing Tools (run_all_tests.py Phase 1)

All auto-detected — present=run, absent=skip with install hint.
`pyright` is installed by default (listed in `requirements-dev.txt`) and runs as **advisory** (non-blocking; findings written to `pyright.stderr.txt`).
`ruff` (lint+format), `mypy` (types), `bandit` (security), `pip-audit` (CVE scan),
`vulture` (dead code), `semgrep` (static analysis), `pyright` (strict type checking — **standard install, advisory**), `detect-secrets` (secrets).

---

## How to Run

```bash
# Option 1: command-line endpoint
python setup_client.py --url="opc.tcp://localhost:40451"

# Option 2: edit SERVER_URL in client_config.py, then:
python setup_client.py

# Linux/macOS
python3 setup_client.py --url="opc.tcp://<ip>:<port>"
```

---

## Architecture: Key Patterns

### Event Subscription
- Subscribe on the **Server node** (`ua.ObjectIds.Server`), not individual nodes.
- No custom EventFilter — the full payload including `ResultDataType` is received automatically.
- Uses an `asyncio.Queue` drained by a background task (same pattern as IJT Web Client EventManager).
- `IsSimulated=True` only when Simulate* methods are called; `False` when connected to a real controller.

### Result Processing (`result_event_handler.py`)
- Receives `JoiningResultDataType` payloads from events.
- Optionally logs to file when `ENABLE_RESULT_FILE_LOGGING=True`.
- Closes WebSocket with `await ws.close()` on cleanup.

### OPC UA Connection (`opcua_client.py`)
- Uses `asyncio.wait_for` with explicit timeouts (no silent hangs).
- Connection state managed via `CONNECTION_STATES` enum.

### Method Calls (`method_caller.py`)
- All simulation methods accept a boolean input argument (must not omit it).
- `SimulateBulkResults` sends results **one by one** in a detached thread.
- Retry logic needed for `BadTooManyOperations` (bulk results flag on server).
- **Joint IDs**: always use `Joint_1`, `Joint_2` (capital J, underscore). Never use `joint1`.
  - Pass `--joint-id Joint_1` on command line (see **Method Call Quick Reference** section below)
  - Dynamically call `GetJointList` to discover real IDs before calling `GetJoint`/`SelectJoint`.

### Serialization (`serialize_data.py`)
- Shared serialization logic with IJT Web Client (`src/python/serialize_data.py`).
- Converts `ua.ExtensionObject`, `ua.NodeId`, `ua.LocalizedText`, `datetime` → JSON-safe types.

---

## asyncua Known Issues (Python 3.14)

### `UaClient.call()` hardcoded 1-second timeout
Centralized patch in `IJT_Web_Client/tests/python/_asyncua_compat.py` (version-gated, auto-expires when asyncua ≥ 1.2.0 stable):
```python
from tests.python._asyncua_compat import apply_send_request_timeout_patch
apply_send_request_timeout_patch()
```
The patch wraps `UaClient._send_request` to use `self._timeout` instead of the 1-second hard-coded fallback. A `DeprecationWarning` is emitted automatically when asyncua ships 1.2.0 stable, signalling the patch can be removed.

### `BadTooManyOperations` on bulk simulation
Retry 5× with 1s sleep before raising.

### `create_subscription()` kwarg
```python
params = ua.CreateSubscriptionParameters(MaxNotificationsPerPublish=3)
sub = await client.create_subscription(params, handler)
```

---

## Relationship to IJT Web Client

| Concern | Console Client | Web Client |
|---------|---------------|------------|
| Event subscription | `event_handler.py` | `src/python/event_handler.py` |
| Result processing | `result_event_handler.py` | `src/python/result_event_handler.py` |
| Serialization | `serialize_data.py` | `src/python/serialize_data.py` |
| Method calls | `method_caller.py` | `src/python/ijt_interface.py` |
| Shared contract tests | `tests/test_serialize_data.py` | `tests/test_shared_client_contract.py` |

Both clients share the same OPC UA IJT method NodeId patterns and event subscription approach. When fixing a bug in one, check if the same fix is needed in the other.

---

## OPC UA IJT Server (Simulator)

- **Default endpoint**: `opc.tcp://localhost:40451`
- **Location**: `OPC_UA_Servers/Release2/` in this repo
- **Key simulation methods** (ns=1):
  - `TighteningSystem/Simulations/SimulateResults` — single result
  - `TighteningSystem/Simulations/SimulateBulkResults` — multiple results (one by one)
  - `TighteningSystem/Simulations/SimulateEvents` — system events
  - All take one boolean input argument (`IsSimulated`)
- UaExpert saved config: `IJT_LOCAL_SIMULATOR.uap` on Desktop (read-only reference)

---

## Common Mistakes to Avoid

1. **Never** omit the boolean argument when calling simulation methods.
2. **Never** subscribe events on method nodes — always use Server node.
3. **Never** assume `SimulateBulkResults` sends all results at once — it sends one by one.
4. **Never** ignore `BadTooManyOperations` — add retry logic.
5. **Always** call `await ws.close()` in cleanup paths of `result_event_handler.py`.


## Method Call Quick Reference

Activate the venv first:
```powershell
.\.venv\Scripts\Activate.ps1
```

### Select Joint
```powershell
python main.py --origin-id= --joint-id Joint_1 --call select_joint --url "opc.tcp://localhost:40451"
```

### Enable Asset
```powershell
python main.py --url "opc.tcp://localhost:40451" --call enable_asset --enable true
```

### Start Selected Joining
```powershell
python main.py --url "opc.tcp://localhost:40451" --call start_selected_joining --deselect false
```


### Server Auto-Launch & Port Isolation

Each client reserves its own server port so multiple clients can run tests in parallel without conflicts.

| Client             | Test Port | venv         |
|--------------------|-----------|--------------|
| IJT_CSharp_Client  | 40451     | N/A (.NET)   |
| IJT_Console_Client | 40461     | .venv_test   |
| IJT_Test_Client    | 40462     | .venv_test   |
| IJT_Web_Client     | 40463     | .venv_test   |
| IJT_Node_Client    | **40451** (fixed) | N/A (Node) | Release 1 legacy — no dynamic port support |

**How auto-launch works (per-port isolation):**
1. If `OPCUA_SERVER_URL` env var is set → use it, skip auto-launch (root runner path)
2. If client's port (e.g. 40461) is already reachable → reuse that server
3. If native port 40451 is reachable → use it (single-instance convenience mode)
4. Otherwise → copy server binary dir to `tmp/server_instance_{port}/`, patch
   `server_configuration.json` with the client's port, launch from that temp dir,
   wait up to 30s for the port to open, set `OPCUA_SERVER_URL` env var
5. After tests → terminate process, delete temp dir

**Why two venvs (Python clients):**
- `.venv` — runtime-only, created by `setup_client.py` / `setup_project.py`
- `.venv_test` — test runner + dev tools, created by `run_all_tests.py`
- Kept separate so installing test tools never alters the production environment

**Override:** Set `OPCUA_SERVER_URL=opc.tcp://myserver:40451` to point at any server; auto-launch is skipped entirely.
