from __future__ import annotations

import importlib
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).parents[2]
_SCRIPTS = _ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS))

_shim: Any = importlib.import_module("make_conformance_summary")
_renderer: Any = importlib.import_module("reporting.conformance_summary")
# Tests historically referred to the renderer module as ``_ci_summary``; keep
# that alias to minimise diff churn now that the renderer is its own module.
# All renderer entry points are accessed through this alias; ``_shim`` is used
# only for the CLI-shim-owned helpers (``_parse``, ``_load_*``,
# ``_write_baseline``). No module-level mutation of either binding.
_ci_summary: Any = _renderer
_excel_report: Any = importlib.import_module("make_excel_report")
_git_info: Any = importlib.import_module("helpers.git_info")
_report_scoring: Any = importlib.import_module("helpers.report_scoring")
ACTION_NEEDED, BLOCKED, NOT_SUPPORTED, WITH_NOTES = _report_scoring.KPI_LABELS

KPI_PATTERN = re.compile(
    rf"{re.escape(_report_scoring.KPI_ICONS[ACTION_NEEDED])}\s+(\d+)\s+"
    rf"{re.escape(ACTION_NEEDED)}"
    rf"{re.escape(_report_scoring.KPI_SEPARATOR)}"
    rf"{re.escape(_report_scoring.KPI_ICONS[BLOCKED])}\s+(\d+)\s+"
    rf"{re.escape(BLOCKED)}"
    rf"{re.escape(_report_scoring.KPI_SEPARATOR)}"
    rf"{re.escape(_report_scoring.KPI_ICONS[NOT_SUPPORTED])}\s+(\d+)\s+"
    rf"{re.escape(NOT_SUPPORTED)}"
    rf"{re.escape(_report_scoring.KPI_SEPARATOR)}"
    rf"{re.escape(_report_scoring.KPI_ICONS[WITH_NOTES])}\s+(\d+)\s+"
    rf"{re.escape(WITH_NOTES)}"
)


def _expected_kpi_counts(counts: Mapping[str, int]) -> dict[str, int]:
    return {
        label: int(counts.get(_report_scoring.status_count_key(label), counts.get(label, 0)) or 0)
        for label in _report_scoring.KPI_LABELS
    }


def _label_counts(action_needed: int, blocked: int, not_supported: int, with_notes: int) -> dict[str, int]:
    values = (action_needed, blocked, not_supported, with_notes)
    return dict(zip(_report_scoring.KPI_LABELS, values, strict=True))


def _assert_kpi_strip(rendered: str, counts: Mapping[str, int]) -> str:
    match = KPI_PATTERN.search(rendered)
    assert match is not None, "KPI strip missing or format drifted"
    observed = {label: int(value) for label, value in zip(_report_scoring.KPI_LABELS, match.groups(), strict=True)}
    assert observed == _expected_kpi_counts(counts)
    return match.group(0)


def _sample_payload() -> dict[str, Any]:
    return {
        "supported_cus": ["joining_system_base", "state_policy_note"],
        "by_cu": {
            "joining_system_base": {
                "passed": 2,
                "test_count": 2,
                "workbook_case_count": 3,
            },
            "state_policy_note": {
                "passed": 1,
                "accepted_policy": 1,
                "test_count": 2,
                "workbook_case_count": 1,
            },
            "optional_feature": {
                "not_supported": 1,
                "test_count": 1,
                "workbook_case_count": 2,
            },
            "outside_profile_note": {
                "not_supported": 1,
                "test_count": 1,
                "workbook_case_count": 1,
            },
        },
        "tests": [
            {
                "cus": ["optional_feature"],
                "nodeid": "conformance/test_optional.py::test_optional_feature",
                "outcome": "not_supported",
                "reason": "Skipped: OptionalFeature: Not Supported — cannot run optional feature",
            },
            {
                "cus": ["outside_profile_note"],
                "nodeid": "conformance/test_optional.py::test_outside_profile_note",
                "outcome": "not_supported",
                "reason": "Skipped: OutsideProfileNote: Not Supported — outside active profile",
            },
            {
                "cus": ["state_policy_note"],
                "nodeid": "conformance/test_state.py::test_state_policy",
                "outcome": "accepted_policy",
                "reason": "Skipped: ACCEPTED POLICY - Method: SelectJoiningProcess - state not ready",
            },
        ],
    }


def _patch_ci_metadata(monkeypatch):
    monkeypatch.setattr(
        _ci_summary,
        "_load_facets",
        lambda: {
            "basic_facet": {
                "display_name": "Basic Facet",
                "description": "Basic joining-system support.",
                "conformance_units": ["joining_system_base", "state_policy_note", "optional_feature"],
            },
            "basic_joining_system_server_facet": {
                "display_name": "Basic Joining System Server Facet",
                "description": "Basic joining system reference facet.",
                "conformance_units": ["joining_system_base"],
            },
        },
    )
    monkeypatch.setattr(
        _ci_summary,
        "_load_profiles",
        lambda: {
            "full_conformance": {
                "name": "Full Conformance",
                "facets": ["basic_facet"],
            },
        },
    )
    monkeypatch.setattr(
        _ci_summary,
        "_load_capabilities",
        lambda: {
            "server": {"name": "Report Test Server"},
            "active_profile": "full_conformance",
        },
    )


def _excel_metadata():
    facets = {
        "basic_facet": _excel_report.FacetInfo(
            "basic_facet",
            "Basic Facet",
            "Basic joining-system support.",
            "",
            "facet",
            ["joining_system_base", "state_policy_note", "optional_feature"],
        ),
        "basic_joining_system_server_facet": _excel_report.FacetInfo(
            "basic_joining_system_server_facet",
            "Basic Joining System Server Facet",
            "Basic joining system reference facet.",
            "",
            "facet",
            ["joining_system_base"],
        ),
    }
    profiles = {
        "full_conformance": _excel_report.ProfileInfo(
            "full_conformance",
            "Full Conformance",
            "",
            ["basic_facet"],
        )
    }
    capabilities = _excel_report.CapabilitiesInfo("Report Test Server", "full_conformance", [], {})
    return profiles, facets, capabilities


def test_ci_summary_skip_reason_bucket_preserves_public_method_label():
    reason = (
        "IJT Send Joining Process - Method: SendJoiningProcess NOT SUPPORTED "
        "- CU: send_joining_process. To enable: update server_capabilities.yaml"
    )

    assert _ci_summary._skip_reason_bucket(reason) == (
        "IJT Send Joining Process - Method: SendJoiningProcess NOT SUPPORTED"
    )


def test_report_compliance_key_labels_mixed_pass_and_blocked_as_notes():
    data = {"passed": 2, "blocked": 1, "not_supported": 0, "failed": 0, "error": 0, "test_count": 3}

    assert _ci_summary._cu_compliance_key(data) == "partial"
    assert _excel_report._cu_compliance_label(_excel_report._cu_compliance_key(data)) == "Supported with Notes"


def test_report_compliance_key_prefers_explicit_json_field():
    data = {
        "outcome": "passed",
        "compliance": "partial",
        "passed": 3,
        "blocked": 0,
        "not_supported": 0,
        "failed": 0,
        "error": 0,
        "test_count": 3,
    }

    assert _ci_summary._cu_compliance_key(data) == "partial"
    assert _excel_report._cu_compliance_key(data) == "partial"


def test_report_compliance_key_keeps_blocked_conservative_without_passes():
    data = {
        "passed": 0,
        "blocked": 1,
        "not_supported": 2,
        "failed": 0,
        "error": 0,
        "test_count": 3,
    }

    assert _ci_summary._cu_compliance_key(data) == "blocked"
    assert _excel_report._cu_compliance_key(data) == "blocked"


def test_report_compliance_key_ignores_accepted_policy_when_support_passed():
    data = {
        "passed": 2,
        "accepted_policy": 3,
        "environment": 1,
        "blocked": 0,
        "not_supported": 0,
        "failed": 0,
        "error": 0,
        "test_count": 6,
    }

    assert _ci_summary._cu_compliance_key(data) == "supported"
    assert _excel_report._cu_compliance_key(data) == "supported"


def test_excel_percentage_fill_thresholds():
    cases = [
        (100.0, _excel_report._LIGHT_GREEN),
        (99.9, _excel_report._LIGHT_GREEN),
        (99.89, _excel_report._LIGHT_GREEN_NOTE),
        (95.0, _excel_report._LIGHT_GREEN_NOTE),
        (90.0, _excel_report._LIGHT_GREEN_NOTE),
        (89.9, _excel_report._LIGHT_YELLOW),
        (75.0, _excel_report._LIGHT_YELLOW),
        (74.9, _excel_report._LIGHT_ORANGE),
        (50.0, _excel_report._LIGHT_ORANGE),
        (49.9, _excel_report._LIGHT_RED),
        (0.0, _excel_report._LIGHT_RED),
        ("n/a", _excel_report._GRAY),
    ]

    for value, expected_colour in cases:
        assert _excel_report._percentage_fill(value).fgColor.rgb == expected_colour


def test_conformance_score_formula():
    assert (
        _ci_summary._conformance_score({"supported": 10, "partial": 0, "action_needed": 0, "blocked": 0}, 10, 10) == 100
    )
    assert (
        _ci_summary._conformance_score({"supported": 95, "partial": 3, "action_needed": 0, "blocked": 0}, 98, 123) == 94
    )
    assert (
        _ci_summary._conformance_score({"supported": 9, "partial": 0, "action_needed": 1, "blocked": 0}, 10, 10) <= 50
    )
    assert (
        _ci_summary._conformance_score({"supported": 9, "partial": 0, "action_needed": 0, "blocked": 1}, 10, 10) <= 75
    )
    assert (
        _ci_summary._conformance_score({"supported": 5, "partial": 0, "action_needed": 0, "blocked": 0}, 10, 10) == 65
    )
    assert _ci_summary._conformance_score({"supported": 0, "partial": 0, "action_needed": 0, "blocked": 0}, 0, 0) == 0


def test_markdown_and_excel_share_report_scoring_helpers():
    assert _ci_summary._conformance_score is _report_scoring.conformance_score
    assert _excel_report._conformance_score is _report_scoring.conformance_score
    assert _ci_summary._status_for is _report_scoring.status_for
    assert _excel_report._status_for is _report_scoring.status_for
    assert _ci_summary._is_healthy is _report_scoring.is_healthy
    assert _excel_report._is_healthy is _report_scoring.is_healthy


def test_markdown_and_excel_use_same_status_count_formatter():
    assert _ci_summary._format_status_counts is _report_scoring.format_status_counts
    assert _excel_report._format_status_counts is _report_scoring.format_status_counts


def test_report_scoring_public_maps_are_immutable():
    with pytest.raises(TypeError):
        cast_icons: Any = _report_scoring.KPI_ICONS
        cast_icons[ACTION_NEEDED] = "x"


def test_status_colors_cover_all_kpi_labels():
    assert set(_report_scoring.STATUS_COLORS_EXCEL) == set(_report_scoring.KPI_LABELS)
    for label in _report_scoring.KPI_LABELS:
        assert _report_scoring.status_color_excel(label) == _report_scoring.STATUS_COLORS_EXCEL[label]


def test_markdown_and_excel_share_git_info_helper():
    assert _ci_summary._short_git_sha is _git_info.short_git_sha
    assert _excel_report._short_git_sha is _git_info.short_git_sha


def test_format_kpi_strip_round_trip():
    cases = [
        _label_counts(0, 0, 0, 0),
        _label_counts(1, 2, 3, 4),
        _label_counts(99, 0, 0, 0),
        {"action_needed": 1, "blocked": 0, "not_supported": 2, "with_notes": 3},
    ]

    for counts in cases:
        rendered = _report_scoring.format_kpi_strip(counts)
        assert _assert_kpi_strip(rendered, counts) == rendered


def test_internal_action_needed_key_renders_failed_public_label():
    rendered = _report_scoring.format_kpi_strip({"action_needed": 1, "blocked": 0, "not_supported": 0, "with_notes": 0})

    assert _report_scoring.status_count_key("Failed") == "action_needed"
    assert "🔴 1 Failed" in rendered
    assert "Action Needed" not in rendered


def test_format_status_count_and_label_use_shared_icons():
    supported = _report_scoring.outcome_label("supported")

    assert _report_scoring.format_status_count(ACTION_NEEDED, 7) == (
        f"{_report_scoring.KPI_ICONS[ACTION_NEEDED]} 7 {ACTION_NEEDED}"
    )
    assert (
        _report_scoring.format_status_label(ACTION_NEEDED)
        == f"{_report_scoring.KPI_ICONS[ACTION_NEEDED]} {ACTION_NEEDED}"
    )
    assert _report_scoring.format_status_label(supported) == f"{_report_scoring.NON_KPI_ICONS[supported]} {supported}"


def test_status_mapping():
    active = {"in_profile"}

    assert _ci_summary._status_for("cu", "action_needed", active) == (
        ACTION_NEEDED,
        _report_scoring.KPI_ICONS[ACTION_NEEDED],
    )
    assert _ci_summary._status_for("cu", "blocked", active) == (
        BLOCKED,
        _report_scoring.KPI_ICONS[BLOCKED],
    )
    assert _ci_summary._status_for("in_profile", "not_supported", active) == (
        NOT_SUPPORTED,
        _report_scoring.KPI_ICONS[NOT_SUPPORTED],
    )
    assert _ci_summary._status_for("outside_profile", "not_supported", active) == (
        WITH_NOTES,
        _report_scoring.KPI_ICONS[WITH_NOTES],
    )
    assert _ci_summary._status_for("cu", "partial", active) == (
        WITH_NOTES,
        _report_scoring.KPI_ICONS[WITH_NOTES],
    )


def test_ci_summary_renders_audience_sections(monkeypatch):
    _patch_ci_metadata(monkeypatch)
    payload = _sample_payload()

    lines, context = _ci_summary._render_profile_facet_summary(payload)
    rendered = "\n".join(lines)

    assert context is not None
    assert context["score"] == 90
    assert "### Change Since Last Run" not in rendered
    assert "Review Items" not in rendered
    assert "🆕" not in rendered
    assert " resolved " not in rendered
    assert " regressed " not in rendered
    assert "## 🧩 IJT Facet Support" in rendered
    assert "## 📌 Conformance Action Items" not in rendered
    assert "## 📝 Server Scope Notes" in rendered
    assert "Information only; review scope and caveats. See Conformance Unit Details below." in rendered
    assert "## 📐 IJT Facet Breakdown" in rendered
    assert "## 📋 Conformance Unit Details" in rendered
    assert "<summary><b>2 rows needing review · 4 total CUs</b></summary>" in rendered
    assert "<summary><b>Coverage Overview</b></summary>" not in rendered
    assert "<summary><b>Conformance Status</b></summary>" not in rendered
    assert "<summary><b>Full CU Coverage</b></summary>" not in rendered
    assert "<summary><b>Test Client Environment</b></summary>" in rendered
    assert "<summary><b>Glossary and Reading Guide</b></summary>" not in rendered
    assert rendered.count("# IJT Conformance Test Report") == 0
    assert "## Coverage Overview" not in rendered
    assert "Server Supported CUs" in rendered
    assert "Server Support %" in rendered
    assert "Supported CUs Validated %" in rendered
    assert "Outcome" in rendered
    for legacy_term in (
        "Dec" + "lared",
        "dec" + "lared",
        "Run " + "Status",
        "Run " + "Overview",
        "Validation " + "Status",
        "Severity",
        "Top " + "Findings",
        "Critical",
        "Major",
        "Minor",
    ):
        assert legacy_term not in rendered
    supported_label = _report_scoring.outcome_label("supported")
    supported_status = _report_scoring.format_outcome_label("supported")
    supported_with_notes_status = _report_scoring.format_outcome_label("partial")
    not_supported_status = _report_scoring.format_outcome_label("not_supported")

    assert "Primary Reason" in rendered
    assert "OptionalFeature: Not Supported" in rendered
    assert not_supported_status in rendered
    assert f"{context['findings_count']['with_notes']} with notes" in rendered
    assert (
        "| Basic Facet | Facet | 3 | 2 | 66.7% | 100.0% | "
        f"2 {supported_label}<br>0 {WITH_NOTES}<br>1 {NOT_SUPPORTED}<br>0 {BLOCKED}<br>"
        f"0 {ACTION_NEEDED} | {supported_with_notes_status} |" in rendered
    )
    assert (
        "| IJT Joining System Base | Basic Facet, Basic Joining System Server Facet "
        f"| Yes | {supported_status} |  | 2 | 2 | 0 | 0 | 0 | 3 |"
    ) in rendered
    assert f"| IJT State Policy Note | Basic Facet | Yes | {supported_status} |  | 2 | 1 | 0 | 0 | 0 | 1 |" in rendered
    assert (
        f"| ⚪ Not Supported | IJT Optional Feature | Basic Facet | No | {not_supported_status} | "
        "OptionalFeature: Not Supported — cannot run optional feature | 1 | 0 | 1 | 0 | 0 | 2 |" in rendered
    )
    assert "Accepted Policy: ACCEPTED POLICY - Method: SelectJoiningProcess - state not ready" not in rendered


def test_full_markdown_uses_layered_headings(monkeypatch):
    _patch_ci_metadata(monkeypatch)
    data = {
        "passed": 5,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "xfailed": 0,
        "total": 5,
        "duration_s": 12,
        "failures": [],
        "skip_reasons": {},
        "xfail_reasons": {},
    }

    rendered, _context = _ci_summary.render_conformance_summary(
        data,
        "opc.tcp://localhost:40462",
        "2026-05-10 15:46 UTC",
        _sample_payload(),
    )
    lines = rendered.splitlines()

    assert lines.count("# IJT Conformance Test Report") == 1
    assert any(line.startswith("## 📊 Conformance Overview") for line in lines)
    assert any(line.startswith("## 🧩 IJT Facet Support") for line in lines)
    assert not any(line.startswith("## 📌 Conformance Action Items") for line in lines)
    assert any(line.startswith("## 📝 Server Scope Notes") for line in lines)
    assert "Conformance Action Items" in rendered
    assert "Server Scope Notes" in rendered
    assert (
        _report_scoring.format_status_counts(_report_scoring.ACTION_ITEM_LABEL_ORDER, _context["findings_count"])
        in rendered
    )
    assert (
        _report_scoring.format_status_counts(_report_scoring.CAPABILITY_NOTE_LABEL_ORDER, _context["findings_count"])
        in rendered
    )
    assert "## 📋 Conformance Unit Details" in rendered
    # When skip_reasons and xfail_reasons are both empty, Diagnostics bundle is omitted entirely.
    assert "<summary><b>Skip &amp; Expected-Failure Diagnostics</b></summary>" not in rendered
    assert "_No diagnostic skips on this run._" not in rendered
    assert "**Diagnostic Skips**" not in rendered


def test_review_items_sort_order(monkeypatch):
    _patch_ci_metadata(monkeypatch)
    payload = _sample_payload()
    payload["by_cu"]["joining_system_base"] = {"failed": 1, "test_count": 1}
    payload["by_cu"]["state_policy_note"] = {"blocked": 1, "test_count": 1}

    _lines, context = _ci_summary._render_profile_facet_summary(payload)

    assert [finding["status"] for finding in context["findings"][:3]] == [
        ACTION_NEEDED,
        BLOCKED,
        NOT_SUPPORTED,
    ]


def test_baseline_kwarg_is_silently_ignored_by_renderer(monkeypatch):
    """``render_conformance_summary`` accepts ``baseline`` for backwards compatibility but never uses it."""
    _patch_ci_metadata(monkeypatch)
    baseline = {
        "run_ts": "2026-05-09T14:21:00Z",
        "git_sha": "abc123e",
        "score": 80,
        "validation_health_pct": 50.0,
        "spec_coverage_pct": 66.7,
        "cu_outcomes": {
            "joining_system_base": "supported",
            "state_policy_note": "not_supported",
            "optional_feature": "supported",
        },
    }
    data = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "xfailed": 0,
        "total": 0,
        "duration_s": 0,
        "failures": [],
        "skip_reasons": {},
        "xfail_reasons": {},
    }

    rendered, _ctx = _ci_summary.render_conformance_summary(
        data,
        "opc.tcp://fixture.test:40451",
        "2026-05-10 15:46 UTC",
        _sample_payload(),
        baseline,
    )

    assert "Change Since Last Run" not in rendered
    assert "Review Items" not in rendered
    assert "🆕" not in rendered
    assert " resolved " not in rendered
    assert " regressed " not in rendered
    assert "abc123e" not in rendered


def test_baseline_written_after_render():
    baseline_path = _ROOT / "test-results" / "report-baseline-unit-test.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    context = {
        "score": 94,
        "validation_health_value": 100.0,
        "spec_coverage_value": 79.7,
        "findings_count": {"action_needed": 0, "blocked": 0, "not_supported": 25, "with_notes": 3},
        "cu_outcomes": {"joining_system_base": "supported"},
    }

    try:
        baseline_env = _ci_summary.ReportEnvironment.from_runtime()
        _shim._write_baseline(
            baseline_path,
            _ci_summary._baseline_payload(context, "2026-05-10T15:46:00Z", baseline_env),
        )

        written = json.loads(baseline_path.read_text(encoding="utf-8"))
        assert written["score"] == 94
        assert written["validation_health_pct"] == 100.0
        assert written["spec_coverage_pct"] == 79.7
        assert written["cu_outcomes"] == {"joining_system_base": "supported"}
        assert written["git_sha"] == baseline_env.git_sha
    finally:
        baseline_path.unlink(missing_ok=True)


def test_excel_cover_sheet_exists_and_first():
    profiles, facets, capabilities = _excel_metadata()
    payload = _sample_payload()
    context = _excel_report._build_report_context(payload, profiles, facets, capabilities)
    wb = _excel_report.openpyxl.Workbook()
    wb.remove(wb.active)

    _excel_report._build_cover(wb, [], "2026-05-10 15:46:00", "passed", context, facets)

    assert wb.sheetnames[0] == "Conformance Overview"
    assert wb["Conformance Overview"]["A1"].value == (
        "🟢 PASSED · 0 action items · Validation 100.0% (2/2) · Server support 66.7% (2/3)"
    )
    assert wb["Conformance Overview"]["A8"].value == "Server Scope Notes"
    assert wb["Conformance Overview"]["B8"].value == _report_scoring.format_status_counts(
        _report_scoring.CAPABILITY_NOTE_LABEL_ORDER, context["findings_count"]
    )
    values = [cell.value for row in wb["Conformance Overview"].iter_rows() for cell in row]
    assert "Conformance Action Items" not in values


def test_excel_cover_status_counts_use_separator():
    profiles, facets, capabilities = _excel_metadata()
    context = _excel_report._build_report_context(_sample_payload(), profiles, facets, capabilities)
    wb = _excel_report.openpyxl.Workbook()
    wb.remove(wb.active)

    _excel_report._build_cover(wb, [], "2026-05-10 15:46:00", "passed", context, facets)

    rendered = str(wb["Conformance Overview"]["B8"].value)
    assert _report_scoring.KPI_SEPARATOR in rendered
    assert "/" not in rendered


def test_excel_cover_has_no_change_since_last_run_section():
    profiles, facets, capabilities = _excel_metadata()
    context = _excel_report._build_report_context(_sample_payload(), profiles, facets, capabilities)
    wb = _excel_report.openpyxl.Workbook()
    wb.remove(wb.active)

    _excel_report._build_cover(wb, [], "2026-05-10 15:46:00", "passed", context, facets)

    values = [
        str(cell.value) for row in wb["Conformance Overview"].iter_rows() for cell in row if cell.value is not None
    ]
    assert "Change Since Last Run" not in values
    assert "Review Items" not in values
    assert "IJT Facet Support" in values


def test_excel_cu_coverage_has_no_change_column():
    profiles, facets, capabilities = _excel_metadata()
    payload = _sample_payload()
    context = _excel_report._build_report_context(payload, profiles, facets, capabilities)
    wb = _excel_report.openpyxl.Workbook()
    wb.remove(wb.active)

    _excel_report._build_cu_coverage(wb, payload, facets, capabilities, context)
    ws = wb["Conformance Unit Details"]

    headers = [ws.cell(row=1, column=col).value for col in range(1, 19)]
    assert "Change" not in headers
    assert ws["A1"].value == "Review Status"
    assert ws["B1"].value == "CU"


def test_skip_diagnostics_filters_not_supported_prefix_in_markdown(monkeypatch):
    """Spec: 'Not Supported:' reasons are filtered from the markdown Diagnostic Skips table,
    but the raw data['skip_reasons'] input is left untouched for Excel/baseline consumers.
    """
    _patch_ci_metadata(monkeypatch)
    raw_skips = {
        "Not Supported: missing precondition": 4,
        "Server unavailable": 2,
    }
    data = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 6,
        "xfailed": 0,
        "total": 6,
        "duration_s": 1,
        "failures": [],
        "skip_reasons": raw_skips,
        "xfail_reasons": {},
    }

    rendered, _ctx = _ci_summary.render_conformance_summary(
        data, "opc.tcp://localhost:40462", "2026-05-10 15:46 UTC", _sample_payload()
    )

    # Markdown Diagnostic Skips table omits the 'Not Supported:' bucket.
    assert "Not Supported: missing precondition" not in rendered
    assert "Server unavailable" in rendered
    # The raw input dict the caller passes is not mutated by the renderer.
    assert raw_skips == {
        "Not Supported: missing precondition": 4,
        "Server unavailable": 2,
    }


def test_github_summary_never_does_not_touch_step_summary(tmp_path, monkeypatch):
    """Spec: --github-summary=never must not write to GITHUB_STEP_SUMMARY even when set."""
    import subprocess

    fixt = Path(__file__).parent / "reporting" / "fixtures" / "ci_unit_no_cu_payload"
    step_summary = tmp_path / "step_summary.md"
    step_summary.write_text("PRE-EXISTING\n", encoding="utf-8")

    out_md = tmp_path / "summary.md"
    baseline_path = tmp_path / "baseline.json"
    env = {
        **dict(__import__("os").environ),
        "GITHUB_STEP_SUMMARY": str(step_summary),
    }
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPTS / "make_conformance_summary.py"),
            "--xml",
            str(fixt / "pytest.xml"),
            "--out",
            str(out_md),
            "--baseline",
            str(baseline_path),
            "--cu-json",
            str(fixt / "cu_results.json"),
            "--github-summary=never",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert out_md.exists()
    # Step summary file is untouched.
    assert step_summary.read_text(encoding="utf-8") == "PRE-EXISTING\n"


def test_is_conformance_skip_reason_helper():
    """Helper filters reasons that display as 'Not Supported:' (after normalization)."""
    assert _ci_summary._is_conformance_skip_reason("Not Supported: missing precondition") is True
    # Display normalization is case-insensitive on the prefix, so lower-case variants are also filtered.
    assert _ci_summary._is_conformance_skip_reason("not supported: lower") is True
    assert _ci_summary._is_conformance_skip_reason("Server unavailable") is False
    assert _ci_summary._is_conformance_skip_reason("") is False


def test_glossary_url_absolute_when_github_env_set(monkeypatch):
    """When GITHUB_SERVER_URL, GITHUB_REPOSITORY, and GITHUB_SHA are all set,
    _glossary_url() returns an absolute blob URL pinned to the run's commit."""
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "OPCFoundation/UA-for-Industrial-Joining-Technologies")
    monkeypatch.setenv("GITHUB_SHA", "abc1234deadbeef")
    url = _ci_summary._glossary_url()
    assert url == (
        "https://github.com/OPCFoundation/UA-for-Industrial-Joining-Technologies/blob/"
        "abc1234deadbeef/OPC_UA_Clients/Release2/IJT_Test_Client/docs/REPORT_GLOSSARY.md"
    )


def test_glossary_url_relative_when_github_env_unset(monkeypatch):
    """When any of the GITHUB_* env vars are missing, _glossary_url() falls
    back to the repo-relative path so local IDE previews keep working."""
    for key in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_SHA"):
        monkeypatch.delenv(key, raising=False)
    assert _ci_summary._glossary_url() == ("OPC_UA_Clients/Release2/IJT_Test_Client/docs/REPORT_GLOSSARY.md")
    # Partial env (only two of three set) must also fall back to relative.
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    assert _ci_summary._glossary_url() == ("OPC_UA_Clients/Release2/IJT_Test_Client/docs/REPORT_GLOSSARY.md")
