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

import pytest

# Import asyncua first to skip the whole module if the library is not installed.
_ = pytest.importorskip("asyncua", reason="asyncua not installed")
from asyncua import ua  # noqa: E402

from python.call_structure import (  # noqa: E402
    _BUILTIN_TYPE_MAP,
    _ENTITY_DATA_TYPE_ARRAY,
    _JOINING_PROCESS_ID_DATA_TYPE,
    create_call_structure,
)


# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------


def test_named_constants_have_correct_values():
    assert _JOINING_PROCESS_ID_DATA_TYPE == 3029
    assert _ENTITY_DATA_TYPE_ARRAY == 3010


# ---------------------------------------------------------------------------
# _BUILTIN_TYPE_MAP completeness and correctness (OPC UA Part 6 Table 1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "type_id, expected",
    [
        (1,  ua.VariantType.Boolean),
        (2,  ua.VariantType.SByte),
        (3,  ua.VariantType.Byte),
        (4,  ua.VariantType.Int16),
        (5,  ua.VariantType.UInt16),
        (6,  ua.VariantType.Int32),
        (7,  ua.VariantType.UInt32),
        (8,  ua.VariantType.Int64),
        (9,  ua.VariantType.UInt64),
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
    assert numeric_keys == set(range(1, 14)), (
        f"Unexpected or missing numeric keys: {numeric_keys}"
    )


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
            ua.StructureField(Name="JoiningProcessId", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1),
            ua.StructureField(Name="JoiningProcessOriginId", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1),
            ua.StructureField(Name="SelectionName", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1),
        ]
        make_structure(ua.NodeId(3029, 4), "JoiningProcessIdentificationDataType", sdef)

    yield

    if not already_registered and hasattr(ua, "JoiningProcessIdentificationDataType"):
        delattr(ua, "JoiningProcessIdentificationDataType")


def test_joining_process_type_happy_path(ijt_nodeset_types):
    """Verifies the happy path for type 3029 (JoiningProcessIdentificationDataType).

    The ``ijt_nodeset_types`` fixture registers the struct via asyncua's
    standard ``make_structure`` API — the same path taken when a live server
    loads its type dictionary — so this test exercises real production behaviour
    without requiring a running OPC UA server.
    """
    arg = {
        "dataType": 3029,
        "value": [
            {"value": "proc-001"},
            {"value": "origin-001"},
            {"value": "selection-A"},
        ],
    }
    result = create_call_structure(arg)
    assert isinstance(result, ua.JoiningProcessIdentificationDataType)
    assert result.JoiningProcessId == "proc-001"
    assert result.JoiningProcessOriginId == "origin-001"
    assert result.SelectionName == "selection-A"
