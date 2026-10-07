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
    assert "Results Received         : 0 total" in captured.out
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
    assert "Results Received         : 1 total" in captured.out
    assert "Integrity Audit          : 1 valid (100.0% valid rate)" in captured.out
    assert "HEALTHY" in captured.out
    assert "22.0ms" in captured.out


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
    print_console_report(samples, verdict, "MultiServerFleet")
    captured = capsys.readouterr()
    assert "PER-SERVER BREAKDOWN (2 Servers, VALID delivery time)" in captured.out
    assert "opc.tcp://localhost:40001" in captured.out
    assert "opc.tcp://localhost:40002" in captured.out
    assert "+1.5 ms (server ahead)" in captured.out
    assert "18.5ms" in captured.out
    assert "N/A" in captured.out
    assert "FLEET AGGREGATE SUMMARY (All Servers):" in captured.out


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
    assert "Results Received         : 2 total" in out
    assert "Integrity Audit          : 1 valid (50.0% valid rate)" in out
    assert "Wire Timing Samples      : 1/1 verified (100.0%)" in out
    assert "11.0ms" in out
    assert "999.0" not in out
    assert "BENCHMARK INTEGRITY AUDIT (1 issues detected)" in out
