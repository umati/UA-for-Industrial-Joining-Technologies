"""
Unit tests for console table reporter.
"""

from ijt_performance_client.attribution import DiagnosticVerdict
from ijt_performance_client.reporters.console import print_console_report
from ijt_performance_client.result_transfer_latency import LatencySample


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
    assert "Total Samples Received: 0" in captured.out
    assert "NO_DATA" in captured.out
    assert "Test warning" in captured.out


def test_print_console_report_with_samples(capsys):
    verdict = DiagnosticVerdict(
        primary_bottleneck="NONE (OPC UA PIPELINE HEALTHY)",
        headline="Healthy",
        explanation="All within limits",
        recommendation="None",
        metrics_summary={"total_p90_ms": 22.0},
        warnings=[],
    )
    sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://localhost:40451",
        network_transport_time_ms=10.0,
        server_processing_time_ms=12.0,
        total_result_transfer_time_ms=22.0,
    )
    print_console_report([sample], verdict, "TestPoolWithSamples")
    captured = capsys.readouterr()
    assert "IJT PERFORMANCE & SCALE BENCHMARK REPORT: TestPoolWithSamples" in captured.out
    assert "Total Samples Received: 1" in captured.out
    assert "HEALTHY" in captured.out
    assert "22.0ms" in captured.out
