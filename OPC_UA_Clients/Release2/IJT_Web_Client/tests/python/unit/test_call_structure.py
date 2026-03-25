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
asyncua = pytest.importorskip("asyncua", reason="asyncua not installed")
from asyncua import ua  # noqa: E402

from Python.call_structure import (  # noqa: E402
    _BUILTIN_TYPE_MAP,
    _ENTITY_DATA_TYPE_ARRAY,
    _JOINING_PROCESS_ID_DATA_TYPE,
    createCallStructure,
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
# createCallStructure — builtin type round-trip
# ---------------------------------------------------------------------------


def test_create_call_structure_string_type():
    arg = {"dataType": 12, "value": "hello"}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.String
    assert result.Value == "hello"


def test_create_call_structure_int32_type():
    arg = {"dataType": 6, "value": 42}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Int32
    assert result.Value == 42


def test_create_call_structure_float_type():
    arg = {"dataType": 10, "value": 3.14}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Float


def test_create_call_structure_double_type():
    arg = {"dataType": 11, "value": 2.718}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Double


def test_create_call_structure_boolean_type():
    arg = {"dataType": 1, "value": True}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Boolean
    assert result.Value is True


def test_create_call_structure_uint32_type():
    arg = {"dataType": 7, "value": 100}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.UInt32


def test_create_call_structure_int16_type():
    arg = {"dataType": 4, "value": -500}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Int16


def test_create_call_structure_uint16_type():
    arg = {"dataType": 5, "value": 500}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.UInt16


def test_create_call_structure_int64_type():
    arg = {"dataType": 8, "value": 9999999999}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Int64


def test_create_call_structure_uint64_type():
    arg = {"dataType": 9, "value": 9999999999}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.UInt64


def test_create_call_structure_sbyte_type():
    arg = {"dataType": 2, "value": -10}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.SByte


def test_create_call_structure_byte_type():
    arg = {"dataType": 3, "value": 255}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Byte


def test_create_call_structure_trimmed_string():
    arg = {"dataType": 31918, "value": "trimmed"}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.String
    assert result.Value == "trimmed"


# ---------------------------------------------------------------------------
# createCallStructure — unknown type falls back to String
# ---------------------------------------------------------------------------


def test_create_call_structure_unknown_type_falls_back_to_string():
    arg = {"dataType": 99999, "value": "some_value"}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.String
    assert result.Value == "some_value"


def test_create_call_structure_zero_type_falls_back_to_string():
    """Type ID 0 is not a valid OPC UA built-in type; should fall back gracefully."""
    arg = {"dataType": 0, "value": "x"}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.String


# ---------------------------------------------------------------------------
# createCallStructure — type 3029 guard checks (no NodeSet needed)
# ---------------------------------------------------------------------------


def test_joining_process_type_with_non_list_returns_null():
    arg = {"dataType": 3029, "value": "not_a_list"}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Null


def test_joining_process_type_with_empty_list_returns_null():
    arg = {"dataType": 3029, "value": []}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Null


def test_joining_process_type_with_two_elements_returns_null():
    """Must have exactly 3 elements: JoiningProcessId, JoiningProcessOriginId, SelectionName."""
    arg = {"dataType": 3029, "value": [{"value": "a"}, {"value": "b"}]}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Null


def test_joining_process_type_with_none_returns_null():
    arg = {"dataType": 3029, "value": None}
    result = createCallStructure(arg)
    assert isinstance(result, ua.Variant)
    assert result.VariantType is ua.VariantType.Null


# ---------------------------------------------------------------------------
# createCallStructure — type 3029 happy path (requires IJT NodeSet on server)
# ---------------------------------------------------------------------------


def test_joining_process_type_happy_path_requires_ijt_nodeset():
    """
    This test verifies the happy path for type 3029 if the IJT NodeSet extension types
    are available. It is skipped if ua.JoiningProcessIdentificationDataType is not defined
    (i.e., when not connected to or loaded from an IJT server NodeSet).
    """
    if not hasattr(ua, "JoiningProcessIdentificationDataType"):
        pytest.skip("IJT NodeSet extension types not loaded (requires server NodeSet import)")

    arg = {
        "dataType": 3029,
        "value": [
            {"value": "proc-001"},
            {"value": "origin-001"},
            {"value": "selection-A"},
        ],
    }
    result = createCallStructure(arg)
    assert isinstance(result, ua.JoiningProcessIdentificationDataType)
    assert result.JoiningProcessId == "proc-001"
    assert result.JoiningProcessOriginId == "origin-001"
    assert result.SelectionName == "selection-A"
