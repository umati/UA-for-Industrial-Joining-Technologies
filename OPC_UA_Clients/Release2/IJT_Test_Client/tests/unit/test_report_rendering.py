from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).parents[2]
_SCRIPTS = _ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS))

_ci_summary: Any = importlib.import_module("make_ci_summary")
_excel_report: Any = importlib.import_module("make_excel_report")


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


def test_ci_summary_renders_profile_facet_and_full_cu_tables(monkeypatch):
    monkeypatch.setattr(
        _ci_summary,
        "_load_facets",
        lambda: {
            "basic_facet": {
                "display_name": "Basic Facet",
                "conformance_units": ["joining_system_base", "state_policy_note", "optional_feature"],
            }
        },
    )
    monkeypatch.setattr(
        _ci_summary,
        "_load_profiles",
        lambda: {
            "full_conformance": {
                "name": "Full Conformance",
                "facets": ["basic_facet"],
            }
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
    payload = {
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

    rendered = "\n".join(_ci_summary._render_profile_facet_summary(payload))

    assert "### Profiles" in rendered
    assert "### Facets" in rendered
    assert "### CUs With Notes / Not Supported" in rendered
    assert "Profile View" in rendered
    assert "CUs in Tested Profile" in rendered
    assert "In Tested Profile" in rendered
    assert "Reason Shown" in rendered
    assert "OptionalFeature: Not Supported" in rendered
    assert "<summary>Full CU coverage table</summary>" in rendered
    assert "Report Test Server" in rendered
    assert "| IJT Joining System Base | Basic Facet | Yes | 🟢 Supported | 2 | 2 | 0 | 0 | 0 | 3 |" in rendered
    assert "| IJT State Policy Note | Basic Facet | Yes | 🟢 Supported | 2 | 1 | 0 | 0 | 0 | 1 |" in rendered
    assert "| IJT Optional Feature | Basic Facet | No | 🟡 Not Supported | 1 | 0 | 1 | 0 | 0 | 2 |" in rendered
    assert "Accepted Policy: ACCEPTED POLICY - Method: SelectJoiningProcess - state not ready" not in rendered
