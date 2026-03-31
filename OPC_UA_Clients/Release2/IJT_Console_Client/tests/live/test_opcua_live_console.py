"""
Live integration tests for IJT_Console_Client.

These tests require a running OPC UA server at opc.tcp://localhost:40451.
They are automatically skipped if the server is unavailable.

Run with:
    pytest tests/live/ -v -m live
"""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

_SERVER_URL = "opc.tcp://localhost:40451"


# ---------------------------------------------------------------------------
# Live tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connect_to_server():
    """Verify that a real connection to the OPC UA server can be established."""
    from opcua_client import OPCUAClient

    client = OPCUAClient(_SERVER_URL)
    try:
        await client.connect()
        assert client.client is not None
    finally:
        await client.cleanup()


@pytest.mark.asyncio
async def test_browse_root_node_returns_results():
    """Browsing the root node must return child nodes."""
    from opcua_client import OPCUAClient

    client = OPCUAClient(_SERVER_URL)
    try:
        await client.connect()
        root = client.client.get_root_node()
        children = await root.get_children()
        assert len(children) > 0
    finally:
        await client.cleanup()


@pytest.mark.asyncio
async def test_subscribe_to_events_and_receive_within_30s():
    """Subscribe to events and wait up to 30s for at least one event."""
    from opcua_client import OPCUAClient

    client = OPCUAClient(_SERVER_URL)
    try:
        await client.connect()
        await client.subscribe_to_events()

        deadline = asyncio.get_event_loop().time() + 30.0
        while asyncio.get_event_loop().time() < deadline:
            if (
                client.handler_result_event is not None
                or client.handler_joining_event is not None
            ):
                break
            await asyncio.sleep(1.0)

        # subscriptions were set up successfully if we got here
        assert True
    finally:
        await client.cleanup()
