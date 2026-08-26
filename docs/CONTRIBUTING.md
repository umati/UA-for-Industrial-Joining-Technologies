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

### Full Test Suite

```bash
python run_all_tests.py
```

## Development Guidelines

1. Run pre-commit checks before pushing.
2. Run the full test suite to validate your changes.
3. Verify component-specific tests when relevant.
4. Keep documentation updated when behavior changes.
