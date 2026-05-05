#!/usr/bin/env python3
"""
make_excel_report.py — Convert JUnit XML test results into a rich Excel workbook.

Reads:  test-results/pytest.xml   (or path given via --xml=FILE)
Writes: test-results/report.xlsx  (or path given via --out=FILE)

Sheets produced:
  Summary          — headline counts (passed / failed / skipped / xfailed) by test area
  All Tests        — every test: name, file, status, duration, skip/fail reason
  Failures         — only failed tests with full message
  Skipped          — only skipped tests with reason
  Expected Fail    — xfailed and xpassed tests with reason
  Profile Coverage — IJT high-level coverage views, when CU JSON is present
  Facet Coverage   — IJT facet coverage, when CU JSON is present
  CU Coverage      — one row per conformance unit, when CU JSON is present

Usage:
  python scripts/make_excel_report.py
  python scripts/make_excel_report.py --xml test-results/pytest.xml --out test-results/report.xlsx
  python scripts/make_excel_report.py --help
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import xml.etree.ElementTree as ET  # nosec B405
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Bandit B405/B314 suppressions are limited to trusted JUnit XML from pytest.

try:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:
    print("ERROR: openpyxl is required.  Run: pip install openpyxl", file=sys.stderr)
    sys.exit(1)

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    yaml = None  # type: ignore[assignment]

# ── Colour palette ────────────────────────────────────────────────────────────
_GREEN = "FF92D050"  # passed
_RED = "FFFF0000"  # failed
_YELLOW = "FFFFFF00"  # skipped
_ORANGE = "FFFFC000"  # xfailed / xpassed
_BLUE = "FF9DC3E6"  # header rows
_GRAY = "FFF2F2F2"  # alternating row background
_DARK_GRAY = "FFD9E1F2"
_WHITE = "FFFFFFFF"
_LIGHT_GREEN = "FFE2F0D9"
_LIGHT_GREEN_NOTE = "FFEAF7E8"
_LIGHT_RED = "FFFFE5E5"
_LIGHT_YELLOW = "FFFFF2CC"
_LIGHT_ORANGE = "FFFCE4D6"
_LIGHT_BLUE = "FFDDEBF7"

_STATUS_COLOUR = {
    "passed": _GREEN,
    "failed": _RED,
    "skipped": _YELLOW,
    "xfailed": _ORANGE,
    "xpassed": _ORANGE,
    "error": _RED,
}

_CU_STATUS_COLOUR = {
    "supported": _LIGHT_GREEN,
    "partial": _LIGHT_GREEN_NOTE,
    "action_needed": _LIGHT_RED,
    "passed": _LIGHT_GREEN,
    "failed": _LIGHT_RED,
    "error": _LIGHT_RED,
    "not_supported": _LIGHT_YELLOW,
    "blocked": _LIGHT_ORANGE,
    "untested": _GRAY,
    "skipped": _LIGHT_YELLOW,
    "unknown": _WHITE,
}

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_PROFILES_DIR = _PROJECT_ROOT / "profiles"
_DEFAULT_CU_JSON = _PROJECT_ROOT / "test-results" / "cu-compliance-report.json"
_CU_COMPLIANCE_KEYS = {"supported", "partial", "not_supported", "blocked", "action_needed", "untested"}

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


@dataclass(frozen=True)
class FacetInfo:
    key: str
    display_name: str
    description: str
    spec_section: str
    kind: str
    conformance_units: list[str]


@dataclass(frozen=True)
class ProfileInfo:
    key: str
    name: str
    description: str
    facets: list[str]


@dataclass(frozen=True)
class CapabilitiesInfo:
    server_name: str
    active_profile: str
    supported_facets: list[str]
    overrides: dict[str, str]


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
    tree = ET.parse(path)  # nosec B314
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


# ── CU / profile metadata parsing ─────────────────────────────────────────────


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None or not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return loaded if isinstance(loaded, dict) else {}


def _load_facets() -> dict[str, FacetInfo]:
    raw = _load_yaml(_PROFILES_DIR / "facets.yaml")
    facets: dict[str, FacetInfo] = {}
    for key, data in (raw.get("facets") or {}).items():
        if not isinstance(data, dict):
            continue
        units = [str(cu) for cu in data.get("conformance_units", [])]
        facets[str(key)] = FacetInfo(
            key=str(key),
            display_name=str(data.get("display_name") or _title_from_key(str(key))),
            description=str(data.get("description") or "").strip(),
            spec_section=str(data.get("spec_section") or ""),
            kind=str(data.get("kind") or "facet"),
            conformance_units=units,
        )
    return facets


def _load_profiles() -> dict[str, ProfileInfo]:
    profiles: dict[str, ProfileInfo] = {}
    for path in sorted(_PROFILES_DIR.glob("*.yaml")):
        if path.name == "facets.yaml":
            continue
        raw = _load_yaml(path)
        profile_raw = raw.get("profile")
        profile: dict[str, Any] = profile_raw if isinstance(profile_raw, dict) else {}
        profiles[path.stem] = ProfileInfo(
            key=path.stem,
            name=str(profile.get("name") or _title_from_key(path.stem)),
            description=str(profile.get("description") or "").strip(),
            facets=[str(facet) for facet in profile.get("facets", [])],
        )
    return profiles


def _load_capabilities(path: Path | None) -> CapabilitiesInfo | None:
    raw = _load_yaml(path) if path else {}
    if not raw:
        return None
    server_raw = raw.get("server")
    server: dict[str, Any] = server_raw if isinstance(server_raw, dict) else {}
    return CapabilitiesInfo(
        server_name=str(server.get("name") or "Server under test"),
        active_profile=str(raw.get("active_profile") or ""),
        supported_facets=[str(facet) for facet in raw.get("supported_facets", [])],
        overrides={str(key): str(value) for key, value in (raw.get("cu_overrides") or {}).items()},
    )


def _title_from_key(key: str) -> str:
    acronyms = {"cu": "CU", "id": "ID", "io": "IO", "ijt": "IJT"}
    return " ".join(acronyms.get(token, token.capitalize()) for token in key.split("_"))


def _cu_display_name(cu_key: str) -> str:
    return f"IJT {_title_from_key(cu_key)}"


def _supported_set(cu_payload: dict[str, Any]) -> set[str] | None:
    supported = cu_payload.get("supported_cus")
    if supported is None:
        return None
    return {str(cu) for cu in supported}


def _server_profile_cu_count(cu_keys: list[str], supported: set[str] | None) -> int | str:
    if supported is None:
        return "n/a"
    return len([cu_key for cu_key in cu_keys if cu_key in supported])


def _in_server_profile(cu_key: str, supported: set[str] | None) -> str:
    if supported is None:
        return "n/a"
    return "Yes" if cu_key in supported else "No"


def _server_profile_pct(server_profile_cus: int | str, total: int) -> str:
    if not isinstance(server_profile_cus, int):
        return "n/a"
    return _pct(server_profile_cus, total)


def _cus_for_profile(profile: ProfileInfo, facets: dict[str, FacetInfo]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for facet_key in profile.facets:
        for cu_key in facets.get(facet_key, FacetInfo(facet_key, facet_key, "", "", "facet", [])).conformance_units:
            if cu_key not in seen:
                seen.add(cu_key)
                ordered.append(cu_key)
    return ordered


def _cu_to_facets(facets: dict[str, FacetInfo]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    rollups: list[FacetInfo] = []
    for facet in facets.values():
        if facet.kind == "rollup":
            rollups.append(facet)
            continue
        for cu_key in facet.conformance_units:
            mapping.setdefault(cu_key, []).append(facet.display_name)
    for facet in rollups:
        for cu_key in facet.conformance_units:
            if cu_key not in mapping:
                mapping.setdefault(cu_key, []).append(facet.display_name)
    return mapping


def _ordered_cu_keys(by_cu: dict[str, Any], facets: dict[str, FacetInfo]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for facet in facets.values():
        for cu_key in facet.conformance_units:
            if cu_key in by_cu and cu_key not in seen:
                seen.add(cu_key)
                ordered.append(cu_key)
    ordered.extend(sorted(str(cu_key) for cu_key in by_cu if str(cu_key) not in seen))
    return ordered


def _cu_compliance_key(data: dict[str, Any]) -> str:
    explicit = str(data.get("compliance") or "")
    if explicit in _CU_COMPLIANCE_KEYS:
        return explicit

    passed = int(data.get("passed", 0) or 0)
    failed = int(data.get("failed", 0) or 0) + int(data.get("error", 0) or 0)
    not_supported = int(data.get("not_supported", 0) or 0)
    blocked = int(data.get("blocked", 0) or 0)
    accepted_policy = int(data.get("accepted_policy", 0) or 0)
    environment = int(data.get("environment", 0) or 0)
    skipped = int(data.get("skipped", 0) or 0)
    untested = int(data.get("untested", 0) or 0)
    test_count = int(data.get("test_count", 0) or 0)

    if failed:
        return "action_needed"
    if passed and (not_supported or blocked or skipped or untested):
        return "partial"
    if blocked:
        return "blocked"
    if not_supported:
        return "not_supported"
    if passed:
        return "supported"
    if accepted_policy or environment:
        return "blocked"
    if untested or test_count == 0:
        return "untested"
    return "unknown"


def _cu_compliance_label(status: str) -> str:
    labels = {
        "supported": "Supported",
        "partial": "Supported with Notes",
        "not_supported": "Not Supported",
        "blocked": "Blocked",
        "action_needed": "Action Needed",
        "untested": "Untested",
    }
    return labels.get(status, status.replace("_", " ").title() or "Unknown")


def _count_cu_outcomes(cu_keys: list[str], by_cu: dict[str, Any]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for cu_key in cu_keys:
        data_raw = by_cu.get(cu_key)
        data: dict[str, Any] = data_raw if isinstance(data_raw, dict) else {}
        counts[_cu_compliance_key(data)] += 1
    return counts


def _reason_bucket(message: str) -> str:
    msg = re.sub(r"\s+", " ", message.strip())
    if not msg:
        return "no reason"
    if msg.startswith("("):
        try:
            longrepr = ast.literal_eval(msg)
        except (SyntaxError, ValueError):
            longrepr = None
        if isinstance(longrepr, tuple) and longrepr and isinstance(longrepr[-1], str):
            msg = re.sub(r"\s+", " ", longrepr[-1].strip())
    msg = re.sub(r"^Skipped:\s*", "", msg, flags=re.IGNORECASE)
    msg = re.split(r"\s+-\s+CU:\s*", msg, maxsplit=1)[0].strip()
    msg = re.split(r"\.\s+To enable:\s*", msg, maxsplit=1)[0].strip()
    msg = re.split(r"\s+Config file:\s*", msg, maxsplit=1)[0].strip()
    not_supported = " NOT SUPPORTED"
    if not_supported in msg:
        end = msg.find(not_supported) + len(not_supported)
        return msg[:end].strip()
    if len(msg) > 180:
        return f"{msg[:177].rstrip()}..."
    return msg


def _cu_test_index(cu_payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    indexed: dict[str, list[dict[str, Any]]] = {}
    tests = cu_payload.get("tests")
    if not isinstance(tests, list):
        return indexed
    for test in tests:
        if not isinstance(test, dict):
            continue
        for cu_key in test.get("cus", []):
            indexed.setdefault(str(cu_key), []).append(test)
    return indexed


def _cu_note_summary(cu_key: str, tests_by_cu: dict[str, list[dict[str, Any]]]) -> str:
    tests = tests_by_cu.get(cu_key, [])
    priority = [
        ("failed", "Failed"),
        ("error", "Error"),
        ("blocked", "Blocked"),
        ("not_supported", "Not Supported"),
        ("accepted_policy", "Accepted Policy"),
        ("environment", "Environment"),
        ("skipped", "Skipped"),
        ("xfailed", "Expected Failure"),
        ("untested", "Untested"),
    ]
    notes: list[str] = []
    for outcome, label in priority:
        matching = [test for test in tests if str(test.get("outcome") or "") == outcome]
        if not matching:
            continue
        reason = next((_reason_bucket(str(test.get("reason") or "")) for test in matching if test.get("reason")), "")
        if reason and reason != "no reason":
            notes.append(f"{label}: {reason}")
        else:
            notes.append(f"{label}: {len(matching)} test(s)")
    if not notes:
        return ""
    if len(notes) > 2:
        return "; ".join(notes[:2]) + f"; {len(notes) - 2} more"
    return "; ".join(notes)


def _compliance_status(counts: Counter[str], total: int) -> str:
    if counts["action_needed"]:
        return "ACTION NEEDED"
    if counts["blocked"]:
        return "BLOCKED"
    if counts["partial"] or counts["not_supported"]:
        return "SUPPORTED WITH NOTES"
    if total and counts["supported"] == total:
        return "SUPPORTED"
    if counts["supported"]:
        return "SUPPORTED WITH NOTES"
    return "NO COMPLIANCE RESULT"


def _status_fill(status: str) -> PatternFill:
    colour = {
        "SUPPORTED": _LIGHT_GREEN,
        "SUPPORTED WITH NOTES": _LIGHT_GREEN_NOTE,
        "BLOCKED": _LIGHT_ORANGE,
        "ACTION NEEDED": _LIGHT_RED,
        "NO COMPLIANCE RESULT": _GRAY,
    }.get(status, _WHITE)
    return _fill(colour)


def _pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "n/a"
    return f"{(numerator * 100 / denominator):.1f}%"


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


def _write_metric_block(ws, start_row: int, rows: list[tuple[str, object]]) -> int:
    _apply_header(ws, start_row, ["Metric", "Value"], [34, 80])
    for idx, (label, value) in enumerate(rows, start=start_row + 1):
        ws.cell(row=idx, column=1, value=label).font = Font(bold=True)
        ws.cell(row=idx, column=2, value=value).alignment = Alignment(wrap_text=True, vertical="top")
    return start_row + len(rows) + 2


def _build_profile_coverage(
    wb: openpyxl.Workbook,
    cu_payload: dict[str, Any],
    profiles: dict[str, ProfileInfo],
    facets: dict[str, FacetInfo],
    capabilities: CapabilitiesInfo | None,
) -> None:
    ws = wb.create_sheet("Profile Coverage")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A10"

    by_cu = cu_payload.get("by_cu", {}) if isinstance(cu_payload.get("by_cu"), dict) else {}
    supported = _supported_set(cu_payload)
    summary = cu_payload.get("summary", {}) if isinstance(cu_payload.get("summary"), dict) else {}
    all_cu_keys = _ordered_cu_keys(by_cu, facets)

    ws["A1"] = "IJT Profiles, Facets, and Conformance Units Coverage"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = (
        "This sheet maps the current test run to IJT high-level coverage views, facets, and conformance units. "
        "Start with the Active Server Declaration row; Reference IJT Facet and Reference Full CU Set rows are comparison views only, not extra pass/fail requirements. "
        "Declared by Server comes from the active server declaration. Run Compliance and validated counts come from this test run. "
        "Raw skip reports remain diagnostic and may overlap with CU attention items."
    )
    ws["A2"].alignment = Alignment(wrap_text=True)

    active = capabilities.active_profile if capabilities else ""
    server = capabilities.server_name if capabilities else "Server under test"
    next_row = _write_metric_block(
        ws,
        4,
        [
            ("Server", server),
            ("Active server declaration", profiles.get(active, ProfileInfo(active, active or "Unknown", "", [])).name),
            ("Official IJT CUs", summary.get("official_cu_count", len(by_cu))),
            ("Declared by server", len(supported) if supported is not None else "n/a"),
            ("Workbook test cases", summary.get("workbook_case_count", "n/a")),
        ],
    )

    headers = [
        "View",
        "Role",
        "Facet Count",
        "CUs in View",
        "Declared by Server",
        "Validated Supported",
        "Validated with Notes",
        "Not Supported",
        "Blocked",
        "Action Needed",
        "Untested",
        "Declared by Server %",
        "Run Compliance",
        "Description",
    ]
    widths = [34, 28, 12, 10, 14, 12, 12, 14, 9, 13, 9, 12, 16, 70]
    _apply_header(ws, next_row, headers, widths)

    view_rows: list[tuple[str, str, int, list[str], str]] = []
    if active in profiles:
        profile = profiles[active]
        view_rows.append(
            (
                profile.name,
                "Active Server Declaration",
                len(profile.facets),
                _cus_for_profile(profile, facets),
                profile.description,
            )
        )

    for facet_key in (
        "basic_joining_system_server_facet",
        "general_joining_system_server_facet",
        "joining_system_selectable_features_server_facet",
    ):
        facet = facets.get(facet_key)
        if facet is None:
            continue
        view_rows.append(
            (
                facet.display_name,
                "Reference IJT Facet",
                1,
                facet.conformance_units,
                facet.description,
            )
        )

    if active != "full_conformance":
        view_rows.append(
            (
                "Full IJT Base CU Set",
                "Reference Full CU Set",
                len(facets),
                all_cu_keys,
                "Flat reference view of all unique IJT Base conformance units.",
            )
        )

    row = next_row + 1
    for view_name, role, facet_count, cu_keys, description in view_rows:
        counts = _count_cu_outcomes(cu_keys, by_cu)
        server_profile_cus = _server_profile_cu_count(cu_keys, supported)
        compliance = _compliance_status(counts, len(cu_keys))
        values = [
            view_name,
            role,
            facet_count,
            len(cu_keys),
            server_profile_cus,
            counts["supported"],
            counts["partial"],
            counts["not_supported"],
            counts["blocked"],
            counts["action_needed"],
            counts["untested"],
            _server_profile_pct(server_profile_cus, len(cu_keys)),
            compliance,
            description,
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if col == 2 and value == "Active Server Declaration":
                cell.fill = _fill(_LIGHT_BLUE)
                cell.font = Font(bold=True)
            if col == 13:
                cell.fill = _status_fill(str(value))
                cell.font = Font(bold=True)
        row += 1

    ws.auto_filter.ref = f"A{next_row}:N{row - 1}"


def _build_facet_coverage(
    wb: openpyxl.Workbook,
    cu_payload: dict[str, Any],
    facets: dict[str, FacetInfo],
    capabilities: CapabilitiesInfo | None,
) -> None:
    ws = wb.create_sheet("Facet Coverage")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"

    by_cu = cu_payload.get("by_cu", {}) if isinstance(cu_payload.get("by_cu"), dict) else {}
    supported = _supported_set(cu_payload)
    active_extra_facets = set(capabilities.supported_facets if capabilities else [])

    headers = [
        "Facet",
        "Facet Key",
        "Facet Type",
        "CUs in Facet",
        "Declared by Server",
        "Validated Supported",
        "Validated with Notes",
        "Not Supported",
        "Blocked",
        "Action Needed",
        "Untested",
        "Declared by Server %",
        "Run Compliance",
        "Description",
    ]
    widths = [34, 34, 12, 10, 14, 12, 12, 14, 9, 13, 9, 12, 16, 70]
    _apply_header(ws, 1, headers, widths)

    for row, facet in enumerate(facets.values(), start=2):
        cu_keys = facet.conformance_units
        counts = _count_cu_outcomes(cu_keys, by_cu)
        server_profile_cus = _server_profile_cu_count(cu_keys, supported)
        compliance = _compliance_status(counts, len(cu_keys))
        facet_type = "Rollup" if facet.kind == "rollup" else "Facet"
        if facet.key in active_extra_facets:
            facet_type = f"Additional {facet_type}"
        values = [
            facet.display_name,
            facet.key,
            facet_type,
            len(cu_keys),
            server_profile_cus,
            counts["supported"],
            counts["partial"],
            counts["not_supported"],
            counts["blocked"],
            counts["action_needed"],
            counts["untested"],
            _server_profile_pct(server_profile_cus, len(cu_keys)),
            compliance,
            facet.description,
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if col == 13:
                cell.fill = _status_fill(str(value))
                cell.font = Font(bold=True)

    ws.auto_filter.ref = f"A1:N{max(1, len(facets) + 1)}"


def _build_cu_coverage(
    wb: openpyxl.Workbook,
    cu_payload: dict[str, Any],
    facets: dict[str, FacetInfo],
    capabilities: CapabilitiesInfo | None,
) -> None:
    ws = wb.create_sheet("CU Coverage")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"

    by_cu = cu_payload.get("by_cu", {}) if isinstance(cu_payload.get("by_cu"), dict) else {}
    supported = _supported_set(cu_payload)
    facet_map = _cu_to_facets(facets)
    overrides = capabilities.overrides if capabilities else {}
    ordered_keys = _ordered_cu_keys(by_cu, facets)
    tests_by_cu = _cu_test_index(cu_payload)

    headers = [
        "CU",
        "CU Key",
        "Facet(s)",
        "Declared by Server",
        "Run Compliance",
        "Tests",
        "Passed",
        "Not Supported",
        "Blocked",
        "Failed/Error",
        "Workbook Cases",
        "Positive",
        "Negative",
        "Override",
        "Notes",
        "Example Test",
    ]
    widths = [34, 34, 44, 18, 16, 8, 8, 14, 9, 12, 14, 9, 9, 14, 80, 80]
    _apply_header(ws, 1, headers, widths)

    for row, cu_key in enumerate(ordered_keys, start=2):
        data_raw = by_cu.get(cu_key)
        data: dict[str, Any] = data_raw if isinstance(data_raw, dict) else {}
        compliance = _cu_compliance_key(data)
        failed = int(data.get("failed", 0) or 0) + int(data.get("error", 0) or 0)
        tests = data.get("tests") if isinstance(data.get("tests"), list) else []
        support = _in_server_profile(cu_key, supported)
        values = [
            _cu_display_name(cu_key),
            cu_key,
            ", ".join(facet_map.get(cu_key, [])),
            support,
            _cu_compliance_label(compliance),
            int(data.get("test_count", 0) or 0),
            int(data.get("passed", 0) or 0),
            int(data.get("not_supported", 0) or 0),
            int(data.get("blocked", 0) or 0),
            failed,
            int(data.get("workbook_case_count", 0) or 0),
            int(data.get("workbook_positive_case_count", 0) or 0),
            int(data.get("workbook_negative_case_count", 0) or 0),
            overrides.get(cu_key, ""),
            _cu_note_summary(cu_key, tests_by_cu),
            str(tests[0]) if tests else "",
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if col == 4 and value == "No":
                cell.fill = _fill(_LIGHT_YELLOW)
            if col == 5:
                cell.fill = _fill(_CU_STATUS_COLOUR.get(compliance, _WHITE))
                cell.font = Font(bold=True)

    ws.auto_filter.ref = f"A1:P{max(1, len(ordered_keys) + 1)}"


# ── Main ──────────────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--xml", default="test-results/pytest.xml", help="JUnit XML input file")
    p.add_argument("--out", default="test-results/report.xlsx", help="Excel output file")
    p.add_argument(
        "--cu-json",
        default=str(_DEFAULT_CU_JSON),
        help="Optional CU compliance JSON input for profile/facet/CU sheets",
    )
    p.add_argument(
        "--capabilities",
        default=None,
        help="Optional server capabilities YAML used to label the active profile",
    )
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
    cu_payload = _load_json(Path(args.cu_json))
    capabilities = _load_capabilities(Path(args.capabilities)) if args.capabilities else None
    facets = _load_facets()
    profiles = _load_profiles()

    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default empty sheet

    _build_summary(wb, cases, run_ts)
    _build_all_tests(wb, cases)
    _build_filtered(wb, cases, "Failures", ["failed", "error"], _RED)
    _build_filtered(wb, cases, "Skipped", ["skipped"], _YELLOW)
    _build_filtered(wb, cases, "Expected Fail", ["xfailed", "xpassed"], _ORANGE)
    if cu_payload and facets:
        _build_profile_coverage(wb, cu_payload, profiles, facets, capabilities)
        _build_facet_coverage(wb, cu_payload, facets, capabilities)
        _build_cu_coverage(wb, cu_payload, facets, capabilities)

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
    if cu_payload and facets:
        print("  CU sheets: Profile Coverage, Facet Coverage, CU Coverage")
    if failed > 0:
        print(f"\n  *** {failed} FAILURE(S) — see 'Failures' sheet ***")
    return 0


if __name__ == "__main__":
    sys.exit(main())
