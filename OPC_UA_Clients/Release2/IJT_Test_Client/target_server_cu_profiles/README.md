# Target Server CU Profiles

This folder contains YAML profiles for Target Server CU validation.

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

Profiles do not replace `server_capabilities.yaml`. The capability file says
which CUs the server supports. The Target Server CU profile says how to run or
classify those CUs for one server under test.

---

## Files in This Directory

| File | Purpose |
|---|---|
| `README.md` | This documentation file |
| `template.yaml` | Fully commented schema template with safe defaults and placeholders |
| `example_remote_start.yaml` | Generic sanitized example for target servers supporting StartSelectedJoining |
| `example_manual_trigger.yaml` | Generic sanitized example for target servers requiring physical tool trigger |
| `example_simulation_methods.yaml` | Generic sanitized example for servers that expose simulation helper methods |

---

## Creating a Local (Private) Profile

**Do not commit profiles containing:**

- Private target server hostnames or IP addresses
- Real `ProductInstanceUri` serial numbers or asset identifiers
- Real joining process IDs, names, or vendor payloads
- Operator credentials or authentication tokens

**Recommended approach:**

1. Copy `template.yaml` to a location **outside** this repository (e.g. `~/my-target-server.yaml`).
2. Fill in your real endpoint, PIU, and process details.
3. Run with: `python run_target_server_cu.py --profile ~/my-target-server.yaml --preflight-only`

If you need to commit a profile for CI/CD, sanitize it first:
- Replace real IP/hostname with `<target-server-host>` or `localhost`
- Replace real PIU with empty string (discovery will find it at runtime)
- Replace real process IDs with empty string (first-available selection)

---

## Run a Target Server Check

```bash
# 1. Preflight only — safe for any target server, no state changes:
python run_target_server_cu.py --profile target_server_cu_profiles/template.yaml --preflight-only

# 2. Full automated run (target server supports StartSelectedJoining):
python run_target_server_cu.py --profile target_server_cu_profiles/example_remote_start.yaml --mode automated

# 3. Guided/manual run with terminal prompts:
python run_target_server_cu.py --profile target_server_cu_profiles/example_manual_trigger.yaml --mode guided --interactive-prompts

# 4. Override endpoint from command line:
python run_target_server_cu.py --profile template.yaml --endpoint opc.tcp://target-server-host:40451 --preflight-only

# 5. Custom output directory:
python run_target_server_cu.py --profile my_profile.yaml --output-dir test-results/target-server-cu/run-2026-06-30
```

---

## Run Modes

### Preflight only (always safe)

```bash
python run_target_server_cu.py --profile target_server_cu_profiles/template.yaml --preflight-only
```

Checks the configuration, TCP reachability, and trigger mode. Does **not** call any OPC UA
methods or open a test session. Safe to run against any target server at any time.

### Automated mode (live spec tests)

```bash
python run_target_server_cu.py --profile target_server_cu_profiles/example_remote_start.yaml --mode automated
```

When the profile has a configured, reachable endpoint:

1. Runs configuration and TCP preflight checks.
2. Shows CU execution classification.
3. Runs the `specification_tests/` pytest suite with `OPCUA_SERVER_URL` set to the
   target server and `OPCUA_CAPABILITIES_FILE` from the profile.
4. Writes a `spec-tests.xml` JUnit report and `target-server-cu-report.json` evidence.

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
python run_all_tests.py --target-server-profile target_server_cu_profiles/example_remote_start.yaml
```

This step is non-blocking by default. Target server preflight failures are shown
as warnings and the simulator-based test run still continues. Use
`--target-server-preflight-strict` when target server preflight must fail the run.

**Note:** Full live target server specification_tests/ runs are a Test Client-level
operation. Use `run_target_server_cu.py --mode automated` for those. The root-level
`run_all_tests.py` only performs the non-blocking preflight step via
`--target-server-profile`.

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
