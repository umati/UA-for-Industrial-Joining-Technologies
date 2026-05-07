from types import SimpleNamespace

from helpers.event_payload import event_payload_field, unwrap_variant


class _Variant:
    def __init__(self, value):
        self.Value = value


def test_unwrap_variant_returns_value_member():
    assert unwrap_variant(_Variant("payload")) == "payload"


def test_event_payload_field_reads_direct_field():
    event = SimpleNamespace(EventCode=_Variant(17))
    assert event_payload_field(event, "EventCode") == 17


def test_event_payload_field_reads_event_content_field():
    event = SimpleNamespace(EventContent=_Variant(SimpleNamespace(EventText=_Variant("text"))))
    assert event_payload_field(event, "EventText") == "text"


def test_event_payload_field_reads_joining_system_event_content_field():
    event = SimpleNamespace(JoiningSystemEventContent=SimpleNamespace(JoiningTechnology="tightening"))
    assert event_payload_field(event, "JoiningTechnology") == "tightening"


def test_event_payload_field_reads_slash_dict_key():
    event = SimpleNamespace()
    event.__dict__["JoiningSystemEventContent/AssociatedEntities"] = _Variant(["asset"])
    assert event_payload_field(event, "AssociatedEntities") == ["asset"]


def test_event_payload_field_reads_nested_dict_content():
    event = SimpleNamespace()
    event.__dict__["JoiningSystemEventContent"] = _Variant(SimpleNamespace(ReportedValues=["temperature"]))
    assert event_payload_field(event, "ReportedValues") == ["temperature"]


def test_event_payload_field_returns_none_when_absent():
    assert event_payload_field(SimpleNamespace(), "EventCode") is None
