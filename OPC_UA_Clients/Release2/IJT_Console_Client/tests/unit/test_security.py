"""
Security tests for IJT_Console_Client.

- No hardcoded passwords, tokens, or secrets in source files
- Endpoint strings with shell metacharacters are handled safely
- Input validation: extremely long strings do not crash
- bandit scan (skipped if bandit not installed)
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

_CONSOLE_ROOT = Path(__file__).resolve().parent.parent.parent

_SOURCE_FILES = [
    "opcua_client.py",
    "event_handler.py",
    "result_event_handler.py",
    "serialize_data.py",
    "utils.py",
    "ijt_logger.py",
    "method_caller.py",
    "client_config.py",
    "main.py",
    "event_types.py",
]

_BANDIT_AVAILABLE = (
    subprocess.run(
        [sys.executable, "-m", "bandit", "--version"],
        capture_output=True,
    ).returncode
    == 0
)


# ---------------------------------------------------------------------------
# No hardcoded secrets
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = [
    re.compile(r'password\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
    re.compile(r'token\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
    re.compile(r'secret\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
    re.compile(r'api_key\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
]


@pytest.mark.parametrize("filename", _SOURCE_FILES)
def test_no_hardcoded_secrets(filename):
    """Source files must not contain hardcoded passwords, tokens, or secrets."""
    path = _CONSOLE_ROOT / filename
    if not path.exists():
        pytest.skip(f"{filename} does not exist")
    content = path.read_text(encoding="utf-8")
    for pattern in _SECRET_PATTERNS:
        matches = pattern.findall(content)
        assert not matches, f"{filename} contains potential hardcoded secret: {matches}"


# ---------------------------------------------------------------------------
# Endpoint safety — shell metacharacters
# ---------------------------------------------------------------------------


def test_endpoint_with_shell_metacharacters_validate_url():
    """validate_url() must reject endpoints with shell metacharacters."""
    sys.path.insert(0, str(_CONSOLE_ROOT))
    from main import validate_url

    evil_url = "opc.tcp://localhost:4840; rm -rf /"
    result = validate_url(evil_url)
    assert ";" not in result


def test_endpoint_with_backtick_is_rejected():
    """validate_url() must reject endpoints with backtick characters."""
    from main import validate_url

    evil = "opc.tcp://`whoami`:4840"
    result = validate_url(evil)
    assert "`" not in result


# ---------------------------------------------------------------------------
# Input validation — long strings
# ---------------------------------------------------------------------------


def test_extremely_long_url_does_not_crash_validate_url():
    """A 10 000-char URL must not cause an exception."""
    from main import validate_url

    long_url = "A" * 10_000
    result = validate_url(long_url)
    assert isinstance(result, str)


def test_extremely_long_string_nodeid_to_str():
    """nodeid_to_str with a 10 000-char string input must not crash."""
    from utils import nodeid_to_str

    long_str = "x" * 10_000
    result = nodeid_to_str(long_str)
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# bandit scan (skip if not available)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _BANDIT_AVAILABLE, reason="bandit not installed")
def test_bandit_scan_no_medium_severity():
    """bandit must find no medium/high severity issues (-ll flag)."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bandit",
            "-r",
            ".",
            "-ll",
            "--exclude",
            "./tests,./venv,./.venv,./.venv-wsl,./.state",
        ],
        cwd=str(_CONSOLE_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"bandit found security issues:\n{result.stdout}\n{result.stderr}"
    )
