"""
Unit tests for JUnit, Markdown, and JSON reporting exporters.
"""

from ijt_performance_client.attribution import DiagnosticVerdict
from ijt_performance_client.reporters.json_exporter import export_json_report
from ijt_performance_client.reporters.junit import write_junit_xml
from ijt_performance_client.reporters.markdown import generate_markdown_report


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
    from ijt_performance_client.result_transfer_latency import LatencySample

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
