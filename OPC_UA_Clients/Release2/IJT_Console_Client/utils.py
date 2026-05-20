import re
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles  # type: ignore[import-untyped]
import pytz  # type: ignore[import-untyped]
from asyncua import Client, ua
from asyncua.ua import String
from asyncua.ua.uaerrors import UaError

# ---- START: robust JSON import (fallback if orjson is missing) ----
try:
    import orjson  # fast path
except ImportError:
    orjson = None  # type: ignore[assignment]


def _to_json_str(obj) -> str:
    if orjson is not None:
        try:
            return orjson.dumps(obj).decode("utf-8")
        except Exception as exc:
            ijt_log.debug(f"orjson serialization failed; using stdlib json fallback: {exc}")

    import json

    # ensure_ascii=True avoids unicode surrogate encoding crashes in noisy payloads
    return json.dumps(obj, ensure_ascii=True, separators=(",", ":"), default=str)


def _to_json_bytes(obj) -> bytes:
    return _to_json_str(obj).encode("utf-8")


# ---- END: robust JSON import ----

from client_config import ENABLE_RESULT_FILE_LOGGING
from ijt_logger import ijt_log
from serialize_data import serialize_full_event

_NS_APP_URI = "urn:AtlasCopco:IJT:Tightening:Server/"


def log_field(label: str, value: str, label_width: int = 35):
    ijt_log.info(f"{label:<{label_width}} : {value}")


def log_separator(label_width: int = 35) -> None:
    """Emit a horizontal separator line to the log at INFO level.

    Args:
        label_width: Width of label column (default 35) — separator spans
            this width plus 40 extra characters.
    """
    ijt_log.info("-" * (label_width + 40))


def format_local_time(dt: datetime, timezone: str = "Europe/Stockholm") -> str:  # pylint: disable=redefined-outer-name
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    local_tz = pytz.timezone(timezone)
    return dt.astimezone(local_tz).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


async def read_server_time(client: Client) -> datetime | None:
    try:
        node = client.get_node(ua.NodeId(2258, 0))  # type: ignore[arg-type]  # ServerStatus.CurrentTime
        return await node.read_value()
    except Exception as e:
        ijt_log.warning(f"{'Server Time Read Failed':<40} : {e}")
        return None


async def _namespace_index(client: Client, namespace_uri: str) -> int | None:
    try:
        return await client.get_namespace_index(namespace_uri)
    except Exception as exc:
        ijt_log.debug(f"Namespace index lookup failed; reading NamespaceArray fallback: {exc}")

    try:
        namespace_array_node = client.get_node(ua.NodeId(2255, 0))  # type: ignore[arg-type]  # Server.NamespaceArray
        namespace_array = await namespace_array_node.read_value()
        return list(namespace_array).index(namespace_uri)
    except Exception:
        return None


async def _find_child_by_browse_name(parent_node, browse_name: str, ns_idx: int | None = None):
    if ns_idx is not None:
        try:
            return await parent_node.get_child(f"{ns_idx}:{browse_name}")
        except Exception as exc:
            ijt_log.debug(f"Direct browse lookup failed for {browse_name}; enumerating children: {exc}")

    try:
        children = await parent_node.get_children()
    except Exception:
        return None

    fallback_child = None
    for child in children:
        try:
            child_browse_name = await child.read_browse_name()
        except (AttributeError, UaError) as exc:
            ijt_log.debug(f"Skipping unreadable child BrowseName while looking for {browse_name}: {exc}")
            child_browse_name = None

        if child_browse_name is None:
            continue

        if getattr(child_browse_name, "Name", None) != browse_name:
            continue
        if ns_idx is None or getattr(child_browse_name, "NamespaceIndex", None) == ns_idx:
            return child
        if fallback_child is None:
            fallback_child = child
    return fallback_child


async def read_tool_identifier(client: Client) -> String | str | None:
    """Return the first Tool's ProductInstanceUri exposed by the server, or
    ``None`` when the address-space legitimately has no such node.

    Exception policy (deliberate):
    Only swallow errors that genuinely mean *the server's address space does
    not currently expose a tool identifier* — OPC UA status errors, network
    timeouts, and transport-level connection drops. Any other exception
    (``NameError``, ``AttributeError``, ``ImportError``, internal asyncua
    bugs, asyncio cancellation propagated through user code, etc.) indicates
    a real programming or environment problem and is re-raised so callers see
    the true root cause instead of a misleading "ProductInstanceUri missing"
    test failure.
    """
    try:
        ns_app = await _namespace_index(client, _NS_APP_URI)
        objects = client.nodes.objects

        joining_system = await _find_child_by_browse_name(objects, "TighteningSystem", ns_app)
        if joining_system is None:
            return None

        asset_management = await _find_child_by_browse_name(joining_system, "AssetManagement", ns_app)
        if asset_management is None:
            return None

        assets = await _find_child_by_browse_name(asset_management, "Assets", ns_app)
        if assets is None:
            return None

        tools = await _find_child_by_browse_name(assets, "Tools", ns_app)
        if tools is None:
            return None

        for tool_node in await tools.get_children():
            identification = await _find_child_by_browse_name(tool_node, "Identification", ns_app)
            if identification is None:
                continue

            piu_node = await _find_child_by_browse_name(identification, "ProductInstanceUri", ns_app)
            if piu_node is None:
                continue

            value = await piu_node.read_value()
            if value is not None and str(value).strip():
                return value
        return None
    except (UaError, TimeoutError, ConnectionError, OSError) as e:
        ijt_log.warning(f"{'Tool Identifier Read Failed':<40} : {e}")
        return None


async def log_result_event_details(event, _server_url: str, client_received_time: datetime) -> str:
    try:
        # Do NOT perform OPC UA reads here — this callback fires concurrently with
        # pending method calls and concurrent OPC UA requests on the same client
        # cause "Unhandled exception while sending request to OPC UA server".
        server_time = client_received_time
        event_time = event.Time
        event_id = event.EventId.decode("utf-8", errors="replace")

        meta = getattr(event.Result, "ResultMetaData", None)
        times = getattr(meta, "ProcessingTimes", None) if meta else None
        start_time = getattr(times, "StartTime", None)
        end_time = getattr(times, "EndTime", None)
        creation_time = getattr(meta, "CreationTime", None) if meta else None

        if end_time and end_time.tzinfo is None:
            end_time = pytz.utc.localize(end_time)

        latency_ms = (client_received_time - end_time).total_seconds() * 1000 if end_time else None

        label_width = 35

        log_separator(label_width)
        log_field(
            "RESULT EVENT RECEIVED",
            getattr(event.Message, "Text", "Unavailable"),
            label_width,
        )
        log_field(
            "1. StartTime of Tightening",
            format_local_time(start_time) if start_time else "Unavailable",
            label_width,
        )
        log_field(
            "2. EndTime of Tightening",
            format_local_time(end_time) if end_time else "Unavailable",
            label_width,
        )
        log_field(
            "3. Result Creation Time",
            format_local_time(creation_time) if creation_time else "Unavailable",
            label_width,
        )
        log_field(
            "4. Result Event Generated Time",
            format_local_time(event_time) if event_time else "Unavailable",
            label_width,
        )
        log_field("5. Client Time", format_local_time(client_received_time), label_width)
        log_field(
            "6. Server Time",
            format_local_time(server_time) if server_time else "Unavailable",
            label_width,
        )

        if latency_ms is not None:
            log_field(
                "*** Turn around Time (EndTime -> Client)",
                f"{abs(latency_ms):.3f} ms",
                label_width,
            )
        else:
            log_field("*** Turn around Time (EndTime -> Client)", "Unavailable", label_width)

        log_separator(label_width)
        return event_id
    except Exception as e:
        ijt_log.error(f"Error logging result event details: {e}")
        ijt_log.error(traceback.format_exc())
        return "unknown"


async def log_joining_system_event(event: Any) -> None:
    label_width = 35
    log_separator(label_width)
    log_field(
        "JOINING SYSTEM EVENT",
        getattr(event.Message, "Text", "Unavailable"),
        label_width,
    )

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
        log_field(
            "LocalTime.Offset",
            getattr(event.LocalTime, "Offset", "Unavailable"),
            label_width,
        )
        log_field(
            "LocalTime.DaylightSavingInOffset",
            getattr(event.LocalTime, "DaylightSavingInOffset", "Unavailable"),
            label_width,
        )
    else:
        log_field("LocalTime", "Unavailable", label_width)

    log_field("ConditionClassId", nodeid_to_str(event.ConditionClassId), label_width)
    log_field(
        "ConditionClassName",
        localizedtext_to_str(event.ConditionClassName),
        label_width,
    )

    subclass_ids = [nodeid_to_str(nid) for nid in event.ConditionSubClassId]
    log_field("ConditionSubClassId", "", label_width)
    for item in subclass_ids:
        log_field("", item, label_width)

    subclass_names = [localizedtext_to_str(lt) for lt in event.ConditionSubClassName]
    log_field("ConditionSubClassName", "", label_width)
    for item in subclass_names:
        log_field("", item, label_width)

    log_field("EventCode", event.EventCode, label_width)
    log_field("EventText", event.EventText, label_width)
    log_field("JoiningTechnology", event.JoiningTechnology, label_width)

    if isinstance(event.AssociatedEntities, list) and event.AssociatedEntities:
        log_field("AssociatedEntities", "", label_width)
        for entity in event.AssociatedEntities:
            try:
                log_entity(entity)
            except Exception as e:
                log_field("Error logging entity", str(e), label_width)
    else:
        log_field("AssociatedEntities", str(event.AssociatedEntities), label_width)

    if isinstance(event.ReportedValues, list) and event.ReportedValues:
        log_field("ReportedValues", "", label_width)
        for rv in event.ReportedValues:
            try:
                log_reported_value(rv)
            except Exception as e:
                log_field("Error logging reported value", str(e), label_width)
    else:
        log_field("ReportedValues", str(event.ReportedValues), label_width)

    log_separator(label_width)


def log_entity(entity: Any) -> None:
    label_width = 35
    for field in ["Name", "Description", "EntityId", "EntityType", "IsExternal"]:
        log_field(field, getattr(entity, field, ""), label_width)


def log_reported_value(rv: Any) -> None:
    label_width = 35
    eu = getattr(rv, "EngineeringUnits", None)
    eu_display = getattr(eu, "DisplayName", "")
    eu_desc = getattr(eu, "Description", "")

    log_field("Name", getattr(rv, "Name", ""), label_width)
    log_field("Current", getattr(getattr(rv, "CurrentValue", None), "Value", ""), label_width)
    log_field(
        "Previous",
        getattr(getattr(rv, "PreviousValue", None), "Value", ""),
        label_width,
    )
    log_field("PhysicalQuantity", getattr(rv, "PhysicalQuantity", ""), label_width)
    log_field("LowLimit", getattr(rv, "LowLimit", ""), label_width)
    log_field("HighLimit", getattr(rv, "HighLimit", ""), label_width)
    log_field("Units", eu_display, label_width)
    log_field("Description", eu_desc, label_width)


def nodeid_to_str(nodeid: ua.NodeId) -> str:
    try:
        if isinstance(nodeid, ua.NodeId):
            ns = nodeid.NamespaceIndex
            identifier = nodeid.Identifier
            # TwoByte and FourByte are compact encodings of numeric node IDs
            if nodeid.NodeIdType in (
                ua.NodeIdType.Numeric,
                ua.NodeIdType.TwoByte,
                ua.NodeIdType.FourByte,
            ):
                return f"ns={ns};i={identifier}"  # type: ignore[str-bytes-safe]
            if nodeid.NodeIdType == ua.NodeIdType.String:
                return f"ns={ns};s={identifier}"  # type: ignore[str-bytes-safe]
            if nodeid.NodeIdType == ua.NodeIdType.Guid:
                return f"ns={ns};g={identifier}"  # type: ignore[str-bytes-safe]
            # ByteString / Opaque
            return f"ns={ns};b={identifier}"  # type: ignore[str-bytes-safe]
    except Exception as exc:
        ijt_log.debug(f"Failed to format node id, falling back to str(): {exc}")
    return str(nodeid)


def localizedtext_to_str(lt: ua.LocalizedText) -> str:
    try:
        if isinstance(lt, ua.LocalizedText):
            # lt.Text may be None when only Locale is set
            return lt.Text if lt.Text is not None else ""
    except Exception as exc:
        ijt_log.debug(f"Failed to read localized text, falling back to str(): {exc}")
    return str(lt)


def format_list_for_logging(label: str, items: list[str], label_width: int = 35) -> list[str]:
    lines = [f"{label:<{label_width}} :"]
    for item in items:
        lines.append(f"{'':<{label_width}} {item}")
    return lines


async def log_result_to_file(event: Any) -> None:
    if ENABLE_RESULT_FILE_LOGGING:
        try:
            json_data = serialize_full_event(event.Result)
            json_str = _to_json_str(json_data)

            log_dir = Path("logs") / "results"
            log_dir.mkdir(exist_ok=True)

            safe_message = re.sub(r"[^\w\-_\. ]", "_", str(event.Message).replace(":", "_"))
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            event_id = getattr(event, "EventId", "unknown")

            filename = f"{safe_message}_{event_id}_{timestamp}.json"
            temp_file = log_dir / f"{filename}.tmp"
            final_file = log_dir / filename

            async with aiofiles.open(temp_file, mode="w", encoding="utf-8") as f:
                await f.write(json_str)
            temp_file.rename(final_file)

            ijt_log.info(f"Event Result logged to {final_file}")
        except Exception as e:
            ijt_log.error(f"Failed to log result to file: {e}")
            ijt_log.error(traceback.format_exc())
