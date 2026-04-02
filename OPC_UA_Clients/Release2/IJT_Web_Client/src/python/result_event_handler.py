"""WebSocket event handler for OPC UA ResultReadyEventType notifications.

Incoming result events are filtered down to a lightweight :class:`Short`
snapshot, detailed timing information is logged, and the serialized payload is
forwarded to the browser by the :class:`ResultEventHandler` queue worker.
"""

import asyncio
import contextlib
import json
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytz
import websockets

from python.ijt_logger import ijt_log
from python.serialize_data import serialize_full_event
from python.utils import log_result_event_details

_QUEUE_SIZE = 200
_SHUTDOWN_TIMEOUT_S = 5.0


@dataclass
class Short:
    """Lightweight snapshot of a ResultReadyEvent notification.

    Stores only the fields forwarded to the browser (``EventType``,
    ``Result``, ``Message``, ``EventId``), discarding the rest of the raw
    asyncua event to keep the serialized payload small.

    Field names use OPC UA PascalCase convention to match the asyncua event
    attribute names they are sourced from.
    """

    EventType: Any
    Result: Any
    Message: Any
    EventId: str


class ResultEventHandler:
    """Asyncio-based handler that queues ResultReadyEvent notifications for WebSocket delivery.

    One instance is created per OPC UA subscription.  Incoming events are
    logged (timing/latency), filtered to a :class:`Short` snapshot, serialized,
    and forwarded to the browser via the internal queue worker.
    """

    def __init__(self, websocket: Any, server_url: str) -> None:
        """Initialise the handler and start the background queue-worker task.

        Args:
            websocket: Active WebSocket connection used to push result events
                to the browser.
            server_url: OPC UA server URL — included in every event message so
                the front-end can route it to the correct connection view.
        """
        self.websocket = websocket
        self.server_url = server_url
        self.queue: asyncio.Queue = asyncio.Queue(_QUEUE_SIZE)
        self.closed = False
        self._queue_task = asyncio.create_task(self.handle_queue())
        ijt_log.info("ResultEventHandler initialized.")

    async def process_event(self, event_obj: Short):
        """Coroutine. Serialize and enqueue a result-event snapshot for WebSocket delivery.

        Args:
            event_obj: A :class:`Short` snapshot ready for serialization.
        """
        if self.closed:
            return
        try:
            arg = serialize_full_event(event_obj)
            return_value = {
                "command": "event",
                "endpoint": self.server_url,
                "data": arg,
            }
            await self.queue.put(json.dumps(return_value))
        except Exception as exc:
            ijt_log.error(f"Result event serialization failed: {exc}")

    async def event_notification(self, event: Any) -> None:
        """Coroutine. asyncua subscription callback for ResultReadyEventType events.

        Records the client-received timestamp, logs event timing details via
        :func:`~Python.utils.log_result_event_details`, builds a :class:`Short`
        snapshot, and forwards it via :meth:`process_event`.

        Args:
            event: Raw asyncua event object delivered by the subscription.
        """
        if self.closed:
            return
        try:
            client_received_time = datetime.now(pytz.utc)
            event_id = await log_result_event_details(
                event, self.server_url, client_received_time
            )
            filtered_event = Short(
                EventType=event.EventType,
                Result=event.Result,
                Message=event.Message,
                EventId=event_id,
            )
            await self.process_event(filtered_event)
        except Exception as exc:
            ijt_log.error(f"Error handling result event notification: {exc}")
            ijt_log.error(traceback.format_exc())

    async def handle_queue(self):
        """Coroutine. Background worker that drains the queue and sends JSON messages.

        Runs until a sentinel ``None`` item is dequeued (placed by
        :meth:`shutdown`).  Breaks out and closes the WebSocket on
        unrecoverable send errors.
        """
        while True:
            item = await self.queue.get()
            if item is None:
                self.queue.task_done()
                break
            try:
                await self.websocket.send(item)
            except websockets.exceptions.ConnectionClosedOK:
                ijt_log.info("WebSocket connection closed normally.")
                break
            except Exception as exc:
                ijt_log.error(f"Error sending result event message: {exc}")
                try:
                    await self.websocket.close()
                except Exception as close_exc:
                    ijt_log.debug(
                        f"WebSocket close failed during error recovery: {close_exc}"
                    )
                break
            finally:
                self.queue.task_done()

    async def shutdown(self):
        """Coroutine. Signal the queue worker to stop by enqueuing a sentinel ``None``.

        Idempotent — only enqueues the sentinel on the first call.
        """
        if not self.closed:
            self.closed = True
            await self.queue.put(None)

    async def close(self):
        """Gracefully shut down the handler and await queue-task completion.

        Safe to call even if ``closed`` was set manually — the task will be
        cancelled with a short timeout instead of waiting forever.
        """
        await self.shutdown()
        if self._queue_task and not self._queue_task.done():
            try:
                await asyncio.wait_for(
                    asyncio.shield(self._queue_task), timeout=_SHUTDOWN_TIMEOUT_S
                )
            except asyncio.TimeoutError:
                self._queue_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._queue_task
        ijt_log.info("ResultEventHandler closed.")
