import asyncio
import websockets
import json
import traceback
from threading import Thread
from asyncua import ua
from Python.ijt_logger import ijt_log
from Python.utils import log_joining_system_event, nodeid_to_str, localizedtext_to_str
from Python.serialize_data import serializeFullEvent


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
        self.queue = asyncio.Queue()
        self.loop = asyncio.new_event_loop()

        def start_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        thread = Thread(target=start_loop, daemon=True)
        thread.start()
        asyncio.run_coroutine_threadsafe(self.handleQueue(), self.loop)

    async def process_event(self, short_event: Short):
        try:
            ijt_log.info("EventHandler: Processing event")
            await self.queue.put(short_event)
        except Exception as e:
            ijt_log.error(f"Error handling process_event: {e}")
            ijt_log.error(traceback.format_exc())

    async def event_notification(self, event):
        try:
            ijt_log.info("EventHandler: Event notification")
            short_event = Short(event)
            await log_joining_system_event(short_event)
            asyncio.run_coroutine_threadsafe(self.process_event(short_event), self.loop)
        except Exception as e:
            ijt_log.error(f"Error handling event notification: {e}")
            ijt_log.error(traceback.format_exc())

    async def handleQueue(self):
        while True:
            item = await self.queue.get()
            if item is None:
                break
            try:
                serialized_event = serializeFullEvent(item)
                returnValue = {
                    "command": "event",
                    "endpoint": self.server_url,
                    "data": serialized_event,
                }

                json_payload = json.dumps(returnValue)
                await self.websocket.send(json_payload)
            except websockets.exceptions.ConnectionClosedOK:
                ijt_log.info("WebSocket connection closed normally.")
                break
            except Exception as e:
                ijt_log.error(f"Error sending message: {e}")
                ijt_log.error(traceback.format_exc())
                await self.websocket.close()
                break
            finally:
                self.queue.task_done()

    async def shutdown(self):
        await self.queue.put(None)

    async def close(self):
        await self.shutdown()
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        ijt_log.info("EventHandler closed.")
