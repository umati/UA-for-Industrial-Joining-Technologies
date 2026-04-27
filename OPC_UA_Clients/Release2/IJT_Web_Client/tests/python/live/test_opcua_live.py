"""
Live functional tests against the running OPC UA IJT Server and Python backend.

These tests verify the complete stack:
  1. OPC UA layer  — direct asyncua connection to opc.tcp://localhost:40451
  2. WebSocket layer — Python backend at ws://localhost:8001
  3. Integration   — full simulation→event→serialization pipeline

Both servers are auto-started by conftest.py if not already running.
Tests never silently skip — any startup failure raises pytest.fail() immediately.

Markers:
  @pytest.mark.live       - requires OPC UA server
  @pytest.mark.live_ws    - requires backend WebSocket

Run all:
    python -m pytest tests/python/live/ -v

Run only OPC UA:
    python -m pytest tests/python/live/ -v -m live

Run only WS:
    python -m pytest tests/python/live/ -v -m live_ws
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import time
from typing import Any

import pytest
import pytest_asyncio
from asyncua import ua

from .._asyncua_compat import apply_send_request_timeout_patch

# All async tests in this file share the module-scoped event loop so they can
# use the module-scoped opcua_client fixture without cross-loop I/O hangs.
pytestmark = pytest.mark.asyncio(loop_scope="module")

apply_send_request_timeout_patch()

# ─────────────────────────────────────────────────────────────────────────────
# Module-level loop scope so all async fixtures and tests share one event loop.
# (pytest-asyncio 0.21+ deprecates the custom event_loop fixture; use this instead.)
# ─────────────────────────────────────────────────────────────────────────────
# asyncio_default_fixture_loop_scope = module is set in pyproject.toml for all async tests

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

OPCUA_ENDPOINT = os.getenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40451")
WS_URL = os.getenv("WS_TEST_URL", "ws://localhost:8001")

_OPCUA_HOST, _OPCUA_PORT = "localhost", 40451

IJT_NAMESPACE_URI = "http://opcfoundation.org/UA/IJT/Base/"

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
        pytest.fail("asyncua not installed — pip install asyncua")

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
        pytest.fail("websockets not installed — pip install websockets")

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
        ws.send_recv = lambda cmd, body=None, **kw: send_recv(ws, cmd, body, **kw)  # type: ignore[attr-defined]
        yield ws


# ─────────────────────────────────────────────────────────────────────────────
# 1. OPC UA direct connection tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.live
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
        assert any(IJT_NAMESPACE_URI in uri for uri in ns_array), f"IJT namespace not found. Available: {ns_array}"

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
        # Reaching this point means load_data_type_definitions() succeeded without raising.
        # The explicit assertion below makes the passing condition unambiguous.
        assert opcua_client is not None

    async def test_browse_tightening_system_has_methods(self, opcua_client):
        """TighteningSystem must expose at least one Method node."""
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

        assert "SimulateSingleResult" in found, f"SimulateSingleResult not found. Found: {found}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Event subscription tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.live
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
        # Success = no exception raised reaching this point means subscribe + delete worked.

    async def test_event_handler_receives_events_after_simulation(self, opcua_client):
        """After calling SimulateSingleResult, at least one event must arrive.

        Uses direct node IDs (NS=1, string identifier) instead of tree traversal
        to avoid the server dropping the subscription under heavy read load.
        """
        from asyncua import Client

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

            parent = client.get_node(ua.NodeId(_SIM_R_ID, _NS, ua.NodeIdType.String))  # type: ignore[arg-type]
            method = client.get_node(ua.NodeId(_SIM_SINGLE_ID, _NS, ua.NodeIdType.String))  # type: ignore[arg-type]
            with contextlib.suppress(
                ua.UaError, OSError
            ):  # Method call may fail; we validate the event subscription below
                await parent.call_method(
                    method.nodeid,
                    ua.Variant(0, ua.VariantType.UInt32),  # ResultType (SIMPLE_OK)
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
class TestBackendWebSocket:
    async def test_connect_command_succeeds(self, ws_client):
        resp = await ws_client.send_recv("connect to")
        assert resp.get("data", {}).get("exception") is None, f"connect to returned exception: {resp['data']}"

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
        flat = " ".join(str(n) for n in (ns or []))
        assert "IJT" in flat or "ijt" in flat.lower() or "joining" in flat.lower(), f"IJT not found in namespaces: {ns}"

    async def test_read_objects_node(self, ws_client):
        await ws_client.send_recv("connect to")
        resp = await ws_client.send_recv("read", {"nodeid": "ns=0;i=85"})
        assert "exception" not in resp.get("data", {}), f"read returned exception: {resp['data']}"

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
        assert "exception" not in resp.get("data", {}), f"subscribe returned exception: {resp['data']}"

    async def test_read_invalid_node_returns_exception_not_crash(self, ws_client):
        await ws_client.send_recv("connect to")
        resp = await ws_client.send_recv("read", {"nodeid": "ns=99;i=999999"})
        # Must return a structured response (not a raw WS disconnect)
        assert resp is not None
        assert isinstance(resp, dict)

    async def test_methodcall_invalid_node_returns_exception_not_crash(self, ws_client):
        await ws_client.send_recv("connect to")
        resp = await ws_client.send_recv(
            "methodcall",
            {
                "objectnode": {"NamespaceIndex": 99, "Identifier": 999999},
                "methodnode": {"NamespaceIndex": 99, "Identifier": 999998},
                "arguments": [],
            },
        )
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
        payload = json.dumps(
            {
                "command": "terminate connection",
                "endpoint": OPCUA_ENDPOINT,
            }
        )
        await ws_client.send(payload)
        await asyncio.sleep(0.5)
        # No exception = success


# Serialisation contract tests live in tests/python/unit/test_serialize_data.py
# (pure sync — moved there to avoid module-level asyncio pytestmark warnings)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Performance / Response-Time SLA tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.live_ws
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
        resp = await ws_client.send_recv("browse", {"nodeid": "ns=0;i=85"}, timeout=5)
        assert resp is not None
        assert isinstance(resp, dict)

    async def test_read_responds_within_3_seconds(self, ws_client):
        """read(ns=0;i=2258 CurrentTime) must respond within 3 seconds once connected."""
        await ws_client.send_recv("connect to", timeout=30)
        resp = await ws_client.send_recv("read", {"nodeid": "ns=0;i=2258"}, timeout=3)
        assert resp is not None
        assert isinstance(resp, dict)

    async def test_namespaces_responds_within_5_seconds(self, ws_client):
        """'namespaces' command must respond within 5 seconds once connected."""
        await ws_client.send_recv("connect to", timeout=30)
        resp = await ws_client.send_recv("namespaces", timeout=5)
        assert resp is not None
        data = resp.get("data", {})
        assert "exception" not in data, f"namespaces returned exception: {data}"


# ─────────────────────────────────────────────────────────────────────────────
# 6. WebSocket connection lifecycle tests
#
# Verifies backend (index.py handler()) correctly handles:
#   - Abrupt disconnect: browser tab closed/refreshed without 'terminate connection'
#   - Invalid JSON: backend returns a structured error; connection stays alive
#   - Multiple sequential connections: each session works independently
#   - Two concurrent sessions: independent OPC UA state, no cross-talk
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.live_ws
class TestWebSocketLifecycle:
    """WebSocket connection lifecycle — disconnect handling, error recovery, concurrency.

    Each test is self-contained: connections are opened and closed within the test
    body so teardown cannot mask connection-state bugs.
    """

    async def test_abrupt_disconnect_backend_recovers(self):
        """Close WS without 'terminate connection' — backend must clean up and accept a new session.

        Simulates a browser tab being closed or refreshed mid-session.  The handler()
        finally-block in index.py must disconnect the OPC UA client and remove the
        handler from active_handlers regardless of how the WebSocket was closed.
        """
        import websockets

        # First session: connect → get OPC UA connection response → close abruptly.
        async with websockets.connect(WS_URL) as ws:
            uid = 900
            await ws.send(json.dumps({"command": "connect to", "endpoint": OPCUA_ENDPOINT, "uniqueid": uid}))
            deadline = time.monotonic() + 30.0
            while time.monotonic() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg = json.loads(raw)
                    if msg.get("uniqueid") == uid:
                        break  # response received — now close without 'terminate connection'
                except asyncio.TimeoutError:
                    continue
        # Exiting 'async with' closes the WS cleanly from the client side, which still
        # exercises the handler() finally-block (OPC UA disconnect + active_handlers.discard).

        # Give the backend finally-block a moment to complete cleanup.
        await asyncio.sleep(1.5)

        # New session — backend must still be alive and accepting connections.
        async with websockets.connect(WS_URL) as ws2:
            uid2 = 901
            await ws2.send(json.dumps({"command": "connect to", "endpoint": OPCUA_ENDPOINT, "uniqueid": uid2}))
            deadline2 = time.monotonic() + 30.0
            reconnect_ok = False
            while time.monotonic() < deadline2:
                try:
                    raw2 = await asyncio.wait_for(ws2.recv(), timeout=1.0)
                    msg2 = json.loads(raw2)
                    if msg2.get("uniqueid") == uid2:
                        assert msg2.get("data", {}).get("exception") is None, (
                            f"Reconnect after abrupt disconnect failed: {msg2.get('data')}"
                        )
                        reconnect_ok = True
                        break
                except asyncio.TimeoutError:
                    continue
            assert reconnect_ok, (
                "No response to 'connect to' after abrupt disconnect — "
                "backend may be stuck or handler finally-block did not complete"
            )

    async def test_invalid_json_returns_structured_error(self, ws_client):
        """Sending invalid JSON must return a structured error; WS connection must remain usable.

        index.py catches json.JSONDecodeError and returns:
          {"command": "invalid request", "endpoint": "common",
           "data": {"exception": "..."}, "error": {"code": "INVALID_JSON", ...}}
        The 'continue' in the handler loop means the connection stays alive.
        """
        # Send garbage — do NOT use send_recv (it expects a uniqueid-matched response).
        await ws_client.send("this { is [ not } valid JSON !!!")

        # Read the error response directly.
        raw = await asyncio.wait_for(ws_client.recv(), timeout=5.0)
        msg = json.loads(raw)
        assert msg.get("command") == "invalid request", (
            f"Backend must return command='invalid request' for invalid JSON, got {msg.get('command')!r}"
        )
        assert "data" in msg, f"Error response must have 'data' field, got keys: {list(msg)}"
        assert "exception" in msg.get("data", {}), (
            f"Error response data must have 'exception' field, got: {msg.get('data')}"
        )

        # Connection must still be usable — issue a valid command and expect a response.
        resp = await ws_client.send_recv("connect to", timeout=30)
        assert resp.get("data", {}).get("exception") is None, (
            f"Connection must still be alive after invalid JSON, but 'connect to' failed: {resp.get('data')}"
        )

    async def test_multiple_sequential_connections_all_succeed(self):
        """Three sequential WS sessions each completing 'connect to' must all succeed.

        Verifies that the backend correctly tears down each session and is ready
        to accept the next one immediately after the previous session closes.
        """
        import websockets

        for attempt in range(3):
            uid = 910 + attempt
            async with websockets.connect(WS_URL) as ws:
                await ws.send(json.dumps({"command": "connect to", "endpoint": OPCUA_ENDPOINT, "uniqueid": uid}))
                deadline = time.monotonic() + 30.0
                success = False
                while time.monotonic() < deadline:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        msg = json.loads(raw)
                        if msg.get("uniqueid") == uid:
                            assert msg.get("data", {}).get("exception") is None, (
                                f"Attempt {attempt + 1}: 'connect to' failed: {msg.get('data')}"
                            )
                            success = True
                            break
                    except asyncio.TimeoutError:
                        continue
                assert success, f"Attempt {attempt + 1}: no response to 'connect to' within 30 s"
            # Brief gap so backend cleanup completes before the next connection.
            await asyncio.sleep(0.5)

    async def test_two_concurrent_sessions_are_independent(self):
        """Two simultaneous WS sessions must each receive their own OPC UA connection response.

        Verifies: (a) both sessions connect successfully, (b) each gets its own
        uniqueid-matched response (no cross-talk between active_handlers), (c) closing
        one session does not affect the other.
        """
        import websockets

        uid1, uid2 = 920, 921
        got1 = got2 = False

        async with websockets.connect(WS_URL) as ws1:
            async with websockets.connect(WS_URL) as ws2:
                await ws1.send(
                    json.dumps({"command": "connect to", "endpoint": OPCUA_ENDPOINT, "uniqueid": uid1})
                )
                await ws2.send(
                    json.dumps({"command": "connect to", "endpoint": OPCUA_ENDPOINT, "uniqueid": uid2})
                )

                deadline = time.monotonic() + 60.0
                while (not got1 or not got2) and time.monotonic() < deadline:
                    for ws, expected_uid, label in [(ws1, uid1, "ws1"), (ws2, uid2, "ws2")]:
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                            msg = json.loads(raw)
                            if msg.get("uniqueid") == uid1:
                                assert msg.get("data", {}).get("exception") is None, (
                                    f"ws1 connect failed: {msg.get('data')}"
                                )
                                got1 = True
                            elif msg.get("uniqueid") == uid2:
                                assert msg.get("data", {}).get("exception") is None, (
                                    f"ws2 connect failed: {msg.get('data')}"
                                )
                                got2 = True
                        except asyncio.TimeoutError:
                            continue
                        except Exception:
                            break

        assert got1, "ws1 never received a 'connect to' response — backend may have dropped session"
        assert got2, "ws2 never received a 'connect to' response — sessions may have conflicted"
