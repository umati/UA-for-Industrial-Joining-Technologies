"""
Console Reporter: Management-clear FINAL SUMMARY with scale, headlines, finding, and color.
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
    OUTCOME_INFORMATION,
    OUTCOME_OK,
    classify_report_outcome,
    detail_metric_rows,
    format_clock_offset,
    headline_metric_rows,
    metric_values,
    summarize_scale,
    valid_samples,
    wire_timing_count,
)

_ANSI_GREEN = "\033[92m"
_ANSI_RED = "\033[91m"
_ANSI_YELLOW = "\033[93m"
_ANSI_CYAN = "\033[96m\033[1m"
_ANSI_BOLD = "\033[1m"
_ANSI_WHITE = "\033[1m\033[97m"
_ANSI_RESET = "\033[0m"


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
    *,
    samples_per_endpoint: int | None = None,
    fail_p90_ms: float | None = None,
    fail_p90_client_ready_ms: float | None = None,
    gate_failed: bool = False,
) -> None:
    """Print a management-clear ANSI summary: Scale → Result Latency → Assessment → Detail → footer."""
    use_colour = sys.stdout.isatty() and (os.name != "nt" or _enable_ansi_windows())

    def _c(ansi: str, text: str) -> str:
        return f"{ansi}{text}{_ANSI_RESET}" if use_colour else text

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

    H = "\u2500"
    V = "\u2502"
    TL = "\u250c"
    TR = "\u2510"
    BL = "\u2514"
    BR = "\u2518"
    LM = "\u251c"
    RM = "\u2524"
    TT = "\u252c"
    BT = "\u2534"
    CR = "\u253c"

    box_w = 115
    meta_lw = 24
    meta_vw = box_w - meta_lw - 7

    def _box_span(lc: str, rc: str) -> str:
        return f"  {lc}{H * (box_w - 2)}{rc}"

    def _print_meta_row(label: str, val: str, *, val_ansi: str | None = None) -> None:
        wrapped = textwrap.wrap(val, width=meta_vw) or [""]
        for i, line in enumerate(wrapped):
            left = label if i == 0 else ""
            sep = ":" if i == 0 else " "
            if val_ansi and use_colour:
                pad = max(0, meta_vw - len(line))
                shown = _c(val_ansi, line) + (" " * pad)
            else:
                shown = f"{line:<{meta_vw}}"
            _safe_print(f"  {V} {left:<{meta_lw}} {sep} {shown} {V}")

    def _section_title(title: str) -> None:
        _safe_print(_box_span(TL, TR))
        _safe_print(f"  {V} {_c(_ANSI_CYAN, title.ljust(box_w - 4))} {V}")
        _safe_print(_box_span(LM, RM))

    def _outcome_ansi(label: str) -> str:
        if label == OUTCOME_OK:
            return _ANSI_GREEN + "\033[1m"
        if label == OUTCOME_INFORMATION:
            return _ANSI_YELLOW + "\033[1m"
        return _ANSI_RED + "\033[1m"

    width = 64
    bar = "\u2550" * width
    pad = "FINAL SUMMARY".ljust(width - 2)

    _safe_print()
    _safe_print(_c(_ANSI_CYAN, f"  \u2554{bar}\u2557"))
    _safe_print(_c(_ANSI_CYAN, f"  \u2551  {pad}\u2551"))
    _safe_print(_c(_ANSI_CYAN, f"  \u255a{bar}\u255d"))
    _safe_print(f"  IJT PERFORMANCE & SCALE BENCHMARK REPORT: {pool_name}")
    _safe_print()

    # --- Scale ---
    valid_pct = (scale.valid_results / scale.total_results * 100.0) if scale.total_results else 0.0
    wire_count = wire_timing_count(valid)
    wire_pct = (wire_count / len(valid) * 100.0) if valid else 0.0
    valid_line = f"{scale.valid_results:,} of {scale.total_results:,} ({valid_pct:.1f}%)"
    valid_ansi = (
        _ANSI_GREEN + "\033[1m"
        if scale.total_results and scale.valid_results == scale.total_results
        else (_ANSI_YELLOW + "\033[1m" if scale.valid_results else _ANSI_RED + "\033[1m")
    )
    if wire_count and valid and wire_count == len(valid):
        wire_line = f"{wire_count}/{len(valid)} verified ({wire_pct:.1f}%)"
        wire_ansi: str | None = _ANSI_GREEN + "\033[1m"
    elif valid:
        wire_line = f"{wire_count}/{len(valid)} verified ({wire_pct:.1f}%)"
        wire_ansi = _ANSI_YELLOW + "\033[1m"
    else:
        wire_line = "0/0"
        wire_ansi = None

    _section_title("Scale")
    _print_meta_row("Servers Tested", f"{scale.servers}")
    _safe_print(_box_span(LM, RM))
    _print_meta_row("Results Per Server", scale.results_per_server_text)
    _safe_print(_box_span(LM, RM))
    _print_meta_row("Total Results", scale.total_results_text)
    _safe_print(_box_span(LM, RM))
    _print_meta_row("Results Used For Stats", valid_line, val_ansi=valid_ansi)
    _safe_print(_box_span(LM, RM))
    _print_meta_row("Wire Timing", wire_line, val_ansi=wire_ansi)
    if timing and timing.get("workers_reported"):
        _safe_print(_box_span(LM, RM))
        _print_meta_row("Workers", f"{timing['workers_reported']}")
    _safe_print(_box_span(BL, BR))
    _safe_print()

    # --- Result Latency ---
    def _latency_line(attr: str) -> str:
        st = compute_statistics(metric_values(valid, attr))
        if st["count"] == 0:
            return "N/A"
        return f"Avg {st['mean']:.1f} ms | 90% Under {st['p90']:.1f} ms | Slowest {st['max']:.1f} ms"

    _section_title("Result Latency")
    for i, (attr, label) in enumerate(headline_metric_rows()):
        if i:
            _safe_print(_box_span(LM, RM))
        p90_ansi = _outcome_ansi(outcome.label) if outcome.label != OUTCOME_OK else (_ANSI_GREEN + "\033[1m")
        _print_meta_row(label, _latency_line(attr), val_ansi=p90_ansi if valid else None)
    _safe_print(_box_span(BL, BR))
    _safe_print()

    # --- Assessment (OK / INFORMATION / ACTION NEEDED — not always a problem) ---
    _section_title("Assessment")
    _print_meta_row("Outcome", outcome.label, val_ansi=_outcome_ansi(outcome.label))
    _safe_print(_box_span(LM, RM))
    _print_meta_row("Bottleneck", verdict.primary_bottleneck, val_ansi=_outcome_ansi(outcome.label))
    _safe_print(_box_span(LM, RM))
    _print_meta_row("Meaning", outcome.what_this_means)
    _safe_print(_box_span(LM, RM))
    _print_meta_row("Next Step", outcome.suggested_next_step)
    if timing and timing.get("workers_reported") is not None:
        lag = float(timing.get("loop_lag_max_ms", 0.0) or 0.0)
        lag_mean = float(timing.get("loop_lag_worst_mean_ms", 0.0) or 0.0)
        _safe_print(_box_span(LM, RM))
        lag_ansi = _ANSI_YELLOW + "\033[1m" if lag >= 50.0 else None
        _print_meta_row(
            "Loop Lag",
            f"Worst {lag:.1f} ms (Worst Worker Avg {lag_mean:.1f} ms)",
            val_ansi=lag_ansi,
        )
    if verdict.warnings:
        for idx, w in enumerate(verdict.warnings, 1):
            _safe_print(_box_span(LM, RM))
            _print_meta_row(f"Warning #{idx}", w, val_ansi=_ANSI_YELLOW + "\033[1m")
    _safe_print(_box_span(BL, BR))
    _safe_print()

    # --- Detail: top-5 / per-server ---
    num_servers = scale.servers
    if num_servers > 1:
        cw = [34, 6, 10, 12, 10, 24]

        def _srv_sep(lc: str, mid: str, rc: str) -> str:
            parts = [H * (w + 2) for w in cw]
            return f"  {lc}{mid.join(parts)}{rc}"

        def _srv_row(vals: list[str], is_header: bool = False, *, emphasize_p90: bool = False) -> str:
            cells_fmt: list[str] = []
            for i, (val, width_i) in enumerate(zip(vals, cw, strict=True)):
                align = "<" if i in (0, 5) else ">"
                raw = f"{val:{align}{width_i}}"
                if is_header:
                    cells_fmt.append(f" {_c(_ANSI_WHITE, raw)} ")
                elif emphasize_p90 and i == 3:
                    cells_fmt.append(f" {_c(_ANSI_YELLOW + '\033[1m', raw)} ")
                else:
                    cells_fmt.append(f" {raw} ")
            return f"  {V}{V.join(cells_fmt)}{V}"

        is_large_fleet = num_servers > 10
        if is_large_fleet:
            srv_title = f"Detail — Top 5 Slowest Of {num_servers} Servers"
            sorted_eps = sorted(
                by_endpoint.items(),
                key=lambda item: compute_statistics(metric_values(valid_samples(item[1]), HEADLINE_METRIC))["p90"],
                reverse=True,
            )
            display_eps = sorted_eps[:5]
        else:
            srv_title = f"Detail — Per Server ({num_servers} Servers)"
            display_eps = sorted(by_endpoint.items())

        _safe_print(_box_span(TL, TR))
        _safe_print(f"  {V}  {_c(_ANSI_CYAN, srv_title.ljust(box_w - 4))}{V}")
        _safe_print(_srv_sep(LM, TT, RM))
        _safe_print(
            _srv_row(["Endpoint", "For Stats", "Average", "90% Under", "Slowest", "Clock Offset"], is_header=True)
        )
        for ep_i, (ep, ep_samples) in enumerate(display_eps):
            _safe_print(_srv_sep(LM, CR, RM))
            ep_valid = valid_samples(ep_samples)
            st = compute_statistics(metric_values(ep_valid, HEADLINE_METRIC))
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
                        ],
                        emphasize_p90=(ep_i == 0 and is_large_fleet),
                    )
                )
        _safe_print(_srv_sep(BL, BT, BR))
        if is_large_fleet:
            _safe_print(f"  \u2514 Complete {num_servers}-server data is in perf-fleet.md and perf-fleet.csv")
        _safe_print()

    # Integrity audit only when issues
    invalid_samples = [s for s in samples if s.integrity_status != "VALID"]
    if invalid_samples:
        audit_cw = [38, 11, 10, 13, 12, 12]

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

        audit_title = f"Detail — Integrity Audit ({len(invalid_samples)} Issues)"
        _safe_print(_box_span(TL, TR))
        _safe_print(f"  {V}  {_c(_ANSI_YELLOW + '\033[1m', audit_title.ljust(box_w - 4))}{V}")
        _safe_print(_aud_sep(LM, TT, RM))
        _safe_print(_aud_row(["Endpoint", "Received", "For Stats", "Incomplete", "Duplicate", "Unmatched"]))
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
            _safe_print(f"  \u2514 Showing 10 of {len(problematic_eps)} affected endpoints; full audit in reports")
        _safe_print()

    # Detail — other latency stages
    detail_rows = detail_metric_rows(valid)
    mw = [32, 11, 11, 15, 16, 11]

    def _met_sep(lc: str, mid: str, rc: str) -> str:
        parts = [H * (w + 2) for w in mw]
        return f"  {lc}{mid.join(parts)}{rc}"

    def _met_row(vals: list[str], is_header: bool = False) -> str:
        cells = []
        for i, (val, width_i) in enumerate(zip(vals, mw, strict=True)):
            align = "<" if i == 0 else ">"
            raw = f"{val:{align}{width_i}}"
            cells.append(f" {_c(_ANSI_WHITE, raw) if is_header else raw} ")
        return f"  {V}{V.join(cells)}{V}"

    table_hdr = "Detail — Other Latency Stages"
    rows_to_show = detail_rows

    if rows_to_show:
        _safe_print(_box_span(TL, TR))
        _safe_print(f"  {V}  {_c(_ANSI_CYAN, table_hdr.ljust(box_w - 4))}{V}")
        _safe_print(_met_sep(LM, TT, RM))
        _safe_print(
            _met_row(["Metric Stage", "Fastest", "Average", "90% Under", "99% Under", "Slowest"], is_header=True)
        )
        for attr, label in rows_to_show:
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

    # Footer
    footer_ansi = _outcome_ansi(outcome.label)
    _safe_print(_c(footer_ansi, f"  {outcome.footer}"))
    _safe_print("  " + "\u2550" * width + "\n")
