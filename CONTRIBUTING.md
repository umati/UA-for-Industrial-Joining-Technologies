# Contributing to OPC UA IJT

Thank you for your interest in contributing to the VDMA OPC UA Industrial Joining Technologies project!

## Development Setup

### Runtime Requirements

- **Python 3.14** or newer (check with `python --version`)
- **Node.js 24** or newer (check with `node --version`)
- **Docker** (optional; tests skip gracefully if unavailable)

These runtimes are centralized in root configuration files:
- `.nvmrc` specifies the Node.js version
- `.python-version` specifies the Python version

Package manifests enforce minimum versions:
- Node.js: `engines` field in `package.json`
- Python: `requires-python` in `pyproject.toml`

### Optional Tools

- **.NET SDK** (for C# client development)
- **npm** (for web/console client development)

Missing optional tools are fine—tests and builds skip gracefully. Exit code `0` means all available tests passed.

## Testing and Validation

### Before Committing

Always run the pre-commit validation suite to catch issues early:

```bash
python run_precommit_all.py
```

This command:
- Runs IJT + Envelope pre-commit hooks (linting, formatting)
- Checks for high-severity dependency CVEs in Node.js and Python packages
- Blocks on critical security issues

### Full Test Suite

Run the complete test and quality gate suite:

```bash
python run_all_tests.py
```

This includes:
- Static code checks (linting, type checking, formatting)
- Unit tests
- Integration tests (if Docker is available)
- Specification compliance tests

### Test Tiers

For detailed information on test categories and how to run specific test tiers, see [docs/TEST_TIERS.md](docs/TEST_TIERS.md).

## Development Guidelines

1. **Run pre-commit checks** before pushing:
   ```bash
   python run_precommit_all.py
   ```

2. **Run the full test suite** to validate your changes:
   ```bash
   python run_all_tests.py
   ```

3. **Verify your changes** don't break existing functionality by running component-specific tests.

4. **Keep documentation up-to-date** when adding features or changing behavior.

## Repository Structure

- **OPC_UA_Servers/** – Server implementations and simulators
- **OPC_UA_Clients/** – Client implementations (Web, Console, C#, Test)
- **IJT_Documents/** – Reference documents and presentations
- **docs/** – Developer and contributor documentation
- **tests/** – Test suites and fixtures
- **scripts/** – Utility and automation scripts

## Specifications and Standards

This project implements OPC UA standards for joining technologies:

- [OPC 40450-1 Joining - Online Reference](https://reference.opcfoundation.org/IJT/Base/v100/docs/)
- [OPC 40451-1 Tightening - Online Reference](https://reference.opcfoundation.org/IJT/Tightening/v200/docs/)
- [OPC Foundation IJT Page](https://opcfoundation.org/markets-collaboration/IJT/)

## Security

To report a security vulnerability, see [SECURITY.md](../SECURITY.md).

## Getting Help

- Check existing issues on [GitHub](https://github.com/umati/UA-for-Industrial-Joining-Technologies/issues)
- Review [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed technical setup
- Contact the project coordinator: Bernd Heitzmann - bernd.heitzmann@vdma.eu

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors.
