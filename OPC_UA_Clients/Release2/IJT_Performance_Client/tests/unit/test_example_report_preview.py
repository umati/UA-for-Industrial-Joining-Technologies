"""Unit test verifying the example report preview script executes successfully."""

from __future__ import annotations

import pytest


def test_example_report_preview_execution(capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.example_report_preview import run_preview

    run_preview()
    captured = capsys.readouterr().out

    assert "IJT PERFORMANCE & SCALE BENCHMARK" in captured
    assert "Run Size" in captured
    assert "Result Latency" in captured
    assert "No Action Needed" in captured or "Action Needed" in captured
    assert "FINDING" not in captured
    assert "HEADLINE LATENCY" not in captured
    assert "Key Latency" not in captured
    assert "METRIC DEFINITIONS" not in captured
    assert "ACTION REQUIRED" not in captured
    assert "Under " in captured or "Over " in captured or "No Results" in captured
