"""Focused contracts for the project runner and mandatory live metrics."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

CLIENT_ROOT = Path(__file__).resolve().parents[2]


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_live_junit(path: Path, *, skip_required: bool) -> None:
    skipped = '<skipped message="server unavailable" />' if skip_required else ""
    path.write_text(
        (
            '<testsuite tests="3">'
            '<testcase name="test_live_single_server_result_transfer_time">'
            f"{skipped}</testcase>"
            '<testcase name="test_live_single_server_burst_transfer_time">'
            f"{skipped}</testcase>"
            '<testcase name="test_live_multi_server_fleet_transfer_time">'
            '<skipped message="fleet not configured" /></testcase>'
            "</testsuite>"
        ),
        encoding="utf-8",
    )


def test_live_runner_requires_mandatory_benchmarks(tmp_path, monkeypatch):
    runner = _load_module("ijt_performance_project_runner", CLIENT_ROOT / "run_all_tests.py")
    runner._RESULTS_DIR = tmp_path

    def successful_run(*args, **kwargs):
        _write_live_junit(tmp_path / "perf-live.xml", skip_required=False)
        return subprocess.CompletedProcess(args[0], 0, "", "")

    monkeypatch.setattr(runner.subprocess, "run", successful_run)
    result = runner._step_live_tests()

    assert result.ok is True
    assert result.note == "Passed"


def test_live_runner_rejects_skipped_mandatory_benchmarks(tmp_path, monkeypatch):
    runner = _load_module("ijt_performance_project_runner_skipped", CLIENT_ROOT / "run_all_tests.py")
    runner._RESULTS_DIR = tmp_path

    def skipped_run(*args, **kwargs):
        _write_live_junit(tmp_path / "perf-live.xml", skip_required=True)
        return subprocess.CompletedProcess(args[0], 0, "3 skipped", "")

    monkeypatch.setattr(runner.subprocess, "run", skipped_run)
    result = runner._step_live_tests()

    assert result.ok is False
    assert result.note == "Mandatory single-server benchmarks did not run"


def test_mandatory_live_metrics_require_nonzero_samples(tmp_path):
    live_tests = _load_module(
        "ijt_performance_live_contract",
        CLIENT_ROOT / "tests" / "live" / "test_performance_runner.py",
    )
    report = tmp_path / "metrics.json"
    report.write_text(
        json.dumps({"statistics": {"total_result_transfer_time_ms": {"count": 0}}}),
        encoding="utf-8",
    )

    try:
        live_tests._read_total_stats(str(report))
    except AssertionError as exc:
        assert "produced no total_result_transfer_time_ms statistics" in str(exc)
    else:
        raise AssertionError("zero-sample live report was accepted")


def test_extract_pytest_summary():
    runner = _load_module("ijt_performance_project_runner_summary", CLIENT_ROOT / "run_all_tests.py")
    assert runner._extract_pytest_summary("=== 108 passed in 12.34s ===") == "108 passed in 12.34s"
    assert (
        runner._extract_pytest_summary("=== 2 passed, 1 skipped, 1 warning in 5.67s ===")
        == "2 passed, 1 skipped in 5.67s"
    )
    assert runner._extract_pytest_summary("no summary line here") == "Passed"
