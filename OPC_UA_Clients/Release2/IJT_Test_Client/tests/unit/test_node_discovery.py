"""
Unit tests for helpers/node_discovery.py

Tests the pure-Python utility functions that do not require a live OPC UA server:
  - _ref_type_nodeid: creates a namespace-0 NodeId from an integer id
  - _node_from_ref: wraps a NodeId in a Node bound to the same session
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from asyncua import ua
from asyncua.common.node import Node as UANode

from helpers import node_discovery
from helpers.namespaces import NS_IJT_BASE, NS_OPC_UA, IJTTypes, RefTypes
from helpers.node_discovery import _browse_refs, _node_from_ref, _ref_type_nodeid


class FakeNode:
    def __init__(self, refs=None, refs_by_type=None, value=None, exc=None):
        self.session = MagicMock()
        self.nodeid = ua.NodeId(id(self) % 10000, 2)
        self.refs = refs or []
        self.refs_by_type = refs_by_type or {}
        self.value = value
        self.exc = exc
        self.reference_calls = []

    async def get_references(self, **kwargs):
        self.reference_calls.append(kwargs)
        if self.exc is not None:
            raise self.exc
        ref_key = kwargs.get("refs")
        if isinstance(ref_key, ua.NodeId):
            ref_key = ref_key.Identifier
        return self.refs_by_type.get(ref_key, self.refs)

    async def read_value(self):
        if self.exc is not None:
            raise self.exc
        return self.value


class FakeClient:
    def __init__(self, objects_node, namespaces=None):
        self.objects_node = objects_node
        self.namespaces = namespaces or {
            NS_OPC_UA: 0,
            NS_IJT_BASE: 2,
        }

    async def get_namespace_index(self, uri):
        return self.namespaces[uri]

    def get_objects_node(self):
        return self.objects_node


def ref(name, ns=2, node_id=100, type_id=None):
    return SimpleNamespace(
        BrowseName=ua.QualifiedName(name, ns),
        NodeId=ua.NodeId(node_id, ns),
        TypeDefinition=ua.NodeId(type_id or 0, ns),
    )


class TestRefTypeNodeId:
    def test_returns_nodeid_with_namespace_zero(self):
        node_id = _ref_type_nodeid(33)
        assert node_id.NamespaceIndex == 0

    def test_returns_nodeid_with_correct_identifier(self):
        node_id = _ref_type_nodeid(33)
        assert node_id.Identifier == 33

    def test_different_ids_produce_different_nodeids(self):
        a = _ref_type_nodeid(33)
        b = _ref_type_nodeid(45)
        assert a.Identifier != b.Identifier

    def test_returns_ua_nodeid_type(self):
        node_id = _ref_type_nodeid(33)
        assert isinstance(node_id, ua.NodeId)

    def test_hierarchical_references_id(self):
        node_id = _ref_type_nodeid(33)
        assert node_id.Identifier == 33

    def test_organizes_id(self):
        node_id = _ref_type_nodeid(35)
        assert node_id.Identifier == 35
        assert node_id.NamespaceIndex == 0


class TestNodeFromRef:
    def test_returns_uanode_instance(self):
        mock_session = MagicMock()
        source = UANode(mock_session, ua.NodeId(1, 0))
        node_id = ua.NodeId(42, 3)
        result = _node_from_ref(source, node_id)
        assert isinstance(result, UANode)

    def test_uses_same_session_as_source(self):
        mock_session = MagicMock()
        source = UANode(mock_session, ua.NodeId(1, 0))
        result = _node_from_ref(source, ua.NodeId(99, 2))
        assert result.session is mock_session

    def test_uses_provided_nodeid(self):
        mock_session = MagicMock()
        source = UANode(mock_session, ua.NodeId(1, 0))
        target_id = ua.NodeId(77, 5)
        result = _node_from_ref(source, target_id)
        assert result.nodeid == target_id


@pytest.mark.asyncio
async def test_browse_refs_uses_hierarchical_references_and_timeout():
    node = FakeNode(refs=[ref("Child", node_id=1)])

    refs = await _browse_refs(node, timeout=0.1)

    assert refs[0].BrowseName.Name == "Child"
    assert node.reference_calls[0]["refs"] == 33
    assert node.reference_calls[0]["direction"] == ua.BrowseDirection.Forward
    assert node.reference_calls[0]["includesubtypes"] is True


@pytest.mark.asyncio
async def test_find_child_by_browse_name_matches_name_and_namespace():
    parent = FakeNode(refs=[ref("Other", ns=3, node_id=1), ref("Target", ns=4, node_id=2)])

    result = await node_discovery.find_child_by_browse_name(parent, "Target", 4)

    assert result is not None
    assert result.nodeid == ua.NodeId(2, 4)


@pytest.mark.asyncio
async def test_find_child_by_browse_name_returns_none_on_error_or_no_match():
    assert await node_discovery.find_child_by_browse_name(FakeNode(exc=RuntimeError("boom")), "X", 2) is None
    assert await node_discovery.find_child_by_browse_name(FakeNode(refs=[]), "X", 2) is None


@pytest.mark.asyncio
async def test_find_child_by_browse_name_any_skips_none_and_duplicate_namespaces(monkeypatch):
    calls = []

    async def fake_find(parent, name, ns_index, timeout=node_discovery._BROWSE_TIMEOUT):
        calls.append(ns_index)
        return "node" if ns_index == 4 else None

    monkeypatch.setattr(node_discovery, "find_child_by_browse_name", fake_find)

    result = await node_discovery.find_child_by_browse_name_any(object(), "MethodSet", [None, 3, 3, 4])

    assert result == "node"
    assert calls == [3, 4]


@pytest.mark.asyncio
async def test_browse_folder_instances_formats_browse_names_and_handles_errors():
    folder = FakeNode(refs=[ref("ToolA", ns=7, node_id=42)])

    results = await node_discovery.browse_folder_instances(folder)

    assert results[0][0] == "7:ToolA"
    assert results[0][1].nodeid == ua.NodeId(42, 7)
    assert await node_discovery.browse_folder_instances(FakeNode(exc=RuntimeError("boom"))) == []


@pytest.mark.asyncio
async def test_get_type_definition_returns_first_type_or_none():
    node = FakeNode(refs_by_type={RefTypes.HAS_TYPE_DEFINITION: [ref("Type", node_id=IJTTypes.JOINING_SYSTEM_TYPE)]})

    assert await node_discovery.get_type_definition(node) == ua.NodeId(IJTTypes.JOINING_SYSTEM_TYPE, 2)
    assert await node_discovery.get_type_definition(FakeNode(exc=RuntimeError("boom"))) is None


@pytest.mark.asyncio
async def test_interface_and_associated_asset_helpers():
    iface = ref("IJoiningSystem", node_id=1234)
    asset = ref("ToolA", node_id=22)
    node = FakeNode(
        refs_by_type={
            RefTypes.HAS_INTERFACE: [iface],
            RefTypes.ASSOCIATED_WITH: [asset],
            RefTypes.HAS_ADD_IN: [ref("AddIn", node_id=33)],
        }
    )

    assert await node_discovery.get_interface_types(node) == [ua.NodeId(1234, 2)]
    assert await node_discovery.has_interface(node, 2, 1234) is True
    assert await node_discovery.has_interface(node, 2, 9999) is False
    assert (await node_discovery.get_associated_assets(node))[0].nodeid == ua.NodeId(22, 2)
    assert (await node_discovery.get_add_in_nodes(node))[0].nodeid == ua.NodeId(33, 2)
    assert await node_discovery.get_interface_types(FakeNode(exc=RuntimeError("boom"))) == []


@pytest.mark.asyncio
async def test_get_children_by_reference_and_find_child_by_reference_type():
    parent = FakeNode(refs_by_type={RefTypes.HAS_COMPONENT: [ref("PhysicalQuantity", ns=7, node_id=44)]})

    children = await node_discovery.get_children_by_reference(parent, RefTypes.HAS_COMPONENT)
    match = await node_discovery.find_child_by_reference_type(
        parent,
        "PhysicalQuantity",
        7,
        RefTypes.HAS_COMPONENT,
    )

    assert children[0].nodeid == ua.NodeId(44, 7)
    assert match is not None
    assert match.nodeid == ua.NodeId(44, 7)
    assert await node_discovery.find_child_by_reference_type(parent, "Missing", 7, RefTypes.HAS_COMPONENT) is None
    assert await node_discovery.get_children_by_reference(FakeNode(exc=RuntimeError("boom")), 1) == []


@pytest.mark.asyncio
async def test_find_method_node_delegates_to_browse_name_lookup(monkeypatch):
    async def fake_find(parent, browse_name, ns_index):
        assert browse_name == "GetLatestResult"
        assert ns_index == 2
        return "method-node"

    monkeypatch.setattr(node_discovery, "find_child_by_browse_name", fake_find)

    assert await node_discovery.find_method_node(object(), "GetLatestResult", 2) == "method-node"


@pytest.mark.asyncio
async def test_find_method_set_tries_di_ijt_and_app_namespaces(monkeypatch):
    calls = []

    async def fake_find(parent, browse_name, ns_index):
        calls.append(ns_index)
        return "method-set" if ns_index == 8 else None

    monkeypatch.setattr(node_discovery, "find_child_by_browse_name", fake_find)

    result = await node_discovery.find_method_set(object(), ns_di=5, ns_ijt=7, ns_app=8)

    assert result == "method-set"
    assert calls == [5, 7, 8]


@pytest.mark.asyncio
async def test_find_joining_system_checks_top_level_then_one_level_deeper(monkeypatch):
    objects = FakeNode()
    top = FakeNode()
    nested = FakeNode()
    child_ref = ref("Folder", node_id=1)
    nested_ref = ref("JoiningSystem", node_id=2)

    async def fake_browse(node, timeout=node_discovery._BROWSE_TIMEOUT):
        if node is objects:
            return [child_ref]
        if node is top:
            return [nested_ref]
        return []

    def fake_node_from_ref(source, node_id):
        return top if node_id == child_ref.NodeId else nested

    async def fake_type_definition(node, ns_opc_ua=0):
        return ua.NodeId(IJTTypes.JOINING_SYSTEM_TYPE, 2) if node is nested else None

    monkeypatch.setattr(node_discovery, "_browse_refs", fake_browse)
    monkeypatch.setattr(node_discovery, "_node_from_ref", fake_node_from_ref)
    monkeypatch.setattr(node_discovery, "get_type_definition", fake_type_definition)

    result = await node_discovery.find_joining_system(FakeClient(objects))

    assert result is nested


@pytest.mark.asyncio
async def test_find_joining_system_returns_none_when_objects_browse_fails(monkeypatch):
    async def fake_browse(node, timeout=node_discovery._BROWSE_TIMEOUT):
        raise RuntimeError("browse failed")

    monkeypatch.setattr(node_discovery, "_browse_refs", fake_browse)

    assert await node_discovery.find_joining_system(FakeClient(FakeNode())) is None


@pytest.mark.asyncio
async def test_read_tool_product_instance_uri_follows_dynamic_tool_path(monkeypatch):
    js = object()
    am = object()
    assets = object()
    tools = object()
    tool = object()
    ident = object()
    pi_node = FakeNode(value="TOOL-PIU-1")
    tool_ref = ref("ToolA", node_id=101)

    async def fake_find_joining_system(client):
        return js

    async def fake_find_child(parent, name, ns_index, timeout=node_discovery._BROWSE_TIMEOUT):
        mapping = {
            (js, "AssetManagement"): am,
            (am, "Assets"): assets,
            (assets, "Tools"): tools,
            (tool, "Identification"): ident,
            (ident, "ProductInstanceUri"): pi_node if ns_index == 5 else None,
        }
        return mapping.get((parent, name))

    async def fake_browse(node, timeout=node_discovery._BROWSE_TIMEOUT):
        return [tool_ref] if node is tools else []

    def fake_node_from_ref(source, node_id):
        assert source is tools
        assert node_id == tool_ref.NodeId
        return tool

    monkeypatch.setattr(node_discovery, "find_joining_system", fake_find_joining_system)
    monkeypatch.setattr(node_discovery, "find_child_by_browse_name", fake_find_child)
    monkeypatch.setattr(node_discovery, "_browse_refs", fake_browse)
    monkeypatch.setattr(node_discovery, "_node_from_ref", fake_node_from_ref)

    result = await node_discovery.read_tool_product_instance_uri(object(), ns_ijt=7, ns_di=5)

    assert result == "TOOL-PIU-1"


@pytest.mark.asyncio
async def test_read_tool_product_instance_uri_returns_empty_on_missing_or_exception(monkeypatch):
    async def missing_joining_system(client):
        return None

    async def failing_joining_system(client):
        raise RuntimeError("not available")

    monkeypatch.setattr(node_discovery, "find_joining_system", missing_joining_system)
    assert await node_discovery.read_tool_product_instance_uri(object(), ns_ijt=7, ns_di=5) == ""

    monkeypatch.setattr(node_discovery, "find_joining_system", failing_joining_system)
    assert await node_discovery.read_tool_product_instance_uri(object(), ns_ijt=7, ns_di=5) == ""
