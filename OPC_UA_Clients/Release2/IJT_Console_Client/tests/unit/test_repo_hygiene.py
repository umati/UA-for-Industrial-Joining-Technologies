"""
Repository hygiene tests.

- No __pycache__ tracked by git in this directory
- No .pytest_cache tracked
- No hardcoded absolute paths (like C:\\DDrive\\...) in source code
- requirements.txt exists and is non-empty
- All .py files have at most 500 lines (complexity gate)
"""

import subprocess
from pathlib import Path

import pytest

_CONSOLE_ROOT = Path(__file__).resolve().parent.parent.parent

_SOURCE_FILES = list(_CONSOLE_ROOT.glob("*.py"))

# setup_client.py is a launcher/setup script and is intentionally larger
# run_all_tests.py is a test orchestrator (not business logic) and is intentionally larger
_LINE_COUNT_EXCLUDED = {"setup_client.py", "run_all_tests.py"}


# ---------------------------------------------------------------------------
# Line count gate (complexity)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source_file",
    [f.name for f in _SOURCE_FILES if f.name not in _LINE_COUNT_EXCLUDED],
)
def test_source_file_under_500_lines(source_file):
    """All .py source files must be under 500 lines (complexity gate)."""
    path = _CONSOLE_ROOT / source_file
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 500, (
        f"{source_file} has {len(lines)} lines (limit: 500). Consider splitting into smaller modules."
    )


# ---------------------------------------------------------------------------
# No hardcoded absolute paths in source
# ---------------------------------------------------------------------------

_ABSOLUTE_PATH_PATTERNS = [
    "C:\\\\DDrive",
    "C:/DDrive",
    "/home/",
    "/Users/",
    "C:\\\\Users",
]


@pytest.mark.parametrize("source_file", [f.name for f in _SOURCE_FILES])
def test_no_hardcoded_absolute_paths(source_file):
    """Source files must not contain hardcoded absolute paths."""
    path = _CONSOLE_ROOT / source_file
    content = path.read_text(encoding="utf-8")
    for pattern in _ABSOLUTE_PATH_PATTERNS:
        assert pattern not in content, f"{source_file} contains hardcoded absolute path: {pattern!r}"


# ---------------------------------------------------------------------------
# requirements.txt
# ---------------------------------------------------------------------------


def test_requirements_txt_exists():
    assert (_CONSOLE_ROOT / "requirements.txt").exists()


def test_requirements_txt_is_nonempty():
    content = (_CONSOLE_ROOT / "requirements.txt").read_text(encoding="utf-8").strip()
    assert content, "requirements.txt is empty"


# ---------------------------------------------------------------------------
# Git hygiene — no compiled artifacts tracked
# ---------------------------------------------------------------------------


def _git_is_available() -> bool:
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:  # noqa: BLE001 — intentional broad catch for availability check
        return False


_GIT_AVAILABLE = _git_is_available()


@pytest.mark.skipif(not _GIT_AVAILABLE, reason="git not available")
def test_no_pycache_tracked_in_console_client():
    """__pycache__ directories must not be tracked by git in this client."""
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "__pycache__"],
        cwd=str(_CONSOLE_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, "__pycache__ should not be tracked by git"


@pytest.mark.skipif(not _GIT_AVAILABLE, reason="git not available")
def test_no_pytest_cache_tracked():
    """'.pytest_cache' must not be tracked by git."""
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".pytest_cache"],
        cwd=str(_CONSOLE_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, ".pytest_cache should not be tracked by git"
