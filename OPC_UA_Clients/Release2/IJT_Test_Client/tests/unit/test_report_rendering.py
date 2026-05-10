from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).parents[2]
_SCRIPTS = _ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS))

_ci_summary: Any = importlib.import_module("make_ci_summary")
_excel_report: Any = importlib.import_module("make_excel_report")
_report_scoring: Any = importlib.import_module("helpers.report_scoring")


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
        },
        "tests": [
            {
                "cus": ["optional_feature"],
                "nodeid": "conformance/test_optional.py::test_optional_feature",
                "outcome": "not_supported",
                "reason": "Skipped: OptionalFeature: Not Supported — cannot run optional feature",
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
    assert _ci_summary._severity_for is _report_scoring.severity_for
    assert _excel_report._severity_for is _report_scoring.severity_for
    assert _ci_summary._delta_symbol is _report_scoring.delta_symbol
    assert _excel_report._delta_symbol is _report_scoring.delta_symbol


def test_delta_symbol_marks_new_cus_only_with_prior_baseline():
    assert _ci_summary._delta_symbol("new_cu", "supported", None) == ""
    assert _ci_summary._delta_symbol("new_cu", "supported", {"cu_outcomes": {}}) == ""
    assert _ci_summary._delta_symbol("new_cu", "supported", {"cu_outcomes": {"old_cu": "supported"}}) == "New"
    assert _ci_summary._delta_symbol("stable_cu", "supported", {"cu_outcomes": {"stable_cu": "supported"}}) == "✓"
    assert _ci_summary._delta_symbol("better_cu", "supported", {"cu_outcomes": {"better_cu": "partial"}}) == "↑"
    assert _ci_summary._delta_symbol("worse_cu", "blocked", {"cu_outcomes": {"worse_cu": "supported"}}) == "↓"


def test_severity_mapping():
    active = {"in_profile"}

    assert _ci_summary._severity_for("cu", "action_needed", active) == ("Critical", "🔴")
    assert _ci_summary._severity_for("cu", "blocked", active) == ("Major", "🟠")
    assert _ci_summary._severity_for("in_profile", "not_supported", active) == ("Minor", "🟡")
    assert _ci_summary._severity_for("outside_profile", "not_supported", active) == ("Info", "ℹ️")
    assert _ci_summary._severity_for("cu", "partial", active) == ("Info", "ℹ️")


def test_ci_summary_renders_audience_sections(monkeypatch):
    _patch_ci_metadata(monkeypatch)
    payload = _sample_payload()

    lines, context = _ci_summary._render_profile_facet_summary(payload, baseline=None)
    rendered = "\n".join(lines)

    assert context is not None
    assert context["score"] == 90
    assert "### Δ Since Last Run" in rendered
    assert "_No baseline yet — this run becomes the baseline._" in rendered
    assert "## What this server supports" in rendered
    assert "## Top Findings" in rendered
    assert "<summary><b>Coverage Overview</b></summary>" in rendered
    assert "<summary><b>Facet Coverage</b></summary>" in rendered
    assert "<summary><b>Conformance Findings</b></summary>" in rendered
    assert "<summary><b>Full CU coverage</b></summary>" in rendered
    assert "<summary><b>Test environment</b></summary>" in rendered
    assert "<summary><b>How to read this report</b></summary>" in rendered
    assert "Purpose" in rendered
    assert "Reference IJT facet" in rendered
    assert "Server Supported CUs" in rendered
    assert "Server Support %" in rendered
    assert "Supported CUs Validated %" in rendered
    assert "Result" in rendered
    for legacy_term in (
        "Dec" + "lared",
        "dec" + "lared",
        "Run " + "Status",
        "Run " + "Overview",
        "Validation " + "Status",
    ):
        assert legacy_term not in rendered
    assert "Primary Reason" in rendered
    assert "OptionalFeature: Not Supported" in rendered
    assert "🟡 Minor" in rendered
    assert (
        "| Full Conformance | Server capability profile | 1 | 3 | 2 | 66.7% | 100.0% | "
        "2 Supported<br>0 With notes<br>1 Not supported<br>0 Blocked<br>0 Action needed | "
        "🟩 Supported with notes |" in rendered
    )
    assert (
        "| IJT Joining System Base | Basic Facet, Basic Joining System Server Facet "
        "| Yes | 🟢 Supported | 2 | 2 | 0 | 0 | 0 | 3 |"
    ) in rendered
    assert "| IJT State Policy Note | Basic Facet | Yes | 🟢 Supported | 2 | 1 | 0 | 0 | 0 | 1 |" in rendered
    assert "| IJT Optional Feature | Basic Facet | No | 🟡 Not Supported | 1 | 0 | 1 | 0 | 0 | 2 |" in rendered
    assert "Accepted Policy: ACCEPTED POLICY - Method: SelectJoiningProcess - state not ready" not in rendered


def test_top_findings_sort_order(monkeypatch):
    _patch_ci_metadata(monkeypatch)
    payload = _sample_payload()
    payload["by_cu"]["joining_system_base"] = {"failed": 1, "test_count": 1}
    payload["by_cu"]["state_policy_note"] = {"blocked": 1, "test_count": 1}

    _lines, context = _ci_summary._render_profile_facet_summary(payload, baseline=None)

    assert [finding["severity"] for finding in context["findings"][:3]] == ["Critical", "Major", "Minor"]


def test_delta_block_present_when_baseline_exists(monkeypatch):
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

    lines, _context = _ci_summary._render_profile_facet_summary(_sample_payload(), baseline=baseline)
    rendered = "\n".join(lines)

    assert "### Δ Since Last Run (commit `abc123e`" in rendered
    assert "Score **80 → 90**" in rendered
    assert "1 resolved" in rendered
    assert "1 regressed" in rendered


def test_baseline_written_after_render():
    baseline_path = _ROOT / "test-results" / "report-baseline-unit-test.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    context = {
        "score": 94,
        "validation_health_value": 100.0,
        "spec_coverage_value": 79.7,
        "findings_count": {"critical": 0, "major": 0, "minor": 25, "info": 3},
        "cu_outcomes": {"joining_system_base": "supported"},
    }

    try:
        _ci_summary._write_baseline(baseline_path, _ci_summary._baseline_payload(context, "2026-05-10T15:46:00Z"))

        written = json.loads(baseline_path.read_text(encoding="utf-8"))
        assert written["score"] == 94
        assert written["validation_health_pct"] == 100.0
        assert written["spec_coverage_pct"] == 79.7
        assert written["cu_outcomes"] == {"joining_system_base": "supported"}
    finally:
        baseline_path.unlink(missing_ok=True)


def test_excel_cover_sheet_exists_and_first():
    profiles, facets, capabilities = _excel_metadata()
    payload = _sample_payload()
    context = _excel_report._build_report_context(payload, profiles, facets, capabilities, baseline=None)
    wb = _excel_report.openpyxl.Workbook()
    wb.remove(wb.active)

    _excel_report._build_cover(wb, [], "2026-05-10 15:46:00", "passed", context, None, facets)

    assert wb.sheetnames[0] == "Cover"
    assert wb["Cover"]["A1"].value == "PASSED - Score 90 / 100"


def test_excel_cu_severity_and_delta_columns_present():
    profiles, facets, capabilities = _excel_metadata()
    payload = _sample_payload()
    baseline = {"cu_outcomes": {"optional_feature": "supported"}}
    context = _excel_report._build_report_context(payload, profiles, facets, capabilities, baseline=baseline)
    wb = _excel_report.openpyxl.Workbook()
    wb.remove(wb.active)

    _excel_report._build_cu_coverage(wb, payload, facets, capabilities, context, baseline)
    ws = wb["CU Coverage"]

    assert ws["A1"].value == "Severity"
    assert ws["B1"].value == "Δ"
    assert ws["A4"].value == "🟡 Minor"
    assert ws["B4"].value == "↓"
