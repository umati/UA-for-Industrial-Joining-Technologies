# Using Agents To Improve Code

## What To Include In Every Agent Request
- Goal: bug fix, refactor, performance, cleanup, or docs.
- Scope: exact files/folders allowed to change.
- Constraints: behavior change allowed or not, coding style constraints.
- Validation: commands the agent must run (`lint`, startup checks).
- Output: required summary format (changed files, risks, follow-up).

## Recommended Prompt Template
```text
Goal:
Scope:
Constraints:
Validation commands:
Definition of done:
```

## Definition Of Done (Agent Tasks)
- Changes stay inside approved scope.
- `npm run lint` passes.
- Backend starts (`index.py`).
- Frontend starts (`npm run start`).
- Agent reports changed files and remaining risks.

## Guardrails
- Do not edit `venv/` or `node_modules/`.
- Do not change Docker setup unless explicitly requested.
- Prefer minimal, targeted edits over broad rewrites.
- If runtime behavior might change, explain assumptions and impact.

# Common Agent Tasks
- Fix lint errors and keep behavior unchanged.
- Repair broken local environment (`venv`, missing dependencies).
- Add small, focused refactors with health-check verification.
- Improve docs and setup reliability.

