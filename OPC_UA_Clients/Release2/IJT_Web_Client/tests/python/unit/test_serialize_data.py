import json
from datetime import datetime, timezone

import pytest

from python.serialize_data import (
    serialize_class_instance_as_dict,
    serialize_full_event,
    serialize_tuple,
    serialize_value,
)


class Custom:
    def __init__(self):
        self.name = "alpha"
        self.count = 2


@pytest.mark.core
def test_serialize_value_generates_valid_json():
    payload = serialize_value({"a": 1, "b": ["x", 2]})
    assert json.loads(payload) == {"a": 1, "b": ["x", 2]}


@pytest.mark.core
def test_serialize_tuple_generates_object_json():
    payload = serialize_tuple([("NodeId", {"Identifier": "X"}), ("Value", 4)])
    decoded = json.loads(payload)
    assert decoded["NodeId"]["Identifier"] == "X"
    assert decoded["Value"] == 4


@pytest.mark.core
def test_serialize_full_event_handles_datetime_and_custom_class():
    obj = Custom()
    now = datetime(2026, 3, 16, 12, 30, tzinfo=timezone.utc)

    payload = serialize_full_event({"time": now, "obj": obj})

    assert payload["time"].startswith("2026-03-16T12:30:00")
    assert payload["obj"]["pythonclass"] == "Custom"
    assert payload["obj"]["count"] == 2


@pytest.mark.core
def test_serialize_full_event_tuple_becomes_list():
    """Tuple input hits the tuple branch in _to_jsonable (line 32)."""
    result = serialize_full_event(("a", "b", 3))
    assert result == ["a", "b", 3]


class _SlottedWithGap:
    """Object with __slots__ but no __dict__ or __weakref__ — goes through _to_jsonable slots branch."""

    __slots__ = ["name", "broken"]

    def __init__(self):
        self.name = "ok"
        # "broken" intentionally not set → getattr raises AttributeError


@pytest.mark.core
def test_serialize_full_event_slotted_object_skips_unset_slot():
    """Exception from unset slot is caught and skipped (lines 42-49 in _to_jsonable)."""
    obj = _SlottedWithGap()
    result = serialize_full_event(obj)
    assert result["pythonclass"] == "_SlottedWithGap"
    assert result["name"] == "ok"
    assert "broken" not in result


class _EmptySlotted:
    """Object with empty __slots__ — falls through to str() fallback in _to_jsonable (line 52)."""

    __slots__: list = []


@pytest.mark.core
def test_serialize_full_event_empty_slots_falls_back_to_str():
    """Object with empty __slots__ returns str() representation (line 52)."""
    obj = _EmptySlotted()
    result = serialize_full_event(obj)
    assert isinstance(result, str)


class _SlottedWithWeakref:
    """Slotted class with __weakref__ — is_instance_of_class returns True, exercises
    the elif __slots__ branch in serialize_class_instance_as_dict (lines 90-102)."""

    __slots__ = ["__weakref__", "value", "broken"]

    def __init__(self):
        self.value = "data"
        # "broken" not set → getattr raises inside serialize_class_instance_as_dict


@pytest.mark.core
def test_serialize_class_instance_as_dict_slotted_branch():
    """Slotted object with __weakref__ uses the elif-slots path (lines 90-102)."""
    obj = _SlottedWithWeakref()
    result = serialize_class_instance_as_dict(obj)
    assert result["pythonclass"] == "_SlottedWithWeakref"
    assert result["value"] == "data"
    assert "broken" not in result
