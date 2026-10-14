"""Unit tests for claim profile resolution."""

from src.claim import resolve_claim


def test_capacity_intended_always_profile_a():
    result = resolve_claim(intended="capacity", endpoints=["opc.tcp://127.0.0.1:40001"])
    assert result.achieved == "A"
    assert result.profile_label == "A"


def test_split_path_unproven_without_topology():
    result = resolve_claim(
        intended="split_path",
        endpoints=["opc.tcp://192.168.1.10:4840"],
        producer_host_id="prod123",
        client_host_id="client456",
        topology_verified=False,
    )
    assert result.achieved == "UNPROVEN"
    assert result.profile_label == "UNPROVEN"


def test_split_path_profile_b_when_verified():
    result = resolve_claim(
        intended="split_path",
        endpoints=["opc.tcp://192.168.1.10:4840"],
        producer_host_id="aaaaaaaaaaaaaaaa",
        client_host_id="bbbbbbbbbbbbbbbb",
        topology_verified=True,
        clock_probe_ran=True,
        clock_quality_ok=True,
        wire_timing_coverage=0.99,
    )
    assert result.achieved == "B"
    assert "not NIC wire time" in result.reason


def test_split_path_unproven_when_coverage_unknown():
    result = resolve_claim(
        intended="split_path",
        endpoints=["opc.tcp://192.168.1.10:4840"],
        producer_host_id="aaaaaaaaaaaaaaaa",
        client_host_id="bbbbbbbbbbbbbbbb",
        topology_verified=True,
        clock_probe_ran=True,
        wire_timing_coverage=None,
    )
    assert result.achieved == "UNPROVEN"


def test_split_path_unproven_when_clock_not_probed():
    result = resolve_claim(
        intended="split_path",
        endpoints=["opc.tcp://192.168.1.10:4840"],
        producer_host_id="aaaaaaaaaaaaaaaa",
        client_host_id="bbbbbbbbbbbbbbbb",
        topology_verified=True,
        clock_probe_ran=False,
        wire_timing_coverage=0.99,
    )
    assert result.achieved == "UNPROVEN"


def test_split_path_unproven_on_loopback_even_with_ids():
    result = resolve_claim(
        intended="split_path",
        endpoints=["opc.tcp://127.0.0.1:4840"],
        producer_host_id="aaaaaaaaaaaaaaaa",
        client_host_id="bbbbbbbbbbbbbbbb",
        topology_verified=True,
        clock_probe_ran=True,
        clock_quality_ok=True,
        wire_timing_coverage=0.99,
    )
    assert result.achieved == "UNPROVEN"
