"""Unit coverage for live result-transfer discovery helpers."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.live.test_result_transfer_time import (
    _delta_ms,
    _extract_sample,
    _find_child,
    _ns_index,
    calibrate_clock_skew,
)


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


def test_delta_ms_computes_duration_and_skew():
    t1 = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 25, 12, 0, 1, tzinfo=timezone.utc)

    # Without skew
    assert _delta_ms(t1, t2) == 1000.0
    # With skew (+20ms)
    assert _delta_ms(t1, t2, skew_ms=20.0) == 1020.0
    # With None input
    assert _delta_ms(None, t2) is None
    assert _delta_ms(t1, None) is None


def test_extract_sample_applies_skew_to_cross_clock_metrics():
    t_start = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 9, 25, 12, 0, 0, 500000, tzinfo=timezone.utc)  # +500ms
    t_event = datetime(2026, 9, 25, 12, 0, 0, 520000, tzinfo=timezone.utc)  # +20ms on server
    t_client = datetime(2026, 9, 25, 12, 0, 0, 550000, tzinfo=timezone.utc)  # +30ms raw wire

    pt = SimpleNamespace(StartTime=t_start, EndTime=t_end, AcquisitionDuration=5.0, ProcessingDuration=15.0)
    meta = SimpleNamespace(ProcessingTimes=pt)
    result = SimpleNamespace(ResultMetaData=meta)
    event = SimpleNamespace(Result=result, Time=t_event)

    sample = _extract_sample(event, t_client, index=1, skew_ms=10.0)

    # Server-internal metrics must NOT have skew applied
    assert sample["joining_duration_ms"] == 500.0
    assert sample["server_processing_time_ms"] == 20.0

    # Cross-clock metrics MUST have skew applied (+10ms)
    assert sample["network_transport_time_ms"] == 40.0  # 30ms raw + 10ms skew
    assert sample["total_result_transfer_time_ms"] == 60.0  # 50ms raw + 10ms skew
    assert sample["skew_ms"] == 10.0


@pytest.mark.asyncio
async def test_calibrate_clock_skew_calculates_skew_via_cristian():
    client = MagicMock()
    server_node = AsyncMock()

    # Simulate server clock ahead by 25ms
    now_utc = datetime.now(timezone.utc)
    server_time = now_utc + timedelta(milliseconds=25)
    server_node.read_value = AsyncMock(return_value=server_time)
    client.get_node.return_value = server_node

    skew = await calibrate_clock_skew(client, num_probes=2)
    # The skew should be positive and close to 25ms (within reasonable RTT uncertainty)
    assert 20.0 <= skew <= 30.0


@pytest.mark.asyncio
async def test_calibrate_clock_skew_handles_errors_gracefully():
    client = MagicMock()
    client.get_node.side_effect = RuntimeError("Node unavailable")

    skew = await calibrate_clock_skew(client, num_probes=1)
    assert skew == 0.0
