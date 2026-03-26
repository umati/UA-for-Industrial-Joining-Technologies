"""Static-analysis enforcement tests.

These tests run external analysis tools as CI gates.  If a tool is not
installed the test is skipped rather than failing (useful for minimal
environments).  They are designed to fail if someone introduces code that
violates lint or security policies.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Resolve src/python relative to this file so tests work from any cwd.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SRC_PYTHON = _PROJECT_ROOT / "src" / "python"
_SRC_JS = _PROJECT_ROOT / "src" / "javascripts"


def _tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def _npm_available() -> bool:
    return shutil.which("npm") is not None


def _is_wsl() -> bool:
    """Detect WSL: Linux kernel but accessing a Windows NTFS filesystem."""
    import platform
    release = platform.release().lower()
    return "microsoft" in release or "wsl" in release


def _eslint_executable() -> bool:
    """Return True only if running npm run lint is expected to work.

    Skipped on WSL because Windows node_modules on /mnt/c/ NTFS are far too
    slow for the 30 s pytest-timeout (cross-filesystem overhead).  Native
    Windows and Linux CI both have platform-native node_modules and work fine.
    """
    if not _npm_available():
        return False
    return not _is_wsl()


# ===========================================================================
# 1. Pylint — Python source quality gate
# ===========================================================================


@pytest.mark.skipif(
    not _tool_available("pylint"),
    reason="pylint not installed — skipping quality gate",
)
def test_pylint_passes_minimum_score():
    """pylint score must be >= 7.0 for src/python/."""
    result = subprocess.run(
        [
            sys.executable, "-m", "pylint",
            str(_SRC_PYTHON),
            "--fail-under=7.0",
            "--output-format=text",
            "--score=yes",
        ],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"pylint exited with code {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


# ===========================================================================
# 2. Bandit — Python security scanner
# ===========================================================================


@pytest.mark.skipif(
    not _tool_available("bandit"),
    reason="bandit not installed — skipping security scan",
)
def test_bandit_no_high_severity_issues():
    """bandit must find no HIGH or MEDIUM severity issues in src/python/."""
    result = subprocess.run(
        [
            "bandit",
            "-r", str(_SRC_PYTHON),
            "-ll",          # only MEDIUM and above
            "--exit-zero",  # don't fail on LOW — only care about return value
            "-f", "txt",
        ],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )
    # Exit code 1 means issues found; exit code 0 means clean
    assert result.returncode == 0, (
        f"bandit found HIGH/MEDIUM issues.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


# ===========================================================================
# 3. ESLint — JavaScript source quality gate
# ===========================================================================


@pytest.mark.skipif(
    not _eslint_executable(),
    reason="eslint binary not executable in this environment — skipping JS lint gate",
)
def test_eslint_passes():
    """npm run lint must exit 0 (no ESLint errors in src/javascripts/)."""
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    result = subprocess.run(
        [npm_cmd, "run", "lint"],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"ESLint failed (exit {result.returncode}).\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
