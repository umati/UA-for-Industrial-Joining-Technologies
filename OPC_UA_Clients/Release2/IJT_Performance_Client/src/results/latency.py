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
5. T_client (datetime.now(UTC))            : Client subscription callback received the event.

Standardized Timing Breakdown (in milliseconds):
- Joining Duration           (joining_duration_ms)        : T_end - T_start (Physical joining operation cycle)
- Server Processing Duration (server_processing_time_ms)  : T_event - T_end (Time server spends assembling & emitting result event)
- Network Transport Latency  (network_transport_time_ms)  : T_client - T_event + Skew (Transit on network + client decoding & callback)
- Total Result Transfer Time (total_result_transfer_time_ms): T_client - T_end + Skew (Total end-to-end result delivery latency)
"""

from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from asyncua import Client, ua

logger = logging.getLogger(__name__)

# Skew uncertainty bound threshold: RTT > 50ms means uncertainty > ±25ms
CLOCK_SKEW_HIGH_RTT_THRESHOLD_MS = 50.0


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
    clock_skew_ms: float = 0.0

    # Standardized timing metrics in milliseconds
    joining_duration_ms: float | None = None
    server_processing_time_ms: float | None = None
    network_transport_time_ms: float | None = None
    total_result_transfer_time_ms: float | None = None

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

        # 3. Network and transport time: from server event emission to client callback
        if t_client and t_event:
            raw_transport = (t_client - t_event).total_seconds() * 1000.0
            self.network_transport_time_ms = raw_transport + self.clock_skew_ms

        # 4. Total Result Transfer Time: from physical joining operation completion to client callback
        if t_client and t_end:
            raw_total = (t_client - t_end).total_seconds() * 1000.0
            self.total_result_transfer_time_ms = raw_total + self.clock_skew_ms


def extract_sample_from_event(
    event: Any,
    client_received: datetime,
    sample_id: int,
    endpoint: str,
    clock_skew_ms: float = 0.0,
) -> LatencySample:
    """Extracts all timestamps from an incoming JoiningSystemResultReadyEvent object."""
    sample = LatencySample(
        sample_id=sample_id,
        endpoint=endpoint,
        client_received_time=client_received,
        clock_skew_ms=clock_skew_ms,
    )

    # 1. Event Generation Time on Server Stack
    sample.event_time = getattr(event, "Time", None)

    # 2. Extract Result payload
    result = getattr(event, "Result", None)
    if result is None:
        result = event

    meta = getattr(result, "ResultMetaData", None)
    if meta is not None:
        sample.creation_time = getattr(meta, "CreationTime", None)

        proc_times = getattr(meta, "ProcessingTimes", None)
        if proc_times is not None:
            sample.start_time = getattr(proc_times, "StartTime", None)
            sample.end_time = getattr(proc_times, "EndTime", None)

    # Also check if ProcessingTimes is directly on Result (some server implementations)
    if sample.end_time is None:
        proc_times = getattr(result, "ProcessingTimes", None)
        if proc_times is not None:
            sample.start_time = getattr(proc_times, "StartTime", None)
            sample.end_time = getattr(proc_times, "EndTime", None)

    sample.calculate_metrics()
    return sample


async def calibrate_clock_skew(client: Client, num_probes: int = 3) -> float:
    """Measures relative clock drift between this client PC and the OPC UA controller.
    Uses multi-sample round-trip time (RTT) probing using Cristian's algorithm.
    Returns estimated skew in milliseconds.
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

            if server_now.tzinfo is None:
                server_now = server_now.replace(tzinfo=UTC)
            else:
                server_now = server_now.astimezone(UTC)

            rtt_ms = (t_after - t_before).total_seconds() * 1000.0
            if rtt_ms < best_rtt:
                best_rtt = rtt_ms
                client_midpoint = t_before + (t_after - t_before) / 2
                best_skew = (server_now - client_midpoint).total_seconds() * 1000.0

        if best_rtt != float("inf"):
            if best_rtt > CLOCK_SKEW_HIGH_RTT_THRESHOLD_MS:
                logger.warning(
                    f"Elevated RTT ({best_rtt:.1f}ms) during clock calibration with {client.server_url}. "
                    f"Clock skew uncertainty is ±{best_rtt / 2.0:.1f}ms."
                )
            return best_skew
        return 0.0
    except Exception as exc:
        logger.warning(f"Clock skew calibration failed for {client.server_url}: {exc}")
        return 0.0


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
