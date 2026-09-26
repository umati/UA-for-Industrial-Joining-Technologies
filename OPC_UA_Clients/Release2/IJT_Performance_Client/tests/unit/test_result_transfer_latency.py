"""
Unit tests for latency calculation, event extraction,
clock skew calibration, and percentile statistics.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from ijt_performance_client.result_transfer_latency import (
    LatencySample,
    calibrate_clock_skew,
    compute_statistics,
    extract_sample_from_event,
)


def test_latency_sample_calculation():
    t0 = datetime(2026, 9, 25, 12, 0, 0, tzinfo=UTC)
    t_end = t0 + timedelta(milliseconds=800)  # 800ms joining operation
    t_create = t_end + timedelta(milliseconds=25)  # 25ms controller result collation
    t_event = t_create + timedelta(milliseconds=5)  # 5ms event creation (total server = 30ms)
    t_client = t_event + timedelta(milliseconds=15)  # 15ms network transport

    sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://localhost:40451",
        start_time=t0,
        end_time=t_end,
        creation_time=t_create,
        event_time=t_event,
        client_received_time=t_client,
        clock_skew_ms=0.0,
    )
    sample.calculate_metrics()

    assert sample.joining_duration_ms == 800.0
    assert sample.server_processing_time_ms == 30.0  # t_event - t_end
    assert sample.network_transport_time_ms == 15.0  # t_client - t_event
    assert sample.total_result_transfer_time_ms == 45.0  # 30 + 15


def test_latency_sample_with_clock_skew():
    t0 = datetime(2026, 9, 25, 12, 0, 0, tzinfo=UTC)
    t_end = t0 + timedelta(milliseconds=500)
    t_event = t_end + timedelta(milliseconds=10)
    # Server clock was 50ms ahead of client clock
    skew = 50.0
    t_client = t_event + timedelta(milliseconds=20) - timedelta(milliseconds=50)

    sample = LatencySample(
        sample_id=2,
        endpoint="opc.tcp://10.0.0.1:40451",
        start_time=t0,
        end_time=t_end,
        event_time=t_event,
        client_received_time=t_client,
        clock_skew_ms=skew,
    )
    sample.calculate_metrics()

    # Without skew correction, raw transport would be -30ms. With skew correction, it is 20ms.
    assert round(sample.network_transport_time_ms, 1) == 20.0
    assert round(sample.total_result_transfer_time_ms, 1) == 30.0


def test_extract_sample_from_event():
    t_event = datetime(2026, 9, 25, 12, 0, 1, tzinfo=UTC)
    t_start = datetime(2026, 9, 25, 12, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 25, 12, 0, 0, 800000, tzinfo=UTC)
    t_recv = datetime(2026, 9, 25, 12, 0, 1, 50000, tzinfo=UTC)

    # Mock event object with Result payload
    mock_result = MagicMock()
    mock_result.ResultMetaData = MagicMock()
    mock_result.ResultMetaData.CreationTime = t_end
    mock_proc = MagicMock()
    mock_proc.StartTime = t_start
    mock_proc.EndTime = t_end
    mock_result.ResultMetaData.ProcessingTimes = mock_proc
    mock_result.ResultMetaData.ToolId = "TOOL-01"

    mock_event = MagicMock()
    mock_event.Time = t_event
    mock_event.Result = mock_result

    sample = extract_sample_from_event(
        event=mock_event,
        client_received=t_recv,
        sample_id=42,
        endpoint="opc.tcp://server:40451",
        clock_skew_ms=0.0,
    )

    assert sample.sample_id == 42
    assert sample.total_result_transfer_time_ms is not None
    assert sample.total_result_transfer_time_ms > 0


@pytest.mark.asyncio
async def test_calibrate_clock_skew_success():
    mock_client = MagicMock()
    mock_client.server_url = "opc.tcp://localhost:40451"
    mock_time_node = MagicMock()
    # Return current datetime in UTC
    mock_time_node.read_value = AsyncMock(return_value=datetime.now(UTC))
    mock_client.get_node = MagicMock(return_value=mock_time_node)

    skew = await calibrate_clock_skew(mock_client, num_probes=2)
    assert isinstance(skew, float)


@pytest.mark.asyncio
async def test_calibrate_clock_skew_error_returns_zero():
    mock_client = MagicMock()
    mock_client.get_node = MagicMock(side_effect=RuntimeError("Node not available"))

    skew = await calibrate_clock_skew(mock_client, num_probes=1)
    assert skew == 0.0


def test_compute_statistics():
    empty_stats = compute_statistics([])
    assert empty_stats["count"] == 0
    assert empty_stats["mean"] == 0.0

    vals = [10.0, 20.0, 30.0, 40.0, 50.0]
    st = compute_statistics(vals)
    assert st["count"] == 5
    assert st["min"] == 10.0
    assert st["max"] == 50.0
    assert st["mean"] == 30.0
    assert st["median"] == 30.0
    assert st["p90"] == 46.0
    assert st["stdev"] > 0.0


def test_extract_sample_processing_times_on_result():
    t_start = datetime(2026, 9, 25, 12, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 25, 12, 0, 0, 750000, tzinfo=UTC)
    t_event = datetime(2026, 9, 25, 12, 0, 1, tzinfo=UTC)

    mock_result = MagicMock()
    mock_result.ResultMetaData = None
    mock_proc = MagicMock()
    mock_proc.StartTime = t_start
    mock_proc.EndTime = t_end
    mock_result.ProcessingTimes = mock_proc

    mock_event = MagicMock()
    mock_event.Time = t_event
    mock_event.Result = mock_result

    sample = extract_sample_from_event(
        event=mock_event,
        client_received=datetime.now(UTC),
        sample_id=10,
        endpoint="opc.tcp://server:40451",
    )
    assert sample.start_time == t_start
    assert sample.end_time == t_end
    assert sample.joining_duration_ms == 750.0


@pytest.mark.asyncio
async def test_calibrate_clock_skew_edge_cases():
    mock_client = MagicMock()
    mock_client.server_url = "opc.tcp://localhost:40451"
    mock_time_node = MagicMock()

    # 1. Non-datetime response followed by naive datetime response
    naive_dt = datetime.now()  # no tzinfo
    mock_time_node.read_value = AsyncMock(side_effect=["not-a-datetime", naive_dt])
    mock_client.get_node = MagicMock(return_value=mock_time_node)

    skew = await calibrate_clock_skew(mock_client, num_probes=2)
    assert isinstance(skew, float)

    # 2. Only non-datetime responses (best_rtt remains inf -> returns 0.0)
    mock_time_node.read_value = AsyncMock(return_value="never-a-datetime")
    skew_zero = await calibrate_clock_skew(mock_client, num_probes=2)
    assert skew_zero == 0.0


@pytest.mark.asyncio
async def test_calibrate_clock_skew_high_rtt(monkeypatch):
    import asyncio

    mock_client = MagicMock()
    mock_client.server_url = "opc.tcp://slow-server:40451"
    mock_time_node = MagicMock()

    async def slow_read():
        await asyncio.sleep(0.06)  # > 50ms
        return datetime.now(UTC)

    mock_time_node.read_value = slow_read
    mock_client.get_node = MagicMock(return_value=mock_time_node)

    skew = await calibrate_clock_skew(mock_client, num_probes=1)
    assert isinstance(skew, float)


def test_extract_sample_event_without_result_attribute():
    mock_event = MagicMock(spec=["Time"])
    mock_event.Time = datetime.now(UTC)

    sample = extract_sample_from_event(
        event=mock_event,
        client_received=datetime.now(UTC),
        sample_id=99,
        endpoint="opc.tcp://test:40451",
    )
    assert sample.sample_id == 99


def test_compute_statistics_single_element():
    st = compute_statistics([42.0])
    assert st["count"] == 1
    assert st["p90"] == 42.0
    assert st["p95"] == 42.0
    assert st["p99"] == 42.0


def test_latency_sample_fallback_server_processing_without_event_time():
    t_end = datetime(2026, 9, 25, 12, 0, 0, tzinfo=UTC)
    t_create = t_end + timedelta(milliseconds=45)
    sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://test:40451",
        end_time=t_end,
        creation_time=t_create,
        event_time=None,
    )
    sample.calculate_metrics()
    assert sample.server_processing_time_ms == 45.0
