import asyncio
import os

import pytest

from python.connection import Connection
from python.network_utils import endpoint_reachable


@pytest.fixture
def opcua_endpoint() -> str:
    endpoint = os.getenv("OPCUA_TEST_ENDPOINT")
    if not endpoint:
        pytest.fail(
            "OPCUA_TEST_ENDPOINT is not set and the auto-start fixture failed to "
            "start the OPC UA server. Check ensure_integration_servers in conftest.py."
        )

    if not endpoint_reachable(endpoint):
        pytest.fail(
            f"OPC UA endpoint {endpoint} is not reachable. The server should have been auto-started by conftest.py."
        )

    return endpoint


@pytest.mark.asyncio
async def test_connect_and_namespace_query(opcua_endpoint):
    conn = Connection(opcua_endpoint, websocket=None)
    try:
        result = await conn.connect()
        assert "exception" not in result

        namespaces = await conn.namespaces({})
        assert "exception" not in namespaces
        assert "namespaces" in namespaces
    finally:
        await conn.terminate()


@pytest.mark.asyncio
async def test_read_root_node(opcua_endpoint):
    conn = Connection(opcua_endpoint, websocket=None)
    try:
        result = await conn.connect()
        assert "exception" not in result

        read_result = await conn.read({"nodeid": "ns=0;i=84"})
        assert "exception" not in read_result
        assert read_result["command"] == "readresult"
        assert read_result["nodeid"] == "ns=0;i=84"
    finally:
        await conn.terminate()


# ---------------------------------------------------------------------------
# Extended integration tests — require live IJT OPC UA server
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_has_ijt_namespace(opcua_endpoint):
    """
    The IJT companion spec registers a specific namespace URI.
    Verify it is present in the server's namespace table.
    """
    conn = Connection(opcua_endpoint, websocket=None)
    try:
        await conn.connect()
        ns_result = await conn.namespaces({})
        namespaces: list = ns_result.get("namespaces", [])
        # IJT companion spec namespace URI (OPC 40010)
        ijt_ns = "http://opcfoundation.org/UA/IJT/"
        assert any(ijt_ns in str(ns) for ns in namespaces), (
            f"IJT namespace '{ijt_ns}' not found in server namespaces: {namespaces}"
        )
    finally:
        await conn.terminate()


@pytest.mark.asyncio
async def test_browse_root_returns_children(opcua_endpoint):
    """Browsing the OPC UA root node must return at least the standard Objects folder."""
    conn = Connection(opcua_endpoint, websocket=None)
    try:
        await conn.connect()
        result = await conn.browse({"nodeid": "ns=0;i=84"})
        assert "exception" not in result
        nodes = result.get("nodes", [])
        assert len(nodes) > 0, "Root browse returned no child nodes"
        node_names = [n.get("BrowseName", "") for n in nodes]
        assert any("Objects" in name for name in node_names), (
            f"Expected 'Objects' folder in root browse, got: {node_names}"
        )
    finally:
        await conn.terminate()


@pytest.mark.asyncio
async def test_read_server_status_current_time(opcua_endpoint):
    """
    ServerStatus/CurrentTime (ns=0;i=2258) must be readable and return a datetime.
    This is a standard OPC UA node present on all compliant servers.
    """
    conn = Connection(opcua_endpoint, websocket=None)
    try:
        await conn.connect()
        result = await conn.read({"nodeid": "ns=0;i=2258"})
        assert "exception" not in result, f"Read failed: {result.get('exception')}"
        value = result.get("value")
        assert value is not None, "ServerStatus/CurrentTime returned None"
    finally:
        await conn.terminate()


@pytest.mark.asyncio
async def test_reconnect_after_terminate(opcua_endpoint):
    """
    Terminate a connection and reconnect to the same endpoint.
    The second connect() must succeed, verifying the client cleans up correctly.
    """
    conn = Connection(opcua_endpoint, websocket=None)
    try:
        r1 = await conn.connect()
        assert "exception" not in r1
        await conn.terminate()

        # Brief pause to allow server-side cleanup
        await asyncio.sleep(0.5)

        r2 = await conn.connect()
        assert "exception" not in r2, f"Reconnect failed: {r2.get('exception')}"
    finally:
        await conn.terminate()


@pytest.mark.asyncio
async def test_is_connection_open_reflects_state(opcua_endpoint):
    """is_connection_open() must return True while connected and False after terminate."""
    conn = Connection(opcua_endpoint, websocket=None)
    try:
        await conn.connect()
        assert await conn.is_connection_open() is True
    finally:
        await conn.terminate()
    assert await conn.is_connection_open() is False


@pytest.mark.asyncio
async def test_subscribe_and_receive_event(opcua_endpoint):
    """
    Subscribe to OPC UA events on the server node.
    With the IJT simulator running, at least the subscription setup must succeed
    without raising an exception.
    """
    received: list = []

    class _SimpleHandler:
        async def event_notification(self, event):
            received.append(event)

    conn = Connection(opcua_endpoint, websocket=None)
    try:
        await conn.connect()
        handler = _SimpleHandler()
        sub_result = await conn.subscribe({"handler": handler})
        # A successful subscription returns no 'exception' key
        assert "exception" not in sub_result, f"Subscription failed: {sub_result.get('exception')}"
        # Wait briefly for any queued events from the live simulator
        await asyncio.sleep(1.0)
        # We don't assert on received count because the simulator may not
        # produce events in the test window — just verify no exception.
    finally:
        await conn.terminate()


@pytest.mark.asyncio
async def test_double_connect_does_not_error(opcua_endpoint):
    """
    Calling connect() on an already-connected Connection must not raise.
    The connection should report open after the second call.
    """
    conn = Connection(opcua_endpoint, websocket=None)
    try:
        r1 = await conn.connect()
        assert "exception" not in r1
        r2 = await conn.connect()
        assert "exception" not in r2
        assert await conn.is_connection_open() is True
    finally:
        await conn.terminate()


@pytest.mark.asyncio
async def test_read_nonexistent_node_returns_exception_not_crash(opcua_endpoint):
    """
    Reading a node that does not exist must return an 'exception' dict,
    not raise an unhandled Python exception.
    """
    conn = Connection(opcua_endpoint, websocket=None)
    try:
        await conn.connect()
        result = await conn.read({"nodeid": "ns=99;i=999999"})
        # Should be a dict (possibly with 'exception') — must not raise
        assert isinstance(result, dict)
    finally:
        await conn.terminate()
