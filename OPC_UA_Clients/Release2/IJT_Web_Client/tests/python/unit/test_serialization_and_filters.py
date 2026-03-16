import json
from datetime import datetime

from Python.serialize_data import serializeFullEvent, serializeTuple, serializeValue
from Pytest.TestSubscriptionHandler import combinedNameFilter


class _Text:
    def __init__(self, text):
        self.Text = text


class _Event:
    def __init__(self, class_name, subclasses):
        self.ConditionClassName = _Text(class_name)
        self.ConditionSubClassName = [_Text(x) for x in subclasses]


class _Payload:
    def __init__(self):
        self.name = "demo"
        self.when = datetime(2025, 1, 2, 3, 4, 5)
        self.items = [1, "x"]
        self._freeze = True


def test_combined_name_filter_true_when_class_and_subclasses_match():
    event = _Event("SystemConditionClassType", ["AssetConnectedConditionClassType", "X"])
    assert combinedNameFilter(event, "SystemConditionClassType", ["AssetConnectedConditionClassType"])


def test_combined_name_filter_false_when_subclass_missing():
    event = _Event("SystemConditionClassType", ["AnotherSubClass"])
    assert not combinedNameFilter(event, "SystemConditionClassType", ["AssetConnectedConditionClassType"])


def test_serialize_full_event_handles_datetime_and_ignores_freeze_flag():
    payload = _Payload()
    serialized = serializeFullEvent(payload)

    assert serialized["pythonclass"] == "_Payload"
    assert serialized["name"] == "demo"
    assert serialized["when"] == "2025-01-02T03:04:05"
    assert serialized["items"] == [1, "x"]
    assert "_freeze" not in serialized


def test_serialize_tuple_and_value_json_shapes():
    out = serializeTuple([("a", 1), ("b", ["x", None])])
    assert json.loads(out) == {"a": 1, "b": ["x", None]}
    assert serializeValue("line1\nline2") == '"line1\\nline2"'
