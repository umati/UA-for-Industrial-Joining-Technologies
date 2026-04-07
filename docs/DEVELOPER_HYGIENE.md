# Developer Hygiene

This document covers local workspace cleanup and generated-artifact handling for the IJT reference repo.

---

## Automatic Cleanup — post-run (every `run_all_tests.py`)

Every `run_all_tests.py` calls `_cleanup_caches()` after reports are written. Cleanup is **self-contained and scoped** — each runner only cleans its own directory:

| Runner | Scope | What is removed |
|--------|-------|-----------------|
| Sub-project runners (Web, Console, Test, Server, C#, Node) | Own project directory (recursive) | `__pycache__`, `.ruff_cache`, `.mypy_cache`, `.coverage*`, `*.pyc` |
| Root orchestrator (`run_all_tests.py`) | Repo root level only (non-recursive) | Same — sub-projects clean themselves via their own runners |

`.pytest_cache` is intentionally **preserved** — it holds `--lf`/`--ff` (last-failed / first-failed) state for developer workflow.
`test-results/` is always **preserved** — it holds the reports.

---

## Automatic Cleanup — pytest temp dirs (primary mechanism)

All Python pytest projects are configured so no manual intervention is needed for test temp dirs:

| Setting | Value | Effect |
|---------|-------|--------|
| `--basetemp=tests/fixtures/tmp` | in each `pytest.ini` `addopts` | Temp dirs land inside the repo; avoids OS temp ACL permission errors on Windows |
| `tmp_path_retention_count = 0` | in each `pytest.ini` | Pytest purges all previous-session dirs automatically at the start of each new run |

Applies to: **IJT_Web_Client**, **IJT_Console_Client**, **IJT_Test_Client**.

The `tests/fixtures/tmp/` dirs in each project are covered by `**/tests/fixtures/tmp/` in `.gitignore` — they will never be committed.

---

## Manual Cleanup — `git clean` (when needed)

For occasional deep cleans (reclaiming disk space, guaranteed fresh state). Always do a dry-run first.

```bash
# 1. Preview what would be removed
git clean -fdXn

# 2. Remove all gitignored artifacts — KEEPS venv/node_modules (excluded below)
git clean -fdX -e 'venv' -e '.venv*' -e 'node_modules' -e 'OPC_UA_IJT_Server_Simulator*'
```

`-f` force, `-d` include dirs, `-X` only gitignored files (safe — never touches committed or untracked files).

### What this removes
Everything in `.gitignore` except the excluded items above:
`__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `.dotnet`, `test-results`,
`playwright-report`, `TestResults`, `coverage`, `htmlcov`, `tests/fixtures/tmp/`, `.pyc`/`.pyo`, `.coverage*`, `logs/`, `.state/`, `pki/`, `PKI/`, `result_logs/`

### What is intentionally preserved

| Excluded | Why |
|----------|-----|
| `venv/`, `.venv*` | Active Python environments — slow to recreate |
| `node_modules/` | npm cache — slow to recreate |
| `OPC_UA_IJT_Server_Simulator*` | Extracted server binary — large, keep unless zip changes |

