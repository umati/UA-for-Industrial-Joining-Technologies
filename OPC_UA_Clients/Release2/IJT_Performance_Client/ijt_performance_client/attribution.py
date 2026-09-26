"""
Heuristic Root-Cause Attribution Engine.

Analyzes multi-stage latency distributions and provides heuristic diagnostic indicators:
Is delay primarily observed in Server Processing vs. Network Transport vs. Client Architecture?

Important Engineering Note:
- network_transport_time_ms represents the elapsed duration between server event emission and client callback execution.
  This includes network transmission, operating system socket buffering, asyncua decoding, and client task dispatch.
  It is a heuristic indicator rather than a laboratory wire probe measurement.
- Attributions are advisory diagnostic indicators to guide investigation, not formal legal proofs.
"""

from __future__ import annotations

from dataclasses import dataclass

from .result_transfer_latency import compute_statistics


@dataclass
class DiagnosticVerdict:
    """The heuristic diagnosis of the benchmark run."""

    primary_bottleneck: str  # Short classification (e.g. SERVER_PROCESSING_DURATION)
    headline: str  # Clear 1-line summary
    explanation: str  # Detailed technical explanation with evidence
    recommendation: str  # Concrete next steps to guide engineering investigation
    metrics_summary: dict[str, float]  # Key P90 and mean numbers
    warnings: list[str]  # Environmental alerts (clock drift, thread explosion)


def evaluate_diagnostics(
    network_transport_latencies: list[float],
    server_processing_latencies: list[float],
    total_latencies: list[float],
    clock_skews: list[float],
    measured_thread_count: int | None = None,
    measured_process_count: int | None = None,
) -> DiagnosticVerdict:
    """Analyzes collected latency numbers and produces a heuristic diagnostic verdict."""
    stats_transport = compute_statistics(network_transport_latencies)
    stats_server = compute_statistics(server_processing_latencies)
    stats_total = compute_statistics(total_latencies)

    warnings: list[str] = []

    # 1. Check for clock drift between server and client
    max_skew = max(abs(s) for s in clock_skews) if clock_skews else 0.0
    if max_skew > 100.0:
        warnings.append(
            f"Clock drift across fleet reaches {max_skew:.1f}ms. "
            "Server and client clocks are out of sync. Ensure NTP or PTP time synchronization is running on controllers."
        )

    # 2. Check for real measured thread explosion on the client host
    if measured_thread_count is not None and measured_thread_count > 200:
        warnings.append(
            f"High measured client thread count ({measured_thread_count} OS threads). "
            "Risk of operating system context-switch latency and scheduler contention."
        )

    p90_total = stats_total["p90"]
    p90_transport = stats_transport["p90"]
    p90_server = stats_server["p90"] if stats_server["count"] > 0 else 0.0

    metrics = {
        "total_p90_ms": p90_total,
        "network_transport_p90_ms": p90_transport,
        "server_processing_p90_ms": p90_server,
        "total_mean_ms": stats_total["mean"],
        "network_transport_mean_ms": stats_transport["mean"],
        "measured_threads": float(measured_thread_count or 0),
        "measured_processes": float(measured_process_count or 0),
    }

    # If no samples were collected
    if stats_total["count"] == 0:
        return DiagnosticVerdict(
            primary_bottleneck="NO_DATA",
            headline="Zero Result Samples Collected",
            explanation="No result events were received during the measurement window.",
            recommendation="Verify server event generation, subscription filters, and tool triggers.",
            metrics_summary=metrics,
            warnings=warnings,
        )

    # --- Heuristic Rule 1: Pipeline is fast and healthy ---
    if p90_total < 100.0 and p90_transport < 50.0:
        return DiagnosticVerdict(
            primary_bottleneck="NONE (OPC UA PIPELINE HEALTHY)",
            headline="OPC UA Result Pipeline is Healthy and Responsive",
            explanation=(
                f"P90 Total Result Transfer Time is {p90_total:.1f}ms, "
                f"with network transport at {p90_transport:.1f}ms. "
                "Event delivery is performing within expected industrial cycle targets."
            ),
            recommendation="System meets normal manufacturing latency guidelines (< 100ms).",
            metrics_summary=metrics,
            warnings=warnings,
        )

    # --- Heuristic Rule 2: Server processing duration dominant ---
    if p90_server > 200.0 and p90_transport < 100.0:
        pct_server = (p90_server / p90_total) * 100.0 if p90_total > 0 else 0.0
        return DiagnosticVerdict(
            primary_bottleneck="SERVER_PROCESSING_DURATION",
            headline="Elevated Server Processing Duration Before Event Emission",
            explanation=(
                f"Server processing duration accounts for ~{pct_server:.0f}% of total result transfer time "
                f"(Server P90: {p90_server:.1f}ms vs Network Transport P90: {p90_transport:.1f}ms). "
                "The delay occurs inside the controller/server between joining operation completion and result event emission."
            ),
            recommendation=(
                "Investigate controller firmware result generation, payload assembly, step curve evaluation, or CPU load. "
                "Network transport is responsive once the event is emitted."
            ),
            metrics_summary=metrics,
            warnings=warnings,
        )

    # --- Heuristic Rule 3: Transport / Socket buffer delay dominant ---
    if p90_transport > 300.0:
        return DiagnosticVerdict(
            primary_bottleneck="NETWORK_OR_TRANSPORT",
            headline="Network Transport / Socket Buffer Delay",
            explanation=(
                f"Network transport latency P90 is {p90_transport:.1f}ms out of {p90_total:.1f}ms total. "
                "Packets experienced transit delays, switch queueing, or OS socket buffering."
            ),
            recommendation="Inspect physical network switch bandwidth, socket buffer limits, or MTU fragmentation.",
            metrics_summary=metrics,
            warnings=warnings,
        )

    # --- Heuristic Rule 4: Mixed or general delay ---
    return DiagnosticVerdict(
        primary_bottleneck="APPLICATION_OR_MIXED",
        headline="Mixed Pipeline Latency Observed",
        explanation=(
            f"Observed total P90 latency of {p90_total:.1f}ms (Network Transport: {p90_transport:.1f}ms, Server: {p90_server:.1f}ms)."
        ),
        recommendation="Review client deserialization, event loop lag, and individual controller performance logs.",
        metrics_summary=metrics,
        warnings=warnings,
    )
