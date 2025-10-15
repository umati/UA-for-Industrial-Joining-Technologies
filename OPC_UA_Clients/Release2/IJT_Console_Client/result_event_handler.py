import re
import asyncio
import traceback
import pytz
import aiofiles
from sys import exception
from datetime import datetime
from typing import Dict
from pathlib import Path
from ijt_logger import ijt_log
from utils import log_event_details
from serialize import serializeFullEvent
from client_config import ENABLE_RESULT_FILE_LOGGING


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
        # Below logic writes the Result content to a file in result_logs/latest_result.json.
        # This logic can be used to parse the Result and use it accordingly.
        if ENABLE_RESULT_FILE_LOGGING:
            try:
                await self.log_result_to_file(event)
            except Exception as e:
                ijt_log.error(f"failed to log result to file: {e}")

    async def log_result_to_file(self, event):
        try:
            json_str = serializeFullEvent(event.Result)

            log_dir = Path("result_logs")
            log_dir.mkdir(exist_ok=True)

            safe_message = re.sub(
                r"[^\w\-_\. ]", "_", str(event.Message.Text).replace(":", "_")
            )
            temp_file = log_dir / f"{safe_message}.tmp"
            final_file = log_dir / f"{safe_message}.json"

            async with aiofiles.open(temp_file, mode="w", encoding="utf-8") as f:
                await f.write(json_str)

            temp_file.rename(final_file)
            ijt_log.info(f"Event Result logged to {final_file}")
        except Exception as e:
            ijt_log.error(f"Error during serialization: {e}")
            ijt_log.error(traceback.format_exc())

    async def event_notification(self, event):
        client_received_time = datetime.now(pytz.utc)
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
            ijt_log.error(traceback.format_exc())
