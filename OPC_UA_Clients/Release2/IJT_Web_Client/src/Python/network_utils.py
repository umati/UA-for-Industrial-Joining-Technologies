"""
Network utility helpers shared by backend and tests.

Canonical location: Python/network_utils.py
The project root network_utils.py is a thin re-export kept for backward compatibility.
"""

import socket
from urllib.parse import urlparse


def parse_endpoint_host_port(endpoint: str) -> tuple[str, int]:
    """Parse an OPC UA endpoint URL and return (host, port)."""
    parsed = urlparse(endpoint)
    host = parsed.hostname or "localhost"
    port = parsed.port or 40451
    return host, port


def endpoint_reachable(endpoint: str, timeout: float = 1.0) -> bool:
    """Return True if the OPC UA endpoint TCP port is reachable within *timeout* seconds."""
    host, port = parse_endpoint_host_port(endpoint)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()
