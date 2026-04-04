"""
Integration test conftest:
  1. AUTO-STARTS the OPC UA server and Web Client WebSocket server if they are not
     already running — guaranteeing zero skips whether running locally or in CI.
       • Windows (local / CI):  extracts ZIP → runs EXE + starts python index.py
       • Linux (CI ubuntu):     expects servers in Docker; starts python index.py
  2. Automatically applies pytest.mark.integration to all tests here.
  3. Patches asyncua _send_request so every request uses client.timeout (60 s)
     instead of asyncua's 1-second internal default.
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

import pytest

# ── Path constants ─────────────────────────────────────────────────────────────
_INTEGRATION_DIR = Path(__file__).resolve().parent
_WEB_CLIENT_ROOT = _INTEGRATION_DIR.parents[2]  # …/IJT_Web_Client/
_RELEASE2_OPC = _WEB_CLIENT_ROOT.parent  # …/OPC_UA_Clients/Release2/
_REPO_ROOT = _RELEASE2_OPC.parents[1]  # …/UA-for-Industrial-Joining-Technologies/
_SERVER_RELEASE2 = _REPO_ROOT / "OPC_UA_Servers" / "Release2"
_SERVER_ZIP = _SERVER_RELEASE2 / "OPC_UA_IJT_Server_Simulator.zip"
_SERVER_DIR = _SERVER_RELEASE2 / "OPC_UA_IJT_Server_Simulator"
_SERVER_EXE = _SERVER_DIR / "opcua_ijt_demo_application.exe"

_OPCUA_PORT = 40451
_WS_PORT = 8001


# ── asyncua 1.2b2 bug-fix ─────────────────────────────────────────────────────
# UaClient.call() passes no timeout → falls back to 1 s; heavy calls fail.
# Fix: substitute self._timeout (set from Client(timeout=60)) when none given.
def _patch_asyncua_send_timeout() -> None:
    with contextlib.suppress(ImportError):
        import asyncua.client.ua_client as _uc
        from asyncua import ua

        _orig = _uc.UaClient._send_request

        async def _fixed(self, request, timeout=None, message_type=ua.MessageType.SecureMessage):
            if timeout is None:
                timeout = self._timeout
            return await _orig(self, request, timeout, message_type)

        _uc.UaClient._send_request = _fixed


_patch_asyncua_send_timeout()


# ── Port utilities ─────────────────────────────────────────────────────────────
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


# ── Server launchers ──────────────────────────────────────────────────────────
def _start_opcua_server() -> "subprocess.Popen | None":
    """Start the OPC UA server EXE (Windows only; on Linux use Docker).

    Extracts the ZIP on first call if the server directory does not exist yet.
    Returns the Popen handle, or None when the platform cannot run the EXE.
    """
    if platform.system() != "Windows":
        return None

    if not _SERVER_EXE.exists():
        if _SERVER_ZIP.exists():
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


def _start_web_server() -> "subprocess.Popen":
    """Start the Web Client WebSocket + HTTP server (python index.py)."""
    return subprocess.Popen(
        [sys.executable, "index.py"],
        cwd=str(_WEB_CLIENT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ── Session fixture: guarantee both servers are up before any test runs ────────
@pytest.fixture(scope="session", autouse=True)
def ensure_integration_servers():
    """Auto-start OPC UA server and Web Client WebSocket server if needed.

    Strategy
    --------
    • Check each port first — if already open, do nothing (CI Docker, manual start).
    • If closed:
        – OPC UA  (port 40451): start EXE on Windows; fail clearly on Linux.
        – WebSocket (port 8001): start ``python index.py`` on any platform.
    • Only processes started HERE are torn down on session exit.
    • Any startup failure → pytest.fail() (never silent skip).
    """
    started: list[tuple[str, subprocess.Popen]] = []

    # ── 1. OPC UA Server ──────────────────────────────────────────────────────
    if not _port_open("localhost", _OPCUA_PORT):
        proc = _start_opcua_server()
        if proc:
            started.append(("opcua-server", proc))
            if not _wait_for_port("localhost", _OPCUA_PORT, timeout=60):
                proc.terminate()
                pytest.fail(
                    f"OPC UA server process started (PID {proc.pid}) but port "
                    f"{_OPCUA_PORT} did not open within 60 s.  "
                    f"Check opcua_ijt_demo_application.exe output."
                )
        else:
            pytest.fail(
                f"OPC UA server is not running on port {_OPCUA_PORT} and cannot be "
                f"auto-started on {platform.system()}.  "
                f"Start it manually (opcua_ijt_demo_application.exe) or via Docker "
                f"before running integration tests."
            )

    os.environ.setdefault("OPCUA_TEST_ENDPOINT", f"opc.tcp://localhost:{_OPCUA_PORT}")

    # ── 2. Web Client WebSocket server ────────────────────────────────────────
    if not _port_open("localhost", _WS_PORT):
        proc = _start_web_server()
        started.append(("web-server", proc))
        if not _wait_for_port("localhost", _WS_PORT, timeout=30):
            proc.terminate()
            pytest.fail(
                f"Web Client server process started (PID {proc.pid}) but port "
                f"{_WS_PORT} did not open within 30 s.  "
                f"Check python index.py in {_WEB_CLIENT_ROOT}."
            )

    os.environ.setdefault("OPCUA_WS_URL", f"ws://localhost:{_WS_PORT}")

    # ── 3. Console Client path ────────────────────────────────────────────────
    if not os.environ.get("OPCUA_CONSOLE_CLIENT_DIR"):
        candidate = _RELEASE2_OPC / "IJT_Console_Client"
        if candidate.exists():
            os.environ["OPCUA_CONSOLE_CLIENT_DIR"] = str(candidate)

    yield

    # Tear down only what this fixture started
    for _, proc in reversed(started):
        with contextlib.suppress(Exception):
            proc.terminate()
            proc.wait(timeout=5)


# ── Mark every test in this directory as integration ──────────────────────────
def pytest_collection_modifyitems(items):
    for item in items:
        if item.fspath and "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
