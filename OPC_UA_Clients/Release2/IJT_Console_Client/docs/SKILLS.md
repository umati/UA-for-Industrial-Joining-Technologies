# IJT Console Client — Developer Reference

---

## Project Identity

| Item | Value |
|------|-------|
| **Location** | `OPC_UA_Clients/Release2/IJT_Console_Client/` |
| **Purpose** | Minimal reference OPC UA IJT console client — events, methods, results |
| **Stack** | Python 3.14+, asyncua pinned via repo-root constraints.txt, asyncio |
| **OPC UA Spec** | OPC UA for Industrial Joining Technologies (IJT) |
| **Server default** | `opc.tcp://localhost:40451` |

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
├── requirements.txt         # asyncua (pin lives in repo-root constraints.txt), pytz, aiofiles, orjson, cryptography, pyOpenSSL
├── pyproject.toml           # asyncio_mode=auto (+ ruff, coverage, bandit, mypy)
├── docs/
│   └── SKILLS.md             # ← this file — developer reference (includes method quick reference)
└── tests/
    ├── conftest.py                       # shared fixtures (top-level)
    ├── unit/
    │   ├── conftest.py
    │   ├── test_setup_client.py              # setup_client.py launcher — pyfakefs for all FS ops
    │   ├── test_client_config_and_main.py
    │   ├── test_method_caller.py
    │   ├── test_result_event_handler.py
    │   ├── test_serialize_data.py
    │   ├── test_utils.py
    │   ├── test_event_handler.py
    │   ├── test_opcua_client.py
    │   ├── test_ijt_logger.py
    │   ├── test_call_structure.py
    │   ├── test_import_paths.py
    │   ├── test_independence.py
    │   ├── test_repo_hygiene.py
    │   ├── test_resource_management.py
    │   ├── test_security.py
    │   ├── test_static_analysis.py
    │   ├── test_wire_format_contracts.py
    │   ├── test_event_handler_extended.py    # bytes/str EventId, handle_queue, ws teardown paths
    │   ├── test_event_types_unit.py           # get_event_types happy + exception re-raise
    │   ├── test_main_extended.py              # run_method_call branches, run_client, main() errors
    │   ├── test_opcua_client_extended.py      # connect retry, subscribe, run_forever, cleanup variants
    │   ├── test_serialize_data_extended.py    # _json_dumps stdlib fallback, __slots__, serialize_tuple
    │   └── test_utils_extended.py             # _to_json_str/bytes, log_* helpers, nodeid_to_str
    └── live/
        ├── conftest.py                   # auto-starts OPC UA server; pytest.fail() if unreachable
        └── test_opcua_live_console.py    # live OPC UA tests with dynamic Tool PIU lookup
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
`pyright` is installed by default (listed in `requirements-dev.txt`) and runs as **advisory** (non-blocking; findings written to `pyright.stderr.txt`). It uses basic mode; `tests/unit` is excluded from pyright scope because unit tests intentionally pass wrong types for edge-case testing. See `pyrightconfig.json`.
`ruff` (lint+format), `mypy` (types), `bandit` (security), `pip-audit` (CVE scan),
`semgrep` (static analysis), `pyright` (standard install, advisory), `detect-secrets` (secrets).
pip-audit uses the PyPI JSON endpoint preflight, local project cache, spinner disabled, and short timeouts; network/TLS/timeout outcomes are SKIP, not PASS/FAIL. Fixable CVEs fail the suite; advisory-only CVEs may pass with an explicit note.

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
- Simulation methods use method-specific signatures. Do not infer a shared
  boolean-only shape across result, event, and bulk simulation methods.
- `SimulateBulkResults` sends results **one by one** in a detached thread.
- Retry logic needed for `BadTooManyOperations` (bulk results flag on server).
- Tool-scoped method calls read `ProductInstanceUri` by browsing the visible
  `AssetManagement/Assets/Tools/*/Identification/ProductInstanceUri` value.
  Do not use hardcoded namespace indexes or string NodeIds for this path.
  Server instance NodeIds and spec BrowseName namespaces can differ, so browse
  helpers should match the expected namespace first and fall back to exact
  BrowseName text when the server exposes mixed namespace shapes.
- Live tests that share a module-scoped asyncua client must use the same
  pytest-asyncio loop scope, e.g. `@pytest.mark.asyncio(loop_scope="module")`.
- **Joint IDs**: dynamically call `GetJointList` to discover real IDs before calling `GetJoint`/`SelectJoint`.
  - `Joint_1` / `Joint_2` are simulator defaults only; do not assume they exist on other IJT servers.
  - Manual CLI calls may pass `--joint-id <server JointId>` after discovery.

### Serialization (`serialize_data.py`)
- Shared serialization logic with IJT Web Client (`src/python/serialize_data.py`).
- Converts `ua.ExtensionObject`, `ua.NodeId`, `ua.LocalizedText`, `datetime` → JSON-safe types.

---

## asyncua Known Issues (Python 3.14)

### `UaClient.call()` hardcoded 1-second timeout
Centralized patch in `IJT_Web_Client/tests/python/_asyncua_compat.py`. The patch is **capability-gated**: it inspects `UaClient._send_request`'s `timeout` parameter default. If the default is still a hard-coded number, the patch is applied; if upstream changes it to `None` or removes the method, the patch is skipped and a `DeprecationWarning` marks the shim for removal. The patch is not gated on asyncua version string — the repo-pinned master SHA can self-report a pre-release version while still keeping the affected signature.
```python
from tests.python._asyncua_compat import apply_send_request_timeout_patch

apply_send_request_timeout_patch()
```
The patch wraps `UaClient._send_request` to use `self._timeout` instead of the hard-coded fallback (1 s).

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
  - `TighteningSystem/Simulations/SimulateResults/SimulateSingleResult(resultType, includeTraces)`
  - `TighteningSystem/Simulations/SimulateResults/SimulateBulkResults(...)` — multiple results (one by one)
  - `TighteningSystem/Simulations/SimulateEventsAndConditions/SimulateEvents(eventType)`
  - `TighteningSystem/Simulations/SimulateEventsAndConditions/SimulateBulkEvents(eventType, count)`
- UaExpert saved config: `IJT_LOCAL_SIMULATOR.uap` (read-only reference)

---

## Common Mistakes to Avoid

1. **Never** assume all simulation methods have the same argument list.
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
python main.py --origin-id= --joint-id "<JointId returned by GetJointList>" --call select_joint --url "opc.tcp://localhost:40451"
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

This client's test runner auto-launches a dedicated server instance on port **40461** (copy-and-patch
mechanism — copies the binary, patches `server_configuration.json`, and manages the full lifecycle).
Port 40451 is never used by this test runner.
GitHub integration uses the root `scripts/start_server_on_port.py` launcher,
which keeps the copied simulator under a short `RUNNER_TEMP/ijt-sim` root.

For the full port assignment table, auto-launch mechanics, and venv rationale, see
[`docs/TEST_TIERS.md`](../../../../docs/TEST_TIERS.md).
