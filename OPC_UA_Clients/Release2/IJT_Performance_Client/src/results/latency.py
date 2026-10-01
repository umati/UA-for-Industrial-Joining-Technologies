"""
Total Result Transfer Time and Latency Evaluation.

What does this module do?
When a manufacturing quality engineer observes delays in receiving joining results over OPC UA,
measuring only total elapsed time does not pinpoint the delay's origin.

This module captures standard OPC UA timestamps according to OPC UA Part 100 (Machinery Result)
and Part 40400 (Industrial Joining Technologies):

1. T_start  (ProcessingTimes.StartTime)    : Physical joining operation started.
2. T_end    (ProcessingTimes.EndTime)      : Physical joining operation completed.
3. T_create (ResultMetaData.CreationTime)  : Server assembled the result record in memory.
4. T_event  (event.Time)                   : OPC UA server emitted the JoiningSystemResultReadyEvent.
5. T_bytes  (bytes_received_time)          : Client read the complete PublishResponse from the socket.
6. T_decode (decoded_time)                 : Client finished decoding the PublishResponse.
7. T_client (client_received_time)         : Subscription handler started processing the event.

T_bytes and T_decode come from the wire timing hooks (src/engine/timing_hooks.py). Without them
(``timing_source == "handler"``) the delivery metrics fall back to T_client.

Standardized Timing Breakdown (in milliseconds; "+ Skew" converts server time to client time):
- Joining Duration           (joining_duration_ms)          : T_end - T_start (physical joining cycle)
- Server Processing Duration (server_processing_time_ms)    : T_event - T_end (server assembles and emits the event)
- Delivery Time              (delivery_time_ms)             : T_bytes - T_end + Skew (headline: result on the client's wire)
- Client Decode Time         (client_decode_time_ms)        : T_decode - T_bytes (client-side decoding, no skew)
- Client-Ready Time          (client_ready_time_ms)         : T_decode - T_end + Skew (result decoded and usable)
- Dispatch Delay             (dispatch_delay_ms)            : T_client - T_decode (asyncio scheduling of the handler)
- Network Transport Latency  (network_transport_time_ms)    : T_client - T_event + Skew (event emission to application handler)
- Total Result Transfer Time (total_result_transfer_time_ms): T_client - T_end + Skew (end-to-end to application handler)
"""

from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass, fields
from datetime import UTC, datetime, timedelta
from typing import Any

from asyncua import Client, ua

logger = logging.getLogger(__name__)

# Skew uncertainty bound threshold: RTT > 50ms means uncertainty > ±25ms
CLOCK_SKEW_HIGH_RTT_THRESHOLD_MS = 50.0

# Default clock-health tolerance: events that appear older than collection start by more than
# this (plus RTT/2) raise a clock warning. Warnings never fail the integrity gate.
DEFAULT_CLOCK_TOLERANCE_MS = 1000.0

# Where delivery timestamps come from: asyncua wire hooks, or handler entry as fallback.
TIMING_SOURCE_WIRE = "wire"
TIMING_SOURCE_HANDLER = "handler"

# Result Integrity Categories (Benchmark Integrity Gate)
INTEGRITY_VALID = "VALID"
INTEGRITY_INCOMPLETE = "INCOMPLETE"
INTEGRITY_DUPLICATE = "DUPLICATE"
INTEGRITY_UNMATCHED = "UNMATCHED"


@dataclass
class LatencySample:
    """Timing profile for one joining result.

    ``sample_id`` is local to one endpoint. Use ``(endpoint, sample_id)`` as
    the stable identity when aggregating samples from multiple endpoints.
    """

    sample_id: int
    endpoint: str
    tool_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    creation_time: datetime | None = None
    event_time: datetime | None = None
    client_received_time: datetime | None = None
    bytes_received_time: datetime | None = None
    decoded_time: datetime | None = None
    timing_source: str = TIMING_SOURCE_HANDLER
    clock_skew_ms: float = 0.0

    # Result verification & audit attributes (proves real results without storing raw arrays)
    result_id: str | None = None
    result_evaluation: str | None = None
    trace_curves_count: int = 0
    trace_total_points: int = 0
    trace_declared_points: int = 0
    trace_decoded_points: int = 0
    trace_is_incomplete: bool | None = None

    # Benchmark Integrity Gate classification. The VALID default is a convenience for building
    # samples directly; extract_sample_from_event and from_dict always set the status explicitly.
    integrity_status: str = INTEGRITY_VALID
    integrity_reason: str = ""
    clock_warning: bool = False

    # Standardized timing metrics in milliseconds
    joining_duration_ms: float | None = None
    server_processing_time_ms: float | None = None
    network_transport_time_ms: float | None = None
    total_result_transfer_time_ms: float | None = None
    raw_network_transport_time_ms: float | None = None
    raw_total_result_transfer_time_ms: float | None = None
    delivery_time_ms: float | None = None
    raw_delivery_time_ms: float | None = None
    client_decode_time_ms: float | None = None
    client_ready_time_ms: float | None = None
    raw_client_ready_time_ms: float | None = None
    dispatch_delay_ms: float | None = None
    is_clamped_to_zero: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize for inter-process transfer (datetimes as ISO 8601 strings)."""
        data: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            data[f.name] = value.isoformat() if isinstance(value, datetime) else value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LatencySample:
        """Inverse of ``to_dict``. A missing integrity status is treated as INCOMPLETE, never VALID."""
        known = {f.name: f for f in fields(cls)}
        kwargs: dict[str, Any] = {}
        for name, value in data.items():
            if name not in known:
                continue
            if name.endswith("_time") and isinstance(value, str):
                value = datetime.fromisoformat(value)
            kwargs[name] = value
        if "integrity_status" not in kwargs:
            kwargs["integrity_status"] = INTEGRITY_INCOMPLETE
            kwargs.setdefault("integrity_reason", "Integrity status missing from transferred sample")
        return cls(**kwargs)

    def calculate_metrics(self) -> None:
        """Compute all latency intervals from timestamps with timezone normalization."""

        def to_utc(dt: datetime | None) -> datetime | None:
            if dt is None:
                return None
            return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)

        t_start = to_utc(self.start_time)
        t_end = to_utc(self.end_time)
        t_create = to_utc(self.creation_time)
        t_event = to_utc(self.event_time)
        t_client = to_utc(self.client_received_time)

        # 1. Physical joining operation duration
        if t_end and t_start:
            self.joining_duration_ms = (t_end - t_start).total_seconds() * 1000.0

        # 2. Server processing duration: time server spends from operation completion to event emission
        if t_event and t_end:
            self.server_processing_time_ms = (t_event - t_end).total_seconds() * 1000.0
        elif t_create and t_end:
            self.server_processing_time_ms = (t_create - t_end).total_seconds() * 1000.0

        # 3. Event emission to application handler (skew-corrected)
        self.network_transport_time_ms, self.raw_network_transport_time_ms = self._skewed(t_client, t_event)
        # 4. Operation end to application handler (skew-corrected)
        self.total_result_transfer_time_ms, self.raw_total_result_transfer_time_ms = self._skewed(t_client, t_end)

        # 5. Wire-level phases; fall back to handler entry when the timing hooks are unavailable.
        t_bytes = to_utc(self.bytes_received_time)
        t_decoded = to_utc(self.decoded_time)
        if t_bytes and t_decoded:
            self.timing_source = TIMING_SOURCE_WIRE
            self.delivery_time_ms, self.raw_delivery_time_ms = self._skewed(t_bytes, t_end)
            self.client_ready_time_ms, self.raw_client_ready_time_ms = self._skewed(t_decoded, t_end)
            self.client_decode_time_ms = (t_decoded - t_bytes).total_seconds() * 1000.0
            if t_client:
                self.dispatch_delay_ms = (t_client - t_decoded).total_seconds() * 1000.0
        else:
            self.timing_source = TIMING_SOURCE_HANDLER
            self.delivery_time_ms = self.client_ready_time_ms = self.total_result_transfer_time_ms
            self.raw_delivery_time_ms = self.raw_client_ready_time_ms = self.raw_total_result_transfer_time_ms

    def _skewed(self, later: datetime | None, earlier: datetime | None) -> tuple[Any, float | None]:
        """Skew-corrected interval in ms as (value clamped at 0, raw value). Clamping sets is_clamped_to_zero."""
        if not later or not earlier:
            return None, None
        value = (later - earlier).total_seconds() * 1000.0 + self.clock_skew_ms
        try:
            raw = float(value)
        except (TypeError, ValueError):
            return value, None
        if raw < 0.0:
            self.is_clamped_to_zero = True
        return max(0.0, raw), raw


def _unwrap_variant(val: Any) -> Any:
    """Recursively unwraps an asyncua ua.Variant wrapper if present."""
    while hasattr(val, "Value") and type(val).__name__ in ("Variant", "_Variant"):
        val = val.Value
    return val


def _safe_getattr(obj: Any, name: str, default: Any = None) -> Any:
    """Safely retrieve attribute without triggering recursive mock creation on unconfigured Mocks."""
    if obj is None:
        return default
    if hasattr(obj, "_mock_return_value"):
        if name in getattr(obj, "__dict__", {}):
            return getattr(obj, name)
        return default
    return getattr(obj, name, default)


def _to_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def _as_list(value: Any) -> list[Any]:
    value = _unwrap_variant(value)
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [_unwrap_variant(v) for v in value]
    return [value]


def _evaluation_name(raw_eval: Any) -> str | None:
    if raw_eval is None:
        return None
    eval_name = getattr(raw_eval, "name", None)
    if eval_name:
        return str(eval_name)
    if raw_eval == 1:
        return "OK"
    if raw_eval == 2:
        return "NOT_OK"
    return str(raw_eval)


def _all_finite_numbers(values: list[Any]) -> bool:
    try:
        return all(map(math.isfinite, values))
    except TypeError:
        return False


@dataclass
class _TraceAudit:
    curves: int = 0
    declared_points: int = 0
    decoded_points: int = 0
    traces: int = 0
    error: str | None = None

    def fail(self, reason: str) -> None:
        if self.error is None:
            self.error = reason


def _audit_trace(trace: Any, owner_result_id: str | None, audit: _TraceAudit) -> None:
    """Strictly validate one JoiningTraceDataType (OPC 40450-1).

    Rules: Trace.ResultId equals the owning result's ResultId; at least one StepTrace;
    every StepTrace declares NumberOfTracePoints >= 1 and carries at least one
    StepTraceContent entry; every entry's Values has exactly NumberOfTracePoints finite numbers.
    """
    audit.traces += 1
    trace_result_id = _safe_getattr(trace, "ResultId", None)
    if trace_result_id is None or str(trace_result_id) != owner_result_id:
        audit.fail(f"Trace.ResultId '{trace_result_id}' does not match ResultId '{owner_result_id}'")

    step_traces = _as_list(_safe_getattr(trace, "StepTraces", None))
    if not step_traces:
        audit.fail("Trace has no StepTraces")
    for index, step in enumerate(step_traces):
        if step is None:
            audit.fail(f"StepTraces[{index}] is empty")
            continue
        raw_declared = _safe_getattr(step, "NumberOfTracePoints", None)
        try:
            declared = int(raw_declared)
        except (TypeError, ValueError):
            declared = 0
        audit.declared_points += max(declared, 0)
        if declared < 1:
            audit.fail(f"StepTraces[{index}].NumberOfTracePoints is missing or zero ({raw_declared})")

        contents = [c for c in _as_list(_safe_getattr(step, "StepTraceContent", None)) if c is not None]
        if not contents:
            audit.fail(f"StepTraces[{index}] has no StepTraceContent curves")
        for c_index, content in enumerate(contents):
            audit.curves += 1
            values = _unwrap_variant(_safe_getattr(content, "Values", None))
            if not isinstance(values, (list, tuple)):
                audit.fail(f"StepTraces[{index}].StepTraceContent[{c_index}].Values is missing")
                continue
            audit.decoded_points += len(values)
            if len(values) != declared:
                audit.fail(
                    f"StepTraces[{index}].StepTraceContent[{c_index}] has {len(values)} values, "
                    f"NumberOfTracePoints declares {declared}"
                )
            elif not _all_finite_numbers(list(values)):
                audit.fail(f"StepTraces[{index}].StepTraceContent[{c_index}] contains non-finite or non-numeric values")


def _result_id_of(node: Any) -> str | None:
    raw = _safe_getattr(_safe_getattr(node, "ResultMetaData", None), "ResultId", None)
    return None if raw is None else str(raw)


def _walk_result_tree(result: Any, audit: _TraceAudit) -> None:
    """Visit the result and every nested ResultContent entry, auditing each Trace found.

    Nested ResultDataType entries (for example batch results) carry their own ResultMetaData;
    their traces must reference their own ResultId. Decoded payloads are finite acyclic trees,
    so no depth cap is needed; the identity guard only protects against malformed object graphs.
    """
    stack: list[tuple[Any, str | None]] = [(result, _result_id_of(result))]
    visited: set[int] = set()
    while stack:
        node, owner_id = stack.pop()
        node = _unwrap_variant(node)
        if node is None or id(node) in visited:
            continue
        visited.add(id(node))
        if isinstance(node, (list, tuple)):
            stack.extend((child, owner_id) for child in node)
            continue
        owner_id = _result_id_of(node) or owner_id
        trace = _unwrap_variant(_safe_getattr(node, "Trace", None))
        if trace is not None:
            _audit_trace(trace, owner_id, audit)
        stack.extend((child, owner_id) for child in reversed(_as_list(_safe_getattr(node, "ResultContent", None))))


def extract_sample_from_event(
    event: Any,
    client_received: datetime,
    sample_id: int,
    endpoint: str,
    clock_skew_ms: float = 0.0,
    trace_expected: bool = False,
    t_collection_start: datetime | None = None,
    clock_tolerance_ms: float = DEFAULT_CLOCK_TOLERANCE_MS,
    clock_rtt_ms: float | None = None,
    bytes_received: datetime | None = None,
    decoded: datetime | None = None,
) -> LatencySample:
    """Build a LatencySample from a JoiningSystemResultReadyEvent and classify its integrity.

    Only the OPC 40450-1 shape ``event.Result.ResultMetaData`` is read; VALID requires
    ResultMetaData.ResultId, event Time, and ResultMetaData.ProcessingTimes.EndTime. Any Trace present is
    validated strictly (see ``_audit_trace``); when ``trace_expected`` is True a missing Trace is
    INCOMPLETE. Events that appear to predate ``t_collection_start`` (after skew correction and
    tolerance) only set ``clock_warning``; they do not change integrity status.
    """
    sample = LatencySample(
        sample_id=sample_id,
        endpoint=endpoint,
        client_received_time=client_received,
        bytes_received_time=bytes_received,
        decoded_time=decoded,
        clock_skew_ms=clock_skew_ms,
        integrity_status=INTEGRITY_INCOMPLETE,
    )
    sample.event_time = _safe_getattr(event, "Time", None)

    # Only the OPC 40450-1 shape is accepted: event.Result (ResultDataType) -> ResultMetaData.
    result = _unwrap_variant(_safe_getattr(event, "Result", None))
    meta = _safe_getattr(result, "ResultMetaData", None)
    proc_times = _safe_getattr(meta, "ProcessingTimes", None)
    sample.creation_time = _safe_getattr(meta, "CreationTime", None)
    sample.start_time = _safe_getattr(proc_times, "StartTime", None)
    sample.end_time = _safe_getattr(proc_times, "EndTime", None)
    sample.result_id = _result_id_of(result)
    sample.result_evaluation = _evaluation_name(_safe_getattr(meta, "ResultEvaluation", None))

    audit = _TraceAudit()
    _walk_result_tree(result, audit)
    if trace_expected and audit.traces == 0:
        audit.fail("No Trace in result although traces were requested")
    sample.trace_curves_count = audit.curves
    sample.trace_declared_points = audit.declared_points
    sample.trace_decoded_points = audit.decoded_points
    sample.trace_total_points = audit.decoded_points
    sample.trace_is_incomplete = (audit.error is not None) if (audit.traces or trace_expected) else None

    missing = [
        name
        for name, value in (
            ("ResultId", sample.result_id),
            ("event Time", sample.event_time),
            ("ProcessingTimes.EndTime", sample.end_time),
        )
        if not value
    ]
    if missing:
        sample.integrity_reason = f"Missing required field(s): {', '.join(missing)}"
    elif audit.error is not None:
        sample.integrity_reason = audit.error
    else:
        sample.integrity_status = INTEGRITY_VALID

    if t_collection_start is not None and isinstance(sample.event_time, datetime):
        tolerance_ms = clock_tolerance_ms + (clock_rtt_ms or 0.0) / 2.0
        event_client_clock = _to_utc(sample.event_time) - timedelta(milliseconds=clock_skew_ms)
        earliest = _to_utc(t_collection_start) - timedelta(milliseconds=tolerance_ms)
        sample.clock_warning = event_client_clock < earliest

    sample.calculate_metrics()
    return sample


@dataclass(frozen=True)
class ClockCalibration:
    """Result of Cristian's-algorithm clock probing (``skew_ms`` = server minus client)."""

    skew_ms: float = 0.0
    rtt_ms: float | None = None


async def calibrate_clock_skew(client: Client, num_probes: int = 3) -> ClockCalibration:
    """Measure server-vs-client clock skew from the lowest-RTT probe (Cristian's algorithm).

    Returns the skew and the RTT of the probe used; ``rtt_ms`` is None when no probe succeeded.
    """
    best_rtt: float = float("inf")
    best_skew: float = 0.0

    try:
        server_time_node = client.get_node(ua.NodeId(ua.ObjectIds.Server_ServerStatus_CurrentTime))  # type: ignore[arg-type]
        for _ in range(max(1, num_probes)):
            t_before = datetime.now(UTC)
            server_now = await server_time_node.read_value()
            t_after = datetime.now(UTC)

            if not isinstance(server_now, datetime):
                continue

            server_now = _to_utc(server_now)
            rtt_ms = (t_after - t_before).total_seconds() * 1000.0
            if rtt_ms < best_rtt:
                best_rtt = rtt_ms
                client_midpoint = t_before + (t_after - t_before) / 2
                best_skew = (server_now - client_midpoint).total_seconds() * 1000.0

        if best_rtt != float("inf"):
            if best_rtt > CLOCK_SKEW_HIGH_RTT_THRESHOLD_MS:
                logger.warning(
                    f"Elevated RTT ({best_rtt:.1f}ms) during clock calibration with {client.server_url}. "
                    f"Clock offset uncertainty is ±{best_rtt / 2.0:.1f}ms."
                )
            return ClockCalibration(skew_ms=best_skew, rtt_ms=best_rtt)
        return ClockCalibration()
    except Exception as exc:
        logger.warning(f"Clock offset calibration failed for {client.server_url}: {exc}")
        return ClockCalibration()


def compute_statistics(values: list[float]) -> dict[str, float | int]:
    """Computes standard manufacturing latency percentiles:
    Min, Mean, Median, P90 (90th percentile), P95, P99, Max, and Standard Deviation.

    Why P90 and P99 matter:
    In automated automotive assembly lines, average latency doesn't tell the full story.
    If 99 out of 100 results arrive in 20ms, but 1 result takes 5,000ms, the cycle on the
    assembly line is delayed. P90 and P99 catch those tail latency spikes.
    """
    if not values:
        return {
            "count": 0,
            "min": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "max": 0.0,
            "stdev": 0.0,
        }

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def percentile(p: float) -> float:
        if n == 1:
            return sorted_vals[0]
        idx = (p / 100.0) * (n - 1)
        lower = int(math.floor(idx))
        upper = int(math.ceil(idx))
        weight = idx - lower
        return sorted_vals[lower] * (1.0 - weight) + sorted_vals[upper] * weight

    return {
        "count": n,
        "min": sorted_vals[0],
        "mean": statistics.mean(sorted_vals),
        "median": statistics.median(sorted_vals),
        "p90": percentile(90.0),
        "p95": percentile(95.0),
        "p99": percentile(99.0),
        "max": sorted_vals[-1],
        "stdev": statistics.stdev(sorted_vals) if n > 1 else 0.0,
    }
