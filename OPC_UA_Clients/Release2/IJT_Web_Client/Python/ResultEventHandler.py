import json
import asyncio
import websockets
import pytz
from datetime import datetime
from Python.Serialize import serializeValue  # Ensure this module is available
from Python.IJTLogger import ijt_logger


class Short:
    """
    Support class to contain just the part of a result event that should be transferred to the webpage
    """

    def __init__(self, eventType, result, message, id):
        self.EventType = eventType
        self.Result = result
        self.Message = message
        self.EventId = id

    def to_dict(self):
        return {
            "EventType": self.EventType,
            "Result": self.Result,
            "Message": self.Message,
            "EventId": self.EventId,
        }


class ResultEventHandler:
    """
    Subscription Handler. To receive events from server for a subscription.
    data_change and event methods are called directly from receiving thread.
    Do not do expensive, slow or network operation there.
    threaded_websocket handles that via wrap_async_func
    """

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
        # Get server time from the server using the CurrentTime node
        server_time = await self.read_server_time(self.server_url)
        # Get current client time in local timezone
        client_time = datetime.now()
        local_timezone = pytz.timezone("Europe/Stockholm")
        localized_client_time = local_timezone.localize(client_time)
        utc_client_time = localized_client_time.astimezone(pytz.utc)

        # Ensure event_time is timezone-aware (assumed UTC)
        event_time = event.Time
        if event_time.tzinfo is None:
            event_time = pytz.utc.localize(event_time)

        # Convert all times to local timezone
        local_event_time = event_time.astimezone(local_timezone)
        local_client_time = utc_client_time.astimezone(local_timezone)
        formatted_event_time = local_event_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        formatted_client_time = local_client_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # Format and calculate server time if available
        if server_time:
            local_server_time = server_time.astimezone(local_timezone)
            formatted_server_time = local_server_time.strftime("%Y-%m-%d %H:%M:%S.%f")[
                :-3
            ]
            server_gap_ms = (utc_client_time - server_time).total_seconds() * 1000
        else:
            formatted_server_time = "Unavailable"
            server_gap_ms = None

        # Calculate event gap
        event_gap_ms = (utc_client_time - event_time).total_seconds() * 1000
        event_id = event.EventId.decode("utf-8", errors="replace")
        event_relation = "slower" if event_gap_ms < 0 else "faster"

        # Log the details
        ijt_logger.info("-----------------------------------------------")
        ijt_logger.info(f"RESULT EVENT RECEIVED + [{event_id}]: {event.Message.Text}")
        ijt_logger.info(
            f"Server Time                   : {formatted_server_time} (Local Time)"
        )
        ijt_logger.info(
            f"Client Time                   : {formatted_client_time} (Local Time)"
        )
        ijt_logger.info(
            f"Event Generated Time          : {formatted_event_time} (Local Time)"
        )

        if server_gap_ms is not None:
            server_relation = "slower" if server_gap_ms < 0 else "faster"
            ijt_logger.info(
                f"Gap: Client - Server: {abs(server_gap_ms):.3f} ms (Client is {server_relation})"
            )
        else:
            ijt_logger.info("Gap: Client - Server: Unavailable")
        ijt_logger.info(
            f"Gap: Result Received - Result Sent : {abs(event_gap_ms):.3f} ms (Client is {event_relation})"
        )
        ijt_logger.info("-----------------------------------------------")
        filtered_event = Short(event.EventType, event.Result, event.Message, event_id)
        asyncio.run_coroutine_threadsafe(self.process_event(filtered_event), self.loop)

    @staticmethod
    async def read_server_time(endpoint):
        from asyncua import Client, ua

        try:
            async with Client(endpoint) as client:
                node = client.get_node(ua.NodeId(2258, 0))  # ServerStatus.CurrentTime
                value = await node.read_value()
                ijt_logger.info(f"Server Current Time (UTC): {value}")
                return value
        except Exception as e:
            ijt_logger.warning(f"Failed to read server time: {e}")
            return None
