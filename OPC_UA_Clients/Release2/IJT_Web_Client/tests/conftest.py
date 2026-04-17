import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import pytest


def pytest_configure(config):
    """Ensure tests/fixtures/ exists for tests that materialize JSON fixtures."""
    _project_root = Path(__file__).resolve().parent.parent
    _project_root.joinpath("tests", "fixtures").mkdir(parents=True, exist_ok=True)
    # Default to repo-local basetemp (stable in this environment). Set
    # IJT_USE_SYSTEM_BASETEMP=1 to opt out and let pytest use system temp.
    _use_system = os.environ.get("IJT_USE_SYSTEM_BASETEMP", "").lower() in {"1", "true", "yes"}
    if config.option.basetemp is None and not _use_system:
        _basetemp_chosen = None
        _pid = os.getpid()
        for _candidate in ("pytest", "pytest_tmp", f"pytest_session_{_pid}"):
            _candidate_path = _project_root / "tmp" / _candidate
            try:
                if _candidate_path.exists():
                    shutil.rmtree(_candidate_path)
                _candidate_path.mkdir(parents=True)
                _probe = _candidate_path / ".acl_probe"
                _probe.write_text("ok")
                _probe.unlink()
                _ = list(_candidate_path.iterdir())
                _basetemp_chosen = _candidate_path
                break
            except OSError:
                continue
        if _basetemp_chosen is not None:
            config.option.basetemp = str(_basetemp_chosen)


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
    """Provide a per-test temporary directory.

    Delegates to pytest's built-in ``tmp_path`` so cleanup is always handled by
    pytest under the same OS user that created the directory.  Using a custom
    path (e.g. ``.state/tmp/``) caused directories to be owned by whichever
    process last ran the test suite; a different-user owner blocks deletion on
    Windows even when the current user has Modify rights.

    Retention is governed by ``tmp_path_retention_policy = "failed"`` in
    pyproject.toml — only failing-test directories survive past the run.
    """
    return tmp_path
