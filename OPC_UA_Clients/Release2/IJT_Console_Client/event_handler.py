import asyncio
import json
import traceback
from dataclasses import dataclass
from typing import List, Any

from asyncua import ua
from ijt_logger import ijt_log
from utils import log_joining_system_event, nodeid_to_str, localizedtext_to_str
from serialize_data import serialize_full_event


@dataclass
class ShortJoiningEvent:
    EventType: ua.NodeId
    EventId: str
    Message: ua.LocalizedText
    SourceName: str
    SourceNode: str
    Severity: int
    Time: Any
    ReceiveTime: Any
    LocalTime: ua.TimeZoneDataType
    ConditionClassId: ua.NodeId
    ConditionClassName: ua.LocalizedText
    ConditionSubClassId: List[ua.NodeId]
    ConditionSubClassName: List[ua.LocalizedText]
    EventCode: Any
    EventText: str
    JoiningTechnology: str
    AssociatedEntities: List[Any]
    ReportedValues: List[Any]


class EventHandler:
    """
    Async event handler for OPC UA JoiningSystemEvent notifications.

    Uses a single asyncio queue drained by a task on the running event loop —
    the same pattern as the IJT Web Client — instead of a daemon-thread loop.
    Must be instantiated from within an async context (e.g. inside subscribe_to_events)
    so that asyncio.create_task() is available.
    """

    def __init__(self, websocket, server_url, client):
        self.websocket = websocket
        self.server_url = server_url
        self.client = client
        self.queue: asyncio.Queue = asyncio.Queue()
        self.closed = False
        self._queue_task = asyncio.create_task(self.handle_queue())

    async def event_notification(self, event):
        if self.closed:
            return
        try:
            ijt_log.info("EventHandler: Event notification")

            short_event = ShortJoiningEvent(
                EventType=event.EventType,
                EventId=(
                    event.EventId.decode("utf-8", errors="replace")
                    if isinstance(event.EventId, bytes)
                    else str(event.EventId)
                ),
                Message=getattr(event, "Message", None),
                SourceName=str(getattr(event, "SourceName", "")),
                SourceNode=nodeid_to_str(getattr(event, "SourceNode", None)),
                Severity=int(getattr(event, "Severity", 0)),
                Time=getattr(event, "Time", None),
                ReceiveTime=getattr(event, "ReceiveTime", None),
                LocalTime=getattr(event, "LocalTime", None),
                ConditionClassId=getattr(event, "ConditionClassId", None),
                ConditionClassName=getattr(event, "ConditionClassName", None),
                ConditionSubClassId=getattr(event, "ConditionSubClassId", []),
                ConditionSubClassName=getattr(event, "ConditionSubClassName", []),
                EventCode=getattr(event, "JoiningSystemEventContent/EventCode", None),
                EventText=localizedtext_to_str(
                    getattr(event, "JoiningSystemEventContent/EventText", None)
                ),
                JoiningTechnology=localizedtext_to_str(
                    getattr(event, "JoiningSystemEventContent/JoiningTechnology", None)
                ),
                AssociatedEntities=getattr(
                    event, "JoiningSystemEventContent/AssociatedEntities", []
                ),
                ReportedValues=getattr(
                    event, "JoiningSystemEventContent/ReportedValues", []
                ),
            )

            await log_joining_system_event(short_event)
            await self.queue.put(short_event)

        except Exception as e:
            ijt_log.error(f"Error handling event notification: {e}")
            ijt_log.error(traceback.format_exc())

    async def handle_queue(self):
        try:
            while True:
                item = await self.queue.get()
                if item is None:
                    self.queue.task_done()
                    break
                try:
                    serialized_event = serialize_full_event(item)
                    json_payload = json.dumps(serialized_event, ensure_ascii=False)

                    if self.websocket:
                        await self.websocket.send(json_payload)
                    else:
                        ijt_log.debug(
                            "WebSocket is None, skipping send. Event processed locally."
                        )

                except Exception as e:
                    ijt_log.error(f"Error sending message: {e}")
                    ijt_log.error(traceback.format_exc())
                    if self.websocket:
                        try:
                            await self.websocket.close()
                        except Exception as close_exc:
                            ijt_log.debug(f"WebSocket close failed during error recovery: {close_exc}")
                    break
                finally:
                    self.queue.task_done()
        except asyncio.CancelledError:
            pass  # Clean cancellation — no noise on Ctrl+C

    async def shutdown(self):
        if not self.closed:
            self.closed = True
            await self.queue.put(None)

    async def close(self):
        """Gracefully shut down and await queue-task completion.

        Safe to call even if ``closed`` was set manually — the task is
        cancelled with a short timeout instead of blocking forever.
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
