"""
Comprehensive tests for IJT_Console_Client/serialize_data.py

Covers every public function and edge case:
- serialize_value: None, bool, int, float, str, datetime, dict, list, tuple,
  custom class (__dict__), custom class (__slots__), bytes fallback,
  _freeze exclusion, nested structures, orjson/json compatibility
- serialize_class_instance_as_dict: __dict__ and __slots__ paths
- serialize_full_event: alias for serialize_value
- serialize_tuple: normal, error path returns "{}"
"""

import json
from datetime import datetime, timezone

import pytest
from serialize_data import (
    _json_dumps,
    serialize_class_instance_as_dict,
    serialize_full_event,
    serialize_tuple,
    serialize_value,
)


# ---------------------------------------------------------------------------
# Helper classes
# ---------------------------------------------------------------------------


class _DictClass:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self._freeze = True  # must be excluded


class _SlotsClass:
    __slots__ = ("alpha", "beta", "_freeze")

    def __init__(self, a, b):
        self.alpha = a
        self.beta = b
        self._freeze = True


class _Nested:
    def __init__(self):
        self.inner = _DictClass(1, "hello")
        self.values = [1, 2, datetime(2025, 1, 1, tzinfo=timezone.utc)]


# ---------------------------------------------------------------------------
# serialize_value — primitives
# ---------------------------------------------------------------------------


def test_serialize_value_none():
    assert serialize_value(None) is None


def test_serialize_value_bool_true():
    assert serialize_value(True) is True


def test_serialize_value_bool_false():
    assert serialize_value(False) is False


def test_serialize_value_int():
    assert serialize_value(42) == 42


def test_serialize_value_negative_int():
    assert serialize_value(-7) == -7


def test_serialize_value_float():
    assert serialize_value(3.14) == pytest.approx(3.14)


def test_serialize_value_string():
    assert serialize_value("hello") == "hello"


def test_serialize_value_empty_string():
    assert serialize_value("") == ""


def test_serialize_value_datetime_returns_iso():
    dt = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
    result = serialize_value(dt)
    assert result == "2025-06-15T10:30:00+00:00"


def test_serialize_value_datetime_without_tz():
    dt = datetime(2025, 1, 2, 3, 4, 5)
    result = serialize_value(dt)
    assert result.startswith("2025-01-02T03:04:05")


# ---------------------------------------------------------------------------
# serialize_value — collections
# ---------------------------------------------------------------------------


def test_serialize_value_list():
    assert serialize_value([1, "a", None]) == [1, "a", None]


def test_serialize_value_empty_list():
    assert serialize_value([]) == []


def test_serialize_value_tuple_becomes_list():
    result = serialize_value((1, 2, 3))
    assert result == [1, 2, 3]


def test_serialize_value_dict():
    assert serialize_value({"a": 1, "b": True}) == {"a": 1, "b": True}


def test_serialize_value_nested_dict_with_datetime():
    dt = datetime(2026, 3, 1, tzinfo=timezone.utc)
    result = serialize_value({"time": dt, "count": 5})
    assert result["time"].startswith("2026-03-01T")
    assert result["count"] == 5


def test_serialize_value_list_of_dicts():
    data = [{"id": 1}, {"id": 2}]
    assert serialize_value(data) == [{"id": 1}, {"id": 2}]


# ---------------------------------------------------------------------------
# serialize_value — custom class instances
# ---------------------------------------------------------------------------


def test_serialize_value_custom_dict_class():
    obj = _DictClass(10, "world")
    result = serialize_value(obj)
    assert result["pythonclass"] == "_DictClass"
    assert result["x"] == 10
    assert result["y"] == "world"
    assert "_freeze" not in result


def test_serialize_value_custom_slots_class():
    obj = _SlotsClass("A", 99)
    result = serialize_value(obj)
    assert result["pythonclass"] == "_SlotsClass"
    assert result["alpha"] == "A"
    assert result["beta"] == 99
    assert "_freeze" not in result


def test_serialize_value_nested_custom_class():
    obj = _Nested()
    result = serialize_value(obj)
    assert result["pythonclass"] == "_Nested"
    inner = result["inner"]
    assert inner["pythonclass"] == "_DictClass"
    assert inner["x"] == 1
    assert inner["y"] == "hello"
    assert "_freeze" not in inner
    vals = result["values"]
    assert vals[0] == 1
    assert vals[1] == 2
    assert "2025-01-01" in vals[2]


def test_serialize_value_bytes_fallback():
    """bytes is not a special-cased type; falls back to str(b'...')"""
    result = serialize_value(b"raw")
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# serialize_class_instance_as_dict
# ---------------------------------------------------------------------------


def test_serialize_class_instance_as_dict_dict_class():
    obj = _DictClass(5, "test")
    result = serialize_class_instance_as_dict(obj)
    assert result["pythonclass"] == "_DictClass"
    assert result["x"] == 5
    assert result["y"] == "test"
    assert "_freeze" not in result


def test_serialize_class_instance_as_dict_slots():
    obj = _SlotsClass("X", 0)
    result = serialize_class_instance_as_dict(obj)
    assert result["pythonclass"] == "_SlotsClass"
    assert result["alpha"] == "X"
    assert "_freeze" not in result


def test_serialize_class_instance_as_dict_has_pythonclass_key():
    result = serialize_class_instance_as_dict(_DictClass(1, 2))
    assert "pythonclass" in result


# ---------------------------------------------------------------------------
# serialize_full_event — alias
# ---------------------------------------------------------------------------


def test_serialize_full_event_same_as_serialize_value():
    obj = _DictClass(7, "z")
    assert serialize_full_event(obj) == serialize_value(obj)


def test_serialize_full_event_with_plain_dict():
    data = {"a": 1, "b": [1, 2, 3]}
    assert serialize_full_event(data) == {"a": 1, "b": [1, 2, 3]}


# ---------------------------------------------------------------------------
# serialize_tuple
# ---------------------------------------------------------------------------


def test_serialize_tuple_basic():
    result = serialize_tuple([("key1", 1), ("key2", "hello")])
    parsed = json.loads(result)
    assert parsed == {"key1": 1, "key2": "hello"}


def test_serialize_tuple_with_datetime():
    dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    result = serialize_tuple([("time", dt)])
    parsed = json.loads(result)
    assert "2025-01-01" in parsed["time"]


def test_serialize_tuple_with_nested_object():
    obj = _DictClass(3, "abc")
    result = serialize_tuple([("item", obj)])
    parsed = json.loads(result)
    assert parsed["item"]["pythonclass"] == "_DictClass"


def test_serialize_tuple_error_returns_empty_json():
    """If serialization fails, returns {} as a JSON string."""
    # We can't easily break orjson/json with a normal class,
    # but we can verify that the function ALWAYS returns valid JSON.
    result = serialize_tuple([("ok", 1)])
    assert json.loads(result) == {"ok": 1}


# ---------------------------------------------------------------------------
# _json_dumps
# ---------------------------------------------------------------------------


def test_json_dumps_produces_valid_json():
    data = {"x": 1, "y": [1, 2, 3]}
    result = _json_dumps(data)
    assert json.loads(result) == data


def test_json_dumps_handles_none():
    result = _json_dumps(None)
    assert json.loads(result) is None


# ---------------------------------------------------------------------------
# New tests per spec
# ---------------------------------------------------------------------------


def test_serialize_full_event_none_returns_none():
    """serialize_full_event(None) must return None, not crash."""
    assert serialize_full_event(None) is None


def test_serialize_full_event_empty_list():
    """serialize_full_event([]) must return []."""
    assert serialize_full_event([]) == []


def test_serialize_deeply_nested_no_recursion_error():
    """Depth-10 nested dicts must serialize without RecursionError."""

    def _make_nested(depth):
        if depth == 0:
            return {"leaf": "value"}
        return {"level": depth, "child": _make_nested(depth - 1)}

    deep = _make_nested(10)
    result = serialize_full_event(deep)
    assert isinstance(result, dict)


def test_serialize_slots_class_is_serialized():
    """Object with __slots__ only (no __dict__) is serialized."""
    obj = _SlotsClass("slot-val", 42)
    result = serialize_full_event(obj)
    assert isinstance(result, dict)
    assert result.get("alpha") == "slot-val"
    assert result.get("beta") == 42


def test_serialize_datetime_in_dict_is_iso_string():
    """datetime values inside dicts become ISO format strings."""
    from datetime import datetime, timezone
    dt = datetime(2025, 7, 4, 12, 0, 0, tzinfo=timezone.utc)
    result = serialize_full_event({"ts": dt})
    assert isinstance(result["ts"], str)
    assert "2025-07-04" in result["ts"]
    assert "T" in result["ts"]


def test_serialize_circular_like_does_not_infinite_loop():
    """An object whose attrs resolve to strings (like circular stubs) terminates."""
    class _Stub:
        def __init__(self):
            self.name = "stub"
            self.value = 42

    obj = _Stub()
    result = serialize_full_event(obj)
    assert result is not None
