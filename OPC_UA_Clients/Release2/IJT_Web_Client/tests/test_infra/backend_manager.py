"""Managed WebSocket/OPC UA backend lifecycle for live Web Client suites."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

UA_NAMESPACE_URI = "http://opcfoundation.org/UA/"


class BackendHealthError(RuntimeError):
    """Raised when the managed backend is not healthy."""


class BackendCrashedError(BackendHealthError):
    """Raised when a managed backend process exits unexpectedly."""


@dataclass(frozen=True)
class HealthStatus:
    """Result from one backend health probe."""

    ok: bool
    step: str
    detail: str = ""
    payload: Any = None
    crashed: bool = False


class WebTestBackendManager:
    """Owns one WebSocket backend and one OPC UA server endpoint for a test suite.

    The health contract intentionally proves more than "the TCP port is open":
    it connects to the WebSocket server, connects that backend to the OPC UA
    endpoint, validates the namespace response envelope, and terminates the
    OPC UA connection.
    """

    def __init__(
        self,
        *,
        ws_port: int,
        opcua_port: int,
        label: str,
        root: Path | None = None,
        results_root: Path | None = None,
        python_executable: str | None = None,
        opcua_command: list[str] | None = None,
        health_timeout: float = 3.0,
    ) -> None:
        self.ws_port = ws_port
        self.opcua_port = opcua_port
        self.label = label
        self.root = root or Path(__file__).resolve().parents[2]
        self.results_root = results_root or self.root / "test-results" / label
        self.python_executable = python_executable or sys.executable
        self.opcua_command = opcua_command
        self.health_timeout = health_timeout
        self.ws_url = f"ws://127.0.0.1:{ws_port}/"
        self.opcua_endpoint = f"opc.tcp://localhost:{opcua_port}"
        self._ws_proc: subprocess.Popen[str] | None = None
        self._opcua_proc: subprocess.Popen[str] | None = None
        self._crashed = False
        self._monitor_stop = threading.Event()
        self._monitor_thread: threading.Thread | None = None
        self._started = False

    def __enter__(self) -> WebTestBackendManager:
        self.start()
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self.stop()

    def start(self) -> None:
        """Start managed services and prove they are healthy."""

        if self._started:
            self.assert_healthy()
            return

        self._emit_event("start_requested", {"ws_port": self.ws_port, "opcua_port": self.opcua_port})
        self._start_opcua_server()
        self._start_websocket_backend()
        self._start_monitor()
        self.assert_healthy()
        self._started = True
        self._emit_event("started", {"ws_url": self.ws_url, "opcua_endpoint": self.opcua_endpoint})

    def stop(self) -> None:
        """Stop managed services and assert their ports are released."""

        self._emit_event("stop_requested", {})
        self._monitor_stop.set()
        owned_ws = self._ws_proc is not None
        owned_opcua = self._opcua_proc is not None
        self._terminate_process(self._ws_proc, "websocket")
        self._terminate_process(self._opcua_proc, "opcua")
        self._ws_proc = None
        self._opcua_proc = None
        self._started = False
        if owned_ws:
            self._wait_for_port_free(self.ws_port)
        if owned_opcua:
            self._wait_for_port_free(self.opcua_port)
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1)
        self._emit_event("stopped", {})

    def restart(self) -> None:
        """Restart both managed services."""

        self._emit_event("restart_requested", {})
        self.stop()
        self._crashed = False
        self._monitor_stop.clear()
        self.start()
        self._emit_event("restarted", {})

    def health(self) -> HealthStatus:
        """Return health status without raising."""

        if self._crashed:
            return HealthStatus(
                ok=False,
                step="process",
                detail="backend process exited unexpectedly",
                payload=self.stderr_tail(),
                crashed=True,
            )
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            return HealthStatus(ok=False, step="event-loop", detail="call async_health() from async test code")
        try:
            return asyncio.run(self.async_health())
        except Exception as exc:  # noqa: BLE001 - infrastructure probe must report all failure modes.
            return HealthStatus(ok=False, step="health", detail=str(exc))

    async def async_health(self) -> HealthStatus:
        """Run the full WebSocket -> OPC UA health handshake."""

        try:
            return await asyncio.wait_for(self._run_health_exchange(), timeout=self.health_timeout)
        except asyncio.TimeoutError:
            return HealthStatus(ok=False, step="timeout", detail=f"health probe exceeded {self.health_timeout}s")
        except Exception as exc:  # noqa: BLE001 - infrastructure probe must report all failure modes.
            return HealthStatus(ok=False, step="websocket", detail=str(exc))

    def assert_healthy(self) -> None:
        """Raise a typed error when health probing fails."""

        status = self.health()
        if status.ok:
            self._emit_event("health_ok", {"step": status.step})
            return
        self._emit_event(
            "health_failed",
            {"step": status.step, "detail": status.detail, "payload": status.payload, "crashed": status.crashed},
        )
        message = f"{self.label} backend unhealthy at {status.step}: {status.detail}; payload={status.payload!r}"
        if status.crashed:
            raise BackendCrashedError(message)
        raise BackendHealthError(message)

    def reset_session(self) -> None:
        """Reset and prove a clean backend session for the next test."""

        self.assert_healthy()

    def stderr_tail(self) -> list[str]:
        """Return the captured process tail."""

        lines: list[str] = []
        for path in (self.results_root / "websocket.log", self.results_root / "opcua.log"):
            if path.exists():
                lines.extend(path.read_text(encoding="utf-8", errors="replace").splitlines()[-100:])
        return lines[-200:]

    async def _run_health_exchange(self) -> HealthStatus:
        import websockets

        async with websockets.connect(self.ws_url, open_timeout=1, close_timeout=1) as websocket:
            connect_payload = await self._send_command(websocket, 1, "connect to")
            connect_data = connect_payload.get("data") if isinstance(connect_payload, dict) else None
            if not isinstance(connect_data, dict) or connect_data.get("exception") is not None:
                return HealthStatus(False, "connect to", "connect response was not successful", connect_payload)

            namespaces_payload = await self._send_command(websocket, 2, "namespaces")
            namespaces_data = namespaces_payload.get("data") if isinstance(namespaces_payload, dict) else None
            namespaces = namespaces_data.get("namespaces") if isinstance(namespaces_data, dict) else None
            if not isinstance(namespaces, list) or UA_NAMESPACE_URI not in namespaces:
                return HealthStatus(
                    False, "namespaces", "namespace envelope did not contain the UA namespace", namespaces_payload
                )

            terminate_payload = await self._send_command(websocket, 3, "terminate connection")
            terminate_data = terminate_payload.get("data") if isinstance(terminate_payload, dict) else None
            if isinstance(terminate_data, dict) and terminate_data.get("exception") is not None:
                return HealthStatus(
                    False, "terminate connection", "terminate response contained an exception", terminate_payload
                )

        return HealthStatus(True, "terminate connection", payload={"namespaces": len(namespaces)})

    async def _send_command(self, websocket: Any, unique_id: int, command: str) -> dict[str, Any]:
        await websocket.send(json.dumps({"command": command, "endpoint": self.opcua_endpoint, "uniqueid": unique_id}))
        while True:
            raw = await asyncio.wait_for(websocket.recv(), timeout=self.health_timeout)
            payload = json.loads(raw)
            if payload.get("uniqueid") == unique_id:
                return payload
        raise BackendHealthError(f"health command {command!r} ended without a matching response")

    def _start_opcua_server(self) -> None:
        if self._port_open(self.opcua_port):
            raise BackendHealthError(f"OPC UA server port {self.opcua_port} is already in use")
        if not self.opcua_command:
            raise BackendHealthError("OPC UA server port is closed and no opcua_command was provided")
        self.results_root.mkdir(parents=True, exist_ok=True)
        with (self.results_root / "opcua.log").open("a", encoding="utf-8") as opcua_log:
            self._opcua_proc = subprocess.Popen(  # noqa: S603 - command is injected by test-suite infrastructure.
                self.opcua_command,
                cwd=str(self.root),
                stdout=opcua_log,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

    def _start_websocket_backend(self) -> None:
        if self._port_open(self.ws_port):
            raise BackendHealthError(f"WebSocket backend port {self.ws_port} is already in use")
        self.results_root.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["WS_PORT"] = str(self.ws_port)
        env["OPCUA_TEST_ENDPOINT"] = self.opcua_endpoint
        with (self.results_root / "websocket.log").open("a", encoding="utf-8") as websocket_log:
            self._ws_proc = subprocess.Popen(  # noqa: S603 - command is internal test infrastructure.
                [self.python_executable, "index.py"],
                cwd=str(self.root),
                env=env,
                stdout=websocket_log,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

    def _start_monitor(self) -> None:
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitor_stop.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_processes, name=f"{self.label}-backend-monitor")
        self._monitor_thread.daemon = True
        self._monitor_thread.start()

    def _monitor_processes(self) -> None:
        while not self._monitor_stop.is_set():
            for name, proc in (("websocket", self._ws_proc), ("opcua", self._opcua_proc)):
                if proc is None:
                    continue
                if proc.poll() is not None:
                    self._crashed = True
                    self._emit_event(
                        "crashed", {"process": name, "returncode": proc.returncode, "tail": self.stderr_tail()}
                    )
                    return
            time.sleep(0.2)

    def _terminate_process(self, proc: subprocess.Popen[str] | None, name: str) -> None:
        if proc is None:
            return
        if proc.poll() is not None:
            self._emit_event("process_stopped", {"process": name, "returncode": proc.returncode})
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        self._emit_event("process_stopped", {"process": name, "returncode": proc.returncode})

    def _wait_for_port_free(self, port: int) -> None:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if not self._port_open(port):
                return
            time.sleep(0.1)
        raise BackendHealthError(f"port {port} was still listening after backend stop")

    def _port_open(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            is_open = sock.connect_ex(("127.0.0.1", port)) == 0
        return is_open

    def _emit_event(self, event: str, data: dict[str, Any]) -> None:
        self.results_root.mkdir(parents=True, exist_ok=True)
        payload = {"event": event, "label": self.label, "time": time.time(), **data}
        with (self.results_root / "backend-events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
