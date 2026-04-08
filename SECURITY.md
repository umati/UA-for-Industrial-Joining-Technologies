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
  `bandit` (Python), `npm audit` (Node.js), and CodeQL static analysis (C#, Python, JavaScript)
  using the `security-extended` query suite (`.github/workflows/codeql.yml`).
- GitHub Actions workflow files are audited by [zizmor](https://woodruffw.github.io/zizmor/)
  on push/PR touching `.github/workflows/` and nightly — findings are uploaded as SARIF to
  GitHub Code Scanning (Security → Code scanning alerts). The audit job never fails CI;
  it is skipped on fork PRs where `security-events: write` is unavailable.
