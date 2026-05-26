"""Unit tests for system_tests_run_summary.py helper functions."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from reporting import system_tests_run_summary


def test_iter_suites_bare_testsuite():
    """iter_suites returns single testsuite when root is testsuite."""
    import xml.etree.ElementTree as ET

    root = ET.Element("testsuite", {"tests": "10"})
    result = system_tests_run_summary.iter_suites(root)
    assert result == [root]


def test_iter_suites_nested_testsuites():
    """iter_suites finds all nested testsuite elements."""
    import xml.etree.ElementTree as ET

    root = ET.Element("testsuites")
    suite1 = ET.SubElement(root, "testsuite", {"tests": "5"})
    suite2 = ET.SubElement(root, "testsuite", {"tests": "3"})
    result = system_tests_run_summary.iter_suites(root)
    assert len(result) == 2
    assert suite1 in result
    assert suite2 in result


def test_parse_junit_success_aggregates_multiple_files(tmp_path):
    """parse_junit aggregates counts across multiple matching files."""
    xml1 = tmp_path / "junit1.xml"
    xml1.write_text("""<?xml version="1.0"?>
<testsuite tests="10" failures="2" errors="0" skipped="1"/>
""")
    xml2 = tmp_path / "junit2.xml"
    xml2.write_text("""<?xml version="1.0"?>
<testsuite tests="5" failures="1" errors="0" skipped="0"/>
""")
    total, passed, failed, skipped = system_tests_run_summary.parse_junit(
        str(tmp_path / "junit*.xml")
    )
    assert total == 15
    assert passed == 11  # (10-2-1) + (5-1-0)
    assert failed == 3  # 2 + 1
    assert skipped == 1


def test_parse_junit_handles_errors_as_failures(tmp_path):
    """parse_junit treats errors as failures."""
    xml = tmp_path / "junit.xml"
    xml.write_text("""<?xml version="1.0"?>
<testsuite tests="10" failures="2" errors="3" skipped="0"/>
""")
    total, passed, failed, skipped = system_tests_run_summary.parse_junit(str(xml))
    assert failed == 5  # 2 failures + 3 errors


def test_parse_junit_no_match_returns_nones(tmp_path):
    """parse_junit returns all None when pattern matches no files."""
    total, passed, failed, skipped = system_tests_run_summary.parse_junit(
        str(tmp_path / "nonexistent-*.xml")
    )
    assert total is None
    assert passed is None
    assert failed is None
    assert skipped is None


def test_collect_skips_aggregates_from_multiple_files(tmp_path):
    """collect_skips aggregates skips across multiple files."""
    xml1 = tmp_path / "junit1.xml"
    xml1.write_text("""<?xml version="1.0"?>
<testsuite>
  <testcase name="test1"><skipped message="reason1"/></testcase>
</testsuite>
""")
    xml2 = tmp_path / "junit2.xml"
    xml2.write_text("""<?xml version="1.0"?>
<testsuite>
  <testcase name="test2"><skipped message="reason2"/></testcase>
</testsuite>
""")
    skips = system_tests_run_summary.collect_skips(str(tmp_path / "junit*.xml"))
    assert len(skips) == 2
    assert ("test1", "reason1") in skips
    assert ("test2", "reason2") in skips


def test_md_cell_escapes_pipe():
    """md_cell escapes pipe characters."""
    assert system_tests_run_summary.md_cell("a|b") == "a\\|b"


def test_md_cell_escapes_angle_brackets():
    """md_cell escapes angle brackets."""
    assert system_tests_run_summary.md_cell("<tag>") == "&lt;tag&gt;"


def test_md_cell_replaces_newlines():
    """md_cell replaces newlines with spaces."""
    assert system_tests_run_summary.md_cell("line1\nline2\rline3") == "line1 line2 line3"


def test_shift_markdown_headings_embeds_standalone_report():
    """shift_markdown_headings lowers standalone summary headings by one level."""
    markdown = "# Report\n\n## Section\n\n###### Deep"

    assert (
        system_tests_run_summary.shift_markdown_headings(markdown)
        == "## Report\n\n### Section\n\n###### Deep"
    )


def test_shift_markdown_headings_basic_two_level_promotion():
    """Spec example: `# A` -> `## A`, `## B` -> `### B`."""
    assert system_tests_run_summary.shift_markdown_headings("# A\n## B\n", by=1) == "## A\n### B\n"


def test_shift_markdown_headings_leaves_fenced_code_blocks_untouched():
    """Headings inside fenced code blocks must not be shifted."""
    markdown = "# Title\n\n```\n# not-a-heading\n## also-not\n```\n\n## Real Section\n"
    shifted = system_tests_run_summary.shift_markdown_headings(markdown, by=1)
    assert "# not-a-heading" in shifted
    assert "## also-not" in shifted
    assert "## Title" in shifted
    assert "### Real Section" in shifted


def test_load_test_client_conformance_summary_shifts_artifact_headings(tmp_path):
    """load_test_client_conformance_summary embeds the artifact with shifted headings."""
    summary = tmp_path / "summary.md"
    summary.write_text("# IJT Conformance Test Report\n\n## Scope\n", encoding="utf-8")

    assert system_tests_run_summary.load_test_client_conformance_summary(str(summary)) == [
        "## IJT Conformance Test Report",
        "",
        "### Scope",
    ]


def test_tc_conformance_artifact_warning_success_with_content_no_warning():
    """When the lane succeeded and summary.md has content, no warning is emitted."""
    assert (
        system_tests_run_summary.tc_conformance_artifact_warning(
            "success", ["## IJT Conformance Test Report", ""], "path/summary.md"
        )
        is None
    )


def test_tc_conformance_artifact_warning_success_missing_emits_warning():
    """When the lane succeeded but summary.md is missing (empty list), a warning is emitted."""
    warning = system_tests_run_summary.tc_conformance_artifact_warning(
        "success", [], "all-results/results-testclient/summary.md"
    )
    assert warning is not None
    assert "Test Client conformance summary" in warning
    assert "all-results/results-testclient/summary.md" in warning


def test_tc_conformance_artifact_warning_success_empty_file_emits_warning(tmp_path):
    """An empty summary.md round-trips through load_* to an empty list and triggers the warning."""
    summary = tmp_path / "summary.md"
    summary.write_text("", encoding="utf-8")
    lines = system_tests_run_summary.load_test_client_conformance_summary(str(summary))
    assert lines == []
    warning = system_tests_run_summary.tc_conformance_artifact_warning(
        "success", lines, str(summary)
    )
    assert warning is not None
    assert "missing or empty" in warning


def test_tc_conformance_artifact_warning_failure_no_warning():
    """When the lane failed, the failure itself is the signal — no artifact warning."""
    assert (
        system_tests_run_summary.tc_conformance_artifact_warning("failure", [], "path/summary.md")
        is None
    )


def test_format_skip_section_empty_returns_empty():
    """format_skip_section returns empty list when no skips."""
    result = system_tests_run_summary.format_skip_section("Test", [], 0)
    assert result == []


def test_format_skip_section_generates_details_section(tmp_path):
    """format_skip_section generates collapsible details section."""
    skips = [
        ("test1", "Not implemented"),
        ("test2", "Not implemented"),
        ("test3", "No server"),
    ]
    result = system_tests_run_summary.format_skip_section("Component", skips, 3)
    assert any("Component" in line for line in result)
    assert any("3 Skipped" in line for line in result)
    assert any("<details>" in line for line in result)


def test_skip_note_inline_single_reason():
    """skip_note_inline returns truncated reason when single reason."""
    skips = [("test1", "This is the reason"), ("test2", "This is the reason")]
    result = system_tests_run_summary.skip_note_inline(skips)
    assert "This is the reason" in result


def test_skip_note_inline_multiple_reasons():
    """skip_note_inline returns count message for multiple reasons."""
    skips = [("test1", "reason1"), ("test2", "reason2")]
    result = system_tests_run_summary.skip_note_inline(skips)
    assert "2 skip reasons" in result


def test_skip_note_inline_empty_with_count():
    """skip_note_inline returns unavailable message when count but no details."""
    result = system_tests_run_summary.skip_note_inline([], 5)
    assert "Skip details unavailable" in result


def test_skip_note_inline_empty_returns_default():
    """skip_note_inline returns default when no skips."""
    result = system_tests_run_summary.skip_note_inline([], None, "custom default")
    assert result == "custom default"


def test_load_integration_baseline_success(tmp_path):
    """load_integration_baseline loads valid baseline file."""
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "suites": {
                    "sd_smoke": {"tests": 10, "skipped": 0},
                    "tc_tests": {"tests": 100, "skipped": 5},
                },
                "skip_tolerance_default": 2,
            }
        )
    )
    baseline, error = system_tests_run_summary.load_integration_baseline(str(baseline_file))
    assert error is None
    assert baseline["suites"]["sd_smoke"]["tests"] == 10
    assert baseline["skip_tolerance_default"] == 2


def test_load_integration_baseline_missing_file():
    """load_integration_baseline returns error message for missing file."""
    baseline, error = system_tests_run_summary.load_integration_baseline("nonexistent.json")
    assert error is not None
    assert "Integration baseline unavailable" in error


def test_load_integration_baseline_invalid_schema(tmp_path):
    """load_integration_baseline rejects invalid schema version."""
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(json.dumps({"schema_version": 99, "suites": {}}))
    baseline, error = system_tests_run_summary.load_integration_baseline(str(baseline_file))
    assert error is not None
    assert "baseline unavailable" in error


def test_baseline_suite_returns_entry_when_exists():
    """baseline_suite returns the suite entry when it exists."""
    baseline = {"suites": {"tc_tests": {"tests": 100}}}
    result = system_tests_run_summary.baseline_suite(baseline, "tc_tests")
    assert result == {"tests": 100}


def test_baseline_suite_returns_none_when_missing():
    """baseline_suite returns None when suite key doesn't exist."""
    baseline = {"suites": {}}
    result = system_tests_run_summary.baseline_suite(baseline, "nonexistent")
    assert result is None


def test_baseline_suite_returns_none_when_not_dict():
    """baseline_suite returns None when entry is not a dict."""
    baseline = {"suites": {"bad": "not_a_dict"}}
    result = system_tests_run_summary.baseline_suite(baseline, "bad")
    assert result is None


def test_format_count_delta_no_baseline():
    """format_count_delta returns empty string when no baseline."""
    assert system_tests_run_summary.format_count_delta(100, None) == ""
    assert system_tests_run_summary.format_count_delta(100, {}) == ""


def test_format_count_delta_no_change():
    """format_count_delta returns empty string when count matches."""
    baseline = {"tests": 100}
    assert system_tests_run_summary.format_count_delta(100, baseline) == ""


def test_format_count_delta_increase():
    """format_count_delta returns positive delta."""
    baseline = {"tests": 100}
    assert system_tests_run_summary.format_count_delta(105, baseline) == " (+5)"


def test_format_count_delta_decrease():
    """format_count_delta returns negative delta."""
    baseline = {"tests": 100}
    assert system_tests_run_summary.format_count_delta(95, baseline) == " (-5)"


def test_integration_drift_warnings_test_count_drift():
    """integration_drift_warnings detects test count drift."""
    baseline = {"suites": {"tc_tests": {"tests": 100, "skipped": 5}}, "skip_tolerance_default": 0}
    suite_counts = [("tc_tests", "Test Client", (105, 100, 0, 5))]
    warnings = system_tests_run_summary.integration_drift_warnings(baseline, suite_counts, "12345")
    assert len(warnings) == 1
    assert "105" in warnings[0]
    assert "(+5 vs baseline 100)" in warnings[0]


def test_integration_drift_warnings_skip_drift():
    """integration_drift_warnings detects skip count drift beyond tolerance."""
    baseline = {
        "suites": {"tc_tests": {"tests": 100, "skipped": 5, "skip_tolerance": 2}},
        "skip_tolerance_default": 0,
    }
    suite_counts = [("tc_tests", "Test Client", (100, 90, 0, 10))]
    warnings = system_tests_run_summary.integration_drift_warnings(baseline, suite_counts, "12345")
    assert len(warnings) == 1
    assert "10" in warnings[0]
    assert "(+5 vs baseline 5; tolerance +2)" in warnings[0]


def test_integration_drift_warnings_skip_within_tolerance():
    """integration_drift_warnings allows skip drift within tolerance."""
    baseline = {
        "suites": {"tc_tests": {"tests": 100, "skipped": 5, "skip_tolerance": 5}},
        "skip_tolerance_default": 0,
    }
    suite_counts = [("tc_tests", "Test Client", (100, 90, 0, 10))]
    warnings = system_tests_run_summary.integration_drift_warnings(baseline, suite_counts, "12345")
    assert len(warnings) == 0


def test_must_not_skip_failures_allows_legitimate_skip_suites():
    """must_not_skip_failures allows skips in conformance/live/security suites."""
    suite_counts = [
        ("tc_tests", "Test Client", (100, 95, 0, 5)),
        ("con_live", "Console Client Live", (57, 19, 0, 38)),
        ("cs_live", "C# Client Live", (110, 110, 0, 0)),
        ("wc_live", "Web Client Live", (100, 97, 0, 3)),
        ("wc_browser", "Web Client Browser", (65, 65, 0, 0)),
        ("csharp_opcua_security", "C# OPC UA Security", (39, 30, 0, 9)),
        ("console_opcua_security", "Console OPC UA Security", (12, 11, 0, 1)),
    ]
    failures = system_tests_run_summary.must_not_skip_failures(suite_counts)
    assert failures == []


def test_must_not_skip_failures_rejects_skips_in_smoke_and_unit_suites():
    """must_not_skip_failures fires when a smoke or unit suite has any skip."""
    suite_counts = [
        ("sd_smoke", "Server Smoke", (10, 9, 0, 1)),
        ("wd_py", "Web Docker Python Unit", (50, 48, 0, 2)),
        ("wd_js", "Web Docker JS Unit", (40, 40, 0, 0)),
        ("tc_smoke", "Test Client Smoke", (10, 8, 0, 2)),
    ]
    failures = system_tests_run_summary.must_not_skip_failures(suite_counts)
    assert len(failures) == 3
    assert any("Server Smoke" in f and "1" in f for f in failures)
    assert any("Web Docker Python Unit" in f and "2" in f for f in failures)
    assert any("Test Client Smoke" in f and "2" in f for f in failures)
    assert all("smoke and unit suites" in f for f in failures)


def test_must_not_skip_failures_handles_missing_artifacts():
    """A suite with no JUnit XML (counts[3] is None) does not trip the gate."""
    suite_counts = [("sd_smoke", "Server Smoke", (None, None, None, None))]
    failures = system_tests_run_summary.must_not_skip_failures(suite_counts)
    assert failures == []


def test_seconds_parses_float_string():
    """seconds parses string to float."""
    assert system_tests_run_summary.seconds("123.45") == 123.45


def test_seconds_returns_zero_for_none():
    """seconds returns 0.0 for None."""
    assert system_tests_run_summary.seconds(None) == 0.0


def test_seconds_returns_zero_for_invalid():
    """seconds returns 0.0 for invalid input."""
    assert system_tests_run_summary.seconds("not a number") == 0.0


def test_format_duration_minutes():
    """format_duration converts to minutes for values >= 60."""
    assert system_tests_run_summary.format_duration(125.0) == "2.1 min"


def test_format_duration_seconds():
    """format_duration shows seconds for values < 60."""
    assert system_tests_run_summary.format_duration(45.5) == "45.5 s"


def test_format_optional_duration_none():
    """format_optional_duration returns dash for None."""
    assert system_tests_run_summary.format_optional_duration(None) == "—"


def test_format_optional_duration_with_value():
    """format_optional_duration formats non-None values."""
    assert "s" in system_tests_run_summary.format_optional_duration(30.0)


def test_parse_actions_time_valid_iso():
    """parse_actions_time parses ISO 8601 timestamp."""
    result = system_tests_run_summary.parse_actions_time("2026-05-14T10:30:00Z")
    assert result == datetime.datetime(2026, 5, 14, 10, 30, 0, tzinfo=datetime.UTC)


def test_parse_actions_time_empty_returns_none():
    """parse_actions_time returns None for empty string."""
    assert system_tests_run_summary.parse_actions_time("") is None
    assert system_tests_run_summary.parse_actions_time(None) is None


def test_parse_actions_time_invalid_returns_none():
    """parse_actions_time returns None for invalid format."""
    assert system_tests_run_summary.parse_actions_time("not a date") is None


def test_next_link_extracts_next_url():
    """next_link extracts the next pagination URL from Link header."""
    header = '<https://api.github.com/repos/org/repo/actions/runs/123/jobs?page=2>; rel="next"'
    result = system_tests_run_summary.next_link(header)
    assert result == "https://api.github.com/repos/org/repo/actions/runs/123/jobs?page=2"


def test_next_link_returns_none_for_no_next():
    """next_link returns None when no next link present."""
    header = '<https://api.github.com/repos/org/repo/actions/runs/123/jobs?page=5>; rel="last"'
    result = system_tests_run_summary.next_link(header)
    assert result is None


def test_next_link_returns_none_for_empty():
    """next_link returns None for empty header."""
    assert system_tests_run_summary.next_link(None) is None
    assert system_tests_run_summary.next_link("") is None


def test_browser_feature_timings_parses_artifacts(tmp_path):
    """browser_feature_timings extracts timing data from JSON artifacts."""
    artifact_dir = tmp_path / "results-shard-1of2" / "timing"
    artifact_dir.mkdir(parents=True)
    timing_file = artifact_dir / "timing-latest.json"
    timing_file.write_text(
        json.dumps(
            {
                "total_seconds": 180.5,
                "stages": [
                    {"name": "pip-install", "duration_seconds": 30.0},
                    {"name": "npm-install", "duration_seconds": 45.0},
                    {"name": "playwright-install", "duration_seconds": 25.0},
                    {"name": "playwright-features", "duration_seconds": 75.0},
                ],
            }
        )
    )

    rows = system_tests_run_summary.browser_feature_timings(
        str(tmp_path / "*shard-1of2*" / "**" / "timing-latest.json")
    )
    assert len(rows) == 1
    assert rows[0]["shard"] == "1/2"
    assert rows[0]["total"] == 180.5
    assert rows[0]["pip"] == 30.0
    assert rows[0]["playwright_features"] == 75.0


def test_browser_feature_timings_handles_full_shard(tmp_path):
    """browser_feature_timings recognizes non-sharded runs."""
    artifact_dir = tmp_path / "results-full" / "timing"
    artifact_dir.mkdir(parents=True)
    timing_file = artifact_dir / "timing-latest.json"
    timing_file.write_text(json.dumps({"total_seconds": 100.0, "stages": []}))

    rows = system_tests_run_summary.browser_feature_timings(
        str(tmp_path / "*" / "**" / "timing-latest.json")
    )
    assert rows[0]["shard"] == "full"


def test_trx_duration_seconds_parses_hh_mm_ss():
    """trx_duration_seconds parses TRX duration format."""
    assert system_tests_run_summary.trx_duration_seconds("00:02:30.1234567") == 150.1234567


def test_trx_duration_seconds_handles_hours():
    """trx_duration_seconds handles hours correctly."""
    assert system_tests_run_summary.trx_duration_seconds("01:30:45.5") == 5445.5


def test_trx_duration_seconds_empty_returns_zero():
    """trx_duration_seconds returns 0.0 for empty input."""
    assert system_tests_run_summary.trx_duration_seconds("") == 0.0
    assert system_tests_run_summary.trx_duration_seconds(None) == 0.0


def test_trx_duration_seconds_fallback_to_float():
    """trx_duration_seconds falls back to float parsing."""
    assert system_tests_run_summary.trx_duration_seconds("123.45") == 123.45


def test_split_csharp_test_name_splits_on_last_dot():
    """split_csharp_test_name splits class and method on last dot."""
    class_name, method_name = system_tests_run_summary.split_csharp_test_name(
        "Namespace.ClassName.MethodName"
    )
    assert class_name == "Namespace.ClassName"
    assert method_name == "MethodName"


def test_split_csharp_test_name_no_dot():
    """split_csharp_test_name handles names without dots."""
    class_name, method_name = system_tests_run_summary.split_csharp_test_name("TestMethod")
    assert class_name == "unknown"
    assert method_name == "TestMethod"


def test_short_csharp_class_extracts_last_segment():
    """short_csharp_class returns last segment after final dot."""
    assert system_tests_run_summary.short_csharp_class("Namespace.ClassName") == "ClassName"


def test_short_csharp_class_no_dot():
    """short_csharp_class returns input when no dot."""
    assert system_tests_run_summary.short_csharp_class("ClassName") == "ClassName"


def test_csharp_live_timings_aggregates_by_class(tmp_path):
    """csharp_live_timings aggregates test timings by class."""
    trx_file = tmp_path / "results.trx"
    trx_file.write_text("""<?xml version="1.0"?>
<TestRun>
  <Results>
    <UnitTestResult testName="MyNamespace.ClassA.Test1" duration="00:00:05.0" outcome="Passed"/>
    <UnitTestResult testName="MyNamespace.ClassA.Test2" duration="00:00:03.0" outcome="Passed"/>
    <UnitTestResult testName="MyNamespace.ClassB.Test1" duration="00:00:10.0" outcome="Passed"/>
  </Results>
</TestRun>
""")
    result = system_tests_run_summary.csharp_live_timings(str(trx_file))
    assert result is not None
    assert len(result["classes"]) == 2
    assert result["classes"][0]["class"] == "MyNamespace.ClassB"  # Sorted by total desc
    assert result["classes"][0]["total"] == 10.0
    assert result["classes"][1]["tests"] == 2


def test_csharp_live_timings_no_files_returns_none(tmp_path):
    """csharp_live_timings returns None when no TRX files found."""
    result = system_tests_run_summary.csharp_live_timings(str(tmp_path / "*.trx"))
    assert result is None


def test_job_icon_all_states():
    """job_icon returns correct icons for all known states."""
    assert system_tests_run_summary.job_icon("success") == "✅"
    assert system_tests_run_summary.job_icon("failure") == "❌"
    assert system_tests_run_summary.job_icon("cancelled") == "🚫"
    assert system_tests_run_summary.job_icon("skipped") == "⏭️"
    assert system_tests_run_summary.job_icon("recorded") == "📊"
    assert system_tests_run_summary.job_icon("unknown") == "⚠️"


def test_tests_formatter_with_baseline():
    """tests formatter includes delta when baseline provided."""
    baseline = {"tests": 100}
    assert system_tests_run_summary.tests(105, 105, 0, 0, baseline) == "105 (+5) ✅"


def test_tests_formatter_no_failures():
    """tests formatter shows checkmark when no failures."""
    assert system_tests_run_summary.tests(100, 100, 0) == "100 ✅"


def test_tests_formatter_with_failures():
    """tests formatter shows X and ratio when failures exist."""
    assert system_tests_run_summary.tests(100, 90, 10) == "90 / 100 ❌"


def test_skips_formatter():
    """skips formatter converts to string or returns dash."""
    assert system_tests_run_summary.skips(5) == "5"
    assert system_tests_run_summary.skips(None) == "—"


def test_count_test_results():
    """count_test_results combines tests and skips formatting."""
    result = system_tests_run_summary.count_test_results((100, 95, 5, 3))
    assert "Passed: 95 / 100" in result
    assert "Skipped: 3" in result


def test_count_test_results_with_baseline():
    """count_test_results includes baseline delta."""
    baseline = {"tests": 98}
    result = system_tests_run_summary.count_test_results((100, 95, 5, 3), baseline)
    assert "(+2)" in result


def test_count_test_results_zero_fail_with_skips_uses_passed_count():
    """When there are skipped tests but no failures, the cell must report the
    *passed* count (not the total) so the math is honest. Regression for the
    bug that reported (1043 total, 889 passed, 0 failed, 154 skipped) as
    "1,043 Passed, 154 Skipped" — which double-counts the 154 skips."""
    result = system_tests_run_summary.count_test_results((1043, 889, 0, 154))
    assert result == "Passed: 889, Skipped: 154"


def test_count_test_results_all_pass_no_skip():
    """Clean all-passed suite prints the passed and skipped counts."""
    result = system_tests_run_summary.count_test_results((50, 50, 0, 0))
    assert result == "Passed: 50, Skipped: 0"


def test_bulleted_test_results_clean_lane():
    """Single-suite report cells use stable HTML bullets and Title Case labels."""
    result = system_tests_run_summary.bulleted_test_results((10, 10, 0, 0))

    assert result == "&bull; Passed: 10<br>&bull; Skipped: 0"


def test_bulleted_test_results_failed_lane_includes_failed_count():
    """Failed suites keep passed/total, failed, and skipped counts visible."""
    result = system_tests_run_summary.bulleted_test_results((10, 7, 2, 1))

    assert result == "&bull; Passed: 7 / 10<br>&bull; Failed: 2<br>&bull; Skipped: 1"


def test_bulleted_test_results_not_reported_lane():
    """Missing artifact data is explicit and still uses the same bullet shape."""
    result = system_tests_run_summary.bulleted_test_results((None, None, None, None))

    assert result == "&bull; Not Reported"


def test_bulleted_multilane_test_results_indents_sub_counts():
    """Multi-suite cells keep suite names and count rows visually distinct."""
    result = system_tests_run_summary.bulleted_multilane_test_results(
        ("Python", (700, 700, 0, 0), None),
        ("JavaScript", (557, 557, 0, 0), None),
    )

    assert result == (
        "&bull; Python<br>"
        "&nbsp;&nbsp;&bull; Passed: 700<br>"
        "&nbsp;&nbsp;&bull; Skipped: 0<br>"
        "&bull; JavaScript<br>"
        "&nbsp;&nbsp;&bull; Passed: 557<br>"
        "&nbsp;&nbsp;&bull; Skipped: 0"
    )


def test_plural_label_handles_singular_and_plural():
    assert system_tests_run_summary.plural_label(1, "suite") == "1 suite"
    assert system_tests_run_summary.plural_label(2, "suite") == "2 suites"
    assert system_tests_run_summary.plural_label(2, "benchmark") == "2 benchmarks"


def test_skipped_count_cell_uses_icon_only_when_nonzero():
    assert system_tests_run_summary.skipped_count_cell(None) == "—"
    assert system_tests_run_summary.skipped_count_cell(0) == "0"
    assert system_tests_run_summary.skipped_count_cell(154) == "154 ⏭️"


def test_tests_cell_zero_fail_with_skips_uses_passed_count():
    """tests_cell mirror of the same regression — used by Conformance Overview."""
    result = system_tests_run_summary.tests_cell((1043, 889, 0, 154))
    assert "889" in result
    assert "1,043" not in result
    assert "✅" in result


def test_bottleneck_candidates_sorts_by_duration():
    """bottleneck_candidates sorts timing sources by duration descending."""
    job_timings = [("job1", 100.0, "success"), ("job2", 200.0, "success")]
    wc_timings = [{"shard": "1/2", "total": 150.0}]
    cs_timings = {"classes": [{"class": "ClassA", "total": 50.0}]}

    result = system_tests_run_summary.bottleneck_candidates(job_timings, wc_timings, cs_timings)

    assert result[0][2] == 200.0  # Highest duration first
    assert result[1][2] == 150.0
    assert result[2][2] == 100.0


def test_bottleneck_candidates_handles_none_durations():
    """bottleneck_candidates filters out None durations from jobs."""
    job_timings = [("job1", None, "success"), ("job2", 100.0, "success")]

    result = system_tests_run_summary.bottleneck_candidates(job_timings, [], None)

    assert len(result) == 1
    assert result[0][1] == "job2"


def test_module_bootstrap_runs_main_via_runpy(tmp_path, monkeypatch):
    """The `if __name__ == "__main__":` bootstrap is exercised end-to-end.

    Runs the module as a script via `runpy.run_path` so the bootstrap
    branch (which previously carried `# pragma: no cover`) is now covered
    by a real test. The module's `main()` reads env vars with defaults
    and globs CI artifacts, so an empty working directory plus a temp
    `GITHUB_STEP_SUMMARY` is enough to exercise the path without side
    effects. `skip_policy_failures` will be empty with no inputs, so the
    bootstrap returns normally without invoking `sys.exit`.
    """
    import runpy

    summary_file = tmp_path / "step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
    monkeypatch.chdir(tmp_path)
    module_path = Path(system_tests_run_summary.__file__)

    runpy.run_path(str(module_path), run_name="__main__")

    assert summary_file.exists()
    assert summary_file.stat().st_size > 0


def test_lane_status_fmt_success():
    assert system_tests_run_summary.lane_status_fmt("success") == "Success ✅"


def test_lane_status_fmt_failure():
    assert system_tests_run_summary.lane_status_fmt("failure") == "Failure ❌"


def test_lane_status_fmt_skipped():
    assert system_tests_run_summary.lane_status_fmt("skipped") == "Skipped ⏭️"


def test_status_text_title_cases_known_unknown_and_snake_case_values():
    """User-facing status text stays Title Case without changing internal keys."""
    assert system_tests_run_summary.status_text("success") == "Success"
    assert system_tests_run_summary.status_text("unknown") == "Unknown"
    assert system_tests_run_summary.status_text("not_reported") == "Not Reported"
    assert system_tests_run_summary.status_text("") == "Unknown"


def test_perf_status_fmt_recorded():
    assert system_tests_run_summary.perf_status_fmt("recorded") == "Recorded 📊"


def test_perf_status_fmt_missing():
    assert system_tests_run_summary.perf_status_fmt("missing") == "Missing ⚠️"


def test_perf_status_fmt_workflow_job_conclusions():
    assert system_tests_run_summary.perf_status_fmt("success") == "Passed ✅"
    assert system_tests_run_summary.perf_status_fmt("failure") == "Failed ❌"
    assert system_tests_run_summary.perf_status_fmt("cancelled") == "Cancelled ⚪"
    assert system_tests_run_summary.perf_status_fmt("skipped") == "Skipped ⏭️"


def test_perf_status_fmt_unknown_fallback():
    assert system_tests_run_summary.perf_status_fmt("") == "Unknown ⚠️"
    assert system_tests_run_summary.perf_status_fmt("None") == "Unknown ⚠️"
    assert system_tests_run_summary.perf_status_fmt("weird") == "Unknown ⚠️"


def _write_perf_xml(tmp_path, properties):
    body = "\n".join(f'      <property name="{k}" value="{v}" />' for k, v in properties.items())
    xml = (
        '<testsuite name="lane">\n'
        '  <testcase classname="lane" name="test_result_transfer_time">\n'
        "    <properties>\n"
        f"{body}\n"
        "    </properties>\n"
        "  </testcase>\n"
        "</testsuite>\n"
    )
    target = tmp_path / "pytest-live.xml"
    target.write_text(xml, encoding="ascii")
    return target


def test_load_perf_benchmarks_happy_path(tmp_path):
    _write_perf_xml(
        tmp_path,
        {
            "perf_sample_count": 20,
            "perf_mean_total_ms": 86.19,
            "perf_p90_total_ms": 100.71,
            "perf_min_total_ms": 12.63,
            "perf_max_total_ms": 102.68,
            "perf_threshold_mean_ms": 500,
            "perf_threshold_p90_ms": 500,
        },
    )
    metrics = system_tests_run_summary.load_perf_benchmarks(str(tmp_path / "*.xml"))
    assert metrics is not None
    assert metrics["perf_sample_count"] == 20.0
    assert metrics["perf_mean_total_ms"] == 86.19
    assert metrics["perf_threshold_p90_ms"] == 500.0


def test_load_perf_benchmarks_missing_file(tmp_path):
    assert system_tests_run_summary.load_perf_benchmarks(str(tmp_path / "absent*.xml")) is None


def test_load_perf_benchmarks_partial_properties_returns_none(tmp_path):
    _write_perf_xml(
        tmp_path,
        {
            "perf_sample_count": 5,
            "perf_mean_total_ms": 10.0,
            # missing perf_p90_total_ms, perf_min_total_ms, perf_max_total_ms
        },
    )
    assert system_tests_run_summary.load_perf_benchmarks(str(tmp_path / "*.xml")) is None


def test_load_perf_benchmarks_skips_unparseable_value(tmp_path):
    _write_perf_xml(
        tmp_path,
        {
            "perf_sample_count": "not-a-number",
            "perf_mean_total_ms": 10.0,
            "perf_p90_total_ms": 12.0,
            "perf_min_total_ms": 5.0,
            "perf_max_total_ms": 20.0,
        },
    )
    # required field is non-numeric => incomplete required set => None
    assert system_tests_run_summary.load_perf_benchmarks(str(tmp_path / "*.xml")) is None


def test_render_perf_section_empty_returns_empty_list():
    assert system_tests_run_summary.render_perf_section([]) == []
    assert system_tests_run_summary.render_perf_section([("X", {})]) == []


def test_render_perf_section_pass_renders_table_and_marks_pass():
    metrics = {
        "perf_sample_count": 20,
        "perf_mean_total_ms": 86.19,
        "perf_p90_total_ms": 100.71,
        "perf_min_total_ms": 12.63,
        "perf_max_total_ms": 102.68,
        "perf_threshold_mean_ms": 500,
        "perf_threshold_p90_ms": 500,
    }
    lines = system_tests_run_summary.render_perf_section([("Console", metrics)])
    assert any("### ⏱️ Performance Benchmarks" in line for line in lines)
    assert any("### ⏱️ Performance Benchmarks — 1 benchmark" in line for line in lines)
    header = [line for line in lines if line.startswith("| Benchmark")][0]
    row = [line for line in lines if line.startswith("| Console")][0]
    assert "90th Percentile" not in header
    assert "20" in row
    assert "86.19" in row
    assert "100.71" not in row
    assert "Average &lt; 500 ms · 90% of samples &lt; 500 ms" in row
    assert "Tail Check" not in row
    assert "102.68" in row
    assert "✅ Pass" in row
    assert any("90% of samples to stay below the target" in line for line in lines)


def test_render_perf_section_fail_when_mean_exceeds_threshold():
    metrics = {
        "perf_sample_count": 10,
        "perf_mean_total_ms": 600.0,
        "perf_p90_total_ms": 100.0,
        "perf_min_total_ms": 5.0,
        "perf_max_total_ms": 700.0,
        "perf_threshold_mean_ms": 500,
        "perf_threshold_p90_ms": 500,
    }
    lines = system_tests_run_summary.render_perf_section([("MyLane", metrics)])
    row = [line for line in lines if line.startswith("| MyLane")][0]
    assert "❌ Fail" in row


def test_render_perf_section_without_thresholds_uses_dash():
    metrics = {
        "perf_sample_count": 3,
        "perf_mean_total_ms": 10.0,
        "perf_p90_total_ms": 12.0,
        "perf_min_total_ms": 5.0,
        "perf_max_total_ms": 20.0,
    }
    lines = system_tests_run_summary.render_perf_section([("MyLane", metrics)])
    row = [line for line in lines if line.startswith("| MyLane")][0]
    assert row.count("—") >= 2
