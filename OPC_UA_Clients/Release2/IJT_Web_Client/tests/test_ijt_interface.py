import json
from unittest.mock import AsyncMock

import pytest

from Python.ijt_interface import IJTInterface


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
