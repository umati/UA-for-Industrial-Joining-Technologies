# Target Server CU Guide

> **Canonical entry point:** `python run_all_tests.py` (see options below).
> The simulator and a Target Server are both "OPC UA Servers Under Test" running
> the identical `specification_tests/` suite; a profile only controls
> applicability, safety, triggers, scoring, and evidence — never a separate
> test suite. Default (no flags) runs everything; `--phase2` runs
> specification_tests only; `--profile` controls Target Server execution.

---

## 1) Overview & Architecture

### What this is in simple words
The **IJT Test Client** verifies whether an OPC UA IJT Server adheres to the OPC 40450-1 specification correctly.
It does **not** replace a simulator — it provides formal, repeatable conformance testing.

- **Simulator** = functional behavior and reference implementation testing
- **IJT Test Client** = formal specification Conformance Unit (CU) testing

### What "123 CUs" means
- The project is built around **123 official IJT Conformance Units (CUs)** defined in OPC UA IJT Release 2.0.
- The test framework and CU reporting classify each CU (e.g. `Supported/Pass`, `Not Supported`, `Blocked`, `Failed`, `Environment/Error`) on every run.
- Goal: **All applicable CUs executed and clearly classified** on every run.

### Test suite organization
The test structure mirrors the specification chapters:
- `specification_tests/` = main specification test suite container
- Domain chapters = `results/`, `assets/`, `joining_process/`, `joint/`, `events/`, `common/`

---

## 2) Auto-discover Tools and Processes

Before writing or editing a profile, connect to the target server to automatically discover its Tool `ProductInstanceUri`, available Joining Processes, and generate a recommended YAML snippet:

```bash
python run_all_tests.py --endpoint opc.tcp://<controller-host>:40451 --discover-target
```

---

## 3) Profiles & Setup Recipes

### Available profile catalog:
- **Automated controller workflow:** `target_server_cu_profiles/example_multi_operation_job.profile.yaml`
- **Manual trigger workflow:** `target_server_cu_profiles/example_manual_trigger.profile.yaml`
- **Simulator helper methods:** `target_server_cu_profiles/example_simulation_methods.profile.yaml`
- **Universal template:** `target_server_cu_profiles/template.profile.yaml`

### Prepare a real controller profile

If the controller matches the supplied capability baseline, use the committed generic pair directly and pass installation values at runtime:

**Windows (PowerShell):**
```powershell
python run_all_tests.py `
  --profile target_server_cu_profiles/example_multi_operation_job.profile.yaml `
  --endpoint opc.tcp://<controller-host>:40451 `
  --joining-process-id <joining-process-id> `
  --joining-process-origin-id <joining-process-origin-id> `
  --preflight-only
```

**Linux / macOS (Bash / Zsh):**
```bash
python run_all_tests.py \
  --profile target_server_cu_profiles/example_multi_operation_job.profile.yaml \
  --endpoint opc.tcp://<controller-host>:40451 \
  --joining-process-id <joining-process-id> \
  --joining-process-origin-id <joining-process-origin-id> \
  --preflight-only
```

Optional runtime overrides are also available through environment variables:
`OPCUA_SERVER_URL`, `OPCUA_TOOL_PRODUCT_INSTANCE_URI`, `OPCUA_JOINING_PROCESS_ID`, `OPCUA_JOINING_PROCESS_ORIGIN_ID`, and `OPCUA_CAPABILITIES_FILE`.

### Creating local paired files

Create local paired files only when the controller's workflow or supported CUs differ from the complete example:

**Windows (PowerShell):**
```powershell
Copy-Item target_server_cu_profiles/example_multi_operation_job.profile.yaml `
  target_server_cu_profiles/my_controller.profile.yaml
Copy-Item target_server_cu_profiles/example_multi_operation_job.capabilities.yaml `
  target_server_cu_profiles/my_controller.capabilities.yaml
```

**Linux / macOS (Bash / Zsh):**
```bash
cp target_server_cu_profiles/example_multi_operation_job.profile.yaml \
   target_server_cu_profiles/my_controller.profile.yaml
cp target_server_cu_profiles/example_multi_operation_job.capabilities.yaml \
   target_server_cu_profiles/my_controller.capabilities.yaml
```

Then update `my_controller.profile.yaml`:

| Setting | What to enter |
|---|---|
| `capabilities_file` | `"my_controller.capabilities.yaml"` |
| `target.endpoint` | Real `opc.tcp://host:port` endpoint |
| `selection.tool.product_instance_uri` | Leave empty for runtime Tool discovery; otherwise enter the Tool PIU |
| `selection.joining_process.joining_process_id` | Default/fallback Process ID returned by `GetJoiningProcessList` |
| `selection.joining_process.joining_process_origin_id` | Stable origin fallback if the controller regenerates the primary ID |
| `selection.joining_process.selection_name` | Final fallback when neither configured ID is advertised |
| `selection.joining_processes.<classification>` | Optional per-classification selectors (`single`, `job`, `batch`, `sync`) |
| `state_changing_methods.allowed_methods` | Safety authorization only: methods approved for this run; it does not enable CUs or create tests |
| `extension_fields.enable_asset_policy` | `when_disabled`, or `always` when safe enablement must be reasserted |
| `workflow_execution.expected_operation_count` | Starts needed to complete the selected JoiningProcess |
| `expected_results.classification` | Final result layer, such as `single`, `batch`, or `job` |
| `expected_results.intermediate_classifications` | Earlier layers, such as `[single, batch, intervention]` |
| `triggers.result.mode` | `start_selected_joining`, `manual_trigger`, `observe_only`, or `none` |

Update `my_controller.capabilities.yaml` with the controller's actual `active_profile`, `supported_facets`, and `cu_overrides`.

---

## 4) Run Commands

- **Safe preflight check:**
  ```bash
  python run_all_tests.py --preflight-only --profile target_server_cu_profiles/my_controller.profile.yaml
  ```
- **Classification without invoking specification tests:**
  ```bash
  python run_all_tests.py --profile target_server_cu_profiles/my_controller.profile.yaml --skip-spec-tests
  ```
- **Full validation (Phase 1 + preflight + specs + evidence):**
  ```bash
  python run_all_tests.py --profile target_server_cu_profiles/my_controller.profile.yaml --spec-tests-timeout 3600 --output-dir test-results/target-server-cu/my-controller
  ```
- **Preflight + specs + evidence only (skipping Phase 1):**
  ```bash
  python run_all_tests.py --phase2 --profile target_server_cu_profiles/my_controller.profile.yaml --spec-tests-timeout 3600 --output-dir test-results/target-server-cu/my-controller
  ```
- **Guided / manual run with interactive prompts:**
  ```bash
  python run_all_tests.py --phase2 --profile target_server_cu_profiles/my_controller.profile.yaml --mode guided --interactive-prompts --output-dir test-results/target-server-cu/my-controller-guided
  ```

---

## 5) Output Artifacts

Every Target Server run generates structured evidence artifacts in the output directory (default: `test-results/target-server-cu/`):

- `target-server-cu-report.json` — machine-readable JSON evidence report with check details
- `target-server-cu-summary.txt` — human-readable ASCII summary for console inspection
- `target-server-cu-summary.md` — GitHub-compatible Markdown summary table
- `spec-tests.xml` — standard JUnit XML report for CI/CD integration
- `cu-coverage-report.json` — run-scoped 123-CU classification report
- `report-controller.xlsx` — automatically generated Excel traceability workbook

---

## 6) Domain Semantics, Process Selection, and Safety Rules

### Generic JoiningProcess abstraction
The IJT information model uses `JoiningProcess` as the generic process abstraction. A controller can use it for a program, batch, job, sequence, application recipe, or another technology-specific process. Shared test client logic never encodes vendor-specific vocabulary.

### Process Selection Precedence
When selecting a process, the runner evaluates selectors in this deterministic order:
1. `JoiningProcessId` (primary selector from `GetJoiningProcessList`)
2. `JoiningProcessOriginId` (stable fallback when a controller regenerates primary IDs)
3. `SelectionName` (optional server-specific fallback)

For workflows exercising both single tightening programs (for SingleResult) and multi-operation Jobs/Batches:
```yaml
selection:
  joining_processes:
    single:
      policy: exact_match
      joining_process_id: "<program-id>"
    job:
      policy: exact_match
      joining_process_id: "<job-id>"
    batch:
      policy: exact_match
      joining_process_id: "<batch-id>"
```
If a test requires a Job process but none is configured or advertised, the runner skips cleanly in milliseconds instead of hanging.

### Result layering & multi-operation starts
Result classification describes the evidence emitted by the workflow, not the vendor name of the process:
- For a sequence that produces multiple result layers, set `workflow_execution.start_invocation_policy: one_start_per_operation` and configure its real `expected_operation_count`.
- The reusable trigger subscribes before starting, selects the generic `JoiningProcess`, waits for each correlated SingleResult, and only then starts the next operation.
- The trigger exits early the moment a terminal `JobResult` (Classification 4) or `BatchResult` (Classification 3) arrives.
- The runner preserves CUs for the primary `classification` and every declared item in `intermediate_classifications` (e.g. `classification: job` with `intermediate_classifications: [single, batch, intervention]`).

### State-change safety & permissions
- Adding a method to `state_changing_methods.allowed_methods` is a **safety permission only** — it does not enable CUs or create tests. The paired capability file determines which CUs are enabled.
- State-changing specification probes are blocked on real targets. Only configured workflow adapters may invoke them.
- `EnableAsset(false)` requires explicit argument-level opt-in, and tests restore `true` in a `finally` block.
- For `EnableAsset(true)`, use `when_disabled` to monitor `Tool.Parameters.Enabled`, or `always` when harmless reassertion is needed for a controller's remote-readiness state.
- Use the discovered Tool `ProductInstanceUri` for Tool-context operations (identifications, joining processes, counters, interventions). Do not use the Controller PIU for Tool methods.
- Keep real endpoints, ProductInstanceUris, process identifiers, serial numbers, and unsanitized evidence in ignored private profiles (`*.profile.yaml` / `*.capabilities.yaml`).
