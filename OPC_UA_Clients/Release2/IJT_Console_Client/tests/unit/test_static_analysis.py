"""
Static analysis tests.

- pylint score check (informational, parses score from output)
- bandit scan (skipped if not installed)
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_CONSOLE_ROOT = Path(__file__).resolve().parent.parent.parent

_MAIN_SOURCE_FILES = [
    "opcua_client.py",
    "event_handler.py",
    "result_event_handler.py",
    "serialize_data.py",
    "utils.py",
    "ijt_logger.py",
    "method_caller.py",
]

_PYLINT_AVAILABLE = shutil.which("pylint") is not None or (
    subprocess.run(
        [sys.executable, "-m", "pylint", "--version"],
        capture_output=True,
    ).returncode == 0
)

_BANDIT_AVAILABLE = subprocess.run(
    [sys.executable, "-m", "bandit", "--version"],
    capture_output=True,
).returncode == 0


def _parse_pylint_score(output: str) -> float | None:
    """Extract the pylint score from 'Your code has been rated at X.XX/10'."""
    match = re.search(r"rated at\s+([\-\d.]+)/10", output)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


@pytest.mark.skipif(not _PYLINT_AVAILABLE, reason="pylint not installed")
def test_pylint_score_above_threshold():
    """pylint must score >= 7.0 on all main source modules."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pylint",
            "--disable=C,R,W0611,W0401",  # skip convention/refactor, unused-import
        ] + _MAIN_SOURCE_FILES,
        cwd=str(_CONSOLE_ROOT),
        capture_output=True,
        text=True,
    )
    combined = result.stdout + result.stderr
    score = _parse_pylint_score(combined)

    # If we can parse the score, check it directly
    if score is not None:
        assert score >= 7.0, (
            f"pylint score {score:.2f}/10 is below threshold 7.0:\n{result.stdout}"
        )
    else:
        # Couldn't parse score — only fail on fatal/usage errors (exit codes 1, 32)
        assert result.returncode not in (1, 32), (
            f"pylint failed with exit code {result.returncode}:\n{result.stdout}\n{result.stderr}"
        )


@pytest.mark.skipif(not _BANDIT_AVAILABLE, reason="bandit not installed")
def test_bandit_no_high_severity():
    """bandit must find no high-severity issues."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bandit",
            "-r",
            ".",
            "-ll",
            "--exclude",
            "./tests,./venv,./.state",
        ],
        cwd=str(_CONSOLE_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"bandit found security issues:\n{result.stdout}\n{result.stderr}"
    )
