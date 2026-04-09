import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest


def pytest_configure(config):
    """Ensure tests/fixtures/ exists and pin basetemp to an absolute project-local path.

    Using an absolute path for basetemp guarantees correct resolution regardless
    of the working directory from which pytest is invoked (CI, repo root, etc.).
    """
    _project_root = Path(__file__).resolve().parent.parent
    _basetemp = _project_root / "tmp" / "pytest"
    _basetemp.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = str(_basetemp)
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
def local_temp_dir(tmp_path):
    return tmp_path
