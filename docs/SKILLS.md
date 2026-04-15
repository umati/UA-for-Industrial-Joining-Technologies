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

## Developer Setup & Hygiene

### Pre-Commit Hooks — Auto-Fix on Every Commit

This repo uses [pre-commit](https://pre-commit.com/) to automatically fix formatting and line-ending issues **before any commit is recorded**. Most hooks are auto-fixers — they silently reformat files so the commit succeeds on the second attempt.

> **Detector hooks that block by design**: `check-json`, `check-yaml`, `check-toml` (config syntax errors), `check-merge-conflict` (stray `<<<<<<<`), `debug-statements` (stray `breakpoint()`). These require manual fixes before committing.

**First-time setup** (once per machine, per clone):
```sh
pip install pre-commit          # or: pip install -r requirements-dev.txt
pre-commit install              # installs hooks into .git/hooks/
```
The three Python runners (Console, Web, Test) call `pre-commit install` automatically on first run. For CSharp, Node, and Server runners — or direct git use — run it manually once after cloning.

**What happens on `git commit`:**
1. `ruff-format` rewrites Python files with wrong indentation/quotes/blank-lines
2. `ruff --fix` applies safe lint fixes
3. `end-of-file-fixer` and `mixed-line-ending` normalise LF/CRLF
4. `trailing-whitespace` strips trailing spaces

If any hook modifies files, the commit is aborted. **Run `git add -u && git commit` again** — fixed files are already staged.

**Auto-generated files excluded**: `OPC_UA_Clients/Release2/IJT_CSharp_Client/Types/` is excluded from all hooks (set in `.pre-commit-config.yaml` and root `pyproject.toml`). Never edit those files manually.

---

### Virtual Environment Naming Convention

Each Python project creates two independent environments:

| Directory | Created by | Contents | Typical use |
|-----------|-----------|----------|-------------|
| `.venv` | `setup_client.py` / `setup_project.py` | `requirements.txt` only | `python main.py` / standalone launch (Windows, Linux, macOS, WSL) |
| `.venv_test` | `run_all_tests.py` | `requirements.txt` + `requirements-dev.txt` | Test runs, CI |
| `/opt/ijt_venv` | Docker `ENTRYPOINT` | `requirements.txt` | Docker container runtime |

> **WSL**: `bootstrap_wsl.sh` calls `setup_project.py` after OS provisioning — uses `.venv` like every other host.

**Rule**: never activate `.venv_test` to run the application, and never run tests inside `.venv`.

Both `setup_*.py` and `run_all_tests.py` remove stale legacy directories (`venv/`, `venv_test/`, `env/`, `ENV/`, `.venv_backup/`) on startup. A fresh clone always starts clean automatically.

---

### Running Tests — Project Isolation Rule

**Always run tests from each project's own directory — never from repo root.**

```sh
# ✅ Correct — run from project directory
cd OPC_UA_Clients/Release2/IJT_Web_Client && pytest tests/python/unit
cd OPC_UA_Clients/Release2/IJT_Console_Client && pytest tests/unit

# ❌ Wrong — from repo root, both conftest.py files collide
pytest OPC_UA_Clients/Release2/IJT_Web_Client/tests OPC_UA_Clients/Release2/IJT_Console_Client/tests
```

Running multiple Python clients together in a single root `pytest` invocation causes `ImportPathMismatchError` because both trees have `tests/conftest.py`. The CI workflows and `run_all_tests.py` both enforce per-project `working-directory`.

**For local full-suite runs**: Use each project's `run_all_tests.py` from its own directory, or the repo root orchestrator which delegates each runner with the correct `cwd`.

---

### Pytest Temp Root Policy

| Project | `addopts` | Notes |
|---------|-----------|-------|
| `IJT_Console_Client` | `-v --basetemp=tmp/pytest` | Project-local pytest session dirs |
| `IJT_Test_Client` | `-v --basetemp=tmp/pytest -p no:cacheprovider` | Project-local + cache provider disabled to prevent `pytest-cache-files-*` accumulation |
| `IJT_Web_Client` | `-v -p no:cacheprovider` | System temp; `cacheprovider` disabled to prevent ACL churn |

`tmp/` is gitignored in each project. `tmp_path_retention_policy = "failed"` retains artifacts only for failing tests.

The Web client's `local_temp_dir` fixture (used in `test_ijt_interface.py`) writes to `.state/tmp/test-fixtures/{uuid}` with explicit `yield`/`finally` cleanup — excluded from Docker build context via `.dockerignore`.

---

### Automatic Cleanup — post-run

Every `run_all_tests.py` calls `_cleanup_caches()` after writing reports. Cleanup is **self-contained** — each runner only cleans its own directory tree.

| Runner | Scope | Removes |
|--------|-------|---------|
| Sub-project runners | Own project dir (recursive) | `__pycache__`, `.ruff_cache`, `.mypy_cache`, `.coverage*`, `*.pyc` |
| Root orchestrator | Repo root only (non-recursive) | Same + `pki/`, `PKI/` |

`.pytest_cache` is cleaned post-run (regenerates on next run; `--lf`/`--ff` only work within the same session). Always preserved: `test-results/` (reports).

---

### pyfakefs — Filesystem-Touching Unit Tests

`IJT_Console_Client` and `IJT_Web_Client` use **`pyfakefs`** for all unit tests that simulate virtual environment layouts. The `fs` fixture intercepts `pathlib`, `os`, `shutil`, and `zipfile` calls in-process — no real files are written for those tests, eliminating OS ACL issues on Windows (writing `.venv/Scripts/python.exe` can trigger security policies that lock containing directories).

```python
# After — all filesystem ops are in-memory, no real disk writes
def test_finds_direct_exe(self, fs, monkeypatch):
    exe = Path("/fake/sim") / sc.SIMULATOR_EXE_NAME
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"fake exe")
```

`pyfakefs~=6.1` is in `requirements-dev.txt` for both Console and Web clients. Works identically on Windows, Linux, and macOS.

The `tests/fixtures/` directory is created at runtime by `conftest.py` (`pytest_configure`) — no `.gitkeep` needed.

---

### Coverage Configuration

Coverage is configured in each project's `pyproject.toml`. **Never hardcode thresholds in runner scripts** — config files are the version-controlled source of truth.

| Project | `fail_under` | Notes |
|---------|-------------|-------|
| Web Client | 70% | Unit run achieves ~74% |
| Console Client | 80% | Unit run achieves ~85% |
| Test Client | 70% | No `tests/unit/`; threshold applies to live conformance stage |

Docstring coverage (`interrogate`) thresholds — calibrated against real codebase with venvs excluded:

| Project | `fail-under` | Notes |
|---------|-------------|-------|
| Console Client | 25% | Honest floor; tests included in scan |
| Web Client | 42% | Honest floor; tests included in scan |
| Test Client | 65% | Higher bar; source is well-documented |

---

### Windows-Locked Temp Directories

On Windows, pyfakefs and pytest can leave directories with restricted ACLs that survive test teardown. Built-in protections already in place:

| Protection | Mechanism |
|-----------|-----------|
| `_force_rmtree(path)` | All 7 runners + 2 setup scripts — `shutil.rmtree(onexc=...)` with `os.chmod` retry |
| `[tool.mypy] exclude` | Skips `pytest-cache-files-*` before mypy walks into them |
| `norecursedirs` | pytest never collects from `pytest-cache-files-*` or `tmp` |
| `-p no:cacheprovider` (Web + Test Client) | Prevents `pytest-cache-files-*` creation entirely |
| `.dockerignore` | `tests/fixtures/tmp/` excluded from Docker build context |

If a locked dir survives a run it sits inert — tools skip it, Docker ignores it. It clears automatically on the next machine restart (Windows releases file handles on reboot).

---

### Manual Deep Clean

```bash
git clean -fdXn                                                              # preview first
git clean -fdX -e 'venv' -e '.venv*' -e 'node_modules' -e 'OPC_UA_IJT_Server_Simulator*'
```

`-X` removes only gitignored files — never touches committed or untracked files.

| Item | Why preserved |
|------|--------------|
| `venv/`, `.venv*` | Python environments — slow to recreate |
| `node_modules/` | npm cache — slow to recreate |
| `OPC_UA_IJT_Server_Simulator*` | Large extracted binary |

---

## Repo Structure

```
UA-for-Industrial-Joining-Technologies/
├── README.md                        # Project overview and links
├── SECURITY.md                      # GitHub security policy (must stay at root)
├── docs/
│   └── SKILLS.md                    # ← THIS FILE: root-level agent context
├── run_all_tests.py                 # Root orchestrator — runs all project suites
├── renovate.json                    # Dependency update config
│
├── IJT_Documents/                   # Spec presentations and reference docs
│
├── OPC_UA_Servers/
│   └── Release2/                    # IJT Server Simulator (Windows + Linux binary + Docker)
│       ├── README.md                # End-user setup guide
│       ├── run_all_tests.py         # Server test runner (hadolint, trivy, smoke)
│       └── docs/SKILLS.md          # Server agent context
│
└── OPC_UA_Clients/
    ├── Release1/
    │   └── IJT_Node_Client/         # Node.js OPC UA browser client
    │       ├── docs/SKILLS.md
    │       └── run_all_tests.py
    └── Release2/
        ├── README.md
        ├── IJT_Web_Client/          # ★ PRIMARY — Python + Node.js browser client
        │   ├── docs/SKILLS.md       # Comprehensive agent context for Web Client
        │   └── run_all_tests.py
        ├── IJT_Console_Client/      # Python console client
        │   ├── docs/SKILLS.md
        │   └── run_all_tests.py
        ├── IJT_Test_Client/         # OPC UA IJT spec conformance test suite
        │   ├── docs/SKILLS.md
        │   └── run_all_tests.py
        └── IJT_CSharp_Client/       # C# .NET OPC UA client
            ├── docs/SKILLS.md
            └── run_all_tests.py
```

---

## Sub-Project Summary

### IJT Web Client (`OPC_UA_Clients/Release2/IJT_Web_Client/`)
- **Stack**: Python 3.14+, asyncua ≥1.2b2, Node.js 24+, Vitest, ESLint, Docker
- **Test baseline**: 310 Python pass / 0 skip / 0 warnings, 229 JS pass (162 unit + 67 source-coverage), ESLint clean
- **Live tests**: `tests/python/live/` — excluded from default run (`norecursedirs = live`); requires running OPC UA server
- **One test command**: `python run_all_tests.py`
- **Docker**: healthy on HTTP:3000 + WS:8001
- **Details**: read `OPC_UA_Clients/Release2/IJT_Web_Client/docs/SKILLS.md`

### IJT Console Client (`OPC_UA_Clients/Release2/IJT_Console_Client/`)
- **Stack**: Python 3.14+, asyncua ≥1.2b2
- **Test baseline**: 374 Python pass, 0 skip (unit); live tests call `pytest.fail()` if server unreachable — no silent skips
- **One test command**: `python run_all_tests.py` (auto-launches server if needed)
- **Entry point**: `python setup_client.py --url="opc.tcp://..."`
- **Details**: read `OPC_UA_Clients/Release2/IJT_Console_Client/docs/SKILLS.md`

### IJT Test Client (`OPC_UA_Clients/Release2/IJT_Test_Client/`)
- **Stack**: Python 3.14+, asyncua ≥1.2b2, pytest
- **Purpose**: OPC UA IJT spec conformance test suite — validates server against OPC 40450-1 / 40451-1
- **Test baseline**: dynamic (depends on server profile and enabled optional features); requires running OPC UA server on port 40451
- **One test command**: `python run_all_tests.py` (auto-launches server if needed)
- **Details**: read `OPC_UA_Clients/Release2/IJT_Test_Client/docs/SKILLS.md`

### IJT CSharp Client (`OPC_UA_Clients/Release2/IJT_CSharp_Client/`)
- **Stack**: C# .NET 10+, OPC Foundation UA SDK, xUnit, Moq, coverlet
- **Purpose**: C# reference OPC UA IJT client — events, results, assets, joining process, and joint management
- **Architecture**: `JoiningSystem` holds `ISession` (OPC UA SDK) directly; no wrapper. `IJoiningSystem` is the interface for management classes and Moq mocks. `IjtSession`/`IIjtSession` do not exist.
- **Test baseline**: **420 unit tests** pass · 0 failed · 0 skipped
- **One test command**: `python run_all_tests.py` (dotnet build + test + NuGet CVE scan)
- **Live tests**: skipped unless `OPCUA_SERVER_URL` is set or `OPCUA_SIMULATOR_EXE` points to server binary
- **Details**: read `OPC_UA_Clients/Release2/IJT_CSharp_Client/docs/SKILLS.md`

### IJT Node Client (`OPC_UA_Clients/Release1/IJT_Node_Client/`)
- **Stack**: Node.js 24+, node-opcua, Socket.io, Vitest
- **Purpose**: Node.js + browser OPC UA IJT client (Release 1)
- **One test command**: `python run_all_tests.py` (npm ci + vitest + eslint + npm audit)
- **Details**: read `OPC_UA_Clients/Release1/IJT_Node_Client/docs/SKILLS.md`

---

## OPC UA IJT Server (Simulator)

- **Default endpoint**: `opc.tcp://localhost:40451`
- **Location**: `OPC_UA_Servers/Release2/` — Windows installer ZIP + Linux binary ZIP + smoke tests
- **Start (Windows)**: run `opcua_ijt_demo_application.exe` as Administrator
- **Start (Linux)**: `chmod +x opcua_ijt_demo_application && ./opcua_ijt_demo_application`
- **Start (Docker)**: `docker compose up` from `OPC_UA_Servers/Release2/`
- **Smoke tests**: `python OPC_UA_Servers/Release2/tests/smoke_test.py` — 10 checks, fails fast if asyncua missing; pass `--junitxml PATH` to emit JUnit XML for CI reporting
- **Key simulation methods** (all require boolean `IsSimulated` argument):
  - `SimulateResults` — single tightening result
  - `SimulateBulkResults` — multiple results, sent one by one in detached thread
  - `SimulateEvents` — system events
- **UaExpert config**: `IJT_LOCAL_SIMULATOR.uap` on Desktop (read-only reference; do not modify)
- **Details**: read `OPC_UA_Servers/Release2/docs/SKILLS.md`

### Server Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPCUA_SERVER_PORT` | `40451` | Override port — used by CI to run parallel isolated instances |
| `OPCUA_HOSTNAME` | `localhost` | Override advertised hostname — used for Docker with remote clients |

---

## CI/CD

**Workflows**: `.github/workflows/ci-required.yml`, `.github/workflows/ci-extended.yml`, and `.github/workflows/codeql.yml` (all at **repo root**)

### CI Required (`ci-required.yml`) — triggers on every push/PR to `main`
| Job | What it tests |
|-----|--------------|
| `web-client` | Python unit (310), JS unit (229), ESLint, Bandit, npm audit |
| `console-client` | Python unit tests (tests/unit/), Bandit, Ruff, mypy |
| `node-client` | JS unit (~152), ESLint, npm audit |
| `test-client` | pytest collect-only (import check), Bandit, Ruff, mypy |
| `csharp-client` | dotnet build + test (`--blame-hang 60s`) + NuGet CVE scan; phase1 unit/static (`IJT_PHASE1_ONLY=true`) + phase2 live tests against server (port 40451) |
| `server-smoke-windows` | Windows native EXE smoke test (port 40451) |
| `report` | Downloads all artifacts · publishes dorny/test-reporter Checks tab (per-test drill-down) · writes summary table to Actions Summary with full pass · fail · skip counts · artifact sanity gate warns on missing XMLs · `continue-on-error` on all dorny steps (fork PR safe) |

Runtime: ~5–7 minutes. Python 3.14, Node.js 24, .NET 10 everywhere.
Action versions: `checkout@v6`, `setup-python@v6`, `setup-node@v6`, `setup-dotnet@v5`, `upload-artifact@v7`, `download-artifact@v8`
All jobs have explicit `timeout-minutes` (5–30 min) and `permissions: contents: read` (plus `checks: write` where dorny/test-reporter runs inline).

### CodeQL (`codeql.yml`) — triggers on every push/PR to `main` + weekly
Advanced Setup (GitHub Default Setup disabled). Uses `security-extended` queries.
| Language | Build method | Notes |
|----------|-------------|-------|
| C# | `dotnet build` (manual) | Types/ generated code excluded via `paths-ignore` in `codeql-config.yml` |
| Python | autobuild | venv, node_modules, __pycache__ excluded |
| JavaScript | autobuild | node_modules excluded |

### Port Ownership

| Job | Workflow | Port | Protocol |
|-----|----------|------|----------|
| `csharp-client` | `ci-required.yml` | 40451 | Windows native EXE |
| `server-smoke-windows` | `ci-required.yml` | 40451 | Windows native EXE |
| `server-smoke-docker` | `ci-extended.yml` | 40451 | Docker (Linux) |
| `int-testclient` | `ci-extended.yml` | 40451 | Windows native EXE |
| `int-live-others` | `ci-extended.yml` | 40451 | Windows native EXE |

> Release1 Node Client always uses 40451 (fixed — no dynamic port support). Release2 clients all use 40451 in ci-extended. The old per-job isolated Docker ports (40452–40455) are no longer used in CI.

### CI Extended (`ci-extended.yml`) — nightly + path-triggered
Triggers on: `OPC_UA_Servers/**`, Web Client Python/integration/Docker/deps, `IJT_Test_Client/**`, or workflow file change.
| Job | What it tests |
|-----|--------------|
| `docker-smoke` | Full Docker build + server smoke (10/10) |
| `webclient-docker` | Web Client Docker test image (Python 310 unit, JS 229) + HTTP:3000 production health |
| `int-testclient` | Windows live: Test Client full suite against running server (counts vary by server profile/features) |
| `int-live-others` | Windows live: Web Client integration (13 tests) + Console Client live tests |

Runtime: ~10 minutes (int-testclient + int-live-others run in parallel). NOT triggered on GUI/JS-only changes (deliberate — keep fast CI fast).
All jobs have explicit `timeout-minutes` (5–45 min) and `permissions: contents: read`.

---

## Key Technical Decisions (History)

| Decision | Reason |
|----------|--------|
| asyncua ≥1.2b2 (pre-release) | Python 3.14 support not in asyncua 1.1.x stable |
| Monkey-patch `_send_request` timeout | asyncua `UaClient.call()` has hardcoded 1s timeout |
| Subscribe events on Server node, not method nodes | Subscribing on individual nodes causes `BadNoSubscription` under load |
| Skip venv in Docker (`IS_DOCKER=true`) | Container runs as non-root; `/opt/ijt_venv` not writable |
| No `scripts/` at repo root | Each project owns its own helpers; nothing shared at root level |
| `Python/network_utils.py` canonical | Moved from root; all imports use `from Python.network_utils import ...` |
| `SimulateBulkResults` retry loop | Server `BULK_RESULTS_IN_PROGRESS` flag → `BadTooManyOperations` on concurrent calls |
| No custom EventFilter | Full `ResultDataType` payload arrives in event without custom filter |
| C# live-test sync OPC UA calls wrapped in hard timeouts | `BrowseChild`, `Subscribe`, `CallMethod`, and `Unsubscribe` are synchronous and can stall under server load; guarded `Task.WhenAny` timeouts prevent test-host hangs |
| `JoiningSystem.DisposeAsync` cleanup guard timeout | Management-object dispose calls can perform synchronous network operations; timeout-bounded cleanup (8s management + 10s session close) avoids indefinite teardown stalls |
| Console live tests override coverage gate (`--cov-fail-under=0`) | Live tests intentionally exercise a narrow surface against a live server; global unit-test coverage threshold should not fail live stage |

---

## Agent Guides Index (All Files)

| Path | Covers |
|------|--------|
| `docs/SKILLS.md` (this file) | Repo-level context, access rules, sub-project summary, CI/CD |
| `docs/TEST_TIERS.md` | Test tier policy, skip/fail standards, per-client port table, server isolation design |
| `OPC_UA_Servers/Release2/docs/SKILLS.md` | Server start/stop, simulation methods, smoke tests, env vars |
| `OPC_UA_Clients/Release2/IJT_Web_Client/docs/SKILLS.md` | Full Web Client context, file map, bugs, Docker, CI, health check |
| `OPC_UA_Clients/Release2/IJT_Web_Client/docs/AGENT_GUIDE.md` | Agent workflow and prompt template |
| `OPC_UA_Clients/Release2/IJT_Web_Client/docs/guides/ijt-support-guide.md` | JS core library contracts |
| `OPC_UA_Clients/Release2/IJT_Web_Client/docs/guides/models-guide.md` | JS model layer |
| `OPC_UA_Clients/Release2/IJT_Web_Client/docs/guides/result-model-guide.md` | Result model hierarchy |
| `OPC_UA_Clients/Release2/IJT_Web_Client/docs/guides/views-guide.md` | UI views and screens |
| `OPC_UA_Clients/Release2/IJT_Web_Client/docs/skills/simulate-single-result-caller.md` | Simulate single result workflow |
| `OPC_UA_Clients/Release2/IJT_Web_Client/docs/skills/endpointgraphics-tab-adder.md` | Adding endpoint graphics tabs |
| `OPC_UA_Clients/Release2/IJT_Web_Client/docs/skills/associated-entities-interpreter.md` | Associated entities interpretation |
| `OPC_UA_Clients/Release2/IJT_Console_Client/docs/SKILLS.md` | Console Client context, patterns, test commands, method call examples |
| `OPC_UA_Clients/Release2/IJT_Test_Client/docs/SKILLS.md` | Test Client conformance suite, test structure, markers |
| `OPC_UA_Clients/Release2/IJT_Test_Client/docs/test-results.md` | Report locations, Excel sheets, status meanings, skip categories |
| `OPC_UA_Clients/Release2/IJT_Test_Client/docs/opc-ua-server-context.md` | Address space map, namespaces, event hierarchy, server limitations |
| `OPC_UA_Clients/Release2/IJT_CSharp_Client/docs/SKILLS.md` | C# client architecture, test commands, Softing SDK DLL integration |
| `OPC_UA_Clients/Release1/IJT_Node_Client/docs/SKILLS.md` | Node Client architecture, socket protocol, test commands |
