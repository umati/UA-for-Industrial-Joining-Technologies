# Developer Hygiene

Covers workspace cleanup, test temp directory management, and coverage configuration for the IJT reference repo.

---

## Running Tests — Project Isolation Rule

**Always run tests from each project's own directory — never from repo root.**

```sh
# ✅ Correct — run from project directory
cd OPC_UA_Clients/Release2/IJT_Web_Client && pytest tests/python/unit
cd OPC_UA_Clients/Release2/IJT_Console_Client && pytest tests/unit

# ❌ Wrong — from repo root, both conftest.py files collide
pytest OPC_UA_Clients/Release2/IJT_Web_Client/tests OPC_UA_Clients/Release2/IJT_Console_Client/tests
```

Running multiple Python clients together in a single root `pytest` invocation causes an `ImportPathMismatchError` because both trees have a `tests/conftest.py`. The CI workflows and `run_all_tests.py` both enforce per-project `working-directory` — this is correct and intentional.

**In CI:** Every job uses `working-directory: OPC_UA_Clients/Release2/<client>` — projects never share a pytest process.

**For local full-suite runs:** Use each project's `run_all_tests.py` from its own directory, or the repo root orchestrator which delegates each runner with the correct `cwd`.

---

## Pytest Temp Root Policy

All three Python pytest projects (Web, Console, Test clients) keep temp files **inside each project directory** to avoid host-level permission issues in protected OS temp folders:

- `IJT_Console_Client/pytest.ini` — `--basetemp=.state/pytest_tmp`, `tmp_path_retention_policy = all`
- `IJT_Web_Client/pytest.ini` — `--basetemp=.state/pytest_tmp`, `tmp_path_retention_policy = all`
- `IJT_Test_Client/pytest.ini` — `--basetemp=.state/pytest_tmp`, `tmp_path_retention_policy = all`
- Each project's `run_all_tests.py` also sets `TMP`, `TEMP`, `TMPDIR`, and `PYTEST_DEBUG_TEMPROOT` to project-local `.state/` paths so subprocesses never fall back to machine temp locations.

`.state/` is gitignored in each project.

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

All three Python projects share the same `pytest.ini` configuration for temp management:

```ini
# pytest.ini (all three Python clients)
addopts = --basetemp=.state/pytest_tmp
tmp_path_retention_policy = all
```

`--basetemp` keeps pytest session directories inside each project under `.state/pytest_tmp`, avoiding OS/user temp folders whose ACLs can be restrictive on corporate Windows machines. `tmp_path_retention_policy = all` prevents pytest from attempting to delete old session directories at startup, which avoids `PermissionError` in edge cases where previous runs left locked artifacts.

### Console Client: pyfakefs for filesystem-touching unit tests

`IJT_Console_Client` and `IJT_Web_Client` go one step further. Tests in `test_setup_client.py` and `test_setup_project.py` simulate virtual environment layouts (checking for `venv/Scripts/python.exe`, extracting simulator ZIPs, etc.). On hardened Windows setups, writing `.exe` files inside a `Scripts/` path can trigger OS security policies that lock the containing directory.

The solution: all filesystem-touching unit tests use the **`fs` fixture from `pyfakefs`** instead of `tmp_path`. The fake filesystem intercepts `pathlib`, `os`, `shutil`, and `zipfile` calls in-process — no real files are written to disk for those tests. Pytest cache, coverage, and report files are still written normally to `.state/pytest_tmp`.

This approach works identically on Windows, Linux, and macOS, and requires no per-machine workarounds.

```python
# Before — wrote real files, could trigger ACL lock on Windows
def test_finds_direct_exe(self, tmp_path, monkeypatch):
    exe = tmp_path / sc.SIMULATOR_EXE_NAME
    exe.write_bytes(b"fake exe")
    ...

# After — all filesystem ops are in-memory, no real disk writes
def test_finds_direct_exe(self, fs, monkeypatch):
    exe = Path("/fake/sim") / sc.SIMULATOR_EXE_NAME
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"fake exe")
    ...
```

`pyfakefs~=6.1` is listed in `IJT_Console_Client/requirements-dev.txt` and `IJT_Web_Client/requirements-dev.txt`.

The `tests/fixtures/` directory is guaranteed to exist on fresh clones via `tests/fixtures/.gitkeep` committed in the project.

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
