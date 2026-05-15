"""Final coverage tests for remaining edge cases."""

from __future__ import annotations

import pytest

from reporting import system_tests_run_summary


def test_parse_xml_root_system_internal_subset_without_end_bracket(tmp_path):
    """parse_xml_root handles edge case where ] appears before > in DOCTYPE."""
    xml = tmp_path / "test.xml"
    xml.write_bytes(b"""<?xml version="1.0"?>
<!DOCTYPE root [
<coverage line-rate="0.5"/>
""")
    with pytest.raises(ValueError, match="DTD/entity"):
        system_tests_run_summary.parse_xml_root(str(xml))


def test_parse_junit_exception_continues_parsing(tmp_path):
    """parse_junit continues processing after encountering bad XML."""
    bad_xml = tmp_path / "bad.xml"
    bad_xml.write_text("not xml")

    good_xml = tmp_path / "good.xml"
    good_xml.write_text("""<?xml version="1.0"?>
<testsuite tests="5" failures="0" errors="0" skipped="0"/>
""")

    # The glob will match both files
    total, passed, failed, skipped = system_tests_run_summary.parse_junit(str(tmp_path / "*.xml"))
    # Should process the good one despite the bad one
    assert total == 5
    assert passed == 5


def test_browser_feature_timings_shard_2of2(tmp_path):
    """browser_feature_timings recognizes shard 2of2."""
    artifact_dir = tmp_path / "results-shard-2of2"
    artifact_dir.mkdir()
    timing_file = artifact_dir / "timing-latest.json"
    timing_file.write_text('{"total_seconds": 50.0, "stages": []}')

    rows = system_tests_run_summary.browser_feature_timings(
        str(tmp_path / "*shard-2of2*" / "timing-latest.json")
    )
    assert len(rows) == 1
    assert rows[0]["shard"] == "2/2"


def test_trx_duration_seconds_invalid_format_fallback(tmp_path):
    """trx_duration_seconds falls back to 0.0 for unparseable format."""
    # Should hit the TypeError/ValueError exception path
    assert system_tests_run_summary.trx_duration_seconds("invalid:format:time") == 0.0


def test_tests_formatter_none_total_returns_dash():
    """tests formatter returns dash when total is None."""
    result = system_tests_run_summary.tests(None, None, None)
    assert result == "—"
