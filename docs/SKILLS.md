# UA-for-Industrial-Joining-Technologies — Developer Reference

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
5. `eslint-node-client` lints Node Client JS (`.js`, `.mjs`)
6. `css-node-client` runs the Node Client CSS checker
7. `eslint-web-client` lints Web Client JS (`src/javascripts/`, `config.js`)
8. `stylelint-web-client` lints Web Client CSS (`src/resources/css/`)

JS hooks (#5–#8) run with the project's own `node_modules` via `npm --prefix` — no global
install required. They only trigger when matching files are staged.

Multi-exception style rule: always write `except (A, B):`, never `except A, B:`. This is enforced
by the unit-level guard test (`test_ruff_format_guard.py`) which verifies ruff does not corrupt
parenthesized except clauses — see **Key Technical Decisions** below.

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

Use `.venv` for running the application and `.venv_test` for running tests — do not mix them.

Both `setup_*.py` and `run_all_tests.py` remove stale legacy directories (`venv/`, `venv_test/`, `env/`, `ENV/`, `.venv_backup/`) on startup. A fresh clone always starts clean automatically.

---

### Running Tests — Project Isolation

Run tests from each project's own directory, not from the repo root.

```sh
# ✅ Correct — run from project directory
cd OPC_UA_Clients/Release2/IJT_Web_Client && pytest tests/python/unit
cd OPC_UA_Clients/Release2/IJT_Console_Client && pytest tests/unit

# ❌ Wrong — from repo root, both conftest.py files collide
pytest OPC_UA_Clients/Release2/IJT_Web_Client/tests OPC_UA_Clients/Release2/IJT_Console_Client/tests
```

Running multiple Python clients together in a single root `pytest` invocation causes `ImportPathMismatchError` because both trees have `tests/conftest.py`. The CI workflows and `run_all_tests.py` both enforce per-project `working-directory`.

**For local full-suite runs**: Use each project's `run_all_tests.py` from its own directory, or the repo root orchestrator which delegates each runner with the correct `cwd`.
The root orchestrator forces Python child runners to UTF-8 output so nested
runner banners, skip reasons, and advisory tool messages render consistently on
Windows terminals and captured logs.

---

### Pytest Temp Root Policy

All three Python clients use a **project-local** `tmp/pytest/` directory as the pytest basetemp so that temp files
are always created under the repo tree and gitignored automatically.  Set `IJT_USE_SYSTEM_BASETEMP=1` to override
and use the OS default temp location instead.

| Project | Basetemp configuration |
|---------|------------------------|
| `IJT_Console_Client` | `pytest_configure` hook in `conftest.py` (CWD-independent absolute path) |
| `IJT_Test_Client` | `pytest_configure` hook in `conftest.py` |
| `IJT_Web_Client` | `pytest_configure` hook in `tests/conftest.py` |

`tmp/` is gitignored in each project. `tmp_path_retention_policy = "failed"` retains artifacts only for failing tests.

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
| Web Client | **90%** | Configured in `pyproject.toml` — applies to Python unit run. |
| Console Client | 80% | Configured in `pyproject.toml` — applies to unit run |
| Test Client | **90%** | Configured in `pyproject.toml` — live-test-only helpers reduce coverage on conformance-only runs; `tests/unit/` supplements with pure-logic coverage |

**C# Client (coverlet)**: Exclusions defined in `coverlet.runsettings` — excludes `UAModel` (auto-generated OPC UA type bindings) and `Program` namespaces, plus `[GeneratedCode]`, `[ExcludeFromCodeCoverage]`, and `[CompilerGeneratedAttribute]` attributes. CI passes `--settings coverlet.runsettings` to `dotnet test` so exclusions are applied to both collection and the summary table.

**Node Client (JavaScript/Vitest)**: Coverage threshold is NOT in pyproject.toml (JS project).
- Hard gate: `coverage.thresholds` in `vitest.config.mjs` (if set)
- Ratchet floor: `_COVERAGE_THRESHOLD = 85.0` in `IJT_Node_Client/run_all_tests.py` — WARN-only, advisory/non-gated, ratchet upward as coverage improves. Aspirational goal: 90%.
- Coverage reporters: `text-summary`, `cobertura` — the cobertura XML is parsed by the CI report job

**Web Client JS (Vitest)**: Threshold enforced at 80% via `vitest.config.mjs` `thresholds.lines`. Reporters: `text`, `lcov`, `cobertura`.

---

### Runner Step Result Model — PASS / WARN / FAIL / SKIP

All Python runner scripts (`run_all_tests.py`) use a `_StepResult` class with four distinct states. **Do not collapse WARN into PASS or FAIL** — the distinction is enforced by unit tests.

| Field | State | Colour | Counts as | Use for |
|-------|-------|--------|-----------|---------|
| `ok=True, warn=False` | **PASS** | green | `passed` | Tool ran clean |
| `warn=True` | **WARN** | yellow | `warned` (never `failed`) | Advisory tool: ran but output unreadable, or found non-critical issues |
| `ok=False, warn=False` | **FAIL** | red | `failed` → suite FAIL | Real defect or gate violation |
| `skipped=True` | **SKIP** | yellow | `skipped` | Tool not installed / not applicable |

**Advisory tool rule**: Tools whose failures are inherently non-actionable on the local/CI environment (Semgrep SSL, pyright advisory, pip-audit network) must use `result.warn = True` — **never** `result.ok = False`. Setting `ok=False` converts an advisory observation into a suite-blocking failure.

**Semgrep preflight rule**: When a runner uses `--config=p/default`, the network preflight must probe `https://semgrep.dev/c/p/default`, not only `https://semgrep.dev/`. Use `requests` when available so the preflight follows the same certifi/TLS trust path as Semgrep and pip-audit. Keep `requests` optional inside the helper and annotate that import with `# type: ignore[import-untyped]` unless `types-requests` is a required dev dependency. Optional imports used by runner/report tooling are covered by the root optional-import typing guard, including untyped imports and forward-annotation/reimport patterns that mypy flags as `no-redef`. The root host can be reachable while the rule download path fails TLS/auth, which otherwise costs roughly 100 seconds and emits traceback noise before producing the same advisory WARN.

The invariant is unit-tested in `tests/unit/test_runner_step_result.py` in both Console Client and Test Client:
- `test_semgrep_parse_failure_sets_warn_not_fail` — parse failure must set `warn=True`
- `test_counter_mixed_suite_warn_does_not_cause_suite_fail` — `warned > 0` with `failed = 0` must still pass

**Summary line format**: `Result: PASS  passed=12  warned=1  failed=0  skipped=1`

Docstring coverage (`interrogate`) thresholds — calibrated against real codebase with venvs excluded:

| Project | `fail-under` | Notes |
|---------|-------------|-------|
| Console Client | 25% | Honest floor; tests included in scan |
| Web Client | 42% | Honest floor; tests included in scan |
| Test Client | 65% | Higher bar; source is well-documented |

---

### Windows Temp Directory Notes

On Windows, pyfakefs and pytest can leave directories with restricted ACLs that survive test teardown.
Built-in protections already in place:

| Protection | Mechanism |
|-----------|-----------|
| `_force_rmtree(path)` | All 7 runners + 2 setup scripts — `shutil.rmtree(onexc=...)` with `os.chmod` retry for read-only files |
| `[tool.mypy] exclude` | Skips `pytest-cache-files-*` before mypy walks into them |
| `norecursedirs` | pytest never collects from `pytest-cache-files-*` or `tmp` |
| `-p no:cacheprovider` (all 3 Python clients) | Prevents `pytest-cache-files-*` creation entirely |
| `.dockerignore` | `tests/fixtures/tmp/` excluded from Docker build context |
| Project-local basetemp | All Python clients write to `tmp/pytest/` instead of system temp |

If a directory is owned by a different OS user (e.g. a CI service account), `_force_rmtree` cannot remove it —
Windows requires owner rights or `SeBackupPrivilege` for deletion.  Use `takeown` + `icacls` as Administrator to
recover such directories.

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
│   └── SKILLS.md                    # ← THIS FILE: root-level developer reference
├── run_all_tests.py                 # Root orchestrator — runs all project suites
├── renovate.json                    # Dependency update config
│
├── IJT_Documents/                   # Spec presentations and reference docs
│
├── OPC_UA_Servers/
│   └── Release2/                    # IJT Server Simulator (Windows + Linux binary + Docker)
│       ├── README.md                # End-user setup guide
│       ├── run_all_tests.py         # Server test runner (hadolint, trivy, smoke)
│       └── docs/SKILLS.md          # Server developer reference
│
└── OPC_UA_Clients/
    ├── Release1/
    │   └── IJT_Node_Client/         # Node.js OPC UA browser client
    │       ├── docs/SKILLS.md
    │       └── run_all_tests.py
    └── Release2/
        ├── README.md
        ├── IJT_Web_Client/          # ★ PRIMARY — Python + Node.js browser client
        │   ├── docs/SKILLS.md       # Web Client developer reference
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
- **Tests**: Python unit (`tests/python/unit/`), JS unit (`src/javascripts/`), live (`tests/python/live/` — excluded from default run, requires OPC UA server)
- **One test command**: `python run_all_tests.py`
- **Docker**: healthy on HTTP:3000 + WS:8001
- **Details**: read `OPC_UA_Clients/Release2/IJT_Web_Client/docs/SKILLS.md`

### IJT Console Client (`OPC_UA_Clients/Release2/IJT_Console_Client/`)
- **Stack**: Python 3.14+, asyncua ≥1.2b2
- **Tests**: unit (`tests/unit/` — no server needed); live (`tests/live/` — calls `pytest.fail()` if server unreachable, no silent skips)
- **One test command**: `python run_all_tests.py` (auto-launches server if needed)
- **Entry point**: `python setup_client.py --url="opc.tcp://..."`
- **Details**: read `OPC_UA_Clients/Release2/IJT_Console_Client/docs/SKILLS.md`

### IJT Test Client (`OPC_UA_Clients/Release2/IJT_Test_Client/`)
- **Stack**: Python 3.14+, asyncua ≥1.2b2, pytest
- **Purpose**: OPC UA IJT spec conformance test suite — validates server against OPC 40450-1 / 40451-1
- **Tests**: conformance (`conformance/` — requires running OPC UA server); unit (`tests/unit/` — pure-logic helper coverage, no server needed)
- **One test command**: `python run_all_tests.py` (auto-launches server if needed)
- **Details**: read `OPC_UA_Clients/Release2/IJT_Test_Client/docs/SKILLS.md`

### IJT CSharp Client (`OPC_UA_Clients/Release2/IJT_CSharp_Client/`)
- **Stack**: C# .NET 10+, OPC Foundation UA SDK, xUnit, Moq, coverlet
- **Purpose**: C# reference OPC UA IJT client — events, results, assets, joining process, and joint management
- **Architecture**: `JoiningSystem` holds `ISession` (OPC UA SDK) directly; no wrapper. `IJoiningSystem` is the interface for management classes and Moq mocks. `IjtSession`/`IIjtSession` do not exist.
- **Tests**: xUnit unit tests + live integration tests (skipped unless `OPCUA_SERVER_URL` or `OPCUA_SIMULATOR_EXE` is set)
- **One test command**: `python run_all_tests.py` (dotnet build + test + NuGet CVE scan)
- **Details**: read `OPC_UA_Clients/Release2/IJT_CSharp_Client/docs/SKILLS.md`

### IJT Node Client (`OPC_UA_Clients/Release1/IJT_Node_Client/`)
- **Stack**: Node.js 24+, node-opcua, Socket.io, Vitest, Playwright
- **Purpose**: Node.js + browser OPC UA IJT client (Release 1)
- **One test command**: `python run_all_tests.py` (npm ci + vitest + eslint + npm audit)
- **E2E tests**: 27 Playwright specs in `tests/e2e/` — skip gracefully in CI (no server); run locally with `node index.js` then `npx playwright test`
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
- **UaExpert config**: `IJT_LOCAL_SIMULATOR.uap` (read-only reference; do not modify)
- **Details**: read `OPC_UA_Servers/Release2/docs/SKILLS.md`

### Server Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPCUA_SERVER_PORT` | `40451` | Override port — used by CI to run parallel isolated instances |
| `OPCUA_HOSTNAME` | `localhost` | Override advertised hostname — used for Docker with remote clients |

---

## CI/CD

**Workflows**: `.github/workflows/ci.yml`, `.github/workflows/integration.yml`, and `.github/workflows/codeql.yml` (all at **repo root**)

### CI (`ci.yml`) — triggers on every push/PR to `main`
| Job | What it tests |
|-----|--------------|
| `web-client` | Python unit tests, JS unit tests, ESLint, Bandit, npm audit |
| `console-client` | Python unit tests (`tests/unit/`), Bandit, Ruff, mypy |
| `node-client` | JS unit tests, ESLint, npm audit |
| `test-client` | pytest unit tests (`tests/unit/`) + Bandit, Ruff, mypy |
| `csharp-unit` | dotnet restore (locked mode) + build (`-warnaserror`) + xUnit unit tests (`Category!=Live`, `--blame-hang 60s`) + format check (`dotnet format --verify-no-changes`) |
| `csharp-vuln` | NuGet vulnerability scan (`--vulnerable --include-transitive`); fails on known CVEs |
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
| `csharp-unit` | `ci.yml` | — | No server (unit tests only) |
| `csharp-vuln` | `ci.yml` | — | No server (NuGet scan only) |
| `server-smoke-windows` | `ci.yml` | 40451 | Windows native EXE (server self-test) |
| `server-smoke-docker` | `integration.yml` | 40451 | Docker Linux (server self-test) |
| `int-testclient` | `integration.yml` | **40462** | Windows native EXE |
| `live-webclient` | `integration.yml` | **40463** | Windows native EXE |
| `live-console` | `integration.yml` | **40461** | Windows native EXE |
| `csharp-live` (nightly) | `integration.yml` | **40464** | Windows native EXE |

Root-level `python run_all_tests.py` includes `server-smoke` in default Phase 2 so local full validation also exercises the native/default server package path on port 40451.

> Release 1 Node Client always uses 40451 (fixed — no dynamic port support).
> Server self-tests (smoke) correctly use 40451 — they test the server in its native configuration.
> All Release 2 client jobs now use dedicated isolated ports.

### Integration (`integration.yml`) — nightly + path-triggered
Triggers on: `OPC_UA_Servers/**`, Web Client Python/integration/Docker/deps, `IJT_Test_Client/**`, Console Client live/deps, or workflow file change.
| Job | What it tests |
|-----|--------------|
| `server-smoke-docker` | Full Docker build + server smoke (10/10) |
| `webclient-docker` | Web Client Docker test image (Python unit + JS unit) + HTTP:3000 production health |
| `int-testclient` | Windows live: Test Client full suite against server on port 40462 |
| `live-webclient` | Windows live: Web Client integration tests (13 tests) — server on port 40463 |
| `live-console` | Windows live: Console Client live tests — server on port 40461 |
| `csharp-live` | Windows live: C# xUnit live tests (nightly drift detection) — server on port 40464 |

Runtime: ~10–15 minutes (int-testclient, live-webclient, live-console, csharp-live all run in parallel). NOT triggered on GUI/JS-only changes (deliberate — keep fast CI fast).
All jobs have explicit `timeout-minutes` (5–45 min) and `permissions: contents: read`.

---

## Key Technical Decisions

| Decision | Reason |
|----------|--------|
| asyncua ≥1.2b2 (pre-release) | Python 3.14 support not in asyncua 1.1.x stable |
| Monkey-patch `_send_request` timeout | asyncua `UaClient.call()` has hardcoded 1s timeout |
| Subscribe events on Server node, not method nodes | Subscribing on individual nodes causes `BadNoSubscription` under load |
| Skip venv in Docker (`IS_DOCKER=true`) | Container runs as non-root; `/opt/ijt_venv` not writable |
| No `scripts/` at repo root | Each project owns its own helpers; nothing shared at root level |
| `Python/network_utils.py` canonical | Shared network helpers live in this module; all imports use `from Python.network_utils import ...` |
| `ruff target-version = "py313"` (not py314) | ruff 0.15.x bug #24041: `ruff format` with py314 strips parens from `except (A, B):` → Python 2 syntax. py313 is the workaround; guard test `test_ruff_format_guard.py` in Console + Test Client unit suites catches any regression. Restore to py314 once upstream fixes #24041 |
| No custom EventFilter | Full `ResultDataType` payload arrives in event without custom filter |
| C# live-test sync OPC UA calls wrapped in hard timeouts | `BrowseChild`, `Subscribe`, `CallMethod`, and `Unsubscribe` are synchronous and can stall under server load; guarded `Task.WhenAny` timeouts prevent test-host hangs |
| `JoiningSystem.DisposeAsync` cleanup guard timeout | Management-object dispose calls can perform synchronous network operations; timeout-bounded cleanup (8s management + 10s session close) avoids indefinite teardown stalls |
| Console live tests override coverage gate (`--cov-fail-under=0`) | Live tests intentionally exercise a narrow surface against a live server; global unit-test coverage threshold should not fail live stage |
| `pre-commit` as sole hook manager (no Husky) | Polyglot monorepo best practice — one hook manager for all languages. `pre-commit` handles Python + JS + YAML + TOML uniformly, and JS linting is wired via `npm --prefix` local hooks in `.pre-commit-config.yaml`. Do not add a second hook manager for subprojects. |
| `coverlet.runsettings` passed via `--settings` in CI | Without `--settings`, `ExcludeByNamespace` (UAModel, Program) and `[GeneratedCode]` exclusions are ignored — auto-generated code inflates C# line count and deflates coverage % |
| `playwright/test` import (not `@playwright/test` package) | Node Client has `playwright` (not `@playwright/test`) in `package.json`. `playwright` exposes the same test API at `playwright/test`. Avoids adding a second overlapping Playwright package. |
| `pytest_sessionfinish` cleanup hook in Web Client `conftest.py` | `__pycache__` and `tmp/pytest` created by direct `pytest` invocations are cleaned up post-session even when `run_all_tests.py` is not used. Keeps project tree clean on every run path. |

---

## Documentation Index (All Files)

| Path | Covers |
|------|--------|
| `docs/SKILLS.md` (this file) | Repo-level developer reference, sub-project summary, CI/CD |
| `docs/TEST_TIERS.md` | Test tier policy, skip/fail standards, per-client port table, server isolation design |
| `OPC_UA_Servers/Release2/docs/SKILLS.md` | Server start/stop, simulation methods, smoke tests, env vars |
| `OPC_UA_Clients/Release2/IJT_Web_Client/docs/SKILLS.md` | Full Web Client context, file map, bugs, Docker, CI, health check |
| `OPC_UA_Clients/Release2/IJT_Web_Client/docs/DEVELOPMENT_GUIDE.md` | Development workflow and guidelines |
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
| `OPC_UA_Servers/Release2/docs/opc-ua-server-context.md` | Address space map, namespaces, event hierarchy, server limitations |
| `OPC_UA_Clients/Release2/IJT_CSharp_Client/docs/SKILLS.md` | C# client architecture, test commands, Softing SDK DLL integration |
| `OPC_UA_Clients/Release1/IJT_Node_Client/docs/SKILLS.md` | Node Client architecture, socket protocol, test commands |
