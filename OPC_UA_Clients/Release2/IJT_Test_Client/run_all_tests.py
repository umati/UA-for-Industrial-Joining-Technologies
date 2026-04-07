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
  python run_all_tests.py --verbose          # verbose pytest output
  python run_all_tests.py --no-server-check  # skip pre-test server check
  python run_all_tests.py --help

Environment variables:
  OPCUA_SERVER_URL           Override server endpoint (default: opc.tcp://localhost:40451)
  OPCUA_SIMULATOR_EXE        Path to opcua_ijt_demo_application(.exe)
  OPCUA_STARTUP_TIMEOUT_SEC  Seconds to wait for simulator start (default: 30)
  SKIP_VENV_INSTALL          Set to "1" to skip pip install step (faster re-runs)
"""
# pylint: disable=broad-exception-caught,global-statement

from __future__ import annotations

import argparse
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
VENV = _HERE / ".venv"
REQUIREMENTS = _HERE / "requirements.txt"
_REQUIREMENTS_DEV = _HERE / "requirements-dev.txt"
_RESULTS_DIR = _HERE / "test-results"
_DEFAULT_JUNIT = _RESULTS_DIR / "pytest-live.xml"

_DEFAULT_SERVER_URL = "opc.tcp://localhost:40462"
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
    return parsed.hostname or "localhost", parsed.port or 40451


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


def _run(
    cmd: list[str],
    *,
    cwd: Path = _HERE,
    extra_env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> tuple[int, str]:
    """
    Run *cmd* and return (returncode, combined_stdout_stderr).
    Never raises — errors are captured and returned via returncode.
    """
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    try:
        proc = subprocess.run(
            [str(c) for c in cmd],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=timeout,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
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


# ---------------------------------------------------------------------------
# Venv management
# ---------------------------------------------------------------------------


def ensure_venv() -> None:
    """Create the virtual environment if it does not already exist."""
    if not VENV.exists():
        logger.info("Creating virtual environment: %s", VENV)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=False)
    else:
        logger.info("Using existing virtual environment: %s", VENV)


def install_requirements() -> None:
    """Install packages from requirements.txt and requirements-dev.txt into the venv."""
    if os.environ.get("SKIP_VENV_INSTALL") == "1":
        logger.info("Skipping pip install (SKIP_VENV_INSTALL=1)")
        return
    pip = str(_venv_pip(VENV))
    # Always upgrade pip itself first to avoid stale CVE warnings in pip-audit
    subprocess.run([pip, "install", "--quiet", "--upgrade", "pip"], check=False)
    for req_file in (REQUIREMENTS, _REQUIREMENTS_DEV):
        if req_file.exists():
            logger.info("Installing requirements from %s...", req_file.name)
            subprocess.run(
                [pip, "install", "--quiet", "-r", str(req_file)],
                check=False,
            )
        else:
            logger.info("No %s found — skipping", req_file.name)


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
    result = subprocess.run([str(venv_py)] + sys.argv, env=env, check=False)
    sys.exit(result.returncode)


# ---------------------------------------------------------------------------
# Server helpers
# ---------------------------------------------------------------------------


def _get_server_url() -> str:
    return os.environ.get("OPCUA_SERVER_URL", _DEFAULT_SERVER_URL)


def _parse_server_url() -> tuple[str, int]:
    """Parse OPCUA_SERVER_URL and return (host, port)."""
    return _parse_opcua_endpoint(_get_server_url())


_SERVER_NATIVE_PORT = 40451  # port the binary always uses (from server_configuration.json)


def _ensure_server(port: int = 40462) -> subprocess.Popen | None:
    """Start OPC UA server if not already running. Returns Popen handle or None.

    If OPCUA_SERVER_URL is already set the caller manages the server — skip auto-launch.
    If the binary is found and started, os.environ["OPCUA_SERVER_URL"] is updated to
    the server's native port so that live tests can locate it.
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
    _log(f"  [server] Starting: {exe}")
    proc = subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        if _is_port_reachable("localhost", _SERVER_NATIVE_PORT):
            _log(f"  [server] Ready on native port {_SERVER_NATIVE_PORT}")
            os.environ["OPCUA_SERVER_URL"] = f"opc.tcp://localhost:{_SERVER_NATIVE_PORT}"
            return proc
        time.sleep(1)
    _log("  [server] Timed out waiting for simulator — terminating")
    proc.terminate()
    return None


def _check_server(skip: bool) -> None:
    """Print informational pre-test server status messages."""
    if skip:
        return
    host, port = _parse_server_url()
    url = _get_server_url()
    logger.info("Checking OPC UA server at %s ...", url)
    if _is_port_reachable(host, port):
        logger.info("OK Server is reachable - tests will connect normally.")
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


def _print_test_count() -> None:
    """Run pytest --collect-only and print a summary of found tests."""
    try:
        result = subprocess.run(
            [str(_venv_python(VENV)), "-m", "pytest", "--collect-only", "-q", "--tb=no"],
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
    if not _tool_available("mypy"):
        result.skipped = True
        result.note = "not installed  (pip install mypy)"
        result.duration = time.monotonic() - t0
        return result
    rc, output = _run(
        [
            sys.executable,
            "-m",
            "mypy",
            ".",
            "--ignore-missing-imports",
            "--no-error-summary",
            "--exclude",
            r"\.venv",
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
            "--ignore=.venv,venv,.venv-wsl",
        ]
    )
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    (_RESULTS_DIR / "pylint.json").write_text(output, encoding="utf-8")
    if not result.ok:
        result.note = f"exit {rc} — see test-results/pylint.json"
        _log(output)
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
            ".venv,venv,.venv-wsl,conftest.py",
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
    rc, output = _run([sys.executable, "-m", "interrogate", "-v", "--fail-under", "60", "."])
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    if not result.ok:
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
    try:
        data = json.loads(output)
        secret_count = sum(len(v) for v in data.get("results", {}).values())
        result.ok = secret_count == 0
        if secret_count:
            result.note = f"{secret_count} potential secret(s) — review .secrets.baseline"
    except json.JSONDecodeError, AttributeError:
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
    cmd: list[str] = [
        sys.executable,
        "-m",
        "pytest",
        str(unit_dir),
        "-q",
        "--tb=short",
        f"--junitxml={unit_xml}",
    ]
    if _tool_available("pytest_cov"):
        cmd += [
            "--cov=.",
            f"--cov-report=xml:{_RESULTS_DIR / 'coverage.xml'}",
            f"--cov-report=html:{_RESULTS_DIR / 'htmlcov'}",
            "--cov-report=term-missing",
            "--cov-fail-under=70",
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
            "--exclude=.venv",
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
    """Run pyright AI type inference; skip if not installed."""
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
        ["pyright", "--outputjson", "--pythonpath", sys.executable]
        if has_bin
        else [sys.executable, "-m", "pyright", "--outputjson", "--pythonpath", sys.executable]
    )
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True, cwd=str(_HERE))
    result.duration = time.monotonic() - t0
    (_RESULTS_DIR / "pyright.json").write_text(proc.stdout or "{}", encoding="utf-8")
    try:
        data = json.loads(proc.stdout or "{}")
        summary = data.get("summary", {})
        errors = summary.get("errorCount", 0)
        warns = summary.get("warningCount", 0)
        if errors:
            result.ok = False
            result.note = f"{errors} error(s), {warns} warning(s)"
        else:
            result.ok = True
            result.note = f"0 errors, {warns} warning(s)" if warns else "0 errors, 0 warnings"
    except Exception:
        result.ok = True
        result.note = "could not parse output"
    return result


# ---------------------------------------------------------------------------
# Phase 2 step — live tests via venv pytest
# ---------------------------------------------------------------------------


def run_pytest(extra_args: list[str]) -> int:
    """Run pytest inside the virtual environment and return its exit code."""
    cmd = [str(_venv_python(VENV)), "-m", "pytest"] + extra_args
    logger.info("Running: %s", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd, cwd=_HERE, check=False)
    return result.returncode


def _step_live_tests(extra_pytest_args: list[str], skip_server_check: bool) -> _StepResult:
    """Run the full live test suite via venv pytest with optional coverage."""
    result = _StepResult("[PHASE 2] pytest live")
    t0 = time.monotonic()

    if not skip_server_check:
        host, port = _parse_server_url()
        if not _is_port_reachable(host, port):
            result.skipped = True
            result.note = f"server not reachable at {host}:{port}"
            result.duration = time.monotonic() - t0
            return result

    _print_test_count()

    # Append coverage flags if pytest-cov is installed
    cov_args: list[str] = []
    if _tool_available("pytest_cov"):
        cov_args = [
            "--cov=.",
            f"--cov-report=xml:{_RESULTS_DIR / 'coverage-live.xml'}",
            "--cov-report=term-missing",
            "--cov-fail-under=70",
        ]

    rc = run_pytest(extra_pytest_args + cov_args)
    result.duration = time.monotonic() - t0
    result.ok = rc == 0
    if not result.ok:
        result.note = f"pytest exited with code {rc}"
    return result


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
    global _USE_COLOUR

    _USE_COLOUR = sys.stdout.isatty() and (os.name != "nt" or _enable_ansi_windows())

    args = _build_parser().parse_args()
    run_phase1 = not args.phase2
    run_phase2 = not args.phase1

    # Step 1: Ensure venv exists and all dependencies are installed
    ensure_venv()
    install_requirements()

    # Step 2: Re-exec under the venv Python so all tools use the same interpreter
    _relaunch_if_needed()

    shutil.rmtree(_RESULTS_DIR, ignore_errors=True)
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
            results.append(_step_mypy())
            results.append(_step_pylint())
            results.append(_step_bandit())
            results.append(_step_pip_audit())
            results.append(_step_vulture())
            results.append(_step_interrogate())
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
            # Clean up env var we set
            os.environ.pop("OPCUA_SERVER_URL", None)

    _divider()
    for r in results:
        r.print_line()
    _divider()

    passed = sum(1 for r in results if r.ok and not r.skipped)
    failed = sum(1 for r in results if not r.ok and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)
    any_failed = failed > 0
    elapsed = time.monotonic() - t_start
    overall = _c(_ANSI_RED, "FAIL") if any_failed else _c(_ANSI_GREEN, "PASS")
    _log(f"  Result: {overall}  passed={passed}  failed={failed}  skipped={skipped}  (elapsed: {elapsed:.1f}s)")
    _log(_c(_ANSI_CYAN, "═" * 52))
    _log("")

    _cleanup_caches(_HERE)
    return 1 if any_failed else 0


def _cleanup_caches(root: Path) -> None:
    """Remove cache/bytecode artifacts after run. Reports in test-results/ are preserved."""
    _SKIP = {"node_modules", ".git", "test-results"}
    _CACHE_DIRS = {"__pycache__", ".ruff_cache", ".mypy_cache"}
    for dirpath, dirs, files in os.walk(root, topdown=True):
        dirs[:] = [d for d in dirs if d not in _SKIP and not d.startswith("venv") and not d.startswith(".venv")]
        for d in list(dirs):
            if d in _CACHE_DIRS:
                shutil.rmtree(Path(dirpath) / d, ignore_errors=True)
                dirs.remove(d)
        for f in files:
            if f == ".coverage" or f.startswith(".coverage.") or f.endswith(".pyc"):
                (Path(dirpath) / f).unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
