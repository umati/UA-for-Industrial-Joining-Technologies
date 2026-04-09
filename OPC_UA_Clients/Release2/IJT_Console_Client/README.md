# IJT Console Client

## Contact
- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Overview
- A minimal **reference client** based on the **OPC UA Industrial Joining Technologies (IJT) Companion Specification** using the open source `opcua-asyncio` stack.
- Demonstrates connecting to a live OPC UA IJT server, subscribing to events (tightening results), calling simulation methods, and reading result data.

## Prerequisites
- **Internet Connection**
- **Download** the project directory `IJT_Console_Client` and open a terminal there.
- Install **Python 3.14+** from the [official website](https://www.python.org/downloads/) and add it to `PATH`.
- A running **OPC UA IJT Server** — see [OPC UA IJT Server Simulator](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2).

## Run
- **Note:** On Linux use `python3` instead of `python`.
### Option 1 — pass endpoint on command line
- `python setup_client.py --url="opc.tcp://<ip>:<port>"`
### Option 2 — edit config file
- Update `SERVER_URL` in `client_config.py` to the OPC UA server endpoint URL, then: `python setup_client.py`

## Testing
- Run all tests: `python run_all_tests.py`

## Project Structure
```
IJT_Console_Client/
├── setup_client.py          # Entry point — installs deps + connects
├── client_config.py         # Server URL and connection settings
├── opcua_client.py          # Core OPC UA connection management
├── event_handler.py         # OPC UA event subscription and parsing
├── result_event_handler.py  # Tightening result processing
├── utils.py                 # Shared utilities
├── requirements.txt         # Python dependencies
├── pyproject.toml           # Test configuration (pytest, ruff, coverage, bandit)
└── tests/                   # Unit and integration tests
```
