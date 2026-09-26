"""
Console Reporter: Outputs clean, readable terminal tables with percentiles.
"""

from __future__ import annotations

from ..attribution import DiagnosticVerdict
from ..result_transfer_latency import LatencySample, compute_statistics


def print_console_report(
    samples: list[LatencySample],
    verdict: DiagnosticVerdict,
    pool_name: str,
) -> None:
    """Print an ANSI-enhanced terminal summary table."""
    totals = [s.total_result_transfer_time_ms for s in samples if s.total_result_transfer_time_ms is not None]
    transports = [s.network_transport_time_ms for s in samples if s.network_transport_time_ms is not None]
    servers = [s.server_processing_time_ms for s in samples if s.server_processing_time_ms is not None]
    joinings = [s.joining_duration_ms for s in samples if s.joining_duration_ms is not None]

    stat_total = compute_statistics(totals)
    stat_transport = compute_statistics(transports)
    stat_server = compute_statistics(servers)
    stat_joining = compute_statistics(joinings)

    sep = "=" * 80
    dash = "-" * 80

    print(f"\n{sep}")
    print(f"  IJT PERFORMANCE & SCALE BENCHMARK REPORT: {pool_name}")
    print(f"{sep}")
    print(f"  Total Samples Received: {len(samples)}")
    print(dash)
    print(f"  {'Metric Interval':<28} | {'Min':>8} | {'Mean':>8} | {'P90':>8} | {'P99':>8} | {'Max':>8}")
    print(dash)

    def row(name: str, st: dict[str, float]) -> str:
        if st["count"] == 0:
            return f"  {name:<28} | {'N/A':>8} | {'N/A':>8} | {'N/A':>8} | {'N/A':>8} | {'N/A':>8}"
        return (
            f"  {name:<28} | {st['min']:>7.1f}ms | {st['mean']:>7.1f}ms | "
            f"{st['p90']:>7.1f}ms | {st['p99']:>7.1f}ms | {st['max']:>7.1f}ms"
        )

    print(row("Total Result Transfer Time", stat_total))
    print(row("Server Processing Duration", stat_server))
    print(row("Network Transport Latency", stat_transport))
    if stat_joining["count"] > 0:
        print(row("Joining Duration", stat_joining))

    print(dash)
    print("  ROOT-CAUSE ATTRIBUTION VERDICT:")
    print(f"  [{verdict.primary_bottleneck}]")
    print(f"  >> {verdict.headline}")
    print(f"  >> {verdict.explanation}")
    print(f"  >> Recommendation: {verdict.recommendation}")

    if verdict.warnings:
        print(dash)
        print("  WARNINGS / ADVISORIES:")
        for w in verdict.warnings:
            print(f"  * {w}")

    print(f"{sep}\n")
