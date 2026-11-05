"""
Shared metric selection for all reporters, so every output uses the same basis and labels.

Statistics are computed from VALID samples only: an INCOMPLETE, DUPLICATE or UNMATCHED result
has no trustworthy timing. Received counts and the integrity audit still use all samples.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ..diagnostics import DiagnosticVerdict
from ..results import INTEGRITY_VALID, TIMING_SOURCE_WIRE, LatencySample, compute_statistics

# Round lines for the headline. The title uses the tightest line the 90% time is still under.
DELIVERY_TIME_BANDS_MS = (100.0, 200.0, 500.0)
# Kept for callers that still treat 500 ms as the plant-comfort line.
PLANT_COMFORT_DELIVERY_P90_MS = 500.0

OUTCOME_OK = "OK"
OUTCOME_INFORMATION = "INFORMATION"
OUTCOME_ACTION_NEEDED = "ACTION NEEDED"
NO_ACTION_NEEDED = "No Action Needed"
ACTION_NEEDED = "Action Needed"

_SOFT_FINDING_BOTTLENECKS = frozenset(
    {
        "LOCAL_HOST_CPU",
        "CLIENT_PROCESSING",
        "SERVER_PROCESSING_DURATION",
        "NETWORK_OR_TRANSPORT",
        "APPLICATION_OR_MIXED",
    }
)

_HEALTHY_BOTTLENECKS = frozenset(
    {
        "NONE",
        "NONE (OPC UA PIPELINE HEALTHY)",
        "NETWORK_AND_WIRE_HEALTHY",
    }
)

_FINDING_BLURBS: dict[str, str] = {
    "NONE (OPC UA PIPELINE HEALTHY)": ("Result path looks healthy on this run (under the ~100 ms industrial guide)."),
    "NONE": "Result path looks healthy on this run.",
    "NETWORK_AND_WIRE_HEALTHY": "Result path looks healthy on this run.",
    "LOCAL_HOST_CPU": ("Client and simulators share this PC — delay is local CPU, not the factory network."),
    "CLIENT_PROCESSING": "Client was busy decoding or handling results.",
    "SERVER_PROCESSING_DURATION": ("Server took longer to publish the result after the join finished."),
    "NETWORK_OR_TRANSPORT": ("Delay seen on the path from server event to client receive (not proven NIC wire time)."),
    "APPLICATION_OR_MIXED": "Mixed delays across server, path, and client stages.",
    "NO_DATA": "No result samples were collected during the measurement window.",
}

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
        "Statistics Policy: Statistics use Results Used For Stats only (integrity OK); without wire timing, delivery falls back to handler time.",
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
        f"Results Received: {len(samples)} | Results Used For Stats: {len(valid)} | "
        f"Wire Timing: {wire_timing_count(valid)}/{len(valid)} | Distinct Servers: {distinct_servers}"
    )


def _format_int(n: int) -> str:
    return f"{n:,}"


@dataclass(frozen=True)
class ScaleSummary:
    """Management-clear server × results-per-server scale for human reports."""

    servers: int
    total_results: int
    valid_results: int
    results_per_server_text: str
    total_results_text: str
    per_server_min: int
    per_server_max: int
    target_per_server: int | None


def summarize_scale(
    samples: Sequence[LatencySample],
    *,
    samples_per_endpoint: int | None = None,
) -> ScaleSummary:
    """Build scale strings: servers, results per server, and total as an explicit product when uniform."""
    by_endpoint: dict[str, list[LatencySample]] = defaultdict(list)
    for s in samples:
        by_endpoint[s.endpoint].append(s)

    servers = len(by_endpoint)
    total = len(samples)
    valid = len(valid_samples(samples))
    target = samples_per_endpoint if samples_per_endpoint and samples_per_endpoint > 0 else None

    if servers == 0:
        per_text = "0" if target is None else f"0 (target {target})"
        total_text = "0"
        return ScaleSummary(
            servers=0,
            total_results=0,
            valid_results=0,
            results_per_server_text=per_text,
            total_results_text=total_text,
            per_server_min=0,
            per_server_max=0,
            target_per_server=target,
        )

    counts = [len(eps) for eps in by_endpoint.values()]
    lo, hi = min(counts), max(counts)
    if lo == hi:
        per = lo
        per_text = str(per) if target is None or target == per else f"{per} (target {target})"
        total_text = f"{_format_int(total)} ({_format_int(servers)} servers × {per} each)"
    else:
        if target is not None:
            per_text = f"{lo}–{hi} (target {target}; varies by server)"
        else:
            per_text = f"{lo}–{hi} (varies by server)"
        total_text = _format_int(total)

    return ScaleSummary(
        servers=servers,
        total_results=total,
        valid_results=valid,
        results_per_server_text=per_text,
        total_results_text=total_text,
        per_server_min=lo,
        per_server_max=hi,
        target_per_server=target,
    )


@dataclass(frozen=True)
class ReportOutcome:
    """Headline for a performance run: tightest true time band, then whether action is needed."""

    label: str
    footer: str
    what_this_means: str
    suggested_next_step: str
    time_band: str
    action: str
    summary: str


def delivery_time_band(p90_ms: float | None) -> str:
    """Tightest true round line: Under 100 ms, Under 200 ms, Under 500 ms, or Over 500 ms."""
    if p90_ms is None:
        return "No Results"
    for bound in DELIVERY_TIME_BANDS_MS:
        if p90_ms < bound:
            return f"Under {bound:.0f} ms"
    return "Over 500 ms"


def finding_blurb(bottleneck: str, fallback: str = "") -> str:
    """Short management wording for a stable bottleneck code."""
    text = _FINDING_BLURBS.get(bottleneck)
    if text:
        return text
    cleaned = (fallback or "").strip()
    return cleaned or f"See bottleneck code {bottleneck}."


def classify_report_outcome(
    verdict: DiagnosticVerdict,
    samples: Sequence[LatencySample],
    *,
    scale: ScaleSummary | None = None,
    fail_p90_ms: float | None = None,
    fail_p90_client_ready_ms: float | None = None,
    gate_failed: bool = False,
) -> ReportOutcome:
    """Map integrity, optional SLA limits, and delivery P90 to a time band and an action."""
    _ = scale  # Callers still pass scale; the headline no longer depends on it.
    valid = valid_samples(samples)
    total = len(samples)
    valid_n = len(valid)
    delivery_vals = metric_values(valid, "delivery_time_ms")
    delivery_p90 = compute_statistics(delivery_vals)["p90"] if delivery_vals else 0.0
    client_ready_vals = metric_values(valid, "client_ready_time_ms")
    client_ready_p90 = compute_statistics(client_ready_vals)["p90"] if client_ready_vals else 0.0

    metrics = verdict.metrics_summary or {}
    if not delivery_vals and "delivery_p90_ms" in metrics:
        delivery_p90 = float(metrics["delivery_p90_ms"])
    if not client_ready_vals and "client_ready_p90_ms" in metrics:
        client_ready_p90 = float(metrics["client_ready_p90_ms"])

    bottleneck = verdict.primary_bottleneck
    means = finding_blurb(bottleneck, verdict.explanation)
    next_step = (verdict.recommendation or "").strip() or "Review the Detail section and re-run if needed."
    has_delivery = bool(delivery_vals) or "delivery_p90_ms" in metrics
    time_band = delivery_time_band(delivery_p90 if has_delivery else None)

    integrity_bad = total == 0 or valid_n < total or bottleneck == "NO_DATA"
    limit_missed = fail_p90_ms is not None and valid and delivery_p90 > fail_p90_ms
    client_ready_missed = fail_p90_client_ready_ms is not None and valid and client_ready_p90 > fail_p90_client_ready_ms
    action_needed = integrity_bad or limit_missed or client_ready_missed or gate_failed
    if integrity_bad or gate_failed:
        legacy_label = OUTCOME_ACTION_NEEDED
    elif limit_missed or client_ready_missed:
        legacy_label = OUTCOME_ACTION_NEEDED
    elif bottleneck in _SOFT_FINDING_BOTTLENECKS or (bool(valid) and delivery_p90 >= PLANT_COMFORT_DELIVERY_P90_MS):
        legacy_label = OUTCOME_INFORMATION
    else:
        legacy_label = OUTCOME_OK

    sentences: list[str] = []
    if not has_delivery:
        sentences.append("No results were collected.")
    else:
        sentences.append(f"90% arrived within {delivery_p90:.1f} ms.")
    if bottleneck == "LOCAL_HOST_CPU":
        sentences.append("Client and servers were on one computer.")
    if limit_missed and fail_p90_ms is not None:
        sentences.append(f"The limit you set was {fail_p90_ms:.0f} ms.")
    if client_ready_missed and fail_p90_client_ready_ms is not None:
        sentences.append(f"The client-ready limit you set was {fail_p90_client_ready_ms:.0f} ms.")
    if total and valid_n < total:
        sentences.append(f"{total - valid_n:,} of {total:,} results could not be used.")
    if gate_failed and not integrity_bad and not limit_missed and not client_ready_missed:
        sentences.append("The quality gate failed.")
    summary = " ".join(sentences)
    action = ACTION_NEEDED if action_needed else NO_ACTION_NEEDED
    return ReportOutcome(
        label=legacy_label,
        footer=f"{time_band} — {action} — {summary}",
        what_this_means=means,
        suggested_next_step=next_step,
        time_band=time_band,
        action=action,
        summary=summary,
    )


def headline_metric_rows() -> list[tuple[str, str]]:
    """Delivery + total transfer — primary latency pair (Title Case labels for summary boxes)."""
    return [
        ("delivery_time_ms", "Delivery Time"),
        ("total_result_transfer_time_ms", "Total Transfer Time"),
    ]


def detail_metric_rows(valid: Sequence[LatencySample]) -> list[tuple[str, str]]:
    """Non-headline metric rows for the DETAIL section."""
    headline_attrs = {attr for attr, _ in headline_metric_rows()}
    return [(attr, label) for attr, label in visible_metric_rows(valid) if attr not in headline_attrs]
