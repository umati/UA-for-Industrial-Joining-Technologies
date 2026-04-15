# Development Guide — IJT Web Client

Development guidelines and workflow for this project.

## Every Request Must Include

| Field | What to put |
|-------|-------------|
| **Goal** | Bug fix / refactor / feature / docs / cleanup |
| **Scope** | Exact files or folders the agent may change |
| **Constraints** | Behaviour change allowed? Style rules? |
| **Validation** | Commands to run to confirm success |
| **Definition of Done** | What passing looks like |

## Guardrails (always apply)

- Do **not** edit `.venv/` or `node_modules/`.
- Do **not** change Docker setup unless explicitly requested.
- Prefer code that is easy to read and understand. This code is used for educational purpose.
- Prefer minimal, targeted edits over broad rewrites.
- Comment the code where it makes reading and understanding easier.
- If runtime behaviour might change, explain assumptions and impact first.
- Never guess — ask if uncertain.
- Preserve existing public APIs unless the request explicitly changes them.

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
- No regressions in previously passing tests.
- Changes stay inside the approved scope.
- Agent summarises: files changed, risks, and any follow-up needed.

---

## Request Templates

### 1 — Generic

```text
Goal:      <what to improve/fix>
Scope:     <allowed files/folders>
Exclude:   <anything off-limits>
Constraints:
  - Behaviour change allowed: Yes / No
  - Style: follow existing conventions
Validation: python run_all_tests.py + npx eslint ...
Done when: lint passes, tests pass, changes inside scope.
Output: summary of changes, files touched, risks.
```

### 2 — Bug Fix

```text
Goal:      Fix <describe bug> at root-cause level.
Scope:     <target files>
Constraints:
  - No unrelated refactor.
  - Preserve behaviour outside the bug.
Validation: reproduce the bug first, then confirm it no longer occurs.
Done when: reproduction passes, no new lint/runtime issues.
```

### 3 — Refactor

```text
Goal:      Refactor <component> for readability/maintainability.
Scope:     <target files>
Constraints:
  - No functional behaviour change.
  - Keep public API stable.
Validation: npx vitest run + python run_all_tests.py
Done when: same behaviour, cleaner structure, all checks pass.
```

### 4 — Environment / Setup Repair

```text
Goal:      Repair local setup so the project runs end-to-end.
Scope:     setup scripts, environment config, dependency files only.
Constraints:
  - Do not edit application behaviour unless required for startup.
Validation:
  - python -m pip check
  - python index.py  (backend starts on ws://localhost:8001)
  - http://localhost:3000 returns 200
  - npm run lint passes
Done when: dependencies install cleanly, backend + frontend both start.
```

### 5 — Documentation Update

```text
Goal:      Improve docs for <setup / operations / agent workflow>.
Scope:     README.md and docs/*.md only.
Constraints:
  - Keep all commands copy-paste ready.
  - Use concise, unambiguous language.
Validation: verify all referenced commands exist in package.json / scripts.
Done when: a new contributor can run the project from docs alone.
```

## Notes

- Prefer small, reviewable changes.
- State assumptions explicitly before editing.
- If blocked, report the exact blocker and the minimum action needed to continue.
