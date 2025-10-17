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


def log_joining_system_event(self):
    ijt_log.info("----- Parsed JoiningSystemEvent -----")
    ijt_log.info(f"EventType: {self.EventType}")
    ijt_log.info(f"EventId: {self.EventId}")
    ijt_log.info(f"Message: {self.Message}")
    ijt_log.info(f"SourceName: {self.SourceName}")
    ijt_log.info(f"SourceNode: {self.SourceNode}")
    ijt_log.info(f"Severity: {self.Severity}")
    ijt_log.info(f"Time: {self.Time}")
    ijt_log.info(f"ReceiveTime: {self.ReceiveTime}")
    ijt_log.info(f"LocalTime: {self.LocalTime}")
    ijt_log.info(f"ConditionClassId: {self.ConditionClassId}")
    ijt_log.info(f"ConditionClassName: {self.ConditionClassName}")
    ijt_log.info(f"ConditionSubClassId: {self.ConditionSubClassId}")
    ijt_log.info(f"ConditionSubClassName: {self.ConditionSubClassName}")
    ijt_log.info(f"EventCode: {self.EventCode}")
    ijt_log.info(f"EventText: {self.EventText}")
    ijt_log.info(f"JoiningTechnology: {self.JoiningTechnology}")

    # AssociatedEntities
    if isinstance(self.AssociatedEntities, list) and self.AssociatedEntities:
        ijt_log.info("--- AssociatedEntities ---")
        for entity in self.AssociatedEntities:
            try:
                ijt_log.info(
                    f"Entity Name: {getattr(entity, 'Name', '')}, "
                    f"Description: {getattr(entity, 'Description', '')}, "
                    f"EntityId: {getattr(entity, 'EntityId', '')}, "
                    f"EntityType: {getattr(entity, 'EntityType', '')}, "
                    f"IsExternal: {getattr(entity, 'IsExternal', '')}"
                )
            except Exception as e:
                ijt_log.warning(f"Error logging entity: {e}")
    else:
        ijt_log.info(f"AssociatedEntities: {self.AssociatedEntities}")

    # ReportedValues
    if isinstance(self.ReportedValues, list) and self.ReportedValues:
        ijt_log.info("--- ReportedValues ---")
        for rv in self.ReportedValues:
            try:
                eu = getattr(rv, "EngineeringUnits", None)
                eu_display = getattr(eu, "DisplayName", "")
                eu_desc = getattr(eu, "Description", "")
                ijt_log.info(
                    f"ReportedValue Name: {getattr(rv, 'Name', '')}, "
                    f"Current: {getattr(getattr(rv, 'CurrentValue', None), 'Value', '')}, "
                    f"Previous: {getattr(getattr(rv, 'PreviousValue', None), 'Value', '')}, "
                    f"PhysicalQuantity: {getattr(rv, 'PhysicalQuantity', '')}, "
                    f"LowLimit: {getattr(rv, 'LowLimit', '')}, "
                    f"HighLimit: {getattr(rv, 'HighLimit', '')}, "
                    f"Units: {eu_display}, Description: {eu_desc}"
                )
            except Exception as e:
                ijt_log.warning(f"Error logging reported value: {e}")
    else:
        ijt_log.info(f"ReportedValues: {self.ReportedValues}")

    ijt_log.info("--------------------------------------")
