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


def test_enable_ansi_windows():
    from unittest.mock import MagicMock, patch

    from src.reporters.console import _enable_ansi_windows

    # Call on the real system (safe on Windows, Linux, and macOS)
    res = _enable_ansi_windows()
    assert isinstance(res, bool)

    # 1. Test missing windll (Linux/macOS behavior)
    with patch.dict("sys.modules", {"ctypes": MagicMock(spec=[])}):
        assert _enable_ansi_windows() is False

    # 2. Test kernel32 error path
    mock_bad = MagicMock()
    mock_bad.kernel32.GetConsoleMode.side_effect = RuntimeError("mock error")
    with patch("ctypes.windll", mock_bad, create=True):
        assert _enable_ansi_windows() is False

    # 3. Test kernel32 success path
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

    # Test reconfigure branch when encoding is not utf-8
    mock_stdout = MagicMock()
    mock_stdout.encoding = "cp1252"
    mock_stdout.reconfigure = MagicMock()
    monkeypatch.setattr(sys, "stdout", mock_stdout)
    _safe_print("test reconfigure")
    mock_stdout.reconfigure.assert_called_once_with(encoding="utf-8")

    # Test reconfigure exception
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


def test_print_console_report_uncolonized_guide_and_notes(capsys, monkeypatch):
    verdict = DiagnosticVerdict(
        primary_bottleneck="TEST", headline="h", explanation="e", recommendation="r", metrics_summary={}, warnings=[]
    )
    sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://localhost:40451",
        network_transport_time_ms=10.0,
        server_processing_time_ms=12.0,
        total_result_transfer_time_ms=22.0,
    )
    monkeypatch.setattr("src.reporters.console.metric_guide", lambda rows: ["NoColonGuideText"])
    monkeypatch.setattr("src.reporters.console.report_notes", lambda valid, timing: ["NoColonNoteText"])

    print_console_report([sample], verdict, "Uncolonized")
    out = capsys.readouterr().out
    assert "General Guidance" in out
    assert "NoColonGuideText" in out
    assert "Operational Note" in out
    assert "NoColonNoteText" in out
