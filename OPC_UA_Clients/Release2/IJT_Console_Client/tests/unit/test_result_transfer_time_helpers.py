"""Unit coverage for live result-transfer discovery helpers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.live.test_result_transfer_time import _find_child, _ns_index


class _FakeBrowseNode:
    def __init__(self, name: str, *, children=None, ns_idx: int = 2):
        self.name = name
        self.children = children or []
        self.ns_idx = ns_idx

    async def get_child(self, path: str):
        ns, child_name = path.split(":", 1)
        for child in self.children:
            if child.name == child_name and child.ns_idx == int(ns):
                return child
        raise RuntimeError(f"{child_name} not found")

    async def get_children(self):
        return self.children

    async def read_browse_name(self):
        return SimpleNamespace(Name=self.name, NamespaceIndex=self.ns_idx)


@pytest.mark.asyncio
async def test_ns_index_reads_namespace_array_when_lookup_fails():
    namespace_array = [
        "http://opcfoundation.org/UA/",
        "urn:example:app",
    ]
    namespace_node = AsyncMock()
    namespace_node.read_value = AsyncMock(return_value=namespace_array)
    client = MagicMock()
    client.get_namespace_index = AsyncMock(side_effect=RuntimeError("lookup not ready"))
    client.get_node.return_value = namespace_node

    result = await _ns_index(client, "urn:example:app")

    assert result == 1


@pytest.mark.asyncio
async def test_find_child_uses_name_fallback_when_namespace_unknown():
    child = _FakeBrowseNode("SimulateResults")
    parent = _FakeBrowseNode("Simulations", children=[child])

    result = await _find_child(parent, None, "SimulateResults")

    assert result is child


@pytest.mark.asyncio
async def test_find_child_prefers_matching_namespace_when_available():
    fallback = _FakeBrowseNode("SimulateResults", ns_idx=3)
    expected = _FakeBrowseNode("SimulateResults", ns_idx=2)
    parent = _FakeBrowseNode("Simulations", children=[fallback, expected])

    result = await _find_child(parent, 2, "SimulateResults")

    assert result is expected


@pytest.mark.asyncio
async def test_find_child_falls_back_to_name_when_browse_namespace_differs_from_node_namespace():
    child = _FakeBrowseNode("AssetManagement", ns_idx=7)
    parent = _FakeBrowseNode("TighteningSystem", children=[child], ns_idx=1)

    result = await _find_child(parent, 1, "AssetManagement")

    assert result is child
