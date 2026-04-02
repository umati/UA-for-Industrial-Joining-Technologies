# IJT Test Client

## Contact
- **Author:** Mohit Agarwal: mohit.agarwal@atlascopco.com

## Overview

A self-contained Python pytest suite that validates an OPC UA IJT server against the
**OPC UA Industrial Joining Technologies (IJT) Companion Specification**.

Two complementary test layers:

| Layer | Folder | Purpose |
|-------|--------|---------|
| Functional | `common/`, `assets/`, `results/`, `events/`, `joining_process/`, `joint/` | Is every node, method, and event correct? |
| Conformance | `conformance/` | Does the server satisfy §11.1 Conformance Units? |

All tests are live — they connect to a running OPC UA IJT server.  
Tests auto-skip gracefully when optional nodes or namespaces are absent.

## Prerequisites

- **Python 3.14 or higher** — add to system `PATH`
- A running **OPC UA IJT Server** — see [OPC UA IJT Server Simulator](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2)
- Default server endpoint: `opc.tcp://localhost:40451`

No manual dependency installation needed — `run_tests.py` creates a virtual environment automatically.

## Quick Start

```bash
# Run all tests (creates .venv on first run)
python run_tests.py

# Verbose output
python run_tests.py -v

# Conformance units only (§11.1)
python run_tests.py -m conformance -v

# Address space structure tests only
python run_tests.py -m structure -v

# Method call tests only
python run_tests.py -m methods -v

# Filter by name
python run_tests.py -k "result_management"

# List all collected tests without running
python run_tests.py --co -q

# Skip venv reinstall on re-runs (faster)
SKIP_VENV_INSTALL=1 python run_tests.py        # Linux / macOS
set SKIP_VENV_INSTALL=1 && python run_tests.py  # Windows
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPCUA_SERVER_URL` | `opc.tcp://localhost:40451` | OPC UA server endpoint |
| `OPCUA_SIMULATOR_EXE` | auto-detected | Path to `opcua_ijt_demo_application` binary |
| `OPCUA_STARTUP_TIMEOUT_SEC` | `10` | Seconds to wait for simulator to start |
| `SKIP_VENV_INSTALL` | — | Set to `1` to skip `pip install` on re-runs |

## Test Structure

```
IJT_Test_Client/
├── run_tests.py                        # Entry point — python run_tests.py
├── conftest.py                         # All shared pytest fixtures
├── pytest.ini                          # asyncio_mode=auto, markers, timeout
├── requirements.txt                    # asyncua, pytest, pytest-asyncio
│
├── helpers/
│   ├── namespaces.py                   # NS URIs, BN, IJTTypes, ResultType constants
│   ├── node_discovery.py               # find_joining_system, browse_folder_instances
│   ├── event_collector.py              # EventCollector async context manager
│   └── server_manager.py              # Auto-start simulator for local testing
│
├── common/
│   ├── test_server_connection.py       # Connect, read server time, load type defs
│   └── test_namespace_registration.py # All companion spec namespaces registered
│
├── assets/
│   ├── test_asset_management_structure.py   # AssetManagement AddIn, folder tree
│   ├── test_asset_identification.py         # Identification node, mandatory fields
│   ├── test_asset_interfaces.py             # HasInterface references per asset type
│   ├── test_asset_health.py                 # Health node, DeviceHealth variable
│   ├── test_asset_operation_counters.py     # OperationCounters, cycle counter
│   ├── test_asset_associations.py           # AssociatedWith references
│   └── data_types/
│       └── test_calibration_data_type.py    # CalibrationDataType structure
│
├── results/
│   ├── test_result_management_structure.py  # ResultManagement AddIn, Results folder
│   ├── test_simulate_results.py             # SimulateSingleResult, Batch, Job
│   ├── test_result_retrieval.py             # GetLatestResult, GetResultById
│   ├── test_result_events.py                # JoiningSystemResultReadyEventType
│   └── data_types/
│       └── test_result_data_types.py        # ResultMetaData, ResultValue fields
│
├── events/
│   ├── test_event_types_structure.py        # Event type node hierarchy
│   ├── test_joining_system_events.py        # Subscribe + receive live events
│   └── data_types/
│       └── test_event_data_types.py         # Event field content types
│
├── joining_process/
│   ├── test_joining_process_structure.py    # JoiningProcessManagement AddIn + methods
│   └── test_joining_process_methods.py      # SelectJoiningProcess, counters
│
├── joint/
│   ├── test_joint_management_structure.py   # JointManagement AddIn + methods
│   └── test_joint_management_methods.py     # GetJoint, GetJointList, SendJoint
│
└── conformance/                             # §11.1 Conformance Units
    ├── test_cu_asset_management.py          # CU-AM-001 … CU-AM-010
    ├── test_cu_result_management.py         # CU-RM-001 … CU-RM-010
    ├── test_cu_event_management.py          # CU-EM-001 … CU-EM-005
    ├── test_cu_joining_process.py           # CU-JP-001 … CU-JP-004
    └── test_cu_joint_management.py          # CU-JT-001 … CU-JT-004
```

## Pytest Markers

| Marker | Meaning |
|--------|---------|
| `live` | Requires a running OPC UA server |
| `structure` | Read-only address space checks (no server state changes) |
| `methods` | Calls OPC UA methods (triggers simulation) |
| `events` | Subscribes to OPC UA events |
| `conformance` | §11.1 Conformance Unit tests |

## Conformance Units Covered

| File | Spec Reference | What Is Verified |
|------|---------------|-----------------|
| `test_cu_asset_management.py` | §11.1 CU-AM-001…010 | JoiningSystem instance, AssetManagement AddIn, all asset folders, controller/tool interfaces, Identification, Health, OperationCounters, AssociatedWith, AssetId |
| `test_cu_result_management.py` | §11.1 CU-RM-001…010 | ResultManagement AddIn, Results folder, GetLatestResult, GetResultById, ResultMetaData, ResultContent, AcknowledgeResults, ResultReadyEvent, ResultEvaluation/Classification values |
| `test_cu_event_management.py` | §11.1 CU-EM-001…005 | Event type hierarchy, subscription support, mandatory OPC UA base fields, IJT-specific fields, event timestamp freshness |
| `test_cu_joining_process.py` | §11.1 CU-JP-001…004 | JoiningProcessManagement AddIn, required methods, EnableAsset/DisableAsset, AbortJoiningProcess |
| `test_cu_joint_management.py` | §11.1 CU-JT-001…004 | JointManagement AddIn, required methods, GetJointList, JointDataType structure |
