import socket
import sys
from pathlib import Path

import pytest

_CONSOLE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_CONSOLE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONSOLE_ROOT))


def _is_server_available(host: str = "localhost", port: int = 40451, timeout: float = 1.0) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    except OSError:
        return False
    finally:
        sock.close()


_SERVER_AVAILABLE = _is_server_available()


def pytest_collection_modifyitems(items):
    for item in items:
        if item.fspath and "live" in str(item.fspath):
            item.add_marker(pytest.mark.live)
            if not _SERVER_AVAILABLE:
                item.add_marker(pytest.mark.skip(reason="OPC UA server not available at localhost:40451"))
