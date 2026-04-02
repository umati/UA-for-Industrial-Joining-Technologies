# IJT Test Client

## Contact
- **Author:** Mohit Agarwal: mohit.agarwal@atlascopco.com

## Overview

A Python pytest suite that validates an OPC UA server against the
**OPC UA Industrial Joining Technologies (IJT) Companion Specification**.
Tests cover address space structure, asset management, result retrieval,
event subscriptions, joining process management, joint management, and
§11.1 Conformance Units — all against a live running OPC UA IJT server.

## Prerequisites

- **Python 3.14 or higher** — add to system `PATH`
- A running **OPC UA IJT Server** — see [OPC UA IJT Server Simulator](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2)
- Default endpoint: `opc.tcp://localhost:40451`

## Quick Start

```bash
python run_tests.py
```

That's it — creates `.venv`, installs dependencies, checks for server, and runs all tests.

## Optional: Run Specific Tests

```bash
# Filter by test name keyword
python run_tests.py -k "asset"

# Run by marker
python run_tests.py -m conformance
python run_tests.py -m structure
python run_tests.py -m methods

# Verbose output
python run_tests.py -v

# List all tests without running
python run_tests.py --co -q

# Stop on first failure
python run_tests.py -x
```

## Server Auto-Launch

Set `OPCUA_SIMULATOR_EXE` to the simulator binary path and `conftest.py` will
start it automatically before running tests:

```bash
OPCUA_SIMULATOR_EXE=/path/to/opcua_ijt_demo_application python run_tests.py
```

## Project Structure

```
IJT_Test_Client/
├── run_tests.py      # Entry point
├── conftest.py       # Shared pytest fixtures (server, client, namespace indices)
├── helpers/          # Node discovery, event collector, server manager
├── common/           # Connection + namespace registration tests
├── assets/           # Asset management structure and interfaces
├── results/          # Result management, retrieval, simulation
├── events/           # Event type hierarchy and subscriptions
├── joining_process/  # JoiningProcessManagement structure + methods
├── joint/            # JointManagement structure + methods
└── conformance/      # §11.1 Conformance Unit tests (CU-AM, CU-RM, CU-EM, CU-JP, CU-JT)
```

> 📖 See [SKILLS.md](docs/SKILLS.md) for full technical details: environment variables,
> fixtures, pytest markers, node discovery patterns, and design rules.

