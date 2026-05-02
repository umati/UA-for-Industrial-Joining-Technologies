"""
helpers/result_validator.py — Reusable validators for IJT OPC UA result data types.

Design:
  - All validators are dataclasses or named classes with a .validate(data, ctx, vr) method.
  - ValidationContext tracks the dot-path to the current object for readable failure messages.
  - Validators return nothing; they append ValidationFailure entries to a shared ValidationResult.
  - Callers invoke vr.assert_no_failures() when done to raise AssertionError if any failures found.
  - Validators handle missing attributes gracefully via getattr(..., None) for optional fields.
  - All validators are independent and composable.

Usage example::

    from helpers.result_validator import ResultDataValidator, assert_result_data_valid

    # Simple one-shot assertion:
    assert_result_data_valid(result_data, context="SendResult event")

    # Or manual flow for custom checks:
    vr = ResultDataValidator().validate(result_data)
    vr.add("custom_check", "my extra assertion") if my_condition else None
    vr.assert_no_failures()
"""

from __future__ import annotations

from dataclasses import dataclass

from helpers.namespaces import ResultClassification, ResultEvaluation

# ---------------------------------------------------------------------------
# Valid ranges for ResultValueDataType enumerations (OPC 40450-1 §9)
# ---------------------------------------------------------------------------

# ValueTagEnumeration: 0=UNDEFINED … 20=PULSE_COUNT
_VALID_VALUE_TAGS: set[int] = set(range(21))

# PhysicalQuantityEnumeration: 0=OTHER … 28=TORQUE_PER_ANGLE_GRADIENT2
_VALID_PHYSICAL_QUANTITIES: set[int] = set(range(29))

# ViolationTypeEnumeration: 0=UNDEFINED, 1=HIGH, 2=LOW, 3=OTHER
_VALID_VIOLATION_TYPES: set[int] = {0, 1, 2, 3}

# ErrorTypeEnumeration: 0=UNDEFINED, 1=OTHER, 2=HARDWARE, 3=PROCESS,
# 4=OPERATOR, 5=SYSTEM, 6=SAFETY
_VALID_ERROR_TYPES: set[int] = set(range(7))

# EntityTypeEnumeration per OPC 40450-1 v100 §10.10 — values 0–42 defined in the spec.
# 0=UNDEFINED, 1=OTHER, 2=ASSET, 3=CONTROLLER, 4=TOOL, 5=SERVO, 6=MEMORY_DEVICE,
# 7=SENSOR, 8=CABLE, 9=BATTERY, 10=POWER_SUPPLY, 11=FEEDER, 12=ACCESSORY,
# 13=SUB_COMPONENT, 14=SOFTWARE, 15=RESULT, 16=EVENT, 17=ERROR, 18=SYSTEM,
# 19=LOG, 20=VEHICLE, 21=PRODUCT, 22=PART, 23=JOINT, 24=MODEL, 25=ORDER,
# 26=JOINING_PROCESS, 27=PROGRAM, 28=JOB, 29=BATCH, 30=RECIPE, 31=TASK,
# 32=PROCESS, 33=CONFIGURATION, 34=SOCKET, 35=CHANNEL, 36=STATION,
# 37=PRODUCTION_LINE, 38=LOCATION, 39=USER, 40=PARENT, 41=VIRTUAL_STATION,
# 42=JOINT_COMPONENT
_VALID_ENTITY_TYPES: set[int] = set(range(43))  # 0–42 per OPC 40450-1 v100 spec
_ENTITY_TYPE_STRICT_MAX: int = 42  # warn but do not fail above this; spec may extend it

# EntityTypes that represent a JoiningProcess reference in AssociatedEntities.
# JoiningProcessId is stored as AssociatedEntities[].EntityId where EntityType is one of:
#   27=PROGRAM  → Single Result links to a Joining Program
#   29=BATCH    → Batch Result links to a Joining Batch
#   28=JOB      → Job Result links to a Joining Job
#   26=JOINING_PROCESS → generic / sync / when no finer classification is available
_JOINING_PROCESS_ENTITY_TYPES: frozenset[int] = frozenset({26, 27, 28, 29})

# FailureReasonEnumeration: 0=NOT_OK_UNDEFINED, 1=PROGRAM, 2=STEP, 3=ERROR
_VALID_FAILURE_REASONS: set[int] = {0, 1, 2, 3}

# ResultClassification values that indicate a *combined* result
# (SINGLE_RESULT=1 must never appear on a ConsolidatedResultDataType)
_COMBINED_CLASSIFICATIONS: set[int] = {2, 3, 4, 5, 6, 7}


# ---------------------------------------------------------------------------
# ValidationContext
# ---------------------------------------------------------------------------


class ValidationContext:
    """
    Tracks the dot-path to the object currently being validated.

    Example path: ``"ResultMetaData.OverallResultValues[2].MeasuredValue"``
    """

    def __init__(self, path: str = "root") -> None:
        self.path = path

    def child(self, name: str) -> ValidationContext:
        """Return a new context for a named child attribute."""
        return ValidationContext(f"{self.path}.{name}")

    def index(self, i: int) -> ValidationContext:
        """Return a new context for a list element at index *i*."""
        return ValidationContext(f"{self.path}[{i}]")

    def __str__(self) -> str:
        return self.path


# ---------------------------------------------------------------------------
# ValidationFailure / ValidationResult
# ---------------------------------------------------------------------------


@dataclass
class ValidationFailure:
    """A single validation failure with its location path and human-readable message."""

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


class ValidationResult:
    """Collects all failures from a validation pass (soft-assertion style)."""

    def __init__(self) -> None:
        self.failures: list[ValidationFailure] = []

    @property
    def ok(self) -> bool:
        """True when no hard failures have been recorded (advisory notes do not count)."""
        return not any("#advisory" not in str(f.path) for f in self.failures)

    def add(self, path: str | ValidationContext, message: str) -> None:
        """Append a new failure."""
        self.failures.append(ValidationFailure(str(path), message))

    def merge(self, other: ValidationResult) -> None:
        """Merge all failures from *other* into this result."""
        self.failures.extend(other.failures)

    def assert_no_failures(self) -> None:
        """Raise AssertionError listing every hard failure if any were recorded.

        Entries whose path contains ``#advisory`` are informational only and
        do not cause a test failure — they appear in the error message of a
        *separate* call to ``assert_no_advisory_issues`` if callers want them.
        """
        hard = [f for f in self.failures if "#advisory" not in str(f.path)]
        if hard:
            lines = "\n  ".join(str(f) for f in hard)
            advisory = [f for f in self.failures if "#advisory" in str(f.path)]
            suffix = f"\n  ({len(advisory)} advisory note(s) suppressed)" if advisory else ""
            raise AssertionError(f"{len(hard)} validation failure(s):\n  {lines}{suffix}")

    def assert_no_advisory_issues(self) -> None:
        """Raise AssertionError if any advisory notes were recorded (opt-in strict mode)."""
        advisory = [f for f in self.failures if "#advisory" in str(f.path)]
        if advisory:
            lines = "\n  ".join(str(f) for f in advisory)
            raise AssertionError(f"{len(advisory)} advisory note(s):\n  {lines}")


# ---------------------------------------------------------------------------
# ResultValueValidator
# ---------------------------------------------------------------------------


class ResultValueValidator:
    """Validates a single ``ResultValueDataType`` object."""

    def validate(
        self,
        value: object,
        ctx: ValidationContext,
        vr: ValidationResult,
    ) -> None:
        """
        Check:
        - ``MeasuredValue`` is numeric (required).
        - ``ValueTag`` is in {0..20} if present.
        - ``PhysicalQuantity`` is in {0..28} if present.
        - ``ViolationType`` is in {0,1,2,3} if present.
        - ``EngineeringUnits`` has a ``.UnitId`` attribute if present.
        """
        # MeasuredValue — required, must be numeric
        measured = getattr(value, "MeasuredValue", _MISSING)
        if measured is _MISSING:
            vr.add(ctx.child("MeasuredValue"), "required field is absent")
        elif not isinstance(measured, (int, float)):
            vr.add(
                ctx.child("MeasuredValue"),
                f"expected numeric type, got {type(measured).__name__!r} (value={measured!r})",
            )

        # ValueTag — optional, must be in valid range
        value_tag = getattr(value, "ValueTag", None)
        if value_tag is not None:
            try:
                tag_int = int(value_tag)
            except (TypeError, ValueError):
                tag_int = None
            if tag_int is None or tag_int not in _VALID_VALUE_TAGS:
                vr.add(
                    ctx.child("ValueTag"),
                    f"expected int in {{0..20}}, got {value_tag!r}",
                )

        # PhysicalQuantity — optional, must be in valid range
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

        # ViolationType — optional, must be in valid range
        violation = getattr(value, "ViolationType", None)
        if violation is not None:
            try:
                viol_int = int(violation)
            except (TypeError, ValueError):
                viol_int = None
            if viol_int is None or viol_int not in _VALID_VIOLATION_TYPES:
                vr.add(
                    ctx.child("ViolationType"),
                    f"expected int in {{0,1,2,3}}, got {violation!r}",
                )

        # EngineeringUnits — optional, but if present must expose .UnitId
        eu = getattr(value, "EngineeringUnits", None)
        eu = getattr(eu, "Value", eu) if eu is not None else None  # unwrap Variant → EUInformation
        if eu is not None and not hasattr(eu, "UnitId"):
            vr.add(
                ctx.child("EngineeringUnits"),
                "present but has no .UnitId attribute (expected EUInformation)",
            )


# ---------------------------------------------------------------------------
# StepResultValidator
# ---------------------------------------------------------------------------


class StepResultValidator:
    """Validates a single ``StepResultDataType`` object."""

    def __init__(self) -> None:
        self._value_validator = ResultValueValidator()

    def validate(
        self,
        step: object,
        ctx: ValidationContext,
        vr: ValidationResult,
    ) -> None:
        """
        Check:
        - ``StepResultId`` is a non-empty string (required).
        - ``StepResultValues`` is a list (may be empty).
        - Each entry in ``StepResultValues`` passes ``ResultValueValidator``.
        """
        # StepResultId — required, non-empty string
        step_id = getattr(step, "StepResultId", _MISSING)
        if step_id is _MISSING:
            vr.add(ctx.child("StepResultId"), "required field is absent")
        elif not isinstance(step_id, str) or not step_id.strip():
            vr.add(
                ctx.child("StepResultId"),
                f"expected non-empty string, got {step_id!r}",
            )

        # StepResultValues — should be a list
        values = getattr(step, "StepResultValues", None)
        if values is not None:
            if not isinstance(values, (list, tuple)):
                vr.add(
                    ctx.child("StepResultValues"),
                    f"expected list, got {type(values).__name__!r}",
                )
            else:
                values_ctx = ctx.child("StepResultValues")
                for i, v in enumerate(values):
                    v = getattr(v, "Value", v)
                    self._value_validator.validate(v, values_ctx.index(i), vr)


# ---------------------------------------------------------------------------
# ErrorInformationValidator
# ---------------------------------------------------------------------------


class ErrorInformationValidator:
    """Validates a single ``ErrorInformationDataType`` object."""

    def validate(
        self,
        error: object,
        ctx: ValidationContext,
        vr: ValidationResult,
    ) -> None:
        """
        Check:
        - ``ErrorType`` is in {0..6} (required).
        - ``ErrorId``, ``LegacyError``, and ``ErrorMessage`` are optional.
        """
        # ErrorType — required by ErrorInformationDataType
        error_type = getattr(error, "ErrorType", _MISSING)
        if error_type is _MISSING:
            vr.add(ctx.child("ErrorType"), "required field is absent")
        else:
            try:
                type_int = int(error_type)
            except (TypeError, ValueError):
                type_int = None
            if type_int is None or type_int not in _VALID_ERROR_TYPES:
                vr.add(
                    ctx.child("ErrorType"),
                    f"expected int in {{0..6}}, got {error_type!r}",
                )


# ---------------------------------------------------------------------------
# ResultMetaDataValidator
# ---------------------------------------------------------------------------


class ResultMetaDataValidator:
    """Validates a ``ResultMetaDataType`` object."""

    def __init__(self) -> None:
        self._value_validator = ResultValueValidator()

    def validate(
        self,
        meta: object,
        ctx: ValidationContext,
        vr: ValidationResult,
    ) -> None:
        """
        Check all required and optional fields on ``ResultMetaDataType``.

        Required:
        - ``ResultId`` — non-empty string.
        - ``Classification`` — in ``ResultClassification.VALID_VALUES``.
        - ``ResultEvaluation`` — in ``ResultEvaluation.VALID_VALUES``.
        - ``CreationTime`` — not None.

        Optional range checks:
        - ``NumberOfResultContent`` >= 0.
        - ``SequenceNumber`` >= 0.
        - ``OverallResultValues`` — each entry validated via ``ResultValueValidator``.
        - ``AssociatedEntities`` — each entry: ``EntityId`` non-empty, ``EntityType`` in {0..42}.
        """
        # ResultId — required, non-empty string
        result_id = getattr(meta, "ResultId", _MISSING)
        if result_id is _MISSING:
            vr.add(ctx.child("ResultId"), "required field is absent")
        elif not isinstance(result_id, str) or not result_id.strip():
            vr.add(
                ctx.child("ResultId"),
                f"expected non-empty string, got {result_id!r}",
            )

        # Classification — required, must be in valid enum range
        classification = getattr(meta, "Classification", _MISSING)
        if classification is _MISSING:
            vr.add(ctx.child("Classification"), "required field is absent")
        else:
            try:
                cls_int = int(classification)
            except (TypeError, ValueError):
                cls_int = None
            if cls_int is None or cls_int not in ResultClassification.VALID_VALUES:
                vr.add(
                    ctx.child("Classification"),
                    f"expected int in {sorted(ResultClassification.VALID_VALUES)}, got {classification!r}",
                )

        # ResultEvaluation — required, must be in valid enum range
        evaluation = getattr(meta, "ResultEvaluation", _MISSING)
        if evaluation is _MISSING:
            vr.add(ctx.child("ResultEvaluation"), "required field is absent")
        else:
            try:
                eval_int = int(evaluation)
            except (TypeError, ValueError):
                eval_int = None
            if eval_int is None or eval_int not in ResultEvaluation.VALID_VALUES:
                vr.add(
                    ctx.child("ResultEvaluation"),
                    f"expected int in {sorted(ResultEvaluation.VALID_VALUES)}, got {evaluation!r}",
                )

        # CreationTime — required, must not be None
        creation_time = getattr(meta, "CreationTime", _MISSING)
        if creation_time is _MISSING:
            vr.add(ctx.child("CreationTime"), "required field is absent")
        elif creation_time is None:
            vr.add(ctx.child("CreationTime"), "must not be None")

        # NumberOfResultContent — optional, must be >= 0
        num_content = getattr(meta, "NumberOfResultContent", None)
        if num_content is not None:
            try:
                num_int = int(num_content)
            except (TypeError, ValueError):
                num_int = -1
            if num_int < 0:
                vr.add(
                    ctx.child("NumberOfResultContent"),
                    f"expected non-negative integer, got {num_content!r}",
                )

        # SequenceNumber — optional, must be >= 0
        seq_num = getattr(meta, "SequenceNumber", None)
        if seq_num is not None:
            try:
                seq_int = int(seq_num)
            except (TypeError, ValueError):
                seq_int = -1
            if seq_int < 0:
                vr.add(
                    ctx.child("SequenceNumber"),
                    f"expected non-negative integer, got {seq_num!r}",
                )

        # OverallResultValues — optional list; validate each entry
        overall_values = getattr(meta, "OverallResultValues", None)
        if overall_values is not None and isinstance(overall_values, (list, tuple)):
            ov_ctx = ctx.child("OverallResultValues")
            for i, v in enumerate(overall_values):
                v = getattr(v, "Value", v)
                self._value_validator.validate(v, ov_ctx.index(i), vr)

        # AssociatedEntities — optional list; validate EntityId and EntityType per entry
        entities = getattr(meta, "AssociatedEntities", None)
        if entities is not None and isinstance(entities, (list, tuple)):
            ent_ctx = ctx.child("AssociatedEntities")
            for i, entity in enumerate(entities):
                entity = getattr(entity, "Value", entity)
                e_ctx = ent_ctx.index(i)
                entity_id = getattr(entity, "EntityId", _MISSING)
                if entity_id is _MISSING:
                    vr.add(e_ctx.child("EntityId"), "required field is absent")
                elif not isinstance(entity_id, str) or not entity_id.strip():
                    vr.add(
                        e_ctx.child("EntityId"),
                        f"expected non-empty string, got {entity_id!r}",
                    )
                entity_type = getattr(entity, "EntityType", None)
                if entity_type is not None:
                    try:
                        et_int = int(entity_type)
                    except (TypeError, ValueError):
                        et_int = None
                    if et_int is None:
                        vr.add(
                            e_ctx.child("EntityType"),
                            f"could not interpret EntityType as integer, got {entity_type!r}",
                        )
                    elif et_int not in _VALID_ENTITY_TYPES:
                        # Values beyond current spec max are advisory: vendor may extend the enum
                        vr.add(
                            e_ctx.child("EntityType#advisory"),
                            f"EntityType {et_int} is beyond currently defined spec max "
                            f"({_ENTITY_TYPE_STRICT_MAX}); may be vendor extension — treating as advisory",
                        )


# ---------------------------------------------------------------------------
# JoiningResultDataValidator
# ---------------------------------------------------------------------------


class JoiningResultDataValidator:
    """Validates a single ``JoiningResultDataType`` object."""

    def __init__(self) -> None:
        self._value_validator = ResultValueValidator()
        self._step_validator = StepResultValidator()
        self._error_validator = ErrorInformationValidator()

    def validate(
        self,
        joining_result: object,
        ctx: ValidationContext,
        vr: ValidationResult,
    ) -> None:
        """
        Check:
        - Each ``OverallResultValues`` entry passes ``ResultValueValidator``.
        - Each ``StepResults`` entry passes ``StepResultValidator``.
        - Each ``Errors`` entry passes ``ErrorInformationValidator``.
        - Emit a diagnostic note (non-failure) when no ``OverallResultValues`` entry has
          ``ValueTag == 1`` (FINAL) — conformance tests may optionally check this separately.
        """
        # FailureReason — optional on JoiningResultDataType, must be in valid range
        failure_reason = getattr(joining_result, "FailureReason", None)
        if failure_reason is not None:
            try:
                reason_int = int(failure_reason)
            except (TypeError, ValueError):
                reason_int = None
            if reason_int is None or reason_int not in _VALID_FAILURE_REASONS:
                vr.add(
                    ctx.child("FailureReason"),
                    f"expected int in {{0,1,2,3}}, got {failure_reason!r}",
                )

        # OverallResultValues — optional list; validate each entry
        overall_values = getattr(joining_result, "OverallResultValues", None)
        has_final_tag = False
        if overall_values is not None and isinstance(overall_values, (list, tuple)):
            ov_ctx = ctx.child("OverallResultValues")
            for i, v in enumerate(overall_values):
                v = getattr(v, "Value", v)
                self._value_validator.validate(v, ov_ctx.index(i), vr)
                vt = getattr(v, "ValueTag", None)
                if vt is not None:
                    try:
                        if int(vt) == 1:  # ValueTag.FINAL
                            has_final_tag = True
                    except (TypeError, ValueError):
                        pass

            # Advisory: at least one FINAL value is recommended per spec
            if overall_values and not has_final_tag:
                # Recorded as an informational failure so callers can decide severity.
                # Use a distinct path suffix so callers can filter on it if desired.
                vr.add(
                    ctx.child("OverallResultValues#advisory"),
                    "no entry with ValueTag=1 (FINAL) found; recommended by OPC 40450-1 §9",
                )

        # StepResults — optional list; validate each entry
        step_results = getattr(joining_result, "StepResults", None)
        if step_results is not None and isinstance(step_results, (list, tuple)):
            sr_ctx = ctx.child("StepResults")
            for i, step in enumerate(step_results):
                step = getattr(step, "Value", step)
                self._step_validator.validate(step, sr_ctx.index(i), vr)

        # Errors — optional list; validate each entry
        errors = getattr(joining_result, "Errors", None)
        if errors is not None and isinstance(errors, (list, tuple)):
            err_ctx = ctx.child("Errors")
            for i, error in enumerate(errors):
                error = getattr(error, "Value", error)
                self._error_validator.validate(error, err_ctx.index(i), vr)


# ---------------------------------------------------------------------------
# ResultDataValidator
# ---------------------------------------------------------------------------


class ResultDataValidator:
    """Validates a complete ``ResultDataType`` object (metadata + content)."""

    def __init__(self) -> None:
        self._meta_validator = ResultMetaDataValidator()
        self._joining_validator = JoiningResultDataValidator()

    def validate(
        self,
        result_data: object,
        ctx: ValidationContext | None = None,
    ) -> ValidationResult:
        """
        Validate ``result_data`` and return a ``ValidationResult``.

        Callers should call ``vr.assert_no_failures()`` to turn failures into an
        ``AssertionError``, or inspect ``vr.failures`` directly.

        Validates:
        - ``ResultMetaData`` via ``ResultMetaDataValidator`` (required).
        - Each ``ResultContent`` entry via ``JoiningResultDataValidator``.
        """
        vr = ValidationResult()
        ctx = ctx or ValidationContext("ResultDataType")

        # ResultMetaData — required
        meta = getattr(result_data, "ResultMetaData", _MISSING)
        if meta is _MISSING or meta is None:
            vr.add(ctx.child("ResultMetaData"), "required field is absent or None")
        else:
            self._meta_validator.validate(meta, ctx.child("ResultMetaData"), vr)

        # ResultContent — optional list; validate each entry
        content = getattr(result_data, "ResultContent", None)
        if content is not None and isinstance(content, (list, tuple)):
            rc_ctx = ctx.child("ResultContent")
            for i, joining_result in enumerate(content):
                joining_result = getattr(joining_result, "Value", joining_result)
                self._joining_validator.validate(joining_result, rc_ctx.index(i), vr)

        return vr


# ---------------------------------------------------------------------------
# ConsolidatedResultValidator
# ---------------------------------------------------------------------------


class ConsolidatedResultValidator:
    """
    Validates a ``ConsolidatedResultDataType`` object (Batch/Sync/Job/Stitching results).

    A consolidated result wraps multiple joining results either inline
    (``ResultContent``) or by reference (``References``).
    """

    def __init__(self) -> None:
        self._meta_validator = ResultMetaDataValidator()
        self._joining_validator = JoiningResultDataValidator()

    def validate(
        self,
        result: object,
        ctx: ValidationContext | None = None,
    ) -> ValidationResult:
        """
        Validate ``result`` as a ``ConsolidatedResultDataType``.

        Rules:
        - ``ResultMetaData`` must be present and valid.
        - ``Classification`` must be in {2,3,4,5,6,7} (never SINGLE_RESULT=1).
        - If ``ResultContent`` is non-empty, validate each entry via ``JoiningResultDataValidator``.
        - If ``References`` is non-empty, each reference must have a non-empty ``ResultId``.
        - At least one of ``ResultContent`` or ``References`` must be populated,
          unless ``IsPartial=True`` (partial results may arrive before content is complete).
        """
        vr = ValidationResult()
        ctx = ctx or ValidationContext("ConsolidatedResultDataType")

        # ResultMetaData — required
        meta = getattr(result, "ResultMetaData", _MISSING)
        if meta is _MISSING or meta is None:
            vr.add(ctx.child("ResultMetaData"), "required field is absent or None")
        else:
            self._meta_validator.validate(meta, ctx.child("ResultMetaData"), vr)

            # Classification must be a combined type (not SINGLE_RESULT)
            classification = getattr(meta, "Classification", None)
            if classification is not None:
                try:
                    cls_int = int(classification)
                except (TypeError, ValueError):
                    cls_int = None
                if cls_int is not None and cls_int not in _COMBINED_CLASSIFICATIONS:
                    vr.add(
                        ctx.child("ResultMetaData.Classification"),
                        f"consolidated result must have Classification in "
                        f"{sorted(_COMBINED_CLASSIFICATIONS)} (not SINGLE_RESULT=1 or UNDEFINED=0), "
                        f"got {classification!r}",
                    )

        # ResultContent — optional inline sub-results
        content = getattr(result, "ResultContent", None)
        content_list: list = list(content) if isinstance(content, (list, tuple)) else []
        if content_list:
            rc_ctx = ctx.child("ResultContent")
            for i, joining_result in enumerate(content_list):
                joining_result = getattr(joining_result, "Value", joining_result)
                self._joining_validator.validate(joining_result, rc_ctx.index(i), vr)

        # References — optional reference-only sub-results
        references = getattr(result, "References", None)
        ref_list: list = list(references) if isinstance(references, (list, tuple)) else []
        if ref_list:
            ref_ctx = ctx.child("References")
            for i, ref in enumerate(ref_list):
                ref = getattr(ref, "Value", ref)
                ref_id = getattr(ref, "ResultId", _MISSING)
                if ref_id is _MISSING:
                    vr.add(ref_ctx.index(i).child("ResultId"), "required field is absent")
                elif not isinstance(ref_id, str) or not ref_id.strip():
                    vr.add(
                        ref_ctx.index(i).child("ResultId"),
                        f"expected non-empty string, got {ref_id!r}",
                    )

        # At least one of ResultContent or References must be populated,
        # unless IsPartial=True allows an empty-so-far consolidated result.
        is_partial = getattr(result, "IsPartial", False)
        if not content_list and not ref_list and not is_partial:
            vr.add(
                ctx,
                "consolidated result has neither ResultContent nor References "
                "(set IsPartial=True if content is expected later)",
            )

        return vr


# ---------------------------------------------------------------------------
# Sentinel for missing required attributes
# ---------------------------------------------------------------------------


class _MissingSentinel:
    """Sentinel object that evaluates as falsy; used to detect absent attributes."""

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "<MISSING>"


_MISSING = _MissingSentinel()


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


def assert_result_data_valid(result_data: object, context: str = "result") -> None:
    """
    Validate a ``ResultDataType`` and raise ``AssertionError`` if invalid.

    :param result_data: The deserialized OPC UA ``ResultDataType`` object.
    :param context:     Human-readable label used as the root path in failure messages.
    """
    vr = ResultDataValidator().validate(result_data, ValidationContext(context))
    vr.assert_no_failures()


def assert_result_meta_data_valid(meta: object, context: str = "ResultMetaData") -> None:
    """
    Validate a ``ResultMetaDataType`` and raise ``AssertionError`` if invalid.

    :param meta:    The deserialized OPC UA ``ResultMetaDataType`` object.
    :param context: Human-readable label used as the root path in failure messages.
    """
    vr = ValidationResult()
    ResultMetaDataValidator().validate(meta, ValidationContext(context), vr)
    vr.assert_no_failures()


def assert_result_value_valid(value: object, context: str = "ResultValue") -> None:
    """
    Validate a single ``ResultValueDataType`` and raise ``AssertionError`` if invalid.

    :param value:   The deserialized OPC UA ``ResultValueDataType`` object.
    :param context: Human-readable label used as the root path in failure messages.
    """
    vr = ValidationResult()
    ResultValueValidator().validate(value, ValidationContext(context), vr)
    vr.assert_no_failures()
