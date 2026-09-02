from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from asyncua import ua

from helpers.connection_security import ConnectionSecurity
from helpers.model_inventory import (
    _namespace_uri,
    _server_nodes,
    build_model_inventory,
    write_model_inventory,
)


def test_model_inventory_public_api_exists() -> None:
    """build_model_inventory and write_model_inventory are importable."""
    assert callable(build_model_inventory)
    assert callable(write_model_inventory)


def test_namespace_uri_bounds():
    ns = ["http://opcfoundation.org/UA/", "http://example.com/ijt"]
    assert _namespace_uri(ns, 0) == "http://opcfoundation.org/UA/"
    assert _namespace_uri(ns, 1) == "http://example.com/ijt"
    assert _namespace_uri(ns, -1) == ""
    assert _namespace_uri(ns, 5) == ""


@pytest.mark.asyncio
async def test_server_nodes_joining_system_not_found(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr("helpers.model_inventory.find_joining_system", AsyncMock(return_value=None))
    with pytest.raises(RuntimeError, match="JoiningSystem node was not found"):
        await _server_nodes(client, timeout=1.0, max_nodes=100)


@pytest.mark.asyncio
async def test_server_nodes_exceeds_max_nodes(monkeypatch):
    client = MagicMock()
    client.get_namespace_array = AsyncMock(return_value=["http://opcfoundation.org/UA/"])
    joining_system = MagicMock()
    joining_system.nodeid = ua.NodeId(1000, 1)
    joining_system.read_browse_name = AsyncMock(return_value=SimpleNamespace(Name="JoiningSystem"))
    monkeypatch.setattr("helpers.model_inventory.find_joining_system", AsyncMock(return_value=joining_system))
    with pytest.raises(RuntimeError, match="Address-space inventory exceeded the safety limit"):
        await _server_nodes(client, timeout=1.0, max_nodes=0)


@pytest.mark.asyncio
async def test_server_nodes_traversal_and_warning(monkeypatch):
    client = MagicMock()
    client.get_namespace_array = AsyncMock(return_value=["http://opcfoundation.org/UA/", "http://test.org/"])
    joining_system = MagicMock()
    joining_system.nodeid = ua.NodeId(1000, 1)
    joining_system.session = client
    joining_system.read_browse_name = AsyncMock(return_value=SimpleNamespace(Name="JoiningSystem"))

    ref1 = SimpleNamespace(
        BrowseName=SimpleNamespace(Name="Child1", NamespaceIndex=1),
        NodeId=ua.NodeId(1001, 1),
        NodeClass=ua.NodeClass.Object,
        TypeDefinition=ua.NodeId(2001, 1),
    )

    # Joining system returns ref1; Child1 throws when getting references (producing a warning)
    async def fake_get_refs(*args, **kwargs):
        return [ref1]

    joining_system.get_references = AsyncMock(side_effect=fake_get_refs)
    monkeypatch.setattr("helpers.model_inventory.find_joining_system", AsyncMock(return_value=joining_system))

    # Child node get_references throws
    def fake_node_init(session, nodeid):
        m = MagicMock()
        m.nodeid = nodeid
        m.session = session
        m.get_references = AsyncMock(side_effect=RuntimeError("Browse failure"))
        return m

    monkeypatch.setattr("helpers.model_inventory.Node", fake_node_init)

    nodes, warnings = await _server_nodes(client, timeout=1.0, max_nodes=100)
    assert len(nodes) == 1
    assert nodes[0]["browse_name"]["name"] == "Child1"
    assert nodes[0]["browse_name"]["namespace_uri"] == "http://test.org/"
    assert len(warnings) == 1
    assert "Browse failure" in warnings[0]


@pytest.mark.asyncio
async def test_build_model_inventory_flow(monkeypatch):
    fake_client = MagicMock()
    fake_client.connect = AsyncMock()
    fake_client.disconnect = AsyncMock()

    monkeypatch.setattr("helpers.model_inventory.Client", lambda url, timeout: fake_client)
    monkeypatch.setattr("helpers.model_inventory.apply_connection_security", AsyncMock())
    monkeypatch.setattr(
        "helpers.model_inventory._server_nodes",
        AsyncMock(return_value=([{"path": "JoiningSystem/Child"}], [])),
    )

    sec = ConnectionSecurity()
    inv = await build_model_inventory("opc.tcp://localhost:40451", timeout=1.0, security=sec)
    assert inv["complete"] is True
    assert inv["server_inventory"]["node_count"] == 1
    fake_client.connect.assert_called_once()
    fake_client.disconnect.assert_called_once()


def test_write_model_inventory(tmp_path, monkeypatch):
    fake_inv = {
        "schema_version": 1,
        "endpoint": "opc.tcp://localhost:40451",
        "complete": True,
        "server_inventory": {"node_count": 0},
    }
    monkeypatch.setattr(
        "helpers.model_inventory.build_model_inventory",
        AsyncMock(return_value=fake_inv),
    )
    out_file = tmp_path / "subdir" / "inv.json"
    result = write_model_inventory("opc.tcp://localhost:40451", out_file)
    assert result == fake_inv
    assert out_file.is_file()


@pytest.mark.asyncio
async def test_server_nodes_skips_visited(monkeypatch):
    client = MagicMock()
    client.get_namespace_array = AsyncMock(return_value=["http://opcfoundation.org/UA/"])
    joining_system = MagicMock()
    joining_system.nodeid = ua.NodeId(1000, 1)
    joining_system.session = client
    joining_system.read_browse_name = AsyncMock(return_value=SimpleNamespace(Name="JoiningSystem"))

    ref_loop = SimpleNamespace(
        BrowseName=SimpleNamespace(Name="Loop", NamespaceIndex=0),
        NodeId=ua.NodeId(1000, 1),
        NodeClass=ua.NodeClass.Object,
        TypeDefinition=None,
    )
    joining_system.get_references = AsyncMock(return_value=[ref_loop])
    monkeypatch.setattr("helpers.model_inventory.find_joining_system", AsyncMock(return_value=joining_system))
    nodes, warnings = await _server_nodes(client, timeout=1.0, max_nodes=100)
    assert len(nodes) == 1
    assert len(warnings) == 0
