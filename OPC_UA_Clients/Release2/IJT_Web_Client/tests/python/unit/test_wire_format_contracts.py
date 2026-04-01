"""Wire-format contract tests.

These tests freeze the exact JSON key names that the Python backend reads from
every WebSocket command payload.  If a key is renamed on either side
(e.g. ``objectnode`` → ``object_node``), these tests fail immediately rather
than silently at runtime.

Critical regression: connection.py was briefly changed to read
``data.get("object_node")`` (snake_case) instead of the correct
``data.get("objectnode")`` (camelCase-ish, matching the JS front-end).  The
tests below ensure that regression can never be silently reintroduced.
"""

from __future__ import annotations

import pytest

pytest.importorskip("asyncua", reason="asyncua not installed")

from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402

from python.connection import Connection  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_connection(server_url: str = "opc.tcp://localhost:40451") -> Connection:
    ws = AsyncMock()
    return Connection(server_url, ws)


# ===========================================================================
# 1. methodcall — objectnode / methodnode key contract
# ===========================================================================


class TestMethodcallWireKeys:
    """The wire format uses 'objectnode' and 'methodnode' (no underscores)."""

    @pytest.mark.asyncio
    async def test_correct_key_objectnode_passes_none_guard(self):
        """'objectnode' must NOT trigger the Missing error.

        The error should be 'not connected', proving the keys were accepted
        and the code progressed past the None guard.
        """
        conn = _make_connection()
        with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=False)):
            result = await conn.methodcall({
                "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                "arguments": [],
            })
        assert "exception" in result
        assert "Missing" not in result["exception"], (
            f"Expected 'not connected' error, got: {result['exception']}"
        )

    @pytest.mark.asyncio
    async def test_wrong_key_object_node_underscore_triggers_missing_error(self):
        """'object_node' (snake_case) is the WRONG key — must return 'Missing' error."""
        conn = _make_connection()
        result = await conn.methodcall({
            "object_node": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
            "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
            "arguments": [],
        })
        assert "exception" in result
        assert "Missing" in result["exception"]
        assert "objectnode" in result["exception"]

    @pytest.mark.asyncio
    async def test_wrong_key_method_node_underscore_triggers_missing_error(self):
        """'method_node' (snake_case) is the WRONG key — must return 'Missing' error."""
        conn = _make_connection()
        result = await conn.methodcall({
            "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
            "method_node": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
            "arguments": [],
        })
        assert "exception" in result
        assert "Missing" in result["exception"]
        assert "methodnode" in result["exception"]

    @pytest.mark.asyncio
    async def test_both_snake_case_keys_trigger_missing_not_nonetype_crash(self):
        """Both wrong snake_case keys → 'Missing' error, not NoneType AttributeError crash.

        This is the exact regression test for the snake_case rename bug:
        object_node / method_node → object_node.get("NamespaceIndex") crashed with
        AttributeError: 'NoneType' object has no attribute 'get'.
        """
        conn = _make_connection()
        result = await conn.methodcall({
            "object_node": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
            "method_node": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
            "arguments": [],
        })
        assert "exception" in result
        assert "Missing" in result["exception"]
        assert "NoneType" not in result["exception"], (
            "NoneType crash detected — the None guard must fire BEFORE any attribute access"
        )

    @pytest.mark.asyncio
    async def test_explicit_none_objectnode_returns_clear_missing_error(self):
        """Explicit None for objectnode → 'Missing' error, not AttributeError crash."""
        conn = _make_connection()
        result = await conn.methodcall({
            "objectnode": None,
            "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
            "arguments": [],
        })
        assert "exception" in result
        assert "Missing" in result["exception"]
        assert "NoneType" not in result["exception"]

    @pytest.mark.asyncio
    async def test_explicit_none_methodnode_returns_clear_missing_error(self):
        """Explicit None for methodnode → 'Missing' error, not AttributeError crash."""
        conn = _make_connection()
        result = await conn.methodcall({
            "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
            "methodnode": None,
            "arguments": [],
        })
        assert "exception" in result
        assert "Missing" in result["exception"]
        assert "NoneType" not in result["exception"]

    @pytest.mark.asyncio
    async def test_empty_payload_returns_missing_error(self):
        """Completely empty payload → 'Missing objectnode or methodnode' error."""
        conn = _make_connection()
        result = await conn.methodcall({})
        assert "exception" in result
        assert "Missing" in result["exception"]

    @pytest.mark.asyncio
    async def test_arguments_key_defaults_to_empty_list(self):
        """'arguments' key is optional; missing it must not crash the None guard path."""
        conn = _make_connection()
        # objectnode/methodnode present but connection not open
        with patch.object(conn, "is_connection_open", new=AsyncMock(return_value=False)):
            result = await conn.methodcall({
                "objectnode": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
                "methodnode": {"NamespaceIndex": 1, "Identifier": "SimulateSingleResult"},
                # "arguments" deliberately omitted
            })
        assert "exception" in result
        assert "Missing" not in result["exception"]  # keys were found


# ===========================================================================
# 2. browse — 'nodeid' key contract
# ===========================================================================


class TestBrowseNodeidKey:
    """browse() reads the 'nodeid' key (no underscore, no separator)."""

    @pytest.mark.asyncio
    async def test_browse_passes_nodeid_value_to_get_node(self):
        """'nodeid' key value is forwarded verbatim to client.get_node()."""
        conn = _make_connection()
        mock_node = MagicMock()
        mock_node.get_references = AsyncMock(return_value=[])
        conn.client = MagicMock()
        conn.client.get_node = MagicMock(return_value=mock_node)

        result = await conn.browse({"nodeid": "ns=0;i=85"})

        assert "exception" not in result, f"Unexpected exception: {result.get('exception')}"
        conn.client.get_node.assert_called_once_with("ns=0;i=85")

    @pytest.mark.asyncio
    async def test_browse_with_node_id_snake_case_passes_none_to_get_node(self):
        """Wrong key 'node_id' is ignored; get_node(None) raises → exception dict."""
        conn = _make_connection()
        conn.client = MagicMock()
        conn.client.get_node = MagicMock(
            side_effect=Exception("Cannot get node for id None")
        )

        result = await conn.browse({"node_id": "ns=0;i=85"})
        assert "exception" in result


# ===========================================================================
# 3. read — 'nodeid' key contract
# ===========================================================================


class TestReadNodeidKey:
    """read() reads the 'nodeid' key."""

    @pytest.mark.asyncio
    async def test_read_uses_nodeid_key_not_node_id(self):
        """read() must extract 'nodeid', not 'node_id', from payload."""
        conn = _make_connection()
        captured: list[str] = []

        def fake_get_node(nid):
            captured.append(nid)
            raise Exception("Stop here — node id recorded")

        conn.client = MagicMock()
        conn.client.get_node = fake_get_node

        await conn.read({"nodeid": "ns=1;s=TestNode", "node_id": "WRONG_KEY"})

        assert len(captured) == 1
        assert captured[0] == "ns=1;s=TestNode", (
            f"Expected get_node('ns=1;s=TestNode'), got get_node({captured[0]!r})"
        )

    @pytest.mark.asyncio
    async def test_read_missing_nodeid_returns_exception_not_crash(self):
        """read() with no 'nodeid' → get_node(None) raises → exception dict returned."""
        conn = _make_connection()
        conn.client = MagicMock()
        conn.client.get_node = MagicMock(
            side_effect=Exception("Invalid node id: None")
        )

        result = await conn.read({})
        assert "exception" in result


# ===========================================================================
# 4. pathtoid — 'nodeid' + 'path' key contract
# ===========================================================================


class TestPathtoidKeyNames:
    """pathtoid() reads 'nodeid' and 'path' from payload."""

    @pytest.mark.asyncio
    async def test_pathtoid_uses_nodeid_key(self):
        """pathtoid() must call get_node with the value of 'nodeid', not 'node_id'."""
        conn = _make_connection()
        captured: list[str] = []

        def fake_get_node(nid):
            captured.append(nid)
            raise Exception("Stop here")

        conn.client = MagicMock()
        conn.client.get_node = fake_get_node

        await conn.pathtoid({
            "nodeid": {"NamespaceIndex": 1, "Identifier": "TighteningSystem"},
            "path": "[]",
        })

        assert len(captured) == 1
        assert captured[0] == "ns=1;s=TighteningSystem"
