import asyncio
import json
import traceback
from datetime import datetime

import pytz
import websockets

from Python.ijt_logger import ijt_log
from Python.serialize_data import serializeFullEvent
from Python.utils import log_result_event_details


class Short:
    def __init__(self, eventType, result, message, event_id):
        self.EventType = eventType
        self.Result = result
        self.Message = message
        self.EventId = event_id


class ResultEventHandler:
    def __init__(self, websocket, server_url, client):
        self.websocket = websocket
        self.server_url = server_url
        self.client = client
        self.queue: asyncio.Queue = asyncio.Queue()
        self.closed = False
        self._queue_task = asyncio.create_task(self.handleQueue())
        ijt_log.info("ResultEventHandler initialized.")

    async def process_event(self, event_obj: Short):
        if self.closed:
            return
        try:
            arg = serializeFullEvent(event_obj)
            return_value = {
                "command": "event",
                "endpoint": self.server_url,
                "data": arg,
            }
            await self.queue.put(json.dumps(return_value))
        except Exception as exc:
            ijt_log.error(f"Result event serialization failed: {exc}")

    async def event_notification(self, event):
        if self.closed:
            return
        try:
            client_received_time = datetime.now(pytz.utc)
            event_id = await log_result_event_details(
                event, self.client, self.server_url, client_received_time
            )
            filtered_event = Short(
                event.EventType,
                event.Result,
                event.Message,
                event_id,
            )
            await self.process_event(filtered_event)
        except Exception as exc:
            ijt_log.error(f"Error handling result event notification: {exc}")
            ijt_log.error(traceback.format_exc())

    async def handleQueue(self):
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
                break
            finally:
                self.queue.task_done()

    async def shutdown(self):
        if not self.closed:
            self.closed = True
            await self.queue.put(None)

    async def close(self):
        await self.shutdown()
        if self._queue_task:
            await self._queue_task
        ijt_log.info("ResultEventHandler closed.")
