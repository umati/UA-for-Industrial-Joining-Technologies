"""Unit test verifying the example report preview script executes successfully."""

from __future__ import annotations

import pytest


def test_example_report_preview_execution(capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.example_report_preview import run_preview

    run_preview()
    captured = capsys.readouterr().out

    assert "IJT PERFORMANCE & SCALE BENCHMARK" in captured
    assert "Scale" in captured
    assert "Result Latency" in captured
    assert "Assessment" in captured
    assert "FINDING" not in captured
    assert "HEADLINE LATENCY" not in captured
    assert "Key Latency" not in captured
    assert "METRIC DEFINITIONS" not in captured
    assert "ACTION REQUIRED" not in captured
    assert "OK —" in captured or "INFORMATION —" in captured or "ACTION NEEDED —" in captured
