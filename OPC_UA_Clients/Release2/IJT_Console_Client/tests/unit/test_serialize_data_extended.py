# ruff: noqa: E402
"""Extended tests for serialize_data.py — covers remaining coverage gaps."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from serialize_data import (
    _json_dumps,
    serialize_class_instance_as_dict,
    serialize_tuple,
    serialize_value,
)

# ── _json_dumps — orjson=None fallback ──


def test_json_dumps_stdlib_fallback_returns_valid_json(monkeypatch):
    """_json_dumps uses stdlib json when orjson is None."""
    monkeypatch.setattr("serialize_data.orjson", None)
    result = _json_dumps({"hello": "world"})
    assert isinstance(result, str)
    assert json.loads(result) == {"hello": "world"}


def test_json_dumps_stdlib_fallback_with_list(monkeypatch):
    """_json_dumps stdlib fallback handles lists correctly."""
    monkeypatch.setattr("serialize_data.orjson", None)
    result = _json_dumps([1, 2, 3])
    assert json.loads(result) == [1, 2, 3]


def test_json_dumps_stdlib_fallback_with_none(monkeypatch):
    """_json_dumps stdlib fallback handles None correctly."""
    monkeypatch.setattr("serialize_data.orjson", None)
    result = _json_dumps(None)
    assert json.loads(result) is None


# ── serialize_value — __slots__ with unreadable slot ──


def test_serialize_value_slots_with_unreadable_slot_skips_gracefully():
    """serialize_value skips __slots__ entries that raise AttributeError."""

    class _SlottedWithBadSlot:
        __slots__ = ("good_slot", "bad_slot")

        def __init__(self):
            self.good_slot = "readable"
            # bad_slot intentionally never assigned

        def __getattribute__(self, name):
            if name == "bad_slot":
                raise AttributeError("unreadable slot")
            return super().__getattribute__(name)

    obj = _SlottedWithBadSlot()
    result = serialize_value(obj)

    assert isinstance(result, dict)
    assert result.get("good_slot") == "readable"
    assert "bad_slot" not in result


def test_serialize_value_slots_freeze_excluded():
    """serialize_value excludes _freeze slot from __slots__ objects."""

    class _SlotsWithFreeze:
        __slots__ = ("value", "_freeze")

        def __init__(self):
            self.value = 99
            self._freeze = True

    obj = _SlotsWithFreeze()
    result = serialize_value(obj)

    assert result.get("value") == 99
    assert "_freeze" not in result


# ── serialize_class_instance_as_dict — __slots__ only (no __dict__) ──


def test_serialize_class_instance_as_dict_slots_only_no_dict():
    """serialize_class_instance_as_dict handles classes with __slots__ and no __dict__."""

    class _PureSlots:
        __slots__ = ("alpha", "beta")

        def __init__(self, a, b):
            self.alpha = a
            self.beta = b

    obj = _PureSlots("x", 42)
    result = serialize_class_instance_as_dict(obj)

    assert result["pythonclass"] == "_PureSlots"
    assert result["alpha"] == "x"
    assert result["beta"] == 42


def test_serialize_class_instance_as_dict_slots_with_unreadable_slot():
    """serialize_class_instance_as_dict skips unreadable slots gracefully."""

    class _BadSlots:
        __slots__ = ("ok", "bad")

        def __init__(self):
            self.ok = "fine"

        def __getattribute__(self, name):
            if name == "bad":
                raise AttributeError("slot not set")
            return super().__getattribute__(name)

    obj = _BadSlots()
    result = serialize_class_instance_as_dict(obj)

    assert result.get("ok") == "fine"
    assert "bad" not in result


def test_serialize_class_instance_as_dict_slots_freeze_excluded():
    """serialize_class_instance_as_dict excludes _freeze from __slots__."""

    class _SlotsClass:
        __slots__ = ("val", "_freeze")

        def __init__(self):
            self.val = "hello"
            self._freeze = True

    obj = _SlotsClass()
    result = serialize_class_instance_as_dict(obj)

    assert result.get("val") == "hello"
    assert "_freeze" not in result


# ── serialize_tuple — exception path ──


def test_serialize_tuple_exception_returns_empty_json():
    """serialize_tuple returns '{}' when iteration raises an exception."""

    class _BadIterable:
        def __iter__(self):
            raise RuntimeError("iteration failed")

    result = serialize_tuple(_BadIterable())  # type: ignore[arg-type]
    assert result == "{}"


def test_serialize_tuple_with_non_serializable_key():
    """serialize_tuple returns '{}' when a key is not JSON-serializable (e.g. tuple key)."""
    # A list of "tuples" where the key itself causes json failure
    # We can force the error by making serialize_value throw inside the dict comp

    class _Exploding:
        def keys(self):
            raise RuntimeError("no keys")

        def __iter__(self):
            # Yield one "tuple" then raise
            yield ("ok_key", 1)
            raise RuntimeError("mid-iteration failure")

    result = serialize_tuple(_Exploding())  # type: ignore[arg-type]
    assert result == "{}"
