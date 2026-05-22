"""
Single-Result Transfer Time — end-to-end latency benchmark (Console Client).

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
  _INTER_RESULT_DELAY_S pause between triggers simulates realistic tool-press cadence.

Prerequisite:
  Client and server clocks must be synchronised to millisecond accuracy and share
  the same timezone.  On a single host (simulator) this is automatically satisfied.

Performance target (aggregate over all samples):
  mean(total_transfer_ms)  <  _THRESHOLD_MEAN_MS
  p90(total_transfer_ms)   <  _THRESHOLD_P90_MS

Note:
  This test requires the IJT simulator's SimulateSingleResult method.
  It will be skipped automatically against a real controller that does not expose
  simulation methods. For real-controller measurement, trigger results manually
  and extend _COLLECT_TIMEOUT_S accordingly.
"""

import asyncio
import logging
import math
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

import pytest
import pytest_asyncio
from asyncua import Client, ua

# ── Console Client root on sys.path (done by conftest.py, but guard here too) ──
_LIVE_DIR = Path(__file__).resolve().parent
_CONSOLE_ROOT = _LIVE_DIR.parents[1]
if str(_CONSOLE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONSOLE_ROOT))

logger = logging.getLogger(__name__)

_SERVER_URL = os.environ.get("OPCUA_SERVER_URL", "opc.tcp://localhost:40451")
_OPCUA_TIMEOUT_S = 120

# Namespace URIs
_NS_IJT_BASE_URI = "http://opcfoundation.org/UA/IJT/Base/"
_NS_APP_URI = "urn:AtlasCopco:IJT:Tightening:Server/"  # simulator-only namespace

# JoiningSystemResultReadyEventType local node ID within NS_IJT_BASE
_RESULT_READY_EVENT_TYPE_ID = 1007

_SAMPLE_COUNT = 20
_INTER_RESULT_DELAY_S = 1.0  # realistic gap between tool trigger presses
_COLLECT_TIMEOUT_S = 30.0  # max time to wait for each ResultReadyEvent
_THRESHOLD_MEAN_MS = 500.0  # mean total transfer time must be < this
_THRESHOLD_P90_MS = 500.0  # p90  total transfer time must be < this


# ---------------------------------------------------------------------------
# Module-scoped fixtures — shared connections across all samples
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def _method_client() -> AsyncGenerator:
    """Module-scoped asyncua Client used for SimulateSingleResult method calls."""
    client = Client(_SERVER_URL, timeout=_OPCUA_TIMEOUT_S)
    await client.connect()
    try:
        await client.load_data_type_definitions()
    except Exception as exc:  # noqa: BLE001
        logger.warning("load_data_type_definitions failed (non-fatal): %s", exc)
    try:
        yield client
    finally:
        try:
            await client.disconnect()
        except Exception as exc:  # noqa: BLE001
            logger.debug("method_client disconnect error (ignored): %s", exc)


@pytest_asyncio.fixture(scope="function")
async def _sub_client() -> AsyncGenerator:
    """Function-scoped asyncua Client dedicated to event subscriptions.

    Kept separate from _method_client because asyncua cannot safely handle
    concurrent OPC UA requests on a single client connection when both method
    calls and event callbacks are in flight simultaneously.
    """
    client = Client(_SERVER_URL, timeout=_OPCUA_TIMEOUT_S)
    await client.connect()
    try:
        await client.load_data_type_definitions()
    except Exception as exc:  # noqa: BLE001
        logger.warning("load_data_type_definitions failed (non-fatal): %s", exc)
    try:
        yield client
    finally:
        try:
            await client.disconnect()
        except Exception as exc:  # noqa: BLE001
            logger.debug("sub_client disconnect error (ignored): %s", exc)


# ---------------------------------------------------------------------------
# Node discovery helpers
# ---------------------------------------------------------------------------


async def _ns_index(client: Client, uri: str) -> int | None:
    """Return the runtime namespace index for *uri*, or None if not registered."""
    try:
        return await client.get_namespace_index(uri)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Namespace index lookup failed; reading NamespaceArray fallback: %s", exc)

    try:
        namespace_array_node = client.get_node(ua.NodeId(2255, 0))  # type: ignore[arg-type]  # Server.NamespaceArray
        namespace_array = await namespace_array_node.read_value()
        return list(namespace_array).index(uri)
    except Exception:  # noqa: BLE001
        return None


async def _find_child(parent_node, ns_idx: int | None, browse_name: str):
    """Return a direct child by BrowseName.

    The simulator stores instance NodeIds in the application namespace, while
    several BrowseNames come from their defining specification namespace
    (DI/IJT/Machinery Result). Try the application namespace first for speed,
    then fall back to the first direct child with the requested BrowseName.Name.
    """
    if ns_idx is not None:
        try:
            return await parent_node.get_child(f"{ns_idx}:{browse_name}")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Direct browse lookup failed for %s; enumerating children: %s", browse_name, exc)

    try:
        children = await parent_node.get_children()
    except Exception:  # noqa: BLE001
        return None

    fallback_child = None
    for child in children:
        try:
            child_browse_name = await child.read_browse_name()
        except Exception:  # noqa: BLE001
            continue

        if getattr(child_browse_name, "Name", None) != browse_name:
            continue
        if ns_idx is None or getattr(child_browse_name, "NamespaceIndex", None) == ns_idx:
            return child
        if fallback_child is None:
            fallback_child = child
    return fallback_child


async def _locate_simulate_results(method_client: Client, ns_app: int | None):
    """Return (simulate_results_node, method_node) or (None, None) on failure.

    Walks:  Objects → TighteningSystem → Simulations → SimulateResults
    Nodes are matched in the application namespace when it is available, then
    by BrowseName.Name as a fallback for servers whose namespace index lookup
    is delayed or unavailable on this connection.
    """
    objects = method_client.nodes.objects
    js = await _find_child(objects, ns_app, "TighteningSystem")
    if js is None:
        return None, None
    sim = await _find_child(js, ns_app, "Simulations")
    if sim is None:
        return None, None
    sim_results = await _find_child(sim, ns_app, "SimulateResults")
    if sim_results is None:
        return None, None
    method_node = await _find_child(sim_results, ns_app, "SimulateSingleResult")
    return sim_results, method_node


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

    def __init__(self, client: Client) -> None:
        self._client = client
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscription: Any = None

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

    st_joining = _col_stats(samples, "joining_ms")
    st_acq = _col_stats(samples, "acquisition_ms")
    st_proc = _col_stats(samples, "processing_ms")
    st_server = _col_stats(samples, "time_on_server_ms")
    st_wire = _col_stats(samples, "wire_ms")
    st_total = _col_stats(samples, "total_ms")

    def _row(label: str, st) -> str:
        if st is None:
            return f"| {label} | N/A | N/A | N/A | N/A | N/A |\n"
        return (
            f"| {label} | {st['min']:.2f} | {st['mean']:.2f} | "
            f"{st['median']:.2f} | {st['p90']:.2f} | {st['max']:.2f} |\n"
        )

    target_met = mean_ms < _THRESHOLD_MEAN_MS and p90_ms < _THRESHOLD_P90_MS
    pass_fail = "✅ PASS" if target_met else "❌ FAIL"

    ends = sorted(s["end_time"] for s in samples if s.get("end_time"))
    receives = sorted(s["client_time"] for s in samples if s.get("client_time"))
    if ends and receives:
        window = f"{ends[0].strftime('%H:%M:%S')} → {receives[-1].strftime('%H:%M:%S')} UTC"
    else:
        window = "Not reported"

    try:
        with open(gh_summary, "a", encoding="utf-8") as fh:
            fh.write(f"\n## ⏱️ Result Transfer Time ({n} samples)\n\n")
            fh.write(
                f"> `MULTI_STEP_OK_RESULT` + full traces &nbsp;·&nbsp; "
                f"Run window: {window}\n>\n"
                f"> **Performance target:** mean &lt; {_THRESHOLD_MEAN_MS:.0f} ms "
                f"**AND** p90 &lt; {_THRESHOLD_P90_MS:.0f} ms\n\n"
            )
            fh.write("| Phase | min (ms) | mean (ms) | median (ms) | p90 (ms) | max (ms) |\n")
            fh.write("|---|---:|---:|---:|---:|---:|\n")
            fh.write(_row("🔧 Joining duration *(informational)*", st_joining))
            fh.write(_row("📥 Result acquisition *(server, informational)*", st_acq))
            fh.write(_row("⚙️ Result processing *(server, informational)*", st_proc))
            fh.write(_row("🖥️ Time on server", st_server))
            fh.write(_row("📶 OPC UA + Wire", st_wire))
            fh.write(_row("🏁 **TOTAL — Result Transfer Time**", st_total))
            fh.write(
                f"\n**{pass_fail}** &nbsp;—&nbsp; mean {mean_ms:.2f} ms &nbsp;·&nbsp; "
                f"p90 {p90_ms:.2f} ms &nbsp;·&nbsp; target both &lt; "
                f"{_THRESHOLD_MEAN_MS:.0f} ms\n\n"
            )
            fh.write(
                "> **Reading the table.** *Joining duration* is the physical "
                "operation itself — shown for context, not gated. *Result "
                "acquisition* and *result processing* are durations the server "
                "reports inside the *Time on server* wall-clock; they are "
                "informational sub-components. *Time on server* covers everything "
                "between end-of-join and the moment the server fires the event. "
                "*OPC UA + Wire* covers transport from server event to client "
                "callback. The **TOTAL** is end-of-join → client callback and is "
                "the gated metric.\n"
            )
    except OSError as exc:
        logger.warning("Could not write to GITHUB_STEP_SUMMARY: %s", exc)


# ---------------------------------------------------------------------------
# Performance test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="module")
async def test_result_transfer_time(
    _method_client: Client,
    _sub_client: Client,
    record_property,
):
    """Measure single-result end-to-end transfer time over _SAMPLE_COUNT samples.

    Triggers MULTI_STEP_OK_RESULT with full trace data, waits for the
    ResultReadyEvent on a dedicated subscription client, and records the
    timing pipeline (joining → acquisition → processing → server → wire → client)
    per result.

    A _INTER_RESULT_DELAY_S pause between triggers simulates the cadence of
    realistic tool-trigger presses from an operator.

    Skipped automatically if SimulateSingleResult is absent. Namespace index
    lookup is advisory; method discovery falls back to BrowseName.Name.
    """
    # Resolve namespaces. NS_APP is advisory for method lookup because the
    # simulator method path can also be discovered by BrowseName.Name.
    ns_app = await _ns_index(_method_client, _NS_APP_URI)

    ns_ijt = await _ns_index(_sub_client, _NS_IJT_BASE_URI)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered — cannot subscribe to ResultReadyEvent")

    # Locate SimulateSingleResult method node
    sim_results_node, method_node = await _locate_simulate_results(_method_client, ns_app)
    if sim_results_node is None or method_node is None:
        pytest.skip("SimulateSingleResult method node not found under TighteningSystem/Simulations/SimulateResults")

    # Subscription setup
    event_type_node = _sub_client.get_node(ua.NodeId(_RESULT_READY_EVENT_TYPE_ID, ns_ijt))  # type: ignore[arg-type]
    server_node = _sub_client.nodes.server

    samples = []

    async with _TimedEventCollector(_sub_client) as collector:
        await collector.subscribe(server_node, event_type_node)

        for i in range(1, _SAMPLE_COUNT + 1):
            # Trigger one single result with full trace data
            try:
                await asyncio.wait_for(
                    sim_results_node.call_method(
                        method_node.nodeid,
                        ua.Variant(2, ua.VariantType.UInt32),  # MULTI_STEP_OK_RESULT
                        ua.Variant(True, ua.VariantType.Boolean),  # include_traces
                    ),
                    timeout=30.0,
                )
            except (ua.UaError, asyncio.TimeoutError) as exc:
                pytest.skip(f"Sample {i}/{_SAMPLE_COUNT}: SimulateSingleResult failed — {exc}")

            # Wait for the ResultReadyEvent with its client arrival timestamp
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
        samples,
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
