"""
Unit tests for helpers/result_validator.py

Tests all validators with pure Python objects — no OPC UA server required.
"""

import types

import pytest

from helpers.result_validator import (
    ConsolidatedResultValidator,
    ErrorInformationValidator,
    JoiningResultDataValidator,
    ResultDataValidator,
    ResultMetaDataValidator,
    ResultValueValidator,
    StepResultValidator,
    ValidationContext,
    ValidationFailure,
    ValidationResult,
    assert_result_data_valid,
    assert_result_meta_data_valid,
    assert_result_value_valid,
)

# ---------------------------------------------------------------------------
# ValidationContext
# ---------------------------------------------------------------------------


class TestValidationContext:
    def test_default_path(self):
        ctx = ValidationContext()
        assert str(ctx) == "root"

    def test_custom_path(self):
        ctx = ValidationContext("MyObject")
        assert str(ctx) == "MyObject"

    def test_child(self):
        ctx = ValidationContext("root")
        child = ctx.child("Field")
        assert str(child) == "root.Field"

    def test_index(self):
        ctx = ValidationContext("root")
        indexed = ctx.index(3)
        assert str(indexed) == "root[3]"

    def test_chained_child_and_index(self):
        ctx = ValidationContext("root")
        result = ctx.child("Items").index(0).child("Value")
        assert str(result) == "root.Items[0].Value"

    def test_nested_children(self):
        ctx = ValidationContext("A")
        deep = ctx.child("B").child("C").child("D")
        assert str(deep) == "A.B.C.D"


# ---------------------------------------------------------------------------
# ValidationFailure
# ---------------------------------------------------------------------------


class TestValidationFailure:
    def test_str_format(self):
        f = ValidationFailure(path="root.Field", message="something went wrong")
        assert str(f) == "root.Field: something went wrong"

    def test_dataclass_fields(self):
        f = ValidationFailure("p", "m")
        assert f.path == "p"
        assert f.message == "m"


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_empty_is_ok(self):
        vr = ValidationResult()
        assert vr.ok is True
        assert vr.failures == []

    def test_add_failure_makes_not_ok(self):
        vr = ValidationResult()
        vr.add("root.Field", "bad value")
        assert vr.ok is False

    def test_add_advisory_does_not_affect_ok(self):
        vr = ValidationResult()
        vr.add("root.Field#advisory", "advisory note")
        assert vr.ok is True

    def test_add_with_validation_context(self):
        vr = ValidationResult()
        ctx = ValidationContext("root")
        vr.add(ctx, "test")
        assert vr.failures[0].path == "root"

    def test_merge_imports_failures(self):
        vr1 = ValidationResult()
        vr2 = ValidationResult()
        vr1.add("a", "err1")
        vr2.add("b", "err2")
        vr1.merge(vr2)
        assert len(vr1.failures) == 2

    def test_merge_empty_has_no_effect(self):
        vr1 = ValidationResult()
        vr2 = ValidationResult()
        vr1.add("x", "err")
        vr1.merge(vr2)
        assert len(vr1.failures) == 1

    def test_assert_no_failures_passes_when_clean(self):
        vr = ValidationResult()
        vr.assert_no_failures()  # no exception

    def test_assert_no_failures_raises_on_hard_failure(self):
        vr = ValidationResult()
        vr.add("root.Field", "bad")
        with pytest.raises(AssertionError, match="1 validation failure"):
            vr.assert_no_failures()

    def test_assert_no_failures_mentions_advisory_count(self):
        vr = ValidationResult()
        vr.add("root.Field", "hard fail")
        vr.add("root.Other#advisory", "advisory note")
        with pytest.raises(AssertionError, match="advisory note"):
            vr.assert_no_failures()

    def test_assert_no_failures_skips_advisory_only(self):
        vr = ValidationResult()
        vr.add("root.Field#advisory", "advisory note")
        vr.assert_no_failures()  # must NOT raise

    def test_assert_no_advisory_issues_passes_when_clean(self):
        vr = ValidationResult()
        vr.assert_no_advisory_issues()  # no exception

    def test_assert_no_advisory_issues_raises_on_advisory(self):
        vr = ValidationResult()
        vr.add("root.Field#advisory", "this is advisory")
        with pytest.raises(AssertionError, match="1 advisory note"):
            vr.assert_no_advisory_issues()

    def test_assert_no_advisory_ignores_hard_failures(self):
        vr = ValidationResult()
        vr.add("root.Field", "hard fail")
        vr.assert_no_advisory_issues()  # no advisory, so no exception


# ---------------------------------------------------------------------------
# ResultValueValidator
# ---------------------------------------------------------------------------


class TestResultValueValidator:
    def _validate(self, obj):
        vr = ValidationResult()
        ctx = ValidationContext("val")
        ResultValueValidator().validate(obj, ctx, vr)
        return vr

    def test_valid_minimal(self):
        obj = types.SimpleNamespace(MeasuredValue=10.0)
        assert self._validate(obj).ok

    def test_measured_value_absent(self):
        obj = types.SimpleNamespace()
        vr = self._validate(obj)
        assert not vr.ok
        assert any("MeasuredValue" in str(f) for f in vr.failures)

    def test_measured_value_none_is_rejected(self):
        # None is not numeric
        obj = types.SimpleNamespace(MeasuredValue=None)
        vr = self._validate(obj)
        assert not vr.ok

    def test_measured_value_string_rejected(self):
        obj = types.SimpleNamespace(MeasuredValue="not_a_number")
        vr = self._validate(obj)
        assert not vr.ok

    def test_measured_value_int_accepted(self):
        obj = types.SimpleNamespace(MeasuredValue=42)
        assert self._validate(obj).ok

    def test_value_tag_valid_bounds(self):
        for tag in [0, 10, 20]:
            obj = types.SimpleNamespace(MeasuredValue=1.0, ValueTag=tag)
            assert self._validate(obj).ok

    def test_value_tag_invalid_high(self):
        obj = types.SimpleNamespace(MeasuredValue=1.0, ValueTag=21)
        vr = self._validate(obj)
        assert not vr.ok

    def test_value_tag_invalid_negative(self):
        obj = types.SimpleNamespace(MeasuredValue=1.0, ValueTag=-1)
        vr = self._validate(obj)
        assert not vr.ok

    def test_value_tag_invalid_type(self):
        obj = types.SimpleNamespace(MeasuredValue=1.0, ValueTag="bad")
        vr = self._validate(obj)
        assert not vr.ok

    def test_value_tag_none_skipped(self):
        obj = types.SimpleNamespace(MeasuredValue=1.0, ValueTag=None)
        assert self._validate(obj).ok

    def test_physical_quantity_valid_bounds(self):
        for qty in [0, 14, 28]:
            obj = types.SimpleNamespace(MeasuredValue=1.0, PhysicalQuantity=qty)
            assert self._validate(obj).ok

    def test_physical_quantity_invalid_high(self):
        obj = types.SimpleNamespace(MeasuredValue=1.0, PhysicalQuantity=29)
        vr = self._validate(obj)
        assert not vr.ok

    def test_physical_quantity_invalid_type(self):
        obj = types.SimpleNamespace(MeasuredValue=1.0, PhysicalQuantity="qty")
        vr = self._validate(obj)
        assert not vr.ok

    def test_violation_type_valid(self):
        for vt in [0, 1, 2, 3]:
            obj = types.SimpleNamespace(MeasuredValue=1.0, ViolationType=vt)
            assert self._validate(obj).ok

    def test_violation_type_invalid(self):
        obj = types.SimpleNamespace(MeasuredValue=1.0, ViolationType=4)
        vr = self._validate(obj)
        assert not vr.ok

    def test_violation_type_invalid_type(self):
        obj = types.SimpleNamespace(MeasuredValue=1.0, ViolationType="bad")
        vr = self._validate(obj)
        assert not vr.ok

    def test_engineering_units_with_unit_id_ok(self):
        eu = types.SimpleNamespace(UnitId=4753)
        obj = types.SimpleNamespace(MeasuredValue=1.0, EngineeringUnits=eu)
        assert self._validate(obj).ok

    def test_engineering_units_without_unit_id_fails(self):
        eu = types.SimpleNamespace()  # no UnitId
        obj = types.SimpleNamespace(MeasuredValue=1.0, EngineeringUnits=eu)
        vr = self._validate(obj)
        assert not vr.ok

    def test_engineering_units_none_skipped(self):
        obj = types.SimpleNamespace(MeasuredValue=1.0, EngineeringUnits=None)
        assert self._validate(obj).ok

    def test_all_optional_fields_valid(self):
        eu = types.SimpleNamespace(UnitId=100)
        obj = types.SimpleNamespace(
            MeasuredValue=9.5,
            ValueTag=1,
            PhysicalQuantity=5,
            ViolationType=2,
            EngineeringUnits=eu,
        )
        assert self._validate(obj).ok


# ---------------------------------------------------------------------------
# StepResultValidator
# ---------------------------------------------------------------------------


class TestStepResultValidator:
    def _validate(self, obj):
        vr = ValidationResult()
        ctx = ValidationContext("step")
        StepResultValidator().validate(obj, ctx, vr)
        return vr

    def test_valid_minimal(self):
        obj = types.SimpleNamespace(StepResultId="step-1")
        assert self._validate(obj).ok

    def test_step_result_id_absent(self):
        obj = types.SimpleNamespace()
        vr = self._validate(obj)
        assert not vr.ok

    def test_step_result_id_empty_string(self):
        obj = types.SimpleNamespace(StepResultId="")
        vr = self._validate(obj)
        assert not vr.ok

    def test_step_result_id_whitespace_only(self):
        obj = types.SimpleNamespace(StepResultId="   ")
        vr = self._validate(obj)
        assert not vr.ok

    def test_step_result_id_non_string(self):
        obj = types.SimpleNamespace(StepResultId=123)
        vr = self._validate(obj)
        assert not vr.ok

    def test_step_result_values_empty_list_ok(self):
        obj = types.SimpleNamespace(StepResultId="s1", StepResultValues=[])
        assert self._validate(obj).ok

    def test_step_result_values_with_valid_entry(self):
        val = types.SimpleNamespace(MeasuredValue=5.0)
        obj = types.SimpleNamespace(StepResultId="s1", StepResultValues=[val])
        assert self._validate(obj).ok

    def test_step_result_values_with_invalid_entry(self):
        val = types.SimpleNamespace()  # missing MeasuredValue
        obj = types.SimpleNamespace(StepResultId="s1", StepResultValues=[val])
        vr = self._validate(obj)
        assert not vr.ok

    def test_step_result_values_not_list(self):
        obj = types.SimpleNamespace(StepResultId="s1", StepResultValues="bad")
        vr = self._validate(obj)
        assert not vr.ok

    def test_step_result_values_none_skipped(self):
        obj = types.SimpleNamespace(StepResultId="s1", StepResultValues=None)
        assert self._validate(obj).ok


# ---------------------------------------------------------------------------
# ErrorInformationValidator
# ---------------------------------------------------------------------------


class TestErrorInformationValidator:
    def _validate(self, obj):
        vr = ValidationResult()
        ctx = ValidationContext("err")
        ErrorInformationValidator().validate(obj, ctx, vr)
        return vr

    def test_valid_minimal(self):
        obj = types.SimpleNamespace(ErrorType=4)
        assert self._validate(obj).ok

    def test_error_type_absent(self):
        obj = types.SimpleNamespace()
        vr = self._validate(obj)
        assert not vr.ok

    def test_error_type_invalid_high(self):
        obj = types.SimpleNamespace(ErrorType=7)
        vr = self._validate(obj)
        assert not vr.ok

    def test_error_type_negative(self):
        obj = types.SimpleNamespace(ErrorType=-1)
        vr = self._validate(obj)
        assert not vr.ok

    def test_error_type_invalid_type(self):
        obj = types.SimpleNamespace(ErrorType="bad")
        vr = self._validate(obj)
        assert not vr.ok

    def test_all_valid_error_types(self):
        for error_type in range(7):
            obj = types.SimpleNamespace(ErrorType=error_type)
            assert self._validate(obj).ok

    def test_optional_legacy_error_fields_do_not_fail(self):
        obj = types.SimpleNamespace(ErrorType=4, ErrorId="ERR-001", LegacyError="42", ErrorMessage=object())
        assert self._validate(obj).ok


# ---------------------------------------------------------------------------
# ResultMetaDataValidator
# ---------------------------------------------------------------------------


class TestResultMetaDataValidator:
    def _validate(self, obj):
        vr = ValidationResult()
        ctx = ValidationContext("meta")
        ResultMetaDataValidator().validate(obj, ctx, vr)
        return vr

    def _good_meta(self, **kwargs):
        base = dict(
            ResultId="r-001",
            Classification=1,
            ResultEvaluation=1,
            CreationTime=object(),
        )
        base.update(kwargs)
        return types.SimpleNamespace(**base)

    def test_valid_minimal(self):
        assert self._validate(self._good_meta()).ok

    def test_result_id_absent(self):
        meta = types.SimpleNamespace(Classification=1, ResultEvaluation=1, CreationTime=object())
        vr = self._validate(meta)
        assert not vr.ok

    def test_result_id_empty(self):
        vr = self._validate(self._good_meta(ResultId=""))
        assert not vr.ok

    def test_classification_absent(self):
        meta = types.SimpleNamespace(ResultId="r", ResultEvaluation=1, CreationTime=object())
        vr = self._validate(meta)
        assert not vr.ok

    def test_classification_invalid(self):
        vr = self._validate(self._good_meta(Classification=99))
        assert not vr.ok

    def test_classification_invalid_type(self):
        vr = self._validate(self._good_meta(Classification="bad"))
        assert not vr.ok

    def test_all_valid_classifications(self):
        for cls in range(8):
            assert self._validate(self._good_meta(Classification=cls)).ok

    def test_result_evaluation_absent(self):
        meta = types.SimpleNamespace(ResultId="r", Classification=1, CreationTime=object())
        vr = self._validate(meta)
        assert not vr.ok

    def test_result_evaluation_invalid(self):
        vr = self._validate(self._good_meta(ResultEvaluation=5))
        assert not vr.ok

    def test_result_evaluation_invalid_type(self):
        vr = self._validate(self._good_meta(ResultEvaluation="ok"))
        assert not vr.ok

    def test_all_valid_evaluations(self):
        for ev in [0, 1, 2]:
            assert self._validate(self._good_meta(ResultEvaluation=ev)).ok

    def test_creation_time_absent(self):
        meta = types.SimpleNamespace(ResultId="r", Classification=1, ResultEvaluation=1)
        vr = self._validate(meta)
        assert not vr.ok

    def test_creation_time_none_fails(self):
        vr = self._validate(self._good_meta(CreationTime=None))
        assert not vr.ok

    def test_number_of_result_content_negative(self):
        vr = self._validate(self._good_meta(NumberOfResultContent=-1))
        assert not vr.ok

    def test_number_of_result_content_zero_ok(self):
        assert self._validate(self._good_meta(NumberOfResultContent=0)).ok

    def test_number_of_result_content_positive_ok(self):
        assert self._validate(self._good_meta(NumberOfResultContent=5)).ok

    def test_sequence_number_negative(self):
        vr = self._validate(self._good_meta(SequenceNumber=-1))
        assert not vr.ok

    def test_sequence_number_zero_ok(self):
        assert self._validate(self._good_meta(SequenceNumber=0)).ok

    def test_overall_result_values_validated(self):
        good_val = types.SimpleNamespace(MeasuredValue=1.0)
        bad_val = types.SimpleNamespace()  # missing MeasuredValue
        assert self._validate(self._good_meta(OverallResultValues=[good_val])).ok
        vr = self._validate(self._good_meta(OverallResultValues=[bad_val]))
        assert not vr.ok

    def test_associated_entities_valid(self):
        entity = types.SimpleNamespace(EntityId="e-001", EntityType=1)
        assert self._validate(self._good_meta(AssociatedEntities=[entity])).ok

    def test_associated_entities_entity_id_absent(self):
        entity = types.SimpleNamespace(EntityType=1)
        vr = self._validate(self._good_meta(AssociatedEntities=[entity]))
        assert not vr.ok

    def test_associated_entities_entity_id_empty(self):
        entity = types.SimpleNamespace(EntityId="", EntityType=1)
        vr = self._validate(self._good_meta(AssociatedEntities=[entity]))
        assert not vr.ok

    def test_associated_entities_entity_type_advisory_beyond_max(self):
        entity = types.SimpleNamespace(EntityId="e-001", EntityType=99)
        vr = self._validate(self._good_meta(AssociatedEntities=[entity]))
        # Entity type beyond spec max is advisory, not hard failure
        assert vr.ok
        assert any("#advisory" in str(f.path) for f in vr.failures)

    def test_associated_entities_entity_type_invalid_non_int(self):
        entity = types.SimpleNamespace(EntityId="e-001", EntityType="bad")
        vr = self._validate(self._good_meta(AssociatedEntities=[entity]))
        assert not vr.ok

    def test_number_of_result_content_invalid_type(self):
        # Non-numeric becomes -1 internally, triggers failure
        vr = self._validate(self._good_meta(NumberOfResultContent="bad"))
        assert not vr.ok

    def test_sequence_number_invalid_type(self):
        vr = self._validate(self._good_meta(SequenceNumber="bad"))
        assert not vr.ok


# ---------------------------------------------------------------------------
# JoiningResultDataValidator
# ---------------------------------------------------------------------------


class TestJoiningResultDataValidator:
    def _validate(self, obj):
        vr = ValidationResult()
        ctx = ValidationContext("jr")
        JoiningResultDataValidator().validate(obj, ctx, vr)
        return vr

    def test_valid_minimal(self):
        obj = types.SimpleNamespace(ResultId="jr-001")
        assert self._validate(obj).ok

    def test_result_id_absent_is_advisory(self):
        obj = types.SimpleNamespace()  # no ResultId
        vr = self._validate(obj)
        # Advisory — ok should still be True
        assert vr.ok
        assert any("#advisory" in str(f.path) for f in vr.failures)

    def test_result_id_empty_string_is_hard_failure(self):
        obj = types.SimpleNamespace(ResultId="")
        vr = self._validate(obj)
        assert not vr.ok

    def test_overall_result_values_valid(self):
        val = types.SimpleNamespace(MeasuredValue=5.0, ValueTag=1)  # FINAL
        obj = types.SimpleNamespace(ResultId="r", OverallResultValues=[val])
        assert self._validate(obj).ok

    def test_overall_result_values_no_final_tag_advisory(self):
        val = types.SimpleNamespace(MeasuredValue=5.0, ValueTag=0)  # not FINAL
        obj = types.SimpleNamespace(ResultId="r", OverallResultValues=[val])
        vr = self._validate(obj)
        assert vr.ok
        assert any("#advisory" in str(f.path) for f in vr.failures)

    def test_overall_result_values_invalid_entry(self):
        val = types.SimpleNamespace()  # missing MeasuredValue
        obj = types.SimpleNamespace(ResultId="r", OverallResultValues=[val])
        vr = self._validate(obj)
        assert not vr.ok

    def test_step_results_validated(self):
        bad_step = types.SimpleNamespace()  # missing StepResultId
        obj = types.SimpleNamespace(ResultId="r", StepResults=[bad_step])
        vr = self._validate(obj)
        assert not vr.ok

    def test_errors_validated(self):
        bad_err = types.SimpleNamespace()  # missing ErrorType
        obj = types.SimpleNamespace(ResultId="r", Errors=[bad_err])
        vr = self._validate(obj)
        assert not vr.ok

    def test_failure_reason_validated_on_joining_result(self):
        for reason in [0, 1, 2, 3]:
            obj = types.SimpleNamespace(ResultId="r", FailureReason=reason)
            assert self._validate(obj).ok

    def test_failure_reason_invalid_on_joining_result(self):
        obj = types.SimpleNamespace(ResultId="r", FailureReason=4)
        vr = self._validate(obj)
        assert not vr.ok

    def test_failure_reason_invalid_type_on_joining_result(self):
        obj = types.SimpleNamespace(ResultId="r", FailureReason="bad")
        vr = self._validate(obj)
        assert not vr.ok

    def test_value_tag_none_does_not_crash(self):
        # ValueTag=None in OverallResultValues should not cause exceptions
        val = types.SimpleNamespace(MeasuredValue=5.0, ValueTag=None)
        obj = types.SimpleNamespace(ResultId="r", OverallResultValues=[val])
        vr = self._validate(obj)
        assert vr.ok

    def test_value_tag_invalid_int_in_overall_values(self):
        # ValueTag "abc" can't be converted; advisory still triggers
        val = types.SimpleNamespace(MeasuredValue=5.0, ValueTag="abc")
        obj = types.SimpleNamespace(ResultId="r", OverallResultValues=[val])
        vr = self._validate(obj)
        # ValueTag invalid → hard failure from ResultValueValidator
        assert not vr.ok


# ---------------------------------------------------------------------------
# ResultDataValidator
# ---------------------------------------------------------------------------


class TestResultDataValidator:
    def _good_meta(self):
        return types.SimpleNamespace(
            ResultId="r-001",
            Classification=1,
            ResultEvaluation=1,
            CreationTime=object(),
        )

    def test_valid_minimal(self):
        data = types.SimpleNamespace(ResultMetaData=self._good_meta())
        vr = ResultDataValidator().validate(data)
        assert vr.ok

    def test_result_meta_data_absent(self):
        data = types.SimpleNamespace()
        vr = ResultDataValidator().validate(data)
        assert not vr.ok

    def test_result_meta_data_none(self):
        data = types.SimpleNamespace(ResultMetaData=None)
        vr = ResultDataValidator().validate(data)
        assert not vr.ok

    def test_result_content_validated(self):
        jr = types.SimpleNamespace(ResultId="jr-001")
        data = types.SimpleNamespace(ResultMetaData=self._good_meta(), ResultContent=[jr])
        vr = ResultDataValidator().validate(data)
        assert vr.ok

    def test_result_content_invalid_entry(self):
        jr = types.SimpleNamespace(ResultId="")  # hard failure on empty ResultId
        data = types.SimpleNamespace(ResultMetaData=self._good_meta(), ResultContent=[jr])
        vr = ResultDataValidator().validate(data)
        assert not vr.ok

    def test_custom_context(self):
        data = types.SimpleNamespace(ResultMetaData=None)
        ctx = ValidationContext("SendResult")
        vr = ResultDataValidator().validate(data, ctx)
        assert any("SendResult" in str(f.path) for f in vr.failures)

    def test_returns_validation_result(self):
        data = types.SimpleNamespace(ResultMetaData=self._good_meta())
        result = ResultDataValidator().validate(data)
        assert isinstance(result, ValidationResult)


# ---------------------------------------------------------------------------
# ConsolidatedResultValidator
# ---------------------------------------------------------------------------


class TestConsolidatedResultValidator:
    def _good_meta(self, classification=2):
        return types.SimpleNamespace(
            ResultId="cr-001",
            Classification=classification,
            ResultEvaluation=1,
            CreationTime=object(),
        )

    def _make_ref(self, result_id="ref-001"):
        return types.SimpleNamespace(ResultId=result_id)

    def test_valid_with_references(self):
        result = types.SimpleNamespace(
            ResultMetaData=self._good_meta(),
            References=[self._make_ref()],
        )
        vr = ConsolidatedResultValidator().validate(result)
        assert vr.ok

    def test_valid_with_result_content(self):
        jr = types.SimpleNamespace(ResultId="jr-001")
        result = types.SimpleNamespace(
            ResultMetaData=self._good_meta(),
            ResultContent=[jr],
        )
        vr = ConsolidatedResultValidator().validate(result)
        assert vr.ok

    def test_valid_is_partial_allows_empty_content(self):
        result = types.SimpleNamespace(
            ResultMetaData=self._good_meta(),
            IsPartial=True,
        )
        vr = ConsolidatedResultValidator().validate(result)
        assert vr.ok

    def test_missing_both_content_and_refs_fails(self):
        result = types.SimpleNamespace(ResultMetaData=self._good_meta())
        vr = ConsolidatedResultValidator().validate(result)
        assert not vr.ok

    def test_result_meta_data_absent(self):
        result = types.SimpleNamespace()
        vr = ConsolidatedResultValidator().validate(result)
        assert not vr.ok

    def test_classification_must_be_combined(self):
        # SINGLE_RESULT=1 is not valid for consolidated results
        result = types.SimpleNamespace(
            ResultMetaData=self._good_meta(classification=1),
            References=[self._make_ref()],
        )
        vr = ConsolidatedResultValidator().validate(result)
        assert not vr.ok

    def test_all_valid_combined_classifications(self):
        for cls in [2, 3, 4, 5, 6, 7]:
            result = types.SimpleNamespace(
                ResultMetaData=self._good_meta(classification=cls),
                References=[self._make_ref()],
            )
            assert ConsolidatedResultValidator().validate(result).ok

    def test_undefined_classification_fails(self):
        result = types.SimpleNamespace(
            ResultMetaData=self._good_meta(classification=0),
            References=[self._make_ref()],
        )
        vr = ConsolidatedResultValidator().validate(result)
        assert not vr.ok

    def test_classification_invalid_type_in_meta(self):
        # Classification that can't be int-converted should not fail (cls_int stays None,
        # and the validator doesn't add a failure for that case in ConsolidatedResultValidator)
        # but the meta validator itself will have flagged it already
        meta = types.SimpleNamespace(
            ResultId="cr-001",
            Classification="not_an_int",
            ResultEvaluation=1,
            CreationTime=object(),
        )
        result = types.SimpleNamespace(
            ResultMetaData=meta,
            References=[self._make_ref()],
        )
        vr = ConsolidatedResultValidator().validate(result)
        # The meta validator catches invalid Classification type
        assert not vr.ok

    def test_reference_missing_result_id(self):
        bad_ref = types.SimpleNamespace()  # no ResultId
        result = types.SimpleNamespace(
            ResultMetaData=self._good_meta(),
            References=[bad_ref],
        )
        vr = ConsolidatedResultValidator().validate(result)
        assert not vr.ok

    def test_reference_empty_result_id(self):
        bad_ref = types.SimpleNamespace(ResultId="")
        result = types.SimpleNamespace(
            ResultMetaData=self._good_meta(),
            References=[bad_ref],
        )
        vr = ConsolidatedResultValidator().validate(result)
        assert not vr.ok

    def test_custom_context(self):
        result = types.SimpleNamespace()
        ctx = ValidationContext("BatchResult")
        vr = ConsolidatedResultValidator().validate(result, ctx)
        assert any("BatchResult" in str(f.path) for f in vr.failures)


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


class TestModuleFunctions:
    def _good_meta(self):
        return types.SimpleNamespace(
            ResultId="r-001",
            Classification=1,
            ResultEvaluation=1,
            CreationTime=object(),
        )

    def test_assert_result_data_valid_passes(self):
        data = types.SimpleNamespace(ResultMetaData=self._good_meta())
        assert_result_data_valid(data)  # no exception

    def test_assert_result_data_valid_raises_on_missing_meta(self):
        data = types.SimpleNamespace()
        with pytest.raises(AssertionError):
            assert_result_data_valid(data)

    def test_assert_result_data_valid_custom_context(self):
        data = types.SimpleNamespace()
        with pytest.raises(AssertionError, match="SendResult"):
            assert_result_data_valid(data, context="SendResult")

    def test_assert_result_meta_data_valid_passes(self):
        assert_result_meta_data_valid(self._good_meta())  # no exception

    def test_assert_result_meta_data_valid_raises(self):
        bad_meta = types.SimpleNamespace(ResultId="", Classification=1, ResultEvaluation=1, CreationTime=object())
        with pytest.raises(AssertionError):
            assert_result_meta_data_valid(bad_meta)

    def test_assert_result_value_valid_passes(self):
        val = types.SimpleNamespace(MeasuredValue=5.0)
        assert_result_value_valid(val)  # no exception

    def test_assert_result_value_valid_raises(self):
        val = types.SimpleNamespace()  # missing MeasuredValue
        with pytest.raises(AssertionError):
            assert_result_value_valid(val)

    def test_assert_result_value_valid_custom_context(self):
        val = types.SimpleNamespace()
        with pytest.raises(AssertionError, match="MyValue"):
            assert_result_value_valid(val, context="MyValue")


# ---------------------------------------------------------------------------
# _MISSING sentinel
# ---------------------------------------------------------------------------


class TestMissingSentinel:
    def test_bool_is_false(self):
        from helpers.result_validator import _MISSING

        assert not _MISSING

    def test_repr(self):
        from helpers.result_validator import _MISSING

        assert repr(_MISSING) == "<MISSING>"
