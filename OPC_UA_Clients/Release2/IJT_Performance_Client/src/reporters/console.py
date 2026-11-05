"""
Console Reporter: Management-clear FINAL SUMMARY with scale, headlines, finding, and color.
"""

from __future__ import annotations

import os
import re
import sys
import textwrap
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from ..diagnostics import DiagnosticVerdict
from ..results import LatencySample, compute_statistics
from ._metrics import (
    ACTION_NEEDED,
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

_ANSI_GREEN = "\033[92m"
_ANSI_RED = "\033[91m"
_ANSI_YELLOW = "\033[93m"
_ANSI_CYAN = "\033[96m\033[1m"
_ANSI_BOLD = "\033[1m"
_ANSI_WHITE = "\033[1m\033[97m"
_ANSI_RESET = "\033[0m"
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")
_MIN_BOX_W = 115


def _visible_len(text: str) -> int:
    return len(_ANSI_RE.sub("", text))


def _fit(text: str, width: int, align: str) -> str:
    gap = width - _visible_len(text)
    if gap <= 0:
        return text
    if align == ">":
        return (" " * gap) + text
    return text + (" " * gap)


def _table_widths(rows: list[list[str]]) -> list[int]:
    count = len(rows[0])
    return [max(_visible_len(row[i]) for row in rows) for i in range(count)]


def _box_for_widths(widths: list[int]) -> int:
    """Border width that holds these columns, including the pipes and one space of padding."""
    return sum(widths) + (3 * len(widths)) + 1


def _stretch_widths(widths: list[int], box_w: int) -> list[int]:
    """Grow the first column so the table's outer border matches the report box."""
    target = box_w - (3 * len(widths)) - 1
    extra = target - sum(widths)
    stretched = list(widths)
    if extra > 0:
        stretched[0] += extra
    return stretched


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
    """Print a management-clear ANSI summary: Run Size → Result Latency → Client Busy Time → footer."""
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
        _safe_print(f"  {V} {_c(_ANSI_CYAN, _fit(title, box_w - 4, '<'))} {V}")
        _safe_print(_box_span(LM, RM))

    def _grid(title: str, headers: list[str], body: list[list[str]], aligns: list[str]) -> None:
        widths = _stretch_widths(_table_widths([headers, *body]), box_w)

        def _sep(lc: str, mid: str, rc: str) -> str:
            parts = [H * (width + 2) for width in widths]
            return f"  {lc}{mid.join(parts)}{rc}"

        def _row(vals: list[str], *, is_header: bool = False) -> str:
            cells = []
            for val, width_i, align in zip(vals, widths, aligns, strict=True):
                raw = _fit(val, width_i, align)
                shown = _c(_ANSI_WHITE, raw) if is_header else raw
                cells.append(f" {shown} ")
            return f"  {V}{V.join(cells)}{V}"

        _safe_print(_box_span(TL, TR))
        _safe_print(f"  {V}  {_c(_ANSI_CYAN, _fit(title, box_w - 4, '<'))}{V}")
        _safe_print(_sep(LM, TT, RM))
        _safe_print(_row(headers, is_header=True))
        for vals in body:
            _safe_print(_sep(LM, CR, RM))
            _safe_print(_row(vals))
        _safe_print(_sep(BL, BT, BR))

    def _band_ansi(band: str) -> str:
        if band.startswith("Over") or band == "No Results":
            return _ANSI_RED + "\033[1m"
        return _ANSI_CYAN + "\033[1m"

    def _action_ansi(action: str) -> str:
        if action == ACTION_NEEDED:
            return _ANSI_RED + "\033[1m"
        return _ANSI_GREEN + "\033[1m"

    width = 64
    bar = "\u2550" * width
    pad = "FINAL SUMMARY".ljust(width - 2)

    _safe_print()
    _safe_print(_c(_ANSI_CYAN, f"  \u2554{bar}\u2557"))
    _safe_print(_c(_ANSI_CYAN, f"  \u2551  {pad}\u2551"))
    _safe_print(_c(_ANSI_CYAN, f"  \u255a{bar}\u255d"))
    _safe_print(f"  IJT PERFORMANCE & SCALE BENCHMARK REPORT: {pool_name}")
    _safe_print()

    def _latency_line(attr: str) -> str:
        st = compute_statistics(metric_values(valid, attr))
        if st["count"] == 0:
            return "N/A"
        return f"Avg {st['mean']:.1f} ms | 90% Under {st['p90']:.1f} ms | Slowest {st['max']:.1f} ms"

    server_headers = ["Endpoint", "For Stats", "Average", "90% Under", "Slowest", "Clock Offset"]
    server_rows: list[list[str]] = []
    server_title = ""
    num_servers = scale.servers
    if num_servers > 1:
        if num_servers > 10:
            server_title = f"Detail — Top 5 Slowest Of {num_servers} Servers"
            display_eps = sorted(
                by_endpoint.items(),
                key=lambda item: compute_statistics(metric_values(valid_samples(item[1]), HEADLINE_METRIC))["p90"],
                reverse=True,
            )[:5]
        else:
            server_title = f"Detail — Per Server ({num_servers} Servers)"
            display_eps = sorted(by_endpoint.items())
        for ep, ep_samples in display_eps:
            ep_valid = valid_samples(ep_samples)
            st = compute_statistics(metric_values(ep_valid, HEADLINE_METRIC))
            skews = [s.clock_skew_ms for s in ep_valid if s.clock_skew_ms is not None]
            skew_str = format_clock_offset(skews[0] if skews else None)
            if st["count"] == 0:
                server_rows.append([ep, str(len(ep_valid)), "N/A", "N/A", "N/A", skew_str])
            else:
                server_rows.append(
                    [
                        ep,
                        str(len(ep_valid)),
                        f"{st['mean']:.1f}ms",
                        f"{st['p90']:.1f}ms",
                        f"{st['max']:.1f}ms",
                        skew_str,
                    ]
                )

    metric_headers = ["Metric Stage", "Fastest", "Average", "90% Under", "99% Under", "Slowest"]
    metric_rows: list[list[str]] = []
    detail_rows = detail_metric_rows(valid)
    for attr, label in detail_rows:
        st = compute_statistics(metric_values(valid, attr))
        if st["count"] == 0:
            metric_rows.append([label, "N/A", "N/A", "N/A", "N/A", "N/A"])
        else:
            metric_rows.append(
                [
                    label,
                    f"{st['min']:.1f}ms",
                    f"{st['mean']:.1f}ms",
                    f"{st['p90']:.1f}ms",
                    f"{st['p99']:.1f}ms",
                    f"{st['max']:.1f}ms",
                ]
            )

    invalid_samples = [s for s in samples if s.integrity_status != "VALID"]
    audit_headers = ["Endpoint", "Received", "For Stats", "Incomplete", "Duplicate", "Unmatched"]
    audit_rows: list[list[str]] = []
    audit_title = ""
    audit_hidden = 0
    if invalid_samples:
        problematic_eps = [
            (ep, eps) for ep, eps in sorted(by_endpoint.items()) if any(s.integrity_status != "VALID" for s in eps)
        ]
        audit_title = f"Detail — Integrity Audit ({len(invalid_samples)} Issues)"
        audit_hidden = max(0, len(problematic_eps) - 10)
        for ep, ep_samples in problematic_eps[:10]:
            audit_rows.append(
                [
                    ep,
                    str(len(ep_samples)),
                    str(sum(1 for s in ep_samples if s.integrity_status == "VALID")),
                    str(sum(1 for s in ep_samples if s.integrity_status == "INCOMPLETE")),
                    str(sum(1 for s in ep_samples if s.integrity_status == "DUPLICATE")),
                    str(sum(1 for s in ep_samples if s.integrity_status == "UNMATCHED")),
                ]
            )

    meta_labels = [
        "Time",
        "Action",
        "Detail",
        "Servers Tested",
        "Results Per Server",
        "Total Results",
        "Results Used For Stats",
        "Wire Timing",
        "Workers",
        "Worst",
        "Worst Worker Avg",
        *[label for _attr, label in headline_metric_rows()],
    ]
    if verdict.warnings:
        meta_labels.extend(f"Note {idx}" for idx in range(1, len(verdict.warnings) + 1))
    meta_lw = max(len(label) for label in meta_labels)
    valid_pct = (scale.valid_results / scale.total_results * 100.0) if scale.total_results else 0.0
    wire_count = wire_timing_count(valid)
    wire_pct = (wire_count / len(valid) * 100.0) if valid else 0.0
    valid_line = f"{scale.valid_results:,} of {scale.total_results:,} ({valid_pct:.1f}%)"
    valid_ansi = (
        _ANSI_GREEN + "\033[1m"
        if scale.total_results and scale.valid_results == scale.total_results
        else (_ANSI_RED + "\033[1m" if scale.total_results else None)
    )
    if wire_count and valid and wire_count == len(valid):
        wire_line = f"{wire_count:,}/{len(valid):,} verified ({wire_pct:.1f}%)"
        wire_ansi: str | None = _ANSI_GREEN + "\033[1m"
    elif valid:
        wire_line = f"{wire_count:,}/{len(valid):,} verified ({wire_pct:.1f}%)"
        wire_ansi = None
    else:
        wire_line = "0/0"
        wire_ansi = None
    one_line_values = [
        outcome.time_band,
        outcome.action,
        valid_line,
        wire_line,
        scale.results_per_server_text,
        scale.total_results_text,
        *[_latency_line(attr) for attr, _label in headline_metric_rows()],
    ]
    if timing and timing.get("workers_reported") is not None:
        one_line_values.append(f"{float(timing.get('loop_lag_max_ms', 0.0) or 0.0):.1f} ms")
        one_line_values.append(f"{float(timing.get('loop_lag_worst_mean_ms', 0.0) or 0.0):.1f} ms")
    box_w = _MIN_BOX_W
    box_w = max(box_w, meta_lw + max(_visible_len(value) for value in one_line_values) + 7)
    for title in (server_title, audit_title, "Detail — Other Latency Stages" if metric_rows else ""):
        if title:
            box_w = max(box_w, _visible_len(title) + 4)
    if server_rows:
        box_w = max(box_w, _box_for_widths(_table_widths([server_headers, *server_rows])))
    if metric_rows:
        box_w = max(box_w, _box_for_widths(_table_widths([metric_headers, *metric_rows])))
    if audit_rows:
        box_w = max(box_w, _box_for_widths(_table_widths([audit_headers, *audit_rows])))
    meta_vw = box_w - meta_lw - 7

    _safe_print(_box_span(TL, TR))
    _print_meta_row("Time", outcome.time_band, val_ansi=_band_ansi(outcome.time_band))
    _safe_print(_box_span(LM, RM))
    _print_meta_row("Action", outcome.action, val_ansi=_action_ansi(outcome.action))
    _safe_print(_box_span(LM, RM))
    _print_meta_row("Detail", outcome.summary)
    if verdict.warnings:
        for idx, warning in enumerate(verdict.warnings, 1):
            _safe_print(_box_span(LM, RM))
            _print_meta_row(f"Note {idx}", warning)
    _safe_print(_box_span(BL, BR))
    _safe_print()

    # --- Run Size ---
    _section_title("Run Size")
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
    _section_title("Result Latency")
    for i, (attr, label) in enumerate(headline_metric_rows()):
        if i:
            _safe_print(_box_span(LM, RM))
        _print_meta_row(label, _latency_line(attr))
    _safe_print(_box_span(BL, BR))
    _safe_print()

    if timing and timing.get("workers_reported") is not None:
        lag = float(timing.get("loop_lag_max_ms", 0.0) or 0.0)
        lag_mean = float(timing.get("loop_lag_worst_mean_ms", 0.0) or 0.0)
        _section_title("Client Busy Time")
        _print_meta_row("Worst", f"{lag:.1f} ms")
        _safe_print(_box_span(LM, RM))
        _print_meta_row("Worst Worker Avg", f"{lag_mean:.1f} ms")
        _safe_print(_box_span(BL, BR))
        _safe_print()

    if server_rows:
        _grid(server_title, server_headers, server_rows, ["<", ">", ">", ">", ">", "<"])
        if num_servers > 10:
            _safe_print(f"  \u2514 Complete {num_servers}-server data is in perf-fleet.md and perf-fleet.csv")
        _safe_print()

    if audit_rows:
        _grid(audit_title, audit_headers, audit_rows, ["<", ">", ">", ">", ">", "<"])
        if audit_hidden:
            _safe_print(f"  \u2514 Showing 10 of {audit_hidden + 10} affected endpoints; full audit in reports")
        _safe_print()

    if metric_rows:
        _grid("Detail — Other Latency Stages", metric_headers, metric_rows, ["<", ">", ">", ">", ">", ">"])
        _safe_print()

    # Footer repeats the same time and action as the top.
    _safe_print(
        "  "
        + _c(_band_ansi(outcome.time_band), outcome.time_band)
        + " — "
        + _c(_action_ansi(outcome.action), outcome.action)
    )
    _safe_print(f"  {outcome.summary}")
    _safe_print("  " + "\u2550" * width + "\n")
