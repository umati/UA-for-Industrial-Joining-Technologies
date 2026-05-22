"""Shared live-test startup diagnostics and protocol readiness probes.

Web Client adapter over the repository-wide readiness module at
``scripts/ijt_live_readiness.py``. The functions ``wait_for_opcua_protocol_ready``
and ``wait_for_websocket_protocol_ready`` keep their existing call signatures
(returning ``str | None`` so they compose with existing callers) and own the
per-attempt retry policy; the inner per-attempt probe (one
asyncua connect+disconnect, one WebSocket handshake) is delegated to the
shared probe-once helpers so the protocol-readiness contract is identical
across all IJT clients. This file remains the home for Web-specific helpers
(log paths, failure-signature extraction, ``start_process_with_opcua_logs``)
that are not generally useful outside the Web Client tree.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


# Locate the shared readiness module robustly. In a normal repo checkout the
# repo root is five ``parents`` up, but Docker test images flatten the tree
# (the Web Client subtree alone is copied into /app), so we walk ancestors
# looking for ``scripts/ijt_live_readiness.py`` and fall back to a vendored
# copy at ``/app/scripts/ijt_live_readiness.py`` for the Docker test target.
def _find_shared_readiness_scripts_dir() -> Path | None:
    here = Path(__file__).resolve()
    for ancestor in (here, *here.parents):
        candidate = ancestor / "scripts" / "ijt_live_readiness.py"
        if candidate.is_file():
            return candidate.parent
    # Docker test image layout: Web Client subtree is copied to /app, and
    # the shared script is copied alongside as /app/scripts/...
    docker_candidate = Path("/app/scripts/ijt_live_readiness.py")
    if docker_candidate.is_file():
        return docker_candidate.parent
    return None


_SCRIPTS_DIR = _find_shared_readiness_scripts_dir()
if _SCRIPTS_DIR is not None and str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from ijt_live_readiness import (  # noqa: E402
    opcua_session_probe_once,
    websocket_probe_once,
)

# Module-level sleep indirection so tests can monkeypatch retry pacing without
# stubbing the global ``time`` module. The retry loop below must call
# ``_sleep`` rather than ``time.sleep`` directly so unit tests can assert on
# inter-attempt waits.
_sleep = time.sleep

OPCUA_PRESTARTED_PORT_ENV = "IJT_OPCUA_PRESTARTED_PORT"
MAX_SIMULATOR_LAUNCH_ATTEMPTS = 2
SIMULATOR_RETRY_TRIGGERS: tuple[str, ...] = (
    "0x80010000",
    "CoInitialize",
    "server-instance creation failed",
)
DEFAULT_PROTOCOL_READY_ATTEMPTS = 10
DEFAULT_PROTOCOL_READY_INTERVAL = 1.5
DEFAULT_PROTOCOL_READY_TIMEOUT = 2.5

# The WebSocket probe is intentionally backend-only. Direct OPC UA protocol
# readiness is checked separately before this probe runs.
DEFAULT_WEBSOCKET_READY_ATTEMPTS = 1
DEFAULT_WEBSOCKET_READY_INTERVAL = 1.0
DEFAULT_WEBSOCKET_READY_RESPONSE_TIMEOUT = 5.0

# The Web Client backend's readiness-probe handshake. ``get connectionpoints``
# is a stateless, side-effect-free command handled directly by
# ``handle_get_connection_points`` in ``src/python/ijt_interface.py``. What we
# are checking is that the WS plumbing reaches the backend dispatcher and the
# reply carries our ``uniqueid``.
_WEB_BACKEND_READINESS_COMMAND = "get connectionpoints"
_WEB_BACKEND_READINESS_ENDPOINT = "common"
_WEB_BACKEND_READINESS_UNIQUEID = "readiness-probe"

_KNOWN_FAILURE_SIGNATURES: tuple[str, ...] = (
    "0x80010000",
    "CoInitialize",
    "server-instance",
    "server-instance creation failed",
    "failed to create",
    "Bad",
)
_FAILURE_SIGNATURE_TAIL_LINES = 40
_FAILURE_SIGNATURE_TAIL_BYTES = 8192


def _tail_log_lines(path: Path, *, max_lines: int, max_bytes: int) -> list[str]:
    try:
        raw = path.read_bytes()
    except OSError:
        return []
    text = raw[-max_bytes:].decode("utf-8", errors="replace")
    return text.splitlines()[-max_lines:]


def extract_known_failure_signatures(err_log_path: Path) -> list[str]:
    """Return known simulator-startup failure lines from the bounded err-log tail."""
    lines = _tail_log_lines(
        err_log_path,
        max_lines=_FAILURE_SIGNATURE_TAIL_LINES,
        max_bytes=_FAILURE_SIGNATURE_TAIL_BYTES,
    )
    matches: list[str] = []
    for line in lines:
        if any(signature.lower() in line.lower() for signature in _KNOWN_FAILURE_SIGNATURES):
            matches.append(line.strip())
    return matches


def web_client_results_dir(web_client_root: Path) -> Path:
    value = os.getenv("IJT_WEB_TEST_RESULTS_DIR")
    if not value:
        return web_client_root / "test-results"
    path = Path(value)
    return path if path.is_absolute() else web_client_root / path


def opcua_server_log_paths(web_client_root: Path, port: int) -> tuple[Path, Path]:
    results_dir = web_client_results_dir(web_client_root)
    return (
        results_dir / f"opcua-server-{port}.out.log",
        results_dir / f"opcua-server-{port}.err.log",
    )


def opcua_server_log_hint(web_client_root: Path, port: int) -> str:
    out_log, err_log = opcua_server_log_paths(web_client_root, port)
    return f"See {out_log} and {err_log}."


def prestarted_port_closed_message(web_client_root: Path, port: int) -> str:
    return (
        f"Runner prestarted OPC UA server on port {port}, but the port is "
        f"closed at fixture startup. {opcua_server_log_hint(web_client_root, port)}"
    )


def prestarted_port_matches(port: int) -> bool:
    return os.getenv(OPCUA_PRESTARTED_PORT_ENV) == str(port)


def start_process_with_opcua_logs(
    command: list[str], *, cwd: Path, web_client_root: Path, port: int
) -> subprocess.Popen:
    out_log, err_log = opcua_server_log_paths(web_client_root, port)
    out_log.parent.mkdir(parents=True, exist_ok=True)
    out_file = out_log.open("ab")
    err_file = err_log.open("ab")
    try:
        return subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=out_file,
            stderr=err_file,
            stdin=subprocess.DEVNULL,
        )
    finally:
        out_file.close()
        err_file.close()


def wait_for_opcua_protocol_ready(
    endpoint: str,
    *,
    attempts: int = DEFAULT_PROTOCOL_READY_ATTEMPTS,
    interval: float = DEFAULT_PROTOCOL_READY_INTERVAL,
    connect_timeout: float = DEFAULT_PROTOCOL_READY_TIMEOUT,
) -> str | None:
    """Wait until ``endpoint`` accepts an asyncua connect+disconnect.

    Returns ``None`` on success, a single-line error string on failure (kept
    for backwards compatibility with callers that distinguish probe types by
    error-string substring matching). Each attempt delegates to
    :func:`ijt_live_readiness.opcua_session_probe_once` so the per-attempt
    contract is shared with the rest of the IJT clients; this wrapper owns
    the retry loop (``attempts`` × ``interval``) so its tests can monkeypatch
    ``_sleep``.
    """

    last_error: str | None = None
    for index in range(attempts):
        last_error = opcua_session_probe_once(endpoint, connect_timeout=connect_timeout)
        if last_error is None:
            return None
        if index < attempts - 1:
            _sleep(interval)
    return last_error


def wait_for_websocket_protocol_ready(
    ws_url: str,
    opcua_endpoint: str | None = None,
    *,
    attempts: int = DEFAULT_WEBSOCKET_READY_ATTEMPTS,
    interval: float = DEFAULT_WEBSOCKET_READY_INTERVAL,
    response_timeout: float = DEFAULT_WEBSOCKET_READY_RESPONSE_TIMEOUT,
) -> str | None:
    """Wait until the WebSocket backend completes the IJT readiness handshake.

    Returns ``None`` on success, an error string on failure. Sends the
    legacy IJT readiness payload
    ``{"command": "get connectionpoints", "endpoint": "common", "uniqueid":
    "readiness-probe"}`` and treats any reply carrying ``uniqueid =
    "readiness-probe"`` as success (the backend may answer with normal data
    or with ``{"exception": "..."}``; both prove the WS plumbing works).
    The per-attempt probe is delegated to
    :func:`ijt_live_readiness.websocket_probe_once`; this wrapper owns the
    retry loop so its tests can monkeypatch ``_sleep``.

    ``opcua_endpoint`` is accepted for backwards-compatibility with older
    callers; the readiness probe itself does not address a specific OPC UA
    endpoint (it asks the backend for its connection-points table, which is
    OPC-UA-independent).
    """

    del opcua_endpoint  # kept in the signature for backwards compatibility
    payload_json = json.dumps(
        {
            "command": _WEB_BACKEND_READINESS_COMMAND,
            "endpoint": _WEB_BACKEND_READINESS_ENDPOINT,
            "uniqueid": _WEB_BACKEND_READINESS_UNIQUEID,
        }
    )
    last_error: str | None = None
    for index in range(attempts):
        last_error = websocket_probe_once(
            ws_url,
            payload_json=payload_json,
            handshake_id=_WEB_BACKEND_READINESS_UNIQUEID,
            open_timeout=response_timeout,
            close_timeout=0.5,
            response_timeout=response_timeout,
        )
        if last_error is None:
            return None
        if index < attempts - 1:
            _sleep(interval)
    return last_error
