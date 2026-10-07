"""
Shared metric selection for all reporters, so every output uses the same basis and labels.

Statistics are computed from VALID samples only: an INCOMPLETE, DUPLICATE or UNMATCHED result
has no trustworthy timing. Received counts and the integrity audit still use all samples.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from ..results import INTEGRITY_VALID, TIMING_SOURCE_WIRE, LatencySample

# (LatencySample attribute, report label, always shown). Optional rows are shown only when they have data.
METRIC_ROWS: list[tuple[str, str, bool]] = [
    ("delivery_time_ms", "End-to-End Delivery Time", True),
    ("client_ready_time_ms", "Client-Ready Time", True),
    ("total_result_transfer_time_ms", "Total Result Transfer Time", True),
    ("server_processing_time_ms", "Server Processing Duration", True),
    ("network_transport_time_ms", "Network Transport Latency", True),
    ("client_decode_time_ms", "Client Decode Time", False),
    ("dispatch_delay_ms", "Dispatch Delay", False),
    ("joining_duration_ms", "Joining Duration", False),
]

HEADLINE_METRIC = "delivery_time_ms"

# (metric attribute or None for general lines, explanation). Metric lines are shown only when their row is shown.
METRIC_GUIDE: list[tuple[str | None, str]] = [
    (
        "delivery_time_ms",
        "End-to-End Delivery Time: Time from Operation End until raw bytes arrive at the client.",
    ),
    (
        "client_ready_time_ms",
        "Client-Ready Time: Time until result is completely decoded and ready for application use.",
    ),
    (
        "total_result_transfer_time_ms",
        "Total Result Transfer Time: Operation End to Application Handler (includes time waiting for client loop).",
    ),
    (
        "server_processing_time_ms",
        "Server Processing Duration: Operation End to Server Event Timestamp (time the server needed to publish).",
    ),
    (
        "network_transport_time_ms",
        "Network Transport Latency: Server Event Timestamp to Application Handler (includes client decode and dispatch).",
    ),
    ("client_decode_time_ms", "Client Decode Time: Raw result bytes read to decoded object in client memory."),
    (
        "dispatch_delay_ms",
        "Dispatch Delay: Decoded result to Application Handler invocation (waiting for client loop to be free).",
    ),
    ("joining_duration_ms", "Joining Duration: Time the joining operation itself took on the server controller."),
    (
        None,
        "Statistics Policy: Statistics use VALID results only; without wire timing, delivery falls back to handler time.",
    ),
    (None, "Clock Offset: Server Clock minus Client Clock, used to synchronize cross-machine timestamps."),
]


# Shown only when the server stamps its event later than the operation end; otherwise both equal Total.
_SERVER_SPLIT_ROWS = frozenset({"server_processing_time_ms", "network_transport_time_ms"})


def server_reports_processing_time(valid: Sequence[LatencySample]) -> bool:
    return any(abs(v) >= 0.05 for v in metric_values(valid, "server_processing_time_ms"))


def visible_metric_rows(valid: Sequence[LatencySample]) -> list[tuple[str, str]]:
    """Rows for human reports: drop empty optional rows and rows that only repeat Total."""
    hide_split = bool(valid) and not server_reports_processing_time(valid)
    return [
        (attr, label)
        for attr, label, always in METRIC_ROWS
        if not (hide_split and attr in _SERVER_SPLIT_ROWS) and (always or metric_values(valid, attr))
    ]


def metric_guide(rows: Sequence[tuple[str, str]]) -> list[str]:
    """Explanations for the shown rows only, plus the general lines."""
    shown = {attr for attr, _label in rows}
    return [text for attr, text in METRIC_GUIDE if attr is None or attr in shown]


def report_notes(valid: Sequence[LatencySample], timing: Mapping[str, Any] | None) -> list[str]:
    """Run-specific notes shown under the metric table (console and Markdown)."""
    notes: list[str] = []
    if valid and not server_reports_processing_time(valid):
        notes.append(
            "Server Processing and Network Transport rows hidden: the server stamps its event at the "
            "Operation End Time, so both equal Total Result Transfer Time."
        )
    if timing and timing.get("workers_reported"):
        notes.append(
            f"Client Busy Delay (Loop Lag): Worst loop lag {float(timing.get('loop_lag_max_ms', 0.0)):.1f} ms, "
            f"worst worker average {float(timing.get('loop_lag_worst_mean_ms', 0.0)):.1f} ms. "
            "High values mean the client was busy, which also delays the measured delivery time."
        )
    return notes


def format_clock_offset(offset_ms: float | None) -> str:
    """Human-readable server clock offset (server minus client), e.g. "+12.0 ms (server ahead)"."""
    if offset_ms is None:
        return "not measured"
    if abs(offset_ms) < 0.05:
        return "0.0 ms (in sync)"
    return f"{offset_ms:+.1f} ms (server {'ahead' if offset_ms > 0 else 'behind'})"


def valid_samples(samples: Sequence[LatencySample]) -> list[LatencySample]:
    return [s for s in samples if s.integrity_status == INTEGRITY_VALID]


def metric_values(samples: Sequence[LatencySample], attr: str) -> list[float]:
    return [v for s in samples if (v := getattr(s, attr)) is not None]


def wire_timing_count(samples: Sequence[LatencySample]) -> int:
    return sum(1 for s in samples if s.timing_source == TIMING_SOURCE_WIRE)


def integrity_counts(samples: Sequence[LatencySample]) -> Counter[str]:
    return Counter(s.integrity_status for s in samples)


def summary_line(samples: Sequence[LatencySample], distinct_servers: int) -> str:
    valid = valid_samples(samples)
    return (
        f"Results received: {len(samples)} | VALID (used for statistics): {len(valid)} | "
        f"Wire timing: {wire_timing_count(valid)}/{len(valid)} | Distinct servers: {distinct_servers}"
    )
