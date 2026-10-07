"""
Unit tests for JUnit, Markdown, and JSON reporting exporters.
"""

import pytest

from src.diagnostics import DiagnosticVerdict
from src.reporters import (
    export_csv_report,
    export_json_report,
    generate_markdown_report,
    write_junit_xml,
)
from src.results import LatencySample


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
    assert "Fleet Aggregate Latency (All Servers)" in md

    json_path = tmp_path / "fleet.json"
    export_json_report(json_path, samples, verdict, "FleetPool")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["distinct_servers"] == 3
    assert "opc.tcp://127.0.0.1:40001" in data["per_server_statistics"]
    assert data["per_server_statistics"]["opc.tcp://127.0.0.1:40001"]["sample_count"] == 1
    sample_entry = data["samples"][0]
    assert "trace_declared_points" in sample_entry
    assert "trace_decoded_points" in sample_entry
    assert "trace_is_incomplete" in sample_entry
    assert "raw_total_result_transfer_time_ms" in sample_entry
    assert "raw_network_transport_time_ms" in sample_entry
    assert "is_clamped_to_zero" in sample_entry


def test_csv_reporter_exports_rows(tmp_path):
    from datetime import UTC, datetime

    from src.results import LatencySample

    csv_path = tmp_path / "samples.csv"
    samples = [
        LatencySample(
            sample_id=1,
            endpoint="opc.tcp://127.0.0.1:40001",
            client_received_time=datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC),
            event_time=datetime(2026, 10, 1, 11, 59, 59, 950000, tzinfo=UTC),
            total_result_transfer_time_ms=50.0,
            server_processing_time_ms=10.0,
            network_transport_time_ms=40.0,
            raw_total_result_transfer_time_ms=50.0,
            raw_network_transport_time_ms=40.0,
            is_clamped_to_zero=False,
            joining_duration_ms=1200.0,
            clock_skew_ms=-2.0,
            result_id="RES-001",
            result_evaluation="OK",
            trace_curves_count=3,
            trace_total_points=600,
            trace_declared_points=600,
            trace_decoded_points=600,
            trace_is_incomplete=False,
        ),
        LatencySample(
            sample_id=2,
            endpoint="opc.tcp://127.0.0.1:40002",
            total_result_transfer_time_ms=None,
            clock_skew_ms=0.0,
        ),
    ]

    export_csv_report(csv_path, samples)
    assert csv_path.is_file()
    lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3  # Header + 2 rows
    assert "sample_id,endpoint,result_id,result_evaluation,trace_curves,trace_points,trace_declared_points" in lines[0]
    assert "is_clamped_to_zero" in lines[0]
    assert "integrity_status,integrity_reason" in lines[0]
    assert "opc.tcp://127.0.0.1:40001" in lines[1]
    assert "RES-001" in lines[1]
    assert "OK" in lines[1]
    assert "3" in lines[1]
    assert "600" in lines[1]
    assert "50.00" in lines[1]
    assert "1200.00" in lines[1]
    assert "FALSE" in lines[1]
    assert "opc.tcp://127.0.0.1:40002" in lines[2]


def test_reporters_render_integrity_breakdown_tables(capsys):
    from src.diagnostics import DiagnosticVerdict
    from src.reporters import generate_markdown_report, print_console_report
    from src.results import (
        INTEGRITY_DUPLICATE,
        INTEGRITY_INCOMPLETE,
        INTEGRITY_UNMATCHED,
        INTEGRITY_VALID,
        LatencySample,
    )

    verdict = DiagnosticVerdict(
        primary_bottleneck="NONE",
        headline="Healthy",
        explanation="Pipeline OK",
        recommendation="None",
        warnings=[],
        metrics_summary={},
    )
    samples = [
        LatencySample(sample_id=1, endpoint="opc.tcp://s1:4840", integrity_status=INTEGRITY_VALID),
        LatencySample(sample_id=2, endpoint="opc.tcp://s1:4840", integrity_status=INTEGRITY_INCOMPLETE),
        LatencySample(sample_id=3, endpoint="opc.tcp://s2:4840", integrity_status=INTEGRITY_DUPLICATE),
        LatencySample(sample_id=4, endpoint="opc.tcp://s2:4840", integrity_status=INTEGRITY_UNMATCHED),
    ]

    # Console output contains integrity audit table
    print_console_report(samples, verdict, "IntegrityTestPool")
    captured = capsys.readouterr().out
    assert "BENCHMARK INTEGRITY AUDIT" in captured
    assert "opc.tcp://s1:4840" in captured
    assert "opc.tcp://s2:4840" in captured

    # Markdown report contains integrity audit section
    md = generate_markdown_report(samples, verdict, "IntegrityTestPool")
    assert "### 🛡️ Benchmark Integrity Audit" in md
    assert "`opc.tcp://s1:4840`" in md
    assert "`opc.tcp://s2:4840`" in md


def test_json_and_csv_include_wire_timing_and_valid_only_statistics(tmp_path):
    import csv
    import json

    from src.reporters import export_csv_report, export_json_report

    verdict = DiagnosticVerdict(
        primary_bottleneck="X", headline="h", explanation="e", recommendation="r", metrics_summary={}, warnings=[]
    )
    good = LatencySample(sample_id=1, endpoint="e", delivery_time_ms=10.0, timing_source="wire")
    bad = LatencySample(sample_id=2, endpoint="e", delivery_time_ms=500.0, integrity_status="DUPLICATE")
    out = tmp_path / "m.json"
    export_json_report(out, [good, bad], verdict, pool_name="P")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["valid_sample_count"] == 1
    assert data["integrity_counts"] == {"VALID": 1, "DUPLICATE": 1}
    assert data["wire_timing_sample_count"] == 1
    assert data["headline_metric"] == "delivery_time_ms"
    assert data["statistics"]["delivery_time_ms"]["max"] == 10.0
    assert data["per_server_statistics"]["e"]["valid_count"] == 1
    assert len(data["samples"]) == 2
    assert data["samples"][1]["delivery_time_ms"] == 500.0

    csv_path = tmp_path / "m.csv"
    export_csv_report(csv_path, [good])
    row = next(csv.DictReader(csv_path.open(encoding="utf-8")))
    assert row["timing_source"] == "wire"
    assert row["delivery_time_ms"] == "10.00"
    assert row["client_decode_time_ms"] == ""
    assert row["clock_warning"] == "FALSE"


@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (None, "not measured"),
        (0.0, "0.0 ms (in sync)"),
        (12.04, "+12.0 ms (server ahead)"),
        (-3.5, "-3.5 ms (server behind)"),
    ],
)
def test_format_clock_offset(offset, expected):
    from src.reporters._metrics import format_clock_offset

    assert format_clock_offset(offset) == expected


def _wire_sample(sample_id: int, server_ms: float) -> LatencySample:
    return LatencySample(
        sample_id=sample_id,
        endpoint="opc.tcp://127.0.0.1:40001",
        network_transport_time_ms=100.0,
        server_processing_time_ms=server_ms,
        joining_duration_ms=0.0,
        total_result_transfer_time_ms=100.0 + server_ms,
        delivery_time_ms=60.0,
        client_decode_time_ms=20.0,
        client_ready_time_ms=80.0,
        dispatch_delay_ms=20.0,
    )


def test_reports_hide_rows_that_only_repeat_total_and_show_loop_lag(capsys):
    from src.reporters import print_console_report
    from src.reporters._metrics import visible_metric_rows

    verdict = DiagnosticVerdict("CLIENT_PROCESSING", "Busy", "Explain", "Fix", {}, [])
    timing = {"workers_reported": 2, "loop_lag_max_ms": 369.1, "loop_lag_worst_mean_ms": 18.4}
    samples = [_wire_sample(i, 0.0) for i in range(5)]

    labels = [label for _, label in visible_metric_rows(samples)]
    assert "Server Processing Duration" not in labels
    assert "Network Transport Latency" not in labels
    assert "Total Result Transfer Time" in labels

    print_console_report(samples, verdict, "Local", timing=timing)
    out = capsys.readouterr().out
    assert "Network Transport Latency" not in out
    assert "Server Processing Duration" not in out
    assert "Total Result Transfer Time" in out
    assert "rows hidden" in out
    assert "Worst loop lag 369.1 ms, worst worker average 18.4 ms" in out

    md = generate_markdown_report(samples, verdict, "Local", timing=timing)
    assert "Network Transport Latency" not in md
    assert "Server Processing Duration" not in md
    assert "Worst loop lag 369.1 ms" in md

    # A server that stamps its event later than the operation end keeps the split rows.
    split = [_wire_sample(i, 5.0) for i in range(5)]
    split_labels = [label for _, label in visible_metric_rows(split)]
    assert "Server Processing Duration" in split_labels
    assert "Network Transport Latency" in split_labels
    split_md = generate_markdown_report(split, verdict, "Remote")
    assert "rows hidden" not in split_md
    assert "Network Transport Latency" in split_md
    assert "Server Processing Duration" in split_md
