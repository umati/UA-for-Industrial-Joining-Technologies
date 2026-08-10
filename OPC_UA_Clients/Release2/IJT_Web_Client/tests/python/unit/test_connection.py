"""
Unit tests for IJT_Web_Client/Python/connection.py

Covers:
- is_connection_open: no client, None client, open state, non-open state
- connect: all retries fail, explicit Docker-host URL rewrite, connection established event
- terminate: already terminated, no client
- _unsubscribe_and_cleanup: connection not open, deletes result subscription
- methodcall: not connected returns exception
"""

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("asyncua", reason="asyncua not installed")

_REPO_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "scripts" / "opcua_session_policy_loader.py").is_file()
)
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from asyncua import ua  # noqa: E402
from asyncua.client.ua_client import UaClientState, UASocketState  # noqa: E402
from opcua_session_policy_loader import locate_repo_scripts_dir  # noqa: E402

from python.connection import Connection  # noqa: E402, I001


def test_session_policy_loader_requires_full_repo_checkout():
    with patch("opcua_session_policy_loader.Path.is_file", return_value=False):
        with pytest.raises(ModuleNotFoundError, match="shared IJT OPC UA session policy module was not found"):
            locate_repo_scripts_dir(__file__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_connection(server_url="opc.tcp://localhost:40451", websocket=None):
    ws = websocket if websocket is not None else AsyncMock()
    return Connection(server_url, ws)


def test_connection_logger_uses_endpoint_identity():
    connection = _make_connection("opc.tcp://controller-b:4840")

    message, _ = connection.log.process("Connected", {})

    assert message == "[opc.tcp://controller-b:4840] Connected"


def _call_method_result(
    output_values=(),
    *,
    status_code=0,
    input_argument_results=(),
    diagnostic_infos=(),
):
    return ua.CallMethodResult(
        StatusCode=ua.StatusCode(status_code),
        InputArgumentResults=[ua.StatusCode(value) for value in input_argument_results],
        InputArgumentDiagnosticInfos=list(diagnostic_infos),
        OutputArguments=[value if isinstance(value, ua.Variant) else ua.Variant(value) for value in output_values],
    )


def _configure_raw_method_call(
    object_node,
    method_node,
    *,
    output_values=(),
    status_code=0,
    input_argument_results=(),
    diagnostic_infos=(),
    captured=None,
    exception=None,
):
    object_node.nodeid = ua.NodeId("Object", 1)
    method_node.nodeid = ua.NodeId("Method", 1)

    async def _call(requests):
        if captured is not None:
            captured.extend(requests[0].InputArguments)
        if exception is not None:
            raise exception
        return [
            _call_method_result(
                output_values,
                status_code=status_code,
                input_argument_results=input_argument_results,
                diagnostic_infos=diagnostic_infos,
            )
        ]

    object_node.session.call = AsyncMock(side_effect=_call)


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
async def test_is_connection_open_returns_true_for_asyncua_2_connected_session():
    conn = _make_connection()
    conn.client = SimpleNamespace(
        uaclient=SimpleNamespace(
            has_session=True,
            state=UaClientState.CONNECTED,
        )
    )
    assert await conn.is_connection_open() is True


@pytest.mark.asyncio
async def test_is_connection_open_returns_false_without_active_session():
    conn = _make_connection()
    conn.client = SimpleNamespace(
        uaclient=SimpleNamespace(
            has_session=False,
            state=UaClientState.SOCKET_OPEN,
            protocol=SimpleNamespace(state=UASocketState.OPEN),
        )
    )
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


@pytest.mark.asyncio
async def test_connect_uses_explicit_single_probe_attempt(monkeypatch):
    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "8")

    mock_client = MagicMock()
    mock_client.connect = AsyncMock(side_effect=ConnectionRefusedError("refused"))
    mock_client.set_security_string = MagicMock(return_value=None)

    with patch("python.connection.Client", return_value=mock_client):
        conn = _make_connection()
        result = await conn.connect(max_retries=1)

    assert "after 1 attempts" in result["exception"]
    assert mock_client.connect.await_count == 1
    assert mock_client.session_timeout == 600_000


# ---------------------------------------------------------------------------
# connect — explicit Docker-host URL rewrite
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_docker_url_rewrite(monkeypatch):
    monkeypatch.setenv("IS_DOCKER", "true")
    monkeypatch.setenv("IJT_OPCUA_HOST_REWRITE", "true")
    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")
    monkeypatch.setenv("OPCUA_CONNECT_DELAY_SEC", "0.01")
    monkeypatch.setenv("OPCUA_CONNECT_MAX_DELAY_SEC", "0.01")

    created_urls = []

    def _fake_client(url, timeout=60, **_kwargs):
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


@pytest.mark.asyncio
async def test_connect_docker_mode_does_not_rewrite_without_host_bridge_opt_in(monkeypatch):
    monkeypatch.setenv("IS_DOCKER", "true")
    monkeypatch.delenv("IJT_OPCUA_HOST_REWRITE", raising=False)
    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")
    monkeypatch.setenv("OPCUA_CONNECT_DELAY_SEC", "0.01")
    monkeypatch.setenv("OPCUA_CONNECT_MAX_DELAY_SEC", "0.01")

    created_urls = []

    def _fake_client(url, timeout=60, **_kwargs):
        created_urls.append(url)
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(side_effect=ConnectionRefusedError("refused"))
        mock_client.set_security_string = MagicMock(return_value=None)
        return mock_client

    with patch("python.connection.Client", side_effect=_fake_client):
        conn = _make_connection(server_url="opc.tcp://localhost:40451")
        await conn.connect()

    assert created_urls == ["opc.tcp://localhost:40451"]


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
    mock_client.load_data_type_definitions = AsyncMock(return_value=None)
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


@pytest.mark.asyncio
async def test_connect_loads_ijt_type_definitions_on_both_clients(monkeypatch):
    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")

    calls: list[str] = []

    main_mock = MagicMock()
    main_mock.connect = AsyncMock(return_value=None)
    main_mock.load_type_definitions = AsyncMock(side_effect=lambda: calls.append("main_legacy"))
    main_mock.load_data_type_definitions = AsyncMock(side_effect=lambda: calls.append("main_modern"))
    main_mock.get_root_node = MagicMock(return_value=MagicMock())
    main_mock.set_security_string = MagicMock(return_value=None)

    sub_mock = MagicMock()
    sub_mock.connect = AsyncMock(return_value=None)
    sub_mock.load_type_definitions = AsyncMock(side_effect=lambda: calls.append("sub_legacy"))
    sub_mock.load_data_type_definitions = AsyncMock(side_effect=lambda: calls.append("sub_modern"))
    sub_mock.set_security_string = MagicMock(return_value=None)

    with patch("python.connection.Client", side_effect=[main_mock, sub_mock]):
        conn = _make_connection(server_url="opc.tcp://localhost:40451")
        result = await conn.connect()

    assert result.get("command") == "connection established"
    assert calls == ["main_modern", "sub_modern"]
    main_mock.load_type_definitions.assert_not_awaited()
    sub_mock.load_type_definitions.assert_not_awaited()


@pytest.mark.asyncio
async def test_connect_configures_long_watchdog_interval(monkeypatch):
    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")
    monkeypatch.setenv("OPCUA_WATCHDOG_INTERVAL_SEC", "120")

    main_mock = MagicMock()
    main_mock.connect = AsyncMock(return_value=None)
    main_mock.load_type_definitions = AsyncMock(return_value=None)
    main_mock.load_data_type_definitions = AsyncMock(return_value=None)
    main_mock.get_root_node = MagicMock(return_value=MagicMock())

    sub_mock = MagicMock()
    sub_mock.connect = AsyncMock(return_value=None)
    sub_mock.load_type_definitions = AsyncMock(return_value=None)
    sub_mock.load_data_type_definitions = AsyncMock(return_value=None)

    with patch("python.connection.Client", side_effect=[main_mock, sub_mock]) as client_factory:
        conn = _make_connection(server_url="opc.tcp://localhost:40451")
        result = await conn.connect()

    assert result.get("command") == "connection established"
    assert client_factory.call_args_list[0].kwargs["watchdog_intervall"] == 120.0
    assert client_factory.call_args_list[1].kwargs["watchdog_intervall"] == 120.0
    assert main_mock.session_timeout == 600_000
    assert sub_mock.session_timeout == 600_000


@pytest.mark.asyncio
async def test_connect_uses_default_watchdog_interval_for_invalid_env(monkeypatch):
    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")
    monkeypatch.setenv("OPCUA_WATCHDOG_INTERVAL_SEC", "not-a-number")

    main_mock = MagicMock()
    main_mock.connect = AsyncMock(return_value=None)
    main_mock.load_type_definitions = AsyncMock(return_value=None)
    main_mock.load_data_type_definitions = AsyncMock(return_value=None)
    main_mock.get_root_node = MagicMock(return_value=MagicMock())

    sub_mock = MagicMock()
    sub_mock.connect = AsyncMock(return_value=None)
    sub_mock.load_type_definitions = AsyncMock(return_value=None)
    sub_mock.load_data_type_definitions = AsyncMock(return_value=None)

    with patch("python.connection.Client", side_effect=[main_mock, sub_mock]) as client_factory:
        conn = _make_connection(server_url="opc.tcp://localhost:40451")
        result = await conn.connect()

    assert result.get("command") == "connection established"
    assert client_factory.call_args_list[0].kwargs["watchdog_intervall"] == 3600.0
    assert client_factory.call_args_list[1].kwargs["watchdog_intervall"] == 3600.0


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


@pytest.mark.asyncio
async def test_methodcall_returns_normalized_result_contract():
    conn = _make_connection()

    mock_method_node = MagicMock()
    mock_method_node.get_child = AsyncMock()
    mock_input_args_node = MagicMock()
    mock_input_args_node.get_value = AsyncMock(return_value=[])
    mock_method_node.get_child.return_value = mock_input_args_node

    mock_object_node = MagicMock()
    _configure_raw_method_call(mock_object_node, mock_method_node, output_values=["A", "B"])

    mock_client = MagicMock()
    mock_client.get_node = MagicMock(side_effect=[mock_object_node, mock_method_node])
    conn.client = mock_client

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        result = await conn.methodcall(
            {
                "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                "methodnode": {"NamespaceIndex": 1, "Identifier": "GetIdentifiers"},
                "arguments": [],
            }
        )

    assert result["callStatus"] == "Succeeded"
    assert result["statusCode"]["name"] == "Good"
    assert result["returnValue"] is None
    assert result["outputArguments"] == ["A", "B"]
    assert result["rawOutput"]["pythonclass"] == "CallMethodResult"
    assert result["rawOutput"]["StatusCode"]["value"] == 0


@pytest.mark.asyncio
async def test_methodcall_void_method_has_no_output_arguments():
    conn = _make_connection()

    mock_method_node = MagicMock()
    mock_method_node.get_child = AsyncMock()
    mock_input_args_node = MagicMock()
    mock_input_args_node.get_value = AsyncMock(return_value=[])
    mock_method_node.get_child.return_value = mock_input_args_node

    mock_object_node = MagicMock()
    _configure_raw_method_call(mock_object_node, mock_method_node)

    mock_client = MagicMock()
    mock_client.get_node = MagicMock(side_effect=[mock_object_node, mock_method_node])
    conn.client = mock_client

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        result = await conn.methodcall(
            {
                "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                "methodnode": {"NamespaceIndex": 1, "Identifier": "EnableAsset"},
                "arguments": [],
            }
        )

    assert result["callStatus"] == "Succeeded"
    assert result["statusCode"]["name"] == "Good"
    assert result["returnValue"] is None
    assert result["outputArguments"] == []
    assert result["inputArgumentResults"] == []
    assert result["inputArgumentDiagnosticInfos"] == []
    assert result["rawOutput"]["OutputArguments"] == []


@pytest.mark.asyncio
async def test_methodcall_uaerror_keeps_normalized_failure_contract():
    from asyncua import ua

    conn, _ = _make_methodcall_conn(expected_args=[], call_method_exc=ua.UaError("Uncertain"))

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        result = await conn.methodcall({**_MC_PAYLOAD, "arguments": []})

    assert result["callStatus"] == "Failed"
    assert result["outputArguments"] == []
    assert "OPC UA error:" in result["exception"]


def test_serialize_argument_definition_keeps_schema_shape():
    from python.connection import _serialize_argument_definition

    argument = MagicMock()
    argument.Name = "GenericInput"
    argument.DataType = MagicMock()
    argument.DataType.NamespaceIndex = 3
    argument.DataType.Identifier = 3029
    argument.ValueRank = -1
    argument.ArrayDimensions = None
    argument.Description = None

    result = _serialize_argument_definition(argument)

    assert result["Name"] == "GenericInput"
    assert result["DataType"] == {"NamespaceIndex": 3, "Identifier": 3029}
    assert result["FieldDefinitions"] == []


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
    _configure_raw_method_call(mock_obj, mock_method, captured=captured_call_args)

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
    assert result["callStatus"] == "Succeeded"
    assert result["outputArguments"] == []
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
    _configure_raw_method_call(mock_obj, mock_method, captured=captured)

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

    assert result["callStatus"] == "Succeeded"
    assert result["outputArguments"] == []
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
    _configure_raw_method_call(mock_obj, mock_method, captured=captured)

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

    assert result["callStatus"] == "Succeeded"
    assert result["outputArguments"] == []
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
    _configure_raw_method_call(mock_obj, mock_method, captured=captured)

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

    assert result["callStatus"] == "Succeeded"
    assert result["outputArguments"] == []
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
    _configure_raw_method_call(mock_obj, mock_method)

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

    assert result.get("callStatus") == "Succeeded" or "exception" in result
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
    _configure_raw_method_call(mock_obj, mock_method, captured=captured)

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

    assert result["callStatus"] == "Succeeded"
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
    main_mock.load_data_type_definitions = AsyncMock(return_value=None)
    main_mock.get_root_node = MagicMock(return_value=MagicMock())
    main_mock.set_security_string = MagicMock(return_value=None)

    sub_mock = MagicMock()
    sub_mock.connect = AsyncMock(side_effect=RuntimeError("sub connection refused"))
    sub_mock.disconnect = AsyncMock(return_value=None)
    sub_mock.set_security_string = MagicMock(return_value=None)
    sub_mock.load_type_definitions = AsyncMock(side_effect=RuntimeError("not reached"))
    sub_mock.load_data_type_definitions = AsyncMock(side_effect=RuntimeError("not reached"))

    ws = AsyncMock()
    with patch("python.connection.Client", side_effect=[main_mock, sub_mock]):
        conn = _make_connection(server_url="opc.tcp://localhost:4840", websocket=ws)
        result = await conn.connect()

    assert result.get("command") == "connection established"
    assert conn.subscription_client is None
    sub_mock.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_connect_failure_after_subscription_open_closes_both_sessions(monkeypatch):
    """A failed browser notification must not leak the subscription session."""
    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "1")

    main_mock = MagicMock()
    main_mock.connect = AsyncMock()
    main_mock.disconnect = AsyncMock()
    main_mock.load_type_definitions = AsyncMock()
    main_mock.load_data_type_definitions = AsyncMock()
    main_mock.get_root_node.return_value = MagicMock()

    sub_mock = MagicMock()
    sub_mock.connect = AsyncMock()
    sub_mock.disconnect = AsyncMock()
    sub_mock.load_type_definitions = AsyncMock()
    sub_mock.load_data_type_definitions = AsyncMock()

    websocket = AsyncMock()
    websocket.send.side_effect = RuntimeError("browser socket closed")

    with patch("python.connection.Client", side_effect=[main_mock, sub_mock]):
        conn = _make_connection(websocket=websocket)
        result = await conn.connect()

    assert "exception" in result
    main_mock.disconnect.assert_awaited_once()
    sub_mock.disconnect.assert_awaited_once()
    assert conn.client is None
    assert conn.subscription_client is None


@pytest.mark.asyncio
async def test_connect_cancellation_closes_partially_open_session(monkeypatch):
    """Cancelling refresh-era connect work must release its server session."""
    monkeypatch.setenv("OPCUA_CONNECT_RETRIES", "8")
    connect_started = asyncio.Event()

    async def _blocking_connect():
        connect_started.set()
        await asyncio.Event().wait()

    main_mock = MagicMock()
    main_mock.connect = AsyncMock(side_effect=_blocking_connect)
    main_mock.disconnect = AsyncMock()

    with patch("python.connection.Client", return_value=main_mock):
        conn = _make_connection()
        connect_task = asyncio.create_task(conn.connect())
        await connect_started.wait()
        connect_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await connect_task

    main_mock.disconnect.assert_awaited_once()
    assert conn.client is None
    assert conn.subscription_client is None


@pytest.mark.asyncio
async def test_terminate_cancellation_finishes_both_session_disconnects():
    """Browser-close cancellation must not interrupt an explicit endpoint terminate."""
    conn = _make_connection()
    main_client = MagicMock()
    main_client.disconnect = AsyncMock()
    subscription_client = MagicMock()
    subscription_client.disconnect = AsyncMock()
    conn.client = main_client
    conn.subscription_client = subscription_client
    cleanup_delay_started = asyncio.Event()
    release_cleanup_delay = asyncio.Event()

    async def _controlled_cleanup_delay(_delay):
        cleanup_delay_started.set()
        await release_cleanup_delay.wait()

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        with patch("python.connection.asyncio.sleep", side_effect=_controlled_cleanup_delay):
            terminate_task = asyncio.create_task(conn.terminate())
            await cleanup_delay_started.wait()
            terminate_task.cancel()
            release_cleanup_delay.set()
            with pytest.raises(asyncio.CancelledError):
                await terminate_task

    main_client.disconnect.assert_awaited_once()
    subscription_client.disconnect.assert_awaited_once()
    assert conn.client is None
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


# ===========================================================================
# NEW TESTS — covering missed lines:
#   355-409  subscribe success paths
#   438-471  read success paths
#   508-521  pathtoid success path
#   566-576  browse details=True
#   628-649  read_product_instance_uri success paths
#   749-754  methodcall array else-branch
#   758      methodcall digit-string → int conversion
#   768      methodcall float with int-type → VariantType.Double
#   770      methodcall bool value (pass branch)
#   774-778  methodcall inner arg-mapping exception fallback
#   787-796  methodcall except ua.UaError handling
#   801-804  methodcall except Exception "Unhandled exception" handling
# ===========================================================================


# ---------------------------------------------------------------------------
# subscribe — success paths (lines 355-409)
# ---------------------------------------------------------------------------


def _make_sub_client():
    """Return a MagicMock wired as a subscription client for subscribe() tests."""
    mock_sub = MagicMock()
    mock_sub.subscribe_events = AsyncMock(return_value=MagicMock())
    sub_client = MagicMock()
    sub_client.get_namespace_index = AsyncMock(return_value=2)
    sub_client.nodes.root.get_child = AsyncMock(return_value=MagicMock())
    sub_client.get_node.return_value = MagicMock()
    sub_client.create_subscription = AsyncMock(return_value=mock_sub)
    return sub_client, mock_sub


@pytest.mark.asyncio
async def test_subscribe_creates_both_subscriptions_when_no_eventtype():
    """subscribe() with no eventtype creates both result and joining subscriptions."""
    conn = _make_connection()
    conn.handler_joining_event = MagicMock()
    conn.handler_result_event = MagicMock()
    sub_client, mock_sub = _make_sub_client()
    conn.subscription_client = None
    conn.client = sub_client

    result = await conn.subscribe({})

    assert result == {}
    assert sub_client.create_subscription.await_count == 2
    assert conn.sub_result_event is mock_sub
    assert conn.sub_joining_event is mock_sub
    requested_event_type = sub_client.get_node.call_args.args[0]
    assert requested_event_type.Identifier == 1035
    assert requested_event_type.NamespaceIndex == 2


@pytest.mark.asyncio
async def test_subscribe_creates_only_result_subscription_for_resultevent():
    """subscribe() with eventtype='resultevent' creates only the result subscription."""
    conn = _make_connection()
    conn.handler_joining_event = MagicMock()
    conn.handler_result_event = MagicMock()
    sub_client, mock_sub = _make_sub_client()
    conn.subscription_client = None
    conn.client = sub_client

    result = await conn.subscribe({"eventtype": "resultevent"})

    assert result == {}
    assert sub_client.create_subscription.await_count == 1
    assert conn.sub_result_event is mock_sub
    assert conn.sub_joining_event == "sub"


@pytest.mark.asyncio
async def test_subscribe_creates_only_joining_subscription_for_joiningsystemevent():
    """subscribe() with eventtype='joiningsystemevent' creates only the joining subscription."""
    conn = _make_connection()
    conn.handler_joining_event = MagicMock()
    conn.handler_result_event = MagicMock()
    sub_client, mock_sub = _make_sub_client()
    conn.subscription_client = None
    conn.client = sub_client

    result = await conn.subscribe({"eventtype": "joiningsystemevent"})

    assert result == {}
    assert sub_client.create_subscription.await_count == 1
    assert conn.sub_joining_event is mock_sub
    assert conn.sub_result_event == "sub"


@pytest.mark.asyncio
async def test_subscribe_skips_already_active_subscriptions():
    """subscribe() does not recreate subscriptions already set to a non-'sub' value."""
    conn = _make_connection()
    conn.handler_joining_event = MagicMock()
    conn.handler_result_event = MagicMock()
    sub_client, _ = _make_sub_client()
    conn.subscription_client = None
    conn.client = sub_client
    # Pre-set both — subscribe() must not call create_subscription again
    conn.sub_result_event = MagicMock()
    conn.sub_joining_event = MagicMock()

    result = await conn.subscribe({})

    assert result == {}
    sub_client.create_subscription.assert_not_awaited()


# ---------------------------------------------------------------------------
# read — success paths (lines 438-471) and exception path (lines 479-482)
# ---------------------------------------------------------------------------


def _make_read_node(node_class_value):
    """Return a MagicMock node ready for read() with the given NodeClass."""
    mock_reply = MagicMock()
    mock_reply.Value.Value = "v"
    mock_node = MagicMock()
    mock_node.read_attributes = AsyncMock(return_value=[mock_reply] * 12)
    mock_node.get_references = AsyncMock(return_value=[])
    mock_node.read_node_class = AsyncMock(return_value=node_class_value)
    mock_node.get_value = AsyncMock(return_value=99)
    return mock_node


@pytest.mark.asyncio
async def test_read_variable_node_fetches_value():
    """read() on a Variable node calls get_value() and returns a readresult dict."""
    from asyncua import ua

    conn = _make_connection()
    mock_node = _make_read_node(ua.NodeClass.Variable)
    conn.client = MagicMock()
    conn.client.get_node = MagicMock(return_value=mock_node)

    with patch("python.connection.serialize_tuple", return_value="{}"):
        with patch("python.connection.serialize_value", return_value="{}"):
            result = await conn.read({"nodeid": "ns=1;s=Var1"})

    assert result.get("command") == "readresult"
    assert result.get("nodeid") == "ns=1;s=Var1"
    mock_node.get_value.assert_awaited_once()


@pytest.mark.asyncio
async def test_read_non_variable_node_does_not_fetch_value():
    """read() on a non-Variable (Object) node skips the get_value() call."""
    from asyncua import ua

    conn = _make_connection()
    mock_node = _make_read_node(ua.NodeClass.Object)
    conn.client = MagicMock()
    conn.client.get_node = MagicMock(return_value=mock_node)

    with patch("python.connection.serialize_tuple", return_value="{}"):
        with patch("python.connection.serialize_value", return_value="{}"):
            result = await conn.read({"nodeid": "ns=1;s=Obj1"})

    assert result.get("command") == "readresult"
    mock_node.get_value.assert_not_awaited()


@pytest.mark.asyncio
async def test_read_exception_returns_exception_dict():
    """read() returns an exception dict when an OPC UA call raises."""
    conn = _make_connection()
    conn.client = MagicMock()
    conn.client.get_node = MagicMock(side_effect=RuntimeError("node not found"))

    result = await conn.read({"nodeid": "ns=1;s=Missing"})

    assert "exception" in result
    assert "Read Exception" in result["exception"]


# ---------------------------------------------------------------------------
# pathtoid — success and exception paths (lines 508-525)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pathtoid_success_returns_serialized_nodeid():
    """pathtoid() translates a browse path and returns the serialized target node-id."""
    conn = _make_connection()

    mock_node = MagicMock()
    mock_node.nodeid = MagicMock()
    mock_target = MagicMock()
    mock_result_item = MagicMock()
    mock_result_item.Targets = [mock_target]

    conn.client = MagicMock()
    conn.client.get_node = MagicMock(return_value=mock_node)
    conn.client.translate_browsepaths = AsyncMock(return_value=[mock_result_item])

    path_json = json.dumps([{"identifier": "Child", "namespaceindex": 1}])
    with patch("python.connection.serialize_full_event", return_value="ns=1;s=Child"):
        result = await conn.pathtoid(
            {
                "nodeid": {"NamespaceIndex": 1, "Identifier": "Parent"},
                "path": path_json,
            }
        )

    assert result == {"nodeid": "ns=1;s=Child"}


@pytest.mark.asyncio
async def test_pathtoid_exception_returns_exception_dict():
    """pathtoid() returns an exception dict when translate_browsepaths raises."""
    conn = _make_connection()

    mock_node = MagicMock()
    mock_node.nodeid = MagicMock()
    conn.client = MagicMock()
    conn.client.get_node = MagicMock(return_value=mock_node)
    conn.client.translate_browsepaths = AsyncMock(side_effect=RuntimeError("translate failed"))

    path_json = json.dumps([{"identifier": "Child", "namespaceindex": 1}])
    result = await conn.pathtoid(
        {
            "nodeid": {"NamespaceIndex": 1, "Identifier": "Parent"},
            "path": path_json,
        }
    )

    assert "exception" in result
    assert "PathToId Exception" in result["exception"]


# ---------------------------------------------------------------------------
# browse — details=True adds TypeDefinition to each entry (lines 574-575)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_browse_with_details_true_includes_type_definition_field():
    """browse() with details=True adds a TypeDefinition key to each result entry."""
    conn = _make_connection()

    mock_ref = MagicMock()
    mock_ref.TypeDefinition = "ns=0;i=58"
    mock_ref.IsForward = True
    mock_node = MagicMock()
    mock_node.get_references = AsyncMock(return_value=[mock_ref])

    conn.client = MagicMock()
    conn.client.get_node = MagicMock(return_value=mock_node)

    result = await conn.browse({"nodeid": "ns=1;i=1", "details": True})

    assert "nodes" in result
    assert len(result["nodes"]) == 1
    assert "TypeDefinition" in result["nodes"][0]


# ---------------------------------------------------------------------------
# read_product_instance_uri — tools found on first path (lines 628-649)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_product_instance_uri_returns_tools_found_on_first_path():
    """read_product_instance_uri returns tool list when first path has accessible tools."""
    conn = _make_connection()

    mock_pi_node = MagicMock()
    mock_pi_node.read_value = AsyncMock(return_value="urn:tool:SN001")
    mock_browse_name = MagicMock()
    mock_browse_name.Name = "Wrench1"
    mock_child = MagicMock()
    mock_child.read_browse_name = AsyncMock(return_value=mock_browse_name)
    mock_tools_node = MagicMock()
    mock_tools_node.get_children = AsyncMock(return_value=[mock_child])

    def _get_node(path):
        if "ProductInstanceUri" in path:
            return mock_pi_node
        return mock_tools_node

    conn.client = MagicMock()
    conn.client.get_node = MagicMock(side_effect=_get_node)

    result = await conn.read_product_instance_uri({})

    assert len(result["tools"]) == 1
    assert result["tools"][0]["toolName"] == "Wrench1"
    assert result["tools"][0]["productInstanceUri"] == "urn:tool:SN001"


@pytest.mark.asyncio
async def test_read_product_instance_uri_child_pi_read_raises_skips_child():
    """read_product_instance_uri skips a child when pi_node.read_value raises."""
    conn = _make_connection()

    mock_pi_node = MagicMock()
    mock_pi_node.read_value = AsyncMock(side_effect=RuntimeError("node inaccessible"))
    mock_browse_name = MagicMock()
    mock_browse_name.Name = "Wrench2"
    mock_child = MagicMock()
    mock_child.read_browse_name = AsyncMock(return_value=mock_browse_name)
    mock_tools_node = MagicMock()
    mock_tools_node.get_children = AsyncMock(return_value=[mock_child])

    def _get_node(path):
        if "ProductInstanceUri" in path:
            return mock_pi_node
        return mock_tools_node

    conn.client = MagicMock()
    conn.client.get_node = MagicMock(side_effect=_get_node)

    result = await conn.read_product_instance_uri({})

    # Child is silently skipped; both paths try and both fail → empty list
    assert result == {"tools": []}


# ---------------------------------------------------------------------------
# methodcall — shared helper for argument-capture tests
# ---------------------------------------------------------------------------


def _make_methodcall_conn(
    expected_args,
    call_method_func=None,
    call_method_exc=None,
    *,
    output_values=(),
    status_code=0,
    input_argument_results=(),
):
    """Build a Connection whose client is wired for a single methodcall invocation.

    Returns (conn, captured_list).  captured_list is populated with the
    ua.Variant objects passed to call_method when call_method_func is None.
    """
    captured: list = []

    mock_input_args_node = MagicMock()
    mock_input_args_node.get_value = AsyncMock(return_value=expected_args)
    mock_method = MagicMock()
    mock_method.get_child = AsyncMock(return_value=mock_input_args_node)
    mock_obj = MagicMock()
    if call_method_exc is not None:
        _configure_raw_method_call(
            mock_obj,
            mock_method,
            captured=captured,
            exception=call_method_exc,
        )
    elif call_method_func is not None:
        mock_obj.nodeid = ua.NodeId("Object", 1)
        mock_method.nodeid = ua.NodeId("Method", 1)
        mock_obj.session.call = call_method_func
    else:
        _configure_raw_method_call(
            mock_obj,
            mock_method,
            captured=captured,
            output_values=output_values,
            status_code=status_code,
            input_argument_results=input_argument_results,
        )

    mock_client = MagicMock()
    mock_client.get_node = MagicMock(side_effect=[mock_obj, mock_method])

    conn = _make_connection()
    conn.client = mock_client
    return conn, captured


_MC_PAYLOAD = {
    "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
    "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateResult"},
}


@pytest.mark.asyncio
async def test_methodcall_preserves_uncertain_status_and_output_arguments():
    status_message = ua.LocalizedText(Text="Joining process not found.", Locale="en")
    conn, _ = _make_methodcall_conn(
        expected_args=[],
        output_values=[4, status_message],
        status_code=ua.StatusCodes.Uncertain,
        input_argument_results=[ua.StatusCodes.BadInvalidArgument],
    )

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        result = await conn.methodcall({**_MC_PAYLOAD, "arguments": []})

    assert result["callStatus"] == "Uncertain"
    assert result["statusCode"] == {
        "name": "Uncertain",
        "value": ua.StatusCodes.Uncertain,
        "isGood": False,
        "isUncertain": True,
        "isBad": False,
    }
    assert result["outputArguments"] == [
        4,
        {
            "pythonclass": "LocalizedText",
            "Encoding": 0,
            "Locale": "en",
            "Text": "Joining process not found.",
        },
    ]
    assert result["inputArgumentResults"][0]["name"] == "BadInvalidArgument"
    assert "operation was uncertain" in result["statusDescription"].lower()
    assert "exception" not in result
    assert result["rawOutput"]["OutputArguments"][0]["Value"] == 4


@pytest.mark.asyncio
async def test_methodcall_preserves_bad_status_and_output_arguments():
    conn, _ = _make_methodcall_conn(
        expected_args=[],
        output_values=[5, "Invalid selection"],
        status_code=ua.StatusCodes.BadInvalidArgument,
    )

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        result = await conn.methodcall({**_MC_PAYLOAD, "arguments": []})

    assert result["callStatus"] == "Failed"
    assert result["statusCode"]["name"] == "BadInvalidArgument"
    assert result["outputArguments"] == [5, "Invalid selection"]
    assert "arguments are invalid" in result["statusDescription"].lower()
    assert "exception" not in result


# ---------------------------------------------------------------------------
# methodcall — array else-branch: non-String, non-ExtensionObject (lines 752-754)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_methodcall_list_of_ints_hits_array_else_branch():
    """Int32 list value goes through the 'else' array branch (lines 752-754)."""
    from asyncua import ua

    mock_arg_desc = MagicMock()
    mock_arg_desc.DataType.Identifier = 6  # Int32
    conn, captured = _make_methodcall_conn(expected_args=[mock_arg_desc])

    with patch("python.connection.serialize_full_event", return_value=[]):
        with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
            result = await conn.methodcall({**_MC_PAYLOAD, "arguments": [{"dataType": 6, "value": [10, 20, 30]}]})

    assert result["callStatus"] == "Succeeded"
    assert len(captured) == 1
    assert isinstance(captured[0].Value, list)
    assert captured[0].VariantType == ua.VariantType.Int32


@pytest.mark.asyncio
async def test_methodcall_converts_iso_datetime_to_opc_ua_datetime():
    """ISO timestamps from the browser must become DateTime variants."""
    from asyncua import ua

    mock_arg_desc = MagicMock()
    mock_arg_desc.DataType.Identifier = 13
    conn, captured = _make_methodcall_conn(expected_args=[mock_arg_desc])

    with patch("python.connection.serialize_full_event", return_value=[]):
        with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
            result = await conn.methodcall(
                {**_MC_PAYLOAD, "arguments": [{"dataType": 13, "value": "2000-01-01T00:00:00Z"}]}
            )

    assert result["callStatus"] == "Succeeded"
    assert captured[0].VariantType == ua.VariantType.DateTime
    assert captured[0].Value.isoformat() == "2000-01-01T00:00:00"


# ---------------------------------------------------------------------------
# methodcall — string digit → int conversion (line 758)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_methodcall_digit_string_value_is_converted_to_int():
    """Scalar string value '42' is converted to int 42 before Variant creation (line 758)."""
    mock_arg_desc = MagicMock()
    mock_arg_desc.DataType.Identifier = 6  # Int32 — avoids UInt abs() branch
    conn, captured = _make_methodcall_conn(expected_args=[mock_arg_desc])

    with patch("python.connection.serialize_full_event", return_value=[]):
        with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
            result = await conn.methodcall({**_MC_PAYLOAD, "arguments": [{"dataType": 6, "value": "42"}]})

    assert result["callStatus"] == "Succeeded"
    assert len(captured) == 1
    assert captured[0].Value == 42  # was a string; must be converted


# ---------------------------------------------------------------------------
# methodcall — float with integer variant type → VariantType.Double (line 768)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_methodcall_float_with_int_type_promotes_to_double():
    """Float scalar value with an Int32 variant type is promoted to Double (line 768)."""
    from asyncua import ua

    mock_arg_desc = MagicMock()
    mock_arg_desc.DataType.Identifier = 6  # Int32
    conn, captured = _make_methodcall_conn(expected_args=[mock_arg_desc])

    with patch("python.connection.serialize_full_event", return_value=[]):
        with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
            result = await conn.methodcall({**_MC_PAYLOAD, "arguments": [{"dataType": 6, "value": 3.14}]})

    assert result["callStatus"] == "Succeeded"
    assert len(captured) == 1
    assert captured[0].VariantType == ua.VariantType.Double


# ---------------------------------------------------------------------------
# methodcall — bool value passes through the 'elif isinstance(bool)' branch (line 770)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_methodcall_bool_value_reaches_bool_branch():
    """Boolean scalar value hits the 'elif isinstance(value, bool): pass' branch (line 770)."""
    from asyncua import ua

    mock_arg_desc = MagicMock()
    mock_arg_desc.DataType.Identifier = 1  # Boolean
    conn, captured = _make_methodcall_conn(expected_args=[mock_arg_desc])

    with patch("python.connection.serialize_full_event", return_value=[]):
        with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
            result = await conn.methodcall({**_MC_PAYLOAD, "arguments": [{"dataType": 1, "value": True}]})

    assert result["callStatus"] == "Succeeded"
    assert len(captured) == 1
    assert captured[0].Value is True
    assert captured[0].VariantType == ua.VariantType.Boolean


# ---------------------------------------------------------------------------
# methodcall — inner arg-mapping exception → fallback to create_call_structure
#              (lines 774-778)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_methodcall_arg_mapping_exception_falls_back_to_create_call_structure():
    """IndexError on expected_args triggers the fallback to create_call_structure (lines 774-778)."""
    # expected_args=[] but 1 argument supplied → IndexError on expected_args[0]
    conn, captured = _make_methodcall_conn(expected_args=[])

    fallback_variant = MagicMock()
    with patch("python.connection.create_call_structure", return_value=fallback_variant) as mock_ccs:
        with patch("python.connection.serialize_full_event", return_value=[]):
            with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
                result = await conn.methodcall({**_MC_PAYLOAD, "arguments": [{"dataType": 12, "value": "hello"}]})

    assert result["callStatus"] == "Succeeded"
    mock_ccs.assert_called_once()
    assert captured[0].Value is fallback_variant


@pytest.mark.asyncio
async def test_methodcall_uses_server_declared_joining_process_structure_type():
    """Custom IJT structure args must be built from the server-declared type, not downgraded to String."""
    mock_arg_desc = MagicMock()
    mock_arg_desc.DataType.Identifier = 3029
    conn, captured = _make_methodcall_conn(expected_args=[mock_arg_desc])

    structured_value = MagicMock()
    with patch("python.connection.create_call_structure", return_value=structured_value) as mock_ccs:
        with patch("python.connection.serialize_full_event", return_value=[]):
            with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
                result = await conn.methodcall(
                    {
                        **_MC_PAYLOAD,
                        "arguments": [
                            {
                                "dataType": 24,
                                "value": [
                                    {"value": "JP-1", "type": "31918"},
                                    {"value": "", "type": "31918"},
                                    {"value": "", "type": "31918"},
                                ],
                            }
                        ],
                    }
                )

    assert result["callStatus"] == "Succeeded"
    mock_ccs.assert_called_once()
    called_argument = mock_ccs.call_args.args[0]
    assert called_argument["dataType"] == 3029
    assert captured[0].Value is structured_value


# ---------------------------------------------------------------------------
# methodcall — except ua.UaError handling (lines 787-796)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_methodcall_uaerror_bad_too_many_sessions_returns_specific_message():
    """ua.UaError with 'BadTooManySessions' returns the server-overloaded message (line 790)."""
    from asyncua import ua

    conn, _ = _make_methodcall_conn(expected_args=[], call_method_exc=ua.UaError("BadTooManySessions"))

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        result = await conn.methodcall({**_MC_PAYLOAD, "arguments": []})

    assert "exception" in result
    assert "too many open sessions" in result["exception"].lower()


@pytest.mark.asyncio
async def test_methodcall_uaerror_secure_channel_closed_connection_alive_returns_unknown_state():
    """A transport failure stays visible when the session remains open."""
    from asyncua import ua

    conn, _ = _make_methodcall_conn(expected_args=[], call_method_exc=ua.UaError("BadSecureChannelClosed"))

    # First call (entry guard) → True; second call (inside except) → True
    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        result = await conn.methodcall({**_MC_PAYLOAD, "arguments": []})

    assert "exception" in result
    assert "completion state is unknown" in result["exception"]


@pytest.mark.asyncio
async def test_methodcall_uaerror_secure_channel_closed_connection_dead_returns_exception():
    """ua.UaError with 'BadSecureChannelClosed' returns connection-lost message when dead (line 795)."""
    from asyncua import ua

    conn, _ = _make_methodcall_conn(expected_args=[], call_method_exc=ua.UaError("BadSecureChannelClosed"))

    # First call (entry guard) → True; second call (inside except) → False (connection lost)
    with patch.object(conn, "is_connection_open", new=AsyncMock(side_effect=[True, False])):
        result = await conn.methodcall({**_MC_PAYLOAD, "arguments": []})

    assert "exception" in result
    assert "reconnect" in result["exception"].lower()


@pytest.mark.asyncio
async def test_methodcall_uaerror_generic_returns_opc_ua_error_message():
    """A generic ua.UaError (no special keyword) returns the OPC UA error message (line 796)."""
    from asyncua import ua

    conn, _ = _make_methodcall_conn(expected_args=[], call_method_exc=ua.UaError("BadNodeIdUnknown"))

    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        result = await conn.methodcall({**_MC_PAYLOAD, "arguments": []})

    assert "exception" in result
    assert "OPC UA error" in result["exception"]


# ---------------------------------------------------------------------------
# methodcall — except Exception with "Unhandled exception" (lines 800-804)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_methodcall_generic_exception_unhandled_connection_alive_returns_unknown_state():
    """An unhandled request failure stays visible when the session remains open."""
    conn, _ = _make_methodcall_conn(
        expected_args=[],
        call_method_exc=RuntimeError("Unhandled exception while sending request"),
    )

    # First call (entry guard) → True; second call (inside except) → True
    with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=True)):
        result = await conn.methodcall({**_MC_PAYLOAD, "arguments": []})

    assert "exception" in result
    assert "completion state is unknown" in result["exception"]


@pytest.mark.asyncio
async def test_methodcall_generic_exception_unhandled_connection_dead_returns_exception():
    """Generic Exception containing 'Unhandled exception' returns connection-lost when dead (line 804)."""
    conn, _ = _make_methodcall_conn(
        expected_args=[],
        call_method_exc=RuntimeError("Unhandled exception while sending request"),
    )

    # First call (entry guard) → True; second call (inside except) → False
    with patch.object(conn, "is_connection_open", new=AsyncMock(side_effect=[True, False])):
        result = await conn.methodcall({**_MC_PAYLOAD, "arguments": []})

    assert "exception" in result
    assert "reconnect" in result["exception"].lower()
