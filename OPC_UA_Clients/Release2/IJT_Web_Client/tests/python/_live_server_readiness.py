"""Shared live-test startup diagnostics and protocol readiness probes."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import os
import subprocess
import time
from pathlib import Path

OPCUA_PRESTARTED_PORT_ENV = "IJT_OPCUA_PRESTARTED_PORT"


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
    attempts: int = 3,
    interval: float = 1.0,
    connect_timeout: float = 1.25,
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


async def _probe_websocket_protocol(ws_url: str, _opcua_endpoint: str, response_timeout: float) -> None:
    import websockets

    async with websockets.connect(ws_url, open_timeout=min(5.0, response_timeout), close_timeout=0.5) as websocket:
        ping_result = websocket.ping()
        if inspect.isawaitable(ping_result):
            awaited = await ping_result
            if inspect.isawaitable(awaited):
                await asyncio.wait_for(awaited, timeout=response_timeout)


def wait_for_websocket_protocol_ready(
    ws_url: str,
    opcua_endpoint: str,
    *,
    attempts: int = 3,
    interval: float = 1.0,
    response_timeout: float = 1.25,
) -> str | None:
    last_error = "no WebSocket protocol probe attempted"
    for attempt in range(attempts):
        try:
            asyncio.run(_probe_websocket_protocol(ws_url, opcua_endpoint, response_timeout))
            return None
        except Exception as exc:  # pragma: no cover - exact backend/websocket error type varies by version
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < attempts - 1:
                time.sleep(interval)
    return last_error
