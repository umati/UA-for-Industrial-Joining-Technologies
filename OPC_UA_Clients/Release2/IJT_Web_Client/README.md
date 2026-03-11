# IJT Web Client

## Contact
- Author: Joakim Gustafsson (joakim.h.gustafsson@atlascopco.com)
- Coordinator: Mohit Agarwal (mohit.agarwal@atlascopco.com)

## Overview
- Python backend using `opcua-asyncio` and WebSockets.
- Node.js frontend for visualizing and interacting with IJT OPC UA data.
- Reference OPC UA client for the Industrial Joining Technologies (IJT) companion specification.

## Project Map
- Backend entry point: `index.py`
- Python modules: `Python/`
- Frontend source: `Javascripts/`
- Static assets: `Resources/`
- Node config: `package.json`, `eslint.config.mjs`
- Python dependencies: `requirements.txt`

## Prerequisites
- Internet connection (for first-time dependency installation).
- Python 3.10+ available on `PATH`.
- Node.js 22.16+ available on `PATH`.
- Optional: Docker Desktop (only for Docker workflow).

## Quick Start (Local)
Run from the project root:

```bash
python setup_project.py
```

If you want a clean rebuild:

```bash
python setup_project.py --force_full
```

Manual setup alternative:

```bash
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
```

Start backend:

```bash
venv\Scripts\python.exe index.py
```

Start frontend (new terminal):

```bash
npm run start
```

Expected endpoints:
- Frontend: `http://localhost:3000`
- Backend WebSocket: `ws://localhost:8001`

## Health Check
Run these before and after code changes:

```bash
npm run lint
venv\Scripts\python.exe -m pip check
venv\Scripts\python.exe index.py
npm run start
```

Expected results:
- `npm run lint` exits with code 0.
- `pip check` reports no broken requirements.
- Backend starts and logs WebSocket startup on port `8001`.
- Frontend responds on `http://localhost:3000`.

## Using Agents To Improve Code

### What To Include In Every Agent Request
- Goal: bug fix, refactor, performance, cleanup, or docs.
- Scope: exact files/folders allowed to change.
- Constraints: behavior change allowed or not, coding style constraints.
- Validation: commands the agent must run (`lint`, startup checks).
- Output: required summary format (changed files, risks, follow-up).

### Recommended Prompt Template
```text
Goal:
Scope:
Constraints:
Validation commands:
Definition of done:
```

### Definition Of Done (Agent Tasks)
- Changes stay inside approved scope.
- `npm run lint` passes.
- Backend starts (`index.py`).
- Frontend starts (`npm run start`).
- Agent reports changed files and remaining risks.

### Guardrails
- Do not edit `venv/` or `node_modules/`.
- Do not change Docker setup unless explicitly requested.
- Prefer minimal, targeted edits over broad rewrites.
- If runtime behavior might change, explain assumptions and impact.

## Common Agent Tasks
- Fix lint errors and keep behavior unchanged.
- Repair broken local environment (`venv`, missing dependencies).
- Add small, focused refactors with health-check verification.
- Improve docs and setup reliability.

## Docker Setup (Optional)
Use `python3` instead of `python` on Linux.

Automated Docker setup:

```bash
python run_setup.py
```

Manual Docker setup:

```bash
docker build -t ijt_web_client .
docker run --name ijt_web_client -d -p 3000:3000 -p 8001:8001 ijt_web_client
```

Access at `http://localhost:3000`.

## OPC UA Server
Use the OPC UA IJT Server Simulator from:
- https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2
