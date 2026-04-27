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
        result = await conn.methodcall(
            {
                "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateJobResult"},
                "arguments": [],
            }
        )

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
            result = await conn.methodcall(
                {
                    "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                    "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                    "arguments": [],
                }
            )

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
            result = await conn.methodcall(
                {
                    "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                    "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                    "arguments": [{"dataType": 12, "value": "hello"}],
                }
            )

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
            result = await conn.methodcall(
                {
                    "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                    "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                    "arguments": [{"dataType": 7, "value": -42}],
                }
            )

    assert "output" in result
    assert len(captured) == 1
    assert captured[0].Value >= 0, f"Expected non-negative UInt32 value after abs(), got {captured[0].Value}"


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
            result = await conn.methodcall(
                {
                    "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                    "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                    "arguments": [{"dataType": 21, "value": {"Text": "Hello", "Locale": "en"}}],
                }
            )

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
            result = await conn.methodcall(
                {
                    "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                    "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                    "arguments": [],  # 0 provided, 1 expected — mismatch
                }
            )

    assert "output" in result or "exception" in result
    assert "NoneType" not in result.get("exception", "")


@pytest.mark.asyncio
async def test_methodcall_missing_input_arguments_node_returns_exception():
    """When get_child('0:InputArguments') raises, returns exception dict not crash."""
    conn = _make_connection()

    mock_method = MagicMock()
    mock_method.get_child = AsyncMock(side_effect=Exception("BadNoMatch: InputArguments not found"))

    mock_obj = MagicMock()
    mock_client = MagicMock()
    mock_client.get_node = MagicMock(side_effect=[mock_obj, mock_method])
    conn.client = mock_client

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        result = await conn.methodcall(
            {
                "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                "arguments": [],
            }
        )

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
            result = await conn.methodcall(
                {
                    "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                    "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                    "arguments": [{"dataType": 12, "value": ["a", "b", "c"]}],
                }
            )

    assert "output" in result
    assert len(captured) == 1
    assert isinstance(captured[0].Value, list)


# ---------------------------------------------------------------------------
# id_object_to_string — pure function, no OPC UA required
# ---------------------------------------------------------------------------


from python.connection import id_object_to_string  # noqa: E402


def test_id_object_to_string_returns_string_unchanged():
    assert id_object_to_string("ns=2;i=1001") == "ns=2;i=1001"


def test_id_object_to_string_dict_integer_identifier():
    result = id_object_to_string({"Identifier": 1001, "NamespaceIndex": 2})
    assert result == "ns=2;i=1001"


def test_id_object_to_string_dict_string_identifier():
    result = id_object_to_string({"Identifier": "MyNode", "NamespaceIndex": 3})
    assert result == "ns=3;s=MyNode"


def test_id_object_to_string_dict_zero_namespace():
    result = id_object_to_string({"Identifier": 84, "NamespaceIndex": 0})
    assert result == "ns=0;i=84"


def test_id_object_to_string_fallback_on_int():
    result = id_object_to_string(42)
    assert result == "42"


def test_id_object_to_string_fallback_on_none():
    result = id_object_to_string(None)
    assert result == "None"


def test_id_object_to_string_fallback_on_list():
    result = id_object_to_string([1, 2, 3])
    assert result == "[1, 2, 3]"


# ---------------------------------------------------------------------------
# connect — early return when already open (line 121)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_returns_immediately_when_already_open():
    """connect() returns success immediately if is_connection_open() is True."""
    conn = _make_connection(server_url="opc.tcp://localhost:4840")
    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        result = await conn.connect()
    assert result == {"command": "connection established", "endpoint": "opc.tcp://localhost:4840"}


# ---------------------------------------------------------------------------
# connect — set_security_string returns awaitable that raises UaError (lines 142-148)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_security_string_awaitable_raises_ua_error_is_caught(monkeypatch):
    """When set_security_string returns a coroutine that raises UaError, the
    except block is hit and connect() continues (single-session fallback test)."""
    from asyncua import ua

    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")
    monkeypatch.setenv("OPCUA_CONNECT_DELAY_SEC", "0.01")
    monkeypatch.setenv("OPCUA_CONNECT_MAX_DELAY_SEC", "0.01")

    async def _raise_ua_error():
        raise ua.UaError("security policy not supported")

    mock_client = MagicMock()
    mock_client.set_security_string = MagicMock(return_value=_raise_ua_error())
    mock_client.connect = AsyncMock(side_effect=ConnectionRefusedError("refused"))

    with patch("python.connection.Client", return_value=mock_client):
        conn = _make_connection()
        result = await conn.connect()

    assert "exception" in result


# ---------------------------------------------------------------------------
# connect — subscription_client.connect() fails → single-session fallback (lines 199-206)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_subscription_client_fails_falls_back_to_single_session(monkeypatch):
    """When subscription_client.connect() raises, connect() still returns success
    and sets self.subscription_client = None (single-session fallback)."""
    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")

    main_mock = MagicMock()
    main_mock.connect = AsyncMock(return_value=None)
    main_mock.load_type_definitions = AsyncMock(return_value=None)
    main_mock.get_root_node = MagicMock(return_value=MagicMock())
    main_mock.set_security_string = MagicMock(return_value=None)

    sub_mock = MagicMock()
    sub_mock.connect = AsyncMock(side_effect=RuntimeError("sub connection refused"))
    sub_mock.set_security_string = MagicMock(return_value=None)
    sub_mock.load_type_definitions = AsyncMock(side_effect=RuntimeError("not reached"))

    ws = AsyncMock()
    with patch("python.connection.Client", side_effect=[main_mock, sub_mock]):
        conn = _make_connection(server_url="opc.tcp://localhost:4840", websocket=ws)
        result = await conn.connect()

    assert result.get("command") == "connection established"
    assert conn.subscription_client is None


# ---------------------------------------------------------------------------
# connect — asyncio.sleep between retries (line 222)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_sleeps_between_retries(monkeypatch):
    """With 2 retries, asyncio.sleep is awaited between attempt 0 and attempt 1."""
    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "2")
    monkeypatch.setenv("OPCUA_CONNECT_DELAY_SEC", "0.01")
    monkeypatch.setenv("OPCUA_CONNECT_MAX_DELAY_SEC", "0.01")

    mock_client = MagicMock()
    mock_client.connect = AsyncMock(side_effect=ConnectionRefusedError("refused"))
    mock_client.set_security_string = MagicMock(return_value=None)

    sleep_calls: list = []

    async def _fake_sleep(delay):
        sleep_calls.append(delay)

    with patch("python.connection.Client", return_value=mock_client):
        with patch("asyncio.sleep", side_effect=_fake_sleep):
            conn = _make_connection()
            result = await conn.connect()

    assert "exception" in result
    assert len(sleep_calls) >= 1


# ---------------------------------------------------------------------------
# terminate — client.disconnect() raises asyncio.TimeoutError (lines 256-257)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_terminate_client_disconnect_timeout(monkeypatch):
    """asyncio.TimeoutError from client.disconnect() is caught and logged."""
    import asyncio as _asyncio

    conn = _make_connection()
    conn.client = MagicMock()
    conn.client.disconnect = AsyncMock(side_effect=_asyncio.TimeoutError())
    conn.subscription_client = None

    with patch.object(conn, "_unsubscribe_and_cleanup", new=AsyncMock(return_value=None)):
        with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
            await conn.terminate()

    assert conn.terminated is True


# ---------------------------------------------------------------------------
# terminate — client.disconnect() raises generic Exception (lines 258-259)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_terminate_client_disconnect_generic_exception(monkeypatch):
    """Generic Exception from client.disconnect() is caught and logged."""
    conn = _make_connection()
    conn.client = MagicMock()
    conn.client.disconnect = AsyncMock(side_effect=RuntimeError("connection reset"))
    conn.subscription_client = None

    with patch.object(conn, "_unsubscribe_and_cleanup", new=AsyncMock(return_value=None)):
        with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
            await conn.terminate()

    assert conn.terminated is True


# ---------------------------------------------------------------------------
# terminate — subscription_client.disconnect() raises asyncio.TimeoutError (lines 266-267)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_terminate_subscription_client_disconnect_timeout():
    """asyncio.TimeoutError from subscription_client.disconnect() is caught and logged."""
    import asyncio as _asyncio

    conn = _make_connection()
    conn.client = MagicMock()
    conn.client.disconnect = AsyncMock(return_value=None)

    sub_client = MagicMock()
    sub_client.disconnect = AsyncMock(side_effect=_asyncio.TimeoutError())
    conn.subscription_client = sub_client

    with patch.object(conn, "_unsubscribe_and_cleanup", new=AsyncMock(return_value=None)):
        with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
            await conn.terminate()

    assert conn.subscription_client is None
    assert conn.terminated is True


# ---------------------------------------------------------------------------
# terminate — subscription_client.disconnect() raises generic Exception (lines 268-269)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_terminate_subscription_client_disconnect_generic_exception():
    """Generic Exception from subscription_client.disconnect() is caught and logged."""
    conn = _make_connection()
    conn.client = MagicMock()
    conn.client.disconnect = AsyncMock(return_value=None)

    sub_client = MagicMock()
    sub_client.disconnect = AsyncMock(side_effect=OSError("broken pipe"))
    conn.subscription_client = sub_client

    with patch.object(conn, "_unsubscribe_and_cleanup", new=AsyncMock(return_value=None)):
        with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
            await conn.terminate()

    assert conn.subscription_client is None
    assert conn.terminated is True


# ---------------------------------------------------------------------------
# terminate — _unsubscribe_and_cleanup raises → outer except (lines 280-281)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_terminate_outer_except_when_unsubscribe_raises():
    """If _unsubscribe_and_cleanup raises, the outer except in terminate() catches it."""
    conn = _make_connection()
    conn.client = MagicMock()
    conn.client.disconnect = AsyncMock(return_value=None)
    conn.subscription_client = None

    with patch.object(
        conn,
        "_unsubscribe_and_cleanup",
        new=AsyncMock(side_effect=RuntimeError("unexpected failure")),
    ):
        with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
            await conn.terminate()

    assert conn.terminated is True


# ---------------------------------------------------------------------------
# _unsubscribe_and_cleanup — result subscription delete raises (lines 313-314)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsubscribe_result_subscription_delete_raises():
    """delete_subscriptions raising for result event is caught, sub reset to 'sub'."""
    conn = _make_connection()

    mock_sub = MagicMock()
    mock_sub.subscription_id = 42
    conn.sub_result_event = mock_sub

    mock_client = MagicMock()
    mock_client.delete_subscriptions = AsyncMock(side_effect=RuntimeError("server rejected delete"))
    conn.client = mock_client

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        await conn._unsubscribe_and_cleanup()

    assert conn.sub_result_event == "sub"


# ---------------------------------------------------------------------------
# _unsubscribe_and_cleanup — joining event subscription delete succeeds (lines 319-325, 328)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsubscribe_deletes_joining_subscription():
    """Joining event subscription with subscription_id is deleted via delete_subscriptions."""
    conn = _make_connection()

    mock_sub = MagicMock()
    mock_sub.subscription_id = 99
    conn.sub_joining_event = mock_sub

    mock_client = MagicMock()
    mock_client.delete_subscriptions = AsyncMock(return_value=None)
    conn.client = mock_client

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        await conn._unsubscribe_and_cleanup()

    mock_client.delete_subscriptions.assert_awaited_once_with([99])
    assert conn.sub_joining_event == "sub"


# ---------------------------------------------------------------------------
# _unsubscribe_and_cleanup — joining event subscription delete raises (lines 326-328)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsubscribe_joining_subscription_delete_raises():
    """delete_subscriptions raising for joining event is caught, sub reset to 'sub'."""
    conn = _make_connection()

    mock_sub = MagicMock()
    mock_sub.subscription_id = 77
    conn.sub_joining_event = mock_sub

    mock_client = MagicMock()
    mock_client.delete_subscriptions = AsyncMock(side_effect=RuntimeError("join delete failed"))
    conn.client = mock_client

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        await conn._unsubscribe_and_cleanup()

    assert conn.sub_joining_event == "sub"


# ---------------------------------------------------------------------------
# namespaces — success and exception paths (lines 537-543)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_namespaces_returns_namespace_list_when_connected():
    """namespaces() returns {'namespaces': [...]} on successful call."""
    conn = _make_connection()
    conn.client = MagicMock()
    conn.client.get_namespace_array = AsyncMock(return_value=["urn:ns0", "urn:ns1"])

    result = await conn.namespaces({})

    assert result == {"namespaces": ["urn:ns0", "urn:ns1"]}


@pytest.mark.asyncio
async def test_namespaces_returns_exception_on_error():
    """namespaces() returns exception dict when get_namespace_array raises."""
    conn = _make_connection()
    conn.client = MagicMock()
    conn.client.get_namespace_array = AsyncMock(side_effect=RuntimeError("server unavailable"))

    result = await conn.namespaces({})

    assert "exception" in result
    assert "server unavailable" in result["exception"]


# ---------------------------------------------------------------------------
# subscribe — exception path (lines 346-413)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscribe_returns_exception_when_namespace_lookup_fails():
    """subscribe() catches and returns exception dict when namespace index lookup raises."""
    conn = _make_connection()

    conn.handler_joining_event = MagicMock()
    conn.handler_result_event = MagicMock()
    conn.subscription_client = None

    conn.client = AsyncMock()
    conn.client.get_namespace_index = AsyncMock(side_effect=RuntimeError("namespace not found"))

    result = await conn.subscribe({})

    assert "exception" in result
    assert "Subscribe exception" in result["exception"]


# ---------------------------------------------------------------------------
# read_product_instance_uri — paths not accessible (lines 620-653)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_product_instance_uri_returns_empty_when_paths_not_accessible():
    """read_product_instance_uri returns {'tools': []} when all tool paths raise."""
    conn = _make_connection()
    conn.client = MagicMock()
    conn.client.get_node = MagicMock(side_effect=RuntimeError("node not found"))

    result = await conn.read_product_instance_uri({})

    assert result == {"tools": []}
