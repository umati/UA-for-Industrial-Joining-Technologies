"""Shared live-test startup diagnostics and protocol readiness probes."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import subprocess
import time
from pathlib import Path

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


async def _probe_opcua_protocol(endpoint: str, connect_timeout: float) -> None:
    from asyncua import Client

    client = Client(endpoint, timeout=connect_timeout)
    try:
        await client.connect()
    finally:
        with contextlib.suppress(Exception):
            await client.disconnect()


def wait_for_opcua_protocol_ready(
    endpoint: str,
    *,
    attempts: int = DEFAULT_PROTOCOL_READY_ATTEMPTS,
    interval: float = DEFAULT_PROTOCOL_READY_INTERVAL,
    connect_timeout: float = DEFAULT_PROTOCOL_READY_TIMEOUT,
) -> str | None:
    last_error = "no OPC UA protocol probe attempted"
    for attempt in range(attempts):
        try:
            asyncio.run(_probe_opcua_protocol(endpoint, connect_timeout))
            return None
        except Exception as exc:  # pragma: no cover - exact asyncua exception type varies by version
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < attempts - 1:
                time.sleep(interval)
    return last_error


async def _probe_websocket_protocol(ws_url: str, response_timeout: float) -> None:
    import websockets

    async with websockets.connect(ws_url, open_timeout=min(5.0, response_timeout), close_timeout=0.5) as websocket:
        uniqueid = "readiness-probe"
        await websocket.send(
            json.dumps(
                {
                    "command": "get connectionpoints",
                    "endpoint": "common",
                    "uniqueid": uniqueid,
                }
            )
        )
        deadline = asyncio.get_running_loop().time() + response_timeout
        last_response = "no response received"
        unmatched_count = 0
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError(f"no matching readiness response received; last response: {last_response}")
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
            except TimeoutError as exc:
                raise TimeoutError(
                    f"no matching readiness response received within {response_timeout:.1f}s; "
                    f"last response: {last_response}"
                ) from exc
            last_response = str(raw)
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid readiness response JSON: {exc.msg}") from exc
            if payload.get("uniqueid") != uniqueid:
                unmatched_count += 1
                if unmatched_count >= 5:
                    raise RuntimeError(f"no matching readiness response received; last response: {last_response}")
                continue
            return


def wait_for_websocket_protocol_ready(
    ws_url: str,
    opcua_endpoint: str | None = None,
    *,
    attempts: int = DEFAULT_WEBSOCKET_READY_ATTEMPTS,
    interval: float = DEFAULT_WEBSOCKET_READY_INTERVAL,
    response_timeout: float = DEFAULT_WEBSOCKET_READY_RESPONSE_TIMEOUT,
) -> str | None:
    last_error = "no WebSocket protocol probe attempted"
    for attempt in range(attempts):
        try:
            asyncio.run(_probe_websocket_protocol(ws_url, response_timeout))
            return None
        except Exception as exc:  # pragma: no cover - exact backend/websocket error type varies by version
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < attempts - 1:
                time.sleep(interval)
    return last_error
