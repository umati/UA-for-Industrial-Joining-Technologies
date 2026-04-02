# Development Log

Chronological record of significant changes to the IJT_Test_Client test suite.

Format: `## YYYY-MM — Short title`

---

## 2026-04 — Test framework hardening

### Context
Comprehensive review of the Python pytest test suite against a live OPC UA IJT server.
Multiple root causes of test failure and hanging were identified and fixed.

---

### Python Test Suite — Root Causes Fixed

#### 1. `get_children()` hangs on complex nodes
**Problem**: `asyncua`'s `get_children()` hangs indefinitely on `ResultManagement`
and other nodes that expose many references. This caused the entire test session to block.

**Fix**: Replaced every `get_children()` call with a `_browse_refs()` helper function
using `get_references(refs=ua.NodeId(33,0), ...)` (HierarchicalReferences) wrapped in
`asyncio.wait_for(timeout=15)`.

Files changed: `helpers/node_discovery.py` (full rewrite), all test files that called `get_children()`.

#### 2. Wrong path to simulate methods
**Problem**: Tests called simulate methods under `ResultManagement`, but the methods
live under `Simulations/SimulateResults/` (App namespace, ns=1).

**Fix**: Added `simulations_node`, `simulate_results_folder`, `simulate_events_folder`
session fixtures in `conftest.py`; all test files updated to use these fixtures.

BrowseName constants added to `helpers/namespaces.py`:
`BN.SIMULATIONS`, `BN.SIMULATE_RESULTS_FOLDER`, `BN.SIMULATE_EVENTS_AND_CONDITIONS`,
`BN.SIMULATE_EVENTS`, `BN.SIMULATE_BULK_EVENTS`, `BN.SIMULATE_BULK_RESULTS`

#### 3. Wrong simulate method names
**Problem**: Tests referenced `SimulateBatchOrSyncResult` (camelCase) but live server
exposes `SimulateBatch_Or_Sync_Result` (underscores).

**Fix**: `BN.SIMULATE_BATCH_OR_SYNC_RESULT = "SimulateBatch_Or_Sync_Result"` in `namespaces.py`.

#### 4. `GetLatestResult` missing required Timeout argument
**Problem**: Calling `GetLatestResult()` with no arguments returned `BadArgumentsMissing`.

**Fix**: All call sites now pass `ua.Variant(5000, ua.VariantType.Int32)` as the Timeout argument.

#### 5. Wrong argument types in simulate method calls
**Problem**: `SimulateJobResult` was called with 2 arguments; actual signature has exactly 1.
`SimulateBulkResults` sequence numbers were passed as `Int32`; server expects `UInt64`.
`SimulateBulkResults` duration was passed as `Int32`; server expects `Int64`.

**Fix**: All simulate calls rewritten with types verified from live server `InputArguments`:
- `SimulateJobResult`: exactly 1 `Boolean` argument (`sendAsRefs`)
- `SimulateBulkResults`: `UInt64` for `fromSeq`/`toSeq`, `Int64` for `minDurationMs`
- All boolean "send as refs" and "include traces" arguments set to `True` (recommended)

#### 6. `node.server` used for namespace index resolution
**Problem**: `node.server.get_namespace_index()` calls the internal `UaClient`, not
the outer `Client` — raises `AttributeError` at runtime.

**Fix**: All namespace index lookups go via `client.get_namespace_index()` on the outer client,
cached in session-scoped fixtures.

---

### New Tests Created

#### `events/test_simulate_events.py`
Tests `SimulateEvents` and `SimulateBulkEvents` methods:
- Single-event trigger with subscription verification (per representative event type)
- Bulk event trigger with count ≥ N verification
- Parametrized over 9 representative categories from `SimulateEventType.REPRESENTATIVE`

---

### Known Issues — Outstanding

| ID | Description |
|----|-------------|
| STUB-001 | `GetResultIdListFiltered` — server returns not-implemented |
| STUB-002 | `ReleaseResultHandle` — server returns not-implemented |

---

### Test Run Status

| Suite | Result |
|-------|--------|
| `common/` | ✅ passing |
| `assets/` | ✅ passing |
| `joining_process/` | ✅ passing |
| `joint/` | ✅ passing |
| `results/` | 🔲 in progress |
| `events/` | 🔲 in progress |
| `conformance/` | 🔲 pending |

```sh
.venv/bin/python -m pytest -v --tb=short   # Linux
.venv\Scripts\python -m pytest -v --tb=short  # Windows
```
