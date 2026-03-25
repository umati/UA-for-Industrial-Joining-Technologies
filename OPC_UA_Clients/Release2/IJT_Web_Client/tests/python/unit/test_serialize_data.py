import json
from datetime import datetime, timezone

import pytest

from Python.serialize_data import serializeFullEvent, serializeTuple, serializeValue


class Custom:
    def __init__(self):
        self.name = "alpha"
        self.count = 2


@pytest.mark.core
def test_serialize_value_generates_valid_json():
    payload = serializeValue({"a": 1, "b": ["x", 2]})
    assert json.loads(payload) == {"a": 1, "b": ["x", 2]}


@pytest.mark.core
def test_serialize_tuple_generates_object_json():
    payload = serializeTuple([("NodeId", {"Identifier": "X"}), ("Value", 4)])
    decoded = json.loads(payload)
    assert decoded["NodeId"]["Identifier"] == "X"
    assert decoded["Value"] == 4


@pytest.mark.core
def test_serialize_full_event_handles_datetime_and_custom_class():
    obj = Custom()
    now = datetime(2026, 3, 16, 12, 30, tzinfo=timezone.utc)

    payload = serializeFullEvent({"time": now, "obj": obj})

    assert payload["time"].startswith("2026-03-16T12:30:00")
    assert payload["obj"]["pythonclass"] == "Custom"
    assert payload["obj"]["count"] == 2
