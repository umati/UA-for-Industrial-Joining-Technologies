# Security Policy

## Scope

This repository contains **reference implementations** of the
[OPC UA Industrial Joining Technologies (IJT)](https://opcfoundation.org/markets-collaboration/IJT/)
companion specification. The code is intended for demonstration and interoperability testing — it is
**not** designed or hardened for production deployment without additional security review.

## Supported Versions

Security fixes are applied to the **`main` branch** only.
Older tags or releases are not actively maintained.

| Branch / Tag | Supported |
|--------------|-----------|
| `main` | ✅ Yes |
| Any tagged release | ❌ No — update to `main` |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report privately by emailing:

| Name | Role | Email |
|------|------|-------|
| Mohit Agarwal | Coordinator / maintainer | mohit.agarwal@atlascopco.com |

Include in your report:
- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept
- The affected file(s) / component(s)

We aim to acknowledge reports within **5 business days** and provide a fix or mitigation within
**30 days** for confirmed vulnerabilities.

## Known Limitations

- The OPC UA server simulator (`OPC_UA_Servers/`) is a **demo server** with no authentication or
  encryption configured by default. Do not expose it on untrusted networks.
- The web client (`IJT_Web_Client`) binds its WebSocket backend to `localhost` by default.
  Review `client_config.py` and Docker port mappings before any network-accessible deployment.
- Dependencies are kept up to date via [Renovate](renovate.json) and audited in CI via
  `pip-audit` (Python dependencies), `npm audit` (Node.js dependencies), the C# NuGet
  vulnerability scan, `bandit` (Python SAST), and CodeQL static analysis.
  Python clients maintain independent PEP 621 `pyproject.toml` configurations with locked
  dependencies in per-client `uv.lock` files. Dependency vulnerability status is audited via
  `pip-audit` against exported lock definitions during pre-commit checks and CI.
  Local `run_precommit_all.py` and the Node/Web Client test runners enforce npm audit in
  strict mode by default (`IJT_NPM_AUDIT_MODE=strict`), so npm registry
  timeout/connectivity failures fail because vulnerability status is unknown.
  npm audit subprocesses are bounded to 15 seconds to prevent an unavailable advisory endpoint from
  hanging validation. `IJT_NPM_AUDIT_MODE=offline` exists only for
  explicitly offline/restricted local development. GitHub application/static lanes also use this
  availability policy so a verified advisory-service outage is reported as infrastructure
  rather than a product defect; high/critical findings and non-network tool errors remain
  blocking. The dedicated dependency-security workflow reviews dependency changes
  on pull requests, monitors all ecosystems daily in offline mode, and
  provides a manual strict release-qualification audit.
  The root audit runner requires package tooling and inputs for public projects;
  preparation failures fail validation. Missing .NET/npm system tools are reported
  as incomplete validation by default; `--strict` fails when unavailable.
  The private Envelope submodule is optional and
  is audited only when its checkout is available. Independent audit tasks run
  with a global two-worker limit and return an aggregate failure status.
  Local launchers prepare package tooling in isolated `.state/tools/`
  environments; preparation errors block validation. CI/Docker use provisioned
  tooling without bootstrap downloads. Pip-based deployments should use the
  locked exports described in the [integration guide](docs/PYTHON_CLIENT_INTEGRATION.md);
  fresh resolution from project metadata does not enforce uv-specific constraints.
- GitHub Actions workflow files are audited by [zizmor](https://woodruffw.github.io/zizmor/)
  in the CI workflow when `.github/workflows/` changes, or on manual dispatch. Findings are
  uploaded as SARIF to GitHub Code Scanning (Security → Code scanning alerts). High/Critical
  findings fail the local root-runner gate; repository branch protection or Code Scanning
  check-failure settings are required if new Code Scanning alerts should also block merges.
  The GitHub Actions zizmor job is skipped on fork PRs where `security-events: write` is
  unavailable.
- The CI `pre-commit` job runs the repository hook set on all files. The local and CI
  zizmor hooks use the same High/Critical severity policy as the root runner so local
  checks do not become stricter than CI.
