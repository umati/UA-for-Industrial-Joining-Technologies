"""
Unit tests for Python/network_utils.py

Covers:
- parse_endpoint_host_port(): well-formed URL, no port (uses default), no host
- endpoint_reachable(): success (connect_ex returns 0), failure (returns non-0),
  exception path (socket raises)
"""

import socket
from unittest.mock import MagicMock, patch

import pytest

from python.network_utils import endpoint_reachable, parse_endpoint_host_port

# ---------------------------------------------------------------------------
# parse_endpoint_host_port
# ---------------------------------------------------------------------------


def test_parse_endpoint_host_port_full_url():
    host, port = parse_endpoint_host_port("opc.tcp://my-server.example.com:4840")
    assert host == "my-server.example.com"
    assert port == 4840


def test_parse_endpoint_host_port_localhost():
    host, port = parse_endpoint_host_port("opc.tcp://localhost:40451")
    assert host == "localhost"
    assert port == 40451


def test_parse_endpoint_host_port_ip_address():
    host, port = parse_endpoint_host_port("opc.tcp://192.168.1.100:4840")
    assert host == "192.168.1.100"
    assert port == 4840


def test_parse_endpoint_host_port_no_port_uses_default():
    host, port = parse_endpoint_host_port("opc.tcp://some-server")
    assert host == "some-server"
    assert port == 40451  # default fallback


def test_parse_endpoint_host_port_no_host_uses_localhost_fallback():
    # urlparse with empty netloc gives None hostname
    host, port = parse_endpoint_host_port("")
    assert host == "localhost"
    assert port == 40451


def test_parse_endpoint_host_port_with_path():
    host, port = parse_endpoint_host_port("opc.tcp://server:4840/UA/Server")
    assert host == "server"
    assert port == 4840


# ---------------------------------------------------------------------------
# endpoint_reachable
# ---------------------------------------------------------------------------


def test_endpoint_reachable_returns_true_when_connect_ex_is_zero():
    mock_sock = MagicMock()
    mock_sock.connect_ex.return_value = 0

    with patch("python.network_utils.socket.socket", return_value=mock_sock):
        result = endpoint_reachable("opc.tcp://localhost:40451", timeout=0.1)

    assert result is True
    mock_sock.settimeout.assert_called_once_with(0.1)
    mock_sock.close.assert_called_once()


def test_endpoint_reachable_returns_false_when_connect_ex_is_nonzero():
    mock_sock = MagicMock()
    mock_sock.connect_ex.return_value = 111  # ECONNREFUSED on Linux

    with patch("python.network_utils.socket.socket", return_value=mock_sock):
        result = endpoint_reachable("opc.tcp://localhost:40451", timeout=0.1)

    assert result is False
    mock_sock.close.assert_called_once()


def test_endpoint_reachable_closes_socket_on_exception():
    """socket.close() must be called even when connect_ex raises."""
    mock_sock = MagicMock()
    mock_sock.connect_ex.side_effect = OSError("Network unreachable")

    with patch("python.network_utils.socket.socket", return_value=mock_sock):
        with pytest.raises(OSError):
            endpoint_reachable("opc.tcp://unreachable:4840", timeout=0.1)

    mock_sock.close.assert_called_once()


def test_endpoint_reachable_default_timeout():
    """Default timeout=1.0 is passed to settimeout."""
    mock_sock = MagicMock()
    mock_sock.connect_ex.return_value = 0

    with patch("python.network_utils.socket.socket", return_value=mock_sock):
        endpoint_reachable("opc.tcp://localhost:4840")

    mock_sock.settimeout.assert_called_once_with(1.0)


def test_endpoint_reachable_uses_AF_INET_SOCK_STREAM():
    """socket is created with AF_INET, SOCK_STREAM."""
    with patch("python.network_utils.socket.socket") as mock_socket_cls:
        mock_socket_cls.return_value.__enter__ = MagicMock()
        mock_inst = MagicMock()
        mock_inst.connect_ex.return_value = 0
        mock_socket_cls.return_value = mock_inst
        endpoint_reachable("opc.tcp://localhost:4840")

    mock_socket_cls.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
