"""
Tests for IJT_Console_Client/event_handler.py

Covers:
- EventHandler initializes with a running queue task
- handle_queue exits cleanly on CancelledError (regression: Ctrl+C noise)
- handle_queue drains the queue and exits on sentinel (None)
- shutdown() puts sentinel, close() awaits task completion
- event_notification() skips enqueue when handler is closed
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from event_handler import EventHandler


def _make_handler():
    ws = AsyncMock()
    client = MagicMock()
    return EventHandler(websocket=ws, server_url="opc.tcp://localhost:4840", client=client)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_event_handler_creates_queue_task():
    h = _make_handler()
    assert h._queue_task is not None
    assert not h._queue_task.done()
    await h.close()


# ---------------------------------------------------------------------------
# Regression: Ctrl+C must NOT produce "Exception ignored while closing generator"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_queue_exits_cleanly_on_cancellation():
    """Cancelling the queue task must raise no exception and leave no pending task noise."""
    h = _make_handler()
    task = h._queue_task
    assert not task.done()

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass  # expected

    assert task.done()
    assert task.cancelled()


@pytest.mark.asyncio
async def test_handle_queue_exits_on_sentinel():
    """Putting None on the queue causes handle_queue to exit normally."""
    h = _make_handler()
    await h.queue.put(None)
    await asyncio.wait_for(h._queue_task, timeout=2.0)
    assert h._queue_task.done()
    assert not h._queue_task.cancelled()


# ---------------------------------------------------------------------------
# shutdown / close
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shutdown_puts_sentinel():
    h = _make_handler()
    assert not h.closed
    await h.shutdown()
    assert h.closed
    # Queue should have the sentinel
    assert not h.queue.empty()
    item = await h.queue.get()
    assert item is None
    # Clean up remaining task
    h._queue_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await h._queue_task


@pytest.mark.asyncio
async def test_close_completes_queue_task():
    h = _make_handler()
    await h.close()
    assert h._queue_task.done()


@pytest.mark.asyncio
async def test_close_is_idempotent():
    """Calling close() twice must not raise."""
    h = _make_handler()
    await h.close()
    await h.close()  # second call is a no-op


# ---------------------------------------------------------------------------
# event_notification skips when closed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_event_notification_skips_when_closed():
    h = _make_handler()
    h.closed = True
    initial_size = h.queue.qsize()
    mock_event = MagicMock()
    await h.event_notification(mock_event)
    assert h.queue.qsize() == initial_size  # nothing added
    h._queue_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await h._queue_task
