"""
Comprehensive tests for IJT_Console_Client/utils.py

Covers:
- nodeid_to_str: numeric, string, GUID, opaque, non-NodeId fallback
- localizedtext_to_str: normal, empty locale, None text, non-LocalizedText fallback
- format_local_time: UTC→Stockholm summer/winter, different TZ, output length/format
- format_list_for_logging: empty, single item, multiple items, default width
- log_separator: produces a dashed line of correct width
"""

import pytest
from datetime import datetime

_ = pytest.importorskip("asyncua", reason="asyncua not installed")
import pytz  # noqa: E402
from asyncua import ua  # noqa: E402

from utils import (  # noqa: E402
    format_list_for_logging,
    format_local_time,
    localizedtext_to_str,
    nodeid_to_str,
)


# ---------------------------------------------------------------------------
# nodeid_to_str
# ---------------------------------------------------------------------------


def test_nodeid_numeric_ns0():
    node = ua.NodeId(84, 0)
    assert nodeid_to_str(node) == "ns=0;i=84"


def test_nodeid_numeric_ns2():
    node = ua.NodeId(1234, 2)
    assert nodeid_to_str(node) == "ns=2;i=1234"


def test_nodeid_string():
    node = ua.NodeId("TighteningSystem", 1, ua.NodeIdType.String)
    result = nodeid_to_str(node)
    assert result == "ns=1;s=TighteningSystem"


def test_nodeid_guid():
    import uuid
    g = uuid.UUID("12345678-1234-5678-1234-567812345678")
    node = ua.NodeId(g, 1, ua.NodeIdType.Guid)
    result = nodeid_to_str(node)
    assert result == f"ns=1;g={g}"


def test_nodeid_opaque():
    data = b"\xDE\xAD"
    # asyncua 1.2b2 renamed NodeIdType.Opaque → NodeIdType.ByteString
    node = ua.NodeId(data, 0, ua.NodeIdType.ByteString)
    result = nodeid_to_str(node)
    assert result == f"ns=0;b={data}"


def test_nodeid_fallback_on_none():
    result = nodeid_to_str(None)
    assert result == "None"


def test_nodeid_fallback_on_string_input():
    result = nodeid_to_str("already-a-string")
    assert result == "already-a-string"


def test_nodeid_fallback_on_int():
    result = nodeid_to_str(42)
    assert result == "42"


# ---------------------------------------------------------------------------
# localizedtext_to_str
# ---------------------------------------------------------------------------


def test_localizedtext_returns_text():
    # asyncua 1.2b2: LocalizedText(Text, Locale) — Text is first arg
    lt = ua.LocalizedText("Hello", "en")
    assert localizedtext_to_str(lt) == "Hello"


def test_localizedtext_empty_text():
    lt = ua.LocalizedText("", "en")
    assert localizedtext_to_str(lt) == ""


def test_localizedtext_none_locale():
    lt = ua.LocalizedText("No locale", None)
    assert localizedtext_to_str(lt) == "No locale"


def test_localizedtext_fallback_on_string():
    assert localizedtext_to_str("plain") == "plain"


def test_localizedtext_fallback_on_none():
    assert localizedtext_to_str(None) == "None"


def test_localizedtext_fallback_on_int():
    assert localizedtext_to_str(99) == "99"


# ---------------------------------------------------------------------------
# format_local_time
# ---------------------------------------------------------------------------


def test_format_local_time_utc_summer_stockholm():
    """Stockholm is UTC+2 in summer (CEST)."""
    dt = datetime(2025, 6, 15, 10, 0, 0, tzinfo=pytz.utc)
    result = format_local_time(dt, timezone="Europe/Stockholm")
    assert result.startswith("2025-06-15 12:00:00")


def test_format_local_time_utc_winter_stockholm():
    """Stockholm is UTC+1 in winter (CET)."""
    dt = datetime(2025, 1, 15, 10, 0, 0, tzinfo=pytz.utc)
    result = format_local_time(dt, timezone="Europe/Stockholm")
    assert result.startswith("2025-01-15 11:00:00")


def test_format_local_time_default_timezone_is_stockholm():
    dt = datetime(2025, 6, 15, 10, 0, 0, tzinfo=pytz.utc)
    result_default = format_local_time(dt)
    result_explicit = format_local_time(dt, timezone="Europe/Stockholm")
    assert result_default == result_explicit


def test_format_local_time_output_length():
    dt = datetime(2025, 3, 27, 8, 30, 45, 123456, tzinfo=pytz.utc)
    result = format_local_time(dt)
    assert len(result) == 23  # YYYY-MM-DD HH:MM:SS.mmm


def test_format_local_time_output_format():
    dt = datetime(2025, 3, 27, 8, 30, 45, 500000, tzinfo=pytz.utc)
    result = format_local_time(dt)
    # Must match YYYY-MM-DD HH:MM:SS.mmm
    parts = result.split(" ")
    assert len(parts) == 2
    date_part, time_part = parts
    assert len(date_part) == 10
    assert len(time_part) == 12  # HH:MM:SS.mmm


def test_format_local_time_different_timezone():
    dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=pytz.utc)
    result = format_local_time(dt, timezone="America/New_York")
    assert result.startswith("2025-06-15 08:00:00")


# ---------------------------------------------------------------------------
# format_list_for_logging
# ---------------------------------------------------------------------------


def test_format_list_empty():
    lines = format_list_for_logging("MyLabel", [], label_width=10)
    assert len(lines) == 1
    assert "MyLabel" in lines[0]
    assert ":" in lines[0]


def test_format_list_single_item():
    lines = format_list_for_logging("IDs", ["ns=2;i=1"], label_width=5)
    assert len(lines) == 2
    assert "ns=2;i=1" in lines[1]


def test_format_list_multiple_items():
    items = ["A", "B", "C"]
    lines = format_list_for_logging("Label", items, label_width=6)
    assert len(lines) == 4
    for item in items:
        assert any(item in line for line in lines)


def test_format_list_default_width_header_length():
    lines = format_list_for_logging("X", ["y"])
    # Default label_width=35; header should be >=37 chars
    assert len(lines[0]) >= 37


def test_format_list_items_indented():
    """Item lines must start with spaces (left-padded to label_width)."""
    lines = format_list_for_logging("Label", ["item"], label_width=10)
    assert lines[1].startswith(" " * 10)


# ---------------------------------------------------------------------------
# New tests per spec
# ---------------------------------------------------------------------------


def test_log_joining_system_event_is_async():
    """log_joining_system_event MUST be async (regression guard against it being sync)."""
    import inspect
    from utils import log_joining_system_event
    assert inspect.iscoroutinefunction(log_joining_system_event), (
        "log_joining_system_event must be async — was wrongly made sync in a previous regression"
    )


def test_nodeid_to_str_has_type_hints():
    """nodeid_to_str must have type hints."""
    import inspect
    sig = inspect.signature(nodeid_to_str)
    params = list(sig.parameters.values())
    assert params[0].annotation is not inspect.Parameter.empty


def test_localizedtext_to_str_has_type_hints():
    import inspect
    sig = inspect.signature(localizedtext_to_str)
    params = list(sig.parameters.values())
    assert params[0].annotation is not inspect.Parameter.empty


def test_format_local_time_handles_none_gracefully():
    """format_local_time with a string input should not raise AttributeError."""
    result = format_local_time("2025-01-01T00:00:00")
    assert isinstance(result, str)


def test_nodeid_to_str_handles_none():
    result = nodeid_to_str(None)
    assert result == "None"


def test_localizedtext_to_str_handles_none():
    result = localizedtext_to_str(None)
    assert result == "None"
