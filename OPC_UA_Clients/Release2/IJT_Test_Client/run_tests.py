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
Environment variables
---------------------
    OPCUA_SERVER_URL        Override server endpoint (default: opc.tcp://localhost:40451)
    OPCUA_SIMULATOR_EXE     Path to opcua_ijt_demo_application(.exe)
    OPCUA_STARTUP_TIMEOUT_SEC  Seconds to wait for simulator start (default: 10)
    SKIP_VENV_INSTALL       Set to "1" to skip pip install step (faster re-runs)
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

_MIN_PYTHON = (3, 14)

if sys.version_info < _MIN_PYTHON:
    sys.exit(
        f"Python {_MIN_PYTHON[0]}.{_MIN_PYTHON[1]}+ required. "
        f"Current: {sys.version}"
    )

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
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
def run_pytest(extra_args: list[str]) -> int:
    """Run pytest inside the virtual environment and return its exit code."""
    cmd = [str(_venv_python()), "-m", "pytest"] + extra_args
    print(f"[run_tests] Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode
def main() -> None:
    ensure_venv()
    install_requirements()
    exit_code = run_pytest(sys.argv[1:])
    sys.exit(exit_code)
if __name__ == "__main__":
    main()