# Contributing to OPC UA IJT

Thank you for your interest in contributing to the VDMA OPC UA Industrial Joining Technologies project.

## Development Setup

### Runtime Requirements

- **Python 3.14** or newer (with `pip` and `venv`)
- **Node.js 24** or newer (with `npm`)
- **Git** (available on system PATH)

Central version files:

- `.nvmrc` for Node.js
- `.python-version` for Python

### Optional Tools (Auto-Skipped if Missing)

- **.NET SDK 10+** for the C# client
- **Docker** for containerized server testing

## Testing and Validation

### Before Committing

```bash
python run_precommit_all.py
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

### Full Test Suite

```bash
python run_all_tests.py
```

## Development Guidelines

1. Run pre-commit checks before pushing.
2. Run the full test suite to validate your changes.
3. Verify component-specific tests when relevant.
4. Keep documentation updated when behavior changes.
