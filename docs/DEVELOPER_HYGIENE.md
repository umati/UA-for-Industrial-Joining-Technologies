# Developer Hygiene

Covers workspace cleanup, test temp directory management, and coverage configuration for the IJT reference repo.

---

## Automatic Cleanup — post-run

Every `run_all_tests.py` calls `_cleanup_caches()` after writing reports. Scope is **self-contained** — each runner cleans only its own directory tree.

| Runner | Scope | Removes |
|--------|-------|---------|
| Sub-project runners (Web, Console, Test, Server, C#, Node) | Own project dir (recursive) | `__pycache__`, `.ruff_cache`, `.mypy_cache`, `.coverage*`, `*.pyc` |
| Root orchestrator | Repo root only (non-recursive) | Same + `pki/`, `PKI/` |

**Always preserved:** `.pytest_cache` (holds `--lf`/`--ff` state for developers) and `test-results/` (reports).

---

## pytest Temp Directory Design

All three Python projects (Web, Console, Test clients) share the same configuration:

```ini
# pytest.ini
addopts = --basetemp=tests/fixtures/tmp
tmp_path_retention_count = 0
```

`--basetemp` keeps temp files inside the repo (avoids OS temp ACL issues on Windows). `tmp_path_retention_count = 0` makes pytest self-clean on every run — no manual intervention needed.

`tests/fixtures/tmp/` is gitignored (`**/tests/fixtures/tmp/`). The parent `tests/fixtures/` must exist before pytest starts; it is guaranteed by two layers:

| Layer | Mechanism |
|-------|-----------|
| **Git** | `tests/fixtures/.gitkeep` committed — directory always exists on fresh clone |
| **pytest** | `pytest_configure` hook in each `conftest.py` calls `mkdir(parents=True, exist_ok=True)` — recreates if somehow absent |

---

## Coverage Configuration

Coverage is configured in each project's `pyproject.toml`. **Never hardcode thresholds in runner scripts** — config files are the version-controlled, reviewable source of truth.

```toml
[tool.coverage.run]
omit = [
    "run_all_tests.py",   # runner infrastructure
    "setup_*.py",         # setup/install scripts
    "tests/live/*",       # require live server; excluded from unit runs
    ".venv/*", "venv/*",
]

[tool.coverage.report]
fail_under = N            # calibrated per-project (see table below)
skip_empty = true
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:", "if __name__ == .__main__.:"]
```

Thresholds are calibrated to what **unit tests alone** can achieve after omitting infrastructure and live-only files:

| Project | `fail_under` | Notes |
|---------|-------------|-------|
| Web Client | 70% | Unit run achieves ~74% with omit list |
| Console Client | 80% | Unit run achieves ~85% with omit list |
| Test Client | 70% | No `tests/unit/`; threshold applies to live conformance stage |

---

## Manual Deep Clean — `git clean`

For reclaiming disk space or guaranteeing a pristine state. **Always dry-run first.**

```bash
git clean -fdXn                                                              # preview
git clean -fdX -e 'venv' -e '.venv*' -e 'node_modules' -e 'OPC_UA_IJT_Server_Simulator*'
```

`-X` removes only gitignored files — never touches committed or untracked files.

**Preserved by the excludes above:**

| Item | Why |
|------|-----|
| `venv/`, `.venv*` | Python environments — slow to recreate |
| `node_modules/` | npm cache — slow to recreate |
| `OPC_UA_IJT_Server_Simulator*` | Large extracted binary |

