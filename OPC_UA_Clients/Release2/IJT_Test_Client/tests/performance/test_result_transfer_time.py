"""
Single-Result Transfer Time — end-to-end latency benchmark.

Measures how long it takes for a completed tightening result to travel from
the controller (ProcessingTimes.EndTime) through the OPC UA server and across
the network/transport to the client subscription callback.

Timing pipeline (per sample):
  ①  ProcessingTimes.StartTime  — tightening begins  (controller clock)
  ②  ProcessingTimes.EndTime    — tightening ends    (controller clock)
  ③  event.Time  (EventTime)    — ResultReadyEvent generated on the server
  ④  client_received_time       — asyncua subscription callback fires on client

Measured intervals:
  Tightening duration  : ② − ①   how long the physical join took
  Server dispatch      : ③ − ②   server processing + event-emission latency
  Wire transfer        : ④ − ③   network + OPC UA transport latency
  Total transfer time  : ④ − ②   end-of-tightening → client  ← primary SLA metric

Test parameters:
  _SAMPLE_COUNT consecutive ONE_STEP_OK_RESULT results with full trace data.
  _INTER_RESULT_DELAY_S pause between triggers to simulate realistic tool-press cadence.
  Statistics are computed over all samples: min / mean / median / p90 / max / stdev.

Prerequisite:
  Client and server clocks must be synchronised to millisecond accuracy and share
  the same timezone.  On a single host (simulator) this is automatically satisfied.

Pass/fail criteria (aggregate over all samples):
  mean(total_transfer_ms)  ≤  _THRESHOLD_MEAN_MS
  p90(total_transfer_ms)   ≤  _THRESHOLD_P90_MS
"""

import asyncio
import logging
import math
import os
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
_THRESHOLD_MEAN_MS = 500.0  # mean total transfer time must be ≤ this
_THRESHOLD_P90_MS = 1000.0  # p90  total transfer time must be ≤ this


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


def _extract_sample(event, received_time: datetime, index: int) -> dict:
    """Pull all four timestamps from a ResultReadyEvent and compute latencies."""
    meta = getattr(getattr(event, "Result", None), "ResultMetaData", None)
    pt = getattr(meta, "ProcessingTimes", None)
    start = _ensure_utc(getattr(pt, "StartTime", None))
    end = _ensure_utc(getattr(pt, "EndTime", None))
    event_time = _ensure_utc(getattr(event, "Time", None))
    client_time = _ensure_utc(received_time)
    return {
        "index": index,
        "start_time": start,
        "end_time": end,
        "event_time": event_time,
        "client_time": client_time,
        "tightening_ms": _delta_ms(start, end),
        "server_dispatch_ms": _delta_ms(end, event_time),
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
    eq = "=" * 92
    sep = "-" * 92
    logger.info(eq)
    logger.info(
        "  SINGLE RESULT TRANSFER TIME  |  %d samples  |  ONE_STEP_OK_RESULT + full traces",
        len(samples),
    )
    logger.info(
        "  Thresholds: mean ≤ %.0f ms,  p90 ≤ %.0f ms",
        _THRESHOLD_MEAN_MS,
        _THRESHOLD_P90_MS,
    )
    logger.info(eq)
    logger.info(
        "  %4s  %16s  %18s  %16s  %14s",
        "#",
        "Tightening (①②)",
        "Server Dispatch (②③)",
        "Wire Transfer (③④)",
        "TOTAL (②④)",
    )
    logger.info(sep)

    for s in samples:

        def _f(v):
            return f"{v:10.2f} ms" if v is not None else f"{'N/A':>12}"

        logger.info(
            "  %4d  %s      %s      %s    %s",
            s["index"],
            _f(s["tightening_ms"]),
            _f(s["server_dispatch_ms"]),
            _f(s["wire_ms"]),
            _f(s["total_ms"]),
        )

    logger.info(sep)
    logger.info(
        "  %4s  %-20s  %10s  %10s  %10s  %10s  %10s  %10s",
        "",
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
        ("Tightening (①②)", "tightening_ms"),
        ("Server Dispatch (②③)", "server_dispatch_ms"),
        ("Wire Transfer (③④)", "wire_ms"),
        ("TOTAL (②④)", "total_ms"),
    ]:
        st = _col_stats(samples, key)
        if st:
            logger.info(
                "  %4s  %-20s  %10.2f  %10.2f  %10.2f  %10.2f  %10.2f  %10.2f",
                "",
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
    samples: list,
    mean_ms: float,
    p90_ms: float,
    min_ms: float,
    max_ms: float,
    n: int,
) -> None:
    """Publish timing metrics to JUnit XML and the GitHub Actions step summary.

    JUnit XML properties (record_property):
        Visible in GitHub Actions "Tests" tab, test-results dashboards, and any
        CI system that parses JUnit XML artifacts.  Prefix ``perf_`` prevents
        collisions with pytest's own properties.

    GitHub Step Summary (GITHUB_STEP_SUMMARY):
        Appends a formatted markdown table to the workflow run summary page —
        the most visible place in a GitHub Actions run.  No-op when the env var
        is absent (local runs, non-GitHub CI).
    """
    record_property("perf_sample_count", str(n))
    record_property("perf_mean_total_ms", f"{mean_ms:.2f}")
    record_property("perf_p90_total_ms", f"{p90_ms:.2f}")
    record_property("perf_min_total_ms", f"{min_ms:.2f}")
    record_property("perf_max_total_ms", f"{max_ms:.2f}")
    record_property("perf_threshold_mean_ms", f"{_THRESHOLD_MEAN_MS:.0f}")
    record_property("perf_threshold_p90_ms", f"{_THRESHOLD_P90_MS:.0f}")

    gh_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not gh_summary:
        return

    st_tight = _col_stats(samples, "tightening_ms")
    st_disp = _col_stats(samples, "server_dispatch_ms")
    st_wire = _col_stats(samples, "wire_ms")
    st_total = _col_stats(samples, "total_ms")

    def _row(label: str, st) -> str:
        if st is None:
            return f"| {label} | N/A | N/A | N/A | N/A | N/A |\n"
        return (
            f"| {label} | {st['min']:.2f} | {st['mean']:.2f} | "
            f"{st['median']:.2f} | {st['p90']:.2f} | {st['max']:.2f} |\n"
        )

    pass_fail = "✅ PASS" if mean_ms <= _THRESHOLD_MEAN_MS and p90_ms <= _THRESHOLD_P90_MS else "❌ FAIL"

    try:
        with open(gh_summary, "a", encoding="utf-8") as fh:
            fh.write(f"\n## 🏎  Result Transfer Time ({n} samples)\n\n")
            fh.write(
                f"> `ONE_STEP_OK_RESULT` + full traces &nbsp;|&nbsp; "
                f"Thresholds: mean ≤ {_THRESHOLD_MEAN_MS:.0f} ms, "
                f"p90 ≤ {_THRESHOLD_P90_MS:.0f} ms\n\n"
            )
            fh.write("| Interval | min (ms) | mean (ms) | median (ms) | p90 (ms) | max (ms) |\n")
            fh.write("|---|---|---|---|---|---|\n")
            fh.write(_row("Tightening ①②", st_tight))
            fh.write(_row("Server Dispatch ②③", st_disp))
            fh.write(_row("Wire Transfer ③④", st_wire))
            fh.write(_row("**TOTAL ②④**", st_total))
            fh.write(f"\n**{pass_fail}** &nbsp;—&nbsp; mean {mean_ms:.2f} ms &nbsp;|&nbsp; p90 {p90_ms:.2f} ms\n")
    except OSError as exc:
        logger.warning("Could not write to GITHUB_STEP_SUMMARY: %s", exc)


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

    Triggers ONE_STEP_OK_RESULT with full trace data, waits for the
    ResultReadyEvent on a separate subscription client, and records the
    four-stage timing pipeline per result.

    A _INTER_RESULT_DELAY_S pause between triggers simulates the cadence of
    realistic tool-trigger presses from an operator.

    Asserts mean total transfer time ≤ 500 ms and p90 ≤ 1000 ms.
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
            outcome = await result_trigger.trigger_single(ResultType.ONE_STEP_OK_RESULT, include_traces=True)
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
                "Sample %2d/%d:  total=%s  |  tightening=%s  dispatch=%s  wire=%s",
                i,
                _SAMPLE_COUNT,
                f"{s['total_ms']:.2f} ms" if s["total_ms"] is not None else "N/A",
                f"{s['tightening_ms']:.2f} ms" if s["tightening_ms"] is not None else "N/A",
                f"{s['server_dispatch_ms']:.2f} ms" if s["server_dispatch_ms"] is not None else "N/A",
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
        samples,
        mean_ms,
        p90_ms,
        valid_totals[0],
        valid_totals[-1],
        len(valid_totals),
    )

    assert mean_ms <= _THRESHOLD_MEAN_MS, (
        f"Mean result transfer time {mean_ms:.1f} ms exceeds "
        f"{_THRESHOLD_MEAN_MS:.0f} ms threshold.\n"
        f"  n={len(valid_totals)},  min={valid_totals[0]:.1f},  "
        f"max={valid_totals[-1]:.1f},  p90={p90_ms:.1f} ms\n"
        "  Prerequisite: client and server clocks synchronised to ms accuracy, "
        "same timezone."
    )
    assert p90_ms <= _THRESHOLD_P90_MS, (
        f"p90 result transfer time {p90_ms:.1f} ms exceeds "
        f"{_THRESHOLD_P90_MS:.0f} ms threshold.\n"
        f"  n={len(valid_totals)},  mean={mean_ms:.1f},  max={valid_totals[-1]:.1f} ms"
    )
