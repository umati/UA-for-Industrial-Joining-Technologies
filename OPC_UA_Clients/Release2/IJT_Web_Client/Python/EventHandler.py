import asyncio
import websockets
import pytz
from datetime import datetime
from threading import Thread
from asyncua import ua
from Python.IJTLogger import ijt_log
from Python.Utils import log_joining_system_event


class Short:
    def __init__(self, event):
        self.EventType = event.EventType
        self.EventId = (
            event.EventId.decode("utf-8", errors="replace")
            if isinstance(event.EventId, bytes)
            else str(event.EventId)
        )
        self.Message = str(event.Message)
        self.SourceName = str(getattr(event, "SourceName", None))
        self.SourceNode = self.nodeid_to_str(getattr(event, "SourceNode", None))
        self.Severity = str(getattr(event, "Severity", None))
        self.Time = str(getattr(event, "Time", None))
        self.ReceiveTime = str(getattr(event, "ReceiveTime", None))
        self.LocalTime = str(getattr(event, "LocalTime", None))

        self.ConditionClassId = self.nodeid_to_str(
            getattr(event, "ConditionClassId", None)
        )
        self.ConditionClassName = self.localizedtext_to_str(
            getattr(event, "ConditionClassName", None)
        )
        self.ConditionSubClassId = [
            self.nodeid_to_str(nid) for nid in getattr(event, "ConditionSubClassId", [])
        ]
        self.ConditionSubClassName = [
            self.localizedtext_to_str(lt)
            for lt in getattr(event, "ConditionSubClassName", [])
        ]

        self.EventCode = getattr(event, "JoiningSystemEventContent/EventCode", None)
        self.EventText = self.localizedtext_to_str(
            getattr(event, "JoiningSystemEventContent/EventText", None)
        )
        self.JoiningTechnology = self.localizedtext_to_str(
            getattr(event, "JoiningSystemEventContent/JoiningTechnology", None)
        )
        self.AssociatedEntities = getattr(
            event, "JoiningSystemEventContent/AssociatedEntities", []
        )

        self.ReportedValues = getattr(
            event, "JoiningSystemEventContent/ReportedValues", []
        )

    def nodeid_to_str(self, nodeid):
        try:
            if isinstance(nodeid, ua.NodeId):
                return f"ns={nodeid.NamespaceIndex};{nodeid.NodeIdType.name.lower()}={nodeid.Identifier}"
        except Exception:
            pass
        return str(nodeid)

    def localizedtext_to_str(self, lt):
        try:
            if isinstance(lt, ua.LocalizedText):
                return lt.Text
        except Exception:
            pass
        return str(lt)


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

    async def handleQueue(self):
        ijt_log.info("EventHandler: Starting handleQueue")
        while True:
            ijt_log.info("EventHandler: Waiting for queue item...")
            item = await self.queue.get()
            if item is None:
                break
            ijt_log.info(f"EventHandler: Got item from queue: {item}")
            try:
                ijt_log.info(f"EventHandler: Sending item over WebSocket: {item}")
                await self.websocket.send(item)
            except websockets.exceptions.ConnectionClosedOK:
                ijt_log.info("WebSocket connection closed normally.")
                break
            except Exception as e:
                ijt_log.error(f"Error sending message: {e}")

    async def shutdown(self):
        await self.queue.put(None)

    async def process_event(self, short_event: Short):
        ijt_log.info("EventHandler: Processing event")
        try:
            summary = f"[{short_event.EventId}] {short_event.Message}"
            await self.queue.put(summary)
        except Exception as e:
            ijt_log.error("Exception: " + str(e))

    async def event_notification(self, event):
        ijt_log.info("EventHandler: Event notification")
        short_event = Short(event)
        log_joining_system_event(short_event)
        asyncio.run_coroutine_threadsafe(self.process_event(short_event), self.loop)

    async def close(self):
        await self.shutdown()
        ijt_log.info("EventHandler closed.")
