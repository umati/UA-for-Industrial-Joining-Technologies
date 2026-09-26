"""
Unit tests for CLI parser, argument overrides, and execution workflow.
"""

from unittest.mock import MagicMock, patch

import pytest

from ijt_performance_client.cli import build_parser, main
from ijt_performance_client.result_transfer_latency import LatencySample


def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["--config", "profiles/single_server.yaml"])
    assert args.config == "profiles/single_server.yaml"
    assert args.junit == "junit-perf.xml"
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

    with patch("ijt_performance_client.cli.OpcUaClientPool") as mock_pool_cls:
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
    )

    with patch("ijt_performance_client.cli.OpcUaClientPool") as mock_pool_cls:
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
    from ijt_performance_client import __main__ as perf_main
    from ijt_performance_client import cli

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
        patch("ijt_performance_client.cli.main", return_value=0),
        pytest.raises(SystemExit) as exc,
    ):
        runpy.run_module("ijt_performance_client", run_name="__main__")
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

    with patch("ijt_performance_client.cli.OpcUaClientPool") as mock_pool_cls:
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
    with patch("ijt_performance_client.cli.OpcUaClientPool") as mock_pool_cls:
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
            runpy.run_module("ijt_performance_client.cli", run_name="__main__", alter_sys=False)
    assert exc.value.code == 0


def test_main_skip_clock_skew_flag(tmp_path):
    """Exercises the --skip-clock-skew CLI flag (cli.py line 139)."""
    mock_sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://localhost:40451",
        network_transport_time_ms=5.0,
        total_result_transfer_time_ms=10.0,
    )

    with patch("ijt_performance_client.cli.OpcUaClientPool") as mock_pool_cls:
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
