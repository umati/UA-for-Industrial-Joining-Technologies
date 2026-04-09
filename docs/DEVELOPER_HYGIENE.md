# Developer Hygiene

Covers workspace cleanup, test temp directory management, and coverage configuration for the IJT reference repo.

---

## Pre-Commit Hooks — Auto-Fix on Every Commit

This repo uses [pre-commit](https://pre-commit.com/) to automatically fix formatting and line-ending issues
**before any commit is recorded**.  Most hooks are auto-fixers that never block a contributor — they silently
reformat files so the commit succeeds on the second attempt.

> **Note:** A small set of *detector* hooks do block by design if they find real problems:
> `check-json`, `check-yaml`, `check-toml` (config syntax errors), `check-merge-conflict` (stray `<<<<<<<`
> markers), and `debug-statements` (stray `breakpoint()`).  These require manual fixes before committing.

### First-time setup (once per machine, per clone)

```sh
pip install pre-commit          # or: pip install -r requirements-dev.txt
pre-commit install              # installs the hooks into .git/hooks/
```

The three Python test runners (Console, Web, Test) call `pre-commit install` automatically, so hooks are
installed the first time you run `python run_all_tests.py`.  For other runners (CSharp, Node, Server) or
direct git use, run `pre-commit install` manually once after cloning.

### What happens on `git commit`

1. `ruff-format` rewrites any Python files with wrong indentation / quotes / blank-lines.
2. `ruff --fix` auto-applies safe lint fixes.
3. `end-of-file-fixer` and `mixed-line-ending` normalise LF/CRLF on all text files.
4. `trailing-whitespace` strips trailing spaces.

If any hook modifies files the commit is aborted and you see:

```
ruff format..............................................................Failed
- hook id: ruff-format
- files were modified by this hook
```

**Simply run `git add -u && git commit` again** — the fixed files are already staged.  One extra command,
then it's done.  No manual reformatting required.

Hooks that detect problems without auto-fixing (and do block the commit until resolved):
- `check-merge-conflict` — stray `<<<<<<` markers
- `check-json` / `check-yaml` / `check-toml` — syntax errors in config files
- `debug-statements` — stray `breakpoint()` / `pdb.set_trace()`

### Auto-generated files are excluded

Everything under `OPC_UA_Clients/Release2/IJT_CSharp_Client/Types/` is generated from UA-ModelCompiler and
is excluded from **all** hooks globally (set in `.pre-commit-config.yaml` `exclude:` key and in root
`pyproject.toml` `[tool.ruff] exclude`).  Never edit those files manually.

---

## Virtual Environment Naming Convention

Each project creates **two independent environments** so that running tests never pollutes the launch
environment and vice versa.

| Directory | Created by | Contents | Typical use |
|-----------|-----------|----------|-------------|
| `.venv` | `setup_client.py` / `setup_project.py` | `requirements.txt` only | `python main.py` / standalone launch (Windows, Linux, macOS, WSL) |
| `.venv_test` | `run_all_tests.py` | `requirements.txt` + `requirements-dev.txt` | Test runs, CI |
| `/opt/ijt_venv` | Docker `ENTRYPOINT` | `requirements.txt` | Docker container runtime |

> **WSL note:** `bootstrap_wsl.sh` calls `setup_project.py` after OS provisioning, which creates the standard
> `.venv`.  There is no separate `.venv_wsl` at runtime — WSL non-Docker uses `.venv` like every other host.

**Rule:** never activate `.venv_test` to run the application, and never run tests inside `.venv`.

Both `setup_*.py` and `run_all_tests.py` remove stale legacy directories (`venv/`, `venv_test/`, `env/`,
`ENV/`, `.venv_backup/`) on startup.  A fresh clone always gets a clean state automatically.

The `.gitignore` uses `.venv*/` which covers all variants.  The `.gitattributes` `eol=lf` rule applies to
all text files so line endings are always normalised regardless of the editor or OS.

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

Console and Test clients keep pytest temp files **inside each project directory** to avoid host-level permission issues in protected OS temp folders. Web client intentionally uses a different policy (below).

| Project | `addopts` | Notes |
|---------|-----------|-------|
| `IJT_Console_Client` | `-v --basetemp=tmp/pytest` | Keeps pytest session dirs project-local |
| `IJT_Test_Client` | `-v --basetemp=tmp/pytest` | Same |
| `IJT_Web_Client` | `-v -p no:cacheprovider` | No fixed basetemp — uses system temp; `cacheprovider` disabled to prevent `pytest-cache-files-*` ACL churn |

`tmp/` is gitignored in each project. `tmp_path_retention_policy = "failed"` means only failing-test artifacts are retained.

The Web client's `local_temp_dir` fixture (used in `test_ijt_interface.py`) writes to `.state/tmp/test-fixtures/{uuid}` with explicit `yield`/`finally` cleanup — it never touches `tmp/pytest` and is excluded from Docker build context via `.dockerignore`.

**Never override `TMP`/`TEMP`/`TMPDIR` env vars** to redirect pip's temp directories — this causes ACL-locked wheel build directories on Windows.

---

## Automatic Cleanup — post-run

Every `run_all_tests.py` calls `_cleanup_caches()` after writing reports. Scope is **self-contained** — each runner cleans only its own directory tree.

| Runner | Scope | Removes |
|--------|-------|---------|
| Sub-project runners (Web, Console, Test, Server, C#, Node) | Own project dir (recursive) | `__pycache__`, `.ruff_cache`, `.mypy_cache`, `.coverage*`, `*.pyc` |
| Root orchestrator | Repo root only (non-recursive) | Same + `pki/`, `PKI/` |

**Cleaned post-run:** `.pytest_cache` (regenerates on next run; `--lf`/`--ff` only works within the same session). Always preserved: `test-results/` (reports).

---

## pytest Temp Directory Design

Console and Test clients share the same `[tool.pytest.ini_options]` basetemp configuration:

```toml
# pyproject.toml (Console + Test clients)
[tool.pytest.ini_options]
addopts = "-v --basetemp=tmp/pytest"
tmp_path_retention_policy = "failed"
```

`--basetemp=tmp/pytest` keeps pytest session directories inside each project under `tmp/pytest/`, avoiding OS/user temp folders whose ACLs can be restrictive on corporate Windows machines. `tmp_path_retention_policy = "failed"` retains artifacts only for failing tests.

The Web client is different — it disables `cacheprovider` to prevent `pytest-cache-files-*` ACL-locked directories:

```toml
# pyproject.toml (Web client)
[tool.pytest.ini_options]
addopts = "-v -p no:cacheprovider"
tmp_path_retention_policy = "failed"
```

### Console and Web Clients: pyfakefs for filesystem-touching unit tests

`IJT_Console_Client` and `IJT_Web_Client` go one step further. Tests in `test_setup_client.py` and `test_setup_project.py` simulate virtual environment layouts (checking for `.venv/Scripts/python.exe`, extracting simulator ZIPs, etc.). On hardened Windows setups, writing `.exe` files inside a `Scripts/` path can trigger OS security policies that lock the containing directory.

The solution: all filesystem-touching unit tests use the **`fs` fixture from `pyfakefs`** instead of `tmp_path`. The fake filesystem intercepts `pathlib`, `os`, `shutil`, and `zipfile` calls in-process — no real files are written to disk for those tests.

> **Web Client `local_temp_dir` fixture:** `test_ijt_interface.py` uses a `local_temp_dir` fixture that writes to `.state/tmp/test-fixtures/{uuid}` (not `tmp_path`) with a `yield`/`finally` cleanup. This avoids pyfakefs interaction with pytest's basetemp chain entirely. The `.state/tmp/` path is gitignored and excluded from Docker build context.

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

---

## Coverage Configuration

Coverage is configured in each project's `pyproject.toml`. **Never hardcode thresholds in runner scripts** — config files are the version-controlled, reviewable source of truth.

```toml
[tool.coverage.run]
omit = [
    "run_all_tests.py",   # runner infrastructure
    "setup_*.py",         # setup/install scripts
    "tests/live/*",       # require live server; excluded from unit runs
    ".venv/*", ".venv_test/*",
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

### Docstring Coverage (interrogate)

`interrogate` measures what percentage of public functions/classes/methods have docstrings.
Thresholds are calibrated against the **real codebase** (source + tests, venvs excluded):

| Project | ail-under | Notes |
|---------|-------------|-------|
| Console Client | 25% | Honest floor; tests included in scan |
| Web Client | 42% | Honest floor; tests included in scan |
| Test Client | 65% | Higher bar; source is well-documented |

> **Why these numbers?** Prior thresholds were inflated because interrogate inadvertently scanned
> .venv_test/ library code (which has near-100% docstrings). After correctly excluding venvs,
> the real scores are lower. Thresholds are set ~2% below actual to allow for minor fluctuations.
> Ratchet them upward as docstrings are added.

---

## Windows-Locked Temp Directories

On Windows, certain tools (notably **pyfakefs**) can leave directories with restricted ACLs that
survive test teardown and cannot be deleted by standard Python or shell commands:

- pytest-cache-files-* at project root — pyfakefs basetemp bookkeeping
- 	mp/pytest — if pyfakefs is active when pytest creates basetemp
- .state/tmp/test-fixtures/ijt-web-* — Web local_temp_dir fixture leftovers

**Built-in protections already in place:**

| Protection | Mechanism |
|-----------|-----------|
| _force_rmtree(path) | All 7 runners + 2 setup scripts — shutil.rmtree(onexc=...) with os.chmod retry |
| [tool.mypy] exclude | Skips pytest-cache-files-.* before mypy walks into them |
| [tool.pylint.main] ignore-paths | Same exclusion for pylint |
|
orecursedirs | pytest never collects from pytest-cache-files-* or 	mp |
| -p no:cacheprovider (Web) | Prevents pytest-cache-files-* creation entirely |
| .dockerignore | 	ests/fixtures/tmp/ excluded from Docker build context |

**If a locked dir survives a run** it sits inert — tools skip it, Docker ignores it. It clears
automatically on the next machine restart (Windows releases file handles on reboot).

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
