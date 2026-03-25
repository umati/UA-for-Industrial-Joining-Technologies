import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

# Ensure src/ is on sys.path so Python/ modules are importable
# from any test file regardless of which directory pytest is invoked from.
_WEB_CLIENT_ROOT = Path(__file__).resolve().parent.parent
if str(_WEB_CLIENT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_WEB_CLIENT_ROOT / "src"))


@dataclass
class FakeWebSocket:
    sent_messages: list[str] = field(default_factory=list)

    async def send(self, payload: str):
        self.sent_messages.append(payload)

    async def close(self):
        return None


@pytest.fixture
def fake_websocket():
    return FakeWebSocket()


@pytest.fixture
def decode_last_message():
    def _decode(fake_ws: FakeWebSocket):
        assert fake_ws.sent_messages, "No websocket payloads were sent"
        return json.loads(fake_ws.sent_messages[-1])

    return _decode


@pytest.fixture
def local_temp_dir():
    path = Path("tests") / "fixtures" / "tmp"
    path.mkdir(parents=True, exist_ok=True)
    return path
