"""
Console Reporter: Outputs clean, readable terminal tables with percentiles.
"""

from __future__ import annotations

import os
import sys
import textwrap
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


def _enable_ansi_windows() -> bool:
    """Enable virtual-terminal processing on Windows 10+ consoles."""
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            return True
        return False
    except Exception:
        return False


def _safe_print(text: str = "") -> None:
    """Print text safely, re-encoding unencodable characters if stdout encoding is limited (e.g. cp1252)."""
    if hasattr(sys.stdout, "reconfigure") and getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, errors="replace").decode(encoding))


def print_console_report(
    samples: list[LatencySample],
    verdict: DiagnosticVerdict,
    pool_name: str,
    timing: Mapping[str, Any] | None = None,
) -> None:
    """Print an ANSI-enhanced terminal summary table modeled after the IJT Root Runner."""
    use_colour = sys.stdout.isatty() and (os.name != "nt" or _enable_ansi_windows())

    def _c(ansi: str, text: str) -> str:
        return f"{ansi}{text}\033[0m" if use_colour else text

    valid = valid_samples(samples)

    by_endpoint: dict[str, list[LatencySample]] = defaultdict(list)
    for s in samples:
        by_endpoint[s.endpoint].append(s)

    # Box-drawing Unicode glyphs
    H = "\u2500"  # ─
    V = "\u2502"  # │
    TL = "\u250c"  # ┌
    TR = "\u2510"  # ┐
    BL = "\u2514"  # └
    BR = "\u2518"  # ┘
    LM = "\u251c"  # ├
    RM = "\u2524"  # ┤
    TT = "\u252c"  # ┬
    BT = "\u2534"  # ┴
    CR = "\u253c"  # ┼

    # Standard table width: 115 characters (inner span: 113)
    box_w = 115

    def _box_span(lc: str, rc: str) -> str:
        return f"  {lc}{H * (box_w - 2)}{rc}"

    # 1. Double-line Banner Header matching root runner
    width = 64
    bar = "\u2550" * width
    pad = "FINAL SUMMARY".ljust(width - 2)

    _safe_print()
    _safe_print(_c("\033[96m\033[1m", f"  \u2554{bar}\u2557"))
    _safe_print(_c("\033[96m\033[1m", f"  \u2551  {pad}\u2551"))
    _safe_print(_c("\033[96m\033[1m", f"  \u255a{bar}\u255d"))
    _safe_print(f"  IJT PERFORMANCE & SCALE BENCHMARK REPORT: {pool_name}")
    _safe_print()

    # 2. Executive Run Metadata Box Table (Aligned colons, no crowded lines)
    total_samples = len(samples)
    valid_count = len(valid)
    num_servers = len(by_endpoint)
    valid_pct = (valid_count / total_samples * 100.0) if total_samples > 0 else 0.0
    wire_count = wire_timing_count(valid)
    wire_pct = (wire_count / valid_count * 100.0) if valid_count > 0 else 0.0

    meta_lw = 24
    meta_vw = box_w - meta_lw - 7  # 115 - 24 - 7 = 84

    def _meta_row(label: str, val: str) -> str:
        return f"  {V} {label:<{meta_lw}} : {val:<{meta_vw}} {V}"

    _safe_print(_box_span(TL, TR))
    _safe_print(f"  {V} {_c('\033[96m\033[1m', 'BENCHMARK EXECUTION SUMMARY:'.ljust(box_w - 4))} {V}")
    _safe_print(_box_span(LM, RM))
    _safe_print(_meta_row("Target Endpoints", f"{num_servers} active servers"))
    _safe_print(_box_span(LM, RM))
    _safe_print(_meta_row("Results Received", f"{total_samples} total"))
    _safe_print(_box_span(LM, RM))
    _safe_print(_meta_row("Integrity Audit", f"{valid_count} valid ({valid_pct:.1f}% valid rate)"))
    _safe_print(_box_span(LM, RM))
    if wire_count > 0:
        _safe_print(_meta_row("Wire Timing Samples", f"{wire_count}/{valid_count} verified ({wire_pct:.1f}%)"))
    else:
        _safe_print(_meta_row("Wire Timing Samples", f"0/{valid_count} (handler timestamps used)"))
    if timing and timing.get("workers_reported"):
        _safe_print(_box_span(LM, RM))
        _safe_print(_meta_row("Worker Processes", f"{timing['workers_reported']} background workers"))
    _safe_print(_box_span(LM, RM))
    _safe_print(_meta_row("Primary Bottleneck", verdict.primary_bottleneck))
    _safe_print(_box_span(BL, BR))
    _safe_print()

    # 3. Optional Per-Server Breakdown (Compact for fleets > 10 servers to preserve scrollback)
    if num_servers > 1:
        cw = [34, 6, 10, 12, 10, 24]
        # Sum cw = 96. Inner width: 96 + 17 = 113. Total box width: 115.

        def _srv_sep(lc: str, mid: str, rc: str) -> str:
            parts = [H * (w + 2) for w in cw]
            return f"  {lc}{mid.join(parts)}{rc}"

        def _srv_row(vals: list[str], is_header: bool = False) -> str:
            c0 = _c("\033[1m\033[97m", f"{vals[0]:<{cw[0]}}") if is_header else f"{vals[0]:<{cw[0]}}"
            c1 = _c("\033[1m\033[97m", f"{vals[1]:>{cw[1]}}") if is_header else f"{vals[1]:>{cw[1]}}"
            c2 = _c("\033[1m\033[97m", f"{vals[2]:>{cw[2]}}") if is_header else f"{vals[2]:>{cw[2]}}"
            c3 = _c("\033[1m\033[97m", f"{vals[3]:>{cw[3]}}") if is_header else f"{vals[3]:>{cw[3]}}"
            c4 = _c("\033[1m\033[97m", f"{vals[4]:>{cw[4]}}") if is_header else f"{vals[4]:>{cw[4]}}"
            c5 = _c("\033[1m\033[97m", f"{vals[5]:<{cw[5]}}") if is_header else f"{vals[5]:<{cw[5]}}"
            cells = [f" {c0} ", f" {c1} ", f" {c2} ", f" {c3} ", f" {c4} ", f" {c5} "]
            return f"  {V}{V.join(cells)}{V}"

        is_large_fleet = num_servers > 10
        if is_large_fleet:
            srv_title = f"PER-SERVER BREAKDOWN (Top 5 Slowest of {num_servers} Servers):"
            sorted_eps = sorted(
                by_endpoint.items(),
                key=lambda item: compute_statistics(metric_values(valid_samples(item[1]), HEADLINE_METRIC))["p90"],
                reverse=True,
            )
            display_eps = sorted_eps[:5]
        else:
            srv_title = f"PER-SERVER BREAKDOWN ({num_servers} Servers, VALID delivery time):"
            display_eps = sorted(by_endpoint.items())

        _safe_print(_box_span(TL, TR))
        srv_pad = srv_title.ljust(box_w - 4)
        _safe_print(f"  {V}  {_c('\033[96m\033[1m', srv_pad)}{V}")
        _safe_print(_srv_sep(LM, TT, RM))
        _safe_print(_srv_row(["Endpoint", "Valid", "Average", "90% under", "Slowest", "Clock offset"], is_header=True))
        for ep, ep_samples in display_eps:
            _safe_print(_srv_sep(LM, CR, RM))
            ep_valid = valid_samples(ep_samples)
            ep_totals = metric_values(ep_valid, HEADLINE_METRIC)
            st = compute_statistics(ep_totals)
            skews = [s.clock_skew_ms for s in ep_valid if s.clock_skew_ms is not None]
            skew_str = format_clock_offset(skews[0] if skews else None)
            if st["count"] == 0:
                _safe_print(_srv_row([ep, str(len(ep_valid)), "N/A", "N/A", "N/A", skew_str]))
            else:
                _safe_print(
                    _srv_row(
                        [
                            ep,
                            str(len(ep_valid)),
                            f"{st['mean']:.1f}ms",
                            f"{st['p90']:.1f}ms",
                            f"{st['max']:.1f}ms",
                            skew_str,
                        ]
                    )
                )

        _safe_print(_srv_sep(BL, BT, BR))
        if is_large_fleet:
            _safe_print(
                f"  \u2514 [Note: Showing top 5 slowest endpoints; complete {num_servers}-server audit saved to perf-fleet.md & perf-fleet.csv]"
            )
        _safe_print()

    # 4. Benchmark Integrity Audit (if issues present)
    invalid_samples = [s for s in samples if s.integrity_status != "VALID"]
    if invalid_samples:
        audit_cw = [38, 11, 10, 13, 12, 12]  # Sum = 96. Total inner: 96 + 17 = 113. Total box: 115.

        def _aud_sep(lc: str, mid: str, rc: str) -> str:
            parts = [H * (w + 2) for w in audit_cw]
            return f"  {lc}{mid.join(parts)}{rc}"

        def _aud_row(vals: list[str]) -> str:
            cells = [
                f" {vals[0]:<{audit_cw[0]}} ",
                f" {vals[1]:>{audit_cw[1]}} ",
                f" {vals[2]:>{audit_cw[2]}} ",
                f" {vals[3]:>{audit_cw[3]}} ",
                f" {vals[4]:>{audit_cw[4]}} ",
                f" {vals[5]:<{audit_cw[5]}} ",
            ]
            return f"  {V}{V.join(cells)}{V}"

        audit_title = f"BENCHMARK INTEGRITY AUDIT ({len(invalid_samples)} issues detected):"

        _safe_print(_box_span(TL, TR))
        audit_pad = audit_title.ljust(box_w - 4)
        _safe_print(f"  {V}  {_c('\033[93m\033[1m', audit_pad)}{V}")
        _safe_print(_aud_sep(LM, TT, RM))
        _safe_print(_aud_row(["Endpoint", "Received", "Valid", "Incomplete", "Duplicate", "Unmatched"]))
        _safe_print(_aud_sep(LM, CR, RM))

        problematic_eps = [
            (ep, eps) for ep, eps in sorted(by_endpoint.items()) if any(s.integrity_status != "VALID" for s in eps)
        ]
        display_audits = problematic_eps if len(problematic_eps) <= 10 else problematic_eps[:10]

        for ep, ep_samples in display_audits:
            n_recv = len(ep_samples)
            n_valid = sum(1 for s in ep_samples if s.integrity_status == "VALID")
            n_incomp = sum(1 for s in ep_samples if s.integrity_status == "INCOMPLETE")
            n_dup = sum(1 for s in ep_samples if s.integrity_status == "DUPLICATE")
            n_unmatch = sum(1 for s in ep_samples if s.integrity_status == "UNMATCHED")
            _safe_print(_aud_row([ep, str(n_recv), str(n_valid), str(n_incomp), str(n_dup), str(n_unmatch)]))

        _safe_print(_aud_sep(BL, BT, BR))
        if len(problematic_eps) > 10:
            _safe_print(
                f"  \u2514 [Note: Showing 10 of {len(problematic_eps)} affected endpoints; full audit in reports]"
            )
        _safe_print()

    # 5. Fleet Latency Metrics Table (Modeled after Root Runner Box Table)
    mw = [32, 11, 11, 15, 16, 11]  # Sum = 96. Total inner: 96 + 17 = 113. Total box: 115.

    def _met_sep(lc: str, mid: str, rc: str) -> str:
        parts = [H * (w + 2) for w in mw]
        return f"  {lc}{mid.join(parts)}{rc}"

    def _met_row(vals: list[str], is_header: bool = False) -> str:
        c0 = _c("\033[1m\033[97m", f"{vals[0]:<{mw[0]}}") if is_header else f"{vals[0]:<{mw[0]}}"
        c1 = _c("\033[1m\033[97m", f"{vals[1]:>{mw[1]}}") if is_header else f"{vals[1]:>{mw[1]}}"
        c2 = _c("\033[1m\033[97m", f"{vals[2]:>{mw[2]}}") if is_header else f"{vals[2]:>{mw[2]}}"
        c3 = _c("\033[1m\033[97m", f"{vals[3]:>{mw[3]}}") if is_header else f"{vals[3]:>{mw[3]}}"
        c4 = _c("\033[1m\033[97m", f"{vals[4]:>{mw[4]}}") if is_header else f"{vals[4]:>{mw[4]}}"
        c5 = _c("\033[1m\033[97m", f"{vals[5]:>{mw[5]}}") if is_header else f"{vals[5]:>{mw[5]}}"
        cells = [f" {c0} ", f" {c1} ", f" {c2} ", f" {c3} ", f" {c4} ", f" {c5} "]
        return f"  {V}{V.join(cells)}{V}"

    table_hdr = "FLEET AGGREGATE SUMMARY (All Servers):" if num_servers > 1 else "LATENCY SUMMARY (Milliseconds):"

    _safe_print(_box_span(TL, TR))
    tpad = table_hdr.ljust(box_w - 4)
    _safe_print(f"  {V}  {_c('\033[96m\033[1m', tpad)}{V}")
    _safe_print(_met_sep(LM, TT, RM))
    _safe_print(_met_row(["Metric Stage", "Fastest", "Average", "90% under", "99% under", "Slowest"], is_header=True))
    rows = visible_metric_rows(valid)
    for attr, label in rows:
        _safe_print(_met_sep(LM, CR, RM))
        st = compute_statistics(metric_values(valid, attr))
        if st["count"] == 0:
            _safe_print(_met_row([label, "N/A", "N/A", "N/A", "N/A", "N/A"]))
        else:
            _safe_print(
                _met_row(
                    [
                        label,
                        f"{st['min']:.1f}ms",
                        f"{st['mean']:.1f}ms",
                        f"{st['p90']:.1f}ms",
                        f"{st['p99']:.1f}ms",
                        f"{st['max']:.1f}ms",
                    ]
                )
            )

    _safe_print(_met_sep(BL, BT, BR))
    _safe_print()

    # 6. Metric Definitions & Run Notes Table (Clean 2-Column Box Table)
    kw = 28
    val_w = box_w - kw - 7  # 115 - 28 - 7 = 80. Inner width: 28 + 80 + 5 = 113.

    def _2col_sep(lc: str, mid: str, rc: str) -> str:
        return f"  {lc}{H * (kw + 2)}{mid}{H * (val_w + 2)}{rc}"

    def _2col_row(left: str, right: str, is_header: bool = False) -> None:
        wrapped = textwrap.wrap(right, width=val_w) or [""]
        if is_header:
            c_left = _c("\033[1m\033[97m", f"{left:<{kw}}")
            c_right = _c("\033[1m\033[97m", f"{wrapped[0]:<{val_w}}")
            _safe_print(f"  {V} {c_left} │ {c_right} {V}")
        else:
            _safe_print(f"  {V} {left:<{kw}} │ {wrapped[0]:<{val_w}} {V}")
        for cont in wrapped[1:]:
            _safe_print(f"  {V} {' ':<{kw}} │ {cont:<{val_w}} {V}")

    notes = report_notes(valid, timing)
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
    if notes:
        for note in notes:
            if ":" in note:
                nk, nv = note.split(":", 1)
                all_note_items.append((nk.strip(), nv.strip()))
            else:
                all_note_items.append(("Operational Note", note.strip()))

    _safe_print(_box_span(TL, TR))
    _safe_print(f"  {V} {_c('\033[96m\033[1m', 'METRIC DEFINITIONS & RUN NOTES:'.ljust(box_w - 4))} {V}")
    _safe_print(_2col_sep(LM, TT, RM))
    _2col_row("Metric / Item", "Description", is_header=True)

    for k, v in all_note_items:
        _safe_print(_2col_sep(LM, CR, RM))
        _2col_row(k, v)

    _safe_print(_2col_sep(BL, BT, BR))
    _safe_print()

    # 7. Diagnostic Assessment / Bottleneck Attribution Table (Clean 2-Column Box Table)
    diag_rows: list[tuple[str, str]] = [
        ("Primary Bottleneck", verdict.primary_bottleneck),
        ("Assessment Headline", verdict.headline),
        ("Root Cause Analysis", verdict.explanation),
        ("Recommended Action", verdict.recommendation),
    ]
    if verdict.warnings:
        for idx, w in enumerate(verdict.warnings, 1):
            diag_rows.append((f"Advisory Warning #{idx}", w))

    _safe_print(_box_span(TL, TR))
    _safe_print(f"  {V} {_c('\033[96m\033[1m', 'DIAGNOSTIC ASSESSMENT & BOTTLENECK ANALYSIS:'.ljust(box_w - 4))} {V}")
    _safe_print(_2col_sep(LM, TT, RM))
    _2col_row("Diagnostic Field", "Assessment Details", is_header=True)

    for k, v in diag_rows:
        _safe_print(_2col_sep(LM, CR, RM))
        _2col_row(k, v)

    _safe_print(_2col_sep(BL, BT, BR))
    _safe_print()

    # 8. Final Status Verdict (Green check / Yellow alert)
    is_healthy = verdict.primary_bottleneck in (
        "NONE",
        "NONE (OPC UA PIPELINE HEALTHY)",
        "NETWORK_AND_WIRE_HEALTHY",
    )
    if is_healthy:
        _safe_print(_c("\033[92m\033[1m", "  \u2714 ALL PERFORMANCE CHECKS PASSED \u2014 SYSTEM HEALTHY"))
    else:
        _safe_print(
            _c("\033[93m\033[1m", f"  \u25b6 BENCHMARK COMPLETED \u2014 ACTION REQUIRED ({verdict.primary_bottleneck})")
        )
    _safe_print("  " + "\u2550" * width + "\n")
