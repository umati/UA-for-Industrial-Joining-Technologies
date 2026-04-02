"""
run_tests.py — Cross-platform test runner for IJT conformance and functional tests.
Creates an isolated Python virtual environment, installs dependencies, and
runs pytest.  Works identically on Windows, Linux, and macOS with just:
    python run_tests.py [pytest-args...]
Examples
--------
    python run_tests.py                              # run all tests
    python run_tests.py -v                           # verbose output
    python run_tests.py -m conformance               # §11.1 conformance units only
    python run_tests.py -m structure                 # address space structure only
    python run_tests.py -m methods                   # method call tests only
    python run_tests.py -k "result_management"       # filter by name
    python run_tests.py --co -q                      # list tests without running
    python run_tests.py -x                           # stop on first failure
    python run_tests.py --no-server-check            # skip pre-test server check
Environment variables
---------------------
    OPCUA_SERVER_URL           Override server endpoint (default: opc.tcp://localhost:40451)
    OPCUA_SIMULATOR_EXE        Path to opcua_ijt_demo_application(.exe)
    OPCUA_STARTUP_TIMEOUT_SEC  Seconds to wait for simulator start (default: 30)
    SKIP_VENV_INSTALL          Set to "1" to skip pip install step (faster re-runs)
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path

_MIN_PYTHON = (3, 14)

if sys.version_info < _MIN_PYTHON:
    sys.exit(
        f"Python {_MIN_PYTHON[0]}.{_MIN_PYTHON[1]}+ required. Current: {sys.version}"
    )

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"

# Well-known simulator binary locations (relative to repo root)
_WELL_KNOWN_SIMULATOR_PATHS = [
    ROOT.parents[3]
    / "OPC_UA_Servers"
    / "Release2"
    / "OPC_UA_IJT_Server_Simulator"
    / "opcua_ijt_demo_application",
    ROOT.parents[3]
    / "OPC_UA_Servers"
    / "Release2"
    / "OPC_UA_IJT_Server_Simulator"
    / "opcua_ijt_demo_application.exe",
]


def _venv_python() -> Path:
    """Return the path to the Python executable inside the virtual environment."""
    if sys.platform == "win32":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def _venv_pip() -> Path:
    if sys.platform == "win32":
        return VENV / "Scripts" / "pip.exe"
    return VENV / "bin" / "pip"


def ensure_venv() -> None:
    """Create the virtual environment if it does not already exist."""
    if not VENV.exists():
        print(f"[run_tests] Creating virtual environment: {VENV}")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    else:
        print(f"[run_tests] Using existing virtual environment: {VENV}")


def install_requirements() -> None:
    """Install (or upgrade) packages from requirements.txt into the venv."""
    if os.environ.get("SKIP_VENV_INSTALL") == "1":
        print("[run_tests] Skipping pip install (SKIP_VENV_INSTALL=1)")
        return
    if not REQUIREMENTS.exists():
        print("[run_tests] No requirements.txt found — skipping install")
        return
    print(f"[run_tests] Installing requirements from {REQUIREMENTS.name}...")
    subprocess.check_call(
        [str(_venv_pip()), "install", "--quiet", "-r", str(REQUIREMENTS)],
    )


def _is_server_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if a TCP connection to host:port succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_server_url() -> tuple[str, int]:
    """Parse OPCUA_SERVER_URL and return (host, port)."""
    url = os.environ.get("OPCUA_SERVER_URL", "opc.tcp://localhost:40451")
    # Strip scheme prefix
    stripped = url.replace("opc.tcp://", "").replace("opc.tcp.//", "")
    if ":" in stripped:
        host, port_str = stripped.rsplit(":", 1)
        try:
            return host, int(port_str)
        except ValueError:
            pass
    return stripped, 40451


def _check_server(skip: bool) -> None:
    """Check server reachability and print pre-test status messages."""
    if skip:
        return
    host, port = _parse_server_url()
    url = os.environ.get("OPCUA_SERVER_URL", f"opc.tcp://{host}:{port}")
    print(f"\n[run_tests] Checking OPC UA server at {url} ...")
    if _is_server_reachable(host, port):
        print("[run_tests] OK Server is reachable - tests will connect normally.\n")
        return
    print(f"[run_tests] NO Server not reachable at {host}:{port}")
    sim_exe = os.environ.get("OPCUA_SIMULATOR_EXE")
    if sim_exe:
        print(f"[run_tests]   Auto-launch enabled: OPCUA_SIMULATOR_EXE={sim_exe}")
        print(
            "[run_tests]   conftest.py will attempt to start the simulator automatically."
        )
    else:
        well_known = next((p for p in _WELL_KNOWN_SIMULATOR_PATHS if p.exists()), None)
        if well_known:
            print(f"[run_tests]   Simulator found at well-known path: {well_known}")
            print("[run_tests]   conftest.py will attempt to start it automatically.")
        else:
            print("[run_tests]   No simulator found. To auto-launch, set:")
            print(
                "[run_tests]     OPCUA_SIMULATOR_EXE=<path/to/opcua_ijt_demo_application>"
            )
            print("[run_tests]   Or start the OPC UA IJT Server Simulator manually.")
    timeout = os.environ.get("OPCUA_STARTUP_TIMEOUT_SEC", "30")
    print(f"[run_tests]   Startup timeout: {timeout}s (OPCUA_STARTUP_TIMEOUT_SEC)")
    print("[run_tests]   Live tests will be skipped if the server cannot be reached.\n")


def _print_test_count(venv_python: Path) -> None:
    """Run pytest --collect-only and print a summary of found tests."""
    try:
        result = subprocess.run(
            [str(venv_python), "-m", "pytest", "--collect-only", "-q", "--tb=no"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        # pytest --collect-only -q outputs "<N> tests collected" or similar on the last line
        for line in reversed(result.stdout.splitlines()):
            line = line.strip()
            if line and (
                "test" in line or "item" in line or "warning" in line or "error" in line
            ):
                print(f"[run_tests] Test suite: {line}")
                break
    except Exception:
        pass  # non-critical


def run_pytest(extra_args: list[str]) -> int:
    """Run pytest inside the virtual environment and return its exit code."""
    cmd = [str(_venv_python()), "-m", "pytest"] + extra_args
    print(f"[run_tests] Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


def main() -> None:
    # Extract --no-server-check before forwarding remaining args to pytest
    raw_args = sys.argv[1:]
    skip_server_check = "--no-server-check" in raw_args
    pytest_args = [a for a in raw_args if a != "--no-server-check"]

    ensure_venv()
    install_requirements()
    _check_server(skip=skip_server_check)
    _print_test_count(_venv_python())
    exit_code = run_pytest(pytest_args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
