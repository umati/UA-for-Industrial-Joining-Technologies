"""
Unit tests for root-cause attribution diagnostics.
"""

import pytest

from src.diagnostics import evaluate_diagnostics


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
    assert any("Clock offset between a server" in w for w in verdict.warnings)
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


def test_client_processing_rule_needs_wire_timing():
    from src.diagnostics import evaluate_diagnostics

    common = dict(
        network_transport_latencies=[300.0] * 10,
        server_processing_latencies=[5.0] * 10,
        total_latencies=[305.0] * 10,
        clock_skews=[0.0],
    )
    verdict = evaluate_diagnostics(**common, client_decode_latencies=[150.0] * 10, dispatch_delays=[100.0] * 10)
    assert verdict.primary_bottleneck == "CLIENT_PROCESSING"
    assert verdict.metrics_summary["client_decode_p90_ms"] == pytest.approx(150.0)

    # Without wire timing the client-side rule cannot fire
    assert evaluate_diagnostics(**common).primary_bottleneck != "CLIENT_PROCESSING"


# Numbers from a real 500-server single-machine run that was wrongly blamed on the network.
_LOCAL_FLEET = dict(
    network_transport_latencies=[328.3] * 10,
    server_processing_latencies=[0.0] * 10,
    total_latencies=[328.3] * 10,
    clock_skews=[0.0],
    delivery_latencies=[225.7] * 10,
    client_decode_latencies=[74.0] * 10,
    dispatch_delays=[66.9] * 10,
)


def test_busy_client_on_one_machine_is_not_blamed_on_the_network():
    verdict = evaluate_diagnostics(**_LOCAL_FLEET, loop_lag_max_ms=369.1, all_endpoints_local=True)
    assert verdict.primary_bottleneck == "CLIENT_PROCESSING"
    assert "this machine" in verdict.explanation
    assert "another host" in verdict.recommendation
    assert verdict.metrics_summary["loop_lag_max_ms"] == pytest.approx(369.1)


def test_loop_lag_alone_marks_the_client_as_busy():
    common = dict(_LOCAL_FLEET, network_transport_latencies=[600.0] * 10, total_latencies=[600.0] * 10)
    assert evaluate_diagnostics(**common).primary_bottleneck == "APPLICATION_OR_MIXED"
    assert evaluate_diagnostics(**common, loop_lag_max_ms=200.0).primary_bottleneck == "CLIENT_PROCESSING"


def test_local_run_never_reports_network_delay():
    verdict = evaluate_diagnostics(
        network_transport_latencies=[400.0] * 10,
        server_processing_latencies=[0.0] * 10,
        total_latencies=[400.0] * 10,
        clock_skews=[0.0],
        all_endpoints_local=True,
    )
    assert verdict.primary_bottleneck == "LOCAL_HOST_CPU"
    assert "not from a network" in verdict.explanation


def test_network_rule_uses_delivery_time_when_wire_timing_exists():
    verdict = evaluate_diagnostics(
        network_transport_latencies=[400.0] * 10,
        server_processing_latencies=[0.0] * 10,
        total_latencies=[400.0] * 10,
        clock_skews=[0.0],
        delivery_latencies=[120.0] * 10,
        client_decode_latencies=[20.0] * 10,
        dispatch_delays=[20.0] * 10,
    )
    assert verdict.primary_bottleneck == "APPLICATION_OR_MIXED"
