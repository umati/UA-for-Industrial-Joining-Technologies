"""
Self-contained API contract tests for IJT_Web_Client Python modules.

Verifies that the web client's serialize_data and utils modules expose the
expected public API and produce correct output — without importing from any
other client.
"""
import json
from datetime import datetime, timezone

from asyncua import ua

from python import serialize_data as web_serialize
from python import utils as web_utils


def _as_object(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


# ---------------------------------------------------------------------------
# serialize_data API contract
# ---------------------------------------------------------------------------


def test_serialize_data_has_required_api():
    """Web client serialize_data must expose the expected public functions."""
    for fn_name in ("serialize_value", "serialize_tuple", "serialize_full_event",
                    "serialize_class_instance_as_dict"):
        assert hasattr(web_serialize, fn_name), (
            f"serialize_data missing required function: {fn_name}"
        )


def test_serialize_value_primitives():
    assert web_serialize.serialize_value(None) is None or \
           web_serialize.serialize_value(None) == "null" or \
           _as_object(web_serialize.serialize_value(None)) is None  # handles str-JSON variant
    assert _as_object(web_serialize.serialize_value(True)) is True
    assert _as_object(web_serialize.serialize_value(42)) == 42
    assert _as_object(web_serialize.serialize_value("hello")) == "hello"


def test_serialize_value_datetime_returns_iso():
    dt = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
    result = _as_object(web_serialize.serialize_value(dt))
    assert isinstance(result, str)
    assert "2025-06-15" in result


def test_serialize_full_event_dict():
    payload = {"a": 1, "b": [1, 2, 3]}
    result = web_serialize.serialize_full_event(payload)
    if isinstance(result, str):
        result = json.loads(result)
    assert result["a"] == 1
    assert result["b"] == [1, 2, 3]


def test_serialize_tuple_produces_valid_json():
    result = web_serialize.serialize_tuple([("key1", 1), ("key2", "hello")])
    parsed = json.loads(result)
    assert parsed["key1"] == 1
    assert parsed["key2"] == "hello"


def test_serialize_class_instance_as_dict_has_pythonclass_key():
    class _Sample:
        def __init__(self):
            self.x = 10
            self.y = "z"

    result = web_serialize.serialize_class_instance_as_dict(_Sample())
    if isinstance(result, str):
        result = json.loads(result)
    assert "pythonclass" in result
    assert result["x"] == 10


# ---------------------------------------------------------------------------
# utils API contract
# ---------------------------------------------------------------------------


def test_utils_has_required_api():
    """Web client utils must expose nodeid_to_str."""
    assert hasattr(web_utils, "nodeid_to_str"), "utils missing nodeid_to_str"


def test_nodeid_to_str_numeric():
    node = ua.NodeId(84, 0)
    result = web_utils.nodeid_to_str(node)
    assert "84" in result
    assert "0" in result


def test_nodeid_to_str_string_node():
    node = ua.NodeId("TighteningSystem", 1)
    result = web_utils.nodeid_to_str(node)
    assert "TighteningSystem" in result
    assert "1" in result

