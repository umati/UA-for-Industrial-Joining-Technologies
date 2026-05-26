"""Contracts for public display names and stable summary links."""

from __future__ import annotations

import re
from pathlib import Path

REPORTING_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "expected"

EXPECTED_CONFORMANCE = (
    Path(__file__).resolve().parents[2]
    / "OPC_UA_Clients"
    / "Release2"
    / "IJT_Test_Client"
    / "tests"
    / "unit"
    / "reporting"
    / "fixtures"
    / "expected"
    / "system_tests_full_conformance.md"
)


def _section(markdown: str, heading: str) -> str:
    start = markdown.index(heading)
    remainder = markdown[start + len(heading) :]
    next_heading = remainder.find("\n## ")
    return remainder if next_heading == -1 else remainder[:next_heading]


def test_primary_cu_columns_use_public_display_names() -> None:
    rendered = EXPECTED_CONFORMANCE.read_text(encoding="utf-8")
    primary_sections = _section(rendered, "## 📋 CUs Needing Review")

    assert "`acknowledge_results`" not in primary_sections
    assert "| ⚪&nbsp;Not Supported | IJT Acknowledge Results |" in primary_sections


def test_quick_index_links_have_explicit_targets() -> None:
    for snapshot_name in ("ci_summary.md", "integration_summary.md"):
        rendered = (REPORTING_FIXTURES / snapshot_name).read_text(encoding="utf-8")
        for anchor in re.findall(r"\]\(#([a-z0-9-]+)\)", rendered):
            assert f'<a id="{anchor}"></a>' in rendered
