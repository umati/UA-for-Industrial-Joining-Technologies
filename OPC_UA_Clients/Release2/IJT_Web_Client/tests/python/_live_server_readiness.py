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
DEFAULT_PROTOCOL_READY_ATTEMPTS = 10
DEFAULT_PROTOCOL_READY_INTERVAL = 1.5
DEFAULT_PROTOCOL_READY_TIMEOUT = 2.5


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


async def _probe_websocket_protocol(ws_url: str, opcua_endpoint: str, response_timeout: float) -> None:
    import websockets

    async with websockets.connect(ws_url, open_timeout=min(5.0, response_timeout), close_timeout=0.5) as websocket:
        uniqueid = "readiness-probe"
        await websocket.send(
            json.dumps(
                {
                    "command": "connect to",
                    "endpoint": opcua_endpoint,
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
            raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
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
            data = payload.get("data")
            exception = data.get("exception") if isinstance(data, dict) else None
            if exception:
                raise RuntimeError(f"readiness connect returned exception: {exception}")
            return


def wait_for_websocket_protocol_ready(
    ws_url: str,
    opcua_endpoint: str,
    *,
    attempts: int = DEFAULT_PROTOCOL_READY_ATTEMPTS,
    interval: float = DEFAULT_PROTOCOL_READY_INTERVAL,
    response_timeout: float = DEFAULT_PROTOCOL_READY_TIMEOUT,
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
