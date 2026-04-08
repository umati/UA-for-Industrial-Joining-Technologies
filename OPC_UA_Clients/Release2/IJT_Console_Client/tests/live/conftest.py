import os
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

_CONSOLE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_CONSOLE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONSOLE_ROOT))


def _resolve_server_host_port() -> tuple[str, int]:
    """Resolve OPC UA server host/port from OPCUA_SERVER_URL env var (default: localhost:40451)."""
    url = os.environ.get("OPCUA_SERVER_URL", "")
    if url:
        try:
            # urlparse needs a scheme it understands; replace opc.tcp with http
            parsed = urlparse(url.replace("opc.tcp://", "http://"))
            host = parsed.hostname or "localhost"
            port = parsed.port or 40451
            return host, port
        except Exception:
            return "localhost", 40451  # malformed URL — fall back to defaults
    return "localhost", 40451


def _is_server_available(host: str = "localhost", port: int = 40451, timeout: float = 1.0) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    except OSError:
        return False
    finally:
        sock.close()


_SERVER_HOST, _SERVER_PORT = _resolve_server_host_port()
_SERVER_AVAILABLE = _is_server_available(_SERVER_HOST, _SERVER_PORT)


def pytest_collection_modifyitems(items):
    for item in items:
        if item.fspath and "live" in str(item.fspath):
            item.add_marker(pytest.mark.live)
            if not _SERVER_AVAILABLE:
                item.add_marker(
                    pytest.mark.skip(reason=f"OPC UA server not available at {_SERVER_HOST}:{_SERVER_PORT}")
                )
