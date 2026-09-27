"""
Console Reporter: Outputs clean, readable terminal tables with percentiles.
"""

from __future__ import annotations

from ..diagnostics import DiagnosticVerdict
from ..results import LatencySample, compute_statistics


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

    from collections import defaultdict

    by_endpoint: dict[str, list[LatencySample]] = defaultdict(list)
    for s in samples:
        by_endpoint[s.endpoint].append(s)

    sep = "=" * 80
    dash = "-" * 80

    print(f"\n{sep}")
    print(f"  IJT PERFORMANCE & SCALE BENCHMARK REPORT: {pool_name}")
    print(f"{sep}")
    print(f"  Total Samples Received: {len(samples)}  |  Distinct Servers: {len(by_endpoint)}")

    if len(by_endpoint) > 1:
        print(dash)
        print(f"  PER-SERVER BREAKDOWN ({len(by_endpoint)} Servers):")
        print(dash)
        print(f"  {'Endpoint':<35} | {'Samples':>7} | {'Mean':>8} | {'P90':>8} | {'Max':>8} | {'Clock Skew':>10}")
        print(dash)
        for ep, ep_samples in sorted(by_endpoint.items()):
            ep_totals = [
                s.total_result_transfer_time_ms for s in ep_samples if s.total_result_transfer_time_ms is not None
            ]
            st = compute_statistics(ep_totals)
            skews = [s.clock_skew_ms for s in ep_samples if s.clock_skew_ms is not None]
            skew_str = f"{skews[0]:+.1f}ms" if skews else "0.0ms"
            if st["count"] == 0:
                print(f"  {ep:<35} | {len(ep_samples):>7} | {'N/A':>8} | {'N/A':>8} | {'N/A':>8} | {skew_str:>10}")
            else:
                print(
                    f"  {ep:<35} | {len(ep_samples):>7} | {st['mean']:>7.1f}ms | "
                    f"{st['p90']:>7.1f}ms | {st['max']:>7.1f}ms | {skew_str:>10}"
                )
        print(dash)
        print("  FLEET AGGREGATE SUMMARY (All Servers):")

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
