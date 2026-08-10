# IJT Web Client

GUI reference client for visualizing OPC UA IJT server data, events, traces, assets, and results in
a web browser. The backend is Python with WebSockets. The frontend is Node.js.

## Contact

- **Author:** Joakim Gustafsson - joakim.h.gustafsson@atlascopco.com
- **Coordinator:** Mohit Agarwal - mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
- Use the local `.python-version` file to match CI exactly.
- Node.js 24.15+
- Use the repo-root `.nvmrc` to stay aligned with CI patch updates in major 24.
- Internet connection for first-time dependency installation
- Docker, only if using the Docker option
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)
  - Default OPC UA endpoint: `opc.tcp://localhost:40451`

## Option 1 - Local Setup

- **Run:** `python setup_project.py`
  - Ctrl+C stops managed processes cleanly.
  - Detached mode: `python setup_project.py --detach`
  - Clean rebuild: `python setup_project.py --force_full`
  - Status: `python setup_project.py --status`
  - Stop detached services: `python setup_project.py --stop`
  - Access: `http://localhost:3000`

## Local configuration files

- Git tracks default templates under `src/resources/`:
  - `connectionpoints.default.json`
  - `settings.default.json`
- The backend creates local runtime files from those templates when missing:
  - `connectionpoints.json`
  - `settings.json`
- Runtime files are ignored by Git. You can add personal OPC UA endpoints or UI settings locally without pushing them.
- Direct setup restores the `LOCAL` profile from `connectionpoints.default.json`
  (`opc.tcp://localhost:40451`) while preserving additional personal endpoints.
  Test runners use separate runtime-resource directories and never persist their
  dedicated ports into this normal profile.
- To reset all local configuration, delete the runtime JSON file and restart the Web Client backend.

## Endpoint readiness in the browser

Endpoint tabs show a compact readiness pill near the endpoint URL:

- **Ready** means the endpoint is usable for IJT work: OPC UA connection is established, event/result subscription is active, and the IJT Tightening System was discovered.
- **Connecting** means the app is still preparing the endpoint.
- **Limited** means OPC UA is connected but subscription or IJT model discovery is incomplete.
- **Disconnected** means the endpoint is not connected.

Click the pill to expand **Readiness diagnostics**. The popup keeps that title
visually separate from the Connection, Subscription, and IJT Tightening System
rows so the checks read as diagnostics, not another tab or primary workflow.
The former full Connection tab is intentionally not shown by default.

## Option 2 - Docker

- **Run with Docker helper:** `python run_docker_setup.py`
  - Manual build from repo root: `docker build -f OPC_UA_Clients/Release2/IJT_Web_Client/Dockerfile -t ijt_web_client .`
  - Manual run: `docker run --rm -d -p 3000:3000 -p 8001:8001 ijt_web_client`
  - Access: `http://localhost:3000`

## Option 3 - WSL

- **Run in WSL:** `RUN_PROJECT_SETUP=1 bash scripts/bootstrap_wsl.sh`
  - Set endpoint when the OPC UA server runs on Windows: `export OPCUA_SERVER_URL="opc.tcp://<windows-host-or-ip>:40451"`
  - Start services: `python3 setup_project.py --detach`
  - Access: `http://localhost:3000`

## Testing

- **Run tests:** `python run_all_tests.py`
- For advanced contributor workflows and CI behavior details, see [`docs/DEVELOPMENT_GUIDE.md`](./docs/DEVELOPMENT_GUIDE.md).

## Methods page behavior

- Method input and output labels follow the connected server.
- `ProductInstanceUri` defaults are resolved and retained independently for each active server.
- Method results remain visible as structured output in the Results view.
- `Uncertain` and Bad method responses retain any Status, StatusMessage, or
  other output arguments returned by the server.
- Backend records for server-specific operations include the OPC UA endpoint,
  so concurrent server activity can be distinguished in the console.

### Browser test prerequisites (optional)

- For local browser E2E checks, install Chromium once: `npx playwright install chromium`.
- If your network uses a proxy or mirror, configure Playwright download environment variables accordingly.
- CI-specific browser execution details are documented in [`docs/TEST_TIERS.md`](../../../docs/TEST_TIERS.md).
