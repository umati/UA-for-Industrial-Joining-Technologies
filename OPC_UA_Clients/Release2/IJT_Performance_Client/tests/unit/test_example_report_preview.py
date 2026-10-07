"""Unit test verifying the example report preview script executes successfully."""

from __future__ import annotations

import pytest


def test_example_report_preview_execution(capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.example_report_preview import run_preview

    run_preview()
    captured = capsys.readouterr().out

    assert "IJT PERFORMANCE & SCALE BENCHMARK" in captured
    assert "BENCHMARK EXECUTION SUMMARY" in captured
    assert "PER-SERVER BREAKDOWN" in captured
    assert "FLEET AGGREGATE SUMMARY" in captured
    assert "METRIC DEFINITIONS & RUN NOTES" in captured
    assert "DIAGNOSTIC ASSESSMENT & BOTTLENECK ANALYSIS" in captured
    assert "ALL PERFORMANCE CHECKS PASSED — SYSTEM HEALTHY" in captured
