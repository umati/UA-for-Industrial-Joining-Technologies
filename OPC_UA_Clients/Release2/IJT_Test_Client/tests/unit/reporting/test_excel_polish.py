"""Visual polish tests for make_excel_report — autofilter, print setup, banner.

Tests that every data sheet has:
  - auto_filter.ref set with the start row anchored at the real table header
    (which is *not* always row 1 — see ``_EXPECTED_AUTOFILTER_START_ROW``)
  - landscape A4 fit-to-width print setup
  - header-row repeat on long table sheets, anchored at the same real header row
  - banner text on Conformance Overview contains Passed/Failed + Validation + Server support
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

import openpyxl
import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import make_excel_report  # noqa: E402 — scripts/ added to sys.path above

_COVER_SHEET = "Conformance Overview"
_FACET_SHEET = "IJT Facet Breakdown"
_CU_SHEET = "Conformance Unit Details"
_SUMMARY_SHEET = "Test Outcome Counts"
_PROFILE_SHEET = "Profile Coverage Comparison"

# Each data sheet's real table header row — used to verify autofilter and print
# title rows are anchored on the correct row when metric blocks sit above the
# table. Sheets not listed default to row 1.
_EXPECTED_AUTOFILTER_START_ROW: dict[str, int] = {
    _SUMMARY_SHEET: 12,
    _PROFILE_SHEET: 11,
}

_AUTOFILTER_REF_RE = re.compile(r"^[A-Z]+(\d+):[A-Z]+\d+$")


def _autofilter_start_row(ref: str) -> int:
    match = _AUTOFILTER_REF_RE.match(ref)
    assert match, f"unexpected auto_filter.ref shape: {ref!r}"
    return int(match.group(1))


def _minimal_cases() -> list[make_excel_report.TestCase]:
    return [
        make_excel_report.TestCase("area", "test_pass", "area/test.py", "passed", 0.1),
        make_excel_report.TestCase("area", "test_fail", "area/test.py", "failed", 0.2, "boom"),
        make_excel_report.TestCase("area", "test_skip", "area/test.py", "skipped", 0.0, "skip reason"),
        make_excel_report.TestCase("area", "test_xfail", "area/test.py", "xfailed", 0.0, "known bug"),
    ]


def _minimal_context() -> dict:
    return {
        "server_supported_count": 2,
        "active_cus": ["cu_a", "cu_b"],
        "by_cu": {
            "cu_a": {"passed": 1, "test_count": 1},
            "cu_b": {"passed": 1, "test_count": 1},
        },
        "supported": {"cu_a", "cu_b"},
        "findings_count": Counter(),
        "validation_health_value": 1.0,
        "spec_coverage_value": 1.0,
        "is_healthy": True,
    }


def _minimal_facets() -> dict:
    return {
        "test_facet": make_excel_report.FacetInfo(
            key="test_facet",
            display_name="Test Facet",
            description="A test facet",
            spec_section="1.1",
            kind="facet",
            conformance_units=["cu_a", "cu_b"],
        )
    }


def _minimal_cu_payload() -> dict:
    return {
        "by_cu": {
            "cu_a": {"passed": 1, "test_count": 1, "compliance": "supported"},
            "cu_b": {"passed": 1, "test_count": 1, "compliance": "supported"},
        },
        "supported_cus": ["cu_a", "cu_b"],
        "summary": {"official_cu_count": 2},
        "tests": [],
    }


@pytest.fixture()
def all_sheets_workbook() -> openpyxl.Workbook:
    """Workbook with all 9 sheets populated with minimal fixture data."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    cases = _minimal_cases()
    run_ts = "2026-01-01 00:00:00"
    run_result = "passed"
    context = _minimal_context()
    facets = _minimal_facets()
    cu_payload = _minimal_cu_payload()
    profiles: dict = {}
    capabilities = None

    make_excel_report._build_cover(wb, cases, run_ts, run_result, context, facets)
    make_excel_report._build_summary(wb, cases, run_ts, run_result)
    make_excel_report._build_facet_coverage(wb, cu_payload, facets, capabilities)
    make_excel_report._build_cu_coverage(wb, cu_payload, facets, capabilities, context)
    make_excel_report._build_profile_coverage(wb, cu_payload, profiles, facets, capabilities, run_result)
    make_excel_report._build_all_tests(wb, cases)
    make_excel_report._build_filtered(wb, cases, "Test Failures", ["failed", "error"], make_excel_report._RED)
    make_excel_report._build_filtered(wb, cases, "Skipped Test Cases", ["skipped"], make_excel_report._YELLOW)
    make_excel_report._build_filtered(wb, cases, "Expected Failures", ["xfailed", "xpassed"], make_excel_report._ORANGE)

    return wb


def test_all_data_sheets_have_autofilter(all_sheets_workbook: openpyxl.Workbook) -> None:
    """Every sheet except Conformance Overview must have auto_filter.ref anchored on its real table header row."""
    wb = all_sheets_workbook
    for ws in wb.worksheets:
        if ws.title == _COVER_SHEET:
            continue
        ref = ws.auto_filter.ref
        assert ref, (
            f"Sheet {ws.title!r} is missing auto_filter.ref — "
            "_apply_autofilter must be called at the end of its builder"
        )
        expected = _EXPECTED_AUTOFILTER_START_ROW.get(ws.title, 1)
        actual = _autofilter_start_row(ref)
        assert actual == expected, (
            f"Sheet {ws.title!r}: autofilter starts at row {actual} but real table header is row {expected} "
            f"(auto_filter.ref={ref!r})"
        )


def test_all_sheets_have_print_setup(all_sheets_workbook: openpyxl.Workbook) -> None:
    """Every sheet must have landscape A4 fit-to-width print setup."""
    wb = all_sheets_workbook
    for ws in wb.worksheets:
        assert ws.page_setup.orientation == "landscape", (
            f"Sheet {ws.title!r}: expected landscape, got {ws.page_setup.orientation!r}"
        )
        assert ws.page_setup.paperSize == 9, (  # 9 == A4
            f"Sheet {ws.title!r}: expected paperSize=9 (A4), got {ws.page_setup.paperSize!r}"
        )
        assert ws.page_setup.fitToWidth == 1, (
            f"Sheet {ws.title!r}: expected fitToWidth=1, got {ws.page_setup.fitToWidth!r}"
        )


def test_long_tables_repeat_header(all_sheets_workbook: openpyxl.Workbook) -> None:
    """Long data sheets must repeat their real header row on print pages.

    Row-1 header sheets repeat row 1; sheets with a metric block above the
    table repeat the row holding the table header instead.
    """
    wb = all_sheets_workbook
    expected_repeat: dict[str, int] = {
        _CU_SHEET: 1,
        _FACET_SHEET: 1,
        _SUMMARY_SHEET: 12,
        _PROFILE_SHEET: 11,
    }
    for sheet_name, row in expected_repeat.items():
        ws = wb[sheet_name]
        # openpyxl normalises "N:N" to "$N:$N" when stored
        assert ws.print_title_rows in (f"{row}:{row}", f"${row}:${row}"), (
            f"Sheet {sheet_name!r}: expected print_title_rows={row}:{row}, got {ws.print_title_rows!r}"
        )


def test_layout_sheet_has_no_print_title_rows(all_sheets_workbook: openpyxl.Workbook) -> None:
    """Conformance Overview is a layout sheet — no single repeating table header row."""
    ws = all_sheets_workbook[_COVER_SHEET]
    assert not ws.print_title_rows, (
        f"Conformance Overview is a layout sheet and must not set print_title_rows; got {ws.print_title_rows!r}"
    )


def test_banner_text_present(all_sheets_workbook: openpyxl.Workbook) -> None:
    """Conformance Overview row 1 or row 2 must contain Passed/Failed + Validation + Server support."""
    ws = all_sheets_workbook[_COVER_SHEET]
    banner_text = ""
    for row_idx in (1, 2):
        for cell in ws[row_idx]:
            if cell.value and isinstance(cell.value, str):
                banner_text += cell.value

    assert "Passed" in banner_text or "Failed" in banner_text, f"Banner missing Passed/Failed. Got: {banner_text!r}"
    assert "Validation" in banner_text, f"Banner missing 'Validation'. Got: {banner_text!r}"
    assert "Server support" in banner_text, f"Banner missing 'Server support'. Got: {banner_text!r}"
