#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import socket
from pathlib import Path
from urllib.parse import urlparse

IS_WINDOWS = sys.platform.startswith("win")
VENV_PYTHON = Path("venv") / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")
REQUIREMENTS_DEV = Path("requirements-dev.txt")


def _endpoint_reachable(endpoint: str, timeout: float = 1.0) -> bool:
    parsed = urlparse(endpoint)
    host = parsed.hostname or "localhost"
    port = parsed.port or 40451
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run tests using the project virtual environment")
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests (marker=integration)",
    )
    args = parser.parse_args()

    if not VENV_PYTHON.exists():
        print(
            "Virtual environment not found. Run 'python setup_project.py --force_full' first.",
            file=sys.stderr,
        )
        return 1

    marker = "integration" if args.integration else "not integration"
    endpoint = os.getenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40451")
    if not _endpoint_reachable(endpoint):
        print(
            f"[WARN] No OPC UA Server running on {endpoint}. "
            "If clients and simulator are in separate folders/downloads, start the server before running tests.",
            file=sys.stderr,
        )

    try:
        subprocess.check_call([str(VENV_PYTHON), "-c", "import pytest, pytest_asyncio"])
    except subprocess.CalledProcessError:
        if not REQUIREMENTS_DEV.exists():
            print(
                "[ERROR] pytest is missing and requirements-dev.txt was not found.",
                file=sys.stderr,
            )
            return 1
        print("Installing missing test dependencies from requirements-dev.txt ...")
        try:
            subprocess.check_call(
                [str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "-r", str(REQUIREMENTS_DEV)]
            )
        except subprocess.CalledProcessError:
            print(
                "[ERROR] Failed to install test dependencies. Check network access or run setup_project.py --force_full.",
                file=sys.stderr,
            )
            return 1

    cmd = [str(VENV_PYTHON), "-m", "pytest", "tests", "-m", marker]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
