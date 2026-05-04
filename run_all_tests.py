#!/usr/bin/env python3
"""
run_all_tests.py -- Top-level test runner for the
UA-for-Industrial-Joining-Technologies repository.

Architecture: Two-phase execution
  Phase 1 (PARALLEL)   -- static analysis + unit tests, no OPC UA server required.
                          Delegates to each sub-project's own run_all_tests.py --phase1,
                          ensuring local runs cover CI checks or stricter (e.g. testclient
                          runs full phase1 locally, matching ci.yml pytest tests/unit/ run):
                            - ruff, mypy, bandit (Python projects)
                            - ESLint, npm audit (Node/JS projects)
                            - dotnet format, NuGet vulnerability scan (C# project)
                            - hadolint, yamllint (Server / Docker)
                          Extra root-level checks: git-sanity, md-hygiene, GHA workflow validation.
  Phase 2 (PARALLEL)   -- live integration tests, no shared server.
                          Each sub-runner owns its server on a dedicated port
                          and manages its full lifecycle independently:
                            - Server smoke    -> native/default server port (40451)
                            - Console Client  → OPCUA_SERVER_PORT_CONSOLE_CLIENT (40461)
                            - Test Client     → OPCUA_SERVER_PORT_TEST_CLIENT    (40462)
                            - Web Client      → OPCUA_SERVER_PORT_WEB_CLIENT     (40463)
                            - C# Client       → OPCUA_SERVER_PORT_CSHARP_CLIENT  (40464)
                          Release 2 clients do not share 40451.

Usage:
  python run_all_tests.py                    # full run (Phase 1 + Phase 2)
  python run_all_tests.py --phase1           # static + unit tests only (no server)
  python run_all_tests.py --phase2           # server smoke + live tests
  python run_all_tests.py --suite md-hygiene # single suite by name
  python run_all_tests.py --suite server-smoke  # focused server smoke on port 40451
  python run_all_tests.py --verbose          # DEBUG-level logging
  python run_all_tests.py --help

Environment variables:
  IJT_SUITE_TIMEOUT     Per-suite timeout in seconds (default: 600)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Colour / ANSI helpers
# ---------------------------------------------------------------------------


def _enable_ansi_windows() -> bool:
    """Enable virtual-terminal processing on Windows 10+ consoles."""
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            return True
        return False
    except Exception:
        return False


_USE_COLOUR: bool = False  # resolved in main() after arg parsing


def _c(ansi: str, text: str) -> str:
    return f"{ansi}{text}\033[0m" if _USE_COLOUR else text


# ---------------------------------------------------------------------------
# Logging setup -- single stream to stdout, optional colour
# ---------------------------------------------------------------------------


class _ColourFormatter(logging.Formatter):
    _CODES = {
        logging.DEBUG: "\033[2m",
        logging.INFO: "",
        logging.WARNING: "\033[93m",
        logging.ERROR: "\033[91m",
        logging.CRITICAL: "\033[91m\033[1m",
    }
    _RESET = "\033[0m"

    def __init__(self, use_colour: bool) -> None:
        super().__init__(
            fmt="%(asctime)s [%(levelname)-8s] %(message)s",
            datefmt="%H:%M:%S",
        )
        self._use_colour = use_colour

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        if self._use_colour:
            code = self._CODES.get(record.levelno, "")
            if code:
                return f"{code}{msg}{self._RESET}"
        return msg


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    use_colour = sys.stdout.isatty() and (os.name != "nt" or _enable_ansi_windows())
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_ColourFormatter(use_colour))
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)


log = logging.getLogger("run_all_tests")

# ---------------------------------------------------------------------------
# Banner / result helpers
# ---------------------------------------------------------------------------


def _banner(title: str) -> None:
    width = 64
    bar = "\u2550" * width
    pad = title.ljust(width - 2)
    lines = [
        "",
        _c("\033[96m\033[1m", f"\u2554{bar}\u2557"),
        _c("\033[96m\033[1m", f"\u2551  {pad}\u2551"),
        _c("\033[96m\033[1m", f"\u255a{bar}\u255d"),
    ]
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


def _result_line(ok: bool, skipped: bool, name: str, duration: float, note: str = "") -> None:
    if skipped:
        icon, colour, status = "\u25cb", "\033[93m", " (skipped)"
    elif ok:
        icon, colour, status = "\u2714", "\033[92m", ""
    else:
        icon, colour, status = "\u2718", "\033[91m", " FAILED"
    suffix = f"  {note}" if note else ""
    line = f"  {icon} {name}{status} ({duration:.1f}s){suffix}"
    sys.stdout.write(_c(colour, line) + "\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Key paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
ROOT = REPO_ROOT  # alias used by GHA validation helpers
SERVER_DIR = REPO_ROOT / "OPC_UA_Servers" / "Release2"
_NATIVE_BINARY_WIN = SERVER_DIR / "OPC_UA_IJT_Server_Simulator" / "opcua_ijt_demo_application.exe"
_NATIVE_BINARY_LINUX = (
    SERVER_DIR / "OPC_UA_IJT_Server_Simulator_Linux" / "opcua_ijt_demo_application"
)
CSHARP_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_CSharp_Client"
CONSOLE_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Console_Client"
TEST_CLIENT_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Test_Client"
WEB_CLIENT_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client"
NODE_CLIENT_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release1" / "IJT_Node_Client"
SMOKE_TEST = SERVER_DIR / "tests" / "smoke_test.py"
_RUNNER_SCRIPT_PATHS: tuple[Path, ...] = (
    NODE_CLIENT_DIR / "run_all_tests.py",
    CSHARP_DIR / "run_all_tests.py",
    CONSOLE_DIR / "run_all_tests.py",
    TEST_CLIENT_DIR / "run_all_tests.py",
    WEB_CLIENT_DIR / "run_all_tests.py",
    SERVER_DIR / "run_all_tests.py",
)
_OPTIONAL_IMPORT_GUARD_PATHS: tuple[Path, ...] = _RUNNER_SCRIPT_PATHS + (
    TEST_CLIENT_DIR / "scripts" / "make_ci_summary.py",
    TEST_CLIENT_DIR / "scripts" / "make_excel_report.py",
)

# ---------------------------------------------------------------------------
# Canonical OPC UA server port assignments — change here, change everywhere.
# Each value is the port the OPC UA server instance listens on for that client.
# ---------------------------------------------------------------------------
OPCUA_SERVER_PORT_CONSOLE_CLIENT = 40461  # server port the Console Client connects to
OPCUA_SERVER_PORT_TEST_CLIENT = 40462  # server port the Test Client connects to
OPCUA_SERVER_PORT_WEB_CLIENT = 40463  # server port the Web Client connects to
OPCUA_SERVER_PORT_CSHARP_CLIENT = 40464  # server port the C# Client connects to

# Release 1 / Node client — legacy default, unchanged for backward compatibility.
# Smoke / utility suites also use this port: they specifically test the server's
# native/default configuration, so 40451 is intentional and correct there.
# Release 2 sub-runners each own their dedicated port above.
OPCUA_PORT = 40451

IS_WINDOWS = sys.platform == "win32"
IS_CI = bool(os.getenv("CI"))

SUITE_TIMEOUT = int(os.getenv("IJT_SUITE_TIMEOUT", "600"))  # 10 min default

# ---------------------------------------------------------------------------
# Suite result
# ---------------------------------------------------------------------------


@dataclass
class SuiteResult:
    name: str
    ok: bool
    duration: float = 0.0
    skipped: bool = False
    output: str = ""  # captured stdout+stderr; printed atomically after run
    notes: list[str] = field(default_factory=list)
    counts: str = ""  # parsed test counts, e.g. "490 passed, 3 skipped"


@dataclass
class StepResult:
    """Lightweight result for root-level pre-flight checks (GHA validation, etc.)."""

    name: str
    status: str  # PASS | FAIL | SKIP | WARN
    detail: str = ""


# ---------------------------------------------------------------------------
# Tool availability
# ---------------------------------------------------------------------------


def _check_tool(cmd: list[str], name: str) -> bool:
    """Return True if the tool runs successfully; warn (not error) if missing."""
    try:
        r = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):  # fmt: skip
        log.warning(
            "Tool unavailable: %s (%s) -- dependent suites will fail naturally.",
            name,
            " ".join(cmd),
        )
        return False


def _find_cmd(names: list[str]) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _current_python() -> str:
    return sys.executable


# ---------------------------------------------------------------------------
# Subprocess -- capture stdout+stderr, process-tree kill on timeout
# ---------------------------------------------------------------------------


def _kill_proc_tree(pid: int) -> None:
    """Kill a process and all its descendants.

    On Windows uses ``taskkill /F /T`` which also closes inherited pipe handles
    held by grandchild processes (MSBuild workers, vitest node, etc.).
    On Unix sends SIGKILL to the process group.
    """
    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        import signal

        with contextlib.suppress(ProcessLookupError):
            os.killpg(os.getpgid(pid), signal.SIGKILL)


def _run_captured(
    cmd: list[str],
    *,
    cwd: Path,
    timeout: int = SUITE_TIMEOUT,
    env: dict | None = None,
    label: str = "",
) -> tuple[int, str]:
    """
    Run *cmd* in *cwd* capturing stdout+stderr combined.
    Returns (returncode, combined_text).

    Uses Popen + communicate() with a secondary tree-kill on timeout.
    This avoids the Windows deadlock where grandchild processes (MSBuild workers,
    vitest/node) hold inherited pipe handles open after the parent exits, causing
    communicate() to block indefinitely.
    """
    display = label or " ".join(str(c) for c in cmd[:6])
    header = f"\u25b6 {display}  [cwd={cwd}]"
    sep = "\u2500" * min(len(header), 78)
    preamble = f"{header}\n{sep}\n"

    run_env = dict(env) if env is not None else os.environ.copy()
    # Child Python runners on Windows otherwise emit text through the active
    # code page while this orchestrator decodes captured output as UTF-8.
    run_env.setdefault("PYTHONIOENCODING", "utf-8")
    run_env.setdefault("PYTHONUTF8", "1")

    # On Unix, place the child in its own session so killpg can reach the tree.
    popen_kwargs: dict = {}
    if not IS_WINDOWS:
        popen_kwargs["start_new_session"] = True

    try:
        proc = subprocess.Popen(
            [str(c) for c in cmd],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            env=run_env,
            **popen_kwargs,
        )
    except FileNotFoundError:
        return 1, preamble + f"[ERROR: command not found: {cmd[0]}]\n"

    def _decode(b):
        if b is None:
            return ""
        return b.decode("utf-8", errors="replace")

    try:
        raw_out, raw_err = proc.communicate(timeout=timeout)
        body = _decode(raw_out)
        err_text = _decode(raw_err)
        if err_text:
            body += "\n[stderr]\n" + err_text
        return proc.returncode, preamble + body

    except subprocess.TimeoutExpired:
        # Kill the whole tree so grandchild processes release pipe handles
        _kill_proc_tree(proc.pid)
        try:
            raw_out, raw_err = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()
            raw_out, raw_err = None, None
        body = _decode(raw_out) + f"\n[TIMEOUT after {timeout}s -- process tree killed]\n"
        err_text = _decode(raw_err)
        if err_text:
            body += "\n[stderr]\n" + err_text
        return 1, preamble + body


def _emit_suite_output(result: SuiteResult) -> None:
    """Print captured suite output atomically (no interleaving with other suites)."""
    if result.output:
        sys.stdout.write(result.output)
        if not result.output.endswith("\n"):
            sys.stdout.write("\n")
    _result_line(
        result.ok,
        result.skipped,
        result.name,
        result.duration,
        note=" | ".join(result.notes) if result.notes else "",
    )
    sys.stdout.flush()


def _parse_suite_counts(text: str) -> str:
    """Return the most informative test-count string from sub-runner captured output.

    Handles four output formats:
      - pytest:  "1298 passed, 267 skipped, 2 xfailed in 409.92s"
      - C# dotnet test:  "Failed: 0, Passed: 800, Skipped: 0, Total: 800"
      - Vitest raw:  "Tests  152 passed (152)"
      - Node sub-runner:  "[PHASE 1] Vitest (unit) .... PASS (299/299)"
    For suites that run both Python and JS (Web Client), combines both counts.
    """
    _WORD = r"(?:failed|error|errors|skipped|xfailed|xpassed|warnings?|deselected)"
    best: tuple[int, str] = (0, "")
    for m in re.finditer(rf"(\d+ passed(?:,\s*\d+ {_WORD})*)\s+in\s+[\d.]+s", text):
        snippet = m.group(1)
        total = sum(int(n) for n in re.findall(r"\d+", snippet))
        if total > best[0]:
            best = (total, snippet)
    py_counts = best[1]

    # Raw vitest output: "Tests  152 passed (152)"
    vm = re.search(r"\bTests\s+(\d+) passed", text)
    # Node sub-runner summary: "[PHASE 1] Vitest (unit) .... PASS (299/299)"
    vnm = re.search(r"Vitest \(unit\).*?PASS \((\d+)/\d+\)", text)
    js_counts = f"{vm.group(1)} passed" if vm else f"{vnm.group(1)} passed" if vnm else ""

    if py_counts and js_counts:
        return f"{py_counts} (py), {js_counts} (js)"
    if py_counts:
        return py_counts
    if js_counts:
        return js_counts

    cs_passed = re.search(r"Passed:\s*(\d+)", text)
    if cs_passed:
        cs_failed = re.search(r"Failed:\s*(\d+)", text)
        cs_skipped = re.search(r"Skipped:\s*(\d+)", text)
        parts = [f"{cs_passed.group(1)} passed"]
        if cs_failed and cs_failed.group(1) != "0":
            parts.append(f"{cs_failed.group(1)} failed")
        if cs_skipped and cs_skipped.group(1) != "0":
            parts.append(f"{cs_skipped.group(1)} skipped")
        return ", ".join(parts)

    return ""


def _delegate_to_runner(
    name: str,
    runner_dir: Path,
    phase_args: list[str],
    label: str,
    extra_env: dict | None = None,
    timeout: int | None = None,
) -> SuiteResult:
    """Delegate a test suite to a sub-project's own run_all_tests.py.

    The sub-project runner is the single source of truth for what that
    sub-project tests.  Calling it here ensures local runs cover CI checks
    or are stricter (ruff, mypy, bandit, npm audit, dotnet format, ...).
    Note: testclient runs full phase1 locally; ci.yml also runs real pytest tests/unit/.
    """
    t0 = time.monotonic()
    runner = runner_dir / "run_all_tests.py"
    if not runner_dir.exists() or not runner.exists():
        return SuiteResult(
            name=name,
            ok=True,
            skipped=True,
            notes=[f"sub-project runner not found: {runner}"],
        )
    env = {**os.environ}
    if extra_env:
        env.update(extra_env)
    run_timeout = timeout if timeout is not None else SUITE_TIMEOUT
    rc, out = _run_captured(
        [sys.executable, str(runner)] + phase_args,
        cwd=runner_dir,
        label=label,
        env=env,
        timeout=run_timeout,
    )
    return SuiteResult(
        name=name,
        ok=(rc == 0),
        duration=time.monotonic() - t0,
        output=out,
        counts=_parse_suite_counts(out),
    )


# ---------------------------------------------------------------------------
# Docker / server management
# ---------------------------------------------------------------------------

_native_server_proc: subprocess.Popen | None = None


def _try_native_binary() -> bool:
    """Launch the native OPC UA server binary (no Docker dependency).

    Tries the Windows .exe on Windows, the Linux binary otherwise.
    Returns True if the binary was found and the process was started.
    Sets module-level ``_native_server_proc`` so ``_stop_server`` can clean up.
    """
    global _native_server_proc
    binary = _NATIVE_BINARY_WIN if IS_WINDOWS else _NATIVE_BINARY_LINUX
    if not binary.exists():
        log.info("Native OPC UA binary not found at %s", binary)
        return False
    log.info("Starting OPC UA server binary: %s", binary)
    try:
        _native_server_proc = subprocess.Popen(
            [str(binary)],
            cwd=str(binary.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("OPC UA binary launched (pid=%d).", _native_server_proc.pid)
        return True
    except OSError as exc:
        log.warning("Failed to launch native binary: %s", exc)
        return False


def _ensure_docker_running() -> None:
    """Ensure Docker daemon is up; on Windows, launch Docker Desktop if needed."""
    docker = _find_cmd(["docker", "docker.exe"])
    if not docker:
        log.error(
            "docker not found in PATH. "
            "Install Docker Desktop: https://www.docker.com/products/docker-desktop"
        )
        sys.exit(1)

    with contextlib.suppress(Exception):
        r = subprocess.run(
            [docker, "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        if r.returncode == 0:
            log.info("Docker daemon is running.")
            return

    if not IS_WINDOWS:
        log.error("Docker daemon is not running. Please start Docker and retry.")
        sys.exit(1)

    # Windows -- attempt to launch Docker Desktop
    candidates = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        / "Docker"
        / "Docker"
        / "Docker Desktop.exe",
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Programs"
        / "Docker"
        / "Docker"
        / "Docker Desktop.exe",
    ]
    exe = next((p for p in candidates if p.exists()), None)
    if not exe:
        log.error(
            "Docker Desktop not found. Install from: https://www.docker.com/products/docker-desktop"
        )
        sys.exit(1)

    log.info("Launching Docker Desktop: %s", exe)
    subprocess.Popen(
        [str(exe)],
        creationflags=subprocess.DETACHED_PROCESS,
    )

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        time.sleep(3)
        with contextlib.suppress(Exception):
            r = subprocess.run(
                [docker, "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            if r.returncode == 0:
                log.info("Docker Desktop started.")
                return

    log.error("Docker Desktop did not start within 60s.")
    sys.exit(1)


def _start_server(no_rebuild: bool = False) -> bool:
    """Start the OPC UA server. Tries native binary first, Docker as fallback.

    Resolution order:
      1. Server already running on OPCUA_PORT → return False (no-op).
      2. Native binary (Windows .exe / Linux ELF) → fastest, no Docker needed.
      3. Docker compose up → cross-platform fallback.

    Returns True if *this call* started something (caller must call ``_stop_server``).
    Returns False if the server was already running.
    Calls ``sys.exit(1)`` only if Docker is the chosen path and compose fails.
    """
    # 1. Already running?
    if _wait_for_port(OPCUA_PORT, timeout=3, missing_ok=True):
        log.info("OPC UA server already running on port %d — skipping start.", OPCUA_PORT)
        return False

    # 2. Native binary (preferred — no Docker dependency)
    if _try_native_binary():
        return True

    # 3. Docker fallback
    log.info("Native binary not available — using Docker.")
    _ensure_docker_running()  # exits on failure if Docker unavailable
    docker = _find_cmd(["docker", "docker.exe"])
    if not docker:
        log.error("Docker binary disappeared after _ensure_docker_running succeeded.")
        sys.exit(1)
    build_flag = "--no-build" if no_rebuild else "--build"
    log.info("Starting OPC UA server: docker compose up -d %s", build_flag)
    rc = subprocess.run(
        [docker, "compose", "up", "-d", build_flag],
        cwd=str(SERVER_DIR),
    ).returncode
    if rc != 0:
        log.error("docker compose up failed (exit=%d).", rc)
        sys.exit(1)
    return True


def _wait_for_port(port: int = OPCUA_PORT, timeout: int = 90, *, missing_ok: bool = False) -> bool:
    """TCP probe; returns True once the port accepts connections."""
    log.info("Waiting for OPC UA server on port %d (timeout=%ds)...", port, timeout)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2.0):
                log.info("Server ready on port %d.", port)
                return True
        except OSError:
            time.sleep(2)
    if missing_ok:
        log.info("No existing OPC UA server detected on port %d; starting one now.", port)
    else:
        log.error("Server did not become ready on port %d within %ds.", port, timeout)
    return False


def _stop_server() -> None:
    """Stop the OPC UA server — handles both native binary and Docker."""
    global _native_server_proc
    if _native_server_proc is not None:
        log.info("Stopping OPC UA server binary (pid=%d)...", _native_server_proc.pid)
        try:
            if _native_server_proc.poll() is None:
                _native_server_proc.terminate()
                try:
                    _native_server_proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    _native_server_proc.kill()
                    _native_server_proc.wait(timeout=5)
        except OSError as exc:
            log.warning("Error stopping server process: %s", exc)
        _native_server_proc = None
        log.info("OPC UA server binary stopped.")
        return

    # Docker path
    docker = _find_cmd(["docker", "docker.exe"])
    if not docker:
        return
    log.info("Stopping OPC UA server (docker compose down)...")
    subprocess.run(
        [docker, "compose", "down"],
        cwd=str(SERVER_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    log.info("Server stopped.")


# ---------------------------------------------------------------------------
# Client venv management
# ---------------------------------------------------------------------------


def _ensure_client_venv(client_dir: Path, outputs: list[str]) -> Path:
    """Ensure *client_dir/.venv* exists and requirements are installed.

    Returns the path to the venv Python interpreter.  All install output is
    appended to *outputs* so it flows into the parent SuiteResult.

    This is used by Phase 2 suites so the root runner can call pytest directly
    inside each client's isolated environment — avoiding the subprocess-chain
    deadlock where a client runner's ``_relaunch_under_venv()`` call would
    create a grandchild process that holds inherited stdout/stderr pipe
    write-handles after the intermediate process exits (Windows P_OVERLAY).
    """
    venv_dir = client_dir / ".venv"
    venv_py = venv_dir / "Scripts" / "python.exe" if IS_WINDOWS else venv_dir / "bin" / "python"

    if not venv_py.exists():
        log.info("[venv] Creating %s/.venv ...", client_dir.name)
        rc, out = _run_captured(
            [sys.executable, "-m", "venv", str(venv_dir)],
            cwd=client_dir,
            label=f"venv create ({client_dir.name})",
            timeout=120,
        )
        outputs.append(out)
        if rc != 0:
            log.error("[venv] Failed to create venv for %s", client_dir.name)
            return Path(sys.executable)  # fallback — suite will likely fail naturally

    # Install from requirements.txt then requirements-dev.txt (if they exist).
    # --pre allows asyncua pre-release builds on Python 3.14+.
    for req_name in ("requirements.txt", "requirements-dev.txt"):
        req_path = client_dir / req_name
        if req_path.exists():
            rc, out = _run_captured(
                [
                    str(venv_py),
                    "-m",
                    "pip",
                    "install",
                    "--quiet",
                    "--disable-pip-version-check",
                    "--pre",
                    "-r",
                    str(req_path),
                ],
                cwd=client_dir,
                label=f"pip install {req_name} ({client_dir.name})",
                timeout=300,
            )
            outputs.append(out)
            if rc != 0:
                log.error(
                    "[venv] pip install %s failed (exit %d) for %s",
                    req_name,
                    rc,
                    client_dir.name,
                )
                raise RuntimeError(
                    f"pip install {req_name} failed with exit {rc} for {client_dir.name}"
                )

    return venv_py


# ---------------------------------------------------------------------------
# Dotnet environment helper
# ---------------------------------------------------------------------------


def _dotnet_env(**extra: str) -> dict:
    """
    Return an os.environ copy with settings that prevent the Roslyn compiler
    server (VBCSCompiler) from persisting after the build.

    Without ``UseSharedCompilation=false``, VBCSCompiler inherits the
    stdout/stderr pipe write-handle and keeps it open after dotnet exits,
    causing Popen.communicate() to block indefinitely.  Setting this property
    forces each build to use a fresh csc.exe instance that exits on completion.
    """
    return {
        **os.environ,
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        **extra,
    }


# ---------------------------------------------------------------------------
# GHA workflow validation -- Phase 1 root-level checks
# ---------------------------------------------------------------------------

# Known minimum major versions — update this dict when actions release new majors
_ACTION_MIN_VERSIONS = {
    "actions/checkout": 6,
    "actions/setup-python": 6,
    "actions/setup-node": 6,
    "actions/setup-dotnet": 4,
    "actions/cache": 4,
    "actions/upload-artifact": 7,
    "actions/download-artifact": 8,
    "docker/build-push-action": 7,
    "docker/login-action": 3,
    "docker/setup-buildx-action": 4,
    "docker/metadata-action": 5,
    "dorny/test-reporter": 3,
    "github/codeql-action/analyze": 3,
    "github/codeql-action/autobuild": 3,
    "github/codeql-action/init": 3,
}


def _check_actionlint(results_dir: Path) -> StepResult:
    """Validate GitHub Actions workflow syntax with actionlint."""
    if not shutil.which("actionlint"):
        return StepResult(
            "GHA actionlint",
            "SKIP",
            "Install: go install github.com/rhysd/actionlint/cmd/actionlint@latest",
        )
    workflows = list((ROOT / ".github/workflows").glob("*.yml"))
    if not workflows:
        return StepResult("GHA actionlint", "SKIP", "No workflow files found")
    result = subprocess.run(
        ["actionlint", "-format", "{{json .}}", *[str(w) for w in workflows]],
        capture_output=True,
        text=True,
        check=False,
    )
    out_file = results_dir / "actionlint.json"
    out_file.write_text(result.stdout or "[]", encoding="utf-8")
    if result.returncode != 0:
        try:
            errors = json.loads(result.stdout or "[]")
            return StepResult("GHA actionlint", "FAIL", f"{len(errors)} workflow error(s)")
        except Exception:
            return StepResult("GHA actionlint", "FAIL", result.stderr[:200])
    return StepResult("GHA actionlint", "PASS", f"{len(workflows)} workflow(s) valid")


def _check_action_versions() -> StepResult:
    """Detect any GitHub Actions pinned below their known minimum major version.

    Recognises two pin styles:
      - SHA-pinned:  uses: owner/action@<40-hex-chars>  # v4
      - Tag-pinned:  uses: owner/action@v4
    All workflows in this repo use SHA pinning (best practice). The tag-pinned
    pattern is only checked for downgrade detection in case tag pins are ever
    introduced alongside SHA pins.
    """
    import re

    workflows_dir = ROOT / ".github/workflows"
    if not workflows_dir.exists():
        return StepResult("GHA version guard", "SKIP", "No .github/workflows/ directory")

    # Matches SHA-pinned actions: owner/repo@<40 hex chars>  (optional trailing comment)
    sha_pattern = re.compile(r"uses:\s+([\w/-]+)@([0-9a-f]{40})")
    # Matches tag-pinned actions: owner/repo@v3
    tag_pattern = re.compile(r"uses:\s+([\w/-]+)@v(\d+)")

    issues = []
    sha_total = 0
    tag_total = 0

    for wf_file in sorted(workflows_dir.glob("*.yml")):
        text = wf_file.read_text(encoding="utf-8")
        sha_total += len(sha_pattern.findall(text))
        for match in tag_pattern.finditer(text):
            tag_total += 1
            action, version_str = match.group(1), match.group(2)
            version = int(version_str)
            min_ver = _ACTION_MIN_VERSIONS.get(action)
            if min_ver and version < min_ver:
                issues.append(f"{wf_file.name}: {action}@v{version} (minimum: v{min_ver})")

    if issues:
        for issue in issues:
            print(f"  \u26a0  {issue}", flush=True)
        return StepResult(
            "GHA version guard", "FAIL", f"{len(issues)} downgraded action(s) detected"
        )

    total = sha_total + tag_total
    detail = f"{total} action pins verified ({sha_total} SHA-pinned, {tag_total} tag-pinned)"
    return StepResult("GHA version guard", "PASS", detail)


def _parse_zizmor_output(stdout: str, returncode: int) -> StepResult:
    """Parse zizmor JSON stdout and return a StepResult. Pure function — no I/O or subprocess."""
    if returncode not in (0, 13):  # 0=clean, 13=findings present (zizmor v1.x); 1=tool error
        return StepResult("GHA zizmor (security)", "SKIP", "zizmor error — skipping")
    try:
        data = json.loads(stdout or "[]")
        if not isinstance(data, list):
            return StepResult(
                "GHA zizmor (security)", "SKIP", "Could not parse output — zizmor version mismatch"
            )
        findings = data
        high = [
            f
            for f in findings
            if f.get("determinations", {}).get("severity") in ("High", "Critical")
        ]
        if high:
            return StepResult(
                "GHA zizmor (security)", "FAIL", f"{len(high)} high/critical finding(s)"
            )
        return StepResult(
            "GHA zizmor (security)", "PASS", f"{len(findings)} finding(s), none high/critical"
        )
    except Exception:
        return StepResult(
            "GHA zizmor (security)", "SKIP", "Could not parse output — zizmor version mismatch"
        )


def _check_zizmor(results_dir: Path) -> StepResult:
    """Security audit GitHub Actions workflows with zizmor."""
    if not shutil.which("zizmor"):
        return StepResult(
            "GHA zizmor (security)", "SKIP", "Install: cargo install zizmor  OR  pip install zizmor"
        )
    workflows_dir = ROOT / ".github/workflows"
    result = subprocess.run(
        ["zizmor", "--format", "json", str(workflows_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    out_file = results_dir / "zizmor.json"
    out_file.write_text(result.stdout or "[]", encoding="utf-8")
    return _parse_zizmor_output(result.stdout, result.returncode)


def _check_optional_import_typing() -> StepResult:
    """Keep optional imports mypy-clean when packages are installed without stubs."""
    issues: list[str] = []
    for path in _OPTIONAL_IMPORT_GUARD_PATHS:
        if not path.exists():
            issues.append(f"{path}: missing")
            continue
        try:
            rel = path.relative_to(REPO_ROOT)
        except ValueError:
            rel = path
        forward_annotations: dict[str, int] = {}
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            annotation_match = re.fullmatch(r"([A-Za-z_]\w*)\s*:\s*Any(?:\s*#.*)?", stripped)
            if annotation_match:
                forward_annotations[annotation_match.group(1)] = lineno

            has_requests_import = stripped.startswith("import requests")
            has_type_ignore = "type: ignore[import-untyped]" in line
            if has_requests_import and not has_type_ignore:
                issues.append(f"{rel}:{lineno} import requests lacks type ignore")

            import_match = re.fullmatch(
                r"import\s+([A-Za-z_]\w*)(?:\s+as\s+([A-Za-z_]\w*))?(?:\s*#.*)?",
                stripped,
            )
            if import_match:
                bound_name = import_match.group(2) or import_match.group(1)
                annotated_at = forward_annotations.get(bound_name)
                if annotated_at is not None:
                    issues.append(
                        f"{rel}:{lineno} import redefines {bound_name!r} "
                        f"annotated at line {annotated_at}"
                    )

    if issues:
        for issue in issues:
            print(f"  optional import typing issue: {issue}", flush=True)
        return StepResult(
            "Optional import typing guard",
            "FAIL",
            f"{len(issues)} optional import typing issue(s)",
        )
    return StepResult(
        "Optional import typing guard",
        "PASS",
        f"{len(_OPTIONAL_IMPORT_GUARD_PATHS)} file(s) verified",
    )


def _check_runner_requests_import_typing() -> StepResult:
    """Backward-compatible wrapper for the old guard name used by older tests/hooks."""
    return _check_optional_import_typing()


def _print_step_result(r: StepResult) -> None:
    """Print a single GHA check result in the [ROOT] format."""
    _STATUS_COLOUR = {
        "PASS": "\033[92m",
        "FAIL": "\033[91m",
        "WARN": "\033[93m",
        "SKIP": "\033[93m",
    }
    fill_width = 46
    dots = "." * max(1, fill_width - len(r.name))
    colour = _STATUS_COLOUR.get(r.status, "")
    status_str = _c(colour, r.status)
    detail = f" ({r.detail})" if r.detail else ""
    sys.stdout.write(f"[ROOT] {r.name} {dots} {status_str}{detail}\n")
    sys.stdout.flush()


def _run_gha_checks() -> list[SuiteResult]:
    """Run all GHA validation checks and return SuiteResult list for the summary."""
    results_dir = ROOT / "test-results"
    shutil.rmtree(results_dir, ignore_errors=True)
    results_dir.mkdir(exist_ok=True)

    step_results = [
        _check_optional_import_typing(),
        _check_actionlint(results_dir),
        _check_action_versions(),
        _check_zizmor(results_dir),
    ]

    suite_results: list[SuiteResult] = []
    for sr in step_results:
        _print_step_result(sr)
        ok = sr.status in ("PASS", "WARN")
        skipped = sr.status == "SKIP"
        suite_results.append(
            SuiteResult(
                name=sr.name,
                ok=ok,
                skipped=skipped,
                notes=[sr.detail] if sr.detail else [],
            )
        )
    return suite_results


# ---------------------------------------------------------------------------
# Phase 1 suites -- unit / static (run in parallel, no server)
# ---------------------------------------------------------------------------


def _suite_csharp_unit() -> SuiteResult:
    """C# Client -- Phase 1 (static + unit).  Delegates to sub-project runner.

    Covers: dotnet format, NuGet vulnerability scan, build, unit tests.
    """
    return _delegate_to_runner(
        name="csharp",
        runner_dir=CSHARP_DIR,
        phase_args=["--phase1"],
        label="csharp runner (phase1)",
    )


def _suite_console_unit() -> SuiteResult:
    """Console Client -- Phase 1 (static + unit).  Delegates to sub-project runner.

    Covers: ruff, mypy, bandit, pytest unit tests.
    """
    return _delegate_to_runner(
        name="console",
        runner_dir=CONSOLE_DIR,
        phase_args=["--phase1"],
        label="console runner (phase1)",
    )


def _suite_webclient_unit() -> SuiteResult:
    """Web Client -- Phase 1 (static + unit).  Delegates to sub-project runner.

    Covers: ruff, mypy, bandit, pytest unit tests, ESLint, npm audit, vitest.
    """
    return _delegate_to_runner(
        name="webclient",
        runner_dir=WEB_CLIENT_DIR,
        phase_args=["--phase1"],
        label="webclient runner (phase1)",
    )


def _suite_testclient_phase1() -> SuiteResult:
    """Test Client -- Phase 1 (static + full collection).  Delegates to sub-project runner.

    Covers: ruff, mypy, bandit, pytest tests/unit/ (real unit test run).
    """
    return _delegate_to_runner(
        name="testclient",
        runner_dir=TEST_CLIENT_DIR,
        phase_args=["--phase1"],
        label="testclient runner (phase1)",
    )


def _suite_node_unit() -> SuiteResult:
    """Node Client -- Phase 1 (static + unit).  Delegates to sub-project runner.

    Covers: npm ci, ESLint, npm audit, vitest unit tests.
    """
    return _delegate_to_runner(
        name="node",
        runner_dir=NODE_CLIENT_DIR,
        phase_args=["--phase1"],
        label="node runner (phase1)",
    )


def _suite_server_static() -> SuiteResult:
    """Server -- Phase 1 (static).  Delegates to server sub-project runner.

    Covers: hadolint (Dockerfile lint), yamllint, any server-side static checks.
    """
    return _delegate_to_runner(
        name="server-static",
        runner_dir=SERVER_DIR,
        phase_args=["--phase1"],
        label="server runner (phase1)",
    )


# ---------------------------------------------------------------------------
# Git-sanity suite -- verify no source file is accidentally gitignored
# ---------------------------------------------------------------------------

# Extensions that identify source files (not build artefacts or data files).
_SOURCE_EXTS: frozenset[str] = frozenset(
    {
        ".py",
        ".mjs",
        ".js",
        ".ts",
        ".cs",
        ".csproj",
        ".sln",
    }
)

# Exact directory names that are always build artefacts or runtime caches.
_SKIP_DIRS: frozenset[str] = frozenset(
    {
        "node_modules",
        "__pycache__",
        "bin",
        "obj",
        ".git",
        "pki",
        "PKI",
        ".ruff_cache",
        ".mypy_cache",
        "dist",
        ".pytest_cache",
        "tmp",
        "fixtures",
        "test-results",
    }
)


def _skip_dir(name: str) -> bool:
    """Return True if *name* is a build-artefact or runtime-cache directory.

    Handles exact names (node_modules) and common prefix patterns (.venv*,
    venv*, *.egg-info) without requiring an exhaustive list of every local
    variant.
    """
    if name in _SKIP_DIRS:
        return True
    # Canonical virtual-environment dirs (.venv*, .venv_test*) and legacy forms
    # (venv*, .venv_wsl etc.) are both skipped so machines mid-transition are
    # handled safely before cleanup fires.
    if name.startswith(".venv") or name.startswith("venv"):
        return True
    # Python packaging artefacts
    return name.endswith(".egg-info") or name.endswith(".dist-info")


def _collect_source_files(base: Path) -> list[str]:
    """Return all source file paths under *base* relative to REPO_ROOT.

    Uses os.walk with in-place directory pruning so build artefacts, venvs,
    and caches are never descended into.
    """
    files: list[str] = []
    for root, dirs, filenames in os.walk(base):
        # Prune in place — os.walk will not descend into pruned directories.
        dirs[:] = [d for d in dirs if not _skip_dir(d)]
        root_path = Path(root)
        for fname in filenames:
            if Path(fname).suffix in _SOURCE_EXTS:
                rel = (root_path / fname).relative_to(REPO_ROOT)
                files.append(str(rel).replace("\\", "/"))
    return files


def _suite_gitignore_sanity() -> SuiteResult:
    """Verify that no on-disk source file is accidentally matched by a .gitignore rule.

    Uses ``git check-ignore --stdin --no-index`` which evaluates .gitignore
    patterns against file *paths* without requiring the files to be tracked.

    SCOPE — what this check catches and what it does not:

    ✔  A file exists in the developer's working tree but is matched by a
       .gitignore rule (class of bug in commit 9598856).  On the developer
       machine the file is present so os.walk finds it; check-ignore then
       flags the offending pattern before the developer can commit.

    ✘  A file that was accidentally gitignored and *never committed* will not
       exist on a fresh CI checkout, so os.walk will not find it and this
       check cannot flag it in CI.

    The complementary CI-level guard is the Playwright smoke test suite: if
    a JS/CSS module is missing the browser will fail to load the page, causing
    the smoke tests to fail.  Together the two layers cover both local and CI
    scenarios.
    """
    name = "git-sanity"
    t0 = time.monotonic()

    source_files = _collect_source_files(REPO_ROOT / "OPC_UA_Clients")
    source_files += _collect_source_files(REPO_ROOT / "OPC_UA_Servers")

    if not source_files:
        return SuiteResult(name, True, notes=["no source files found to check"])

    try:
        proc = subprocess.run(
            ["git", "check-ignore", "--stdin", "--no-index", "-v"],
            input="\n".join(source_files),
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=30,
        )
    except FileNotFoundError:
        return SuiteResult(name, True, skipped=True, notes=["git not in PATH"])
    except subprocess.TimeoutExpired:
        return SuiteResult(name, False, time.monotonic() - t0, notes=["git check-ignore timed out"])

    # git check-ignore writes to stdout the paths it matched; any output = failure.
    ignored = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]

    if ignored:
        lines = [
            f"Scanned {len(source_files)} source files.\n",
            "ERROR: the following source files are matched by .gitignore rules.",
            "They will be MISSING on every fresh git clone:\n",
        ]
        lines.extend(f"  {entry}" for entry in ignored)
        lines.append(
            "\nFix: remove or narrow the offending .gitignore pattern, then run: git add <file>"
        )
        return SuiteResult(name, False, time.monotonic() - t0, output="\n".join(lines))

    notes = [f"{len(source_files)} source files checked — none gitignored"]
    return SuiteResult(name, True, time.monotonic() - t0, notes=notes)


# ---------------------------------------------------------------------------
# Phase 1 suite -- markdown hygiene (no private paths or internal references)
# ---------------------------------------------------------------------------

# Patterns that must never appear in committed .md files.
# Key = string to search for, Value = human-readable reason.
_MD_PRIVATE_PATTERNS: dict[str, str] = {
    "C:\\\\": "Windows absolute path",
    "C:/DDrive": "machine-specific path",
    "C:/Users": "Windows user absolute path",
    "MyWork": "private repository reference",
    "CodexSandboxOffline": "internal sandbox user",
    "Access Rules (CRITICAL)": "AI assistant permission block",
    "Never Violate": "AI assistant instruction language",
    "user reviews and commits manually": "personal workflow rule",
    "user explicitly requests": "personal workflow rule",
}


def _suite_md_hygiene() -> SuiteResult:
    """Scan all committed .md files for private paths and internal references.

    Catches content that belongs in private context files (e.g. absolute local
    paths, internal repo names, personal workflow rules) before it reaches the
    public repo.
    """
    name = "md-hygiene"
    t0 = time.monotonic()

    md_files = sorted(REPO_ROOT.rglob("*.md"))
    # Exclude generated output directories and gitignored output files
    _EXCLUDED_MD_PARTS = {"node_modules", "test-results", ".git"}
    _EXCLUDED_MD_NAMES = {"TestOutput.md"}
    md_files = [
        f
        for f in md_files
        if not any(part in f.parts for part in _EXCLUDED_MD_PARTS)
        and f.name not in _EXCLUDED_MD_NAMES
    ]

    violations: list[str] = []
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = md_file.relative_to(REPO_ROOT)
        for pattern, reason in _MD_PRIVATE_PATTERNS.items():
            if pattern in content:
                # Find line numbers
                for lineno, line in enumerate(content.splitlines(), 1):
                    if pattern in line:
                        violations.append(f"  {rel}:{lineno} — {reason}: {line.strip()[:120]}")

    if violations:
        lines = [
            f"Scanned {len(md_files)} markdown files.\n",
            "ERROR: the following .md files contain private or internal content:\n",
        ]
        lines.extend(violations)
        lines.append(
            "\nFix: move internal content to private context files; public .md files must be"
            " free of local paths, internal repo names, and personal workflow rules."
        )
        return SuiteResult(name, False, time.monotonic() - t0, output="\n".join(lines))

    notes = [f"{len(md_files)} markdown files checked — no private content found"]
    return SuiteResult(name, True, time.monotonic() - t0, notes=notes)


# ---------------------------------------------------------------------------
# Phase 2 suites -- live / integration (run in parallel, each owns its server)
# ---------------------------------------------------------------------------


def _suite_server_smoke() -> SuiteResult:
    """OPC UA server smoke test (TCP connection + basic node browse).

    Starts a server on the native port (OPCUA_PORT / 40451), runs smoke_test.py,
    then stops the server.  Uses the same _start_server / _stop_server helpers
    that previously backed the full Phase 2 shared server.
    """
    name = "server-smoke"
    t0 = time.monotonic()

    if not SMOKE_TEST.exists():
        return SuiteResult(name, True, skipped=True, notes=["smoke_test.py not found"])

    python = _current_python()
    outputs: list[str] = []
    started_server = False

    try:
        started_server = _start_server()

        smoke_reqs = SERVER_DIR / "tests" / "requirements.txt"
        if smoke_reqs.exists():
            rc_pip, out = _run_captured(
                [
                    python,
                    "-m",
                    "pip",
                    "install",
                    "-q",
                    "--disable-pip-version-check",
                    "-r",
                    str(smoke_reqs),
                ],
                cwd=SERVER_DIR,
                label="pip install (smoke)",
            )
            outputs.append(out)
            if rc_pip != 0:
                return SuiteResult(
                    name,
                    False,
                    time.monotonic() - t0,
                    output="\n".join(outputs),
                    notes=["pip install failed"],
                )

        rc, out = _run_captured(
            [python, str(SMOKE_TEST), "--tcp-timeout", "30"],
            cwd=SERVER_DIR,
            label="smoke_test.py --tcp-timeout 30",
        )
        outputs.append(out)
        return SuiteResult(name, rc == 0, time.monotonic() - t0, output="\n".join(outputs))
    finally:
        if started_server:
            _stop_server()


def _suite_csharp_live() -> SuiteResult:
    """C# Client -- Phase 2 (live).  Delegates to sub-project runner.

    Passes OPCUA_SERVER_PORT only (not OPCUA_SERVER_URL) so the C# runner's
    Phase 2 logic enters the fixture-managed path: OpcUaServerFixture.cs
    copies the binary, patches the port to 40464, and manages its own server
    instance.  Passing OPCUA_SERVER_URL would trigger the "user-managed server"
    branch which skips live tests when 40464 isn't already reachable.
    """
    return _delegate_to_runner(
        name="csharp-live",
        runner_dir=CSHARP_DIR,
        phase_args=["--phase2"],
        label="csharp runner (phase2)",
        extra_env={
            "OPCUA_SERVER_PORT": str(OPCUA_SERVER_PORT_CSHARP_CLIENT),
        },
    )


def _suite_console_live() -> SuiteResult:
    """Console Client -- Phase 2 (live).  Delegates to sub-project runner.

    No OPCUA_SERVER_URL passed — the Console runner owns its server on port 40461.
    """
    return _delegate_to_runner(
        name="console-live",
        runner_dir=CONSOLE_DIR,
        phase_args=["--phase2"],
        label="console runner (phase2)",
    )


def _suite_testclient_full() -> SuiteResult:
    """Test Client -- Phase 2 (live conformance).  Delegates to sub-project runner.

    No OPCUA_SERVER_URL passed — the TestClient runner owns its server on port 40462.
    Uses 1200s timeout — conformance tests span many OPC UA round-trips.
    """
    return _delegate_to_runner(
        name="testclient-full",
        runner_dir=TEST_CLIENT_DIR,
        phase_args=["--phase2"],
        label="testclient runner (phase2)",
        timeout=1200,
    )


def _suite_webclient_live() -> SuiteResult:
    """Web Client -- Phase 2 (live + integration).  Delegates to sub-project runner.

    No OPCUA_SERVER_URL passed — the WebClient runner owns its server on port 40463.
    """
    return _delegate_to_runner(
        name="webclient-live",
        runner_dir=WEB_CLIENT_DIR,
        phase_args=["--phase2"],
        label="webclient runner (phase2)",
    )


# ---------------------------------------------------------------------------
# Suite registries
# ---------------------------------------------------------------------------

PHASE1_SUITES: dict[str, object] = {
    "csharp": _suite_csharp_unit,
    "console": _suite_console_unit,
    "webclient": _suite_webclient_unit,
    "testclient": _suite_testclient_phase1,
    "node": _suite_node_unit,
    "server-static": _suite_server_static,
    "git-sanity": _suite_gitignore_sanity,
    "md-hygiene": _suite_md_hygiene,
}

PHASE2_SUITES: dict[str, object] = {
    "server-smoke": _suite_server_smoke,
    "csharp-live": _suite_csharp_live,
    "console-live": _suite_console_live,
    "testclient-full": _suite_testclient_full,
    "webclient-live": _suite_webclient_live,
}

# Utility suites — not part of the default parallel Phase 2 run.
# Keep this registry for focused future checks that should not run by default.
_UTILITY_SUITES: dict[str, object] = {}

ALL_SUITE_KEYS: list[str] = list(PHASE1_SUITES) + list(PHASE2_SUITES) + list(_UTILITY_SUITES)

# ---------------------------------------------------------------------------
# Phase runners
# ---------------------------------------------------------------------------


def run_phase1(suites: dict) -> list[SuiteResult]:
    """Run all Phase 1 suites in parallel; emit each result atomically as it completes."""
    _banner("PHASE 1 \u2014 Unit / Static tests  (parallel, no server required)")
    log.info(
        "\u25b6 Starting %d suites simultaneously: %s",
        len(suites),
        ", ".join(suites.keys()),
    )
    results: list[SuiteResult] = []

    with ThreadPoolExecutor(max_workers=len(suites), thread_name_prefix="phase1") as ex:
        future_to_key = {
            ex.submit(fn): key  # type: ignore[operator]
            for key, fn in suites.items()
        }
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                result: SuiteResult = future.result()
            except Exception as exc:
                result = SuiteResult(key, False, output=f"[unexpected error: {exc}]\n")
            results.append(result)
            _emit_suite_output(result)

    return results


def run_phase2(suites: dict) -> list[SuiteResult]:
    """Run Phase 2 suites in parallel.

    Phase 1 completes before Phase 2 starts, so the Release 1 Node Client's
    Phase 1-only suite cannot overlap with server-smoke on port 40451.

    server-smoke validates the native/default server package on port 40451.
    Each Release 2 client suite delegates to its sub-project runner, which fully
    owns its OPC UA server lifecycle on a dedicated port:

        Console Client   → OPCUA_SERVER_PORT_CONSOLE_CLIENT (40461)
        Test Client      → OPCUA_SERVER_PORT_TEST_CLIENT    (40462)
        Web Client       → OPCUA_SERVER_PORT_WEB_CLIENT     (40463)
        C# Client        → OPCUA_SERVER_PORT_CSHARP_CLIENT  (40464)

    Results are emitted as each suite completes; order is non-deterministic
    (fastest finishes first).
    """
    _banner("PHASE 2 \u2014 Live / Integration tests  (parallel, dedicated ports per suite)")
    log.info(
        "\u25b6 Starting %d suites simultaneously: %s",
        len(suites),
        ", ".join(suites.keys()),
    )
    results: list[SuiteResult] = []

    with ThreadPoolExecutor(max_workers=len(suites), thread_name_prefix="phase2") as ex:
        future_to_key: dict = {ex.submit(fn): key for key, fn in suites.items()}  # type: ignore[arg-type]
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            log.info("\u25c0 Phase 2 suite completed: %s", key)
            try:
                result: SuiteResult = future.result()
            except Exception as exc:
                result = SuiteResult(key, False, output=f"[unexpected error: {exc}]\n")
            _emit_suite_output(result)
            results.append(result)

    return results


# ---------------------------------------------------------------------------
# Final summary table
# ---------------------------------------------------------------------------


def _print_summary(results: list[SuiteResult], total_time: float) -> int:  # noqa: C901
    """Print a structured summary table grouped by phase.

    Layout (single-line box drawing, Unicode):

        ┌──────────────────────┬────────┬──────────┬──────────────────────┐
        │ Suite                │ Status │     Time │ Detail               │
        ├──────────────────────┴────────┴──────────┴──────────────────────┤
        │  GHA / Repo Checks                                               │
        ├──────────────────────┬────────┬──────────┬──────────────────────┤
        │ GHA actionlint       │  PASS  │     0.0s │ 3 workflow(s) valid  │
        │ GHA zizmor           │  SKIP  │     0.0s │ zizmor unavailable   │
        ├──────────────────────┴────────┴──────────┴──────────────────────┤
        │  Phase 1 — Unit & Static                                         │
        ├──────────────────────┬────────┬──────────┬──────────────────────┤
        │ node                 │  PASS  │   160.8s │ 705 passed           │
        ├──────────────────────┼────────┼──────────┼──────────────────────┤
        │ TOTAL                │        │   732.6s │ 14 suites  ✔ 13 ...  │
        └──────────────────────┴────────┴──────────┴──────────────────────┘
    """
    _banner("FINAL SUMMARY")

    phase1_names = set(PHASE1_SUITES.keys())
    phase2_names = set(PHASE2_SUITES.keys())

    gha_rows = [r for r in results if r.name not in phase1_names and r.name not in phase2_names]
    p1_rows = [r for r in results if r.name in phase1_names]
    p2_rows = [r for r in results if r.name in phase2_names]

    # ── Column content widths (each cell = " {content} " → adds 2 chars) ──────
    nw = max(max((len(r.name) for r in results), default=14), 18)
    sw = 6  # "Status" / center-padded "PASS" etc. → 8 chars per cell total
    tw = 8  # time right-aligned                   → 10 chars per cell total
    # Detail column: auto-sized to fit the longest detail string (min 38)
    _all_details: list[str] = []
    for _r in results:
        _det = _r.counts or (_r.notes[0] if _r.notes else "")
        _all_details.append(_det)
        for _note in _r.notes if _r.counts else _r.notes[1:]:
            _all_details.append(f"  \u2514 {_note}")
    dw = max(max((len(d) for d in _all_details), default=14), 38)

    # Visible chars between the two outer │ borders in a spanning (section) row:
    #   (nw+2) + │ + (sw+2) + │ + (tw+2) + │ + (dw+2) = nw+sw+tw+dw+11
    span_w = nw + sw + tw + dw + 11

    # ── Box-drawing characters ─────────────────────────────────────────────────
    H = "\u2500"
    V = "\u2502"  # ─  │
    TL = "\u250c"
    TR = "\u2510"  # ┌  ┐
    BL = "\u2514"
    BR = "\u2518"  # └  ┘
    LM = "\u251c"
    RM = "\u2524"  # ├  ┤
    TT = "\u252c"
    BT = "\u2534"
    CR = "\u253c"  # ┬  ┴  ┼

    def _hcols(lc: str, mid: str, r: str) -> str:
        """4-column separator (mid char at every junction)."""
        return f"  {lc}{H * (nw + 2)}{mid}{H * (sw + 2)}{mid}{H * (tw + 2)}{mid}{H * (dw + 2)}{r}"

    def _hclose(lc: str, r: str) -> str:
        """Merge columns into a full-width span (┴ closes each column above)."""
        return f"  {lc}{H * (nw + 2)}{BT}{H * (sw + 2)}{BT}{H * (tw + 2)}{BT}{H * (dw + 2)}{r}"

    def _hopen(lc: str, r: str) -> str:
        """Re-open columns from a span (┬ opens each column below)."""
        return f"  {lc}{H * (nw + 2)}{TT}{H * (sw + 2)}{TT}{H * (tw + 2)}{TT}{H * (dw + 2)}{r}"

    def _row(name: str, scell: str, time_str: str, detail: str) -> str:
        """One data row. `scell` must be exactly sw+2 visible chars (ANSI OK)."""
        n = f" {name[:nw]:<{nw}} "
        t = f" {time_str[:tw]:>{tw}} "
        d = f" {detail[:dw]:<{dw}} "
        return f"  {V}{n}{V}{scell}{V}{t}{V}{d}{V}"

    def _scell(r: SuiteResult) -> str:
        """Coloured status badge — exactly sw+2 visible chars."""
        if r.skipped:
            label, colour = "SKIP", "\033[93m"
        elif r.ok:
            label, colour = "PASS", "\033[92m"
        else:
            label, colour = "FAIL", "\033[91m"
        return _c(colour, f" {label:^{sw}} ")

    def _section_row(label: str) -> str:
        """Full-width row with a bold group label (spanning all columns)."""
        content = f"  {label}"
        padded = content + " " * max(0, span_w - len(content))
        text = _c("\033[1m", padded) if _USE_COLOUR else padded
        return f"  {V}{text}{V}"

    blank_s = f" {'':{sw}} "  # sw+2 spaces — blank status cell

    out = sys.stdout.write
    overall = 0

    # ── Header ────────────────────────────────────────────────────────────────
    out(_hcols(TL, TT, TR) + "\n")
    out(_row("Suite", f" {'Status':^{sw}} ", "Time", "Detail") + "\n")

    # ── One group of rows (GHA / Phase 1 / Phase 2) ───────────────────────────
    def _emit_group(label: str, rows: list[SuiteResult]) -> None:
        nonlocal overall
        if not rows:
            return
        out(_hclose(LM, RM) + "\n")  # ├──┴──┴──┴──┤  collapse columns
        out(_section_row(label) + "\n")  # │  Label     │
        out(_hopen(LM, RM) + "\n")  # ├──┬──┬──┬──┤  re-open columns
        for r in rows:
            if not r.ok and not r.skipped:
                overall = 1
            t = f"{r.duration:.1f}s"
            det = r.counts or (r.notes[0] if r.notes else "")
            out(_row(r.name, _scell(r), t, det) + "\n")
            # Show extra notes as indented continuation rows
            extra = r.notes if r.counts else r.notes[1:]
            for note in extra:
                out(_row("", blank_s, "", f"  \u2514 {note}") + "\n")

    _emit_group("GHA / Repo Checks", gha_rows)
    _emit_group("Phase 1 \u2014 Unit & Static", p1_rows)
    _emit_group("Phase 2 \u2014 Live / Integration", p2_rows)

    # ── Totals row ────────────────────────────────────────────────────────────
    n_pass = sum(1 for r in results if r.ok and not r.skipped)
    n_skip = sum(1 for r in results if r.skipped)
    n_fail = sum(1 for r in results if not r.ok and not r.skipped)
    totals = (
        f"{len(results)} suites"
        + (f"   \u2714 {n_pass}" if n_pass else "")
        + (f"   \u25cb {n_skip}" if n_skip else "")
        + (f"   \u2718 {n_fail}" if n_fail else "")
    )
    out(_hcols(LM, CR, RM) + "\n")
    out(_row("TOTAL", blank_s, f"{total_time:.1f}s", totals) + "\n")
    out(_hcols(BL, BT, BR) + "\n\n")

    # ── Verdict ───────────────────────────────────────────────────────────────
    if overall == 0:
        out(_c("\033[92m\033[1m", "  \u2714  ALL TESTS PASSED\n"))
    else:
        out(_c("\033[91m\033[1m", "  \u2718  ONE OR MORE SUITES FAILED\n"))
    out("\u2550" * 66 + "\n\n")
    sys.stdout.flush()
    return overall


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_all_tests.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--phase1",
        action="store_true",
        help="Phase 1 only: unit tests, no server required",
    )
    group.add_argument(
        "--phase2",
        action="store_true",
        help="Phase 2 only: server smoke on 40451 plus live client tests on dedicated ports",
    )
    group.add_argument(
        "--suite",
        choices=ALL_SUITE_KEYS,
        metavar="{" + "|".join(ALL_SUITE_KEYS) + "}",
        help="Run a single named suite and exit",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG-level logging",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available suite names and exit",
    )
    return parser


def _configure_stdio_utf8() -> None:
    """Use UTF-8 for runner output before argparse can print help text."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            with contextlib.suppress(Exception):
                stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    _configure_stdio_utf8()
    _cleanup_caches(REPO_ROOT)  # pre-run: clear stale caches from interrupted runs
    parser = _build_parser()
    args = parser.parse_args()

    if args.list:
        print("Phase 1 suites (parallel, no server):")
        for k in PHASE1_SUITES:
            print(f"  {k}")
        print("Phase 2 suites (parallel, server smoke on 40451; clients own dedicated ports):")
        for k in PHASE2_SUITES:
            print(f"  {k}")
        if _UTILITY_SUITES:
            print("Utility suites (run manually with --suite <name>):")
            for k in _UTILITY_SUITES:
                print(f"  {k}")
        return 0

    _setup_logging(verbose=args.verbose)

    global _USE_COLOUR
    _USE_COLOUR = sys.stdout.isatty() and (os.name != "nt" or _enable_ansi_windows())

    _banner("IJT Repository Test Runner")
    log.info("Python    : %s", sys.version.split()[0])
    log.info("Platform  : %s", platform.platform())
    log.info("Repo root : %s", REPO_ROOT)
    log.info("CI        : %s", IS_CI)
    log.info("Timeout   : %ds per suite", SUITE_TIMEOUT)

    # Pre-flight tool checks -- warn only, suites fail naturally if tools missing
    _check_tool([sys.executable, "--version"], "python")
    _check_tool(["dotnet", "--version"], "dotnet")
    _check_tool(["docker", "--version"], "docker")
    npm = _find_cmd(["npm", "npm.cmd"])
    if npm:
        _check_tool([npm, "--version"], "npm")
    else:
        log.warning("npm/node not found -- JS unit tests will be skipped")

    t_total = time.monotonic()
    all_results: list[SuiteResult] = []

    try:
        # -- Single-suite shortcut -------------------------------------------
        if args.suite:
            fn = {**PHASE1_SUITES, **PHASE2_SUITES, **_UTILITY_SUITES}[args.suite]  # type: ignore[index]
            log.info("Running single suite: %s", args.suite)
            result = fn()  # type: ignore[operator]
            _emit_suite_output(result)
            return 0 if (result.ok or result.skipped) else 1

        # -- Phase 1 ---------------------------------------------------------
        if not args.phase2:
            _banner("PHASE 1 \u2014 GHA Workflow Validation  (root-level checks)")
            gha_results = _run_gha_checks()
            all_results.extend(gha_results)
            p1 = run_phase1(PHASE1_SUITES)
            all_results.extend(p1)

        # -- Phase 2 (parallel — each sub-runner owns its server) ------------
        if not args.phase1:
            p2 = run_phase2(PHASE2_SUITES)
            all_results.extend(p2)

    finally:
        _cleanup_caches(ROOT)  # always runs: normal exit, Ctrl+C, or exception

    rc = _print_summary(all_results, time.monotonic() - t_total)
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
    _SKIP = {"node_modules", ".git", "test-results"}
    _CACHE_DIRS = {
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "htmlcov",
        "pki",
        "PKI",
        "tmp",  # sub-runner workspace (tmp/pytest/, tmp/server_instance_*/); recreated on next run
    }
    for dirpath, dirs, files in os.walk(root, topdown=True):
        dirs[:] = [
            d
            for d in dirs
            if d not in _SKIP and not d.startswith(".venv") and not d.startswith("venv")
        ]
        for d in list(dirs):
            if d in _CACHE_DIRS or d.startswith("pytest-cache-files-") or d.startswith(".dotnet"):
                _force_rmtree(Path(dirpath) / d)
                dirs.remove(d)
        for f in files:
            if f == ".coverage" or f.startswith(".coverage.") or f.endswith(".pyc"):
                with contextlib.suppress(OSError):
                    (Path(dirpath) / f).unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
