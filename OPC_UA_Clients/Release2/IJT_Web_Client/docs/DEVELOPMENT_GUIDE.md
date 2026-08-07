# Development Guide — IJT Web Client

Contribution guidelines and workflow for this project.

## Contribution Checklist

Before submitting a change, confirm:

| Item | Detail |
|------|--------|
| **Goal** | Bug fix / refactor / feature / docs / cleanup |
| **Scope** | Files and folders changed |
| **Constraints** | Behaviour change intended? Style rules followed? |
| **Validation** | Validation commands run and passing |
| **Summary** | Files changed, risks noted, follow-up identified |

## Contribution Guidelines

- Do **not** edit `.venv/` or `node_modules/`.
- Do **not** commit local `src/resources/connectionpoints.json` or `src/resources/settings.json`; edit the `*.default.json` templates only when changing shared defaults.
- Do **not** change Docker setup unless the contribution requires it.
- Prefer code that is easy to read and understand — this project is used for educational purposes.
- Prefer minimal, targeted edits over broad rewrites.
- Comment code where it aids understanding.
- If runtime behaviour might change, document the assumptions and impact.
- Preserve existing public APIs unless the change explicitly requires updating them.

## Runtime JSON resources

The shared defaults live in `src/resources/connectionpoints.default.json` and `src/resources/settings.default.json`.
The backend creates `connectionpoints.json` and `settings.json` locally when they are missing, then reads and writes those runtime files.

Keep personal controller endpoints and local UI preferences in the generated runtime files only. If a default should apply to every fresh checkout, change the matching `*.default.json` template and keep the runtime file ignored.

`setup_project.py` keeps direct launches independent from tests: it restores the
normal `LOCAL` profile from the committed template while preserving additional
profiles, uses `OPCUA_SERVER_URL` only as an explicit direct-runtime server
override, and removes `OPCUA_TEST_ENDPOINT` and `IJT_RUNTIME_RESOURCES_DIR` from
the backend launch environment. Runner-managed backends use isolated resource
directories and dedicated ports. Each Playwright backend worker owns a separate
runtime-resource directory seeded with its matching `LOCAL` endpoint before the
backend starts. Browser fixtures also reassert that worker baseline before use
and restore the prior profile afterward, so failed or restarted workers cannot
leak Servers-page edits into another worker or a developer runtime profile.

With a lockfile present, setup retries transient `npm ci` failures. If Windows
still cannot clean stale generated packages, setup removes `node_modules` and
performs one final deterministic `npm ci` rather than switching install modes.
Docker detection takes precedence over WSL markers exposed by Docker Desktop.
Production images intentionally omit developer-only JavaScript packages, so
setup does not probe ESLint or neostandard versions when `NODE_ENV=production`.

Both Web Client OPC UA sessions explicitly request the simulator-supported
600,000 ms session timeout instead of relying on asyncua's one-hour default.
The repository-wide readiness probe uses the same value. This avoids harmless
server-revision warnings without changing the shorter per-request and
connection-handshake limits.

Pyright path configuration must resolve both `src/` and the repository-wide
`scripts/` directory. Console and Test Client live fixtures use the same shared
readiness module, so their Pyright paths must also include the repository
scripts directory. Keep actionable type findings at zero; do not suppress
missing imports caused by incomplete project paths.

Local multi-worker Playwright runs own one simulator per worker. The runner
monitors those owned processes throughout the feature stage and restarts an
instance if the native simulator exits unexpectedly. Keep this recovery in the
owner process; browser tests must not launch or manage simulator binaries.

## Validation Commands

```bash
# Install JavaScript dependencies (no hook side-effects)
npm ci

# Public baseline validation (no envelope required)
python run_all_tests.py --private-modules skip

# JavaScript lane; public deterministic baseline
python run_all_tests.py --phase1-js

# JavaScript lane; run envelope checks when the submodule is present (default)
python run_all_tests.py --phase1-js --private-modules auto

# JavaScript lane; require the private Envelope submodule and fail if absent
python run_all_tests.py --phase1-js --private-modules require

# Authorized developers: initialize optional private Envelope from the IJT repo root
git submodule update --checkout --init --recursive -- OPC_UA_Clients\Release2\IJT_Web_Client\src\javascripts\views\envelope

# Full local runner
python run_all_tests.py

# One-command pre-push quality + dependency security gate from IJT repo root
python run_precommit_all.py

# Backend starts
python index.py

# Frontend serves
# open http://localhost:3000
```

The private Envelope submodule is opt-in for Git updates so normal IJT pulls work
without private repository access. If you want recursive pulls to update Envelope
on your authenticated machine, set local-only Git config from the IJT repo root:

```bash
git config submodule.OPC_UA_Clients/Release2/IJT_Web_Client/src/javascripts/views/envelope.update checkout
git config submodule.recurse true
```

## Local Git hooks

Pre-commit hooks are managed by [pre-commit](https://pre-commit.com/) from the **IJT repository root** — a single hook manager covers all sub-projects including this Web Client.

Install once after cloning:

```bash
pip install pre-commit
pre-commit install        # installs into root .git/hooks
```

| Hook (IJT root `.pre-commit-config.yaml`) | Covers |
|---|---|
| `eslint-web-client` | ESLint auto-fix on **all tracked modified** `.mjs` / `.js` files (staged + unstaged) via `scripts/precommit-fix-uncommitted.mjs` |
| `stylelint-web-client` | Stylelint auto-fix on **all tracked modified** `.css` files (staged + unstaged) |
| `eslint-envelope` | Same as above for Envelope JS files (no-op when submodule absent) |
| `stylelint-envelope` | Same as above for Envelope CSS files (no-op when submodule absent) |

> **All tracked modified files, not just staged** — `scripts/precommit-fix-uncommitted.mjs` uses `git status --porcelain` to collect every modified tracked file (staged and unstaged). This prevents a commit leaving the working tree with lint issues in unstaged hunks. Fixed files are automatically re-staged. Set `PRECOMMIT_AUTO_STAGE=0` to opt out of auto-staging.

`python run_precommit_all.py` from the IJT repo root is the default local pre-push gate. It runs pre-commit hooks first, then dependency vulnerability checks:
1. `npm audit --package-lock-only --audit-level=high` for Node Client, Web Client, and Envelope lockfiles.
2. `pip-audit` across IJT and Envelope Python requirement files.

**Why not Husky?** The Web Client previously used Husky for its `pre-commit` hook. Husky v9 sets `git config core.hooksPath` to its own directory, which silently overrides the root `.git/hooks/` where `pre-commit install` writes — the two hook managers conflict. Pre-commit is the single source of truth.

## Definition of Done

- All validation commands pass.
- No regressions in existing passing tests.
- Changes stay inside the intended scope.
- Summary of changes provided: files touched, risks, and any follow-up needed.

## Notes

- Prefer small, reviewable changes.
- Document significant design decisions or assumptions in code comments or the PR description.
