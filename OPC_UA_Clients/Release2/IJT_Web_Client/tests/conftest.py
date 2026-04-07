import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest


def pytest_configure(config):
    """Ensure tests/fixtures/ exists so --basetemp=tests/fixtures/tmp never fails."""
    Path(__file__).parent.parent.joinpath("tests", "fixtures").mkdir(parents=True, exist_ok=True)


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
def local_temp_dir(tmp_path):
    return tmp_path
