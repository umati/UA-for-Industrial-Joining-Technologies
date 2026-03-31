"""
Unit tests for IJT_Web_Client/Python/connection.py

Covers:
- is_connection_open: no client, None client, open state, non-open state
- connect: all retries fail, Docker URL rewrite, connection established event
- terminate: already terminated, no client
- _unsubscribe_and_cleanup: connection not open, deletes result subscription
- methodcall: not connected returns exception
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("asyncua", reason="asyncua not installed")

from python.connection import Connection  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_connection(server_url="opc.tcp://localhost:40451", websocket=None):
    ws = websocket if websocket is not None else AsyncMock()
    return Connection(server_url, ws)


# ---------------------------------------------------------------------------
# is_connection_open
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_is_connection_open_returns_false_when_no_client():
    """Fresh Connection with no client attribute set returns False."""
    conn = _make_connection()
    # The __init__ already sets self.client = None, but let's also confirm
    # via del to simulate "attribute missing" branch
    del conn.client
    assert await conn.is_connection_open() is False


@pytest.mark.asyncio
async def test_is_connection_open_returns_false_when_client_is_none():
    conn = _make_connection()
    conn.client = None
    assert await conn.is_connection_open() is False


@pytest.mark.asyncio
async def test_is_connection_open_returns_true_when_state_is_open():
    conn = _make_connection()
    mock_client = MagicMock()
    mock_client.uaclient.protocol.state = "open"
    conn.client = mock_client
    assert await conn.is_connection_open() is True


@pytest.mark.asyncio
async def test_is_connection_open_returns_false_when_state_is_not_open():
    conn = _make_connection()
    mock_client = MagicMock()
    mock_client.uaclient.protocol.state = "closed"
    conn.client = mock_client
    assert await conn.is_connection_open() is False


# ---------------------------------------------------------------------------
# connect — retry exhaustion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_returns_exception_when_all_retries_fail(monkeypatch):
    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")
    monkeypatch.setenv("OPCUA_CONNECT_DELAY_SEC", "0.01")
    monkeypatch.setenv("OPCUA_CONNECT_MAX_DELAY_SEC", "0.01")

    mock_client = MagicMock()
    mock_client.connect = AsyncMock(side_effect=ConnectionRefusedError("refused"))
    mock_client.set_security_string = MagicMock(return_value=None)

    with patch("python.connection.Client", return_value=mock_client):
        conn = _make_connection()
        result = await conn.connect()

    assert "exception" in result


# ---------------------------------------------------------------------------
# connect — Docker URL rewrite
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_docker_url_rewrite(monkeypatch):
    monkeypatch.setenv("IS_DOCKER", "true")
    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")
    monkeypatch.setenv("OPCUA_CONNECT_DELAY_SEC", "0.01")
    monkeypatch.setenv("OPCUA_CONNECT_MAX_DELAY_SEC", "0.01")

    created_urls = []

    def _fake_client(url, timeout=60):
        created_urls.append(url)
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(side_effect=ConnectionRefusedError("refused"))
        mock_client.set_security_string = MagicMock(return_value=None)
        return mock_client

    with patch("python.connection.Client", side_effect=_fake_client):
        conn = _make_connection(server_url="opc.tcp://localhost:40451")
        await conn.connect()

    assert len(created_urls) == 1
    assert "host.docker.internal" in created_urls[0]
    assert "localhost" not in created_urls[0]


# ---------------------------------------------------------------------------
# connect — connection established event sent via websocket
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_sends_connection_established_on_success(monkeypatch):
    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")

    ws = AsyncMock()
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(return_value=None)
    mock_client.load_type_definitions = AsyncMock(return_value=None)
    mock_client.get_root_node = MagicMock(return_value=MagicMock())
    mock_client.set_security_string = MagicMock(return_value=None)

    with patch("python.connection.Client", return_value=mock_client):
        conn = _make_connection(server_url="opc.tcp://localhost:40451", websocket=ws)
        result = await conn.connect()

    assert result.get("command") == "connection established"
    ws.send.assert_awaited_once()
    sent_payload = json.loads(ws.send.call_args[0][0])
    assert sent_payload["command"] == "connection established"
    assert sent_payload["endpoint"] == "opc.tcp://localhost:40451"


# ---------------------------------------------------------------------------
# terminate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_terminate_does_nothing_when_already_terminated():
    conn = _make_connection()
    conn.terminated = True
    # Must return without raising even though client is not set up
    await conn.terminate()
    # terminated flag remains True, no error raised
    assert conn.terminated is True


@pytest.mark.asyncio
async def test_terminate_skips_when_no_client():
    conn = _make_connection()
    conn.client = None
    # Must return without raising
    await conn.terminate()
    assert conn.terminated is True


# ---------------------------------------------------------------------------
# _unsubscribe_and_cleanup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsubscribe_skips_when_connection_not_open():
    conn = _make_connection()
    conn.sub_result_event = MagicMock()
    conn.sub_joining_event = MagicMock()

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=False)):
        await conn._unsubscribe_and_cleanup()

    assert conn.sub_result_event == "sub"
    assert conn.sub_joining_event == "sub"


@pytest.mark.asyncio
async def test_unsubscribe_deletes_result_subscription():
    conn = _make_connection()

    mock_sub = MagicMock()
    mock_sub.subscription_id = 42
    conn.sub_result_event = mock_sub

    mock_client = MagicMock()
    mock_client.delete_subscriptions = AsyncMock(return_value=None)
    conn.client = mock_client

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        await conn._unsubscribe_and_cleanup()

    mock_client.delete_subscriptions.assert_awaited_once_with([42])
    assert conn.sub_result_event == "sub"


# ---------------------------------------------------------------------------
# methodcall — not connected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_methodcall_returns_exception_when_not_connected():
    conn = _make_connection()

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=False)):
        result = await conn.methodcall({
            "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
            "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateJobResult"},
            "arguments": [],
        })

    assert "exception" in result


# ---------------------------------------------------------------------------
# methodcall — connected path: valid keys reach client.get_node()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_methodcall_valid_keys_connected_reaches_get_node():
    """methodcall with correct keys when mock-connected calls client.get_node()."""
    conn = _make_connection()

    mock_input_args_node = MagicMock()
    mock_input_args_node.get_value = AsyncMock(return_value=[])

    mock_method = MagicMock()
    mock_method.get_child = AsyncMock(return_value=mock_input_args_node)

    mock_obj = MagicMock()
    captured_call_args: list = []

    async def _fake_call(_method, *args):
        captured_call_args.extend(args)
        return []

    mock_obj.call_method = _fake_call

    mock_client = MagicMock()
    mock_client.get_node = MagicMock(side_effect=[mock_obj, mock_method])
    conn.client = mock_client

    with patch("python.connection.serialize_full_event", return_value=[]):
        with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
            result = await conn.methodcall({
                "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                "arguments": [],
            })

    assert mock_client.get_node.call_count == 2
    assert "output" in result
    assert "Missing" not in result.get("exception", "")


@pytest.mark.asyncio
async def test_methodcall_string_argument_type_mapping():
    """String argument (dataType=12) is mapped to ua.VariantType.String."""
    conn = _make_connection()
    from asyncua import ua

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
                "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                "arguments": [{"dataType": 12, "value": "hello"}],
            })

    assert "output" in result
    assert len(captured) == 1
    assert captured[0].VariantType == ua.VariantType.String


@pytest.mark.asyncio
async def test_methodcall_uint32_negative_value_abs_applied():
    """UInt32 (dataType=7) with negative value → abs() applied before Variant creation."""
    conn = _make_connection()

    mock_arg_desc = MagicMock()
    mock_arg_desc.DataType.Identifier = 7  # UInt32

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
                "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                "arguments": [{"dataType": 7, "value": -42}],
            })

    assert "output" in result
    assert len(captured) == 1
    assert captured[0].Value >= 0, (
        f"Expected non-negative UInt32 value after abs(), got {captured[0].Value}"
    )


@pytest.mark.asyncio
async def test_methodcall_localized_text_dict_converted_to_ua_type():
    """LocalizedText (dataType=21) dict is converted to ua.LocalizedText object."""
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
                "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                "arguments": [{"dataType": 21, "value": {"Text": "Hello", "Locale": "en"}}],
            })

    assert "output" in result
    assert len(captured) == 1
    assert isinstance(captured[0].Value, ua.LocalizedText)


@pytest.mark.asyncio
async def test_methodcall_argument_count_mismatch_logs_but_continues():
    """Arg count mismatch (1 expected, 0 provided) logs warning but does not crash."""
    conn = _make_connection()

    mock_arg_desc = MagicMock()
    mock_arg_desc.DataType.Identifier = 12  # String

    mock_input_args_node = MagicMock()
    mock_input_args_node.get_value = AsyncMock(return_value=[mock_arg_desc])

    mock_method = MagicMock()
    mock_method.get_child = AsyncMock(return_value=mock_input_args_node)

    mock_obj = MagicMock()
    mock_obj.call_method = AsyncMock(return_value=[])

    mock_client = MagicMock()
    mock_client.get_node = MagicMock(side_effect=[mock_obj, mock_method])
    conn.client = mock_client

    with patch("python.connection.serialize_full_event", return_value=[]):
        with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
            result = await conn.methodcall({
                "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                "arguments": [],  # 0 provided, 1 expected — mismatch
            })

    assert "output" in result or "exception" in result
    assert "NoneType" not in result.get("exception", "")


@pytest.mark.asyncio
async def test_methodcall_missing_input_arguments_node_returns_exception():
    """When get_child('0:InputArguments') raises, returns exception dict not crash."""
    conn = _make_connection()

    mock_method = MagicMock()
    mock_method.get_child = AsyncMock(
        side_effect=Exception("BadNoMatch: InputArguments not found")
    )

    mock_obj = MagicMock()
    mock_client = MagicMock()
    mock_client.get_node = MagicMock(side_effect=[mock_obj, mock_method])
    conn.client = mock_client

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        result = await conn.methodcall({
            "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
            "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
            "arguments": [],
        })

    assert "exception" in result
    assert "NoneType" not in result["exception"]


@pytest.mark.asyncio
async def test_methodcall_array_argument_creates_list_variant():
    """List value for String type creates a Variant carrying the list."""
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
                "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                "arguments": [{"dataType": 12, "value": ["a", "b", "c"]}],
            })

    assert "output" in result
    assert len(captured) == 1
    assert isinstance(captured[0].Value, list)
