"""Unit tests for host fingerprint collection."""

from unittest.mock import MagicMock

from src.host_fingerprint import _local_ips, _total_ram_bytes, collect_host_fingerprint, generate_host_id


def test_fingerprint_no_username():
    fp = collect_host_fingerprint(redact=True)
    assert "username" not in fp
    assert "host_id" in fp
    assert fp["redacted"] is True


def test_fingerprint_redact_hides_hostname():
    fp = collect_host_fingerprint(include_network=True, redact=True)
    assert "hostname" not in fp
    assert "ip_addresses" not in fp
    assert "hostname_hash" in fp
    assert "ip_count" in fp


def test_fingerprint_no_redact_can_include_network():
    fp = collect_host_fingerprint(include_network=True, redact=False)
    assert "hostname" in fp
    assert "ip_addresses" in fp


def test_generate_host_id_is_deterministic_and_bounded():
    h1 = generate_host_id()
    h2 = generate_host_id()
    assert h1 == h2
    assert len(h1) == 16


def test_total_ram_bytes_posix_fallback(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    fake_sysconf = MagicMock(side_effect=lambda name: 1024 if name == "SC_PAGE_SIZE" else 2048)
    monkeypatch.setattr("os.sysconf", fake_sysconf, raising=False)
    ram = _total_ram_bytes()
    assert ram == 1024 * 2048


def test_total_ram_bytes_handles_os_error(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    fake_sysconf = MagicMock(side_effect=OSError("not supported"))
    monkeypatch.setattr("os.sysconf", fake_sysconf, raising=False)
    assert _total_ram_bytes() is None


def test_local_ips_filters_loopbacks_and_duplicates(monkeypatch):
    fake_addrs = [
        (None, None, None, None, ("127.0.0.1", 0)),
        (None, None, None, None, ("192.168.1.50", 0)),
        (None, None, None, None, ("192.168.1.50", 0)),
        (None, None, None, None, (12345, 0)),
    ]
    monkeypatch.setattr("socket.gethostname", lambda: "mock-host")
    monkeypatch.setattr("socket.getaddrinfo", lambda host, port: fake_addrs)
    ips = _local_ips()
    assert ips == ["192.168.1.50"]


def test_local_ips_handles_socket_error(monkeypatch):
    monkeypatch.setattr("socket.gethostname", MagicMock(side_effect=OSError("network down")))
    assert _local_ips() == []
