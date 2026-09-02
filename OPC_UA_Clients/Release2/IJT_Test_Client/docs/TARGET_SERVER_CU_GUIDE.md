# Target Server CU Guide

> **Canonical entry point:** `python run_all_tests.py` (see options below).
> The simulator and a Target Server are both "OPC UA Servers Under Test" running
> the identical `specification_tests/` suite; a profile only controls
> applicability, safety, triggers, scoring, and evidence — never a separate
> test suite. Default (no flags) runs everything; `--phase2` runs
> specification_tests only; `--profile` controls Target Server execution.

---

## Stable Subcommands (recommended)

```bash
# Full run against a controller
python run_all_tests.py run --profile controller.sut.yaml

# Read-only server inspection (no state change — safe to run anytime)
python run_all_tests.py inspect --endpoint opc.tcp://10.246.32.8:40451
python run_all_tests.py inspect --profile controller.sut.yaml

# Generate a pre-filled manifest from a live server
python run_all_tests.py init-profile --endpoint opc.tcp://10.246.32.8:40451 --output controller.sut.yaml
```

All flags from `run_all_tests.py` still work unchanged. The subcommands are
thin aliases over the flag-based API for discoverability.

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

Before writing or editing a manifest, connect to the target server to automatically discover its Tool `ProductInstanceUri`, available Joining Processes, and generate a recommended YAML snippet:

```bash
python run_all_tests.py init-profile --endpoint opc.tcp://<controller-host>:40451 --output controller.sut.yaml
```

---

## 3) SUT Manifests & Setup Recipes

### Available SUT manifest catalog:
- **Universal template:** `target_server_cu_profiles/template.sut.yaml`
- **Checked-in simulator:** `target_server_cu_profiles/simulator.sut.yaml`
- **Remote-start multi-operation workflow:** `target_server_cu_profiles/controller_remote_start.sut.yaml`
- **Manual trigger workflow:** `target_server_cu_profiles/controller_manual_trigger.sut.yaml`

One System Under Test is described by exactly one `*.sut.yaml` manifest. Every field is documented in the generated [SUT Manifest Field Reference](SUT_MANIFEST_REFERENCE.md).

### Prepare a real controller manifest

If the controller matches the supplied claim baseline, use the committed generic example directly and pass installation values at runtime:

**Windows (PowerShell):**
```powershell
python run_all_tests.py `
  --profile target_server_cu_profiles/controller_remote_start.sut.yaml `
  --endpoint opc.tcp://<controller-host>:40451 `
  --joining-process-id <joining-process-id> `
  --joining-process-origin-id <joining-process-origin-id> `
  --preflight-only
```

**Linux / macOS (Bash / Zsh):**
```bash
python run_all_tests.py \
  --profile target_server_cu_profiles/controller_remote_start.sut.yaml \
  --endpoint opc.tcp://<controller-host>:40451 \
  --joining-process-id <joining-process-id> \
  --joining-process-origin-id <joining-process-origin-id> \
  --preflight-only
```

Optional runtime overrides are also available through environment variables:
`OPCUA_SERVER_URL`, `OPCUA_TOOL_PRODUCT_INSTANCE_URI`, `OPCUA_JOINING_PROCESS_ID`, `OPCUA_JOINING_PROCESS_ORIGIN_ID`, and `OPCUA_CAPABILITIES_FILE` (which now names a `*.sut.yaml` manifest).

### Creating a local manifest

Create a local manifest when the controller's workflow or claimed CUs differ from the committed example. Copy one file - there is no companion file to keep in sync:

**Windows (PowerShell):**
```powershell
Copy-Item target_server_cu_profiles/template.sut.yaml `
  target_server_cu_profiles/controller.sut.yaml
```

**Linux / macOS (Bash / Zsh):**
```bash
cp target_server_cu_profiles/template.sut.yaml \
   target_server_cu_profiles/controller.sut.yaml
```

Then update `controller.sut.yaml`:

| Setting | What to enter |
|---|---|
| `lifecycle.mode` | `external` for a real controller; `auto_simulator` only for the checked-in simulator |
| `connection.endpoint` | Real `opc.tcp://host:port` endpoint |
| `connection.security_mode` / `connection.security_policy` | Session security; certificate paths sit alongside them |
| `authentication.source` | `anonymous`, `prompt`, `file`, or `environment` - references only, never a secret value |
| `capability_claims.active_profile` / `supported_facets` / `cu_overrides` | The controller's authoritative CU claims |
| `workflows.tool_selector.product_instance_uri` | Leave empty for runtime Tool discovery; otherwise enter the Tool PIU |
| `workflows.process_selector.policy` | `first_compatible` is the schema default; committed presets may use `first_ready`. All non-exact policies select the first returned process with the requested standard Classification and do not infer readiness from names or vendor fields. `exact_match` pins an advertised ID/origin/name and still requires matching Classification metadata. |
| `workflows.process_selector.joining_process_id` | Default/fallback Process ID returned by `GetJoiningProcessList` |
| `workflows.process_selector.joining_process_origin_id` | Stable origin fallback if the controller regenerates the primary ID |
| `workflows.process_selector.selection_name` | Final fallback when neither configured ID is advertised |
| `workflows.process_selectors_by_classification.<classification>` | Optional per-classification selectors (`single`, `job`, `batch`, `sync`) |
| `workflows.max_start_invocations` | Maximum accepted StartSelectedJoining invocations before stopping (default: 6) |
| `workflows.consecutive_start_delay_seconds` | Pacing delay in seconds between consecutive starts (default: 0.25s) |
| `workflows.process_selector.identifier_strategy` | Strategy for populating JoiningProcessIdentificationDataType (`id_only`, `id_with_origin`, `id_with_selection_name`, `all_available`) |
| `workflows.expected_results.classification` | Final result layer, such as `single`, `batch`, or `job` |
| `workflows.expected_results.intermediate_classifications` | Earlier layers, such as `[single, batch, intervention]` |
| `triggers.result.mode` | `start_selected_joining`, `manual_trigger`, `observe_only`, or `none` |
| `timeouts.*` | Separate budgets for passive observation, active results, whole workflow, operator action, and single method calls |
| `scoring.mode` | `strict_profile` (strict claimed scope, default), `diagnostic`, or `acceptance` |

An `external` manifest that still contains `<placeholder>` values in an *operational* field
fails fast before any server is contacted. Descriptive prose (`name`, `description`) is not
scanned, so an example may keep documenting the word `<placeholder>` and still be live-ready
once its real values are filled in.

### Connection security and credentials

`connection.security_mode` / `connection.security_policy` and `authentication.source` are
applied end to end: preflight, `inspect`, `init-profile`, and every asyncua client the pytest
fixtures open use the same declaration. A declared setting that cannot be applied is a
blocking `connection_security` preflight check — it is never ignored and never downgraded
to an anonymous, unsecured session.

| `authentication.source` | Where the credentials come from | Notes |
|---|---|---|
| `anonymous` | No user identity | Default, and what the checked-in simulator uses |
| `prompt` | Operator, at run time | Only with `--interactive-prompts`; an unattended run fails preflight instead of blocking on stdin |
| `file` | A local, git-ignored YAML/JSON file with `username` / `password` | `authentication.credentials_file` holds the path; relative paths resolve against the manifest |
| `environment` | Environment / CI secret variables | `authentication.username_env_var` and `authentication.password_env_var` hold variable *names*; an unset variable fails preflight |

A secure channel (`security_mode` other than `None`) requires
`connection.client_certificate_path` and `connection.client_private_key_path`;
`connection.server_certificate_path` pins the server certificate and
`connection.trust_store_path` installs a trusted-issuer/CRL validator. The manifest never
holds a secret value, and no credential is ever written to a log, report, or error message.

---

## 4) Run Commands

- **Safe preflight check:**
  ```bash
  python run_all_tests.py --preflight-only --profile target_server_cu_profiles/controller.sut.yaml
  ```
- **Classification without invoking specification tests:**
  ```bash
  python run_all_tests.py --profile target_server_cu_profiles/controller.sut.yaml --skip-spec-tests
  ```
- **Full validation (Phase 1 + preflight + specs + evidence):**
  ```bash
  python run_all_tests.py run --profile target_server_cu_profiles/controller.sut.yaml --endpoint opc.tcp://<host>:40451
  ```
- **Preflight + specs + evidence only (skipping Phase 1):**
  ```bash
  python run_all_tests.py run --phase2 --profile target_server_cu_profiles/controller.sut.yaml --endpoint opc.tcp://<host>:40451
  ```
- **Guided / manual run with interactive prompts:**
  ```bash
  python run_all_tests.py --phase2 --profile target_server_cu_profiles/controller.sut.yaml --mode guided --interactive-prompts --output-dir test-results/target-server-cu/controller-guided
  ```

---

## 5) Output Artifacts

Every Target Server run generates structured evidence artifacts in the output directory (default: `test-results/target-server-cu/`):

- `target-server-cu-report.json` — machine-readable JSON evidence report with check details
- `target-server-cu-summary.txt` — human-readable ASCII summary for console inspection
- `target-server-cu-summary.md` — GitHub-compatible Markdown summary table
- `spec-tests.xml` — standard JUnit XML report for CI/CD integration
- `cu-coverage-report.json` — run-scoped 123-CU classification report
- `report-controller.xlsx` — automatically generated Excel traceability workbook, written inside the run's own output directory. It is copied elsewhere only when `--excel-out FILE` is explicitly passed. If the run completed but this workbook cannot be produced — for example because `spec-tests.xml` or `cu-coverage-report.json` is missing — the target run fails; only `--excel=never` and `--excel=on-success` decline it benignly.

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
Joining-process and result classifications are different OPC 40450-1 domains:

- `JoiningProcessMetaData.Classification`: Other=1, Program=2, Sync=3, Batch=4, Job=5.
- `ResultMetaData.Classification`: Single=1, Sync=2, Batch=3, Job=4, Stitching=5, Intervention=6, Text=7.

Runtime selection and `init-profile` use the joining-process domain. Never copy a
numeric value from one domain into the other. Discovery treats advertised process
metadata as authoritative; name-based suggestions are advisory only when that
metadata is absent or unusable and must be reviewed before use.

YAML keys such as `single:`, `sync:`, `batch:`, and `job:` are human-readable
configuration labels only. They are converted at the configuration boundary;
execution and OPC UA comparisons use the integer result constants and the distinct
joining-process classification enum. These strings are never sent as OPC UA
Classification values.

Result classification describes the evidence emitted by the workflow, not the vendor name of the process:
- For a compound process that produces multiple result layers (Job, Batch, or Sync), configure `workflows.max_start_invocations` (default: 6) and `workflows.consecutive_start_delay_seconds` (default: 0.25s).
- Exact process selectors still require `JoiningProcessMetaData.Classification` to match the requested Program, Sync, Batch, or Job domain; an ID match never overrides incompatible or unreadable classification metadata.
- The reusable trigger subscribes before starting, selects the generic `JoiningProcess`, waits for a completed Tool-correlated `SingleResult` as operation evidence, and applies the pacing delay between starts.
- The trigger exits early when the matching terminal completed `SyncResult`, `BatchResult`, or `JobResult` arrives with `ResultState=1` and `IsPartial=False`.
- Queue inspection and the pacing drain reduce extra-start races, but cannot eliminate the small check-to-start window without an atomic controller readiness/completion signal.
- The runner preserves CUs for the primary `classification` and every declared item in `intermediate_classifications` (e.g. `classification: job` with `intermediate_classifications: [single, batch, intervention]`).

### Autonomous Abort and Reset Workflows
The Test Client provides dedicated trigger methods for compound multi-step sequence abort and reset testing:
- **Required permissions**: Add `AbortJoiningProcess` and/or `ResetJoiningProcess` to `cu_execution.state_changing_methods.allowed_methods`.
- **Approved workflows**: Add `remote_abort_job` and/or `remote_reset_job` to `workflows.approved`.
- **Abort workflow (`trigger_abort_job`)**:
  - Selects a multi-step Job (Classification 5) or Batch (Classification 4).
  - Starts step 1 via `StartSelectedJoining` and waits for its completed intermediate `SingleResult` to confirm active sequence state, strictly ensuring the parent sequence did not finish prematurely.
  - Invokes `AbortJoiningProcess(ToolPIU, Identification, LocalizedText(Message))` with `target_server_authorized=True`.
  - Asserts that the terminal consolidated result arrives with `ResultState=3 (ABORTED)` and `IsPartial=False`. Set `results.reject_ok_evaluation_on_abort: true` only when the server contract requires rejection of an aborted result evaluated as `OK (1)`.
- **Reset workflow (`trigger_reset_job`)**:
  - Requires a live subscription client to establish and verify sequence state.
  - Starts step 1 and verifies the intermediate `SingleResult`.
  - Invokes `ResetJoiningProcess(ToolPIU, Identification)` with `target_server_authorized=True`.
  - Drains queued notifications, issues `StartSelectedJoining` again, and requires a new `ResultId`, increasing `SequenceNumber`, and matching non-empty `StepId`. This rejects stale notifications and proves return to the same first step.
  - Reports the conformance probe as inconclusive and skips it when `StepId` is absent because OPC 40001-101 makes this field optional; observing another `SingleResult` alone cannot prove which step ran.
- **Dedicated Trigger Routing**: The Abort event and Reset functional conformance tests call the dedicated trigger methods. Unsupported adapters return a non-triggering outcome, while approved `start_selected_joining` profiles run the autonomous workflows. `trigger_job()` remains strictly dedicated to standard completed Job execution (`ResultState=1: COMPLETED`).

### State-change safety & permissions
- Adding a method to `state_changing_methods.allowed_methods` is a **safety permission only** — it does not enable CUs or create tests. The manifest's `capability_claims` determine which CUs are enabled.
- State-changing specification probes are blocked on real targets. Only configured workflow adapters may invoke them.
- `EnableAsset(false)` requires explicit argument-level opt-in, and tests restore `true` in a `finally` block.
- For `EnableAsset(true)`, use `when_disabled` to monitor `Tool.Parameters.Enabled`, or `always` when harmless reassertion is needed for a controller's remote-readiness state.
- Use the discovered Tool `ProductInstanceUri` for Tool-context operations (identifications, joining processes, counters, interventions). Do not use the Controller PIU for Tool methods.
- Keep real endpoints, ProductInstanceUris, process identifiers, serial numbers, and unsanitized evidence in ignored private manifests (`*.sut.yaml`).
