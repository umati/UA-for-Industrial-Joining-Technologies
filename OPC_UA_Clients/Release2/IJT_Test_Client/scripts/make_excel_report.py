#!/usr/bin/env python3
"""
make_excel_report.py — Convert JUnit XML test results into a rich Excel workbook.

Reads:  test-results/pytest.xml   (or path given via --xml=FILE)
Writes: test-results/report.xlsx  (or path given via --out=FILE)

Sheets produced:
  Summary       — headline counts (passed / failed / skipped / xfailed) by test area
  All Tests     — every test: name, file, status, duration, skip/fail reason
  Failures      — only failed tests with full message
  Skipped       — only skipped tests with reason
  Expected Fail — xfailed and xpassed tests with reason

Usage:
  python scripts/make_excel_report.py
  python scripts/make_excel_report.py --xml test-results/pytest.xml --out test-results/report.xlsx
  python scripts/make_excel_report.py --help
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET  # nosec B405 — parses trusted JUnit XML from our own test runner
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:
    print("ERROR: openpyxl is required.  Run: pip install openpyxl", file=sys.stderr)
    sys.exit(1)

# ── Colour palette ────────────────────────────────────────────────────────────
_GREEN = "FF92D050"  # passed
_RED = "FFFF0000"  # failed
_YELLOW = "FFFFFF00"  # skipped
_ORANGE = "FFFFC000"  # xfailed / xpassed
_BLUE = "FF9DC3E6"  # header rows
_GRAY = "FFF2F2F2"  # alternating row background
_WHITE = "FFFFFFFF"

_STATUS_COLOUR = {
    "passed": _GREEN,
    "failed": _RED,
    "skipped": _YELLOW,
    "xfailed": _ORANGE,
    "xpassed": _ORANGE,
    "error": _RED,
}

# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class TestCase:
    classname: str
    name: str
    file: str
    status: str  # passed | failed | skipped | xfailed | xpassed | error
    duration: float
    message: str = ""  # skip reason, failure message, or xfail reason

    @property
    def area(self) -> str:
        """Top-level directory of the test file."""
        parts = Path(self.file).parts
        return parts[0] if parts else "unknown"

    @property
    def short_name(self) -> str:
        return self.name


# ── XML parsing ───────────────────────────────────────────────────────────────


def _text(elem: ET.Element | None) -> str:
    if elem is None:
        return ""
    parts = []
    if elem.text:
        parts.append(elem.text.strip())
    for child in elem:
        if child.text:
            parts.append(child.text.strip())
        if child.tail:
            parts.append(child.tail.strip())
    return "\n".join(p for p in parts if p)


def parse_junit_xml(path: Path) -> list[TestCase]:
    tree = ET.parse(path)  # nosec B314 — source is trusted JUnit XML written by pytest
    root = tree.getroot()

    # Handle both <testsuites><testsuite>... and bare <testsuite>...
    suites = root.findall(".//testsuite") if root.tag == "testsuites" else [root]

    cases: list[TestCase] = []
    for suite in suites:
        for tc in suite.findall("testcase"):
            classname = tc.get("classname", "")
            name = tc.get("name", "")
            file = tc.get("file", classname.replace(".", "/") + ".py")
            duration = float(tc.get("time", "0") or "0")

            failure = tc.find("failure")
            error = tc.find("error")
            skip = tc.find("skipped")

            if failure is not None:
                status = "failed"
                message = (failure.get("message") or "") + "\n" + (failure.text or "")
            elif error is not None:
                status = "error"
                message = (error.get("message") or "") + "\n" + (error.text or "")
            elif skip is not None:
                status = "skipped"
                message = skip.get("message") or _text(skip)
                # pytest encodes xfail as <skipped type="pytest.xfail" ...>
                # Fallback: some JUnit emitters prefix the message with "xfail" instead
                if (skip.get("type") or "").lower() == "pytest.xfail" or message.lower().startswith("xfail"):
                    status = "xfailed"
            else:
                status = "passed"
                message = ""

            cases.append(
                TestCase(
                    classname=classname,
                    name=name,
                    file=file,
                    status=status,
                    duration=duration,
                    message=message.strip(),
                )
            )

    return cases


# ── Excel helpers ─────────────────────────────────────────────────────────────


def _fill(hex_colour: str) -> PatternFill:
    return PatternFill(fill_type="solid", fgColor=hex_colour)


def _header_font() -> Font:
    return Font(bold=True, color="FF000000")


def _apply_header(ws, row: int, headers: list[str], col_widths: list[int]) -> None:
    for col, (hdr, width) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=row, column=col, value=hdr)
        cell.font = _header_font()
        cell.fill = _fill(_BLUE)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(col)].width = width


def _write_row(ws, row: int, values: list, status: str, alternate: bool) -> None:
    bg = _fill(_GRAY) if alternate else _fill(_WHITE)
    for col, val in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col, value=val)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        if col == 4:  # Status column — colour by status
            cell.fill = _fill(_STATUS_COLOUR.get(status, _WHITE))
            cell.font = Font(bold=True)
        else:
            cell.fill = bg


# ── Sheet builders ────────────────────────────────────────────────────────────


def _build_summary(wb: openpyxl.Workbook, cases: list[TestCase], run_ts: str) -> None:
    ws = wb.create_sheet("Summary")
    ws.sheet_view.showGridLines = False

    # Title
    ws["A1"] = "IJT Test Client — Conformance Test Report"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Generated: {run_ts}"
    ws["A2"].font = Font(italic=True, size=10)

    # Overall counts
    statuses = [c.status for c in cases]
    passed = statuses.count("passed")
    failed = statuses.count("failed") + statuses.count("error")
    skipped = statuses.count("skipped")
    xfailed = statuses.count("xfailed") + statuses.count("xpassed")
    total = len(cases)

    ws["A4"] = "Overall"
    ws["A4"].font = Font(bold=True)
    summary_data = [
        ("Total", total, _BLUE),
        ("Passed", passed, _GREEN),
        ("Failed", failed, _RED),
        ("Skipped", skipped, _YELLOW),
        ("Xfailed", xfailed, _ORANGE),
    ]
    for i, (label, count, colour) in enumerate(summary_data, start=5):
        ws.cell(row=i, column=1, value=label).font = Font(bold=True)
        cell = ws.cell(row=i, column=2, value=count)
        cell.fill = _fill(colour)
        cell.font = Font(bold=True)

    # Per-area breakdown
    ws["A11"] = "By Test Area"
    ws["A11"].font = Font(bold=True)
    _apply_header(ws, 12, ["Area", "Total", "Passed", "Failed", "Skipped", "Xfailed"], [20, 8, 8, 8, 10, 10])

    areas: dict[str, list[TestCase]] = {}
    for c in cases:
        areas.setdefault(c.area, []).append(c)

    for row_idx, (area, area_cases) in enumerate(sorted(areas.items()), start=13):
        sc = [c.status for c in area_cases]
        values = [
            area,
            len(area_cases),
            sc.count("passed"),
            sc.count("failed") + sc.count("error"),
            sc.count("skipped"),
            sc.count("xfailed") + sc.count("xpassed"),
        ]
        for col, val in enumerate(values, start=1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            if col == 4 and isinstance(val, int) and val > 0:
                cell.fill = _fill(_RED)
                cell.font = Font(bold=True)
            elif col == 3:
                cell.fill = _fill(_GREEN if val == len(area_cases) else _WHITE)

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 8


def _build_all_tests(wb: openpyxl.Workbook, cases: list[TestCase]) -> None:
    ws = wb.create_sheet("All Tests")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"

    headers = ["Area", "File", "Test Name", "Status", "Duration (s)", "Reason / Message"]
    col_widths = [15, 35, 55, 10, 12, 70]
    _apply_header(ws, 1, headers, col_widths)

    for row_idx, (i, c) in enumerate(enumerate(cases), start=2):
        _write_row(
            ws,
            row_idx,
            [
                c.area,
                c.file,
                c.short_name,
                c.status.upper(),
                round(c.duration, 3),
                c.message,
            ],
            c.status,
            i % 2 == 0,
        )

    ws.row_dimensions[1].height = 20


def _build_filtered(
    wb: openpyxl.Workbook, cases: list[TestCase], sheet_name: str, statuses: list[str], colour: str
) -> None:
    filtered = [c for c in cases if c.status in statuses]
    ws = wb.create_sheet(f"{sheet_name} ({len(filtered)})")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"

    if not filtered:
        ws["A1"] = f"No {sheet_name.lower()} tests."
        return

    headers = ["Area", "File", "Test Name", "Duration (s)", "Reason / Message"]
    col_widths = [15, 35, 55, 12, 80]
    _apply_header(ws, 1, headers, col_widths)

    for row_idx, c in enumerate(filtered, start=2):
        for col, val in enumerate([c.area, c.file, c.short_name, round(c.duration, 3), c.message], start=1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.fill = _fill(colour)
            cell.alignment = Alignment(wrap_text=True, vertical="top")


# ── Main ──────────────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--xml", default="test-results/pytest.xml", help="JUnit XML input file")
    p.add_argument("--out", default="test-results/report.xlsx", help="Excel output file")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    xml_path = Path(args.xml)
    out_path = Path(args.out)

    if not xml_path.exists():
        print(f"ERROR: JUnit XML not found: {xml_path}", file=sys.stderr)
        print("  Run tests first: python -m pytest ... --junitxml=test-results/pytest.xml", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Reading: {xml_path}")
    cases = parse_junit_xml(xml_path)
    print(f"  {len(cases)} test cases found")

    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default empty sheet

    _build_summary(wb, cases, run_ts)
    _build_all_tests(wb, cases)
    _build_filtered(wb, cases, "Failures", ["failed", "error"], _RED)
    _build_filtered(wb, cases, "Skipped", ["skipped"], _YELLOW)
    _build_filtered(wb, cases, "Expected Fail", ["xfailed", "xpassed"], _ORANGE)

    wb.save(out_path)

    # Print summary to console
    statuses = [c.status for c in cases]
    passed = statuses.count("passed")
    failed = statuses.count("failed") + statuses.count("error")
    skipped = statuses.count("skipped")
    xfailed = statuses.count("xfailed") + statuses.count("xpassed")

    print(f"\nReport written: {out_path}")
    print(f"  Passed:   {passed}")
    print(f"  Failed:   {failed}")
    print(f"  Skipped:  {skipped}")
    print(f"  Xfailed:  {xfailed}")
    print(f"  Total:    {len(cases)}")
    if failed > 0:
        print(f"\n  *** {failed} FAILURE(S) — see 'Failures' sheet ***")
    return 0


if __name__ == "__main__":
    sys.exit(main())
