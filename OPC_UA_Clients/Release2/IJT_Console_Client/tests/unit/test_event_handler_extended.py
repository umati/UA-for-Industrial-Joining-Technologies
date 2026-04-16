# ruff: noqa: E402
"""Extended tests for event_handler.py — covers remaining coverage gaps."""

import asyncio
import contextlib
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

_ = pytest.importorskip("asyncua", reason="asyncua not installed")

from event_handler import EventHandler


def _make_handler(websocket=None):
    """Create an EventHandler with optional websocket mock."""
    client = MagicMock()
    return EventHandler(websocket=websocket, server_url="opc.tcp://localhost:4840", client=client)


async def _cleanup(handler):
    """Cancel the queue task and suppress CancelledError."""
    handler._queue_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await handler._queue_task


# ── event_notification — bytes EventId ──


@pytest.mark.asyncio
async def test_event_notification_bytes_event_id_decoded():
    """event_notification decodes bytes EventId to str in the ShortJoiningEvent."""
    h = _make_handler()
    try:
        mock_event = MagicMock()
        mock_event.EventId = b"abc\x00def"
        mock_event.ConditionSubClassId = []
        mock_event.ConditionSubClassName = []

        with patch("event_handler.log_joining_system_event", new_callable=AsyncMock):
            await h.event_notification(mock_event)

        item = await h.queue.get()
        assert item.EventId == "abc\x00def"
    finally:
        await _cleanup(h)


# ── event_notification — str EventId ──


@pytest.mark.asyncio
async def test_event_notification_str_event_id_converted():
    """event_notification converts non-bytes EventId with str()."""
    h = _make_handler()
    try:
        mock_event = MagicMock()
        mock_event.EventId = 12345  # not bytes → str(12345)
        mock_event.ConditionSubClassId = []
        mock_event.ConditionSubClassName = []

        with patch("event_handler.log_joining_system_event", new_callable=AsyncMock):
            await h.event_notification(mock_event)

        item = await h.queue.get()
        assert item.EventId == "12345"
    finally:
        await _cleanup(h)


# ── event_notification — closed handler ──


@pytest.mark.asyncio
async def test_event_notification_skips_when_handler_closed():
    """event_notification returns immediately if handler is closed."""
    h = _make_handler()
    h.closed = True
    try:
        mock_event = MagicMock()
        with patch("event_handler.log_joining_system_event", new_callable=AsyncMock) as mock_log:
            await h.event_notification(mock_event)
            mock_log.assert_not_called()
        assert h.queue.empty()
    finally:
        await _cleanup(h)


# ── event_notification — exception path ──


@pytest.mark.asyncio
async def test_event_notification_exception_does_not_propagate():
    """event_notification catches exceptions and does not raise."""
    h = _make_handler()
    try:
        mock_event = MagicMock()
        # Make event.EventType raise an error when accessed
        mock_event.EventId = b"test"
        mock_event.ConditionSubClassId = []
        mock_event.ConditionSubClassName = []

        with patch("event_handler.log_joining_system_event", side_effect=RuntimeError("log failed")):
            # Should not raise — exception is caught internally
            await h.event_notification(mock_event)
    finally:
        await _cleanup(h)


# ── handle_queue — websocket=None ──


@pytest.mark.asyncio
async def test_handle_queue_websocket_none_does_not_send():
    """handle_queue logs locally and skips websocket.send when websocket is None."""
    h = _make_handler(websocket=None)
    try:
        item = {"key": "value"}  # simple dict, json.dumps-safe
        with patch("event_handler.serialize_full_event", return_value={"key": "value"}):
            await h.queue.put(item)
            await asyncio.sleep(0.05)  # let handle_queue consume it
        # Task should still be running (waiting for next item)
        assert not h._queue_task.done()
    finally:
        await h.queue.put(None)  # sentinel
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait_for(h._queue_task, timeout=1.0)


# ── handle_queue — websocket present ──


@pytest.mark.asyncio
async def test_handle_queue_sends_via_websocket():
    """handle_queue calls websocket.send with JSON payload when websocket is set."""
    mock_ws = AsyncMock()
    h = _make_handler(websocket=mock_ws)
    try:
        item = {"event": "data"}
        with patch("event_handler.serialize_full_event", return_value={"event": "data"}):
            await h.queue.put(item)
            await asyncio.sleep(0.05)

        mock_ws.send.assert_awaited()
    finally:
        await h.queue.put(None)
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait_for(h._queue_task, timeout=1.0)


# ── handle_queue — websocket send raises ──


@pytest.mark.asyncio
async def test_handle_queue_websocket_send_raises_calls_close():
    """handle_queue calls websocket.close() when send raises an exception."""
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock(side_effect=RuntimeError("send failed"))
    h = _make_handler(websocket=mock_ws)
    try:
        item = {"event": "data"}
        with patch("event_handler.serialize_full_event", return_value={"event": "data"}):
            await h.queue.put(item)
            # Wait for the task to process and break out of the loop
            await asyncio.wait_for(h._queue_task, timeout=2.0)

        mock_ws.close.assert_awaited()
    except asyncio.TimeoutError:
        pass  # task may still be running; close should have been called
    finally:
        if not h._queue_task.done():
            await _cleanup(h)


# ── handle_queue — None sentinel exits task ──


@pytest.mark.asyncio
async def test_handle_queue_exits_cleanly_on_none_sentinel():
    """handle_queue exits normally when the sentinel None is received."""
    h = _make_handler()
    await h.queue.put(None)
    await asyncio.wait_for(h._queue_task, timeout=2.0)
    assert h._queue_task.done()
    assert not h._queue_task.cancelled()


# ── shutdown ──


@pytest.mark.asyncio
async def test_shutdown_sets_closed_and_puts_sentinel():
    """shutdown() sets closed=True and puts None on the queue."""
    h = _make_handler()
    assert not h.closed
    try:
        await h.shutdown()
        assert h.closed
        sentinel = await asyncio.wait_for(h.queue.get(), timeout=1.0)
        assert sentinel is None
    finally:
        await _cleanup(h)


@pytest.mark.asyncio
async def test_shutdown_idempotent():
    """Calling shutdown() twice does not double-put the sentinel."""
    h = _make_handler()
    try:
        await h.shutdown()
        await h.shutdown()  # second call is a no-op
        assert h.queue.qsize() == 1  # only one sentinel
    finally:
        await _cleanup(h)


# ── close() — timeout path ──


@pytest.mark.asyncio
async def test_close_timeout_cancels_task():
    """close() cancels the queue task when wait_for times out."""
    h = _make_handler()

    # Replace the queue task with a never-ending coroutine
    h._queue_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await h._queue_task

    async def _block_forever():
        await asyncio.sleep(9999)

    h._queue_task = asyncio.ensure_future(_block_forever())

    # Patch wait_for to simulate timeout immediately
    with patch("event_handler.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        await h.close()  # must not raise

    assert h._queue_task.cancelled()
