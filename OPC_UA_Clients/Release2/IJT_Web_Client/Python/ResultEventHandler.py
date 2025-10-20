import json
import asyncio
import websockets
import pytz
import traceback
from datetime import datetime
from typing import Optional, Dict
from Python.Serialize import serializeValue
from Python.IJTLogger import ijt_log
from Python.Utils import log_result_event_details


class Short:
    def __init__(self, eventType, result, message, id):
        self.EventType = eventType
        self.Result = result
        self.Message = message
        self.EventId = id

    def to_dict(self) -> Dict:
        return {
            "EventType": self.EventType,
            "Result": self.Result,
            "Message": self.Message,
            "EventId": self.EventId,
        }


class ResultEventHandler:
    def __init__(self, websocket, server_url, client):
        self.websocket = websocket
        self.server_url = server_url
        self.client = client
        self.queue = asyncio.Queue()
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        self.loop.create_task(self.handleQueue())
        ijt_log.info("ResultEventHandler initialized.")

    async def process_event(self, tmp):
        try:
            arg = str(serializeValue(tmp))
            returnValue = {
                "command": "event",
                "endpoint": self.server_url,
                "data": arg,
            }
            await self.queue.put(json.dumps(returnValue))
        except Exception as e:
            ijt_log.error("Exception: " + str(e))

    async def event_notification(self, event):
        try:
            client_received_time = datetime.now(pytz.utc)
            event_id = await log_result_event_details(
                event, self.client, self.server_url, client_received_time
            )
            filtered_event = Short(
                event.EventType, event.Result, event.Message, event_id
            )
            asyncio.run_coroutine_threadsafe(
                self.process_event(filtered_event), self.loop
            )
        except Exception as e:
            ijt_log.error(f"Error handling event notification: {e}")
            ijt_log.error(traceback.format_exc())

    async def handleQueue(self):
        while True:
            item = await self.queue.get()
            if item is None:
                break
            try:
                await self.websocket.send(item)
            except websockets.exceptions.ConnectionClosedOK:
                ijt_log.info("WebSocket connection closed normally.")
                break
            except Exception as e:
                ijt_log.error(f"Error sending message: {e}")

    async def shutdown(self):
        await self.queue.put(None)

    async def close(self):
        await self.shutdown()
        ijt_log.info("ResultEventHandler closed.")
