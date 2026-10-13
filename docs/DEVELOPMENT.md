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

The project uses Python 3.14.x as the maintained runtime for Python clients,
testing, and automation scripts. Keep normal development, required CI, and
Python container images on this line until a coordinated migration is approved.

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
python --version  # Should be 3.14.x
```

#### Python runtime update policy

`renovate.json` restricts the `python` dependency from the Docker datasource
(used by both the pyenv manager for `.python-version` and Docker image managers)
to 3.14, and separately restricts the Python component
of `nikolaik/python-nodejs` tags to 3.14. These rules apply repository-wide,
not just to one Dockerfile. Python 3.14 patch updates and Docker digest
refreshes remain eligible for review; Python package updates and lockfile
maintenance remain enabled. Package releases must still work with Python 3.14.

Client manifests retain `requires-python = ">=3.14"`: this is the minimum
interpreter requirement, not certification of newer Python versions. Python
3.15 is released and stable, but IJT compatibility with its locked dependencies,
including asyncua 2.1.0, must be established before changing the maintained runtime.
Newer interpreters may be evaluated separately without changing required CI.

After this policy is published to the default branch, Renovate applies it on
its next repository run. Do not merge an existing 3.15 runtime PR such as
[#616](https://github.com/umati/UA-for-Industrial-Joining-Technologies/pull/616);
close it as deferred if Renovate has not already removed it. The rules, rather
than closing an individual PR, prevent subsequent unsupported runtime proposals.

For a future migration:

1. Verify the locked runtime and development dependencies on the proposed Python
   version, including Windows/Linux wheels and targeted OPC UA connection,
   subscription, reconnect, security, and shutdown behavior.
2. Update both runtime rules in `renovate.json`, `.python-version`, Python Docker
   tags/digests, browser image version assertions, and any explicit workflow
   version pins together. Coordinate separately owned plugin runtime pins rather
   than editing a submodule implicitly.
3. Regenerate affected locks as needed and rebuild the browser CI image with its
   offline wheelhouse. Refresh the reviewed image pin using the existing image
   publication procedure; do not hand-edit provenance.
4. Update runtime documentation and policy tests. Raise client `requires-python`
   floors only if intentionally dropping 3.14 support; keep Ruff's documented
   target-version workaround separate from the runtime decision.
5. Complete the normal CI and live validation gates before adopting the new
   runtime. A calendar date or upstream stable release alone does not lift the hold.

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

1. **Python 3.14.x** installed and on your PATH (with `pip` and `venv`)
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
| **Python Tooling** | Prepares uv under `.state/tools/` when needed; syncs root `.venv` from root `uv.lock` for locked CLIs (zizmor); no global pip installation |
| **Node.js Packages** | Automatically runs `npm ci` when `node_modules` is missing |
| **Playwright Browsers** | Automatically installs browser binaries (`playwright install chromium`) during E2E stages |
| **OPC UA Server Simulators** | Ensures present simulator ZIPs via `scripts/simulator_extract.py` (locked staging → rename-aside swap), then launches native/containerized instances with dedicated port isolation |
| **Missing Optional Tools** | OS/binary scanners (Hadolint, Trivy, Actionlint, Semgrep, …) skip gracefully when absent; CI remains authoritative |

**Lockfile Python tools (required):** The repository **root is a uv project**
(`pyproject.toml` + `uv.lock`) for root-runner CLIs; it is **not** a uv workspace
that joins clients — each client keeps its own lock. Client and root dependencies
are installed with `uv sync --locked`. If sync fails, the runner **FAIL**s — do
not `pip install` those tools into global Python.

For **zizmor** (workflow security), keep the same CLI version `X.Y.Z` on these
**version pins** (contract tests enforce all three):
1. root `pyproject.toml` (`zizmor==X.Y.Z`) + `uv.lock` — Renovate `zizmor-lockstep`
2. `.pre-commit-config.yaml` (`rev: vX.Y.Z`) — same group (`:enablePreCommit`;
   other pre-commit hooks stay disabled in Renovate)
3. `.github/workflows/ci.yml` zizmor-action `version: "X.Y.Z"` — same group via
   a Renovate regex customManager (depName `zizmor`). The action *SHA* stays on
   Dependabot. Contract tests still enforce (1)–(3).

Local runner behavior: sync/provision failure **FAIL**s; High/Critical findings
**FAIL**; empty/unparseable tool output **FAIL**s (locked CLI is a hard gate).
Root `.venv` is **owned by** `uv sync --locked` — do not install ad-hoc packages
into it (exact sync removes them). Prefer the separate
`.state/tools/root-tests-py…/` env for pytest. Windows ARM64 has no published
zizmor wheel today — sync falls back to sdist/Rust and will FAIL without a
toolchain.

The pre-commit zizmor hook uses pre-commit’s own cached environment (from
`zizmor-pre-commit`), not root `.venv`. Both local runner and pre-commit pass
`--offline`. CI’s `zizmor-action` uploads SARIF and does not fail the job by
itself — Code Scanning / branch protection decide merge impact. The CI
`pre-commit` job still runs the zizmor hook and fails on High findings.

`SKIP_VENV_INSTALL=1` is for Docker/provisioned images that already have the
env: the root runner still requires root CLIs present **and**
`uv sync --locked --check` clean (no silent stale binary). Root GHA preflight
(`_check_zizmor`) runs on local full / `--phase1` orchestrator paths, not on
`--suite`-only Docker jobs.

**OS/binary scanners** (hadolint, trivy, actionlint, …) stay optional locally;
CI remains authoritative until a pinned bootstrap exists.

#### Adding a root-locked CLI

When you need another **Python** CLI at the repo root (same pattern as zizmor):

1. Add `"toolname==X.Y.Z"` under root `[dependency-groups] dev` in `pyproject.toml`.
2. Append `"toolname"` to `ROOT_REQUIRED_DEV_CLIS` in `run_all_tests.py`.
3. From the repository root, run `uv lock` and commit `uv.lock`.
4. Call the tool from the root runner via `_root_cli_bin(venv, "toolname")` after
   `_ensure_root_venv()` (do not use the system PATH).
5. If a pre-commit or CI pin must match, add the same lockstep as zizmor and a
   small contract test.

Project runners still install their own quality tools into each client’s
`.venv_test`. A personal `detect-secrets` (or similar) on your PATH is fine for
ad-hoc scans; it does not replace the version the project runner uses.

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
- `pyproject.toml` + `uv.lock` at the **repository root** – Root-locked toolchain for `run_all_tests.py` (e.g. zizmor in `[dependency-groups] dev`); syncs into root `.venv`
- `OPC_UA_Clients/Release2/<client>/pyproject.toml` – Independent per-client PEP 621 project configuration and dependencies
- `OPC_UA_Clients/Release2/<client>/uv.lock` – Deterministic, cross-platform lockfile generated by uv; never edit by hand

**Python dependency workflow (client or root):**
```bash
# Root toolchain (zizmor, …):
uv sync --locked --group dev     # from repository root → .venv

# Client:
cd OPC_UA_Clients/Release2/<client>
uv sync --locked                 # synchronize virtual environment from lockfile
uv lock                          # re-resolve and update uv.lock after pyproject.toml edits
uv lock --upgrade                # upgrade dependencies to latest allowed versions
```
Setup scripts and runners install from each project's lock into their dedicated
environment, using uv sync or a frozen export. Plain `uv sync` at a client targets
`.venv`; use that client's `run_all_tests.py` to manage `.venv_test` or local
`.venv_ci` automatically. The root runner syncs root `.venv` before the zizmor
preflight. The `python-locks-current` hook / `scripts/check_python_locks.py`
validates root and client `uv.lock` files; `run_precommit_all.py` audits client
locks for CVEs.

**Enforcement:** `requires-python` field enforces minimum Python version
```toml
[project]
requires-python = ">=3.14"
```

Setup and test scripts prepare the reviewed uv version automatically in an
isolated `.state/tools/` environment when needed. Only Python and Node.js need
manual installation for ordinary Python/Web development. Direct uv maintenance
commands require an installed uv or the managed executable. Run client uv commands
in the affected client directory; run root toolchain commands at the repository
root. Use `uv sync --locked --no-dev` for client runtime-only installation. For
development checks, use the client's `python run_all_tests.py --phase1` (Web:
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
- Suites that need Docker / .NET skip gracefully when those host tools are absent
- Zizmor: **FAIL** if provision fails, findings are High/Critical, or output is
  empty/unparseable after a locked sync (no soft SKIP for tool errors)

An explicitly selected root `--suite` must run; a skipped selected suite fails.
Local root runs prepare two distinct environments (neither touches global Python):
- **Root `.venv`** — `uv sync --locked --group dev` from root `uv.lock` (zizmor and future root CLIs)
- **`.state/tools/root-tests-py<major><minor>/`** — interpreter for root pytest / smoke packages

CI/Docker retain their provisioned interpreter for hosted jobs.

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

Inspect the summaries, not just the exit codes: Docker / .NET / binary scanners can
skip project suites. A GHA Zizmor **FAIL** (sync failed, High/Critical findings, or
tool/parse error) is a real failure. For Python environment changes, also run
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

The pytest example uses the root-tests interpreter under `.state/tools/` (not root
`.venv`, which holds locked CLIs such as zizmor). Adjust `py314` for your Python
version; on POSIX use `.state/tools/root-tests-py314/bin/python`. A bare
`python -m pytest` does not automatically use that environment.

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

**Prerequisites:** Docker Desktop (macOS/Windows) or Docker Engine (Linux) with Compose CLI v2 (`docker compose`).

Product and Browser CI images pin base layers by digest. Renovate opens a weekly
`docker-digests` PR (no automerge, no sticky `needs-manual-review`); merge after
green CI when you are ready. OS base *version* bumps (ubuntu/debian/alpine major/
minor/patch) still get `needs-manual-review`. Browser CI `image-pin.json`
`base_digests` describe the published artifact and may lag Dockerfile `FROM`
digests until the next verified rebuild + pin PR. After a successful
`build-browser-ci-image` workflow_dispatch/schedule publish, open/merge the
reviewed pin PR so `digest` / fingerprint / `base_digests` move together.

### Server (`opcua-ijt-server`)

Prefer Compose from `OPC_UA_Servers/Release2`:

```bash
cd OPC_UA_Servers/Release2
docker compose up --build
```

Equivalent one-off:

```bash
docker build -t opcua-ijt-server .
docker run --rm -p 40451:40451 opcua-ijt-server
```

The Dockerfile copies `OPC_UA_IJT_Server_Simulator_Linux.zip` and extracts it in a
BusyBox stage — do not host-unzip before `docker build`. The image sets
`IS_DOCKER=true` (same convention as Web Client / CI).

### Web Client

From `OPC_UA_Clients/Release2/IJT_Web_Client`:

```bash
python run_docker_setup.py          # docker compose (v2) when Docker is running
python run_docker_setup.py --mode local
```

Compose scopes container names by project (no global `container_name`).
`run_docker_setup.py` uses Compose CLI v2 with a path-derived `COMPOSE_PROJECT_NAME`
and image tag (parallel checkouts do not collide), `docker compose down -v
--remove-orphans` so the named `node_modules` volume cannot retain stale installs,
optional `--no-cache`, and forwards `--setup-args` into the container via
`IJT_SETUP_ARGS`. Healthchecks run `docker_healthcheck.py`: HTTP on `HTTP_PORT`
plus a real WebSocket upgrade on `WS_PORT`.

### Simulator ZIP extraction (host runners)

Shared helper: `scripts/simulator_extract.py` (cross-process lock, unique staging,
rename-aside swap, ZIP stamp + binary check, Unix exec-bit restore, member-path
and size/count caps before extract). The root
runner and Release 2 client runners ensure every **present** ZIP under
`OPC_UA_Servers/Release2/` into its own folder (`OPC_UA_IJT_Server_Simulator` and
`OPC_UA_IJT_Server_Simulator_Linux`). Auto-extract needs a full IJT clone (or set
`OPCUA_SIMULATOR_EXE` / `OPCUA_SERVER_URL`). Pre-stamp folders that already contain
the expected binary are **adopted in place** (stamp written, no rename-aside) so a
running simulator is not torn out from under parallel live suites on upgrade.

#### Hosted GHA vs local extract races

Local Phase 2 can start several client runners that would otherwise extract the
same ZIP concurrently. The shared helper serializes that with a cross-process
lock, unique staging, and rename-aside swap. Hosted GitHub Actions often **does
not** hit that race: many jobs pre-extract a single ZIP serially
(`Expand-Archive` / `unzip`) or build the server image (in-container BusyBox
extract) before live suites. Treat hosted green runs as evidence of *their*
setup path, not proof that local parallel extract is safe without the shared
helper.

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
