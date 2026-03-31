"""Utility helpers for logging, time formatting, and OPC UA node serialization.

This module centralises functions that are shared across the event-handler
pipeline: structured log output, local-time formatting, OPC UA node-id and
localized-text stringification, and optional result-file persistence.
"""

import json
import re
import traceback
from datetime import datetime
from typing import Any
from pathlib import Path

import aiofiles
import pytz
from asyncua import ua

from python.ijt_logger import ijt_log
from python.serialize_data import serialize_full_event

ENABLE_RESULT_FILE_LOGGING = False  # Set to True to enable result file logging


def log_field(label: str, value: str, label_width: int = 35):
    """Log a single labelled field at INFO level with consistent column alignment.

    Args:
        label: Field name, left-padded to ``label_width`` characters.
        value: Field value as a string (or any type accepted by f-string).
        label_width: Column width for the label. Defaults to ``35``.
    """
    ijt_log.info(f"{label:<{label_width}} : {value}")


def format_local_time(dt: datetime, timezone: str = "Europe/Stockholm") -> str:
    """Format a UTC-aware datetime as a local-time string with millisecond precision.

    Args:
        dt: The datetime to format.  Should be timezone-aware; naïve datetimes
            are treated as UTC by ``astimezone``.
        timezone: A ``pytz``-compatible timezone name. Defaults to
            ``"Europe/Stockholm"``.

    Returns:
        A string in ``"YYYY-MM-DD HH:MM:SS.mmm"`` format.
    """
    local_tz = pytz.timezone(timezone)
    return dt.astimezone(local_tz).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


async def log_result_event_details(
    event: Any, _server_url: str, client_received_time: datetime
) -> str:
    """Coroutine. Log timing and metadata for a received ResultReadyEvent.

    Computes the turn-around latency between ``Result.ProcessingTimes.EndTime``
    and ``client_received_time``, then writes a structured INFO block to the
    log.  Does **not** perform additional OPC UA reads to avoid races with
    concurrent method calls.

    Args:
        event: The raw asyncua event object with at least ``Time``,
            ``EventId``, ``Result``, and ``Message`` attributes.
        _server_url: Unused (kept for interface uniformity).
        client_received_time: UTC-aware datetime captured immediately when the
            event was received.

    Returns:
        The event-id string decoded from ``event.EventId`` (UTF-8).
    """
    # Do NOT perform OPC UA reads here — this callback fires concurrently with
    # pending method calls (e.g. SimulateJobResult fires many events before
    # returning) and concurrent OPC UA requests on the same client cause
    # "Unhandled exception while sending request to OPC UA server".
    # client_received_time is a close-enough approximation for server time.
    server_time = client_received_time

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


def log_joining_system_event(event: Any) -> None:
    """Log all fields of a JoiningSystemEvent in a structured INFO block.

    Iterates over standard OPC UA base-event fields as well as
    IJT-specific extensions (``AssociatedEntities``, ``ReportedValues``,
    ``EventCode``, ``JoiningTechnology``, …) and writes each one via
    :func:`log_field`.

    Args:
        event: The event object (or a :class:`~Python.event_handler.Short`
            snapshot) exposing the fields described above as attributes.
    """
    label_width = 35
    ijt_log.info("-" * 80)
    message_text = getattr(event.Message, "Text", "Unavailable")
    ijt_log.info(f"{'JOINING SYSTEM EVENT':<40} : {message_text}")
    ijt_log.info("-" * 80)

    def log_entity(entity: Any, label_width: int) -> None:
        log_field("  Entity Name", getattr(entity, "Name", ""), label_width)
        log_field("  Description", getattr(entity, "Description", ""), label_width)
        log_field("  EntityId", getattr(entity, "EntityId", ""), label_width)
        log_field("  EntityType", getattr(entity, "EntityType", ""), label_width)
        log_field("  IsExternal", getattr(entity, "IsExternal", ""), label_width)

    def log_reported_value(rv: Any, label_width: int) -> None:
        eu = getattr(rv, "EngineeringUnits", None)
        eu_display = getattr(eu, "DisplayName", "")
        eu_desc = getattr(eu, "Description", "")
        log_field("  Name", getattr(rv, "Name", ""), label_width)
        log_field(
            "  Current",
            getattr(getattr(rv, "CurrentValue", None), "Value", ""),
            label_width,
        )
        log_field(
            "  Previous",
            getattr(getattr(rv, "PreviousValue", None), "Value", ""),
            label_width,
        )
        log_field(
            "  PhysicalQuantity", getattr(rv, "PhysicalQuantity", ""), label_width
        )
        log_field("  LowLimit", getattr(rv, "LowLimit", ""), label_width)
        log_field("  HighLimit", getattr(rv, "HighLimit", ""), label_width)
        log_field("  Units", eu_display, label_width)
        log_field("  Description", eu_desc, label_width)

    log_field("EventType", nodeid_to_str(event.EventType), label_width)
    log_field("EventId", event.EventId, label_width)
    log_field("Message", event.Message, label_width)
    log_field("SourceName", event.SourceName, label_width)
    log_field("SourceNode", event.SourceNode, label_width)
    log_field("Severity", event.Severity, label_width)
    log_field(
        "Time",
        format_local_time(event.Time) if event.Time else "Unavailable",
        label_width,
    )
    log_field(
        "ReceiveTime",
        format_local_time(event.ReceiveTime) if event.ReceiveTime else "Unavailable",
        label_width,
    )
    if event.LocalTime:
        offset = getattr(event.LocalTime, "Offset", "Unavailable")
        dst = getattr(event.LocalTime, "DaylightSavingInOffset", "Unavailable")
        log_field("LocalTime.Offset", offset, label_width)
        log_field("LocalTime.DaylightSavingInOffset", dst, label_width)
    else:
        log_field("LocalTime", "Unavailable", label_width)
    log_field("ConditionClassId", event.ConditionClassId, label_width)
    log_field("ConditionClassName", event.ConditionClassName, label_width)

    subclass_ids = [nodeid_to_str(nid) for nid in event.ConditionSubClassId]
    subclass_names = [localizedtext_to_str(lt) for lt in event.ConditionSubClassName]

    for line in format_list_for_logging(
        "ConditionSubClassId", subclass_ids, label_width
    ):
        ijt_log.info(line)

    for line in format_list_for_logging(
        "ConditionSubClassName", subclass_names, label_width
    ):
        ijt_log.info(line)

    log_field("EventCode", event.EventCode, label_width)
    log_field("EventText", event.EventText, label_width)
    log_field("JoiningTechnology", event.JoiningTechnology, label_width)

    # AssociatedEntities
    if isinstance(event.AssociatedEntities, list) and event.AssociatedEntities:
        ijt_log.info(f"{'AssociatedEntities':<{label_width}} :")
        for entity in event.AssociatedEntities:
            try:
                log_entity(entity, label_width)
            except (AttributeError, TypeError) as e:
                log_field("Error logging entity", e, label_width)
    else:
        log_field("AssociatedEntities", event.AssociatedEntities, label_width)

    # ReportedValues
    if isinstance(event.ReportedValues, list) and event.ReportedValues:
        ijt_log.info(f"{'ReportedValues':<{label_width}} :")
        for rv in event.ReportedValues:
            try:
                log_reported_value(rv, label_width)
            except (AttributeError, TypeError) as e:
                log_field("Error logging reported value", e, label_width)
    else:
        log_field("ReportedValues", event.ReportedValues, label_width)

    ijt_log.info("-" * 80)


async def log_result_to_file(event: Any) -> None:
    """Coroutine. Optionally persist a result event to a JSON file in ``logs/results/``.

    Writing is controlled by the module-level flag
    :data:`ENABLE_RESULT_FILE_LOGGING`.  The file is written atomically via a
    ``.tmp`` staging file.  Errors are logged but never propagated.

    Args:
        event: The raw asyncua result event; ``event.Result`` is serialized and
            ``event.Message.Text`` is used to derive the filename.
    """
    # Below logic writes the Result content to a file in logs/results/.
    # This logic can be used to parse the Result and use it accordingly.
    if ENABLE_RESULT_FILE_LOGGING:
        try:
            json_str = json.dumps(serialize_full_event(event.Result), ensure_ascii=False)

            log_dir = Path("logs/results")
            log_dir.mkdir(parents=True, exist_ok=True)

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


def nodeid_to_str(nodeid: ua.NodeId) -> str:
    """Convert a :class:`ua.NodeId` to its canonical OPC UA string representation.

    Supports Numeric (TwoByte/FourByte/Numeric), String, Guid, and ByteString
    node-id types.  Falls back to ``str(nodeid)`` on unexpected types or
    exceptions.

    Args:
        nodeid: An asyncua :class:`ua.NodeId` instance.

    Returns:
        A string such as ``"ns=0;i=2258"``, ``"ns=2;s=MyNode"``, or the
        ``str()`` representation on failure.
    """
    try:
        if isinstance(nodeid, ua.NodeId):
            nodeid_type = nodeid.NodeIdType
            identifier = nodeid.Identifier
            ns = nodeid.NamespaceIndex

            # TwoByte and FourByte are compact encodings of numeric node IDs
            if nodeid_type in (
                ua.NodeIdType.Numeric,
                ua.NodeIdType.TwoByte,
                ua.NodeIdType.FourByte,
            ):
                return f"ns={ns};i={identifier}"
            if nodeid_type == ua.NodeIdType.String:
                return f"ns={ns};s={identifier}"
            if nodeid_type == ua.NodeIdType.Guid:
                return f"ns={ns};g={identifier}"
            # ByteString / Opaque
            return f"ns={ns};b={identifier}"
    except Exception as exc:
        ijt_log.debug(f"Failed to format node id, falling back to str(): {exc}")
    return str(nodeid)


def localizedtext_to_str(lt: ua.LocalizedText) -> str:
    """Extract the text component from a :class:`ua.LocalizedText` value.

    Args:
        lt: An asyncua :class:`ua.LocalizedText` instance (or any value that
            will be stringified on failure).

    Returns:
        The ``Text`` attribute if set, an empty string if ``Text`` is ``None``,
        or ``str(lt)`` on failure.
    """
    try:
        if isinstance(lt, ua.LocalizedText):
            # lt.Text may be None when only Locale is set
            return lt.Text if lt.Text is not None else ""
    except Exception as exc:
        ijt_log.debug(f"Failed to read localized text, falling back to str(): {exc}")
    return str(lt)


def format_list_for_logging(
    label: str, items: list[str], label_width: int = 35
) -> list[str]:
    """Format a list of strings as indented log lines under a labelled header.

    Args:
        label: Column header, left-padded to ``label_width`` characters.
        items: String items to list under the header.
        label_width: Column width for the label. Defaults to ``35``.

    Returns:
        A list of strings: the first is the header line (``"<label> :"``), the
        remaining lines are the items indented by ``label_width + 3`` spaces.
    """
    lines = [f"{label:<{label_width}} :"]
    for item in items:
        lines.append(f"{'':<{label_width}}   {item}")
    return lines
