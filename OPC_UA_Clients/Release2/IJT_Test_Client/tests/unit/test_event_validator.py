"""
Unit tests for helpers/event_validator.py

Tests all validators with pure Python objects — no OPC UA server required.
"""

import types

import pytest

from helpers.event_validator import (
    AssociatedEntitiesValidator,
    BaseEventFieldsValidator,
    ConditionClassValidator,
    EntityDataTypeValidator,
    JoiningSystemConditionValidator,
    JoiningSystemEventValidator,
    JoiningSystemResultReadyEventValidator,
    JoiningTechnologyValidator,
    ReportedValuesValidator,
    ReportedValueValidator,
)
from helpers.result_validator import ValidationContext, ValidationResult

# ---------------------------------------------------------------------------
# JoiningTechnologyValidator
# ---------------------------------------------------------------------------


class TestJoiningTechnologyValidator:
    def _validate(self, value):
        vr = ValidationResult()
        ctx = ValidationContext("tech")
        JoiningTechnologyValidator().validate(value, ctx, vr)
        return vr

    def test_all_valid_values(self):
        for tech in range(8):  # 0..7
            assert self._validate(tech).ok

    def test_invalid_high(self):
        vr = self._validate(8)
        assert not vr.ok

    def test_invalid_negative(self):
        vr = self._validate(-1)
        assert not vr.ok

    def test_invalid_non_int_string(self):
        vr = self._validate("OTHER")
        assert not vr.ok

    def test_invalid_none(self):
        vr = self._validate(None)
        assert not vr.ok

    def test_int_boundary_zero(self):
        assert self._validate(0).ok

    def test_int_boundary_seven(self):
        assert self._validate(7).ok


# ---------------------------------------------------------------------------
# EntityDataTypeValidator
# ---------------------------------------------------------------------------


class TestEntityDataTypeValidator:
    def _validate(self, obj):
        vr = ValidationResult()
        ctx = ValidationContext("entity")
        EntityDataTypeValidator().validate(obj, ctx, vr)
        return vr

    def test_valid_minimal(self):
        obj = types.SimpleNamespace(EntityId="e-001")
        assert self._validate(obj).ok

    def test_entity_id_absent(self):
        obj = types.SimpleNamespace()
        vr = self._validate(obj)
        assert not vr.ok

    def test_entity_id_empty_string(self):
        obj = types.SimpleNamespace(EntityId="")
        vr = self._validate(obj)
        assert not vr.ok

    def test_entity_id_whitespace_only(self):
        obj = types.SimpleNamespace(EntityId="   ")
        vr = self._validate(obj)
        assert not vr.ok

    def test_entity_id_non_string(self):
        obj = types.SimpleNamespace(EntityId=42)
        vr = self._validate(obj)
        assert not vr.ok

    def test_entity_type_valid_bounds(self):
        for et in range(9):  # 0..8 are all valid for events
            obj = types.SimpleNamespace(EntityId="e", EntityType=et)
            assert self._validate(obj).ok

    def test_entity_type_invalid_high(self):
        obj = types.SimpleNamespace(EntityId="e", EntityType=9)
        vr = self._validate(obj)
        assert not vr.ok

    def test_entity_type_invalid_type(self):
        obj = types.SimpleNamespace(EntityId="e", EntityType="bad")
        vr = self._validate(obj)
        assert not vr.ok

    def test_entity_type_none_skipped(self):
        obj = types.SimpleNamespace(EntityId="e", EntityType=None)
        assert self._validate(obj).ok


# ---------------------------------------------------------------------------
# AssociatedEntitiesValidator
# ---------------------------------------------------------------------------


class TestAssociatedEntitiesValidator:
    def _make_entity(self, entity_id="e-001"):
        return types.SimpleNamespace(EntityId=entity_id)

    def _validate(self, entities, require_non_empty=False):
        vr = ValidationResult()
        ctx = ValidationContext("entities")
        AssociatedEntitiesValidator().validate(entities, ctx, vr, require_non_empty=require_non_empty)
        return vr

    def test_none_allowed_when_not_required(self):
        assert self._validate(None).ok

    def test_none_fails_when_required(self):
        vr = self._validate(None, require_non_empty=True)
        assert not vr.ok

    def test_empty_list_allowed_when_not_required(self):
        assert self._validate([]).ok

    def test_empty_list_fails_when_required(self):
        vr = self._validate([], require_non_empty=True)
        assert not vr.ok

    def test_valid_single_entity(self):
        assert self._validate([self._make_entity()]).ok

    def test_invalid_entity_fails(self):
        bad = types.SimpleNamespace()  # missing EntityId
        vr = self._validate([bad])
        assert not vr.ok

    def test_non_list_none_when_not_required(self):
        # Not a list — treated same as None when not required
        assert self._validate("not_a_list").ok

    def test_non_list_fails_when_required(self):
        vr = self._validate("not_a_list", require_non_empty=True)
        assert not vr.ok

    def test_multiple_entities_all_validated(self):
        good = self._make_entity("e1")
        bad = types.SimpleNamespace()
        vr = self._validate([good, bad])
        assert not vr.ok

    def test_tuple_is_valid_sequence(self):
        entity = self._make_entity()
        assert self._validate((entity,)).ok


# ---------------------------------------------------------------------------
# ReportedValueValidator
# ---------------------------------------------------------------------------


class TestReportedValueValidator:
    def _validate(self, obj):
        vr = ValidationResult()
        ctx = ValidationContext("rv")
        ReportedValueValidator().validate(obj, ctx, vr)
        return vr

    def test_valid_minimal(self):
        obj = types.SimpleNamespace(CurrentValue=5.0)
        assert self._validate(obj).ok

    def test_current_value_absent(self):
        obj = types.SimpleNamespace()
        vr = self._validate(obj)
        assert not vr.ok

    def test_current_value_none_rejected(self):
        obj = types.SimpleNamespace(CurrentValue=None)
        vr = self._validate(obj)
        assert not vr.ok

    def test_current_value_string_rejected(self):
        obj = types.SimpleNamespace(CurrentValue="not_a_number")
        vr = self._validate(obj)
        assert not vr.ok

    def test_current_value_int_accepted(self):
        obj = types.SimpleNamespace(CurrentValue=100)
        assert self._validate(obj).ok

    def test_physical_quantity_valid(self):
        for qty in [0, 14, 28]:
            obj = types.SimpleNamespace(CurrentValue=1.0, PhysicalQuantity=qty)
            assert self._validate(obj).ok

    def test_physical_quantity_invalid(self):
        obj = types.SimpleNamespace(CurrentValue=1.0, PhysicalQuantity=29)
        vr = self._validate(obj)
        assert not vr.ok

    def test_physical_quantity_invalid_type(self):
        obj = types.SimpleNamespace(CurrentValue=1.0, PhysicalQuantity="bad")
        vr = self._validate(obj)
        assert not vr.ok

    def test_engineering_units_with_identifier_ok(self):
        eu = types.SimpleNamespace(Identifier=4753)
        obj = types.SimpleNamespace(CurrentValue=1.0, EngineeringUnits=eu)
        assert self._validate(obj).ok

    def test_engineering_units_without_identifier_fails(self):
        eu = types.SimpleNamespace()  # no Identifier
        obj = types.SimpleNamespace(CurrentValue=1.0, EngineeringUnits=eu)
        vr = self._validate(obj)
        assert not vr.ok

    def test_engineering_units_none_skipped(self):
        obj = types.SimpleNamespace(CurrentValue=1.0, EngineeringUnits=None)
        assert self._validate(obj).ok

    def test_all_optional_fields(self):
        eu = types.SimpleNamespace(Identifier=100)
        obj = types.SimpleNamespace(
            CurrentValue=9.5,
            PhysicalQuantity=5,
            EngineeringUnits=eu,
        )
        assert self._validate(obj).ok


# ---------------------------------------------------------------------------
# ReportedValuesValidator
# ---------------------------------------------------------------------------


class TestReportedValuesValidator:
    def _validate(self, lst, require_non_empty=False):
        vr = ValidationResult()
        ctx = ValidationContext("rvlist")
        ReportedValuesValidator().validate(lst, ctx, vr, require_non_empty=require_non_empty)
        return vr

    def test_none_allowed_when_not_required(self):
        assert self._validate(None).ok

    def test_none_fails_when_required(self):
        vr = self._validate(None, require_non_empty=True)
        assert not vr.ok

    def test_empty_list_allowed_when_not_required(self):
        assert self._validate([]).ok

    def test_empty_list_fails_when_required(self):
        vr = self._validate([], require_non_empty=True)
        assert not vr.ok

    def test_valid_entry(self):
        val = types.SimpleNamespace(CurrentValue=5.0)
        assert self._validate([val]).ok

    def test_invalid_entry(self):
        val = types.SimpleNamespace()  # missing CurrentValue
        vr = self._validate([val])
        assert not vr.ok

    def test_non_list_not_required(self):
        assert self._validate("not_a_list").ok

    def test_non_list_required_fails(self):
        vr = self._validate("not_a_list", require_non_empty=True)
        assert not vr.ok


# ---------------------------------------------------------------------------
# BaseEventFieldsValidator
# ---------------------------------------------------------------------------


class TestBaseEventFieldsValidator:
    def _make_good_event(self, **kwargs):
        base = dict(
            EventId=b"abc123",
            EventType=types.SimpleNamespace(Identifier=1006),
            Time=object(),
            Message=types.SimpleNamespace(Text="Something happened"),
            Severity=500,
        )
        base.update(kwargs)
        return types.SimpleNamespace(**base)

    def _validate(self, obj):
        vr = ValidationResult()
        ctx = ValidationContext("event")
        BaseEventFieldsValidator().validate(obj, ctx, vr)
        return vr

    def test_valid_event(self):
        assert self._validate(self._make_good_event()).ok

    def test_event_id_absent(self):
        vr = self._validate(types.SimpleNamespace(EventType=object(), Time=object(), Message=object(), Severity=500))
        assert not vr.ok

    def test_event_id_none(self):
        vr = self._validate(self._make_good_event(EventId=None))
        assert not vr.ok

    def test_event_type_absent(self):
        vr = self._validate(types.SimpleNamespace(EventId=b"id", Time=object(), Message=object(), Severity=500))
        assert not vr.ok

    def test_event_type_none(self):
        vr = self._validate(self._make_good_event(EventType=None))
        assert not vr.ok

    def test_time_absent(self):
        vr = self._validate(types.SimpleNamespace(EventId=b"id", EventType=object(), Message=object(), Severity=500))
        assert not vr.ok

    def test_time_none(self):
        vr = self._validate(self._make_good_event(Time=None))
        assert not vr.ok

    def test_message_absent(self):
        vr = self._validate(types.SimpleNamespace(EventId=b"id", EventType=object(), Time=object(), Severity=500))
        assert not vr.ok

    def test_severity_absent(self):
        vr = self._validate(types.SimpleNamespace(EventId=b"id", EventType=object(), Time=object(), Message=object()))
        assert not vr.ok

    def test_severity_too_low(self):
        vr = self._validate(self._make_good_event(Severity=0))
        assert not vr.ok

    def test_severity_too_high(self):
        vr = self._validate(self._make_good_event(Severity=1001))
        assert not vr.ok

    def test_severity_boundary_values(self):
        assert self._validate(self._make_good_event(Severity=1)).ok
        assert self._validate(self._make_good_event(Severity=1000)).ok

    def test_severity_invalid_type(self):
        vr = self._validate(self._make_good_event(Severity="high"))
        assert not vr.ok


# ---------------------------------------------------------------------------
# JoiningSystemEventValidator
# ---------------------------------------------------------------------------


class TestJoiningSystemEventValidator:
    def _make_good_event(self, **kwargs):
        base = dict(
            EventId=b"abc123",
            EventType=types.SimpleNamespace(Identifier=1006),
            Time=object(),
            Message=types.SimpleNamespace(Text="Event"),
            Severity=500,
        )
        base.update(kwargs)
        return types.SimpleNamespace(**base)

    def test_valid_minimal(self):
        vr = JoiningSystemEventValidator().validate(self._make_good_event())
        assert vr.ok

    def test_joining_technology_valid(self):
        event = self._make_good_event(JoiningTechnology=3)
        vr = JoiningSystemEventValidator().validate(event)
        assert vr.ok

    def test_joining_technology_invalid(self):
        event = self._make_good_event(JoiningTechnology=8)
        vr = JoiningSystemEventValidator().validate(event)
        assert not vr.ok

    def test_joining_technology_none_is_ok(self):
        # Absent/None JoiningTechnology just logs debug — no failure
        event = self._make_good_event()
        vr = JoiningSystemEventValidator().validate(event)
        assert vr.ok

    def test_event_code_valid(self):
        event = self._make_good_event(EventCode=42)
        vr = JoiningSystemEventValidator().validate(event)
        assert vr.ok

    def test_event_code_negative_fails(self):
        event = self._make_good_event(EventCode=-1)
        vr = JoiningSystemEventValidator().validate(event)
        assert not vr.ok

    def test_event_code_invalid_type(self):
        event = self._make_good_event(EventCode="bad")
        vr = JoiningSystemEventValidator().validate(event)
        assert not vr.ok

    def test_event_code_none_skipped(self):
        event = self._make_good_event(EventCode=None)
        vr = JoiningSystemEventValidator().validate(event)
        assert vr.ok

    def test_associated_entities_valid(self):
        entity = types.SimpleNamespace(EntityId="e-001")
        event = self._make_good_event(AssociatedEntities=[entity])
        vr = JoiningSystemEventValidator().validate(event)
        assert vr.ok

    def test_associated_entities_invalid(self):
        bad = types.SimpleNamespace()  # missing EntityId
        event = self._make_good_event(AssociatedEntities=[bad])
        vr = JoiningSystemEventValidator().validate(event)
        assert not vr.ok

    def test_reported_values_valid(self):
        val = types.SimpleNamespace(CurrentValue=5.0)
        event = self._make_good_event(ReportedValues=[val])
        vr = JoiningSystemEventValidator().validate(event)
        assert vr.ok

    def test_reported_values_invalid(self):
        val = types.SimpleNamespace()  # missing CurrentValue
        event = self._make_good_event(ReportedValues=[val])
        vr = JoiningSystemEventValidator().validate(event)
        assert not vr.ok

    def test_custom_context(self):
        ctx = ValidationContext("MyEvent")
        event = types.SimpleNamespace()  # all fields missing
        vr = JoiningSystemEventValidator().validate(event, ctx)
        assert any("MyEvent" in str(f.path) for f in vr.failures)

    def test_returns_validation_result(self):
        result = JoiningSystemEventValidator().validate(self._make_good_event())
        assert isinstance(result, ValidationResult)


# ---------------------------------------------------------------------------
# JoiningSystemResultReadyEventValidator
# ---------------------------------------------------------------------------


class TestJoiningSystemResultReadyEventValidator:
    def _make_good_meta(self):
        return types.SimpleNamespace(
            ResultId="r-001",
            Classification=1,
            ResultEvaluation=1,
            CreationTime=object(),
        )

    def _make_good_event(self, **kwargs):
        base = dict(
            EventId=b"abc123",
            EventType=types.SimpleNamespace(Identifier=1007),
            Time=object(),
            Message=types.SimpleNamespace(Text="ResultReady"),
            Severity=500,
            Result=types.SimpleNamespace(ResultMetaData=self._make_good_meta()),
        )
        base.update(kwargs)
        return types.SimpleNamespace(**base)

    def test_valid_event(self):
        vr = JoiningSystemResultReadyEventValidator().validate(self._make_good_event())
        assert vr.ok

    def test_result_absent_fails(self):
        event = types.SimpleNamespace(
            EventId=b"id",
            EventType=object(),
            Time=object(),
            Message=object(),
            Severity=500,
        )
        vr = JoiningSystemResultReadyEventValidator().validate(event)
        assert not vr.ok

    def test_result_none_fails(self):
        vr = JoiningSystemResultReadyEventValidator().validate(self._make_good_event(Result=None))
        assert not vr.ok

    def test_result_meta_data_absent_fails(self):
        result = types.SimpleNamespace()  # no ResultMetaData
        vr = JoiningSystemResultReadyEventValidator().validate(self._make_good_event(Result=result))
        assert not vr.ok

    def test_result_meta_data_none_fails(self):
        result = types.SimpleNamespace(ResultMetaData=None)
        vr = JoiningSystemResultReadyEventValidator().validate(self._make_good_event(Result=result))
        assert not vr.ok

    def test_custom_context(self):
        ctx = ValidationContext("ReadyEvent")
        event = types.SimpleNamespace()
        vr = JoiningSystemResultReadyEventValidator().validate(event, ctx)
        assert any("ReadyEvent" in str(f.path) for f in vr.failures)


# ---------------------------------------------------------------------------
# ConditionClassValidator
# ---------------------------------------------------------------------------


class TestConditionClassValidator:
    def _validator(self):
        return ConditionClassValidator()

    def _validate_name(self, name):
        vr = ValidationResult()
        ctx = ValidationContext("cc")
        self._validator().validate_condition_class(name, ctx, vr)
        return vr

    def _validate_id(self, node_id):
        vr = ValidationResult()
        ctx = ValidationContext("ccid")
        self._validator().validate_condition_class_id(node_id, ctx, vr)
        return vr

    def test_valid_condition_class_names(self):
        valid_names = [
            "ProcessConditionClassType",
            "MaintenanceConditionClassType",
            "SystemConditionClassType",
            "SafetyConditionClassType",
            "CheckFunctionConditionClassType",
        ]
        for name in valid_names:
            assert self._validate_name(name).ok, f"Expected {name} to be valid"

    def test_valid_subclass_names(self):
        valid_subs = [
            "ToolConditionClassType",
            "SoftwareConditionClassType",
            "CertificateConditionClassType",
            "LicenseConditionClassType",
            "ProcessConditionSubClassType",
            "IdentifierConditionSubClassType",
            "ConfigurationConditionSubClassType",
            "CalibrationConditionSubClassType",
        ]
        for name in valid_subs:
            assert self._validate_name(name).ok, f"Expected {name} to be valid"

    def test_invalid_class_name(self):
        vr = self._validate_name("UnknownConditionClassType")
        assert not vr.ok

    def test_empty_class_name(self):
        vr = self._validate_name("")
        assert not vr.ok

    def test_whitespace_class_name(self):
        vr = self._validate_name("   ")
        assert not vr.ok

    def test_prefix_match_accepted(self):
        # "Process" is a prefix of "ProcessConditionClassType"
        assert self._validate_name("Process").ok

    def test_valid_condition_class_id(self):
        node_id = types.SimpleNamespace(Identifier=1020)
        assert self._validate_id(node_id).ok

    def test_condition_class_id_none(self):
        vr = self._validate_id(None)
        assert not vr.ok

    def test_condition_class_id_no_identifier(self):
        node_id = types.SimpleNamespace()
        vr = self._validate_id(node_id)
        assert not vr.ok

    def test_condition_class_id_zero(self):
        node_id = types.SimpleNamespace(Identifier=0)
        vr = self._validate_id(node_id)
        assert not vr.ok

    def test_condition_class_id_negative(self):
        node_id = types.SimpleNamespace(Identifier=-1)
        vr = self._validate_id(node_id)
        assert not vr.ok

    def test_condition_class_id_non_int(self):
        node_id = types.SimpleNamespace(Identifier="bad")
        vr = self._validate_id(node_id)
        assert not vr.ok


# ---------------------------------------------------------------------------
# JoiningSystemConditionValidator
# ---------------------------------------------------------------------------


class TestJoiningSystemConditionValidator:
    def _make_good_condition(self, **kwargs):
        base = dict(
            ConditionClassId=types.SimpleNamespace(Identifier=1020),
            ConditionClassName=types.SimpleNamespace(Text="ProcessConditionClassType"),
        )
        base.update(kwargs)
        return types.SimpleNamespace(**base)

    def test_valid_minimal(self):
        vr = JoiningSystemConditionValidator().validate(self._make_good_condition())
        assert vr.ok

    def test_condition_class_id_absent(self):
        condition = types.SimpleNamespace(ConditionClassName=types.SimpleNamespace(Text="ProcessConditionClassType"))
        vr = JoiningSystemConditionValidator().validate(condition)
        assert not vr.ok

    def test_condition_class_id_none(self):
        vr = JoiningSystemConditionValidator().validate(self._make_good_condition(ConditionClassId=None))
        assert not vr.ok

    def test_condition_class_name_absent(self):
        condition = types.SimpleNamespace(ConditionClassId=types.SimpleNamespace(Identifier=1020))
        vr = JoiningSystemConditionValidator().validate(condition)
        assert not vr.ok

    def test_condition_class_name_none(self):
        vr = JoiningSystemConditionValidator().validate(self._make_good_condition(ConditionClassName=None))
        assert not vr.ok

    def test_condition_class_name_empty_text(self):
        vr = JoiningSystemConditionValidator().validate(
            self._make_good_condition(ConditionClassName=types.SimpleNamespace(Text=""))
        )
        assert not vr.ok

    def test_condition_class_name_unknown(self):
        vr = JoiningSystemConditionValidator().validate(
            self._make_good_condition(ConditionClassName=types.SimpleNamespace(Text="UnknownClass"))
        )
        assert not vr.ok

    def test_joining_technology_valid(self):
        condition = self._make_good_condition(JoiningTechnology=2)
        vr = JoiningSystemConditionValidator().validate(condition)
        assert vr.ok

    def test_joining_technology_invalid(self):
        condition = self._make_good_condition(JoiningTechnology=9)
        vr = JoiningSystemConditionValidator().validate(condition)
        assert not vr.ok

    def test_sub_class_ids_valid(self):
        sub_id = types.SimpleNamespace(Identifier=100)
        condition = self._make_good_condition(ConditionSubClassId=[sub_id])
        vr = JoiningSystemConditionValidator().validate(condition)
        assert vr.ok

    def test_sub_class_ids_none_entry_fails(self):
        condition = self._make_good_condition(ConditionSubClassId=[None])
        vr = JoiningSystemConditionValidator().validate(condition)
        assert not vr.ok

    def test_associated_entities_valid(self):
        entity = types.SimpleNamespace(EntityId="e-001")
        condition = self._make_good_condition(AssociatedEntities=[entity])
        vr = JoiningSystemConditionValidator().validate(condition)
        assert vr.ok

    def test_custom_context(self):
        ctx = ValidationContext("MyCondition")
        condition = types.SimpleNamespace()
        vr = JoiningSystemConditionValidator().validate(condition, ctx)
        assert any("MyCondition" in str(f.path) for f in vr.failures)

    def test_returns_validation_result(self):
        result = JoiningSystemConditionValidator().validate(self._make_good_condition())
        assert isinstance(result, ValidationResult)

    def test_event_code_valid(self):
        condition = self._make_good_condition(EventCode=5)
        vr = JoiningSystemConditionValidator().validate(condition)
        assert vr.ok

    def test_event_code_negative_fails(self):
        condition = self._make_good_condition(EventCode=-1)
        vr = JoiningSystemConditionValidator().validate(condition)
        assert not vr.ok

    def test_event_code_invalid_type_fails(self):
        condition = self._make_good_condition(EventCode="bad")
        vr = JoiningSystemConditionValidator().validate(condition)
        assert not vr.ok

    def test_event_code_none_skipped(self):
        condition = self._make_good_condition(EventCode=None)
        vr = JoiningSystemConditionValidator().validate(condition)
        assert vr.ok


# ---------------------------------------------------------------------------
# Module-level convenience functions (event_validator)
# ---------------------------------------------------------------------------


class TestEventValidatorModuleFunctions:
    def _make_good_event(self):
        return types.SimpleNamespace(
            EventId=b"id",
            EventType=object(),
            Time=object(),
            Message=object(),
            Severity=500,
        )

    def _make_good_condition(self):
        return types.SimpleNamespace(
            ConditionClassId=types.SimpleNamespace(Identifier=1020),
            ConditionClassName=types.SimpleNamespace(Text="ProcessConditionClassType"),
        )

    def _make_good_result_ready_event(self):
        meta = types.SimpleNamespace(
            ResultId="r-001",
            Classification=1,
            ResultEvaluation=1,
            CreationTime=object(),
        )
        return types.SimpleNamespace(
            EventId=b"id",
            EventType=object(),
            Time=object(),
            Message=object(),
            Severity=500,
            Result=types.SimpleNamespace(ResultMetaData=meta),
        )

    def test_assert_joining_system_event_valid_passes(self):
        from helpers.event_validator import assert_joining_system_event_valid

        assert_joining_system_event_valid(self._make_good_event())

    def test_assert_joining_system_event_valid_raises(self):
        from helpers.event_validator import assert_joining_system_event_valid

        with pytest.raises(AssertionError):
            assert_joining_system_event_valid(types.SimpleNamespace())

    def test_assert_joining_system_event_valid_custom_context(self):
        from helpers.event_validator import assert_joining_system_event_valid

        with pytest.raises(AssertionError, match="MyContext"):
            assert_joining_system_event_valid(types.SimpleNamespace(), context="MyContext")

    def test_assert_result_ready_event_valid_passes(self):
        from helpers.event_validator import assert_result_ready_event_valid

        assert_result_ready_event_valid(self._make_good_result_ready_event())

    def test_assert_result_ready_event_valid_raises(self):
        from helpers.event_validator import assert_result_ready_event_valid

        with pytest.raises(AssertionError):
            assert_result_ready_event_valid(types.SimpleNamespace())

    def test_assert_condition_valid_passes(self):
        from helpers.event_validator import assert_condition_valid

        assert_condition_valid(self._make_good_condition())

    def test_assert_condition_valid_raises(self):
        from helpers.event_validator import assert_condition_valid

        with pytest.raises(AssertionError):
            assert_condition_valid(types.SimpleNamespace())

    def test_assert_condition_valid_custom_context(self):
        from helpers.event_validator import assert_condition_valid

        with pytest.raises(AssertionError, match="MyCondCtx"):
            assert_condition_valid(types.SimpleNamespace(), context="MyCondCtx")


# ---------------------------------------------------------------------------
# _MISSING sentinel
# ---------------------------------------------------------------------------


class TestMissingSentinel:
    def test_bool_is_false(self):
        from helpers.event_validator import _MISSING

        assert not _MISSING

    def test_repr(self):
        from helpers.event_validator import _MISSING

        assert repr(_MISSING) == "<MISSING>"
