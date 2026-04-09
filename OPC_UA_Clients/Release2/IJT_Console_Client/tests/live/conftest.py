"""
Console Client live test conftest — guaranteed zero skips.

AUTO-STARTS the OPC UA server if it is not already running so that live tests
never silently skip due to a missing server.  Any startup failure raises
pytest.fail() immediately (loud, not silent).

Strategy
--------
• Windows (local / CI): extracts OPC UA server ZIP → runs EXE
• Linux (CI Docker)   : server already running in the compose stack — no-op
• Port already open   : do nothing (re-use existing process)

Auto-marks
----------
Every test collected from tests/live/ is tagged with pytest.mark.live so that
unit-only runs can exclude them via  -m "not live"  without any silent skip.
"""

from __future__ import annotations

import contextlib
import os
import platform
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import pytest

# ── Path constants ─────────────────────────────────────────────────────────────
_LIVE_DIR = Path(__file__).resolve().parent
# _LIVE_DIR = tests/live/
# parents: [0]=tests/, [1]=IJT_Console_Client/, [2]=Release2/, [3]=OPC_UA_Clients/, [4]=repo root
_CONSOLE_ROOT = _LIVE_DIR.parents[1]
_REPO_ROOT = _LIVE_DIR.parents[4]
_SERVER_RELEASE2 = _REPO_ROOT / "OPC_UA_Servers" / "Release2"
_SERVER_ZIP = _SERVER_RELEASE2 / "OPC_UA_IJT_Server_Simulator.zip"
_SERVER_DIR = _SERVER_RELEASE2 / "OPC_UA_IJT_Server_Simulator"
_SERVER_EXE = _SERVER_DIR / "opcua_ijt_demo_application.exe"

_OPCUA_PORT = 40451

sys.path.insert(0, str(_CONSOLE_ROOT))


# ── Port / URL utilities ───────────────────────────────────────────────────────
def _resolve_server_host_port() -> tuple[str, int]:
    url = os.environ.get("OPCUA_SERVER_URL", "")
    if url:
        try:
            parsed = urlparse(url.replace("opc.tcp://", "http://"))
            return parsed.hostname or "localhost", parsed.port or _OPCUA_PORT
        except ValueError, AttributeError:
            pass
    return "localhost", _OPCUA_PORT


def _port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_for_port(host: str, port: int, timeout: float, interval: float = 1.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_open(host, port):
            return True
        time.sleep(interval)
    return False


# ── Server launcher ───────────────────────────────────────────────────────────
def _start_opcua_server() -> "subprocess.Popen | None":
    """Start the OPC UA simulator EXE (Windows only; on Linux use Docker).

    Extracts the ZIP on first call if the server directory does not exist yet.
    Returns the Popen handle, or None when the platform cannot run the EXE.
    """
    if platform.system() != "Windows":
        return None

    if not _SERVER_EXE.exists() and _SERVER_ZIP.exists():
        with zipfile.ZipFile(_SERVER_ZIP) as zf:
            zf.extractall(_SERVER_RELEASE2)

    if not _SERVER_EXE.exists():
        return None

    return subprocess.Popen(
        [str(_SERVER_EXE)],
        cwd=str(_SERVER_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ── Session fixture: guarantee OPC UA server is up before any test runs ────────
@pytest.fixture(scope="session", autouse=True)
def ensure_opcua_server():
    """Auto-start OPC UA server for Console Client live tests.

    Never silently skips — calls pytest.fail() if the server cannot start.
    Only tears down the process that THIS fixture started.
    """
    host, port = _resolve_server_host_port()
    started_proc: subprocess.Popen | None = None

    if not _port_open(host, port):
        proc = _start_opcua_server()
        if proc:
            started_proc = proc
            if not _wait_for_port(host, port, timeout=60):
                proc.terminate()
                pytest.fail(
                    f"OPC UA server process started (PID {proc.pid}) but port "
                    f"{port} did not open within 60 s. "
                    f"Check opcua_ijt_demo_application.exe output."
                )
        else:
            pytest.fail(
                f"OPC UA server is not running on {host}:{port} and cannot be "
                f"auto-started on {platform.system()}. "
                f"Start it manually or via Docker before running live tests."
            )

    os.environ.setdefault("OPCUA_SERVER_URL", f"opc.tcp://{host}:{port}")

    yield

    if started_proc is not None:
        with contextlib.suppress(Exception):
            started_proc.terminate()
            started_proc.wait(timeout=5)


# ── Auto-mark all live tests ──────────────────────────────────────────────────
def pytest_collection_modifyitems(items):
    """Tag every test in tests/live/ with pytest.mark.live."""
    for item in items:
        if item.fspath and "live" in str(item.fspath):
            item.add_marker(pytest.mark.live)
