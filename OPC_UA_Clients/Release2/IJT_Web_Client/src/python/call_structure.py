"""Utilities for constructing asyncua call-input structures from front-end data.

The single public function :func:`create_call_structure` maps web-client argument
descriptors (containing an OPC UA data-type ID and a raw Python value) to the
``asyncua`` ``Variant`` or extension-object instances required by
``Node.call_method``.
"""

import datetime
from typing import Any

from asyncua import ua

from python.ijt_logger import ijt_log

# IJT-specific OPC UA extension type identifiers (namespace-qualified IDs from IJT companion spec)
_JOINING_PROCESS_ID_DATA_TYPE = 3029  # ua.JoiningProcessIdentificationDataType
_ENTITY_DATA_TYPE_ARRAY = 3010  # ua.EntityDataType[]
_STRUCTURED_CALL_DATA_TYPES = frozenset(
    {
        _JOINING_PROCESS_ID_DATA_TYPE,
        _ENTITY_DATA_TYPE_ARRAY,
    }
)

# Correct OPC UA built-in data type ID → asyncua VariantType mapping (OPC UA Part 6, Table 1)
_BUILTIN_TYPE_MAP: dict[int, ua.VariantType] = {
    1: ua.VariantType.Boolean,
    2: ua.VariantType.SByte,
    3: ua.VariantType.Byte,
    4: ua.VariantType.Int16,
    5: ua.VariantType.UInt16,
    6: ua.VariantType.Int32,
    7: ua.VariantType.UInt32,
    8: ua.VariantType.Int64,
    9: ua.VariantType.UInt64,
    10: ua.VariantType.Float,
    11: ua.VariantType.Double,
    12: ua.VariantType.String,
    13: ua.VariantType.DateTime,
    31918: ua.VariantType.String,  # TrimmedString (IJT custom scalar type)
}


def is_structured_call_type(data_type: Any) -> bool:
    """Return whether a data type requires an IJT custom call-input builder."""
    return data_type in _STRUCTURED_CALL_DATA_TYPES


def _cast_structure_field_value(raw_value: Any, raw_type: Any) -> Any:
    """Cast structure field values according to OPC UA built-in type IDs when known."""
    try:
        type_id = int(raw_type)
    except (TypeError, ValueError):
        return raw_value
    if type_id in {2, 3, 4, 5, 6, 7, 8, 9}:
        if raw_value is None or (isinstance(raw_value, str) and raw_value.strip() == ""):
            return 0
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return raw_value
    if type_id in {10, 11}:
        if raw_value is None or (isinstance(raw_value, str) and raw_value.strip() == ""):
            return 0.0
        try:
            return float(raw_value)
        except (TypeError, ValueError):
            return raw_value
    if type_id in {12, 31918}:
        return "" if raw_value is None else str(raw_value)
    if type_id in {13, 294}:
        if isinstance(raw_value, datetime.datetime):
            return raw_value
        if isinstance(raw_value, str) and raw_value.strip():
            normalized = raw_value.replace("Z", "+00:00")
            try:
                parsed = datetime.datetime.fromisoformat(normalized)
            except ValueError:
                return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
            if parsed.tzinfo is not None:
                return parsed.astimezone(datetime.UTC).replace(tzinfo=None)
            return parsed
        return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    if type_id == 21:
        if isinstance(raw_value, ua.LocalizedText):
            return raw_value
        if isinstance(raw_value, dict):
            return ua.LocalizedText(
                Text=str(raw_value.get("Text", "") or ""),
                Locale=str(raw_value.get("Locale", "en") or "en"),
            )
        return ua.LocalizedText(Text="" if raw_value is None else str(raw_value), Locale="en")
    if type_id == 1:
        if isinstance(raw_value, bool):
            return raw_value
        return str(raw_value).strip().lower() == "true"
    if type_id == 26:
        if isinstance(raw_value, ua.Variant):
            return raw_value
        text = str(raw_value).strip()
        if text.lower() in {"true", "false"}:
            return ua.Variant(text.lower() == "true")
        try:
            return ua.Variant(int(text))
        except (TypeError, ValueError):
            pass
        try:
            return ua.Variant(float(text))
        except (TypeError, ValueError):
            pass
        return ua.Variant(raw_value)
    if type_id == _ENTITY_DATA_TYPE_ARRAY:
        if isinstance(raw_value, list):
            return _build_entity_data_type_array(raw_value)
        return raw_value
    return raw_value


def _field_entries_to_object(field_entries: list[Any]) -> dict[str, Any]:
    mapped: dict[str, Any] = {}
    for field in field_entries:
        if not isinstance(field, dict):
            continue
        field_name = field.get("name")
        if not field_name:
            continue
        mapped[field_name] = _cast_structure_field_value(field.get("value"), field.get("type"))
    return mapped


def _coerce_bool(raw_value: Any) -> bool:
    if isinstance(raw_value, bool):
        return raw_value
    return str(raw_value).strip().lower() == "true"


def _coerce_int(raw_value: Any, fallback: int = 0) -> int:
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return fallback


def _try_coerce_int(raw_value: Any) -> int | None:
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _build_entity_data_type_array(value: Any) -> list[Any]:
    rows = value if isinstance(value, list) else []
    entities = []
    for row in rows:
        if isinstance(row, dict) and "value" in row:
            entity_row = row["value"]
        else:
            entity_row = row
        if isinstance(entity_row, list):
            entity_row = _field_entries_to_object(entity_row)
        if not isinstance(entity_row, dict):
            ijt_log.warning(
                "[create_call_structure] Invalid EntityDataType row (expected dict/field-list), got %s",
                type(entity_row).__name__,
            )
            continue
        entity = ua.EntityDataType()  # type: ignore[attr-defined]
        entity.Name = str(entity_row.get("Name", "") or "")
        entity.Description = str(entity_row.get("Description", "") or "")
        entity.EntityId = str(entity_row.get("EntityId", "") or "")
        entity.EntityOriginId = str(entity_row.get("EntityOriginId", "") or "")
        entity.IsExternal = _coerce_bool(entity_row.get("IsExternal", False))
        entity.EntityType = _coerce_int(entity_row.get("EntityType", 0))
        entities.append(entity)
    return entities


def _extract_named_or_positional_field(value_rows: list[Any], field_name: str, index: int) -> Any:
    for row in value_rows:
        if isinstance(row, dict) and str(row.get("name", "")).strip().lower() == field_name.lower():
            return row.get("value", "")
    if index < len(value_rows) and isinstance(value_rows[index], dict):
        return value_rows[index].get("value", "")
    return ""


def _resolve_structure_class(data_type: Any, namespace_index: Any, structure_name: str) -> Any:
    """Resolve an asyncua generated structure class by explicit name or type id."""
    if structure_name:
        structure_cls = getattr(ua, structure_name, None)
        if structure_cls is not None:
            return structure_cls

    try:
        data_type_id = int(data_type)
    except (TypeError, ValueError):
        return None
    try:
        ns_index = int(namespace_index) if namespace_index is not None else None
    except (TypeError, ValueError):
        ns_index = None

    try:
        node_id = ua.NodeId(
            ua.Int32(data_type_id),
            ua.Int16(ns_index if ns_index is not None else 0),
        )
        structure_cls = ua.get_extensionobject_class_type(node_id)
        if structure_cls is not None:
            return structure_cls
    except Exception as exc:
        ijt_log.debug(
            "[create_call_structure] get_extensionobject_class_type lookup failed for ns=%s;i=%s: %s",
            ns_index,
            data_type_id,
            exc,
        )

    for registry_name in ("extension_objects_by_datatype", "extension_objects_by_typeid"):
        registry = getattr(ua, registry_name, {})
        for node_id, structure_cls in registry.items():
            node_identifier = getattr(node_id, "Identifier", None)
            node_namespace = getattr(node_id, "NamespaceIndex", None)
            parsed_identifier = _try_coerce_int(node_identifier)
            if parsed_identifier is not None:
                node_identifier = parsed_identifier
            parsed_namespace = _try_coerce_int(node_namespace)
            if parsed_namespace is not None:
                node_namespace = parsed_namespace
            if node_identifier != data_type_id:
                continue
            if ns_index is not None and node_namespace != ns_index:
                continue
            return structure_cls

    for node_id, structure_cls in getattr(ua, "extension_objects_by_typeid", {}).items():
        node_identifier = getattr(node_id, "Identifier", None)
        node_namespace = getattr(node_id, "NamespaceIndex", None)
        parsed_identifier = _try_coerce_int(node_identifier)
        if parsed_identifier is not None:
            node_identifier = parsed_identifier
        parsed_namespace = _try_coerce_int(node_namespace)
        if parsed_namespace is not None:
            node_namespace = parsed_namespace
        if node_identifier != data_type_id:
            continue
        if ns_index is not None and node_namespace != ns_index:
            continue
        return structure_cls

    return None


def _build_extension_object(structure_cls: Any, structure_label: str, field_entries: list[Any]) -> Any:
    """Instantiate a generated asyncua structure from class + field descriptors."""
    if structure_cls is None:
        ijt_log.warning(f"[create_call_structure] Unknown structure class for {structure_label!r}")
        return None
    try:
        instance = structure_cls()  # type: ignore[misc]
    except Exception as exc:
        ijt_log.warning(f"[create_call_structure] Could not instantiate structure {structure_label!r}: {exc}")
        return None

    for field in field_entries:
        if not isinstance(field, dict):
            continue
        field_name = field.get("name")
        if not field_name:
            continue
        field_value = _cast_structure_field_value(field.get("value"), field.get("type"))
        try:
            setattr(instance, field_name, field_value)
        except Exception as exc:
            ijt_log.warning(f"[create_call_structure] Could not set field {field_name!r} on {structure_label!r}: {exc}")
            return None
    return instance


def create_call_structure(argument: dict[str, Any]) -> Any:
    """Convert a web-client argument descriptor into an asyncua call input structure.

    Handles three categories of OPC UA data types:

    * **JoiningProcessIdentificationDataType** (type ID 3029) — builds a
      ``ua.JoiningProcessIdentificationDataType`` from a three-element list.
    * **EntityDataType array** (type ID 3010) — builds a
      ``ua.Variant(list[EntityDataType], ExtensionObject)``.
    * **OPC UA built-in types** — maps the numeric type ID to the matching
      :class:`ua.VariantType` via ``_BUILTIN_TYPE_MAP`` and wraps the value
      in a ``ua.Variant``.

    Args:
        argument: A dict with the following keys:

            * ``"dataType"`` (``int``) — OPC UA data type node identifier.
            * ``"value"`` (``Any``) — Raw value received from the front-end.
              For ``JoiningProcessIdentificationDataType`` this must be a
              list of at least three ``{"value": …}`` dicts.

    Returns:
        An ``asyncua`` call-input object — either a typed ``ua.Variant``, a
        ``ua.JoiningProcessIdentificationDataType``, or
        ``ua.Variant(None, ua.VariantType.Null)`` when the input is invalid.

    Raises:
        KeyError: If ``"dataType"`` or ``"value"`` is missing from
            ``argument``.
    """
    value = argument["value"]
    data_type = argument["dataType"]
    namespace_index = argument.get("dataTypeNamespaceIndex")
    structure_name_hint = str(argument.get("dataTypeName") or "").strip()
    inp: Any = 0

    match data_type:
        case _ if data_type == _JOINING_PROCESS_ID_DATA_TYPE:
            entries = value.get("value") if isinstance(value, dict) else value
            if not isinstance(entries, list) or len(entries) < 3:
                ijt_log.error(
                    "[create_call_structure] JoiningProcessIdentificationDataType requires 3 "
                    "elements (JoiningProcessId, JoiningProcessOriginId, SelectionName), "
                    f"got {len(entries) if isinstance(entries, list) else type(value).__name__}"
                )
                return ua.Variant(None, ua.VariantType.Null)
            inp = ua.JoiningProcessIdentificationDataType()  # type: ignore[attr-defined]
            inp.JoiningProcessId = _extract_named_or_positional_field(entries, "JoiningProcessId", 0)
            inp.JoiningProcessOriginId = _extract_named_or_positional_field(entries, "JoiningProcessOriginId", 1)
            inp.SelectionName = _extract_named_or_positional_field(entries, "SelectionName", 2)

        case _ if data_type == _ENTITY_DATA_TYPE_ARRAY:
            lst = _build_entity_data_type_array(value)
            inp = ua.Variant(lst, ua.VariantType.ExtensionObject)

        case _:
            if isinstance(value, dict) and isinstance(value.get("value"), list):
                structure_name = str(value.get("structure", "")).strip()
                structure_cls = _resolve_structure_class(
                    data_type, namespace_index, structure_name or structure_name_hint
                )
                extension_object = _build_extension_object(
                    structure_cls,
                    structure_name or structure_name_hint or f"ns={namespace_index};i={data_type}",
                    value["value"],
                )
                if extension_object is None:
                    return ua.Variant(None, ua.VariantType.Null)
                return ua.Variant(extension_object, ua.VariantType.ExtensionObject)
            if (
                isinstance(value, list)
                and value
                and all(isinstance(field, dict) and field.get("name") for field in value)
            ):
                structure_cls = _resolve_structure_class(data_type, namespace_index, structure_name_hint)
                extension_object = _build_extension_object(
                    structure_cls,
                    structure_name_hint or f"ns={namespace_index};i={data_type}",
                    value,
                )
                if extension_object is None:
                    return ua.Variant(None, ua.VariantType.Null)
                return ua.Variant(extension_object, ua.VariantType.ExtensionObject)
            if isinstance(value, list) and value and all(isinstance(row, dict) for row in value):
                if all(isinstance(row.get("value"), list) for row in value):
                    extension_objects = []
                    for row in value:
                        structure_name = str(row.get("structure", "")).strip()
                        structure_cls = _resolve_structure_class(
                            data_type, namespace_index, structure_name or structure_name_hint
                        )
                        extension_object = _build_extension_object(
                            structure_cls,
                            structure_name or structure_name_hint or f"ns={namespace_index};i={data_type}",
                            row["value"],
                        )
                        if extension_object is None:
                            return ua.Variant(None, ua.VariantType.Null)
                        extension_objects.append(extension_object)
                    return ua.Variant(extension_objects, ua.VariantType.ExtensionObject)
            variant_type = _BUILTIN_TYPE_MAP.get(data_type)
            if variant_type is None:
                ijt_log.warning(
                    f"[create_call_structure] Unknown dataType {data_type!r}; falling back to String Variant."
                )
                variant_type = ua.VariantType.String
            inp = ua.Variant(value, variant_type)

    return inp
