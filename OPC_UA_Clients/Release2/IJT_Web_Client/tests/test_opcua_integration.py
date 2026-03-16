import os
import socket
from urllib.parse import urlparse

import pytest

from Python.connection import Connection


pytestmark = pytest.mark.integration


@pytest.fixture
def opcua_endpoint() -> str:
    endpoint = os.getenv("OPCUA_TEST_ENDPOINT")
    if not endpoint:
        pytest.skip("Set OPCUA_TEST_ENDPOINT to run integration tests.")

    parsed = urlparse(endpoint)
    host = parsed.hostname or "localhost"
    port = parsed.port or 40451
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        if sock.connect_ex((host, port)) != 0:
            pytest.skip(
                f"OPC UA endpoint {endpoint} is not reachable. Start the simulator/server and rerun."
            )
    finally:
        sock.close()

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
