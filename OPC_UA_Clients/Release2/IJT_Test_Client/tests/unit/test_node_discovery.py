"""
Unit tests for helpers/node_discovery.py

Tests the pure-Python utility functions that do not require a live OPC UA server:
  - _ref_type_nodeid: creates a namespace-0 NodeId from an integer id
"""

from asyncua import ua

from helpers.node_discovery import _ref_type_nodeid


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
