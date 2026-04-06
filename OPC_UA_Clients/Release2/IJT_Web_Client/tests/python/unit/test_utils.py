"""
Tests for Python/utils.py — logging helpers, NodeId/LocalizedText formatters.

Covers:
- nodeid_to_str(): all 4 NodeId types (Numeric, String, Guid, Opaque) + fallback
- localizedtext_to_str(): normal LocalizedText + fallback on broken input
- format_local_time(): known datetime converts to expected Stockholm-local string
- format_list_for_logging(): empty list, single item, multiple items
"""

import uuid
from datetime import datetime

import pytest

try:
    import pytz  # noqa: E402
    from asyncua import ua  # noqa: E402

    HAS_ASYNCUA = True
except ImportError:  # pragma: no cover - environment-dependent
    pytz = None  # type: ignore[assignment]
    ua = None  # type: ignore[assignment]
    HAS_ASYNCUA = False

from python.utils import (  # noqa: E402
    format_list_for_logging,
    format_local_time,
    localizedtext_to_str,
    nodeid_to_str,
)

# ---------------------------------------------------------------------------
# nodeid_to_str
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_nodeid_to_str_numeric():
    node = ua.NodeId(1234, 2)
    result = nodeid_to_str(node)
    assert result == "ns=2;i=1234"


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_nodeid_to_str_string():
    node = ua.NodeId("MyIdentifier", 3, ua.NodeIdType.String)
    result = nodeid_to_str(node)
    assert result == "ns=3;s=MyIdentifier"


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_nodeid_to_str_guid():
    guid = uuid.UUID("12345678-1234-5678-1234-567812345678")
    node = ua.NodeId(guid, 1, ua.NodeIdType.Guid)
    result = nodeid_to_str(node)
    assert result == f"ns=1;g={guid}"


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_nodeid_to_str_opaque():
    data = b"\x01\x02\x03"
    # asyncua 1.x renamed NodeIdType.Opaque → ByteString
    node = ua.NodeId(data, 0, ua.NodeIdType.ByteString)
    result = nodeid_to_str(node)
    assert result == f"ns=0;b={data}"


def test_nodeid_to_str_fallback_on_non_nodeid():
    """Non-NodeId input should fall back to str() without raising."""
    result = nodeid_to_str("not_a_nodeid")
    assert result == "not_a_nodeid"


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_nodeid_to_str_numeric_namespace_zero():
    """Namespace 0 is the core OPC UA namespace."""
    node = ua.NodeId(2258, 0)  # Server/ServerStatus/CurrentTime
    result = nodeid_to_str(node)
    assert result == "ns=0;i=2258"


# ---------------------------------------------------------------------------
# localizedtext_to_str
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_localizedtext_to_str_returns_text():
    # asyncua 1.x: LocalizedText(Text, Locale) — Text is the first positional arg
    lt = ua.LocalizedText("Hello World", "en")
    assert localizedtext_to_str(lt) == "Hello World"


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_localizedtext_to_str_empty_text():
    lt = ua.LocalizedText("", "en")
    assert localizedtext_to_str(lt) == ""


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_localizedtext_to_str_none_locale():
    # Text present, no locale
    lt = ua.LocalizedText("No locale", None)
    assert localizedtext_to_str(lt) == "No locale"


def test_localizedtext_to_str_fallback_on_non_localizedtext():
    """Non-LocalizedText input falls back to str()."""
    result = localizedtext_to_str(42)
    assert result == "42"


def test_localizedtext_to_str_fallback_on_string():
    result = localizedtext_to_str("plain string")
    assert result == "plain string"


# ---------------------------------------------------------------------------
# format_local_time
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_format_local_time_utc_aware():
    """A UTC-aware datetime converts correctly to Stockholm local time."""
    utc_dt = datetime(2025, 6, 15, 10, 0, 0, tzinfo=pytz.utc)
    # Stockholm is UTC+2 in summer (CEST)
    result = format_local_time(utc_dt, timezone="Europe/Stockholm")
    assert result.startswith("2025-06-15 12:00:00")
    # milliseconds part should be 3 digits
    assert len(result) == len("2025-06-15 12:00:00.000")


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_format_local_time_winter_utc_plus_one():
    """Stockholm is UTC+1 in winter (CET)."""
    utc_dt = datetime(2025, 1, 15, 10, 0, 0, tzinfo=pytz.utc)
    result = format_local_time(utc_dt, timezone="Europe/Stockholm")
    assert result.startswith("2025-01-15 11:00:00")


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_format_local_time_different_timezone():
    utc_dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=pytz.utc)
    result = format_local_time(utc_dt, timezone="America/New_York")
    # New York is UTC-4 in summer (EDT)
    assert result.startswith("2025-06-15 08:00:00")


@pytest.mark.skipif(not HAS_ASYNCUA, reason="asyncua or pytz not installed")
def test_format_local_time_output_length():
    """Output must be exactly 23 chars: YYYY-MM-DD HH:MM:SS.mmm"""
    utc_dt = datetime(2025, 3, 27, 8, 30, 45, 123456, tzinfo=pytz.utc)
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
