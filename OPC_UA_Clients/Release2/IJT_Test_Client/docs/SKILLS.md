# IJT Test Client — Developer Reference

Full technical reference: [`opc-ua-server-context.md`](../../../../OPC_UA_Servers/Release2/docs/opc-ua-server-context.md)

---

## Running Tests

```bash
# Full suite — OPC UA server auto-launched if needed
python run_all_tests.py

# Always generate Excel report (non-fatal post-step)
python run_all_tests.py --excel=always

# Generate a reference workflow walkthrough for review/demo use
python scripts/run_reference_workflow.py --output test-results/reference-workflows/reference_joining_process_workflow.md
```

Use `run_all_tests.py` as the only test runner entry point.

See [`docs/test-results.md`](test-results.md) for report formats, skip/xfail explanations, and Excel output details.

Reference workflow walkthroughs are separate from conformance compliance
validation. They are driven by YAML under `reference_workflows/`, render
Markdown tables for review or Teams demos, and are not collected by default
Phase 2 runs.

`python run_all_tests.py` is the full orchestrator. Phase 1 runs static,
security, unit, type, and formatting checks. Phase 2 runs the live
server-facing compliance/conformance suite and defaults to `conformance` so
unit tests are not duplicated after Phase 1. Phase 2 appends helper coverage
diagnostics to `test-results/coverage-combined.xml` and disables only the live
coverage fail-under gate; the hard helper coverage gate belongs to the Phase 1
unit stage and is currently 95%.

### Report Output Behavior

- `run_all_tests.py` writes JUnit XML to `test-results/pytest-live.xml` by default (or `--junit-xml FILE`).
- Live CU compliance output is `test-results/cu-compliance-report.json`; unit-stage plugin output is redirected to `test-results/cu-compliance-report-unit.json` when CU-marked tests are collected.
- In each `by_cu` row, `outcome` is the raw execution rollup kept for compatibility; `compliance` is the conservative report status consumed by GitHub/Excel. New tooling should read `compliance`.
- The live CU compliance report includes workbook traceability for the checked-in Test Cases workbook: 1,122 expected TC header rows grouped by official CU, positive/negative classification, CTT/review/spec-link metadata, and optional exact row links from `@pytest.mark.workbook_ref("Sheet", [row])`.
- Unit-only and collect-only pytest sessions must not write or overwrite the live CU compliance report.
- Excel generation mode is controlled by `--excel {never,on-success,always}`.
- Local default is `on-success`; CI default is `always`.
- Excel output path defaults to `test-results/report.xlsx` and can be overridden with `--excel-out FILE`.
- Excel and GitHub Actions summaries include IJT high-level coverage views, facet, and CU coverage tables when the live CU compliance report is present; report wording separates `Active server declaration`, `Reference IJT facet`, `Reference full CU set`, `Declared by Server`, `Run Compliance`, and `Primary Reason` for public clarity.
- Missing phase1 tools are auto-installed locally by default; CI keeps auto-install off by default for reproducibility.
- Use `--no-auto-install-tools` to disable local auto-install, or `--auto-install-tools` to force-enable it.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPCUA_SERVER_URL` | raw pytest: `opc.tcp://localhost:40451`; runner auto-launch: `opc.tcp://localhost:40462` | OPC UA server endpoint URL |
| `OPCUA_SIMULATOR_EXE` | (none) | Path to simulator binary for auto-launch |
| `OPCUA_CAPABILITIES_FILE` | `server_capabilities.yaml` | Capability declaration for the server under test; auto-launched checked-in simulator uses `server_capabilities.simulator.yaml` when this is unset |
| `OPCUA_STARTUP_TIMEOUT_SEC` | `30` | Seconds to wait for server OPC UA readiness |
| `SKIP_VENV_INSTALL` | (none) | Set to `1` to skip pip install |

### Zero-Escape Testing Tools (Phase 1, auto-detected)

`ruff` (lint+format), `mypy` (types), `bandit` (security), `pip-audit` (CVE scan),
`semgrep` (static analysis), `pyright` (strict type checking — **advisory, non-blocking**), `detect-secrets` (secrets).
pip-audit uses the PyPI JSON endpoint preflight, local project cache, spinner disabled, and short timeouts; network/TLS/timeout outcomes are SKIP, not PASS/FAIL.
The runner refreshes `pip` before the requirements-hash fast path so stale bootstrap tooling does not create false CVE failures.
Pyright is configured in `pyproject.toml` to use `.venv_test` so installed project dependencies are resolved consistently during local runner checks.
`mypy` is blocking in local Phase 1 and uses the same command as CI:
`python -m mypy . --ignore-missing-imports --no-error-summary`. Its output is
written to `test-results/mypy.txt`, so strict type issues in conformance files
are caught before CI.

A **Python pytest suite** that validates an OPC UA server implementing the
[OPC UA Industrial Joining Technologies (IJT)](https://reference.opcfoundation.org/IJT/Base/v100/)
companion specifications against a live OPC UA IJT server.

Test areas: address space structure, asset management, result retrieval, event
subscriptions, joining process management, joint management, and conformance units
from the IJT specification.

---

## Critical Technical Requirements

| Rule | Detail |
|------|--------|
| **No `get_children()`** | Hangs on complex server nodes — use `_browse_refs()` from `helpers/node_discovery.py` |
| **Always `asyncio.wait_for`** | Every OPC UA call and browse must have a timeout (15–20 s) |
| **Namespace indices are runtime** | Never hardcode `ns=7` etc. — always resolve via `ns_indices[NS_IJT_BASE]` |
| **Multi-exception syntax** | Always write `except (A, B):` in this project; `except A, B:` is not allowed |
| **Simulate path** | SimulateSingleResult etc. live under `Simulations/SimulateResults/` — NOT under ResultManagement |
| **GetLatestResult needs Timeout** | Signature is `GetLatestResult(Timeout: Int32)` — pass `ua.Variant(5000, ua.VariantType.Int32)` |
| **include_traces = True** | All SimulateSingleResult calls should pass `True` for include_traces |
| **send_as_refs = True** | SimulateBatch_Or_Sync_Result and SimulateJobResult booleans should be `True` |
| **ResultState values** | Machinery Result NodeSet uses `1=Completed`, `2=Processing`, `3=Aborted`, `4=Failed`; do not use stale `1=Processing`, `2=Completed` mappings |
| **node.session not node.server** | asyncua 1.2+ renamed the attribute — use `node.session` |
| **Annotate empty accumulators** | `check_untyped_defs = true`; dynamic OPC UA lists such as `all_values = []` need explicit types, usually `list[Any]` |
| **Bandit `nosec` IDs only** | Keep `# nosec Bxxx` comments to valid Bandit IDs only; put explanations on a separate comment line to avoid `Test in comment` warnings |

---

## Server & Environment

```
Endpoint:       opc.tcp://localhost:40451   (override: OPCUA_SERVER_URL env var)
Binary:         OPC_UA_Servers/Release2/OPC_UA_IJT_Server_Simulator/opcua_ijt_demo_application.exe
Python:         3.14+  (test venv at .venv_test/)
Key packages:   asyncua>=1.2b2, PyYAML>=6.0, pytest>=9.0.2, pytest-asyncio>=1.3.0, pytest-timeout>=2.4.0
Run tests:      .venv_test/bin/python -m pytest -v          (Linux)
                .venv_test\Scripts\python -m pytest -v      (Windows)
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
    │   ├── GetResultById(ResultId: TrimmedString, Timeout: Int32)
    │   ├── GetResultIdListFiltered(...)            ← optional/profile-dependent; presence checked by Executable
    │   ├── ReleaseResultHandle(...)                ← optional/profile-dependent
    │   ├── AcknowledgeResults(...)                 ← optional/profile-dependent
    │   ├── RequestUnacknowledgedResults(...)       ← optional/profile-dependent
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
            ├── SimulateConditions(eventType:UInt32)      ← 1-60, raises retained condition
            └── SimulateBulkEvents(eventType:UInt32, count:UInt32)
```

Event and condition validation has two layers:
- `conformance/test_event_condition_catalog.py` walks every simulator id
  `1..60` by use-case category and verifies each id as a
  `JoiningSystemEventType` and as a retained `JoiningSystemConditionType`.
- `conformance/test_joining_system_condition_methods.py` samples standard OPC
  UA condition methods against received `JoiningSystemConditionType`
  notifications: Acknowledge, Confirm, AddComment, Enable/Disable, invalid
  EventId rejection, and ConditionRefresh.

Focused checks against a locally running Debug server:

```bash
python -m pytest conformance/test_event_condition_catalog.py conformance/test_joining_system_condition_methods.py -q
python -m pytest conformance/test_events.py events -q
```

---

## Test Suite Structure

```
IJT_Test_Client/
├── docs/SKILLS.md                ← developer reference for this sub-project
├── reference_workflows/          ← reference workflow YAML for demo/report lanes
├── conftest.py                   ← all pytest fixtures (session + function scoped)
├── pyproject.toml                ← asyncio_mode=auto, timeout=120, mypy check_untyped_defs=true (+ ruff, coverage, bandit); OPC UA test dirs have [[tool.mypy.overrides]] suppressing asyncua stub false-positives
├── helpers/
│   ├── namespaces.py             ← ALL type IDs and BrowseName constants
│   ├── cu_compliance_report.py   ← pytest plugin for CU/workbook compliance JSON
│   ├── method_signature.py       ← NodeSet-derived method InputArguments guards
│   ├── workbook_traceability.py  ← checked-in Test Cases workbook row metadata
│   ├── reference_workflow.py     ← reference workflow demo/report renderer helpers
│   ├── identifier_utils.py       ← shared identifier conformance helpers
│   ├── node_discovery.py         ← async browse helpers (_browse_refs, find_child_by_browse_name)
│   ├── event_collector.py        ← EventCollector for subscription tests
│   ├── result_collector.py       ← events-primary result delivery
│   ├── result_navigation.py      ← Variant unwrap + ResultContent traversal helpers
│   └── server_manager.py         ← auto-start simulator if not running
├── common/                       ← connection + namespace registration tests
├── assets/                       ← asset structure, interfaces, health, counters
├── results/                      ← result management structure + retrieval + simulation
│   └── data_types/               ← ResultMetaData field validation
├── events/                       ← event type hierarchy + simulation
│   └── data_types/
├── joining_process/              ← JoiningProcessManagement structure + methods
├── joint/                        ← JointManagement structure + methods
├── conformance/                  ← Conformance Unit tests (asset, result, event, joining process, joint)
├── scripts/run_reference_workflow.py ← Markdown + interactive reference workflow runner
├── tests/
    └── unit/                     ← Pure-logic helper tests (no OPC UA server needed)
        ├── conftest.py           ← SimpleNamespace fixtures for validator inputs
        ├── test_result_validator.py
        ├── test_event_validator.py
        ├── test_method_caller.py
        ├── test_result_collector.py  ← covers ResultCollector + unwrap_result / get_classification / is_partial
        ├── test_result_navigation.py
        ├── test_node_discovery.py
        ├── test_trigger.py
        ├── test_cu_registry.py
        ├── test_namespaces.py
        ├── test_cu_compliance_report.py
        ├── test_method_signature.py
        ├── test_workbook_traceability.py
        ├── test_profile_loader.py
        └── test_ruff_format_guard.py ← canary: ruff format must not corrupt except (A, B): clauses
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
| `opcua_client` | **module** | One connection shared across all tests in a file — avoids per-test OPC UA handshake overhead |
| `subscription_client` | **module** | Separate client for event subscriptions (module-scoped — one per file for result/event tests) |

> **Note**: `tests/unit/` fixtures use `SimpleNamespace` — no OPC UA connection required. All unit tests run offline and collect instantly.

---

## Core Design Patterns

### ResultCollector — events-primary result delivery
```python
from helpers.result_collector import ResultCollector

async with ResultCollector(client, ns_indices, is_simulator=True) as rc:
    # Trigger a result via SimulateSingleResult or external trigger
    await trigger(...)
    result = await rc.collect_single()      # SINGLE_RESULT (Classification=1)
    result = await rc.collect_combined(cls) # SYNC/BATCH/JOB/etc.
    result = await rc.collect_partial(cls)  # IsPartial=True result
    result = await rc.collect_job()         # JOB_RESULT
# result is None on timeout; test should skip in that case
```

Prefer this over `GetLatestResult`/`GetResultById` in conformance tests — events are the primary delivery path per the IJT specification.

### OpcUa_Uncertain — method call business-logic response
```python
# Uncertain is a VALID server response (IJT §7.4: business-logic failure, NOT transport failure).
# asyncua raises UaStatusCodeError for Uncertain — output arguments ARE readable.
# Always include "Uncertain" in skip-condition checks alongside Bad* variants:
except ua.UaError as exc:
    err_str = str(exc)
    if any(s in err_str for s in ("BadNotSupported", "BadNothingToDo", "BadArgumentsMissing", "Uncertain")):
        pytest.skip(f"Method returned {err_str} — skipping")
    pytest.fail(f"Unexpected error: {err_str}")
```

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

## When to Skip vs Fail

| Situation | What to do |
|-----------|-----------|
| Feature is optional and not present | `pytest.skip(...)` |
| Server behaves differently from spec (documented deviation) | `pytest.skip("known deviation: ...")` |
| Feature is mandatory and missing | `pytest.fail(...)` |
| Feature is present but returns wrong data | `assert ...` |
| Method call fails (not "absent" — method node found but call errored) | `pytest.fail(...)` — not skip |
| Method returns `OpcUa_Uncertain` (IJT §7.4 business-logic response) | `pytest.skip(...)` — Uncertain is a valid domain-level response; output args are readable |
| Timing race — GetLatestResult returns stale result (retry exhausted, real server) | `pytest.fail(...)` — real server must store triggered result within retry window |
| Timing race — retry exhausted on simulator (known limitation) | `return None` from helper → caller does `pytest.skip(...)` |

Skip reasons must name the actual missing capability or precondition. Avoid generic text like
`No condition event received` or `RequestResults raised ua.UaError`; include the event source,
method name, and actual exception/status so CI skip summaries are diagnostic.
Unsupported CU/optional-method skips should summarize as
`IJT <CU Name> - Method: <BrowseName> NOT SUPPORTED` when the CU maps to a
method, for example `IJT Send Joining Process - Method: SendJoiningProcess NOT SUPPORTED`.
Use `helpers.skip_reasons.skip_not_supported(...)`,
`skip_feature_not_supported(...)`, `skip_blocked(...)`,
`skip_accepted_policy(...)`, or `skip_environment(...)` instead of
hand-written generic text. JUnit summary normalization accepts direct
`Not Supported` messages for compatibility, but new skip sites should use the
helper APIs.
`JoiningSystemConditionType` Not Supported wording is reserved for servers or
packages that do not expose retained Acknowledgeable Conditions. It must not
imply that `JoiningSystemEventType` ConditionClass fields are unsupported. When
`SimulateConditions` is present, condition tests should use that trigger and
validate the received condition `NodeId` plus `EventId` method flow.

### GetLatestResult Return Convention
`GetLatestResult` returns **three** output arguments: `[ResultHandle: UInt32, Result: ResultDataType, Error: Int32]`.

- **Always use index 1**: `raw[1]` for the actual result data
- `raw[0]` is the integer handle — useless for data inspection
- `raw[2]` is the Error code (0 = success)
- Applies everywhere: `_trigger_and_get_result`, `_trigger_and_get_combined_result`, `_get_result_with_traces`

### Timing Race Retry Pattern
After triggering a result, GetLatestResult may return a stale result from a prior test.
Use a retry loop — do NOT skip immediately:

```python
_GLR_RETRY_MAX = 4
_GLR_RETRY_SLEEP_S = 2.0

for attempt in range(_GLR_RETRY_MAX):
    raw = await asyncio.wait_for(rm.call_method(...), timeout=...)
    result_data = raw[1] if isinstance(raw, (list, tuple)) and len(raw) > 1 else raw
    if result_data is not None and is_stale(result_data):
        if attempt < _GLR_RETRY_MAX - 1:
            await asyncio.sleep(_GLR_RETRY_SLEEP_S)
            continue
        # Retry exhausted — known simulator limitation (combined results not visible via GLR).
        # Return None so callers skip. For real servers the correct result appears within the window.
        logger.warning("GetLatestResult still returning stale result after %d retries — returning None", _GLR_RETRY_MAX)
        return None
    break
return result_data
```

All callers must guard: `if result_data is None: pytest.skip(...)`.

Use this retry pattern only in standalone GetLatestResult-specific tests in
`test_result_access.py`. Result conformance tests should prefer
`ResultCollector`.

---

## Custom Trigger Adapter (for Real Controllers)

For servers that cannot simulate their own results, implement a trigger adapter:

```python
# my_server/trigger.py
from helpers.trigger import ResultTrigger, TriggerOutcome, ResultType

class MyServerTrigger(ResultTrigger):
    async def trigger_single(self, result_type: ResultType, include_traces=False):
        await self._api.run_program(result_type.value)
        return TriggerOutcome(triggered=True, method="api.run_program")
```

Register it before running:

```bash
export OPCUA_TRIGGER_CLASS=my_server.trigger.MyServerTrigger
pytest conformance/
```

All tests call `result_trigger.trigger_single(...)` and skip gracefully if no trigger is available.

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
| ResultManagement, GetLatestResult, GetResultById, GetResultIdListFiltered, ReleaseResultHandle, Results | Machinery/Result | `NS_MACH_RESULT` |
| RequestResults, RequestUnacknowledgedResults | IJT Base | `NS_IJT_BASE` — ⚠️ exception: these two methods are defined in IJT Base NodeSet (ns=1;i=7074, ns=1;i=7092), NOT in Machinery/Result |
| RequestedResult variable | App | `NS_APP` — registered by server with `NAMESPACE_INDEX_TIGHTENING_SERVER` = `urn:AtlasCopco:IJT:Tightening:Server/` |
| SimulateSingleResult, Simulations, SimulateResults | App | `NS_APP` |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPCUA_SERVER_URL` | `opc.tcp://localhost:40451` | OPC UA server endpoint URL |
| `OPCUA_SIMULATOR_EXE` | (none) | Path to simulator binary for auto-launch |
| `OPCUA_STARTUP_TIMEOUT_SEC` | `30` | Seconds to wait for server OPC UA readiness |
| `SKIP_VENV_INSTALL` | (none) | Set to `1` to skip pip install on run_all_tests.py |


### Server Auto-Launch & Port Isolation

This client's test runner auto-launches a dedicated server instance on port **40462** (copy-and-patch
mechanism — copies the binary, patches `server_configuration.json`, and manages the full lifecycle).
Port 40451 is never used by this test runner.

For the full port assignment table, auto-launch mechanics, and venv rationale, see
[`docs/TEST_TIERS.md`](../../../../docs/TEST_TIERS.md).

---

## Writing New Conformance Tests

### Passing ProductInstanceUri to counter/method calls

Several IJT methods require a `ProductInstanceUri` (String) argument. Read it from the address space — do not hardcode it:

```python
from helpers.node_discovery import read_tool_product_instance_uri

ns_di = ns_indices.get(NS_DI)
ns_app = ns_indices.get(NS_APP)
pi_uri = await read_tool_product_instance_uri(opcua_client, ns_ijt, ns_di or 0, ns_app)
# pi_uri = "" when no tools configured — still a valid argument to pass
result = await call_method(jpm, method_node, ua.Variant(pi_uri, ua.VariantType.String), ...)
```

Do not reject a `ProductInstanceUri` only because it lacks an `urn:`, `http://`,
or `https://` scheme. Some conforming deployments use a manufacturer URI plus
an implementation-specific suffix. Test the value as a non-empty String when the
property is present, then pass the server's actual value to methods that require
it.

Methods that require PIU include Asset operation methods, Identifier methods,
I/O methods, JoiningProcess methods, and JointManagement methods. Result access
methods under Machinery/Result do not take PIU.

For Method Input Argument tests, keep the asset category applicable to the
method. Use a general AssetManagement method such as `GetIdentifiers` when
checking that the server's own Controller `ProductInstanceUri` is accepted.
Use Tool-specific methods such as `EnableAsset` only with a Tool PIU for
positive tests; calling `EnableAsset` with a valid Controller PIU belongs to
the non-applicable-asset negative case and must not be treated as a positive
server-own-asset check.

### EntityType Enum — v100 Values (CRITICAL)

The `EntityType` field in `EntityDataType` entries inside `AssociatedEntities[]` uses **v100 values (0–42)**. Old v1.01 values (PROGRAM=1, BATCH=3) are completely wrong.

| Value | Constant | Used for |
|-------|----------|---------|
| 26 | JOINING_PROCESS | Generic fallback — spec allows if no specific classification; **current OPC UA server does NOT use this value** |
| 27 | PROGRAM | Single Result JoiningProcessId (links to a Joining Program) |
| 28 | JOB | Job Result JoiningProcessId (links to a Joining Job) |
| 29 | BATCH | Batch Result JoiningProcessId (links to a Joining Batch) |

```python
_JOINING_PROCESS_ENTITY_TYPES = frozenset({26, 27, 28, 29})
_VALID_ENTITY_TYPES = set(range(43))  # 0..42 inclusive
```

### JoiningProcessId — Not a Direct Field

`JoiningProcessId` does **NOT** exist as a direct field on `JointDataType` or `ResultMetaDataType`.
It lives in `AssociatedEntities[i].EntityId` where `EntityType in {26, 27, 28, 29}`:

```python
joining_process_id = None
for ent in getattr(result_meta, "AssociatedEntities", []) or []:
    if getattr(ent, "EntityType", -1) in _JOINING_PROCESS_ENTITY_TYPES:
        joining_process_id = ent.EntityId
        break
```

### Variant Unwrap — ResultContent Items

`ResultDataType.ResultContent` is a `List[ua.Variant]`. Each element must be unwrapped before
accessing fields like `OverallResultValues`, `StepResults`, `Trace`:

```python
for jr in result_data.ResultContent or []:
    jr = getattr(jr, "Value", jr)   # unwrap ua.Variant wrapper
    # Now jr is JoiningResultDataType — access fields directly
    overall = getattr(jr, "OverallResultValues", []) or []
    trace = getattr(jr, "Trace", None)
```

Skipping this unwrap means all field accesses return `None` — the test silently passes but validates nothing.

**Nested Variant unwrap** — `asyncua` also wraps nested structures inside `ua.Variant`.
`EngineeringUnits` and all nested ExtensionObject list elements need the same treatment,
including `OverallResultValues`, `StepResults`, `StepResultValues`, `StepTraces`,
`StepTraceContent`, `ReportedValues`, `Errors`, `AssociatedEntities`, and `References`:

```python
eu = getattr(jr, "EngineeringUnits", None)
eu = getattr(eu, "Value", eu)          # unwrap nested Variant
unit_id = getattr(eu, "UnitId", None)

for v in getattr(jr, "OverallResultValues", []) or []:
    v = getattr(v, "Value", v)         # unwrap nested Variant
    tag = getattr(v, "ValueTag", None)

for step in getattr(jr, "StepResults", []) or []:
    step = getattr(step, "Value", step)  # unwrap nested Variant
    for sv in getattr(step, "StepResultValues", []) or []:
        sv = getattr(sv, "Value", sv)    # unwrap nested Variant

for error in getattr(jr, "Errors", []) or []:
    error = getattr(error, "Value", error)
```

Missing the nested unwrap causes field access to fail with `AttributeError`
on the `Variant` wrapper object. Apply this pattern at **every** nesting level.

### EUInformation Field Name — `.UnitId` not `.Identifier`

asyncua's `EUInformation` type exposes `UnitId` (Int32), NOT `Identifier`.
All EU validation code must use `eu.UnitId` or `getattr(eu, "UnitId", None)`.

### Identifier Methods — Prefer `SendIdentifiers`

`SendIdentifiers` is the primary/recommended identifier method. It takes:

```
SendIdentifiers(ProductInstanceUri: String, EntityList: EntityDataType[])
```

Use structured `EntityDataType` entries for new positive coverage. Test IDs should be unique
and asserted exactly through `GetIdentifiers` or result `AssociatedEntities`. For persistence
checks, read and pass a real Tool `ProductInstanceUri` with `read_tool_product_instance_uri()`;
an empty PIU is accepted by the simulator but intentionally stores nothing, so it must not be
used when asserting identifier propagation.

Default structured identifier test data should model a VIN, the common joining-domain
external identifier: `Name="VIN"`, `Description="Vehicle Identification Number"`,
`EntityType=VEHICLE (20)`, `IsExternal=True`, `EntityId=<actual VIN value>`, and an empty
`EntityOriginId`. Use `helpers.identifier_utils.make_test_vin()` for unique VIN-like values.

`SendTextIdentifiers` is the legacy compatibility path. Keep coverage for it, but do not replace
`SendIdentifiers` coverage with text-only tests.

`ResetIdentifiers` has a required 4-argument signature:

```
ResetIdentifiers(ProductInstanceUri: String, IdentifierList: String[], ResetAll: Boolean, ResetLatest: Boolean)
```

Pass `IdentifierList` as a string array, not an `ExtensionObject` array.

### ResultManagement → Results Folder Structure

```
ResultManagement
├── Results/              (folder)
│   ├── Result            (variable — live/latest result, updated on every tightening)
│   └── RequestedResult   (variable — stored/historical, updated only by RequestResults)
├── GetLatestResult       (method)
├── GetResultById         (method)
├── RequestResults        (method — IJT Base)
└── ...
```

Both `Result` and `RequestedResult` carry the same `ResultDataType` payload.
The difference: `Result` reflects the live tightening outcome; `RequestedResult`
is populated only when `RequestResults` or `RequestUnacknowledgedResults` is called
(stored/historical lookup). The corresponding event is `RequestedResultEventType`.

### Result Access Method Signatures (Machinery/Result spec — NO ProductInstanceUri)

```
GetLatestResult(Timeout: Int32) → [ResultHandle: UInt32, Result: ResultDataType, Error: Int32]
GetResultById(ResultId: TrimmedString, Timeout: Int32) → [ResultHandle: UInt32, Result: ResultDataType, Error: Int32]
GetResultIdListFiltered(Filter: ContentFilter, OrderedBy: RelativePath[], MaxResults: UInt32, Timeout: Int32) → [ResultHandle: UInt32, ResultIdList: TrimmedString[], Error: Int32]
```

There is no generic `GetResult` method in the current model. These result access
methods come from **Machinery/Result** (NS_MACH_RESULT), NOT from IJT Base. They
have **no ProductInstanceUri argument**.
`RequestResults` and `RequestUnacknowledgedResults` come from IJT Base (NS_IJT_BASE) and have different signatures:

```
RequestResults(
  FromSequenceNumber: UInt64,
  ToSequenceNumber: UInt64,
  FromTime: DateTime,
  ToTime: DateTime,
  RequestedMinimumDurationBetweenResults: Duration,
) → [RevisedMinimumDurationBetweenResults: Duration, Status: Int64, StatusMessage: LocalizedText]

RequestUnacknowledgedResults(
  MaxResults: UInt32,
  RequestedMinimumDurationBetweenResults: Duration,
) → [RevisedMinimumDurationBetweenResults: Duration, UnacknowledgedResultCount: UInt32, Status: Int64, StatusMessage: LocalizedText]
```
