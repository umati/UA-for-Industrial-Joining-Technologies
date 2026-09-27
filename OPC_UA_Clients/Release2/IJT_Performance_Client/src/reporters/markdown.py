"""
Markdown Reporter: Formats GitHub Flavored Markdown for GHA Step Summaries.
"""

from __future__ import annotations

from ..diagnostics import DiagnosticVerdict
from ..results import LatencySample, compute_statistics


def generate_markdown_report(
    samples: list[LatencySample],
    verdict: DiagnosticVerdict,
    pool_name: str,
) -> str:
    """Generate a clean GitHub Flavored Markdown summary."""
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

    lines = [
        f"## ⚡ IJT Performance & Scale Benchmark: {pool_name}",
        "",
        f"**Total Samples:** `{len(samples)}` | **Distinct Servers:** `{len(by_endpoint)}` | **Primary Attribution:** `{verdict.primary_bottleneck}`",
        "",
    ]

    if len(by_endpoint) > 1:
        lines.extend(
            [
                f"### 🏭 Per-Server Latency Breakdown ({len(by_endpoint)} Servers)",
                "",
                "| Server Endpoint | Samples | Mean | P90 | Min | Max | Clock Skew |",
                "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
            ]
        )
        for ep, ep_samples in sorted(by_endpoint.items()):
            ep_totals = [
                s.total_result_transfer_time_ms for s in ep_samples if s.total_result_transfer_time_ms is not None
            ]
            st = compute_statistics(ep_totals)
            skews = [s.clock_skew_ms for s in ep_samples if s.clock_skew_ms is not None]
            skew_str = f"{skews[0]:+.1f} ms" if skews else "0.0 ms"
            if st["count"] == 0:
                lines.append(f"| `{ep}` | {len(ep_samples)} | N/A | N/A | N/A | N/A | {skew_str} |")
            else:
                lines.append(
                    f"| `{ep}` | {len(ep_samples)} | {st['mean']:.1f} ms | "
                    f"**{st['p90']:.1f} ms** | {st['min']:.1f} ms | {st['max']:.1f} ms | {skew_str} |"
                )
        lines.append("")
        lines.append("### ⏱️ Fleet Aggregate Latency Percentiles (All Servers)")
    else:
        lines.append("### ⏱️ Latency Percentiles (Milliseconds)")

    lines.append("")
    lines.append("| Interval / Stage | Min | Mean | P90 | P99 | Max | StdDev |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    def fmt_row(label: str, st: dict[str, float]) -> str:
        if st["count"] == 0:
            return f"| **{label}** | N/A | N/A | N/A | N/A | N/A | N/A |"
        return (
            f"| **{label}** | {st['min']:.1f} ms | {st['mean']:.1f} ms | "
            f"**{st['p90']:.1f} ms** | {st['p99']:.1f} ms | {st['max']:.1f} ms | {st['stdev']:.1f} ms |"
        )

    lines.append(fmt_row("Total Result Transfer Time", stat_total))
    lines.append(fmt_row("Server Processing Duration", stat_server))
    lines.append(fmt_row("Network Transport Latency", stat_transport))
    if stat_joining["count"] > 0:
        lines.append(fmt_row("Joining Duration", stat_joining))

    lines.extend(
        [
            "",
            "### 🔍 Root-Cause Attribution Verdict",
            "",
            f"> **{verdict.headline}**  ",
            f"> {verdict.explanation}  ",
            f"> *Recommendation:* {verdict.recommendation}",
            "",
        ]
    )

    if verdict.warnings:
        lines.append("### ⚠️ Advisories & Environmental Warnings")
        lines.append("")
        for w in verdict.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    return "\n".join(lines)
