import socket
from urllib.parse import urlparse


def parse_endpoint_host_port(endpoint: str) -> tuple[str, int]:
    parsed = urlparse(endpoint)
    host = parsed.hostname or "localhost"
    port = parsed.port or 40451
    return host, port


def endpoint_reachable(endpoint: str, timeout: float = 1.0) -> bool:
    host, port = parse_endpoint_host_port(endpoint)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()
