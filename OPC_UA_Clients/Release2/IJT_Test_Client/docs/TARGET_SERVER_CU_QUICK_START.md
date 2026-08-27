# Target Server CU Quick Start

## 1) Choose profile
- Complete automated controller workflow: `target_server_cu_profiles/example_multi_operation_job.profile.yaml`
- Manual trigger workflow: `target_server_cu_profiles/example_manual_trigger.profile.yaml`
- Simulator helper methods workflow: `target_server_cu_profiles/example_simulation_methods.profile.yaml`
- New profile creation: copy from `target_server_cu_profiles/template.profile.yaml`

### Prepare a real controller profile

If the controller matches the supplied capability baseline, use the committed
generic pair directly and pass installation values at runtime:

```powershell
python run_target_server_cu.py `
  --profile target_server_cu_profiles\example_multi_operation_job.profile.yaml `
  --endpoint opc.tcp://<controller-host>:40451 `
  --joining-process-id <joining-process-id> `
  --joining-process-origin-id <joining-process-origin-id> `
  --preflight-only
```

Optional runtime overrides are also available through
`OPCUA_SERVER_URL`, `OPCUA_TOOL_PRODUCT_INSTANCE_URI`,
`OPCUA_JOINING_PROCESS_ID`, `OPCUA_JOINING_PROCESS_ORIGIN_ID`, and
`OPCUA_CAPABILITIES_FILE`.

Create local paired files only when the controller's workflow or supported CUs
differ from the complete example:

```powershell
Copy-Item target_server_cu_profiles\example_multi_operation_job.profile.yaml `
  target_server_cu_profiles\my_controller.profile.yaml
Copy-Item target_server_cu_profiles\example_multi_operation_job.capabilities.yaml `
  target_server_cu_profiles\my_controller.capabilities.yaml
```

Then update `my_controller.profile.yaml`:

| Setting | What to enter |
|---|---|
| `capabilities_file` | `"my_controller.capabilities.yaml"` |
| `target.endpoint` | Real `opc.tcp://host:port` endpoint |
| `selection.tool.product_instance_uri` | Leave empty for runtime Tool discovery; otherwise enter the Tool PIU |
| `selection.joining_process.joining_process_id` | Primary ID returned by `GetJoiningProcessList` |
| `selection.joining_process.joining_process_origin_id` | Stable fallback if the controller regenerates the primary ID |
| `selection.joining_process.selection_name` | Final fallback when neither configured ID is advertised |
| `state_changing_methods.allowed_methods` | Safety authorization only: methods approved for this run; it does not enable CUs or create tests |
| `extension_fields.enable_asset_policy` | `when_disabled`, or `always` when safe enablement must be reasserted |
| `workflow_execution.expected_operation_count` | Starts needed to complete the selected JoiningProcess |
| `expected_results.classification` | Final result layer, such as `single`, `batch`, or `job` |
| `expected_results.intermediate_classifications` | Earlier layers, such as `[single, batch, intervention]` |
| `triggers.result.mode` | `start_selected_joining`, `manual_trigger`, `observe_only`, or `none` |

Update `my_controller.capabilities.yaml` with the controller's actual
`active_profile`, `supported_facets`, and `cu_overrides`. The supplied file is
the capability selection observed for the tested multi-operation pattern, not a
claim that every controller supports the same CUs.

## 2) Run commands
- Safe preflight check:
  `python run_target_server_cu.py --profile target_server_cu_profiles\my_controller.profile.yaml --preflight-only`
- Classification without invoking specification tests:
  `python run_target_server_cu.py --profile target_server_cu_profiles\my_controller.profile.yaml --mode automated --skip-spec-tests`
- Full automated run:
  `python run_target_server_cu.py --profile target_server_cu_profiles\my_controller.profile.yaml --mode automated --spec-tests-timeout 3600 --output-dir test-results\target-server-cu\my-controller`
- Guided/manual run with prompts:
  `python run_target_server_cu.py --profile target_server_cu_profiles\my_controller.profile.yaml --mode guided --interactive-prompts --output-dir test-results\target-server-cu\my-controller-guided`

Run preflight first. Do not authorize disable, reboot, disconnect, write, or
execution methods unless the controller state change is understood and intended.
The default full-suite timeout is 600 seconds. Increase `--spec-tests-timeout`
for real workflows where multiple result-producing operations can legitimately
take longer. The runner also raises pytest's per-test ceiling from its 120-second
baseline when the configured multi-operation workflow needs more time.

## 3) Read outputs
- `test-results/target-server-cu/target-server-cu-report.json` (machine-readable CU report)
- `test-results/target-server-cu/target-server-cu-summary.txt` (human-readable summary)
- `test-results/target-server-cu/spec-tests.xml` (CI/JUnit output)
- `test-results/target-server-cu/cu-coverage-report.json` (run-scoped 123-CU evidence)
- `test-results/target-server-cu/report-controller.xlsx` (automatically generated workbook)

All five artifacts belong to the same run directory. Do not generate a target
workbook from the global `test-results/cu-coverage-report.json`, because a later
focused or simulator run may have replaced it. Failed runs still generate a
diagnostic workbook with a failure banner; they are not conformance passes.

## 4) Batch, job, and identifier workflows

Use `CONTROLLER_PROFILE_GUIDE.md` for process selection, layered
Single/Batch/Job results, intervention actions, state-change safety, and
controller event rules. Use `../target_server_cu_profiles/README.md` for profile
files and commands. Review both before running against a production controller.
