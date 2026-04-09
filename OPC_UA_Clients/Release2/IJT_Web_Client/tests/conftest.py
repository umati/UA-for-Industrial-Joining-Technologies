import json
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pytest


def pytest_configure(config):
    """Ensure tests/fixtures/ exists for tests that materialize JSON fixtures."""
    _project_root = Path(__file__).resolve().parent.parent
    _project_root.joinpath("tests", "fixtures").mkdir(parents=True, exist_ok=True)


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
    project_root = Path(__file__).resolve().parent.parent
    tmp_root = project_root / ".state" / "tmp" / "test-fixtures"
    tmp_root.mkdir(parents=True, exist_ok=True)
    path = tmp_root / f"ijt-web-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
