# Contributing to OPC UA IJT

Thank you for your interest in contributing to the VDMA OPC UA Industrial Joining Technologies project.

## Development Setup

### Runtime Requirements

- **Python 3.14.x** for maintained development and CI (with `pip` and `venv`)
- **Node.js 24.15** or newer (with `npm`)
- **Git** (available on system PATH)

Central version files:

- `.nvmrc` for Node.js
- `.python-version` for Python

Python runtime updates are held to the 3.14 line by Renovate; dependency updates
remain enabled. The client minimum requirement `>=3.14` does not certify newer
interpreters. See [Python runtime update policy](DEVELOPMENT.md#python-runtime-update-policy)
for the hold and coordinated migration procedure.

### Optional Tools (Auto-Skipped if Missing)

- **.NET SDK 10+** for the C# client
- **Docker** for containerized server testing
- **OS/binary scanners** (hadolint, trivy, actionlint, …) when not on your PATH

Setup and test launchers install Python tools for you — you do **not** need to
`pip install` them globally. First run needs network (or an offline cache).
CI uses its own provisioned tools.

**Note:** `python run_all_tests.py` provisions pinned `zizmor` automatically. If
**install/sync fails**, findings are High/Critical, or the tool returns
empty/unparseable output, treat that as a real failure (not “optional tool
missing”). Details:
[What is Handled Automatically](DEVELOPMENT.md#what-is-handled-automatically).

For pip deployment and source reuse, see the
[Python Client Integration Guide](PYTHON_CLIENT_INTEGRATION.md).

## Testing and Validation

### Before Committing

```bash
python run_precommit_all.py --strict
```

`run_precommit_all.py` and the Node/Web Client test runners enforce dependency audits
at high severity. npm lockfile audits use a bounded 15-second process timeout and
default to **strict** connectivity mode (`IJT_NPM_AUDIT_MODE=strict`): registry
timeout/connectivity failures fail quickly because vulnerability status is unknown.
Use `IJT_NPM_AUDIT_MODE=offline` for explicitly offline local runs. GitHub
application/static lanes use the same availability policy so recognized npm
advisory-service outages are reported as infrastructure warnings rather than
product failures. Actual high/critical findings and non-network tool failures
still fail in both modes. The dependency-security workflow reviews pull-request
dependency changes, runs daily monitoring, and provides manual strict release
qualification.

For available-only local checks, omit `--strict`: missing .NET/npm system audit
tools are reported as incomplete validation. Package preparation failures and
available check failures remain blocking. System-tool strictness is separate
from npm registry connectivity mode.

### Full Test Suite

```bash
python run_all_tests.py
```

Inspect the summary for skipped suites (e.g. Docker or .NET missing). An
explicitly requested `--suite` fails if it cannot run. More detail:
[Development — Testing](DEVELOPMENT.md#testing).

## Development Guidelines

1. Run pre-commit checks before pushing.
2. Run the full test suite to validate your changes.
3. Verify component-specific tests when relevant.
4. Keep documentation updated when behavior changes.
