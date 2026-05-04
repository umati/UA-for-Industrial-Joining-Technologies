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


def test_report_evidence_key_marks_mixed_pass_and_blocked_as_partial():
    data = {"passed": 2, "blocked": 1, "not_supported": 0, "failed": 0, "error": 0, "test_count": 3}

    assert _ci_summary._cu_evidence_key(data) == "partial"
    assert _excel_report._cu_evidence_label(_excel_report._cu_evidence_key(data)) == "Partial"


def test_ci_summary_renders_profile_facet_and_full_cu_tables(monkeypatch):
    monkeypatch.setattr(
        _ci_summary,
        "_load_facets",
        lambda: {
            "basic_facet": {
                "display_name": "Basic Facet",
                "conformance_units": ["joining_system_base", "optional_feature"],
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
        "supported_cus": ["joining_system_base"],
        "by_cu": {
            "joining_system_base": {
                "passed": 2,
                "test_count": 2,
                "workbook_case_count": 3,
            },
            "optional_feature": {
                "not_supported": 1,
                "test_count": 1,
                "workbook_case_count": 2,
            },
        },
    }

    rendered = "\n".join(_ci_summary._render_profile_facet_summary(payload))

    assert "### Profiles" in rendered
    assert "### Facets" in rendered
    assert "### CUs Requiring Attention" in rendered
    assert "<summary>Full CU coverage table</summary>" in rendered
    assert "Report Test Server" in rendered
    assert "| IJT Joining System Base | Basic Facet | Yes | 🟢 Supported | 2 | 2 | 0 | 0 | 0 | 3 |" in rendered
    assert "| IJT Optional Feature | Basic Facet | No | 🟡 Not Supported | 1 | 0 | 1 | 0 | 0 | 2 |" in rendered
