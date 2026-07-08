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
# Lint
npx eslint src/javascripts config.js --config eslint.config.mjs --max-warnings 0

# JS unit tests
npx vitest run

# Python unit tests (fast, no server)
python -m pytest tests/python/unit/ -q --timeout=30

# All tests
python run_all_tests.py

# Backend starts
python index.py

# Frontend serves
# open http://localhost:3000
```

## Definition of Done

- All validation commands pass.
- No regressions in existing passing tests.
- Changes stay inside the intended scope.
- Summary of changes provided: files touched, risks, and any follow-up needed.

## Notes

- Prefer small, reviewable changes.
- Document significant design decisions or assumptions in code comments or the PR description.
