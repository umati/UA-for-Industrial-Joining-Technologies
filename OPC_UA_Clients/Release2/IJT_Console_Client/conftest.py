"""
conftest.py — Root-level pytest session configuration for IJT Console Client.

Sets basetemp to <project-root>/tmp/pytest (absolute, CWD-independent) so that
all pytest temp directories always land inside this project regardless of where
the test runner is invoked from (repo root, client dir, CI, etc.).

Set IJT_USE_SYSTEM_BASETEMP=1 to opt out and let pytest choose its own basetemp
(useful when the project filesystem rejects the ACL probe, e.g. on some network
mounts or read-only overlays).

Probe order: tmp/pytest → tmp/pytest_tmp → tmp/pytest_session_<pid>
If all three fail the ACL probe, basetemp falls through to pytest's default
(system temp).  This pattern is shared across all three client conftest files
— keep them in sync.
"""

import os
import shutil
from pathlib import Path


def pytest_configure(config):
    """Set absolute basetemp to keep all pytest temp files inside this project."""
    _project_root = Path(__file__).resolve().parent
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
