"""Unit tests for effective config env parsing and CLI failure modes."""

import pytest

from src.cli import main
from src.effective_config import parse_env_float, parse_env_int


def test_parse_env_int_invalid():
    with pytest.raises(ValueError, match="Invalid integer"):
        parse_env_int("OPCUA_WORKERS", "not-a-number")


def test_parse_env_float_invalid():
    with pytest.raises(ValueError, match="Invalid float"):
        parse_env_float("OPCUA_BURST_DELAY", "fast")


def test_cli_invalid_opcua_workers_exits(monkeypatch):
    monkeypatch.setenv("OPCUA_WORKERS", "abc")
    with pytest.raises(SystemExit):
        main(["-e", "opc.tcp://127.0.0.1:4840"])
