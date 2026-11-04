"""Unit tests for claim profile resolution."""

from src.claim import endpoint_hosts, resolve_claim


def test_capacity_intended_always_profile_a():
    result = resolve_claim(intended="capacity", endpoints=["opc.tcp://127.0.0.1:40001"])
    assert result.achieved == "A"
    assert result.profile_label == "A"
    assert result.to_dict()["achieved"] == "A"


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


def test_split_path_unproven_when_coverage_below_threshold():
    result = resolve_claim(
        intended="split_path",
        endpoints=["opc.tcp://192.168.1.10:4840"],
        producer_host_id="aaaaaaaaaaaaaaaa",
        client_host_id="bbbbbbbbbbbbbbbb",
        topology_verified=True,
        clock_probe_ran=True,
        clock_quality_ok=True,
        wire_timing_coverage=0.85,
    )
    assert result.achieved == "UNPROVEN"
    assert "need >= 95%" in result.reason


def test_split_path_unproven_when_clock_quality_bad():
    result = resolve_claim(
        intended="split_path",
        endpoints=["opc.tcp://192.168.1.10:4840"],
        producer_host_id="aaaaaaaaaaaaaaaa",
        client_host_id="bbbbbbbbbbbbbbbb",
        topology_verified=True,
        clock_probe_ran=True,
        clock_quality_ok=False,
        wire_timing_coverage=0.98,
    )
    assert result.achieved == "UNPROVEN"
    assert "clock quality is insufficient" in result.reason


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


def test_auto_intended_promotes_to_b_when_fully_proven():
    result = resolve_claim(
        intended="auto",
        endpoints=["opc.tcp://192.168.1.10:4840"],
        producer_host_id="aaaaaaaaaaaaaaaa",
        client_host_id="bbbbbbbbbbbbbbbb",
        topology_verified=True,
        clock_probe_ran=True,
        clock_quality_ok=True,
        wire_timing_coverage=0.99,
    )
    assert result.achieved == "B"
    assert result.profile_label == "B"


def test_auto_intended_falls_back_to_a_on_loopback():
    result = resolve_claim(
        intended="auto",
        endpoints=["opc.tcp://127.0.0.1:4840"],
    )
    assert result.achieved == "A"
    assert result.profile_label == "A"


def test_endpoint_hosts_extracts_normalized_hosts():
    hosts = endpoint_hosts(["opc.tcp://HostA:4840", "opc.tcp://10.0.0.2:4840", "invalid"])
    assert hosts == {"hosta", "10.0.0.2"}


def test_unknown_intended_normalizes_to_auto():
    result = resolve_claim(intended="invalid_value", endpoints=["opc.tcp://127.0.0.1:4840"])
    assert result.intended == "auto"
    assert result.achieved == "A"
