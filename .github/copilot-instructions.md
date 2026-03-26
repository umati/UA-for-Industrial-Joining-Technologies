# Copilot Instructions

## Hard Rules — NEVER violate these

1. **NO git commits** — Never run `git commit`, `git push`, `git merge`, or any command that writes to git history. The user will commit manually when ready.
2. **NO git staging** — Never run `git add` unless explicitly asked.
3. **Current directory only** — All file changes must stay within `C:\DDrive\SourceControl\GIT_HUB\UA-for-Industrial-Joining-Technologies\`. Never write, delete, or move files outside this directory.
4. **No force-push, no branch creation** — No destructive git operations.

## Working conventions

- Run tests freely (pytest, vitest, playwright, eslint, pylint, bandit, docker).
- Read any file or URL without asking.
- Make code changes, renames, and refactors freely within the repo.
- Always verify tests pass after changes.
- Report what was changed; do not silently commit or stage.
