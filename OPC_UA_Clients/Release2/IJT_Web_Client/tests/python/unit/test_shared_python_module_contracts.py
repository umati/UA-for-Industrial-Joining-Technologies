import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from asyncua import ua

from Python import serialize_data as web_serialize
from Python import utils as web_utils

# Console Client lives two levels above the Web Client root (Release2/IJT_Console_Client)
_CONSOLE_DIR = (Path(__file__).resolve().parents[4] / "IJT_Console_Client").resolve()
_CONSOLE_AVAILABLE = _CONSOLE_DIR.is_dir()


def _load_console_module(module_name: str):
    if not _CONSOLE_AVAILABLE:
        pytest.skip(f"Console Client not available at {_CONSOLE_DIR} (Docker/isolated env)")
    if str(_CONSOLE_DIR) not in sys.path:
        sys.path.insert(0, str(_CONSOLE_DIR))
    return importlib.import_module(module_name)


def _as_object(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def test_serialize_data_contract_matches_for_common_payloads():
    console_serialize = _load_console_module("serialize_data")

    payload = {
        "a": 1,
        "b": True,
        "c": [1, "x", {"z": 3}],
        "d": datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        "e": None,
    }

    web_value = _as_object(web_serialize.serializeValue(payload))
    console_value = _as_object(console_serialize.serializeValue(payload))
    assert web_value == console_value

    web_tuple = _as_object(web_serialize.serializeTuple([("alpha", payload), ("beta", 42)]))
    console_tuple = _as_object(console_serialize.serializeTuple([("alpha", payload), ("beta", 42)]))
    assert web_tuple == console_tuple

    assert web_serialize.serializeFullEvent(payload) == console_serialize.serializeFullEvent(payload)


def test_utils_nodeid_format_contract_matches():
    console_utils = _load_console_module("utils")

    numeric = ua.NodeId(84, 0)
    string_node = ua.NodeId("TighteningSystem", 1)

    assert web_utils.nodeid_to_str(numeric) == console_utils.nodeid_to_str(numeric)
    assert web_utils.nodeid_to_str(string_node) == console_utils.nodeid_to_str(string_node)
