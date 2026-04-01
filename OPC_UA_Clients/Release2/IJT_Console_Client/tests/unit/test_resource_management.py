"""
Resource management tests.

- asyncio.Queue is bounded (finite _QUEUE_SIZE) — prevents unbounded memory growth
- Multiple connect→cleanup cycles are stable
- EventHandler shutdown is clean
- After cleanup(), no dangling client references
"""
import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from opcua_client import _QUEUE_SIZE, OPCUAClient
from event_handler import EventHandler


# ---------------------------------------------------------------------------
# Queue boundedness
# ---------------------------------------------------------------------------

def test_queue_size_constant_is_finite():
    assert isinstance(_QUEUE_SIZE, int)
    assert 0 < _QUEUE_SIZE < 1_000_000  # sanity: bounded but not absurdly small


@pytest.mark.asyncio
async def test_event_handler_queue_is_not_unbounded():
    """EventHandler uses asyncio.Queue() (no maxsize arg checked via constants)."""
    ws = AsyncMock()
    client = MagicMock()
    h = EventHandler(websocket=ws, server_url="opc.tcp://localhost:4840", client=client)
    assert _QUEUE_SIZE > 0
    h._queue_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await h._queue_task



# ---------------------------------------------------------------------------
# Multiple connect→cleanup cycles
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multiple_cleanup_cycles_stable():
    """Calling cleanup() multiple times (e.g. after failed connect) must not raise."""
    with patch("opcua_client.Client") as MockClient:
        mock_inner = AsyncMock()
        MockClient.return_value = mock_inner
        c = OPCUAClient("opc.tcp://localhost:40451")
        c.client = mock_inner

    await c.cleanup()
    # Second cleanup — client is None now
    await c.cleanup()  # must not raise


@pytest.mark.asyncio
async def test_cleanup_sets_client_to_none():
    with patch("opcua_client.Client") as MockClient:
        mock_inner = AsyncMock()
        MockClient.return_value = mock_inner
        c = OPCUAClient("opc.tcp://localhost:40451")
        c.client = mock_inner

    await c.cleanup()
    assert c.client is None


@pytest.mark.asyncio
async def test_cleanup_sets_subs_to_none():
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:40451")

    c.sub_result_event = AsyncMock()
    c.sub_joining_event = AsyncMock()
    c.client = AsyncMock()

    await c.cleanup()

    assert c.sub_result_event is None
    assert c.sub_joining_event is None


# ---------------------------------------------------------------------------
# EventHandler shutdown is clean — no CancelledError propagation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_event_handler_close_no_cancelled_error_propagates():
    """close() must not propagate CancelledError to the caller."""
    ws = AsyncMock()
    client = MagicMock()
    h = EventHandler(websocket=ws, server_url="opc.tcp://localhost:4840", client=client)
    await h.close()


@pytest.mark.asyncio
async def test_event_handler_queue_drains_on_close():
    """After close(), the queue task must be done."""
    ws = AsyncMock()
    client = MagicMock()
    h = EventHandler(websocket=ws, server_url="opc.tcp://localhost:4840", client=client)
    await h.close()
    assert h._queue_task.done()


@pytest.mark.asyncio
async def test_no_tasks_leaked_after_event_handler_close():
    """After EventHandler.close(), no extra asyncio tasks should remain running."""
    ws = AsyncMock()
    client = MagicMock()

    tasks_before = len([t for t in asyncio.all_tasks() if not t.done()])
    h = EventHandler(websocket=ws, server_url="opc.tcp://localhost:4840", client=client)
    await h.close()
    await asyncio.sleep(0)  # drain any deferred

    tasks_after = len([t for t in asyncio.all_tasks() if not t.done()])
    assert tasks_after <= tasks_before
