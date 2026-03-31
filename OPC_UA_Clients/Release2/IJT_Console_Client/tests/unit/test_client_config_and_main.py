"""
Comprehensive tests for:
- IJT_Console_Client/client_config.py  (URL_PATTERN, SERVER_URL, ENABLE_RESULT_FILE_LOGGING)
- IJT_Console_Client/main.py           (validate_url)
"""

import os
import re
import pytest
from pathlib import Path
from unittest.mock import patch

from client_config import URL_PATTERN, SERVER_URL, ENABLE_RESULT_FILE_LOGGING
from main import validate_url


# ---------------------------------------------------------------------------
# client_config.py
# ---------------------------------------------------------------------------


class TestUrlPattern:
    def test_matches_localhost_default_port(self):
        assert URL_PATTERN.match("opc.tcp://localhost:40451")

    def test_matches_localhost_standard_port(self):
        assert URL_PATTERN.match("opc.tcp://localhost:4840")

    def test_matches_ip_address(self):
        assert URL_PATTERN.match("opc.tcp://192.168.1.100:4840")

    def test_matches_hostname_with_dashes(self):
        assert URL_PATTERN.match("opc.tcp://my-machine.local:4840")

    def test_matches_hostname_with_dots(self):
        assert URL_PATTERN.match("opc.tcp://server.corp.example.com:4840")

    def test_matches_single_char_hostname(self):
        assert URL_PATTERN.match("opc.tcp://a:4840")

    def test_rejects_http_scheme(self):
        assert not URL_PATTERN.match("http://localhost:4840")

    def test_rejects_missing_port(self):
        # Pattern requires :\d+ — must have port
        full = "opc.tcp://localhost"
        assert not URL_PATTERN.fullmatch(full)

    def test_rejects_empty_string(self):
        assert not URL_PATTERN.match("")

    def test_rejects_ws_scheme(self):
        assert not URL_PATTERN.match("ws://localhost:4840")

    def test_returns_match_object_not_bool(self):
        """URL_PATTERN.match() returns a Match object, not None."""
        m = URL_PATTERN.match("opc.tcp://localhost:4840")
        assert m is not None
        assert hasattr(m, "group")


class TestServerUrlDefault:
    def test_server_url_is_correct_default(self):
        assert SERVER_URL == "opc.tcp://localhost:40451"

    def test_server_url_matches_pattern(self):
        assert URL_PATTERN.match(SERVER_URL)


class TestResultFileLogging:
    def test_enable_result_file_logging_is_true(self):
        assert ENABLE_RESULT_FILE_LOGGING is True


# ---------------------------------------------------------------------------
# main.py — validate_url
# ---------------------------------------------------------------------------


class TestValidateUrl:
    def test_valid_url_is_returned_unchanged(self):
        url = "opc.tcp://192.168.1.50:4840"
        assert validate_url(url) == url

    def test_localhost_url_is_returned(self):
        url = "opc.tcp://localhost:40451"
        assert validate_url(url) == url

    def test_invalid_url_falls_back_to_env_var(self):
        env_url = "opc.tcp://env-server:4840"
        with patch.dict(os.environ, {"OPCUA_SERVER_URL": env_url}):
            result = validate_url("not-a-valid-url")
        assert result == env_url

    def test_none_url_with_env_var(self):
        env_url = "opc.tcp://env-host:4840"
        with patch.dict(os.environ, {"OPCUA_SERVER_URL": env_url}):
            result = validate_url(None)
        assert result == env_url

    def test_empty_string_with_valid_env_var(self):
        env_url = "opc.tcp://env-host:4840"
        with patch.dict(os.environ, {"OPCUA_SERVER_URL": env_url}):
            result = validate_url("")
        assert result == env_url

    def test_invalid_url_invalid_env_falls_back_to_default(self):
        with patch.dict(os.environ, {"OPCUA_SERVER_URL": "not-valid-either"}, clear=False):
            # Remove OPCUA_SERVER_URL if set elsewhere and set to invalid
            result = validate_url("also-invalid")
        # Falls back to DEFAULT_SERVER_URL = SERVER_URL
        assert result == SERVER_URL

    def test_env_var_invalid_format_falls_back_to_default(self):
        with patch.dict(os.environ, {"OPCUA_SERVER_URL": "http://wrong-scheme:4840"}):
            result = validate_url(None)
        assert result == SERVER_URL

    def test_no_env_var_falls_back_to_default(self):
        env = {k: v for k, v in os.environ.items() if k != "OPCUA_SERVER_URL"}
        with patch.dict(os.environ, env, clear=True):
            result = validate_url(None)
        assert result == SERVER_URL

    def test_valid_url_preferred_over_env_var(self):
        """When a valid URL is supplied, it takes precedence over env var."""
        provided = "opc.tcp://provided-host:9999"
        env_url = "opc.tcp://env-host:4840"
        with patch.dict(os.environ, {"OPCUA_SERVER_URL": env_url}):
            result = validate_url(provided)
        assert result == provided

    def test_env_var_with_path_suffix_is_rejected_by_fullmatch(self):
        """Env var URL with trailing path must be rejected (fullmatch, not match).

        Regression test for H-2: using re.match() only validates the prefix,
        allowing bypass like 'opc.tcp://server:4840/../../etc/passwd'.
        fullmatch() must be used so the entire string is validated.
        """
        evil_env = "opc.tcp://server:4840/../../etc/passwd"
        with patch.dict(os.environ, {"OPCUA_SERVER_URL": evil_env}):
            result = validate_url(None)
        # Must fall back to the safe default, not return the evil URL
        assert result == SERVER_URL
        assert "etc/passwd" not in result

    def test_env_var_with_semicolon_is_rejected(self):
        """Env var URL with shell injection characters must be rejected."""
        evil_env = "opc.tcp://localhost:4840; rm -rf /"
        with patch.dict(os.environ, {"OPCUA_SERVER_URL": evil_env}):
            result = validate_url(None)
        assert result == SERVER_URL


class TestUrlPatternNotDuplicatedInMain:
    """Regression test for L-2: URL_PATTERN must not be defined in main.py.

    It should be imported from client_config only.
    """

    _MAIN_PATH = Path(__file__).resolve().parent.parent.parent / "main.py"

    def test_url_pattern_not_redefined_in_main(self):
        content = self._MAIN_PATH.read_text(encoding="utf-8")
        assert "URL_PATTERN = re.compile" not in content, (
            "URL_PATTERN is re-defined in main.py — it should only be imported from client_config.py"
        )

    def test_url_pattern_imported_from_client_config_in_main(self):
        content = self._MAIN_PATH.read_text(encoding="utf-8")
        assert "from client_config import" in content and "URL_PATTERN" in content, (
            "URL_PATTERN should be imported from client_config in main.py"
        )
