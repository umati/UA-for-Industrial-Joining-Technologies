"""Unit tests for reporting/_junit_failures.py pure helper module."""

from __future__ import annotations

from defusedxml import ElementTree as ET

from reporting import _junit_failures


def test_extract_failures_with_message_attribute():
    xml = """
    <testsuite>
        <testcase classname="pkg.TestA" name="test_one">
            <failure message="AssertionError: expected 1 got 2" type="AssertionError"/>
        </testcase>
    </testsuite>
    """
    root = ET.fromstring(xml)
    failures = _junit_failures.extract_failures(root)
    assert failures == [("pkg.TestA", "test_one", "AssertionError: expected 1 got 2")]


def test_extract_failures_with_text_content():
    xml = """
    <testsuite>
        <testcase classname="pkg.TestB" name="test_error">
            <error>ZeroDivisionError: division by zero
  traceback line 1
  traceback line 2</error>
        </testcase>
    </testsuite>
    """
    root = ET.fromstring(xml)
    failures = _junit_failures.extract_failures(root)
    assert failures == [("pkg.TestB", "test_error", "ZeroDivisionError: division by zero")]


def test_extract_failures_emits_both_failure_and_error():
    xml = """
    <testsuite>
        <testcase classname="pkg.TestC" name="test_both">
            <failure message="Assertion failure"/>
            <error message="Teardown error"/>
        </testcase>
    </testsuite>
    """
    root = ET.fromstring(xml)
    failures = _junit_failures.extract_failures(root)
    assert failures == [
        ("pkg.TestC", "test_both (failure)", "Assertion failure"),
        ("pkg.TestC", "test_both (error)", "Teardown error"),
    ]


def test_extract_failures_ignores_passing_and_skipped():
    xml = """
    <testsuite>
        <testcase classname="pkg.TestD" name="test_pass"/>
        <testcase classname="pkg.TestD" name="test_skip">
            <skipped message="skip reason"/>
        </testcase>
    </testsuite>
    """
    root = ET.fromstring(xml)
    failures = _junit_failures.extract_failures(root)
    assert failures == []


def test_extract_failures_defaults_for_missing_attributes():
    xml = """
    <testsuite>
        <testcase>
            <failure/>
        </testcase>
    </testsuite>
    """
    root = ET.fromstring(xml)
    failures = _junit_failures.extract_failures(root)
    assert failures == [("", "unknown", "no message")]


def test_extract_failures_truncates_long_messages():
    long_msg = "A" * 300
    xml = f"""
    <testsuite>
        <testcase classname="pkg.TestE" name="test_long">
            <failure message="{long_msg}"/>
        </testcase>
    </testsuite>
    """
    root = ET.fromstring(xml)
    failures = _junit_failures.extract_failures(root)
    assert len(failures[0][2]) == 200
    assert failures[0][2] == "A" * 200


def test_format_failure_section_empty():
    assert _junit_failures.format_failure_section("Suite", [], lambda x: x) == []
    assert _junit_failures.format_failure_section("Suite", [], lambda x: x, fail_count=0) == []


def test_format_failure_section_renders_table():
    failures = [
        ("pkg.ClassA", "test_1", "error msg"),
        ("", "test_standalone", "another msg"),
    ]

    def dummy_escape(val):
        return f"[{val}]"

    lines = _junit_failures.format_failure_section("My Suite", failures, dummy_escape)
    assert lines[1] == "<details open><summary>❌ <b>My Suite</b> — 2 Failed</summary>"
    assert "| Test | Message |" in lines
    assert "| [pkg.ClassA.test_1] | [error msg] |" in lines
    assert "| [test_standalone] | [another msg] |" in lines
    assert lines[-1] == "</details>"


def test_format_failure_section_caps_at_max_rows():
    failures = [(f"pkg.Class{i}", f"test_{i}", f"msg_{i}") for i in range(60)]
    lines = _junit_failures.format_failure_section("Suite", failures, lambda x: x)
    assert any("…and 10 more" in line for line in lines)


def test_format_failure_section_indicates_unavailable_details():
    failures = [("pkg.Class1", "test_1", "msg_1")]
    lines = _junit_failures.format_failure_section("Suite", failures, lambda x: x, fail_count=5)
    assert lines[1] == "<details open><summary>❌ <b>Suite</b> — 5 Failed</summary>"
    assert any("…and 4 more (details unavailable in JUnit XML)" in line for line in lines)


def test_annotation_lines_formatting_and_escaping():
    failures = [
        ("pkg.Class", "test_name", "Error: failed 50% of runs\r\nsecond line"),
    ]
    annotations = _junit_failures.annotation_lines("Suite, Special: Title", failures)
    assert len(annotations) == 1
    # Check escaping:
    # Title has ',' replaced with %2C and ':' with %3A
    assert "title=Suite%2C Special%3A Title" in annotations[0]
    # Message has '%' -> '%25', '\r' -> '%0D', '\n' -> '%0A'
    assert "%25" in annotations[0]
    assert "%0D" in annotations[0]
    assert "%0A" in annotations[0]


def test_annotation_lines_caps_at_max():
    failures = [(f"pkg.Class{i}", f"test_{i}", f"msg_{i}") for i in range(25)]
    annotations = _junit_failures.annotation_lines("Suite", failures)
    assert len(annotations) == _junit_failures.MAX_ANNOTATIONS_PER_SUITE
