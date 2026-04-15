# IJT Web Client

## Contact
- **Author:** Joakim Gustafsson — joakim.h.gustafsson@atlascopco.com
- **Coordinator:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Overview
- GUI reference client for visualization of IJT data and traces from an OPC UA server. Python backend (`opcua-asyncio` + WebSockets) and Node.js frontend.

## Prerequisites
- **Internet Connection**
- **Download** the project directory `IJT_Web_Client` and open a terminal there.
- Install **Python 3.14+** and **Node.js 24+** from the official websites and add them to `PATH`.
- Docker installed and running (required for the Docker setup option).

## OPC UA Server
- Use the [**OPC UA IJT Server Simulator**](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2) to connect from the **IJT Web Client**.

## Option 1 — Local Setup Script

- **Run:** `python setup_project.py` — Ctrl+C stops managed processes cleanly
- **Detached Mode:** `python setup_project.py --detach` — exit the terminal for cleanup
- **Clean Rebuild:** `python setup_project.py --force_full`
- **Status:** `python setup_project.py --status`
- **Stop:** `python setup_project.py --stop`

## Option 2 — Docker

- **Note:** Use `python3` on Linux instead of `python`.
- **Automated:** `python run_docker_setup.py`
- **Manual:**
  - Build: `docker build -t ijt_web_client .`
  - Run: `docker run --name ijt_web_client -d -p 3000:3000 -p 8001:8001 ijt_web_client`
- **Access:** `http://localhost:3000` or the URL shown in the terminal.

## Option 3 — WSL (Ubuntu)

- Open a terminal and change to the `IJT_Web_Client` directory.
- Install WSL dependencies and run setup: `RUN_PROJECT_SETUP=1 bash scripts/bootstrap_wsl.sh`
- Launch the OPC UA IJT Server Simulator manually on Windows.
- Set endpoint to a Windows-reachable IP: `export OPCUA_TEST_ENDPOINT="opc.tcp://<windows-host-or-ip>:40451"`
- Start web client services: `python3 setup_project.py --detach`
- Open in Windows browser: `http://localhost:3000`
