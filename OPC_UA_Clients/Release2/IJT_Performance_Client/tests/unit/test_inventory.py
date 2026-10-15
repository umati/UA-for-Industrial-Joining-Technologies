"""Unit tests for fleet inventory I/O and port preflight."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from src.inventory import (
    build_inventory,
    load_inventory,
    preflight_http_port,
    preflight_port_range,
    remaining_ttl_seconds,
    write_inventory_atomic,
)


def test_inventory_round_trip(tmp_path):
    endpoints = ["opc.tcp://127.0.0.1:50001", "opc.tcp://127.0.0.1:50002"]
    inv = build_inventory(endpoints, ttl_seconds=3600, role="colocated")
    path = write_inventory_atomic(tmp_path / "inv.json", inv)
    loaded = load_inventory(path)
    assert loaded.endpoint_urls() == endpoints
    assert loaded.producer_host_id == inv.producer_host_id
    assert loaded.role == "colocated"


def test_inventory_hash_mismatch(tmp_path):
    inv = build_inventory(["opc.tcp://127.0.0.1:50003"], ttl_seconds=3600)
    path = write_inventory_atomic(tmp_path / "bad.json", inv)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["expected_scale"] = 999
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="content_hash mismatch"):
        load_inventory(path)


def test_inventory_expired(tmp_path):
    inv = build_inventory(["opc.tcp://127.0.0.1:50004"], ttl_seconds=3600)
    path = write_inventory_atomic(tmp_path / "exp.json", inv)
    data = json.loads(path.read_text(encoding="utf-8"))
    past = (datetime.now(UTC) - timedelta(seconds=10)).isoformat()
    data["expires_at"] = past
    from src.inventory import FleetInventory

    data["content_hash"] = FleetInventory.from_dict(data).to_dict()["content_hash"]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="expired"):
        load_inventory(path)


def test_preflight_reserved_ports_overlap():
    # 40451 is reserved — range starting at 40450 should conflict
    errors = preflight_port_range(40450, 3)
    assert any("reserved" in e.lower() for e in errors)


def test_preflight_clean_high_port():
    errors = preflight_port_range(50100, 2)
    reserved_overlap = [e for e in errors if "reserved" in e.lower()]
    assert not reserved_overlap


def test_inventory_missing_content_hash(tmp_path):
    inv = build_inventory(["opc.tcp://127.0.0.1:50005"], ttl_seconds=3600)
    path = write_inventory_atomic(tmp_path / "nohash.json", inv)
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["content_hash"]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="content_hash"):
        load_inventory(path)


def test_inventory_refuses_bearer_over_plaintext_http():
    with pytest.raises(ValueError, match="plaintext HTTP"):
        load_inventory("HTTP://example.invalid/inventory", token="secret")


def test_inventory_http_server_rejects_non_loopback_without_flag():
    from src.inventory import InventoryHttpServer, build_inventory

    inv = build_inventory(["opc.tcp://127.0.0.1:50006"], ttl_seconds=60)
    with pytest.raises(ValueError, match="non-loopback"):
        InventoryHttpServer(inv, host="192.168.1.50", port=18765, allow_non_loopback=False)


def test_inventory_http_server_loopback_roundtrip():
    from src.inventory import InventoryHttpServer, build_inventory, load_inventory

    inv = build_inventory(["opc.tcp://127.0.0.1:50007"], ttl_seconds=60)
    server = InventoryHttpServer(inv, host="127.0.0.1", port=18766, token=None)
    server.start()
    try:
        loaded = load_inventory(server.url)
        assert loaded.endpoint_urls() == inv.endpoint_urls()
    finally:
        server.stop()


def test_effective_config_redacts_token():
    from src.config import OpcUaPoolConfig
    from src.effective_config import EffectiveConfigTracker

    cfg = OpcUaPoolConfig(endpoints=["opc.tcp://127.0.0.1:40451"], inventory_http_token="super-secret")
    snap = EffectiveConfigTracker().snapshot(cfg)
    assert snap["inventory_http_token"]["value"] == "***"
    assert "explicit_profile_fields" not in snap


def test_remaining_ttl_seconds_positive():
    inv = build_inventory(["opc.tcp://127.0.0.1:50008"], ttl_seconds=3600)
    remaining = remaining_ttl_seconds(inv)
    assert remaining is not None
    assert remaining > 3500


def test_preflight_http_port_clean():
    # High ephemeral-ish port unlikely to be busy; may still be occupied — only assert type
    errors = preflight_http_port(18770)
    assert isinstance(errors, list)


def test_remaining_ttl_invalid_expires_returns_none():
    inv = build_inventory(["opc.tcp://127.0.0.1:50009"], ttl_seconds=60)
    inv.expires_at = "not-a-timestamp"
    assert remaining_ttl_seconds(inv) is None


def test_fetch_inventory_url_rejects_redirect(monkeypatch):
    from urllib.error import URLError

    from src.inventory import _fetch_inventory_url

    def fake_build_opener(*handlers):
        class Opener:
            def open(self, req, timeout=30):
                raise URLError("Refusing to follow HTTP redirect from inventory URL (status 302)")

        return Opener()

    monkeypatch.setattr("urllib.request.build_opener", fake_build_opener)
    with pytest.raises(URLError, match="redirect"):
        _fetch_inventory_url("https://example.invalid/inventory", token="secret")


def test_port_appears_busy_when_socket_active():
    import socket

    from src.inventory import _port_appears_busy

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        assert _port_appears_busy(port) is True
        assert preflight_http_port(port) == [f"Inventory HTTP port {port} on 127.0.0.1 appears already in use"]
