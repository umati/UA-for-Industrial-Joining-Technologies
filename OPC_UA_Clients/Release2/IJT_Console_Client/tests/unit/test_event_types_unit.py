# ruff: noqa: E402
"""Unit tests for event_types.py — get_event_types happy path and exception path."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

_ = pytest.importorskip("asyncua", reason="asyncua not installed")

from event_types import get_event_types

# ── get_event_types — happy path ──


@pytest.mark.asyncio
async def test_get_event_types_returns_three_nodes():
    """get_event_types resolves and returns 3 event type nodes."""
    mock_client = AsyncMock()
    mock_client.get_namespace_index = AsyncMock(side_effect=[1, 2])

    node1 = AsyncMock()
    node2 = AsyncMock()
    node3 = AsyncMock()
    mock_root = AsyncMock()
    mock_root.get_child = AsyncMock(side_effect=[node1, node2, node3])

    result = await get_event_types(mock_client, mock_root)

    assert result == (node1, node2, node3)


@pytest.mark.asyncio
async def test_get_event_types_calls_get_namespace_index_twice():
    """get_event_types calls get_namespace_index for both namespaces."""
    mock_client = AsyncMock()
    mock_client.get_namespace_index = AsyncMock(side_effect=[3, 4])

    mock_root = AsyncMock()
    mock_root.get_child = AsyncMock(return_value=AsyncMock())

    await get_event_types(mock_client, mock_root)

    assert mock_client.get_namespace_index.await_count == 2


@pytest.mark.asyncio
async def test_get_event_types_calls_get_child_three_times():
    """get_event_types calls root.get_child three times — once per event type."""
    mock_client = AsyncMock()
    mock_client.get_namespace_index = AsyncMock(side_effect=[1, 2])

    mock_root = AsyncMock()
    mock_root.get_child = AsyncMock(return_value=AsyncMock())

    await get_event_types(mock_client, mock_root)

    assert mock_root.get_child.await_count == 3


@pytest.mark.asyncio
async def test_get_event_types_uses_correct_namespace_indices():
    """get_event_types passes the namespace indices into the get_child paths."""
    ns_result = 5
    ns_joining = 7

    mock_client = AsyncMock()
    mock_client.get_namespace_index = AsyncMock(side_effect=[ns_result, ns_joining])

    call_args_list = []

    async def _capture_get_child(path):
        call_args_list.append(path)
        return AsyncMock()

    mock_root = AsyncMock()
    mock_root.get_child = _capture_get_child

    await get_event_types(mock_client, mock_root)

    # First call should reference ns_result
    assert any(f"{ns_result}:ResultReadyEventType" in str(p) for p in call_args_list[0])
    # Third call should reference ns_joining
    assert any(f"{ns_joining}:JoiningSystemEventType" in str(p) for p in call_args_list[2])


# ── get_event_types — exception path ──


@pytest.mark.asyncio
async def test_get_event_types_reraises_on_exception():
    """get_event_types re-raises when get_namespace_index fails."""
    mock_client = AsyncMock()
    mock_client.get_namespace_index = AsyncMock(side_effect=RuntimeError("namespace not found"))

    mock_root = AsyncMock()

    with pytest.raises(RuntimeError, match="namespace not found"):
        await get_event_types(mock_client, mock_root)


@pytest.mark.asyncio
async def test_get_event_types_reraises_on_get_child_failure():
    """get_event_types re-raises when root.get_child fails."""
    mock_client = AsyncMock()
    mock_client.get_namespace_index = AsyncMock(side_effect=[1, 2])

    mock_root = AsyncMock()
    mock_root.get_child = AsyncMock(side_effect=ConnectionError("node not found"))

    with pytest.raises(ConnectionError):
        await get_event_types(mock_client, mock_root)
