# Target Server CU Profiles

This folder contains YAML profiles for Target Server CU validation.

Related orientation documents:

- `../docs/IJT_TEST_CLIENT_OPCUA_SERVER_INTEGRATION_SUMMARY.md`
- `../docs/TARGET_SERVER_CU_QUICK_START.md`

A **target server** is the OPC UA IJT server under test (SUT). It can be the
checked-in simulator, a physical/device controller from any vendor, or any custom OPC UA IJT server endpoint.
The simulator may use `SimulateResults` and `SimulateEvents`; a production controller
normally uses `StartSelectedJoining`, manual tool action, or observe-only
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
| `default.capabilities.yaml` | Fully commented default CU declaration when no explicit capability file is selected |
| `simulator.capabilities.yaml` | Fully commented simulator CU declaration selected automatically by the runner |
| `template.profile.yaml` | Fully commented execution-profile schema with safe defaults and placeholders |
| `example_multi_operation_job.profile.yaml` | Fully commented automated-controller example: ID-first Tool/process selection, layered results, intervention evidence, and safe enablement |
| `example_multi_operation_job.capabilities.yaml` | Fully commented capability declaration paired with the complete automated example |
| `example_manual_trigger.profile.yaml` | Fully commented example for controllers requiring a physical tool trigger |
| `example_simulation_methods.profile.yaml` | Fully commented example for servers exposing simulator helper methods |

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

`state_changing_methods.allowed_methods` is a safety permission list only. It
does not enable CUs, create tests, or guarantee execution. The paired capability
declaration, existing automated tests, configured inputs, and live prerequisites
determine what is actually tested.

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

`run_all_tests.py` is the canonical entry point for all of the commands below
(`run_target_server_cu.py` is a deprecated compatibility shim that forwards to
the exact same implementation in `helpers/target_server_execution.py`).

```bash
# 1. Preflight only — safe for any target server, no state changes:
python run_all_tests.py --preflight-only --profile target_server_cu_profiles/template.profile.yaml

# 2. Full validation (Phase 1 + strict preflight + specs + evidence; target server supports StartSelectedJoining):
python run_all_tests.py --profile target_server_cu_profiles/example_multi_operation_job.profile.yaml --spec-tests-timeout 3600

# 2b. Preflight + specs + evidence only, skipping Phase 1:
python run_all_tests.py --phase2 --profile target_server_cu_profiles/example_multi_operation_job.profile.yaml --spec-tests-timeout 3600

# 3. Guided/manual run with terminal prompts:
python run_all_tests.py --phase2 --profile target_server_cu_profiles/example_manual_trigger.profile.yaml --mode guided --interactive-prompts

# 4. Override endpoint from command line (suppresses simulator auto-launch; --profile is optional):
python run_all_tests.py --preflight-only --profile target_server_cu_profiles/template.profile.yaml --endpoint opc.tcp://target-server-host:40451

# 5. Custom output directory:
python run_all_tests.py --profile my_profile.yaml --output-dir test-results/target-server-cu/run-2026-06-30
```

---

## Run Modes

### Preflight only (always safe)

```bash
python run_all_tests.py --preflight-only --profile target_server_cu_profiles/template.profile.yaml
```

Checks the configuration, TCP reachability, and trigger mode. Does **not** call any OPC UA
methods or open a test session. Safe to run against any target server at any time.
Requires `--profile`, `--endpoint`, or `OPCUA_SERVER_URL` so the runner knows which
server to check — it never falls back to the simulator.

### Automated mode (live spec tests)

```bash
python run_all_tests.py --profile target_server_cu_profiles/example_multi_operation_job.profile.yaml
```

When the profile has a configured, reachable endpoint:

1. Runs configuration and TCP preflight checks (always strict: blocking issues fail the run).
2. Shows CU execution classification.
3. Runs the `specification_tests/` pytest suite with `OPCUA_SERVER_URL` set to the
   target server, `OPCUA_CAPABILITIES_FILE` from the profile, and the resolved
   Tool/JoiningProcess runtime overrides forwarded to the target workflow fixtures.
4. Writes a `spec-tests.xml` JUnit report and `target-server-cu-report.json` evidence.

This is the same `specification_tests/` suite the simulator runs by default —
the profile only changes applicability, safety, triggers, scoring, and evidence,
never the test suite itself.

The default subprocess limit is 600 seconds. Use `--spec-tests-timeout SECONDS`
when real result generation makes the complete suite take longer. The runner
automatically sizes pytest's per-test ceiling for the configured method, result,
and operation timeouts, capped by the full-suite limit.

Generic specification tests cannot invoke state-changing methods on a real target.
Those calls are permitted only through the configured workflow adapter. Disabling
an asset requires the separate `allow_disable_asset: true` opt-in.

The complete multi-operation example authorizes selection, remote start, abort,
reset, increment, and decrement for its Job/Sequence workflow. Abort/reset/counter
controls are not applicable to a single-program profile. Authorization remains a
safety gate; it does not cause every listed method to run.

With `selection.joining_process.policy: exact_match`, selection tries the
configured JoiningProcess ID first, then origin ID, then SelectionName. This
allows a stable origin ID to survive controller-generated primary ID changes.

When the endpoint is a placeholder or not reachable, this is reported as a
blocking preflight issue and the run fails — it is never silently downgraded to
a classification-only or simulator run.

### Classification only (no spec test invocation)

```bash
python run_all_tests.py --profile my_profile.yaml --skip-spec-tests
```

Runs classification without invoking the spec test suite, even if the endpoint is configured.

---

## Canonical CLI Reference

All Target Server options are available directly on `run_all_tests.py`:

```bash
python run_all_tests.py                                    # full run: Phase 1 + Phase 2 (simulator auto-launch)
python run_all_tests.py --phase1                            # static/security/unit/type checks only
python run_all_tests.py --phase2                            # specification_tests only (simulator auto-launch if no target)
python run_all_tests.py --profile FILE                      # Phase 1 + strict preflight + specs + target evidence
python run_all_tests.py --phase2 --profile FILE              # strict preflight + specs + target evidence only
python run_all_tests.py --preflight-only --profile FILE      # configuration/readiness classification only
```

Relevant Target Server options: `--endpoint`, `--capabilities-file`,
`--tool-product-instance-uri`, `--joining-process-id`, `--joining-process-origin-id`,
`--mode {automated,guided}`, `--scoring-mode`, `--output-dir`,
`--interactive-prompts`, `--skip-spec-tests`, `--spec-tests-timeout`.

Precedence is resolved once per run: `--endpoint` > non-placeholder profile
endpoint > `OPCUA_SERVER_URL` > simulator auto-launch (only when there is no
profile and no external endpoint at all). A profile with an empty or
placeholder endpoint always fails preflight/live execution — it is never
silently downgraded to the simulator.

`--target-server-profile` remains a deprecated alias for `--profile`.
`--target-server-preflight-strict` is accepted but no longer needed: `--profile`
preflight is always strict now.

**Note:** Run these commands from `IJT_Test_Client`. The repository-root runner
does not expose Target Server options; run `run_all_tests.py` directly from
this directory for target server validation.

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

Adding a target server CU profile and running `python run_all_tests.py --profile FILE`
does **not** affect the standard simulator-based test run (`python run_all_tests.py`
with no `--profile`/`--endpoint`). The simulator path, default behavior, report
schemas, skip/fail semantics, and CU coverage outputs remain unchanged.


See `docs/test-results.md` for simulator output documentation.
