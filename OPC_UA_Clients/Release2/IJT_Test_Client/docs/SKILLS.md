# IJT_Test_Client — AI Agent Context

This file is the primary entry point for any AI assistant (GitHub Copilot, Claude,
ChatGPT/GPT-4o, etc.) working on this project. Read it before making any changes.
Full technical reference: [`opc-ua-server-context.md`](opc-ua-server-context.md)

---

## Running Tests

```bash
# Full suite — OPC UA server auto-launched if needed
python run_all_tests.py
```

Note: `run_tests.py` was merged into `run_all_tests.py` and deleted. Use `run_all_tests.py` only.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPCUA_SERVER_URL` | `opc.tcp://localhost:40451` | OPC UA server endpoint URL |
| `OPCUA_SIMULATOR_EXE` | (none) | Path to simulator binary for auto-launch |
| `OPCUA_STARTUP_TIMEOUT_SEC` | `30` | Seconds to wait for server OPC UA readiness |
| `SKIP_VENV_INSTALL` | (none) | Set to `1` to skip pip install |

### Zero-Escape Testing Tools (Phase 1, auto-detected)

`ruff` (lint+format), `mypy` (types), `bandit` (security), `pip-audit` (CVE scan),
`vulture` (dead code), `semgrep` (AI rules), `pyright` (AI types), `detect-secrets` (secrets).

A **Python pytest suite** that validates an OPC UA server implementing the
[OPC UA Industrial Joining Technologies (IJT)](https://reference.opcfoundation.org/IJT/Base/v100/)
companion specifications against a live OPC UA IJT server.

Test areas: address space structure, asset management, result retrieval, event
subscriptions, joining process management, joint management, and conformance units
from the IJT specification.

---

## Absolute Rules (Never Violate)

| Rule | Detail |
|------|--------|
| **No git commits** | Never run `git commit`, `git push`, or `git add` unless user explicitly requests |
| **No `get_children()`** | Hangs on complex server nodes — use `_browse_refs()` from `helpers/node_discovery.py` |
| **Always `asyncio.wait_for`** | Every OPC UA call and browse must have a timeout (15–20 s) |
| **Namespace indices are runtime** | Never hardcode `ns=7` etc. — always resolve via `ns_indices[NS_IJT_BASE]` |
| **Simulate path** | SimulateSingleResult etc. live under `Simulations/SimulateResults/` — NOT under ResultManagement |
| **GetLatestResult needs Timeout** | Signature is `GetLatestResult(Timeout: Int32)` — pass `ua.Variant(5000, ua.VariantType.Int32)` |
| **include_traces = True** | All SimulateSingleResult calls should pass `True` for include_traces |
| **send_as_refs = True** | SimulateBatch_Or_Sync_Result and SimulateJobResult booleans should be `True` |
| **node.session not node.server** | asyncua 1.2+ renamed the attribute — use `node.session` |

---

## Server & Environment

```
Endpoint:       opc.tcp://localhost:40451   (override: OPCUA_SERVER_URL env var)
Binary:         OPC_UA_Servers/Release2/OPC_UA_IJT_Server_Simulator/opcua_ijt_demo_application.exe
Python:         3.14+  (venv at .venv/)
Key packages:   asyncua>=1.2b2, pytest>=9.0.2, pytest-asyncio>=1.3.0, pytest-timeout>=2.4.0
Run tests:      .venv/bin/python -m pytest -v          (Linux)
                .venv\Scripts\python -m pytest -v      (Windows)
Auto-launch:    set OPCUA_SIMULATOR_EXE=<path>  to auto-start server if not running
```

Namespace indices resolve dynamically — always use the URI constants in `helpers/namespaces.py`:
```
NS_OPC_UA           http://opcfoundation.org/UA/
NS_DI               http://opcfoundation.org/UA/DI/
NS_AMB              http://opcfoundation.org/UA/AMB/
NS_IA               http://opcfoundation.org/UA/IA/
NS_MACHINERY        http://opcfoundation.org/UA/Machinery/
NS_MACH_RESULT      http://opcfoundation.org/UA/Machinery/Result/
NS_IJT_BASE         http://opcfoundation.org/UA/IJT/Base/
NS_IJT_TIGHTENING   http://opcfoundation.org/UA/IJT/Tightening/
NS_APP              urn of the server application namespace (simulator-specific)
```

---

## Address Space Navigation Map

```
Objects/
└── TighteningSystem  (JoiningSystemType, IJT Base ns i=1005)
    ├── Identification          (DI ns)
    ├── AssetManagement         (IJT Base ns)
    │   └── Assets/
    │       ├── Controllers/, Tools/, Batteries/, Servos/, Sensors/
    │       ├── PowerSupplies/, Cables/, Feeders/, MemoryDevices/
    │       ├── Accessories/, SubComponents/, SoftwareComponents/, VirtualStations/
    ├── ResultManagement        (Machinery/Result ns)
    │   ├── Results/
    │   ├── GetLatestResult(Timeout: Int32)        ← Timeout is REQUIRED
    │   ├── GetResultById(ResultId: String)
    │   ├── GetResultIdListFiltered(...)
    │   ├── ReleaseResultHandle(...)
    │   └── RequestResults(...)
    ├── JoiningProcessManagement (IJT Base ns)
    ├── JointManagement          (IJT Base ns)
    └── Simulations              (App ns)           ← ALL simulate methods here
        ├── SimulateResults/
        │   ├── SimulateSingleResult(type:UInt32, includeTraces:Boolean)
        │   ├── SimulateBatch_Or_Sync_Result(class:Byte, numChildren:UInt32,
        │   │                                includeTraces:Boolean, sendAsRefs:Boolean)
        │   ├── SimulateJobResult(sendAsRefs:Boolean)    ← only 1 argument
        │   ├── SimulateBulkResults(type:UInt32, includeTraces:Boolean,
        │   │                       from:UInt64, to:UInt64, minMs:Int64, updateVars:Boolean)
        │   └── SendSimulatedBulkResults(...)
        └── SimulateEventsAndConditions/
            ├── SimulateEvents(eventType:UInt32)          ← 1-60, fires 1 event
            └── SimulateBulkEvents(eventType:UInt32, count:UInt32)
```

---

## Test Suite Structure

```
IJT_Test_Client/
├── AGENTS.md                     ← you are here
├── docs/opc-ua-server-context.md ← full technical OPC UA reference
├── conftest.py                   ← all pytest fixtures (session + function scoped)
├── pytest.ini                    ← asyncio_mode=auto, timeout=120
├── helpers/
│   ├── namespaces.py             ← ALL type IDs and BrowseName constants
│   ├── node_discovery.py         ← async browse helpers (_browse_refs, find_child_by_browse_name)
│   ├── event_collector.py        ← EventCollector for subscription tests
│   └── server_manager.py         ← auto-start simulator if not running
├── common/                       ← connection + namespace registration tests
├── assets/                       ← asset structure, interfaces, health, counters
├── results/                      ← result management structure + retrieval + simulation
│   └── data_types/               ← ResultMetaData field validation
├── events/                       ← event type hierarchy + simulation
│   └── data_types/
├── joining_process/              ← JoiningProcessManagement structure + methods
├── joint/                        ← JointManagement structure + methods
└── conformance/                  ← §11.1 Conformance Unit tests (CU-AM, CU-RM, CU-EM, CU-JP, CU-JT)
```

### Key Fixtures (conftest.py)
| Fixture | Scope | Description |
|---------|-------|-------------|
| `managed_server` | session | Ensures server is running (auto-launch or skip) |
| `session_client` | session | Read-only shared asyncua Client |
| `ns_indices` | session | Dict of URI → runtime namespace index |
| `joining_system` | session | JoiningSystem node (found by TypeDefinition) |
| `result_management` | session | ResultManagement AddIn |
| `simulate_results_folder` | session | `Simulations/SimulateResults/` node |
| `simulate_events_folder` | session | `Simulations/SimulateEventsAndConditions/` node |
| `opcua_client` | **function** | Fresh client for method calls (state-changing) |
| `subscription_client` | **function** | Separate client for event subscriptions |

---

## Core Design Patterns

### Safe browsing (always use — never `get_children()`)
```python
from helpers.node_discovery import _browse_refs, _node_from_ref, find_child_by_browse_name

refs = await _browse_refs(node, timeout=15.0)          # list of ReferenceDescription
child = await find_child_by_browse_name(node, "Name", ns_index)
```

### Method call with timeout
```python
result = await asyncio.wait_for(
    node.call_method(method.nodeid, ua.Variant(5000, ua.VariantType.Int32)),
    timeout=15,
)
```

### Triggering a simulation (correct path)
```python
sf = opcua_client.get_node(simulate_results_folder.nodeid)
method = await find_child_by_browse_name(sf, BN.SIMULATE_SINGLE_RESULT, ns_app)
await asyncio.wait_for(
    sf.call_method(
        method.nodeid,
        ua.Variant(ResultType.ONE_STEP_OK_RESULT, ua.VariantType.UInt32),
        ua.Variant(True, ua.VariantType.Boolean),   # include_traces = True
    ),
    timeout=15,
)
```

### Event subscription (two-client rule)
```python
# Always use separate clients: subscription_client receives, opcua_client triggers
async with EventCollector(subscription_client) as collector:
    await collector.subscribe(subscription_client.nodes.server, [event_type_node])
    await _call(opcua_client_node, method, ...)
    events = await collector.collect(count=1, timeout_s=20.0)
assert len(events) >= 1
```

---

## Interface Placement Rules (from NodeSet files)

| Node | Interface | Namespace | Local ID |
|------|-----------|-----------|----------|
| Asset instance | `IControllerType` / `IToolType` / etc. | IJT Base | 1003–1031 |
| Asset instance | `IJoiningSystemAssetType` (base) | IJT Base | 1002 |
| **Identification** | `IJoiningAdditionalInformationType` | IJT Base | **1017** |
| **Tool/Parameters** | `ITighteningToolParametersType` | IJT Tightening | **1003** |
| Other Parameters | *(no additional interface)* | — | — |

---

## BrowseName → Defining Namespace Quick Reference

| BrowseName | Defining NS | Constant |
|-----------|-------------|---------|
| Identification, MethodSet, OperationCounters | DI | `NS_DI` |
| AssetId, ComponentName, Location | AMB | `NS_AMB` |
| LifetimeCounters, MachineryBuildingBlocks | Machinery | `NS_MACHINERY` |
| Health, Parameters, AssetManagement, Assets | IJT Base | `NS_IJT_BASE` |
| ResultManagement, GetLatestResult, Results | Machinery/Result | `NS_MACH_RESULT` |
| SimulateSingleResult, Simulations, SimulateResults | App | `NS_APP` |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPCUA_SERVER_URL` | `opc.tcp://localhost:40451` | OPC UA server endpoint URL |
| `OPCUA_SIMULATOR_EXE` | (none) | Path to simulator binary for auto-launch |
| `OPCUA_STARTUP_TIMEOUT_SEC` | `30` | Seconds to wait for server OPC UA readiness |
| `SKIP_VENV_INSTALL` | (none) | Set to `1` to skip pip install on run_all_tests.py |

