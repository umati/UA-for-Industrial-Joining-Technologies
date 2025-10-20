import pytz
import traceback
import aiofiles
import re
from datetime import datetime
from typing import Optional, Dict
from asyncua import Client, ua
from pathlib import Path
from ijt_logger import ijt_log
from serialize import serializeFullEvent
from client_config import ENABLE_RESULT_FILE_LOGGING


def format_local_time(dt: datetime, timezone: str = "Europe/Stockholm") -> str:
    local_tz = pytz.timezone(timezone)
    return dt.astimezone(local_tz).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


async def read_server_time(client: Client) -> Optional[datetime]:
    try:
        node = client.get_node(ua.NodeId(2258, 0))  # ServerStatus.CurrentTime
        value = await node.read_value()
        return value
    except Exception as e:
        ijt_log.warning(f"{'Server Time Read Failed':<40} : {e}")
        return None


async def log_result_event_details(
    event, client: Client, server_url: str, client_received_time: datetime
) -> str:
    ijt_log.debug(f"Reading 'ServerStatus.CurrentTime' property.")
    server_time = await read_server_time(client)

    event_time = event.Time
    event_id = event.EventId.decode("utf-8", errors="replace")

    start_time = getattr(
        getattr(getattr(event.Result, "ResultMetaData", None), "ProcessingTimes", None),
        "StartTime",
        None,
    )
    end_time = getattr(
        getattr(getattr(event.Result, "ResultMetaData", None), "ProcessingTimes", None),
        "EndTime",
        None,
    )

    creation_time = getattr(
        getattr(event.Result, "ResultMetaData", None), "CreationTime", None
    )

    if end_time and end_time.tzinfo is None:
        end_time = pytz.utc.localize(end_time)

    latency_ms = (
        (client_received_time - end_time).total_seconds() * 1000 if end_time else None
    )

    formatted_event_time = (
        format_local_time(event_time) if event_time else "Unavailable"
    )
    formatted_client_time = format_local_time(client_received_time)
    formatted_server_time = (
        format_local_time(server_time) if server_time else "Unavailable"
    )
    formatted_start_time = (
        format_local_time(start_time) if start_time else "Unavailable"
    )
    formatted_end_time = format_local_time(end_time) if end_time else "Unavailable"
    formatted_creation_time = (
        format_local_time(creation_time) if creation_time else "Unavailable"
    )

    message = getattr(event.Message, "Text", "Unavailable")

    label_width = 40
    ijt_log.info("-" * 80)
    ijt_log.info(f"{'RESULT EVENT RECEIVED':<{label_width}} : {message}")
    ijt_log.info(
        f"{'1. StartTime of Tightening':<{label_width}} : {formatted_start_time}"
    )
    ijt_log.info(f"{'2. EndTime of Tightening':<{label_width}} : {formatted_end_time}")
    ijt_log.info(
        f"{'3. Result Creation Time':<{label_width}} : {formatted_creation_time}"
    )
    ijt_log.info(
        f"{'4. Result Event Generated Time':<{label_width}} : {formatted_event_time}"
    )
    ijt_log.info(f"{'5. Client Time':<{label_width}} : {formatted_client_time}")
    ijt_log.info(f"{'6. Server Time':<{label_width}} : {formatted_server_time}")

    if latency_ms is not None:
        ijt_log.info(
            f"{'*** Turn around Time (EndTime → Client)':<{label_width}} : {abs(latency_ms):.3f} ms"
        )
    else:
        ijt_log.info(
            f"{'*** Turn around Time (EndTime → Client)':<{label_width}} : Unavailable"
        )
    ijt_log.info("-" * 80)
    return event_id


async def log_joining_system_event(event):
    label_width = 40
    ijt_log.info("-" * 80)
    message_text = getattr(event.Message, "Text", "Unavailable")
    ijt_log.info(f"{'JOINING SYSTEM EVENT':<40} : {message_text}")
    ijt_log.info("-" * 80)

    def log_field(label, value):
        ijt_log.info(f"{label:<{label_width}} : {value}")

    log_field("EventType", event.EventType)
    log_field("EventId", event.EventId)
    log_field("Message", event.Message)
    log_field("SourceName", event.SourceName)
    log_field("SourceNode", event.SourceNode)
    log_field("Severity", event.Severity)
    log_field("Time", format_local_time(event.Time) if event.Time else "Unavailable")
    log_field(
        "ReceiveTime",
        format_local_time(event.ReceiveTime) if event.ReceiveTime else "Unavailable",
    )
    if event.LocalTime:
        offset = getattr(event.LocalTime, "Offset", "Unavailable")
        dst = getattr(event.LocalTime, "DaylightSavingInOffset", "Unavailable")
        log_field("LocalTime.Offset", offset)
        log_field("LocalTime.DaylightSavingInOffset", dst)
    else:
        log_field("LocalTime", "Unavailable")
    log_field("ConditionClassId", event.ConditionClassId)
    log_field("ConditionClassName", event.ConditionClassName)
    log_field("ConditionSubClassId", event.ConditionSubClassId)
    log_field("ConditionSubClassName", event.ConditionSubClassName)
    log_field("EventCode", event.EventCode)
    log_field("EventText", event.EventText)
    log_field("JoiningTechnology", event.JoiningTechnology)

    # AssociatedEntities
    if isinstance(event.AssociatedEntities, list) and event.AssociatedEntities:
        ijt_log.info(f"{'AssociatedEntities':<{label_width}} :")
        for entity in event.AssociatedEntities:
            try:
                ijt_log.info(
                    f"{'  Entity Name':<{label_width}} : {getattr(entity, 'Name', '')}"
                )
                ijt_log.info(
                    f"{'  Description':<{label_width}} : {getattr(entity, 'Description', '')}"
                )
                ijt_log.info(
                    f"{'  EntityId':<{label_width}} : {getattr(entity, 'EntityId', '')}"
                )
                ijt_log.info(
                    f"{'  EntityType':<{label_width}} : {getattr(entity, 'EntityType', '')}"
                )
                ijt_log.info(
                    f"{'  IsExternal':<{label_width}} : {getattr(entity, 'IsExternal', '')}"
                )
            except Exception as e:
                ijt_log.warning(f"{'Error logging entity':<{label_width}} : {e}")
    else:
        log_field("AssociatedEntities", event.AssociatedEntities)

    # ReportedValues
    if isinstance(event.ReportedValues, list) and event.ReportedValues:
        ijt_log.info(f"{'ReportedValues':<{label_width}} :")
        for rv in event.ReportedValues:
            try:
                eu = getattr(rv, "EngineeringUnits", None)
                eu_display = getattr(eu, "DisplayName", "")
                eu_desc = getattr(eu, "Description", "")
                ijt_log.info(f"{'  Name':<{label_width}} : {getattr(rv, 'Name', '')}")
                ijt_log.info(
                    f"{'  Current':<{label_width}} : {getattr(getattr(rv, 'CurrentValue', None), 'Value', '')}"
                )
                ijt_log.info(
                    f"{'  Previous':<{label_width}} : {getattr(getattr(rv, 'PreviousValue', None), 'Value', '')}"
                )
                ijt_log.info(
                    f"{'  PhysicalQuantity':<{label_width}} : {getattr(rv, 'PhysicalQuantity', '')}"
                )
                ijt_log.info(
                    f"{'  LowLimit':<{label_width}} : {getattr(rv, 'LowLimit', '')}"
                )
                ijt_log.info(
                    f"{'  HighLimit':<{label_width}} : {getattr(rv, 'HighLimit', '')}"
                )
                ijt_log.info(f"{'  Units':<{label_width}} : {eu_display}")
                ijt_log.info(f"{'  Description':<{label_width}} : {eu_desc}")
            except Exception as e:
                ijt_log.warning(
                    f"{'Error logging reported value':<{label_width}} : {e}"
                )
    else:
        log_field("ReportedValues", event.ReportedValues)

    ijt_log.info("-" * 80)


async def log_result_to_file(event):

    # Below logic writes the Result content to a file in result_logs/latest_result.json.
    # This logic can be used to parse the Result and use it accordingly.
    if ENABLE_RESULT_FILE_LOGGING:
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
            ijt_log.error(f"failed to log result to file: {e}")
            ijt_log.error(traceback.format_exc())
