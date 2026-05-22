"""Unit tests for ci_run_summary.py helper functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reporting import ci_run_summary


@pytest.fixture
def tmp_xml_dir(tmp_path):
    """Create temporary directory for XML test files."""
    return tmp_path / "xml-artifacts"


def test_iter_suites_bare_testsuite():
    """iter_suites returns single testsuite when root is testsuite."""
    import xml.etree.ElementTree as ET

    root = ET.Element("testsuite", {"tests": "10"})
    result = ci_run_summary.iter_suites(root)
    assert result == [root]


def test_iter_suites_nested_testsuites():
    """iter_suites finds all nested testsuite elements."""
    import xml.etree.ElementTree as ET

    root = ET.Element("testsuites")
    suite1 = ET.SubElement(root, "testsuite", {"tests": "5"})
    suite2 = ET.SubElement(root, "testsuite", {"tests": "3"})
    result = ci_run_summary.iter_suites(root)
    assert len(result) == 2
    assert suite1 in result
    assert suite2 in result


def test_parse_junit_success(tmp_path):
    """parse_junit extracts test counts from valid JUnit XML."""
    xml = tmp_path / "junit.xml"
    xml.write_text("""<?xml version="1.0"?>
<testsuites>
  <testsuite tests="10" failures="2" errors="1" skipped="3"/>
</testsuites>
""")
    total, passed, failed, skipped = ci_run_summary.parse_junit(str(xml))
    assert total == 10
    assert passed == 4  # 10 - 3 (failures+errors) - 3 (skipped)
    assert failed == 3  # 2 failures + 1 error
    assert skipped == 3


def test_parse_junit_no_match_returns_nones(tmp_path):
    """parse_junit returns all None when pattern matches no files."""
    total, passed, failed, skipped = ci_run_summary.parse_junit(str(tmp_path / "nonexistent-*.xml"))
    assert total is None
    assert passed is None
    assert failed is None
    assert skipped is None


def test_parse_junit_invalid_xml_returns_nones_with_warning(tmp_path, capsys):
    """parse_junit returns None and prints warning for invalid XML."""
    xml = tmp_path / "bad.xml"
    xml.write_text("not xml at all")
    total, passed, failed, skipped = ci_run_summary.parse_junit(str(xml))
    assert total is None
    captured = capsys.readouterr()
    assert "[WARN] parse_junit" in captured.out


def test_collect_skips_extracts_skipped_tests(tmp_path):
    """collect_skips returns list of (name, reason) tuples."""
    xml = tmp_path / "junit.xml"
    xml.write_text("""<?xml version="1.0"?>
<testsuite>
  <testcase name="test_one">
    <skipped message="Not implemented"/>
  </testcase>
  <testcase name="test_two">
    <skipped>No server available</skipped>
  </testcase>
  <testcase name="test_passing"/>
</testsuite>
""")
    skips = ci_run_summary.collect_skips(str(xml))
    assert len(skips) == 2
    assert ("test_one", "Not implemented") in skips
    assert ("test_two", "No server available") in skips


def test_collect_skips_handles_no_reason(tmp_path):
    """collect_skips uses default message when no reason given."""
    xml = tmp_path / "junit.xml"
    xml.write_text("""<?xml version="1.0"?>
<testsuite>
  <testcase name="test_skip">
    <skipped/>
  </testcase>
</testsuite>
""")
    skips = ci_run_summary.collect_skips(str(xml))
    assert skips == [("test_skip", "no reason given")]


def test_collect_skips_truncates_long_messages(tmp_path):
    """collect_skips truncates messages longer than 200 chars."""
    xml = tmp_path / "junit.xml"
    long_msg = "x" * 300
    xml.write_text(f"""<?xml version="1.0"?>
<testsuite>
  <testcase name="test_long">
    <skipped message="{long_msg}"/>
  </testcase>
</testsuite>
""")
    skips = ci_run_summary.collect_skips(str(xml))
    assert len(skips[0][1]) == 200


def test_collect_skips_takes_first_line_of_multiline_message(tmp_path):
    """collect_skips takes only first line of multi-line messages."""
    xml = tmp_path / "junit.xml"
    xml.write_text("""<?xml version="1.0"?>
<testsuite>
  <testcase name="test_multiline">
    <skipped message="First line&#10;Second line&#10;Third line"/>
  </testcase>
</testsuite>
""")
    skips = ci_run_summary.collect_skips(str(xml))
    assert skips[0][1] == "First line"


def test_md_cell_escapes_pipe():
    """md_cell escapes pipe characters for markdown tables."""
    assert ci_run_summary.md_cell("a|b") == "a\\|b"


def test_md_cell_escapes_angle_brackets():
    """md_cell escapes < and > to HTML entities."""
    assert ci_run_summary.md_cell("<script>") == "&lt;script&gt;"


def test_md_cell_replaces_newlines_with_space():
    """md_cell replaces newlines and carriage returns with spaces."""
    assert ci_run_summary.md_cell("line1\nline2\rline3") == "line1 line2 line3"


def test_md_cell_handles_none():
    """md_cell converts None to empty string."""
    assert ci_run_summary.md_cell(None) == ""


def test_format_skip_section_empty_no_skips():
    """format_skip_section returns empty list when no skips."""
    result = ci_run_summary.format_skip_section("Test", [], 0)
    assert result == []


def test_format_skip_section_with_skips():
    """format_skip_section generates collapsible markdown section."""
    skips = [
        ("test1", "Not implemented"),
        ("test2", "Not implemented"),
        ("test3", "No server"),
    ]
    result = ci_run_summary.format_skip_section("Component", skips, 3)
    assert len(result) > 0
    assert any("Component" in line for line in result)
    assert any("3 skipped" in line for line in result)
    assert any("Not implemented" in line for line in result)
    assert any("<details>" in line for line in result)


def test_format_skip_section_skip_count_mismatch():
    """format_skip_section handles mismatch between skip_count and list length."""
    skips = [("test1", "reason1")]
    result = ci_run_summary.format_skip_section("Test", skips, 5)
    assert any("Skip details unavailable in JUnit XML" in line for line in result)


def test_parse_coverage_no_match_returns_none(tmp_path):
    """parse_coverage returns None when no coverage file found."""
    result = ci_run_summary.parse_coverage(str(tmp_path / "nonexistent.xml"))
    assert result is None


def test_parse_coverage_extracts_line_rate(tmp_path):
    """parse_coverage extracts and converts line-rate to percentage."""
    xml = tmp_path / "coverage.xml"
    xml.write_text("""<?xml version="1.0"?>
<coverage line-rate="0.856"/>
""")
    result = ci_run_summary.parse_coverage(str(xml))
    assert result == pytest.approx(85.6, abs=0.1)


def test_parse_bandit_no_match_returns_none_none(tmp_path):
    """parse_bandit returns (None, None) when no file found."""
    high, medium = ci_run_summary.parse_bandit(str(tmp_path / "nonexistent.json"))
    assert high is None
    assert medium is None


def test_parse_bandit_counts_severity(tmp_path):
    """parse_bandit counts high and medium severity issues."""
    json_file = tmp_path / "bandit.json"
    json_file.write_text(
        json.dumps(
            {
                "results": [
                    {"issue_severity": "HIGH"},
                    {"issue_severity": "HIGH"},
                    {"issue_severity": "MEDIUM"},
                    {"issue_severity": "LOW"},
                ]
            }
        )
    )
    high, medium = ci_run_summary.parse_bandit(str(json_file))
    assert high == 2
    assert medium == 1


def test_parse_npm_audit_no_match_returns_none_none(tmp_path):
    """parse_npm_audit returns (None, None) when no file found."""
    crit, high = ci_run_summary.parse_npm_audit(str(tmp_path / "nonexistent.json"))
    assert crit is None
    assert high is None


def test_parse_npm_audit_extracts_vulnerabilities(tmp_path):
    """parse_npm_audit extracts critical and high vulnerability counts."""
    json_file = tmp_path / "npm-audit.json"
    json_file.write_text(
        json.dumps(
            {
                "metadata": {
                    "vulnerabilities": {
                        "critical": 3,
                        "high": 5,
                        "moderate": 10,
                    }
                }
            }
        )
    )
    crit, high = ci_run_summary.parse_npm_audit(str(json_file))
    assert crit == 3
    assert high == 5


def test_parse_eslint_no_match_returns_none_none(tmp_path):
    """parse_eslint returns (None, None) when no file found."""
    errors, warnings = ci_run_summary.parse_eslint(str(tmp_path / "nonexistent.json"))
    assert errors is None
    assert warnings is None


def test_parse_eslint_counts_errors_and_warnings(tmp_path):
    """parse_eslint sums errorCount and warningCount across results."""
    json_file = tmp_path / "eslint.json"
    json_file.write_text(
        json.dumps(
            [
                {"errorCount": 2, "warningCount": 5},
                {"errorCount": 1, "warningCount": 3},
            ]
        )
    )
    errors, warnings = ci_run_summary.parse_eslint(str(json_file))
    assert errors == 3
    assert warnings == 8


def test_job_icon_known_results():
    """job_icon returns correct emoji for known results."""
    assert ci_run_summary.job_icon("success") == "✅"
    assert ci_run_summary.job_icon("failure") == "❌"
    assert ci_run_summary.job_icon("cancelled") == "🚫"
    assert ci_run_summary.job_icon("skipped") == "⏭️"


def test_job_icon_unknown_result():
    """job_icon returns warning icon for unknown results."""
    assert ci_run_summary.job_icon("unknown") == "⚠️"
    assert ci_run_summary.job_icon("anything") == "⚠️"


def test_tests_formatter_none_returns_not_reported():
    """tests formatter explains missing test-count data."""
    assert ci_run_summary.tests(None, None, None) == "Not reported"
    assert ci_run_summary.tests(None, None, None, job_result="skipped") == "Not run"


def test_tests_formatter_no_failures():
    """tests formatter returns checkmark and total when no failures."""
    assert ci_run_summary.tests(100, 100, 0) == "100 passed ✅"


def test_tests_formatter_with_failures():
    """tests formatter shows passed/total with X when failures exist."""
    assert ci_run_summary.tests(100, 90, 10) == "90 / 100 passed ❌"


def test_tests_formatter_includes_thousands_separator():
    """tests formatter includes comma separators for large numbers."""
    assert ci_run_summary.tests(1000, 1000, 0) == "1,000 passed ✅"


def test_skips_formatter_none_returns_not_reported():
    """skips formatter explains missing skip data."""
    assert ci_run_summary.skips(None) == "Not reported"
    assert ci_run_summary.skips(None, "skipped") == "Not run"


def test_skips_formatter_converts_to_string():
    """skips formatter labels the count for readable copied tables."""
    assert ci_run_summary.skips(5) == "5 skipped"
    assert ci_run_summary.skips(0) == "0 skipped"


def test_cov_formatter_none_returns_not_reported():
    """cov formatter explains missing coverage data."""
    assert ci_run_summary.cov(None) == "Not reported"
    assert ci_run_summary.cov(None, job_result="skipped") == "Not run"


def test_cov_formatter_no_threshold_uses_defaults():
    """cov formatter uses default thresholds when none provided."""
    assert "✅" in ci_run_summary.cov(95.0)
    assert "⚠️" in ci_run_summary.cov(85.0)
    assert "❌" in ci_run_summary.cov(65.0)


def test_module_bootstrap_runs_main_via_runpy(tmp_path, monkeypatch):
    """The ``if __name__ == "__main__":`` bootstrap is exercised end-to-end.

    Runs the module as a script via ``runpy.run_path`` so the bootstrap
    branch (which previously carried ``# pragma: no cover``) is now covered
    by a real test. The module's ``main()`` reads env vars with defaults
    and globs CI artifacts, so an empty working directory plus a temp
    ``GITHUB_STEP_SUMMARY`` is enough to exercise the path without side
    effects.
    """
    import runpy

    summary_file = tmp_path / "step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
    monkeypatch.chdir(tmp_path)
    module_path = Path(ci_run_summary.__file__)

    runpy.run_path(str(module_path), run_name="__main__")

    # The bootstrap must have invoked main() which writes at least one line.
    assert summary_file.exists()
    assert summary_file.stat().st_size > 0


def test_cov_formatter_with_threshold():
    """cov formatter compares against provided threshold."""
    result = ci_run_summary.cov(92.0, 95.0)
    assert "92.0% / 95%" in result
    assert "⚠️" in result


def test_cov_formatter_meets_threshold():
    """cov formatter shows checkmark when meeting threshold."""
    result = ci_run_summary.cov(95.5, 95.0)
    assert "95.5% / 95%" in result
    assert "✅" in result


def test_tool_formatter_empty_returns_not_reported():
    """tool formatter explains empty, unknown, and skipped results."""
    assert ci_run_summary.tool("", "mypy") == "mypy (not reported) ⏭️"
    assert ci_run_summary.tool("unknown", "ruff") == "ruff (not reported) ⏭️"
    assert ci_run_summary.tool("", "ruff", "skipped") == "ruff (not run) ⏭️"


def test_tool_formatter_known_result():
    """tool formatter returns label with icon for known result."""
    assert "mypy" in ci_run_summary.tool("success", "mypy")
    assert "✅" in ci_run_summary.tool("success", "mypy")
    assert "❌" in ci_run_summary.tool("failure", "ruff")


def test_bandit_fmt_no_issues():
    """bandit_fmt returns success message when no issues."""
    assert ci_run_summary.bandit_fmt(0, 0) == "bandit (0 issues) ✅"


def test_bandit_fmt_with_issues():
    """bandit_fmt returns failure message with counts."""
    result = ci_run_summary.bandit_fmt(3, 5)
    assert "❌" in result
    assert "3 high" in result
    assert "5 medium" in result


def test_bandit_fmt_none_returns_not_reported():
    """bandit_fmt explains missing artifacts without implying scan failure."""
    assert ci_run_summary.bandit_fmt(None, None) == "bandit (not reported) ⏭️"


def test_bandit_fmt_skipped_lane_is_explicit():
    """bandit_fmt distinguishes skipped lanes from missing artifacts."""
    assert ci_run_summary.bandit_fmt(None, None, "skipped") == "bandit (not run) ⏭️"


def test_npm_fmt_none_returns_not_reported():
    """npm_fmt explains missing artifacts without implying audit failure."""
    assert ci_run_summary.npm_fmt(None, None) == "npm-audit (not reported) ⏭️"


def test_npm_fmt_skipped_lane_is_explicit():
    """npm_fmt distinguishes skipped lanes from missing artifacts."""
    assert ci_run_summary.npm_fmt(None, None, "skipped") == "npm-audit (not run) ⏭️"


def test_npm_fmt_no_issues():
    """npm_fmt returns success message when no issues."""
    assert ci_run_summary.npm_fmt(0, 0) == "npm-audit (0 critical) ✅"


def test_npm_fmt_with_issues():
    """npm_fmt returns failure message with counts."""
    result = ci_run_summary.npm_fmt(2, 4)
    assert "❌" in result
    assert "2 critical" in result
    assert "4 high" in result


def test_parse_pip_audit_counts_fixable_and_advisory(tmp_path):
    """parse_pip_audit uses pip-audit's dependencies[].vulns[] JSON shape."""
    report = tmp_path / "pip-audit.json"
    report.write_text(
        json.dumps(
            {
                "dependencies": [
                    {
                        "name": "pkg-a",
                        "vulns": [
                            {"id": "CVE-1", "fix_versions": ["1.2.3"]},
                            {"id": "CVE-2", "fix_versions": []},
                        ],
                    },
                    {"name": "pkg-b", "vulns": []},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert ci_run_summary.parse_pip_audit(str(report)) == (2, 1, True)


def test_pip_audit_fmt_states():
    assert ci_run_summary.pip_audit_fmt(0, 0, True) == "pip-audit (0 CVEs) ✅"
    assert ci_run_summary.pip_audit_fmt(2, 1, True) == "pip-audit (1 fixable CVE) ❌"
    assert ci_run_summary.pip_audit_fmt(2, 0, True) == "pip-audit (2 advisory CVEs) ⚠️"
    assert ci_run_summary.pip_audit_fmt(None, None, False) == "pip-audit (not reported) ⏭️"
    assert ci_run_summary.pip_audit_fmt(None, None, False, "skipped") == "pip-audit (not run) ⏭️"


def test_nuget_fmt_uses_countless_failure():
    assert ci_run_summary.nuget_fmt("success") == "nuget (0 vulnerable) ✅"
    assert ci_run_summary.nuget_fmt("failure") == "nuget (vulnerable packages detected) ❌"
    assert ci_run_summary.nuget_fmt("skipped") == "nuget (not run) ⏭️"


def test_eslint_fmt_none_uses_step_result():
    """eslint_fmt falls back to tool formatter when errors is None."""
    result = ci_run_summary.eslint_fmt("success", (None, None))
    assert "eslint ✅" in result


def test_eslint_fmt_no_issues():
    """eslint_fmt returns success when no errors or warnings."""
    assert ci_run_summary.eslint_fmt("success", (0, 0)) == "eslint ✅"


def test_eslint_fmt_only_warnings():
    """eslint_fmt returns warning indicator when only warnings."""
    result = ci_run_summary.eslint_fmt("success", (0, 5))
    assert "⚠️" in result
    assert "5 warnings" in result


def test_eslint_fmt_with_errors():
    """eslint_fmt returns error indicator when errors present."""
    result = ci_run_summary.eslint_fmt("success", (3, 5))
    assert "❌" in result
    assert "3 errors" in result
    assert "5 warnings" in result


def test_lint_joins_items():
    """lint joins non-dash items with separator."""
    result = ci_run_summary.lint("ruff ✅", "mypy ✅")
    assert result == "ruff ✅ · mypy ✅"


def test_lint_filters_legacy_dashes():
    """lint still filters legacy dash entries."""
    result = ci_run_summary.lint("ruff ✅", "—", "mypy ✅")
    assert result == "ruff ✅ · mypy ✅"


def test_lint_all_dashes_returns_not_reported():
    """lint does not emit dash-only report cells."""
    assert ci_run_summary.lint("—", "—") == "Not reported"


def test_lint_no_items_returns_not_reported():
    """lint does not emit dash-only report cells."""
    assert ci_run_summary.lint() == "Not reported"


def test_timing_status_fmt_success():
    assert ci_run_summary.timing_status_fmt("success") == "success ✅"


def test_timing_status_fmt_failure():
    assert ci_run_summary.timing_status_fmt("failure") == "failure ❌"


def test_timing_status_fmt_skipped():
    assert ci_run_summary.timing_status_fmt("skipped") == "skipped ⏭️"


def test_timing_status_fmt_unknown():
    assert "⚠️" in ci_run_summary.timing_status_fmt("bogus")
