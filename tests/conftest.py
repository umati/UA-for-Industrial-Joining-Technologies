"""conftest.py — Suppress bytecode generation and clean root tool caches after pytest."""

from __future__ import annotations

import contextlib
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True


def pytest_sessionfinish(session, exitstatus):
    """Remove root tool caches (tmp/ruff-cache, tmp/mypy-cache) after root pytest runs."""
    del session, exitstatus
    if os.environ.get("IJT_PRESERVE_TEST_ARTIFACTS", "").lower() in {"1", "true", "yes", "on"}:
        return
    repo_root = Path(__file__).resolve().parents[1]
    tmp_root = repo_root / "tmp"
    if tmp_root.exists():
        for name in ("ruff-cache", "mypy-cache", "pytest", "pytest_tmp", "pytest-root-tests"):
            shutil.rmtree(tmp_root / name, ignore_errors=True)
        with contextlib.suppress(OSError):
            tmp_root.rmdir()
