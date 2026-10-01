"""
Markdown Reporter: Formats GitHub Flavored Markdown for GHA Step Summaries.
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


def generate_markdown_report(
    samples: list[LatencySample],
    verdict: DiagnosticVerdict,
    pool_name: str,
    timing: Mapping[str, Any] | None = None,
) -> str:
    """Generate a clean GitHub Flavored Markdown summary."""
    valid = valid_samples(samples)

    from collections import defaultdict

    by_endpoint: dict[str, list[LatencySample]] = defaultdict(list)
    for s in samples:
        by_endpoint[s.endpoint].append(s)

    lines = [
        f"## ⚡ IJT Performance & Scale Benchmark: {pool_name}",
        "",
        f"{summary_line(samples, len(by_endpoint))} | Primary attribution: `{verdict.primary_bottleneck}`",
        "",
    ]

    if len(by_endpoint) > 1:
        lines.extend(
            [
                f"### 🏭 Per-Server Latency Breakdown ({len(by_endpoint)} Servers)",
                "",
                "Delivery time of VALID results.",
                "",
                "| Server Endpoint | Valid | Average | 90% under | Fastest | Slowest | Clock offset |",
                "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
            ]
        )
        for ep, ep_samples in sorted(by_endpoint.items()):
            ep_valid = valid_samples(ep_samples)
            st = compute_statistics(metric_values(ep_valid, HEADLINE_METRIC))
            skews = [s.clock_skew_ms for s in ep_samples if s.clock_skew_ms is not None]
            skew_str = format_clock_offset(skews[0] if skews else None)
            if st["count"] == 0:
                lines.append(f"| `{ep}` | {len(ep_valid)} | N/A | N/A | N/A | N/A | {skew_str} |")
            else:
                lines.append(
                    f"| `{ep}` | {len(ep_valid)} | {st['mean']:.1f} ms | "
                    f"**{st['p90']:.1f} ms** | {st['min']:.1f} ms | {st['max']:.1f} ms | {skew_str} |"
                )
        lines.append("")
        lines.append("### ⏱️ Fleet Aggregate Latency (All Servers)")
    else:
        lines.append("### ⏱️ Latency (Milliseconds)")

    invalid_samples = [s for s in samples if s.integrity_status != "VALID"]
    if invalid_samples:
        lines.extend(
            [
                "",
                f"### 🛡️ Benchmark Integrity Audit ({len(invalid_samples)} issues detected)",
                "",
                "| Server Endpoint | Received | Valid | Incomplete | Duplicate | Unmatched |",
                "| :--- | :---: | :---: | :---: | :---: | :---: |",
            ]
        )
        for ep, ep_samples in sorted(by_endpoint.items()):
            n_recv = len(ep_samples)
            n_valid = sum(1 for s in ep_samples if s.integrity_status == "VALID")
            n_incomp = sum(1 for s in ep_samples if s.integrity_status == "INCOMPLETE")
            n_dup = sum(1 for s in ep_samples if s.integrity_status == "DUPLICATE")
            n_unmatch = sum(1 for s in ep_samples if s.integrity_status == "UNMATCHED")
            lines.append(f"| `{ep}` | {n_recv} | {n_valid} | {n_incomp} | {n_dup} | {n_unmatch} |")

    lines.append("")
    lines.append("| Interval / Stage | Fastest | Average | 90% under | 99% under | Slowest | Spread |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    def fmt_row(label: str, st: dict[str, float]) -> str:
        if st["count"] == 0:
            return f"| **{label}** | N/A | N/A | N/A | N/A | N/A | N/A |"
        return (
            f"| **{label}** | {st['min']:.1f} ms | {st['mean']:.1f} ms | "
            f"**{st['p90']:.1f} ms** | {st['p99']:.1f} ms | {st['max']:.1f} ms | {st['stdev']:.1f} ms |"
        )

    rows = visible_metric_rows(valid)
    for attr, label in rows:
        lines.append(fmt_row(label, compute_statistics(metric_values(valid, attr))))
    notes = report_notes(valid, timing)
    if notes:
        lines.append("")
        lines.extend(f"> **Note:** {note}  " for note in notes)

    lines.extend(
        [
            "",
            "> **Plain-English Guide to the Metrics:**",
            "> - **Fastest (Min):** Minimum value observed across VALID results.",
            "> - **Average (Mean):** Mean value across VALID results.",
            "> - **90% under (P90):** 90 of every 100 results were at or below this time.",
            "> - **99% under (P99):** 99 of every 100 results were at or below this time; shows rare spikes.",
            "> - **Slowest (Max):** The single slowest result recorded during the benchmark.",
            *(f"> - {line}" for line in metric_guide(rows)),
            "",
            "### 🔍 Likely Cause of Delay",
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
