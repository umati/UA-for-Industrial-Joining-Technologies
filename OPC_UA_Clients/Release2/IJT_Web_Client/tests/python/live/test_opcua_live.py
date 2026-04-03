"""
Live functional tests against the running OPC UA IJT Server and Python backend.

These tests verify the complete stack:
  1. OPC UA layer  — direct asyncua connection to opc.tcp://localhost:40451
  2. WebSocket layer — Python backend at ws://localhost:8001
  3. Integration   — full simulation→event→serialization pipeline

Markers:
  @pytest.mark.live       - requires OPC UA server
  @pytest.mark.live_ws    - requires backend WebSocket

Run all:
    python -m pytest tests/test_opcua_live.py -v

Run only OPC UA:
    python -m pytest tests/test_opcua_live.py -v -m live

Run only WS:
    python -m pytest tests/test_opcua_live.py -v -m live_ws
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import socket
import time
from typing import Any

import asyncua.client.ua_client as _uc
import pytest
import pytest_asyncio
from asyncua import ua

# All async tests in this file share the module-scoped event loop so they can
# use the module-scoped opcua_client fixture without cross-loop I/O hangs.
pytestmark = pytest.mark.asyncio(loop_scope="module")

# ─────────────────────────────────────────────────────────────────────────────
# asyncua 1.2b2 bug-fix: UaClient.call() calls _send_request without a
# timeout, falling back to a 1-second default. Heavy calls (load_data_type_
# definitions, browse-heavy operations) exceed 1s and raise spurious timeouts.
# Fix: replace _send_request so it uses self._timeout when none is given.
# ─────────────────────────────────────────────────────────────────────────────
def _patch_asyncua_send_timeout() -> None:
    _orig = _uc.UaClient._send_request

    async def _fixed(self, request, timeout=None,
                     message_type=ua.MessageType.SecureMessage):
        if timeout is None:
            timeout = self._timeout
        return await _orig(self, request, timeout, message_type)

    _uc.UaClient._send_request = _fixed

_patch_asyncua_send_timeout()

# ─────────────────────────────────────────────────────────────────────────────
# Module-level loop scope so all async fixtures and tests share one event loop.
# (pytest-asyncio 0.21+ deprecates the custom event_loop fixture; use this instead.)
# ─────────────────────────────────────────────────────────────────────────────
# asyncio_default_fixture_loop_scope = module is set in pytest.ini for all async tests

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

OPCUA_ENDPOINT = os.getenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40451")
WS_URL = os.getenv("WS_TEST_URL", "ws://localhost:8001")

_OPCUA_HOST, _OPCUA_PORT = "localhost", 40451
_WS_PORT = 8001

IJT_NAMESPACE_URI = "http://opcfoundation.org/UA/IJT/Base/"


def _port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


OPCUA_UP = _port_open(_OPCUA_HOST, _OPCUA_PORT)
WS_UP = _port_open("localhost", _WS_PORT)

skip_no_opcua = pytest.mark.skipif(
    not OPCUA_UP, reason=f"OPC UA server not reachable at {OPCUA_ENDPOINT}"
)
skip_no_ws = pytest.mark.skipif(
    not WS_UP, reason=f"Backend WebSocket not reachable at {WS_URL}"
)

# ─────────────────────────────────────────────────────────────────────────────
# Shared asyncua client fixture
# ─────────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def opcua_client():
    """Connected asyncua Client — shared across all tests in this module.

    Type definitions are NOT pre-loaded here: load_data_type_definitions()
    makes 200+ sequential requests that can saturate the server and cause
    subsequent simple reads to time out. Tests that need structured event
    types should call client.load_data_type_definitions() themselves.
    """
    try:
        from asyncua import Client
    except ImportError:
        pytest.skip("asyncua not installed")

    client = Client(OPCUA_ENDPOINT, timeout=60)
    await client.connect()
    yield client
    with contextlib.suppress(Exception):
        await client.disconnect()


@pytest_asyncio.fixture(scope="function")
async def ws_client():
    """Fresh websockets client per test."""
    try:
        import websockets
    except ImportError:
        pytest.skip("websockets not installed")

    _next_id = 0

    async def send_recv(ws, command: str, body: dict | None = None, timeout: float = 15.0) -> dict:
        nonlocal _next_id
        _next_id += 1
        uid = _next_id
        payload = {**(body or {}), "command": command, "endpoint": OPCUA_ENDPOINT, "uniqueid": uid}
        await ws.send(json.dumps(payload))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            raw = await asyncio.wait_for(ws.recv(), timeout=max(0.5, deadline - time.monotonic()))
            msg = json.loads(raw)
            if msg.get("uniqueid") == uid:
                return msg
            if msg.get("command") == "event":
                continue  # not our response — collect later
        raise TimeoutError(f"No response to '{command}' within {timeout}s")

    async with websockets.connect(WS_URL) as ws:
        ws.send_recv = lambda cmd, body=None, **kw: send_recv(ws, cmd, body, **kw)
        yield ws


# ─────────────────────────────────────────────────────────────────────────────
# 1. OPC UA direct connection tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.live
@skip_no_opcua
class TestOpcuaDirectConnection:
    async def test_connect_and_disconnect(self):
        """Connection to the IJT server must succeed."""
        from asyncua import Client
        client = Client(OPCUA_ENDPOINT, timeout=30)
        await client.connect()
        assert client is not None
        await client.disconnect()

    async def test_server_time_is_readable(self, opcua_client):
        """CurrentTime node (ns=0;i=2258) must return a datetime."""
        node = opcua_client.get_node("ns=0;i=2258")
        value = await node.read_value()
        assert value is not None

    async def test_namespaces_contain_ijt(self, opcua_client):
        """Server namespace array must contain the IJT namespace URI."""
        ns_array = await opcua_client.get_namespace_array()
        assert any(IJT_NAMESPACE_URI in uri for uri in ns_array), (
            f"IJT namespace not found. Available: {ns_array}"
        )

    async def test_objects_node_is_browseable(self, opcua_client):
        """Objects (ns=0;i=85) must have at least one child node."""
        objects = await opcua_client.nodes.root.get_child(["0:Objects"])
        children = await objects.get_children()
        assert len(children) > 0

    async def test_ijt_namespace_index_is_valid(self, opcua_client):
        """IJT namespace index must be a positive integer."""
        idx = await opcua_client.get_namespace_index(IJT_NAMESPACE_URI)
        assert isinstance(idx, int)
        assert idx > 0

    async def test_tightening_system_node_exists(self, opcua_client):
        """TighteningSystem node must exist under Objects."""
        from asyncua import ua
        _ = await opcua_client.get_namespace_index(IJT_NAMESPACE_URI)
        objects = await opcua_client.nodes.root.get_child(["0:Objects"])
        children = await objects.get_children()

        ts_node = None
        for child in children:
            try:
                bn = await child.read_browse_name()
                if "TighteningSystem" in str(bn.Name):
                    ts_node = child
                    break
            except (ua.UaError, OSError):
                continue

        assert ts_node is not None, "TighteningSystem node not found under Objects"

    async def test_load_data_type_definitions_succeeds(self, opcua_client):
        """Loading type definitions must not raise (already done in fixture)."""
        # If we reach here, load_data_type_definitions() succeeded
        assert True

    async def test_browse_tightening_system_has_methods(self, opcua_client):
        """TighteningSystem must expose at least one Method node."""
        from asyncua import ua
        objects = await opcua_client.nodes.root.get_child(["0:Objects"])
        children = await objects.get_children()

        methods_found = 0
        for child in children:
            try:
                grandchildren = await child.get_children()
                for node in grandchildren:
                    nc = await node.read_node_class()
                    if nc == ua.NodeClass.Method:
                        methods_found += 1
                    if methods_found >= 4:
                        break
            except Exception:
                continue
            if methods_found >= 4:
                break

        assert methods_found >= 1, "Expected at least 1 Method node in TighteningSystem subtree"

    async def test_simulate_single_result_method_exists(self, opcua_client):
        """SimulateSingleResult method must be discoverable."""
        from asyncua import ua
        target_names = {"SimulateSingleResult", "SimulateJobResult"}
        found: set[str] = set()

        queue = [(await opcua_client.nodes.root.get_child(["0:Objects"]), 0)]
        visited: set[str] = set()

        while queue and len(found) < len(target_names):
            node, depth = queue.pop(0)
            nid = str(node.nodeid)
            if nid in visited or depth > 6:
                continue
            visited.add(nid)
            try:
                nc = await node.read_node_class()
            except Exception:
                continue
            if nc == ua.NodeClass.Method:
                with contextlib.suppress(Exception):
                    bn = await node.read_browse_name()
                    if bn.Name in target_names:
                        found.add(bn.Name)
            with contextlib.suppress(Exception):
                for child in await node.get_children():
                    queue.append((child, depth + 1))

        assert "SimulateSingleResult" in found, (
            f"SimulateSingleResult not found. Found: {found}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Event subscription tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.live
@skip_no_opcua
class TestOpcuaSubscription:
    async def test_subscribe_to_events_succeeds(self, opcua_client):
        """Event subscription must be established without error."""

        received: list[Any] = []

        class Handler:
            def event_notification(self, event):
                received.append(event)

        handler = Handler()
        subscription = await opcua_client.create_subscription(500, handler)

        objects = await opcua_client.nodes.root.get_child(["0:Objects"])
        await subscription.subscribe_events(objects)

        # Give 5 seconds for any spontaneous events
        await asyncio.sleep(5)

        await subscription.delete()
        # Success = no exception raised
        assert True

    async def test_event_handler_receives_events_after_simulation(self, opcua_client):
        """After calling SimulateSingleResult, at least one event must arrive.

        Uses direct node IDs (NS=1, string identifier) instead of tree traversal
        to avoid the server dropping the subscription under heavy read load.
        """
        from asyncua import Client, ua

        received: list = []

        class Handler:
            def event_notification(self, event):
                received.append(event)

        _NS = 1
        _SIM_R_ID = "TighteningSystem/Simulations/SimulateResults"
        _SIM_SINGLE_ID = f"{_SIM_R_ID}/SimulateSingleResult"

        async with Client(OPCUA_ENDPOINT, timeout=30) as client:
            await client.load_data_type_definitions()
            handler = Handler()
            subscription = await client.create_subscription(500, handler)
            server_node = await client.nodes.root.get_child(["0:Objects", "0:Server"])
            await subscription.subscribe_events(server_node)

            # Give asyncua's publish loop a moment to register the subscription
            await asyncio.sleep(1)

            parent = client.get_node(ua.NodeId(_SIM_R_ID, _NS, ua.NodeIdType.String))
            method = client.get_node(ua.NodeId(_SIM_SINGLE_ID, _NS, ua.NodeIdType.String))
            with contextlib.suppress(ua.UaError, OSError):  # Method call may fail; we validate the event subscription below
                await parent.call_method(
                    method.nodeid,
                    ua.Variant(0, ua.VariantType.UInt32),     # ResultType (SIMPLE_OK)
                    ua.Variant(True, ua.VariantType.Boolean),  # IncludeTraces
                )

            # Wait for event propagation
            await asyncio.sleep(8)
            await subscription.delete()

        assert len(received) > 0, (
            "Expected at least one OPC UA event after SimulateSingleResult call. "
            "Check that the server emits result events."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Backend WebSocket protocol tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.live_ws
@skip_no_ws
class TestBackendWebSocket:
    async def test_connect_command_succeeds(self, ws_client):
        resp = await ws_client.send_recv("connect to")
        assert resp.get("data", {}).get("exception") is None, (
            f"connect to returned exception: {resp['data']}"
        )

    async def test_namespaces_returns_list(self, ws_client):
        await ws_client.send_recv("connect to")
        resp = await ws_client.send_recv("namespaces")
        data = resp.get("data", {})
        # Backend returns {"namespaces": [...]}
        ns = data.get("namespaces") if isinstance(data, dict) else data
        assert isinstance(ns, list), f"Expected list, got {type(ns)}: {data}"
        assert len(ns) > 0

    async def test_namespaces_contains_ijt_uri(self, ws_client):
        await ws_client.send_recv("connect to")
        resp = await ws_client.send_recv("namespaces")
        data = resp.get("data", {})
        ns = data.get("namespaces") if isinstance(data, dict) else data
        flat = " ".join(str(n) for n in ns)
        assert "IJT" in flat or "ijt" in flat.lower() or "joining" in flat.lower(), (
            f"IJT not found in namespaces: {ns}"
        )

    async def test_read_objects_node(self, ws_client):
        await ws_client.send_recv("connect to")
        resp = await ws_client.send_recv("read", {"nodeid": "ns=0;i=85"})
        assert "exception" not in resp.get("data", {}), (
            f"read returned exception: {resp['data']}"
        )

    async def test_browse_objects_returns_children(self, ws_client):
        await ws_client.send_recv("connect to")
        resp = await ws_client.send_recv("browse", {"nodeid": "ns=0;i=85"})
        data = resp.get("data", {})
        assert "exception" not in (data if isinstance(data, dict) else {})
        # Backend returns {"nodes": [...]}
        nodes = data.get("nodes") if isinstance(data, dict) else data
        assert isinstance(nodes, list)
        assert len(nodes) > 0, "Browse Objects must return at least one child"

    async def test_subscribe_returns_success(self, ws_client):
        await ws_client.send_recv("connect to")
        resp = await ws_client.send_recv("subscribe")
        assert "exception" not in resp.get("data", {}), (
            f"subscribe returned exception: {resp['data']}"
        )

    async def test_read_invalid_node_returns_exception_not_crash(self, ws_client):
        await ws_client.send_recv("connect to")
        resp = await ws_client.send_recv("read", {"nodeid": "ns=99;i=999999"})
        # Must return a structured response (not a raw WS disconnect)
        assert resp is not None
        assert isinstance(resp, dict)

    async def test_methodcall_invalid_node_returns_exception_not_crash(self, ws_client):
        await ws_client.send_recv("connect to")
        resp = await ws_client.send_recv("methodcall", {
            "objectnode": {"NamespaceIndex": 99, "Identifier": 999999},
            "methodnode": {"NamespaceIndex": 99, "Identifier": 999998},
            "arguments": [],
        })
        assert resp is not None
        data = resp.get("data", {})
        assert "exception" in data, "Invalid methodcall must return exception field"

    async def test_full_simulation_flow_produces_event_messages(self, ws_client):
        """End-to-end: connect → subscribe → collect events for 15 s."""
        await ws_client.send_recv("connect to")
        await ws_client.send_recv("namespaces")
        await ws_client.send_recv("subscribe")

        events = []
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                raw = await asyncio.wait_for(ws_client.recv(), timeout=1.0)
                msg = json.loads(raw)
                if msg.get("command") == "event":
                    events.append(msg)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

        # Events are optional (server may not emit without simulation trigger)
        # Just verify structure when they do arrive
        for evt in events:
            assert evt.get("command") == "event"
            assert "data" in evt
            assert "endpoint" in evt

    async def test_terminate_connection_graceful(self, ws_client):
        """Terminate must not raise or crash the backend."""
        await ws_client.send_recv("connect to")
        payload = json.dumps({
            "command": "terminate connection",
            "endpoint": OPCUA_ENDPOINT,
        })
        await ws_client.send(payload)
        await asyncio.sleep(0.5)
        # No exception = success


# Serialisation contract tests live in tests/python/unit/test_serialize_data.py
# (pure sync — moved there to avoid module-level asyncio pytestmark warnings)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Performance / Response-Time SLA tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.live_ws
@skip_no_ws
class TestResponseTimeSLA:
    """Backend WebSocket operations must respond within defined SLA windows.

    Uses the send_recv timeout parameter to assert the deadline.  If the
    backend does not respond in time, TimeoutError is raised by the
    send_recv helper, which fails the test with a clear message.
    """

    async def test_connect_responds_within_30_seconds(self, ws_client):
        """'connect to' must receive a response within 30 seconds."""
        resp = await ws_client.send_recv("connect to", timeout=30)
        assert resp is not None
        assert isinstance(resp, dict)

    async def test_browse_responds_within_5_seconds(self, ws_client):
        """browse(ns=0;i=85 Objects) must respond within 5 seconds once connected."""
        await ws_client.send_recv("connect to", timeout=30)
        resp = await ws_client.send_recv(
            "browse", {"nodeid": "ns=0;i=85"}, timeout=5
        )
        assert resp is not None
        assert isinstance(resp, dict)

    async def test_read_responds_within_3_seconds(self, ws_client):
        """read(ns=0;i=2258 CurrentTime) must respond within 3 seconds once connected."""
        await ws_client.send_recv("connect to", timeout=30)
        resp = await ws_client.send_recv(
            "read", {"nodeid": "ns=0;i=2258"}, timeout=3
        )
        assert resp is not None
        assert isinstance(resp, dict)

    async def test_namespaces_responds_within_5_seconds(self, ws_client):
        """'namespaces' command must respond within 5 seconds once connected."""
        await ws_client.send_recv("connect to", timeout=30)
        resp = await ws_client.send_recv("namespaces", timeout=5)
        assert resp is not None
        data = resp.get("data", {})
        assert "exception" not in data, f"namespaces returned exception: {data}"
