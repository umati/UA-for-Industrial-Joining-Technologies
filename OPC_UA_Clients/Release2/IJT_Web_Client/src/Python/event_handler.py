import asyncio
import json
import traceback

import websockets

from Python.ijt_logger import ijt_log
from Python.serialize_data import serializeFullEvent
from Python.utils import log_joining_system_event, localizedtext_to_str, nodeid_to_str


class Short:
    def __init__(self, event):
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
    def __init__(self, websocket, server_url, client):
        self.websocket = websocket
        self.server_url = server_url
        self.client = client
        self.queue: asyncio.Queue = asyncio.Queue()
        self.closed = False
        self._queue_task = asyncio.create_task(self.handleQueue())

    async def process_event(self, short_event: Short):
        if self.closed:
            return
        try:
            await self.queue.put(short_event)
        except Exception as exc:
            ijt_log.error(f"Error handling process_event: {exc}")
            ijt_log.error(traceback.format_exc())

    async def event_notification(self, event):
        if self.closed:
            return
        try:
            short_event = Short(event)
            await log_joining_system_event(short_event)
            await self.process_event(short_event)
        except Exception as exc:
            ijt_log.error(f"Error handling event notification: {exc}")
            ijt_log.error(traceback.format_exc())

    async def handleQueue(self):
        while True:
            item = await self.queue.get()
            if item is None:
                self.queue.task_done()
                break
            try:
                serialized_event = serializeFullEvent(item)
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
                    ijt_log.debug(f"WebSocket close failed during error recovery: {close_exc}")
                break
            finally:
                self.queue.task_done()

    async def shutdown(self):
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
                await asyncio.wait_for(asyncio.shield(self._queue_task), timeout=5.0)
            except asyncio.TimeoutError:
                self._queue_task.cancel()
                try:
                    await self._queue_task
                except asyncio.CancelledError:
                    pass
        ijt_log.info("EventHandler closed.")
