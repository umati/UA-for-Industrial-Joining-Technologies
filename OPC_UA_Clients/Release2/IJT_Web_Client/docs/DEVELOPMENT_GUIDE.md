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

- Do not edit `.venv/`, `.venv_test/`, `.venv_ci/`, `.state/tools/`, or `node_modules/`.
- Do not commit local runtime JSON files.
- Prefer small, targeted edits over broad rewrites.
- Preserve existing public APIs unless the change explicitly requires updating them.

## Python Dependencies

Install Python 3.14+ and Node.js 24.15+, then run commands from the Web Client directory.
uv is prepared automatically if needed. `python setup_project.py` prepares
the runtime environment; `python run_all_tests.py --phase1-python` prepares the
separate test environment and runs Python checks.

Edit dependencies in `pyproject.toml`, run `uv lock`, and review both files.
Do not edit `uv.lock` by hand or commit generated requirements exports. Plain
`uv sync` targets `.venv`, not the runner's `.venv_test` or `.venv_ci`.

For deployment into a pip-managed environment and source reuse, see the
[shared integration guide](../../../../docs/PYTHON_CLIENT_INTEGRATION.md).
Those are user integration instructions, distinct from contributor tooling.

## Optional Private Envelope Module

Envelope is an optional private Git submodule mounted at `src/javascripts/views/envelope`. The public Web Client must continue to work when that submodule is unavailable.

Authorized developers with access to both repositories can use:

```powershell
python .\setup_project.py
python .\setup_project.py --private-modules-pinned
python .\setup_project.py --skip-private-modules
```

The deeper Envelope notes remain in `docs/SKILLS.md` and the local Envelope docs tree. The public README should stay free of those implementation details.
