# IJT Web Client

## Contact
- **Author:** Joakim Gustafsson: joakim.h.gustafsson@atlascopco.com
- **Coordinator:** Mohit Agarwal: mohit.agarwal@atlascopco.com

## Overview
- This is a **reference** OPC UA Client application to **demonstrate** the **usage** of getting data from the **OPC UA Server** based on the **OPC UA Industrial Joining Technologies (IJT)**. It has the following modules.
  - Python backend using `opcua-asyncio` and WebSockets.
  - Node.js frontend for visualizing and interacting with IJT OPC UA data.

## Prerequisites
-  **Internet Connection**
-  **Download** the project directory: **`IJT_Web_Client`** and launch a terminial from the project directory.
-  **Install** **Python 3.14+** (recommended: 3.14.x) and **Node.js 24.x** from the **official** websites and add them to `PATH`.
- Ensure that Docker is installed and running **for** Docker Option.


  
## IJT Web Client - Option 1 - Automated Local Setup Script Guide

- **Run the Setup Script:**
    ```bash
    python setup_project.py
    ```
- **Default run is foreground-managed; Ctrl+C stops managed processes cleanly:**
   ```bash
   python setup_project.py
   ```
- **Run detached (old behavior):**
   ```bash
   python setup_project.py --detach
   ```
- **Show/stop managed local frontend+backend processes:**
   ```bash
   python setup_project.py --status
   python setup_project.py --stop
   ```
- **Clean Rebuild:**
   ```bash
   python setup_project.py --force_full
   ```
- **Run regression tests (autonomous `venv_test` bootstrap):**
   ```bash
   python setup_project.py --run-tests
   ```
- **Run integration tests (autonomous `venv_test` bootstrap; requires `OPCUA_TEST_ENDPOINT`):**
   ```bash
   python setup_project.py --integration-tests
   ```

## IJT Web Client - Option 2 - Docker Setup Guide
- **Note:** Use **python3** on **Linux** instead of **python**
- **Automated Docker Setup:**
  ```bash
  python run_docker_setup.py
  ```
- **Manual Docker Setup:**
    - **Build the Docker Image:**
      ```bash
      docker build -t ijt_web_client .
      ```
    - **Run the Container:**
      ```bash
      docker run --name ijt_web_client -d -p 3000:3000 -p 8001:8001 ijt_web_client
       ```
- **Access the Application:** Go to **http://localhost:3000** or the **URL shown** in the command line.

## OPC UA Server
- Use the following [**OPC UA IJT Server Simulator**](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2) to connect from the **IJT Web Client**.

## Testing
- Tests and regression scripts auto-create/use `venv_test` and auto-install Python prerequisites (`requirements.txt` + `requirements-dev.txt`).
- Run backend tests (mocked/unit style):
  ```bash
  python scripts/run_tests.py
  ```
- Run docker setup smoke tests (includes local-mode pass-through checks for `run_docker_setup.py`):
  ```bash
  python scripts/run_tests.py --docker-tests
  ```
- Run docker setup live validation (build + compose up, no log tail):
  ```bash
  python scripts/run_tests.py --docker-tests --live-docker
  ```
- Run integration tests against a live OPC UA server:
  ```bash
  set OPCUA_TEST_ENDPOINT=opc.tcp://<host>:<port>
  python scripts/run_tests.py --integration
  ```
- Run functional regression directly (also autonomous test env bootstrap):
  ```bash
  python scripts/run_regression.py --endpoint opc.tcp://localhost:40451 --ws-url ws://localhost:8001
  ```
## WSL Setup
- If WSL is already opened in `IJT_Web_Client`, no `cd` is required.
- Run one command to bootstrap WSL dependencies and fixes:
  ```bash
  bash scripts/bootstrap_wsl.sh
  ```
- Optional: bootstrap and also run project setup automatically:
  ```bash
  RUN_PROJECT_SETUP=1 bash scripts/bootstrap_wsl.sh
  ```
- For WSL usage, launch the OPC UA IJT Server Simulator manually on Windows.
- Set endpoint in WSL to a Windows-reachable host/IP (recommended once in `~/.bashrc`):
  ```bash
  export OPCUA_TEST_ENDPOINT="opc.tcp://<windows-host-or-ip>:40451"
  ```
- Start web client services from WSL:
  ```bash
  python3.14 setup_project.py --detach
  ```
- Open UI from Windows browser:
  ```text
  http://localhost:3000
  ```
- Optional validation from WSL:
  ```bash
  python3.14 scripts/run_tests.py
  python3.14 scripts/run_regression.py --endpoint "$OPCUA_TEST_ENDPOINT"
  python3.14 scripts/run_cross_client_regression.py --endpoint "$OPCUA_TEST_ENDPOINT"
  ```