# Development Guide

This guide provides detailed information for developers setting up their environment, configuring project tools, and troubleshooting development issues.

## Table of Contents

1. [Runtime Configuration](#runtime-configuration)
2. [Environment Setup](#environment-setup)
3. [Package Management](#package-management)
4. [Testing](#testing)
5. [Docker](#docker)
6. [Troubleshooting](#troubleshooting)

## Runtime Configuration

### Node.js Runtime

The project uses Node.js 24 as the baseline runtime for the Web Client and
Release 1 Node Client. The Python Console Client does not require Node.js.

**Configuration:** `.nvmrc` (project root)
- Contains `24` (major version)
- Used by tools like `nvm` (Node Version Manager) and GitHub Actions CI

**Why:** Ensures consistent behavior across:
- Local development machines
- CI/CD pipelines
- Docker builds
- Team collaboration

**Checking your version:**
```bash
node --version  # Should be v24.15.0 or newer for the Web and Node clients
```

**Installing Node.js 24:**
- Using **nvm** (recommended):
  ```bash
  nvm install 24
  nvm use 24
  ```
- Using **homebrew** (macOS):
  ```bash
  brew install node@24
  ```
- Download from [nodejs.org](https://nodejs.org/)

### Python Runtime

The project uses Python 3.14 as the baseline runtime for server simulations, testing, and automation scripts.

**Configuration:** `.python-version` (project root)
- Contains `3.14`
- Used by tools like `pyenv` and GitHub Actions CI

**Why:** Ensures consistent behavior across:
- Local development machines
- CI/CD pipelines
- Test runner environments
- Team collaboration

**Checking your version:**
```bash
python --version  # Should be 3.14.x or newer
```

**Installing Python 3.14:**
- Using **pyenv** (recommended):
  ```bash
  pyenv install 3.14.0
  pyenv local 3.14.0
  ```
- Using **homebrew** (macOS):
  ```bash
  brew install python@3.14
  ```
- Download from [python.org](https://www.python.org/downloads/)

## Environment Setup

### Prerequisites

Before starting development, ensure you have:

1. **Python 3.14+** installed and on your PATH (with `pip` and `venv`)
2. **Node.js 24.15+** installed and on your PATH (with `npm`)
3. **Git** installed and on your PATH (required for pre-commit hooks and repo-level checks)
4. A code editor (VS Code, JetBrains IDEs, etc.)

#### Fresh Machine Setup (One-Command Install)

- **Windows (PowerShell with winget):**
  ```powershell
  winget install --id Python.Python.3.14 -e ; winget install --id OpenJS.NodeJS.LTS -e ; winget install --id Git.Git -e
  ```
- **macOS (Homebrew):**
  ```bash
  brew install python@3.14 node@24 git
  ```
- **Linux (Ubuntu / Debian):**
  Install Python 3.14+ (including pip and venv), Node.js 24.15+, and Git using
  sources suitable for your distribution. Default distribution repositories
  may provide older Python/Node versions; verify versions before running setup.

### Optional Tools (Auto-Detected & Skipped if Missing)

These tools are optional for available-only comprehensive runs. Dependent suites
can be skipped when prerequisites are unavailable; an explicitly requested root
`--suite` fails if it cannot run, and the strict pre-commit gate requires its
system audit tools:

- **.NET SDK 10+** – Required only if developing or testing the C# IJT Client
- **Docker / Docker Compose** – Required only if running Docker-based server tests
- **UaExpert** – Optional desktop OPC UA client for manual GUI inspection

### What is Handled Automatically

When you run `python run_all_tests.py`, the repository handles the following without manual intervention:

| Component | Automated Behavior |
|-----------|--------------------|
| **Python Virtual Environments** | Automatically creates `.venv_test/` in each client directory and installs required packages |
| **Python Tooling** | Prepares uv and isolated root tooling under `.state/tools/`; no global pip installation |
| **Node.js Packages** | Automatically runs `npm ci` when `node_modules` is missing |
| **Playwright Browsers** | Automatically installs browser binaries (`playwright install chromium`) during E2E stages |
| **OPC UA Server Simulators** | Automatically launches native/containerized simulator instances with dedicated port isolation |
| **Missing Optional Tools** | Dotnet, Docker, Hadolint, Semgrep, Actionlint, and Git-dependent scans skip gracefully |

Project runners install required Python quality tools into their project test
virtual environments. A user-level installation of a CLI such as
`detect-secrets` is also suitable for ad-hoc scans; add its Python `Scripts`
directory to `PATH` if the command is not found. It does not replace the
version used by the project runner.

## Package Management

### Node.js Packages

**Manifest files:** `package.json` in each client directory
- `OPC_UA_Clients/Release2/IJT_Web_Client/package.json`
- `OPC_UA_Clients/Release1/IJT_Node_Client/package.json`

**Enforcement:** `engines` field enforces minimum Node.js version
```json
{
  "engines": {
    "node": ">=24.15.0"
  }
}
```

**Install dependencies:**
```bash
cd OPC_UA_Clients/Release2/IJT_Web_Client
npm ci --legacy-peer-deps
```

### Python Packages

**Manifest files:**
- `OPC_UA_Clients/Release2/<client>/pyproject.toml` – Independent per-client PEP 621 project configuration and dependencies
- `OPC_UA_Clients/Release2/<client>/uv.lock` – Deterministic, cross-platform lockfile generated by uv; never edit by hand

**Python client dependency workflow:**
```bash
cd OPC_UA_Clients/Release2/<client>
uv sync --locked                 # synchronize virtual environment from lockfile
uv lock                          # re-resolve and update uv.lock after pyproject.toml edits
uv lock --upgrade                # upgrade dependencies to latest allowed versions
```
Setup scripts and runners install from each client's lock into their dedicated
environment, using uv sync or a frozen export. Plain `uv sync` targets `.venv`;
use `run_all_tests.py` to manage `.venv_test` or local `.venv_ci` automatically.
The `python-locks-current` pre-commit hook validates that all client locks remain up to date,
and `run_precommit_all.py` audits every client lock.

**Enforcement:** `requires-python` field enforces minimum Python version
```toml
[project]
requires-python = ">=3.14"
```

Setup and test scripts prepare the reviewed uv version automatically in an
isolated `.state/tools/` environment when needed. Only Python and Node.js need
manual installation for ordinary Python/Web development. Direct uv maintenance
commands require an installed uv or the managed executable. The repository root is
not a uv project or workspace; run uv dependency commands in the affected client.
Use `uv sync --locked --no-dev` for runtime-only installation. For development
checks, use the client's `python run_all_tests.py --phase1` (Web:
`--phase1-python`) rather than mixing test tools into the runtime environment.

For pip-managed deployments, locked exports, and source-layout requirements, see
the [Python Client Integration Guide](PYTHON_CLIENT_INTEGRATION.md).

## Testing

### Running Tests

**Full test suite** (recommended before committing):
```bash
python run_all_tests.py
```

This runs:
- Linting and static checks
- Unit tests
- Integration tests (if Docker available)
- Specification compliance tests

**Exit codes:**
- `0` – All available tests passed
- `1` – Test failures (fix required)
- Tests for unavailable tools (Docker, .NET) skip gracefully

An explicitly selected root `--suite` must run; a skipped selected suite fails.
Local root runs prepare an isolated `.state/tools/root-tests-py<major><minor>/`
interpreter, so root tooling and smoke-test packages do not modify global Python.
CI/Docker retain their provisioned interpreter.

**Pre-commit validation** (hooks and dependency audits):
```bash
python run_precommit_all.py
```

This runs:
- Pre-commit hooks (linting, formatting)
- Dependency CVE checks
- Blocks on high-severity security issues

Root and Envelope hooks run sequentially because hooks can modify files.
Dependency audits then run with at most two tasks globally: one task for each
Python client, NuGet, remaining Python requirements, and a sequential npm group.
Every applicable npm project is checked even if an earlier project fails.
Python audit tooling is prepared once before workers start. Required missing
package tools or inputs fail validation; an absent optional Envelope checkout is excluded.
Missing .NET/npm system tools are reported as incomplete validation by default;
`--strict` fails instead. Docker and .NET are never installed automatically.
Results and subprocess output are buffered per task and printed in a stable order.

Each Python client uses `uv lock --check` and a frozen export of all dependency
groups. `pip-audit --strict --require-hashes --disable-pip` audits the complete exact pins
without recreating an environment. Unsupported fast-path flags trigger an
explicitly reported pip-based audit, not a skipped check. Remaining requirements
still use dependency resolution. Separate persistent caches isolate these tasks.
Both locked-export audit paths enforce `--require-hashes`; exports retain uv's hashes.
NuGet's filtered JSON may omit frameworks for clean projects; reported problems
and vulnerability findings still fail validation.
Client summaries include lock, export, and audit timings. Audits apply environment
markers for the running interpreter/platform; a Windows pass does not establish
Linux coverage. All required failures produce a nonzero overall exit, after
collecting the other tasks' results.

npm lockfile audits in `run_precommit_all.py` and the Node/Web Client
`run_all_tests.py` runners use a bounded 15-second process timeout and run in strict
mode by default (`IJT_NPM_AUDIT_MODE=strict`). npm registry timeout/connectivity
failures therefore fail quickly because security status is unknown, rather than
hanging the suite. For explicitly offline local development only,
`IJT_NPM_AUDIT_MODE=offline` allows continuing on connectivity failures
while still
failing on reported high/critical vulnerabilities and non-network tool errors.
GitHub application/static lanes use offline handling so a recognized
npm advisory-service outage is an infrastructure warning rather than a product
failure. The dependency-security workflow reviews dependency changes on pull
requests, monitors all ecosystems daily in offline mode, and provides
manual strict release qualification.

### Before Committing Dependency Changes

From the repository root, run these commands sequentially:

```powershell
python .\run_all_tests.py
python .\run_precommit_all.py --strict
.\.state\tools\root-tests-py314\Scripts\python.exe -m pytest tests
git diff --check
git diff --cached --check
```

Inspect the summaries, not just the exit codes: unavailable optional tools can
skip project suites. For Python environment changes, also run
`python .\run_all_tests.py --phase1 --ci-mode` to exercise the local CI environments.
With Docker running, verify the Web production image using
`python .\run_all_tests.py --suite web-client-docker-smoke` if the full run did not
already execute it successfully. Linux smoke requires Docker's Linux-container
mode; native Windows checks do not replace Linux verification.

Hooks can fix files. Review those edits, then rerun validation until it passes
without additional fixes. Review both staged and unstaged changes before manually
staging the intended final versions. Do not stage unrelated changes or an altered
private-submodule pointer accidentally. Envelope is optional; authorized owners
can use `--private-modules require` with the root test runner to require its checks.
After publishing, check GitHub Actions and the first hosted Renovate dependency
PR separately; local validation does not prove hosted lockfile regeneration.

The pytest example uses the root tooling interpreter prepared by the root runner
with Python 3.14. Adjust `py314` for your Python version; on POSIX use
`.state/tools/root-tests-py314/bin/python`. A bare `python -m pytest` does not
automatically use that environment.

Tool preparation uses dedicated environments, not the user's global Python.
Root pre-commit tooling lives under `.state/tools/precommit-py<major><minor>/`;
uv uses a versioned tooling environment. Cross-process locks serialize preparation,
requirements fingerprints detect changes, and repeated runs reuse verified installs.
First use needs package-index access or an offline cache, honouring pip proxy/index
settings. CI/Docker must provision uv explicitly; offline containers never bootstrap it.

### Test Tiers

The project uses tiered testing for flexibility:

- **Tier 0 (Fast):** Linting, formatting, type checks (~few seconds)
- **Tier 1 (Standard):** Unit tests, basic integration (~few minutes)
- **Tier 2 (Extended):** Docker-based server tests (~10+ minutes)
- **Tier 3 (Full):** Specification compliance and stress tests (~20+ minutes)

See [TEST_TIERS.md](TEST_TIERS.md) for running specific tiers.

### Continuous Integration

Tests run automatically on:
- Every push to `main` and pull requests
- Scheduled nightly runs for extended tests
- Security scanning via CodeQL

View results: [GitHub Actions CI](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions)

## Docker

### Optional: Running Server in Docker

Docker enables isolated testing of the IJT server without affecting your local environment.

**Prerequisites:** Docker Desktop (macOS/Windows) or Docker Engine (Linux)

**Build the server image:**
```bash
cd OPC_UA_Servers/Release2
docker build -t ijt-server .
```

**Run the server:**
```bash
docker run -p 40451:40451 ijt-server
```

The server listens on `opc.tcp://localhost:40451` (accessible from your host machine).

**Connect a client:**
```bash
# From another terminal on your host
# Use any OPC UA client pointed at opc.tcp://localhost:40451
```

**View server logs:**
```bash
docker logs <container-id>
```

### Docker Compose (if available)

Some components may provide `docker-compose.yml` for multi-service setups. Check the relevant component directory.

## Troubleshooting

### Python Version Issues

**Error:** `python: command not found` or version mismatch

**Solutions:**
1. Verify Python 3.14 is installed: `python3 --version`
2. On some systems, use `python3` instead of `python`
3. Use `pyenv` to manage multiple Python versions
4. Add Python to your PATH

### Node.js Version Issues

**Error:** `node: command not found` or npm install fails

**Solutions:**
1. Verify Node.js 24.15+ is installed: `node --version`
2. Use `nvm use` to switch to the correct version
3. Run `nvm install 24` if not installed
4. Restart your terminal after installing

### Test Failures

**Error:** Tests fail with missing dependencies

**Solutions:**
1. Ensure `python run_precommit_all.py` passes first
2. Delete `node_modules/` and run `npm install` again
3. Check that Python and Node.js versions match the baselines
4. Review test output for specific missing packages

### Docker Issues

**Error:** Docker daemon is not running / Port 40451 already in use

**Solutions:**
1. Start Docker Desktop (macOS/Windows) or `sudo systemctl start docker` (Linux)
2. Kill existing containers: `docker ps`, then `docker kill <id>`
3. Use a different port: `docker run -p 40452:40451 ijt-server`

### Still Stuck?

1. Check existing [GitHub Issues](https://github.com/umati/UA-for-Industrial-Joining-Technologies/issues)
2. Review project logs in `.github/workflows/` for CI setup examples
3. Contact the project coordinator: Bernd Heitzmann - bernd.heitzmann@vdma.eu

## Related Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) – Contribution guidelines and testing workflow
- [TEST_TIERS.md](TEST_TIERS.md) – Detailed test tier documentation
- [OPC UA IJT Specifications](https://reference.opcfoundation.org/IJT/Base/v100/docs/)
