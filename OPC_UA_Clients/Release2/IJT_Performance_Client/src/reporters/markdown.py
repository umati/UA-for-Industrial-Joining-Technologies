"""
Markdown Reporter: Management-clear GitHub Flavored Markdown for perf-fleet.md (no emoji, no ANSI).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from ..diagnostics import DiagnosticVerdict
from ..results import LatencySample, compute_statistics
from ._metrics import (
    HEADLINE_METRIC,
    classify_report_outcome,
    detail_metric_rows,
    format_clock_offset,
    headline_metric_rows,
    metric_values,
    summarize_scale,
    valid_samples,
    wire_timing_count,
)


def generate_markdown_report(
    samples: list[LatencySample],
    verdict: DiagnosticVerdict,
    pool_name: str,
    timing: Mapping[str, Any] | None = None,
    *,
    samples_per_endpoint: int | None = None,
    fail_p90_ms: float | None = None,
    fail_p90_client_ready_ms: float | None = None,
    gate_failed: bool = False,
) -> str:
    """Generate a clean management-oriented Markdown summary."""
    valid = valid_samples(samples)
    by_endpoint: dict[str, list[LatencySample]] = defaultdict(list)
    for s in samples:
        by_endpoint[s.endpoint].append(s)

    scale = summarize_scale(samples, samples_per_endpoint=samples_per_endpoint)
    outcome = classify_report_outcome(
        verdict,
        samples,
        scale=scale,
        fail_p90_ms=fail_p90_ms,
        fail_p90_client_ready_ms=fail_p90_client_ready_ms,
        gate_failed=gate_failed,
    )

    valid_pct = (scale.valid_results / scale.total_results * 100.0) if scale.total_results else 0.0
    wire_count = wire_timing_count(valid)
    wire_pct = (wire_count / len(valid) * 100.0) if valid else 0.0

    lines = [
        f"## IJT Performance & Scale Benchmark: {pool_name}",
        "",
        "### Final Summary",
        "",
        "| Field | Detail |",
        "| :--- | :--- |",
        f"| **Time** | **{outcome.time_band}** |",
        f"| **Action** | **{outcome.action}** |",
        f"| **Detail** | {outcome.summary} |",
    ]
    if verdict.warnings:
        for idx, warning in enumerate(verdict.warnings, 1):
            lines.append(f"| **Note {idx}** | {warning} |")
    lines.extend(
        [
            "",
            "### Run Size",
            "",
            "| Parameter | Value |",
            "| :--- | :--- |",
            f"| **Servers Tested** | {scale.servers} |",
            f"| **Results Per Server** | {scale.results_per_server_text} |",
            f"| **Total Results** | {scale.total_results_text} |",
            f"| **Results Used For Stats** | {scale.valid_results:,} of {scale.total_results:,} ({valid_pct:.1f}%) |",
        ]
    )
    if wire_count > 0:
        lines.append(f"| **Wire Timing** | {wire_count}/{len(valid)} verified ({wire_pct:.1f}%) |")
    else:
        lines.append(f"| **Wire Timing** | 0/{len(valid)} (handler timestamps used) |")
    if timing and timing.get("workers_reported"):
        lines.append(f"| **Workers** | {timing['workers_reported']} |")
    lines.append("")

    lines.extend(
        [
            "### Result Latency",
            "",
            "| Metric | Average | 90% Under | Slowest |",
            "| :--- | :---: | :---: | :---: |",
        ]
    )
    for attr, label in headline_metric_rows():
        st = compute_statistics(metric_values(valid, attr))
        if st["count"] == 0:
            lines.append(f"| **{label}** | N/A | N/A | N/A |")
        else:
            lines.append(f"| **{label}** | {st['mean']:.1f} ms | **{st['p90']:.1f} ms** | {st['max']:.1f} ms |")
    lines.append("")

    if timing and timing.get("workers_reported") is not None:
        lag = float(timing.get("loop_lag_max_ms", 0.0) or 0.0)
        lag_mean = float(timing.get("loop_lag_worst_mean_ms", 0.0) or 0.0)
        lines.extend(
            [
                "### Client Busy Time",
                "",
                "| Field | Value |",
                "| :--- | :--- |",
                f"| **Worst** | {lag:.1f} ms |",
                f"| **Worst Worker Avg** | {lag_mean:.1f} ms |",
                "",
            ]
        )

    num_servers = scale.servers
    if num_servers > 1:
        is_large_fleet = num_servers > 10
        if is_large_fleet:
            srv_title = f"### Detail — Top 5 Slowest Of {num_servers} Servers"
            sorted_eps = sorted(
                by_endpoint.items(),
                key=lambda item: compute_statistics(metric_values(valid_samples(item[1]), HEADLINE_METRIC))["p90"],
                reverse=True,
            )
            display_eps = sorted_eps[:5]
        else:
            srv_title = f"### Detail — Per Server ({num_servers} Servers)"
            display_eps = sorted(by_endpoint.items())

        lines.extend(
            [
                srv_title,
                "",
                "Delivery Time for results used for stats (integrity OK).",
                "",
                "| Server Endpoint | For Stats | Average | 90% Under | Fastest | Slowest | Clock Offset |",
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
                f"*Showing top 5 slowest endpoints. Complete {num_servers}-server data is in `perf-fleet.csv`.*"
            )
        lines.append("")

    invalid_samples = [s for s in samples if s.integrity_status != "VALID"]
    if invalid_samples:
        problematic_eps = [
            (ep, eps) for ep, eps in sorted(by_endpoint.items()) if any(s.integrity_status != "VALID" for s in eps)
        ]
        display_audits = problematic_eps if len(problematic_eps) <= 10 else problematic_eps[:10]
        lines.extend(
            [
                f"### Detail — Integrity Audit ({len(invalid_samples)} Issues)",
                "",
                "| Server Endpoint | Received | For Stats | Incomplete | Duplicate | Unmatched |",
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
                f"*Showing 10 of {len(problematic_eps)} affected endpoints. Complete audit is in `report.json`.*"
            )
        lines.append("")

    detail_rows = detail_metric_rows(valid)
    if detail_rows:
        lines.extend(
            [
                "### Detail — Other Latency Stages",
                "",
                "| Metric Stage | Fastest | Average | 90% Under | 99% Under | Slowest |",
                "| :--- | :---: | :---: | :---: | :---: | :---: |",
            ]
        )
        for attr, label in detail_rows:
            st = compute_statistics(metric_values(valid, attr))
            if st["count"] == 0:
                lines.append(f"| **{label}** | N/A | N/A | N/A | N/A | N/A |")
            else:
                lines.append(
                    f"| **{label}** | {st['min']:.1f} ms | {st['mean']:.1f} ms | "
                    f"**{st['p90']:.1f} ms** | {st['p99']:.1f} ms | {st['max']:.1f} ms |"
                )
        lines.append("")

    lines.append(f"> **{outcome.footer}**")
    lines.append("")
    return "\n".join(lines)
