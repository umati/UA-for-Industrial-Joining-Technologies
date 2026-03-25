import json
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from Python.ijt_interface import IJTInterface
from Python.connection import Connection


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
        assert inspect.iscoroutinefunction(method), (
            f"Connection.{method_name} must be async"
        )


# ---------------------------------------------------------------------------
# CONTRACT: Critical static assets must exist on disk
# ---------------------------------------------------------------------------

WEB_CLIENT_ROOT = Path(__file__).parents[3]

REQUIRED_STATIC_ASSETS = [
    "src/Resources/digital_twin.jpg",
    "src/Resources/settings.json",
    "src/Resources/connectionpoints.json",
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

JS_SRC_ROOT = WEB_CLIENT_ROOT / "src" / "Javascripts"

def test_jointdemo_uses_absolute_image_path():
    """JointDemo.mjs must use /src/Resources/ (absolute) for the digital_twin image.
    A relative ./Resources/ path resolves from document root and breaks after src/ reorg."""
    joint_demo = WEB_CLIENT_ROOT / "src" / "Javascripts" / "Views" / "Demo" / "JointDemo.mjs"
    assert joint_demo.exists(), f"JointDemo.mjs not found at {joint_demo}"
    content = joint_demo.read_text(encoding="utf-8")
    assert "./Resources/digital_twin" not in content, (
        "JointDemo.mjs uses './Resources/digital_twin' which is relative to document root and breaks. "
        "Use '/src/Resources/digital_twin.jpg' instead."
    )
    assert "/src/Resources/digital_twin" in content, (
        "JointDemo.mjs must reference digital_twin.jpg via '/src/Resources/digital_twin.jpg'"
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
    settings_file.write_text('{"initialViewLevel": 3}', encoding="utf-8")

    interface._resource_path = lambda filename: settings_file  # type: ignore[method-assign]

    await interface.handle(
        fake_websocket,
        {"command": "get settings", "endpoint": "common", "uniqueid": 11},
    )

    payload = decode_last_message(fake_websocket)
    assert payload["data"]["initialViewLevel"] == 3
    assert payload["uniqueid"] == 11


@pytest.mark.asyncio
@pytest.mark.core
async def test_set_settings_writes_json(local_temp_dir, fake_websocket):
    interface = IJTInterface()
    settings_file = local_temp_dir / "settings-set.json"

    interface._resource_path = lambda filename: settings_file  # type: ignore[method-assign]

    await interface.handle(
        fake_websocket,
        {"command": "set settings", "endpoint": "common", "initialViewLevel": 2},
    )

    saved = json.loads(settings_file.read_text(encoding="utf-8"))
    assert saved["initialViewLevel"] == 2
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

