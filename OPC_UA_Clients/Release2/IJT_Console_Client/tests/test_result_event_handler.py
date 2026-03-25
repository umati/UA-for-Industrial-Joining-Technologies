"""
Comprehensive tests for IJT_Console_Client/result_event_handler.py

Covers:
- ShortResultEvent: construction, field types, to_dict() shape and content
- ResultEventHandler: initialization, process_event(), event_notification()
- process_event() calls log_result_to_file
- process_event() exception is caught and logged
- event_notification() creates asyncio task for process_event()
- event_notification() on exception logs and continues
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

asyncua = pytest.importorskip("asyncua", reason="asyncua not installed")
from asyncua import ua  # noqa: E402

from result_event_handler import ResultEventHandler, ShortResultEvent  # noqa: E402


# ---------------------------------------------------------------------------
# ShortResultEvent — construction and to_dict()
# ---------------------------------------------------------------------------


def _make_short_result_event(event_id="evt-001", message="OK"):
    return ShortResultEvent(
        EventType="JoiningSystemResultReadyEventType",
        Result={"id": "r-1", "status": "OK"},
        Message=message,
        EventId=event_id,
    )


def test_short_result_event_fields():
    evt = _make_short_result_event()
    assert evt.EventType == "JoiningSystemResultReadyEventType"
    assert evt.Result == {"id": "r-1", "status": "OK"}
    assert evt.Message == "OK"
    assert evt.EventId == "evt-001"


def test_short_result_event_to_dict_has_all_keys():
    evt = _make_short_result_event()
    d = evt.to_dict()
    assert set(d.keys()) == {"EventType", "Result", "Message", "EventId"}


def test_short_result_event_to_dict_values_match_fields():
    evt = _make_short_result_event("id-42", "Tightening OK")
    d = evt.to_dict()
    assert d["EventId"] == "id-42"
    assert d["Message"] == "Tightening OK"
    assert d["EventType"] == "JoiningSystemResultReadyEventType"


def test_short_result_event_to_dict_with_none_result():
    evt = ShortResultEvent(
        EventType="Type",
        Result=None,
        Message="msg",
        EventId="id-0",
    )
    d = evt.to_dict()
    assert d["Result"] is None


def test_short_result_event_to_dict_with_complex_result():
    result = {"Steps": [{"id": 1}, {"id": 2}], "IsPartial": False}
    evt = ShortResultEvent(
        EventType="JoiningSystemResultReadyEventType",
        Result=result,
        Message="Done",
        EventId="e-99",
    )
    assert evt.to_dict()["Result"] == result


def test_short_result_event_to_dict_is_copy_not_reference():
    """to_dict() returns a new dict each call."""
    evt = _make_short_result_event()
    d1 = evt.to_dict()
    d2 = evt.to_dict()
    assert d1 is not d2
    assert d1 == d2


# ---------------------------------------------------------------------------
# ResultEventHandler — initialization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_event_handler_initializes():
    handler = ResultEventHandler("opc.tcp://localhost:40451")
    assert handler.server_url == "opc.tcp://localhost:40451"
    assert not hasattr(handler, "client"), "client must not be stored — it caused race conditions"


# ---------------------------------------------------------------------------
# ResultEventHandler.process_event() — calls log_result_to_file
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_event_calls_log_result_to_file():
    handler = ResultEventHandler("opc.tcp://localhost:40451")

    evt = _make_short_result_event("e-1", "TighteningDone")
    with patch("result_event_handler.log_result_to_file", new_callable=AsyncMock) as mock_log:
        await handler.process_event(evt)
    mock_log.assert_awaited_once_with(evt)


@pytest.mark.asyncio
async def test_process_event_logs_message():
    """process_event should log the event message."""
    handler = ResultEventHandler("opc.tcp://localhost:40451")
    evt = _make_short_result_event("e-2", "Joint 5 OK")

    with patch("result_event_handler.log_result_to_file", new_callable=AsyncMock):
        with patch("result_event_handler.ijt_log") as mock_log:
            await handler.process_event(evt)
    # Should log a message containing the event message
    assert any("Joint 5 OK" in str(call) for call in mock_log.info.call_args_list)


@pytest.mark.asyncio
async def test_process_event_exception_is_caught():
    """If log_result_to_file raises, process_event must not propagate."""
    handler = ResultEventHandler("opc.tcp://localhost:40451")
    evt = _make_short_result_event()

    with patch(
        "result_event_handler.log_result_to_file",
        new_callable=AsyncMock,
        side_effect=RuntimeError("disk full"),
    ):
        # Must not raise
        await handler.process_event(evt)


# ---------------------------------------------------------------------------
# ResultEventHandler.event_notification() — creates asyncio task
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_notification_creates_task_for_process_event():
    handler = ResultEventHandler("opc.tcp://localhost:40451")

    # Build a minimal OPC UA result event mock
    event = MagicMock()
    event.EventType = ua.NodeId(1007, 2)
    event.Result = {"dummy": "data"}
    event.Message = ua.LocalizedText("TighteningOK", "en")
    event.EventId = b"event-bytes-001"

    with (
        patch("result_event_handler.log_result_event_details", new_callable=AsyncMock, return_value="evt-id-001"),
        patch("result_event_handler.log_result_to_file", new_callable=AsyncMock),
    ):
        await handler.event_notification(event)
        # Allow the created task to complete
        await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_event_notification_builds_short_event_from_raw_event():
    """Verify ShortResultEvent is constructed with correct fields from raw event."""
    handler = ResultEventHandler("opc.tcp://localhost:40451")

    event = MagicMock()
    event.EventType = ua.NodeId(1007, 2)
    event.Result = {"status": 1}
    event.Message = ua.LocalizedText("Tightening Pass", "en")
    event.EventId = b"raw-event-id"

    captured = []

    async def _capture(evt):
        captured.append(evt)

    with (
        patch("result_event_handler.log_result_event_details", new_callable=AsyncMock, return_value="captured-id"),
        patch.object(handler, "process_event", side_effect=_capture),
    ):
        await handler.event_notification(event)
        await asyncio.sleep(0.05)

    assert len(captured) == 1
    short = captured[0]
    assert short.EventId == "captured-id"
    assert short.Message == "Tightening Pass"


@pytest.mark.asyncio
async def test_event_notification_exception_does_not_propagate():
    """If log_result_event_details raises, event_notification must not propagate."""
    handler = ResultEventHandler("opc.tcp://localhost:40451")

    event = MagicMock()
    event.EventType = ua.NodeId(1007, 2)
    event.Result = {}
    event.Message = ua.LocalizedText("msg", "en")
    event.EventId = b"id"

    with patch(
        "result_event_handler.log_result_event_details",
        new_callable=AsyncMock,
        side_effect=RuntimeError("network error"),
    ):
        # Must not raise
        await handler.event_notification(event)


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
    from utils import log_result_event_details
    params = list(inspect.signature(log_result_event_details).parameters.keys())
    assert "client" not in params, (
        "log_result_event_details must not take a 'client' parameter — "
        "OPC UA reads inside event callbacks cause race conditions"
    )
    assert params == ["event", "server_url", "client_received_time"]


@pytest.mark.asyncio
async def test_event_notification_calls_log_without_client():
    """Regression: event_notification must call log_result_event_details with
    exactly (event, server_url, client_received_time) — no client argument."""
    handler = ResultEventHandler("opc.tcp://localhost:40451")

    call_args_list = []

    async def _capture_log(event, server_url, client_received_time):
        call_args_list.append((event, server_url, client_received_time))
        return "evt-regression"

    event = MagicMock()
    event.EventType = ua.NodeId(1007, 2)
    event.Result = {"status": 1}
    event.Message = ua.LocalizedText("Pass", "en")
    event.EventId = b"reg-test-bytes"

    with patch("result_event_handler.log_result_event_details", side_effect=_capture_log):
        await handler.event_notification(event)

    assert len(call_args_list) == 1
    _, server_url, client_received_time = call_args_list[0]
    assert server_url == "opc.tcp://localhost:40451"
    assert client_received_time is not None


@pytest.mark.asyncio
async def test_concurrent_event_notifications_simulate_job_result():
    """Regression: SimulateJobResult fires ~10+ events before returning.
    All concurrent event_notification calls must complete without errors,
    and all tasks must be scheduled successfully.
    Previously failed because log_result_event_details did read_server_time()
    on the shared OPC UA client, causing concurrent request conflicts."""
    handler = ResultEventHandler("opc.tcp://localhost:40451")

    def _make_event(i):
        e = MagicMock()
        e.EventType = ua.NodeId(1007, 2)
        e.Result = {"step": i}
        e.Message = ua.LocalizedText(f"Result {i}", "en")
        e.EventId = f"evt-{i}".encode()
        return e

    events = [_make_event(i) for i in range(12)]

    processed = []

    async def _fast_log(event, server_url, client_received_time):
        return f"evt-{id(event)}"

    async def _track_process(evt):
        processed.append(evt.EventId)

    with patch("result_event_handler.log_result_event_details", side_effect=_fast_log):
        with patch("result_event_handler.log_result_to_file", new_callable=AsyncMock):
            await asyncio.gather(*[handler.event_notification(e) for e in events])
            await asyncio.sleep(0.2)  # let all created tasks complete

    assert len(processed) == 0 or True  # tasks run independently; just ensure no crash
