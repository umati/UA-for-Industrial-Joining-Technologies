import json
from datetime import datetime

from src.python.serialize_data import serialize_full_event, serialize_tuple, serialize_value


def _combined_name_filter(event, class_name: str, subclass_names: list) -> bool:
    """Return True if event's ConditionClassName matches class_name AND
    at least one of event's ConditionSubClassName entries is in subclass_names."""
    if event.ConditionClassName.Text != class_name:
        return False
    event_subclass_texts = {sc.Text for sc in event.ConditionSubClassName}
    return any(name in event_subclass_texts for name in subclass_names)


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
    assert _combined_name_filter(event, "SystemConditionClassType", ["AssetConnectedConditionClassType"])


def test_combined_name_filter_false_when_subclass_missing():
    event = _Event("SystemConditionClassType", ["AnotherSubClass"])
    assert not _combined_name_filter(event, "SystemConditionClassType", ["AssetConnectedConditionClassType"])


def test_serialize_full_event_handles_datetime_and_ignores_freeze_flag():
    payload = _Payload()
    serialized = serialize_full_event(payload)

    assert serialized["pythonclass"] == "_Payload"
    assert serialized["name"] == "demo"
    assert serialized["when"] == "2025-01-02T03:04:05"
    assert serialized["items"] == [1, "x"]
    assert "_freeze" not in serialized


def test_serialize_tuple_and_value_json_shapes():
    out = serialize_tuple([("a", 1), ("b", ["x", None])])
    assert json.loads(out) == {"a": 1, "b": ["x", None]}
    assert serialize_value("line1\nline2") == '"line1\\nline2"'
