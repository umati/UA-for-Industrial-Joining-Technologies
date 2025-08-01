import json
import asyncio
import websockets
import pytz
from datetime import datetime
from typing import Optional, Dict
from Python.Serialize import serializeValue  # Ensure this module is available
from Python.IJTLogger import ijt_logger


def format_local_time(dt: datetime, timezone: str = "Europe/Stockholm") -> str:
    local_tz = pytz.timezone(timezone)
    return dt.astimezone(local_tz).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


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
    def __init__(self, websocket, server_url):
        self.websocket = websocket
        self.server_url = server_url
        self.queue = asyncio.Queue()
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        self.loop.create_task(self.handleQueue())

    async def handleQueue(self):
        while True:
            item = await self.queue.get()
            if item is None:
                break
            try:
                await self.websocket.send(item)
            except websockets.exceptions.ConnectionClosedOK:
                ijt_logger.info("WebSocket connection closed normally.")
                break
            except Exception as e:
                ijt_logger.error(f"Error sending message: {e}")

    async def shutdown(self):
        await self.queue.put(None)

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
            ijt_logger.error("Exception: " + str(e))

    async def event_notification(self, event):
        client_received_time = datetime.utcnow().replace(tzinfo=pytz.utc)
        event_id = await ResultEventHandler.log_event_details(
            event, self.server_url, client_received_time
        )
        filtered_event = Short(event.EventType, event.Result, event.Message, event_id)
        asyncio.run_coroutine_threadsafe(self.process_event(filtered_event), self.loop)

    @staticmethod
    async def read_server_time(endpoint: str) -> Optional[datetime]:
        from asyncua import Client, ua

        try:
            async with Client(endpoint) as client:
                node = client.get_node(ua.NodeId(2258, 0))  # ServerStatus.CurrentTime
                value = await node.read_value()
                return value
        except Exception as e:
            ijt_logger.warning(f"Failed to read server time: {e}")
            return None

    @staticmethod
    async def log_event_details(
        event, server_url: str, client_received_time: datetime
    ) -> str:
        server_time = await ResultEventHandler.read_server_time(server_url)
        event_time = event.Time
        event_id = event.EventId.decode("utf-8", errors="replace")

        timing = ResultEventHandler.calculate_event_latency(
            event_time, client_received_time
        )

        formatted_event_time = format_local_time(timing["utc_event_time"])
        formatted_client_time = format_local_time(timing["utc_client_time"])
        formatted_server_time = (
            format_local_time(server_time) if server_time else "Unavailable"
        )

        ijt_logger.info("-" * 80)
        ijt_logger.info(f"RESULT EVENT RECEIVED               : {event.Message.Text}")
        ijt_logger.info(
            f"Client Time                         : {formatted_client_time}"
        )
        ijt_logger.info(f"Event Generated Time                : {formatted_event_time}")
        ijt_logger.info(
            f"Latency (Event → Client)            : {abs(timing['event_gap_ms']):.3f} ms"
        )

        if server_time:
            server_gap_ms = (
                timing["utc_client_time"] - server_time
            ).total_seconds() * 1000
            drift_relation = "slower" if server_gap_ms < 0 else "faster"
            ijt_logger.info(
                f"Clock Drift (Client - Server)       : {abs(server_gap_ms):.3f} ms (Client is {drift_relation})"
            )
            ijt_logger.info(
                f"Server Time                         : {formatted_server_time}"
            )
        else:
            ijt_logger.info("Server Time                         : Unavailable")

        ijt_logger.info("-" * 80)
        return event_id

    @staticmethod
    def calculate_event_latency(event_time: datetime, client_time: datetime) -> Dict:
        if event_time.tzinfo is None:
            event_time = pytz.utc.localize(event_time)
        event_gap_ms = (client_time - event_time).total_seconds() * 1000
        return {
            "utc_client_time": client_time,
            "utc_event_time": event_time,
            "event_gap_ms": event_gap_ms,
        }
