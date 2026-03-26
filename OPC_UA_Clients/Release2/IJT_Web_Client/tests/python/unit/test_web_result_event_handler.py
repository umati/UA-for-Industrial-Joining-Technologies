"""
Comprehensive tests for IJT_Web_Client/Python/result_event_handler.py

Covers:
- Short class: field storage (EventType, Result, Message, EventId)
- ResultEventHandler lifecycle: init creates queue+task, shutdown/close
- ResultEventHandler.process_event: serializes Short → JSON with command="event",
  enqueues JSON string, respects closed flag, exception caught
- ResultEventHandler.event_notification: respects closed flag, creates Short,
  calls process_event; exception does not propagate
- ResultEventHandler.handle_queue: sends JSON string via websocket,
  breaks on ConnectionClosedOK, breaks on other exception
- Double shutdown is idempotent
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

asyncua = pytest.importorskip("asyncua", reason="asyncua not installed")
from asyncua import ua  # noqa: E402

from python.result_event_handler import ResultEventHandler, Short  # noqa: E402


# ---------------------------------------------------------------------------
# Short class
# ---------------------------------------------------------------------------


def test_short_stores_all_fields():
    event_type = ua.NodeId(1007, 2)
    result_data = {"Steps": [1, 2]}
    # asyncua 1.x: LocalizedText(Text, Locale)
    message = ua.LocalizedText("Tightening OK", "en")
    short = Short(event_type, result_data, message, "evt-abc")
    assert short.EventType is event_type
    assert short.Result is result_data
    assert short.Message is message
    assert short.EventId == "evt-abc"


def test_short_result_can_be_none():
    short = Short(ua.NodeId(0, 0), None, ua.LocalizedText("", "en"), "id-0")
    assert short.Result is None


# ---------------------------------------------------------------------------
# ResultEventHandler — lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_event_handler_creates_queue_and_task():
    ws = AsyncMock()
    handler = ResultEventHandler(ws, "opc.tcp://localhost:40451")
    assert not handler._queue_task.done()
    assert not handler.closed
    await handler.close()


@pytest.mark.asyncio
async def test_result_event_handler_shutdown_sets_closed():
    ws = AsyncMock()
    handler = ResultEventHandler(ws, "opc.tcp://localhost:40451")
    await handler.shutdown()
    assert handler.closed
    await handler._queue_task


@pytest.mark.asyncio
async def test_result_event_handler_close_awaits_task():
    ws = AsyncMock()
    handler = ResultEventHandler(ws, "opc.tcp://localhost:40451")
    await handler.close()
    assert handler._queue_task.done()
    assert handler.closed


@pytest.mark.asyncio
async def test_result_event_handler_double_shutdown_idempotent():
    ws = AsyncMock()
    handler = ResultEventHandler(ws, "opc.tcp://localhost:40451")
    await handler.shutdown()
    await handler.shutdown()
    await asyncio.wait_for(handler._queue_task, timeout=1.0)


# ---------------------------------------------------------------------------
# ResultEventHandler.process_event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_event_enqueues_json_string():
    ws = AsyncMock()
    server_url = "opc.tcp://localhost:40451"
    handler = ResultEventHandler(ws, server_url)

    short = Short(ua.NodeId(1007, 2), {"result": 1}, ua.LocalizedText("OK", "en"), "id-1")

    with patch("python.result_event_handler.serialize_full_event", return_value={"serialized": True}):
        await handler.process_event(short)
        await asyncio.sleep(0)  # let queue task pick it up

    # The queue should have had something; the handler may have consumed it already
    # — just verify ws.send was eventually called
    await asyncio.sleep(0.05)
    ws.send.assert_awaited()

    payload = json.loads(ws.send.call_args[0][0])
    assert payload["command"] == "event"
    assert payload["endpoint"] == server_url
    assert payload["data"] == {"serialized": True}
    await handler.close()


@pytest.mark.asyncio
async def test_process_event_respects_closed_flag():
    ws = AsyncMock()
    handler = ResultEventHandler(ws, "opc.tcp://localhost:40451")
    handler.closed = True

    short = Short(ua.NodeId(0, 0), {}, ua.LocalizedText("", "en"), "id-0")
    await handler.process_event(short)

    assert handler.queue.qsize() == 0
    await handler.close()


@pytest.mark.asyncio
async def test_process_event_exception_caught():
    ws = AsyncMock()
    handler = ResultEventHandler(ws, "opc.tcp://localhost:40451")

    short = Short(ua.NodeId(0, 0), {}, ua.LocalizedText("", "en"), "id-0")
    with patch("python.result_event_handler.serialize_full_event", side_effect=ValueError("bad")):
        # Must not raise
        await handler.process_event(short)
    await handler.close()


# ---------------------------------------------------------------------------
# ResultEventHandler.event_notification
# ---------------------------------------------------------------------------


def _make_result_event():
    event = MagicMock()
    event.EventType = ua.NodeId(1007, 2)
    event.Result = {"status": 1}
    # asyncua 1.x: LocalizedText(Text, Locale)
    event.Message = ua.LocalizedText("Pass", "en")
    event.EventId = b"result-evt-bytes"
    return event


@pytest.mark.asyncio
async def test_event_notification_respects_closed_flag():
    ws = AsyncMock()
    handler = ResultEventHandler(ws, "opc.tcp://localhost:40451")
    handler.closed = True

    with patch("python.result_event_handler.log_result_event_details", new_callable=AsyncMock):
        await handler.event_notification(_make_result_event())

    assert handler.queue.qsize() == 0
    await handler.close()


@pytest.mark.asyncio
async def test_event_notification_builds_short_and_calls_process():
    ws = AsyncMock()
    handler = ResultEventHandler(ws, "opc.tcp://localhost:40451")

    captured = []

    async def _capture(evt):
        captured.append(evt)

    with (
        patch("python.result_event_handler.log_result_event_details", new_callable=AsyncMock, return_value="evt-id-xx"),
        patch.object(handler, "process_event", side_effect=_capture),
    ):
        await handler.event_notification(_make_result_event())

    assert len(captured) == 1
    short = captured[0]
    assert short.EventId == "evt-id-xx"
    assert short.Message.Text == "Pass"
    await handler.close()


@pytest.mark.asyncio
async def test_event_notification_exception_does_not_propagate():
    ws = AsyncMock()
    handler = ResultEventHandler(ws, "opc.tcp://localhost:40451")

    with patch(
        "python.result_event_handler.log_result_event_details",
        new_callable=AsyncMock,
        side_effect=RuntimeError("server gone"),
    ):
        # Must not raise
        await handler.event_notification(_make_result_event())
    await handler.close()


# ---------------------------------------------------------------------------
# ResultEventHandler.handle_queue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_queue_breaks_on_connection_closed_ok():
    import websockets.exceptions

    ws = AsyncMock()
    ws.send = AsyncMock(side_effect=websockets.exceptions.ConnectionClosedOK(None, None))
    server_url = "opc.tcp://localhost:40451"
    handler = ResultEventHandler(ws, server_url)

    short = Short(ua.NodeId(0, 0), {}, ua.LocalizedText("msg", "en"), "id-ok")
    with patch("python.result_event_handler.serialize_full_event", return_value={}):
        await handler.process_event(short)
    await asyncio.wait_for(handler._queue_task, timeout=2.0)


@pytest.mark.asyncio
async def test_handle_queue_breaks_on_exception():
    ws = AsyncMock()
    ws.send = AsyncMock(side_effect=RuntimeError("connection reset"))
    handler = ResultEventHandler(ws, "opc.tcp://localhost:40451")

    short = Short(ua.NodeId(0, 0), {}, ua.LocalizedText("msg", "en"), "id-err")
    with patch("python.result_event_handler.serialize_full_event", return_value={}):
        await handler.process_event(short)
    await asyncio.wait_for(handler._queue_task, timeout=2.0)


# ---------------------------------------------------------------------------
# Regression tests: SimulateJobResult concurrent-event race condition
# (fix: log_result_event_details must NOT do OPC UA reads inside event callbacks)
# ---------------------------------------------------------------------------


def test_log_result_event_details_has_no_client_parameter():
    """Regression: log_result_event_details must not accept a client argument.

    If a client parameter exists, a caller might pass the shared OPC UA client,
    triggering concurrent read_server_time() calls while call_method() is pending
    on the same client — causing asyncua to throw "Unhandled exception while
    sending request to OPC UA server" for methods like SimulateJobResult that
    fire many events before returning.
    """
    import inspect
    from python.utils import log_result_event_details
    params = list(inspect.signature(log_result_event_details).parameters.keys())
    assert "client" not in params, (
        "log_result_event_details must not take a 'client' parameter — "
        "OPC UA reads inside event callbacks cause race conditions"
    )
    assert params == ["event", "_server_url", "client_received_time"]


@pytest.mark.asyncio
async def test_event_notification_calls_log_without_client():
    """Regression: event_notification must call log_result_event_details with
    exactly (event, server_url, client_received_time) — no client argument."""
    ws = AsyncMock()
    handler = ResultEventHandler(ws, "opc.tcp://localhost:40451")

    call_args_list = []

    async def _capture_log(event, server_url, client_received_time):
        call_args_list.append((event, server_url, client_received_time))
        return "evt-regression"

    with patch("python.result_event_handler.log_result_event_details",
               side_effect=_capture_log):
        await handler.event_notification(_make_result_event())

    assert len(call_args_list) == 1
    _, server_url, client_received_time = call_args_list[0]
    assert server_url == "opc.tcp://localhost:40451"
    assert client_received_time is not None
    await handler.close()


@pytest.mark.asyncio
async def test_concurrent_event_notifications_simulate_job_result():
    """Regression: SimulateJobResult fires ~10+ events before returning.
    All concurrent event_notification calls must complete without errors,
    and all events must be enqueued and sent via WebSocket.
    Previously failed because log_result_event_details did read_server_time()
    on the shared OPC UA client, causing concurrent request conflicts."""
    ws = AsyncMock()
    handler = ResultEventHandler(ws, "opc.tcp://localhost:40451")

    events = [_make_result_event() for _ in range(12)]  # realistic SimulateJobResult count

    async def _fast_log(event, server_url, client_received_time):
        return f"evt-{id(event)}"

    with patch("python.result_event_handler.log_result_event_details",
               side_effect=_fast_log):
        # Fire all events concurrently — as asyncua does when a method triggers many events
        await asyncio.gather(*[handler.event_notification(e) for e in events])

    # Allow queue to drain
    await asyncio.sleep(0.2)
    assert ws.send.call_count == 12, (
        f"Expected 12 events sent, got {ws.send.call_count} — "
        "concurrent event notifications failed"
    )
    await handler.close()
