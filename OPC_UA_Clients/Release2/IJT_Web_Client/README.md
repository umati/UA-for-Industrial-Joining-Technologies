# IJT Web Client

GUI reference client for visualizing OPC UA IJT server data, events, traces, assets, and results in
a web browser. The backend is Python with WebSockets. The frontend is Node.js.

## Contact

- **Author:** Joakim Gustafsson - joakim.h.gustafsson@atlascopco.com
- **Coordinator:** Mohit Agarwal - mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
- Node.js 24+
- Internet connection for first-time dependency installation
- Docker, only if using the Docker option
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)
  - Default OPC UA endpoint: `opc.tcp://localhost:40451`

### Prerequisites for local browser tests

- Local Playwright browser tests need Chromium downloaded from `https://cdn.playwright.dev` over HTTPS.
- On corporate networks, set `HTTPS_PROXY` for the proxy path or `PLAYWRIGHT_DOWNLOAD_HOST` for an approved mirror before running `npx playwright install chromium`.
- For offline machines, prepopulate a browser cache and set `PLAYWRIGHT_BROWSERS_PATH` to that mirror/cache location.
- For CI-equivalent browser dependencies, the Integration `live-webclient-browser` job runs each suite **inside** the owned `ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci` image (digest pinned via [`.github/docker/ijt-browser-ci/image-pin.json`](../../../.github/docker/ijt-browser-ci/image-pin.json)) started with `docker run --network=none`; Chromium and its Linux system dependencies are baked into the image at build time against the locked `@playwright/test` version in [`package.json`](./package.json). Local Linux developers can reproduce the same browser/system-deps surface via `npx playwright install chromium --with-deps`, but local Web E2E itself does **not** require Docker or GHCR access. See [`docs/TEST_TIERS.md`](../../../docs/TEST_TIERS.md) for the full tier description.

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
- To reset local configuration, delete the runtime JSON file and restart the Web Client backend.

## Option 2 - Docker

- **Run with Docker helper:** `python run_docker_setup.py`
  - Manual build from repo root: `docker build -f OPC_UA_Clients/Release2/IJT_Web_Client/Dockerfile -t ijt_web_client .`
  - Manual run: `docker run --rm -d -p 3000:3000 -p 8001:8001 ijt_web_client`
  - Access: `http://localhost:3000`

## Option 3 - WSL

- **Run in WSL:** `RUN_PROJECT_SETUP=1 bash scripts/bootstrap_wsl.sh`
  - Set endpoint when the OPC UA server runs on Windows: `export OPCUA_TEST_ENDPOINT="opc.tcp://<windows-host-or-ip>:40451"`
  - Start services: `python3 setup_project.py --detach`
  - Access: `http://localhost:3000`

## Testing

- **Run tests:** `python run_all_tests.py`

### Optional private Envelope module

The Envelope view is an optional private Git submodule mounted at:

```text
src\javascripts\views\envelope
```

Public IJT checkouts continue to work when this private module is absent. The Web Client runner defaults to:

```powershell
python run_all_tests.py --private-modules skip
```

`skip` keeps public/local baseline validation deterministic. In `auto` mode,
private Envelope checks run only when the submodule is checked out locally.
Use `--private-modules require` when an authorized developer or private CI job
must fail if the Envelope module is missing.

The submodule is configured as opt-in for Git updates, so a normal IJT pull does not require private Envelope access. Authorized developers can initialize it through `python setup_project.py` or, from the IJT repo root, explicitly with:

```powershell
git submodule update --checkout --init --recursive -- OPC_UA_Clients\Release2\IJT_Web_Client\src\javascripts\views\envelope
```

Authorized developers who want their local Git client to update Envelope during recursive pulls can opt in locally after authenticating to the private repo:

```powershell
git config submodule.OPC_UA_Clients/Release2/IJT_Web_Client/src/javascripts/views/envelope.update checkout
git config submodule.recurse true
```

That local config should not be committed; the shared IJT default remains safe for public users.
