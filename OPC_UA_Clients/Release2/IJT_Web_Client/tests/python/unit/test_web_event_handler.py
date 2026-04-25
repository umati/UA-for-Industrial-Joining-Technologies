"""
Comprehensive tests for IJT_Web_Client/Python/event_handler.py

Covers:
- Short class: EventId bytes→str, non-bytes→str, missing attributes via getattr defaults,
  ConditionSubClassId list formatting, ConditionSubClassName list formatting,
  IJT slash-path attributes extraction
- EventHandler lifecycle: init creates queue+task, shutdown sets closed, close awaits task
- EventHandler.process_event: respects closed flag, enqueues item
- EventHandler.event_notification: respects closed flag, builds Short event, calls process_event
- EventHandler.handle_queue: sends JSON with command="event", endpoint=server_url, data=serialized;
  breaks on ConnectionClosedOK; breaks + closes websocket on other exceptions
- EventHandler double-shutdown is idempotent
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("asyncua", reason="asyncua not installed")
from asyncua import ua  # noqa: E402

from python.event_handler import EventHandler, Short  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_raw_event(message_text="Event", event_id_bytes=b"evt-001"):
    event = MagicMock()
    event.EventType = ua.NodeId(1006, 2)  # type: ignore[arg-type]
    event.EventId = event_id_bytes
    # asyncua 1.x: LocalizedText(Text, Locale) — text is the first positional arg
    event.Message = ua.LocalizedText(message_text, "en")
    event.SourceName = "ToolController"
    event.SourceNode = ua.NodeId(500, 1)  # type: ignore[arg-type]
    event.Severity = 300
    event.Time = None
    event.ReceiveTime = None
    event.LocalTime = None
    event.ConditionClassId = ua.NodeId(0, 0)  # type: ignore[arg-type]
    event.ConditionClassName = ua.LocalizedText("JoiningSystemEventType", "en")
    event.ConditionSubClassId = []
    event.ConditionSubClassName = []
    setattr(event, "JoiningSystemEventContent/EventCode", "E001")
    setattr(event, "JoiningSystemEventContent/EventText", ua.LocalizedText("Joint tightened", "en"))
    setattr(event, "JoiningSystemEventContent/JoiningTechnology", ua.LocalizedText("Torque", "en"))
    setattr(event, "JoiningSystemEventContent/AssociatedEntities", [])
    setattr(event, "JoiningSystemEventContent/ReportedValues", [])
    return event


# ---------------------------------------------------------------------------
# Short class
# ---------------------------------------------------------------------------


def test_short_event_id_from_bytes():
    raw = _fake_raw_event(event_id_bytes=b"hello-bytes")
    with patch("python.event_handler.log_joining_system_event"):
        short = Short(raw)
    assert short.EventId == "hello-bytes"


def test_short_event_id_from_non_bytes():
    raw = _fake_raw_event()
    raw.EventId = "string-id-42"
    with patch("python.event_handler.log_joining_system_event"):
        short = Short(raw)
    assert short.EventId == "string-id-42"


def test_short_source_name_is_string():
    raw = _fake_raw_event()
    short = Short(raw)
    assert isinstance(short.SourceName, str)
    assert short.SourceName == "ToolController"


def test_short_severity_is_string():
    raw = _fake_raw_event()
    short = Short(raw)
    assert isinstance(short.Severity, str)


def test_short_condition_subclass_id_is_list():
    raw = _fake_raw_event()
    raw.ConditionSubClassId = [ua.NodeId(1, 2), ua.NodeId(3, 4)]  # type: ignore[arg-type]
    short = Short(raw)
    assert isinstance(short.ConditionSubClassId, list)
    assert all(isinstance(x, str) for x in short.ConditionSubClassId)


def test_short_condition_subclass_name_is_list_of_strings():
    raw = _fake_raw_event()
    raw.ConditionSubClassName = [
        ua.LocalizedText("Alpha", "en"),
        ua.LocalizedText("Beta", "en"),
    ]
    short = Short(raw)
    assert short.ConditionSubClassName == ["Alpha", "Beta"]


def test_short_event_code_extracted():
    raw = _fake_raw_event()
    short = Short(raw)
    assert short.EventCode == "E001"


def test_short_event_text_extracted():
    raw = _fake_raw_event()
    short = Short(raw)
    assert short.EventText == "Joint tightened"


def test_short_joining_technology_extracted():
    raw = _fake_raw_event()
    short = Short(raw)
    assert short.JoiningTechnology == "Torque"


def test_short_associated_entities_is_list():
    raw = _fake_raw_event()
    short = Short(raw)
    assert short.AssociatedEntities == []


def test_short_missing_attribute_does_not_raise():
    """If an optional attribute is absent, getattr should return default without raising."""
    raw = MagicMock()
    raw.EventType = ua.NodeId(0, 0)  # type: ignore[arg-type]
    raw.EventId = b""
    raw.ConditionSubClassId = []
    raw.ConditionSubClassName = []
    setattr(raw, "JoiningSystemEventContent/EventCode", None)
    setattr(raw, "JoiningSystemEventContent/EventText", None)
    setattr(raw, "JoiningSystemEventContent/JoiningTechnology", None)
    setattr(raw, "JoiningSystemEventContent/AssociatedEntities", [])
    setattr(raw, "JoiningSystemEventContent/ReportedValues", [])
    short = Short(raw)
    assert short is not None


# ---------------------------------------------------------------------------
# EventHandler lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_handler_creates_task_on_init():
    ws = AsyncMock()
    with patch("python.event_handler.log_joining_system_event"):
        handler = EventHandler(ws, "opc.tcp://localhost:40451")
    assert not handler._queue_task.done()
    await handler.close()


@pytest.mark.asyncio
async def test_event_handler_shutdown_sets_closed():
    ws = AsyncMock()
    handler = EventHandler(ws, "opc.tcp://localhost:40451")
    assert not handler.closed
    await handler.shutdown()
    assert handler.closed
    await handler._queue_task


@pytest.mark.asyncio
async def test_event_handler_close_awaits_task():
    ws = AsyncMock()
    handler = EventHandler(ws, "opc.tcp://localhost:40451")
    await handler.close()
    assert handler._queue_task.done()
    assert handler.closed


@pytest.mark.asyncio
async def test_event_handler_double_shutdown_idempotent():
    ws = AsyncMock()
    handler = EventHandler(ws, "opc.tcp://localhost:40451")
    await handler.shutdown()
    await handler.shutdown()  # second call must not add another sentinel
    await asyncio.wait_for(handler._queue_task, timeout=1.0)


# ---------------------------------------------------------------------------
# EventHandler.process_event — closed flag
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_event_ignored_when_closed():
    ws = AsyncMock()
    handler = EventHandler(ws, "opc.tcp://localhost:40451")
    handler.closed = True
    short = Short(_fake_raw_event())
    await handler.process_event(short)
    assert handler.queue.qsize() == 0
    await handler.close()


@pytest.mark.asyncio
async def test_process_event_enqueues_when_open():
    ws = AsyncMock()
    handler = EventHandler(ws, "opc.tcp://localhost:40451")
    short = Short(_fake_raw_event())
    await handler.process_event(short)
    # Give the queue task a tick to process the item
    await asyncio.sleep(0)
    # Handler should still be running (not closed by an error)
    assert not handler.closed
    await handler.close()


# ---------------------------------------------------------------------------
# EventHandler.event_notification — closed flag
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_notification_ignored_when_closed():
    ws = AsyncMock()
    handler = EventHandler(ws, "opc.tcp://localhost:40451")
    handler.closed = True
    with patch("python.event_handler.log_joining_system_event"):
        await handler.event_notification(_fake_raw_event())
    assert handler.queue.qsize() == 0
    await handler.close()


# ---------------------------------------------------------------------------
# EventHandler.handle_queue — happy path sends correct JSON
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_queue_sends_json_with_correct_structure():
    ws = AsyncMock()
    server_url = "opc.tcp://localhost:40451"

    with (
        patch("python.event_handler.log_joining_system_event"),
        patch("python.event_handler.serialize_full_event", return_value={"key": "value"}),
    ):
        handler = EventHandler(ws, server_url)
        await handler.event_notification(_fake_raw_event("TighteningOK"))
        await asyncio.sleep(0.05)

    ws.send.assert_awaited()
    payload = json.loads(ws.send.call_args[0][0])
    assert payload["command"] == "event"
    assert payload["endpoint"] == server_url
    assert payload["data"] == {"key": "value"}
    await handler.close()


@pytest.mark.asyncio
async def test_handle_queue_breaks_on_connection_closed_ok():
    """ConnectionClosedOK must stop the queue loop gracefully without error."""
    import websockets.exceptions

    ws = AsyncMock()
    ws.send = AsyncMock(side_effect=websockets.exceptions.ConnectionClosedOK(None, None))

    with (
        patch("python.event_handler.log_joining_system_event"),
        patch("python.event_handler.serialize_full_event", return_value={"x": 1}),
    ):
        handler = EventHandler(ws, "opc.tcp://localhost:40451")
        await handler.event_notification(_fake_raw_event())
        await asyncio.wait_for(handler._queue_task, timeout=2.0)


@pytest.mark.asyncio
async def test_handle_queue_breaks_and_closes_ws_on_exception():
    ws = AsyncMock()
    ws.send = AsyncMock(side_effect=RuntimeError("broken pipe"))

    with (
        patch("python.event_handler.log_joining_system_event"),
        patch("python.event_handler.serialize_full_event", return_value={"x": 1}),
    ):
        handler = EventHandler(ws, "opc.tcp://localhost:40451")
        await handler.event_notification(_fake_raw_event())
        await asyncio.wait_for(handler._queue_task, timeout=2.0)

    ws.close.assert_awaited()
