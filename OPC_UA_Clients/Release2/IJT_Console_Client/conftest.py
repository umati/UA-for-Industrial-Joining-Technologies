"""
conftest.py — Root-level pytest session configuration for IJT Console Client.

Sets basetemp to <project-root>/tmp/pytest (absolute, CWD-independent) so that
all pytest temp directories always land inside this project regardless of where
the test runner is invoked from (repo root, client dir, CI, etc.).

Set IJT_USE_SYSTEM_BASETEMP=1 to opt out and let pytest choose its own basetemp
(useful when the project filesystem rejects the ACL probe, e.g. on some network
mounts or read-only overlays).

Probe order: tmp/pytest → tmp/pytest_tmp → tmp/pytest_session_<pid> → tmp/pytest_auto_<pid> (mkdtemp)
If all fail the ACL probe, logs a warning to stderr and basetemp falls through to pytest's default
(system temp).  This pattern is shared across all three client conftest files
— keep them in sync.
"""

import contextlib
import os
import shutil
import sys
import tempfile
from pathlib import Path


def pytest_configure(config):
    """Set absolute basetemp to keep all pytest temp files inside this project."""
    _project_root = Path(__file__).resolve().parent
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


def _sessionfinish_cleanup(session: object) -> None:
    """Best-effort cleanup — called by pytest_sessionfinish inside a try/except."""
    _project_root = Path(__file__).resolve().parent

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

    # Remove tool caches and stale pytest basetemp from tmp/
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
