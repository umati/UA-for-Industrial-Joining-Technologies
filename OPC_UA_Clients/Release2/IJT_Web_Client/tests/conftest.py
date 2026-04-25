import contextlib
import json
import os
import shutil
import sys
import tempfile
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
        _tmp_root = _project_root / "tmp"
        for _candidate in ("pytest", "pytest_tmp", f"pytest_session_{_pid}"):
            _candidate_path = _tmp_root / _candidate
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
        # All named candidates failed (e.g. ACL-locked by another user/process).
        # Try an auto-named dir in tmp/ as a last resort before falling through
        # to pytest's system-temp default.
        if _basetemp_chosen is None:
            with contextlib.suppress(OSError):
                _tmp_root.mkdir(parents=True, exist_ok=True)
                _auto = Path(tempfile.mkdtemp(dir=_tmp_root, prefix="pytest_auto_"))
                _basetemp_chosen = _auto
        if _basetemp_chosen is None:
            sys.stderr.write(
                "\n[conftest] WARNING: all local tmp/ candidates are ACL-locked. "
                "Falling back to system temp. Set IJT_USE_SYSTEM_BASETEMP=1 to silence this.\n"
            )
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


def _sessionfinish_cleanup(session: object) -> None:
    """Best-effort cleanup — called by pytest_sessionfinish inside a try/except."""
    _project_root = Path(__file__).resolve().parent.parent

    # Remove __pycache__ dirs.  os.walk is used instead of rglob so that
    # ACL-locked directories (e.g. tmp/pytest_session_* owned by another user)
    # are safely skipped via onerror rather than raising PermissionError.
    # "tmp" is pruned from the walk so we never attempt to traverse it at all.
    _skip_dirs = {".venv", "venv", "node_modules", "test-results", ".git", "tmp"}
    for _dirpath, _dirnames, _ in os.walk(_project_root, onerror=lambda _e: None):
        _dirnames[:] = [d for d in _dirnames if d not in _skip_dirs]
        if "__pycache__" in _dirnames:
            shutil.rmtree(Path(_dirpath) / "__pycache__", ignore_errors=True)
            _dirnames.remove("__pycache__")

    # Identify the active basetemp so we don't race with pytest's own cleanup.
    _active_basetemp: Path | None = None
    with contextlib.suppress(AttributeError, OSError):
        _bt = getattr(getattr(session, "config", None), "option", None)
        if _bt is not None:
            _bt = getattr(_bt, "basetemp", None)
        if _bt:
            _active_basetemp = Path(_bt).resolve()

    # Remove tool caches and stale pytest basetemp from tmp/.
    # Skips the active basetemp (pytest still holds handles on Windows).
    _tmp_root = _project_root / "tmp"
    if _tmp_root.exists():
        _managed = {"pytest", "pytest_tmp", "ruff-cache", "mypy-cache", "pip-audit-cache"}
        for child in list(_tmp_root.iterdir()):
            try:
                if _active_basetemp is not None and child.resolve() == _active_basetemp:
                    continue  # pytest still owns this dir — leave it for next-run cleanup
            except (AttributeError, OSError):
                # Cannot resolve path — skip pytest-named children conservatively
                if child.name.startswith("pytest"):
                    continue
            if child.name in _managed or child.name.startswith("pytest"):
                shutil.rmtree(child, ignore_errors=True)
        # Remove tmp/ itself if now empty (gitignored — safe to delete)
        with contextlib.suppress(OSError):
            _tmp_root.rmdir()


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """Remove __pycache__ dirs, tool caches, and stale pytest basetemp after every session.

    The currently active basetemp (session.config.option.basetemp) is intentionally
    skipped — pytest manages its own session dir and still holds Windows file handles
    at this point.  Only stale dirs from prior interrupted runs and tool caches are
    removed.  run_all_tests.py calls _cleanup_caches() independently (which covers the
    active basetemp at the start of the next run), so this hook is harmless when both
    run together.

    All cleanup is wrapped in a bare except so that filesystem errors (e.g. ACL-locked
    dirs left by a different OS user / sandbox) never cause pytest to exit non-zero.
    """
    try:
        _sessionfinish_cleanup(session)
    except Exception:  # noqa: BLE001
        return  # Best-effort cleanup — errors must never affect the test session exit code
