"""
Unit tests for latency calculation, event extraction,
clock skew calibration, and percentile statistics.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from asyncua import ua

from src.results import (
    INTEGRITY_INCOMPLETE,
    INTEGRITY_VALID,
    ClockCalibration,
    LatencySample,
    calibrate_clock_skew,
    compute_statistics,
    extract_sample_from_event,
)
from src.results.latency import _safe_getattr


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


def test_latency_sample_clamping_to_zero():
    # If clock skew estimation has transient uncertainty causing raw + skew < 0,
    # physical latency must clamp to 0.0 rather than reporting impossible negative durations.
    t0 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
    sample = LatencySample(
        sample_id=2,
        endpoint="opc.tcp://localhost:40001",
        end_time=t0,
        event_time=t0,
        client_received_time=t0 + timedelta(milliseconds=10),
        clock_skew_ms=-50.0,  # larger negative skew than raw 10ms
    )
    sample.calculate_metrics()
    assert sample.network_transport_time_ms == 0.0
    assert sample.total_result_transfer_time_ms == 0.0
    assert sample.raw_network_transport_time_ms == -40.0
    assert sample.raw_total_result_transfer_time_ms == -40.0
    assert sample.is_clamped_to_zero is True


def test_latency_sample_unfloatable_skew_keeps_raw_value():
    class Unfloatable:
        def __radd__(self, other):
            return self

    t0 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
    s_bad = LatencySample(
        sample_id=2,
        endpoint="opc.tcp://test:40001",
        end_time=t0,
        event_time=t0,
        client_received_time=t0,
        clock_skew_ms=Unfloatable(),  # type: ignore[arg-type]
    )
    s_bad.calculate_metrics()
    assert isinstance(s_bad.network_transport_time_ms, Unfloatable)
    assert isinstance(s_bad.total_result_transfer_time_ms, Unfloatable)


# ---------------------------------------------------------------------------
# Spec-shaped event builders (OPC 40450-1: event.Result -> ResultDataType)
# ---------------------------------------------------------------------------

T_START = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
T_END = T_START + timedelta(milliseconds=800)
T_EVENT = T_END + timedelta(milliseconds=20)
T_RECV = T_EVENT + timedelta(milliseconds=30)
EP = "opc.tcp://test:40001"


def _step(declared, *curves):
    return SimpleNamespace(
        NumberOfTracePoints=declared,
        StepTraceContent=[SimpleNamespace(Values=list(v) if v is not None else None) for v in curves],
    )


def _trace(result_id, *steps):
    return SimpleNamespace(TraceId="T-1", ResultId=result_id, StepTraces=list(steps))


def _result(result_id="R-1", *, end=T_END, start=T_START, evaluation=1, content=None):
    meta = SimpleNamespace(
        ResultId=result_id,
        CreationTime=end,
        ResultEvaluation=evaluation,
        ProcessingTimes=SimpleNamespace(StartTime=start, EndTime=end),
    )
    return SimpleNamespace(ResultMetaData=meta, ResultContent=content)


def _joining(trace):
    return SimpleNamespace(OverallResultValues=[], StepResults=[], Trace=trace)


def _event(result, time=T_EVENT):
    return SimpleNamespace(Time=time, Result=result)


def _extract(event, **kwargs):
    return extract_sample_from_event(event, T_RECV, 1, EP, **kwargs)


def test_extract_valid_event_without_trace():
    s = _extract(_event(_result()))
    assert s.integrity_status == INTEGRITY_VALID
    assert s.integrity_reason == ""
    assert s.result_id == "R-1"
    assert s.result_evaluation == "OK"
    assert s.trace_is_incomplete is None
    assert s.joining_duration_ms == 800.0
    assert s.server_processing_time_ms == 20.0
    assert s.network_transport_time_ms == 30.0
    assert s.total_result_transfer_time_ms == 50.0


def test_extract_valid_event_with_complete_trace():
    trace = _trace("R-1", _step(3, [1.0, 2.0, 3.0], [4, 5, 6]), _step(2, [0.5, 0.25]))
    s = _extract(_event(_result(content=[ua.Variant(_joining(trace))])), trace_expected=True)
    assert s.integrity_status == INTEGRITY_VALID
    assert s.trace_is_incomplete is False
    assert s.trace_curves_count == 3
    assert s.trace_declared_points == 5
    assert s.trace_decoded_points == 8
    assert s.trace_total_points == s.trace_decoded_points


@pytest.mark.parametrize(
    ("trace", "reason"),
    [
        (_trace("OTHER", _step(1, [1.0])), "does not match ResultId"),
        (_trace(None, _step(1, [1.0])), "does not match ResultId"),
        (_trace("R-1"), "has no StepTraces"),
        (_trace("R-1", None), "StepTraces[0] is empty"),
        (_trace("R-1", _step(0, [])), "NumberOfTracePoints is missing or zero"),
        (_trace("R-1", _step(None, [1.0])), "NumberOfTracePoints is missing or zero"),
        (_trace("R-1", _step(2)), "has no StepTraceContent"),
        (_trace("R-1", _step(2, None)), "Values is missing"),
        (_trace("R-1", _step(3, [1.0, 2.0])), "has 2 values, NumberOfTracePoints declares 3"),
        (_trace("R-1", _step(2, [1.0, 2.0, 3.0])), "has 3 values, NumberOfTracePoints declares 2"),
        (_trace("R-1", _step(2, [1.0, float("nan")])), "non-finite or non-numeric"),
        (_trace("R-1", _step(2, [1.0, float("inf")])), "non-finite or non-numeric"),
        (_trace("R-1", _step(2, [1.0, "x"])), "non-finite or non-numeric"),
    ],
)
def test_extract_strict_trace_rules_mark_incomplete(trace, reason):
    s = _extract(_event(_result(content=[_joining(trace)])))
    assert s.integrity_status == INTEGRITY_INCOMPLETE
    assert reason in s.integrity_reason
    assert s.trace_is_incomplete is True


def test_extract_missing_trace_when_expected_is_incomplete():
    s = _extract(_event(_result()), trace_expected=True)
    assert s.integrity_status == INTEGRITY_INCOMPLETE
    assert "No Trace in result" in s.integrity_reason
    assert s.trace_is_incomplete is True


@pytest.mark.parametrize(
    ("event", "missing"),
    [
        (_event(_result(result_id=None)), "ResultId"),
        (_event(_result(), time=None), "event Time"),
        (_event(_result(end=None)), "ProcessingTimes.EndTime"),
        (_event(SimpleNamespace(ResultContent=None)), "ResultId, ProcessingTimes.EndTime"),
        (SimpleNamespace(Time=T_EVENT), "ResultId"),
    ],
)
def test_extract_missing_required_fields_are_incomplete(event, missing):
    s = _extract(event)
    assert s.integrity_status == INTEGRITY_INCOMPLETE
    assert s.integrity_reason.startswith("Missing required field(s)")
    assert missing in s.integrity_reason


def test_extract_ignores_non_spec_flat_shape():
    # A flat Result (ResultId/ProcessingTimes directly on Result) is not OPC 40450-1 and is never VALID.
    flat = SimpleNamespace(
        ResultId="R-FLAT",
        ResultEvaluation=1,
        ProcessingTimes=SimpleNamespace(StartTime=T_START, EndTime=T_END),
    )
    s = _extract(_event(flat))
    assert s.integrity_status == INTEGRITY_INCOMPLETE
    assert s.result_id is None
    assert s.end_time is None


def test_extract_nested_batch_results_use_their_own_result_id():
    child = _result("R-CHILD", content=[_joining(_trace("R-CHILD", _step(1, [1.0])))])
    root = _result("R-BATCH", content=[ua.Variant(child), _joining(_trace("R-BATCH", _step(2, [1.0, 2.0])))])
    s = _extract(_event(root), trace_expected=True)
    assert s.integrity_status == INTEGRITY_VALID
    assert s.result_id == "R-BATCH"
    assert s.trace_curves_count == 2
    assert s.trace_decoded_points == 3

    wrong_owner = _result("R-CHILD", content=[_joining(_trace("R-BATCH", _step(1, [1.0])))])
    s_bad = _extract(_event(_result("R-BATCH", content=[wrong_owner])))
    assert s_bad.integrity_status == INTEGRITY_INCOMPLETE
    assert "'R-BATCH' does not match ResultId 'R-CHILD'" in s_bad.integrity_reason


def test_extract_walks_deep_nesting_lists_and_single_entries_without_cap():
    leaf = _joining(_trace("R-1", _step(1, [7.0])))
    node = leaf
    for _ in range(2000):  # deeper than the recursion limit; walker is iterative
        node = SimpleNamespace(ResultContent=node)
    s = _extract(_event(_result(content=[[node]])), trace_expected=True)
    assert s.integrity_status == INTEGRITY_VALID
    assert s.trace_decoded_points == 1


def test_extract_cycle_guard_terminates():
    loop = SimpleNamespace(ResultContent=None)
    loop.ResultContent = [loop]
    s = _extract(_event(_result(content=[loop])))
    assert s.integrity_status == INTEGRITY_VALID


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(1, "OK"), (2, "NOT_OK"), (99, "99"), (SimpleNamespace(name="CUSTOM"), "CUSTOM"), (None, None)],
)
def test_extract_result_evaluation_names(raw, expected):
    assert _extract(_event(_result(evaluation=raw))).result_evaluation == expected


def test_clock_warning_uses_skew_tolerance_and_rtt_without_changing_status():
    start = T_EVENT + timedelta(milliseconds=1500)
    # Event appears 1.5 s before collection start: beyond the 1000 ms default tolerance.
    s = _extract(_event(_result()), t_collection_start=start)
    assert s.clock_warning is True
    assert s.integrity_status == INTEGRITY_VALID
    # RTT/2 widens the tolerance (1000 + 1200/2 = 1600 ms > 1500 ms).
    assert _extract(_event(_result()), t_collection_start=start, clock_rtt_ms=1200.0).clock_warning is False
    # A custom tolerance.
    assert _extract(_event(_result()), t_collection_start=start, clock_tolerance_ms=2000.0).clock_warning is False
    # Skew correction: server clock 1.5 s behind client -> event really happened at collection start.
    assert _extract(_event(_result()), t_collection_start=start, clock_skew_ms=-1500.0).clock_warning is False
    # Naive datetimes are treated as UTC.
    naive = _event(_result(), time=T_EVENT.replace(tzinfo=None))
    assert _extract(naive, t_collection_start=start.replace(tzinfo=None)).clock_warning is True
    assert _extract(_event(_result())).clock_warning is False


def test_latency_sample_dict_round_trip():
    trace = _trace("R-1", _step(2, [1.0, 2.0]))
    original = _extract(_event(_result(content=[_joining(trace)])), trace_expected=True)
    data = original.to_dict()
    assert data["event_time"] == T_EVENT.isoformat()
    assert LatencySample.from_dict(data) == original


def test_latency_sample_from_dict_missing_status_is_incomplete_and_ignores_unknown_keys():
    s = LatencySample.from_dict({"sample_id": 1, "endpoint": EP, "unknown_future_field": 5})
    assert s.integrity_status == INTEGRITY_INCOMPLETE
    assert "missing" in s.integrity_reason


def test_safe_getattr_none_and_unconfigured_mock():
    assert _safe_getattr(None, "foo") is None
    assert _safe_getattr(MagicMock(), "NotConfigured", "dflt") == "dflt"


# ---------------------------------------------------------------------------
# Clock calibration
# ---------------------------------------------------------------------------


def _time_client(read_value):
    client = MagicMock()
    client.server_url = EP
    node = MagicMock()
    node.read_value = read_value
    client.get_node = MagicMock(return_value=node)
    return client


@pytest.mark.asyncio
async def test_calibrate_clock_skew_success_returns_skew_and_rtt():
    cal = await calibrate_clock_skew(_time_client(AsyncMock(return_value=datetime.now(UTC))), num_probes=2)
    assert isinstance(cal, ClockCalibration)
    assert cal.rtt_ms is not None and cal.rtt_ms >= 0.0
    assert abs(cal.skew_ms) < 1000.0


@pytest.mark.asyncio
async def test_calibrate_clock_skew_error_returns_default():
    client = MagicMock()
    client.get_node = MagicMock(side_effect=RuntimeError("Node not available"))
    assert await calibrate_clock_skew(client, num_probes=1) == ClockCalibration()


@pytest.mark.asyncio
async def test_calibrate_clock_skew_ignores_non_datetime_and_accepts_naive():
    cal = await calibrate_clock_skew(_time_client(AsyncMock(side_effect=["nope", datetime.now()])), num_probes=2)
    assert cal.rtt_ms is not None
    none = await calibrate_clock_skew(_time_client(AsyncMock(return_value="never")), num_probes=2)
    assert none == ClockCalibration(skew_ms=0.0, rtt_ms=None)


@pytest.mark.asyncio
async def test_calibrate_clock_skew_high_rtt_is_reported():
    import asyncio

    async def slow_read():
        await asyncio.sleep(0.06)
        return datetime.now(UTC)

    cal = await calibrate_clock_skew(_time_client(slow_read), num_probes=1)
    assert cal.rtt_ms is not None and cal.rtt_ms > 50.0


def _timed_sample(**kw):
    end = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    base = dict(sample_id=1, endpoint="e", end_time=end, event_time=end + timedelta(milliseconds=5))
    base.update(kw)
    s = LatencySample(**base)
    s.calculate_metrics()
    return s, end


def test_wire_timing_metrics_split_delivery_decode_and_dispatch():
    end = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    s, _ = _timed_sample(
        bytes_received_time=end + timedelta(milliseconds=30),
        decoded_time=end + timedelta(milliseconds=34),
        client_received_time=end + timedelta(milliseconds=40),
        clock_skew_ms=2.0,
    )
    assert s.timing_source == "wire"
    assert s.delivery_time_ms == pytest.approx(32.0)
    assert s.client_ready_time_ms == pytest.approx(36.0)
    assert s.client_decode_time_ms == pytest.approx(4.0)  # client-only interval: no skew
    assert s.dispatch_delay_ms == pytest.approx(6.0)
    assert s.total_result_transfer_time_ms == pytest.approx(42.0)  # unchanged legacy metric
    assert s.is_clamped_to_zero is False


def test_handler_fallback_labels_source_and_reuses_handler_time():
    end = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    s, _ = _timed_sample(client_received_time=end + timedelta(milliseconds=40), decoded_time=end)
    assert s.timing_source == "handler"
    assert s.delivery_time_ms == s.client_ready_time_ms == s.total_result_transfer_time_ms == pytest.approx(40.0)
    assert s.client_decode_time_ms is None and s.dispatch_delay_ms is None


def test_negative_skewed_delivery_is_clamped_with_raw_value_kept():
    end = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    s, _ = _timed_sample(
        bytes_received_time=end + timedelta(milliseconds=5),
        decoded_time=end + timedelta(milliseconds=6),
        client_received_time=end + timedelta(milliseconds=7),
        clock_skew_ms=-10.0,
    )
    assert s.delivery_time_ms == 0.0
    assert s.raw_delivery_time_ms == pytest.approx(-5.0)
    assert s.raw_client_ready_time_ms == pytest.approx(-4.0)
    assert s.is_clamped_to_zero is True


def test_wire_timing_fields_survive_dict_round_trip():
    end = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    s, _ = _timed_sample(
        bytes_received_time=end + timedelta(milliseconds=1), decoded_time=end + timedelta(milliseconds=2)
    )
    back = LatencySample.from_dict(s.to_dict())
    assert back.bytes_received_time == s.bytes_received_time
    assert back.decoded_time == s.decoded_time
    assert back.timing_source == "wire"
    assert back.delivery_time_ms == s.delivery_time_ms
