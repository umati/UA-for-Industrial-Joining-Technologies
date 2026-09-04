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

The project uses Node.js 24 as the baseline runtime for the web client and console client.

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
node --version  # Should be v24.x.x or newer
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
2. **Node.js 24+** installed and on your PATH (with `npm`)
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
  ```bash
  sudo apt update && sudo apt install -y python3 python3-pip python3-venv nodejs npm git
  ```

### Optional Tools (Auto-Detected & Skipped if Missing)

These tools are optional; test runners automatically detect their availability and skip dependent suites gracefully with exit code `0`:

- **.NET SDK 10+** – Required only if developing or testing the C# IJT Client
- **Docker / Docker Compose** – Required only if running Docker-based server tests
- **UaExpert** – Optional desktop OPC UA client for manual GUI inspection

### What is Handled Automatically

When you run `python run_all_tests.py`, the repository handles the following without manual intervention:

| Component | Automated Behavior |
|-----------|--------------------|
| **Python Virtual Environments** | Automatically creates `.venv_test/` in each client directory and installs required packages |
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
- `OPC_UA_Clients/Release2/IJT_Console_Client/package.json`

**Enforcement:** `engines` field enforces minimum Node.js version
```json
{
  "engines": {
    "node": ">=24.0.0"
  }
}
```

**Install dependencies:**
```bash
cd OPC_UA_Clients/Release2/IJT_Web_Client
npm install
```

### Python Packages

**Manifest files:**
- `pyproject.toml` – Main Python project configuration
- `constraints.txt` – Transitive dependency pinning for reproducibility

**Enforcement:** `requires-python` field enforces minimum Python version
```toml
[project]
requires-python = ">=3.14"
```

**Install dependencies:**
```bash
pip install -e .  # Install in editable mode for development
```

**Install dev dependencies:**
```bash
pip install -r requirements-dev.txt  # If available
```

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

**Pre-commit validation** (quick check):
```bash
python run_precommit_all.py
```

This runs:
- Pre-commit hooks (linting, formatting)
- Dependency CVE checks
- Blocks on high-severity security issues

npm lockfile audits in `run_precommit_all.py` and the Node/Web Client
`run_all_tests.py` runners use a bounded 15-second process timeout and run in strict
mode by default (`IJT_NPM_AUDIT_MODE=strict`). npm registry timeout/connectivity
failures therefore fail quickly because security status is unknown, rather than
hanging the suite. For explicitly offline local development only,
`IJT_NPM_AUDIT_MODE=degraded` allows continuing on connectivity failures while still
failing on reported high/critical vulnerabilities and non-network tool errors.
Degraded mode must not be used for CI or release qualification.

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
1. Verify Node.js 24 is installed: `node --version`
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

- [CONTRIBUTING.md](../CONTRIBUTING.md) – Contribution guidelines and testing workflow
- [TEST_TIERS.md](TEST_TIERS.md) – Detailed test tier documentation
- [OPC UA IJT Specifications](https://reference.opcfoundation.org/IJT/Base/v100/docs/)
