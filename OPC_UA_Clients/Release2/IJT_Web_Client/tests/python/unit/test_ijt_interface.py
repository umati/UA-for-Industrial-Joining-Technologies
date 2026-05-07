import inspect
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from python.connection import Connection
from python.ijt_interface import IJTInterface

# ---------------------------------------------------------------------------
# CONTRACT: Connection class must expose every command the frontend sends
# This test catches any accidentally-dropped `async def` lines in connection.py
# ---------------------------------------------------------------------------

REQUIRED_CONNECTION_METHODS = [
    "connect",
    "terminate",
    "subscribe",
    "read",
    "pathtoid",
    "namespaces",
    "browse",
    "methodcall",
    "read_product_instance_uri",
    "is_connection_open",
]


@pytest.mark.parametrize("method_name", REQUIRED_CONNECTION_METHODS)
def test_connection_has_required_method(method_name):
    """Every command the frontend sends must have a corresponding async method on Connection."""
    method = getattr(Connection, method_name, None)
    assert method is not None, (
        f"Connection.{method_name} is missing — this command from the browser will always fail. "
        f"Check connection.py for a dropped 'async def' line."
    )
    if method_name not in ("is_connection_open",):
        assert inspect.iscoroutinefunction(method), f"Connection.{method_name} must be async"


# ---------------------------------------------------------------------------
# CONTRACT: Critical static assets must exist on disk
# ---------------------------------------------------------------------------

WEB_CLIENT_ROOT = Path(__file__).parents[3]

REQUIRED_STATIC_ASSETS = [
    "src/resources/digital_twin.jpg",
    "src/resources/settings.json",
    "src/resources/connectionpoints.json",
    "node_modules/chart.js/dist/chart.umd.js",
]


@pytest.mark.parametrize("asset_path", REQUIRED_STATIC_ASSETS)
def test_required_static_asset_exists(asset_path):
    """Static assets that the browser fetches must exist — missing ones cause 404s."""
    full = WEB_CLIENT_ROOT / asset_path
    assert full.exists(), (
        f"Required asset missing: {asset_path}\n"
        f"Expected at: {full}\n"
        "This causes a browser 404. If the file was moved, update its reference too."
    )


# ---------------------------------------------------------------------------
# CONTRACT: JS source must not use stale relative paths for static assets
# ---------------------------------------------------------------------------

JS_SRC_ROOT = WEB_CLIENT_ROOT / "src" / "javascripts"


def test_jointdemo_uses_absolute_image_path():
    """joint-demo.mjs must use /src/resources/ (absolute) for the digital_twin image.
    A relative ./resources/ path resolves from document root and breaks after src/ reorg."""
    joint_demo = WEB_CLIENT_ROOT / "src" / "javascripts" / "views" / "standard-demo" / "joint-demo.mjs"
    assert joint_demo.exists(), f"joint-demo.mjs not found at {joint_demo}"
    content = joint_demo.read_text(encoding="utf-8")
    assert "./resources/digital_twin" not in content, (
        "joint-demo.mjs uses './resources/digital_twin' which is relative to document root and breaks. "
        "Use '/src/resources/digital_twin.jpg' instead."
    )
    assert "/src/resources/digital_twin" in content, (
        "joint-demo.mjs must reference digital_twin.jpg via '/src/resources/digital_twin.jpg'"
    )


def test_no_js_uses_stale_three_level_node_modules_path():
    """After src/ reorganization chart.js must use 4 levels of '../' not 3.
    '../../../../node_modules/' is correct; '../../../node_modules/' as a standalone import is wrong."""
    import re

    # Match only exactly 3 levels: quote or space then ../../../node_modules/ (not preceded by another ../)
    pattern = re.compile(r"""['"`\s]\.\.\/\.\.\/\.\.\/node_modules\/""")
    for js_file in JS_SRC_ROOT.rglob("*.mjs"):
        content = js_file.read_text(encoding="utf-8")
        match = pattern.search(content)
        assert not match, (
            f"{js_file.relative_to(WEB_CLIENT_ROOT)} uses '../../../node_modules/' "
            f"which is wrong after src/ reorganization. Use '../../../../node_modules/' instead."
        )


@pytest.mark.asyncio
@pytest.mark.core
async def test_unknown_command_returns_structured_error(fake_websocket, decode_last_message):
    interface = IJTInterface()

    await interface.handle(
        fake_websocket,
        {"command": "read", "endpoint": "opc.tcp://missing:4840", "uniqueid": 7},
    )

    payload = decode_last_message(fake_websocket)
    assert payload["command"] == "read"
    assert payload["uniqueid"] == 7
    assert "exception" in payload["data"]
    assert payload["error"]["code"] == "OPCUA_REQUEST_FAILED"


@pytest.mark.asyncio
@pytest.mark.core
async def test_get_settings_uses_resource_file(local_temp_dir, fake_websocket, decode_last_message):
    interface = IJTInterface()
    settings_file = local_temp_dir / "settings-get.json"
    settings_file.write_text('{"initialviewlevel": 3}', encoding="utf-8")

    interface._resource_path = lambda filename: settings_file  # type: ignore[method-assign]

    await interface.handle(
        fake_websocket,
        {"command": "get settings", "endpoint": "common", "uniqueid": 11},
    )

    payload = decode_last_message(fake_websocket)
    assert payload["data"]["initialviewlevel"] == 3
    assert payload["uniqueid"] == 11


@pytest.mark.asyncio
@pytest.mark.core
async def test_set_settings_writes_json(local_temp_dir, fake_websocket):
    interface = IJTInterface()
    settings_file = local_temp_dir / "settings-set.json"

    interface._resource_path = lambda filename: settings_file  # type: ignore[method-assign]

    await interface.handle(
        fake_websocket,
        {"command": "set settings", "endpoint": "common", "initialviewlevel": 2},
    )

    saved = json.loads(settings_file.read_text(encoding="utf-8"))
    assert saved["initialviewlevel"] == 2
    assert fake_websocket.sent_messages == []


@pytest.mark.asyncio
@pytest.mark.core
async def test_disconnect_terminates_all_connections():
    interface = IJTInterface()
    conn_a = AsyncMock()
    conn_b = AsyncMock()

    interface.connection_list = {
        "opc.tcp://a:4840": conn_a,
        "opc.tcp://b:4840": conn_b,
    }

    await interface.disconnect()

    conn_a.terminate.assert_awaited_once()
    conn_b.terminate.assert_awaited_once()
    assert interface.connection_list == {}


# ---------------------------------------------------------------------------
# _build_response
# ---------------------------------------------------------------------------


def test_build_response_includes_uniqueid_when_provided():
    resp = IJTInterface._build_response("browse", "opc.tcp://host:4840", 42, {"nodes": []})
    assert resp["uniqueid"] == 42
    assert resp["command"] == "browse"
    assert resp["endpoint"] == "opc.tcp://host:4840"
    assert resp["data"] == {"nodes": []}
    assert "error" not in resp


def test_build_response_omits_uniqueid_when_none():
    resp = IJTInterface._build_response("browse", "ep", None, {})
    assert "uniqueid" not in resp


def test_build_response_adds_error_block_on_exception_data():
    data = {"exception": "Connection refused"}
    resp = IJTInterface._build_response("connect to", "ep", 1, data)
    assert resp["error"]["code"] == "OPCUA_REQUEST_FAILED"
    assert "Connection refused" in resp["error"]["message"]


def test_build_response_no_error_block_on_clean_data():
    resp = IJTInterface._build_response("read", "ep", 1, {"value": 99})
    assert "error" not in resp


def test_build_response_zero_uniqueid_is_included():
    """uniqueid=0 is falsy in Python but must still be included in the response."""
    resp = IJTInterface._build_response("cmd", "ep", 0, {})
    assert "uniqueid" in resp
    assert resp["uniqueid"] == 0


# ---------------------------------------------------------------------------
# handle_terminate_connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_terminate_connection_calls_safe_terminate():
    interface = IJTInterface()
    mock_conn = AsyncMock()
    interface.connection_list["opc.tcp://host:4840"] = mock_conn

    result = await interface.handle_terminate_connection("opc.tcp://host:4840")

    mock_conn.terminate.assert_awaited_once()
    assert interface.connection_list["opc.tcp://host:4840"] is None
    assert result == {}


@pytest.mark.asyncio
async def test_handle_terminate_connection_unknown_endpoint_returns_empty():
    interface = IJTInterface()
    result = await interface.handle_terminate_connection("opc.tcp://unknown:4840")
    assert result == {}


@pytest.mark.asyncio
async def test_handle_terminate_connection_tolerates_terminate_error():
    """Even if terminate() raises, the connection is set to None and {} is returned."""
    interface = IJTInterface()
    broken_conn = AsyncMock()
    broken_conn.terminate.side_effect = RuntimeError("transport closed")
    interface.connection_list["opc.tcp://broken:4840"] = broken_conn

    result = await interface.handle_terminate_connection("opc.tcp://broken:4840")

    assert result == {}
    assert interface.connection_list["opc.tcp://broken:4840"] is None


# ---------------------------------------------------------------------------
# disconnect — double-call guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disconnect_is_idempotent():
    """Calling disconnect() twice must not double-terminate connections."""
    interface = IJTInterface()
    conn = AsyncMock()
    interface.connection_list = {"opc.tcp://host:4840": conn}

    await interface.disconnect()
    await interface.disconnect()  # second call is a no-op

    conn.terminate.assert_awaited_once()


# ---------------------------------------------------------------------------
# ensure_connection_open — reconnect path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_connection_open_returns_true_when_already_open():
    interface = IJTInterface()
    conn = AsyncMock()
    conn.is_connection_open.return_value = True

    result = await interface.ensure_connection_open(conn)

    assert result is True
    conn.connect.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_connection_open_reconnects_when_closed():
    interface = IJTInterface()
    conn = AsyncMock()
    conn.is_connection_open.return_value = False
    conn.connect.return_value = {"status": "connected"}

    result = await interface.ensure_connection_open(conn)

    assert result is True
    conn.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_connection_open_returns_false_on_exception_result():
    """connect() returning a dict with 'exception' key means reconnect failed."""
    interface = IJTInterface()
    conn = AsyncMock()
    conn.is_connection_open.return_value = False
    conn.connect.return_value = {"exception": "Timeout"}

    result = await interface.ensure_connection_open(conn)

    assert result is False


@pytest.mark.asyncio
async def test_ensure_connection_open_returns_false_on_raised_exception():
    interface = IJTInterface()
    conn = AsyncMock()
    conn.is_connection_open.side_effect = RuntimeError("socket error")

    result = await interface.ensure_connection_open(conn)

    assert result is False


# ---------------------------------------------------------------------------
# handle — command routing via websocket
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_terminate_command_via_handle(fake_websocket, decode_last_message):
    interface = IJTInterface()
    mock_conn = AsyncMock()
    interface.connection_list["opc.tcp://host:4840"] = mock_conn

    await interface.handle(
        fake_websocket,
        {"command": "terminate connection", "endpoint": "opc.tcp://host:4840", "uniqueid": 5},
    )

    payload = decode_last_message(fake_websocket)
    assert payload["command"] == "terminate connection"
    assert payload["uniqueid"] == 5
    assert payload["data"] == {}
    mock_conn.terminate.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_missing_endpoint_returns_exception(fake_websocket, decode_last_message):
    """call_connection with no connection registered returns exception, not crash."""
    interface = IJTInterface()

    await interface.handle(
        fake_websocket,
        {"command": "browse", "endpoint": "opc.tcp://not_registered:4840"},
    )

    payload = decode_last_message(fake_websocket)
    assert "exception" in payload["data"]
    assert payload["error"]["code"] == "OPCUA_REQUEST_FAILED"


# ===========================================================================
# _resource_path — lines 52-56
# ===========================================================================


def test_resource_path_returns_path_in_existing_directory():
    """_resource_path returns a path inside the first candidate dir that exists."""
    result = IJTInterface._resource_path("settings.json")
    assert result.name == "settings.json"
    assert result.parent.exists()


def test_resource_path_fallback_when_no_candidate_directory():
    """_resource_path falls back to first candidate name when no dir exists (line 56)."""
    from pathlib import Path
    from unittest.mock import patch

    with patch.object(IJTInterface, "_SOURCE_ROOT", Path("/nonexistent/xyz_root")):
        with patch.object(IJTInterface, "_RESOURCE_DIR_CANDIDATES", ("no_such_dir",)):
            result = IJTInterface._resource_path("test.json")

    assert result.name == "test.json"
    assert "no_such_dir" in str(result)


# ===========================================================================
# _normalize_json_keys_lower — list input (line 64)
# ===========================================================================


def test_normalize_json_keys_lower_handles_list():
    """_normalize_json_keys_lower normalizes keys inside dicts nested in lists."""
    payload = [{"KEY": "val"}, {"Another": 2}]
    result = IJTInterface._normalize_json_keys_lower(payload)
    assert result == [{"key": "val"}, {"another": 2}]


# ===========================================================================
# call_connection — ensure_connection_open returns False (lines 110-111)
# ===========================================================================


@pytest.mark.asyncio
async def test_call_connection_returns_exception_when_ensure_open_fails():
    """call_connection returns exception when ensure_connection_open returns False."""
    from unittest.mock import AsyncMock, patch

    interface = IJTInterface()
    mock_conn = AsyncMock()
    ep = "opc.tcp://host:4840"
    interface.connection_list[ep] = mock_conn

    with patch.object(interface, "ensure_connection_open", new=AsyncMock(return_value=False)):
        result = await interface.call_connection({"endpoint": ep}, "read")

    assert "exception" in result
    assert "open" in result["exception"].lower() or "ensure" in result["exception"].lower()


# ===========================================================================
# call_connection — disallowed method (lines 113-115)
# ===========================================================================


@pytest.mark.asyncio
async def test_call_connection_returns_exception_for_disallowed_method():
    """call_connection returns exception when method is not in _ALLOWED_METHODS."""
    from unittest.mock import AsyncMock, patch

    interface = IJTInterface()
    mock_conn = AsyncMock()
    ep = "opc.tcp://host:4840"
    interface.connection_list[ep] = mock_conn

    with patch.object(interface, "ensure_connection_open", new=AsyncMock(return_value=True)):
        result = await interface.call_connection({"endpoint": ep}, "delete_all_nodes")

    assert "exception" in result
    assert "not allowed" in result["exception"]


# ===========================================================================
# call_connection — getattr raises AttributeError (lines 117-121)
# ===========================================================================


@pytest.mark.asyncio
async def test_call_connection_returns_exception_on_attribute_error():
    """call_connection returns exception when the connection has no matching method."""
    from unittest.mock import AsyncMock, patch

    class _NoMethods:
        pass

    interface = IJTInterface()
    ep = "opc.tcp://host:4840"
    interface.connection_list[ep] = _NoMethods()  # type: ignore[arg-type]

    with patch.object(interface, "ensure_connection_open", new=AsyncMock(return_value=True)):
        result = await interface.call_connection({"endpoint": ep}, "read")

    assert "exception" in result
    assert "not found" in result["exception"]


# ===========================================================================
# call_connection — method call raises Exception (lines 123-127)
# ===========================================================================


@pytest.mark.asyncio
async def test_call_connection_returns_exception_on_method_exception():
    """call_connection wraps an exception raised by the dispatched method."""
    from unittest.mock import AsyncMock, patch

    interface = IJTInterface()
    mock_conn = AsyncMock()
    mock_conn.read = AsyncMock(side_effect=RuntimeError("opc ua read error"))
    ep = "opc.tcp://host:4840"
    interface.connection_list[ep] = mock_conn

    with patch.object(interface, "ensure_connection_open", new=AsyncMock(return_value=True)):
        result = await interface.call_connection({"endpoint": ep}, "read")

    assert "exception" in result
    assert "opc ua read error" in result["exception"]


# ===========================================================================
# handle_get_connection_points — exception path (lines 136-142)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_get_connection_points_returns_exception_on_read_error():
    """handle_get_connection_points returns exception dict when file read fails."""
    from pathlib import Path
    from unittest.mock import MagicMock

    interface = IJTInterface()
    bad_path = MagicMock(spec=Path)
    bad_path.read_text.side_effect = PermissionError("permission denied")
    interface._resource_path = lambda _: bad_path  # type: ignore[method-assign]

    result = await interface.handle_get_connection_points()

    assert "exception" in result


# ===========================================================================
# handle_set_connection_points — exception path (lines 151-156)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_set_connection_points_logs_on_write_error():
    """handle_set_connection_points swallows write exceptions (no raise)."""
    from pathlib import Path

    interface = IJTInterface()
    interface._resource_path = lambda _: Path("/nonexistent/xyz/file.json")  # type: ignore[method-assign]

    await interface.handle_set_connection_points({"connectionpoints": []})


# ===========================================================================
# handle_get_settings — generic Exception path (lines 169-173)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_get_settings_returns_exception_on_generic_error():
    """handle_get_settings returns exception dict for non-FileNotFoundError errors."""
    from pathlib import Path
    from unittest.mock import MagicMock

    interface = IJTInterface()
    bad_path = MagicMock(spec=Path)
    bad_path.read_text.side_effect = PermissionError("no access")
    interface._resource_path = lambda _: bad_path  # type: ignore[method-assign]

    result = await interface.handle_get_settings()

    assert "exception" in result
    assert "no access" in result["exception"]


# ===========================================================================
# handle_set_settings — exception path (lines 186-187)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_set_settings_logs_on_write_error():
    """handle_set_settings swallows write exceptions (no raise)."""
    from pathlib import Path

    interface = IJTInterface()
    interface._resource_path = lambda _: Path("/nonexistent/xyz/settings.json")  # type: ignore[method-assign]

    await interface.handle_set_settings({"initialviewlevel": 1})


# ===========================================================================
# handle_connect_to — endpoint already in list, terminate old conn (lines 203-211)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_connect_to_terminates_existing_connection(fake_websocket):
    """handle_connect_to terminates an existing connection before creating a new one."""
    from unittest.mock import AsyncMock, patch

    interface = IJTInterface()
    ep = "opc.tcp://host:4840"

    old_conn = AsyncMock()
    old_conn.terminate = AsyncMock(return_value=None)
    interface.connection_list[ep] = old_conn

    new_conn = AsyncMock()
    new_conn.connect = AsyncMock(return_value={"command": "connection established", "endpoint": ep})

    with patch("python.ijt_interface.Connection", return_value=new_conn):
        result = await interface.handle_connect_to(ep, fake_websocket)

    old_conn.terminate.assert_awaited_once()
    assert result.get("command") == "connection established"
    assert interface.connection_list[ep] is new_conn


@pytest.mark.asyncio
async def test_handle_connect_to_terminates_existing_connection_even_on_terminate_error(fake_websocket):
    """handle_connect_to sets old conn to None even when terminate() raises."""
    from unittest.mock import AsyncMock, patch

    interface = IJTInterface()
    ep = "opc.tcp://host:4840"

    old_conn = AsyncMock()
    old_conn.terminate = AsyncMock(side_effect=RuntimeError("already gone"))
    interface.connection_list[ep] = old_conn

    new_conn = AsyncMock()
    new_conn.connect = AsyncMock(return_value={"command": "connection established", "endpoint": ep})

    with patch("python.ijt_interface.Connection", return_value=new_conn):
        result = await interface.handle_connect_to(ep, fake_websocket)

    assert result.get("command") == "connection established"


# ===========================================================================
# handle_connect_to — new connection (lines 213-219)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_connect_to_creates_new_connection(fake_websocket):
    """handle_connect_to creates a new Connection and calls connect()."""
    from unittest.mock import AsyncMock, patch

    interface = IJTInterface()
    ep = "opc.tcp://new-host:4840"

    mock_conn = AsyncMock()
    mock_conn.connect = AsyncMock(return_value={"command": "connection established", "endpoint": ep})

    with patch("python.ijt_interface.Connection", return_value=mock_conn):
        result = await interface.handle_connect_to(ep, fake_websocket)

    assert result.get("command") == "connection established"
    assert interface.connection_list[ep] is mock_conn


# ===========================================================================
# handle() — "get connectionpoints" command (line 278)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_get_connectionpoints_command(fake_websocket, decode_last_message):
    """handle() routes 'get connectionpoints' to handle_get_connection_points."""
    from unittest.mock import AsyncMock, patch

    interface = IJTInterface()

    with patch.object(
        interface,
        "handle_get_connection_points",
        new=AsyncMock(return_value={"connectionpoints": []}),
    ):
        await interface.handle(fake_websocket, {"command": "get connectionpoints", "endpoint": ""})

    payload = decode_last_message(fake_websocket)
    assert payload["data"] == {"connectionpoints": []}


# ===========================================================================
# handle() — "set connectionpoints" returns early, no send (lines 280-281)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_set_connectionpoints_returns_early_no_websocket_send(fake_websocket):
    """handle() returns early after 'set connectionpoints' — no websocket.send call."""
    from unittest.mock import AsyncMock, patch

    interface = IJTInterface()

    with patch.object(
        interface,
        "handle_set_connection_points",
        new=AsyncMock(return_value=None),
    ):
        await interface.handle(fake_websocket, {"command": "set connectionpoints", "endpoint": ""})

    assert fake_websocket.sent_messages == []


# ===========================================================================
# handle() — "read product instance uri" command (line 288)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_read_product_instance_uri_command(fake_websocket, decode_last_message):
    """handle() routes 'read product instance uri' to call_connection."""
    from unittest.mock import AsyncMock, patch

    interface = IJTInterface()
    ep = "opc.tcp://host:4840"

    with patch.object(
        interface,
        "call_connection",
        new=AsyncMock(return_value={"uri": "urn:example:product"}),
    ):
        await interface.handle(
            fake_websocket,
            {"command": "read product instance uri", "endpoint": ep},
        )

    payload = decode_last_message(fake_websocket)
    assert payload["data"] == {"uri": "urn:example:product"}


# ===========================================================================
# handle() — "connect to" command (line 290)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_connect_to_command(fake_websocket, decode_last_message):
    """handle() routes 'connect to' to handle_connect_to."""
    from unittest.mock import AsyncMock, patch

    interface = IJTInterface()
    ep = "opc.tcp://host:4840"

    with patch.object(
        interface,
        "handle_connect_to",
        new=AsyncMock(return_value={"command": "connection established", "endpoint": ep}),
    ):
        await interface.handle(fake_websocket, {"command": "connect to", "endpoint": ep})

    payload = decode_last_message(fake_websocket)
    assert payload["data"]["command"] == "connection established"


# ===========================================================================
# handle() — inner exception sets return_values (lines 295-297)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_inner_exception_sets_return_values(fake_websocket, decode_last_message):
    """When a handler raises, handle() catches it and sends exception in response."""
    from unittest.mock import AsyncMock, patch

    interface = IJTInterface()

    with patch.object(
        interface,
        "handle_get_connection_points",
        new=AsyncMock(side_effect=RuntimeError("unexpected boom")),
    ):
        await interface.handle(fake_websocket, {"command": "get connectionpoints", "endpoint": ""})

    payload = decode_last_message(fake_websocket)
    assert "exception" in payload["data"]
    assert payload["error"]["code"] == "OPCUA_REQUEST_FAILED"


# ===========================================================================
# __del__ (pass in __del__)
# ===========================================================================


def test_ijt_interface_del_is_callable():
    """IJTInterface.__del__() is a no-op and must not raise."""
    interface = IJTInterface()
    interface.__del__()


# ===========================================================================
# handle_get_connection_points — success path (line 139)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_get_connection_points_returns_data_when_file_exists(tmp_path):
    """handle_get_connection_points reads and normalises JSON via a patched hermetic path."""
    cp_data = {"ConnectionPoint1": {"Url": "opc.tcp://localhost:4840", "Name": "Test"}}
    cp_file = tmp_path / "connectionpoints.json"
    cp_file.write_text(json.dumps(cp_data), encoding="utf-8")

    interface = IJTInterface()
    interface._resource_path = lambda _: cp_file  # type: ignore[method-assign]

    result = await interface.handle_get_connection_points()

    assert "exception" not in result
    assert "connectionpoint1" in result  # key normalised to lower-case
    assert result["connectionpoint1"]["url"] == "opc.tcp://localhost:4840"
    assert result["connectionpoint1"]["name"] == "Test"


@pytest.mark.asyncio
async def test_handle_get_connection_points_uses_runtime_local_endpoint(tmp_path, monkeypatch):
    """OPCUA_TEST_ENDPOINT makes the browser LOCAL tab match the runner server."""
    cp_data = {
        "connectionpoints": [
            {
                "name": "LOCAL",
                "address": "opc.tcp://127.0.0.1:40451",
                "autoconnect": True,
            }
        ]
    }
    cp_file = tmp_path / "connectionpoints.json"
    cp_file.write_text(json.dumps(cp_data), encoding="utf-8")
    monkeypatch.setenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40463")

    interface = IJTInterface()
    interface._resource_path = lambda _: cp_file  # type: ignore[method-assign]

    result = await interface.handle_get_connection_points()

    assert result["connectionpoints"] == [
        {
            "name": "LOCAL",
            "address": "opc.tcp://localhost:40463",
            "autoconnect": True,
        }
    ]


def test_runtime_local_endpoint_is_inserted_when_missing(monkeypatch):
    monkeypatch.setenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40463")

    result = IJTInterface._apply_runtime_local_endpoint(
        {
            "connectionpoints": [
                {
                    "name": "REMOTE",
                    "address": "opc.tcp://example.com:4840",
                    "autoconnect": False,
                }
            ]
        }
    )

    assert result["connectionpoints"][0] == {
        "name": "LOCAL",
        "address": "opc.tcp://localhost:40463",
        "autoconnect": True,
    }
    assert result["connectionpoints"][1]["name"] == "REMOTE"


def test_runtime_local_endpoint_handles_non_dict_payload(monkeypatch):
    monkeypatch.setenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40463")

    result = IJTInterface._apply_runtime_local_endpoint([])

    assert result == {
        "connectionpoints": [
            {
                "name": "LOCAL",
                "address": "opc.tcp://localhost:40463",
                "autoconnect": True,
            }
        ]
    }


# ===========================================================================
# handle_get_settings — FileNotFoundError path (line 170)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_get_settings_returns_exception_on_file_not_found():
    """handle_get_settings returns structured exception when file is missing."""
    from pathlib import Path

    interface = IJTInterface()
    interface._resource_path = lambda _: Path("/no/such/path/settings.json")  # type: ignore[method-assign]

    result = await interface.handle_get_settings()

    assert "exception" in result
    assert "File not found" in result["exception"]


# ===========================================================================
# handle_connect_to — Connection.connect() raises (lines 217-219)
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_connect_to_returns_exception_when_connect_raises(fake_websocket):
    """handle_connect_to wraps exceptions from connection.connect() in exception dict."""
    from unittest.mock import AsyncMock, patch

    interface = IJTInterface()
    ep = "opc.tcp://broken:4840"

    mock_conn = AsyncMock()
    mock_conn.connect = AsyncMock(side_effect=RuntimeError("OPCUA handshake failed"))

    with patch("python.ijt_interface.Connection", return_value=mock_conn):
        result = await interface.handle_connect_to(ep, fake_websocket)

    assert "exception" in result
    assert "OPCUA handshake failed" in result["exception"]


# ===========================================================================
# _safe_terminate — early return when connection is None (line 333)
# ===========================================================================


@pytest.mark.asyncio
async def test_safe_terminate_is_noop_when_connection_is_none():
    """_safe_terminate returns immediately when called with None connection."""
    interface = IJTInterface()
    await interface._safe_terminate("opc.tcp://host:4840", None)
