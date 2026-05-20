import os
import sys

# Suppress __pycache__ / .pyc generation for all child processes (matches Docker behavior)
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
import argparse
import atexit
import contextlib
import json
import logging
import re
import shlex
import shutil
import signal
import socket
import subprocess
import time
import webbrowser
import zipfile
from pathlib import Path
from typing import IO, Any

# Add src/ to path so "from python.xxx import" works regardless of cwd
sys.path.insert(0, str(Path(__file__).parent / "src"))
from python.network_utils import endpoint_reachable, parse_endpoint_host_port

PROJECT_DIR = Path(__file__).resolve().parent
STATE_DIR = PROJECT_DIR / ".state"
LOGS_DIR = PROJECT_DIR / "logs"
RESULTS_LOG_DIR = LOGS_DIR / "results"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _detect_repo_root(start_dir: Path) -> Path:
    """
    Find repository root by looking for both OPC_UA_Clients and OPC_UA_Servers.
    Falls back to start_dir when running from standalone/container layouts.
    """
    for candidate in [start_dir] + list(start_dir.parents):
        if (candidate / "OPC_UA_Clients").exists() and (candidate / "OPC_UA_Servers").exists():
            return candidate
    return start_dir


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOGS_DIR / "setup.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Paths
# ---------------------------------------------------------------------------
IS_DOCKER = os.getenv("IS_DOCKER") == "true"
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
_ENV_IS_PRE_ISOLATED = IS_DOCKER or IS_GITHUB_ACTIONS
IS_WSL = bool(os.getenv("WSL_DISTRO_NAME")) or (
    os.path.exists("/proc/version")
    and "microsoft" in Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
)
# Venv naming convention:
#   .venv          — runtime launch (this script, Windows/Linux/macOS/WSL non-Docker)
#   .venv_test     — test runner (run_all_tests.py, full dev deps)
#   .venv_ci       — local CI-mode test runner (run_all_tests.py --ci-mode)
#   /opt/ijt_venv  — Docker container (avoids Windows bind-mount conflicts)
# GitHub Actions uses the runner-provided Python environment.
# Note: .venv_wsl was previously documented as a separate WSL env but bootstrap_wsl.sh
# calls this script, so WSL non-Docker also ends up using .venv (same as all other hosts).
VENV_DIR = Path("/opt/ijt_venv") if IS_DOCKER else Path(".venv")
SETUP_TIMESTAMP_FILE = STATE_DIR / "setup_timestamp"
IS_WINDOWS = os.name == "nt"
REPO_ROOT = _detect_repo_root(PROJECT_DIR)
PYTHON_CONSTRAINTS = REPO_ROOT / "constraints.txt"
SIMULATOR_DIR = REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator"
SIMULATOR_ZIP = REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator.zip"
SIMULATOR_EXE_NAME = "opcua_ijt_demo_application.exe"
SETUP_LOCK_FILE = STATE_DIR / "setup.lock"
RUNTIME_STATE_FILE = STATE_DIR / "runtime_processes.json"

# Legacy venv directory names that pre-date the .venv / .venv_test / .venv_ci convention.
_STALE_VENV_NAMES: tuple[str, ...] = ("venv", "venv_test", "env", "ENV", ".venv_backup")


def _pip_constraint_args() -> list[str]:
    return ["-c", str(PYTHON_CONSTRAINTS)] if PYTHON_CONSTRAINTS.exists() else []


def _remove_stale_venvs(project_dir: Path) -> None:
    """Delete any legacy virtual-environment directories under *project_dir*.

    Only ``.venv``, ``.venv_test``, and ``.venv_ci`` are canonical on all hosts
    (including WSL).
    The Docker path ``/opt/ijt_venv`` is canonical only inside containers.
    Anything matching :data:`_STALE_VENV_NAMES` is obsolete and removed automatically so that
    fresh clones start from a known-clean state.
    """
    for name in _STALE_VENV_NAMES:
        stale = project_dir / name
        if stale.is_dir():
            log.info("[cleanup] Removing stale virtual environment: %s", stale)
            shutil.rmtree(stale, ignore_errors=True)


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


def _cleanup_local_project_artifacts(project_dir: Path) -> None:
    """Remove safe transient cache artifacts under the local project only.

    This is intentionally narrow and never touches virtual environments,
    reports, logs, or runtime state folders.
    """
    skip_dirs = {"node_modules", ".git", "test-results", "logs", ".state", "tmp"}
    cache_dirs = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
    for dirpath, dirs, files in os.walk(project_dir, topdown=True):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not (d.startswith(".venv") or d.startswith("venv"))]
        for d in list(dirs):
            if d in cache_dirs:
                _force_rmtree(Path(dirpath) / d)
                dirs.remove(d)
        for f in files:
            if f == ".coverage" or f.startswith(".coverage.") or f.endswith(".pyc"):
                with contextlib.suppress(OSError):
                    (Path(dirpath) / f).unlink(missing_ok=True)
    # Clean transient pip temp dir created by venv_bootstrap
    state_tmp = project_dir / ".state" / "tmp"
    if state_tmp.exists():
        _force_rmtree(state_tmp)


def _run_command(cmd: list[str], check: bool = True, capture_output: bool = False):
    if capture_output:
        return subprocess.check_output(cmd, text=True).strip()
    if check:
        subprocess.check_call(cmd)
        return None
    return subprocess.run(cmd, check=False)


def _semver_tuple(ver: str):
    """
    Convert a version string like '24.11.0' or '20.11.1' to a comparable tuple (24, 11, 0).
    Non-digit parts are ignored; missing parts default to 0.
    """
    nums = [int(x) for x in re.findall(r"\d+", ver)]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _warn_if_untested_python(version_string: str | None = None) -> None:
    if not version_string:
        version_string = f"{sys.version_info[0]}.{sys.version_info[1]}"
    try:
        major, minor = map(int, version_string.split("."))
    except Exception:
        return None

    tested_max_minor_raw = os.getenv("PYTHON_TESTED_MAX_MINOR", "14").strip()
    try:
        tested_max_minor = int(tested_max_minor_raw)
    except Exception:
        log.warning(
            "Invalid PYTHON_TESTED_MAX_MINOR=%r. Expected integer (e.g. 14).",
            tested_max_minor_raw,
        )
        return None

    if major == 3 and minor > tested_max_minor:
        log.warning(
            "Python %s detected. This project officially tests up to 3.%s; continuing in compatibility mode.",
            version_string,
            tested_max_minor,
        )
    return None


def _warn_if_untested_node(version_string: str) -> None:
    nums = [int(x) for x in re.findall(r"\d+", version_string)]
    if not nums:
        return None
    major = nums[0]
    tested_max_major_raw = os.getenv("NODE_TESTED_MAX_MAJOR", "24").strip()
    try:
        tested_max_major = int(tested_max_major_raw)
    except Exception:
        log.warning(
            "Invalid NODE_TESTED_MAX_MAJOR=%r. Expected integer (e.g. 24).",
            tested_max_major_raw,
        )
        return None

    if major > tested_max_major:
        log.warning(
            "Node.js %s detected. This project officially tests up to major %s; continuing in compatibility mode.",
            version_string,
            tested_max_major,
        )
    return None


# ---------------------------------------------------------------------------
# Windows/Posix: Find newest Python & relaunch under it (future-proof)
# ---------------------------------------------------------------------------


def _list_pythons_windows():
    """
    Use 'py -0' to list installed Python versions and return a list of '3.X' strings.
    Example lines: ' -V:3.14 *        Python 3.14 (64-bit)' or ' -3.12  Python 3.12 (64-bit)'
    """
    try:
        out = subprocess.check_output(["py", "-0"], text=True, stderr=subprocess.STDOUT)
    except Exception as e:
        log.debug("py -0 failed: %s", e)
        return []
    vers = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("-V:") and not line.startswith("-"):
            continue
        token = line.split()[0]  # '-V:3.14' or '-3.12'
        v = token.replace("-V:", "").replace("-", "")
        if v.startswith("3.") and v.count(".") == 1:
            vers.append(v)
    return vers


def _find_latest_python_executable():
    """
    Return (cmd_list, version_string) for the newest Python 3.x on this system.
    - On Windows: ['py', '-3.16'], '3.16'
    - On POSIX:   ['python3.16'], '3.16' (falls back to python3)
    """
    if IS_WINDOWS:
        versions = _list_pythons_windows()
        candidates: list[tuple[tuple[int, int], list[str], str]] = []

        for version in versions:
            try:
                major, minor = map(int, version.split("."))
                candidates.append(((major, minor), ["py", f"-{version}"], version))
            except Exception:
                continue

        # Also include the currently running interpreter to avoid downgrading when
        # 'py -0' is stale/misconfigured compared to PATH python.
        current_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
        candidates.append(
            (
                (sys.version_info[0], sys.version_info[1]),
                [sys.executable],
                current_ver,
            )
        )

        if not candidates:
            log.error("No Python 3.x interpreter candidates found on this system.")
            sys.exit(1)

        _, cmd, version = max(candidates, key=lambda row: row[0])
        if cmd and cmd[0] == "py":
            try:
                major, minor = version.split(".")
                local_appdata = os.getenv("LOCALAPPDATA")
                if local_appdata:
                    direct_py = Path(local_appdata) / "Programs" / "Python" / f"Python{major}{minor}" / "python.exe"
                    if direct_py.exists():
                        return ([str(direct_py)], version)
            except Exception as exc:
                log.debug("Could not resolve direct python.exe via LOCALAPPDATA hint: %s", exc)
        return (cmd, version)
    else:
        # Probe newer to older (extend upper bound periodically, harmless if missing)
        for minor in range(20, 9, -1):  # 3.20 down to 3.10
            exe = f"python3.{minor}"
            try:
                subprocess.check_call(
                    [exe, "--version"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return ([exe], f"3.{minor}")
            except Exception:
                continue
        # Fallback: python3
        try:
            subprocess.check_call(
                ["python3", "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            out = subprocess.check_output(
                [
                    "python3",
                    "-c",
                    "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')",
                ],
                text=True,
            )
            v = out.strip()
            if not v.startswith("3."):
                raise RuntimeError("python3 isn't a Python 3 interpreter")
            return (["python3"], v)
        except Exception:
            log.error("Could not find a usable Python 3 interpreter on this system.")
            sys.exit(1)
    return None


def _relaunch_under_latest_python():
    """
    If current interpreter is not the newest available, re-exec the script under it,
    forwarding all arguments. This guarantees the rest of the script and the venv
    will use the newest Python version on the machine.
    """
    latest_cmd, latest_ver = _find_latest_python_executable()
    current_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
    if current_ver == latest_ver:
        log.info("Using latest Python %s", current_ver)
        return
    cmd = latest_cmd + [__file__] + sys.argv[1:]
    log.info(
        "Re-launching with Python %s: %s",
        latest_ver,
        " ".join(shlex.quote(c) for c in cmd),
    )
    os.execvp(cmd[0], cmd)


def _require_python_314_or_newer(version_string: str | None = None) -> None:
    if version_string:
        try:
            major, minor = map(int, version_string.split("."))
        except Exception:
            major, minor = sys.version_info[0], sys.version_info[1]
    else:
        major, minor = sys.version_info[0], sys.version_info[1]

    if (major, minor) < (3, 14):
        log.error(
            "Python 3.14 or newer is required. Current interpreter: %s.%s",
            major,
            minor,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Utility: Internet availability
# ---------------------------------------------------------------------------
def _check_internet(host="8.8.8.8", port=53, timeout=3):
    sock = None
    try:
        socket.setdefaulttimeout(timeout)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        return True
    except socket.error:
        return False
    finally:
        if sock:
            sock.close()


def _is_port_in_use(host: str, port: int, timeout: float = 0.5) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if IS_WINDOWS:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                check=False,
                capture_output=True,
                text=True,
            )
            output = (result.stdout or "").strip()
            if not output:
                return False
            if "No tasks are running" in output:
                return False
            return output.startswith('"')
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_runtime_state() -> dict:
    if not RUNTIME_STATE_FILE.exists():
        return {}
    try:
        return json.loads(RUNTIME_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_runtime_state(state: dict) -> None:
    RUNTIME_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _clear_runtime_state() -> None:
    if RUNTIME_STATE_FILE.exists():
        RUNTIME_STATE_FILE.unlink()


def _record_runtime_processes(frontend_pid: int | None, backend_pid: int | None) -> None:
    if frontend_pid is None and backend_pid is None:
        return
    state = {
        "created_at": time.time(),
        "frontend_pid": frontend_pid,
        "backend_pid": backend_pid,
    }
    _write_runtime_state(state)


def _collect_managed_processes() -> list[tuple[str, int]]:
    state = _read_runtime_state()
    managed: list[tuple[str, int]] = []
    for key, label in (("frontend_pid", "frontend"), ("backend_pid", "backend")):
        raw = state.get(key)
        try:
            pid = int(raw or 0)
        except (ValueError, TypeError):  # fmt: skip
            continue
        if pid <= 0:
            continue
        if _pid_is_running(pid):
            managed.append((label, pid))
    return managed


def _stop_managed_processes(timeout_sec: float = 8.0) -> None:
    managed = _collect_managed_processes()
    if not managed:
        log.info("No managed frontend/backend processes are currently running.")
        _clear_runtime_state()
        return

    # Phase 1: graceful signal
    for label, pid in managed:
        try:
            if IS_WINDOWS:
                with contextlib.suppress(Exception):
                    os.kill(pid, signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            else:
                os.kill(pid, signal.SIGTERM)
            log.info("Requested graceful stop for %s process (pid=%s).", label, pid)
        except Exception as e:
            log.warning("Failed graceful stop request for %s process (pid=%s): %s", label, pid, e)

    deadline = time.time() + max(1.0, timeout_sec)
    while time.time() < deadline:
        if not _collect_managed_processes():
            break
        time.sleep(0.2)

    # Phase 2: soft taskkill on Windows for anything still alive.
    leftovers = _collect_managed_processes()
    if IS_WINDOWS and leftovers:
        for label, pid in leftovers:
            with contextlib.suppress(Exception):
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                log.info("Requested soft taskkill for %s process (pid=%s).", label, pid)
        deadline = time.time() + 4.0
        while time.time() < deadline:
            if not _collect_managed_processes():
                break
            time.sleep(0.2)

    # Phase 3: force kill as last resort.
    leftovers = _collect_managed_processes()
    if leftovers:
        for label, pid in leftovers:
            try:
                if IS_WINDOWS:
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    os.kill(pid, getattr(signal, "SIGKILL", signal.SIGTERM))
                log.warning("Forced stop for %s process (pid=%s).", label, pid)
            except Exception as e:
                log.warning("Failed forced stop for %s process (pid=%s): %s", label, pid, e)
        time.sleep(0.4)
        leftovers = _collect_managed_processes()
        for label, pid in leftovers:
            log.warning("%s process (pid=%s) is still running.", label, pid)
    else:
        _clear_runtime_state()


def _runtime_status() -> dict[str, bool]:
    state = _read_runtime_state()
    frontend_pid = int(state.get("frontend_pid") or 0)
    backend_pid = int(state.get("backend_pid") or 0)
    return {
        "frontend": _pid_is_running(frontend_pid),
        "backend": _pid_is_running(backend_pid),
    }


def _should_block_foreground(frontend_proc, backend_proc) -> bool:
    if frontend_proc is not None or backend_proc is not None:
        return True
    managed = _runtime_status()
    return managed["frontend"] or managed["backend"]


class _SetupLock:
    def __init__(self, path: Path):
        self.path = path
        self._fh: IO[str] | None = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a+", encoding="utf-8")
        try:
            if IS_WINDOWS:
                import msvcrt  # type: ignore[import]

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
            else:
                import fcntl  # type: ignore[import]

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
            self._fh.seek(0)
            self._fh.truncate()
            self._fh.write(str(os.getpid()))
            self._fh.flush()
            atexit.register(self.release)
            return True
        except Exception:
            self.release()
            return False

    def release(self) -> None:
        if not self._fh:
            return
        try:
            if IS_WINDOWS:
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]
        except Exception as exc:
            log.debug("Failed to release setup lock cleanly: %s", exc)
        try:
            self._fh.close()
        finally:
            self._fh = None


def _is_websocket_server_ready(port: int, timeout: float = 1.5) -> bool:
    python = _get_python_path()
    if not python.exists():
        return _is_port_in_use("127.0.0.1", port, timeout=timeout)

    probe_code = (
        "import asyncio, sys\n"
        "import websockets\n"
        "async def main():\n"
        "  try:\n"
        f"    async with websockets.connect('ws://127.0.0.1:{port}', open_timeout={timeout}, close_timeout=0.3):\n"
        "      return 0\n"
        "  except Exception:\n"
        "      return 1\n"
        "raise SystemExit(asyncio.run(main()))\n"
    )
    try:
        completed = subprocess.run(
            [str(python), "-c", probe_code],
            check=False,
            capture_output=True,
            text=True,
        )
        return completed.returncode == 0
    except Exception:
        return _is_port_in_use("127.0.0.1", port, timeout=timeout)


def _parse_endpoint_host_port(endpoint: str) -> tuple[str, int]:
    return parse_endpoint_host_port(endpoint)


def _is_endpoint_reachable(endpoint: str, timeout: float = 1.0) -> bool:
    return endpoint_reachable(endpoint, timeout=timeout)


def _env_float(name: str, default: float, minimum: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError:
        log.warning("Invalid %s=%r. Falling back to %.2f.", name, raw, default)
        value = default
    return max(minimum, value)


def _wait_for_endpoint_ready(
    endpoint: str,
    timeout_seconds: float = 45.0,
    poll_interval: float = 0.5,
) -> bool:
    deadline = time.time() + max(1.0, timeout_seconds)
    while time.time() < deadline:
        if _is_endpoint_reachable(endpoint):
            return True
        time.sleep(max(0.1, poll_interval))
    return _is_endpoint_reachable(endpoint)


def _extract_simulator_zip_if_needed() -> None:
    if not SIMULATOR_ZIP.exists():
        return
    if SIMULATOR_DIR.exists():
        zip_mtime = SIMULATOR_ZIP.stat().st_mtime
        dir_mtime = SIMULATOR_DIR.stat().st_mtime
        if zip_mtime <= dir_mtime:
            return  # extracted folder is already up-to-date
        log.info(
            "Newer simulator ZIP detected (zip mtime=%.0f > dir mtime=%.0f). Removing old folder: %s",
            zip_mtime,
            dir_mtime,
            SIMULATOR_DIR,
        )
        shutil.rmtree(SIMULATOR_DIR)
    try:
        log.info("Extracting OPC UA simulator from ZIP: %s", SIMULATOR_ZIP)
        with zipfile.ZipFile(SIMULATOR_ZIP, "r") as zf:
            zf.extractall(SIMULATOR_ZIP.parent)
    except Exception as e:
        log.warning("Failed to extract simulator ZIP '%s': %s", SIMULATOR_ZIP, e)


def _find_simulator_executable() -> Path | None:
    if not SIMULATOR_DIR.exists():
        return None
    direct = SIMULATOR_DIR / SIMULATOR_EXE_NAME
    if direct.exists():
        return direct
    matches = list(SIMULATOR_DIR.rglob(SIMULATOR_EXE_NAME))
    return matches[0] if matches else None


def _ensure_opc_server_running(endpoint: str, *, allow_launch: bool, context: str) -> bool:
    # Source of truth is OPC UA endpoint connectivity, not whether a terminal/process exists.
    if _is_endpoint_reachable(endpoint):
        return True

    if IS_WSL:
        host, port = _parse_endpoint_host_port(endpoint)
        log.warning(
            "%s: OPC UA endpoint %s is unreachable from WSL. "
            "WSL mode skips auto-launch of the Windows simulator. "
            "Start the simulator manually on Windows and set OPCUA_TEST_ENDPOINT "
            "to a Windows-reachable host (not '%s' if needed), e.g. opc.tcp://<windows-host>:%s.",
            context,
            endpoint,
            host,
            port,
        )
        return False

    if allow_launch and not IS_DOCKER:
        _extract_simulator_zip_if_needed()
        exe = _find_simulator_executable()
        if exe:
            try:
                log.info(
                    "OPC UA endpoint %s is unreachable. Launching simulator binary: %s",
                    endpoint,
                    exe,
                )
                popen_kwargs: "dict[str, Any]" = {"cwd": str(exe.parent)}
                if IS_WINDOWS:
                    popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10)
                subprocess.Popen([str(exe)], **popen_kwargs)
                startup_timeout = _env_float("OPCUA_STARTUP_TIMEOUT_SEC", 45.0, 1.0)
                startup_poll = _env_float("OPCUA_STARTUP_POLL_SEC", 0.5, 0.1)
                if _wait_for_endpoint_ready(
                    endpoint,
                    timeout_seconds=startup_timeout,
                    poll_interval=startup_poll,
                ):
                    log.info("OPC UA endpoint became reachable: %s", endpoint)
                    return True
                log.warning(
                    "Simulator process launched but endpoint %s was not reachable after %.1fs.",
                    endpoint,
                    startup_timeout,
                )
            except Exception as e:
                log.warning("Failed to launch OPC UA simulator '%s': %s", exe, e)
    elif allow_launch and IS_DOCKER:
        log.info("Docker mode detected (IS_DOCKER=true). Skipping local OPC UA simulator launch.")

    startup_timeout = _env_float("OPCUA_STARTUP_TIMEOUT_SEC", 45.0, 1.0)
    startup_poll = _env_float("OPCUA_STARTUP_POLL_SEC", 0.5, 0.1)
    if _wait_for_endpoint_ready(
        endpoint,
        timeout_seconds=startup_timeout,
        poll_interval=startup_poll,
    ):
        return True

    log.warning(
        "%s: No OPC UA server is running on %s. "
        "If your server is in a separate download/folder, start it manually before running tests.",
        context,
        endpoint,
    )
    return False


# ---------------------------------------------------------------------------
# Venv & Python paths
# ---------------------------------------------------------------------------
def _python_in_venv() -> Path:
    return VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def _pip_in_venv() -> Path:
    return VENV_DIR / ("Scripts/pip.exe" if IS_WINDOWS else "bin/pip")


def _get_python_path() -> Path:
    """
    In pre-isolated environments, use the provided Python.
    Otherwise use the local runtime venv Python.
    """
    if _ENV_IS_PRE_ISOLATED:
        return Path(sys.executable)
    return _python_in_venv()


# ---------------------------------------------------------------------------
# Node / npm / npx helpers
# ---------------------------------------------------------------------------
def _get_npm_path():
    return shutil.which("npm")


def _get_npx_path():
    return shutil.which("npx")


def _get_node_version():
    try:
        output = subprocess.check_output(["node", "-v"], text=True).strip()
        return output.lstrip("v")
    except Exception as e:
        log.error("Failed to get Node.js version: %s", e)
        return None


# ---------------------------------------------------------------------------
# Environment age / timestamp
# ---------------------------------------------------------------------------
def _get_environment_age_days():
    try:
        if VENV_DIR.exists():
            creation_time = os.path.getmtime(VENV_DIR)
            return (time.time() - creation_time) / (60 * 60 * 24)
    except Exception as e:
        log.warning("Could not determine environment age: %s", e)
    return None


def _get_last_setup_age_days():
    try:
        if SETUP_TIMESTAMP_FILE.exists():
            timestamp = float(SETUP_TIMESTAMP_FILE.read_text().strip())
            return (time.time() - timestamp) / (60 * 60 * 24)
    except Exception as e:
        log.warning("Could not read setup timestamp: %s", e)
    return None


def _update_setup_timestamp():
    try:
        SETUP_TIMESTAMP_FILE.write_text(str(time.time()))
    except Exception as e:
        log.warning("Could not update setup timestamp: %s", e)


def _resolve_python_executable(latest_cmd):
    """
    Resolve the absolute path to the interpreter behind latest_cmd.
    Example: latest_cmd == ["py", "-3.13"]  -> returns "C:\\...\\python.exe"
             latest_cmd == ["python3.16"]   -> returns "/usr/bin/python3.16"
    """
    try:
        exe = subprocess.check_output(latest_cmd + ["-c", "import sys; print(sys.executable)"], text=True).strip()
        if not exe:
            raise RuntimeError("Could not resolve target python executable.")
        return exe
    except Exception as e:
        log.error("Failed to resolve Python executable from %s: %s", " ".join(latest_cmd), e)
        sys.exit(1)
    return None


# ---------------------------------------------------------------------------
# Python: Create venv with newest interpreter
# ---------------------------------------------------------------------------
def _create_virtualenv(latest_cmd):
    """
    Create venv with the newest Python interpreter.
    - Resolves the real python.exe (or python3.x) behind 'latest_cmd'
    - Calls that interpreter directly for ' -m venv '
    - Gives clear guidance if creation fails (Store / broken association cases)
    """
    # Remove only the selected venv dir (in Docker this is /opt/ijt_venv, not your bind-mount)
    if VENV_DIR.exists():

        def _on_rm_error(func, path, _exc_info):
            try:
                os.chmod(path, 0o700)
                func(path)
            except Exception:
                # As a last resort, leave the file in place and continue
                log.warning("Could not remove %s; continuing.", path)

        try:
            shutil.rmtree(VENV_DIR, onerror=_on_rm_error)
        except Exception as e:
            log.warning("Non-fatal: could not fully remove %s: %s", VENV_DIR, e)

    target_exe = _resolve_python_executable(latest_cmd)
    log.info("Creating virtual environment with interpreter: %s", target_exe)

    try:
        subprocess.check_call([target_exe, "-m", "venv", "--without-pip", str(VENV_DIR)])
    except subprocess.CalledProcessError as e:
        log.error("Venv creation failed with %s", e)
        log.error(
            "This can happen on Windows when the 'py' launcher points to a Store/stub install "
            "or a conflicting association. Please install Python from python.org or the Microsoft Store, "
            "ensure the 'py' launcher is installed, and that 'py -0' lists your interpreter correctly."
        )
        log.error(
            "Tip: run  py -0  to list Pythons; the one with '*' is the default. "
            'You can also try:  py -3.13 -c "import sys; print(sys.executable)"'
        )
        sys.exit(1)

    # Ensure pip inside the new venv
    py = _python_in_venv()
    try:
        tmp_dir = STATE_DIR / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["TMPDIR"] = str(tmp_dir)
        env["TEMP"] = str(tmp_dir)
        env["TMP"] = str(tmp_dir)
        subprocess.check_call([str(py), "-m", "ensurepip", "--upgrade"], env=env)
    except Exception as e:
        log.warning("Failed to ensure pip in virtualenv via ensurepip: %s", e)
        subprocess.check_call([sys.executable, "-m", "pip", "--python", str(py), "install", "--upgrade", "pip"])


# ---------------------------------------------------------------------------
# Python: Install packages (stable-first asyncua with optional pre-release fallback)
# ---------------------------------------------------------------------------
def _install_python_packages():
    """
    Install from requirements.txt, then ensure asyncua in the configured range.
    Prefer stable builds first; if resolution fails (e.g. newest Python support lag),
    optionally retry with --pre.
    """
    python = _get_python_path()
    log.info("Using Python executable: %s", python)

    # Upgrade pip first
    subprocess.check_call([str(python), "-m", "pip", "install", "--upgrade", "pip"])

    req_file = Path("requirements.txt")
    if not req_file.exists():
        log.error("requirements.txt not found. Cannot continue.")
        sys.exit(1)

    # Install core from requirements (stable channel)
    log.info("Installing packages from requirements.txt (stable channel)...")
    subprocess.check_call(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--upgrade",
            *_pip_constraint_args(),
            "-r",
            str(req_file),
        ]
    )

    # Proactively upgrade crypto stack for asyncua (often required by newer wheels)
    # (The asyncua project lists cryptography / pyOpenSSL among dependencies.)
    # https://github.com/FreeOpcUa/opcua-asyncio/network/dependencies
    try:
        subprocess.check_call(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--upgrade",
                *_pip_constraint_args(),
                "cryptography",
                "pyOpenSSL",
            ]
        )
    except Exception as exc:
        log.debug("Optional crypto stack upgrade skipped: %s", exc)

    # asyncua is pinned in repo-root constraints.txt to upstream SHA 35a77c6b
    # (post-1.2b2; 2026-05-11). ASYNCUA_VERSION_SPEC is a deliberate operator
    # escape hatch for testing a future tagged release; when set, this final
    # asyncua install intentionally bypasses constraints so the override wins.
    asyncua_override = os.getenv("ASYNCUA_VERSION_SPEC")
    asyncua_spec = (asyncua_override or "asyncua").strip() or "asyncua"
    log.info("Installing asyncua (constraints pin or explicit ASYNCUA_VERSION_SPEC): %s", asyncua_spec)
    subprocess.check_call(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--upgrade",
            *([] if asyncua_override and asyncua_override.strip() else _pip_constraint_args()),
            asyncua_spec,
        ]
    )

    # Verify the installed asyncua satisfies the minimum version.
    try:
        installed = subprocess.check_output(
            [str(python), "-c", "import asyncua; print(asyncua.__version__)"],
            text=True,
        ).strip()
        log.info("asyncua installed version: %s", installed)
        from packaging.version import Version

        if Version(installed) < Version("1.2b2"):
            log.error(
                "asyncua %s is too old for Python 3.14. Minimum required: 1.2b2. "
                "Run with --force_full to trigger a clean reinstall.",
                installed,
            )
            sys.exit(1)
    except Exception as exc:
        log.warning("Could not verify asyncua version: %s", exc)


# ---------------------------------------------------------------------------
# Node / npm / npx: checks & install
# ---------------------------------------------------------------------------
def _create_nodeenv():
    """
    Ensure Node.js (node, npm, npx) are present and at/above the required version.
    JS toolchain remains global (unchanged from your workflow).
    """
    log.info("Checking Node.js installation...")
    node_path = shutil.which("node")
    npm_path = shutil.which("npm")
    npx_path = shutil.which("npx")

    missing = []
    if not node_path:
        missing.append("node")
    if not npm_path:
        missing.append("npm")
    if not npx_path:
        missing.append("npx")
    if missing:
        log.error("Missing global tools: %s", ", ".join(missing))
        log.error("Please install Node.js with npm and npx, and ensure they are in your PATH.")
        sys.exit(1)

    # All three are non-None: sys.exit(1) above if any were missing.
    assert node_path is not None and npm_path is not None and npx_path is not None

    # quick smoke checks
    try:
        subprocess.check_call([node_path, "-v"])
        subprocess.check_call([npm_path, "-v"])
        subprocess.check_call([npx_path, "--version"])
    except Exception as e:
        log.error("Node.js tools aren't functioning correctly: %s", e)
        sys.exit(1)

    node_ver = _get_node_version() or "0.0.0"
    required_node_ver = os.getenv("NODE_VERSION", "24.0.0")

    if _semver_tuple(node_ver) < _semver_tuple(required_node_ver):
        log.error(
            "Node.js version %s is older than required %s. Please upgrade Node.js.",
            node_ver,
            required_node_ver,
        )
        sys.exit(1)

    _warn_if_untested_node(node_ver)
    log.info("Node.js %s OK (>= %s). npm and npx found.", node_ver, required_node_ver)
    log.info("Using node: %s", node_path)
    log.info("Using npm:  %s", npm_path)
    log.info("Using npx:  %s", npx_path)


def _validate_package_json():
    package_json_path = Path("package.json")
    if not package_json_path.exists():
        log.error("package.json not found.")
        sys.exit(1)
    try:
        # utf-8-sig tolerates accidental BOM and keeps parsing stable on Windows editors.
        with open(package_json_path, "r", encoding="utf-8-sig") as f:
            json.load(f)
        log.info("package.json is valid.")
    except json.JSONDecodeError as e:
        log.error("Invalid package.json: %s", e)
        sys.exit(1)


def _install_js_packages(dev_mode: bool = False):
    npm = _get_npm_path()
    if not npm:
        log.error("npm not found. Node.js environment setup failed.")
        sys.exit(1)

    _validate_package_json()

    # Set HUSKY=0 for end users so the prepare script does not install git hooks.
    # Contributors pass --dev to opt in to hook installation.
    env = os.environ.copy()
    if not dev_mode:
        env["HUSKY"] = "0"
        log.info("Installing JavaScript packages (HUSKY=0 — git hooks skipped for end users)...")
    else:
        log.info("Installing JavaScript packages with git hooks (contributor mode)...")

    try:
        if Path("package-lock.json").exists():
            log.info("Found package-lock.json. Running 'npm ci'...")
            subprocess.check_call([str(npm), "ci"], env=env)
        else:
            log.warning("package-lock.json not found. Running 'npm install' with --legacy-peer-deps...")
            subprocess.check_call([str(npm), "install", "--legacy-peer-deps"], env=env)
    except subprocess.CalledProcessError as e:
        log.error("JavaScript package installation failed. Command failed: %s", e.cmd)
        sys.exit(1)

    # Log a couple of versions to assist troubleshooting
    try:
        eslint_version = subprocess.check_output([str(npm), "list", "eslint", "--depth=0"], text=True)
        neostandard_version = subprocess.check_output([str(npm), "list", "neostandard", "--depth=0"], text=True)
        log.info("Installed ESLint version:\n%s", eslint_version)
        log.info("Installed neostandard version:\n%s", neostandard_version)
    except subprocess.CalledProcessError as e:
        log.warning("Failed to retrieve installed JS package versions: %s", e)


# ---------------------------------------------------------------------------
# Web server & Python process runner
# ---------------------------------------------------------------------------
def _start_server(args):
    npx = _get_npx_path()
    if not npx:
        log.error("npx not found. Please ensure Node.js is installed.")
        sys.exit(1)

    http_port = os.getenv("HTTP_PORT", "3000")
    try:
        port_num = int(http_port)
    except ValueError:
        log.error("Invalid HTTP_PORT '%s'. Falling back to 3000.", http_port)
        port_num = 3000
        http_port = "3000"

    if _is_port_in_use("127.0.0.1", port_num):
        log.info(
            "HTTP port %s is already in use. Skipping frontend start (assumed already running).",
            http_port,
        )
        return None

    browser_host = os.getenv("WS_HOST") or socket.gethostbyname(socket.gethostname())
    browser_url = f"http://{browser_host}:{http_port}"

    log.info("Starting local server on %s ...", browser_url)

    try:
        cmd = [
            str(npx),
            "--yes",
            "serve",
            "--listen",
            f"tcp://0.0.0.0:{http_port}",
            "--no-clipboard",
            "--no-request-logging",
        ]
        if args.silent:
            cmd.append("--no-request-logging")

        popen_kwargs = {}
        if IS_WINDOWS:
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(cmd, **popen_kwargs)

        if os.getenv("IS_DOCKER") != "true":
            webbrowser.open(browser_url)
        else:
            log.info("Skipping browser launch inside Docker.")
        return proc
    except Exception as e:
        log.error("Failed to start server or open browser: %s", e)
        return None


def _run_index():
    python = _get_python_path()
    try:
        ws_port = int(os.getenv("WS_PORT", "8001"))
    except ValueError:
        log.error("Invalid WS_PORT value. Falling back to 8001.")
        ws_port = 8001

    if _is_websocket_server_ready(ws_port):
        log.info(
            "WebSocket port %s is already in use. Skipping backend start (assumed already running).",
            ws_port,
        )
        return None

    if Path("index.py").exists():
        try:
            popen_kwargs = {}
            if IS_WINDOWS:
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            return subprocess.Popen([str(python), "index.py"], **popen_kwargs)
        except Exception as e:
            log.error("Failed to run index.py: %s", e)
    else:
        log.warning("index.py not found.")
    return None


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        log.warning("python-dotenv is unavailable in controller interpreter; skipping .env load.")


def _run_tests_in_venv(integration: bool = False) -> None:
    controller_python = Path(sys.executable)
    test_script = Path("scripts") / "run_tests.py"
    if not test_script.exists():
        log.error("%s not found.", test_script)
        raise FileNotFoundError(str(test_script))

    cmd = [str(controller_python), str(test_script)]
    if integration:
        cmd.append("--integration")
    log.info(
        "Delegating test execution to autonomous test bootstrap script: %s",
        " ".join(cmd),
    )
    _run_command(cmd)


# ---------------------------------------------------------------------------
# .env template
# ---------------------------------------------------------------------------
def _create_env_template():
    if not Path(".env").exists():
        if Path(".env.example").exists():
            shutil.copy(".env.example", ".env")
            log.info(".env file created from .env.example.")
        else:
            with open(".env.example", "w", encoding="utf-8") as f:
                f.write("# Environment Configuration Example\n\n")
                f.write("# WebSocket Server Port\n")
                f.write("# Default: 8001\n")
                f.write("WS_PORT=8001\n")
            log.info(".env.example created.")


# ---------------------------------------------------------------------------
# Runtime readiness check (reuse your original aging logic)
# ---------------------------------------------------------------------------
def _is_runtime_ready():
    python = _get_python_path()
    npm = _get_npm_path()
    npx = _get_npx_path()

    if _ENV_IS_PRE_ISOLATED:
        # Docker and GitHub Actions provide the Python isolation boundary.
        venv_ok = True
    else:
        venv_ok = VENV_DIR.exists()

    if not (venv_ok and python.exists() and npm and npx):
        return False

    # Ensure runtime dependencies are present in the selected Python interpreter.
    _dep_check_cmd = (
        "import asyncua, websockets, dotenv, packaging, "
        "pytz, aiofiles; "
        "from packaging.version import Version; "
        "v = asyncua.__version__; "
        "ok = Version(v) >= Version('1.2b2'); "
        "raise SystemExit(0) if ok else SystemExit('asyncua ' + v + ' is too old; need >= 1.2b2')"
    )
    try:
        _run_command([str(python), "-c", _dep_check_cmd])
    except Exception:
        log.info(
            "Runtime dependency check failed in %s. Triggering full setup.",
            python,
        )
        return False

    env_max_age = int(os.getenv("ENV_MAX_AGE_DAYS", "14"))
    age_days = _get_last_setup_age_days()
    if age_days is None:
        age_days = _get_environment_age_days()

    if age_days is not None:
        log.info(
            "Environment last set up %d days ago. Will refresh after %d days.",
            int(age_days),
            env_max_age,
        )
        if age_days > env_max_age:
            log.info(
                "Environment is %d days old (threshold: %d). Triggering full setup.",
                int(age_days),
                env_max_age,
            )
            return False
    return True


# ---------------------------------------------------------------------------
# WSL OS-level bootstrap
# ---------------------------------------------------------------------------


def _run_cmd(args: list[str], *, check: bool = True) -> int:
    """Run a system command, stream output live, and return the exit code.

    Raises subprocess.CalledProcessError when check=True and the command fails,
    mirroring ``set -e`` behaviour from the original bootstrap_wsl.sh.
    """
    log.info("$ %s", " ".join(args))
    result = subprocess.run(args, check=check)  # noqa: S603
    return result.returncode


def _bootstrap_disable_puppet_repo() -> None:
    """Comment out Puppet apt repo entries whose key has expired (if present)."""
    import glob as _glob
    import re as _re

    _puppet_repo_re = _re.compile(r"https?://apt\.puppet\.com(?:/|$)")

    candidate_files = ["/etc/apt/sources.list"] + _glob.glob("/etc/apt/sources.list.d/*.list")
    for path in candidate_files:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "apt.puppet.com" not in text:
            continue
        log.info("Disabling Puppet apt repo entries in %s", path)
        lines = []
        for line in text.splitlines():
            if line.startswith("deb ") and _puppet_repo_re.search(line):
                lines.append(f"# {line}")
            else:
                lines.append(line)
        subprocess.run(  # noqa: S603
            ["sudo", "tee", path],
            input="\n".join(lines) + "\n",
            text=True,
            check=True,
        )


def _bootstrap_fix_system_python() -> None:
    """Restore /usr/bin/python3 → python3.12 so apt tooling works correctly.

    WSL images sometimes have python3 pointing at a newer interpreter that
    lacks the ``apt_pkg`` C extension — breaking ``apt-get``.
    """
    py312 = Path("/usr/bin/python3.12")
    if not py312.exists():
        return
    try:
        current = Path("/usr/bin/python3").resolve()
    except OSError:
        current = Path()
    if current != py312:
        log.info("Restoring /usr/bin/python3 → python3.12 for apt tooling.")
        _run_cmd(["sudo", "ln", "-sf", str(py312), "/usr/bin/python3"])


def _bootstrap_install_base_packages() -> None:
    log.info("Updating apt package index.")
    _run_cmd(["sudo", "apt-get", "update", "-y"])
    log.info("Installing base packages.")
    _run_cmd(
        [
            "sudo",
            "apt-get",
            "install",
            "-y",
            "software-properties-common",
            "curl",
            "ca-certificates",
            "build-essential",
            "git",
            "gnupg",
        ]
    )


def _bootstrap_ensure_deadsnakes() -> None:
    import glob as _glob

    sources = ["/etc/apt/sources.list"] + _glob.glob("/etc/apt/sources.list.d/*.list")
    already = any(
        "deadsnakes/ppa" in Path(p).read_text(encoding="utf-8", errors="ignore") for p in sources if Path(p).exists()
    )
    if not already:
        log.info("Adding deadsnakes PPA.")
        _run_cmd(["sudo", "add-apt-repository", "-y", "ppa:deadsnakes/ppa"])


def _bootstrap_install_python_314() -> None:
    log.info("Installing Python 3.14 toolchain.")
    _run_cmd(["sudo", "apt-get", "update", "-y"])
    _run_cmd(
        [
            "sudo",
            "apt-get",
            "install",
            "-y",
            "python3.14",
            "python3.14-venv",
            "python3.14-dev",
            "python3-apt",
            "command-not-found",
        ]
    )


def _bootstrap_install_node_24() -> None:
    log.info("Installing Node.js 24.x via NodeSource.")
    # Fetch and run the NodeSource setup script without shell piping.
    setup_script = subprocess.check_output(
        ["curl", "-fsSL", "https://deb.nodesource.com/setup_24.x"],
        text=True,
    )
    subprocess.run(  # noqa: S603
        ["sudo", "-E", "bash", "-"],
        input=setup_script,
        text=True,
        check=True,
    )
    _run_cmd(["sudo", "apt-get", "install", "-y", "nodejs"])


def _bootstrap_verify_runtime() -> None:
    log.info("Verifying installed runtime versions.")
    for cmd in (
        ["python3", "--version"],
        ["python3", "-c", "import apt_pkg; print('apt_pkg OK')"],
        ["python3.14", "--version"],
        ["node", "-v"],
        ["npm", "-v"],
        ["npx", "--version"],
    ):
        _run_cmd(cmd, check=False)


def _bootstrap_print_next_steps(project_dir: Path) -> None:
    print(f"""
Completed WSL bootstrap.

Next steps:
  1. cd "{project_dir}"
  2. python3 setup_project.py
  3. python3 run_all_tests.py
  4. python3 scripts/run_regression.py
  5. python3 scripts/run_cross_client_regression.py

Optional (run project setup automatically):
  python3 setup_project.py --bootstrap-wsl --run-project-setup
""")


def wsl_bootstrap(project_dir: Path, *, run_project_setup: bool = False) -> None:
    """Replicate bootstrap_wsl.sh OS-provisioning steps in Python.

    Installs system-level dependencies (Python 3.14, Node 24, base apt packages)
    into the WSL Linux environment.  Requires ``sudo`` to be available.

    This is intentionally run with the *system* Python 3 that ships with WSL —
    not the project venv — because it is bootstrapping the tools needed to
    create that venv.
    """
    if sys.platform == "win32":
        log.error("--bootstrap-wsl must be run inside WSL (Linux), not Windows.")
        sys.exit(1)

    if not shutil.which("sudo"):
        log.error("sudo is required but not found in PATH.")
        sys.exit(1)

    _bootstrap_fix_system_python()
    _bootstrap_disable_puppet_repo()
    _bootstrap_install_base_packages()
    _bootstrap_ensure_deadsnakes()
    _bootstrap_install_python_314()
    _bootstrap_install_node_24()
    _bootstrap_verify_runtime()

    if run_project_setup:
        log.info("Running project setup in: %s", project_dir)
        _run_cmd(["python3", str(project_dir / "setup_project.py")])

    _bootstrap_print_next_steps(project_dir)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # Parse args first so --bootstrap-wsl can skip the Python version checks
    # (it is intentionally run under the system Python to install Python 3.14).
    parser = argparse.ArgumentParser(
        description="Setup and run the IJT Web Client environment.",
        epilog=(
            "Default behavior:\n"
            "If the environment is already set up (venv, npm, npx exist), the script runs in "
            "runtime-only mode. Use --force_full to perform full setup regardless."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--force_full", action="store_true", help="Force full setup")
    parser.add_argument(
        "--dev",
        action="store_true",
        help=(
            "Contributor mode: install git pre-commit hooks (husky + lint-staged).\n"
            "Use this if you intend to make and commit changes to the project.\n"
            "End users who only run the Web Client should omit this flag."
        ),
    )
    parser.add_argument("--silent", action="store_true", help="Show only warnings/errors")
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run pytest from the project venv after setup/runtime checks.",
    )
    parser.add_argument(
        "--integration-tests",
        action="store_true",
        help="Run integration pytest marker (requires OPCUA_TEST_ENDPOINT).",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop managed frontend/backend processes started by setup_project.py.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show runtime status for managed frontend/backend processes and exit.",
    )
    parser.add_argument(
        "--detach",
        action="store_true",
        help="Run setup launcher in detached mode (do not block terminal).",
    )
    parser.add_argument(
        "--bootstrap-wsl",
        action="store_true",
        help=(
            "WSL OS bootstrap mode: install system-level dependencies\n"
            "(Python 3.14, Node 24, apt packages) into the WSL Linux environment.\n"
            "Requires sudo. Run under system Python 3, not the project venv.\n"
            "Equivalent to: bash scripts/bootstrap_wsl.sh"
        ),
    )
    parser.add_argument(
        "--run-project-setup",
        action="store_true",
        help="After --bootstrap-wsl, also run setup_project.py to create the venv.",
    )
    args = parser.parse_args()

    # --bootstrap-wsl runs under system Python (before 3.14 is installed),
    # so skip the version gate and relaunch entirely.
    if args.bootstrap_wsl:
        wsl_bootstrap(PROJECT_DIR, run_project_setup=args.run_project_setup)
        return

    # Normal operation: ensure newest Python and 3.14+ requirement.
    _relaunch_under_latest_python()
    _require_python_314_or_newer()
    _warn_if_untested_python()

    # Remove any stale legacy venv directories left from previous naming conventions.
    _remove_stale_venvs(PROJECT_DIR)
    _cleanup_local_project_artifacts(PROJECT_DIR)

    if args.stop:
        _stop_managed_processes()
        return
    if args.status:
        status = _runtime_status()
        log.info("Managed frontend running: %s", status["frontend"])
        log.info("Managed backend running: %s", status["backend"])
        return

    setup_lock = _SetupLock(SETUP_LOCK_FILE)
    if not setup_lock.acquire():
        log.info("Another setup_project.py instance is already running. Exiting this invocation.")
        return

    # Fast path: if everything exists and isn't too old, just run.
    if not args.force_full and _is_runtime_ready():
        _load_dotenv_if_available()
        if args.run_tests or args.integration_tests:
            _run_tests_in_venv(integration=args.integration_tests)
            return
        endpoint = os.getenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40451")
        _ensure_opc_server_running(
            endpoint,
            allow_launch=True,
            context="Startup pre-check",
        )
        frontend_proc = _start_server(args)
        backend_proc = _run_index()
        _record_runtime_processes(
            frontend_proc.pid if frontend_proc else None,
            backend_proc.pid if backend_proc else None,
        )
        if not args.detach and _should_block_foreground(frontend_proc, backend_proc):
            log.info("Foreground mode active. Press Ctrl+C to stop managed processes.")
            try:
                while True:
                    time.sleep(1.0)
            except KeyboardInterrupt:
                log.info("Ctrl+C received. Stopping managed processes...")
                _stop_managed_processes()
        elif not args.detach:
            log.info("No managed processes were started by this run. Exiting.")
        return

    # Full setup path
    log.info("Starting full project setup...")
    if not _check_internet():
        log.error("No internet connection. Please connect to the internet and try again.")
        sys.exit(1)

    latest_cmd, latest_ver = _find_latest_python_executable()
    _require_python_314_or_newer(latest_ver)
    _warn_if_untested_python(latest_ver)
    log.info("Newest Python detected on this system: %s", latest_ver)

    if _ENV_IS_PRE_ISOLATED:
        log.info("Pre-isolated Python environment detected. Skipping local venv creation.")
    else:
        _create_virtualenv(latest_cmd)
    _install_python_packages()

    _create_nodeenv()
    _install_js_packages(dev_mode=args.dev)
    _create_env_template()

    _load_dotenv_if_available()
    if args.run_tests or args.integration_tests:
        _run_tests_in_venv(integration=args.integration_tests)
        return
    endpoint = os.getenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40451")
    _ensure_opc_server_running(
        endpoint,
        allow_launch=True,
        context="Startup pre-check",
    )
    frontend_proc = _start_server(args)
    backend_proc = _run_index()
    _record_runtime_processes(
        frontend_proc.pid if frontend_proc else None,
        backend_proc.pid if backend_proc else None,
    )
    if not args.detach and _should_block_foreground(frontend_proc, backend_proc):
        log.info("Foreground mode active. Press Ctrl+C to stop managed processes.")
        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            log.info("Ctrl+C received. Stopping managed processes...")
            _stop_managed_processes()
    elif not args.detach:
        log.info("No managed processes were started by this run. Exiting.")
    _update_setup_timestamp()
    log.info("Setup complete.")


if __name__ == "__main__":
    main()
