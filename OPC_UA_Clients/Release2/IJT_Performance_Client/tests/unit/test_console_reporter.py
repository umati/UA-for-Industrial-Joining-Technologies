"""
Unit tests for console table reporter.
"""

from src.diagnostics import DiagnosticVerdict
from src.reporters import print_console_report
from src.results import LatencySample


def test_print_console_report_empty(capsys):
    verdict = DiagnosticVerdict(
        primary_bottleneck="NO_DATA",
        headline="No Data",
        explanation="No samples received",
        recommendation="Check setup",
        metrics_summary={},
        warnings=["Test warning"],
    )
    print_console_report([], verdict, "TestPool")
    captured = capsys.readouterr()
    assert "IJT PERFORMANCE & SCALE BENCHMARK REPORT: TestPool" in captured.out
    assert "Servers Tested" in captured.out
    assert "Results Per Server" in captured.out
    assert "Action Needed" in captured.out
    assert "No Results" in captured.out
    assert "Test warning" in captured.out
    assert "FINDING" not in captured.out


def test_print_console_report_with_samples(capsys):
    verdict = DiagnosticVerdict(
        primary_bottleneck="NONE (OPC UA PIPELINE HEALTHY)",
        headline="Healthy",
        explanation="All within limits",
        recommendation="None",
        metrics_summary={"total_p90_ms": 22.0, "delivery_p90_ms": 18.0},
        warnings=[],
    )
    sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://localhost:40451",
        network_transport_time_ms=10.0,
        server_processing_time_ms=12.0,
        total_result_transfer_time_ms=22.0,
        delivery_time_ms=18.0,
    )
    print_console_report([sample], verdict, "TestPoolWithSamples", samples_per_endpoint=1)
    captured = capsys.readouterr()
    assert "IJT PERFORMANCE & SCALE BENCHMARK REPORT: TestPoolWithSamples" in captured.out
    assert "Results Per Server" in captured.out
    assert "1 servers × 1 each" in captured.out or "1 each" in captured.out
    assert "Results Used For Stats" in captured.out
    assert "Under 100 ms" in captured.out
    assert "No Action Needed" in captured.out
    assert "Run Size" in captured.out
    assert "Result Latency" in captured.out
    assert "HEADLINE LATENCY" not in captured.out
    assert "Key Latency" not in captured.out
    assert "FINDING" not in captured.out
    assert "METRIC DEFINITIONS" not in captured.out


def test_print_console_report_per_server(capsys):
    verdict = DiagnosticVerdict(
        primary_bottleneck="NONE (OPC UA PIPELINE HEALTHY)",
        headline="Healthy",
        explanation="Multi-server fleet",
        recommendation="None",
        metrics_summary={},
        warnings=[],
    )
    samples = [
        LatencySample(
            sample_id=1,
            endpoint="opc.tcp://localhost:40001",
            network_transport_time_ms=10.0,
            server_processing_time_ms=12.0,
            total_result_transfer_time_ms=22.0,
            delivery_time_ms=18.5,
            clock_skew_ms=1.5,
        ),
        LatencySample(
            sample_id=2,
            endpoint="opc.tcp://localhost:40002",
            network_transport_time_ms=None,
            server_processing_time_ms=None,
            total_result_transfer_time_ms=None,
        ),
    ]
    print_console_report(samples, verdict, "MultiServerFleet", samples_per_endpoint=1)
    captured = capsys.readouterr()
    assert "Detail — Per Server (2 Servers)" in captured.out
    assert "opc.tcp://localhost:40001" in captured.out
    assert "opc.tcp://localhost:40002" in captured.out
    assert "+1.5 ms (server ahead)" in captured.out
    assert "18.5ms" in captured.out
    assert "N/A" in captured.out
    assert "Results Per Server" in captured.out
    lines = captured.out.splitlines()
    header_idx = next(i for i, line in enumerate(lines) if "For Stats" in line)
    assert len(lines[header_idx]) == len(lines[header_idx - 1])
    assert len(lines[header_idx]) == len(lines[header_idx + 1])


def test_print_console_report_excludes_invalid_results_from_statistics(capsys):
    verdict = DiagnosticVerdict(
        primary_bottleneck="X", headline="h", explanation="e", recommendation="r", metrics_summary={}, warnings=[]
    )
    samples = [
        LatencySample(sample_id=1, endpoint="opc.tcp://a:4840", delivery_time_ms=11.0, timing_source="wire"),
        LatencySample(
            sample_id=2,
            endpoint="opc.tcp://a:4840",
            delivery_time_ms=999.0,
            integrity_status="INCOMPLETE",
            integrity_reason="missing trace",
        ),
    ]
    print_console_report(samples, verdict, "Mixed")
    out = capsys.readouterr().out
    assert "Total Results" in out
    assert "Results Used For Stats" in out
    assert "50.0%" in out
    assert "Wire Timing" in out
    assert "11.0" in out
    assert "999.0" not in out
    assert "Integrity Audit (1 Issues)" in out
    assert "Action Needed" in out


def test_enable_ansi_windows():
    from unittest.mock import MagicMock, patch

    from src.reporters.console import _enable_ansi_windows

    res = _enable_ansi_windows()
    assert isinstance(res, bool)

    with patch.dict("sys.modules", {"ctypes": MagicMock(spec=[])}):
        assert _enable_ansi_windows() is False

    mock_bad = MagicMock()
    mock_bad.kernel32.GetConsoleMode.side_effect = RuntimeError("mock error")
    with patch("ctypes.windll", mock_bad, create=True):
        assert _enable_ansi_windows() is False

    mock_good = MagicMock()
    mock_good.kernel32.GetConsoleMode.return_value = 1
    with patch("ctypes.windll", mock_good, create=True):
        assert _enable_ansi_windows() is True


def test_safe_print_branches(capsys, monkeypatch):
    import sys
    from unittest.mock import MagicMock

    from src.reporters.console import _safe_print

    _safe_print("test regular print")
    out = capsys.readouterr().out
    assert "test regular print" in out

    mock_stdout = MagicMock()
    mock_stdout.encoding = "cp1252"
    mock_stdout.reconfigure = MagicMock()
    monkeypatch.setattr(sys, "stdout", mock_stdout)
    _safe_print("test reconfigure")
    mock_stdout.reconfigure.assert_called_once_with(encoding="utf-8")

    mock_stdout.reconfigure.side_effect = RuntimeError("cannot reconfigure")
    _safe_print("test reconfigure exception")


def test_safe_print_unicode_encode_error(capsys, monkeypatch):
    from src.reporters.console import _safe_print

    calls = []
    real_print = print

    def failing_print(text=""):
        if not calls:
            calls.append(1)
            raise UnicodeEncodeError("ascii", text, 0, 1, "test")
        real_print(text)

    monkeypatch.setattr("builtins.print", failing_print)
    _safe_print("unicode chars: üñîçødé")
    out = capsys.readouterr().out
    assert "unicode chars" in out


def test_print_console_report_more_than_ten_problematic_endpoints(capsys):
    verdict = DiagnosticVerdict(
        primary_bottleneck="TEST", headline="h", explanation="e", recommendation="r", metrics_summary={}, warnings=[]
    )
    samples = [
        LatencySample(sample_id=i, endpoint=f"opc.tcp://server{i}:4840", integrity_status="INCOMPLETE")
        for i in range(12)
    ]
    print_console_report(samples, verdict, "FleetWithManyIssues")
    out = capsys.readouterr().out
    assert "Showing 10 of 12 affected endpoints" in out


def test_console_columns_follow_the_longest_cell(capsys):
    verdict = DiagnosticVerdict(
        primary_bottleneck="LOCAL_HOST_CPU",
        headline="Shared computer",
        explanation="colocated",
        recommendation="None",
        metrics_summary={"delivery_p90_ms": 175.1},
        warnings=[],
    )
    long_endpoint = "opc.tcp://joining-controller.factory.example:48400"
    samples = []
    for index in range(12):
        endpoint = long_endpoint if index < 6 else "opc.tcp://127.0.0.1:41001"
        samples.append(
            LatencySample(
                sample_id=index,
                endpoint=endpoint,
                delivery_time_ms=8296.2 + index,
                total_result_transfer_time_ms=8388.9 + index,
                joining_duration_ms=51.7,
                clock_skew_ms=12345.6,
                timing_source="wire",
            )
        )
    print_console_report(samples, verdict, "LongValues", samples_per_endpoint=6, timing={"workers_reported": 20})
    out = capsys.readouterr().out
    assert long_endpoint in out
    assert "8301.2ms" in out
    assert "+12345.6 ms (server ahead)" in out
    box_lines = [line for line in out.splitlines() if line.startswith(("  \u2502", "  \u250c", "  \u2514", "  \u251c"))]
    assert box_lines
    assert len(set(map(len, box_lines))) == 1
    lines = out.splitlines()
    header_idx = next(i for i, line in enumerate(lines) if "For Stats" in line)
    assert len(lines[header_idx]) == len(lines[header_idx - 1]) == len(lines[header_idx + 1])


def test_local_host_cpu_is_information_not_action(capsys):
    verdict = DiagnosticVerdict(
        primary_bottleneck="LOCAL_HOST_CPU",
        headline="Client and Servers Share This Machine",
        explanation="colocated",
        recommendation="Move simulators",
        metrics_summary={"delivery_p90_ms": 113.0},
        warnings=[],
    )
    samples = [
        LatencySample(
            sample_id=i,
            endpoint=f"opc.tcp://127.0.0.1:{41000 + (i % 3)}",
            delivery_time_ms=113.0,
            total_result_transfer_time_ms=128.0,
            timing_source="wire",
        )
        for i in range(6)
    ]
    print_console_report(samples, verdict, "Colocated", samples_per_endpoint=2)
    out = capsys.readouterr().out
    assert "Under 200 ms" in out
    assert "No Action Needed" in out
    assert "Client and servers were on one computer." in out
    assert "ACTION NEEDED" not in out
    assert "ACTION REQUIRED" not in out
    assert "Results Per Server" in out
    assert "2" in out
    assert "3 servers × 2 each" in out
    assert "METRIC DEFINITIONS" not in out
    assert "FINDING" not in out
