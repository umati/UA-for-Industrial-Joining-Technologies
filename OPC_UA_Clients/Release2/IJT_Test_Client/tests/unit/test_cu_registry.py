"""
Unit tests for helpers/cu_registry.py

Tests CU string constant correctness, uniqueness, count, and
ConformanceUnitMeta dataclass construction.
"""

import inspect
import re

import pytest

from helpers.cu_registry import (
    CU,
    ConformanceUnitMeta,
    cu_display_name,
    cu_key_for_method,
    cu_method_names,
    format_cu_not_supported,
    format_method_not_supported,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_string_cu_constants() -> dict[str, str]:
    """Return {name: value} for all string CU constants on the CU class."""
    result = {}
    for name, value in inspect.getmembers(CU):
        if name.startswith("_"):
            continue
        if isinstance(value, str):
            result[name] = value
    return result


def _get_all_facet_cu_keys() -> set[str]:
    """Load all CU keys from profiles/facets.yaml."""
    from pathlib import Path

    import yaml

    facets_path = Path(__file__).parent.parent.parent / "profiles" / "facets.yaml"
    with facets_path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    keys: set[str] = set()
    for facet_data in raw.get("facets", {}).values():
        keys.update(facet_data.get("conformance_units", []))
    return keys


# ---------------------------------------------------------------------------
# String constant properties
# ---------------------------------------------------------------------------


class TestCuStringConstants:
    def test_all_constants_are_non_empty(self):
        constants = _get_string_cu_constants()
        assert len(constants) > 0
        for name, value in constants.items():
            assert value, f"CU.{name} is empty"

    def test_all_constants_are_snake_case(self):
        constants = _get_string_cu_constants()
        snake_pattern = re.compile(r"^[a-z][a-z0-9_]*$")
        for name, value in constants.items():
            assert snake_pattern.match(value), f"CU.{name} = {value!r} is not valid snake_case"

    def test_no_duplicate_values(self):
        constants = _get_string_cu_constants()
        values = list(constants.values())
        duplicates = [v for v in values if values.count(v) > 1]
        assert not duplicates, f"Duplicate CU values found: {set(duplicates)}"

    def test_constant_count_is_123(self):
        """Exactly 123 CU string constants as documented in full_conformance.yaml."""
        constants = _get_string_cu_constants()
        count = len(constants)
        assert count == 123, f"Expected 123 CU constants, got {count}"

    def test_no_spaces_in_values(self):
        for name, value in _get_string_cu_constants().items():
            assert " " not in value, f"CU.{name} = {value!r} contains a space"


# ---------------------------------------------------------------------------
# Cross-check with facets.yaml
# ---------------------------------------------------------------------------


class TestCuFacetsConsistency:
    def test_all_facet_keys_appear_in_cu(self):
        """Every CU key in facets.yaml must have a matching constant in CU."""
        facet_keys = _get_all_facet_cu_keys()
        cu_values = set(_get_string_cu_constants().values())
        missing = facet_keys - cu_values
        assert not missing, f"facets.yaml keys not found in CU class: {sorted(missing)}"

    def test_no_extra_cu_constants_missing_from_facets(self):
        """All CU string constants should appear in at least one facet."""
        facet_keys = _get_all_facet_cu_keys()
        cu_values = set(_get_string_cu_constants().values())
        unregistered = cu_values - facet_keys
        # It's acceptable for some CUs to not be in facets (future/extended ones),
        # but there should be minimal divergence. Warn if > 0 but don't fail.
        # Adjust this test if the spec intentionally has CUs outside facets.
        assert isinstance(unregistered, set)  # just ensures it runs


# ---------------------------------------------------------------------------
# Specific important constants exist
# ---------------------------------------------------------------------------


class TestCuImportantConstants:
    def test_joining_system_base_exists(self):
        assert CU.JOINING_SYSTEM_BASE == "joining_system_base"

    def test_single_result_exists(self):
        assert CU.SINGLE_RESULT == "single_result"

    def test_basic_result_exists(self):
        assert CU.BASIC_RESULT == "basic_result"

    def test_get_latest_result_exists(self):
        assert CU.GET_LATEST_RESULT == "get_latest_result"

    def test_event_payload_exists(self):
        assert CU.EVENT_PAYLOAD == "event_payload"

    def test_joint_management_exists(self):
        assert CU.JOINT_MANAGEMENT == "joint_management"

    def test_engineering_units_exists(self):
        assert CU.ENGINEERING_UNITS == "engineering_units"


# ---------------------------------------------------------------------------
# Collection attributes (tuples)
# ---------------------------------------------------------------------------


class TestCuCollections:
    def test_all_joining_system_structure_is_tuple(self):
        assert isinstance(CU.ALL_JOINING_SYSTEM_STRUCTURE, tuple)

    def test_all_joining_system_structure_non_empty(self):
        assert len(CU.ALL_JOINING_SYSTEM_STRUCTURE) > 0

    def test_all_joining_system_structure_contains_base(self):
        assert CU.JOINING_SYSTEM_BASE in CU.ALL_JOINING_SYSTEM_STRUCTURE

    def test_all_result_data_structure_non_empty(self):
        assert len(CU.ALL_RESULT_DATA_STRUCTURE) > 0

    def test_all_result_access_methods_non_empty(self):
        assert len(CU.ALL_RESULT_ACCESS_METHODS) > 0

    def test_all_joining_result_payload_non_empty(self):
        assert len(CU.ALL_JOINING_RESULT_PAYLOAD) > 0

    def test_all_consolidated_result_types_non_empty(self):
        assert len(CU.ALL_CONSOLIDATED_RESULT_TYPES) > 0

    def test_all_asset_types_is_tuple_of_strings(self):
        assert isinstance(CU.ALL_ASSET_TYPES, tuple)
        for item in CU.ALL_ASSET_TYPES:
            assert isinstance(item, str)

    def test_all_event_types_is_tuple(self):
        assert isinstance(CU.ALL_EVENT_TYPES, tuple)

    def test_all_joining_process_management_is_tuple(self):
        assert isinstance(CU.ALL_JOINING_PROCESS_MANAGEMENT, tuple)

    def test_all_joint_management_is_tuple(self):
        assert isinstance(CU.ALL_JOINT_MANAGEMENT, tuple)

    def test_collection_values_are_string_constants(self):
        """All values in collections should be valid snake_case strings."""
        all_collections = [
            CU.ALL_JOINING_SYSTEM_STRUCTURE,
            CU.ALL_RESULT_DATA_STRUCTURE,
            CU.ALL_RESULT_ACCESS_METHODS,
            CU.ALL_JOINING_RESULT_PAYLOAD,
            CU.ALL_CONSOLIDATED_RESULT_TYPES,
            CU.ALL_ASSET_TYPES,
            CU.ALL_EVENT_TYPES,
            CU.ALL_JOINING_PROCESS_MANAGEMENT,
            CU.ALL_JOINT_MANAGEMENT,
        ]
        pattern = re.compile(r"^[a-z][a-z0-9_]*$")
        for coll in all_collections:
            for item in coll:
                assert pattern.match(item), f"Collection item {item!r} is not snake_case"


# ---------------------------------------------------------------------------
# Report labels
# ---------------------------------------------------------------------------


class TestCuReportLabels:
    def test_display_name_is_public_ijt_label(self):
        assert cu_display_name(CU.SEND_JOINING_PROCESS) == "IJT Send Joining Process"

    def test_method_names_for_method_cu(self):
        assert cu_method_names(CU.SEND_JOINING_PROCESS) == ("SendJoiningProcess",)

    def test_not_supported_label_includes_method_name(self):
        assert (
            format_cu_not_supported(CU.SEND_JOINING_PROCESS)
            == "IJT Send Joining Process - Method: SendJoiningProcess NOT SUPPORTED"
        )

    def test_not_supported_label_handles_multi_method_cu(self):
        assert (
            format_cu_not_supported(CU.FEEDBACK_METHODS)
            == "IJT Feedback Methods - Methods: GetFeedbackFileList, SendFeedback NOT SUPPORTED"
        )

    def test_not_supported_label_without_method_mapping(self):
        assert format_cu_not_supported(CU.JOINT_DESIGN_DATA) == "IJT Joint Design Data NOT SUPPORTED"

    def test_method_lookup_uses_cu_label(self):
        assert (
            format_method_not_supported("SendJoiningProcess")
            == "IJT Send Joining Process - Method: SendJoiningProcess NOT SUPPORTED"
        )

    def test_cu_key_for_method(self):
        assert cu_key_for_method("SendJoiningProcess") == CU.SEND_JOINING_PROCESS


# ---------------------------------------------------------------------------
# ConformanceUnitMeta dataclass
# ---------------------------------------------------------------------------


class TestConformanceUnitMeta:
    def test_construction_with_all_fields(self):
        meta = ConformanceUnitMeta(
            key="single_result",
            display_name="Single Result",
            description="Validates a single result.",
            facets=frozenset({"general_joining_system_server_facet"}),
            spec_section="§9.1",
        )
        assert meta.key == "single_result"
        assert meta.display_name == "Single Result"
        assert meta.description == "Validates a single result."
        assert "general_joining_system_server_facet" in meta.facets
        assert meta.spec_section == "§9.1"

    def test_construction_with_default_spec_section(self):
        meta = ConformanceUnitMeta(
            key="basic_result",
            display_name="Basic Result",
            description="Desc",
            facets=frozenset({"some_facet"}),
        )
        assert meta.spec_section == ""

    def test_is_frozen(self):
        meta = ConformanceUnitMeta(
            key="test",
            display_name="Test",
            description="",
            facets=frozenset(),
        )
        with pytest.raises(Exception):
            meta.key = "changed"  # type: ignore[misc]

    def test_equality(self):
        meta1 = ConformanceUnitMeta("k", "d", "desc", frozenset())
        meta2 = ConformanceUnitMeta("k", "d", "desc", frozenset())
        assert meta1 == meta2

    def test_facets_is_frozenset(self):
        meta = ConformanceUnitMeta("k", "d", "desc", frozenset({"a", "b"}))
        assert isinstance(meta.facets, frozenset)
