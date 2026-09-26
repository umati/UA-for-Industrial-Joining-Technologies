"""
Unit tests for Result Transfer Time benchmarking scenarios.

Covers:
1. Scenario 1 — Single OPC UA Server with several joining results (single-station latency & SLA check).
2. Scenario 2 — Multiple OPC UA Servers with several results per server (multi-controller scaling).
3. Scenario 3 — Forensic attribution decomposition across all timing stages:
   - Tool execution (T_joining)
   - Server Processing Duration (server_processing_time_ms)
   - Network Transport Latency (network_transport_time_ms)
   - Total Result Transfer Time (total_result_transfer_time_ms)
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from ijt_performance_client.attribution import evaluate_diagnostics
from ijt_performance_client.cli import main
from ijt_performance_client.opcua_client_pool import OpcUaClientPool
from ijt_performance_client.result_transfer_latency import LatencySample, compute_statistics


def test_scenario_single_server_several_results(tmp_path):
    """Scenario 1: Single OPC UA Server with several results.

    Simulates 1 tool controller producing 25 consecutive joining results.
    Validates that:
    - Result transfer times (total, transport, server) are accurately aggregated.
    - Percentiles (Mean, P90, P99) are computed.
    - Diagnostic verdict detects a healthy pipeline under SLA.
    """
    server_ep = "opc.tcp://192.168.1.100:40451"
    t_base = datetime(2026, 9, 25, 14, 0, 0, tzinfo=UTC)

    # Generate 25 simulated result samples with small variance
    samples: list[LatencySample] = []
    for i in range(1, 26):
        t_start = t_base + timedelta(seconds=i * 2)
        t_end = t_start + timedelta(milliseconds=750)  # 750ms joining operation
        t_create = t_end + timedelta(milliseconds=12 + (i % 3))
        t_event = t_create + timedelta(milliseconds=4)  # Server processing = 16-18ms
        t_client = t_event + timedelta(milliseconds=18 + (i % 5))  # Network transport = 18-22ms

        sample = LatencySample(
            sample_id=i,
            endpoint=server_ep,
            start_time=t_start,
            end_time=t_end,
            creation_time=t_create,
            event_time=t_event,
            client_received_time=t_client,
            clock_skew_ms=0.0,
        )
        sample.calculate_metrics()
        samples.append(sample)

    assert len(samples) == 25
    totals = [s.total_result_transfer_time_ms for s in samples if s.total_result_transfer_time_ms is not None]
    transports = [s.network_transport_time_ms for s in samples if s.network_transport_time_ms is not None]
    servers = [s.server_processing_time_ms for s in samples if s.server_processing_time_ms is not None]

    st_total = compute_statistics(totals)
    st_transport = compute_statistics(transports)
    st_server = compute_statistics(servers)

    # Total transfer time: ~35ms, transport: ~20ms, server: ~17ms
    assert 30.0 < st_total["p90"] < 50.0
    assert 15.0 < st_transport["p90"] < 25.0
    assert 10.0 < st_server["p90"] < 25.0

    # Diagnostic verdict confirms pipeline is healthy (< 100ms P90)
    verdict = evaluate_diagnostics(
        network_transport_latencies=transports,
        server_processing_latencies=servers,
        total_latencies=totals,
        clock_skews=[0.0],
    )
    assert "HEALTHY" in verdict.primary_bottleneck

    # Run through CLI with mock pool
    junit_path = str(tmp_path / "junit-single.xml")
    json_path = str(tmp_path / "metrics-single.json")

    with patch("ijt_performance_client.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 1
        mock_pool.collect_samples.return_value = samples
        mock_pool.stop.return_value = samples
        mock_pool.verify_coverage.return_value = (True, "Single server coverage OK")
        mock_pool.connected_endpoints = {server_ep}
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        code = main(
            [
                "--endpoints",
                server_ep,
                "--duration",
                "5.0",
                "--samples",
                "25",
                "--fail-p90",
                "100.0",  # SLA passes because P90 is ~40ms
                "--junit",
                junit_path,
                "--json",
                json_path,
            ]
        )
        assert code == 0


def test_scenario_multiple_servers_several_results_per_server(tmp_path):
    """Scenario 2: Multiple OPC UA Servers with several results per server.

    Simulates a 4-controller joining cell (4 endpoints) with 10 results each
    (40 total samples).
    Validates that:
    - Multi-server sharding connects to all 4 endpoints.
    - Full coverage is verified (100% of controllers produced results).
    - Cross-pool statistics and SLA validation succeed.
    """
    endpoints = [
        "opc.tcp://cell-controller-01:40451",
        "opc.tcp://cell-controller-02:40451",
        "opc.tcp://cell-controller-03:40451",
        "opc.tcp://cell-controller-04:40451",
    ]

    all_samples: list[LatencySample] = []
    sample_id = 1
    t_base = datetime(2026, 9, 25, 14, 30, 0, tzinfo=UTC)

    # 10 samples per controller = 40 total
    for ep in endpoints:
        for j in range(10):
            t_start = t_base + timedelta(seconds=sample_id)
            t_end = t_start + timedelta(milliseconds=800)
            t_create = t_end + timedelta(milliseconds=15)
            t_event = t_create + timedelta(milliseconds=5)
            t_client = t_event + timedelta(milliseconds=20)

            sample = LatencySample(
                sample_id=sample_id,
                endpoint=ep,
                start_time=t_start,
                end_time=t_end,
                creation_time=t_create,
                event_time=t_event,
                client_received_time=t_client,
            )
            sample.calculate_metrics()
            all_samples.append(sample)
            sample_id += 1

    assert len(all_samples) == 40

    # Verify coverage across all 4 controllers
    pool = OpcUaClientPool(endpoints=endpoints, max_workers=4, require_full_coverage=True)
    pool.connected_endpoints = set(endpoints)
    valid, msg = pool.verify_coverage(all_samples)
    assert valid is True
    assert "4/4 endpoints produced samples" in msg

    # CLI execution test for multi-server fleet
    junit_path = str(tmp_path / "junit-multi.xml")
    json_path = str(tmp_path / "metrics-multi.json")

    with patch("ijt_performance_client.cli.OpcUaClientPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_pool._num_workers_started = 4
        mock_pool.collect_samples.return_value = all_samples
        mock_pool.stop.return_value = all_samples
        mock_pool.verify_coverage.return_value = (True, "4/4 endpoints produced samples")
        mock_pool.connected_endpoints = set(endpoints)
        mock_pool.failed_endpoints = {}
        mock_pool.worker_errors = []

        code = main(
            [
                "--endpoints",
                ",".join(endpoints),
                "--duration",
                "10.0",
                "--samples",
                "40",
                "--require-full-coverage",
                "--junit",
                junit_path,
                "--json",
                json_path,
            ]
        )
        assert code == 0


def test_scenario_forensic_latency_aspects_decomposition():
    """Scenario 3: Different aspects of Result Transfer Time forensics.

    Validates that the client correctly isolates:
    1. Physical joining duration (joining_duration_ms)
    2. Server processing duration (server_processing_time_ms)
    3. Network transport latency (network_transport_time_ms)
    4. Total Result Transfer Time (total_result_transfer_time_ms)
    """
    t0 = datetime(2026, 9, 25, 15, 0, 0, tzinfo=UTC)
    t_end = t0 + timedelta(milliseconds=1200)  # 1200ms joining operation
    t_create = t_end + timedelta(milliseconds=350)
    t_event = t_create + timedelta(milliseconds=10)  # 360ms server processing
    t_recv = t_event + timedelta(milliseconds=25)  # 25ms network transport

    sample = LatencySample(
        sample_id=1,
        endpoint="opc.tcp://slow-server-controller:40451",
        start_time=t0,
        end_time=t_end,
        creation_time=t_create,
        event_time=t_event,
        client_received_time=t_recv,
        clock_skew_ms=0.0,
    )
    sample.calculate_metrics()

    # 1. Aspect: Joining duration
    assert sample.joining_duration_ms == 1200.0

    # 2. Aspect: Server processing duration
    assert sample.server_processing_time_ms == 360.0

    # 3. Aspect: Network transport latency
    assert sample.network_transport_time_ms == 25.0

    # 4. Aspect: Total result transfer time
    assert sample.total_result_transfer_time_ms == 385.0  # 360 + 25

    # 5. Aspect: Forensic Attribution pinpointing server processing delay
    verdict = evaluate_diagnostics(
        network_transport_latencies=[sample.network_transport_time_ms],
        server_processing_latencies=[sample.server_processing_time_ms],
        total_latencies=[sample.total_result_transfer_time_ms],
        clock_skews=[0.0],
    )
    assert verdict.primary_bottleneck == "SERVER_PROCESSING_DURATION"
    assert "Server" in verdict.headline
