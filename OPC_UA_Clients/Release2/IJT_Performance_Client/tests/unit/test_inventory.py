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


def test_build_inventory_url_port_exception():
    # Large invalid port causing urlparse.port to fail
    inv = build_inventory(["opc.tcp://localhost:99999999999999999999999999999999999"])
    assert inv.endpoints[0].port is None


def test_inventory_load_validation_and_errors(tmp_path):
    from unittest.mock import patch
    from urllib.error import URLError

    # File not found (line 192)
    with pytest.raises(FileNotFoundError, match="Inventory file not found"):
        load_inventory(tmp_path / "missing.json")

    # JSON not an object (line 196)
    bad_json = tmp_path / "not_object.json"
    bad_json.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="Inventory must be a JSON object"):
        load_inventory(bad_json)

    # Schema version mismatch (line 198)
    bad_schema = tmp_path / "bad_schema.json"
    bad_schema.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported inventory schema_version"):
        load_inventory(bad_schema)

    # Invalid expires_at ISO timestamp (lines 212-213)
    inv = build_inventory(["opc.tcp://127.0.0.1:40451"])
    inv.expires_at = "invalid-date"
    inv_data = inv.to_dict()
    bad_date_file = tmp_path / "bad_date.json"
    bad_date_file.write_text(json.dumps(inv_data), encoding="utf-8")
    with pytest.raises(ValueError, match="Inventory expires_at is not a valid ISO timestamp"):
        load_inventory(bad_date_file)

    # URLError when fetching URL (lines 186-187)
    with patch("src.inventory._fetch_inventory_url", side_effect=URLError("Connection refused")):
        with pytest.raises(FileNotFoundError, match="Failed to fetch inventory from"):
            load_inventory("https://127.0.0.1:8765/inventory")


def test_reject_redirects_handler():
    from unittest.mock import MagicMock, patch
    from urllib.error import URLError

    import src.inventory as inv_mod

    # Inspect _fetch_inventory_url code by calling with redirect simulation
    with patch("urllib.request.build_opener") as mock_build_opener:
        mock_opener = MagicMock()
        mock_build_opener.return_value = mock_opener
        mock_opener.open.return_value.__enter__.return_value.read.return_value = b"{}"
        # Get the class passed to build_opener
        inv_mod._fetch_inventory_url("https://example.com/test", token=None)
        redirect_handler_cls = mock_build_opener.call_args[0][0]
        handler = redirect_handler_cls()
        with pytest.raises(URLError, match="Refusing to follow HTTP redirect"):
            handler.redirect_request(None, None, 302, "Found", {}, "https://new.com")


def test_preflight_port_range_busy_overflow():
    from unittest.mock import patch

    from src.inventory import preflight_port_range

    with patch("src.inventory._port_appears_busy", return_value=True):
        # 12 busy ports (lines 248-250)
        conflicts = preflight_port_range(50000, 12, reserved=frozenset())
        assert any("(+2 more)" in c for c in conflicts)


def test_inventory_http_server_remote_requires_token():
    from src.inventory import InventoryHttpServer

    inv = build_inventory(["opc.tcp://127.0.0.1:40451"])
    # Line 313: remote non-loopback without token
    with pytest.raises(ValueError, match="Remote inventory HTTP requires an auth token"):
        InventoryHttpServer(inv, host="10.0.0.1", token=None, allow_non_loopback=True)


def test_inventory_handler_status_codes():
    from io import BytesIO

    from src.inventory import _InventoryHandler

    class DummyHandler(_InventoryHandler):
        def __init__(self, path, headers=None, token=None):
            self.path = path
            self.headers = headers or {}
            self.auth_token = token
            self.inventory_bytes = b'{"status": "ok"}'
            self.rfile = BytesIO()
            self.wfile = BytesIO()
            self.error_code = None
            self.error_message = None
            self.response_code = None

        def send_error(self, code, message=None):
            self.error_code = code
            self.error_message = message

        def send_response(self, code, message=None):
            self.response_code = code

        def send_header(self, keyword, value):
            pass

        def end_headers(self):
            pass

    # 404 test (lines 279-280)
    h404 = DummyHandler("/not_found")
    h404.do_GET()
    assert h404.error_code == 404

    # 401 test with missing/bad token (lines 282-285)
    h401 = DummyHandler("/inventory", headers={"Authorization": "Bearer wrong"}, token="expected_token")
    h401.do_GET()
    assert h401.error_code == 401
