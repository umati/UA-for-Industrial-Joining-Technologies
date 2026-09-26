"""Unit tests for result transfer time helpers in IJT Test Client."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.performance.test_result_transfer_time import (
    _delta_ms,
    _extract_sample,
    calibrate_clock_skew,
)


def test_delta_ms_computes_duration_and_skew():
    t1 = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 25, 12, 0, 1, tzinfo=timezone.utc)

    # Without skew
    assert _delta_ms(t1, t2) == 1000.0
    # With skew (+15ms)
    assert _delta_ms(t1, t2, skew_ms=15.0) == 1015.0
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
    # The skew should be positive and close to 25ms
    assert 20.0 <= skew <= 30.0


@pytest.mark.asyncio
async def test_calibrate_clock_skew_handles_errors_gracefully():
    client = MagicMock()
    client.get_node.side_effect = RuntimeError("Node unavailable")

    skew = await calibrate_clock_skew(client, num_probes=1)
    assert skew == 0.0
