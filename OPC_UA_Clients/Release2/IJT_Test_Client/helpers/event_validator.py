"""
helpers/event_validator.py — Reusable validators for IJT OPC UA event data.

All validators follow the same pattern as result_validator.py:
  - .validate(data, ctx) → ValidationResult
  - Never raise; collect all failures
  - Graceful handling of missing attributes via getattr(..., None)

Covers:
  - JoiningSystemEventType      (OPC 40450-1 §8, extends BaseEventType)
  - JoiningSystemResultReadyEventType  (§8, carries a JoiningSystemResultType)
  - JoiningSystemConditionType  (§8, extends ConditionType from OPC UA Part 9)
"""

from __future__ import annotations

import logging
from typing import Optional

from helpers.result_validator import (
    ResultMetaDataValidator,
    ValidationContext,
    ValidationResult,
)

logger = logging.getLogger(__name__)


def _unwrap_variant(value):
    """Unwrap asyncua Variant containers used for nested ExtensionObjects."""
    return getattr(value, "Value", value)


# ---------------------------------------------------------------------------
# Sentinel for missing required attributes (mirrors result_validator pattern)
# ---------------------------------------------------------------------------


class _MissingSentinel:
    """Evaluates as falsy; distinguishes absent attribute from None value."""

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "<MISSING>"


_MISSING = _MissingSentinel()

# ---------------------------------------------------------------------------
# Valid enum ranges (OPC 40450-1 §8 and OPC UA Part 9)
# ---------------------------------------------------------------------------

# EntityTypeEnumeration per OPC 40450-1 v100 §10.10.
_VALID_EVENT_ENTITY_TYPES: set[int] = set(range(43))

# OPC UA Severity: 1–1000 (OPC UA Part 4 §7.19)
_SEVERITY_MIN = 1
_SEVERITY_MAX = 1000

# PhysicalQuantityEnumeration: 0=OTHER … 28=TORQUE_PER_ANGLE_GRADIENT2
# Shared by ResultValueDataType and ReportedValueDataType.
_VALID_PHYSICAL_QUANTITIES: set[int] = set(range(29))


# ---------------------------------------------------------------------------
# JoiningTechnologyValidator
# ---------------------------------------------------------------------------


class JoiningTechnologyValidator:
    """
    Validates a JoiningTechnology value.

    In the IJT Base NodeSet the field is LocalizedText, not a numeric enum.
    asyncua test doubles often represent LocalizedText as an object with a
    ``Text`` attribute; plain strings are also accepted for unit-test and
    deserialization compatibility.
    """

    def validate(
        self,
        value: object,
        ctx: ValidationContext,
        vr: ValidationResult,
    ) -> None:
        """Check that *value* is a non-empty LocalizedText/string payload."""
        if value is None:
            vr.add(ctx, "expected LocalizedText/string, got None")
            return

        text = getattr(value, "Text", value)
        if not isinstance(text, str) or not text.strip():
            vr.add(ctx, f"expected non-empty LocalizedText/string, got {value!r}")


# ---------------------------------------------------------------------------
# EntityDataTypeValidator
# ---------------------------------------------------------------------------


class EntityDataTypeValidator:
    """Validates a single EntityDataType object from an IJT event."""

    def validate(
        self,
        entity: object,
        ctx: ValidationContext,
        vr: ValidationResult,
    ) -> None:
        """
        Check:
        - ``EntityId`` non-empty string (required).
        - ``EntityType`` in {0..42} if present.
        """
        # EntityId — required, non-empty string
        entity_id = getattr(entity, "EntityId", _MISSING)
        if entity_id is _MISSING:
            vr.add(ctx.child("EntityId"), "required field is absent")
        elif not isinstance(entity_id, str) or not entity_id.strip():
            vr.add(
                ctx.child("EntityId"),
                f"expected non-empty string, got {entity_id!r}",
            )

        # EntityType — optional, must be in valid range if present
        entity_type = getattr(entity, "EntityType", None)
        if entity_type is not None:
            try:
                et_int = int(entity_type)
            except (TypeError, ValueError):
                et_int = None
            if et_int is None or et_int not in _VALID_EVENT_ENTITY_TYPES:
                vr.add(
                    ctx.child("EntityType"),
                    f"expected int in {{0..42}} (EntityType enum), got {entity_type!r}",
                )


# ---------------------------------------------------------------------------
# AssociatedEntitiesValidator
# ---------------------------------------------------------------------------


class AssociatedEntitiesValidator:
    """Validates an AssociatedEntities list from an IJT event or condition."""

    def __init__(self) -> None:
        self._entity_validator = EntityDataTypeValidator()

    def validate(
        self,
        entities_list: object,
        ctx: ValidationContext,
        vr: ValidationResult,
        require_non_empty: bool = False,
    ) -> None:
        """
        Check:
        - If *require_non_empty* is True and the list is empty → failure.
        - Each entry in the list is validated via ``EntityDataTypeValidator``.

        :param entities_list:    The AssociatedEntities list (or None).
        :param ctx:              Validation context path.
        :param vr:               Validation result collector.
        :param require_non_empty: When True, an empty or absent list is a failure.
        """
        if entities_list is None or not isinstance(entities_list, (list, tuple)):
            if require_non_empty:
                vr.add(ctx, "AssociatedEntities must be a non-empty list (required)")
            return

        if require_non_empty and len(entities_list) == 0:
            vr.add(ctx, "AssociatedEntities must contain at least one entry")
            return

        for i, entity in enumerate(entities_list):
            entity = _unwrap_variant(entity)
            self._entity_validator.validate(entity, ctx.index(i), vr)


# ---------------------------------------------------------------------------
# ReportedValueValidator
# ---------------------------------------------------------------------------


class ReportedValueValidator:
    """Validates a single ``ReportedValueDataType`` object (OPC 40450-1 §8).

    ``ReportedValueDataType`` fields per NodeSet2 spec:
      - ``CurrentValue``       — **mandatory** (Variant)
      - ``PhysicalQuantity``   — optional (IJTPhysicalQuantityEnumeration 0..28)
      - ``Name``               — optional (String)
      - ``PreviousValue``      — optional (Double)
      - ``LowLimit``           — optional (Double)
      - ``HighLimit``          — optional (Double)
      - ``EngineeringUnits``   — optional (EUInformation)

    Note: this type is distinct from ``ResultValueDataType`` (which has
    ``MeasuredValue`` as its mandatory field and is used in result payloads).
    """

    def validate(
        self,
        value: object,
        ctx: ValidationContext,
        vr: ValidationResult,
    ) -> None:
        """
        Check:
        - ``CurrentValue`` is present and non-None (Variant, required per spec).
        - ``PhysicalQuantity`` is in {0..28} if present.
        - ``EngineeringUnits`` has a ``.UnitId`` attribute if present.
        """
        # CurrentValue — required Variant; may hold any scalar value.
        current = getattr(value, "CurrentValue", _MISSING)
        if current is _MISSING:
            vr.add(ctx.child("CurrentValue"), "required field is absent")
        elif current is None:
            vr.add(ctx.child("CurrentValue"), "must not be None")

        # PhysicalQuantity — optional, must be in valid range if present
        phys_qty = getattr(value, "PhysicalQuantity", None)
        if phys_qty is not None:
            try:
                qty_int = int(phys_qty)
            except (TypeError, ValueError):
                qty_int = None
            if qty_int is None or qty_int not in _VALID_PHYSICAL_QUANTITIES:
                vr.add(
                    ctx.child("PhysicalQuantity"),
                    f"expected int in {{0..28}}, got {phys_qty!r}",
                )

        # EngineeringUnits — optional, but must expose .UnitId if present
        eu = getattr(value, "EngineeringUnits", None)
        eu = _unwrap_variant(eu) if eu is not None else None
        if eu is not None and not hasattr(eu, "UnitId"):
            vr.add(
                ctx.child("EngineeringUnits"),
                "present but has no .UnitId attribute (expected EUInformation)",
            )


# ---------------------------------------------------------------------------
# ReportedValuesValidator
# ---------------------------------------------------------------------------


class ReportedValuesValidator:
    """Validates a ReportedValues list from an IJT event."""

    def __init__(self) -> None:
        self._value_validator = ReportedValueValidator()

    def validate(
        self,
        values_list: object,
        ctx: ValidationContext,
        vr: ValidationResult,
        require_non_empty: bool = False,
    ) -> None:
        """
        Validate each entry via ``ReportedValueValidator`` (checks CurrentValue
        and PhysicalQuantity among others).

        :param values_list:      The ReportedValues list (or None).
        :param ctx:              Validation context path.
        :param vr:               Validation result collector.
        :param require_non_empty: When True, an empty or absent list is a failure.
        """
        if values_list is None or not isinstance(values_list, (list, tuple)):
            if require_non_empty:
                vr.add(ctx, "ReportedValues must be a non-empty list (required)")
            return

        if require_non_empty and len(values_list) == 0:
            vr.add(ctx, "ReportedValues must contain at least one entry")
            return

        for i, value in enumerate(values_list):
            value = _unwrap_variant(value)
            self._value_validator.validate(value, ctx.index(i), vr)


# ---------------------------------------------------------------------------
# BaseEventFieldsValidator
# ---------------------------------------------------------------------------


class BaseEventFieldsValidator:
    """
    Validates the mandatory OPC UA BaseEventType fields.

    Required per OPC UA Part 9 §5.6.1:
      EventId, EventType, Time, Message, Severity
    """

    def validate(
        self,
        event: object,
        ctx: ValidationContext,
        vr: ValidationResult,
    ) -> None:
        """
        Check:
        - ``EventId`` present and non-None (ByteString identifier).
        - ``EventType`` present and non-None (NodeId).
        - ``Time`` present and non-None (DateTime).
        - ``Message`` present (LocalizedText).
        - ``Severity`` present and in {1..1000}.
        """
        # EventId — required, must not be None
        event_id = getattr(event, "EventId", _MISSING)
        if event_id is _MISSING:
            vr.add(ctx.child("EventId"), "required field is absent")
        elif event_id is None:
            vr.add(ctx.child("EventId"), "must not be None")

        # EventType — required, non-None NodeId
        event_type = getattr(event, "EventType", _MISSING)
        if event_type is _MISSING:
            vr.add(ctx.child("EventType"), "required field is absent")
        elif event_type is None:
            vr.add(ctx.child("EventType"), "must not be None (expected NodeId)")

        # Time — required, non-None DateTime
        time = getattr(event, "Time", _MISSING)
        if time is _MISSING:
            vr.add(ctx.child("Time"), "required field is absent")
        elif time is None:
            vr.add(ctx.child("Time"), "must not be None (expected DateTime)")

        # Message — required, should be a LocalizedText (presence check only)
        message = getattr(event, "Message", _MISSING)
        if message is _MISSING:
            vr.add(ctx.child("Message"), "required field is absent")

        # Severity — required, must be in OPC UA valid range {1..1000}
        severity = getattr(event, "Severity", _MISSING)
        if severity is _MISSING:
            vr.add(ctx.child("Severity"), "required field is absent")
        else:
            try:
                sev_int = int(severity)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                sev_int = None
            if sev_int is None or not _SEVERITY_MIN <= sev_int <= _SEVERITY_MAX:
                vr.add(
                    ctx.child("Severity"),
                    f"expected integer in {{{_SEVERITY_MIN}..{_SEVERITY_MAX}}}, got {severity!r}",
                )


# ---------------------------------------------------------------------------
# JoiningSystemEventValidator
# ---------------------------------------------------------------------------


class JoiningSystemEventValidator:
    """
    Validates a JoiningSystemEventType event object.

    Checks all BaseEventType fields plus the IJT-specific extensions defined
    in OPC 40450-1 §8.
    """

    def __init__(self) -> None:
        self._base_validator = BaseEventFieldsValidator()
        self._tech_validator = JoiningTechnologyValidator()
        self._entities_validator = AssociatedEntitiesValidator()
        self._values_validator = ReportedValuesValidator()

    def validate(
        self,
        event: object,
        ctx: Optional[ValidationContext] = None,
    ) -> ValidationResult:
        """
        Validate *event* as a JoiningSystemEventType.

        Validates:
        - All BaseEventType fields.
        - ``JoiningTechnology`` is LocalizedText/string if present (logs DEBUG if absent).
        - ``EventCode`` is integer ≥ 0 if present.
        - ``AssociatedEntities`` list via ``AssociatedEntitiesValidator``.
        - ``ReportedValues`` list via ``ReportedValuesValidator``.

        :param event: The asyncua event object (attribute-access based).
        :param ctx:   Optional root context; defaults to "JoiningSystemEventType".
        :returns:     A ``ValidationResult`` with all collected failures.
        """
        vr = ValidationResult()
        ctx = ctx or ValidationContext("JoiningSystemEventType")

        # Validate BaseEventType mandatory fields
        self._base_validator.validate(event, ctx, vr)

        # JoiningTechnology — optional per spec, but advisory if absent
        joining_tech = getattr(event, "JoiningTechnology", None)
        if joining_tech is None:
            logger.debug("%s: JoiningTechnology field is absent or None", ctx)
        else:
            self._tech_validator.validate(joining_tech, ctx.child("JoiningTechnology"), vr)

        # EventCode — optional, must be integer ≥ 0 if present
        event_code = getattr(event, "EventCode", None)
        if event_code is not None:
            try:
                code_int = int(event_code)
            except (TypeError, ValueError):
                code_int = None
            if code_int is None or code_int < 0:
                vr.add(
                    ctx.child("EventCode"),
                    f"expected non-negative integer, got {event_code!r}",
                )

        # AssociatedEntities — optional list; validate each entry if present
        entities = getattr(event, "AssociatedEntities", None)
        if entities is not None:
            self._entities_validator.validate(entities, ctx.child("AssociatedEntities"), vr)

        # ReportedValues — optional list; validate each entry if present
        reported_values = getattr(event, "ReportedValues", None)
        if reported_values is not None:
            self._values_validator.validate(reported_values, ctx.child("ReportedValues"), vr)

        return vr


# ---------------------------------------------------------------------------
# JoiningSystemResultReadyEventValidator
# ---------------------------------------------------------------------------


class JoiningSystemResultReadyEventValidator:
    """
    Validates a JoiningSystemResultReadyEventType event object.

    Extends ResultReadyEventType (from OPC UA Machinery/Result companion spec)
    with a ``Result`` attribute of type JoiningSystemResultType.
    """

    def __init__(self) -> None:
        self._base_validator = BaseEventFieldsValidator()
        self._meta_validator = ResultMetaDataValidator()

    def validate(
        self,
        event: object,
        ctx: Optional[ValidationContext] = None,
    ) -> ValidationResult:
        """
        Validate *event* as a JoiningSystemResultReadyEventType.

        Validates:
        - All BaseEventType fields.
        - ``Result`` attribute is present (JoiningSystemResultType).
        - If ``Result`` is present: ``ResultMetaData`` is present and valid.

        :param event: The asyncua event object.
        :param ctx:   Optional root context; defaults to "JoiningSystemResultReadyEventType".
        :returns:     A ``ValidationResult`` with all collected failures.
        """
        vr = ValidationResult()
        ctx = ctx or ValidationContext("JoiningSystemResultReadyEventType")

        # Validate BaseEventType mandatory fields
        self._base_validator.validate(event, ctx, vr)

        # Result — required, must be present
        result = getattr(event, "Result", _MISSING)
        if result is _MISSING or result is None:
            vr.add(ctx.child("Result"), "required field is absent or None")
        else:
            # ResultMetaData — required on JoiningSystemResultType
            meta = getattr(result, "ResultMetaData", _MISSING)
            if meta is _MISSING or meta is None:
                vr.add(
                    ctx.child("Result").child("ResultMetaData"),
                    "required field is absent or None",
                )
            else:
                self._meta_validator.validate(meta, ctx.child("Result").child("ResultMetaData"), vr)

        return vr


# ---------------------------------------------------------------------------
# ConditionClassValidator
# ---------------------------------------------------------------------------


class ConditionClassValidator:
    """
    Validates OPC UA condition class names and NodeIds for IJT conditions.

    Valid condition classes (OPC UA Part 9 §5.9 + IJT Annexure G):
    """

    VALID_CONDITION_CLASSES: set[str] = {
        "BaseConditionClassType",
        "ProcessConditionClassType",
        "MaintenanceConditionClassType",
        "SystemConditionClassType",
        "SafetyConditionClassType",
        "CheckFunctionConditionClassType",
        "HighlyManagedAlarmConditionClassType",
        "TrainingConditionClassType",
        "StatisticalConditionClassType",
        "TestingConditionClassType",
        "ConnectionFailureConditionClassType",
        "OverTemperatureConditionClassType",
        "CalibrationDueConditionClassType",
        "SelfTestFailureConditionClassType",
        "FlashUpdateInProgressConditionClassType",
        "FlashUpdatedFailedConditionClassType",
        "BadConfigurationConditionClassType",
        "OutOfResourcesConditionClassType",
        "OutOfMemoryConditionClassType",
        "InspectionConditionClassType",
        "ExternalCheckConditionClassType",
        "ServicingConditionClassType",
        "ImprovementConditionClassType",
        "RepairConditionClassType",
    }

    VALID_CONDITION_SUBCLASSES: set[str] = {
        "ToolConditionClassType",
        "SoftwareConditionClassType",
        "CertificateConditionClassType",
        "LicenseConditionClassType",
        "ProcessConditionSubClassType",
        "IdentifierConditionSubClassType",
        "ConfigurationConditionSubClassType",
        "CalibrationConditionSubClassType",
    }

    def validate_condition_class(
        self,
        condition_class_name: str,
        ctx: ValidationContext,
        vr: ValidationResult,
    ) -> None:
        """
        Check that *condition_class_name* is a recognised IJT condition class.

        Accepts both the full type name (e.g. "ProcessConditionClassType") and
        a bare prefix (e.g. "Process").  Unknown names are recorded as failures.

        :param condition_class_name: The ``ConditionClassName.Text`` string value.
        :param ctx:                  Validation context path.
        :param vr:                   Validation result collector.
        """
        if not condition_class_name or not condition_class_name.strip():
            vr.add(ctx, "condition class name must be a non-empty string")
            return

        name = condition_class_name.strip()
        # Accept exact match first
        if name in self.VALID_CONDITION_CLASSES or name in self.VALID_CONDITION_SUBCLASSES:
            return

        # Try suffix normalisation: "ProcessConditionClassType" → bare "Process"
        all_known = self.VALID_CONDITION_CLASSES | self.VALID_CONDITION_SUBCLASSES
        for known in all_known:
            if known.startswith(name) or name.startswith(known):
                return

        vr.add(
            ctx,
            f"unrecognised condition class name {name!r}; "
            f"expected one of {sorted(self.VALID_CONDITION_CLASSES | self.VALID_CONDITION_SUBCLASSES)}",
        )

    def validate_condition_class_id(
        self,
        condition_class_id: object,
        ctx: ValidationContext,
        vr: ValidationResult,
    ) -> None:
        """
        Check that *condition_class_id* is a non-null NodeId with a positive
        integer Identifier.

        :param condition_class_id: The ``ConditionClassId`` NodeId object.
        :param ctx:                Validation context path.
        :param vr:                 Validation result collector.
        """
        if condition_class_id is None:
            vr.add(ctx, "ConditionClassId must not be None (required by IJT spec)")
            return

        identifier = getattr(condition_class_id, "Identifier", _MISSING)
        if identifier is _MISSING:
            vr.add(ctx.child("Identifier"), "NodeId has no Identifier attribute")
            return

        try:
            id_int = int(identifier)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            id_int = None

        if id_int is None or id_int <= 0:
            vr.add(
                ctx.child("Identifier"),
                f"expected positive integer NodeId Identifier, got {identifier!r}",
            )


# ---------------------------------------------------------------------------
# JoiningSystemConditionValidator
# ---------------------------------------------------------------------------


class JoiningSystemConditionValidator:
    """
    Validates a JoiningSystemConditionType condition object.

    Extends ConditionType (OPC UA Part 9) with IJT-specific fields defined in
    OPC 40450-1 §8 and Annexure G.
    """

    def __init__(self) -> None:
        self._tech_validator = JoiningTechnologyValidator()
        self._entities_validator = AssociatedEntitiesValidator()
        self._condition_class_validator = ConditionClassValidator()

    def validate(
        self,
        condition: object,
        ctx: Optional[ValidationContext] = None,
    ) -> ValidationResult:
        """
        Validate *condition* as a JoiningSystemConditionType.

        Validates:
        - ``ConditionClassId`` non-null NodeId (required per IJT spec §8).
        - ``ConditionClassName`` non-null LocalizedText with non-empty ``.Text``.
        - ``ConditionSubClassId`` list: entries must be non-null if list is present.
        - ``JoiningTechnology`` is LocalizedText/string if present.
        - ``AssociatedEntities`` list via ``AssociatedEntitiesValidator``.
        - ``EventCode`` is integer ≥ 0 if present.

        :param condition: The asyncua condition object (attribute-access based).
        :param ctx:       Optional root context; defaults to "JoiningSystemConditionType".
        :returns:         A ``ValidationResult`` with all collected failures.
        """
        vr = ValidationResult()
        ctx = ctx or ValidationContext("JoiningSystemConditionType")

        # ConditionClassId — required, non-null NodeId
        class_id = getattr(condition, "ConditionClassId", _MISSING)
        if class_id is _MISSING or class_id is None:
            vr.add(ctx.child("ConditionClassId"), "required field is absent or None")
        else:
            self._condition_class_validator.validate_condition_class_id(class_id, ctx.child("ConditionClassId"), vr)

        # ConditionClassName — required, non-null LocalizedText with non-empty .Text
        class_name = getattr(condition, "ConditionClassName", _MISSING)
        if class_name is _MISSING or class_name is None:
            vr.add(
                ctx.child("ConditionClassName"),
                "required field is absent or None",
            )
        else:
            text = getattr(class_name, "Text", None)
            if not text or not str(text).strip():
                vr.add(
                    ctx.child("ConditionClassName").child("Text"),
                    f"expected non-empty string, got {text!r}",
                )
            else:
                self._condition_class_validator.validate_condition_class(str(text), ctx.child("ConditionClassName"), vr)

        # ConditionSubClassId — optional list; each entry must be non-null if present
        sub_class_ids = getattr(condition, "ConditionSubClassId", None)
        if sub_class_ids is not None and isinstance(sub_class_ids, (list, tuple)):
            sub_ctx = ctx.child("ConditionSubClassId")
            for i, sub_id in enumerate(sub_class_ids):
                if sub_id is None:
                    vr.add(
                        sub_ctx.index(i),
                        "ConditionSubClassId entry must not be None",
                    )

        # JoiningTechnology — optional per spec, advisory if absent
        joining_tech = getattr(condition, "JoiningTechnology", None)
        if joining_tech is None:
            logger.debug("%s: JoiningTechnology field is absent or None", ctx)
        else:
            self._tech_validator.validate(joining_tech, ctx.child("JoiningTechnology"), vr)

        # AssociatedEntities — optional list; validate each entry if present
        entities = getattr(condition, "AssociatedEntities", None)
        if entities is not None:
            self._entities_validator.validate(entities, ctx.child("AssociatedEntities"), vr)

        # EventCode — optional, must be integer ≥ 0 if present
        event_code = getattr(condition, "EventCode", None)
        if event_code is not None:
            try:
                code_int = int(event_code)
            except (TypeError, ValueError):
                code_int = None
            if code_int is None or code_int < 0:
                vr.add(
                    ctx.child("EventCode"),
                    f"expected non-negative integer, got {event_code!r}",
                )

        return vr


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


def assert_joining_system_event_valid(
    event: object,
    context: str = "JoiningSystemEvent",
) -> None:
    """
    Validate a JoiningSystemEventType event and raise AssertionError if invalid.

    :param event:   The asyncua event object received from a subscription callback.
    :param context: Human-readable label used as the root path in failure messages.
    :raises AssertionError: If one or more validation failures are found.
    """
    vr = JoiningSystemEventValidator().validate(event, ValidationContext(context))
    vr.assert_no_failures()


def assert_result_ready_event_valid(
    event: object,
    context: str = "ResultReadyEvent",
) -> None:
    """
    Validate a JoiningSystemResultReadyEventType event and raise AssertionError if
    invalid.

    :param event:   The asyncua event object received from a subscription callback.
    :param context: Human-readable label used as the root path in failure messages.
    :raises AssertionError: If one or more validation failures are found.
    """
    vr = JoiningSystemResultReadyEventValidator().validate(event, ValidationContext(context))
    vr.assert_no_failures()


def assert_condition_valid(
    condition: object,
    context: str = "JoiningSystemCondition",
) -> None:
    """
    Validate a JoiningSystemConditionType condition and raise AssertionError if
    invalid.

    :param condition: The asyncua condition object received from a subscription callback.
    :param context:   Human-readable label used as the root path in failure messages.
    :raises AssertionError: If one or more validation failures are found.
    """
    vr = JoiningSystemConditionValidator().validate(condition, ValidationContext(context))
    vr.assert_no_failures()
