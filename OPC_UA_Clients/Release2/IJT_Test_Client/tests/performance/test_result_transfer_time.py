"""
Single-Result Transfer Time — end-to-end latency benchmark.

Measures how long it takes for a completed joining result to travel from the
controller (ProcessingTimes.EndTime) through the OPC UA server and across the
network to the client subscription callback.

Five timestamps / durations per sample:
  StartTime           ProcessingTimes.StartTime          (controller clock)
  EndTime             ProcessingTimes.EndTime            (controller clock)
  AcquisitionDuration ProcessingTimes.AcquisitionDuration (reported by server, ms)
  ProcessingDuration  ProcessingTimes.ProcessingDuration  (reported by server, ms)
  EventTime           event.Time (ResultReadyEvent generated on the server)
  ClientReceived      datetime.now(UTC) at subscription callback

Measured intervals (all in ms):
  Joining duration            EndTime − StartTime         informational (not gated)
  Result acquisition          AcquisitionDuration         informational sub-component
  Result processing           ProcessingDuration          informational sub-component
  Time on server              EventTime − EndTime         wall-clock on the server
  OPC UA + Wire               ClientReceived − EventTime  network + transport
  TOTAL — Result Transfer     ClientReceived − EndTime    ← primary gated metric

Test parameters:
  _SAMPLE_COUNT consecutive MULTI_STEP_OK_RESULT results with full trace data.
  _INTER_RESULT_DELAY_S pause between triggers to simulate realistic tool-press cadence.
  Statistics computed over all samples: min / mean / median / p90 / max / stdev.

Prerequisite:
  Client and server clocks must be synchronised to millisecond accuracy and share
  the same timezone.  On a single host (simulator) this is automatically satisfied.

Performance target (aggregate over all samples):
  mean(total_transfer_ms)  <  _THRESHOLD_MEAN_MS
  p90(total_transfer_ms)   <  _THRESHOLD_P90_MS
"""

import asyncio
import logging
import math
import statistics
from datetime import datetime, timezone

import pytest
from asyncua import ua

from helpers.namespaces import (
    NS_IJT_BASE,
    IJTTypes,
    ResultType,
)

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.performance]

_SAMPLE_COUNT = 20
_INTER_RESULT_DELAY_S = 1.0  # realistic gap between tool trigger presses
_COLLECT_TIMEOUT_S = 30.0  # max time to wait for each ResultReadyEvent
_THRESHOLD_MEAN_MS = 500.0  # mean total transfer time must be < this
_THRESHOLD_P90_MS = 500.0  # p90  total transfer time must be < this


# ---------------------------------------------------------------------------
# Timed event collector
# ---------------------------------------------------------------------------


class _TimedEventCollector:
    """OPC UA event collector that pairs each event with a UTC arrival timestamp.

    event_notification() is called synchronously by asyncua immediately when
    an event is delivered on the subscription.  ``datetime.now(timezone.utc)``
    is captured at the very start of that call — the most accurate client-side
    timestamp achievable without modifying the asyncua transport layer.
    """

    def __init__(self, client) -> None:
        self._client = client
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscription = None

    # ── asyncua handler interface ──────────────────────────────────────────

    def event_notification(self, event) -> None:
        received = datetime.now(timezone.utc)
        try:
            self._queue.put_nowait((event, received))
        except asyncio.QueueFull:
            logger.warning("_TimedEventCollector: queue full — event dropped")

    def datachange_notification(self, _node, _val, _data) -> None:
        pass

    def status_change_notification(self, _status) -> None:
        pass

    # ── public API ────────────────────────────────────────────────────────

    async def subscribe(
        self,
        server_node,
        event_type_node,
        period_ms: int = 100,
        queue_size: int = 500,
    ) -> None:
        sub = await self._client.create_subscription(period_ms, self)
        self._subscription = sub
        await sub.subscribe_events(server_node, event_type_node, queuesize=queue_size)

    async def collect_one(self, timeout_s: float = _COLLECT_TIMEOUT_S):
        """Return the next (event, received_time) pair, or None on timeout."""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout_s)
        except asyncio.TimeoutError:
            return None

    async def unsubscribe(self) -> None:
        if self._subscription is not None:
            try:
                await asyncio.wait_for(self._subscription.delete(), timeout=5.0)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Unsubscribe failed: %s", exc)
            finally:
                self._subscription = None

    # ── context manager ───────────────────────────────────────────────────

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_) -> None:
        await self.unsubscribe()


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------


def _ensure_utc(dt: datetime | None) -> datetime | None:
    """Return dt with UTC tzinfo; treat naïve datetimes as UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _delta_ms(dt_from: datetime | None, dt_to: datetime | None) -> float | None:
    """(dt_to − dt_from) in milliseconds, or None if either argument is None."""
    a = _ensure_utc(dt_from)
    b = _ensure_utc(dt_to)
    if a is None or b is None:
        return None
    return (b - a).total_seconds() * 1000.0


def _duration_ms(value) -> float | None:
    """Convert an OPC UA Duration value (float ms or timedelta-like) to milliseconds."""
    if value is None:
        return None
    if hasattr(value, "total_seconds"):
        return value.total_seconds() * 1000.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_sample(event, received_time: datetime, index: int) -> dict:
    """Pull all timestamps + reported durations from a ResultReadyEvent and compute latencies."""
    meta = getattr(getattr(event, "Result", None), "ResultMetaData", None)
    pt = getattr(meta, "ProcessingTimes", None)
    start = _ensure_utc(getattr(pt, "StartTime", None))
    end = _ensure_utc(getattr(pt, "EndTime", None))
    acquisition_ms = _duration_ms(getattr(pt, "AcquisitionDuration", None))
    processing_ms = _duration_ms(getattr(pt, "ProcessingDuration", None))
    event_time = _ensure_utc(getattr(event, "Time", None))
    client_time = _ensure_utc(received_time)
    return {
        "index": index,
        "start_time": start,
        "end_time": end,
        "event_time": event_time,
        "client_time": client_time,
        "joining_ms": _delta_ms(start, end),
        "acquisition_ms": acquisition_ms,
        "processing_ms": processing_ms,
        "time_on_server_ms": _delta_ms(end, event_time),
        "wire_ms": _delta_ms(event_time, client_time),
        "total_ms": _delta_ms(end, client_time),
    }


def _percentile(sorted_values: list, p: float) -> float:
    """p-th percentile (0–100) of a pre-sorted list."""
    n = len(sorted_values)
    rank = max(1, math.ceil((p / 100.0) * n))
    return sorted_values[min(rank - 1, n - 1)]


def _col_stats(samples: list, key: str):
    vals = sorted(v for s in samples if (v := s.get(key)) is not None)
    if not vals:
        return None
    return {
        "n": len(vals),
        "min": vals[0],
        "mean": statistics.mean(vals),
        "median": statistics.median(vals),
        "p90": _percentile(vals, 90),
        "max": vals[-1],
        "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
    }


def _log_report(samples: list) -> None:
    """Write a structured per-sample table and aggregate statistics to the log."""
    eq = "=" * 110
    sep = "-" * 110
    logger.info(eq)
    logger.info(
        "  RESULT TRANSFER TIME  |  %d samples  |  MULTI_STEP_OK_RESULT + full traces",
        len(samples),
    )
    logger.info(
        "  Performance target: mean < %.0f ms AND p90 < %.0f ms",
        _THRESHOLD_MEAN_MS,
        _THRESHOLD_P90_MS,
    )
    logger.info(eq)
    logger.info(
        "  %4s  %14s  %14s  %14s  %14s  %14s  %14s",
        "#",
        "Joining",
        "Acquisition",
        "Processing",
        "On-server",
        "OPC UA+Wire",
        "TOTAL",
    )
    logger.info(sep)

    def _f(v):
        return f"{v:10.2f} ms" if v is not None else f"{'N/A':>12}"

    for s in samples:
        logger.info(
            "  %4d  %s  %s  %s  %s  %s  %s",
            s["index"],
            _f(s["joining_ms"]),
            _f(s["acquisition_ms"]),
            _f(s["processing_ms"]),
            _f(s["time_on_server_ms"]),
            _f(s["wire_ms"]),
            _f(s["total_ms"]),
        )

    logger.info(sep)
    logger.info(
        "  %-22s  %10s  %10s  %10s  %10s  %10s  %10s",
        "STATISTICS (ms)",
        "min",
        "mean",
        "median",
        "p90",
        "max",
        "stdev",
    )
    logger.info(eq)

    for label, key in [
        ("Joining duration", "joining_ms"),
        ("Result acquisition", "acquisition_ms"),
        ("Result processing", "processing_ms"),
        ("Time on server", "time_on_server_ms"),
        ("OPC UA + Wire", "wire_ms"),
        ("TOTAL — Result Transfer", "total_ms"),
    ]:
        st = _col_stats(samples, key)
        if st:
            logger.info(
                "  %-22s  %10.2f  %10.2f  %10.2f  %10.2f  %10.2f  %10.2f",
                label,
                st["min"],
                st["mean"],
                st["median"],
                st["p90"],
                st["max"],
                st["stdev"],
            )

    logger.info(eq)


# ---------------------------------------------------------------------------
# CI reporting
# ---------------------------------------------------------------------------


def _write_ci_report(
    record_property,
    mean_ms: float,
    p90_ms: float,
    min_ms: float,
    max_ms: float,
    n: int,
) -> None:
    """Publish timing metrics to JUnit XML for the aggregated System Tests Report.

    JUnit XML properties (record_property):
        Visible in GitHub Actions "Tests" tab, test-results dashboards, and any
        CI system that parses JUnit XML artifacts.  Prefix ``perf_`` prevents
        collisions with pytest's own properties.

        These properties are the durable signal: the aggregated System Tests
        Report job parses them out of ``pytest-live.xml`` (or equivalent) and
        renders the Performance Benchmarks block inside the single run-page
        step summary owned by that job. Writing directly to
        ``GITHUB_STEP_SUMMARY`` from this lane is intentionally avoided so
        the run page is not fragmented in job-completion order.
    """
    record_property("perf_sample_count", str(n))
    record_property("perf_mean_total_ms", f"{mean_ms:.2f}")
    record_property("perf_p90_total_ms", f"{p90_ms:.2f}")
    record_property("perf_min_total_ms", f"{min_ms:.2f}")
    record_property("perf_max_total_ms", f"{max_ms:.2f}")
    record_property("perf_threshold_mean_ms", f"{_THRESHOLD_MEAN_MS:.0f}")
    record_property("perf_threshold_p90_ms", f"{_THRESHOLD_P90_MS:.0f}")


# ---------------------------------------------------------------------------
# Performance test
# ---------------------------------------------------------------------------


async def test_result_transfer_time(
    subscription_client,
    opcua_client,  # noqa: ARG001  kept to ensure module-scoped client is open
    result_trigger,
    ns_indices,
    record_property,
):
    """Measure single-result end-to-end transfer time over _SAMPLE_COUNT samples.

    Triggers MULTI_STEP_OK_RESULT with full trace data, waits for the
    ResultReadyEvent on a separate subscription client, and records the
    timing pipeline (joining → acquisition → processing → server → wire → client)
    per result.

    A _INTER_RESULT_DELAY_S pause between triggers simulates the cadence of
    realistic tool-trigger presses from an operator.

    Asserts mean total transfer time < 500 ms AND p90 < 500 ms.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered — server does not support IJT Base spec")

    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))  # type: ignore[arg-type]
    server_node = subscription_client.nodes.server

    samples = []

    async with _TimedEventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)

        for i in range(1, _SAMPLE_COUNT + 1):
            outcome = await result_trigger.trigger_single(ResultType.MULTI_STEP_OK_RESULT, include_traces=True)
            if not outcome.triggered:
                if result_trigger.is_simulator:
                    pytest.skip(f"Sample {i}/{_SAMPLE_COUNT}: simulator trigger failed — {outcome.skip_reason}")
                else:
                    pytest.skip(
                        f"Sample {i}/{_SAMPLE_COUNT}: external trigger required — "
                        "trigger the tool manually within the collection window"
                    )

            item = await collector.collect_one(timeout_s=_COLLECT_TIMEOUT_S)
            if item is None:
                pytest.skip(
                    f"Sample {i}/{_SAMPLE_COUNT}: no ResultReadyEvent received within {_COLLECT_TIMEOUT_S:.0f} s"
                )

            event, received_time = item
            s = _extract_sample(event, received_time, i)
            samples.append(s)

            logger.info(
                "Sample %2d/%d:  total=%s  |  joining=%s  on-server=%s  wire=%s",
                i,
                _SAMPLE_COUNT,
                f"{s['total_ms']:.2f} ms" if s["total_ms"] is not None else "N/A",
                f"{s['joining_ms']:.2f} ms" if s["joining_ms"] is not None else "N/A",
                f"{s['time_on_server_ms']:.2f} ms" if s["time_on_server_ms"] is not None else "N/A",
                f"{s['wire_ms']:.2f} ms" if s["wire_ms"] is not None else "N/A",
            )

            if i < _SAMPLE_COUNT:
                await asyncio.sleep(_INTER_RESULT_DELAY_S)

    _log_report(samples)

    valid_totals = sorted(s["total_ms"] for s in samples if s["total_ms"] is not None)
    if not valid_totals:
        pytest.skip("No valid total_ms from any sample — ProcessingTimes.EndTime absent in all events")

    mean_ms = statistics.mean(valid_totals)
    p90_ms = _percentile(valid_totals, 90)

    _write_ci_report(
        record_property,
        mean_ms,
        p90_ms,
        valid_totals[0],
        valid_totals[-1],
        len(valid_totals),
    )

    assert mean_ms < _THRESHOLD_MEAN_MS, (
        f"Mean result transfer time {mean_ms:.1f} ms exceeds "
        f"{_THRESHOLD_MEAN_MS:.0f} ms target.\n"
        f"  n={len(valid_totals)},  min={valid_totals[0]:.1f},  "
        f"max={valid_totals[-1]:.1f},  p90={p90_ms:.1f} ms\n"
        "  Prerequisite: client and server clocks synchronised to ms accuracy, "
        "same timezone."
    )
    assert p90_ms < _THRESHOLD_P90_MS, (
        f"p90 result transfer time {p90_ms:.1f} ms exceeds "
        f"{_THRESHOLD_P90_MS:.0f} ms target.\n"
        f"  n={len(valid_totals)},  mean={mean_ms:.1f},  max={valid_totals[-1]:.1f} ms"
    )
