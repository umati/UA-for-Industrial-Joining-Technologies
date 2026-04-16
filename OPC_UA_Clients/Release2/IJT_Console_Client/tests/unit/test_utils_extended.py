# ruff: noqa: E402
"""Extended tests for utils.py — covers remaining coverage gaps."""

import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

_ = pytest.importorskip("asyncua", reason="asyncua not installed")

from asyncua import ua

from utils import (
    _to_json_bytes,
    _to_json_str,
    format_local_time,
    localizedtext_to_str,
    log_entity,
    log_field,
    log_joining_system_event,
    log_reported_value,
    log_result_event_details,
    log_result_to_file,
    log_separator,
    nodeid_to_str,
    read_server_time,
    read_tool_identifier,
)

# ── _to_json_str / _to_json_bytes ──


def test_to_json_str_with_orjson_returns_string():
    """_to_json_str returns a str when orjson is available."""
    result = _to_json_str({"a": 1})
    assert isinstance(result, str)
    assert '"a"' in result


def test_to_json_str_with_orjson_none_uses_stdlib(monkeypatch):
    """_to_json_str falls back to stdlib json when utils.orjson is None."""
    monkeypatch.setattr("utils.orjson", None)
    result = _to_json_str({"x": 42})
    assert isinstance(result, str)
    import json

    assert json.loads(result) == {"x": 42}


def test_to_json_str_orjson_none_fallback_ensure_ascii(monkeypatch):
    """Fallback path uses ensure_ascii=True and does not crash on unicode."""
    monkeypatch.setattr("utils.orjson", None)
    result = _to_json_str({"msg": "café"})
    assert isinstance(result, str)


def test_to_json_bytes_returns_bytes():
    """_to_json_bytes encodes _to_json_str output as UTF-8 bytes."""
    result = _to_json_bytes({"k": "v"})
    assert isinstance(result, bytes)
    assert b"k" in result


def test_to_json_bytes_orjson_none(monkeypatch):
    """_to_json_bytes works via stdlib fallback when orjson is None."""
    monkeypatch.setattr("utils.orjson", None)
    result = _to_json_bytes([1, 2, 3])
    assert isinstance(result, bytes)


# ── log_field ──


def test_log_field_calls_ijt_log_info():
    """log_field emits an info log line with label and value."""
    with patch("utils.ijt_log") as mock_log:
        log_field("MyLabel", "MyValue")
        mock_log.info.assert_called_once()
        call_arg = mock_log.info.call_args[0][0]
        assert "MyLabel" in call_arg
        assert "MyValue" in call_arg


def test_log_field_custom_width():
    """log_field respects custom label_width."""
    with patch("utils.ijt_log") as mock_log:
        log_field("L", "V", label_width=10)
        mock_log.info.assert_called_once()


# ── log_separator ──


def test_log_separator_calls_ijt_log_info():
    """log_separator emits a dashed line via ijt_log.info."""
    with patch("utils.ijt_log") as mock_log:
        log_separator()
        mock_log.info.assert_called_once()
        call_arg = mock_log.info.call_args[0][0]
        assert "-" in call_arg


def test_log_separator_custom_width():
    """log_separator uses custom label_width for line length."""
    with patch("utils.ijt_log") as mock_log:
        log_separator(label_width=10)
        mock_log.info.assert_called_once()
        assert len(mock_log.info.call_args[0][0]) == 50  # 10 + 40


# ── format_local_time ──


def test_format_local_time_invalid_iso_string_returns_original():
    """format_local_time returns the original string when ISO parse fails."""
    bad = "not-a-date"
    result = format_local_time(bad)
    assert result == bad


def test_format_local_time_valid_iso_string_is_converted():
    """format_local_time parses a valid ISO string and formats it."""
    result = format_local_time("2025-06-15T10:00:00+00:00")
    assert isinstance(result, str)
    assert "2025-06-15" in result


def test_format_local_time_datetime_without_tz():
    """format_local_time works on a naive datetime (no tzinfo)."""
    dt = datetime(2025, 3, 15, 8, 0, 0)
    result = format_local_time(dt)
    assert isinstance(result, str)
    assert len(result) == 23


# ── read_server_time ──


@pytest.mark.asyncio
async def test_read_server_time_happy_path():
    """read_server_time returns the datetime read from the server node."""
    expected = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    mock_client = MagicMock()
    mock_node = AsyncMock()
    mock_node.read_value = AsyncMock(return_value=expected)
    mock_client.get_node.return_value = mock_node

    result = await read_server_time(mock_client)
    assert result == expected


@pytest.mark.asyncio
async def test_read_server_time_exception_returns_none():
    """read_server_time returns None when an exception is raised."""
    mock_client = MagicMock()
    mock_node = AsyncMock()
    mock_node.read_value = AsyncMock(side_effect=RuntimeError("connection lost"))
    mock_client.get_node.return_value = mock_node

    result = await read_server_time(mock_client)
    assert result is None


# ── read_tool_identifier ──


@pytest.mark.asyncio
async def test_read_tool_identifier_happy_path():
    """read_tool_identifier returns the value read from the node."""
    mock_client = MagicMock()
    mock_node = AsyncMock()
    mock_node.read_value = AsyncMock(return_value="ProductInstanceUri_123")
    mock_client.get_node.return_value = mock_node

    result = await read_tool_identifier(mock_client)
    assert result == "ProductInstanceUri_123"


@pytest.mark.asyncio
async def test_read_tool_identifier_exception_returns_none():
    """read_tool_identifier returns None when an exception is raised."""
    mock_client = MagicMock()
    mock_node = AsyncMock()
    mock_node.read_value = AsyncMock(side_effect=OSError("no node"))
    mock_client.get_node.return_value = mock_node

    result = await read_tool_identifier(mock_client)
    assert result is None


# ── log_result_event_details ──


def _make_result_event():
    """Build a minimal mock event suitable for log_result_event_details."""
    event = MagicMock()
    event.EventId = b"evt-bytes-001"
    event.Time = datetime(2025, 6, 1, 12, 0, 5, tzinfo=timezone.utc)
    event.Message.Text = "Tightening OK"

    start = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    end = datetime(2025, 6, 1, 12, 0, 4)  # naive — triggers tzinfo branch
    creation = datetime(2025, 6, 1, 12, 0, 4, 500000, tzinfo=timezone.utc)

    times_mock = MagicMock()
    times_mock.StartTime = start
    times_mock.EndTime = end

    meta_mock = MagicMock()
    meta_mock.ProcessingTimes = times_mock
    meta_mock.CreationTime = creation

    result_mock = MagicMock()
    result_mock.ResultMetaData = meta_mock

    event.Result = result_mock
    return event


@pytest.mark.asyncio
async def test_log_result_event_details_happy_path():
    """log_result_event_details returns the decoded EventId string."""
    event = _make_result_event()
    client_time = datetime(2025, 6, 1, 12, 0, 6, tzinfo=timezone.utc)

    result = await log_result_event_details(event, "opc.tcp://localhost:4840", client_time)
    assert result == "evt-bytes-001"


@pytest.mark.asyncio
async def test_log_result_event_details_no_end_time():
    """log_result_event_details handles missing EndTime gracefully."""
    event = _make_result_event()
    event.Result.ResultMetaData.ProcessingTimes.EndTime = None
    client_time = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    result = await log_result_event_details(event, "opc.tcp://localhost:4840", client_time)
    assert result == "evt-bytes-001"


@pytest.mark.asyncio
async def test_log_result_event_details_no_meta():
    """log_result_event_details handles missing ResultMetaData gracefully."""
    event = MagicMock()
    event.EventId = b"no-meta"
    event.Time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    event.Message.Text = "msg"
    event.Result = MagicMock(spec=[])  # no ResultMetaData attr
    client_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    result = await log_result_event_details(event, "opc.tcp://localhost:4840", client_time)
    assert result == "no-meta"


@pytest.mark.asyncio
async def test_log_result_event_details_exception_returns_unknown():
    """log_result_event_details returns 'unknown' when an unexpected exception occurs."""
    event = MagicMock()
    # Make event.EventId raise when .decode() is called on a non-bytes value
    event.EventId = MagicMock()
    event.EventId.decode = MagicMock(side_effect=RuntimeError("boom"))
    client_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    result = await log_result_event_details(event, "opc.tcp://localhost:4840", client_time)
    assert result == "unknown"


# ── log_joining_system_event ──


def _make_mock_joining_event(*, with_local_time=True, entities=None, reported_values=None):
    """Build a minimal mock event suitable for log_joining_system_event."""
    event = MagicMock()
    event.Message.Text = "Joining event text"
    event.EventType = MagicMock()
    event.EventId = "joining-evt-001"
    event.SourceName = "Source"
    event.SourceNode = MagicMock()
    event.Severity = 500
    event.Time = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    event.ReceiveTime = datetime(2025, 6, 1, 12, 0, 1, tzinfo=timezone.utc)

    if with_local_time:
        event.LocalTime.Offset = 60
        event.LocalTime.DaylightSavingInOffset = True
    else:
        event.LocalTime = None

    event.ConditionClassId = MagicMock()
    event.ConditionClassName = MagicMock()
    event.ConditionSubClassId = []
    event.ConditionSubClassName = []
    event.EventCode = "EC001"
    event.EventText = "event text"
    event.JoiningTechnology = "Bolting"
    event.AssociatedEntities = entities if entities is not None else []
    event.ReportedValues = reported_values if reported_values is not None else []
    return event


@pytest.mark.asyncio
async def test_log_joining_system_event_with_local_time():
    """log_joining_system_event logs LocalTime fields when LocalTime is set."""
    event = _make_mock_joining_event(with_local_time=True)
    with patch("utils.ijt_log"):
        await log_joining_system_event(event)  # must not raise


@pytest.mark.asyncio
async def test_log_joining_system_event_without_local_time():
    """log_joining_system_event logs 'Unavailable' when LocalTime is None."""
    event = _make_mock_joining_event(with_local_time=False)
    with patch("utils.ijt_log"):
        await log_joining_system_event(event)


@pytest.mark.asyncio
async def test_log_joining_system_event_with_associated_entities():
    """log_joining_system_event calls log_entity for each entity in the list."""
    entity = MagicMock()
    entity.Name = "Tool1"
    entity.Description = "desc"
    entity.EntityId = "eid1"
    entity.EntityType = "type"
    entity.IsExternal = False

    event = _make_mock_joining_event(entities=[entity])
    with patch("utils.ijt_log"):
        await log_joining_system_event(event)


@pytest.mark.asyncio
async def test_log_joining_system_event_with_reported_values():
    """log_joining_system_event calls log_reported_value for each rv in the list."""
    rv = MagicMock()
    rv.Name = "Torque"
    rv.CurrentValue.Value = 12.5
    rv.PreviousValue.Value = 11.0
    rv.PhysicalQuantity = "Torque"
    rv.LowLimit = 10.0
    rv.HighLimit = 15.0
    rv.EngineeringUnits.DisplayName = "Nm"
    rv.EngineeringUnits.Description = "Newton-metre"

    event = _make_mock_joining_event(reported_values=[rv])
    with patch("utils.ijt_log"):
        await log_joining_system_event(event)


@pytest.mark.asyncio
async def test_log_joining_system_event_empty_entities():
    """log_joining_system_event handles empty AssociatedEntities list."""
    event = _make_mock_joining_event(entities=[])
    with patch("utils.ijt_log"):
        await log_joining_system_event(event)


@pytest.mark.asyncio
async def test_log_joining_system_event_non_list_reported_values():
    """log_joining_system_event handles non-list ReportedValues (None)."""
    event = _make_mock_joining_event(reported_values=None)
    event.ReportedValues = None  # override to non-list
    with patch("utils.ijt_log"):
        await log_joining_system_event(event)


@pytest.mark.asyncio
async def test_log_joining_system_event_entity_raises():
    """log_joining_system_event handles exceptions in log_entity gracefully."""
    bad_entity = MagicMock()
    # Make log_entity raise by having an attribute access raise
    type(bad_entity).__getattr__ = MagicMock(side_effect=RuntimeError("bad attr"))

    event = _make_mock_joining_event(entities=[bad_entity])
    with patch("utils.ijt_log"):
        with patch("utils.log_entity", side_effect=RuntimeError("entity error")):
            await log_joining_system_event(event)  # must not raise


# ── log_entity ──


def test_log_entity_logs_all_fields():
    """log_entity logs all standard entity fields."""
    entity = MagicMock()
    entity.Name = "Tool"
    entity.Description = "A tool"
    entity.EntityId = "eid42"
    entity.EntityType = "Spindle"
    entity.IsExternal = False

    with patch("utils.ijt_log") as mock_log:
        log_entity(entity)
        assert mock_log.info.call_count >= 5


def test_log_entity_missing_fields():
    """log_entity uses getattr defaults for missing fields."""
    entity = MagicMock(spec=[])  # no attributes defined

    with patch("utils.ijt_log"):
        log_entity(entity)  # must not raise


# ── log_reported_value ──


def test_log_reported_value_with_engineering_units():
    """log_reported_value logs value fields including engineering units."""
    rv = MagicMock()
    rv.Name = "Torque"
    rv.CurrentValue.Value = 12.5
    rv.PreviousValue.Value = 11.0
    rv.PhysicalQuantity = "Torque"
    rv.LowLimit = 10.0
    rv.HighLimit = 15.0
    rv.EngineeringUnits.DisplayName = "Nm"
    rv.EngineeringUnits.Description = "Newton-metre"

    with patch("utils.ijt_log") as mock_log:
        log_reported_value(rv)
        assert mock_log.info.call_count >= 1


def test_log_reported_value_no_engineering_units():
    """log_reported_value handles missing EngineeringUnits gracefully."""
    rv = MagicMock(spec=["Name", "CurrentValue", "PreviousValue", "PhysicalQuantity", "LowLimit", "HighLimit"])
    rv.Name = "Speed"
    rv.CurrentValue.Value = 100
    rv.PreviousValue.Value = 90
    rv.PhysicalQuantity = "Speed"
    rv.LowLimit = 50
    rv.HighLimit = 150
    # EngineeringUnits not in spec → getattr returns ""

    with patch("utils.ijt_log"):
        log_reported_value(rv)  # must not raise


# ── nodeid_to_str exception path ──


def test_nodeid_to_str_guid_type():
    """nodeid_to_str returns g= prefix for Guid node IDs."""
    import uuid

    g = uuid.UUID("12345678-1234-5678-1234-567812345678")
    node = ua.NodeId(g, 2, ua.NodeIdType.Guid)
    result = nodeid_to_str(node)
    assert result.startswith("ns=2;g=")


def test_nodeid_to_str_bytestring_type():
    """nodeid_to_str returns b= prefix for ByteString node IDs."""
    data = b"\x01\x02"
    node = ua.NodeId(data, 0, ua.NodeIdType.ByteString)
    result = nodeid_to_str(node)
    assert result.startswith("ns=0;b=")


def test_nodeid_to_str_exception_returns_str_fallback():
    """nodeid_to_str returns str(nodeid) when an exception is raised internally."""

    class _BadNodeId(ua.NodeId):
        @property
        def NodeIdType(self):
            raise RuntimeError("forced failure")

        def __str__(self):
            return "bad-node-id-str"

    node = _BadNodeId.__new__(_BadNodeId)
    result = nodeid_to_str(node)
    assert result == "bad-node-id-str"


# ── localizedtext_to_str exception path ──


def test_localizedtext_to_str_exception_returns_str_fallback():
    """localizedtext_to_str returns str(lt) when an exception is raised."""

    class _BadLocalizedText(ua.LocalizedText):
        @property
        def Text(self):
            raise RuntimeError("bad text access")

        def __str__(self):
            return "bad-lt-str"

    lt = _BadLocalizedText.__new__(_BadLocalizedText)
    result = localizedtext_to_str(lt)
    assert result == "bad-lt-str"


def test_localizedtext_to_str_none_text():
    """localizedtext_to_str returns '' when lt.Text is None."""
    lt = ua.LocalizedText(None, "en")
    result = localizedtext_to_str(lt)
    assert result == ""


# ── log_result_to_file ──


@pytest.mark.asyncio
async def test_log_result_to_file_enabled_writes_file(monkeypatch):
    """log_result_to_file creates a JSON file when ENABLE_RESULT_FILE_LOGGING is True."""
    orig_cwd = Path.cwd()
    work_dir = orig_cwd / "tmp" / f"pytest-local-{uuid.uuid4().hex}"
    work_dir.mkdir(parents=True, exist_ok=False)
    try:
        monkeypatch.chdir(work_dir)
        monkeypatch.setattr("utils.ENABLE_RESULT_FILE_LOGGING", True)
        # mkdir(exist_ok=True) without parents=True requires the parent dir to exist
        (work_dir / "logs").mkdir()

        event = MagicMock()
        event.Result = MagicMock()
        event.Message = "TestMessage"
        event.EventId = "evt001"

        with patch("utils.serialize_full_event", return_value={"key": "value"}):
            await log_result_to_file(event)

        result_dir = work_dir / "logs" / "results"
        assert result_dir.exists()
        json_files = list(result_dir.glob("*.json"))
        assert len(json_files) >= 1
    finally:
        monkeypatch.chdir(orig_cwd)
        shutil.rmtree(work_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_log_result_to_file_disabled_does_nothing(monkeypatch):
    """log_result_to_file does nothing when ENABLE_RESULT_FILE_LOGGING is False."""
    orig_cwd = Path.cwd()
    work_dir = orig_cwd / "tmp" / f"pytest-local-{uuid.uuid4().hex}"
    work_dir.mkdir(parents=True, exist_ok=False)
    try:
        monkeypatch.chdir(work_dir)
        monkeypatch.setattr("utils.ENABLE_RESULT_FILE_LOGGING", False)

        event = MagicMock()
        await log_result_to_file(event)

        result_dir = work_dir / "logs" / "results"
        assert not result_dir.exists()
    finally:
        monkeypatch.chdir(orig_cwd)
        shutil.rmtree(work_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_log_result_to_file_exception_is_caught(monkeypatch):
    """log_result_to_file logs error and does not raise when serialization fails."""
    orig_cwd = Path.cwd()
    work_dir = orig_cwd / "tmp" / f"pytest-local-{uuid.uuid4().hex}"
    work_dir.mkdir(parents=True, exist_ok=False)
    try:
        monkeypatch.chdir(work_dir)
        monkeypatch.setattr("utils.ENABLE_RESULT_FILE_LOGGING", True)

        event = MagicMock()
        event.Result = MagicMock()
        event.Message = "msg"
        event.EventId = "e1"

        with patch("utils.serialize_full_event", side_effect=RuntimeError("serialize boom")):
            with patch("utils.ijt_log") as mock_log:
                await log_result_to_file(event)  # must not raise
                mock_log.error.assert_called()
    finally:
        monkeypatch.chdir(orig_cwd)
        shutil.rmtree(work_dir, ignore_errors=True)
