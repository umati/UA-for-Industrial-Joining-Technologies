# Development Guide — IJT Web Client

Contribution guidelines and workflow for this project.

## Contribution Checklist

| Item | Detail |
|------|--------|
| Goal | Bug fix, refactor, feature, docs, or cleanup |
| Scope | Files and folders changed |
| Constraints | Behavior change intended? Style rules followed? |
| Validation | Validation commands run and passing |
| Summary | Files changed, risks noted, follow-up identified |

## Contribution Guidelines

- Do not edit `.venv/` or `node_modules/`.
- Do not commit local runtime JSON files.
- Prefer small, targeted edits over broad rewrites.
- Preserve existing public APIs unless the change explicitly requires updating them.

## Optional Private Envelope Module

Envelope is an optional private Git submodule mounted at `src/javascripts/views/envelope`. The public Web Client must continue to work when that submodule is unavailable.

Authorized developers with access to both repositories can use:

```powershell
python .\setup_project.py
python .\setup_project.py --private-modules-pinned
python .\setup_project.py --skip-private-modules
```

The deeper Envelope notes remain in `docs/SKILLS.md` and the local Envelope docs tree. The public README should stay free of those implementation details.
