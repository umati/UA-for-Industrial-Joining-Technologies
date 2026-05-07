"""
Live test conftest — no silent infrastructure skips.

AUTO-STARTS both the OPC UA server and the Web Client WebSocket server if they
are not already running, so that live tests never silently skip due to a missing
server.  Any startup failure raises pytest.fail() immediately (loud, not silent).
Cleanup always runs via try/finally — no process leaks even on startup failure.

Strategy
--------
• Windows (local / CI): extracts OPC UA server ZIP → runs EXE; starts index.py
• Linux (CI Docker)   : servers already running in the compose stack — no-op
• Port already open   : do nothing (re-use existing process)

Auto-marks
----------
Every test collected from tests/python/live/ is tagged with pytest.mark.live.
Tests in TestBackendWebSocket and TestResponseTimeSLA also get pytest.mark.live_ws.
These markers let run_all_tests.py and CI exclude them from unit-only runs via
  -m "not live and not live_ws"
without the tests silently skipping when the server IS available.
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

from .._asyncua_compat import apply_send_request_timeout_patch
from .._live_server_readiness import (
    opcua_server_log_hint,
    prestarted_port_closed_message,
    prestarted_port_matches,
    start_process_with_opcua_logs,
    wait_for_opcua_protocol_ready,
    wait_for_websocket_protocol_ready,
)

# ── Path constants ─────────────────────────────────────────────────────────────
_LIVE_DIR = Path(__file__).resolve().parent
_WEB_CLIENT_ROOT = _LIVE_DIR.parents[2]          # …/IJT_Web_Client/
_RELEASE2_OPC = _WEB_CLIENT_ROOT.parent           # …/OPC_UA_Clients/Release2/
_REPO_ROOT = _RELEASE2_OPC.parents[1]             # …/UA-for-Industrial-Joining-Technologies/
_SERVER_RELEASE2 = _REPO_ROOT / "OPC_UA_Servers" / "Release2"
_SERVER_ZIP = _SERVER_RELEASE2 / "OPC_UA_IJT_Server_Simulator.zip"
_SERVER_DIR = _SERVER_RELEASE2 / "OPC_UA_IJT_Server_Simulator"
_SERVER_EXE = _SERVER_DIR / "opcua_ijt_demo_application.exe"

_OPCUA_ENDPOINT = os.getenv("OPCUA_TEST_ENDPOINT", f"opc.tcp://localhost:{os.getenv('OPCUA_SERVER_PORT', '40451')}")
_WS_URL = os.getenv("WS_TEST_URL", f"ws://localhost:{os.getenv('WS_PORT', '8001')}")


def _parse_endpoint(endpoint: str) -> tuple[str, int]:
    parsed = urlparse(endpoint)
    if parsed.hostname and parsed.port:
        return parsed.hostname, parsed.port
    clean = endpoint.replace("opc.tcp://", "").replace("opc.tcp//", "")
    if ":" in clean:
        host, port = clean.rsplit(":", 1)
        return host.strip("[]"), int(port)
    return clean or "localhost", 4840


def _parse_ws_url(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    if parsed.hostname and parsed.port:
        return parsed.hostname, parsed.port
    clean = url.replace("wss://", "").replace("ws://", "").split("/")[0]
    if ":" in clean:
        host, port = clean.rsplit(":", 1)
        return host.strip("[]"), int(port)
    return clean or "localhost", 80


_OPCUA_HOST, _OPCUA_PORT = _parse_endpoint(_OPCUA_ENDPOINT)
_WS_HOST, _WS_PORT = _parse_ws_url(_WS_URL)


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

    return start_process_with_opcua_logs(
        [str(_SERVER_EXE)],
        cwd=_SERVER_DIR,
        web_client_root=_WEB_CLIENT_ROOT,
        port=_OPCUA_PORT,
    )


def _start_web_server() -> "subprocess.Popen":
    """Start the Web Client WebSocket + HTTP server (python index.py)."""
    env = os.environ.copy()
    env["OPCUA_TEST_ENDPOINT"] = _OPCUA_ENDPOINT
    env["WS_PORT"] = str(_WS_PORT)
    return subprocess.Popen(
        [sys.executable, "index.py"],
        cwd=str(_WEB_CLIENT_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ── Session fixture: guarantee both servers are up before any test runs ────────
@pytest.fixture(scope="session", autouse=True)
def ensure_live_servers(request):
    """Auto-start OPC UA server and Web Client WebSocket server for live tests.

    Never silently skips — calls pytest.fail() if a required server cannot start.
    Only tears down processes that THIS fixture started.
    Cleanup runs in a finally block so no process leaks even if startup fails.
    """
    started: list[tuple[str, subprocess.Popen]] = []
    needs_ws = any(item.get_closest_marker("live_ws") for item in request.session.items)

    try:
        # ── 1. OPC UA Server ──────────────────────────────────────────────────
        if not _port_open(_OPCUA_HOST, _OPCUA_PORT):
            if prestarted_port_matches(_OPCUA_PORT):
                pytest.fail(prestarted_port_closed_message(_WEB_CLIENT_ROOT, _OPCUA_PORT))
            proc = _start_opcua_server()
            if proc:
                started.append(("opcua-server", proc))
                if not _wait_for_port(_OPCUA_HOST, _OPCUA_PORT, timeout=60):
                    pytest.fail(
                        f"OPC UA server process started (PID {proc.pid}) but port "
                        f"{_OPCUA_PORT} did not open within 60 s. "
                        f"{opcua_server_log_hint(_WEB_CLIENT_ROOT, _OPCUA_PORT)}"
                    )
            else:
                pytest.fail(
                    f"OPC UA server is not running on port {_OPCUA_PORT} and cannot be "
                    f"auto-started on {platform.system()}. "
                    f"Start it manually or via Docker before running live tests."
                )

        os.environ.setdefault("OPCUA_TEST_ENDPOINT", _OPCUA_ENDPOINT)
        opcua_probe_error = wait_for_opcua_protocol_ready(_OPCUA_ENDPOINT)
        if opcua_probe_error is not None:
            pytest.fail(
                f"OPC UA server port {_OPCUA_PORT} is open, but the OPC UA protocol "
                f"did not become ready after 3 attempts. Last error: {opcua_probe_error}. "
                f"{opcua_server_log_hint(_WEB_CLIENT_ROOT, _OPCUA_PORT)}"
            )

        # ── 2. Web Client WebSocket server ────────────────────────────────────
        if needs_ws:
            if not _port_open(_WS_HOST, _WS_PORT):
                proc = _start_web_server()
                started.append(("web-server", proc))
                if not _wait_for_port(_WS_HOST, _WS_PORT, timeout=30):
                    pytest.fail(
                        f"Web Client server process started (PID {proc.pid}) but port "
                        f"{_WS_PORT} did not open within 30 s. "
                        f"Check python index.py in {_WEB_CLIENT_ROOT}."
                    )

            os.environ.setdefault("WS_TEST_URL", _WS_URL)
            websocket_probe_error = wait_for_websocket_protocol_ready(_WS_URL, _OPCUA_ENDPOINT)
            if websocket_probe_error is not None:
                pytest.fail(
                    f"Web Client server port {_WS_PORT} is open, but the WebSocket "
                    f"ping probe did not become ready after 3 attempts. "
                    f"Last error: {websocket_probe_error}."
                )

        yield

    finally:
        for _, proc in reversed(started):
            with contextlib.suppress(Exception):
                proc.terminate()
                proc.wait(timeout=5)


# Apply asyncua _send_request timeout workaround for all live tests in this dir.
apply_send_request_timeout_patch()


# ── Auto-mark all live tests ──────────────────────────────────────────────────
def pytest_collection_modifyitems(items):
    """Tag every test in tests/python/live/ with appropriate markers."""
    for item in items:
        fspath = str(item.fspath)
        if "live" not in fspath:
            continue
        item.add_marker(pytest.mark.live)
        # WebSocket-specific classes also get live_ws
        if any(cls in item.nodeid for cls in ("TestBackendWebSocket", "TestResponseTimeSLA", "TestWebSocketLifecycle")):
            item.add_marker(pytest.mark.live_ws)
