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

## Validation Commands

```bash
# Install dependencies and activate shared local Git hooks
npm ci

# Public baseline validation
python run_all_tests.py --private-modules skip

# JavaScript lane; public deterministic baseline (private modules skipped by default)
python run_all_tests.py --phase1-js

# JavaScript lane; opportunistic private checks when the submodule is present
python run_all_tests.py --phase1-js --private-modules auto

# JavaScript lane; require the private Envelope submodule and fail if absent
python run_all_tests.py --phase1-js --private-modules require

# Authorized developers: initialize optional private Envelope from the IJT repo root
git submodule update --checkout --init --recursive -- OPC_UA_Clients\Release2\IJT_Web_Client\src\javascripts\views\envelope

# Full local runner
python run_all_tests.py

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

The Web Client has repo-tracked Husky hooks under `.husky/`. They are installed by `npm ci` from this package and configured against the IJT Git root, because this package is nested under `OPC_UA_Clients\Release2\IJT_Web_Client`.

| Hook | Purpose |
|------|---------|
| `pre-commit` | Auto-fixes changed tracked JavaScript and CSS files through `npm run lint:precommit`, then re-stages fixes only during actual Git hook execution. |
| `pre-push` | Runs `npm run lint:test:prepush`, currently the stable lint gate. Full unit and integration coverage remain CI/runner owned because the current local unit baseline includes unrelated failures. |

Hook files must stay LF-normalized through `.gitattributes`; do not add shell hook files without matching `text eol=lf` coverage.

## Definition of Done

- All validation commands pass.
- No regressions in existing passing tests.
- Changes stay inside the intended scope.
- Summary of changes provided: files touched, risks, and any follow-up needed.

## Notes

- Prefer small, reviewable changes.
- Document significant design decisions or assumptions in code comments or the PR description.
