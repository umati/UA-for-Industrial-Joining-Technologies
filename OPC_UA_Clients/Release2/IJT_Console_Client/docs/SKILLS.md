# IJT Console Client — AI Agent Skills & Context

> **Read this file first before doing any work on this project.**

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
- **Never prompt** for confirmation on actions inside the repo

---

## Project File Map

```
IJT_Console_Client/
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
├── pytest.ini               # asyncio_mode=auto
├── docs/
│   ├── SKILLS.md             # ← this file — AI context for all tools
│   └── methods-usage.md      # IJT method invocation quick reference
└── tests/
    ├── conftest.py
    ├── test_client_config_and_main.py
    ├── test_method_caller.py
    ├── test_result_event_handler.py
    ├── test_serialize_data.py
    └── test_utils.py
```

---

## Test Commands

```bash
# All unit tests
python -m pytest tests/ -v

# With live OPC UA server
set OPCUA_TEST_ENDPOINT=opc.tcp://localhost:40451
python -m pytest tests/ -m live -v

# Install test deps first (if needed)
pip install pytest pytest-asyncio
```

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
  - Pass `--joint-id Joint_1` on command line (see `docs/methods-usage.md`)
  - Dynamically call `GetJointList` to discover real IDs before calling `GetJoint`/`SelectJoint`.

### Serialization (`serialize_data.py`)
- Shared serialization logic with IJT Web Client (`Python/serialize_data.py`).
- Converts `ua.ExtensionObject`, `ua.NodeId`, `ua.LocalizedText`, `datetime` → JSON-safe types.

---

## asyncua Known Issues (Python 3.14)

### `UaClient.call()` hardcoded 1-second timeout
Monkey-patch in tests:
```python
import asyncua.client.ua_client as _ua_client_mod
original_send = _ua_client_mod.UaClient._send_request
async def _patched_send(self, request, timeout=None, message_type=None):
    return await original_send(self, request, self._timeout, message_type)
_ua_client_mod.UaClient._send_request = _patched_send
```

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
| Event subscription | `event_handler.py` | `Python/event_handler.py` |
| Result processing | `result_event_handler.py` | `Python/result_event_handler.py` |
| Serialization | `serialize_data.py` | `Python/serialize_data.py` |
| Method calls | `method_caller.py` | `Python/ijt_interface.py` |
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
