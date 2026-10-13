"""Unit tests for docker_healthcheck.py (HTTP + real WebSocket upgrade)."""

from __future__ import annotations

import importlib.util
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_MODULE_PATH = _PROJECT_ROOT / "docker_healthcheck.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("ijt_docker_healthcheck", _MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def health():
    return _load_module()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
    return port


class _OkHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_args) -> None:
        return


class _ServerErrorHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(500)
        self.end_headers()
        self.wfile.write(b"err")

    def log_message(self, *_args) -> None:
        return


def _serve_http(handler_cls: type[BaseHTTPRequestHandler], port: int) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", port), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _serve_tcp_only(port: int) -> socket.socket:
    """Accept TCP connections but never complete a WebSocket handshake."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
    sock.listen(5)

    def _loop() -> None:
        while True:
            try:
                conn, _addr = sock.accept()
            except OSError:
                return
            try:
                conn.recv(1024)
            except OSError:
                pass
            finally:
                conn.close()

    threading.Thread(target=_loop, daemon=True).start()
    return sock


def test_healthcheck_fails_when_websocket_is_tcp_only(health, monkeypatch) -> None:
    """A bare TCP listener must not satisfy the WebSocket upgrade probe."""
    http_port = _free_port()
    ws_port = _free_port()
    http_server = _serve_http(_OkHandler, http_port)
    tcp_sock = _serve_tcp_only(ws_port)
    monkeypatch.setenv("HTTP_PORT", str(http_port))
    monkeypatch.setenv("WS_PORT", str(ws_port))
    try:
        assert health.main() == 1
    finally:
        http_server.shutdown()
        tcp_sock.close()


def test_healthcheck_fails_on_http_server_error(health, monkeypatch) -> None:
    http_port = _free_port()
    ws_port = _free_port()
    http_server = _serve_http(_ServerErrorHandler, http_port)
    monkeypatch.setenv("HTTP_PORT", str(http_port))
    monkeypatch.setenv("WS_PORT", str(ws_port))
    try:
        assert health.main() == 1
    finally:
        http_server.shutdown()


def test_healthcheck_passes_with_http_and_websocket_upgrade(health, monkeypatch) -> None:
    websockets = pytest.importorskip("websockets")
    import asyncio
    import time

    http_port = _free_port()
    ws_port = _free_port()
    http_server = _serve_http(_OkHandler, http_port)
    started = threading.Event()
    stop = threading.Event()

    async def _echo(websocket) -> None:
        async for _message in websocket:
            pass

    def _ws_thread() -> None:
        async def _run() -> None:
            async with websockets.serve(_echo, "127.0.0.1", ws_port):
                started.set()
                while not stop.is_set():
                    await asyncio.sleep(0.05)

        asyncio.run(_run())

    thread = threading.Thread(target=_ws_thread, daemon=True)
    thread.start()
    assert started.wait(timeout=5)
    time.sleep(0.05)
    monkeypatch.setenv("HTTP_PORT", str(http_port))
    monkeypatch.setenv("WS_PORT", str(ws_port))
    try:
        assert health.main() == 0
    finally:
        stop.set()
        http_server.shutdown()
        thread.join(timeout=2)
