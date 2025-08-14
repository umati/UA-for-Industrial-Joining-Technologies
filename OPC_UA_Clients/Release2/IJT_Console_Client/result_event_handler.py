import asyncio
import pytz
from datetime import datetime
from typing import Dict
from ijt_logger import ijt_log
from utils import log_event_details


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
    def __init__(self, server_url, client):
        self.server_url = server_url
        self.client = client
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        ijt_log.info("ResultEventHandler initialized.")

    async def process_event(self, event: Short):
        ijt_log.info(
            f"Event processed: Message={getattr(event.Message, 'Text', 'N/A')}"
        )

    async def event_notification(self, event):
        client_received_time = datetime.utcnow().replace(tzinfo=pytz.utc)
        try:
            event_id = await log_event_details(
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
