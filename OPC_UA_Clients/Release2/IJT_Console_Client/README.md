# IJT Console Client

## Contact
- **Author:** Mohit Agarwal: mohit.agarwal@atlascopco.com

## Overview
- This application uses the open source OPC UA Python `opcua-asyncio` stack.
- This is a minimal **reference client** based on the **OPC UA Industrial Joining Technologies (IJT) Companion Specification**.
- Demonstrates: connecting to a live OPC UA IJT server, subscribing to events (tightening results), calling simulation methods, and reading result data.

## Prerequisites
-  **Internet Connection**
-  **Download** the project directory: **`IJT_Console_Client`** and launch a terminal from the project directory.
-  **Install** **Python 3.14 or higher** from the **official** **website** and **add** the installation directory to the system **PATH**.
-  A running **OPC UA IJT Server** — see [OPC UA IJT Server Simulator](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2).

## Run the client application
- **Note:** On Linux, the command should be **python3** instead of **python**.
### Option 1 — pass endpoint on command line
```bash
python setup_client.py --url="opc.tcp://<ip>:<port>"
```
### Option 2 — edit config file
- **Update** the **SERVER_URL** in **`client_config.py`** to the OPC UA Server EndpointUrl.
```bash
python setup_client.py
```

## Testing
- **All unit tests:**
  ```bash
  python -m pytest tests/ -v
  ```
- **With a live OPC UA server** (set endpoint first):
  ```bash
  set OPCUA_TEST_ENDPOINT=opc.tcp://<host>:<port>
  python -m pytest tests/ -m live -v
  ```
- **Install test dependencies first** (if not already installed):
  ```bash
  pip install pytest pytest-asyncio
  ```

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
├── pytest.ini               # Test configuration
└── tests/                   # Unit and integration tests
```
