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
python run_all_tests.py init-profile --endpoint opc.tcp://<controller-host>:40451 --output my_controller.sut.yaml
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
  target_server_cu_profiles/my_controller.sut.yaml
```

**Linux / macOS (Bash / Zsh):**
```bash
cp target_server_cu_profiles/template.sut.yaml \
   target_server_cu_profiles/my_controller.sut.yaml
```

Then update `my_controller.sut.yaml`:

| Setting | What to enter |
|---|---|
| `lifecycle.mode` | `external` for a real controller; `auto_simulator` only for the checked-in simulator |
| `connection.endpoint` | Real `opc.tcp://host:port` endpoint |
| `connection.security_mode` / `connection.security_policy` | Session security; certificate paths sit alongside them |
| `authentication.source` | `anonymous`, `prompt`, `file`, or `environment` - references only, never a secret value |
| `capability_claims.active_profile` / `supported_facets` / `cu_overrides` | The controller's authoritative CU claims |
| `workflows.tool_selector.product_instance_uri` | Leave empty for runtime Tool discovery; otherwise enter the Tool PIU |
| `workflows.process_selector.joining_process_id` | Default/fallback Process ID returned by `GetJoiningProcessList` |
| `workflows.process_selector.joining_process_origin_id` | Stable origin fallback if the controller regenerates the primary ID |
| `workflows.process_selector.selection_name` | Final fallback when neither configured ID is advertised |
| `workflows.process_selectors_by_classification.<classification>` | Optional per-classification selectors (`single`, `job`, `batch`, `sync`) |
| `execution_policy.state_changing_methods.allowed_methods` | Safety authorization only: methods approved for this run; it does not enable CUs or create tests |
| `execution_policy.risk_approvals` | Who approved elevated risk (asset disable, destructive methods) and under which reference |
| `workflows.expected_operation_count` | Starts needed to complete the selected JoiningProcess |
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
  python run_all_tests.py --preflight-only --profile target_server_cu_profiles/my_controller.sut.yaml
  ```
- **Classification without invoking specification tests:**
  ```bash
  python run_all_tests.py --profile target_server_cu_profiles/my_controller.sut.yaml --skip-spec-tests
  ```
- **Full validation (Phase 1 + preflight + specs + evidence):**
  ```bash
  python run_all_tests.py run --profile target_server_cu_profiles/my_controller.sut.yaml --endpoint opc.tcp://<host>:40451
  ```
- **Preflight + specs + evidence only (skipping Phase 1):**
  ```bash
  python run_all_tests.py run --phase2 --profile target_server_cu_profiles/my_controller.sut.yaml --endpoint opc.tcp://<host>:40451
  ```
- **Guided / manual run with interactive prompts:**
  ```bash
  python run_all_tests.py --phase2 --profile target_server_cu_profiles/my_controller.sut.yaml --mode guided --interactive-prompts --output-dir test-results/target-server-cu/my-controller-guided
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
Result classification describes the evidence emitted by the workflow, not the vendor name of the process:
- For a sequence that produces multiple result layers, set `workflow_execution.start_invocation_policy: one_start_per_operation` and configure its real `expected_operation_count`.
- The reusable trigger subscribes before starting, selects the generic `JoiningProcess`, waits for each correlated SingleResult, and only then starts the next operation.
- The trigger exits early the moment a terminal `JobResult` (Classification 4) or `BatchResult` (Classification 3) arrives.
- The runner preserves CUs for the primary `classification` and every declared item in `intermediate_classifications` (e.g. `classification: job` with `intermediate_classifications: [single, batch, intervention]`).

### State-change safety & permissions
- Adding a method to `state_changing_methods.allowed_methods` is a **safety permission only** — it does not enable CUs or create tests. The manifest's `capability_claims` determine which CUs are enabled.
- State-changing specification probes are blocked on real targets. Only configured workflow adapters may invoke them.
- `EnableAsset(false)` requires explicit argument-level opt-in, and tests restore `true` in a `finally` block.
- For `EnableAsset(true)`, use `when_disabled` to monitor `Tool.Parameters.Enabled`, or `always` when harmless reassertion is needed for a controller's remote-readiness state.
- Use the discovered Tool `ProductInstanceUri` for Tool-context operations (identifications, joining processes, counters, interventions). Do not use the Controller PIU for Tool methods.
- Keep real endpoints, ProductInstanceUris, process identifiers, serial numbers, and unsanitized evidence in ignored private manifests (`*.sut.yaml`).
