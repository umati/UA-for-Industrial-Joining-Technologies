"""
Markdown Reporter: Formats GitHub Flavored Markdown for GHA Step Summaries and perf-fleet.md.
"""

from __future__ import annotations

from collections import defaultdict
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
    valid_samples,
    visible_metric_rows,
    wire_timing_count,
)


def generate_markdown_report(
    samples: list[LatencySample],
    verdict: DiagnosticVerdict,
    pool_name: str,
    timing: Mapping[str, Any] | None = None,
) -> str:
    """Generate a clean GitHub Flavored Markdown summary."""
    valid = valid_samples(samples)

    by_endpoint: dict[str, list[LatencySample]] = defaultdict(list)
    for s in samples:
        by_endpoint[s.endpoint].append(s)

    total_samples = len(samples)
    valid_count = len(valid)
    num_servers = len(by_endpoint)
    valid_pct = (valid_count / total_samples * 100.0) if total_samples > 0 else 0.0
    wire_count = wire_timing_count(valid)
    wire_pct = (wire_count / valid_count * 100.0) if valid_count > 0 else 0.0

    lines = [
        f"## ⚡ IJT Performance & Scale Benchmark: {pool_name}",
        "",
        "### 📋 Benchmark Execution Summary",
        "",
        "| Parameter | Value |",
        "| :--- | :--- |",
        f"| **Target Endpoints** | {num_servers} active servers |",
        f"| **Results Received** | {total_samples} total |",
        f"| **Integrity Audit** | {valid_count} valid ({valid_pct:.1f}% valid rate) |",
    ]

    if wire_count > 0:
        lines.append(f"| **Wire Timing Status** | {wire_count}/{valid_count} verified ({wire_pct:.1f}%) |")
    else:
        lines.append(f"| **Wire Timing Status** | 0/{valid_count} (handler timestamps used) |")

    if timing and timing.get("workers_reported"):
        lines.append(f"| **Worker Processes** | {timing['workers_reported']} background workers |")

    lines.append(f"| **Primary Bottleneck** | `{verdict.primary_bottleneck}` |")
    lines.append("")

    if num_servers > 1:
        is_large_fleet = num_servers > 10
        if is_large_fleet:
            srv_title = f"### 🏭 Per-Server Latency Breakdown (Top 5 Slowest of {num_servers} Servers)"
            sorted_eps = sorted(
                by_endpoint.items(),
                key=lambda item: compute_statistics(metric_values(valid_samples(item[1]), HEADLINE_METRIC))["p90"],
                reverse=True,
            )
            display_eps = sorted_eps[:5]
        else:
            srv_title = f"### 🏭 Per-Server Latency Breakdown ({num_servers} Servers)"
            display_eps = sorted(by_endpoint.items())

        lines.extend(
            [
                srv_title,
                "",
                "Delivery time of VALID results.",
                "",
                "| Server Endpoint | Valid | Average | 90% under | Fastest | Slowest | Clock offset |",
                "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
            ]
        )
        for ep, ep_samples in display_eps:
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
        if is_large_fleet:
            lines.append("")
            lines.append(
                f"*> Showing top 5 slowest endpoints. Complete {num_servers}-server data is recorded in `perf-fleet.csv`.*"
            )
        lines.append("")
        lines.append("### ⏱️ Fleet Aggregate Latency (All Servers)")
    else:
        lines.append("### ⏱️ Latency (Milliseconds)")

    invalid_samples = [s for s in samples if s.integrity_status != "VALID"]
    if invalid_samples:
        problematic_eps = [
            (ep, eps) for ep, eps in sorted(by_endpoint.items()) if any(s.integrity_status != "VALID" for s in eps)
        ]
        display_audits = problematic_eps if len(problematic_eps) <= 10 else problematic_eps[:10]
        lines.extend(
            [
                "",
                f"### 🛡️ Benchmark Integrity Audit ({len(invalid_samples)} issues detected)",
                "",
                "| Server Endpoint | Received | Valid | Incomplete | Duplicate | Unmatched |",
                "| :--- | :---: | :---: | :---: | :---: | :---: |",
            ]
        )
        for ep, ep_samples in display_audits:
            n_recv = len(ep_samples)
            n_valid = sum(1 for s in ep_samples if s.integrity_status == "VALID")
            n_incomp = sum(1 for s in ep_samples if s.integrity_status == "INCOMPLETE")
            n_dup = sum(1 for s in ep_samples if s.integrity_status == "DUPLICATE")
            n_unmatch = sum(1 for s in ep_samples if s.integrity_status == "UNMATCHED")
            lines.append(f"| `{ep}` | {n_recv} | {n_valid} | {n_incomp} | {n_dup} | {n_unmatch} |")
        if len(problematic_eps) > 10:
            lines.append("")
            lines.append(
                f"*> Showing 10 of {len(problematic_eps)} affected endpoints. Complete audit is in `report.json`.*"
            )

    lines.append("")
    lines.append("| Metric Stage | Fastest | Average | 90% under | 99% under | Slowest | Spread |")
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

    # 4. Metric Definitions & Run Notes Table
    guide_lines = metric_guide(rows)
    guide_items: list[tuple[str, str]] = []
    for g in guide_lines:
        if ":" in g:
            k, v = g.split(":", 1)
            guide_items.append((k.strip(), v.strip()))
        else:
            guide_items.append(("General Guidance", g.strip()))

    percentile_items = [
        ("Fastest (Min)", "Minimum Latency observed across all VALID results."),
        ("Average (Mean)", "Arithmetic Mean duration across all VALID results."),
        ("90% under (P90)", "90% of all operations completed within or under this duration."),
        ("99% under (P99)", "99% of all operations completed within or under this duration (detects tail spikes)."),
        ("Slowest (Max)", "Single slowest operation observed during the entire benchmark run."),
    ]

    all_note_items: list[tuple[str, str]] = []
    all_note_items.extend(guide_items)
    all_note_items.extend(percentile_items)
    notes = report_notes(valid, timing)
    if notes:
        for note in notes:
            if ":" in note:
                nk, nv = note.split(":", 1)
                all_note_items.append((nk.strip(), nv.strip()))
            else:
                all_note_items.append(("Operational Note", note.strip()))

    lines.extend(
        [
            "",
            "### 📖 Metric Definitions & Run Notes",
            "",
            "| Metric / Item | Description |",
            "| :--- | :--- |",
        ]
    )
    for k, v in all_note_items:
        lines.append(f"| **{k}** | {v} |")

    # 5. Diagnostic Assessment / Bottleneck Table
    lines.extend(
        [
            "",
            "### 🩺 Diagnostic Assessment & Bottleneck Analysis",
            "",
            "| Diagnostic Field | Assessment Details |",
            "| :--- | :--- |",
            f"| **Primary Bottleneck** | `{verdict.primary_bottleneck}` |",
            f"| **Assessment Headline** | {verdict.headline} |",
            f"| **Root Cause Analysis** | {verdict.explanation} |",
            f"| **Recommended Action** | {verdict.recommendation} |",
        ]
    )

    if verdict.warnings:
        lines.append("")
        lines.append("### ⚠️ Advisories & Environmental Warnings")
        lines.append("")
        for w in verdict.warnings:
            lines.append(f"- ⚠️ {w}")

    # 6. Status Verdict
    is_healthy = verdict.primary_bottleneck in (
        "NONE",
        "NONE (OPC UA PIPELINE HEALTHY)",
        "NETWORK_AND_WIRE_HEALTHY",
    )
    lines.append("")
    if is_healthy:
        lines.append("> **✔ ALL PERFORMANCE CHECKS PASSED — SYSTEM HEALTHY**")
    else:
        lines.append(f"> **▶ BENCHMARK COMPLETED — ACTION REQUIRED ({verdict.primary_bottleneck})**")
    lines.append("")

    return "\n".join(lines)
