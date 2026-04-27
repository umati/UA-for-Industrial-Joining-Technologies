"""
Tests for Python/utils.py — logging helpers, NodeId/LocalizedText formatters.

Covers:
- nodeid_to_str(): all 4 NodeId types (Numeric, String, Guid, Opaque) + fallback
- localizedtext_to_str(): normal LocalizedText + fallback on broken input
- format_local_time(): known datetime converts to expected Stockholm-local string
- format_list_for_logging(): empty list, single item, multiple items
- log_field(): labelled log line
- log_joining_system_event(): full event with entities and reported values
- log_result_event_details(): async, timing and event_id extraction
- log_result_to_file(): ENABLE_RESULT_FILE_LOGGING flag behaviour
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import pytest_asyncio  # noqa: F401  (registers asyncio mode)

try:
    import pytz  # type: ignore[import-untyped]  # noqa: E402
    from asyncua import ua  # noqa: E402

    HAS_ASYNCUA = True
except ImportError:  # pragma: no cover - environment-dependent
    pytz = None  # type: ignore[assignment]
    ua = None  # type: ignore[assignment]
    HAS_ASYNCUA = False

# TYPE_CHECKING block gives pyright the correct module types rather than
# the Optional[None] union from the try/except above.
if TYPE_CHECKING:
    import pytz  # noqa: F811
    from asyncua import ua  # noqa: F811

from python.utils import (  # noqa: E402
    format_list_for_logging,
    format_local_time,
    localizedtext_to_str,
    log_field,
    log_joining_system_event,
    log_result_event_details,
    log_result_to_file,
    nodeid_to_str,
)

# ---------------------------------------------------------------------------
# nodeid_to_str
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_nodeid_to_str_numeric():
    node = ua.NodeId(1234, 2)  # type: ignore[arg-type]
    result = nodeid_to_str(node)
    assert result == "ns=2;i=1234"


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_nodeid_to_str_string():
    node = ua.NodeId("MyIdentifier", 3, ua.NodeIdType.String)  # type: ignore[arg-type]
    result = nodeid_to_str(node)
    assert result == "ns=3;s=MyIdentifier"


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_nodeid_to_str_guid():
    guid = uuid.UUID("12345678-1234-5678-1234-567812345678")
    node = ua.NodeId(guid, 1, ua.NodeIdType.Guid)  # type: ignore[arg-type]
    result = nodeid_to_str(node)
    assert result == f"ns=1;g={guid}"


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_nodeid_to_str_opaque():
    data = b"\x01\x02\x03"
    # asyncua 1.x renamed NodeIdType.Opaque → ByteString
    node = ua.NodeId(data, 0, ua.NodeIdType.ByteString)  # type: ignore[arg-type]
    result = nodeid_to_str(node)
    assert result == f"ns=0;b={data}"


def test_nodeid_to_str_fallback_on_non_nodeid():
    """Non-NodeId input should fall back to str() without raising."""
    result = nodeid_to_str("not_a_nodeid")  # type: ignore[arg-type]  # intentional wrong-type fallback test
    assert result == "not_a_nodeid"


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_nodeid_to_str_numeric_namespace_zero():
    """Namespace 0 is the core OPC UA namespace."""
    node = ua.NodeId(2258, 0)  # type: ignore[arg-type]  # Server/ServerStatus/CurrentTime
    result = nodeid_to_str(node)
    assert result == "ns=0;i=2258"


# ---------------------------------------------------------------------------
# localizedtext_to_str
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_localizedtext_to_str_returns_text():
    # asyncua 1.x: LocalizedText(Text, Locale) — Text is the first positional arg
    lt = ua.LocalizedText("Hello World", "en")  # type: ignore[union-attr]
    assert localizedtext_to_str(lt) == "Hello World"


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_localizedtext_to_str_empty_text():
    lt = ua.LocalizedText("", "en")  # type: ignore[union-attr]
    assert localizedtext_to_str(lt) == ""


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_localizedtext_to_str_none_locale():
    # Text present, no locale
    lt = ua.LocalizedText("No locale", None)  # type: ignore[union-attr]
    assert localizedtext_to_str(lt) == "No locale"


def test_localizedtext_to_str_fallback_on_non_localizedtext():
    """Non-LocalizedText input falls back to str()."""
    result = localizedtext_to_str(42)  # type: ignore[arg-type]  # intentional wrong-type fallback test
    assert result == "42"


def test_localizedtext_to_str_fallback_on_string():
    result = localizedtext_to_str("plain string")  # type: ignore[arg-type]  # intentional wrong-type fallback test
    assert result == "plain string"


# ---------------------------------------------------------------------------
# format_local_time
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_format_local_time_utc_aware():
    """A UTC-aware datetime converts correctly to Stockholm local time."""
    utc_dt = datetime(2025, 6, 15, 10, 0, 0, tzinfo=pytz.utc)  # type: ignore[union-attr]
    # Stockholm is UTC+2 in summer (CEST)
    result = format_local_time(utc_dt, timezone="Europe/Stockholm")
    assert result.startswith("2025-06-15 12:00:00")
    # milliseconds part should be 3 digits
    assert len(result) == len("2025-06-15 12:00:00.000")


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_format_local_time_winter_utc_plus_one():
    """Stockholm is UTC+1 in winter (CET)."""
    utc_dt = datetime(2025, 1, 15, 10, 0, 0, tzinfo=pytz.utc)  # type: ignore[union-attr]
    result = format_local_time(utc_dt, timezone="Europe/Stockholm")
    assert result.startswith("2025-01-15 11:00:00")


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_format_local_time_different_timezone():
    utc_dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=pytz.utc)  # type: ignore[union-attr]
    result = format_local_time(utc_dt, timezone="America/New_York")
    # New York is UTC-4 in summer (EDT)
    assert result.startswith("2025-06-15 08:00:00")


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_format_local_time_output_length():
    """Output must be exactly 23 chars: YYYY-MM-DD HH:MM:SS.mmm"""
    utc_dt = datetime(2025, 3, 27, 8, 30, 45, 123456, tzinfo=pytz.utc)  # type: ignore[union-attr]
    result = format_local_time(utc_dt)
    assert len(result) == 23
    # milliseconds are 3 digits (µs truncated)
    assert result[-4] == "."


# ---------------------------------------------------------------------------
# format_list_for_logging
# ---------------------------------------------------------------------------


def test_format_list_for_logging_empty():
    lines = format_list_for_logging("MyLabel", [], label_width=10)
    assert lines == ["MyLabel    :"]


def test_format_list_for_logging_single_item():
    lines = format_list_for_logging("Foo", ["alpha"], label_width=5)
    assert len(lines) == 2
    assert lines[0] == "Foo   :"
    assert "alpha" in lines[1]


def test_format_list_for_logging_multiple_items():
    items = ["ns=2;i=1", "ns=2;i=2", "ns=2;i=3"]
    lines = format_list_for_logging("IDs", items, label_width=5)
    assert len(lines) == 4  # header + 3 items
    assert lines[0] == "IDs   :"
    for i, item in enumerate(items):
        assert item in lines[i + 1]


def test_format_list_for_logging_default_width():
    lines = format_list_for_logging("X", ["y"])
    # Default label_width=35; label padded to 35 chars, then space and colon.
    expected_header = "X" + (" " * 34) + " :"
    assert lines[0] == expected_header


# ---------------------------------------------------------------------------
# log_field
# ---------------------------------------------------------------------------


def test_log_field_calls_ijt_log_info():
    """log_field does not raise for any value type."""
    # Should not raise for string, int, None, or object values
    log_field("MyLabel", "MyValue", label_width=10)
    log_field("Count", 42, label_width=10)
    log_field("Empty", None, label_width=10)
    log_field("List", [1, 2, 3], label_width=10)


def test_log_field_default_width_does_not_raise():
    # Should not raise with default label_width
    log_field("SomeLabel", 42)
    log_field("AnotherLabel", None)
    log_field("L", "v", label_width=5)


# ---------------------------------------------------------------------------
# log_joining_system_event
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_log_joining_system_event_with_full_mock():
    """log_joining_system_event logs all fields without raising."""
    import types

    def _make_nid(ns, i):
        return ua.NodeId(i, ns)  # type: ignore[union-attr, arg-type]

    def _make_lt(text):
        return ua.LocalizedText(text, "en")  # type: ignore[union-attr]

    # Entity mock
    entity = types.SimpleNamespace(
        Name="Tool1",
        Description="A tightening tool",
        EntityId="E001",
        EntityType=1,
        IsExternal=False,
    )

    # ReportedValue mock
    eu = types.SimpleNamespace(DisplayName=_make_lt("Nm"), Description=_make_lt("Newton-metre"))
    rv = types.SimpleNamespace(
        Name="Torque",
        CurrentValue=types.SimpleNamespace(Value=12.5),
        PreviousValue=types.SimpleNamespace(Value=11.0),
        PhysicalQuantity="Torque",
        LowLimit=0.0,
        HighLimit=100.0,
        EngineeringUnits=eu,
    )

    event = types.SimpleNamespace(
        Message=types.SimpleNamespace(Text="Tightening complete"),
        EventType=_make_nid(0, 2041),
        EventId=b"\x01\x02\x03",
        SourceName="Tool1",
        SourceNode=_make_nid(1, 1000),
        Severity=500,
        Time=pytz.utc.localize(__import__("datetime").datetime(2025, 6, 15, 10, 0, 0)),  # type: ignore[union-attr]
        ReceiveTime=pytz.utc.localize(__import__("datetime").datetime(2025, 6, 15, 10, 0, 1)),  # type: ignore[union-attr]
        LocalTime=types.SimpleNamespace(Offset=120, DaylightSavingInOffset=True),
        ConditionClassId=_make_nid(0, 2782),
        ConditionClassName=_make_lt("ProcessCondition"),
        ConditionSubClassId=[_make_nid(0, 9999)],
        ConditionSubClassName=[_make_lt("JoiningCondition")],
        EventCode="EC001",
        EventText="Tightening result OK",
        JoiningTechnology="Torque",
        AssociatedEntities=[entity],
        ReportedValues=[rv],
    )

    # Should not raise
    log_joining_system_event(event)


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_log_joining_system_event_no_local_time():
    """log_joining_system_event handles LocalTime=None without raising."""
    import types

    event = types.SimpleNamespace(
        Message=types.SimpleNamespace(Text="Event"),
        EventType=ua.NodeId(2041, 0),  # type: ignore[arg-type]
        EventId=b"\x00",
        SourceName="S",
        SourceNode=ua.NodeId(1000, 1),  # type: ignore[arg-type]
        Severity=100,
        Time=None,
        ReceiveTime=None,
        LocalTime=None,
        ConditionClassId=ua.NodeId(0, 0),  # type: ignore[arg-type]
        ConditionClassName=ua.LocalizedText("", ""),  # type: ignore[union-attr]
        ConditionSubClassId=[],
        ConditionSubClassName=[],
        EventCode="",
        EventText="",
        JoiningTechnology="",
        AssociatedEntities=[],
        ReportedValues=[],
    )

    log_joining_system_event(event)


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_log_joining_system_event_entities_not_list():
    """AssociatedEntities=None and ReportedValues=None branches are hit."""
    import types

    event = types.SimpleNamespace(
        Message=types.SimpleNamespace(Text="E"),
        EventType=ua.NodeId(2041, 0),  # type: ignore[arg-type]
        EventId=b"\x00",
        SourceName="",
        SourceNode=ua.NodeId(0, 0),  # type: ignore[arg-type]
        Severity=0,
        Time=None,
        ReceiveTime=None,
        LocalTime=None,
        ConditionClassId=ua.NodeId(0, 0),  # type: ignore[arg-type]
        ConditionClassName=ua.LocalizedText("", ""),  # type: ignore[union-attr]
        ConditionSubClassId=[],
        ConditionSubClassName=[],
        EventCode="",
        EventText="",
        JoiningTechnology="",
        AssociatedEntities=None,  # not a list
        ReportedValues=None,  # not a list
    )

    log_joining_system_event(event)


# ---------------------------------------------------------------------------
# log_result_event_details
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
@pytest.mark.asyncio
async def test_log_result_event_details_with_full_mock():
    """log_result_event_details logs timing and returns event_id string."""
    import types

    start_time = pytz.utc.localize(__import__("datetime").datetime(2025, 6, 15, 10, 0, 0))  # type: ignore[union-attr]
    end_time = pytz.utc.localize(__import__("datetime").datetime(2025, 6, 15, 10, 0, 5))  # type: ignore[union-attr]
    creation_time = pytz.utc.localize(__import__("datetime").datetime(2025, 6, 15, 10, 0, 6))  # type: ignore[union-attr]
    event_time = pytz.utc.localize(__import__("datetime").datetime(2025, 6, 15, 10, 0, 7))  # type: ignore[union-attr]
    client_received = pytz.utc.localize(__import__("datetime").datetime(2025, 6, 15, 10, 0, 8))  # type: ignore[union-attr]

    processing_times = types.SimpleNamespace(StartTime=start_time, EndTime=end_time)
    result_meta = types.SimpleNamespace(ProcessingTimes=processing_times, CreationTime=creation_time)
    event_result = types.SimpleNamespace(ResultMetaData=result_meta)

    event = types.SimpleNamespace(
        Time=event_time,
        EventId=b"evt-id-001",
        Result=event_result,
        Message=types.SimpleNamespace(Text="TighteningResult"),
    )

    event_id = await log_result_event_details(event, "opc.tcp://localhost:4840", client_received)
    assert event_id == "evt-id-001"


# ---------------------------------------------------------------------------
# nodeid_to_str / localizedtext_to_str — exception fallback branches
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua not installed")
def test_nodeid_to_str_exception_falls_back_to_str():
    """When NodeIdType access raises, nodeid_to_str falls back to str() (lines 302-303).
    Uses raise-once pattern so str(nodeid) in the fallback path succeeds even if
    ua.NodeId.__str__ also reads NodeIdType internally."""
    from unittest.mock import PropertyMock

    node = ua.NodeId(0, 0)  # type: ignore[arg-type]
    actual_type = node.NodeIdType  # stash before patching
    raised = False

    def _raise_once() -> object:
        nonlocal raised
        if not raised:
            raised = True
            raise RuntimeError("deliberate test failure")
        return actual_type  # subsequent reads (e.g. from __str__) return the real value

    with patch.object(type(node), "NodeIdType", new_callable=PropertyMock, side_effect=_raise_once):
        result = nodeid_to_str(node)
    assert isinstance(result, str)


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua not installed")
def test_localizedtext_to_str_exception_falls_back_to_str():
    """When lt.Text access raises, localizedtext_to_str falls back to str() (lines 322-323)."""
    from unittest.mock import PropertyMock

    lt = ua.LocalizedText("hello", "en")  # type: ignore[union-attr]
    actual_text = lt.Text  # stash before patching
    raised = False

    def _raise_once() -> object:
        nonlocal raised
        if not raised:
            raised = True
            raise RuntimeError("deliberate test failure")
        return actual_text  # subsequent reads succeed

    with patch.object(type(lt), "Text", new_callable=PropertyMock, side_effect=_raise_once):
        result = localizedtext_to_str(lt)
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# log_joining_system_event — entity and reported-value error paths
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_log_joining_system_event_entity_raises_is_caught():
    """TypeError from formatting entity field is caught and logged at lines 216-217.
    log_entity and log_reported_value are nested functions so cannot be patched directly;
    instead a __format__-raising value is used to trigger TypeError inside log_field."""
    import types

    class _BadFormat:
        """Value whose f-string formatting raises TypeError."""

        def __format__(self, spec: str) -> str:
            raise TypeError("deliberate format failure")

    entity = types.SimpleNamespace(
        Name=_BadFormat(),  # triggers TypeError in log_field inside log_entity
        Description="",
        EntityId="",
        EntityType="",
        IsExternal="",
    )
    event = types.SimpleNamespace(
        Message=types.SimpleNamespace(Text="E"),
        EventType=ua.NodeId(2041, 0),  # type: ignore[arg-type]
        EventId=b"\x00",
        SourceName="",
        SourceNode=ua.NodeId(0, 0),  # type: ignore[arg-type]
        Severity=0,
        Time=None,
        ReceiveTime=None,
        LocalTime=None,
        ConditionClassId=ua.NodeId(0, 0),  # type: ignore[arg-type]
        ConditionClassName=ua.LocalizedText("", ""),  # type: ignore[union-attr]
        ConditionSubClassId=[],
        ConditionSubClassName=[],
        EventCode="",
        EventText="",
        JoiningTechnology="",
        AssociatedEntities=[entity],
        ReportedValues=[],
    )

    log_joining_system_event(event)  # must not raise


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_log_joining_system_event_reported_value_raises_is_caught():
    """TypeError from formatting rv field is caught and logged at lines 227-228."""
    import types

    class _BadFormat:
        def __format__(self, spec: str) -> str:
            raise TypeError("deliberate format failure")

    rv = types.SimpleNamespace(
        Name=_BadFormat(),  # triggers TypeError in log_field inside log_reported_value
        CurrentValue=None,
        PreviousValue=None,
        PhysicalQuantity="",
        LowLimit="",
        HighLimit="",
        EngineeringUnits=None,
    )
    event = types.SimpleNamespace(
        Message=types.SimpleNamespace(Text="E"),
        EventType=ua.NodeId(2041, 0),  # type: ignore[arg-type]
        EventId=b"\x00",
        SourceName="",
        SourceNode=ua.NodeId(0, 0),  # type: ignore[arg-type]
        Severity=0,
        Time=None,
        ReceiveTime=None,
        LocalTime=None,
        ConditionClassId=ua.NodeId(0, 0),  # type: ignore[arg-type]
        ConditionClassName=ua.LocalizedText("", ""),  # type: ignore[union-attr]
        ConditionSubClassId=[],
        ConditionSubClassName=[],
        EventCode="",
        EventText="",
        JoiningTechnology="",
        AssociatedEntities=[],
        ReportedValues=[rv],
    )

    log_joining_system_event(event)  # must not raise


# ---------------------------------------------------------------------------
# MillisecondFormatter.formatTime — no-datefmt branch (ijt_logger.py line 34)
# ---------------------------------------------------------------------------


def test_millisecond_formatter_without_datefmt():
    """formatTime without datefmt hits the else branch (ijt_logger.py line 34)."""
    import logging

    from python.ijt_logger import MillisecondFormatter

    formatter = MillisecondFormatter("%(message)s")  # no datefmt
    record = logging.LogRecord("test", logging.INFO, "", 0, "msg", [], None)
    result = formatter.formatTime(record)
    assert len(result) == 23  # "YYYY-MM-DD HH:MM:SS.mmm"
    assert result[10] == " " and result[19] == "."


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
@pytest.mark.asyncio
async def test_log_result_event_details_no_end_time():
    """log_result_event_details handles missing EndTime gracefully."""
    import types

    processing_times = types.SimpleNamespace(StartTime=None, EndTime=None)
    result_meta = types.SimpleNamespace(ProcessingTimes=processing_times, CreationTime=None)
    event_result = types.SimpleNamespace(ResultMetaData=result_meta)

    client_received = pytz.utc.localize(__import__("datetime").datetime(2025, 1, 1, 0, 0, 0))  # type: ignore[union-attr]

    event = types.SimpleNamespace(
        Time=None,
        EventId=b"no-endtime",
        Result=event_result,
        Message=types.SimpleNamespace(Text="Test"),
    )

    event_id = await log_result_event_details(event, "", client_received)
    assert event_id == "no-endtime"


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
@pytest.mark.asyncio
async def test_log_result_event_details_naive_end_time_localized():
    """Naive (tz-unaware) EndTime is localized to UTC without raising."""
    import types
    from datetime import datetime

    naive_end = datetime(2025, 6, 15, 10, 0, 5)  # no tzinfo
    processing_times = types.SimpleNamespace(StartTime=None, EndTime=naive_end)
    result_meta = types.SimpleNamespace(ProcessingTimes=processing_times, CreationTime=None)
    event_result = types.SimpleNamespace(ResultMetaData=result_meta)

    client_received = pytz.utc.localize(datetime(2025, 6, 15, 10, 0, 8))  # type: ignore[union-attr]

    event = types.SimpleNamespace(
        Time=None,
        EventId=b"naive-endtime",
        Result=event_result,
        Message=types.SimpleNamespace(Text="T"),
    )

    event_id = await log_result_event_details(event, "", client_received)
    assert event_id == "naive-endtime"


# ---------------------------------------------------------------------------
# log_result_to_file
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
@pytest.mark.asyncio
async def test_log_result_to_file_does_nothing_when_disabled():
    """log_result_to_file is a no-op when ENABLE_RESULT_FILE_LOGGING is False."""
    import types

    event = types.SimpleNamespace(
        Result="result",
        Message=types.SimpleNamespace(Text="Test"),
    )

    with patch("python.utils.ENABLE_RESULT_FILE_LOGGING", False):
        # Should complete without opening any files
        await log_result_to_file(event)


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
@pytest.mark.asyncio
async def test_log_result_to_file_writes_file_when_enabled(tmp_path, monkeypatch):
    """log_result_to_file writes a JSON file when ENABLE_RESULT_FILE_LOGGING is True."""
    import types

    event = types.SimpleNamespace(
        Result=types.SimpleNamespace(Value="test"),
        Message=types.SimpleNamespace(Text="MyResult"),
    )

    # Redirect logs/results/ to tmp_path
    monkeypatch.chdir(tmp_path)

    with patch("python.utils.ENABLE_RESULT_FILE_LOGGING", True):
        with patch("python.utils.serialize_full_event", return_value={"key": "value"}):
            await log_result_to_file(event)

    # Check that a .json file was created
    results_dir = tmp_path / "logs" / "results"
    json_files = list(results_dir.glob("*.json"))
    assert len(json_files) == 1, f"Expected 1 JSON file, found: {json_files}"


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
@pytest.mark.asyncio
async def test_log_result_to_file_handles_exception_gracefully():
    """log_result_to_file catches exceptions from serialize_full_event and logs."""
    import types

    event = types.SimpleNamespace(
        Result=None,
        Message=types.SimpleNamespace(Text="BadResult"),
    )

    with patch("python.utils.ENABLE_RESULT_FILE_LOGGING", True):
        with patch(
            "python.utils.serialize_full_event",
            side_effect=RuntimeError("serialization failed"),
        ):
            # Should not raise — exception is caught internally
            await log_result_to_file(event)
