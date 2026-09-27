"""
Unit tests for JUnit, Markdown, and JSON reporting exporters.
"""

from src.diagnostics import DiagnosticVerdict
from src.reporters import (
    export_json_report,
    generate_markdown_report,
    write_junit_xml,
)


def test_junit_reporter_handles_empty_samples(tmp_path):
    junit_file = tmp_path / "empty_junit.xml"
    verdict = DiagnosticVerdict(
        primary_bottleneck="NO_DATA",
        headline="Zero Samples",
        explanation="No samples",
        recommendation="Check setup",
        metrics_summary={},
        warnings=[],
    )

    write_junit_xml(
        output_path=junit_file,
        samples=[],
        verdict=verdict,
        pool_name="TestPool",
        coverage_valid=False,
        coverage_msg="No samples received",
    )

    assert junit_file.is_file()
    content = junit_file.read_text(encoding="utf-8")
    assert 'failures="2"' in content  # Coverage failure + no samples
    assert 'perf_mean_total_ms" value="0.00"' in content


def test_markdown_and_json_reporters_empty_samples(tmp_path):
    verdict = DiagnosticVerdict(
        primary_bottleneck="NO_DATA",
        headline="Zero Samples",
        explanation="No samples",
        recommendation="Check setup",
        metrics_summary={},
        warnings=[],
    )
    md = generate_markdown_report([], verdict, "TestPool")
    assert "Zero Samples" in md

    json_file = tmp_path / "report.json"
    export_json_report(json_file, [], verdict, "TestPool")
    assert json_file.is_file()


def test_markdown_report_with_warnings_and_samples():
    from src.results import LatencySample

    verdict = DiagnosticVerdict(
        primary_bottleneck="NETWORK_OR_TRANSPORT",
        headline="Network Latency",
        explanation="Wire transit delay",
        recommendation="Inspect switch",
        metrics_summary={"total_p90_ms": 60.0},
        warnings=["Switch backlog detected", "High packet jitter"],
    )
    sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://localhost:40451",
        network_transport_time_ms=50.0,
        server_processing_time_ms=10.0,
        joining_duration_ms=500.0,
        total_result_transfer_time_ms=60.0,
    )
    md = generate_markdown_report([sample], verdict, "WarningPool")
    assert "IJT Performance & Scale Benchmark: WarningPool" in md
    assert "Switch backlog detected" in md
    assert "High packet jitter" in md


def test_junit_reporter_with_worker_errors(tmp_path):
    junit_file = tmp_path / "worker_err_junit.xml"
    verdict = DiagnosticVerdict(
        primary_bottleneck="NETWORK_OR_TRANSPORT",
        headline="Network issue",
        explanation="Detail",
        recommendation="Fix",
        metrics_summary={},
        warnings=[],
    )
    write_junit_xml(
        output_path=junit_file,
        samples=[],
        verdict=verdict,
        pool_name="ErrPool",
        coverage_valid=True,
        coverage_msg="Coverage OK",
        failed_threshold_msg="P90 latency breached SLA",
        worker_errors=["Connection refused on port 40451"],
    )
    content = junit_file.read_text(encoding="utf-8")
    assert "Worker Errors: Connection refused on port 40451" in content
    assert "P90 latency breached SLA" in content


def test_markdown_and_json_per_server_reporting(tmp_path):
    import json

    from src.results import LatencySample

    verdict = DiagnosticVerdict(
        primary_bottleneck="NONE (OPC UA PIPELINE HEALTHY)",
        headline="Healthy Fleet",
        explanation="All endpoints nominal",
        recommendation="None",
        metrics_summary={},
        warnings=[],
    )
    samples = [
        LatencySample(
            sample_id=1,
            endpoint="opc.tcp://127.0.0.1:40001",
            total_result_transfer_time_ms=50.0,
            network_transport_time_ms=40.0,
            server_processing_time_ms=10.0,
            clock_skew_ms=-2.0,
        ),
        LatencySample(
            sample_id=2,
            endpoint="opc.tcp://127.0.0.1:40002",
            total_result_transfer_time_ms=60.0,
            network_transport_time_ms=50.0,
            server_processing_time_ms=10.0,
            clock_skew_ms=-1.5,
        ),
        LatencySample(
            sample_id=3,
            endpoint="opc.tcp://127.0.0.1:40003",
            total_result_transfer_time_ms=None,
            network_transport_time_ms=None,
            server_processing_time_ms=None,
            clock_skew_ms=None,
        ),
    ]
    md = generate_markdown_report(samples, verdict, "FleetPool")
    assert "Per-Server Latency Breakdown (3 Servers)" in md
    assert "opc.tcp://127.0.0.1:40001" in md
    assert "opc.tcp://127.0.0.1:40002" in md
    assert "Fleet Aggregate Latency Percentiles (All Servers)" in md

    json_path = tmp_path / "fleet.json"
    export_json_report(json_path, samples, verdict, "FleetPool")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["distinct_servers"] == 3
    assert "opc.tcp://127.0.0.1:40001" in data["per_server_statistics"]
    assert data["per_server_statistics"]["opc.tcp://127.0.0.1:40001"]["sample_count"] == 1
