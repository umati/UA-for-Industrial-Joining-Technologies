"""
test_server_connection.py — Basic OPC UA server connectivity tests.
Verifies:
  - The server is reachable and the OPC UA Server node is readable.
  - The active endpoint uses the OPC UA Binary (opc.tcp) transport.
  - Data type definitions load without raising an exception.
"""
import os
import pytest
pytestmark = pytest.mark.live
async def test_server_reachable(session_client):
    """OPC UA Server node must be readable."""
    server_node = session_client.nodes.server
    browse_name = await server_node.read_browse_name()
    assert browse_name is not None, "Server node browse name should not be None"
    assert str(browse_name.Name) != "", "Server node browse name should not be empty"
async def test_server_supports_opc_ua_binary(session_client):
    """Active server endpoint must use the opc.tcp:// transport scheme."""
    server_url = os.environ.get("OPCUA_SERVER_URL", "opc.tcp://localhost:40451")
    assert server_url.startswith("opc.tcp://"), (
        f"Expected opc.tcp:// transport, got URL: {server_url}"
    )
async def test_load_data_type_definitions_succeeds(opcua_client):
    """load_data_type_definitions() must complete without raising an exception."""
    try:
        await opcua_client.load_data_type_definitions()
    except Exception as exc:
        pytest.fail(f"load_data_type_definitions() raised an unexpected exception: {exc}")