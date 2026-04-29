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
  - Test results are written to `test-results/`.
- **Generate an Excel report:** `python run_all_tests.py --excel=always`

## Test Reports

- [Test report formats](docs/test-results.md)
