"""Additional edge case tests for coverage completion."""

from __future__ import annotations

import pytest

from reporting import ci_run_summary, system_tests_run_summary


def test_parse_xml_root_internal_subset_without_end_bracket(tmp_path):
    """parse_xml_root handles edge case where ] appears before > in DOCTYPE."""
    xml = tmp_path / "test.xml"
    xml.write_bytes(b"""<?xml version="1.0"?>
<!DOCTYPE root [
<coverage line-rate="0.5"/>
""")
    with pytest.raises(ValueError, match="DTD/entity"):
        ci_run_summary.parse_xml_root(str(xml))


def test_collect_skips_with_exception(tmp_path):
    """collect_skips prints warning and continues on exception."""
    xml = tmp_path / "bad.xml"
    xml.write_text("not xml")
    result = ci_run_summary.collect_skips(str(xml))
    assert result == []


def test_system_collect_skips_with_exception(tmp_path):
    """system collect_skips prints warning and continues on exception."""
    xml = tmp_path / "bad.xml"
    xml.write_text("not xml")
    result = system_tests_run_summary.collect_skips(str(xml))
    assert result == []


def test_format_count_delta_invalid_baseline():
    """format_count_delta handles invalid baseline tests value."""
    baseline = {"tests": "not_a_number"}
    result = system_tests_run_summary.format_count_delta(100, baseline)
    assert result == ""


def test_format_count_delta_none_in_baseline():
    """format_count_delta handles None in baseline tests."""
    baseline = {"tests": None}
    result = system_tests_run_summary.format_count_delta(100, baseline)
    assert result == ""


def test_integration_drift_warnings_skip_continues_when_expected_none():
    """integration_drift_warnings skips when expected_skips is None."""
    baseline = {
        "suites": {"tc_tests": {"tests": 100}},  # No skipped field
        "skip_tolerance_default": 0,
    }
    suite_counts = [("tc_tests", "Test", (100, 95, 0, 5))]
    warnings = system_tests_run_summary.integration_drift_warnings(baseline, suite_counts, "12345")
    assert len(warnings) == 0


def test_integration_drift_warnings_skip_continues_when_counts_none():
    """integration_drift_warnings skips when entry exists but counts[0] is None."""
    baseline = {"suites": {"tc_tests": {"tests": 100}}, "skip_tolerance_default": 0}
    suite_counts = [("tc_tests", "Test", (None, None, None, None))]
    warnings = system_tests_run_summary.integration_drift_warnings(baseline, suite_counts, "12345")
    assert len(warnings) == 0


def test_job_durations_no_token_returns_empty(monkeypatch):
    """job_durations returns empty list when no token available."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = system_tests_run_summary.job_durations("repos/org/repo/actions/runs/123/jobs")
    assert result == []


def test_job_durations_no_path_returns_empty():
    """job_durations returns empty list when no path provided."""
    result = system_tests_run_summary.job_durations("")
    assert result == []


def test_job_durations_non_https_url_raises_error(monkeypatch):
    """job_durations rejects non-HTTPS URLs."""
    import importlib

    module = importlib.import_module("reporting.system_tests_run_summary")

    monkeypatch.setenv("GH_TOKEN", "test-token")
    monkeypatch.setenv("GH_API_URL", "http://insecure.api.github.com")

    result = module.job_durations("repos/org/repo/actions/runs/123/jobs")
    assert result == []


def test_job_durations_filters_incomplete_jobs(monkeypatch):
    """job_durations filters out jobs with no duration that aren't completed."""
    import importlib
    import io

    module = importlib.import_module("reporting.system_tests_run_summary")

    monkeypatch.setenv("GH_TOKEN", "test-token")

    class FakeResponse(io.BytesIO):
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout):
        payload = (
            b'{"jobs": ['
            b'{"name": "Running Job", "status": "in_progress", "started_at": null, '
            b'"completed_at": null},'
            b'{"name": "Completed Job", "status": "completed", "started_at": '
            b'"2026-05-14T10:00:00Z", "completed_at": "2026-05-14T10:01:00Z", '
            b'"conclusion": "success"}'
            b"]}"
        )
        return FakeResponse(payload)

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    rows = module.job_durations("repos/org/repo/actions/runs/123/jobs")
    assert len(rows) == 1
    assert rows[0][0] == "Completed Job"


def test_browser_feature_timings_exception(tmp_path, capsys):
    """browser_feature_timings prints warning on exception."""
    bad_json = tmp_path / "timing-latest.json"
    bad_json.write_text("not json")

    result = system_tests_run_summary.browser_feature_timings(str(bad_json))
    assert result == []
    captured = capsys.readouterr()
    assert "[WARN] browser_feature_timings" in captured.out


def test_csharp_live_timings_exception(tmp_path, capsys):
    """csharp_live_timings prints warning on exception."""
    bad_trx = tmp_path / "bad.trx"
    bad_trx.write_text("not xml")

    result = system_tests_run_summary.csharp_live_timings(str(bad_trx))
    assert result is None
    captured = capsys.readouterr()
    assert "[WARN] csharp_live_timings" in captured.out


def test_format_skip_section_counter_increment_when_mismatch():
    """format_skip_section increments counter for unavailable skip details."""
    skips = [("test1", "reason1")]
    result = system_tests_run_summary.format_skip_section("Label", skips, 3)
    # Check that the counter was incremented by 2 (3 - 1)
    lines = "\n".join(result)
    assert "Skip details unavailable in JUnit XML" in lines
    assert "| 2 |" in lines or "2 |" in lines
