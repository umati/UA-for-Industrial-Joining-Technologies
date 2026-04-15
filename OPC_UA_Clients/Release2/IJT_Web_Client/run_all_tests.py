#!/usr/bin/env python3
"""
IJT Web Client — Cross-Platform Test Runner
============================================
Works on: Windows, Linux, macOS, Docker, WSL
Requires: Python 3.14+  (already installed for this project)
No PowerShell, no bash, no special shell required.

Usage:
  python run_all_tests.py        # auto-detects all optional stages — ONE command for everything
  python run_all_tests.py --list # print stages and exit

Optional stages activate automatically when available:
  Docker smoke  — if Docker daemon is running  (BuildKit build + compose-up + readiness + down)
  Live OPC UA   — if server reachable at OPCUA_TEST_ENDPOINT  (default: opc.tcp://localhost:40451)
  Playwright E2E — if WebSocket backend reachable at WS_TEST_URL (default: ws://localhost:8001)

Force flags (override auto-detection):
  --integration  force live OPC UA stage even if server unreachable
  --e2e          force Playwright E2E stage even if WS backend unreachable
  --all          force every optional stage

Environment variables (all optional):
  OPCUA_TEST_ENDPOINT   default: opc.tcp://localhost:40451
  WS_TEST_URL           default: ws://localhost:8001
  UI_TEST_BASE_URL      default: http://127.0.0.1:3000
  IJT_DOCKER_TIMEOUT    seconds to wait for Docker HTTP readiness (default: 90)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Ensure stdout/stderr use UTF-8 on Windows (cp1252 can't encode box-drawing chars)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
IS_WINDOWS = os.name == "nt"
IS_DOCKER = os.getenv("IS_DOCKER") == "true"
IS_CI = bool(os.getenv("CI"))
# .venv_test is the test-runner venv (requirements.txt + requirements-dev.txt).
# .venv is the runtime-only venv created by setup_project.py — kept separate so
# running tests never alters the launch environment and vice versa.
_VENV = ROOT / ".venv_test"
_TMP_DIR = ROOT / "tmp"
_REQUIREMENTS = ROOT / "requirements.txt"
_REQUIREMENTS_DEV = ROOT / "requirements-dev.txt"


# ---------------------------------------------------------------------------
# Venv bootstrap — ensure isolated Python environment (skipped in CI/Docker)
# ---------------------------------------------------------------------------

# Legacy venv directory names predating the .venv / .venv_test convention.
_STALE_VENV_NAMES: tuple[str, ...] = ("venv", "venv_test", "env", "ENV", ".venv_backup")


def _remove_stale_venvs() -> None:
    """Delete obsolete virtual-environment directories from the project root.

    Canonical dirs (``.venv`` runtime, ``.venv_test`` tests) are never touched.
    Legacy aliases (for example ``.venv_wsl``) are also preserved.
    Everything in :data:`_STALE_VENV_NAMES` is removed so that users who pull
    fresh code start from a known-clean state.
    """
    for name in _STALE_VENV_NAMES:
        stale = ROOT / name
        if stale.is_dir():
            print(f"[cleanup] Removing stale virtual environment: {stale}")
            shutil.rmtree(stale, ignore_errors=True)


def _inside_venv() -> bool:
    """Return True if the current interpreter lives inside _VENV."""
    try:
        return Path(sys.executable).resolve().is_relative_to(_VENV.resolve())
    except AttributeError:
        return str(sys.executable).startswith(str(_VENV))


def _relaunch_under_venv() -> None:
    """Create .venv_test if needed, then re-exec this script inside it."""
    _remove_stale_venvs()
    if not _VENV.exists():
        print(f"[bootstrap] Creating venv: {_VENV}")
        subprocess.check_call([sys.executable, "-m", "venv", str(_VENV)])
    venv_py_rel = Path("Scripts" if IS_WINDOWS else "bin") / ("python.exe" if IS_WINDOWS else "python")
    venv_py = str(_VENV / venv_py_rel)
    print(f"[bootstrap] Re-launching under venv Python: {venv_py}")
    # subprocess.run() + sys.exit() instead of os.execv():
    # On Windows, os.execv is implemented as P_OVERLAY (CreateProcess + ExitProcess),
    # which creates a new grandchild process and immediately exits the current one.
    # The grandchild INHERITS stdout/stderr pipe write-handles, so any parent using
    # Popen(stdout=PIPE) and communicate() blocks forever on stdout_thread.join()
    # because the grandchild keeps the handles open.
    # subprocess.run() keeps the current process alive until the child finishes,
    # ensuring pipe handles close in the correct order on all platforms.
    result = subprocess.run(
        [venv_py, str(Path(__file__).resolve()), *sys.argv[1:]],
        check=False,
        env={**os.environ, "_IJT_RELAUNCHED": "1"},
        cwd=str(ROOT),
    )
    sys.exit(result.returncode)


# ---------------------------------------------------------------------------
# Colour helpers — ANSI on Linux/macOS/Win10+, plain text fallback
# ---------------------------------------------------------------------------
def _enable_ansi_windows() -> bool:
    """Enable virtual terminal processing on Windows 10+."""
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
            return True
        return False
    except AttributeError, OSError:
        return False


_USE_COLOUR = sys.stdout.isatty() and (not IS_WINDOWS or _enable_ansi_windows())


class _C:
    RESET = "\033[0m" if _USE_COLOUR else ""
    BOLD = "\033[1m" if _USE_COLOUR else ""
    DIM = "\033[2m" if _USE_COLOUR else ""
    GREEN = "\033[92m" if _USE_COLOUR else ""
    RED = "\033[91m" if _USE_COLOUR else ""
    YELLOW = "\033[93m" if _USE_COLOUR else ""
    CYAN = "\033[96m" if _USE_COLOUR else ""


def _ok(msg: str) -> None:
    print(f"{_C.GREEN}  [PASS]{_C.RESET} {msg}")


def _fail(msg: str) -> None:
    print(f"{_C.RED}  [FAIL]{_C.RESET} {msg}", file=sys.stderr)


def _info(msg: str) -> None:
    print(f"{_C.CYAN}  [INFO]{_C.RESET} {msg}")


def _warn(msg: str) -> None:
    print(f"{_C.YELLOW}  [WARN]{_C.RESET} {msg}")


def _skip(msg: str) -> None:
    print(f"{_C.DIM}  [SKIP]{_C.RESET} {msg}")


def _banner(title: str) -> None:
    line = "=" * 65
    print(f"\n{_C.BOLD}{_C.CYAN}{line}{_C.RESET}")
    print(f"{_C.BOLD}{_C.CYAN}  {title}{_C.RESET}")
    print(f"{_C.BOLD}{_C.CYAN}{line}{_C.RESET}")


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------
def _run(
    cmd: list,
    *,
    cwd: Path = ROOT,
    label: str = "",
    env: dict | None = None,
    timeout: int | None = None,
) -> int:
    display = label or " ".join(str(c) for c in cmd[:5])
    print(f"\n{_C.DIM}CMD: {display}{_C.RESET}")
    try:
        result = subprocess.run(
            [str(c) for c in cmd],
            cwd=str(cwd),
            env=env or os.environ.copy(),
            timeout=timeout,
            check=False,
            stdin=subprocess.DEVNULL,  # prevent interactive prompts (e.g. npx install)
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"{_C.YELLOW}[TIMEOUT] {display} exceeded {timeout}s{_C.RESET}")
        return -1


def _run_to_file(
    cmd: list,
    output_file: Path,
    *,
    cwd: Path = ROOT,
    label: str = "",
    env: dict | None = None,
) -> int:
    """Run *cmd*, capture stdout to *output_file*, return exit code."""
    display = label or " ".join(str(c) for c in cmd[:5])
    print(f"\n{_C.DIM}CMD: {display} → {output_file.name}{_C.RESET}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as fh:
        result = subprocess.run(
            [str(c) for c in cmd],
            cwd=str(cwd),
            env=env or os.environ.copy(),
            stdout=fh,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    return result.returncode


def _py_module_available(mod: str) -> bool:
    """Return True if *mod* can be imported in the current interpreter."""
    return (
        subprocess.run(
            [sys.executable, "-c", f"import {mod}"],
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _cmd_available(cmd: str) -> bool:
    """Return True if *cmd* is found on PATH."""
    return shutil.which(cmd) is not None


def _requirements_hash() -> str:
    """Return a short hash of all requirements files combined."""
    import hashlib

    h = hashlib.sha256()
    for req in (_REQUIREMENTS, _REQUIREMENTS_DEV):
        if req.exists():
            h.update(req.read_bytes())
    return h.hexdigest()[:16]


def _ensure_precommit_hooks() -> None:
    """Install pre-commit hooks into .git/hooks/ if not already present."""
    git_root = ROOT
    # Walk up to find .git directory (project may be nested in a monorepo)
    for parent in [ROOT] + list(ROOT.parents):
        if (parent / ".git").exists():
            git_root = parent
            break
    hook_path = git_root / ".git" / "hooks" / "pre-commit"
    if hook_path.exists():
        return  # already installed
    if not _py_module_available("pre_commit"):
        return  # pre-commit not installed — skip silently
    print("[bootstrap] Installing pre-commit hooks …")
    subprocess.check_call(
        [sys.executable, "-m", "pre_commit", "install", "--install-hooks"],
        cwd=str(git_root),
    )


def _prepare_tmp_dir() -> None:
    """Reset runner-managed tmp workspace and recreate tmp/pytest/."""
    _TMP_DIR.mkdir(parents=True, exist_ok=True)
    for child in _TMP_DIR.iterdir():
        name = child.name
        managed = name in {"pytest", "pylint", "pip-audit-cache"} or name.startswith("server_instance_")
        if not managed:
            continue
        with contextlib.suppress(OSError):
            if child.is_dir():
                _force_rmtree(child)
            else:
                child.unlink(missing_ok=True)
    pytest_tmp = _TMP_DIR / "pytest"
    pytest_tmp.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Server / port helpers
# ---------------------------------------------------------------------------
def _port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_opcua_host_port(endpoint: str) -> tuple[str, int]:
    """Parse 'opc.tcp://host:port' → (host, port).

    The 'opc.tcp//' variant (missing colon) is a common copy-paste typo seen
    in config files and environment variables, so both forms are stripped.
    """
    clean = endpoint.replace("opc.tcp://", "").replace("opc.tcp//", "")
    if ":" in clean:
        host, port_str = clean.rsplit(":", 1)
        return host, int(port_str)
    return clean, 4840


def _parse_ws_host_port(url: str) -> tuple[str, int]:
    """Parse 'ws://host:port[/path]' or 'wss://host:port[/path]' → (host, port)."""
    clean = url.replace("wss://", "").replace("ws://", "").split("/")[0]
    if ":" in clean:
        host, port_str = clean.rsplit(":", 1)
        return host, int(port_str)
    return clean, 80  # ws default port when none specified


# ---------------------------------------------------------------------------
# Stage result
# ---------------------------------------------------------------------------
@dataclass
class StageResult:
    name: str
    rc: int
    skipped: bool = False
    duration: float = 0.0
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------


def _stage_versions() -> StageResult:
    """Print tool versions for debugging."""
    _banner("STAGE 0  Tool versions")
    t0 = time.monotonic()
    _info(f"Python   : {sys.version}")
    _info(f"Platform : {platform.platform()}")
    _info(f"Docker   : {IS_DOCKER}  CI: {IS_CI}")
    npm = shutil.which("npm")
    node = shutil.which("node") or shutil.which("node.exe")
    if node:
        _run([node, "--version"], label="node --version")
    if npm:
        _run([npm, "--version"], label="npm --version")
    else:
        _warn("npm not found in PATH")
    return StageResult("versions", 0, duration=time.monotonic() - t0)


def _stage_pip_install(python: Path) -> StageResult:
    _banner("STAGE 1  Install / verify Python test dependencies")
    t0 = time.monotonic()
    if os.getenv("SKIP_VENV_INSTALL") == "1":
        _info("SKIP_VENV_INSTALL=1 — skipping pip install")
        _ensure_precommit_hooks()
        return StageResult("pip-install", 0, duration=time.monotonic() - t0, notes=["skipped via SKIP_VENV_INSTALL"])
    hash_file = _VENV / ".req-hash"
    current_hash = _requirements_hash()
    if hash_file.exists() and hash_file.read_text().strip() == current_hash:
        _info("Requirements unchanged — skipping pip install")
        _ensure_precommit_hooks()
        return StageResult("pip-install", 0, duration=time.monotonic() - t0, notes=["requirements unchanged"])
    # Upgrade pip first to ensure latest version (avoids stale CVE warnings)
    _run([python, "-m", "pip", "install", "--quiet", "--upgrade", "pip"], label="pip self-upgrade")
    overall_rc = 0
    for req in (_REQUIREMENTS, _REQUIREMENTS_DEV):
        if req.exists():
            rc = _run(
                [python, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "--pre", "-r", str(req)],
                label=f"pip install {req.name}",
            )
            if rc != 0:
                overall_rc = rc
    if overall_rc == 0:
        hash_file.write_text(current_hash)
    _ensure_precommit_hooks()
    return StageResult("pip-install", overall_rc, duration=time.monotonic() - t0)


def _stage_python_lint(python: Path) -> StageResult:
    _banner("STAGE 1b  Python static analysis")
    t0 = time.monotonic()
    results_dir = ROOT / "test-results"
    overall_rc = 0
    notes: list[str] = []

    ruff = shutil.which("ruff") or shutil.which("ruff.exe")
    if ruff:
        results_dir.mkdir(parents=True, exist_ok=True)
        rc = _run(
            [ruff, "check", ".", "--output-format=json", "--output-file", str(results_dir / "ruff.json")],
            label="ruff check",
        )
        if rc not in (0, 1):  # 0 = clean, 1 = lint findings
            overall_rc = rc
        rc_fmt = _run([ruff, "format", "--check", "."], label="ruff format --check")
        if rc_fmt != 0:
            overall_rc = rc_fmt
    else:
        _skip("ruff not found — pip install ruff")
        notes.append("ruff not installed")

    if _py_module_available("mypy"):
        rc = _run(
            [python, "-m", "mypy", "src/", "--ignore-missing-imports"],
            label="mypy",
        )
        if rc != 0:
            overall_rc = rc
    else:
        _skip("mypy not installed — pip install mypy")
        notes.append("mypy not installed")

    if _py_module_available("bandit"):
        results_dir.mkdir(parents=True, exist_ok=True)
        rc = _run(
            [
                python,
                "-m",
                "bandit",
                "-r",
                ".",
                "-c",
                "pyproject.toml",
                "-f",
                "json",
                "-o",
                str(results_dir / "bandit.json"),
            ],
            label="bandit",
        )
        if rc not in (0, 1):  # 1 = findings (informational), 2+ = error
            overall_rc = rc
    else:
        _skip("bandit not installed — pip install bandit")
        notes.append("bandit not installed")

    if _py_module_available("pip_audit"):
        results_dir.mkdir(parents=True, exist_ok=True)
        rc = _run(
            [python, "-m", "pip_audit", "--format", "json", "-o", str(results_dir / "pip-audit.json")],
            label="pip-audit",
        )
        if rc not in (0, 1):  # 1 = vulnerabilities found (informational)
            overall_rc = rc
    else:
        _skip("pip-audit not installed — pip install pip-audit")
        notes.append("pip-audit not installed")

    if _py_module_available("vulture"):
        rc = _run(
            [
                python,
                "-m",
                "vulture",
                ".",
                "--min-confidence",
                "80",
                "--exclude",
                ".venv,.venv_test,.venv_wsl,tests",
            ],
            label="vulture",
        )
        if rc not in (0, 1):  # 1 = dead code found (informational)
            overall_rc = rc
    else:
        _skip("vulture not installed — pip install vulture")
        notes.append("vulture not installed")

    if _py_module_available("pylint"):
        results_dir.mkdir(parents=True, exist_ok=True)
        rc = _run(
            [
                python,
                "-m",
                "pylint",
                "src/",
                "--output-format=json",
                f"--output={results_dir / 'pylint.json'}",
            ],
            label="pylint",
        )
        # Match Console policy: keep convention/refactor/warning findings
        # advisory and fail only for fatal/error/usage classes.
        if (rc & (1 | 2 | 32)) != 0:
            overall_rc = rc
        elif rc != 0:
            notes.append(f"pylint advisory findings (exit {rc})")
    else:
        _skip("pylint not installed — pip install pylint")
        notes.append("pylint not installed")

    if _py_module_available("interrogate"):
        rc = _run(
            [python, "-m", "interrogate", "-v"],
            label="interrogate",
        )
        if rc != 0:
            _warn("interrogate below configured threshold (advisory)")
            notes.append("interrogate below threshold (advisory)")
    else:
        _skip("interrogate not installed — pip install interrogate")
        notes.append("interrogate not installed")

    if _cmd_available("detect-secrets"):
        rc = _run(["detect-secrets", "scan"], label="detect-secrets scan")
        if rc != 0:
            overall_rc = rc
    else:
        _skip("detect-secrets not installed — pip install detect-secrets")
        notes.append("detect-secrets not installed")

    # Semgrep AI code review
    if _cmd_available("semgrep"):
        results_dir.mkdir(parents=True, exist_ok=True)
        rc = _run(
            [
                "semgrep",
                "--config=p/default",
                "--json",
                "--output",
                str(results_dir / "semgrep.json"),
                "--exclude=.venv,.venv_test",
                "--exclude=test-results",
                ".",
            ],
            label="semgrep",
            timeout=120,
        )
        if rc == -1:
            _skip("semgrep timed out (>120s) — skipped")
            notes.append("semgrep timed out")
        else:
            try:
                data = json.loads((results_dir / "semgrep.json").read_text(encoding="utf-8"))
                findings = data.get("results", [])
                errors = [f for f in findings if f.get("extra", {}).get("severity") == "ERROR"]
                warns = [f for f in findings if f.get("extra", {}).get("severity") == "WARNING"]
                if errors:
                    _fail(f"semgrep: {len(errors)} error(s), {len(warns)} warning(s)")
                    overall_rc = 1
                elif warns:
                    _warn(f"semgrep: 0 errors, {len(warns)} warning(s)")
                else:
                    _ok(f"semgrep: {len(findings)} finding(s), none critical")
            except Exception:
                _warn("semgrep: could not parse output")
    else:
        _skip("semgrep not installed — pip install semgrep")
        notes.append("semgrep not installed")

    # pyright AI type inference
    if _cmd_available("pyright") or _py_module_available("pyright"):
        results_dir.mkdir(parents=True, exist_ok=True)
        cmd_py = (
            ["pyright", "--outputjson", "--pythonpath", sys.executable]
            if _cmd_available("pyright")
            else [sys.executable, "-m", "pyright", "--outputjson", "--pythonpath", sys.executable]
        )
        proc = subprocess.run(cmd_py, check=False, capture_output=True, text=True, cwd=str(ROOT))
        (results_dir / "pyright.json").write_text(proc.stdout or "{}", encoding="utf-8")
        try:
            data = json.loads(proc.stdout or "{}")
            summary = data.get("summary", {})
            py_errors = summary.get("errorCount", 0)
            py_warns = summary.get("warningCount", 0)
            if py_errors:
                _fail(f"pyright: {py_errors} error(s), {py_warns} warning(s)")
                overall_rc = 1
            elif py_warns:
                _warn(f"pyright: 0 errors, {py_warns} warning(s)")
            else:
                _ok("pyright: 0 errors, 0 warnings")
        except Exception:
            _warn("pyright: could not parse output")
    else:
        _skip("pyright not installed — pip install pyright")
        notes.append("pyright not installed")

    return StageResult("python-lint", overall_rc, duration=time.monotonic() - t0, notes=notes)


def _stage_python_unit(python: Path) -> StageResult:
    _banner("STAGE 2  Python unit tests (no server needed)")
    t0 = time.monotonic()
    results_dir = ROOT / "test-results"
    cmd: list = [
        python,
        "-m",
        "pytest",
        "tests/",
        "-m",
        "not integration and not live and not live_ws",
        "-v",
        "--tb=short",
        "--no-header",
    ]
    if _py_module_available("pytest_cov"):
        results_dir.mkdir(parents=True, exist_ok=True)
        cmd += [
            "--cov=.",
            f"--cov-report=xml:{results_dir / 'coverage-py.xml'}",
            f"--cov-report=html:{results_dir / 'htmlcov-py'}",
            # fail_under threshold is in [tool.coverage.report] in pyproject.toml
        ]
    else:
        _skip("pytest-cov not installed — coverage skipped (pip install pytest-cov)")
    rc = _run(cmd, label="pytest unit")
    return StageResult("python-unit", rc, duration=time.monotonic() - t0)


def _stage_js_lint() -> StageResult:
    _banner("STAGE 2b  JavaScript static analysis")
    t0 = time.monotonic()
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        _skip("npx not found — skipping JS lint")
        return StageResult("js-lint", 0, skipped=True)
    if not (ROOT / "node_modules").exists():
        _skip("node_modules not found — run npm install first")
        return StageResult("js-lint", 0, skipped=True, notes=["run npm install"])

    results_dir = ROOT / "test-results"
    overall_rc = 0
    notes: list[str] = []

    if (ROOT / "node_modules" / "eslint").exists():
        results_dir.mkdir(parents=True, exist_ok=True)
        rc = _run(
            [
                npx,
                "eslint",
                "src/",
                "--format",
                "json",
                "--output-file",
                str(results_dir / "eslint.json"),
                "--config",
                "eslint.config.mjs",
            ],
            label="eslint src/",
        )
        if rc not in (0, 1):  # 0 = clean, 1 = lint findings
            overall_rc = rc
    else:
        _skip("eslint not in node_modules — npm install")
        notes.append("eslint not installed")

    if (ROOT / "node_modules" / "prettier").exists():
        rc = _run([npx, "prettier", "--check", "src/"], label="prettier --check src/")
        if rc != 0:
            overall_rc = rc
    else:
        _skip("prettier not in node_modules — npm install prettier")
        notes.append("prettier not installed")

    if npm:
        results_dir.mkdir(parents=True, exist_ok=True)
        rc = _run_to_file(
            [npm, "audit", "--audit-level=high", "--json"],
            results_dir / "npm-audit.json",
            label="npm audit",
        )
        if rc not in (0, 1):  # 1 = vulnerabilities found (informational)
            overall_rc = rc

    if (ROOT / "node_modules" / "depcheck").exists() or _cmd_available("depcheck"):
        results_dir.mkdir(parents=True, exist_ok=True)
        rc = _run_to_file(
            [npx, "depcheck", "--json"],
            results_dir / "depcheck.json",
            label="depcheck",
        )
        if rc not in (0, 1):  # 1 = unused deps found (informational)
            overall_rc = rc
    else:
        _skip("depcheck not installed — npm install -g depcheck")
        notes.append("depcheck not installed")

    if (ROOT / "node_modules" / "license-checker").exists() or _cmd_available("license-checker"):
        results_dir.mkdir(parents=True, exist_ok=True)
        rc = _run_to_file(
            [npx, "license-checker", "--json"],
            results_dir / "licenses.json",
            label="license-checker",
        )
        if rc != 0:
            overall_rc = rc
    else:
        _skip("license-checker not installed — npm install -g license-checker")
        notes.append("license-checker not installed")

    return StageResult("js-lint", overall_rc, duration=time.monotonic() - t0, notes=notes)


def _stage_js_unit() -> StageResult:
    _banner("STAGE 3  JavaScript unit tests (vitest)")
    t0 = time.monotonic()
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        _warn("npm not found — skipping JS unit tests")
        return StageResult("js-unit", 0, skipped=True)

    if not (ROOT / "node_modules").exists():
        _info("node_modules not found — running npm install")
        rc = _run([npm, "install", "--legacy-peer-deps"], label="npm install")
        if rc != 0:
            return StageResult("js-unit", rc, duration=time.monotonic() - t0, notes=["npm install failed"])

    npx = shutil.which("npx") or shutil.which("npx.cmd")
    results_dir = ROOT / "test-results"
    has_coverage = (ROOT / "node_modules" / "@vitest" / "coverage-v8").exists() or (
        ROOT / "node_modules" / "@vitest" / "coverage-istanbul"
    ).exists()

    if npx and has_coverage:
        results_dir.mkdir(parents=True, exist_ok=True)
        vitest_xml = str(results_dir / "vitest.xml").replace("\\", "/")
        rc = _run(
            [
                npx,
                "vitest",
                "run",
                "--reporter=verbose",
                "--reporter=junit",
                f"--outputFile.junit={vitest_xml}",
                "--coverage",
                "--coverage.reporter=lcov",
                "--coverage.reporter=json",
            ],
            label="vitest --coverage",
        )
    else:
        if npx and not has_coverage:
            _skip("@vitest/coverage-v8 not installed — coverage skipped (npm install --save-dev @vitest/coverage-v8)")
        rc = _run([npm, "run", "test:unit:js"], label="vitest")
    return StageResult("js-unit", rc, duration=time.monotonic() - t0)


def _stage_python_live(python: Path) -> StageResult:
    _banner("STAGE 4  Python live tests (OPC UA + WebSocket backend)")
    t0 = time.monotonic()
    rc = _run(
        [
            python,
            "-m",
            "pytest",
            "tests/python/live/",
            "-v",
            "--tb=short",
            "--no-header",
            "--timeout=120",
        ],
        label="pytest live",
    )
    return StageResult("python-live", rc, duration=time.monotonic() - t0)


def _stage_playwright_install() -> StageResult:
    _banner("STAGE 5  Install Playwright browsers")
    t0 = time.monotonic()
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        _warn("npx not found — skipping Playwright stages")
        return StageResult("playwright-install", 0, skipped=True)

    env = os.environ.copy()

    # Try with --with-deps first (Linux CI); fall back without it (Windows, no admin)
    rc = _run(
        [npx, "playwright", "install", "chromium", "--with-deps"],
        label="playwright install chromium --with-deps",
        env=env,
    )
    if rc != 0:
        _warn("--with-deps failed, retrying without it")
        rc = _run(
            [npx, "playwright", "install", "chromium"],
            label="playwright install chromium",
            env=env,
        )
    if rc != 0:
        # Network or environment issue — skip Playwright smoke tests without blocking others.
        # To resolve: configure system/npm proxy settings or a trusted CA bundle, then run:
        #   npx playwright install chromium
        _warn("Playwright browser install failed (network issue) — smoke tests will be skipped")
        result = StageResult("playwright-install", 0, skipped=True)
        result.notes.append(
            "Browser download failed — configure proxy/CA certs and run 'npx playwright install chromium' manually"
        )
        return result
    return StageResult("playwright-install", rc, duration=time.monotonic() - t0)


def _stage_playwright_smoke() -> StageResult:
    _banner("STAGE 6  Playwright smoke tests (static HTML, no server needed)")
    t0 = time.monotonic()
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        return StageResult("playwright-smoke", 0, skipped=True)
    rc = _run(
        [npx, "playwright", "test", "--project=smoke", "--reporter=line"],
        label="playwright smoke",
    )
    return StageResult("playwright-smoke", rc, duration=time.monotonic() - t0)


def _stage_playwright_e2e(ws_url: str, ui_url: str) -> StageResult:
    _banner("STAGE 7  Playwright E2E — features + regression")
    t0 = time.monotonic()
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        return StageResult("playwright-e2e", 0, skipped=True)

    results_dir = ROOT / "test-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["WS_TEST_URL"] = ws_url
    env["PLAYWRIGHT_TEST_BASE_URL"] = ui_url

    env1 = {**env, "PLAYWRIGHT_JUNIT_OUTPUT_FILE": str(results_dir / "playwright-features.xml")}
    rc1 = _run(
        [npx, "playwright", "test", "--project=features", "--reporter=line", "--reporter=junit"],
        env=env1,
        label="playwright features",
    )
    env2 = {**env, "PLAYWRIGHT_JUNIT_OUTPUT_FILE": str(results_dir / "playwright-regression.xml")}
    rc2 = _run(
        [npx, "playwright", "test", "--project=regression", "--reporter=line", "--reporter=junit"],
        env=env2,
        label="playwright regression",
    )
    return StageResult("playwright-e2e", max(rc1, rc2), duration=time.monotonic() - t0)


def _stage_infra_lint() -> StageResult:
    _banner("STAGE Infra  Dockerfile / YAML / Compose linting")
    t0 = time.monotonic()
    results_dir = ROOT / "test-results"
    overall_rc = 0
    notes: list[str] = []

    hadolint = shutil.which("hadolint") or shutil.which("hadolint.exe")
    dockerfile = ROOT / "Dockerfile"
    if hadolint and dockerfile.exists():
        results_dir.mkdir(parents=True, exist_ok=True)
        rc = _run_to_file(
            [hadolint, "Dockerfile", "--format", "json"],
            results_dir / "hadolint.json",
            label="hadolint Dockerfile",
        )
        if rc != 0:
            overall_rc = rc
    elif not hadolint:
        _skip("hadolint not found — see https://github.com/hadolint/hadolint")
        notes.append("hadolint not installed")
    else:
        _skip("Dockerfile not found — skipping hadolint")

    yamllint = shutil.which("yamllint") or shutil.which("yamllint.exe")
    compose_yml = ROOT / "docker-compose.yml"
    if yamllint and compose_yml.exists():
        rc = _run([yamllint, "docker-compose.yml", "-f", "parsable"], label="yamllint docker-compose.yml")
        if rc != 0:
            overall_rc = rc
    elif not yamllint:
        _skip("yamllint not found — pip install yamllint")
        notes.append("yamllint not installed")

    docker = shutil.which("docker") or shutil.which("docker.exe")
    if docker and compose_yml.exists():
        rc = _run([docker, "compose", "config", "--quiet"], label="docker compose config --quiet")
        if rc != 0:
            overall_rc = rc
    elif not docker:
        _skip("docker not found — skipping compose config validation")

    return StageResult("infra-lint", overall_rc, duration=time.monotonic() - t0, notes=notes)


# ---------------------------------------------------------------------------
# Phase 2 — OPC UA server auto-launch helpers
# ---------------------------------------------------------------------------
_SERVER_COMPOSE_DIR = ROOT.parent.parent.parent / "OPC_UA_Servers" / "Release2"

_WELL_KNOWN_SIMULATOR_PATHS: list[Path] = [
    _SERVER_COMPOSE_DIR / "OPC_UA_IJT_Server_Simulator" / "opcua_ijt_demo_application.exe",
    _SERVER_COMPOSE_DIR / "OPC_UA_IJT_Server_Simulator_Linux" / "opcua_ijt_demo_application",
]
_SERVER_NATIVE_PORT = 40451
_CLIENT_DEFAULT_PORT = 40463
_server_tmp_dir: Path | None = None  # set by _launch_simulator_on_port; cleared in _stop_opcua_server


def _parse_int_env(name: str, default: int) -> int:
    """Parse an integer environment variable, falling back to *default* on bad input.

    Warns on stderr when the value is not a valid integer.  The warning is
    suppressed on venv-relaunched invocations (``_IJT_RELAUNCHED=1``) to avoid
    printing the same message twice when the outer bootstrap process re-execs
    this script under the isolated venv.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        # Suppress the duplicate warning in the inner (venv-relaunched) process.
        if not os.environ.get("_IJT_RELAUNCHED"):
            import warnings

            warnings.warn(
                f"IJT: {name}={raw!r} is not a valid integer — using default {default}s",
                stacklevel=2,
            )
        return default


# Configurable Docker readiness timeout (seconds).  90 s is ample for most
# environments; override with IJT_DOCKER_TIMEOUT=<seconds> for slow CI runners.
_DOCKER_TIMEOUT = _parse_int_env("IJT_DOCKER_TIMEOUT", 90)


def _opcua_server_port() -> int:
    return int(os.getenv("OPCUA_SERVER_PORT", str(_CLIENT_DEFAULT_PORT)))


def _launch_simulator_on_port(port: int, exe: str) -> subprocess.Popen | None:
    """Copy the binary dir to a temp location, patch the port config, and launch.

    Stores the temp dir in the module-global ``_server_tmp_dir`` so
    ``_stop_opcua_server`` can remove it on teardown.
    Returns the Popen handle on success, None on failure (temp dir cleaned on failure).
    """
    global _server_tmp_dir

    exe_path = Path(exe)
    if not exe_path.exists():
        _warn(f"Binary not found: {exe}")
        return None

    src_dir = exe_path.parent
    tmp_dir = _TMP_DIR / f"server_instance_{port}"
    _info(f"[server] Launching simulator on port {port} (copied to {tmp_dir})")
    try:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        shutil.copytree(src_dir, tmp_dir)
    except OSError as exc:
        _warn(f"Failed to copy binary dir: {exc}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    cfg_path = tmp_dir / "server_configuration.json"
    if cfg_path.exists():
        try:
            with cfg_path.open(encoding="utf-8") as fh:
                cfg = json.load(fh)
            cfg.setdefault("serverConfigurationData", {})["serverEndpointTCPPort"] = port
            with cfg_path.open("w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2)
        except (OSError, ValueError) as exc:
            _warn(f"Failed to patch server_configuration.json: {exc}")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return None

    try:
        proc = subprocess.Popen(
            [str(tmp_dir / exe_path.name)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(tmp_dir),
        )
    except OSError as exc:
        _warn(f"Failed to launch binary: {exc}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    _info(f"Waiting up to 30s for port {port} ...")
    for _ in range(30):
        if _port_open("localhost", port, timeout=1.0):
            _ok(f"OPC UA server ready on :{port}")
            os.environ["OPCUA_TEST_ENDPOINT"] = f"opc.tcp://localhost:{port}"
            _server_tmp_dir = tmp_dir
            return proc
        time.sleep(1)

    _warn(f"Binary did not open port {port} within 30s")
    proc.terminate()
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return None


def _maybe_start_opcua_server() -> tuple[bool, bool, subprocess.Popen | None]:
    """Start the OPC UA server if the target port is not yet open.

    Returns *(started_by_us, port_open, proc)*.
    *started_by_us* is True when this call launched the server.
    *proc* is the Popen handle if a binary was started (None for Docker).
    """
    # If user explicitly set the endpoint, don't auto-launch
    if os.getenv("OPCUA_TEST_ENDPOINT") or os.getenv("OPCUA_SERVER_URL"):
        port = _opcua_server_port()
        endpoint = os.getenv("OPCUA_TEST_ENDPOINT") or os.getenv("OPCUA_SERVER_URL") or ""
        host, srv_port = _parse_opcua_host_port(endpoint)
        open_ = _port_open(host, srv_port)
        return False, open_, None

    port = _opcua_server_port()
    if _port_open("localhost", port):
        _info(f"OPC UA server already listening on port {port}")
        return False, True, None

    # Check native port as well
    if _port_open("localhost", _SERVER_NATIVE_PORT):
        _info(f"OPC UA server already on native port {_SERVER_NATIVE_PORT}")
        os.environ["OPCUA_TEST_ENDPOINT"] = f"opc.tcp://localhost:{_SERVER_NATIVE_PORT}"
        return False, True, None

    # Try binary launch first
    exe: str | None = os.getenv("OPCUA_SIMULATOR_EXE")
    if not exe:
        for candidate in _WELL_KNOWN_SIMULATOR_PATHS:
            if candidate.exists():
                exe = str(candidate)
                break

    if exe:
        proc = _launch_simulator_on_port(port, exe)
        if proc is not None:
            return True, True, proc

    # Fall back to Docker
    docker = shutil.which("docker") or shutil.which("docker.exe")
    if not docker or not _docker_available():
        _warn("Docker unavailable — cannot auto-launch OPC UA server")
        return False, False, None

    compose_dir = _SERVER_COMPOSE_DIR
    if not compose_dir.exists():
        _warn(f"OPC UA server compose dir not found: {compose_dir}")
        return False, False, None

    _info(f"Launching OPC UA Docker server from {compose_dir}")
    rc = _run([docker, "compose", "up", "-d"], cwd=compose_dir, label="docker compose up -d  (OPC UA server)")
    if rc != 0:
        _warn("docker compose up failed for OPC UA server")
        return True, False, None

    _info(f"Waiting up to 60s for OPC UA port {port} ...")
    for _ in range(30):
        if _port_open("localhost", port, timeout=1.0):
            _ok(f"OPC UA server ready on :{port}")
            return True, True, None
        time.sleep(2)

    _warn(f"OPC UA server not ready after 60s (port {port})")
    return True, False, None


def _stop_opcua_server(proc: subprocess.Popen | None = None) -> None:
    global _server_tmp_dir
    if proc is not None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        os.environ.pop("OPCUA_TEST_ENDPOINT", None)
        shutil.rmtree(_server_tmp_dir, ignore_errors=True) if _server_tmp_dir else None
        _server_tmp_dir = None
        return
    docker = shutil.which("docker") or shutil.which("docker.exe")
    if docker and _SERVER_COMPOSE_DIR.exists():
        _run([docker, "compose", "down"], cwd=_SERVER_COMPOSE_DIR, label="docker compose down  (OPC UA server)")


def _stage_python_integration(
    python: Path,
    *,
    prestarted: tuple[bool, bool, subprocess.Popen | None] | None = None,
) -> StageResult:
    """Phase 2 — run integration tests against a live OPC UA server.

    Auto-launches the Docker server if the port is not yet open and Docker
    is available.  Always tears down any container it started.

    If *prestarted* is provided (a tuple from ``_maybe_start_opcua_server``),
    this function uses it instead of calling ``_maybe_start_opcua_server`` again —
    the caller owns the server lifecycle and is responsible for teardown.
    """
    _banner("STAGE 4b  Python integration tests (Phase 2 — live OPC UA)")
    t0 = time.monotonic()
    results_dir = ROOT / "test-results"
    results_dir.mkdir(parents=True, exist_ok=True)

    if prestarted is not None:
        # Server lifecycle is owned by caller — do NOT stop on exit
        started, port_open, server_proc = False, prestarted[1], prestarted[2]
    else:
        started, port_open, server_proc = _maybe_start_opcua_server()
    try:
        if not port_open:
            _skip("OPC UA server unreachable — skipping integration tests")
            return StageResult("python-integration", 0, skipped=True, notes=["OPC UA server not available"])
        rc = _run(
            [
                python,
                "-m",
                "pytest",
                "tests/python/integration/",
                "-v",
                "--tb=short",
                "--no-header",
                f"--junitxml={results_dir / 'pytest-integration.xml'}",
            ],
            label="pytest integration",
        )
        return StageResult("python-integration", rc, duration=time.monotonic() - t0)
    finally:
        if started:
            _stop_opcua_server(server_proc)


# ---------------------------------------------------------------------------
# Docker helpers
# ---------------------------------------------------------------------------
def _docker_available() -> bool:
    """Return True if the Docker daemon is reachable via the active context."""
    docker = shutil.which("docker") or shutil.which("docker.exe")
    if not docker:
        return False
    try:
        r = subprocess.run(
            [docker, "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=20,
        )
        return r.returncode == 0
    except Exception:
        return False


def _docker_skip_reason() -> str:
    """Return an actionable message explaining why Docker is unavailable."""
    docker = shutil.which("docker") or shutil.which("docker.exe")
    if not docker:
        return "docker not in PATH — install Docker Desktop (Windows/Mac) or 'sudo apt install docker.io' (Linux)"
    # docker binary exists but daemon not responding
    if sys.platform == "win32":
        return (
            "Docker daemon not running — start Docker Desktop, wait for the whale icon in the system tray, then re-run"
        )
    if sys.platform == "darwin":
        return "Docker daemon not running — start Docker Desktop for Mac or run: open -a Docker"
    return "Docker daemon not running — run: sudo systemctl start docker  (or: sudo service docker start)"


def _stage_docker_smoke() -> StageResult:
    """Build image with BuildKit layer caching, start compose, verify readiness, tear down."""
    _banner("STAGE 8  Docker smoke (build + compose up + readiness + down)")
    t0 = time.monotonic()
    # Pytest on Windows can leave transient "pytest-cache-files-*" directories
    # that intermittently block Docker build context packing.
    _cleanup_caches(ROOT)
    docker = shutil.which("docker") or shutil.which("docker.exe")
    if not docker:
        return StageResult("docker-smoke", 0, skipped=True, notes=["docker not in PATH"])
    compose_cmd = [docker, "compose"]

    # DOCKER_BUILDKIT=1 enables layer caching — repeated local builds take seconds, not minutes.
    build_env = {**os.environ, "DOCKER_BUILDKIT": "1", "BUILDKIT_INLINE_CACHE": "1"}
    build_cmd = [
        docker,
        "build",
        "--cache-from",
        "ijt_web_client:latest",
        "-t",
        "ijt_web_client",
        ".",
    ]
    rc = _run(build_cmd, label="docker build (BuildKit)", env=build_env)
    if rc != 0:
        return StageResult("docker-smoke", rc, duration=time.monotonic() - t0, notes=["docker build failed"])

    rc = _run(compose_cmd + ["up", "-d"], label="docker compose up -d")
    if rc != 0:
        return StageResult("docker-smoke", rc, duration=time.monotonic() - t0, notes=["docker compose up failed"])

    # Wait up to _DOCKER_TIMEOUT seconds for HTTP readiness (1 poll per second).
    _info(f"Waiting up to {_DOCKER_TIMEOUT} s for http://127.0.0.1:3000 ...")
    ready = False
    for _ in range(_DOCKER_TIMEOUT):
        if _port_open("127.0.0.1", 3000, timeout=1.0):
            ready = True
            break
        time.sleep(1)

    ws_ready = _port_open("127.0.0.1", 8001, timeout=2.0)

    _run(compose_cmd + ["logs", "--tail=20"], label="docker compose logs")
    _run(compose_cmd + ["down", "-v"], label="docker compose down -v")

    if not ready:
        return StageResult(
            "docker-smoke",
            1,
            duration=time.monotonic() - t0,
            notes=[f"HTTP :3000 not ready within {_DOCKER_TIMEOUT} s (set IJT_DOCKER_TIMEOUT to override)"],
        )

    notes = [] if ws_ready else ["WS :8001 not ready — backend may need OPC UA server"]
    return StageResult("docker-smoke", 0, duration=time.monotonic() - t0, notes=notes)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def _print_summary(results: list[StageResult], total_time: float) -> int:
    _banner("TEST SUMMARY")
    overall = 0
    for r in results:
        if r.skipped:
            tag = f"{_C.YELLOW}[SKIP]{_C.RESET}"
        elif r.rc == 0:
            tag = f"{_C.GREEN}[PASS]{_C.RESET}"
        else:
            tag = f"{_C.RED}[FAIL]{_C.RESET}"
            overall = max(overall, r.rc)
        dur = f"  {r.duration:.1f}s" if r.duration else ""
        print(f"  {tag}  {r.name:<35} exit={r.rc}{dur}")
        for note in r.notes:
            print(f"         {_C.DIM}^ {note}{_C.RESET}")

    print(f"\n  Total time: {total_time:.1f}s")
    if overall == 0:
        print(f"\n{_C.GREEN}{_C.BOLD}  ALL TESTS PASSED{_C.RESET}")
    else:
        print(f"\n{_C.RED}{_C.BOLD}  SOME TESTS FAILED — review output above{_C.RESET}")
    print("=" * 65 + "\n")
    return overall


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
STAGES = [
    "versions",
    "pip-install",
    "python-lint",
    "python-unit",
    "js-lint",
    "js-unit",
    "infra-lint",
    "python-live",
    "python-integration",
    "playwright-install",
    "playwright-smoke",
    "playwright-e2e",
    "docker-smoke",
]


def main() -> int:
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    _cleanup_caches(ROOT)  # pre-run: clear stale caches from interrupted runs
    _prepare_tmp_dir()

    parser = argparse.ArgumentParser(
        description="IJT Web Client cross-platform test runner",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--all", action="store_true", help="Run every stage (unit + live + E2E)")
    parser.add_argument("--integration", action="store_true", help="Include live OPC UA + WS backend tests")
    parser.add_argument("--e2e", action="store_true", help="Include Playwright smoke + E2E tests")
    # CI-compatible phase flags (mirrors other project runners)
    parser.add_argument("--phase1", action="store_true", help="Static/unit tests only — no live/E2E stages (CI use)")
    parser.add_argument("--phase2", action="store_true", help="Live/E2E stages only — skip static analysis (CI use)")
    parser.add_argument("--list", action="store_true", help="Print available stages and exit")
    parser.add_argument("--opcua-endpoint", default=os.getenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40451"))
    parser.add_argument("--ws-url", default=os.getenv("WS_TEST_URL", "ws://localhost:8001"))
    parser.add_argument("--ui-url", default=os.getenv("UI_TEST_BASE_URL", "http://127.0.0.1:3000"))
    args = parser.parse_args()

    # Bootstrap: run inside isolated .venv (skipped when already in venv, CI, or Docker)
    if not IS_CI and not IS_DOCKER and not _inside_venv():
        _relaunch_under_venv()
        return 0  # unreachable after sys.exit(); satisfies type checker

    if args.list:
        print("Available stages:")
        for s in STAGES:
            print(f"  {s}")
        return 0

    run_live = args.integration or args.all or args.phase2
    run_e2e = args.e2e or args.all or args.phase2
    skip_static = args.phase2  # --phase2: live/E2E only, skip static analysis

    python = Path(sys.executable)
    t_start = time.monotonic()

    # Check availability upfront — drives auto-detection of optional stages
    opcua_host, opcua_port = _parse_opcua_host_port(args.opcua_endpoint)
    ws_host, ws_port = _parse_ws_host_port(args.ws_url)
    opcua_up = _port_open(opcua_host, opcua_port)
    ws_up = _port_open(ws_host, ws_port)
    docker_up = _docker_available()

    # Auto-detect optional stages when not explicitly requested
    # --phase1: force off all live/docker stages
    if args.phase1:
        run_live = False
        run_e2e = False
        run_docker = False
    else:
        run_live = run_live or opcua_up
        run_e2e = run_e2e or ws_up
        run_docker = args.all or docker_up

    _banner("IJT Web Client — Cross-Platform Test Runner")
    _info(f"Python  : {python}")
    _info(f"Root    : {ROOT}")
    _info(f"OS      : {sys.platform} / {platform.machine()}")
    _info(f"OPC UA  : {'UP' if opcua_up else 'not reachable'} ({args.opcua_endpoint})")
    _info(f"WS      : {'UP' if ws_up else 'not reachable'} ({args.ws_url})")
    _info(f"Docker  : {'available' if docker_up else 'not available'}")

    if (args.integration or args.all) and not opcua_up:
        _warn(f"OPC UA server NOT reachable at {args.opcua_endpoint} — live tests will be skipped")
    if (args.e2e or args.all) and not ws_up:
        _warn(f"WebSocket backend NOT reachable at {args.ws_url} — E2E tests will be skipped")

    results: list[StageResult] = []

    # Wipe previous run's results so the local copy always reflects the latest run only
    shutil.rmtree(ROOT / "test-results", ignore_errors=True)
    (ROOT / "test-results").mkdir(parents=True, exist_ok=True)

    # ── Static / unit stages (skipped when --phase2) ──────────────────────────
    if not skip_static:
        results.append(_stage_versions())
        results.append(_stage_pip_install(python))
        results.append(_stage_python_lint(python))
        results.append(_stage_python_unit(python))
        results.append(_stage_js_lint())
        results.append(_stage_js_unit())
        results.append(_stage_infra_lint())

    # ── Live + Integration tests (Phase 2 — skipped when --phase1) ────────────
    # Auto-launch server ONCE and share it between live and integration stages.
    # This ensures live tests are not skipped just because the server was not
    # running at startup — the same auto-launch logic that integration uses.
    if not args.phase1:
        _srv_started, _srv_port_open, _srv_proc = _maybe_start_opcua_server()
        try:
            if run_live:
                if _srv_port_open:
                    results.append(_stage_python_live(python))
                else:
                    _skip("python-live: OPC UA server not available")
                    results.append(StageResult("python-live", 0, skipped=True, notes=["OPC UA server not available"]))

            if run_live or docker_up or _srv_port_open:
                # Pass prestarted so integration stage re-uses the running server
                results.append(_stage_python_integration(python, prestarted=(_srv_started, _srv_port_open, _srv_proc)))
            else:
                _skip("python-integration: OPC UA server not available and Docker not running")
                results.append(
                    StageResult(
                        "python-integration",
                        0,
                        skipped=True,
                        notes=["start OPC UA server or Docker to enable"],
                    )
                )
        finally:
            if _srv_started:
                _stop_opcua_server(_srv_proc)

    # Hint: multi-version testing via pyenv
    if _cmd_available("pyenv"):
        _info("pyenv detected — multi-version testing available: pyenv local X.Y.Z && python run_all_tests.py")

    # ── Playwright (smoke always runs; E2E auto-detected or explicit) ─────────
    if not args.phase1:
        pw_install = _stage_playwright_install()
        results.append(pw_install)

        if not pw_install.skipped and pw_install.rc == 0:
            # Smoke always runs — catches 404s, JS errors, missing assets
            results.append(_stage_playwright_smoke())

            if run_e2e:
                if ws_up:
                    results.append(_stage_playwright_e2e(args.ws_url, args.ui_url))
                else:
                    _skip("playwright-e2e: WebSocket backend not reachable")
                    results.append(StageResult("playwright-e2e", 0, skipped=True))

    # ── Docker smoke (auto-detected; skipped if Docker unavailable) ───────────
    if not args.phase1 and run_docker:
        results.append(_stage_docker_smoke())
    elif not args.phase1:
        _skip(f"docker-smoke: {_docker_skip_reason()}")
        results.append(StageResult("docker-smoke", 0, skipped=True))

    rc = _print_summary(results, time.monotonic() - t_start)
    _cleanup_caches(ROOT)
    return rc


def _force_rmtree(path: Path) -> None:
    """Remove a directory tree, handling Windows read-only / locked files."""
    import stat as _stat

    def _on_exc(func, fpath, exc):
        try:
            os.chmod(fpath, _stat.S_IWRITE)
            func(fpath)
        except OSError:
            time.sleep(0.05)
            with contextlib.suppress(OSError):
                func(fpath)

    shutil.rmtree(path, onexc=_on_exc)


def _cleanup_caches(root: Path) -> None:
    """Remove cache/bytecode artifacts after run. Reports in test-results/ are preserved."""
    _SKIP = {"node_modules", ".git", "test-results"}  # tmp workspace is handled by _prepare_tmp_dir()
    _CACHE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
    for dirpath, dirs, files in os.walk(root, topdown=True):
        dirs[:] = [d for d in dirs if d not in _SKIP and not d.startswith(".venv") and not d.startswith("venv")]
        for d in list(dirs):
            if d in _CACHE_DIRS or d.startswith("pytest-cache-files-"):
                _force_rmtree(Path(dirpath) / d)
                dirs.remove(d)
        for f in files:
            if f == ".coverage" or f.startswith(".coverage.") or f.endswith(".pyc"):
                with contextlib.suppress(OSError):
                    (Path(dirpath) / f).unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
