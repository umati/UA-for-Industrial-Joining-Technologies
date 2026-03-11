# Agent Task Template

Use this file to create clear, repeatable requests for coding agents.

## 1) Generic Template

```text
Goal:
- What should be improved/fixed?

Scope:
- Allowed files/folders:
- Excluded files/folders:

Constraints:
- Behavior change allowed: Yes/No
- Performance impact constraints:
- Style/format constraints:

Validation Commands:
- npm run lint
- venv\Scripts\python.exe -m pip check
- venv\Scripts\python.exe index.py
- npm run start

Definition of Done:
- Lint passes.
- Backend starts on ws://localhost:8001.
- Frontend serves on http://localhost:3000.
- Changes are minimal and inside scope.
- Output includes changed files + risks.

Output Format Required:
1. Summary of changes
2. Files changed
3. Validation results
4. Risks / follow-ups
```

## 2) Bug Fix Request

```text
Goal:
- Fix [describe bug] with root-cause-level correction.

Scope:
- [list target files]

Constraints:
- No unrelated refactor.
- Preserve existing behavior outside the bug.

Validation Commands:
- npm run lint
- [add a specific reproduction check]

Definition of Done:
- Reproduction no longer fails.
- No new lint/runtime issues.
```

## 3) Refactor Request

```text
Goal:
- Refactor [component/module] for readability/maintainability.

Scope:
- [list target files]

Constraints:
- No functional behavior change.
- Keep public API stable.

Validation Commands:
- npm run lint
- venv\Scripts\python.exe index.py
- npm run start

Definition of Done:
- Same behavior, cleaner structure, passing checks.
```

## 4) Runtime/Environment Repair Request

```text
Goal:
- Repair local setup so project runs end-to-end.

Scope:
- setup scripts, environment config, dependency files only.

Constraints:
- Do not edit application behavior unless required for startup.

Validation Commands:
- venv\Scripts\python.exe -m pip check
- venv\Scripts\python.exe index.py
- npm run start
- npm run lint

Definition of Done:
- Dependencies install cleanly.
- Backend + frontend both start.
- Lint passes.
```

## 5) Documentation Update Request

```text
Goal:
- Improve docs for [setup/operations/agent workflow].

Scope:
- README.md and docs/*.md only.

Constraints:
- Keep commands copy/paste ready.
- Use concise, unambiguous language.

Validation Commands:
- Verify all referenced commands still exist in package.json/scripts.

Definition of Done:
- New contributor can run project from docs alone.
```

## Notes
- Prefer small, reviewable changes.
- If assumptions are needed, state them explicitly before editing.
- If blocked, report exact blocker and the minimum action needed to continue.
