"""Security-focused unit tests for the IJT Web Client Python backend.

Verifies that unexpected, oversized, or malicious inputs are handled
gracefully (return exception dicts) rather than crashing or exposing
internal state.
"""

from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

_ = pytest.importorskip("asyncua", reason="asyncua not installed")

from python.connection import Connection  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_connection(server_url: str = "opc.tcp://localhost:40451") -> Connection:
    ws = AsyncMock()
    return Connection(server_url, ws)


def _mock_client_fails():
    """MagicMock Client that always raises ConnectionRefusedError on connect()."""
    mock = MagicMock()
    mock.connect = AsyncMock(side_effect=ConnectionRefusedError("refused"))
    mock.set_security_string = MagicMock(return_value=None)
    return mock


# ===========================================================================
# 1. Endpoint injection — shell metacharacters must not cause a crash
# ===========================================================================


class TestEndpointInjection:
    """Unusual endpoint strings must always produce an exception dict, never crash."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", [
        "opc.tcp://localhost; rm -rf /",
        "opc.tcp://`whoami`:40451",
        "opc.tcp://$(id):40451",
        "opc.tcp://127.0.0.1:40451\n\nGET / HTTP/1.1",
        "opc.tcp://' OR '1'='1",
        "opc.tcp://<script>alert(1)</script>:40451",
    ])
    async def test_shell_metacharacter_endpoint_returns_exception(
        self, endpoint: str, monkeypatch
    ):
        """Shell metacharacters/injection patterns in endpoint → exception dict, not crash."""
        monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")
        monkeypatch.setenv("OPCUA_CONNECT_DELAY_SEC", "0.01")
        monkeypatch.setenv("OPCUA_CONNECT_MAX_DELAY_SEC", "0.01")

        with patch("python.connection.Client", return_value=_mock_client_fails()):
            conn = Connection(endpoint, AsyncMock())
            result = await conn.connect()

        assert "exception" in result, (
            f"Expected exception dict for malicious endpoint {endpoint!r}, got {result}"
        )

    @pytest.mark.asyncio
    async def test_empty_string_endpoint_returns_exception(self, monkeypatch):
        """Empty endpoint string → exception dict, not crash."""
        monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")
        monkeypatch.setenv("OPCUA_CONNECT_DELAY_SEC", "0.01")
        monkeypatch.setenv("OPCUA_CONNECT_MAX_DELAY_SEC", "0.01")

        with patch("python.connection.Client", return_value=_mock_client_fails()):
            conn = Connection("", AsyncMock())
            result = await conn.connect()

        assert "exception" in result

    @pytest.mark.asyncio
    async def test_extremely_long_endpoint_returns_exception(self, monkeypatch):
        """10 000-character endpoint string → exception dict, not MemoryError/crash."""
        monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")
        monkeypatch.setenv("OPCUA_CONNECT_DELAY_SEC", "0.01")
        monkeypatch.setenv("OPCUA_CONNECT_MAX_DELAY_SEC", "0.01")

        long_url = "opc.tcp://" + "a" * 10_000 + ":40451"

        with patch("python.connection.Client", return_value=_mock_client_fails()):
            conn = Connection(long_url, AsyncMock())
            result = await conn.connect()

        assert "exception" in result


# ===========================================================================
# 2. Oversized payloads
# ===========================================================================


class TestOversizedPayloads:
    @pytest.mark.asyncio
    async def test_methodcall_with_1000_arguments_does_not_crash(self):
        """1 000 arguments in methodcall payload → exception dict, not MemoryError/crash."""
        conn = _make_connection()
        large_args = [{"dataType": 12, "value": f"arg_{i}"} for i in range(1000)]

        with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=False)):
            result = await conn.methodcall({
                "objectnode": {"NamespaceIndex": 1, "Identifier": "TS"},
                "methodnode": {"NamespaceIndex": 1, "Identifier": "M"},
                "arguments": large_args,
            })

        assert "exception" in result

    def test_deeply_nested_json_does_not_raise_recursion_error(self):
        """json.loads() must not raise RecursionError on 100-level nested JSON."""
        nested: dict = {}
        current = nested
        for _ in range(100):
            inner: dict = {}
            current["a"] = inner
            current = inner

        serialized = json.dumps(nested)
        try:
            parsed = json.loads(serialized)
        except RecursionError:
            pytest.fail("json.loads() raised RecursionError on 100-level nesting")

        assert parsed is not None

    @pytest.mark.asyncio
    async def test_browse_with_very_long_nodeid_returns_exception(self):
        """browse() with a 5000-char nodeid → exception dict, not crash."""
        conn = _make_connection()
        conn.client = MagicMock()
        conn.client.get_node = MagicMock(
            side_effect=Exception("Invalid node id: string too long")
        )

        result = await conn.browse({"nodeid": "ns=1;s=" + "x" * 5000})
        assert "exception" in result


# ===========================================================================
# 3. methodcall — argument value sanitization
# ===========================================================================


class TestMethodcallArgumentSanitization:
    @pytest.mark.asyncio
    async def test_string_argument_with_none_value_is_sanitized_to_empty_string(self):
        """None argument value for String type (dataType=12) → sanitized to '' not crash."""
        conn = _make_connection()

        mock_arg_desc = MagicMock()
        mock_arg_desc.DataType.Identifier = 12  # String

        mock_input_args_node = MagicMock()
        mock_input_args_node.get_value = AsyncMock(return_value=[mock_arg_desc])

        mock_method = MagicMock()
        mock_method.get_child = AsyncMock(return_value=mock_input_args_node)

        mock_obj = MagicMock()
        captured: list = []

        async def _capture(_method, *args):
            captured.extend(args)
            return []

        mock_obj.call_method = _capture

        mock_client = MagicMock()
        mock_client.get_node = MagicMock(side_effect=[mock_obj, mock_method])
        conn.client = mock_client

        with patch("python.connection.serialize_full_event", return_value=[]):
            with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
                result = await conn.methodcall({
                    "objectnode": {"NamespaceIndex": 1, "Identifier": "TS"},
                    "methodnode": {"NamespaceIndex": 1, "Identifier": "M"},
                    "arguments": [{"dataType": 12, "value": None}],
                })

        assert "output" in result
        assert len(captured) == 1
        assert captured[0].Value == "", (
            f"Expected empty string sanitization of None, got {captured[0].Value!r}"
        )

    @pytest.mark.asyncio
    async def test_localized_text_none_value_sanitized_to_empty_localized_text(self):
        """None argument value for LocalizedText (dataType=21) → ua.LocalizedText('', 'en')."""
        conn = _make_connection()
        from asyncua import ua

        mock_arg_desc = MagicMock()
        mock_arg_desc.DataType.Identifier = 21  # LocalizedText

        mock_input_args_node = MagicMock()
        mock_input_args_node.get_value = AsyncMock(return_value=[mock_arg_desc])

        mock_method = MagicMock()
        mock_method.get_child = AsyncMock(return_value=mock_input_args_node)

        mock_obj = MagicMock()
        captured: list = []

        async def _capture(_method, *args):
            captured.extend(args)
            return []

        mock_obj.call_method = _capture

        mock_client = MagicMock()
        mock_client.get_node = MagicMock(side_effect=[mock_obj, mock_method])
        conn.client = mock_client

        with patch("python.connection.serialize_full_event", return_value=[]):
            with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
                result = await conn.methodcall({
                    "objectnode": {"NamespaceIndex": 1, "Identifier": "TS"},
                    "methodnode": {"NamespaceIndex": 1, "Identifier": "M"},
                    "arguments": [{"dataType": 21, "value": None}],
                })

        assert "output" in result
        assert len(captured) == 1
        assert isinstance(captured[0].Value, ua.LocalizedText)
