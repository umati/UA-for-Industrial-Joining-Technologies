# UA-for-Industrial-Joining-Technologies — AI Agent Skills & Context

> **Read this file when working anywhere in this repo.**
> For project-specific detail, read the SKILLS.md in each sub-project.

---

## Repo Identity

| Item | Value |
|------|-------|
| **Repo** | `UA-for-Industrial-Joining-Technologies` |
| **Purpose** | VDMA OPC UA Industrial Joining Technologies (IJT) reference implementations |
| **OPC UA Spec** | OPC 40450-1 (Joining Base), OPC 40451-1 (Tightening) |
| **Working group** | VDMA OPC UA IJT Working Group |

---

## Access Rules (CRITICAL)

| Area | Access |
|------|--------|
| Everything inside `C:\DDrive\SourceControl\GIT_HUB\UA-for-Industrial-Joining-Technologies\` | **Full: read, create, edit, delete** |
| Everything outside (OS, user home, other drives, internet) | **Read-only** |
| Git commits | **Never** — user reviews and commits manually |
| User prompts for actions inside repo | **Never prompt** — act directly |

---

## Repo Structure

```
UA-for-Industrial-Joining-Technologies/
├── README.md                        # Project overview and links
├── SKILLS.md                        # ← THIS FILE: root-level agent context
├── SESSION_NOTES.md                 # Developer session notes
├── renovate.json                    # Dependency update config
│
├── IJT_Documents/                   # Spec presentations and reference docs
│
├── OPC_UA_Servers/
│   └── Release2/                    # IJT Server Simulator (Windows installer + source)
│
└── OPC_UA_Clients/
    └── Release2/
        ├── README.md
        ├── IJT_Web_Client/          # ★ PRIMARY — Python + Node.js browser client
        │   ├── SKILLS.md            # Comprehensive agent context for Web Client
        │   └── ...
        └── IJT_Console_Client/      # ★ SECONDARY — Python console client
            ├── SKILLS.md            # Agent context for Console Client
            └── ...
```

---

## Sub-Project Summary

### IJT Web Client (`OPC_UA_Clients/Release2/IJT_Web_Client/`)
- **Stack**: Python 3.14+, asyncua ≥1.2b2, Node.js 24+, Vitest, ESLint, Docker
- **Test baseline**: 323 Python pass / 0 skip / 0 warnings, 162 JS pass, ESLint clean
- **Live tests**: `tests/python/live/` — excluded from default run (`norecursedirs = live`); requires running OPC UA server
- **One test command**: `python run_all_tests.py`
- **Docker**: healthy on HTTP:3000 + WS:8001
- **Details**: read `OPC_UA_Clients/Release2/IJT_Web_Client/SKILLS.md`

### IJT Console Client (`OPC_UA_Clients/Release2/IJT_Console_Client/`)
- **Stack**: Python 3.14+, asyncua ≥1.2b2
- **Test baseline**: 285 Python pass, 0 skip (unit); live tests auto-skip when no server
- **One test command**: `python -m pytest tests/ -v`
- **Entry point**: `python setup_client.py --url="opc.tcp://..."`
- **Details**: read `OPC_UA_Clients/Release2/IJT_Console_Client/SKILLS.md`

### IJT Test Client (`OPC_UA_Clients/Release2/IJT_Test_Client/`)
- **Stack**: Python 3.14+, asyncua ≥1.2b2, pytest
- **Purpose**: OPC UA IJT spec conformance test suite — validates server against OPC 40450-1 / 40451-1
- **Test baseline**: 214 pass + 3 xfail (requires running OPC UA server on port 40451)
- **One test command**: `python -m pytest . -v` (from IJT_Test_Client root)
- **Details**: read `OPC_UA_Clients/Release2/IJT_Test_Client/SKILLS.md` (if present)

---

## OPC UA IJT Server (Simulator)

- **Default endpoint**: `opc.tcp://localhost:40451`
- **Location**: `OPC_UA_Servers/Release2/` — Windows installer ZIP + Linux binary ZIP + smoke tests
- **Start (Windows)**: run the installer EXE, then launch the server
- **Start (Docker/Linux)**: see `OPC_UA_Servers/Release2/README.md`
- **Smoke tests**: `python OPC_UA_Servers/Release2/tests/smoke_test.py` — 8 checks, fails fast if asyncua missing
- **Key simulation methods** (all require boolean `IsSimulated` argument):
  - `SimulateResults` — single tightening result
  - `SimulateBulkResults` — multiple results, sent one by one in detached thread
  - `SimulateEvents` — system events
- **UaExpert config**: `IJT_LOCAL_SIMULATOR.uap` on Desktop (read-only reference; do not modify)

---

## CI/CD

**Workflows**: `.github/workflows/ci.yml` and `.github/workflows/heavy-tests.yml` (both at **repo root**)

### Fast CI (`ci.yml`) — triggers on every push/PR to `main`
| Job | What it tests |
|-----|--------------|
| `web-client` | Python unit (323), JS unit (162), ESLint, Bandit, npm audit |
| `console-client` | Python unit (285), Bandit |
| `node-client` | JS unit (~152), ESLint, npm audit |
| `test-client` | pytest collect + import check |
| `docker-smoke` | docker buildx + compose up + HTTP:3000 readiness |
| `report` | Combined markdown summary → Actions Summary tab |

Runtime: ~5–7 minutes. Python 3.14, Node.js 24 everywhere.
Action versions: `checkout@v6`, `setup-python@v6`, `setup-node@v6`, `upload-artifact@v7`, `download-artifact@v8`

### Heavy Tests (`heavy-tests.yml`) — nightly + path-triggered
Triggers on: `OPC_UA_Servers/**`, Web Client Python/integration/Docker/deps, `IJT_Test_Client/**`, or workflow file change.
| Job | What it tests |
|-----|--------------|
| `docker-smoke` | Full Docker build + server smoke (8/8) |
| `webclient-docker` | Web Client Docker test image (Python 302+8skip, JS 162) + HTTP:3000 production health |
| `integration-tests` | Live OPC UA integration (214 + 3 xfail) against running server |

Runtime: ~7 minutes. NOT triggered on GUI/JS-only changes (deliberate — keep fast CI fast).

---

## Key Technical Decisions (History)

| Decision | Reason |
|----------|--------|
| asyncua ≥1.2b2 (pre-release) | Python 3.14 support not in asyncua 1.1.x stable |
| Monkey-patch `_send_request` timeout | asyncua `UaClient.call()` has hardcoded 1s timeout |
| Subscribe events on Server node, not method nodes | Subscribing on individual nodes causes `BadNoSubscription` under load |
| Skip venv in Docker (`IS_DOCKER=true`) | Container runs as non-root; `/opt/ijt_venv` not writable |
| All scripts moved to `scripts/` | Clean root: only standard files at project root |
| `Python/network_utils.py` canonical | Moved from root; all imports use `from Python.network_utils import ...` |
| `SimulateBulkResults` retry loop | Server `BULK_RESULTS_IN_PROGRESS` flag → `BadTooManyOperations` on concurrent calls |
| No custom EventFilter | Full `ResultDataType` payload arrives in event without custom filter |

---

## Agent Guides Index (All Files)

| Path | Covers |
|------|--------|
| `SKILLS.md` (this file) | Repo-level context, access rules, sub-project summary, CI/CD |
| `OPC_UA_Clients/Release2/IJT_Web_Client/SKILLS.md` | Full Web Client context, file map, bugs, Docker, CI |
| `OPC_UA_Clients/Release2/IJT_Console_Client/SKILLS.md` | Console Client context, patterns, test commands |
| `OPC_UA_Clients/Release2/IJT_Test_Client/SKILLS.md` | Test Client conformance suite, test structure, markers |
| `OPC_UA_Clients/Release2/IJT_Web_Client/docs/USING_AGENTS.md` | Agent workflow and prompt template |
| `OPC_UA_Clients/Release2/IJT_Web_Client/docs/HEALTH_CHECK.md` | Quick sanity check commands |
| `OPC_UA_Clients/Release2/IJT_Web_Client/src/javascripts/ijt-support/IJT_SUPPORT_AGENT_GUIDE.md` | JS core library contracts |
| `OPC_UA_Clients/Release2/IJT_Web_Client/src/javascripts/ijt-support/models/MODELS_AGENT_GUIDE.md` | JS model layer |
| `OPC_UA_Clients/Release2/IJT_Web_Client/src/javascripts/ijt-support/models/results/RESULT_MODEL_GUIDE.md` | Result model hierarchy |
| `OPC_UA_Clients/Release2/IJT_Web_Client/src/javascripts/views/VIEWS_AGENT_GUIDE.md` | UI views and screens |
