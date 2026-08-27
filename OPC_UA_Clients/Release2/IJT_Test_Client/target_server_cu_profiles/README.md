# Target Server CU Profiles

This folder contains YAML profiles for Target Server CU validation.

Related orientation documents:

- `../docs/IJT_TEST_CLIENT_OPCUA_SERVER_INTEGRATION_SUMMARY.md`
- `../docs/TARGET_SERVER_CU_QUICK_START.md`

A **target server** is the OPC UA IJT server under test (SUT). It can be the
checked-in simulator, a product/device server, or another IJT server endpoint.
The simulator may use `SimulateResults` and `SimulateEvents`; a product/device
server normally uses `StartSelectedJoining`, manual tool action, or observe-only
evidence.

---

## What Is a Target Server CU Profile?

A target server CU profile configures:

- **Target endpoint** — the OPC UA server URL to connect to
- **CU execution policy** — mode (automated/guided/preflight_only), scoring, precondition handling
- **State-changing method opt-in** — explicit list of OPC UA methods allowed to modify target server state
- **Trigger mode** — how result evidence is generated (simulate_methods, start_selected_joining, manual_trigger, observe_only)
- **Tool and process selection** — how the runner picks the target tool PIU and joining process
- **Workflow execution** — start invocation policy, expected results, cleanup
- **Reporting** — output directory, sanitization settings

The capability file says which CUs the server supports. The execution profile
says how to run or classify those CUs for one server under test. Keep the pair
together and reference the capability filename from `capabilities_file`.

## Why YAML files have different locations

| Location | Responsibility | Tester normally edits it? |
|---|---|---|
| `target_server_cu_profiles/` | Controller execution profiles, capability declarations, template, and examples | Yes, when configuring a controller |
| `profiles/` | Internal OPC UA IJT profile/facet-to-CU catalog used by the loader | No |
| `reference_workflows/` | Non-executable documentation/demo workflows | No |

Execution and capability files that belong to one controller are kept together
here. The suffix states the role: `*.profile.yaml` controls execution and
`*.capabilities.yaml` controls which CUs are claimed. Internal catalogs and
runtime defaults remain separate because they are application data, not
controller configuration.

The runner limits result CUs to the profile's configured primary and intermediate
classifications. See `../docs/CONTROLLER_PROFILE_GUIDE.md` for layered result,
selection, intervention, event, and state-change semantics.

---

## Files in This Directory

| File | Purpose |
|---|---|
| `README.md` | This documentation file |
| `default.capabilities.yaml` | Default Test Client CU declaration when no explicit capability file is selected |
| `simulator.capabilities.yaml` | Checked-in simulator CU declaration selected automatically by the runner |
| `template.profile.yaml` | Fully commented execution-profile schema with safe defaults and placeholders |
| `example_multi_operation_job.profile.yaml` | Complete automated-controller example: ID-first Tool/process selection, layered results, intervention evidence, and safe enablement |
| `example_multi_operation_job.capabilities.yaml` | Capability declaration paired with the complete automated example |
| `example_manual_trigger.profile.yaml` | Distinct example for controllers requiring a physical tool trigger |
| `example_simulation_methods.profile.yaml` | Distinct example for servers exposing simulator helper methods |

---

## Creating a Local (Private) Profile

**Do not commit profiles containing:**

- Private target server hostnames or IP addresses
- Real `ProductInstanceUri` serial numbers or asset identifiers
- Real joining process IDs, names, or vendor payloads
- Operator credentials or authentication tokens

**Recommended approach:**

1. Start from `example_multi_operation_job.profile.yaml` for a complete
   automated controller workflow, `example_manual_trigger.profile.yaml` for
   physical operation, `example_simulation_methods.profile.yaml` for a
   simulator, or `template.profile.yaml` for the complete field reference.
2. When its workflow and CU declaration match the target, use it directly and
   pass `--endpoint`, `--joining-process-id`, and
   `--joining-process-origin-id`. No private YAML is required.
3. Only when behavior differs, copy the execution profile to
   `<controller>.profile.yaml` and its declaration to
   `<controller>.capabilities.yaml`. Local non-example YAML files here are
   intentionally Git-ignored.
4. Set `capabilities_file` in the copied profile to the paired capability
   filename, then adjust workflow and CU support values.
5. Keep Tool PIU empty when runtime discovery is preferred.

`GetJoiningProcessList` can return many programs/jobs. One execution profile
selects one JoiningProcess because operation count, allowed state changes, and
expected result layers must be deterministic. Use a separate named profile for
each process workflow that needs different expectations.

If you need to commit a profile for CI/CD, sanitize it first:
- Replace real IP/hostname with `<target-server-host>` or `localhost`
- Replace real PIU with empty string (discovery will find it at runtime)
- For a reusable discovery example, replace real process IDs with empty strings
  **and** change `selection.joining_process.policy` from `exact_match` to
  `first_compatible`

---

## Run a Target Server Check

```bash
# 1. Preflight only — safe for any target server, no state changes:
python run_target_server_cu.py --profile target_server_cu_profiles/template.profile.yaml --preflight-only

# 2. Full automated run (target server supports StartSelectedJoining):
python run_target_server_cu.py --profile target_server_cu_profiles/example_multi_operation_job.profile.yaml --mode automated

# 3. Guided/manual run with terminal prompts:
python run_target_server_cu.py --profile target_server_cu_profiles/example_manual_trigger.profile.yaml --mode guided --interactive-prompts

# 4. Override endpoint from command line:
python run_target_server_cu.py --profile target_server_cu_profiles/template.profile.yaml --endpoint opc.tcp://target-server-host:40451 --preflight-only

# 5. Custom output directory:
python run_target_server_cu.py --profile my_profile.yaml --output-dir test-results/target-server-cu/run-2026-06-30
```

---

## Run Modes

### Preflight only (always safe)

```bash
python run_target_server_cu.py --profile target_server_cu_profiles/template.profile.yaml --preflight-only
```

Checks the configuration, TCP reachability, and trigger mode. Does **not** call any OPC UA
methods or open a test session. Safe to run against any target server at any time.

### Automated mode (live spec tests)

```bash
python run_target_server_cu.py --profile target_server_cu_profiles/example_multi_operation_job.profile.yaml --mode automated
```

When the profile has a configured, reachable endpoint:

1. Runs configuration and TCP preflight checks.
2. Shows CU execution classification.
3. Runs the `specification_tests/` pytest suite with `OPCUA_SERVER_URL` set to the
   target server and `OPCUA_CAPABILITIES_FILE` from the profile.
4. Writes a `spec-tests.xml` JUnit report and `target-server-cu-report.json` evidence.

Generic specification tests cannot invoke state-changing methods on a real target.
Those calls are permitted only through the configured workflow adapter. Disabling
an asset requires the separate `allow_disable_asset: true` opt-in.

When the endpoint is a placeholder or not reachable, step 3 is skipped and only
classification is shown (same as before).

### Classification only (no spec test invocation)

```bash
python run_target_server_cu.py --profile my_profile.yaml --mode automated --skip-spec-tests
```

Runs classification without invoking the spec test suite, even if the endpoint is configured.

---

## Integration with run_all_tests.py

`run_all_tests.py` supports an optional target server preflight step:

```bash
# Add target server preflight to the standard run:
python run_all_tests.py --target-server-profile target_server_cu_profiles/example_multi_operation_job.profile.yaml
```

This step is non-blocking by default. Target server preflight failures are shown
as warnings and the simulator-based test run still continues. Use
`--target-server-preflight-strict` when target server preflight must fail the run.

**Note:** Run these commands from `IJT_Test_Client`. Full live target-server
`specification_tests/` runs use `run_target_server_cu.py --mode automated`.
The `run_all_tests.py` in this same Test Client directory performs only the
optional preflight step via `--target-server-profile`; the repository-root
runner does not expose that argument.

---

## Evidence Report Outputs

Target Server CU runs write artifacts to `test-results/target-server-cu/` by default:

| File | Format | Contents |
|---|---|---|
| `target-server-cu-report.json` | JSON | Machine-readable evidence report with preflight checks, CU classification, spec test exit code, and outcome details |
| `target-server-cu-summary.txt` | Text | Human-readable operator summary |
| `spec-tests.xml` | JUnit XML | Pytest result evidence from the live specification_tests/ run (automated/guided mode only) |

---

## Non-Regression Guarantee

Adding a target server CU profile and running `run_target_server_cu.py` does **not** affect
the standard simulator-based test run.  The simulator path, `run_all_tests.py` default
behavior, report schemas, skip/fail semantics, and CU coverage outputs remain unchanged.

See `docs/test-results.md` for simulator output documentation.
