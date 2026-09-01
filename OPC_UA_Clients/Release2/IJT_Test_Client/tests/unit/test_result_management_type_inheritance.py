"""
Unit tests for the type-inheritance helper used by the ResultManagement
Results-declaration specification test.

Guards against the tautological check where a Results declaration found on an
unrelated global type node would satisfy the assertion.  No OPC UA server
required — the client and its references are mocked.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from asyncua import ua

_PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))
_spec_module: Any = importlib.import_module("specification_tests.test_result_management")
_supertype_chain = _spec_module._supertype_chain


def _nid(identifier: int, ns: int = 3) -> ua.NodeId:
    return ua.NodeId(identifier, ns)


class _FakeClient:
    """Client whose HasSubtype-inverse references form a configurable chain."""

    def __init__(self, parents: dict[tuple[int, Any], ua.NodeId], failing: set | None = None) -> None:
        self._parents = parents
        self._failing = failing or set()

    def get_node(self, nodeid: ua.NodeId):
        key = (nodeid.NamespaceIndex, nodeid.Identifier)
        node = MagicMock()
        if key in self._failing:
            node.get_references = AsyncMock(side_effect=RuntimeError("browse failed"))
            return node
        parent = self._parents.get(key)
        refs = [MagicMock(NodeId=parent)] if parent is not None else []
        node.get_references = AsyncMock(return_value=refs)
        return node


class TestSupertypeChain:
    async def test_returns_ancestors_in_order(self):
        start, mid, top = _nid(1005, 3), _nid(1000, 2), _nid(58, 0)
        client = _FakeClient(
            {
                (start.NamespaceIndex, start.Identifier): mid,
                (mid.NamespaceIndex, mid.Identifier): top,
            }
        )
        chain = await _supertype_chain(client, start)
        assert [(n.NamespaceIndex, n.Identifier) for n in chain] == [(2, 1000), (0, 58)]

    async def test_start_node_is_never_part_of_its_own_ancestry(self):
        start = _nid(1005, 3)
        client = _FakeClient({})
        assert await _supertype_chain(client, start) == []

    async def test_cycle_is_terminated(self):
        a, b = _nid(1, 3), _nid(2, 3)
        client = _FakeClient(
            {
                (a.NamespaceIndex, a.Identifier): b,
                (b.NamespaceIndex, b.Identifier): a,
            }
        )
        chain = await _supertype_chain(client, a)
        assert [(n.NamespaceIndex, n.Identifier) for n in chain] == [(3, 2)]

    async def test_browse_failure_returns_partial_chain_without_raising(self):
        start, mid = _nid(1005, 3), _nid(1000, 2)
        client = _FakeClient(
            {(start.NamespaceIndex, start.Identifier): mid},
            failing={(mid.NamespaceIndex, mid.Identifier)},
        )
        chain = await _supertype_chain(client, start)
        assert [(n.NamespaceIndex, n.Identifier) for n in chain] == [(2, 1000)]

    async def test_depth_is_bounded(self):
        # A server that reports an endless ancestry must not hang the test run.
        nodes = [_nid(i, 3) for i in range(50)]
        parents = {(n.NamespaceIndex, n.Identifier): nodes[i + 1] for i, n in enumerate(nodes[:-1])}
        client = _FakeClient(parents)
        chain = await _supertype_chain(client, nodes[0], max_depth=4)
        assert len(chain) == 4

    async def test_unrelated_type_is_not_reachable(self):
        """The core regression: an unrelated global type is never in the ancestry,
        so a Results declaration found only there cannot satisfy the test."""
        start, real_parent = _nid(1005, 3), _nid(1000, 2)
        unrelated = _nid(9999, 2)
        client = _FakeClient({(start.NamespaceIndex, start.Identifier): real_parent})
        chain = await _supertype_chain(client, start)
        keys = {(n.NamespaceIndex, n.Identifier) for n in chain}
        assert (real_parent.NamespaceIndex, real_parent.Identifier) in keys
        assert (unrelated.NamespaceIndex, unrelated.Identifier) not in keys


if __name__ == "__main__":  # pragma: no cover - convenience entry point
    pytest.main([__file__])
