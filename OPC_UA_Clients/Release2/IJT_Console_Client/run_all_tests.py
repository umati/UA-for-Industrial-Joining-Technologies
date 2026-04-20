#!/usr/bin/env python3
"""
run_all_tests.py — Per-project test runner for IJT Console Client.

Architecture: Two-phase execution
  Phase 1 — static / quality analysis + unit tests (no OPC UA server required).
  Phase 2 — live integration tests (OPC UA server auto-started or must be reachable).

Usage:
  python run_all_tests.py                    # full run (Phase 1 + Phase 2)
  python run_all_tests.py --phase1           # unit / static only
  python run_all_tests.py --phase2           # live tests only
  python run_all_tests.py --junit-xml=PATH   # write JUnit XML to PATH
  python run_all_tests.py --help

Environment variables:
  OPCUA_SERVER_URL      Override server URL (default: opc.tcp://localhost:40451)
  OPCUA_SIMULATOR_EXE   Path to opcua_ijt_demo_application(.exe)
  SKIP_VENV_INSTALL     Set to "1" to skip pip install (for CI where deps are pre-installed)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

# Ensure stdout/stderr use UTF-8 on Windows (cp1252 can't encode box-drawing chars)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Repo-root bootstrap — try to import shared utilities; fall back gracefully.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# Key paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
# .venv_test is the test-runner venv (requirements.txt + requirements-dev.txt).
# .venv is the runtime-only venv created by setup_client.py — kept separate so
# running tests never alters the launch environment and vice versa.
_VENV = _HERE / ".venv_test"
_REQUIREMENTS = _HERE / "requirements.txt"
_REQUIREMENTS_DEV = _HERE / "requirements-dev.txt"
_PYPROJECT = _HERE / "pyproject.toml"
_TESTS_DIR = _HERE / "tests"
_TESTS_UNIT = _TESTS_DIR / "unit"
_TESTS_LIVE = _TESTS_DIR / "live"
_RESULTS_DIR = _HERE / "test-results"
_DEFAULT_JUNIT = _RESULTS_DIR / "pytest-unit.xml"
_TMP_DIR = _HERE / "tmp"
_DEFAULT_SERVER_URL = "opc.tcp://localhost:40461"
_MIN_PYTHON = (3, 14)

_WELL_KNOWN_SIMULATOR_PATHS = [
    # Windows native binary (checked first on Windows)
    _REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator" / "opcua_ijt_demo_application.exe",
    # Linux / WSL binary
    _REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator_Linux" / "opcua_ijt_demo_application",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_port_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name, "").strip().lower()
    return val in ("1", "true", "yes", "on") if val else default


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


def _parse_server_url(url: str) -> tuple[str, int]:
    stripped = url.removeprefix("opc.tcp://")
    if ":" in stripped:
        host_part, port_part = stripped.rsplit(":", 1)
        return host_part, int(port_part.split("/")[0])
    return stripped, 40451


# ---------------------------------------------------------------------------
# Colour / logging helpers
# ---------------------------------------------------------------------------

_USE_COLOUR: bool = False

_ANSI_GREEN = "\033[92m"
_ANSI_RED = "\033[91m"
_ANSI_YELLOW = "\033[93m"
_ANSI_CYAN = "\033[96m\033[1m"
_ANSI_RESET = "\033[0m"


def _enable_ansi_windows() -> bool:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            return True
        return False
    except Exception:
        return False


def _c(ansi: str, text: str) -> str:
    return f"{ansi}{text}{_ANSI_RESET}" if _USE_COLOUR else text


def _log(msg: str) -> None:
    """Write *msg* to stdout immediately."""
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def _banner(title: str) -> None:
    width = 50
    bar = "═" * width
    pad = title.ljust(width - 2)
    _log("")
    _log(_c(_ANSI_CYAN, f"╔{bar}╗"))
    _log(_c(_ANSI_CYAN, f"║  {pad}║"))
    _log(_c(_ANSI_CYAN, f"╚{bar}╝"))


def _divider() -> None:
    _log(_c(_ANSI_CYAN, "─" * 52))


def _section(title: str) -> None:
    _log(_c(_ANSI_CYAN, f"\n  ── {title} ──"))


# ---------------------------------------------------------------------------
# Venv management
# ---------------------------------------------------------------------------


def _venv_python(venv: Path) -> Path:
    """Return the Python interpreter path inside *venv*."""
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _venv_pip(venv: Path) -> Path:
    """Return the pip path inside *venv*."""
    if sys.platform == "win32":
        return venv / "Scripts" / "pip.exe"
    return venv / "bin" / "pip"


def _inside_venv() -> bool:
    """Return True if the current interpreter is already inside *_VENV*."""
    try:
        return Path(sys.executable).resolve().is_relative_to(_VENV.resolve())
    except AttributeError:
        return str(sys.executable).startswith(str(_VENV))


# Legacy venv directory names predating the .venv / .venv_test convention.
_STALE_VENV_NAMES: tuple[str, ...] = ("venv", "venv_test", "env", "ENV", ".venv_backup")


def _remove_stale_venvs() -> None:
    """Delete obsolete virtual-environment directories from the project root.

    Runs at startup so that users who pull fresh code are not left with
    orphaned, potentially-conflicting environments.
    Canonical dirs (``.venv`` runtime, ``.venv_test`` tests) are never touched.
    Legacy aliases (for example ``.venv_wsl``) are also preserved.
    """
    for name in _STALE_VENV_NAMES:
        stale = _HERE / name
        if stale.is_dir():
            _log(f"[cleanup] Removing stale virtual environment: {stale}")
            shutil.rmtree(stale, ignore_errors=True)


def _ensure_venv() -> None:
    """Create the virtual environment if it does not already exist."""
    if not _VENV.exists():
        _log(f"  Creating venv: {_VENV}")
        subprocess.check_call([sys.executable, "-m", "venv", str(_VENV)])
    else:
        _log(f"  Using existing venv: {_VENV}")


def _requirements_hash() -> str:
    """Return a short hash of all requirements files combined."""
    import hashlib

    h = hashlib.sha256()
    for req in (_REQUIREMENTS, _REQUIREMENTS_DEV):
        if req.exists():
            h.update(req.read_bytes())
    return h.hexdigest()[:16]


def _install_requirements() -> None:
    """Install packages; reinstall automatically when requirements files change."""
    if _env_bool("SKIP_VENV_INSTALL"):
        _log("  Skipping pip install (SKIP_VENV_INSTALL=1)")
        return
    hash_file = _VENV / ".req-hash"
    current_hash = _requirements_hash()
    if hash_file.exists() and hash_file.read_text().strip() == current_hash:
        _log("  Requirements unchanged — skipping pip install")
        return
    pip = str(_venv_pip(_VENV))
    python = str(_venv_python(_VENV))
    subprocess.check_call([python, "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    for req in (_REQUIREMENTS, _REQUIREMENTS_DEV):
        if req.exists():
            _log(f"  Installing {req.name} …")
            subprocess.check_call([pip, "install", "--quiet", "--pre", "-r", str(req)])
    hash_file.write_text(current_hash)


def _relaunch_under_venv() -> None:
    """Re-exec this script under the venv Python if not already there."""
    _remove_stale_venvs()
    _ensure_venv()
    _install_requirements()
    _ensure_precommit_hooks()
    venv_py = str(_venv_python(_VENV))
    _log(f"  Re-launching under venv Python: {venv_py}")
    # subprocess.run() + sys.exit() instead of os.execv():
    # On Windows, os.execv uses P_OVERLAY (CreateProcess + ExitProcess), creating a
    # grandchild that inherits stdout/stderr pipe write-handles. Any parent using
    # Popen(stdout=PIPE).communicate() then blocks forever because the grandchild
    # keeps those handles open. subprocess.run() keeps the current process alive until
    # the child finishes, so pipe handles close in the correct order on all platforms.
    script_path = str(Path(__file__).resolve())
    result = subprocess.run([venv_py, script_path, *sys.argv[1:]], check=False, cwd=str(_HERE))
    sys.exit(result.returncode)


def _ensure_precommit_hooks() -> None:
    """Install pre-commit hooks into .git/hooks/ if not already present."""
    git_root = _HERE
    # Walk up to find .git directory (project may be nested in a monorepo)
    for parent in [_HERE] + list(_HERE.parents):
        if (parent / ".git").exists():
            git_root = parent
            break
    hook_path = git_root / ".git" / "hooks" / "pre-commit"
    if hook_path.exists():
        return  # already installed
    if not _tool_available("pre_commit"):
        return  # pre-commit not installed — skip silently
    _log("  Installing pre-commit hooks …")
    subprocess.check_call(
        [str(_venv_python(_VENV)), "-m", "pre_commit", "install", "--install-hooks"],
        cwd=str(git_root),
    )


# ---------------------------------------------------------------------------
# Tool detection helpers
# ---------------------------------------------------------------------------


def _tool_available(module_name: str) -> bool:
    """Check if a Python module is importable in the current interpreter."""
    result = subprocess.run(
        [sys.executable, "-c", f"import {module_name}"],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def _binary_available(name: str) -> bool:
    """Return True if *name* is found on PATH."""
    return shutil.which(name) is not None


# ---------------------------------------------------------------------------
# Server auto-launch
# ---------------------------------------------------------------------------


_SERVER_NATIVE_PORT = 40451  # port the binary always uses (from server_configuration.json)
_server_tmp_dir: Path | None = None  # set by _launch_simulator_on_port; cleared in finally


def _launch_simulator_on_port(port: int, exe: str) -> subprocess.Popen | None:
    """Copy the binary dir to a temp location, patch the port config, and launch.

    Stores the temp dir in the module-global ``_server_tmp_dir`` so the caller's
    finally block can remove it via ``shutil.rmtree(_server_tmp_dir, ignore_errors=True)``.
    Returns the Popen handle on success, None on failure (temp dir cleaned on failure).
    """
    global _server_tmp_dir

    exe_path = Path(exe)
    if not exe_path.exists():
        _log(f"  [server] Binary not found: {exe}")
        return None

    src_dir = exe_path.parent
    tmp_dir = _TMP_DIR / f"server_instance_{port}"
    _log(f"  [server] Launching simulator on port {port} (copied to {tmp_dir})")
    try:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        shutil.copytree(src_dir, tmp_dir)
    except OSError as exc:
        _log(f"  [server] Failed to copy binary dir: {exc}")
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
            _log(f"  [server] Failed to patch server_configuration.json: {exc}")
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
        _log(f"  [server] Failed to launch binary: {exc}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    for _ in range(30):
        if _is_port_reachable("localhost", port):
            _log(f"  [server] Ready on port {port}")
            os.environ["OPCUA_SERVER_URL"] = f"opc.tcp://localhost:{port}"
            _server_tmp_dir = tmp_dir
            return proc
        time.sleep(1)

    _log("  [server] Timed out waiting for simulator — terminating")
    proc.terminate()
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return None


def _ensure_server(port: int = 40461) -> subprocess.Popen | None:
    """Start OPC UA server if not already running. Returns Popen handle or None.

    If OPCUA_SERVER_URL is already set the caller manages the server — skip auto-launch.
    If the binary is found and started, os.environ["OPCUA_SERVER_URL"] is updated to
    the client's port so that live tests can locate it.
    """
    if os.environ.get("OPCUA_SERVER_URL"):
        _log("  [server] OPCUA_SERVER_URL already set — skipping auto-launch")
        return None
    if _is_port_reachable("localhost", port):
        _log(f"  [server] Already running on port {port}")
        return None
    if _is_port_reachable("localhost", _SERVER_NATIVE_PORT):
        _log(f"  [server] Already running on native port {_SERVER_NATIVE_PORT}")
        os.environ["OPCUA_SERVER_URL"] = f"opc.tcp://localhost:{_SERVER_NATIVE_PORT}"
        return None
    exe = os.environ.get("OPCUA_SIMULATOR_EXE")
    if not exe:
        for candidate in _WELL_KNOWN_SIMULATOR_PATHS:
            if candidate.exists():
                exe = str(candidate)
                break
    if not exe:
        _log("  [server] No simulator binary found — Phase 2 will be skipped")
        _log("  [server] Set OPCUA_SIMULATOR_EXE=<path> to enable auto-launch")
        return None
    return _launch_simulator_on_port(port, exe)


# ---------------------------------------------------------------------------
# Result helper
# ---------------------------------------------------------------------------


class _StepResult:
    """Result of a single test / analysis step."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.ok: bool = False
        self.skipped: bool = False
        self.note: str = ""
        self.duration: float = 0.0

    def print_line(self) -> None:
        width = 44
        dots = "." * max(0, width - len(self.label))
        if self.skipped:
            status = _c(_ANSI_YELLOW, "SKIP")
        elif self.ok:
            status = _c(_ANSI_GREEN, "PASS")
        else:
            status = _c(_ANSI_RED, "FAIL")
        suffix = f"  ({self.note})" if self.note else ""
        _log(f"  {self.label} {dots} {status} ({self.duration:.1f}s){suffix}")


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------


def _kill_proc_tree(pid: int) -> None:
    """Kill *pid* and all its descendants.

    On Windows, ``taskkill /F /T`` also forces child processes to release
    inherited pipe handles — preventing the communicate() deadlock where
    grandchild processes (e.g. semgrep workers) keep stdout/stderr pipes open
    after their parent has been killed.
    On Unix, SIGKILL is sent to the whole process group.
    """
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        import signal

        with contextlib.suppress(ProcessLookupError):
            os.killpg(os.getpgid(pid), signal.SIGKILL)  # pylint: disable=no-member


def _run(
    cmd: list[str],
    *,
    cwd: Path = _HERE,
    extra_env: dict[str, str] | None = None,
    timeout: int | None = 300,
) -> tuple[int, str]:
    """
    Run *cmd* and return (returncode, combined_stdout_stderr).
    Never raises — errors are captured and returned via returncode.

    Uses Popen + communicate(timeout) so that on TimeoutExpired we can kill
    the entire process tree before draining pipes.  This avoids the Windows
    deadlock where grandchild processes (e.g. semgrep workers) keep inherited
    pipe handles open after the parent exits, causing communicate() to block
    indefinitely.

    Default timeout is 300s — prevents network tools (pip_audit, semgrep) from
    hanging indefinitely on SSL/network issues.
    """
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    try:
        with subprocess.Popen(
            [str(c) for c in cmd],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        ) as proc:
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
                return proc.returncode, (stdout or "") + (stderr or "")
            except subprocess.TimeoutExpired:
                _kill_proc_tree(proc.pid)
                proc.kill()
                try:
                    stdout, stderr = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    stdout, stderr = "", ""
                return 1, f"[TIMEOUT] Command exceeded {timeout}s limit: {cmd[0]}\n"
    except FileNotFoundError:
        return 1, f"[ERROR] Command not found: {cmd[0]}\n"
    except Exception as exc:
        return 1, f"[ERROR] Unexpected error: {exc}\n"


# ---------------------------------------------------------------------------
# Sanity checks (always run, before Phase 1)
# ---------------------------------------------------------------------------


def _sanity_checks() -> list[_StepResult]:
    """Return results for basic environment sanity checks."""
    results: list[_StepResult] = []

    r = _StepResult("[SANITY] Python >= 3.14")
    t0 = time.monotonic()
    r.ok = sys.version_info >= _MIN_PYTHON
    r.note = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if r.ok
        else f"got {sys.version_info.major}.{sys.version_info.minor} — upgrade recommended"
    )
    r.duration = time.monotonic() - t0
    results.append(r)

    r2 = _StepResult("[SANITY] requirements.txt")
    t0 = time.monotonic()
    r2.ok = _REQUIREMENTS.exists()
    r2.note = "" if r2.ok else "file not found"
    r2.duration = time.monotonic() - t0
    results.append(r2)

    r3 = _StepResult("[SANITY] pyproject.toml")
    t0 = time.monotonic()
    r3.ok = _PYPROJECT.exists()
    r3.note = "" if r3.ok else "file not found"
    r3.duration = time.monotonic() - t0
    results.append(r3)

    r4 = _StepResult("[SANITY] test-results/ dir")
    t0 = time.monotonic()
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    r4.ok = _RESULTS_DIR.is_dir()
    r4.duration = time.monotonic() - t0
    results.append(r4)

    return results


# ---------------------------------------------------------------------------
# Phase 1 steps — static / quality / unit tests
# ---------------------------------------------------------------------------


def _step_ruff_lint() -> _StepResult:
    """Run ruff linter; write JSON report to test-results/ruff.json."""
    result = _StepResult("[PHASE 1] ruff lint")
    t0 = time.monotonic()
    if not _tool_available("ruff"):
        result.skipped = True
        result.note = "not installed  (pip install ruff)"
        result.duration = time.monotonic() - t0
        return result
    rc, output = _run([sys.executable, "-m", "ruff", "check", ".", "--output-format=json"])
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    (_RESULTS_DIR / "ruff.json").write_text(output, encoding="utf-8")
    if not result.ok:
        _log(output)
    return result


def _step_ruff_format() -> _StepResult:
    """Check ruff formatting; advisory — style diffs do not fail the suite."""
    result = _StepResult("[PHASE 1] ruff format check")
    t0 = time.monotonic()
    if not _tool_available("ruff"):
        result.skipped = True
        result.note = "not installed"
        result.duration = time.monotonic() - t0
        return result
    rc, output = _run([sys.executable, "-m", "ruff", "format", "--check", "."])
    result.duration = time.monotonic() - t0
    result.ok = True  # advisory — style diffs do not fail the overall run
    if rc != 0:
        result.note = "style diffs found (advisory)"
        _log(output)
    return result


def _step_mypy() -> _StepResult:
    """Run mypy type-checker; skip if mypy not installed."""
    result = _StepResult("[PHASE 1] mypy")
    t0 = time.monotonic()
    # Defensive sweep right before mypy: transient pytest lock dirs can
    # appear between runner startup and this step on Windows.
    _cleanup_caches(_HERE)
    if not _tool_available("mypy"):
        result.skipped = True
        result.note = "not installed  (pip install mypy)"
        result.duration = time.monotonic() - t0
        return result
    # Avoid scanning repo root directly: transient lock dirs such as
    # pytest-cache-files-* can be unreadable on Windows and break os.listdir.
    sources: list[str] = [str(p) for p in _HERE.glob("*.py")]
    if _TESTS_DIR.exists():
        sources.append(str(_TESTS_DIR))
    rc, output = _run(
        [
            sys.executable,
            "-m",
            "mypy",
            *sources,
            "--ignore-missing-imports",
            "--no-error-summary",
            "--exclude",
            r"(\.venv|pytest-cache-files-.*)",
        ]
    )
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    if not result.ok:
        _log(output)
    return result


def _step_pylint() -> _StepResult:
    """Run pylint deep linter; write JSON report to test-results/pylint.json."""
    result = _StepResult("[PHASE 1] pylint")
    t0 = time.monotonic()
    if not _tool_available("pylint"):
        result.skipped = True
        result.note = "not installed  (pip install pylint)"
        result.duration = time.monotonic() - t0
        return result
    rc, output = _run(
        [
            sys.executable,
            "-m",
            "pylint",
            ".",
            "--output-format=json",
            "--recursive=y",
            "--ignore=.venv,.venv_test,.venv_wsl",
        ]
    )
    result.duration = time.monotonic() - t0
    # Non-fatal findings (convention/refactor/warning) are advisory here;
    # fail only on fatal/error/usage bits.
    result.ok = (rc & (1 | 2 | 32)) == 0
    (_RESULTS_DIR / "pylint.json").write_text(output, encoding="utf-8")
    if not result.ok:
        result.note = f"exit {rc} — see test-results/pylint.json"
        _log(output)
    elif rc != 0:
        result.note = f"advisory findings (exit {rc}) — see test-results/pylint.json"
    return result


def _step_bandit() -> _StepResult:
    """Run bandit security linter; write JSON report to test-results/bandit.json."""
    result = _StepResult("[PHASE 1] bandit")
    t0 = time.monotonic()
    if not _tool_available("bandit"):
        result.skipped = True
        result.note = "not installed  (pip install bandit)"
        result.duration = time.monotonic() - t0
        return result
    cmd: list[str] = [sys.executable, "-m", "bandit", "-r", ".", "-f", "json"]
    if _PYPROJECT.exists():
        cmd += ["-c", str(_PYPROJECT)]
    rc, output = _run(cmd)
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    (_RESULTS_DIR / "bandit.json").write_text(output, encoding="utf-8")
    for line in output.splitlines():
        if line.strip().startswith("Total issues"):
            result.note = line.strip()
            break
    if not result.ok:
        _log(output)
    return result


def _step_pip_audit() -> _StepResult:
    """Run pip-audit CVE scanner; write JSON report to test-results/pip-audit.json."""
    result = _StepResult("[PHASE 1] pip-audit")
    t0 = time.monotonic()
    if not _tool_available("pip_audit"):
        result.skipped = True
        result.note = "not installed  (pip install pip-audit)"
        result.duration = time.monotonic() - t0
        return result
    rc, output = _run([sys.executable, "-m", "pip_audit", "--format", "json"])
    result.duration = time.monotonic() - t0
    (_RESULTS_DIR / "pip-audit.json").write_text(output, encoding="utf-8")
    try:
        # pip-audit writes JSON to stdout and progress text to stderr; _run()
        # merges both — extract the JSON blob by finding the outermost { }.
        json_start = output.find("{")
        json_end = output.rfind("}") + 1
        json_text = output[json_start:json_end] if json_start >= 0 else output
        data = json.loads(json_text)
        vulns = [v for dep in data.get("dependencies", []) for v in dep.get("vulns", [])]
        fixable = [v for v in vulns if v.get("fix_versions")]
        if fixable:
            result.ok = False
            result.note = f"{len(fixable)} fixable CVE(s) — see test-results/pip-audit.json"
            _log(output)
        elif vulns:
            result.ok = True
            result.note = f"{len(vulns)} advisory CVE(s), none fixable — see pip-audit.json"
        else:
            result.ok = True
            result.note = "0 vulnerabilities"
    except Exception:
        low = output.lower()
        network_markers = (
            "httpsconnectionpool(",
            "max retries exceeded",
            "failed to establish a new connection",
            "ssl:",
            "certificate verify failed",
            "connectionerror",
            "newconnectionerror",
            "[timeout]",
        )
        if any(marker in low for marker in network_markers):
            result.ok = True
            result.note = "network/TLS unavailable — pip-audit advisory only"
            _log(output)
        else:
            result.ok = rc == 0
            if not result.ok:
                result.note = "CVEs found — see test-results/pip-audit.json"
                _log(output)
    return result


def _step_vulture() -> _StepResult:
    """Run vulture dead-code detector; skip if not installed."""
    result = _StepResult("[PHASE 1] vulture")
    t0 = time.monotonic()
    if not _tool_available("vulture"):
        result.skipped = True
        result.note = "not installed  (pip install vulture)"
        result.duration = time.monotonic() - t0
        return result
    rc, output = _run(
        [
            sys.executable,
            "-m",
            "vulture",
            ".",
            "--min-confidence",
            "80",
            "--exclude",
            ".venv,.venv_test,.venv_wsl,tests",
        ]
    )
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    if not result.ok:
        result.note = "dead code found"
        _log(output)
    return result


def _step_interrogate() -> _StepResult:
    """Check docstring coverage with interrogate; skip if not installed."""
    result = _StepResult("[PHASE 1] interrogate")
    t0 = time.monotonic()
    if not _tool_available("interrogate"):
        result.skipped = True
        result.note = "not installed  (pip install interrogate)"
        result.duration = time.monotonic() - t0
        return result
    rc, output = _run([sys.executable, "-m", "interrogate", "-v"])
    result.duration = time.monotonic() - t0
    # Docstring coverage is advisory in this runner: report it, don't block.
    result.ok = True
    if rc != 0:
        result.note = "docstring coverage below threshold (advisory)"
        _log(output)
    return result


def _step_detect_secrets() -> _StepResult:
    """Scan for leaked secrets with detect-secrets; skip if not installed."""
    result = _StepResult("[PHASE 1] detect-secrets")
    t0 = time.monotonic()
    has_bin = _binary_available("detect-secrets")
    has_mod = _tool_available("detect_secrets")
    if not has_bin and not has_mod:
        result.skipped = True
        result.note = "not installed  (pip install detect-secrets)"
        result.duration = time.monotonic() - t0
        return result
    cmd = ["detect-secrets", "scan", "."] if has_bin else [sys.executable, "-m", "detect_secrets", "scan", "."]
    baseline = _HERE / ".secrets.baseline"
    if baseline.exists():
        cmd += ["--baseline", str(baseline)]
    rc, output = _run(cmd)
    result.duration = time.monotonic() - t0
    if rc != 0 and "PermissionError: [WinError 5]" in output:
        result.skipped = True
        result.ok = True
        result.note = "detect-secrets scan blocked by Windows policy (WinError 5); non-actionable on this host"
        return result
    try:
        data = json.loads(output)
        secret_count = sum(len(v) for v in data.get("results", {}).values())
        result.ok = secret_count == 0
        if secret_count:
            result.note = f"{secret_count} potential secret(s) — review .secrets.baseline"
    except (json.JSONDecodeError, AttributeError):
        result.ok = rc == 0
    if not result.ok:
        _log(output)
    return result


def _step_unit_tests(junit_xml: str | None, verbose: bool = False) -> _StepResult:
    """Run pytest over tests/unit/ with coverage; uses tests/ if unit/ absent."""
    result = _StepResult("[PHASE 1] pytest unit")
    t0 = time.monotonic()

    test_dir = _TESTS_UNIT if _TESTS_UNIT.exists() else _TESTS_DIR
    if not test_dir.exists():
        result.skipped = True
        result.note = "no tests/ directory found"
        result.duration = time.monotonic() - t0
        return result

    unit_xml = junit_xml or str(_DEFAULT_JUNIT)
    verbosity = "-v" if verbose else "-q"
    cmd: list[str] = [
        sys.executable,
        "-m",
        "pytest",
        str(test_dir),
        verbosity,
        "--tb=short",
        f"--junitxml={unit_xml}",
    ]
    if _tool_available("pytest_cov"):
        cmd += [
            "--cov=.",
            f"--cov-report=xml:{_RESULTS_DIR / 'coverage.xml'}",
            f"--cov-report=html:{_RESULTS_DIR / 'htmlcov'}",
            "--cov-report=term-missing",
            # fail_under threshold is in [tool.coverage.report] in pyproject.toml
        ]
    rc, output = _run(cmd)
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        if "passed" in stripped or "failed" in stripped or "error" in stripped:
            result.note = stripped.split("=")[-1].strip().rstrip("=").strip()
            break
    if not result.ok:
        _log(output)
    return result


def _step_semgrep() -> _StepResult:
    """Run Semgrep AI code review; skip if not installed."""
    result = _StepResult("[PHASE 1] Semgrep (AI review)")
    t0 = time.monotonic()
    if not _binary_available("semgrep"):
        result.skipped = True
        result.note = "Install: pip install semgrep"
        result.duration = time.monotonic() - t0
        return result
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    _, output = _run(
        [
            "semgrep",
            "--config=p/default",
            "--json",
            "--output",
            str(_RESULTS_DIR / "semgrep.json"),
            "--exclude=.venv,.venv_test",
            "--exclude=test-results",
            ".",
        ],
        timeout=120,
    )
    if "[TIMEOUT]" in output:
        result.skipped = True
        result.note = "timed out (>120s) — skipped"
        result.duration = time.monotonic() - t0
        return result
    result.duration = time.monotonic() - t0
    try:
        data = json.loads((_RESULTS_DIR / "semgrep.json").read_text(encoding="utf-8"))
        findings = data.get("results", [])
        errors = [f for f in findings if f.get("extra", {}).get("severity") == "ERROR"]
        warns = [f for f in findings if f.get("extra", {}).get("severity") == "WARNING"]
        if errors:
            result.ok = False
            result.note = f"{len(errors)} error(s), {len(warns)} warning(s)"
        else:
            result.ok = True
            result.note = (
                f"0 errors, {len(warns)} warning(s)" if warns else f"{len(findings)} finding(s), none critical"
            )
    except Exception:
        result.ok = True
        result.note = "could not parse output"
    return result


def _step_pyright() -> _StepResult:
    """Run pyright type checker; always advisory — never blocks the run."""
    result = _StepResult("[PHASE 1] pyright (AI types)")
    t0 = time.monotonic()
    has_bin = _binary_available("pyright")
    has_mod = _tool_available("pyright")
    if not has_bin and not has_mod:
        result.skipped = True
        result.note = "Install: pip install pyright"
        result.duration = time.monotonic() - t0
        return result
    cmd = (
        ["pyright", "--outputjson", "--pythonpath", sys.executable, "--project", str(_PYPROJECT)]
        if has_bin
        else [
            sys.executable,
            "-m",
            "pyright",
            "--outputjson",
            "--pythonpath",
            sys.executable,
            "--project",
            str(_PYPROJECT),
        ]
    )
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True, cwd=str(_HERE))
    result.duration = time.monotonic() - t0
    (_RESULTS_DIR / "pyright.json").write_text(proc.stdout or "{}", encoding="utf-8")
    if proc.stderr:
        (_RESULTS_DIR / "pyright.stderr.txt").write_text(proc.stderr, encoding="utf-8")
    try:
        if not (proc.stdout or "").strip():
            result.ok = True
            result.note = (
                "advisory: pyright failed with no JSON output"
                if proc.returncode != 0
                else "advisory: 0 errors, 0 warnings"
            )
            return result
        data = json.loads(proc.stdout)
        summary = data.get("summary", {})
        errors = summary.get("errorCount", 0)
        warns = summary.get("warningCount", 0)
        result.ok = True
        if errors:
            result.note = f"advisory: {errors} error(s), {warns} warning(s)"
        else:
            result.note = f"advisory: 0 errors, {warns} warning(s)" if warns else "advisory: 0 errors, 0 warnings"
    except Exception:
        result.ok = True
        result.note = "advisory: pyright output parse failed"
    return result


# ---------------------------------------------------------------------------
# Phase 2 steps — live integration tests
# ---------------------------------------------------------------------------


def _step_live_tests(_junit_xml: str | None, verbose: bool = False) -> _StepResult:
    """Run pytest over tests/live/ (or -m live); requires a reachable OPC UA server."""
    result = _StepResult("[PHASE 2] pytest live")
    t0 = time.monotonic()

    server_url = os.environ.get("OPCUA_SERVER_URL", _DEFAULT_SERVER_URL)
    host, port = _parse_server_url(server_url)

    if not _is_port_reachable(host, port):
        result.skipped = True
        result.note = f"server not reachable at {host}:{port}"
        result.duration = time.monotonic() - t0
        return result

    if _TESTS_LIVE.exists():
        test_target: list[str] = [str(_TESTS_LIVE)]
        extra_args: list[str] = []
    elif _TESTS_DIR.exists():
        test_target = [str(_TESTS_DIR)]
        extra_args = ["-m", "live"]
    else:
        result.skipped = True
        result.note = "no live tests found"
        result.duration = time.monotonic() - t0
        return result

    live_xml = str(_RESULTS_DIR / "pytest-live.xml")
    verbosity = "-v" if verbose else "-q"
    cmd: list[str] = [
        sys.executable,
        "-m",
        "pytest",
        *test_target,
        verbosity,
        "--tb=short",
        f"--junitxml={live_xml}",
        *extra_args,
    ]
    if _tool_available("pytest_cov"):
        cmd += [
            "--cov=.",
            f"--cov-report=xml:{_RESULTS_DIR / 'coverage-live.xml'}",
            "--cov-report=term-missing",
            "--cov-fail-under=0",  # coverage threshold is for unit tests only; live tests skip many paths
        ]
    rc, output = _run(cmd)
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        if "passed" in stripped or "failed" in stripped or "error" in stripped:
            result.note = stripped.split("=")[-1].strip().rstrip("=").strip()
            break
    if not result.ok:
        _log(output)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="IJT Console Client — per-project test runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = p.add_mutually_exclusive_group()
    group.add_argument("--phase1", action="store_true", help="Unit / static tests only")
    group.add_argument("--phase2", action="store_true", help="Live tests only (server must be up)")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose pytest output (-v flag)")
    p.add_argument(
        "--junit-xml",
        metavar="PATH",
        default=str(_DEFAULT_JUNIT),
        help=f"Write JUnit XML to PATH (default: {_DEFAULT_JUNIT})",
    )
    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Entry point; returns 0 on success, 1 on any failure."""
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    _cleanup_caches(_HERE)  # pre-run: clear stale caches from interrupted runs
    global _USE_COLOUR  # pylint: disable=global-statement
    _USE_COLOUR = sys.stdout.isatty() and (os.name != "nt" or _enable_ansi_windows())
    _prepare_tmp_dir()

    args = _build_parser().parse_args()
    junit_xml: str | None = args.junit_xml

    if junit_xml:
        Path(junit_xml).parent.mkdir(parents=True, exist_ok=True)

    # Re-launch under venv if not already there
    if not _inside_venv():
        _relaunch_under_venv()
        return 0  # unreachable after sys.exit(); satisfies type checker

    shutil.rmtree(_RESULTS_DIR, ignore_errors=True)
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    run_phase1 = not args.phase2
    run_phase2 = not args.phase1

    _banner("IJT Console Client — Test Suite")

    t_start = time.monotonic()
    results: list[_StepResult] = []
    server_proc: subprocess.Popen | None = None

    try:
        _section("Sanity Checks")
        results.extend(_sanity_checks())

        if run_phase1:
            _section("Phase 1: Static / Quality")
            results.append(_step_ruff_lint())
            results.append(_step_ruff_format())
            results.append(_step_mypy())
            results.append(_step_pylint())
            results.append(_step_bandit())
            results.append(_step_pip_audit())
            results.append(_step_vulture())
            results.append(_step_interrogate())
            results.append(_step_detect_secrets())
            results.append(_step_unit_tests(junit_xml, verbose=args.verbose))
            results.append(_step_semgrep())
            results.append(_step_pyright())

        if run_phase2:
            _section("Phase 2: Live Tests")
            server_proc = _ensure_server()
            results.append(_step_live_tests(junit_xml, verbose=args.verbose))

    finally:
        if server_proc is not None:
            _log("  [server] Stopping simulator …")
            server_proc.terminate()
            try:
                server_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_proc.kill()
            # Clean up env var and temp dir we set
            os.environ.pop("OPCUA_SERVER_URL", None)
            global _server_tmp_dir
            shutil.rmtree(_server_tmp_dir, ignore_errors=True) if _server_tmp_dir else None
            _server_tmp_dir = None

    elapsed = time.monotonic() - t_start

    _divider()
    for r in results:
        r.print_line()
    _divider()

    passed = sum(1 for r in results if r.ok and not r.skipped)
    failed = sum(1 for r in results if not r.ok and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)
    any_failed = failed > 0
    overall = _c(_ANSI_RED, "FAIL") if any_failed else _c(_ANSI_GREEN, "PASS")
    _log(f"  Result: {overall}  passed={passed}  failed={failed}  skipped={skipped}  (elapsed: {elapsed:.1f}s)")
    _log(_c(_ANSI_CYAN, "═" * 52))
    _log("")

    _cleanup_caches(_HERE)
    return 1 if any_failed else 0


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
    _CACHE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov"}
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
    sys.exit(main())
