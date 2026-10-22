"""Unit tests for helpers.cu_test_counts (per-CU and unique live test counts)."""

from __future__ import annotations

import json
import re

from helpers.cu_test_counts import (
    CATEGORY_EXERCISED,
    CATEGORY_NO_TESTS,
    CATEGORY_NOT_RUN,
    CATEGORY_SKIPPED_ONLY,
    TestCountSummary,
    build_test_count_summary,
    junit_totals_from_parsed,
    load_test_count_summary,
    normalize_reason,
    parse_junit_totals,
    render_console_lines,
    render_markdown_details,
    render_markdown_overview_line,
    render_text_lines,
)


def _test(nodeid: str, cus: list[str], outcome: str, reason: str = "", phase: str = "call") -> dict:
    return {"nodeid": nodeid, "cus": cus, "outcome": outcome, "reason": reason, "phase": phase}


def _payload() -> dict:
    tests = [
        _test("t.py::multi_cu_pass", ["ALPHA", "BETA"], "passed"),
        _test(
            "t.py::alpha_not_supported",
            ["ALPHA"],
            "not_supported",
            "('C:\\\\x\\\\conftest.py', 12, \"Skipped: Method 'Foo' is not supported NOT SUPPORTED\")",
            phase="setup",
        ),
        _test("t.py::gamma_blocked", ["GAMMA"], "blocked", "Skipped: External trigger required"),
        _test("t.py::delta_failed", ["DELTA"], "failed"),
        _test("t.py::epsilon_setup_error", ["EPSILON"], "error", phase="setup"),
        _test("t.py::zeta_untested", ["ZETA"], "untested", phase="collection"),
        _test("t.py::vendor_pass", ["VENDOR_EXT"], "passed"),
    ]
    by_cu: dict[str, dict] = {
        key: {} for key in ("ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON", "ZETA", "ETA", "VENDOR_EXT")
    }
    return {
        "schema": "ijt-cu-coverage-report/v1",
        "summary": {"official_cu_count": 7, "extension_cus": ["VENDOR_EXT"]},
        "by_cu": by_cu,
        "tests": tests,
    }


def _junit_xml(cases: list[str]) -> str:
    body = "".join(cases)
    return f'<?xml version="1.0"?><testsuites><testsuite name="pytest">{body}</testsuite></testsuites>'


def _case(name: str, child: str = "") -> str:
    return f'<testcase classname="t" name="{name}">{child}</testcase>'


def _summary(junit: dict[str, int] | None = None) -> TestCountSummary:
    summary = build_test_count_summary(_payload(), junit)
    assert summary is not None
    return summary


def _row(summary, key):
    return next(row for row in summary.rows if row.cu_key == key)


def test_global_cu_marked_totals_count_each_test_once():
    summary = build_test_count_summary(_payload())
    assert summary is not None
    assert summary.cu_marked_tests == 7
    assert summary.cu_marked["passed"] == 2
    assert summary.cu_marked["failed"] == 1
    assert summary.cu_marked["error"] == 1
    assert summary.cu_marked["not_supported"] == 1
    assert summary.cu_marked["blocked"] == 1
    assert summary.cu_marked["untested"] == 1
    # The multi-CU test adds one link to both ALPHA and BETA: links exceed unique tests.
    assert summary.cu_links == 8
    assert _row(summary, "ALPHA").tests == 2
    assert _row(summary, "BETA").tests == 1


def test_cu_categories_never_treat_skips_as_exercised():
    summary = _summary()
    assert _row(summary, "ALPHA").category == CATEGORY_EXERCISED
    assert _row(summary, "GAMMA").category == CATEGORY_SKIPPED_ONLY
    assert _row(summary, "DELTA").category == CATEGORY_EXERCISED
    assert _row(summary, "EPSILON").category == CATEGORY_EXERCISED
    assert _row(summary, "ZETA").category == CATEGORY_NOT_RUN
    assert _row(summary, "ETA").category == CATEGORY_NO_TESTS
    assert summary.category_counts() == {
        CATEGORY_EXERCISED: 4,
        CATEGORY_SKIPPED_ONLY: 1,
        CATEGORY_NOT_RUN: 1,
        CATEGORY_NO_TESTS: 1,
    }
    assert [row.cu_key for row in summary.extension_rows] == ["VENDOR_EXT"]
    assert {row.cu_key for row in summary.failing_rows} == {"DELTA", "EPSILON"}


def test_failed_and_error_are_reported_separately():
    summary = build_test_count_summary(_payload())
    assert _row(summary, "DELTA").counts["failed"] == 1
    assert _row(summary, "DELTA").counts["error"] == 0
    assert _row(summary, "EPSILON").counts["error"] == 1
    assert _row(summary, "EPSILON").counts["failed"] == 0


def test_normalize_reason_handles_setup_tuple_and_prefix():
    assert normalize_reason("('f.py', 3, 'Skipped: Method X is not supported')") == "Method X is not supported"
    assert normalize_reason("Skipped: External trigger\n  required") == "External trigger required"
    assert normalize_reason("(not a tuple") == "(not a tuple"
    assert normalize_reason("(broken, ')") == "(broken, ')"
    assert len(normalize_reason("Skipped: " + "x" * 500)) == 120


def test_skip_reasons_are_attached_to_skipped_only_cu():
    summary = build_test_count_summary(_payload())
    assert _row(summary, "GAMMA").reasons == (("blocked", "External trigger required", 1),)
    assert _row(summary, "ALPHA").reasons == (("not_supported", "Method 'Foo' is not supported NOT SUPPORTED", 1),)


def test_parse_junit_totals_dedupes_and_keeps_worst_outcome(tmp_path):
    xml = tmp_path / "spec-tests.xml"
    xml.write_text(
        _junit_xml(
            [
                _case("a"),
                _case("a", '<error message="teardown"/>'),
                _case("b", '<skipped message="nope"/>'),
                _case("c", '<skipped type="pytest.xfail" message="known"/>'),
                _case("d", '<failure message="boom"/>'),
                _case("e"),
            ]
        ),
        encoding="utf-8",
    )
    assert parse_junit_totals(xml) == {"tests": 5, "passed": 1, "failed": 1, "error": 1, "skipped": 1, "xfailed": 1}


def test_parse_junit_totals_returns_none_for_missing_or_invalid(tmp_path):
    assert parse_junit_totals(None) is None
    assert parse_junit_totals(tmp_path / "missing.xml") is None
    bad = tmp_path / "bad.xml"
    bad.write_text("<testsuites", encoding="utf-8")
    assert parse_junit_totals(bad) is None


def test_junit_totals_from_parsed_maps_errors_key():
    totals = junit_totals_from_parsed({"passed": 3, "failed": 1, "errors": 2, "skipped": 4, "xfailed": 0})
    assert totals == {"tests": 10, "passed": 3, "failed": 1, "error": 2, "skipped": 4, "xfailed": 0}


def test_unmarked_tests_derive_from_unique_junit_total():
    summary = _summary({"tests": 9, "passed": 4, "failed": 1, "error": 1, "skipped": 3})
    assert summary.unmarked_tests == 2
    assert _summary().unmarked_tests is None


def test_build_returns_none_for_unusable_payload():
    assert build_test_count_summary(None) is None
    assert build_test_count_summary({"tests": "x", "by_cu": {}}) is None
    ignored = build_test_count_summary({"tests": ["not-a-dict"], "by_cu": {"ALPHA": {}}})
    assert ignored is not None
    assert ignored.cu_marked_tests == 0


def test_load_test_count_summary_reads_artifacts(tmp_path):
    cu_json = tmp_path / "cu-coverage-report.json"
    cu_json.write_text(json.dumps(_payload()), encoding="utf-8")
    xml = tmp_path / "spec-tests.xml"
    xml.write_text(_junit_xml([_case("x"), _case("y", '<skipped message="s"/>')]), encoding="utf-8")
    summary = load_test_count_summary(cu_json, xml)
    assert summary is not None
    assert summary.junit is not None
    assert summary.junit["tests"] == 2
    assert load_test_count_summary(tmp_path / "missing.json") is None
    assert load_test_count_summary(None) is None
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    assert load_test_count_summary(broken) is None


def test_console_lines_separate_scopes_and_avoid_root_runner_count_patterns():
    summary = build_test_count_summary(_payload(), {"tests": 9, "passed": 4, "failed": 1, "error": 1, "skipped": 3})
    lines = render_console_lines(summary)
    text = "\n".join(lines)
    assert "Live tests (unique): total=9 passed=4 failed=1 error=1 skipped=3" in text
    assert "CU-marked tests: total=7 (no CU marker: 2)" in text
    assert "CUs (7 official): exercised=4 skipped_only=1 not_run=1 no_tests=0" not in text
    assert "CUs (7 official): exercised=4 skipped_only=1 not_run=1 no_tests=1 extension_cus=1" in text
    assert "CUs with failed/error tests: 2" in text
    for line in lines:
        # Mirror root run_all_tests.py _parse_suite_counts patterns so these lines never
        # replace the child's authoritative pytest/Result counts.
        word = r"(?:passed|failed|errors?|skipped|xfailed|xpassed|warnings?|deselected)"
        assert not re.search(rf"\d+\s+{word}(?:,\s*\d+\s+{word})*\s+in\s+[\d.]+s", line)
        assert not re.search(rf"^\s*\d+\s+{word}\b", line)
        assert not re.search(r"\b\d+/\d+\s+passed\b", line)
        assert not re.search(r"\bTests\s+\d+ passed|Passed:\s*\d", line)
        assert "Checks:" not in line
        assert "Result:" not in line


def test_console_lines_without_junit_and_failing_limit():
    summary = build_test_count_summary(_payload())
    lines = render_console_lines(summary, failing_limit=1)
    assert lines[0] == "  Live tests (unique): unavailable (no JUnit XML)"
    assert any("1 more (see saved summary)" in line for line in lines)


def test_text_lines_include_full_breakdown_and_skipped_only_reasons():
    text = "\n".join(render_text_lines(build_test_count_summary(_payload())))
    assert "Per-CU test counts (CU rows overlap; do not sum):" in text
    assert "[Skipped only]: tests=1 passed=0 blocked=1" in text
    assert "Skipped-only CUs (1):" in text
    assert "Blocked (1): External trigger required" in text
    assert "Not run CUs (1):" in text
    assert "No tests CUs (1):" in text
    assert "[extension]" in text


def test_markdown_details_has_no_headings_and_lists_reasons():
    summary = build_test_count_summary(_payload(), {"tests": 9, "passed": 4, "failed": 1, "error": 1, "skipped": 3})
    overview = render_markdown_overview_line(summary)
    assert "**Live tests (unique):** 9 — 4 passed" in overview
    assert "**CU-marked:** 7 (2 without CU marker)" in overview
    assert "**CUs (7):** 4 exercised · 1 skipped only · 1 not run · 1 without tests" in overview
    lines = render_markdown_details(summary)
    assert lines[0] == "<details>"
    assert not any(line.startswith("#") for line in lines)
    text = "\n".join(lines)
    assert "(extension)" in text
    assert "| External trigger required" not in text  # reason is prefixed by its outcome label
    assert "Blocked (1): External trigger required" in text
    assert render_markdown_details(summary, open_details=True)[0] == "<details open>"


def test_markdown_handles_no_skipped_only_and_xfail():
    payload = _payload()
    payload["tests"] = [t for t in payload["tests"] if t["outcome"] != "blocked"]
    summary = build_test_count_summary(
        payload, {"tests": 7, "passed": 2, "failed": 1, "error": 1, "skipped": 1, "xfailed": 2}
    )
    assert "· 2 xfailed" in render_markdown_overview_line(summary)
    assert "_None._" in render_markdown_details(summary)
    assert "**Live tests:** unavailable" in render_markdown_overview_line(build_test_count_summary(payload))
