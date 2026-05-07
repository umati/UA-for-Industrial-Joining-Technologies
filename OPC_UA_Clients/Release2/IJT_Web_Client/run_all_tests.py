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
  Live OPC UA   — if server reachable at OPCUA_TEST_ENDPOINT  (default: opc.tcp://localhost:40463)
  Playwright E2E — if WebSocket backend reachable at WS_TEST_URL (default: ws://localhost:8001)

Force flags (override auto-detection):
  --integration  force live OPC UA stage even if server unreachable
  --e2e          force Playwright E2E stage even if WS backend unreachable
  --all          force every optional stage
  --docker-only  run only Docker smoke
  --skip-docker  do not run Docker smoke
  --python-opcua-only          root-runner target: direct OPC UA live tests
  --python-backend-only        root-runner target: WebSocket backend tests
  --python-lifecycle-only      root-runner target: WebSocket lifecycle tests
  --playwright-smoke-only      root-runner target: browser smoke tests
  --playwright-features-only   root-runner target: browser feature specs
  --playwright-regression-only root-runner target: browser regression spec

Environment variables (all optional):
  OPCUA_TEST_ENDPOINT   default: opc.tcp://localhost:40463
  WS_TEST_URL           default: ws://localhost:8001
  UI_TEST_BASE_URL      default: http://127.0.0.1:3000
  IJT_PLAYWRIGHT_FEATURE_WORKERS
                         feature-suite Playwright worker count (default: 4)
  IJT_DOCKER_TIMEOUT    seconds to wait for Docker HTTP readiness (default: 90)
  IJT_DOCKER_BUILD_TIMEOUT
                         seconds to wait for Docker image build (default: 1200)
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
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

# Ensure stdout/stderr use UTF-8 on Windows (cp1252 can't encode box-drawing chars)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

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
_NPM_CACHE = _TMP_DIR / "npm-cache"
_PIP_CACHE = _TMP_DIR / "pip-cache"
_STATE_DIR = ROOT / ".state"
_TIMING_HISTORY = _STATE_DIR / "timing-history.jsonl"
_REQUIREMENTS = ROOT / "requirements.txt"
_REQUIREMENTS_DEV = ROOT / "requirements-dev.txt"
_NPM_INSTALL_FLAGS = ["--legacy-peer-deps", "--no-audit", "--no-fund"]
# Minimum smoke-import contract for focused live/browser targets. Keep this
# aligned with requirements.txt and requirements-dev.txt when target deps change.
_PYTHON_TARGET_REQUIRED_MODULES = (
    "pytest",
    "pytest_asyncio",
    "pytest_timeout",
    "asyncua",
    "websockets",
    "dotenv",
    "aiofiles",
    "pytz",
)
# Minimum local Playwright contract for focused browser targets. Keep this
# aligned with package.json/package-lock.json when Playwright deps change.
_PLAYWRIGHT_REQUIRED_PACKAGES = ("@playwright/test", "playwright")
_PLAYWRIGHT_REQUIRED_BINS = ("playwright",)


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


_RESULTS_DIR = _path_from_env("IJT_WEB_TEST_RESULTS_DIR", ROOT / "test-results")
_OPCUA_PRESTARTED_PORT_ENV = "IJT_OPCUA_PRESTARTED_PORT"


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
    except (AttributeError, OSError):  # fmt: skip
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


def _subprocess_env(env: dict | None = None) -> dict:
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    _NPM_CACHE.mkdir(parents=True, exist_ok=True)
    run_env.setdefault("npm_config_cache", str(_NPM_CACHE))
    run_env.setdefault("npm_config_update_notifier", "false")
    return run_env


def _npm_install_args(npm: str) -> list[str]:
    """Return deterministic install args for CI and developer-friendly args locally."""
    command = "ci" if IS_CI and (ROOT / "package-lock.json").exists() else "install"
    return [npm, command, *_NPM_INSTALL_FLAGS]


def _node_package_path(package: str) -> Path:
    if package.startswith("@"):
        scope, name = package.split("/", 1)
        return ROOT / "node_modules" / scope / name
    return ROOT / "node_modules" / package


def _node_bin_path(name: str) -> Path | None:
    bin_dir = ROOT / "node_modules" / ".bin"
    candidates = [f"{name}.cmd", f"{name}.exe", name] if IS_WINDOWS else [name]
    for candidate in candidates:
        path = bin_dir / candidate
        if path.exists():
            return path
    return None


def _missing_node_requirements(
    *,
    packages: tuple[str, ...] = (),
    bins: tuple[str, ...] = (),
) -> list[str]:
    missing = [f"package:{package}" for package in packages if not _node_package_path(package).exists()]
    missing.extend(f"bin:{name}" for name in bins if _node_bin_path(name) is None)
    return missing


def _kill_proc_tree(pid: int) -> None:
    """Kill *pid* and all its descendants.

    On Windows, ``taskkill /F /T`` also forces child processes to release
    inherited pipe handles — preventing the communicate() deadlock where
    grandchild processes (e.g. semgrep workers) keep the parent's stdout pipe
    open after their parent has been killed, blocking the root runner's read.
    On Unix, SIGKILL is sent to the whole process group.
    """
    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        import signal

        with contextlib.suppress(ProcessLookupError):
            os.killpg(os.getpgid(pid), signal.SIGKILL)  # type: ignore[attr-defined]  # Unix only


def _run(
    cmd: list,
    *,
    cwd: Path = ROOT,
    label: str = "",
    env: dict | None = None,
    timeout: int | None = 300,
    timeout_message: str | None = None,
) -> int:
    display = label or " ".join(str(c) for c in cmd[:5])
    print(f"\n{_C.DIM}CMD: {display}{_C.RESET}")
    try:
        with subprocess.Popen(
            [str(c) for c in cmd],
            cwd=str(cwd),
            env=_subprocess_env(env),
            stdin=subprocess.DEVNULL,
        ) as proc:
            try:
                proc.communicate(timeout=timeout)
                return proc.returncode
            except subprocess.TimeoutExpired:
                _kill_proc_tree(proc.pid)
                proc.kill()
                with contextlib.suppress(subprocess.TimeoutExpired):
                    proc.communicate(timeout=5)
                message = timeout_message or f"[TIMEOUT] {display} exceeded {timeout}s"
                print(f"{_C.YELLOW}{message}{_C.RESET}")
                return -1
    except FileNotFoundError:
        print(f"{_C.YELLOW}[WARN] Command not found: {cmd[0]}{_C.RESET}")
        return 1


def _run_captured(
    cmd: list,
    *,
    cwd: Path = ROOT,
    label: str = "",
    env: dict | None = None,
    timeout: int | None = 300,
) -> tuple[int, str]:
    """Run *cmd* quietly and return (exit_code, combined_output)."""
    display = label or " ".join(str(c) for c in cmd[:5])
    print(f"\n{_C.DIM}CMD: {display}{_C.RESET}")
    try:
        with subprocess.Popen(
            [str(c) for c in cmd],
            cwd=str(cwd),
            env=_subprocess_env(env),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            stdin=subprocess.DEVNULL,
        ) as proc:
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
                return proc.returncode, (stdout or "") + (stderr or "")
            except subprocess.TimeoutExpired:
                _kill_proc_tree(proc.pid)
                proc.kill()
                with contextlib.suppress(subprocess.TimeoutExpired):
                    stdout, stderr = proc.communicate(timeout=5)
                return -1, f"[TIMEOUT] {display} exceeded {timeout}s"
    except FileNotFoundError:
        return 1, f"[WARN] Command not found: {cmd[0]}"


def _run_to_file(
    cmd: list,
    output_file: Path,
    *,
    cwd: Path = ROOT,
    label: str = "",
    env: dict | None = None,
    timeout: int | None = 300,
) -> int:
    """Run *cmd*, capture stdout to *output_file*, return exit code.

    Uses Popen so that on timeout the process tree is killed before returning,
    preventing orphaned children from holding inherited handles.
    """
    display = label or " ".join(str(c) for c in cmd[:5])
    print(f"\n{_C.DIM}CMD: {display} → {output_file.name}{_C.RESET}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(output_file, "w", encoding="utf-8") as fh:
            with subprocess.Popen(
                [str(c) for c in cmd],
                cwd=str(cwd),
                env=_subprocess_env(env),
                stdout=fh,
                stdin=subprocess.DEVNULL,
            ) as proc:
                try:
                    proc.communicate(timeout=timeout)
                    return proc.returncode
                except subprocess.TimeoutExpired:
                    _kill_proc_tree(proc.pid)
                    proc.kill()
                    with contextlib.suppress(subprocess.TimeoutExpired):
                        proc.communicate(timeout=5)
                    print(f"{_C.YELLOW}[TIMEOUT] {display} exceeded {timeout}s{_C.RESET}")
                    return -1
    except FileNotFoundError:
        print(f"{_C.YELLOW}[WARN] Command not found: {cmd[0]}{_C.RESET}")
        return 1


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


def _missing_py_modules(python: Path, modules: tuple[str, ...]) -> list[str]:
    """Return required Python modules that cannot be imported by *python*."""
    if not modules:
        return []
    script = (
        "import importlib.util, sys\n"
        "missing = [m for m in sys.argv[1:] if importlib.util.find_spec(m) is None]\n"
        "print('\\n'.join(missing))\n"
        "raise SystemExit(1 if missing else 0)\n"
    )
    rc, output = _run_captured(
        [python, "-c", script, *modules],
        label="python dependency probe",
        timeout=30,
    )
    if rc == 0:
        return []
    missing = [line.strip() for line in output.splitlines() if line.strip()]
    return missing or list(modules)


def _cmd_available(cmd: str) -> bool:
    """Return True if *cmd* is found on PATH."""
    return shutil.which(cmd) is not None


def _is_https_reachable(host: str, timeout: float = 5.0) -> bool:
    """Fast preflight: return True only if a verified HTTPS connection to host succeeds.

    Prefer requests when available because Semgrep and pip-audit use the
    requests/certifi trust path. Returns False immediately on SSL cert errors,
    connection refused, or timeout, avoiding the multi-minute retry delays that
    advisory tools impose on failure.
    """
    path = {
        "pypi.org": "/pypi/pip/json",
        "semgrep.dev": "/c/p/default",
    }.get(host, "/")
    url = f"https://{host}{path}"
    try:
        try:
            import requests  # type: ignore[import-untyped]
        except Exception:
            import urllib.request

            # safe: always https; host is a known constant (pypi.org, semgrep.dev)
            urllib.request.urlopen(url, timeout=timeout)  # noqa: S310  # nosec B310
        else:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
        return True
    except Exception:
        return False


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
        managed = name in {
            "pytest",
            "pytest_tmp",
            "pip-audit-cache",
            "pip-cache",
            "npm-cache",
            "ruff-cache",
        } or name.startswith("server_instance_")
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


def _parse_http_port(url: str) -> int:
    parsed = urlparse(url)
    if parsed.port:
        return parsed.port
    return 443 if parsed.scheme == "https" else 80


def _wait_for_port(host: str, port: int, timeout: int = 30) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_open(host, port, timeout=1.0):
            return True
        time.sleep(1)
    return False


def _local_host(host: str) -> bool:
    return host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _maybe_start_websocket_backend(
    python: Path,
    host: str,
    port: int,
    *,
    opcua_endpoint: str | None = None,
    log_name: str = "websocket-backend.log",
) -> tuple[bool, bool, subprocess.Popen | None]:
    """Ensure the local WebSocket backend is listening for Playwright E2E."""
    if _port_open(host, port, timeout=1.0):
        return False, True, None
    if not _local_host(host):
        _warn(f"Cannot auto-start non-local WebSocket backend at {host}:{port}")
        return False, False, None
    if not (ROOT / "index.py").exists():
        _warn("index.py not found — cannot auto-start WebSocket backend")
        return False, False, None

    results_dir = _RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)
    log_path = results_dir / log_name
    env = _subprocess_env({"WS_PORT": str(port)})
    if opcua_endpoint:
        env["OPCUA_TEST_ENDPOINT"] = opcua_endpoint
    _info(f"Starting WebSocket backend for Playwright E2E on :{port}")
    with open(log_path, "w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [str(python), "index.py"],
            cwd=str(ROOT),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )

    ready_host = "127.0.0.1" if host in {"localhost", "0.0.0.0"} else host
    if _wait_for_port(ready_host, port, timeout=30):
        _ok(f"WebSocket backend ready on :{port}")
        return True, True, proc

    _warn(f"WebSocket backend did not open port {port}; see {log_path}")
    _stop_websocket_backend(proc)
    return True, False, None


def _stop_websocket_backend(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
        with contextlib.suppress(Exception):
            proc.wait(timeout=5)


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


def _stage_npm_install(
    *,
    required: bool = False,
    required_packages: tuple[str, ...] = (),
    required_bins: tuple[str, ...] = (),
) -> StageResult:
    """Ensure node_modules are installed before any stage that depends on them."""
    t0 = time.monotonic()
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        _warn("npm not found")
        return StageResult(
            "npm-install",
            1 if required else 0,
            skipped=not required,
            duration=time.monotonic() - t0,
            notes=["npm not found"],
        )
    nm = ROOT / "node_modules"
    missing = _missing_node_requirements(packages=required_packages, bins=required_bins)
    if nm.exists() and any(nm.iterdir()) and not missing:
        return StageResult(
            "npm-install", 0, skipped=True, duration=time.monotonic() - t0, notes=["node_modules already present"]
        )
    reason = "node_modules missing or empty" if not nm.exists() or not any(nm.iterdir()) else "missing npm deps"
    _banner(f"STAGE 1c  npm install ({reason})")
    if missing:
        _info("Missing npm requirements: " + ", ".join(missing))
    rc = _run(_npm_install_args(npm), label="npm dependencies")
    if rc != 0:
        return StageResult("npm-install", rc, duration=time.monotonic() - t0, notes=["npm install failed"])
    missing = _missing_node_requirements(packages=required_packages, bins=required_bins)
    if missing:
        return StageResult(
            "npm-install",
            1,
            duration=time.monotonic() - t0,
            notes=["missing npm requirements after install: " + ", ".join(missing)],
        )
    return StageResult("npm-install", 0, duration=time.monotonic() - t0)


def _stage_pip_install(python: Path, *, required_modules: tuple[str, ...] = ()) -> StageResult:
    _banner("STAGE 1  Install / verify Python test dependencies")
    t0 = time.monotonic()
    if os.getenv("SKIP_VENV_INSTALL") == "1":
        _info("SKIP_VENV_INSTALL=1 — skipping pip install")
        _ensure_precommit_hooks()
        missing = _missing_py_modules(python, required_modules)
        if missing:
            return StageResult(
                "pip-install",
                1,
                duration=time.monotonic() - t0,
                notes=["missing Python requirements: " + ", ".join(missing)],
            )
        return StageResult("pip-install", 0, duration=time.monotonic() - t0, notes=["skipped via SKIP_VENV_INSTALL"])
    _PIP_CACHE.mkdir(parents=True, exist_ok=True)
    pip_env = {**os.environ, "PIP_CACHE_DIR": str(_PIP_CACHE)}
    # Keep bootstrap tooling current even when dependency files are unchanged.
    # pip-audit scans the active environment, so stale pip can fail a clean run.
    _run(
        [python, "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
        label="pip self-upgrade",
        env=pip_env,
    )
    hash_file = _VENV / ".req-hash"
    current_hash = _requirements_hash()
    if hash_file.exists() and hash_file.read_text().strip() == current_hash:
        missing = _missing_py_modules(python, required_modules)
        if not missing:
            _info("Requirements unchanged — skipping pip install")
            _ensure_precommit_hooks()
            return StageResult("pip-install", 0, duration=time.monotonic() - t0, notes=["requirements unchanged"])
        _info("Requirements hash unchanged but required modules are missing: " + ", ".join(missing))
    overall_rc = 0
    for req in (_REQUIREMENTS, _REQUIREMENTS_DEV):
        if req.exists():
            rc = _run(
                [python, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "--pre", "-r", str(req)],
                label=f"pip install {req.name}",
                env=pip_env,
            )
            if rc != 0:
                overall_rc = rc
    if overall_rc == 0:
        missing = _missing_py_modules(python, required_modules)
        if missing:
            overall_rc = 1
            _warn("Missing Python requirements after install: " + ", ".join(missing))
        else:
            hash_file.parent.mkdir(parents=True, exist_ok=True)
            hash_file.write_text(current_hash)
    _ensure_precommit_hooks()
    return StageResult("pip-install", overall_rc, duration=time.monotonic() - t0)


def _stage_python_lint(python: Path) -> StageResult:
    _banner("STAGE 1b  Python static analysis")
    t0 = time.monotonic()
    results_dir = _RESULTS_DIR
    overall_rc = 0
    notes: list[str] = []

    ruff = shutil.which("ruff") or shutil.which("ruff.exe")
    if ruff:
        results_dir.mkdir(parents=True, exist_ok=True)
        rc = _run(
            [
                ruff,
                "check",
                ".",
                "--output-format=json",
                "--output-file",
                str(results_dir / "ruff.json"),
                "--cache-dir",
                str(_TMP_DIR / "ruff-cache"),
            ],
            label="ruff check",
        )
        if rc not in (0, 1):  # 0 = clean, 1 = lint findings
            overall_rc = rc
        rc_fmt = _run(
            [ruff, "format", "--check", ".", "--cache-dir", str(_TMP_DIR / "ruff-cache")], label="ruff format --check"
        )
        if rc_fmt != 0:
            overall_rc = rc_fmt
    else:
        _skip("ruff not found — pip install ruff")
        notes.append("ruff not installed")

    if _py_module_available("mypy"):
        sources: list[str] = [str(p) for p in ROOT.glob("*.py")]
        sources.extend(str(ROOT / name) for name in ("scripts", "src/python", "tests") if (ROOT / name).exists())
        rc = _run(
            [
                python,
                "-m",
                "mypy",
                *sources,
                "--ignore-missing-imports",
                "--no-error-summary",
                "--disable-error-code",
                "annotation-unchecked",
                "--cache-dir",
                str(_TMP_DIR / "mypy-cache"),
                "--exclude",
                r"(\.venv|node_modules|tmp|test-results|pytest-cache-files-.*|\.state)",
            ],
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
        if not _is_https_reachable("pypi.org"):
            _skip("pip-audit skipped — network/TLS unavailable")
            notes.append("pip-audit skipped (network)")
        else:
            pip_audit_cache = _TMP_DIR / "pip-audit-cache"
            pip_audit_cache.mkdir(parents=True, exist_ok=True)
            pip_audit_env = os.environ.copy()
            pip_audit_env.update(
                {
                    # Keep cache local to project temp dir to avoid user-profile permission issues.
                    "PIP_AUDIT_CACHE_DIR": str(pip_audit_cache),
                    "PIP_CACHE_DIR": str(pip_audit_cache),
                }
            )
            rc = _run(
                [
                    python,
                    "-m",
                    "pip_audit",
                    "--format",
                    "json",
                    "-o",
                    str(results_dir / "pip-audit.json"),
                    "--progress-spinner",
                    "off",
                    "--timeout",
                    "5",
                    "--cache-dir",
                    str(pip_audit_cache),
                ],
                label="pip-audit",
                env=pip_audit_env,
                timeout=90 if IS_CI else 30,
                timeout_message="[SKIP] pip-audit skipped — network/TLS timeout",
            )
            if rc not in (0, 1, -1):  # 1 = CVEs found (informational); -1 = timeout/network (advisory)
                overall_rc = rc
            if rc == -1:
                notes.append("pip-audit skipped (network timeout)")
    else:
        _skip("pip-audit not installed — pip install pip-audit")
        notes.append("pip-audit not installed")

    if _py_module_available("detect_secrets"):
        rc, output = _run_captured(
            [python, "-m", "detect_secrets", "scan"],
            label="detect-secrets scan",
            timeout=60,
        )
        if rc == 1:
            if "WinError 5" in output or "PermissionError" in output:
                _skip("detect-secrets skipped — Windows policy blocked multiprocessing")
                notes.append("detect-secrets skipped (Windows policy)")
                rc = 0
            else:
                # rc=1: secrets found OR tool error (e.g. git not in PATH on Windows).
                # Treat as advisory — detect-secrets is informational, not a hard gate.
                _warn("detect-secrets: advisory exit 1 (findings or environment issue)")
                notes.append("detect-secrets: advisory")
        elif rc == -1:
            _skip("detect-secrets skipped — timeout")
            notes.append("detect-secrets skipped (timeout)")
        elif rc not in (0, -1):
            overall_rc = rc
    else:
        _skip("detect-secrets not installed — pip install detect-secrets")
        notes.append("detect-secrets not installed")

    # Semgrep AI code review
    if _cmd_available("semgrep"):
        if not _is_https_reachable("semgrep.dev"):
            _warn("semgrep: network/TLS unavailable — rules not downloaded")
            notes.append("semgrep skipped (network)")
        else:
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
                json_file = results_dir / "semgrep.json"
                if not json_file.exists():
                    _warn("semgrep: no output file (network/auth failure)")
                else:
                    try:
                        data = json.loads(json_file.read_text(encoding="utf-8"))
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
                    except Exception as exc:
                        _warn(f"semgrep: parse failed (rc={rc}): {exc}")
    else:
        _skip("semgrep not installed — pip install semgrep")
        notes.append("semgrep not installed")

    # pyright AI type inference — advisory only, never blocks the run
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
                _warn(f"pyright: advisory: {py_errors} error(s), {py_warns} warning(s)")
                notes.append(f"pyright advisory: {py_errors} error(s)")
            elif py_warns:
                _warn(f"pyright: advisory: 0 errors, {py_warns} warning(s)")
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
    results_dir = _RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)
    cmd: list = [
        python,
        "-m",
        "pytest",
        "tests/python/unit/",
        "-v",
        "--tb=short",
        "--no-header",
        f"--junitxml={results_dir / 'pytest.xml'}",
    ]
    if _py_module_available("pytest_cov"):
        cmd += [
            "--cov=.",
            f"--cov-report=xml:{results_dir / 'coverage.xml'}",
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

    results_dir = _RESULTS_DIR
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
        rc = _run(_npm_install_args(npm), label="npm dependencies")
        if rc != 0:
            return StageResult("js-unit", rc, duration=time.monotonic() - t0, notes=["npm install failed"])

    npx = shutil.which("npx") or shutil.which("npx.cmd")
    results_dir = _RESULTS_DIR
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
                "--coverage.reporter=cobertura",
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


def _stage_pytest_group(
    python: Path,
    *,
    name: str,
    title: str,
    targets: list[str],
    timeout: int = 300,
) -> StageResult:
    _banner(title)
    t0 = time.monotonic()
    results_dir = _RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)
    rc = _run(
        [
            python,
            "-m",
            "pytest",
            *targets,
            "-v",
            "--tb=short",
            "--no-header",
            "--timeout=120",
            f"--junitxml={results_dir / (name + '.xml')}",
        ],
        label=f"pytest {name}",
        timeout=timeout,
    )
    return StageResult(name, rc, duration=time.monotonic() - t0)


def _stage_python_opcua(python: Path) -> StageResult:
    return _stage_pytest_group(
        python,
        name="python-opcua",
        title="STAGE 4a  Python OPC UA live tests",
        targets=[
            "tests/python/live/test_opcua_live.py::TestOpcuaDirectConnection",
            "tests/python/live/test_opcua_live.py::TestOpcuaSubscription",
            "tests/python/live/test_opcua_methods.py",
        ],
        timeout=420,
    )


def _stage_python_backend(python: Path) -> StageResult:
    return _stage_pytest_group(
        python,
        name="python-backend",
        title="STAGE 4b  Python WebSocket backend contract tests",
        targets=[
            "tests/python/live/test_opcua_live.py::TestBackendWebSocket",
            "tests/python/live/test_opcua_live.py::TestResponseTimeSLA",
            "tests/python/integration/",
        ],
        timeout=360,
    )


def _stage_python_lifecycle(python: Path) -> StageResult:
    return _stage_pytest_group(
        python,
        name="python-lifecycle",
        title="STAGE 4c  Python WebSocket lifecycle tests",
        targets=[
            "tests/python/live/test_opcua_live.py::TestWebSocketLifecycle",
        ],
        timeout=240,
    )


def _stage_playwright_install() -> StageResult:
    _banner("STAGE 5  Install Playwright browsers")
    t0 = time.monotonic()
    playwright = _node_bin_path("playwright")
    if playwright is None:
        _warn("local Playwright CLI not found - run npm install first")
        return StageResult(
            "playwright-install",
            1,
            duration=time.monotonic() - t0,
            notes=["local Playwright CLI not found"],
        )

    if _playwright_chromium_available():
        return StageResult(
            "playwright-install",
            0,
            duration=time.monotonic() - t0,
            notes=["chromium browser already installed"],
        )

    env = os.environ.copy()

    if IS_WINDOWS:
        rc = _run(
            [playwright, "install", "chromium"],
            label="playwright install chromium",
            env=env,
        )
    else:
        rc = _run(
            [playwright, "install", "chromium", "--with-deps"],
            label="playwright install chromium --with-deps",
            env=env,
        )
        if rc != 0:
            _warn("--with-deps failed, retrying without it")
            rc = _run(
                [playwright, "install", "chromium"],
                label="playwright install chromium",
                env=env,
            )
    if rc != 0:
        _warn("Playwright browser install failed")
        return StageResult(
            "playwright-install",
            rc if rc > 0 else 1,
            duration=time.monotonic() - t0,
            notes=[
                "Browser download failed - configure proxy/CA certs and run 'npm install' then 'npm run test:e2e:smoke'"
            ],
        )
    return StageResult("playwright-install", rc, duration=time.monotonic() - t0)


def _playwright_chromium_available() -> bool:
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        return False
    script = (
        "const { chromium } = require('playwright');"
        "const fs = require('fs');"
        "process.exit(fs.existsSync(chromium.executablePath()) ? 0 : 1);"
    )
    rc, _output = _run_captured(
        [node, "-e", script],
        label="playwright chromium availability",
        timeout=15,
    )
    return rc == 0


def _stage_playwright_smoke() -> StageResult:
    _banner("STAGE 6  Playwright smoke tests (static HTML, no server needed)")
    t0 = time.monotonic()
    playwright = _node_bin_path("playwright")
    if playwright is None:
        return StageResult("playwright-smoke", 1, notes=["local Playwright CLI not found"])
    rc = _run(
        [playwright, "test", "--project=smoke", "--reporter=line"],
        label="playwright smoke",
    )
    return StageResult("playwright-smoke", rc, duration=time.monotonic() - t0)


def _stage_playwright_project(
    *,
    project: str,
    name: str,
    title: str,
    ws_url: str,
    ui_url: str,
    timeout: int = 600,
    workers: int | None = None,
    extra_env: dict[str, str] | None = None,
) -> StageResult:
    _banner(title)
    t0 = time.monotonic()
    playwright = _node_bin_path("playwright")
    if playwright is None:
        return StageResult(name, 1, notes=["local Playwright CLI not found"])

    results_dir = _RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["WS_TEST_URL"] = ws_url
    env["PLAYWRIGHT_TEST_BASE_URL"] = ui_url
    env["UI_TEST_BASE_URL"] = ui_url
    env.setdefault("UI_TEST_PORT", str(_parse_http_port(ui_url)))
    if workers is not None:
        env["IJT_PLAYWRIGHT_WORKERS"] = str(workers)
    if extra_env:
        env.update(extra_env)

    run_env = {**env, "PLAYWRIGHT_JUNIT_OUTPUT_FILE": str(results_dir / f"{name}.xml")}
    cmd = [playwright, "test", f"--project={project}", "--reporter=line", "--reporter=junit"]
    if workers is not None:
        cmd.append(f"--workers={workers}")
    rc = _run(
        cmd,
        env=run_env,
        label=f"playwright {project}",
        timeout=timeout,
    )
    return StageResult(name, rc, duration=time.monotonic() - t0)


def _stage_playwright_e2e(ws_url: str, ui_url: str) -> StageResult:
    _banner("STAGE 7  Playwright E2E — features + regression")
    t0 = time.monotonic()
    features = _stage_playwright_project(
        project="features",
        name="playwright-features",
        title="STAGE 7a  Playwright E2E — features",
        ws_url=ws_url,
        ui_url=ui_url,
        timeout=480,
    )
    regression = _stage_playwright_project(
        project="regression",
        name="playwright-regression",
        title="STAGE 7b  Playwright E2E — regression",
        ws_url=ws_url,
        ui_url=ui_url,
        timeout=360,
    )
    rc = max(features.rc, regression.rc)
    skipped = features.skipped and regression.skipped
    return StageResult("playwright-e2e", rc, skipped=skipped, duration=time.monotonic() - t0)


def _stage_playwright_features(
    ws_url: str,
    ui_url: str,
    *,
    workers: int | None = None,
    extra_env: dict[str, str] | None = None,
) -> StageResult:
    feature_env = dict(extra_env or {})
    if workers:
        feature_env.setdefault("IJT_E2E_BACKEND_WORKERS", str(workers))
    return _stage_playwright_project(
        project="features",
        name="playwright-features",
        title="STAGE 7a  Playwright E2E — features",
        ws_url=ws_url,
        ui_url=ui_url,
        timeout=600,
        workers=workers,
        extra_env=feature_env,
    )


def _stage_playwright_regression(ws_url: str, ui_url: str) -> StageResult:
    return _stage_playwright_project(
        project="regression",
        name="playwright-regression",
        title="STAGE 7b  Playwright E2E — regression",
        ws_url=ws_url,
        ui_url=ui_url,
        timeout=360,
    )


def _stage_infra_lint() -> StageResult:
    _banner("STAGE Infra  Dockerfile / YAML / Compose linting")
    t0 = time.monotonic()
    results_dir = _RESULTS_DIR
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
_SIMULATOR_PACKAGE_ZIPS: list[Path] = [
    _SERVER_COMPOSE_DIR / "OPC_UA_IJT_Server_Simulator.zip",
    _SERVER_COMPOSE_DIR / "OPC_UA_IJT_Server_Simulator_Linux.zip",
]
# The OPC UA server port this client connects to.  Defined once here so every
# reference below derives from it — change the port in one place only.
_OPCUA_SERVER_PORT = 40463
_MAX_SIMULATOR_INSTANCE_PATH = 100
_SIMULATOR_INSTANCE_ROOT_ENV = "IJT_SIMULATOR_INSTANCE_ROOT"
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
_DOCKER_BUILD_TIMEOUT = _parse_int_env("IJT_DOCKER_BUILD_TIMEOUT", 1200)
_PLAYWRIGHT_FEATURE_WORKERS = _parse_int_env("IJT_PLAYWRIGHT_FEATURE_WORKERS", 4)


@dataclass
class _OpcuaServerInstance:
    port: int
    proc: subprocess.Popen | None
    tmp_dir: Path | None


def _opcua_server_port() -> int:
    return int(os.getenv("OPCUA_SERVER_PORT", str(_OPCUA_SERVER_PORT)))


def _set_opcua_test_endpoint(port: int) -> None:
    os.environ["OPCUA_TEST_ENDPOINT"] = f"opc.tcp://localhost:{port}"


def _set_opcua_prestarted_port(port: int) -> None:
    os.environ[_OPCUA_PRESTARTED_PORT_ENV] = str(port)


def _clear_opcua_runner_env() -> None:
    os.environ.pop("OPCUA_TEST_ENDPOINT", None)
    os.environ.pop(_OPCUA_PRESTARTED_PORT_ENV, None)


def _opcua_server_log_paths(port: int) -> tuple[Path, Path]:
    return (
        _RESULTS_DIR / f"opcua-server-{port}.out.log",
        _RESULTS_DIR / f"opcua-server-{port}.err.log",
    )


def _opcua_server_log_hint(port: int) -> str:
    out_log, err_log = _opcua_server_log_paths(port)
    return f"see {out_log} and {err_log}"


def _absolute_path_text(path: Path) -> str:
    return os.fspath(path if path.is_absolute() else path.resolve())


def _short_windows_simulator_root() -> Path:
    system_drive = os.getenv("SystemDrive", "C:")
    return Path(f"{system_drive.rstrip(':\\\\')}:\\") / "ijt-sim"


def _simulator_instance_dir(port: int) -> Path:
    """Return a short per-port simulator copy directory.

    The Windows simulator creates PKI certificate filenames up to roughly 110
    chars long and rejects install roots above its own 145-char safety
    threshold. GitHub-hosted Windows checkouts are long, so runner-owned
    simulator copies must live under a short temp root, not inside the repo.
    """
    configured_root = os.getenv(_SIMULATOR_INSTANCE_ROOT_ENV)
    if configured_root:
        return Path(configured_root) / str(port)

    base_root = Path(os.getenv("RUNNER_TEMP") or tempfile.gettempdir()) / "ijt-sim"
    candidate = base_root / str(port)
    if IS_WINDOWS and len(_absolute_path_text(candidate)) > _MAX_SIMULATOR_INSTANCE_PATH:
        candidate = _short_windows_simulator_root() / str(port)
    return candidate


def _start_process_with_opcua_logs(command: list[str], *, cwd: Path, port: int) -> subprocess.Popen:
    """Start an OPC UA simulator process and capture its output by port."""
    out_log, err_log = _opcua_server_log_paths(port)
    out_log.parent.mkdir(parents=True, exist_ok=True)
    out_file = out_log.open("ab")
    err_file = err_log.open("ab")
    try:
        return subprocess.Popen(
            command,
            stdout=out_file,
            stderr=err_file,
            stdin=subprocess.DEVNULL,
            cwd=str(cwd),
        )
    finally:
        out_file.close()
        err_file.close()


def _launch_simulator_instance(port: int, exe: str) -> _OpcuaServerInstance | None:
    """Copy the binary dir to a temp location, patch the port config, and launch.

    Returns an owned process/temp-dir pair on success, or None on failure.
    """
    exe_path = Path(exe)
    if not exe_path.exists():
        _warn(f"Binary not found: {exe}")
        return None

    src_dir = exe_path.parent
    tmp_dir = _simulator_instance_dir(port)
    tmp_dir_text = _absolute_path_text(tmp_dir)
    if IS_WINDOWS and len(tmp_dir_text) > _MAX_SIMULATOR_INSTANCE_PATH:
        _warn(
            f"Simulator temp path is too long for Windows certificate generation "
            f"({len(tmp_dir_text)} > {_MAX_SIMULATOR_INSTANCE_PATH}): {tmp_dir_text}"
        )
        return None

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
        proc = _start_process_with_opcua_logs([str(tmp_dir / exe_path.name)], cwd=tmp_dir, port=port)
    except OSError as exc:
        _warn(f"Failed to launch binary: {exc}; {_opcua_server_log_hint(port)}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    _info(f"Waiting up to 30s for port {port} ...")
    for _ in range(30):
        if _port_open("localhost", port, timeout=1.0):
            _ok(f"OPC UA server ready on :{port}")
            return _OpcuaServerInstance(port=port, proc=proc, tmp_dir=tmp_dir)
        time.sleep(1)

    _warn(f"Binary did not open port {port} within 30s; {_opcua_server_log_hint(port)}")
    proc.terminate()
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return None


def _launch_simulator_on_port(port: int, exe: str) -> subprocess.Popen | None:
    """Launch one simulator and bind it to the legacy single-server globals."""
    global _server_tmp_dir

    instance = _launch_simulator_instance(port, exe)
    if instance is None:
        return None
    _set_opcua_test_endpoint(port)
    _set_opcua_prestarted_port(port)
    _server_tmp_dir = instance.tmp_dir
    return instance.proc


def _stop_opcua_server_instance(instance: _OpcuaServerInstance) -> None:
    if instance.proc is not None:
        instance.proc.terminate()
        try:
            instance.proc.wait(timeout=10)
        except Exception:
            instance.proc.kill()
    shutil.rmtree(instance.tmp_dir, ignore_errors=True) if instance.tmp_dir else None


def _find_simulator_executable() -> str | None:
    exe = os.getenv("OPCUA_SIMULATOR_EXE")
    if exe:
        return exe
    for candidate in _WELL_KNOWN_SIMULATOR_PATHS:
        if candidate.exists():
            return str(candidate)
    for package in _SIMULATOR_PACKAGE_ZIPS:
        if not package.exists():
            continue
        _info(f"[server] Extracting simulator package: {package.name}")
        try:
            with zipfile.ZipFile(package) as archive:
                archive.extractall(_SERVER_COMPOSE_DIR)
        except (OSError, zipfile.BadZipFile) as exc:
            _warn(f"[server] Could not extract {package.name}: {exc}")
            continue
        for candidate in _WELL_KNOWN_SIMULATOR_PATHS:
            if candidate.exists():
                return str(candidate)
    return None


def _maybe_start_opcua_server() -> tuple[bool, bool, subprocess.Popen | None]:
    """Start the OPC UA server if the target port is not yet open.

    Returns *(started_by_us, port_open, proc)*.
    *started_by_us* is True when this call launched the server.
    *proc* is the Popen handle if a binary was started (None for Docker).
    """
    # If user explicitly set the endpoint, don't auto-launch
    if os.getenv("OPCUA_TEST_ENDPOINT") or os.getenv("OPCUA_SERVER_URL"):
        os.environ.pop(_OPCUA_PRESTARTED_PORT_ENV, None)
        port = _opcua_server_port()
        endpoint = os.getenv("OPCUA_TEST_ENDPOINT") or os.getenv("OPCUA_SERVER_URL") or ""
        os.environ.setdefault("OPCUA_TEST_ENDPOINT", endpoint)
        host, srv_port = _parse_opcua_host_port(endpoint)
        open_ = _port_open(host, srv_port)
        return False, open_, None

    port = _opcua_server_port()
    if _port_open("localhost", port):
        os.environ.pop(_OPCUA_PRESTARTED_PORT_ENV, None)
        _info(f"OPC UA server already listening on port {port}")
        _set_opcua_test_endpoint(port)
        return False, True, None

    # Try binary launch first
    exe = _find_simulator_executable()

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
            _set_opcua_test_endpoint(port)
            _set_opcua_prestarted_port(port)
            return True, True, None
        time.sleep(2)

    _warn(f"OPC UA server not ready after 60s (port {port})")
    return True, False, None


def _stop_opcua_server(proc: subprocess.Popen | None = None) -> None:
    global _server_tmp_dir
    _clear_opcua_runner_env()
    if proc is not None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
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
    results_dir = _RESULTS_DIR
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


def _run_with_owned_services(
    *,
    python: Path,
    name: str,
    need_ws: bool,
    ws_url: str,
    stage: Callable[[], StageResult],
) -> StageResult:
    """Run one live stage with an OPC UA server and optional WS backend owned here."""
    if not os.getenv("OPCUA_TEST_ENDPOINT") and not os.getenv("OPCUA_SERVER_URL"):
        opcua_port = _opcua_server_port()
        if _port_open("localhost", opcua_port, timeout=1.0):
            return StageResult(name, 1, notes=[f"OPC UA port {opcua_port} is already in use"])

    if need_ws:
        ws_host, ws_port = _parse_ws_host_port(ws_url)
        if _port_open(ws_host, ws_port, timeout=1.0):
            return StageResult(name, 1, notes=[f"WebSocket port {ws_port} is already in use"])

    srv_started, srv_open, srv_proc = _maybe_start_opcua_server()
    ws_started = False
    ws_proc: subprocess.Popen | None = None
    try:
        if not srv_open:
            return StageResult(name, 1, notes=["OPC UA server not available"])

        if need_ws:
            ws_host, ws_port = _parse_ws_host_port(ws_url)
            ws_started, ws_ready, ws_proc = _maybe_start_websocket_backend(python, ws_host, ws_port)
            if not ws_ready:
                return StageResult(name, 1, notes=["WebSocket backend not reachable"])

        return stage()
    finally:
        if ws_started:
            _stop_websocket_backend(ws_proc)
        if srv_started:
            _stop_opcua_server(srv_proc)


def _run_playwright_features_with_owned_pool(
    *,
    python: Path,
    name: str,
    ws_url: str,
    ui_url: str,
    workers: int,
) -> StageResult:
    """Run Playwright feature specs against one owned backend/server pair per worker."""
    workers = max(1, workers)
    if workers == 1 or os.getenv("OPCUA_TEST_ENDPOINT") or os.getenv("OPCUA_SERVER_URL"):
        return _run_with_owned_services(
            python=python,
            name=name,
            need_ws=True,
            ws_url=ws_url,
            stage=lambda: _stage_playwright_features(ws_url, ui_url, workers=1),
        )

    ws_host, ws_base_port = _parse_ws_host_port(ws_url)
    if not _local_host(ws_host):
        return StageResult(name, 1, notes=[f"Cannot auto-start non-local WebSocket backend at {ws_host}"])

    opcua_base_port = _opcua_server_port()
    blocked_ports: list[str] = []
    for index in range(workers):
        opcua_port = opcua_base_port + index
        ws_port = ws_base_port + index
        if _port_open("localhost", opcua_port, timeout=1.0):
            blocked_ports.append(f"OPC UA {opcua_port}")
        if _port_open(ws_host, ws_port, timeout=1.0):
            blocked_ports.append(f"WS {ws_port}")
    if blocked_ports:
        return StageResult(name, 1, notes=["Worker pool ports already in use: " + ", ".join(blocked_ports)])

    exe = _find_simulator_executable()
    if not exe:
        return StageResult(name, 1, notes=["OPC UA simulator binary not found for worker pool"])

    servers: list[_OpcuaServerInstance] = []
    ws_procs: list[subprocess.Popen | None] = []
    try:
        for index in range(workers):
            opcua_port = opcua_base_port + index
            instance = _launch_simulator_instance(opcua_port, exe)
            if instance is None:
                return StageResult(name, 1, notes=[f"OPC UA worker {index} failed to start on port {opcua_port}"])
            servers.append(instance)

        for index in range(workers):
            ws_port = ws_base_port + index
            opcua_endpoint = f"opc.tcp://localhost:{opcua_base_port + index}"
            started, ready, proc = _maybe_start_websocket_backend(
                python,
                ws_host,
                ws_port,
                opcua_endpoint=opcua_endpoint,
                log_name=f"websocket-backend-{ws_port}.log",
            )
            if not started or not ready:
                return StageResult(name, 1, notes=[f"WebSocket worker {index} failed to start on port {ws_port}"])
            ws_procs.append(proc)

        return _stage_playwright_features(
            ws_url,
            ui_url,
            workers=workers,
            extra_env={
                "OPCUA_TEST_ENDPOINT": f"opc.tcp://localhost:{opcua_base_port}",
                "IJT_E2E_BACKEND_WORKERS": str(workers),
            },
        )
    finally:
        for proc in reversed(ws_procs):
            _stop_websocket_backend(proc)
        for instance in reversed(servers):
            _stop_opcua_server_instance(instance)


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
    rc = _run(
        build_cmd,
        label="docker build (BuildKit)",
        env=build_env,
        timeout=_DOCKER_BUILD_TIMEOUT,
    )
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
def _stage_status(result: StageResult) -> str:
    if result.skipped:
        return "skipped"
    return "passed" if result.rc == 0 else "failed"


def _timing_payload(results: list[StageResult], total_time: float, mode: str) -> dict:
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "total_seconds": round(total_time, 3),
        "results_dir": str(_RESULTS_DIR),
        "stages": [
            {
                "name": result.name,
                "status": _stage_status(result),
                "exit_code": result.rc,
                "duration_seconds": round(result.duration, 3),
                "notes": list(result.notes),
            }
            for result in results
        ],
    }


def _write_timing_artifacts(results: list[StageResult], total_time: float, mode: str) -> None:
    payload = _timing_payload(results, total_time, mode)
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    latest_json = json.dumps(payload, indent=2, sort_keys=True)
    latest_line = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    (_RESULTS_DIR / "timing-latest.json").write_text(latest_json + "\n", encoding="utf-8")
    (_RESULTS_DIR / "timing-history.jsonl").write_text(latest_line + "\n", encoding="utf-8")

    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    with _TIMING_HISTORY.open("a", encoding="utf-8") as history:
        history.write(latest_line + "\n")


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
            if overall == 0:
                overall = r.rc if r.rc > 0 else 1
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
    "python-opcua",
    "python-backend",
    "python-lifecycle",
    "python-integration",
    "playwright-install",
    "playwright-smoke",
    "playwright-features",
    "playwright-regression",
    "playwright-e2e",
    "docker-smoke",
]


def _mode_name(args: argparse.Namespace, target_only: bool) -> str:
    if target_only:
        return "target-only"
    if args.phase1:
        return "phase1"
    if args.phase2:
        return "phase2"
    if args.docker_only:
        return "docker-only"
    return "full"


@dataclass(frozen=True)
class TargetDependencyRequirements:
    python: bool
    npm: bool


def _target_only_dependency_requirements(args: argparse.Namespace) -> TargetDependencyRequirements:
    """Return dependency families required before a focused live-suite target."""
    return TargetDependencyRequirements(
        python=bool(
            args.python_opcua_only
            or args.python_backend_only
            or args.python_lifecycle_only
            or args.playwright_features_only
            or args.playwright_regression_only
        ),
        npm=bool(args.playwright_smoke_only or args.playwright_features_only or args.playwright_regression_only),
    )


def _run_target_dependency_stages(
    args: argparse.Namespace,
    python: Path,
    results: list[StageResult],
) -> bool:
    """Run prerequisite install/verification stages for focused live-suite targets."""
    requirements = _target_only_dependency_requirements(args)
    if requirements.python:
        result = _stage_pip_install(python, required_modules=_PYTHON_TARGET_REQUIRED_MODULES)
        results.append(result)
        if result.rc != 0:
            return False
    if requirements.npm:
        result = _stage_npm_install(
            required=True,
            required_packages=_PLAYWRIGHT_REQUIRED_PACKAGES,
            required_bins=_PLAYWRIGHT_REQUIRED_BINS,
        )
        results.append(result)
        if result.rc != 0:
            return False
    return True


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
    parser.add_argument("--docker-only", action="store_true", help="Docker smoke only — skip static/live/E2E stages")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker smoke even when Docker is available")
    parser.add_argument("--python-opcua-only", action="store_true", help="Run only direct OPC UA Python live tests")
    parser.add_argument("--python-backend-only", action="store_true", help="Run only Python WebSocket backend tests")
    parser.add_argument(
        "--python-lifecycle-only", action="store_true", help="Run only Python WebSocket lifecycle tests"
    )
    parser.add_argument("--playwright-smoke-only", action="store_true", help="Run only Playwright smoke tests")
    parser.add_argument("--playwright-features-only", action="store_true", help="Run only Playwright feature E2E tests")
    parser.add_argument(
        "--playwright-regression-only", action="store_true", help="Run only Playwright regression E2E tests"
    )
    parser.add_argument("--list", action="store_true", help="Print available stages and exit")
    parser.add_argument(
        "--opcua-endpoint", default=os.getenv("OPCUA_TEST_ENDPOINT", f"opc.tcp://localhost:{_opcua_server_port()}")
    )
    parser.add_argument("--ws-url", default=os.getenv("WS_TEST_URL", "ws://localhost:8001"))
    parser.add_argument("--ui-url", default=os.getenv("UI_TEST_BASE_URL", "http://127.0.0.1:3000"))
    args = parser.parse_args()

    targeted_flags = [
        args.python_opcua_only,
        args.python_backend_only,
        args.python_lifecycle_only,
        args.playwright_smoke_only,
        args.playwright_features_only,
        args.playwright_regression_only,
    ]
    if sum(1 for flag in targeted_flags if flag) > 1:
        parser.error("choose only one targeted live-suite flag")

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
    target_only = any(targeted_flags)
    mode = _mode_name(args, target_only)
    skip_static = args.phase2 or args.docker_only or target_only

    python = Path(sys.executable)
    t_start = time.monotonic()

    # Check availability upfront — drives auto-detection of optional stages
    opcua_host, opcua_port = _parse_opcua_host_port(args.opcua_endpoint)
    ws_host, ws_port = _parse_ws_host_port(args.ws_url)
    opcua_up = _port_open(opcua_host, opcua_port)
    ws_up = _port_open(ws_host, ws_port)
    docker_up = False if target_only else _docker_available()

    # Auto-detect optional stages when not explicitly requested
    # --phase1: force off all live/docker stages
    if args.phase1:
        run_live = False
        run_e2e = False
        run_docker = False
    elif args.docker_only:
        run_live = False
        run_e2e = False
        run_docker = not args.skip_docker
    else:
        run_live = run_live or opcua_up
        run_e2e = run_e2e or ws_up
        run_docker = (args.all or docker_up) and not args.skip_docker

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
        _warn(f"WebSocket backend NOT reachable at {args.ws_url} — runner will try to auto-start it for E2E")

    results: list[StageResult] = []

    # Wipe previous run's results so the local copy always reflects the latest run only
    shutil.rmtree(_RESULTS_DIR, ignore_errors=True)
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if target_only:
        if not _run_target_dependency_stages(args, python, results):
            total_time = time.monotonic() - t_start
            _write_timing_artifacts(results, total_time, mode)
            rc = _print_summary(results, total_time)
            _cleanup_caches(ROOT)
            return rc

        if args.python_opcua_only:
            results.append(
                _run_with_owned_services(
                    python=python,
                    name="python-opcua",
                    need_ws=False,
                    ws_url=args.ws_url,
                    stage=lambda: _stage_python_opcua(python),
                )
            )
        elif args.python_backend_only:
            results.append(
                _run_with_owned_services(
                    python=python,
                    name="python-backend",
                    need_ws=True,
                    ws_url=args.ws_url,
                    stage=lambda: _stage_python_backend(python),
                )
            )
        elif args.python_lifecycle_only:
            results.append(
                _run_with_owned_services(
                    python=python,
                    name="python-lifecycle",
                    need_ws=True,
                    ws_url=args.ws_url,
                    stage=lambda: _stage_python_lifecycle(python),
                )
            )
        elif args.playwright_smoke_only:
            pw_install = _stage_playwright_install()
            results.append(pw_install)
            if not pw_install.skipped and pw_install.rc == 0:
                results.append(_stage_playwright_smoke())
        elif args.playwright_features_only:
            pw_install = _stage_playwright_install()
            results.append(pw_install)
            if not pw_install.skipped and pw_install.rc == 0:
                results.append(
                    _run_playwright_features_with_owned_pool(
                        python=python,
                        name="playwright-features",
                        ws_url=args.ws_url,
                        ui_url=args.ui_url,
                        workers=_PLAYWRIGHT_FEATURE_WORKERS,
                    )
                )
        elif args.playwright_regression_only:
            pw_install = _stage_playwright_install()
            results.append(pw_install)
            if not pw_install.skipped and pw_install.rc == 0:
                results.append(
                    _run_with_owned_services(
                        python=python,
                        name="playwright-regression",
                        need_ws=True,
                        ws_url=args.ws_url,
                        stage=lambda: _stage_playwright_regression(args.ws_url, args.ui_url),
                    )
                )

        total_time = time.monotonic() - t_start
        _write_timing_artifacts(results, total_time, mode)
        rc = _print_summary(results, total_time)
        _cleanup_caches(ROOT)
        return rc

    # ── Static / unit stages (skipped when --phase2) ──────────────────────────
    if not skip_static:
        results.append(_stage_versions())
        results.append(_stage_pip_install(python))
        results.append(_stage_npm_install())
        results.append(_stage_python_lint(python))
        results.append(_stage_python_unit(python))
        results.append(_stage_js_lint())
        results.append(_stage_js_unit())
        results.append(_stage_infra_lint())

    # ── Live + Integration tests (Phase 2 — skipped when --phase1) ────────────
    # Auto-launch server ONCE and share it between live and integration stages.
    # This ensures live tests are not skipped just because the server was not
    # running at startup — the same auto-launch logic that integration uses.
    _srv_started = False
    _srv_port_open = False
    _srv_proc: subprocess.Popen | None = None
    try:
        if not args.phase1 and not args.docker_only:
            _srv_started, _srv_port_open, _srv_proc = _maybe_start_opcua_server()
            if run_live:
                if _srv_port_open:
                    results.append(_stage_python_live(python))
                else:
                    _skip("python-live: OPC UA server not available")
                    results.append(StageResult("python-live", 0, skipped=True, notes=["OPC UA server not available"]))

            if run_live or docker_up or _srv_port_open:
                # Pass prestarted so integration stage re-uses the running server.
                # Keep this same server alive through Playwright E2E below.
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

        # Hint: multi-version testing via pyenv
        if _cmd_available("pyenv"):
            _info("pyenv detected — multi-version testing available: pyenv local X.Y.Z && python run_all_tests.py")

        # ── Playwright (smoke always runs; E2E auto-detected or explicit) ─────────
        if not args.phase1 and not args.docker_only:
            pw_install = _stage_playwright_install()
            results.append(pw_install)

            if not pw_install.skipped and pw_install.rc == 0:
                # Smoke always runs — catches 404s, JS errors, missing assets
                results.append(_stage_playwright_smoke())

                if run_e2e:
                    ws_ready = _port_open(ws_host, ws_port, timeout=1.0)
                    ws_started = False
                    ws_proc: subprocess.Popen | None = None
                    if not ws_ready:
                        ws_started, ws_ready, ws_proc = _maybe_start_websocket_backend(python, ws_host, ws_port)
                    try:
                        if not _srv_port_open:
                            _skip("playwright-e2e: OPC UA server not available")
                            results.append(
                                StageResult("playwright-e2e", 0, skipped=True, notes=["OPC UA server not available"])
                            )
                        elif ws_ready:
                            results.append(_stage_playwright_e2e(args.ws_url, args.ui_url))
                        else:
                            _skip("playwright-e2e: WebSocket backend not reachable")
                            results.append(
                                StageResult(
                                    "playwright-e2e", 0, skipped=True, notes=["WebSocket backend not reachable"]
                                )
                            )
                    finally:
                        if ws_started:
                            _stop_websocket_backend(ws_proc)
    finally:
        if _srv_started:
            _stop_opcua_server(_srv_proc)

    # ── Docker smoke (auto-detected; skipped if Docker unavailable) ───────────
    if not args.phase1 and run_docker:
        results.append(_stage_docker_smoke())
    elif not args.phase1:
        _skip(f"docker-smoke: {_docker_skip_reason()}")
        results.append(StageResult("docker-smoke", 0, skipped=True))

    total_time = time.monotonic() - t_start
    _write_timing_artifacts(results, total_time, mode)
    rc = _print_summary(results, total_time)
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
                    (Path(dirpath) / f).unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
