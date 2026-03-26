"""Resource-management and cleanup tests.

Verifies that:
  - Connection.terminate() properly nulls out subscription_client
  - IJTInterface.disconnect() clears connection_list and is idempotent
  - Calling disconnect/terminate multiple times does not raise
  - None entries in connection_list are skipped gracefully
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

asyncua = pytest.importorskip("asyncua", reason="asyncua not installed")

from python.connection import Connection  # noqa: E402
from python.ijt_interface import IJTInterface  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_connection(server_url: str = "opc.tcp://localhost:40451") -> Connection:
    ws = AsyncMock()
    return Connection(server_url, ws)


# ===========================================================================
# 1. Connection.terminate() — subscription_client cleanup
# ===========================================================================


class TestConnectionTerminateCleanup:
    @pytest.mark.asyncio
    async def test_terminate_sets_subscription_client_to_none(self):
        """After terminate(), subscription_client must be None."""
        conn = _make_connection()

        mock_sub = MagicMock()
        mock_sub.disconnect = AsyncMock(return_value=None)
        conn.subscription_client = mock_sub

        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock(return_value=None)
        conn.client = mock_client

        with patch.object(conn, "_unsubscribe_and_cleanup", new=AsyncMock()):
            await conn.terminate()

        assert conn.subscription_client is None

    @pytest.mark.asyncio
    async def test_terminate_sets_terminated_flag(self):
        """After terminate(), self.terminated is True."""
        conn = _make_connection()

        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock(return_value=None)
        conn.client = mock_client

        with patch.object(conn, "_unsubscribe_and_cleanup", new=AsyncMock()):
            await conn.terminate()

        assert conn.terminated is True

    @pytest.mark.asyncio
    async def test_terminate_twice_is_idempotent(self):
        """Calling terminate() twice must not raise any exception."""
        conn = _make_connection()

        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock(return_value=None)
        conn.client = mock_client

        with patch.object(conn, "_unsubscribe_and_cleanup", new=AsyncMock()):
            await conn.terminate()
            await conn.terminate()  # second call must be a no-op

        assert conn.terminated is True

    @pytest.mark.asyncio
    async def test_terminate_with_none_client_returns_cleanly(self):
        """terminate() with client=None logs warning and returns without raising."""
        conn = _make_connection()
        conn.client = None
        conn.terminated = False

        await conn.terminate()  # must not raise

        assert conn.terminated is True

    @pytest.mark.asyncio
    async def test_terminate_with_already_terminated_is_noop(self):
        """If terminated=True already set, terminate() returns immediately without error."""
        conn = _make_connection()
        conn.terminated = True
        conn.client = MagicMock()  # would fail if actually used

        await conn.terminate()  # must not call client.disconnect

        conn.client.disconnect.assert_not_called()

    @pytest.mark.asyncio
    async def test_terminate_closes_event_handlers(self):
        """terminate() must call close() on both event handlers if present."""
        conn = _make_connection()

        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock(return_value=None)
        conn.client = mock_client

        mock_handler_joining = MagicMock()
        mock_handler_joining.close = AsyncMock(return_value=None)
        conn.handler_joining_event = mock_handler_joining

        mock_handler_result = MagicMock()
        mock_handler_result.close = AsyncMock(return_value=None)
        conn.handler_result_event = mock_handler_result

        with patch.object(conn, "_unsubscribe_and_cleanup", new=AsyncMock()):
            await conn.terminate()

        mock_handler_joining.close.assert_awaited_once()
        mock_handler_result.close.assert_awaited_once()


# ===========================================================================
# 2. IJTInterface.disconnect() — clears connection_list
# ===========================================================================


class TestIJTInterfaceDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_calls_terminate_on_all_connections(self):
        """disconnect() must call terminate() on every connection in the list."""
        iface = IJTInterface()

        mock_conn1 = MagicMock()
        mock_conn1.terminate = AsyncMock(return_value=None)
        mock_conn2 = MagicMock()
        mock_conn2.terminate = AsyncMock(return_value=None)

        iface.connection_list = {
            "opc.tcp://server1:4840": mock_conn1,
            "opc.tcp://server2:4840": mock_conn2,
        }

        await iface.disconnect()

        mock_conn1.terminate.assert_awaited_once()
        mock_conn2.terminate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_clears_connection_list(self):
        """After disconnect(), connection_list must be empty."""
        iface = IJTInterface()

        mock_conn = MagicMock()
        mock_conn.terminate = AsyncMock(return_value=None)
        iface.connection_list = {"opc.tcp://server:4840": mock_conn}

        await iface.disconnect()

        assert iface.connection_list == {}

    @pytest.mark.asyncio
    async def test_disconnect_twice_is_idempotent(self):
        """Calling disconnect() twice must not raise (second call is a no-op)."""
        iface = IJTInterface()
        iface.connection_list = {}

        await iface.disconnect()
        await iface.disconnect()
        # No exception raised → test passes

    @pytest.mark.asyncio
    async def test_disconnect_skips_none_connections(self):
        """disconnect() must not raise when connection_list contains None values."""
        iface = IJTInterface()
        iface.connection_list = {"opc.tcp://dead:4840": None}

        await iface.disconnect()  # must not raise

        assert iface.connection_list == {}

    @pytest.mark.asyncio
    async def test_disconnect_handles_terminate_exception_gracefully(self):
        """If terminate() raises, disconnect() must still clear the list."""
        iface = IJTInterface()

        mock_conn = MagicMock()
        mock_conn.terminate = AsyncMock(side_effect=RuntimeError("OPC UA error"))
        iface.connection_list = {"opc.tcp://server:4840": mock_conn}

        await iface.disconnect()  # must not raise

        assert iface.connection_list == {}
