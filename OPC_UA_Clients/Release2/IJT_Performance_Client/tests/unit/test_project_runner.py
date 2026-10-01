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


def test_runner_phase2_preflight_validation():
    runner = _load_module("ijt_performance_project_runner_preflight", CLIENT_ROOT / "run_all_tests.py")
    parser = runner._build_parser()

    assert runner._validate_phase2_args(parser.parse_args([])) is None
    assert runner._validate_phase2_args(parser.parse_args(["--fleet", "2", "--fleet-start-port", "65534"])) is None
    assert "port range" in runner._validate_phase2_args(
        parser.parse_args(["--fleet", "3", "--fleet-start-port", "65534"])
    )
    assert "port range" in runner._validate_phase2_args(
        parser.parse_args(["--fleet", "1", "--fleet-start-port", "1023"])
    )
    assert "--fleet" in runner._validate_phase2_args(parser.parse_args(["--fleet", "-1"]))
    assert "--workers" in runner._validate_phase2_args(parser.parse_args(["--workers", "33"]))
    assert "--burst-delay" in runner._validate_phase2_args(parser.parse_args(["--burst-delay", "nan"]))


def test_runner_invalid_port_range_exits_before_any_step(monkeypatch):
    runner = _load_module("ijt_performance_project_runner_port_exit", CLIENT_ROOT / "run_all_tests.py")
    monkeypatch.setattr(sys, "argv", ["run_all_tests.py", "--fleet", "3", "--fleet-start-port", "65534"])

    def must_not_run(*args, **kwargs):
        raise AssertionError("no step or simulator may start after invalid arguments")

    monkeypatch.setattr(runner, "_relaunch_under_venv", must_not_run)
    monkeypatch.setattr(runner, "_step_ruff_lint", must_not_run)
    monkeypatch.setattr(runner, "_find_simulator_exe", must_not_run)
    monkeypatch.setattr(runner, "_launch_simulator_on_port", must_not_run)

    assert runner.main() == 1


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


def test_project_runner_parser():
    runner = _load_module("ijt_performance_project_runner_parser", CLIENT_ROOT / "run_all_tests.py")
    parser = runner._build_parser()
    default_p = parser.parse_args([])
    assert default_p.burst_delay is None
    args = parser.parse_args(["--fleet", "50", "-w", "8", "--burst-delay", "0.5"])
    assert args.fleet == 50
    assert args.workers == 8
    assert args.burst_delay == 0.5


def test_run_fleet_parser_and_worker_forwarding():
    fleet_module = _load_module("ijt_performance_run_fleet", CLIENT_ROOT / "run_fleet.py")
    parser = fleet_module.build_parser()

    # Default run: workers must be None so client pool auto-scaling applies
    default_args = parser.parse_args([])
    assert default_args.workers is None
    assert default_args.burst_delay == 1.0

    # Explicit workers flag
    explicit_args = parser.parse_args(["--workers", "12", "--burst-delay", "0.2"])
    assert explicit_args.workers == 12
    assert explicit_args.burst_delay == 0.2


def test_run_fleet_uses_lock_pinned_runtime_venv(monkeypatch):
    fleet_module = _load_module("ijt_performance_run_fleet_venv", CLIENT_ROOT / "run_fleet.py")
    calls: list[tuple] = []

    def fake_relaunch(*args):
        calls.append(args)
        return 7

    monkeypatch.setattr(fleet_module, "_ENV_IS_PRE_ISOLATED", False)
    monkeypatch.setattr(fleet_module, "_inside_venv", lambda venv: False)
    monkeypatch.setattr(fleet_module, "_relaunch_under_venv", fake_relaunch)

    # Invalid arguments fail before any venv is created.
    monkeypatch.setattr(sys, "argv", ["run_fleet.py", "--servers", "0"])
    assert fleet_module.main() == 1
    assert calls == []

    monkeypatch.setattr(sys, "argv", ["run_fleet.py", "--servers", "2"])
    assert fleet_module.main() == 7
    venv, requirements, script = calls[0]
    assert venv == CLIENT_ROOT / ".venv"
    assert [req.name for req in requirements] == ["requirements.txt"]
    assert script.name == "run_fleet.py"


def test_validate_fleet_args():
    import argparse

    fleet_module = _load_module("ijt_performance_run_fleet_val", CLIENT_ROOT / "run_fleet.py")
    validate = fleet_module.validate_fleet_args

    base_args = argparse.Namespace(
        servers=10,
        samples_per_server=5,
        start_port=40001,
        burst_delay=1.0,
        workers=None,
        duration=None,
        settle_timeout=None,
        fail_p90=None,
        fail_p90_client_ready=None,
    )
    assert validate(base_args) is None
    assert "Invalid --servers" in (validate(argparse.Namespace(**{**vars(base_args), "servers": 0})) or "")
    assert "Invalid --samples-per-server" in (
        validate(argparse.Namespace(**{**vars(base_args), "samples_per_server": 0})) or ""
    )
    # Legal upper port bound: 65535 with 1 server is valid
    assert validate(argparse.Namespace(**{**vars(base_args), "start_port": 65535, "servers": 1})) is None
    assert "Invalid port range" in (
        validate(argparse.Namespace(**{**vars(base_args), "start_port": 65535, "servers": 2})) or ""
    )
    assert "Invalid --burst-delay" in (validate(argparse.Namespace(**{**vars(base_args), "burst_delay": -0.1})) or "")
    assert "Invalid --workers" in (validate(argparse.Namespace(**{**vars(base_args), "workers": 0})) or "")
    assert "Invalid --workers" in (validate(argparse.Namespace(**{**vars(base_args), "workers": 33})) or "")
    assert "Invalid --duration" in (validate(argparse.Namespace(**{**vars(base_args), "duration": 0.0})) or "")
    assert validate(argparse.Namespace(**{**vars(base_args), "settle_timeout": 0.0})) is None
    assert "Invalid --settle-timeout" in (
        validate(argparse.Namespace(**{**vars(base_args), "settle_timeout": -1.0})) or ""
    )
    assert "Invalid --fail-p90:" in (validate(argparse.Namespace(**{**vars(base_args), "fail_p90": 0.0})) or "")
    assert "Invalid --fail-p90-client-ready" in (
        validate(argparse.Namespace(**{**vars(base_args), "fail_p90_client_ready": float("nan")})) or ""
    )


def test_fleet_status_lines_carry_log_style_timestamps(capsys) -> None:
    import re

    runner = _load_module("perf_runner_print_status", CLIENT_ROOT / "run_all_tests.py")
    runner._print_status("\n  [fleet] Ready")
    runner._print_status("[fleet] ERROR: boom", file=sys.stderr)
    captured = capsys.readouterr()
    assert re.fullmatch(r"\n  \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \[fleet\] Ready\n", captured.out)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \[fleet\] ERROR: boom\n", captured.err)
