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
    # Default to a process-unique basetemp under tmp/ (stable in this environment).
    # Each pytest process owns its own tmp/pytest_session_<pid>/, so parallel suites
    # in IJT_Web_Client (or any other project run concurrently) cannot delete each
    # other's basetemp during pytest_sessionfinish or pytest_configure. Set
    # IJT_USE_SYSTEM_BASETEMP=1 to opt out and let pytest use system temp.
    _use_system = os.environ.get("IJT_USE_SYSTEM_BASETEMP", "").lower() in {"1", "true", "yes"}
    if config.option.basetemp is None and not _use_system:
        _basetemp_chosen: Path | None = None
        _pid = os.getpid()
        _tmp_root = _project_root / "tmp"
        # Process-unique candidate first. The legacy shared names ("pytest",
        # "pytest_tmp") are intentionally NOT in this list — those races are
        # exactly what the per-pid path eliminates.
        _candidate = _tmp_root / f"pytest_session_{_pid}"
        try:
            if _candidate.exists():
                # Same pid reused for a fresh session — safe to wipe our own dir.
                shutil.rmtree(_candidate)
            _candidate.mkdir(parents=True)
            _probe = _candidate / ".acl_probe"
            _probe.write_text("ok")
            _probe.unlink()
            _ = list(_candidate.iterdir())
            _basetemp_chosen = _candidate
        except OSError:
            _basetemp_chosen = None
        # If the named per-pid candidate failed (e.g. ACL-locked path), fall
        # back to an auto-named dir under tmp/ before pytest's system temp.
        if _basetemp_chosen is None:
            with contextlib.suppress(OSError):
                _tmp_root.mkdir(parents=True, exist_ok=True)
                _auto = Path(tempfile.mkdtemp(dir=_tmp_root, prefix=f"pytest_auto_{_pid}_"))
                _basetemp_chosen = _auto
        if _basetemp_chosen is None:
            sys.stderr.write(
                "\n[conftest] WARNING: tmp/ is not writable for this process. "
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
    # Critical: only delete OUR own basetemp's siblings if they're clearly stale
    # (older than the cutoff) — never blindly remove pytest_session_*  dirs since
    # they may belong to another live pytest process running in parallel.
    _tmp_root = _project_root / "tmp"
    if _tmp_root.exists():
        _managed_tool_caches = {"ruff-cache", "mypy-cache", "pip-audit-cache"}
        # 6 h is a safe staleness cutoff: longer than any legitimate IJT suite
        # (longest is web-client-e2e-regression at ~5 min) and short enough that
        # interrupted runs from earlier in the day still get cleaned.
        _stale_cutoff_seconds = 6 * 60 * 60
        import time as _time

        _now = _time.time()
        for child in list(_tmp_root.iterdir()):
            try:
                if _active_basetemp is not None and child.resolve() == _active_basetemp:
                    continue  # pytest still owns this dir — leave it for next-run cleanup
            except (AttributeError, OSError):
                # Cannot resolve path — skip pytest-named children conservatively
                if child.name.startswith("pytest"):
                    continue
            # Tool caches: always safe to remove (no inter-process state).
            if child.name in _managed_tool_caches:
                shutil.rmtree(child, ignore_errors=True)
                continue
            # pytest_session_<pid>/ and pytest_auto_<pid>_*/ from OTHER processes:
            # only delete if clearly stale. Otherwise leave them — another live
            # pytest may still be writing to its tmp_path tree.
            if child.name.startswith("pytest_session_") or child.name.startswith("pytest_auto_"):
                try:
                    if _now - child.stat().st_mtime > _stale_cutoff_seconds:
                        shutil.rmtree(child, ignore_errors=True)
                except OSError:
                    continue
                continue
            # Legacy shared "pytest"/"pytest_tmp" names: leave them alone. New
            # pytest_configure no longer creates these, so any survivor is from
            # an older runner and will be cleaned by run_all_tests._prepare_tmp_dir.
        # Remove tmp/ itself only if now empty (gitignored — safe to delete)
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
