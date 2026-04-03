"""WebSocket event handler for OPC UA JoiningSystemEventType notifications.

Incoming OPC UA subscription events are briefly summarised into a
:class:`Short` snapshot, logged, and forwarded to the browser over the shared
WebSocket by the :class:`EventHandler` queue worker.
"""

import asyncio
import contextlib
import json
import traceback
from typing import Any

import websockets

from python.ijt_logger import ijt_log
from python.serialize_data import serialize_full_event
from python.utils import localizedtext_to_str, log_joining_system_event, nodeid_to_str

_SHUTDOWN_TIMEOUT_S = 5.0


class Short:
    """Lightweight snapshot of a JoiningSystemEventType notification.

    Extracts and normalises a small subset of fields from the raw asyncua
    event object so that the rest of the pipeline can work with plain Python
    types rather than asyncua-specific objects.

    Attribute names use OPC UA PascalCase convention (e.g. ``EventType``,
    ``Message``) to match the field names on asyncua event objects directly,
    avoiding an extra mapping layer.
    """

    def __init__(self, event: Any) -> None:
        self.EventType = event.EventType
        self.EventId = (
            event.EventId.decode("utf-8", errors="replace")
            if isinstance(event.EventId, bytes)
            else str(event.EventId)
        )
        self.Message = getattr(event, "Message", None)
        self.SourceName = str(getattr(event, "SourceName", None))
        self.SourceNode = nodeid_to_str(getattr(event, "SourceNode", None))
        self.Severity = str(getattr(event, "Severity", None))
        self.Time = getattr(event, "Time", None)
        self.ReceiveTime = getattr(event, "ReceiveTime", None)
        self.LocalTime = getattr(event, "LocalTime", None)

        self.ConditionClassId = nodeid_to_str(getattr(event, "ConditionClassId", None))
        self.ConditionClassName = localizedtext_to_str(
            getattr(event, "ConditionClassName", None)
        )
        self.ConditionSubClassId = [
            nodeid_to_str(nid) for nid in getattr(event, "ConditionSubClassId", [])
        ]
        self.ConditionSubClassName = [
            localizedtext_to_str(lt)
            for lt in getattr(event, "ConditionSubClassName", [])
        ]

        self.EventCode = getattr(event, "JoiningSystemEventContent/EventCode", None)
        self.EventText = localizedtext_to_str(
            getattr(event, "JoiningSystemEventContent/EventText", None)
        )
        self.JoiningTechnology = localizedtext_to_str(
            getattr(event, "JoiningSystemEventContent/JoiningTechnology", None)
        )
        self.AssociatedEntities = getattr(
            event, "JoiningSystemEventContent/AssociatedEntities", []
        )

        self.ReportedValues = getattr(
            event, "JoiningSystemEventContent/ReportedValues", []
        )


class EventHandler:
    """Asyncio-based handler that queues JoiningSystemEvent notifications for WebSocket delivery.

    Instances are created once per OPC UA subscription and remain alive until
    :meth:`close` is called (typically during connection teardown).
    """

    def __init__(
        self, websocket: Any, server_url: str, client: Any | None = None
    ) -> None:
        """Initialise the handler and start the background queue-worker task.

        Args:
            websocket: Active WebSocket connection used to push events to the
                browser.
            server_url: OPC UA server URL — included in every event message so
                the front-end can route it to the right connection view.
            client: Optional asyncua :class:`~asyncua.Client` instance.
                Stored for potential future use; defaults to ``None``.
        """
        self.websocket = websocket
        self.server_url = server_url
        self.client = client
        self.queue: asyncio.Queue = asyncio.Queue()
        self.closed = False
        self._queue_task = asyncio.create_task(self.handle_queue())

    async def process_event(self, short_event: Short):
        """Coroutine. Enqueue a pre-processed event snapshot for WebSocket delivery.

        Args:
            short_event: A :class:`Short` snapshot ready for serialization.
        """
        if self.closed:
            return
        try:
            await self.queue.put(short_event)
        except Exception as exc:
            ijt_log.error(f"Error handling process_event: {exc}")
            ijt_log.error(traceback.format_exc())

    async def event_notification(self, event: Any) -> None:
        """Coroutine. asyncua subscription callback for JoiningSystemEventType events.

        Wraps the raw event in a :class:`Short` snapshot, logs its details via
        :func:`~Python.utils.log_joining_system_event`, and forwards it to the
        queue via :meth:`process_event`.

        Args:
            event: Raw asyncua event object delivered by the subscription.
        """
        if self.closed:
            return
        try:
            short_event = Short(event)
            log_joining_system_event(short_event)
            await self.process_event(short_event)
        except Exception as exc:
            ijt_log.error(f"Error handling event notification: {exc}")
            ijt_log.error(traceback.format_exc())

    async def handle_queue(self):
        """Coroutine. Background worker that drains the event queue and sends messages.

        Runs until a sentinel ``None`` item is dequeued (placed by
        :meth:`shutdown`).  Breaks out of the loop and closes the WebSocket on
        unrecoverable send errors.
        """
        while True:
            item = await self.queue.get()
            if item is None:
                self.queue.task_done()
                break
            try:
                serialized_event = serialize_full_event(item)
                return_value = {
                    "command": "event",
                    "endpoint": self.server_url,
                    "data": serialized_event,
                }
                await self.websocket.send(json.dumps(return_value))
            except websockets.exceptions.ConnectionClosedOK:
                ijt_log.info("WebSocket connection closed normally.")
                break
            except Exception as exc:
                ijt_log.error(f"Error sending message: {exc}")
                ijt_log.error(traceback.format_exc())
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

        Safe to call even if ``closed`` was set manually (e.g. in tests) — the
        task will be cancelled with a short timeout instead of waiting forever.
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
        ijt_log.info("EventHandler closed.")
