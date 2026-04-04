"""Utilities for constructing asyncua call-input structures from front-end data.

The single public function :func:`create_call_structure` maps web-client argument
descriptors (containing an OPC UA data-type ID and a raw Python value) to the
``asyncua`` ``Variant`` or extension-object instances required by
``Node.call_method``.
"""

from typing import Any

from asyncua import ua

from python.ijt_logger import ijt_log

# IJT-specific OPC UA extension type identifiers (namespace-qualified IDs from IJT companion spec)
_JOINING_PROCESS_ID_DATA_TYPE = 3029  # ua.JoiningProcessIdentificationDataType
_ENTITY_DATA_TYPE_ARRAY = 3010  # ua.EntityDataType[]

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
    inp: Any = 0

    match data_type:
        case _ if data_type == _JOINING_PROCESS_ID_DATA_TYPE:
            if not isinstance(value, list) or len(value) < 3:
                ijt_log.error(
                    "[create_call_structure] JoiningProcessIdentificationDataType requires 3 "
                    "elements (JoiningProcessId, JoiningProcessOriginId, SelectionName), "
                    f"got {len(value) if isinstance(value, list) else type(value).__name__}"
                )
                return ua.Variant(None, ua.VariantType.Null)
            inp = ua.JoiningProcessIdentificationDataType()  # type: ignore[attr-defined]
            inp.JoiningProcessId = value[0]["value"]
            inp.JoiningProcessOriginId = value[1]["value"]
            inp.SelectionName = value[2]["value"]

        case _ if data_type == _ENTITY_DATA_TYPE_ARRAY:
            lst = []
            for row in value:
                entity_row = row["value"]
                entity = ua.EntityDataType()  # type: ignore[attr-defined]
                entity.Name = entity_row["Name"]
                entity.Description = entity_row["Description"]
                entity.EntityId = entity_row["EntityId"]
                entity.EntityOriginId = entity_row["EntityOriginId"]
                entity.IsExternal = entity_row["IsExternal"]
                entity.EntityType = entity_row["EntityType"]
                lst.append(entity)
            inp = ua.Variant(lst, ua.VariantType.ExtensionObject)

        case _:
            variant_type = _BUILTIN_TYPE_MAP.get(data_type)
            if variant_type is None:
                ijt_log.warning(
                    f"[create_call_structure] Unknown dataType {data_type!r}; falling back to String Variant."
                )
                variant_type = ua.VariantType.String
            inp = ua.Variant(value, variant_type)

    return inp
