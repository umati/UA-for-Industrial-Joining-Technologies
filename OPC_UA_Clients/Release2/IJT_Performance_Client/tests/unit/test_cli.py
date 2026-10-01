"""
Unit tests for CLI parser, argument overrides, and execution workflow.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from src.cli import build_parser, main
from src.results import LatencySample


def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["--config", "profiles/single_server.yaml"])
    assert args.config == "profiles/single_server.yaml"
    assert args.junit == "test-results/junit-perf.xml"
    assert args.verbose is False


def test_build_parser_overrides():
    parser = build_parser()
    args = parser.parse_args(
        [
            "--endpoints",
            "opc.tcp://s1:4840,opc.tcp://s2:4840",
            "--duration",
            "30.0",
            "--samples",
            "100",
            "--burst",
            "5",
            "--mode",
            "both",
            "--require-full-coverage",
            "--fail-p90",
            "45.0",
            "--markdown",
            "summary.md",
            "--json",
            "metrics.json",
            "--workers",
            "8",
            "--verbose",
        ]
    )
    assert args.endpoints == "opc.tcp://s1:4840,opc.tcp://s2:4840"
    assert args.duration == 30.0
    assert args.samples == 100
    assert args.burst == 5
    assert args.mode == "both"
    assert args.require_full_coverage is True
    assert args.fail_p90 == 45.0
    assert args.markdown == "summary.md"
    assert args.json == "metrics.json"
    assert args.workers == 8
    assert args.verbose is True


def test_main_successful_execution(tmp_path):
    junit_path = str(tmp_path / "junit.xml")
    md_path = str(tmp_path / "summary.md")
    json_path = str(tmp_path / "metrics.json")

    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://localhost:40451",
        network_transport_time_ms=10.0,
        server_processing_time_ms=15.0,
        total_result_transfer_time_ms=25.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.stop.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://localhost:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(
            [
                "--endpoints",
                "opc.tcp://localhost:40451",
                "--duration",
                "1.0",
                "--junit",
                junit_path,
                "--markdown",
                md_path,
                "--json",
                json_path,
            ]
        )

        assert exit_code == 0
        mock_pool.start.assert_called_once()
        mock_pool.collect_samples.assert_called_once()
        mock_pool.stop.assert_called_once()


def test_main_sla_breach_returns_nonzero(tmp_path):
    junit_path = str(tmp_path / "junit.xml")
    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://localhost:40451",
        network_transport_time_ms=80.0,
        total_result_transfer_time_ms=120.0,
        delivery_time_ms=120.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://localhost:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        # Request fail-p90 of 50ms when sample is 120ms
        exit_code = main(
            [
                "--endpoints",
                "opc.tcp://localhost:40451",
                "--duration",
                "1.0",
                "--fail-p90",
                "50.0",
                "--junit",
                junit_path,
            ]
        )

        assert exit_code == 1


def test_main_module_execution():
    from src import __main__ as perf_main
    from src import cli

    with patch.object(perf_main, "main", return_value=0), pytest.raises(SystemExit) as exc:
        perf_main.sys.exit(perf_main.main())
    assert exc.value.code == 0

    with patch.object(cli, "main", return_value=0), pytest.raises(SystemExit) as exc2:
        cli.sys.exit(cli.main())
    assert exc2.value.code == 0


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_package_dunder_main():
    import runpy

    with (
        patch("sys.argv", ["perf-client", "--duration", "0.01"]),
        patch("src.cli.main", return_value=0),
        pytest.raises(SystemExit) as exc,
    ):
        runpy.run_module("src", run_name="__main__")
    assert exc.value.code == 0


def test_main_coverage_failure_and_config_loading(tmp_path):
    # Test --config, overrides, and coverage failure path
    profile = tmp_path / "test_prof.yaml"
    profile.write_text(
        """
meta:
  name: "CLI Profile"
fleet:
  endpoints:
    - "opc.tcp://localhost:40451"
execution:
  mode: "passive"
  duration_seconds: 1.0
""",
        encoding="utf-8",
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = []
        mock_pool.verify_coverage.return_value = (False, "Missing endpoint samples")
        mock_pool.connected_endpoints = set()
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(
            [
                "--config",
                str(profile),
                "--samples",
                "50",
                "--burst",
                "2",
                "--mode",
                "both",
                "--require-full-coverage",
                "--junit",
                str(tmp_path / "junit.xml"),
                "--markdown",
                str(tmp_path / "summary.md"),
            ]
        )
        assert exit_code == 1


def test_main_default_endpoint_fallback(tmp_path):
    # Test main() with no config and no endpoints provided (falls back to default localhost)
    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_sample = LatencySample(
            1, "opc.tcp://localhost:40451", network_transport_time_ms=5.0, total_result_transfer_time_ms=10.0
        )
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://localhost:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(["--duration", "0.1", "--junit", str(tmp_path / "junit.xml")])
        assert exit_code == 0
        assert mock_pool_cls.call_args[1]["endpoints"] == ["opc.tcp://localhost:40451"]


def test_cli_module_entrypoint():
    import runpy
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        with patch("sys.argv", ["ijt-perf", "--help"]), pytest.raises(SystemExit) as exc:
            runpy.run_module("src.cli", run_name="__main__", alter_sys=False)
    assert exc.value.code == 0


def test_main_skip_clock_skew_flag(tmp_path):
    """Exercises the --skip-clock-skew CLI flag (cli.py line 139)."""
    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://localhost:40451",
        network_transport_time_ms=5.0,
        total_result_transfer_time_ms=10.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://localhost:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(
            [
                "--endpoints",
                "opc.tcp://localhost:40451",
                "--duration",
                "0.1",
                "--skip-clock-skew",
                "--junit",
                str(tmp_path / "junit.xml"),
            ]
        )
        assert exit_code == 0
        # Verify the skip_clock_skew flag was forwarded to the pool
        assert mock_pool_cls.call_args[1]["skip_clock_skew"] is True


def test_main_allow_partial_coverage_flag(tmp_path):
    """Exercises the --allow-partial-coverage CLI flag."""
    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://localhost:40451",
        network_transport_time_ms=5.0,
        total_result_transfer_time_ms=10.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://localhost:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(
            [
                "--endpoints",
                "opc.tcp://localhost:40451",
                "--duration",
                "0.1",
                "--allow-partial-coverage",
                "--junit",
                str(tmp_path / "junit.xml"),
            ]
        )
        assert exit_code == 0
        assert mock_pool_cls.call_args[1]["require_full_coverage"] is False


def test_main_mutually_exclusive_coverage_flags():
    """Verify specifying both --require-full-coverage and --allow-partial-coverage raises parser error."""
    with pytest.raises(SystemExit):
        main(
            [
                "--endpoints",
                "opc.tcp://localhost:40451",
                "--require-full-coverage",
                "--allow-partial-coverage",
            ]
        )


def test_cli_version_flag(capsys):
    """Verify --version prints package version and exits."""
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "1.0.0" in captured.out or "1.0.0" in captured.err


def test_main_env_var_fallback(monkeypatch, tmp_path):
    """Verify environment variables are used when --endpoints and --config are omitted."""
    monkeypatch.setenv("OPCUA_FLEET_ENDPOINTS", "opc.tcp://fleet1:40451,opc.tcp://fleet2:40451")

    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://fleet1:40451",
        network_transport_time_ms=5.0,
        total_result_transfer_time_ms=10.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://fleet1:40451", "opc.tcp://fleet2:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(["--duration", "0.1", "--junit", str(tmp_path / "junit.xml")])
        assert exit_code == 0
        endpoints_passed = mock_pool_cls.call_args[1]["endpoints"]
        assert endpoints_passed == ["opc.tcp://fleet1:40451", "opc.tcp://fleet2:40451"]


def test_main_env_var_single_fallback(monkeypatch, tmp_path):
    """Verify single OPCUA_SERVER_URL is used when OPCUA_FLEET_ENDPOINTS is not set."""
    monkeypatch.delenv("OPCUA_FLEET_ENDPOINTS", raising=False)
    monkeypatch.setenv("OPCUA_SERVER_URL", "opc.tcp://single:40451")

    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://single:40451",
        network_transport_time_ms=5.0,
        total_result_transfer_time_ms=10.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://single:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(["--duration", "0.1", "--junit", str(tmp_path / "junit.xml")])
        assert exit_code == 0
        endpoints_passed = mock_pool_cls.call_args[1]["endpoints"]
        assert endpoints_passed == ["opc.tcp://single:40451"]


def test_main_workers_flag(tmp_path):
    """Verify -w / --workers flag sets max_worker_processes on the pool."""
    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://single:40451",
        network_transport_time_ms=5.0,
        total_result_transfer_time_ms=10.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 8
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://single:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(["-w", "8", "--duration", "0.1", "--junit", str(tmp_path / "junit.xml")])
        assert exit_code == 0
        workers_passed = mock_pool_cls.call_args[1]["max_workers"]
        assert workers_passed == 8


def test_main_env_var_workers_fallback(monkeypatch, tmp_path):
    """Verify OPCUA_WORKERS env var is applied when --workers is omitted."""
    monkeypatch.setenv("OPCUA_WORKERS", "6")

    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://single:40451",
        network_transport_time_ms=5.0,
        total_result_transfer_time_ms=10.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 6
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://single:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(["--duration", "0.1", "--junit", str(tmp_path / "junit.xml")])
        assert exit_code == 0
        workers_passed = mock_pool_cls.call_args[1]["max_workers"]
        assert workers_passed == 6


def test_main_env_var_workers_invalid_ignored(monkeypatch, tmp_path):
    """Verify non-integer OPCUA_WORKERS is ignored gracefully."""
    monkeypatch.setenv("OPCUA_WORKERS", "not-a-number")

    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://single:40451",
        network_transport_time_ms=5.0,
        total_result_transfer_time_ms=10.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://single:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(["--duration", "0.1", "--junit", str(tmp_path / "junit.xml")])
        assert exit_code == 0
        workers_passed = mock_pool_cls.call_args[1]["max_workers"]
        assert workers_passed is None


def test_main_burst_delay_flag(tmp_path):
    """Verify --burst-delay flag sets pool burst_delay."""
    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://single:40451",
        network_transport_time_ms=5.0,
        total_result_transfer_time_ms=10.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://single:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(["--duration", "0.1", "--burst-delay", "0.25", "--junit", str(tmp_path / "junit.xml")])
        assert exit_code == 0
        burst_delay_passed = mock_pool_cls.call_args[1]["burst_delay"]
        assert burst_delay_passed == 0.25


def test_main_env_var_burst_delay(monkeypatch, tmp_path):
    """Verify OPCUA_BURST_DELAY env var is applied when --burst-delay is omitted."""
    monkeypatch.setenv("OPCUA_BURST_DELAY", "0.5")

    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://single:40451",
        network_transport_time_ms=5.0,
        total_result_transfer_time_ms=10.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://single:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(["--duration", "0.1", "--junit", str(tmp_path / "junit.xml")])
        assert exit_code == 0
        burst_delay_passed = mock_pool_cls.call_args[1]["burst_delay"]
        assert burst_delay_passed == 0.5


def test_main_env_var_burst_delay_invalid_ignored(monkeypatch, tmp_path):
    """Verify invalid OPCUA_BURST_DELAY env var falls back to default 1.0."""
    monkeypatch.setenv("OPCUA_BURST_DELAY", "not-a-float")

    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://single:40451",
        network_transport_time_ms=5.0,
        total_result_transfer_time_ms=10.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://single:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(["--duration", "0.1", "--junit", str(tmp_path / "junit.xml")])
        assert exit_code == 0
        burst_delay_passed = mock_pool_cls.call_args[1]["burst_delay"]
        assert burst_delay_passed == 1.0


def test_main_csv_report_export(tmp_path):
    """Verify --csv flag generates a CSV report with sample rows."""
    csv_file = tmp_path / "report.csv"
    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://single:40451",
        network_transport_time_ms=5.2,
        server_processing_time_ms=12.1,
        total_result_transfer_time_ms=17.3,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://single:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(["--duration", "0.1", "--csv", str(csv_file), "--junit", str(tmp_path / "junit.xml")])
        assert exit_code == 0
        assert csv_file.exists()
        content = csv_file.read_text(encoding="utf-8")
        assert "sample_id,endpoint" in content
        assert "opc.tcp://single:40451" in content
        assert "17.30" in content


def test_main_allow_partial_samples_flag(tmp_path):
    """Verify --allow-partial-samples flag passes allow_partial_samples=True to pool.verify_coverage."""
    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://single:40451",
        network_transport_time_ms=5.0,
        server_processing_time_ms=10.0,
        total_result_transfer_time_ms=15.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://single:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(
            ["--duration", "0.1", "--samples", "10", "--allow-partial-samples", "--junit", str(tmp_path / "junit.xml")]
        )
        assert exit_code == 0
        call_kwargs = mock_pool.verify_coverage.call_args[1]
        assert call_kwargs["target_sample_count"] == 10
        assert call_kwargs["allow_partial_samples"] is True


def test_main_samples_per_endpoint_and_verbose_flag(tmp_path):
    """Verify --samples-per-endpoint and --verbose flags are passed to pool."""
    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://single:40451",
        network_transport_time_ms=5.0,
        server_processing_time_ms=10.0,
        total_result_transfer_time_ms=15.0,
    )

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://single:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        exit_code = main(
            [
                "--duration",
                "0.1",
                "--samples-per-endpoint",
                "5",
                "--verbose",
                "--junit",
                str(tmp_path / "junit.xml"),
            ]
        )
        assert exit_code == 0
        pool_init_kwargs = mock_pool_cls.call_args[1]
        assert pool_init_kwargs["verbose"] is True
        coverage_kwargs = mock_pool.verify_coverage.call_args[1]
        assert coverage_kwargs["target_samples_per_endpoint"] == 5


def test_main_json_exports_fleet_integrity_summary(tmp_path):
    import json

    from src.engine import FleetIntegritySummary

    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://single:40451",
        network_transport_time_ms=5.0,
        server_processing_time_ms=10.0,
        total_result_transfer_time_ms=15.0,
    )
    json_path = tmp_path / "metrics.json"

    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = [mock_sample]
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://single:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []
        mock_pool.fleet_integrity = FleetIntegritySummary(
            total_received=1,
            total_valid=1,
            total_incomplete=0,
            total_duplicate=0,
            total_unmatched=0,
            total_dropped=0,
            passed=True,
            failure_reasons=[],
        )

        exit_code = main(
            [
                "--duration",
                "0.1",
                "--json",
                str(json_path),
            ]
        )
        assert exit_code == 0
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "integrity_summary" in data["metadata"]
        summary = data["metadata"]["integrity_summary"]
        assert summary["evaluated"] is True
        assert summary["passed"] is True
        assert summary["total_valid"] == 1
        assert summary["endpoints"] == []


def test_integrity_summary_json_has_no_optimistic_defaults():
    from src.cli import _integrity_summary_json
    from src.engine import EndpointIntegrity, FleetIntegritySummary

    not_run = _integrity_summary_json(None)
    assert not_run["evaluated"] is False
    assert not_run["passed"] is False

    fi = FleetIntegritySummary(total_received=2, total_valid=1, total_incomplete=1, passed=False)
    fi.endpoints["opc.tcp://a:1"] = EndpointIntegrity(endpoint="opc.tcp://a:1", received_count=2, dropped_count=3)
    fi.failure_reasons.append("1 samples failed validation")
    data = _integrity_summary_json(fi)
    assert data["evaluated"] is True
    assert data["passed"] is False
    assert data["endpoints"][0]["endpoint"] == "opc.tcp://a:1"
    assert data["endpoints"][0]["dropped_count"] == 3
    assert data["failure_reasons"] == ["1 samples failed validation"]


def test_main_clock_tolerance_flag_and_default(tmp_path):
    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://single:40451",
        network_transport_time_ms=5.0,
        total_result_transfer_time_ms=10.0,
    )
    for argv, expected in (([], 1000.0), (["--clock-tolerance-ms", "250"], 250.0)):
        with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
            mock_pool = MagicMock()
            mock_pool_cls.return_value = mock_pool
            mock_pool._num_workers_started = 1
            mock_pool.collect_samples.return_value = [mock_sample]
            mock_pool.verify_coverage.return_value = (True, "Coverage OK")
            mock_pool.connected_endpoints = {"opc.tcp://single:40451"}
            mock_pool.failed_endpoints = {}
            mock_pool.worker_errors = []
            exit_code = main(["--duration", "0.1", *argv, "--junit", str(tmp_path / "junit.xml")])
            assert exit_code == 0
            assert mock_pool_cls.call_args[1]["clock_tolerance_ms"] == expected


def test_main_rejects_negative_clock_tolerance(tmp_path):
    with patch("src.cli.OpcUaClientPool") as mock_pool_cls, pytest.raises(SystemExit) as exc_info:
        main(["--duration", "0.1", "--clock-tolerance-ms", "-5", "--junit", str(tmp_path / "j.xml")])
    assert exc_info.value.code == 2
    mock_pool_cls.assert_not_called()


def _run_sla(tmp_path, samples, extra_args, endpoint="opc.tcp://localhost:40451"):
    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = samples
        mock_pool.stop.return_value = samples
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        mock_pool.connected_endpoints = {"opc.tcp://localhost:40451"}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []
        junit = tmp_path / "junit.xml"
        code = main(["--endpoints", endpoint, "--junit", str(junit), *extra_args])
        return code, junit.read_text(encoding="utf-8")


def test_main_client_ready_sla_is_separate_from_delivery_sla(tmp_path):
    sample = LatencySample(sample_id=1, endpoint="e", delivery_time_ms=40.0, client_ready_time_ms=90.0)
    code, junit = _run_sla(tmp_path, [sample], ["--fail-p90", "50", "--fail-p90-client-ready", "60"])
    assert code == 1
    assert "90%-under client-ready time (P90) (90.0ms) exceeded SLA threshold (60.0ms)" in junit
    assert "delivery time (P90)" not in junit

    code, _ = _run_sla(tmp_path, [sample], ["--fail-p90", "50", "--fail-p90-client-ready", "100"])
    assert code == 0


def test_main_sla_ignores_invalid_results(tmp_path):
    good = LatencySample(sample_id=1, endpoint="e", delivery_time_ms=10.0, client_ready_time_ms=12.0)
    bad = LatencySample(
        sample_id=2, endpoint="e", delivery_time_ms=999.0, client_ready_time_ms=999.0, integrity_status="INCOMPLETE"
    )
    code, junit = _run_sla(tmp_path, [good, bad], ["--fail-p90", "50", "--fail-p90-client-ready", "50"])
    assert code == 0
    assert 'perf_valid_sample_count" value="1"' in junit
    assert 'perf_p90_delivery_time_ms" value="10.00"' in junit


@pytest.mark.parametrize(
    ("endpoint", "hint_expected"), [("opc.tcp://localhost:40451", True), ("opc.tcp://plc-7:4840", False)]
)
def test_main_sla_breach_hints_at_single_machine_limit_only_for_local_runs(tmp_path, caplog, endpoint, hint_expected):
    sample = LatencySample(sample_id=1, endpoint=endpoint, delivery_time_ms=180.0, client_ready_time_ms=190.0)
    with caplog.at_level(logging.WARNING, logger="ijt_performance_client"):
        code, junit = _run_sla(tmp_path, [sample], ["--fail-p90", "150"], endpoint=endpoint)
    assert code == 1
    assert ("SLA HINT" in caplog.text) is hint_expected
    assert "SLA HINT" not in junit


@pytest.mark.parametrize("value", ["0", "-5", "nan"])
def test_main_rejects_invalid_client_ready_sla(value):
    with pytest.raises(SystemExit) as exc:
        main(["--endpoints", "opc.tcp://localhost:40451", "--fail-p90-client-ready", value])
    assert exc.value.code == 2


def test_main_settle_timeout_flag(tmp_path):
    with patch("src.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = []
        mock_pool.stop.return_value = []
        mock_pool.verify_coverage.return_value = (True, "Coverage OK")
        main(["--duration", "0.1", "--settle-timeout", "2.5", "--junit", str(tmp_path / "junit.xml")])
        assert mock_pool_cls.call_args[1]["settle_timeout_s"] == 2.5

    with pytest.raises(SystemExit) as exc:
        main(["--duration", "0.1", "--settle-timeout", "-1", "--junit", str(tmp_path / "junit.xml")])
    assert exc.value.code == 2
