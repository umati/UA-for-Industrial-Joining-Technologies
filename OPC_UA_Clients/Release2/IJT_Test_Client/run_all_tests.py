#!/usr/bin/env python3
"""
run_all_tests.py — Complete test orchestrator for IJT Test Client.

Manages a virtual environment, runs static analysis (Phase 1), and executes
the full live test suite via pytest (Phase 2).

Usage:
  python run_all_tests.py                    # full run (Phase 1 + Phase 2)
  python run_all_tests.py --phase1           # static analysis only (no server)
  python run_all_tests.py --phase2           # live tests only (server must be up)
  python run_all_tests.py --junit-xml=FILE   # write JUnit XML report
  python run_all_tests.py --excel=always     # generate Excel report after run (non-fatal)
  python run_all_tests.py --no-auto-install-tools  # do not auto-install missing quality tools
  python run_all_tests.py --verbose          # verbose pytest output
  python run_all_tests.py --no-server-check  # skip pre-test server check
  python run_all_tests.py --help

Environment variables:
  OPCUA_SERVER_URL           Override server endpoint (default: opc.tcp://localhost:40462)
  OPCUA_SIMULATOR_EXE        Path to opcua_ijt_demo_application(.exe)
  OPCUA_STARTUP_TIMEOUT_SEC  Seconds to wait for simulator start (default: 30)
  SKIP_VENV_INSTALL          Set to "1" to skip pip install step (faster re-runs)
  IJT_RUNNER_NO_DELETE       Set to "1" to preserve runner outputs/tmp/caches
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
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

_REPO_ROOT = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# Key paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_PYPROJECT = _HERE / "pyproject.toml"
# .venv_test is the test-runner venv (requirements.txt + requirements-dev.txt).
# .venv is the runtime-only venv — kept separate so tests never alter the
# launch environment and vice versa.
VENV = _HERE / ".venv_test"
REQUIREMENTS = _HERE / "requirements.txt"
_REQUIREMENTS_DEV = _HERE / "requirements-dev.txt"
_RESULTS_DIR = _HERE / "test-results"
_DEFAULT_JUNIT = _RESULTS_DIR / "pytest-live.xml"
_DEFAULT_EXCEL_OUT = _RESULTS_DIR / "report.xlsx"
_TMP_DIR = _HERE / "tmp"
_SIMULATOR_CAPABILITIES = _HERE / "server_capabilities.simulator.yaml"
_AUTO_INSTALL_TOOLS = False
_AUTO_INSTALL_BLOCKED_REASON: str | None = None
_RUN_START: float = 0.0  # set at main() entry; used to reject stale XML files
_RUNNER_SET_CAPABILITIES_FILE = False

# The OPC UA server port this client connects to.  Defined once here so every
# reference below derives from it — change the port in one place only.
_OPCUA_SERVER_PORT = 40462

_DEFAULT_SERVER_URL = f"opc.tcp://localhost:{_OPCUA_SERVER_PORT}"
_MIN_PYTHON = (3, 14)

# Well-known simulator binary locations relative to the repo root
_WELL_KNOWN_SIMULATOR_PATHS = [
    # Windows native binary (checked first on Windows)
    _REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator" / "opcua_ijt_demo_application.exe",
    # Linux / WSL binary
    _REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator_Linux" / "opcua_ijt_demo_application",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deletes_disabled() -> bool:
    """Return True when the runner must preserve existing files and directories."""
    return os.environ.get("IJT_RUNNER_NO_DELETE", "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_rmtree(path: Path) -> None:
    """Remove a directory tree unless deletion is disabled for this run."""
    if _deletes_disabled():
        logger.info("[cleanup] Preserving directory because IJT_RUNNER_NO_DELETE=1: %s", path)
        return
    shutil.rmtree(path, ignore_errors=True)


def _safe_unlink(path: Path) -> None:
    """Remove a file unless deletion is disabled for this run."""
    if _deletes_disabled():
        logger.info("[cleanup] Preserving file because IJT_RUNNER_NO_DELETE=1: %s", path)
        return
    path.unlink(missing_ok=True)


def _venv_python(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")


def _venv_pip(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts" if os.name == "nt" else "bin") / ("pip.exe" if os.name == "nt" else "pip")


def _is_port_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_opcua_endpoint(url: str) -> tuple[str, int]:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return parsed.hostname or "localhost", parsed.port or _OPCUA_SERVER_PORT


def _prepare_tmp_dir() -> None:
    """Reset runner-managed tmp workspace and recreate tmp/pytest/."""
    _TMP_DIR.mkdir(parents=True, exist_ok=True)
    if _deletes_disabled():
        (_TMP_DIR / "pytest").mkdir(parents=True, exist_ok=True)
        return
    for child in _TMP_DIR.iterdir():
        name = child.name
        managed = name in {"pytest", "pytest_tmp", "pip-audit-cache", "ruff-cache"} or name.startswith(
            "server_instance_"
        )
        if not managed:
            continue
        with contextlib.suppress(OSError):
            if child.is_dir():
                _safe_rmtree(child)
            else:
                _safe_unlink(child)
    pytest_tmp = _TMP_DIR / "pytest"
    pytest_tmp.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Logging / output helpers
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_all_tests")

_USE_COLOUR: bool = False
_VERBOSE: bool = False

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


def _log_verbose(msg: str) -> None:
    """Emit noisy diagnostic output only when verbose mode is enabled."""
    if _VERBOSE and msg.strip():
        _log(msg)


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
# Result helper
# ---------------------------------------------------------------------------


class _StepResult:
    """Result of a single test / analysis step."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.ok: bool = False
        self.skipped: bool = False
        self.warn: bool = False  # advisory: ran with issues but does not block the suite
        self.note: str = ""
        self.duration: float = 0.0

    def print_line(self) -> None:
        width = 44
        dots = "." * max(0, width - len(self.label))
        if self.skipped:
            status = _c(_ANSI_YELLOW, "SKIP")
        elif self.warn:
            status = _c(_ANSI_YELLOW, "WARN")
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
            os.killpg(os.getpgid(pid), signal.SIGKILL)


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
    deadlock where grandchild processes (e.g. semgrep parallel workers) keep
    inherited pipe handles open after the parent exits, causing communicate()
    to block indefinitely.

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
# Tool availability helpers
# ---------------------------------------------------------------------------


def _tool_available(module_name: str) -> bool:
    """Return True if *module_name* can be imported by the current interpreter."""
    result = subprocess.run(
        [sys.executable, "-c", f"import {module_name}"],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def _binary_available(name: str) -> bool:
    """Return True if *name* is found on PATH."""
    return shutil.which(name) is not None


def _default_auto_install_tools() -> bool:
    """Best-practice default: auto-install locally, keep CI reproducible."""
    return not bool(os.environ.get("CI"))


def _ensure_python_tool(*, module_name: str, pip_package: str, label: str) -> tuple[bool, str]:
    """Ensure a Python module tool is available, optionally auto-installing it."""
    if _tool_available(module_name):
        return True, ""
    if not _AUTO_INSTALL_TOOLS:
        return False, f"not installed  (pip install {pip_package})"
    global _AUTO_INSTALL_BLOCKED_REASON
    if _AUTO_INSTALL_BLOCKED_REASON:
        return False, _AUTO_INSTALL_BLOCKED_REASON

    _log(f"  [setup] Installing missing tool: {label} ({pip_package}) ...")
    rc, output = _run(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", pip_package],
        timeout=300,
    )
    if rc == 0 and _tool_available(module_name):
        return True, "auto-installed"
    network_error_markers = (
        "Failed to establish a new connection",
        "Max retries exceeded",
        "NameResolutionError",
        "Temporary failure in name resolution",
    )
    if any(marker in output for marker in network_error_markers):
        _AUTO_INSTALL_BLOCKED_REASON = "auto-install unavailable (network/index access blocked)"
    if output.strip():
        _log(output)
    return False, f"auto-install failed for {pip_package}"


def _ensure_cli_tool(
    *, binary_name: str, pip_package: str, label: str, module_name: str | None = None
) -> tuple[bool, str]:
    """Ensure a CLI tool is available, optionally auto-installing it."""
    if _binary_available(binary_name) or (module_name and _tool_available(module_name)):
        return True, ""
    if not _AUTO_INSTALL_TOOLS:
        return False, f"Install: pip install {pip_package}"
    global _AUTO_INSTALL_BLOCKED_REASON
    if _AUTO_INSTALL_BLOCKED_REASON:
        return False, _AUTO_INSTALL_BLOCKED_REASON

    _log(f"  [setup] Installing missing tool: {label} ({pip_package}) ...")
    rc, output = _run(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", pip_package],
        timeout=300,
    )
    has_tool = _binary_available(binary_name) or (module_name and _tool_available(module_name))
    if rc == 0 and has_tool:
        return True, "auto-installed"
    network_error_markers = (
        "Failed to establish a new connection",
        "Max retries exceeded",
        "NameResolutionError",
        "Temporary failure in name resolution",
    )
    if any(marker in output for marker in network_error_markers):
        _AUTO_INSTALL_BLOCKED_REASON = "auto-install unavailable (network/index access blocked)"
    if output.strip():
        _log(output)
    return False, f"auto-install failed for {pip_package}"


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
    logger.info("Installing pre-commit hooks …")
    subprocess.check_call(
        [str(_venv_python(VENV)), "-m", "pre_commit", "install", "--install-hooks"],
        cwd=str(git_root),
    )


# ---------------------------------------------------------------------------
# Venv management
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
        stale = _HERE / name
        if stale.is_dir():
            logger.info("[cleanup] Stale virtual environment found: %s", stale)
            _safe_rmtree(stale)


def ensure_venv() -> None:
    """Create the virtual environment if it does not already exist."""
    _remove_stale_venvs()
    if not VENV.exists():
        logger.info("Creating virtual environment: %s", VENV)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=False)
    else:
        logger.info("Using existing virtual environment: %s", VENV)


def _requirements_hash() -> str:
    """Return a short hash of all requirements files combined."""
    import hashlib

    h = hashlib.sha256()
    for req in (REQUIREMENTS, _REQUIREMENTS_DEV):
        if req.exists():
            h.update(req.read_bytes())
    return h.hexdigest()[:16]


def install_requirements() -> None:
    """Install packages; reinstall automatically when requirements files change."""
    if os.environ.get("SKIP_VENV_INSTALL") == "1":
        logger.info("Skipping pip install (SKIP_VENV_INSTALL=1)")
        return
    hash_file = VENV / ".req-hash"
    current_hash = _requirements_hash()
    if hash_file.exists() and hash_file.read_text().strip() == current_hash:
        logger.info("Requirements unchanged — skipping pip install")
        return
    pip = str(_venv_pip(VENV))
    python = str(_venv_python(VENV))
    # Use python -m pip for self-upgrade (newer pip requires this on Windows)
    subprocess.run([python, "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=False)
    for req_file in (REQUIREMENTS, _REQUIREMENTS_DEV):
        if req_file.exists():
            logger.info("Installing requirements from %s...", req_file.name)
            subprocess.run(
                [pip, "install", "--quiet", "-r", str(req_file)],
                check=False,
            )
        else:
            logger.info("No %s found — skipping", req_file.name)
    hash_file.write_text(current_hash)


def _relaunch_if_needed() -> None:
    """Re-exec this script under the venv Python if not already running inside it."""
    venv_py = _venv_python(VENV)
    if not venv_py.exists():
        return
    try:
        current = Path(sys.executable).resolve()
        target = venv_py.resolve()
        if current == target:
            return
    except Exception:
        return
    # Tell the re-launched process to skip install (already done above)
    env = os.environ.copy()
    env["SKIP_VENV_INSTALL"] = "1"
    # subprocess.run() + sys.exit() instead of os.execve():
    # On Windows, os.execve uses P_OVERLAY (CreateProcess + ExitProcess), creating a
    # grandchild that inherits stdout/stderr pipe write-handles. Any parent using
    # Popen(stdout=PIPE).communicate() then blocks forever because the grandchild
    # keeps those handles open. subprocess.run() keeps the current process alive until
    # the child finishes, so pipe handles close in the correct order on all platforms.
    script_path = str(Path(__file__).resolve())
    result = subprocess.run([str(venv_py), script_path, *sys.argv[1:]], env=env, check=False, cwd=str(_HERE))
    sys.exit(result.returncode)


# ---------------------------------------------------------------------------
# Server helpers
# ---------------------------------------------------------------------------


def _get_server_url() -> str:
    return os.environ.get("OPCUA_SERVER_URL", _DEFAULT_SERVER_URL)


def _parse_server_url() -> tuple[str, int]:
    """Parse OPCUA_SERVER_URL and return (host, port)."""
    return _parse_opcua_endpoint(_get_server_url())


def _startup_timeout_s() -> float:
    """Return simulator startup timeout in seconds."""
    try:
        return float(os.environ.get("OPCUA_STARTUP_TIMEOUT_SEC", "30"))
    except ValueError:
        return 30.0


def _is_opcua_ready(url: str, timeout_s: float) -> bool:
    """Return True when the endpoint accepts a real OPC UA connection."""
    try:
        from helpers.server_manager import wait_for_opcua_ready

        return wait_for_opcua_ready(url, timeout_s=timeout_s)
    except Exception as exc:  # noqa: BLE001
        logger.debug("OPC UA readiness probe failed: %s", exc)
        return False


_server_tmp_dir: Path | None = None  # set by _launch_simulator_on_port; cleared in finally


def _sourcecontrol_root() -> Path:
    """Return the SourceControl root when this checkout is below it."""
    for parent in [_HERE, *_HERE.parents]:
        if parent.name.lower() == "sourcecontrol":
            return parent
    return _TMP_DIR


def _simulator_tmp_dir(port: int) -> Path:
    """Return a short runner-managed simulator copy path for Windows MAX_PATH safety."""
    suffix = f"_ijt_sim_{port}"
    if _deletes_disabled():
        suffix = f"{suffix}_{os.getpid()}_{int(time.time())}"
    return _sourcecontrol_root() / suffix


def _launch_simulator_on_port(port: int, exe: str) -> subprocess.Popen | None:
    """Copy the binary dir to a temp location, patch the port config, and launch.

    Stores the temp dir in the module-global ``_server_tmp_dir`` so the caller's
    finally block can remove it via ``shutil.rmtree(_server_tmp_dir, ignore_errors=True)``.
    Returns the Popen handle on success, None on failure (temp dir cleaned on failure).
    """
    global _RUNNER_SET_CAPABILITIES_FILE, _server_tmp_dir

    exe_path = Path(exe)
    if not exe_path.exists():
        _log(f"  [server] Binary not found: {exe}")
        return None

    src_dir = exe_path.parent
    tmp_dir = _simulator_tmp_dir(port)
    _log(f"  [server] Launching simulator on port {port} (copied to {tmp_dir})")
    try:
        if tmp_dir.exists():
            _safe_rmtree(tmp_dir)
        shutil.copytree(src_dir, tmp_dir)
    except OSError as exc:
        _log(f"  [server] Failed to copy binary dir: {exc}")
        _safe_rmtree(tmp_dir)
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
            _safe_rmtree(tmp_dir)
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
        _safe_rmtree(tmp_dir)
        return None

    server_url = f"opc.tcp://localhost:{port}"
    if _is_opcua_ready(server_url, timeout_s=_startup_timeout_s()):
        _log(f"  [server] Ready on port {port}")
        os.environ["OPCUA_SERVER_URL"] = server_url
        if "OPCUA_CAPABILITIES_FILE" not in os.environ and _SIMULATOR_CAPABILITIES.exists():
            os.environ["OPCUA_CAPABILITIES_FILE"] = str(_SIMULATOR_CAPABILITIES)
            _RUNNER_SET_CAPABILITIES_FILE = True
            _log(f"  [server] Using simulator capabilities: {_SIMULATOR_CAPABILITIES.name}")
        _server_tmp_dir = tmp_dir
        return proc

    _log("  [server] Timed out waiting for simulator — terminating")
    proc.terminate()
    _safe_rmtree(tmp_dir)
    return None


def _ensure_server(port: int = _OPCUA_SERVER_PORT) -> subprocess.Popen | None:
    """Start OPC UA server if not already running. Returns Popen handle or None.

    If OPCUA_SERVER_URL is already set the caller manages the server — skip auto-launch.
    If the binary is found and started, os.environ["OPCUA_SERVER_URL"] is updated to
    the client's port so that live tests can locate it.
    """
    if os.environ.get("OPCUA_SERVER_URL"):
        _log("  [server] OPCUA_SERVER_URL already set — skipping auto-launch")
        return None
    if _is_port_reachable("localhost", port):
        server_url = f"opc.tcp://localhost:{port}"
        if _is_opcua_ready(server_url, timeout_s=min(_startup_timeout_s(), 10.0)):
            _log(f"  [server] Already running on port {port}")
        else:
            _log(f"  [server] Port {port} is open but OPC UA handshake failed")
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


def _check_server(skip: bool) -> None:
    """Print informational pre-test server status messages."""
    if skip:
        return
    host, port = _parse_server_url()
    url = _get_server_url()
    logger.info("Checking OPC UA server at %s ...", url)
    if _is_port_reachable(host, port):
        if _is_opcua_ready(url, timeout_s=min(_startup_timeout_s(), 10.0)):
            logger.info("OK Server is reachable - tests will connect normally.")
        else:
            logger.warning("NO Server TCP port is open but OPC UA handshake failed.")
        return
    logger.warning("NO Server not reachable at %s:%s", host, port)
    sim_exe = os.environ.get("OPCUA_SIMULATOR_EXE")
    if sim_exe:
        logger.info("  Auto-launch enabled: OPCUA_SIMULATOR_EXE=%s", sim_exe)
    else:
        well_known = next((p for p in _WELL_KNOWN_SIMULATOR_PATHS if p.exists()), None)
        if well_known:
            logger.info("  Simulator found at well-known path: %s", well_known)
            logger.info("  Will attempt to start it automatically.")
        else:
            logger.info("  No simulator found. To auto-launch, set:")
            logger.info("    OPCUA_SIMULATOR_EXE=<path/to/opcua_ijt_demo_application>")
    timeout = os.environ.get("OPCUA_STARTUP_TIMEOUT_SEC", "30")
    logger.info("  Startup timeout: %ss (OPCUA_STARTUP_TIMEOUT_SEC)", timeout)
    logger.info("  Live tests will be skipped if the server cannot be reached.")


def _print_test_count(pytest_args: list[str] | None = None) -> None:
    """Run pytest --collect-only and print a summary of found tests."""
    try:
        result = subprocess.run(
            [
                str(_venv_python(VENV)),
                "-m",
                "pytest",
                *(pytest_args or []),
                "--collect-only",
                "-q",
                "--tb=no",
            ],
            cwd=_HERE,
            capture_output=True,
            text=True,
            check=False,
        )
        for line in reversed(result.stdout.splitlines()):
            line = line.strip()
            if line and ("test" in line or "item" in line or "warning" in line or "error" in line):
                logger.info("Test suite: %s", line)
                break
    except Exception:
        pass  # non-critical


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
    r2.ok = REQUIREMENTS.exists()
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
# Phase 1 steps — static / quality analysis + unit tests
# ---------------------------------------------------------------------------


def _step_ruff_lint() -> _StepResult:
    """Run ruff linter; write JSON report to test-results/ruff.json."""
    result = _StepResult("[PHASE 1] ruff lint")
    t0 = time.monotonic()
    ok, note = _ensure_python_tool(module_name="ruff", pip_package="ruff", label="ruff")
    if not ok:
        result.skipped = True
        result.note = note
        result.duration = time.monotonic() - t0
        return result
    rc, output = _run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            ".",
            "--output-format=json",
            "--cache-dir",
            str(_TMP_DIR / "ruff-cache"),
        ]
    )
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    (_RESULTS_DIR / "ruff.json").write_text(output, encoding="utf-8")
    if not result.ok:
        _log(output)
    return result


def _step_ruff_format() -> _StepResult:
    result = _StepResult("[PHASE 1] ruff format check")
    t0 = time.monotonic()
    ok, note = _ensure_python_tool(module_name="ruff", pip_package="ruff", label="ruff")
    if not ok:
        result.skipped = True
        result.note = note
        result.duration = time.monotonic() - t0
        return result
    rc, output = _run(
        [sys.executable, "-m", "ruff", "format", "--check", ".", "--cache-dir", str(_TMP_DIR / "ruff-cache")]
    )
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    if rc != 0:
        result.note = "style diffs found — run: ruff format ."
        _log(output)
    return result


def _step_bandit() -> _StepResult:
    """Run bandit security linter; write JSON report to test-results/bandit.json."""
    result = _StepResult("[PHASE 1] bandit")
    t0 = time.monotonic()
    ok, note = _ensure_python_tool(module_name="bandit", pip_package="bandit", label="bandit")
    if not ok:
        result.skipped = True
        result.note = note
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


def _is_https_reachable(host: str, timeout: float = 5.0) -> bool:
    """Fast preflight: return True only if a verified HTTPS connection to host succeeds.

    Uses the default SSL context (certificate verification enabled). Returns False
    immediately on SSL cert errors, connection refused, or timeout — avoiding
    the multi-minute retry delays that pip-audit and semgrep impose on failure.
    """
    import urllib.request

    try:
        # safe: always https; host is a known constant (pypi.org, semgrep.dev)
        urllib.request.urlopen(f"https://{host}/", timeout=timeout)  # nosec B310
        return True
    except Exception:
        return False


def _step_pip_audit() -> _StepResult:
    """Run pip-audit CVE scanner; write JSON report to test-results/pip-audit.json."""
    result = _StepResult("[PHASE 1] pip-audit")
    t0 = time.monotonic()
    ok, note = _ensure_python_tool(module_name="pip_audit", pip_package="pip-audit", label="pip-audit")
    if not ok:
        result.skipped = True
        result.note = note
        result.duration = time.monotonic() - t0
        return result
    if not _is_https_reachable("pypi.org"):
        result.ok = True
        result.skipped = True
        result.note = "network/TLS unavailable — pip-audit skipped"
        result.duration = time.monotonic() - t0
        return result
    pip_audit_cache = _TMP_DIR / "pip-audit-cache"
    pip_audit_cache.mkdir(parents=True, exist_ok=True)
    rc, output = _run(
        [sys.executable, "-m", "pip_audit", "--format", "json"],
        extra_env={
            # Keep cache local to project temp dir to avoid user-profile permission issues.
            "PIP_AUDIT_CACHE_DIR": str(pip_audit_cache),
            "PIP_CACHE_DIR": str(pip_audit_cache),
        },
        timeout=60,  # Match Console Client; 300s default caused 5-minute stall on network-unavailable hosts.
    )
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
        # When pip-audit cannot reach PyPI (offline/corporate firewall), do not fail the full
        # test run as "CVEs found" — treat it as a skipped network-dependent check.
        network_error_markers = (
            "Failed to establish a new connection",
            "Max retries exceeded",
            "ConnectionError",
            "CERTIFICATE_VERIFY_FAILED",
            "NameResolutionError",
            "Temporary failure in name resolution",
            "socket operation was attempted to an unreachable network",
            "[TIMEOUT]",
        )
        if any(marker in output for marker in network_error_markers):
            result.ok = True
            result.skipped = True
            result.note = "network unavailable for pip-audit (security check skipped)"
            return result
        result.ok = rc == 0
        if not result.ok:
            result.note = "pip-audit failed — see test-results/pip-audit.json"
            _log(output)
    return result


def _step_detect_secrets() -> _StepResult:
    """Scan for leaked secrets with detect-secrets; skip if not installed."""
    result = _StepResult("[PHASE 1] detect-secrets")
    t0 = time.monotonic()
    ok, note = _ensure_cli_tool(
        binary_name="detect-secrets",
        module_name="detect_secrets",
        pip_package="detect-secrets",
        label="detect-secrets",
    )
    if not ok:
        result.skipped = True
        result.note = note
        result.duration = time.monotonic() - t0
        return result
    has_bin = _binary_available("detect-secrets")
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


def _step_unit_tests() -> _StepResult:
    """Run pytest over tests/unit/ if it exists; skipped otherwise."""
    result = _StepResult("[PHASE 1] pytest unit")
    t0 = time.monotonic()
    unit_dir = _HERE / "tests" / "unit"
    if not unit_dir.exists():
        result.skipped = True
        result.note = "no tests/unit/ directory"
        result.duration = time.monotonic() - t0
        return result
    unit_xml = str(_RESULTS_DIR / "pytest-unit.xml")
    pytest_args: list[str] = [
        str(unit_dir),
        "-q",
        "--tb=short",
        f"--junitxml={unit_xml}",
    ]
    if _tool_available("pytest_cov"):
        pytest_args += [
            # Cover only helpers/ — the library actually tested by unit tests.
            # Using --cov=. would include live/conformance test files (0% coverage)
            # and pull the total far below the fail_under threshold.
            "--cov=helpers",
            f"--cov-report=xml:{_RESULTS_DIR / 'coverage.xml'}",
            f"--cov-report=html:{_RESULTS_DIR / 'htmlcov'}",
            "--cov-report=term-missing",
            # fail_under threshold is in [tool.coverage.report] in pyproject.toml
        ]
    cmd: list[str] = [sys.executable, "-m", "pytest", *pytest_args]
    rc, output = _run(
        cmd,
        extra_env={"IJT_CU_COMPLIANCE_REPORT_FILE": str(_RESULTS_DIR / "cu-compliance-report-unit.json")},
    )
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        if "passed" in stripped or "failed" in stripped or "error" in stripped:
            result.note = stripped.strip("= ").strip()
            break
    if not result.ok:
        _log(output)
    return result


def _step_semgrep() -> _StepResult:
    """Run Semgrep AI code review; skip if not installed."""
    result = _StepResult("[PHASE 1] Semgrep (AI review)")
    t0 = time.monotonic()
    ok, note = _ensure_cli_tool(
        binary_name="semgrep",
        module_name="semgrep",
        pip_package="semgrep",
        label="semgrep",
    )
    if not ok:
        result.skipped = True
        result.note = note
        result.duration = time.monotonic() - t0
        return result
    if not _is_https_reachable("semgrep.dev"):
        result.warn = True
        result.note = "semgrep produced no output (rc=N/A) — network/TLS unavailable (preflight)"
        result.duration = time.monotonic() - t0
        return result
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    semgrep_cmd = ["semgrep"] if _binary_available("semgrep") else [sys.executable, "-m", "semgrep"]
    rc, output = _run(
        semgrep_cmd
        + [
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
    json_file = _RESULTS_DIR / "semgrep.json"
    if not json_file.exists():
        # Semgrep exited without writing output — typically a network or auth failure
        # when downloading cloud rules (p/default requires internet + optional login).
        result.warn = True
        result.note = (
            f"semgrep produced no output (rc={rc}) — network unavailable or authentication required (semgrep login)"
        )
        _log_verbose(output)
        return result
    try:
        data = json.loads(json_file.read_text(encoding="utf-8"))
        findings = data.get("results", [])
        errors = [f for f in findings if f.get("extra", {}).get("severity") == "ERROR"]
        warns = [f for f in findings if f.get("extra", {}).get("severity") == "WARNING"]
        if errors:
            result.ok = False
            result.note = f"{len(errors)} error(s), {len(warns)} warning(s)"
        elif warns:
            result.ok = True
            result.warn = True  # advisory findings — non-blocking
            result.note = f"0 errors, {len(warns)} warning(s)"
        else:
            result.ok = True
            result.note = f"{len(findings)} finding(s), none critical"
    except Exception as exc:
        # JSON exists but is malformed — log content for diagnosis, never block.
        result.warn = True
        result.note = f"semgrep.json parse failed (rc={rc}): {exc!s:.120}"
        _log_verbose(output)
    return result


def _step_pyright() -> _StepResult:
    """Run pyright AI type inference; skip if not installed."""
    result = _StepResult("[PHASE 1] pyright (AI types)")
    t0 = time.monotonic()
    ok, note = _ensure_cli_tool(
        binary_name="pyright",
        module_name="pyright",
        pip_package="pyright",
        label="pyright",
    )
    if not ok:
        result.skipped = True
        result.note = note
        result.duration = time.monotonic() - t0
        return result
    has_bin = _binary_available("pyright")
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
            if proc.returncode != 0:
                result.note = "advisory: pyright failed with no JSON output"
            else:
                result.note = "advisory: 0 errors, 0 warnings"
            return result

        data = json.loads(proc.stdout)
        summary = data.get("summary", {})
        errors = summary.get("errorCount", 0)
        warns = summary.get("warningCount", 0)
        result.ok = True
        if errors:
            result.warn = True
            result.note = f"advisory: {errors} error(s), {warns} warning(s)"
        else:
            result.note = f"advisory: 0 errors, {warns} warning(s)" if warns else "advisory: 0 errors, 0 warnings"
    except Exception:
        result.ok = True
        result.note = "advisory: pyright output parse failed"
    return result


# ---------------------------------------------------------------------------
# Phase 2 step — live tests via venv pytest
# ---------------------------------------------------------------------------


_PYTEST_OPTIONS_WITH_VALUE = {
    "--basetemp",
    "--cov",
    "--cov-report",
    "--junit-xml",
    "--junitxml",
    "--maxfail",
    "--rootdir",
    "--tb",
    "-k",
    "-m",
    "-n",
}


def _has_explicit_pytest_selection(args: list[str]) -> bool:
    """Return True when forwarded pytest args include a positional test selector."""
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg == "--":
            continue
        if arg in _PYTEST_OPTIONS_WITH_VALUE:
            skip_next = True
            continue
        if any(arg.startswith(f"{option}=") for option in _PYTEST_OPTIONS_WITH_VALUE if option.startswith("--")):
            continue
        if arg.startswith("-"):
            continue
        return True
    return False


def _has_explicit_coverage_option(args: list[str]) -> bool:
    """Return True when forwarded pytest args explicitly request coverage behavior."""
    return any(arg == "--no-cov" or arg == "--cov" or arg.startswith("--cov") for arg in args)


def _default_live_coverage_args() -> list[str]:
    """Return live-stage coverage args that collect diagnostics without blocking compliance."""
    return [
        "--cov=helpers",
        "--cov-append",
        f"--cov-report=xml:{_RESULTS_DIR / 'coverage-combined.xml'}",
        "--cov-report=term-missing",
        "--cov-fail-under=0",
    ]


def run_pytest(extra_args: list[str]) -> int:
    """Run pytest inside the virtual environment and return its exit code."""
    cmd = [str(_venv_python(VENV)), "-m", "pytest"] + extra_args
    logger.info("Running: %s", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd, cwd=_HERE, check=False)
    return result.returncode


def _step_live_tests(extra_pytest_args: list[str], skip_server_check: bool) -> _StepResult:
    """Run the full live test suite via venv pytest.

    The unit stage owns the hard coverage gate. Live conformance tests still
    collect helper coverage diagnostics by default, but force fail-under to 0
    so an otherwise passing server-facing compliance run is not failed by the
    live coverage shape.
    """
    result = _StepResult("[PHASE 2] pytest live")
    t0 = time.monotonic()

    if not skip_server_check:
        host, port = _parse_server_url()
        if not _is_port_reachable(host, port):
            result.skipped = True
            result.note = f"server not reachable at {host}:{port}"
            result.duration = time.monotonic() - t0
            return result

    live_selection_args = list(extra_pytest_args)
    if not _has_explicit_pytest_selection(live_selection_args):
        live_selection_args.append("conformance")

    _print_test_count(live_selection_args)

    cov_args: list[str] = []
    if _tool_available("pytest_cov") and not _has_explicit_coverage_option(live_selection_args):
        cov_args = _default_live_coverage_args()

    rc = run_pytest(live_selection_args + cov_args)
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    if not result.ok:
        result.note = f"pytest exited with code {rc}"
    return result


def _default_excel_mode() -> str:
    """Default Excel behavior: always in CI, on-success for local runs."""
    return "always" if os.environ.get("CI") else "on-success"


def _print_skip_reason_summary(junit_xml_path: Path | None) -> None:
    """Parse a pytest JUnit XML and print a grouped skip-reason summary.

    Helps catch regressions where a new skip reason appears or skip volume
    grows unexpectedly.  Printed only when there are skipped test cases.
    """
    import xml.etree.ElementTree as ET
    from collections import Counter

    if junit_xml_path is None or not junit_xml_path.exists():
        return
    try:
        tree = ET.parse(junit_xml_path)
    except ET.ParseError:
        return

    reasons: Counter[str] = Counter()
    for testcase in tree.iter("testcase"):
        skip_el = testcase.find("skipped")
        if skip_el is None:
            continue
        # pytest sets the skip reason in 'message'; fall back to element text
        msg = (skip_el.get("message") or "").strip()
        if not msg:
            msg = (skip_el.text or "").strip()
        # Normalise: strip leading "Skipped: " prefix that pytest sometimes adds
        msg = msg.removeprefix("Skipped: ").strip()
        # Truncate long reasons to keep the table readable
        reason = msg[:80] + "…" if len(msg) > 80 else msg
        reasons[reason or "(no reason)"] += 1

    if not reasons:
        return

    total_skipped = sum(reasons.values())
    _log(f"  Skip reason summary ({total_skipped} total):")
    for reason, count in reasons.most_common():
        _log(f"    {count:>5}  {reason}")


def _resolve_junit_xml_path(explicit_junit_xml: str | None) -> Path | None:
    """Pick the best available JUnit XML produced by this run.

    Explicit paths (via --junit-xml) are trusted unconditionally.
    Auto-detected candidates are rejected if older than _RUN_START to avoid
    consuming stale XML from a previous run.
    """
    if explicit_junit_xml:
        p = Path(explicit_junit_xml)
        return p if p.exists() else None
    candidates = [_DEFAULT_JUNIT, _RESULTS_DIR / "pytest-unit.xml", _RESULTS_DIR / "pytest.xml"]
    for path in candidates:
        if not path.exists():
            continue
        if _RUN_START and path.stat().st_mtime < _RUN_START:
            print(f"  [excel] Skipping stale {path.name} (predates this run)")
            continue
        return path
    return None


def _step_excel_report(xml_path: Path, out_path: Path) -> _StepResult:
    """Generate Excel report from JUnit XML. Failures here are advisory only."""
    result = _StepResult("[POST] Excel report")
    t0 = time.monotonic()
    cmd = [
        str(_venv_python(VENV)),
        str(_HERE / "scripts" / "make_excel_report.py"),
        "--xml",
        str(xml_path),
        "--out",
        str(out_path),
    ]
    rc, output = _run(cmd, cwd=_HERE)
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    if result.ok:
        result.note = str(out_path)
    else:
        result.note = f"non-fatal (exit {rc})"
        if output.strip():
            _log(output.strip())
    return result


def _maybe_generate_excel(
    excel_mode: str,
    tests_passed: bool,
    explicit_junit_xml: str | None,
    excel_out: str | None,
) -> _StepResult:
    """Generate (or skip) Excel report according to selected mode."""
    result = _StepResult("[POST] Excel report")
    t0 = time.monotonic()

    if excel_mode == "never":
        result.skipped = True
        result.note = "disabled (--excel=never)"
        result.duration = time.monotonic() - t0
        return result

    if excel_mode == "on-success" and not tests_passed:
        result.skipped = True
        result.note = "tests failed; skipped (--excel=on-success)"
        result.duration = time.monotonic() - t0
        return result

    xml_path = _resolve_junit_xml_path(explicit_junit_xml)
    if xml_path is None:
        result.skipped = True
        result.note = "no JUnit XML found"
        result.duration = time.monotonic() - t0
        return result

    out_path = Path(excel_out) if excel_out else _DEFAULT_EXCEL_OUT
    return _step_excel_report(xml_path, out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="IJT Test Client — venv setup, static analysis + live test orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = p.add_mutually_exclusive_group()
    group.add_argument("--phase1", action="store_true", help="Static analysis only (no server)")
    group.add_argument("--phase2", action="store_true", help="Live tests only (server must be up)")
    p.add_argument("--junit-xml", metavar="FILE", help="Write JUnit XML report to FILE")
    p.add_argument(
        "--excel",
        choices=["never", "on-success", "always"],
        default=_default_excel_mode(),
        help="Generate Excel report after tests (non-fatal). Default: on-success locally, always in CI.",
    )
    p.add_argument(
        "--excel-out",
        metavar="FILE",
        help=f"Excel output path (default: {_DEFAULT_EXCEL_OUT})",
    )
    p.add_argument(
        "--auto-install-tools",
        action="store_true",
        default=_default_auto_install_tools(),
        help="Auto-install missing quality tools via pip (default: on locally, off in CI).",
    )
    p.add_argument(
        "--no-auto-install-tools",
        action="store_false",
        dest="auto_install_tools",
        help="Disable auto-install of missing quality tools.",
    )
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose pytest output")
    p.add_argument(
        "--no-server-check",
        action="store_true",
        help="Skip pre-test OPC UA server reachability check",
    )
    p.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Extra args forwarded to pytest (phase 2 only)",
    )
    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Entry point; returns 0 on success, 1 on any failure."""
    global _RUNNER_SET_CAPABILITIES_FILE, _RUN_START
    _RUN_START = time.time()
    _RUNNER_SET_CAPABILITIES_FILE = False
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    _cleanup_caches(_HERE)  # pre-run: clear stale caches from interrupted runs
    global _USE_COLOUR, _AUTO_INSTALL_TOOLS, _VERBOSE

    _USE_COLOUR = sys.stdout.isatty() and (os.name != "nt" or _enable_ansi_windows())
    _prepare_tmp_dir()

    args = _build_parser().parse_args()
    _VERBOSE = bool(args.verbose)
    _AUTO_INSTALL_TOOLS = bool(args.auto_install_tools)
    run_phase1 = not args.phase2
    run_phase2 = not args.phase1

    # Step 1: Ensure venv exists and all dependencies are installed
    ensure_venv()
    install_requirements()
    _ensure_precommit_hooks()

    # Step 2: Re-exec under the venv Python so all tools use the same interpreter
    _relaunch_if_needed()

    _safe_rmtree(_RESULTS_DIR)
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Build pytest arg list from CLI flags + any raw remainder args
    extra_pytest_args: list[str] = list(args.pytest_args or [])
    if args.verbose:
        extra_pytest_args = ["-v"] + extra_pytest_args
    if args.junit_xml:
        extra_pytest_args = [f"--junit-xml={args.junit_xml}"] + extra_pytest_args
    else:
        extra_pytest_args = [f"--junit-xml={_DEFAULT_JUNIT}"] + extra_pytest_args

    _banner("IJT Test Client — Test Suite")

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
            results.append(_step_bandit())
            results.append(_step_pip_audit())
            results.append(_step_detect_secrets())
            results.append(_step_unit_tests())
            results.append(_step_semgrep())
            results.append(_step_pyright())

        if run_phase2:
            _section("Phase 2: Live Tests")
            _check_server(skip=args.no_server_check)
            server_proc = _ensure_server()
            results.append(_step_live_tests(extra_pytest_args, skip_server_check=args.no_server_check))

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
            if _RUNNER_SET_CAPABILITIES_FILE:
                os.environ.pop("OPCUA_CAPABILITIES_FILE", None)
            global _server_tmp_dir
            if _server_tmp_dir:
                _safe_rmtree(_server_tmp_dir)
            _server_tmp_dir = None

    _divider()
    for r in results:
        r.print_line()

    passed = sum(1 for r in results if r.ok and not r.skipped and not r.warn)
    warned = sum(1 for r in results if r.warn and not r.skipped)
    failed = sum(1 for r in results if not r.ok and not r.skipped and not r.warn)
    skipped = sum(1 for r in results if r.skipped)
    any_failed = failed > 0

    excel_result = _maybe_generate_excel(
        args.excel,
        tests_passed=not any_failed,
        explicit_junit_xml=args.junit_xml,
        excel_out=args.excel_out,
    )
    excel_result.print_line()

    _divider()

    elapsed = time.monotonic() - t_start
    overall = _c(_ANSI_RED, "FAIL") if any_failed else _c(_ANSI_GREEN, "PASS")
    _log(
        f"  Result: {overall}  passed={passed}  warned={warned}  failed={failed}  skipped={skipped}  (elapsed: {elapsed:.1f}s)"
    )
    # Print skip-reason breakdown when phase 2 ran (live tests produce significant skip volume)
    if run_phase2:
        live_xml = Path(args.junit_xml) if args.junit_xml else _DEFAULT_JUNIT
        _print_skip_reason_summary(live_xml)
    _log(_c(_ANSI_CYAN, "═" * 52))
    _log("")

    _cleanup_caches(_HERE)
    return 1 if any_failed else 0


def _force_rmtree(path: Path) -> None:
    """Remove a directory tree, handling Windows read-only / locked files."""
    if _deletes_disabled():
        logger.info("[cleanup] Preserving directory because IJT_RUNNER_NO_DELETE=1: %s", path)
        return
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
    if _deletes_disabled():
        logger.info("[cleanup] Preserving caches because IJT_RUNNER_NO_DELETE=1")
        return
    _SKIP = {"node_modules", ".git", "test-results", "tmp"}  # tmp workspace is handled by _prepare_tmp_dir()
    _CACHE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov"}
    for dirpath, dirs, files in os.walk(root, topdown=True):
        dirs[:] = [d for d in dirs if d not in _SKIP and not d.startswith(".venv") and not d.startswith("venv")]
        for d in list(dirs):
            if d in _CACHE_DIRS or d.startswith("pytest-cache-files-") or d.startswith(".dotnet"):
                _force_rmtree(Path(dirpath) / d)
                dirs.remove(d)
        for f in files:
            if f == ".coverage" or f.startswith(".coverage.") or f.endswith(".pyc"):
                with contextlib.suppress(OSError):
                    _safe_unlink(Path(dirpath) / f)


if __name__ == "__main__":
    sys.exit(main())
