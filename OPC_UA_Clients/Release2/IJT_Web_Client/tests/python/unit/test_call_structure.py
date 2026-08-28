"""
Tests for Python/call_structure.py — OPC UA method argument builder.

Covers:
- All 14 OPC UA built-in data types map to the correct ua.VariantType (OPC UA Part 6 Table 1)
- TrimmedString (31918) maps to String
- Unknown dataType falls back to String with a warning
- IJT-specific type 3029 (JoiningProcessIdentificationDataType) guards:
    - non-list value returns Null variant
    - list shorter than 3 returns Null variant
- Named constants expose the correct numeric IDs
- Builtin type round-trip: value is preserved inside ua.Variant
"""

import datetime

import pytest

# Import asyncua first to skip the whole module if the library is not installed.
_ = pytest.importorskip("asyncua", reason="asyncua not installed")
from asyncua import ua  # noqa: E402

from python.call_structure import (  # noqa: E402
    _BUILTIN_TYPE_MAP,
    _ENTITY_DATA_TYPE_ARRAY,
    _JOINING_PROCESS_ID_DATA_TYPE,
    _build_extension_object,
    _cast_structure_field_value,
    _coerce_bool,
    _coerce_int,
    _extract_named_or_positional_field,
    _field_entries_to_object,
    _resolve_structure_class,
    _try_coerce_int,
    create_call_structure,
    is_structured_call_type,
)

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------


def test_named_constants_have_correct_values():
    assert _JOINING_PROCESS_ID_DATA_TYPE == 3029
    assert _ENTITY_DATA_TYPE_ARRAY == 3010


@pytest.mark.parametrize("data_type", [3029, 3010])
def test_structured_call_types_are_centralized(data_type):
    assert is_structured_call_type(data_type)


def test_builtin_call_type_does_not_require_custom_builder():
    assert not is_structured_call_type(12)


# ---------------------------------------------------------------------------
# _BUILTIN_TYPE_MAP completeness and correctness (OPC UA Part 6 Table 1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "type_id, expected",
    [
        (1, ua.VariantType.Boolean),
        (2, ua.VariantType.SByte),
        (3, ua.VariantType.Byte),
        (4, ua.VariantType.Int16),
        (5, ua.VariantType.UInt16),
        (6, ua.VariantType.Int32),
        (7, ua.VariantType.UInt32),
        (8, ua.VariantType.Int64),
        (9, ua.VariantType.UInt64),
        (10, ua.VariantType.Float),
        (11, ua.VariantType.Double),
        (12, ua.VariantType.String),
        (13, ua.VariantType.DateTime),
    ],
)
def test_builtin_type_map_matches_opcua_spec(type_id, expected):
    assert _BUILTIN_TYPE_MAP[type_id] is expected, (
        f"Type ID {type_id}: expected {expected}, got {_BUILTIN_TYPE_MAP.get(type_id)}"
    )


def test_trimmed_string_maps_to_string():
    assert _BUILTIN_TYPE_MAP[31918] is ua.VariantType.String


def test_builtin_type_map_has_no_extra_numeric_ids():
    """Ensure no accidental duplicate or extra numeric keys beyond the 14 spec entries."""
    numeric_keys = {k for k in _BUILTIN_TYPE_MAP if isinstance(k, int) and k < 1000}
    assert numeric_keys == set(range(1, 14)), f"Unexpected or missing numeric keys: {numeric_keys}"


# ---------------------------------------------------------------------------
# create_call_structure — builtin type round-trip
# ---------------------------------------------------------------------------


def test_create_call_structure_string_type():
    arg = {"dataType": 12, "value": "hello"}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.String
    assert result.Value == "hello"


def test_create_call_structure_int32_type():
    arg = {"dataType": 6, "value": 42}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Int32
    assert result.Value == 42


def test_create_call_structure_float_type():
    arg = {"dataType": 10, "value": 3.14}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Float


def test_create_call_structure_double_type():
    arg = {"dataType": 11, "value": 2.718}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Double


def test_create_call_structure_boolean_type():
    arg = {"dataType": 1, "value": True}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Boolean
    assert result.Value is True


def test_create_call_structure_uint32_type():
    arg = {"dataType": 7, "value": 100}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.UInt32


def test_create_call_structure_int16_type():
    arg = {"dataType": 4, "value": -500}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Int16


def test_create_call_structure_uint16_type():
    arg = {"dataType": 5, "value": 500}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.UInt16


def test_create_call_structure_int64_type():
    arg = {"dataType": 8, "value": 9999999999}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Int64


def test_create_call_structure_uint64_type():
    arg = {"dataType": 9, "value": 9999999999}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.UInt64


def test_create_call_structure_sbyte_type():
    arg = {"dataType": 2, "value": -10}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.SByte


def test_create_call_structure_byte_type():
    arg = {"dataType": 3, "value": 255}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Byte


def test_create_call_structure_trimmed_string():
    arg = {"dataType": 31918, "value": "trimmed"}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.String
    assert result.Value == "trimmed"


# ---------------------------------------------------------------------------
# create_call_structure — unknown type falls back to String
# ---------------------------------------------------------------------------


def test_create_call_structure_unknown_type_falls_back_to_string():
    arg = {"dataType": 99999, "value": "some_value"}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.String
    assert result.Value == "some_value"


def test_create_call_structure_zero_type_falls_back_to_string():
    """Type ID 0 is not a valid OPC UA built-in type; should fall back gracefully."""
    arg = {"dataType": 0, "value": "x"}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.String


# ---------------------------------------------------------------------------
# create_call_structure — type 3029 guard checks (no NodeSet needed)
# ---------------------------------------------------------------------------


def test_joining_process_type_with_non_list_returns_null():
    arg = {"dataType": 3029, "value": "not_a_list"}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Null


def test_joining_process_type_with_empty_list_returns_null():
    arg = {"dataType": 3029, "value": []}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Null


def test_joining_process_type_with_two_elements_returns_null():
    """Must have exactly 3 elements: JoiningProcessId, JoiningProcessOriginId, SelectionName."""
    arg = {"dataType": 3029, "value": [{"value": "a"}, {"value": "b"}]}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Null


def test_joining_process_type_with_none_returns_null():
    arg = {"dataType": 3029, "value": None}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Null


# ---------------------------------------------------------------------------
# create_call_structure — type 3029 happy path (IJT NodeSet fixture)
# ---------------------------------------------------------------------------


@pytest.fixture()
def ijt_nodeset_types():
    """Register IJT struct types using asyncua's native make_structure API.

    ``asyncua.common.structures104.make_structure`` builds a proper OPC UA
    dataclass from a ``ua.StructureDefinition`` and registers it on the ``ua``
    module — exactly the same mechanism used when a real server loads its type
    dictionary.  No stub or monkey-patching is needed.

    Field definitions are derived from Opc.Ua.Ijt.Base.NodeSet2.xml (NodeId
    3029, namespace 4) which ships with the Release 2 server simulator.

    Cleanup removes the registration after the test so other tests are not
    affected even when the full suite is run in a single process.
    """
    from asyncua.common.structures104 import make_structure

    already_registered = hasattr(ua, "JoiningProcessIdentificationDataType")
    if not already_registered:
        sdef = ua.StructureDefinition()
        sdef.StructureType = ua.StructureType.Structure
        sdef.Fields = [
            ua.StructureField(Name="JoiningProcessId", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1),  # type: ignore[arg-type]
            ua.StructureField(Name="JoiningProcessOriginId", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1),  # type: ignore[arg-type]
            ua.StructureField(Name="SelectionName", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1),  # type: ignore[arg-type]
        ]
        make_structure(ua.NodeId(3029, 4), "JoiningProcessIdentificationDataType", sdef)  # type: ignore[arg-type]

    yield

    if not already_registered and hasattr(ua, "JoiningProcessIdentificationDataType"):
        delattr(ua, "JoiningProcessIdentificationDataType")


def test_joining_process_type_happy_path(ijt_nodeset_types):  # noqa: ARG001 — fixture registers types
    """Verifies the happy path for type 3029 (JoiningProcessIdentificationDataType)."""
    arg = {
        "dataType": 3029,
        "value": [
            {"value": "proc-001"},
            {"value": "origin-001"},
            {"value": "selection-A"},
        ],
    }
    result = create_call_structure(arg)
    assert isinstance(result, ua.JoiningProcessIdentificationDataType)  # type: ignore[attr-defined]
    assert result.JoiningProcessId == "proc-001"
    assert result.JoiningProcessOriginId == "origin-001"
    assert result.SelectionName == "selection-A"


def test_joining_process_type_accepts_wrapped_schema_rows(ijt_nodeset_types):  # noqa: ARG001
    arg = {
        "dataType": 3029,
        "value": {
            "value": [
                {"name": "JoiningProcessId", "value": "proc-002", "type": "31918"},
                {"name": "JoiningProcessOriginId", "value": "origin-002", "type": "31918"},
                {"name": "SelectionName", "value": "selection-B", "type": "31918"},
            ]
        },
    }
    result = create_call_structure(arg)
    assert isinstance(result, ua.JoiningProcessIdentificationDataType)  # type: ignore[attr-defined]
    assert result.JoiningProcessId == "proc-002"
    assert result.JoiningProcessOriginId == "origin-002"
    assert result.SelectionName == "selection-B"


# ---------------------------------------------------------------------------
# create_call_structure — type 3010 (EntityDataType array)
# ---------------------------------------------------------------------------


@pytest.fixture()
def ijt_entity_type():
    """Register EntityDataType using asyncua's native make_structure API (NodeId 3010)."""
    from asyncua.common.structures104 import make_structure

    already_registered = hasattr(ua, "EntityDataType")
    if not already_registered:
        sdef = ua.StructureDefinition()
        sdef.StructureType = ua.StructureType.Structure
        sdef.Fields = [
            ua.StructureField(Name="Name", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1),  # type: ignore[arg-type]
            ua.StructureField(Name="Description", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1),  # type: ignore[arg-type]
            ua.StructureField(Name="EntityId", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1),  # type: ignore[arg-type]
            ua.StructureField(Name="EntityOriginId", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1),  # type: ignore[arg-type]
            ua.StructureField(Name="IsExternal", DataType=ua.NodeId(ua.ObjectIds.Boolean), ValueRank=-1),  # type: ignore[arg-type]
            # EntityType is Int16 per Opc.Ua.Ijt.Base.NodeSet2.xml NodeId 3010
            ua.StructureField(Name="EntityType", DataType=ua.NodeId(ua.ObjectIds.Int16), ValueRank=-1),  # type: ignore[arg-type]
        ]
        make_structure(ua.NodeId(3010, 4), "EntityDataType", sdef)  # type: ignore[arg-type]

    yield

    if not already_registered and hasattr(ua, "EntityDataType"):
        delattr(ua, "EntityDataType")


def test_entity_data_type_array_happy_path(ijt_entity_type):  # noqa: ARG001
    """EntityDataType array (type 3010) wraps entities in ExtensionObject Variant."""
    arg = {
        "dataType": 3010,
        "value": [
            {
                "value": {
                    "Name": "Wrench-1",
                    "Description": "Electric torque wrench",
                    "EntityId": "ent-001",
                    "EntityOriginId": "orig-001",
                    "IsExternal": False,
                    "EntityType": 1,
                }
            },
            {
                "value": {
                    "Name": "Socket-1",
                    "Description": "Socket adapter",
                    "EntityId": "ent-002",
                    "EntityOriginId": "orig-002",
                    "IsExternal": True,
                    "EntityType": 2,
                }
            },
        ],
    }
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.ExtensionObject
    assert isinstance(result.Value, list)
    assert len(result.Value) == 2
    assert result.Value[0].Name == "Wrench-1"
    assert result.Value[1].IsExternal is True


def test_entity_data_type_array_empty_list(ijt_entity_type):  # noqa: ARG001
    """Empty entity list still returns an ExtensionObject Variant."""
    arg = {"dataType": 3010, "value": []}
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.ExtensionObject
    assert result.Value == []


def test_entity_data_type_array_accepts_schema_field_rows(ijt_entity_type):  # noqa: ARG001
    arg = {
        "dataType": 3010,
        "value": [
            {
                "value": [
                    {"name": "Name", "value": "Tool", "type": "12"},
                    {"name": "Description", "value": "Joining tool", "type": "12"},
                    {"name": "EntityId", "value": "ent-01", "type": "12"},
                    {"name": "EntityOriginId", "value": "orig-01", "type": "12"},
                    {"name": "IsExternal", "value": "true", "type": "1"},
                    {"name": "EntityType", "value": "27", "type": "4"},
                ]
            }
        ],
    }
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.ExtensionObject
    assert len(result.Value) == 1
    assert result.Value[0].Name == "Tool"
    assert result.Value[0].IsExternal is True
    assert result.Value[0].EntityType == 27


@pytest.fixture()
def generic_signal_type():
    """Register a generic structure used by schema-driven structure editors."""
    from asyncua.common.structures104 import make_structure

    already_registered = hasattr(ua, "IOSignalDataType")
    registry_key = ua.NodeId(49001, 3)  # type: ignore[arg-type]
    had_registry_entry = registry_key in ua.extension_objects_by_typeid
    previous_registry_value = ua.extension_objects_by_typeid.get(registry_key)
    if not already_registered:
        sdef = ua.StructureDefinition()
        sdef.StructureType = ua.StructureType.Structure
        sdef.Fields = [
            ua.StructureField(Name="SignalId", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1),  # type: ignore[arg-type]
            ua.StructureField(Name="Active", DataType=ua.NodeId(ua.ObjectIds.Boolean), ValueRank=-1),  # type: ignore[arg-type]
        ]
        make_structure(ua.NodeId(49001, 3), "IOSignalDataType", sdef)  # type: ignore[arg-type]
    ua.extension_objects_by_typeid[registry_key] = ua.IOSignalDataType  # type: ignore[attr-defined]

    yield

    if had_registry_entry:
        if previous_registry_value is not None:
            ua.extension_objects_by_typeid[registry_key] = previous_registry_value
        else:
            ua.extension_objects_by_typeid.pop(registry_key, None)
    else:
        ua.extension_objects_by_typeid.pop(registry_key, None)
    if not already_registered and hasattr(ua, "IOSignalDataType"):
        delattr(ua, "IOSignalDataType")


def test_generic_structure_payload_happy_path(generic_signal_type):  # noqa: ARG001
    arg = {
        "dataType": 49001,
        "value": {
            "structure": "IOSignalDataType",
            "value": [
                {"name": "SignalId", "value": "I1", "type": "12"},
                {"name": "Active", "value": "true", "type": "1"},
            ],
        },
    }
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.ExtensionObject
    assert result.Value.SignalId == "I1"
    assert result.Value.Active is True


def test_generic_structure_array_payload_happy_path(generic_signal_type):  # noqa: ARG001
    arg = {
        "dataType": 49001,
        "value": [
            {
                "structure": "IOSignalDataType",
                "value": [
                    {"name": "SignalId", "value": "I1", "type": "12"},
                    {"name": "Active", "value": "true", "type": "1"},
                ],
            },
            {
                "structure": "IOSignalDataType",
                "value": [
                    {"name": "SignalId", "value": "I2", "type": "12"},
                    {"name": "Active", "value": False, "type": "1"},
                ],
            },
        ],
    }
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.ExtensionObject
    assert len(result.Value) == 2
    assert result.Value[0].SignalId == "I1"
    assert result.Value[1].Active is False


def test_generic_structure_payload_without_name_resolves_by_datatype(generic_signal_type):  # noqa: ARG001
    arg = {
        "dataType": 49001,
        "dataTypeNamespaceIndex": 3,
        "value": {
            "value": [
                {"name": "SignalId", "value": "I3", "type": "12"},
                {"name": "Active", "value": "true", "type": "1"},
            ],
        },
    }
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.ExtensionObject
    assert result.Value.SignalId == "I3"
    assert result.Value.Active is True


def test_generic_structure_field_list_payload_is_accepted(generic_signal_type):  # noqa: ARG001
    arg = {
        "dataType": 49001,
        "dataTypeNamespaceIndex": 3,
        "dataTypeName": "IOSignalDataType",
        "value": [
            {"name": "SignalId", "value": "I4", "type": "12"},
            {"name": "Active", "value": "true", "type": "1"},
        ],
    }
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.ExtensionObject
    assert result.Value.SignalId == "I4"
    assert result.Value.Active is True


@pytest.fixture()
def signal_data_type_with_variant():
    from asyncua.common.structures104 import make_structure

    already_registered = hasattr(ua, "SignalDataType")
    registry_key = ua.NodeId(3019, 7)  # type: ignore[arg-type]
    had_registry_entry = registry_key in ua.extension_objects_by_typeid
    previous_registry_value = ua.extension_objects_by_typeid.get(registry_key)
    if not already_registered:
        sdef = ua.StructureDefinition()
        sdef.StructureType = ua.StructureType.Structure
        sdef.Fields = [
            ua.StructureField(Name="SignalId", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1),  # type: ignore[arg-type]
            ua.StructureField(Name="SignalValue", DataType=ua.NodeId(26), ValueRank=-1),  # type: ignore[arg-type]
            ua.StructureField(Name="SignalDescription", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1),  # type: ignore[arg-type]
            ua.StructureField(Name="SignalType", DataType=ua.NodeId(ua.ObjectIds.Int16), ValueRank=-1),  # type: ignore[arg-type]
        ]
        make_structure(ua.NodeId(3019, 7), "SignalDataType", sdef)  # type: ignore[arg-type]
    ua.extension_objects_by_typeid[registry_key] = ua.SignalDataType  # type: ignore[attr-defined]

    yield

    if had_registry_entry:
        if previous_registry_value is not None:
            ua.extension_objects_by_typeid[registry_key] = previous_registry_value
        else:
            ua.extension_objects_by_typeid.pop(registry_key, None)
    else:
        ua.extension_objects_by_typeid.pop(registry_key, None)
    if not already_registered and hasattr(ua, "SignalDataType"):
        delattr(ua, "SignalDataType")


@pytest.fixture()
def joint_data_type_with_associated_entities():
    class JointDataType:  # local lightweight stand-in for test-only structure registration
        def __init__(self):
            self.JointId = ""
            self.AssociatedEntities = []

    already_registered = hasattr(ua, "JointDataType")
    previous_class = getattr(ua, "JointDataType", None)
    registry_key = ua.NodeId(3028, 7)  # type: ignore[arg-type]
    had_registry_entry = registry_key in ua.extension_objects_by_typeid
    previous_registry_value = ua.extension_objects_by_typeid.get(registry_key)
    setattr(ua, "JointDataType", JointDataType)
    ua.extension_objects_by_typeid[registry_key] = JointDataType

    yield

    if had_registry_entry:
        if previous_registry_value is not None:
            ua.extension_objects_by_typeid[registry_key] = previous_registry_value
        else:
            ua.extension_objects_by_typeid.pop(registry_key, None)
    else:
        ua.extension_objects_by_typeid.pop(registry_key, None)
    if already_registered and previous_class is not None:
        setattr(ua, "JointDataType", previous_class)
    elif hasattr(ua, "JointDataType"):
        delattr(ua, "JointDataType")


def test_signal_data_type_variant_field_casting(signal_data_type_with_variant):  # noqa: ARG001
    arg = {
        "dataType": 3019,
        "dataTypeNamespaceIndex": 7,
        "value": [
            {
                "value": [
                    {"name": "SignalId", "value": "Signal-A", "type": "31918"},
                    {"name": "SignalValue", "value": "1", "type": "26"},
                    {"name": "SignalDescription", "value": "Desc", "type": "12"},
                    {"name": "SignalType", "value": "2", "type": "4"},
                ]
            }
        ],
    }
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.ExtensionObject
    assert result.Value[0].SignalId == "Signal-A"
    assert isinstance(result.Value[0].SignalValue, ua.Variant)
    assert result.Value[0].SignalValue.Value == 1
    assert result.Value[0].SignalType == 2


def test_joint_data_type_nested_entities_are_cast_to_entity_datatype(
    ijt_entity_type, joint_data_type_with_associated_entities
):  # noqa: ARG001
    arg = {
        "dataType": 3028,
        "dataTypeNamespaceIndex": 7,
        "value": {
            "value": [
                {"name": "JointId", "value": "Joint_9", "type": "31918"},
                {
                    "name": "AssociatedEntities",
                    "type": "3010",
                    "value": [
                        {
                            "value": {
                                "Name": "VIN",
                                "Description": "Vehicle identifier",
                                "EntityId": "ABCDid000011",
                                "EntityOriginId": "-",
                                "IsExternal": True,
                                "EntityType": 20,
                            }
                        }
                    ],
                },
            ]
        },
    }
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.ExtensionObject
    assert result.Value.JointId == "Joint_9"
    assert isinstance(result.Value.AssociatedEntities, list)
    assert result.Value.AssociatedEntities[0].EntityId == "ABCDid000011"
    assert result.Value.AssociatedEntities[0].EntityType == 20


@pytest.mark.parametrize(
    ("raw_value", "raw_type", "expected"),
    [
        (None, 4, 0),
        ("", 10, 0.0),
        ("7", 7, 7),
        ("2.5", 11, 2.5),
        ("abc", 4, "abc"),
        ("abc", 11, "abc"),
    ],
)
def test_cast_structure_field_value_numeric_paths(raw_value, raw_type, expected):
    assert _cast_structure_field_value(raw_value, raw_type) == expected


def test_cast_structure_field_value_datetime_and_localizedtext_paths():
    dt = datetime.datetime.now(datetime.UTC)
    assert _cast_structure_field_value(dt, 13) is dt

    parsed = _cast_structure_field_value("2026-08-17T12:30:00Z", 13)
    assert hasattr(parsed, "year")
    assert parsed.tzinfo is None

    fallback = _cast_structure_field_value("not-a-date", 13)
    assert hasattr(fallback, "year")

    localized = ua.LocalizedText(Text="X", Locale="en")
    assert _cast_structure_field_value(localized, 21) is localized

    from_dict = _cast_structure_field_value({"Text": "ABC", "Locale": "de"}, 21)
    assert isinstance(from_dict, ua.LocalizedText)
    assert from_dict.Text == "ABC"
    assert from_dict.Locale == "de"

    from_scalar = _cast_structure_field_value("DEF", 21)
    assert isinstance(from_scalar, ua.LocalizedText)
    assert from_scalar.Text == "DEF"


def test_cast_structure_field_value_variant_and_bool_paths():
    variant_bool = _cast_structure_field_value("true", 26)
    assert isinstance(variant_bool, ua.Variant)
    assert variant_bool.Value is True

    variant_int = _cast_structure_field_value("12", 26)
    assert isinstance(variant_int, ua.Variant)
    assert variant_int.Value == 12

    variant_float = _cast_structure_field_value("1.5", 26)
    assert isinstance(variant_float, ua.Variant)
    assert variant_float.Value == 1.5

    variant_raw = _cast_structure_field_value(["x"], 26)
    assert isinstance(variant_raw, ua.Variant)
    assert variant_raw.Value == ["x"]

    assert _cast_structure_field_value("false", 1) is False
    assert _cast_structure_field_value([], _ENTITY_DATA_TYPE_ARRAY) == []
    assert _cast_structure_field_value("raw", _ENTITY_DATA_TYPE_ARRAY) == "raw"


def test_field_entry_mapping_and_extraction_helpers_cover_invalid_rows():
    mapped = _field_entries_to_object(
        [
            {"name": "SignalId", "value": "I1", "type": "12"},
            {"name": "", "value": "ignored", "type": "12"},
            "not-a-dict",
        ]
    )
    assert mapped == {"SignalId": "I1"}
    assert _coerce_int("NaN", fallback=9) == 9

    value_rows = [{"name": "A", "value": "x"}]
    assert _extract_named_or_positional_field(value_rows, "A", 0) == "x"
    assert _extract_named_or_positional_field([], "Missing", 3) == ""


def test_resolve_structure_class_handles_lookup_failures_and_registry_fallback(monkeypatch):
    class DummyStructure:
        pass

    class FakeNode:
        def __init__(self, identifier, namespace):
            self.Identifier = identifier
            self.NamespaceIndex = namespace

    monkeypatch.setattr(ua, "DummyStructure", DummyStructure, raising=False)
    assert _resolve_structure_class(49001, 3, "DummyStructure") is DummyStructure

    monkeypatch.delattr(ua, "DummyStructure", raising=False)
    monkeypatch.setattr(ua, "get_extensionobject_class_type", lambda _node_id: None, raising=False)
    monkeypatch.setattr(ua, "extension_objects_by_datatype", {FakeNode("49001", "3"): DummyStructure}, raising=False)
    monkeypatch.setattr(ua, "extension_objects_by_typeid", {}, raising=False)
    assert _resolve_structure_class(49001, 3, "") is DummyStructure

    monkeypatch.setattr(ua, "extension_objects_by_datatype", {}, raising=False)
    monkeypatch.setattr(ua, "extension_objects_by_typeid", {FakeNode("49002", "4"): DummyStructure}, raising=False)
    assert _resolve_structure_class(49002, 4, "") is DummyStructure

    monkeypatch.setattr(
        ua, "get_extensionobject_class_type", lambda _node_id: (_ for _ in ()).throw(RuntimeError("x")), raising=False
    )
    monkeypatch.setattr(ua, "extension_objects_by_datatype", {}, raising=False)
    monkeypatch.setattr(ua, "extension_objects_by_typeid", {}, raising=False)
    assert _resolve_structure_class("not-int", 4, "") is None
    assert _resolve_structure_class(49003, "not-int", "") is None
    assert _resolve_structure_class(49003, 4, "") is None


def test_build_extension_object_failure_paths_are_null_safe():
    assert _build_extension_object(None, "MissingType", [{"name": "A", "value": "x", "type": "12"}]) is None

    class BrokenInit:
        def __init__(self):
            raise RuntimeError("init failed")

    assert _build_extension_object(BrokenInit, "BrokenInit", [{"name": "A", "value": "x", "type": "12"}]) is None

    class SlotOnly:
        __slots__ = ("Allowed",)

    obj = _build_extension_object(SlotOnly, "SlotOnly", ["not-a-dict", {"value": "missing-name"}])
    assert isinstance(obj, SlotOnly)

    assert _build_extension_object(SlotOnly, "SlotOnly", [{"name": "Forbidden", "value": "x", "type": "12"}]) is None


def test_create_call_structure_returns_null_variant_when_extension_build_fails():
    result_from_object = create_call_structure(
        {"dataType": 49901, "dataTypeNamespaceIndex": 3, "value": {"structure": "Nope", "value": [{"name": "A"}]}}
    )
    assert isinstance(result_from_object, ua.Variant)
    assert result_from_object.VariantType is ua.VariantType.Null

    result_from_field_list = create_call_structure(
        {"dataType": 49902, "dataTypeNamespaceIndex": 3, "dataTypeName": "Nope", "value": [{"name": "A"}]}
    )
    assert isinstance(result_from_field_list, ua.Variant)
    assert result_from_field_list.VariantType is ua.VariantType.Null

    result_from_array = create_call_structure(
        {
            "dataType": 49903,
            "dataTypeNamespaceIndex": 3,
            "value": [{"structure": "Nope", "value": [{"name": "A"}]}],
        }
    )
    assert isinstance(result_from_array, ua.Variant)
    assert result_from_array.VariantType is ua.VariantType.Null


def test_remaining_scalar_helper_paths_are_covered():
    sentinel = object()
    assert _cast_structure_field_value(sentinel, "not-a-number") is sentinel
    assert _cast_structure_field_value("2026-08-17T12:30:00", 13).tzinfo is None
    assert _cast_structure_field_value("", 13).tzinfo is None

    variant = ua.Variant("keep")
    assert _cast_structure_field_value(variant, 26) is variant
    assert _cast_structure_field_value("x", 9999) == "x"
    assert _cast_structure_field_value("TRUE", 1) is True


def test_try_coerce_int_and_entity_array_invalid_rows_are_safe(ijt_entity_type):  # noqa: ARG001
    assert _try_coerce_int(None) is None
    assert _try_coerce_int("bad-int") is None
    assert _try_coerce_int("12") == 12

    arg = {
        "dataType": 3010,
        "value": [
            {
                "Name": "A",
                "Description": "",
                "EntityId": "1",
                "EntityOriginId": "o",
                "IsExternal": False,
                "EntityType": 1,
            },
            123,
        ],
    }
    result = create_call_structure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.ExtensionObject
    assert len(result.Value) == 1


def test_resolve_structure_class_namespace_mismatch_and_second_registry_loop(monkeypatch):
    class DummyStructure:
        pass

    class FakeNode:
        def __init__(self, identifier, namespace):
            self.Identifier = identifier
            self.NamespaceIndex = namespace

    monkeypatch.setattr(ua, "get_extensionobject_class_type", lambda _node_id: None, raising=False)
    monkeypatch.setattr(ua, "extension_objects_by_datatype", {FakeNode(49010, 99): DummyStructure}, raising=False)
    monkeypatch.setattr(ua, "extension_objects_by_typeid", {FakeNode(49010, 3): DummyStructure}, raising=False)
    assert _resolve_structure_class(49010, 3, "") is DummyStructure


def test_coerce_bool_and_second_typeid_registry_pass_handle_nonstandard_inputs(monkeypatch):
    class DummyStructure:
        pass

    class FakeNode:
        Identifier = 49011
        NamespaceIndex = 3

    class DelayedTypeIdRegistry:
        def __init__(self):
            self.calls = 0

        def items(self):
            self.calls += 1
            return () if self.calls == 1 else ((FakeNode(), DummyStructure),)

    registry = DelayedTypeIdRegistry()
    monkeypatch.setattr(ua, "get_extensionobject_class_type", lambda _node_id: None, raising=False)
    monkeypatch.setattr(ua, "extension_objects_by_datatype", {}, raising=False)
    monkeypatch.setattr(ua, "extension_objects_by_typeid", registry, raising=False)

    assert _coerce_bool(" TRUE ") is True
    assert _coerce_bool("false") is False
    assert _resolve_structure_class(49011, 3, "") is DummyStructure
    assert registry.calls == 2


def test_second_typeid_registry_pass_ignores_a_matching_type_in_another_namespace(monkeypatch):
    class FakeNode:
        Identifier = 49012
        NamespaceIndex = 99

    class DelayedTypeIdRegistry:
        def __init__(self):
            self.calls = 0

        def items(self):
            self.calls += 1
            return () if self.calls == 1 else ((FakeNode(), object),)

    monkeypatch.setattr(ua, "get_extensionobject_class_type", lambda _node_id: None, raising=False)
    monkeypatch.setattr(ua, "extension_objects_by_datatype", {}, raising=False)
    monkeypatch.setattr(ua, "extension_objects_by_typeid", DelayedTypeIdRegistry(), raising=False)

    assert _resolve_structure_class(49012, 3, "") is None
