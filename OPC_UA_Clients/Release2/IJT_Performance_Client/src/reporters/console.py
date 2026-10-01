"""
Console Reporter: Outputs clean, readable terminal tables with percentiles.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..diagnostics import DiagnosticVerdict
from ..results import LatencySample, compute_statistics
from ._metrics import (
    HEADLINE_METRIC,
    format_clock_offset,
    metric_guide,
    metric_values,
    report_notes,
    summary_line,
    valid_samples,
    visible_metric_rows,
)


def print_console_report(
    samples: list[LatencySample],
    verdict: DiagnosticVerdict,
    pool_name: str,
    timing: Mapping[str, Any] | None = None,
) -> None:
    """Print an ANSI-enhanced terminal summary table."""
    valid = valid_samples(samples)

    from collections import defaultdict

    by_endpoint: dict[str, list[LatencySample]] = defaultdict(list)
    for s in samples:
        by_endpoint[s.endpoint].append(s)

    sep = "=" * 94
    dash = "-" * 94

    print(f"\n{sep}")
    print(f"  IJT PERFORMANCE & SCALE BENCHMARK REPORT: {pool_name}")
    print(f"{sep}")
    print(f"  {summary_line(samples, len(by_endpoint))}")

    if len(by_endpoint) > 1:
        print(dash)
        print(f"  PER-SERVER BREAKDOWN ({len(by_endpoint)} Servers, VALID delivery time):")
        print(dash)
        print(
            f"  {'Endpoint':<35} | {'Valid':>7} | {'Average':>9} | {'90% under':>13} | {'Slowest':>9} | {'Clock offset':>24}"
        )
        print(dash)
        for ep, ep_samples in sorted(by_endpoint.items()):
            ep_valid = valid_samples(ep_samples)
            st = compute_statistics(metric_values(ep_valid, HEADLINE_METRIC))
            skews = [s.clock_skew_ms for s in ep_samples if s.clock_skew_ms is not None]
            skew_str = format_clock_offset(skews[0] if skews else None)
            if st["count"] == 0:
                print(f"  {ep:<35} | {len(ep_valid):>7} | {'N/A':>9} | {'N/A':>13} | {'N/A':>9} | {skew_str:>24}")
            else:
                print(
                    f"  {ep:<35} | {len(ep_valid):>7} | {st['mean']:>7.1f}ms | "
                    f"{st['p90']:>11.1f}ms | {st['max']:>7.1f}ms | {skew_str:>24}"
                )
        print(dash)
        print("  FLEET AGGREGATE SUMMARY (All Servers):")

    invalid_samples = [s for s in samples if s.integrity_status != "VALID"]
    if invalid_samples:
        print(dash)
        print(f"  BENCHMARK INTEGRITY AUDIT ({len(invalid_samples)} issues detected):")
        print(dash)
        print(
            f"  {'Endpoint':<35} | {'Received':>8} | {'Valid':>6} | {'Incomp':>7} | {'Duplicate':>9} | {'Unmatch':>7}"
        )
        print(dash)
        for ep, ep_samples in sorted(by_endpoint.items()):
            n_recv = len(ep_samples)
            n_valid = sum(1 for s in ep_samples if s.integrity_status == "VALID")
            n_incomp = sum(1 for s in ep_samples if s.integrity_status == "INCOMPLETE")
            n_dup = sum(1 for s in ep_samples if s.integrity_status == "DUPLICATE")
            n_unmatch = sum(1 for s in ep_samples if s.integrity_status == "UNMATCHED")
            print(f"  {ep:<35} | {n_recv:>8} | {n_valid:>6} | {n_incomp:>7} | {n_dup:>9} | {n_unmatch:>7}")

    print(dash)
    print(
        f"  {'Metric Stage':<28} | {'Fastest':>9} | {'Average':>9} | {'90% under':>13} | {'99% under':>14} | {'Slowest':>9}"
    )
    print(dash)

    def row(name: str, st: dict[str, float]) -> str:
        if st["count"] == 0:
            return f"  {name:<28} | {'N/A':>9} | {'N/A':>9} | {'N/A':>13} | {'N/A':>14} | {'N/A':>9}"
        return (
            f"  {name:<28} | {st['min']:>7.1f}ms | {st['mean']:>7.1f}ms | "
            f"{st['p90']:>11.1f}ms | {st['p99']:>12.1f}ms | {st['max']:>7.1f}ms"
        )

    rows = visible_metric_rows(valid)
    for attr, label in rows:
        print(row(label, compute_statistics(metric_values(valid, attr))))
    print(dash)
    for note in report_notes(valid, timing):
        print(f"  NOTE: {note}")
    for line in metric_guide(rows):
        print(f"  * {line}")
    print("  * Fastest:        Minimum value observed across VALID results")
    print("  * Average:        Mean value across VALID results")
    print("  * 90% under:      90 of every 100 results were at or below this time (P90)")
    print("  * 99% under:      99 of every 100 results were at or below this time (P99); shows rare spikes")
    print("  * Slowest:        The single slowest result observed during the entire run")

    print(dash)
    print("  LIKELY CAUSE OF DELAY:")
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
