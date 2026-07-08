"""
Unit tests for helpers/cu_evidence_map.py

Tests data-driven CU evidence metadata mapping without any OPC UA server.
"""

from __future__ import annotations

import pytest

from helpers.cu_evidence_map import (
    CuEvidenceMeta,
    all_registered_cu_keys,
    cu_evidence_meta,
    cus_by_evidence_kind,
    is_manual_only,
    is_state_changing,
    valid_evidence_kinds,
)
from helpers.cu_registry import CU

# ---------------------------------------------------------------------------
# valid_evidence_kinds
# ---------------------------------------------------------------------------


class TestValidEvidenceKinds:
    def test_returns_frozenset(self):
        kinds = valid_evidence_kinds()
        assert isinstance(kinds, frozenset)

    def test_contains_expected_kinds(self):
        kinds = valid_evidence_kinds()
        for expected in [
            "structure",
            "method",
            "result",
            "consolidated_result",
            "event",
            "condition",
            "workflow",
            "optional_operation",
            "negative_path",
            "manual",
        ]:
            assert expected in kinds, f"Expected kind '{expected}' not in valid_evidence_kinds()"


# ---------------------------------------------------------------------------
# CuEvidenceMeta validation
# ---------------------------------------------------------------------------


class TestCuEvidenceMetaValidation:
    def test_valid_kind_accepted(self):
        meta = CuEvidenceMeta(cu_key="some_cu", evidence_kind="structure")
        assert meta.cu_key == "some_cu"
        assert meta.evidence_kind == "structure"

    def test_invalid_kind_raises(self):
        with pytest.raises(ValueError, match="Invalid evidence_kind"):
            CuEvidenceMeta(cu_key="x", evidence_kind="unknown_kind")

    def test_defaults(self):
        meta = CuEvidenceMeta(cu_key="x", evidence_kind="method")
        assert meta.state_changing is False
        assert meta.manual_only is False
        assert meta.notes == ""

    def test_state_changing_flag(self):
        meta = CuEvidenceMeta(cu_key="y", evidence_kind="method", state_changing=True)
        assert meta.state_changing is True

    def test_manual_only_flag(self):
        meta = CuEvidenceMeta(cu_key="z", evidence_kind="manual", manual_only=True)
        assert meta.manual_only is True

    def test_frozen(self):
        meta = CuEvidenceMeta(cu_key="x", evidence_kind="structure")
        with pytest.raises((AttributeError, TypeError)):
            meta.cu_key = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# cu_evidence_meta lookup
# ---------------------------------------------------------------------------


class TestCuEvidenceMeta:
    def test_returns_meta_for_known_cu(self):
        meta = cu_evidence_meta(CU.JOINING_SYSTEM_BASE)
        assert meta.cu_key == CU.JOINING_SYSTEM_BASE
        assert meta.evidence_kind == "structure"

    def test_single_result_is_result_kind(self):
        meta = cu_evidence_meta(CU.SINGLE_RESULT)
        assert meta.evidence_kind == "result"

    def test_start_selected_joining_is_workflow(self):
        meta = cu_evidence_meta(CU.START_SELECTED_JOINING)
        assert meta.evidence_kind == "workflow"
        assert meta.state_changing is True

    def test_batch_result_is_consolidated(self):
        meta = cu_evidence_meta(CU.BATCH_RESULT)
        assert meta.evidence_kind == "consolidated_result"

    def test_event_payload_is_event(self):
        meta = cu_evidence_meta(CU.EVENT_PAYLOAD)
        assert meta.evidence_kind == "event"

    def test_asset_connection_event_is_manual(self):
        meta = cu_evidence_meta(CU.ASSET_CONNECTION_EVENT)
        assert meta.manual_only is True

    def test_delete_joint_is_negative_path(self):
        meta = cu_evidence_meta(CU.DELETE_JOINT)
        assert meta.evidence_kind == "negative_path"
        assert meta.state_changing is True

    def test_acknowledge_results_is_state_changing(self):
        meta = cu_evidence_meta(CU.ACKNOWLEDGE_RESULTS)
        assert meta.state_changing is True

    def test_unknown_cu_returns_safe_default(self):
        meta = cu_evidence_meta("totally_unknown_cu_key")
        assert meta.cu_key == "totally_unknown_cu_key"
        assert meta.evidence_kind == "structure"
        assert meta.state_changing is False
        assert meta.manual_only is False

    def test_get_identifiers_is_method_not_state_changing(self):
        meta = cu_evidence_meta(CU.GET_IDENTIFIERS)
        assert meta.evidence_kind == "method"
        assert meta.state_changing is False

    def test_send_identifiers_is_state_changing(self):
        meta = cu_evidence_meta(CU.SEND_IDENTIFIERS)
        assert meta.state_changing is True

    def test_joining_system_base_not_state_changing(self):
        meta = cu_evidence_meta(CU.JOINING_SYSTEM_BASE)
        assert meta.state_changing is False
        assert meta.manual_only is False


# ---------------------------------------------------------------------------
# cus_by_evidence_kind
# ---------------------------------------------------------------------------


class TestCusByEvidenceKind:
    def test_structure_includes_joining_system(self):
        cus = cus_by_evidence_kind("structure")
        assert CU.JOINING_SYSTEM_BASE in cus
        assert CU.ASSET_MANAGEMENT_TOOL in cus

    def test_result_includes_single_result(self):
        cus = cus_by_evidence_kind("result")
        assert CU.SINGLE_RESULT in cus
        assert CU.BASIC_RESULT in cus

    def test_consolidated_result_includes_batch(self):
        cus = cus_by_evidence_kind("consolidated_result")
        assert CU.BATCH_RESULT in cus
        assert CU.JOB_RESULT in cus

    def test_workflow_includes_start_selected_joining(self):
        cus = cus_by_evidence_kind("workflow")
        assert CU.START_SELECTED_JOINING in cus

    def test_event_includes_event_payload(self):
        cus = cus_by_evidence_kind("event")
        assert CU.EVENT_PAYLOAD in cus

    def test_unknown_kind_returns_empty(self):
        cus = cus_by_evidence_kind("nonexistent_kind")
        assert cus == frozenset()

    def test_all_returned_sets_are_frozensets(self):
        for kind in valid_evidence_kinds():
            cus = cus_by_evidence_kind(kind)
            assert isinstance(cus, frozenset), f"Expected frozenset for kind '{kind}'"

    def test_negative_path_includes_delete_cus(self):
        cus = cus_by_evidence_kind("negative_path")
        assert CU.DELETE_JOINT in cus
        assert CU.DELETE_JOINING_PROCESS in cus

    def test_manual_includes_asset_connection_events(self):
        cus = cus_by_evidence_kind("manual")
        assert CU.ASSET_CONNECTION_EVENT in cus


# ---------------------------------------------------------------------------
# is_state_changing / is_manual_only helpers
# ---------------------------------------------------------------------------


class TestConvenienceHelpers:
    def test_is_state_changing_true(self):
        assert is_state_changing(CU.SELECT_JOINING_PROCESS) is True

    def test_is_state_changing_false(self):
        assert is_state_changing(CU.JOINING_SYSTEM_BASE) is False

    def test_is_state_changing_unknown_key_defaults_false(self):
        assert is_state_changing("not_a_real_cu") is False

    def test_is_manual_only_true(self):
        assert is_manual_only(CU.ASSET_CONNECTION_EVENT) is True

    def test_is_manual_only_false(self):
        assert is_manual_only(CU.SINGLE_RESULT) is False

    def test_is_manual_only_unknown_defaults_false(self):
        assert is_manual_only("not_a_real_cu") is False


# ---------------------------------------------------------------------------
# all_registered_cu_keys
# ---------------------------------------------------------------------------


class TestAllRegisteredCuKeys:
    def test_returns_frozenset(self):
        keys = all_registered_cu_keys()
        assert isinstance(keys, frozenset)

    def test_includes_core_cus(self):
        keys = all_registered_cu_keys()
        assert CU.JOINING_SYSTEM_BASE in keys
        assert CU.SINGLE_RESULT in keys
        assert CU.START_SELECTED_JOINING in keys
        assert CU.EVENT_PAYLOAD in keys

    def test_count_reasonable(self):
        # Should have at least 50 registered CUs (currently ~120+)
        keys = all_registered_cu_keys()
        assert len(keys) >= 50, f"Expected at least 50 registered CUs, got {len(keys)}"

    def test_no_empty_keys(self):
        for key in all_registered_cu_keys():
            assert key, "Empty key found in registered CU keys"

    def test_all_evidence_kinds_covered(self):
        """Ensure every valid evidence kind has at least one CU registered."""
        for kind in valid_evidence_kinds():
            cus = cus_by_evidence_kind(kind)
            assert len(cus) > 0, f"No CUs registered for evidence kind '{kind}'"
