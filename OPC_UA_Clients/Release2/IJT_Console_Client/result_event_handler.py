import asyncio
import traceback
import pytz
from datetime import datetime
from typing import Dict
from dataclasses import dataclass

from ijt_logger import ijt_log
from utils import log_result_to_file, log_result_event_details


@dataclass
class ShortResultEvent:
    EventType: str
    Result: dict
    Message: str
    EventId: str

    def to_dict(self) -> Dict:
        return {
            "EventType": self.EventType,
            "Result": self.Result,
            "Message": self.Message,
            "EventId": self.EventId,
        }


class ResultEventHandler:
    """
    Async handler for OPC UA ResultReadyEvent notifications.

    Uses asyncio.create_task() on the running event loop — the same pattern as
    the IJT Web Client — instead of asyncio.run_coroutine_threadsafe().
    Must be instantiated from within an async context (e.g. inside subscribe_to_events).
    """

    def __init__(self, server_url):
        self.server_url = server_url
        ijt_log.info("ResultEventHandler initialized.")

    async def process_event(self, event: ShortResultEvent):
        try:
            ijt_log.info(f"Processing Result Event: {event.Message}")
            await log_result_to_file(event)
        except Exception as e:
            ijt_log.error("Exception: " + str(e))
            ijt_log.error(traceback.format_exc())

    async def event_notification(self, event):
        try:
            client_received_time = datetime.now(pytz.utc)
            event_id = await log_result_event_details(
                event, self.server_url, client_received_time
            )
            filtered_event = ShortResultEvent(
                EventType=str(event.EventType),
                Result=event.Result,
                Message=getattr(event.Message, "Text", "N/A"),
                EventId=event_id,
            )
            asyncio.create_task(self.process_event(filtered_event))
        except Exception as e:
            ijt_log.error(f"Error handling result event notification: {e}")
            ijt_log.error(traceback.format_exc())
