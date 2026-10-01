"""
Heuristic Root-Cause Attribution Engine.

Analyzes multi-stage latency distributions and provides heuristic diagnostic indicators:
Is delay primarily observed in Server Processing vs. Network Transport vs. Client Processing?

Important Engineering Note:
- network_transport_time_ms is the elapsed time from server event emission to the client handler. It includes
  network transmission, OS socket buffering, asyncua decoding and client task dispatch.
- With wire timing (see src/engine/timing_hooks.py) the client-side part is split out as client decode time
  and dispatch delay, so a slow client can be told apart from a slow network.
- Wire timing is taken when the client event loop reads the bytes, so a busy client (loop lag) also delays it.
- When every endpoint is local (loopback), the network cannot be the cause: servers and client share the CPU.
- These are diagnostic indicators, not hardware network probe measurements.
- Attributions are advisory diagnostic indicators to guide investigation, not formal legal proofs.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..results import compute_statistics


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
    delivery_latencies: list[float] | None = None,
    client_ready_latencies: list[float] | None = None,
    client_decode_latencies: list[float] | None = None,
    dispatch_delays: list[float] | None = None,
    loop_lag_max_ms: float | None = None,
    all_endpoints_local: bool = False,
) -> DiagnosticVerdict:
    """Analyzes collected latency numbers and produces a heuristic diagnostic verdict.

    The client-side lists (decode, dispatch) only contain samples with wire timing.
    loop_lag_max_ms is the worst client event-loop stall; all_endpoints_local marks loopback-only runs.
    """
    stats_transport = compute_statistics(network_transport_latencies)
    stats_server = compute_statistics(server_processing_latencies)
    stats_total = compute_statistics(total_latencies)
    stats_delivery = compute_statistics(delivery_latencies or [])
    stats_ready = compute_statistics(client_ready_latencies or [])
    stats_decode = compute_statistics(client_decode_latencies or [])
    stats_dispatch = compute_statistics(dispatch_delays or [])

    warnings: list[str] = []

    # 1. Check for clock drift between server and client
    max_skew = max(abs(s) for s in clock_skews) if clock_skews else 0.0
    if max_skew > 100.0:
        warnings.append(
            f"Clock offset between a server and the client reaches {max_skew:.1f}ms. "
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
        "delivery_p90_ms": stats_delivery["p90"],
        "delivery_mean_ms": stats_delivery["mean"],
        "client_ready_p90_ms": stats_ready["p90"],
        "client_decode_p90_ms": stats_decode["p90"],
        "dispatch_delay_p90_ms": stats_dispatch["p90"],
        "loop_lag_max_ms": float(loop_lag_max_ms or 0.0),
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
                f"90% of results had a Total Result Transfer Time under {p90_total:.1f}ms "
                f"and a network transport time under {p90_transport:.1f}ms. "
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
                f"(90% under: server {p90_server:.1f}ms vs network transport {p90_transport:.1f}ms). "
                "The delay occurs inside the controller/server between joining operation completion and result event emission."
            ),
            recommendation=(
                "Investigate controller firmware result generation, payload assembly, step curve evaluation, or CPU load. "
                "Network transport is responsive once the event is emitted."
            ),
            metrics_summary=metrics,
            warnings=warnings,
        )

    has_wire_timing = stats_decode["count"] > 0
    lag_max = float(loop_lag_max_ms or 0.0)
    local_note = (
        " All servers run on this machine, so they compete with the client for CPU." if all_endpoints_local else ""
    )

    # --- Heuristic Rule 3: Client-side decoding or task dispatch dominant (needs wire timing) ---
    # Decode + dispatch are part of network_transport_time_ms; a third of it is already client-dominated,
    # and a loop stall as long as that client time means the measured delivery was delayed by the client too.
    p90_client_side = stats_decode["p90"] + stats_dispatch["p90"]
    if (
        has_wire_timing
        and p90_client_side > 100.0
        and (p90_client_side >= p90_transport / 3.0 or lag_max >= p90_client_side)
    ):
        return DiagnosticVerdict(
            primary_bottleneck="CLIENT_PROCESSING",
            headline="Client Too Busy: Decoding or Waiting to Handle Results",
            explanation=(
                f"90% under: client decode {stats_decode['p90']:.1f}ms and dispatch delay "
                f"{stats_dispatch['p90']:.1f}ms, out of {p90_transport:.1f}ms from server event to handler; "
                f"worst client busy delay (loop lag) {lag_max:.1f}ms. "
                "Results waited while the client was decoding or busy, which also delays the measured delivery time."
                + local_note
            ),
            recommendation=(
                "Run fewer servers per machine or move the simulators to another host; single-machine fleet runs "
                "measure this machine's CPU, not the network."
                if all_endpoints_local
                else "Reduce endpoints per worker (--workers), and check client CPU load and the client busy delay (loop lag)."
            ),
            metrics_summary=metrics,
            warnings=warnings,
        )

    # --- Heuristic Rule 4: Loopback-only run - there is no physical network to blame ---
    if all_endpoints_local:
        return DiagnosticVerdict(
            primary_bottleneck="LOCAL_HOST_CPU",
            headline="Client and Servers Share This Machine",
            explanation=(
                f"90% under: delivery {stats_delivery['p90']:.1f}ms, total {p90_total:.1f}ms; worst client busy "
                f"delay (loop lag) {lag_max:.1f}ms. Every endpoint is local, so the delay comes from server "
                "publishing and CPU contention between servers and client, not from a network."
            ),
            recommendation=(
                "Run fewer servers per machine or move the simulators to another host for network-realistic numbers."
            ),
            metrics_summary=metrics,
            warnings=warnings,
        )

    # --- Heuristic Rule 5: Transport / Socket buffer delay dominant ---
    # With wire timing, delivery excludes client decode/dispatch, so it is the better network indicator.
    use_delivery = has_wire_timing and stats_delivery["count"] > 0
    p90_network = stats_delivery["p90"] if use_delivery else p90_transport
    if p90_network > 300.0:
        return DiagnosticVerdict(
            primary_bottleneck="NETWORK_OR_TRANSPORT",
            headline="Network Transport / Socket Buffer Delay",
            explanation=(
                f"90% under: {'delivery' if use_delivery else 'network transport'} "
                f"{p90_network:.1f}ms out of {p90_total:.1f}ms total. "
                "Packets experienced transit delays, switch queueing, or OS socket buffering."
            ),
            recommendation="Inspect physical network switch bandwidth, socket buffer limits, or MTU fragmentation.",
            metrics_summary=metrics,
            warnings=warnings,
        )

    # --- Heuristic Rule 6: Mixed or general delay ---
    return DiagnosticVerdict(
        primary_bottleneck="APPLICATION_OR_MIXED",
        headline="Mixed Pipeline Latency Observed",
        explanation=(
            f"90% under: total {p90_total:.1f}ms (network transport {p90_transport:.1f}ms, server {p90_server:.1f}ms)."
        ),
        recommendation="Review client decoding time, client busy delay (loop lag), and individual controller performance logs.",
        metrics_summary=metrics,
        warnings=warnings,
    )
