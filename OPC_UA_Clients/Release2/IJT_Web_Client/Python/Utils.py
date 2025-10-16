import pytz
from datetime import datetime
from typing import Optional, Dict
from asyncua import Client, ua
from Python.IJTLogger import ijt_log


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


async def log_event_details(
    event, client: Client, server_url: str, client_received_time: datetime
) -> str:
    # ijt_log.info(f"Getting Server Time")
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
    message = getattr(event.Message, "Text", "Unavailable")

    label_width = 40
    ijt_log.info("-" * 80)
    ijt_log.info(f"{'RESULT EVENT RECEIVED':<{label_width}} : {message}")
    ijt_log.info(
        f"{'1. StartTime of Tightening':<{label_width}} : {formatted_start_time}"
    )
    ijt_log.info(f"{'2. EndTime of Tightening':<{label_width}} : {formatted_end_time}")
    ijt_log.info(f"{'3. Event Generated Time':<{label_width}} : {formatted_event_time}")
    ijt_log.info(f"{'4. Client Time':<{label_width}} : {formatted_client_time}")
    # ijt_log.info(f"{'5. Server Time':<{label_width}} : {formatted_server_time}")
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
