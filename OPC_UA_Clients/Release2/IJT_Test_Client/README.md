# IJT Test Client

IJT Specification Test Client for validating OPC UA IJT servers against the Industrial Joining Technologies
(IJT) companion specifications.

## Contact

- **Author:** Mohit Agarwal - mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
- Internet connection for first-time dependency installation
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)
  - Default OPC UA endpoint: `opc.tcp://localhost:40451`

## Quick Start

- **Run tests:** `python run_all_tests.py`
  - Test results and `test-results/report.xlsx` are written to `test-results/` by default.
  - If tests fail, the Excel workbook is diagnostic and includes a warning banner.
  - `test-results/report-baseline.json` is refreshed after report generation and is used for the next run's delta view.
- **Skip Excel report generation:** `python run_all_tests.py --excel=never`
- **Generate a reference workflow walkthrough:** `python scripts/run_reference_workflow.py --output test-results/reference-workflows/reference_joining_process_workflow.md`

## Target Server CU Validation

Use this when you want to check an OPC UA IJT server under test (SUT), such as a
product/device server or any other IJT server endpoint. The checked-in simulator
remains the default test target for `run_all_tests.py`.

Target Server CU validation is additive. It does not change the simulator path,
default test runner behavior, or existing report files.

```bash
# Preflight only — safe for any target server, no state changes.
# Copy template.yaml first, edit the endpoint, then run:
python run_target_server_cu.py --profile my_target_server.yaml --preflight-only

# Automated run (target server supports StartSelectedJoining):
python run_target_server_cu.py --profile target_server_cu_profiles/example_remote_start.yaml --mode automated

# Guided/manual run, for servers that need a physical tool trigger:
python run_target_server_cu.py --profile my_profile.yaml --mode guided --interactive-prompts
```

- Target Server CU profiles are in `target_server_cu_profiles/` — see `target_server_cu_profiles/README.md`.
- Evidence reports are written to `test-results/target-server-cu/` by default.
- Never commit profiles with real endpoints, PIUs, process IDs, or vendor identifiers.

## Event And Condition Coverage

For servers that expose simulator triggers, the Test Client covers all 60
`SimulateEvents` event ids and all 60 `SimulateConditions` condition ids by
use-case category. It also samples standard OPC UA condition methods for
`JoiningSystemConditionType`: Acknowledge, Confirm, AddComment, Enable/Disable,
invalid EventId rejection, and ConditionRefresh.

Focused Debug-server checks:

```bash
python -m pytest specification_tests/test_event_condition_catalog.py specification_tests/test_joining_system_condition_methods.py -q
python -m pytest specification_tests/test_events.py events -q
```

## Test Reports

- [Test report formats](docs/test-results.md)
- [Reference workflow demos](reference_workflows/README.md)
