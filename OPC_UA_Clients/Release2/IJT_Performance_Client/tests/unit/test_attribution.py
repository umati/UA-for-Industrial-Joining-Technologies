"""
Unit tests for root-cause attribution diagnostics.
"""

from ijt_performance_client.attribution import evaluate_diagnostics


def test_attribution_healthy():
    transports = [15.0, 18.0, 22.0, 20.0, 16.0]
    servers = [10.0, 12.0, 15.0, 14.0, 11.0]
    totals = [25.0, 30.0, 37.0, 34.0, 27.0]

    verdict = evaluate_diagnostics(
        network_transport_latencies=transports,
        server_processing_latencies=servers,
        total_latencies=totals,
        clock_skews=[5.0, -2.0],
        measured_thread_count=8,
        measured_process_count=2,
    )
    assert "HEALTHY" in verdict.primary_bottleneck


def test_attribution_server_processing_bottleneck():
    transports = [20.0, 25.0, 22.0, 24.0]
    servers = [350.0, 420.0, 390.0, 410.0]
    totals = [370.0, 445.0, 412.0, 434.0]

    verdict = evaluate_diagnostics(
        network_transport_latencies=transports,
        server_processing_latencies=servers,
        total_latencies=totals,
        clock_skews=[0.0],
    )
    assert verdict.primary_bottleneck == "SERVER_PROCESSING_DURATION"
    assert "Server" in verdict.headline


def test_attribution_network_bottleneck():
    transports = [450.0, 520.0, 490.0, 510.0]
    servers = [10.0, 12.0, 11.0, 15.0]
    totals = [460.0, 532.0, 501.0, 525.0]

    verdict = evaluate_diagnostics(
        network_transport_latencies=transports,
        server_processing_latencies=servers,
        total_latencies=totals,
        clock_skews=[0.0],
    )
    assert verdict.primary_bottleneck == "NETWORK_OR_TRANSPORT"


def test_attribution_no_samples():
    verdict = evaluate_diagnostics(
        network_transport_latencies=[],
        server_processing_latencies=[],
        total_latencies=[],
        clock_skews=[],
    )
    assert verdict.primary_bottleneck == "NO_DATA"
    assert "Zero Result" in verdict.headline


def test_attribution_clock_drift_and_high_thread_count():
    transports = [10.0, 12.0]
    servers = [5.0, 6.0]
    totals = [15.0, 18.0]

    verdict = evaluate_diagnostics(
        network_transport_latencies=transports,
        server_processing_latencies=servers,
        total_latencies=totals,
        clock_skews=[150.0],
        measured_thread_count=250,
    )
    assert any("Clock drift" in w for w in verdict.warnings)
    assert any("High measured client thread count" in w for w in verdict.warnings)


def test_attribution_mixed_delay():
    transports = [120.0, 125.0, 122.0]
    servers = [30.0, 35.0, 32.0]
    totals = [150.0, 160.0, 154.0]

    verdict = evaluate_diagnostics(
        network_transport_latencies=transports,
        server_processing_latencies=servers,
        total_latencies=totals,
        clock_skews=[0.0],
    )
    assert verdict.primary_bottleneck == "APPLICATION_OR_MIXED"
    assert "Mixed Pipeline" in verdict.headline
