"""
Unit tests for helpers/node_discovery.py

Tests the pure-Python utility functions that do not require a live OPC UA server:
  - _ref_type_nodeid: creates a namespace-0 NodeId from an integer id
  - _node_from_ref: wraps a NodeId in a Node bound to the same session
"""

from unittest.mock import MagicMock

from asyncua import ua
from asyncua.common.node import Node as UANode

from helpers.node_discovery import _node_from_ref, _ref_type_nodeid


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
