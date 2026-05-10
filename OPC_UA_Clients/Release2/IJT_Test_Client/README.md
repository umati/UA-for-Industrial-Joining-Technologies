# IJT Test Client

Conformance test client for validating OPC UA IJT servers against the Industrial Joining Technologies
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

## Event And Condition Coverage

For servers that expose simulator triggers, the Test Client covers all 60
`SimulateEvents` event ids and all 60 `SimulateConditions` condition ids by
use-case category. It also samples standard OPC UA condition methods for
`JoiningSystemConditionType`: Acknowledge, Confirm, AddComment, Enable/Disable,
invalid EventId rejection, and ConditionRefresh.

Focused Debug-server checks:

```bash
python -m pytest conformance/test_event_condition_catalog.py conformance/test_joining_system_condition_methods.py -q
python -m pytest conformance/test_events.py events -q
```

## Test Reports

- [Test report formats](docs/test-results.md)
- [Reference workflow demos](reference_workflows/README.md)
