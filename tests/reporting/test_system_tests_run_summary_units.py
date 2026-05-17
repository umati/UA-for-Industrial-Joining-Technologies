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
    assert any("3 skipped" in line for line in result)
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


def test_non_test_client_skip_failures_allows_tc_tests():
    """non_test_client_skip_failures allows skips in tc_tests suite."""
    suite_counts = [("tc_tests", "Test Client", (100, 95, 0, 5))]
    failures = system_tests_run_summary.non_test_client_skip_failures(suite_counts)
    assert len(failures) == 0


def test_non_test_client_skip_failures_rejects_other_skips():
    """non_test_client_skip_failures rejects skips in non-tc_tests suites."""
    suite_counts = [("wc_live", "Web Client Live", (100, 97, 0, 3))]
    failures = system_tests_run_summary.non_test_client_skip_failures(suite_counts)
    assert len(failures) == 1
    assert "Web Client Live" in failures[0]
    assert "3" in failures[0]


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
    result = system_tests_run_summary.tests(105, 105, 0, 0, baseline)
    assert "105" in result
    assert "(+5)" in result


def test_tests_formatter_no_failures():
    """tests formatter shows checkmark when no failures."""
    assert "✅" in system_tests_run_summary.tests(100, 100, 0)


def test_tests_formatter_with_failures():
    """tests formatter shows X and ratio when failures exist."""
    result = system_tests_run_summary.tests(100, 90, 10)
    assert "❌" in result
    assert "90 / 100" in result


def test_skips_formatter():
    """skips formatter converts to string or returns dash."""
    assert system_tests_run_summary.skips(5) == "5"
    assert system_tests_run_summary.skips(None) == "—"


def test_count_test_results():
    """count_test_results combines tests and skips formatting."""
    result = system_tests_run_summary.count_test_results((100, 95, 5, 3))
    assert "95 / 100" in result
    assert "3 skipped" in result


def test_count_test_results_with_baseline():
    """count_test_results includes baseline delta."""
    baseline = {"tests": 98}
    result = system_tests_run_summary.count_test_results((100, 95, 5, 3), baseline)
    assert "(+2)" in result


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
