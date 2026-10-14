"""Unit tests for host fingerprint collection."""

from src.host_fingerprint import collect_host_fingerprint


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


def test_fingerprint_no_redact_can_include_network():
    fp = collect_host_fingerprint(include_network=True, redact=False)
    assert "hostname" in fp
