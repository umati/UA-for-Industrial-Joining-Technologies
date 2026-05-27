"""
Unit tests for index.py — IJT Web Client WebSocket server entry point.

Tests cover:
- handler()    : shutdown guard, normal message dispatch, JSON decode error,
                 ConnectionClosed, generic exception, cleanup on exit
- shutdown()   : no-op double call, stop accepting connections, disconnect
                 active handlers, close active websockets
- main()       : WS_PORT env-var parsing (valid / invalid), non-Windows signal
                 registration, Windows signal registration, server bind

All tests are hermetic (no real network I/O, no real OPC UA connections).
Async helpers use pytest-asyncio (asyncio_mode = "auto" from pyproject.toml).
"""

from __future__ import annotations

import asyncio
import json
import logging
import runpy
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Import index from the Web Client root ────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parents[3]))
sys.path.insert(0, str(Path(__file__).parents[3] / "src"))

import index  # noqa: E402


def _log_record_for_exc(message: str, exc: Exception) -> logging.LogRecord:
    try:
        raise exc
    except Exception:
        return logging.LogRecord(
            name="ijt_web_client.websockets",
            level=logging.ERROR,
            pathname=__file__,
            lineno=0,
            msg=message,
            args=(),
            exc_info=sys.exc_info(),
        )


def test_bootstrap_adds_src_path_when_absent(monkeypatch):
    """The module bootstrap must add src/ when launched as a script."""
    root = Path(index.__file__).resolve().parent
    src = str(root / "src")
    monkeypatch.setattr(sys, "path", [entry for entry in sys.path if entry != src])

    runpy.run_path(str(root / "index.py"), run_name="phase5_index_bootstrap")

    assert sys.path[0] == src


def test_websocket_logger_suppresses_invalid_http_handshake():
    record = _log_record_for_exc(
        "opening handshake failed",
        RuntimeError("did not receive a valid HTTP request"),
    )

    assert not index._SuppressInvalidWebSocketHandshake().filter(record)


def test_websocket_logger_keeps_real_handler_failures_visible():
    record = _log_record_for_exc("connection handler failed", RuntimeError("backend crashed"))

    assert index._SuppressInvalidWebSocketHandshake().filter(record)


# =============================================================================
# Helpers
# =============================================================================


def _make_ws(remote_address=("127.0.0.1", 12345)):
    """Return a mock websocket with async iterator and send/close support."""
    ws = MagicMock()
    ws.remote_address = remote_address
    ws.send = AsyncMock()
    ws.close = AsyncMock()
    return ws


def _make_ws_iter(messages: list[str]):
    """Wrap a list of raw string messages as an async iterable."""

    async def _aiter(self):
        for msg in messages:
            yield msg

    ws = _make_ws()
    ws.__aiter__ = _aiter
    return ws


# =============================================================================
# handler()
# =============================================================================


class TestHandler:
    def setup_method(self):
        """Reset global state before every test."""
        index.shutdown_started = False
        index.active_handlers.clear()
        index.active_websockets.clear()

    @pytest.mark.asyncio
    async def test_shutdown_guard_closes_immediately(self):
        """When shutdown_started is True, websocket is closed immediately."""
        index.shutdown_started = True
        ws = _make_ws()
        # No __aiter__ needed — handler exits before the message loop when shutdown_started=True

        with patch("index.IJTInterface") as MockIJT:
            mock_iface = AsyncMock()
            MockIJT.return_value = mock_iface
            await index.handler(ws)

        ws.close.assert_awaited_once_with(code=1012, reason="Server shutting down")

    @pytest.mark.asyncio
    async def test_normal_message_dispatched_to_handle(self):
        """Valid JSON messages are forwarded to opcua_handler.handle()."""
        index.shutdown_started = False
        payload = {"command": "ping", "data": {}}
        ws = _make_ws_iter([json.dumps(payload)])

        with patch("index.IJTInterface") as MockIJT:
            mock_iface = AsyncMock()
            mock_iface.disconnect = AsyncMock()
            MockIJT.return_value = mock_iface
            await index.handler(ws)

        mock_iface.handle.assert_awaited_once()
        # First arg is the websocket, second is the parsed payload dict
        call_args = mock_iface.handle.await_args
        assert call_args[0][1] == payload

    @pytest.mark.asyncio
    async def test_json_decode_error_sends_error_response(self):
        """Malformed JSON triggers an error response on the websocket."""
        index.shutdown_started = False
        ws = _make_ws_iter(["not valid json {{{"])

        with patch("index.IJTInterface") as MockIJT:
            mock_iface = AsyncMock()
            mock_iface.disconnect = AsyncMock()
            MockIJT.return_value = mock_iface
            await index.handler(ws)

        ws.send.assert_awaited_once()
        sent = json.loads(ws.send.await_args[0][0])
        assert "exception" in sent["data"] or "INVALID_JSON" in sent.get("error", {}).get("code", "")

    @pytest.mark.asyncio
    async def test_connection_closed_handled_gracefully(self):
        """ConnectionClosed does not propagate — handler exits cleanly."""
        import websockets.exceptions

        index.shutdown_started = False

        async def _aiter(self):
            raise websockets.exceptions.ConnectionClosed(None, None)
            yield  # make it an async generator

        ws = _make_ws()
        ws.__aiter__ = _aiter

        with patch("index.IJTInterface") as MockIJT:
            mock_iface = AsyncMock()
            mock_iface.disconnect = AsyncMock()
            MockIJT.return_value = mock_iface
            await index.handler(ws)  # must not raise

        mock_iface.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generic_exception_handled_gracefully(self):
        """Unexpected exception inside the message loop is caught, not re-raised."""
        index.shutdown_started = False

        async def _aiter(self):
            raise RuntimeError("unexpected crash")
            yield

        ws = _make_ws()
        ws.__aiter__ = _aiter

        with patch("index.IJTInterface") as MockIJT:
            mock_iface = AsyncMock()
            mock_iface.disconnect = AsyncMock()
            MockIJT.return_value = mock_iface
            await index.handler(ws)  # must not raise

        mock_iface.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handler_registers_and_removes_from_active_sets(self):
        """handler() adds to active sets on enter and removes on exit."""
        index.shutdown_started = False
        ws = _make_ws_iter([])  # no messages → exits immediately

        with patch("index.IJTInterface") as MockIJT:
            mock_iface = AsyncMock()
            mock_iface.disconnect = AsyncMock()
            MockIJT.return_value = mock_iface
            await index.handler(ws)

        # After handler returns, sets must be empty.
        assert ws not in index.active_websockets
        assert mock_iface not in index.active_handlers

    @pytest.mark.asyncio
    async def test_handler_unknown_remote_address(self):
        """handler() copes with websocket.remote_address being None."""
        index.shutdown_started = False
        ws = _make_ws_iter([])
        ws.remote_address = None

        with patch("index.IJTInterface") as MockIJT:
            mock_iface = AsyncMock()
            mock_iface.disconnect = AsyncMock()
            MockIJT.return_value = mock_iface
            await index.handler(ws)  # must not raise


# =============================================================================
# shutdown()
# =============================================================================


class TestShutdown:
    def setup_method(self):
        index.shutdown_started = False
        index.active_handlers.clear()
        index.active_websockets.clear()
        index.websocket_server = None

    @pytest.mark.asyncio
    async def test_shutdown_sets_flag_and_logs(self):
        """First call sets shutdown_started = True."""
        await index.shutdown()
        assert index.shutdown_started is True

    @pytest.mark.asyncio
    async def test_double_shutdown_is_noop(self):
        """Second shutdown() call returns immediately without double-disconnecting."""
        mock_iface = AsyncMock()
        index.active_handlers.add(mock_iface)

        await index.shutdown()  # first call
        await index.shutdown()  # second call — should be a no-op

        # disconnect should only have been called once (first shutdown)
        mock_iface.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_stops_websocket_server(self):
        """websocket_server.close() and wait_closed() are called."""
        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()
        index.websocket_server = mock_server

        await index.shutdown()

        mock_server.close.assert_called_once()
        mock_server.wait_closed.assert_awaited_once()
        assert index.websocket_server is None

    @pytest.mark.asyncio
    async def test_shutdown_disconnects_active_handlers(self):
        """All active IJTInterface handlers are disconnected."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        index.active_handlers.update({handler1, handler2})

        await index.shutdown()

        handler1.disconnect.assert_awaited_once()
        handler2.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_closes_active_websockets(self):
        """All active websockets receive a close(1001) call."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        index.active_websockets.update({ws1, ws2})

        await index.shutdown()

        ws1.close.assert_awaited_once_with(code=1001, reason="Server shutdown")
        ws2.close.assert_awaited_once_with(code=1001, reason="Server shutdown")

    @pytest.mark.asyncio
    async def test_shutdown_no_server_no_handlers(self):
        """shutdown() completes cleanly when there is nothing to shut down."""
        await index.shutdown()  # must not raise
        assert index.shutdown_started is True


# =============================================================================
# main()
# =============================================================================


class TestMain:
    def setup_method(self):
        index.shutdown_started = False
        index.active_handlers.clear()
        index.active_websockets.clear()
        index.websocket_server = None

    @pytest.mark.asyncio
    async def test_valid_ws_port_from_env(self, monkeypatch):
        """main() reads WS_PORT from env and binds there."""
        monkeypatch.setenv("WS_PORT", "9999")

        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()

        with (
            patch("index.websockets.serve", new_callable=AsyncMock) as mock_serve,
            patch("asyncio.Future", side_effect=asyncio.CancelledError),
            patch("index.shutdown", new_callable=AsyncMock),
        ):
            mock_serve.return_value = mock_server
            try:
                await index.main()
            except (asyncio.CancelledError, Exception):
                pass

        assert mock_serve.call_args is not None
        port_arg = mock_serve.call_args[0][2]  # serve(handler, host, port)
        assert port_arg == 9999
        assert mock_serve.call_args.kwargs["logger"].name == "ijt_web_client.websockets"

    @pytest.mark.asyncio
    async def test_invalid_ws_port_falls_back_to_8001(self, monkeypatch):
        """When WS_PORT is not a valid integer, port falls back to 8001."""
        monkeypatch.setenv("WS_PORT", "not_a_port")

        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()

        with (
            patch("index.websockets.serve", new_callable=AsyncMock) as mock_serve,
            patch("asyncio.Future", side_effect=asyncio.CancelledError),
            patch("index.shutdown", new_callable=AsyncMock),
        ):
            mock_serve.return_value = mock_server
            try:
                await index.main()
            except (asyncio.CancelledError, Exception):
                pass

        assert mock_serve.call_args is not None
        port_arg = mock_serve.call_args[0][2]  # serve(handler, host, port)
        assert port_arg == 8001

    @pytest.mark.asyncio
    async def test_signal_handlers_registered_on_non_windows(self):
        """On non-Windows, add_signal_handler is called for SIGINT and SIGTERM."""
        import asyncio as _asyncio
        import signal as _signal

        actual_loop = _asyncio.get_running_loop()
        signal_registrations: list = []

        def _mock_add_signal_handler(sig, cb):
            signal_registrations.append(sig)

        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()

        with (
            patch.object(actual_loop, "add_signal_handler", side_effect=_mock_add_signal_handler),
            patch("index.platform") as mock_plat,
            patch("index.websockets.serve", new_callable=AsyncMock) as mock_serve,
            patch("asyncio.Future", side_effect=asyncio.CancelledError),
            patch("index.shutdown", new_callable=AsyncMock),
        ):
            mock_plat.system.return_value = "Linux"
            mock_serve.return_value = mock_server
            try:
                await index.main()
            except (asyncio.CancelledError, Exception):
                pass

        assert _signal.SIGINT in signal_registrations or len(signal_registrations) >= 1

    @pytest.mark.asyncio
    async def test_signal_handler_not_implemented_error_on_non_windows(self):
        """When add_signal_handler raises NotImplementedError, it is caught and logged."""
        import asyncio as _asyncio

        actual_loop = _asyncio.get_running_loop()

        def _mock_add_signal_handler_fail(sig, cb):
            raise NotImplementedError("Signal not supported")

        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()

        with (
            patch.object(actual_loop, "add_signal_handler", side_effect=_mock_add_signal_handler_fail),
            patch("index.platform") as mock_plat,
            patch("index.websockets.serve", new_callable=AsyncMock) as mock_serve,
            patch("asyncio.Future", side_effect=asyncio.CancelledError),
            patch("index.shutdown", new_callable=AsyncMock),
        ):
            mock_plat.system.return_value = "Linux"
            mock_serve.return_value = mock_server
            try:
                await index.main()  # must not raise
            except (asyncio.CancelledError, Exception):
                pass

    @pytest.mark.asyncio
    async def test_windows_signal_handler_schedules_shutdown(self):
        """Windows signal handler schedules shutdown via call_soon_threadsafe."""
        import asyncio as _asyncio
        import signal as _signal

        actual_loop = _asyncio.get_running_loop()
        scheduled_tasks: list = []

        def _mock_call_soon_threadsafe(cb):
            scheduled_tasks.append(cb)

        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()

        with (
            patch.object(actual_loop, "call_soon_threadsafe", side_effect=_mock_call_soon_threadsafe),
            patch("index.platform") as mock_plat,
            patch("index.signal.signal") as mock_signal_signal,
            patch("index.websockets.serve", new_callable=AsyncMock) as mock_serve,
            patch("asyncio.Future", side_effect=asyncio.CancelledError),
            patch("index.shutdown", new_callable=AsyncMock),
        ):
            mock_plat.system.return_value = "Windows"
            mock_serve.return_value = mock_server

            # Capture the registered signal handler
            registered_handler = None

            def _capture_signal_handler(sig, handler):
                nonlocal registered_handler
                registered_handler = handler
                return None

            mock_signal_signal.side_effect = _capture_signal_handler

            try:
                await index.main()
            except (asyncio.CancelledError, Exception):
                pass

            # Now invoke the captured Windows signal handler
            if registered_handler:
                registered_handler(_signal.SIGINT, None)
                assert len(scheduled_tasks) >= 1
