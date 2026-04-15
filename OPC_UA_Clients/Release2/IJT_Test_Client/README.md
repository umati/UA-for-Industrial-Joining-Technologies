# IJT Test Client

## Contact
- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Overview

Conformance test suite for the
**OPC UA Industrial Joining Technologies (IJT) Companion Specification**,
built with Python `pytest`.

## Prerequisites

- **Python 3.14+** — add to system `PATH`
- A running **OPC UA IJT Server** — see [OPC UA IJT Server Simulator](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2)
- Default endpoint: `opc.tcp://localhost:40451`

## Quick Start

```bash
python run_all_tests.py                  # run tests
python run_all_tests.py --excel=always   # run tests and generate Excel report
```

Test results are written to `test-results/`.
