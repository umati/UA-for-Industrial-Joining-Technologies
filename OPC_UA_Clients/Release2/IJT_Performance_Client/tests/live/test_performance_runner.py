"""
Live integration test runner for IJT Performance Client.
Can be executed via pytest in GHA or against live local controllers.
Mandatory single-server benchmarks fail if the live target is not reachable.
"""

import json
import os
import socket
import urllib.parse
from pathlib import Path
from typing import Any

import pytest

from ijt_performance_client.cli import main


def _is_port_open(host: str, port: int, timeout_s: float = 1.0) -> bool:
    """Check if target TCP port is actively listening."""
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def _parse_endpoint_host_port(url: str, default_port: int = 40451) -> tuple[str, int]:
    """Extract host and port from OPC UA endpoint string."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or default_port
    return host, port


def _require_server(url: str) -> None:
    host, port = _parse_endpoint_host_port(url, default_port=40485)
    if not _is_port_open(host, port):
        pytest.fail(f"Required OPC UA server on {host}:{port} is not reachable.")


def _read_total_stats(json_out: str) -> dict[str, Any]:
    metrics = json.loads(Path(json_out).read_text(encoding="utf-8"))
    totals = metrics.get("statistics", {}).get("total_result_transfer_time_ms")
    assert isinstance(totals, dict) and totals.get("count", 0) > 0, (
        "Mandatory benchmark produced no total_result_transfer_time_ms statistics"
    )
    return metrics


@pytest.mark.live
def test_live_single_server_result_transfer_time(tmp_path: Path, record_property: Any) -> None:
    """Benchmark Result Transfer Time against 1 OPC UA Server across several joining results.

    Measures standardized timing breakdown:
    1. Joining Duration (joining_duration_ms = T_end - T_start)
    2. Server Processing Duration (server_processing_time_ms = T_event - T_end)
    3. Network Transport Latency (network_transport_time_ms = T_client - T_event + Delta_t_skew)
    Total Result Transfer Time: total_result_transfer_time_ms = T_client - T_end + Delta_t_skew
    """
    server_url = os.environ.get("OPCUA_SERVER_URL", "opc.tcp://localhost:40485")
    _require_server(server_url)

    junit_out = str(tmp_path / "junit-single-server.xml")
    md_out = str(tmp_path / "perf-single-server.md")
    json_out = str(tmp_path / "perf-single-server.json")

    # Collect several results (target: 3 samples) with active burst simulation
    exit_code = main(
        [
            "-e",
            server_url,
            "-d",
            "10.0",
            "-s",
            "3",
            "-b",
            "3",
            "--mode",
            "both",
            "--fail-p90",
            "500.0",  # SLA threshold: 500ms P90 total delivery
            "--junit",
            junit_out,
            "--markdown",
            md_out,
            "--json",
            json_out,
        ]
    )

    assert exit_code == 0
    assert Path(junit_out).is_file()
    assert Path(md_out).is_file()
    assert Path(json_out).is_file()

    # Verify and publish Result Transfer Time properties into JUnit XML
    metrics = _read_total_stats(json_out)
    tot = metrics["statistics"]["total_result_transfer_time_ms"]
    transport = metrics["statistics"]["network_transport_time_ms"]
    server = metrics["statistics"]["server_processing_time_ms"]
    verdict = metrics["verdict"]
    record_property("perf_sample_count", str(tot["count"]))
    record_property("perf_mean_total_ms", f"{tot['mean']:.2f}")
    record_property("perf_p90_total_ms", f"{tot['p90']:.2f}")
    record_property("perf_min_total_ms", f"{tot['min']:.2f}")
    record_property("perf_max_total_ms", f"{tot['max']:.2f}")
    record_property("perf_p90_transport_ms", f"{transport['p90']:.2f}")
    record_property("perf_p90_server_ms", f"{server['p90']:.2f}")
    record_property("perf_primary_bottleneck", verdict["primary_bottleneck"])
    record_property("perf_threshold_mean_ms", "250")
    record_property("perf_threshold_p90_ms", "500")


@pytest.mark.live
def test_live_single_server_burst_transfer_time(tmp_path: Path) -> None:
    """Benchmark rapid consecutive burst tightenings on 1 OPC UA Server.

    Validates that socket queues and worker memory buffers process back-to-back
    results without packet drops or queue saturation.
    """
    server_url = os.environ.get("OPCUA_SERVER_URL", "opc.tcp://localhost:40485")
    _require_server(server_url)

    junit_out = str(tmp_path / "junit-burst.xml")
    json_out = str(tmp_path / "perf-burst.json")

    exit_code = main(
        [
            "-e",
            server_url,
            "-d",
            "8.0",
            "-b",
            "5",  # Rapid 5-event burst
            "-s",
            "5",
            "--mode",
            "both",
            "--junit",
            junit_out,
            "--json",
            json_out,
        ]
    )

    assert exit_code == 0
    assert Path(junit_out).is_file()
    assert Path(json_out).is_file()
    _read_total_stats(json_out)


@pytest.mark.live
def test_live_multi_server_fleet_transfer_time(tmp_path: Path) -> None:
    """Benchmark multi-controller fleet scaling across multiple OPC UA Servers.

    Activated when multiple endpoints are provided via OPCUA_FLEET_ENDPOINTS
    (e.g., 'opc.tcp://10.0.0.1:40451,opc.tcp://10.0.0.2:40451').
    """
    fleet_eps = os.environ.get("OPCUA_FLEET_ENDPOINTS")
    if not fleet_eps:
        pytest.skip("OPCUA_FLEET_ENDPOINTS not configured — skipping live multi-server fleet test.")

    endpoints = [ep.strip() for ep in fleet_eps.split(",") if ep.strip()]
    if len(endpoints) < 2:
        pytest.fail("Configured fleet benchmark requires at least 2 endpoints.")

    for endpoint in endpoints:
        _require_server(endpoint)

    junit_out = str(tmp_path / "junit-fleet.xml")
    json_out = str(tmp_path / "perf-fleet.json")

    exit_code = main(
        [
            "-e",
            fleet_eps,
            "-d",
            "10.0",
            "--mode",
            "both",
            "--junit",
            junit_out,
            "--json",
            json_out,
        ]
    )

    assert exit_code == 0
    assert Path(junit_out).is_file()
    assert Path(json_out).is_file()
    _read_total_stats(json_out)
