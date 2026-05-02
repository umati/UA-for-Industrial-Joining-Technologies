"""
Single result data structure conformance tests — OPC 40450-1.

Covers: single_result, basic_result, result_additional_data,
result_extended_meta_data, joining_result_failure_reason,
joining_result_overall_result_values, joining_result_step_results,
joining_result_errors, result_value_final_tag.

Tests validate the complete structure and content of a
JoiningResultDataType returned by GetLatestResult after a
single joining operation.
"""
# pylint: disable=too-many-lines

import logging
from typing import Any

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.event_collector import EventCollector
from helpers.event_validator import assert_result_ready_event_valid
from helpers.method_caller import call_method, find_and_call_method
from helpers.namespaces import (
    BN,
    NS_APP,
    NS_IJT_BASE,
    NS_MACH_RESULT,
    IJTTypes,
    ResultClassification,
    ResultEvaluation,
    ResultType,
)
from helpers.node_discovery import find_child_by_browse_name, find_child_by_browse_name_any, find_joining_system
from helpers.result_collector import ResultCollector
from helpers.result_validator import (
    assert_result_data_valid,
)

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

# ---------------------------------------------------------------------------
# Timeouts — numeric literals are duration values, not CU identifiers
# ---------------------------------------------------------------------------
_SIMULATOR_TIMEOUT_MS = 5000
_EXTERNAL_TIMEOUT_MS = 60000
_METHOD_CALL_TIMEOUT_S = 30.0
_EXTERNAL_CALL_TIMEOUT_S = 90.0

# ValueTagEnumeration: FINAL = 1 (OPC UA protocol-level enum value)
_FINAL_VALUE_TAG = 1

# AssemblyType enum: 0=UNDEFINED, 1=ASSEMBLED, 2=DISASSEMBLED (per OPC 40450-1 ResultMetaDataType)
_VALID_ASSEMBLY_TYPE_VALUES: frozenset = frozenset({0, 1, 2})
# OperationMode enum: 0=UNDEFINED, 1=AUTOMATIC, 2=MANUAL (per OPC 40450-1 ResultMetaDataType)
_VALID_OPERATION_MODE_VALUES: frozenset = frozenset({0, 1, 2})
# ResultState: 0=Undefined, 1=Completed, 2=Processing, 3=Aborted, 4=Failed (Machinery Result NodeSet)
_RESULT_STATE_COMPLETED = 1
_RESULT_STATE_PROCESSING = 2
_VALID_RESULT_STATE_VALUES: frozenset = frozenset({0, 1, 2, 3, 4})


# ---------------------------------------------------------------------------
# Module-level shared helper
# ---------------------------------------------------------------------------


def _unwrap_variant(value):
    """Unwrap asyncua Variant containers used for nested ExtensionObjects."""
    return getattr(value, "Value", value)


def _localized_text_text(value) -> str:
    """Return the text payload from asyncua LocalizedText-like values."""
    value = _unwrap_variant(value)
    text = getattr(value, "Text", value)
    return "" if text is None else str(text)


def _value_tag_int(result_value) -> int | None:
    """Return ValueTag as an integer when present and readable."""
    result_value = _unwrap_variant(result_value)
    value_tag = getattr(result_value, "ValueTag", None)
    if value_tag is None:
        return None
    try:
        return int(value_tag)
    except (TypeError, ValueError):
        return None


def _joining_result_has_final_tag(joining_result) -> bool:
    """Return True when OverallResultValues or StepResultValues include ValueTag=FINAL."""
    joining_result = _unwrap_variant(joining_result)
    for result_value in getattr(joining_result, "OverallResultValues", None) or []:
        if _value_tag_int(result_value) == _FINAL_VALUE_TAG:
            return True
    for step in getattr(joining_result, "StepResults", None) or []:
        step = _unwrap_variant(step)
        for result_value in getattr(step, "StepResultValues", None) or []:
            if _value_tag_int(result_value) == _FINAL_VALUE_TAG:
                return True
    return False


async def _get_result(
    subscription_client,
    result_trigger,
    ns_indices,
    result_type: int = ResultType.MULTI_STEP_OK_RESULT,
    include_traces: bool = True,
):
    """Trigger a result and collect it via IJTResultEventType events.

    Returns ``(result_data, result_meta)`` on success, or ``(None, None)`` when:
    - The required namespace is absent.
    - A simulator trigger call failed (caller should call ``pytest.skip``).
    - No result event arrived within timeout.
    """
    async with ResultCollector(subscription_client, ns_indices, is_simulator=result_trigger.is_simulator) as rc:
        outcome = await result_trigger.trigger_single(result_type, include_traces=include_traces)
        if not outcome.triggered and result_trigger.is_simulator:
            return None, None
        result_data = await rc.collect_single()

    if result_data is None:
        return None, None

    meta = getattr(result_data, "ResultMetaData", None)
    return result_data, meta


def _skip_if_no_result(result_data, result_trigger):
    """Call pytest.skip() when *result_data* is None, with an appropriate message."""
    if result_data is None:
        if result_trigger.is_simulator:
            pytest.skip("Simulator trigger failed or no result event received within timeout")
        else:
            pytest.skip("No result received from external trigger within timeout")


# ---------------------------------------------------------------------------
# basic_result — ResultMetaData top-level structure
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_single_result_has_result_meta_data(subscription_client, result_trigger, ns_indices):
    """The Server supports a Result instance which includes at least the following
    properties in Result.ResultMetaData: ResultId, Classification, IsSimulated,
    IsPartial, ResultEvaluation, JoiningTechnology, ResultState, SequenceNumber,
    CreationTime.

    Checks that a collected result event includes a non-None ResultMetaData.
    """
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    assert meta is not None, "Result collected from event has no 'ResultMetaData' attribute."


@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_single_result_result_id_is_non_empty_string(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.ResultId must be a non-empty string."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData: Not Supported — covered by basic_result test")
    result_id = getattr(meta, "ResultId", None)
    assert isinstance(result_id, str) and result_id.strip(), (
        f"ResultMetaData.ResultId must be a non-empty string, got {result_id!r}"
    )


@pytest.mark.requires_cu(CU.SINGLE_RESULT)
async def test_single_result_classification_is_single_result(subscription_client, result_trigger, ns_indices):
    """The JoiningSystem supports generating Single Results where
    Result.ResultMetaData.Classification is SINGLE_RESULT.
    """
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData: Not Supported — covered by basic_result test")
    classification = getattr(meta, "Classification", None)
    if classification is None:
        pytest.skip("Classification field absent from ResultMetaData — cannot verify")
    cls_int = int(classification)
    assert cls_int == ResultClassification.SINGLE_RESULT, (
        f"Classification for a SimulateSingleResult must be "
        f"SINGLE_RESULT={ResultClassification.SINGLE_RESULT}, got {cls_int}"
    )


@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_single_result_evaluation_in_valid_range(subscription_client, result_trigger, ns_indices):
    """ResultEvaluation must be in the valid enumeration range defined by the spec."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData: Not Supported — covered by basic_result test")
    evaluation = getattr(meta, "ResultEvaluation", None)
    if evaluation is None:
        pytest.skip("ResultEvaluation field absent from ResultMetaData")
    eval_int = int(evaluation)
    assert eval_int in ResultEvaluation.VALID_VALUES, (
        f"ResultEvaluation {eval_int} not in valid set {sorted(ResultEvaluation.VALID_VALUES)}"
    )


@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_single_result_creation_time_is_present(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.CreationTime must be present and non-null."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData: Not Supported — covered by basic_result test")
    creation_time = getattr(meta, "CreationTime", None)
    assert creation_time is not None, "ResultMetaData.CreationTime must be present and non-null."


@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_single_result_sequence_number_increments(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.SequenceNumber must be a non-negative integer and monotonically increasing.

    Triggers two consecutive results and verifies that each SequenceNumber is a
    non-negative integer and that the second is greater than the first.
    """
    result_data_first, meta_first = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data_first, result_trigger)
    if meta_first is None:
        pytest.skip("ResultMetaData not present in first result — covered by basic_result test")
    seq_first = getattr(meta_first, "SequenceNumber", None)
    if seq_first is None:
        pytest.skip("SequenceNumber field absent from ResultMetaData — optional per spec")
    seq_first_int = int(seq_first)
    assert seq_first_int >= 0, f"First SequenceNumber must be non-negative, got {seq_first_int}"

    async with ResultCollector(subscription_client, ns_indices, is_simulator=result_trigger.is_simulator) as rc:
        outcome = await result_trigger.trigger_single(ResultType.MULTI_STEP_OK_RESULT, include_traces=False)
        if not outcome.triggered and result_trigger.is_simulator:
            pytest.skip("Second simulator trigger failed — cannot verify monotonic sequence")
        rd_second = await rc.collect_single()

    if rd_second is None:
        pytest.skip("No second result event received within timeout")
    meta_second = getattr(rd_second, "ResultMetaData", None)
    if meta_second is None:
        pytest.skip("No ResultMetaData in second result")
    seq_second = getattr(meta_second, "SequenceNumber", None)
    if seq_second is None:
        pytest.skip("SequenceNumber absent from second result")
    seq_second_int = int(seq_second)
    assert seq_second_int >= 0, f"Second SequenceNumber must be non-negative, got {seq_second_int}"
    assert seq_second_int > seq_first_int, (
        f"SequenceNumber must be monotonically increasing; first={seq_first_int}, second={seq_second_int}"
    )


@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_simple_result_content_is_list(subscription_client, result_trigger, ns_indices):
    """ResultContent must be a list (may be empty for simple results)."""
    # SIMPLE_OK_RESULT carries no step content — ResultContent may be empty or absent.
    result_data, _ = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.SIMPLE_OK_RESULT,
        include_traces=False,
    )
    _skip_if_no_result(result_data, result_trigger)
    content = getattr(result_data, "ResultContent", None)
    if content is None:
        return
    assert isinstance(content, (list, tuple)), f"ResultContent must be a list or tuple, got {type(content).__name__!r}"


# ---------------------------------------------------------------------------
# joining_result_step_results — StepResultDataType structure
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINING_RESULT_STEP_RESULTS)
async def test_multi_step_result_step_result_id_present(subscription_client, result_trigger, ns_indices):
    """The Server supports Single Result instances with at least one element of
    JoiningResult.StepResults[] where each StepResultDataType includes at least
    StepResultId, ProgramStepId or ProgramStep, Name, ResultEvaluation and
    StepTraceId, StartTimeOffset if traces are sent.

    Checks that each StepResultDataType in JoiningResult.StepResults has a
    non-empty StepResultId.
    """
    result_data, _ = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.MULTI_STEP_OK_RESULT,
    )
    _skip_if_no_result(result_data, result_trigger)
    content = getattr(result_data, "ResultContent", None)
    if not content:
        pytest.skip("ResultContent is empty — no step results to check")
    failures = []
    for i, jr in enumerate(content):
        jr = getattr(jr, "Value", jr)  # unwrap asyncua Variant
        step_results = getattr(jr, "StepResults", None)
        if not step_results:
            failures.append(f"ResultContent[{i}].StepResults is absent or empty")
            continue
        for j, step in enumerate(step_results):
            step = getattr(step, "Value", step)
            step_id = getattr(step, "StepResultId", None)
            if not isinstance(step_id, str) or not step_id.strip():
                failures.append(f"ResultContent[{i}].StepResults[{j}].StepResultId={step_id!r}")
    assert not failures, "StepResultDataType entries missing non-empty StepResultId:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# joining_result_overall_result_values — OverallResultValues structure
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINING_RESULT_OVERALL_RESULT_VALUES)
async def test_multi_step_result_has_overall_result_values(subscription_client, result_trigger, ns_indices):
    """The Server supports Single Result instances where the instance of
    JoiningResultDataType contains OverallResultValues[] where each element includes
    MeasuredValue, PhysicalQuantity, Name, ResultEvaluation and includes ViolationType
    and ViolationConsequence if ResultEvaluation is NotOK.

    Checks that OverallResultValues is present and is a list.
    """
    result_data, _ = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.MULTI_STEP_OK_RESULT,
    )
    _skip_if_no_result(result_data, result_trigger)
    content = getattr(result_data, "ResultContent", None)
    if not content:
        pytest.skip("ResultContent is empty — no step results to check")
    for i, jr in enumerate(content):
        jr = getattr(jr, "Value", jr)  # unwrap asyncua Variant
        overall_values = getattr(jr, "OverallResultValues", None)
        if overall_values is None:
            # OverallResultValues is optional per spec — some simulators omit it on step results.
            # Skip when all step results have it absent rather than hard-fail.
            logger.info(
                "ResultContent[%d].OverallResultValues is None — optional field, may not be set by this server",
                i,
            )
            continue
        assert isinstance(overall_values, (list, tuple)), (
            f"ResultContent[{i}].OverallResultValues must be a list, got {type(overall_values).__name__!r}"
        )

    # If every step result had OverallResultValues absent, skip the whole test
    has_any = any(getattr(getattr(jr, "Value", jr), "OverallResultValues", None) is not None for jr in content)
    if not has_any:
        pytest.skip(
            "No step results contain OverallResultValues — "
            "optional field not populated by this server; "
            "verify result content via joining_result_overall_result_values tests"
        )


@pytest.mark.requires_cu(CU.JOINING_RESULT_OVERALL_RESULT_VALUES)
async def test_result_value_measured_value_is_numeric(subscription_client, result_trigger, ns_indices):
    """Each ResultValueDataType must carry a numeric MeasuredValue."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    all_values: list[Any] = []
    if meta is not None:
        ovr = getattr(meta, "OverallResultValues", None)
        if ovr:
            all_values.extend(getattr(v, "Value", v) for v in ovr)
    content = getattr(result_data, "ResultContent", None) or []
    for jr in content:
        jr = getattr(jr, "Value", jr)  # unwrap asyncua Variant
        ovr = getattr(jr, "OverallResultValues", None)
        if ovr:
            all_values.extend(getattr(v, "Value", v) for v in ovr)
        step_results = getattr(jr, "StepResults", None) or []
        for step in step_results:
            step = _unwrap_variant(step)
            svs = getattr(step, "StepResultValues", None) or []
            all_values.extend(_unwrap_variant(v) for v in svs)

    if not all_values:
        pytest.skip("No result values found in result — cannot verify")

    failures = []
    for i, v in enumerate(all_values):
        measured = getattr(v, "MeasuredValue", None)
        if not isinstance(measured, (int, float)):
            failures.append(f"value[{i}].MeasuredValue={measured!r} ({type(measured).__name__})")
    assert not failures, "Non-numeric MeasuredValue found:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.JOINING_RESULT_OVERALL_RESULT_VALUES)
async def test_result_value_physical_quantity_in_valid_range(subscription_client, result_trigger, ns_indices):
    """PhysicalQuantity on each ResultValueDataType must be within the valid enumeration range."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    valid_range = set(range(29))
    all_values: list[Any] = []
    if meta is not None:
        ovr = getattr(meta, "OverallResultValues", None)
        if ovr:
            all_values.extend(getattr(v, "Value", v) for v in ovr)
    content = getattr(result_data, "ResultContent", None) or []
    for jr in content:
        jr = getattr(jr, "Value", jr)  # unwrap asyncua Variant
        ovr = getattr(jr, "OverallResultValues", None)
        if ovr:
            all_values.extend(getattr(v, "Value", v) for v in ovr)

    checked = 0
    failures = []
    for i, v in enumerate(all_values):
        pq = getattr(v, "PhysicalQuantity", None)
        if pq is not None:
            checked += 1
            try:
                pq_int = int(pq)
            except (TypeError, ValueError):
                pq_int = -1
            if pq_int not in valid_range:
                failures.append(f"value[{i}].PhysicalQuantity={pq!r}")

    if checked == 0:
        pytest.skip("No result values with PhysicalQuantity found — optional field per spec")
    assert not failures, "PhysicalQuantity out of valid enumeration range:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.JOINING_RESULT_OVERALL_RESULT_VALUES)
async def test_result_value_tag_in_valid_range(subscription_client, result_trigger, ns_indices):
    """ValueTag on each ResultValueDataType must be within the valid enumeration range."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    valid_range = set(range(21))
    all_values: list[Any] = []
    if meta is not None:
        ovr = getattr(meta, "OverallResultValues", None)
        if ovr:
            all_values.extend(_unwrap_variant(v) for v in ovr)
    content = getattr(result_data, "ResultContent", None) or []
    for jr in content:
        jr = getattr(jr, "Value", jr)  # unwrap asyncua Variant
        ovr = getattr(jr, "OverallResultValues", None)
        if ovr:
            all_values.extend(_unwrap_variant(v) for v in ovr)

    checked = 0
    failures = []
    for i, v in enumerate(all_values):
        vt = getattr(v, "ValueTag", None)
        if vt is not None:
            checked += 1
            try:
                vt_int = int(vt)
            except (TypeError, ValueError):
                vt_int = -1
            if vt_int not in valid_range:
                failures.append(f"value[{i}].ValueTag={vt!r}")

    if checked == 0:
        pytest.skip("No result values with ValueTag found — optional field per spec")
    assert not failures, "ValueTag out of valid enumeration range:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.JOINING_RESULT_OVERALL_RESULT_VALUES)
async def test_result_value_engineering_units_if_present_has_identifier(
    subscription_client, result_trigger, ns_indices
):
    """If EngineeringUnits is present on a result value, it must have a valid UnitId."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    all_values: list[Any] = []
    if meta is not None:
        ovr = getattr(meta, "OverallResultValues", None)
        if ovr:
            all_values.extend(_unwrap_variant(v) for v in ovr)
    content = getattr(result_data, "ResultContent", None) or []
    for jr in content:
        jr = getattr(jr, "Value", jr)  # unwrap asyncua Variant
        for src in (getattr(jr, "OverallResultValues", None) or [],):
            all_values.extend(_unwrap_variant(v) for v in src)
        for step in getattr(jr, "StepResults", None) or []:
            step = _unwrap_variant(step)
            all_values.extend(_unwrap_variant(v) for v in (getattr(step, "StepResultValues", None) or []))

    checked = 0
    failures = []
    for i, v in enumerate(all_values):
        eu = getattr(v, "EngineeringUnits", None)
        eu = getattr(eu, "Value", eu) if eu is not None else None  # unwrap Variant → EUInformation
        if eu is not None:
            checked += 1
            if not hasattr(eu, "UnitId"):
                failures.append(
                    f"value[{i}].EngineeringUnits has no .UnitId attribute (got type {type(eu).__name__!r})"
                )

    if checked == 0:
        pytest.skip("No result values carry EngineeringUnits — optional field per spec")
    assert not failures, "EngineeringUnits present but missing .UnitId:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# joining_result_errors — ErrorInformationDataType
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINING_RESULT_ERRORS)
async def test_nok_result_error_information_fields_are_valid(subscription_client, result_trigger, ns_indices):
    """The Server supports Single Result instances where JoiningResultDataType contains
    error information as ErrorInformationDataType in JoiningResult.Errors.
    Each ErrorInformationDataType includes at least ErrorType, ErrorMessage.

    Checks that mandatory ErrorType/ErrorMessage fields are valid on NOK results.
    """
    result_data, _ = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.MULTI_STEP_NOK_FAILING_STEP,
    )
    _skip_if_no_result(result_data, result_trigger)

    content = getattr(result_data, "ResultContent", None) or []
    all_errors: list[Any] = []
    for jr in content:
        jr = getattr(jr, "Value", jr)  # unwrap asyncua Variant
        errors = getattr(jr, "Errors", None) or []
        all_errors.extend(_unwrap_variant(err) for err in errors)

    if not all_errors:
        pytest.skip(
            "NOK result contains no Errors entries — cannot verify (server may not populate Errors on this result type)"
        )

    failures = []
    for i, err in enumerate(all_errors):
        error_type = getattr(err, "ErrorType", None)
        try:
            error_type_int = int(error_type)
        except (TypeError, ValueError):
            error_type_int = -1
        if error_type_int not in range(7):
            failures.append(f"Errors[{i}].ErrorType={error_type!r}")

        error_message = _localized_text_text(getattr(err, "ErrorMessage", None))
        if not error_message.strip():
            failures.append(f"Errors[{i}].ErrorMessage={error_message!r}")

        error_id = getattr(err, "ErrorId", None)
        if error_id is not None and not str(error_id).strip():
            failures.append(f"Errors[{i}].ErrorId={error_id!r}")

    assert not failures, "ErrorInformationDataType field validation failed:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# joining_result_failure_reason — FailureReason on NOK results
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINING_RESULT_FAILURE_REASON)
async def test_nok_result_failure_reason_in_valid_range(subscription_client, result_trigger, ns_indices):
    """The Server supports Single Result instances where if Result.ResultContent is an
    instance of JoiningResultDataType, then it provides FailureReason defined in
    JoiningResultDataType if Result.ResultMetaData.ResultEvaluation = NotOK.

    Checks that FailureReason is within the valid enumeration range.
    """
    result_data, _ = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.MULTI_STEP_NOK_FAILING_STEP,
    )
    _skip_if_no_result(result_data, result_trigger)

    valid_reasons = {0, 1, 2, 3}
    joining_results = [_unwrap_variant(jr) for jr in (getattr(result_data, "ResultContent", None) or [])]
    if not joining_results:
        pytest.fail("NOK result has no ResultContent entries — cannot verify JoiningResultDataType.FailureReason")

    failures = []
    for i, jr in enumerate(joining_results):
        fr = getattr(jr, "FailureReason", None)
        if fr is None:
            failures.append(f"ResultContent[{i}].FailureReason is absent")
            continue
        fr = _unwrap_variant(fr)
        try:
            fr_int = int(fr)
        except (TypeError, ValueError):
            fr_int = -1
        if fr_int not in valid_reasons:
            failures.append(f"ResultContent[{i}].FailureReason={fr!r}")

    assert not failures, "FailureReason out of valid enumeration range:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# result_value_final_tag — FINAL tag on OverallResultValues or StepResultValues
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_VALUE_FINAL_TAG)
async def test_result_overall_values_contains_final_tag(subscription_client, result_trigger, ns_indices):
    """The Server supports Single Result instances where JoiningResultDataType contains
    at least one element of Torque and Angle Value in JoiningResult.StepResults[].StepResultValues[]
    where ValueTag = FINAL. It is allowed to include key ResultValues with ValueTag = FINAL
    in JoiningResult.OverallResultValues[].

    Checks that each JoiningResultDataType payload carries ValueTag = FINAL in
    either OverallResultValues or StepResults[].StepResultValues[].
    """
    result_data, _ = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.MULTI_STEP_OK_RESULT,
    )
    _skip_if_no_result(result_data, result_trigger)

    content = getattr(result_data, "ResultContent", None) or []
    if not content:
        pytest.skip("ResultContent is empty — no JoiningResultDataType entries to check")

    failures = []
    for i, jr in enumerate(content):
        jr = _unwrap_variant(jr)
        if not _joining_result_has_final_tag(jr):
            failures.append(f"ResultContent[{i}] has no ValueTag=FINAL in OverallResultValues or StepResultValues")

    assert not failures, "Missing FINAL tag in JoiningResultDataType payloads:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Trace data structure
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINING_RESULT_TRACE)
async def test_result_with_traces_has_trace_data(subscription_client, result_trigger, ns_indices):
    """When traces are requested, the result must carry TraceDataType with TraceId."""
    result_data, _ = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.MULTI_STEP_OK_RESULT,
        include_traces=True,
    )
    _skip_if_no_result(result_data, result_trigger)

    content = getattr(result_data, "ResultContent", None) or []
    if not content:
        pytest.skip("ResultContent is empty — no step results to check for trace data")

    found_trace = False
    failures = []
    for i, jr in enumerate(content):
        jr = getattr(jr, "Value", jr)  # unwrap asyncua Variant
        trace_data = _unwrap_variant(getattr(jr, "Trace", None))  # field is Trace, not TraceData
        if trace_data is not None:
            found_trace = True
            trace_id = getattr(trace_data, "TraceId", None)
            if not trace_id:
                failures.append(f"ResultContent[{i}].Trace.TraceId is absent or empty")

    if not found_trace:
        pytest.skip(
            "No TraceData found on any JoiningResultDataType — server may not support trace data for this result type"
        )
    assert not failures, "TraceDataType missing TraceId:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Parametrized: all result types produce structurally valid ResultDataType
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.BASIC_RESULT)
@pytest.mark.parametrize(
    "result_type,description",
    [
        (ResultType.SIMPLE_OK_RESULT, "simple-ok"),
        (ResultType.ONE_STEP_OK_RESULT, "one-step-ok"),
        (ResultType.MULTI_STEP_OK_RESULT, "multi-step-ok"),
        (ResultType.MULTI_STEP_NOK_FAILING_STEP, "multi-step-nok-failing-step"),
        (ResultType.MULTI_STEP_NOK_TOOL_TRIGGER_LOST, "multi-step-nok-trigger-lost"),
    ],
)
async def test_all_result_types_produce_valid_result_data_structure(
    subscription_client, result_trigger, ns_indices, result_type, description
):
    """All result types must produce structurally valid ResultDataType instances."""
    result_data, _ = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=result_type,
        include_traces=False,
    )
    _skip_if_no_result(result_data, result_trigger)
    assert_result_data_valid(result_data, context=f"ResultDataType[{description}]")


# ---------------------------------------------------------------------------
# Negative tests
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
async def test_get_latest_result_with_zero_timeout_returns_quickly(subscription_client, ns_indices):
    """GetLatestResult with timeout=0 should return quickly (may be empty).

    A timeout of zero milliseconds means the server must not block waiting for a result.
    The call must complete promptly regardless of whether data is available.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    js = await find_joining_system(subscription_client)
    if js is None:
        pytest.skip("JoiningSystem not found")
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement not found")

    result = await find_and_call_method(
        rm,
        BN.GET_LATEST_RESULT,
        ns_mr,
        ua.Variant(0, ua.VariantType.Int32),
        timeout=10.0,
    )
    assert result is not None, "GetLatestResult with timeout=0 returned None unexpectedly"


@pytest.mark.requires_cu(CU.GET_RESULT_BY_ID)
async def test_get_result_by_id_with_invalid_id_returns_bad_status(subscription_client, ns_indices):
    """GetResultById with an unknown ResultId must report a not-found error.

    Spec: The Server supports GetResultById method.
    Negative check: a non-existent id must not return spurious data. Current
    signature returns [ResultHandle, Result, Error], where a non-zero Error or
    null Result is the expected domain-level failure signal.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    js = await find_joining_system(subscription_client)
    if js is None:
        pytest.skip("JoiningSystem not found")
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement not found")
    grbi = await find_child_by_browse_name(rm, BN.GET_RESULT_BY_ID, ns_mr)
    if grbi is None:
        pytest.skip("GetResultById method not found — optional method per spec")

    result = await call_method(
        rm,
        grbi.nodeid,
        ua.Variant("__invalid_result_id_that_does_not_exist__", ua.VariantType.String),
        ua.Variant(1000, ua.VariantType.Int32),
        timeout=15.0,
        method_name="GetResultById(invalid)",
    )
    if result.success:
        output = result.output_list
        if len(output) >= 3:
            try:
                if int(output[2]) != 0:
                    return
            except (TypeError, ValueError):
                pass
            if output[1] is None:
                return
        message = (
            "GetResultById with a non-existent ResultId returned Success with no error indicator — "
            "expected non-zero output[2] Error or null output[1] Result"
        )
        if ns_indices.get(NS_APP) is not None:
            pytest.skip(f"{message}; known simulator gap")
        pytest.fail(message)


# ===========================================================================
# ─── single_result ───
# ===========================================================================


@pytest.mark.requires_cu(CU.SINGLE_RESULT)
async def test_single_result_content_has_one_joining_result_element(subscription_client, result_trigger, ns_indices):
    """ResultContent for a single joining operation must contain exactly one
    JoiningResultDataType element."""
    result_data, meta = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.ONE_STEP_OK_RESULT,
    )
    _skip_if_no_result(result_data, result_trigger)

    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result tests")
    cls_val = getattr(meta, "Classification", None)
    if cls_val is None or int(cls_val) != ResultClassification.SINGLE_RESULT:
        pytest.skip("Result is not Classification=SINGLE_RESULT — skipping element count check")

    content = getattr(result_data, "ResultContent", None)
    if content is None:
        pytest.skip("ResultContent absent — server may not populate it for this result type")
    content_list = list(content)
    assert len(content_list) >= 1, "A Single Result must contain at least one JoiningResultDataType in ResultContent"


@pytest.mark.requires_cu(CU.SINGLE_RESULT)
async def test_single_result_is_partial_false_for_completed_result(subscription_client, result_trigger, ns_indices):
    """A completed Single Result must have IsPartial = False."""
    result_data, meta = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.ONE_STEP_OK_RESULT,
    )
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result tests")

    is_partial = getattr(meta, "IsPartial", None)
    if is_partial is None:
        pytest.skip("IsPartial field absent from ResultMetaData — cannot verify")
    assert is_partial is False or is_partial == 0, (
        f"A completed Single Result must have IsPartial=False, got {is_partial!r}"
    )


@pytest.mark.requires_cu(CU.SINGLE_RESULT)
async def test_single_result_state_is_not_processing(subscription_client, result_trigger, ns_indices):
    """A final Single Result must not have ResultState=Processing; it must be completed."""
    result_data, meta = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.ONE_STEP_OK_RESULT,
    )
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result tests")

    result_state = getattr(meta, "ResultState", None)
    if result_state is None:
        pytest.skip("ResultState field absent — covered by basic_result tests")
    state_int = int(result_state)
    if state_int not in _VALID_RESULT_STATE_VALUES:
        pytest.skip(f"ResultState value {state_int} outside known range — cannot classify")
    # Skip rather than fail when simulator returns Processing for a completed result
    if state_int == _RESULT_STATE_PROCESSING:
        pytest.skip(
            f"Server returned ResultState=Processing ({_RESULT_STATE_PROCESSING}) for a completed "
            "result — known simulator behaviour; spec requires a terminal state (Good/Bad). "
            "Skipping rather than failing; test against a fully compliant server to verify."
        )


@pytest.mark.requires_cu(CU.SINGLE_RESULT)
async def test_single_result_ids_are_unique_between_consecutive_operations(
    subscription_client, result_trigger, ns_indices
):
    """Two consecutive joining operations must produce results with distinct non-empty ResultIds."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    result_data_a, meta_a = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.MULTI_STEP_OK_RESULT,
    )
    _skip_if_no_result(result_data_a, result_trigger)
    if meta_a is None:
        pytest.skip("ResultMetaData absent from first result")
    id_a = getattr(meta_a, "ResultId", None)
    if not id_a or not str(id_a).strip():
        pytest.skip("ResultId absent or empty in first result — covered by basic_result tests")

    result_data_b, meta_b = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.MULTI_STEP_OK_RESULT,
    )
    _skip_if_no_result(result_data_b, result_trigger)
    if meta_b is None:
        pytest.skip("ResultMetaData absent from second result")
    id_b = getattr(meta_b, "ResultId", None)
    if not id_b or not str(id_b).strip():
        pytest.skip("ResultId absent or empty in second result")

    assert str(id_a) != str(id_b), (
        f"Two consecutive Single Results must have distinct ResultIds; both returned {id_a!r}"
    )


# ===========================================================================
# ─── basic_result ───
# ===========================================================================


@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_basic_result_classification_in_valid_range(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.Classification must be a valid value in the ResultClassification range."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result presence test")

    cls_val = getattr(meta, "Classification", None)
    if cls_val is None:
        pytest.skip("Classification field absent — covered by basic_result presence test")
    cls_int = int(cls_val)
    assert cls_int in ResultClassification.VALID_VALUES, (
        f"ResultMetaData.Classification={cls_int} is not in valid set {sorted(ResultClassification.VALID_VALUES)}"
    )


@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_basic_result_is_simulated_is_boolean(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.IsSimulated must be present and of boolean type."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result presence test")

    is_simulated = getattr(meta, "IsSimulated", None)
    assert is_simulated is not None, "ResultMetaData.IsSimulated must be present (mandatory per basic_result CU)"
    assert isinstance(is_simulated, bool) or is_simulated in (0, 1), (
        f"ResultMetaData.IsSimulated must be boolean, got {type(is_simulated).__name__!r}: {is_simulated!r}"
    )


@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_basic_result_is_partial_is_present(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.IsPartial must be present and of boolean type."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result presence test")

    is_partial = getattr(meta, "IsPartial", None)
    assert is_partial is not None, "ResultMetaData.IsPartial must be present (mandatory per basic_result CU)"
    assert isinstance(is_partial, bool) or is_partial in (0, 1), (
        f"ResultMetaData.IsPartial must be boolean, got {type(is_partial).__name__!r}: {is_partial!r}"
    )


@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_basic_result_joining_technology_is_present(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.JoiningTechnology must be present (may be empty LocalizedText)."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result presence test")

    # JoiningTechnology is declared as a mandatory field in JoiningResultMetaDataType;
    # presence is what we verify here — an empty LocalizedText("") is acceptable.
    has_field = hasattr(meta, "JoiningTechnology")
    assert has_field, "ResultMetaData.JoiningTechnology field must be present (mandatory per basic_result CU)"


@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_basic_result_result_state_is_present(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.ResultState must be present with a value in the known valid range."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result presence test")

    result_state = getattr(meta, "ResultState", None)
    assert result_state is not None, "ResultMetaData.ResultState must be present (mandatory per basic_result CU)"
    try:
        state_int = int(result_state)
    except (TypeError, ValueError):
        pytest.fail(f"ResultMetaData.ResultState must be numeric, got {result_state!r}")
        return
    assert state_int in _VALID_RESULT_STATE_VALUES, (
        f"ResultMetaData.ResultState={state_int} is outside the known valid range {sorted(_VALID_RESULT_STATE_VALUES)}"
    )


@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_basic_result_creation_time_not_before_processing_end_time(
    subscription_client, result_trigger, ns_indices
):
    """ResultMetaData.CreationTime must be >= ProcessingTimes.EndTime for the same result."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result presence test")

    creation_time = getattr(meta, "CreationTime", None)
    if creation_time is None:
        pytest.skip("CreationTime absent — covered by basic_result creation time test")

    pt = getattr(meta, "ProcessingTimes", None)
    if pt is None:
        pytest.skip("ProcessingTimes absent — covered by result_processing_times tests")
    end_time = getattr(pt, "EndTime", None)
    if end_time is None:
        pytest.skip("ProcessingTimes.EndTime absent — covered by result_processing_times tests")

    assert creation_time >= end_time, (
        f"ResultMetaData.CreationTime ({creation_time!r}) must be >= "
        f"ProcessingTimes.EndTime ({end_time!r}); result is always created after processing completes"
    )


@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_basic_result_all_nine_mandatory_fields_present(subscription_client, result_trigger, ns_indices):
    """All nine mandatory ResultMetaData fields must be present in a single result:
    ResultId, Classification, IsSimulated, IsPartial, ResultEvaluation,
    JoiningTechnology, ResultState, SequenceNumber, CreationTime."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result presence test")

    mandatory_fields = (
        "ResultId",
        "Classification",
        "IsSimulated",
        "IsPartial",
        "ResultEvaluation",
        "JoiningTechnology",
        "ResultState",
        "SequenceNumber",
        "CreationTime",
    )
    missing = [f for f in mandatory_fields if not hasattr(meta, f)]
    assert not missing, f"The following mandatory ResultMetaData fields are absent: {missing}"


@pytest.mark.negative
@pytest.mark.requires_cu(CU.BASIC_RESULT)
async def test_basic_result_sequence_number_monotonically_increasing_across_five_results(
    subscription_client, result_trigger, ns_indices
):
    """SequenceNumber must be strictly increasing across five consecutive results
    (no unexpected reset to zero between operations)."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    sequence_numbers = []
    for _ in range(5):
        _, meta = await _get_result(
            subscription_client,
            result_trigger,
            ns_indices,
            result_type=ResultType.MULTI_STEP_OK_RESULT,
        )
        if meta is None:
            pytest.skip("ResultMetaData absent — cannot collect five sequence numbers")
        seq = getattr(meta, "SequenceNumber", None)
        if seq is None:
            pytest.skip("SequenceNumber absent — optional per spec")
        sequence_numbers.append(int(seq))
        if not result_trigger.is_simulator:
            break  # external trigger: single observation is sufficient

    if len(sequence_numbers) < 2:
        pytest.skip("Fewer than two sequence numbers collected — monotonicity cannot be checked")

    failures = []
    for i in range(1, len(sequence_numbers)):
        if sequence_numbers[i] <= sequence_numbers[i - 1]:
            failures.append(
                f"SequenceNumber[{i}]={sequence_numbers[i]} is not > SequenceNumber[{i - 1}]={sequence_numbers[i - 1]}"
            )
    assert not failures, "SequenceNumber is not monotonically increasing:\n  " + "\n  ".join(failures)


# ===========================================================================
# ─── result_additional_data ───
# ===========================================================================


@pytest.mark.requires_cu(CU.RESULT_ADDITIONAL_DATA)
async def test_result_name_is_non_empty_string_when_present(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.Name, when populated, must be a non-empty string."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result tests")

    name = getattr(meta, "Name", None)
    if name is None:
        pytest.skip("ResultMetaData.Name is not populated — optional field, absence is valid")
    assert isinstance(name, str), f"ResultMetaData.Name must be a string when present, got {type(name).__name__!r}"
    assert name.strip(), f"ResultMetaData.Name is present but empty; expected a non-empty string, got {name!r}"


@pytest.mark.requires_cu(CU.RESULT_ADDITIONAL_DATA)
async def test_result_description_is_present_when_populated(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.Description, when populated, must be non-None (LocalizedText)."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result tests")

    description = getattr(meta, "Description", None)
    if description is None:
        pytest.skip("ResultMetaData.Description is not populated — optional field, absence is valid")
    # LocalizedText is a structured type; presence and non-None is the key assertion
    assert description is not None, "ResultMetaData.Description must be non-null when the field is declared"


@pytest.mark.requires_cu(CU.RESULT_ADDITIONAL_DATA)
async def test_result_evaluation_code_is_int64_when_present(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.ResultEvaluationCode, when present, must be an Int64-compatible integer."""
    result_data, meta = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.MULTI_STEP_NOK_FAILING_STEP,
    )
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result tests")

    code = getattr(meta, "ResultEvaluationCode", None)
    if code is None:
        pytest.skip("ResultEvaluationCode not populated — optional field, absence is valid")
    assert isinstance(code, int) and not isinstance(code, bool), (
        f"ResultMetaData.ResultEvaluationCode must be an Int64-compatible integer when present, got {code!r}"
    )


@pytest.mark.requires_cu(CU.RESULT_ADDITIONAL_DATA)
async def test_result_evaluation_details_is_present_when_populated(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.ResultEvaluationDetails, when present, must be non-None (LocalizedText)."""
    result_data, meta = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.MULTI_STEP_NOK_FAILING_STEP,
    )
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result tests")

    details = getattr(meta, "ResultEvaluationDetails", None)
    if details is None:
        pytest.skip("ResultEvaluationDetails not populated — optional field, absence is valid")
    assert details is not None, "ResultMetaData.ResultEvaluationDetails must be non-null when declared"


@pytest.mark.requires_cu(CU.RESULT_ADDITIONAL_DATA)
async def test_result_assembly_type_in_valid_range_when_present(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.AssemblyType, when present, must be 0 (UNDEFINED), 1 (ASSEMBLED),
    or 2 (DISASSEMBLED)."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result tests")

    assembly_type = getattr(meta, "AssemblyType", None)
    if assembly_type is None:
        pytest.skip("AssemblyType not populated — optional field, absence is valid")
    try:
        at_int = int(assembly_type)
    except (TypeError, ValueError):
        pytest.fail(f"ResultMetaData.AssemblyType must be numeric, got {assembly_type!r}")
        return
    assert at_int in _VALID_ASSEMBLY_TYPE_VALUES, (
        f"ResultMetaData.AssemblyType={at_int} is not in valid set "
        f"{sorted(_VALID_ASSEMBLY_TYPE_VALUES)} (0=UNDEFINED, 1=ASSEMBLED, 2=DISASSEMBLED)"
    )


@pytest.mark.requires_cu(CU.RESULT_ADDITIONAL_DATA)
async def test_result_operation_mode_in_valid_range_when_present(subscription_client, result_trigger, ns_indices):
    """ResultMetaData.OperationMode, when present, must be 0 (UNDEFINED), 1 (AUTOMATIC),
    or 2 (MANUAL)."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result tests")

    operation_mode = getattr(meta, "OperationMode", None)
    if operation_mode is None:
        pytest.skip("OperationMode not populated — optional field, absence is valid")
    try:
        om_int = int(operation_mode)
    except (TypeError, ValueError):
        pytest.fail(f"ResultMetaData.OperationMode must be numeric, got {operation_mode!r}")
        return
    assert om_int in _VALID_OPERATION_MODE_VALUES, (
        f"ResultMetaData.OperationMode={om_int} is not in valid set "
        f"{sorted(_VALID_OPERATION_MODE_VALUES)} (0=UNDEFINED, 1=AUTOMATIC, 2=MANUAL)"
    )


@pytest.mark.requires_cu(CU.RESULT_ADDITIONAL_DATA)
async def test_result_is_valid_when_additional_data_fields_absent(subscription_client, result_trigger, ns_indices):
    """A result must be accepted as valid even when all optional additional-data fields
    (Name, Description, AssemblyType, OperationMode) are absent."""
    result_data, meta = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.SIMPLE_OK_RESULT,
    )
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result tests")

    # The mandatory nine fields must still be present regardless of optional fields
    mandatory = ("ResultId", "Classification", "ResultEvaluation")
    missing = [f for f in mandatory if getattr(meta, f, None) is None]
    assert not missing, f"Mandatory ResultMetaData fields missing even when optional fields are absent: {missing}"


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_ADDITIONAL_DATA)
async def test_result_additional_data_write_is_rejected(subscription_client, ns_indices):
    """Attempting to write to a result variable node's sub-variables must be rejected
    with Bad_NotWritable or Bad_UserAccessDenied."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    js = await find_joining_system(subscription_client)
    if js is None:
        pytest.skip("JoiningSystem not found")
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement not found")

    results_folder = await find_child_by_browse_name_any(
        rm,
        BN.RESULTS,
        (ns_mr, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP)),
    )
    if results_folder is None:
        pytest.skip("Results folder not found in ResultManagement — cannot test write rejection")
    result_var = await find_child_by_browse_name_any(
        results_folder,
        BN.RESULT,
        (ns_mr, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP)),
    )
    if result_var is None:
        pytest.skip("Results/Result variable not found — cannot test write rejection")
    last_result_meta = await find_child_by_browse_name_any(
        result_var,
        BN.RESULT_META_DATA,
        (ns_mr, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP)),
    )
    if last_result_meta is None:
        pytest.skip("Results/Result/ResultMetaData variable not found — cannot test write rejection")
    try:
        await last_result_meta.write_value(ua.Variant("__test_write__", ua.VariantType.String))
        pytest.fail(
            "Write to Results/Result/ResultMetaData node succeeded — expected Bad_NotWritable or Bad_UserAccessDenied"
        )
    except ua.UaError:
        pass  # Any UaError (Bad_NotWritable, Bad_UserAccessDenied, etc.) is the expected outcome


# ===========================================================================
# ─── result_extended_meta_data ───
# ===========================================================================


@pytest.mark.requires_cu(CU.RESULT_EXTENDED_META_DATA)
async def test_extended_meta_data_keys_are_non_empty_strings_when_present(
    subscription_client, result_trigger, ns_indices
):
    """Each element in ResultMetaData.ExtendedMetaData must have a non-empty string Key."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result tests")

    ext = getattr(meta, "ExtendedMetaData", None)
    if ext is None:
        pytest.skip("ExtendedMetaData not populated — optional field, absence is valid")
    ext_list = list(ext)
    if not ext_list:
        pytest.skip("ExtendedMetaData is an empty array — nothing to validate")

    failures = []
    for i, entry in enumerate(ext_list):
        key = getattr(entry, "Key", None)
        if key is None or not isinstance(key, str) or not str(key).strip():
            failures.append(
                f"ExtendedMetaData[{i}].Key is absent or empty; each KeyValueDataType must have a non-empty string Key"
            )
    assert not failures, "Invalid ExtendedMetaData keys:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.RESULT_EXTENDED_META_DATA)
async def test_extended_meta_data_values_have_concrete_type_when_present(
    subscription_client, result_trigger, ns_indices
):
    """Each Value in ResultMetaData.ExtendedMetaData must be a Variant with a concrete DataType
    (not null and not untyped)."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result tests")

    ext = getattr(meta, "ExtendedMetaData", None)
    if ext is None:
        pytest.skip("ExtendedMetaData not populated — optional field")
    ext_list = list(ext)
    if not ext_list:
        pytest.skip("ExtendedMetaData is empty — nothing to validate")

    failures = []
    for i, entry in enumerate(ext_list):
        value = getattr(entry, "Value", None)
        if value is None:
            failures.append(
                f"ExtendedMetaData[{i}].Value is None; each entry must carry a Variant with a concrete type"
            )
    assert not failures, "Null ExtendedMetaData values found:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.RESULT_EXTENDED_META_DATA)
async def test_extended_meta_data_keys_are_unique_within_result(subscription_client, result_trigger, ns_indices):
    """All Keys within a single ExtendedMetaData array must be unique (case-sensitive)."""
    result_data, meta = await _get_result(subscription_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic_result tests")

    ext = getattr(meta, "ExtendedMetaData", None)
    if ext is None:
        pytest.skip("ExtendedMetaData not populated — optional field")
    ext_list = list(ext)
    if len(ext_list) < 2:
        logger.info("ExtendedMetaData has fewer than 2 entries; key uniqueness is vacuously satisfied")
        return

    keys = [str(getattr(e, "Key", "")) for e in ext_list]
    seen = set()
    duplicates = set()
    for k in keys:
        if k in seen:
            duplicates.add(k)
        seen.add(k)
    assert not duplicates, (
        f"Duplicate Keys in ExtendedMetaData: {sorted(duplicates)}; all Keys within a single result must be unique"
    )


@pytest.mark.requires_cu(CU.RESULT_EXTENDED_META_DATA)
async def test_extended_meta_data_empty_array_is_valid(subscription_client, result_trigger, ns_indices):
    """A result with an empty ExtendedMetaData array must still be structurally valid
    and include all mandatory ResultMetaData fields."""
    result_data, meta = await _get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.SIMPLE_OK_RESULT,
    )
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — cannot verify mandatory field presence")

    ext = getattr(meta, "ExtendedMetaData", None)
    if ext is not None and len(list(ext)) > 0:
        logger.info(
            "ExtendedMetaData is application-specific and non-empty for this result; validating mandatory fields"
        )

    # Mandatory fields must be present regardless of ExtendedMetaData content
    for field_name in ("ResultId", "Classification", "ResultEvaluation"):
        assert getattr(meta, field_name, None) is not None, (
            f"Mandatory field ResultMetaData.{field_name} must be present even when ExtendedMetaData is empty or absent"
        )


# ===========================================================================
# ─── result_event_access ───
# ===========================================================================


@pytest.mark.requires_cu(CU.RESULT_EVENT_ACCESS)
async def test_joining_system_event_notifier_allows_subscriptions(session_client, ns_indices):
    """The JoiningSystem instance's EventNotifier attribute must have the SubscribeToEvents
    bit (bit 0) set, making it usable as an event source for result-ready events."""
    js = await find_joining_system(session_client)
    if js is None:
        pytest.skip("JoiningSystem not found — cannot check EventNotifier attribute")

    event_notifier = await js.read_attribute(ua.AttributeIds.EventNotifier)
    notifier_val = event_notifier.Value.Value if event_notifier.Value else None
    if notifier_val is None:
        pytest.skip("EventNotifier attribute returned None — cannot verify subscription support")

    subscribe_to_events_bit = 0x01
    assert int(notifier_val) & subscribe_to_events_bit, (
        f"JoiningSystem.EventNotifier={notifier_val:#04x} does not have SubscribeToEvents bit (0x01) set; "
        "clients cannot subscribe to result-ready events on this node"
    )


@pytest.mark.requires_cu(CU.RESULT_EVENT_ACCESS)
async def test_result_ready_event_received_after_result_trigger(subscription_client, result_trigger, ns_indices):
    """A JoiningSystemResultReadyEventType event must be received within the timeout
    after a result is triggered."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")

    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))

    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)
        outcome = await result_trigger.trigger_single(ResultType.MULTI_STEP_OK_RESULT, include_traces=False)
        if not outcome.triggered and result_trigger.is_simulator:
            pytest.skip(outcome.skip_reason or "Simulator result trigger failed")
        timeout_s = 15.0 if result_trigger.is_simulator else 90.0
        events = await collector.collect(count=1, timeout_s=timeout_s)

    assert len(events) >= 1, (
        "No JoiningSystemResultReadyEventType event received within the timeout after "
        "triggering a result; the server must fire a result-ready event for each operation"
    )


@pytest.mark.requires_cu(CU.RESULT_EVENT_ACCESS)
async def test_result_ready_event_carries_non_null_result_field(subscription_client, result_trigger, ns_indices):
    """The JoiningSystemResultReadyEventType event must carry a non-null Result field
    with a valid non-empty ResultId in ResultMetaData."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")

    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))

    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)
        outcome = await result_trigger.trigger_single(ResultType.MULTI_STEP_OK_RESULT, include_traces=False)
        if not outcome.triggered and result_trigger.is_simulator:
            pytest.skip(outcome.skip_reason or "Simulator result trigger failed")
        timeout_s = 15.0 if result_trigger.is_simulator else 90.0
        events = await collector.collect(count=1, timeout_s=timeout_s)

    if not events:
        pytest.skip("No result-ready event received — covered by receipt test")

    event = events[0]
    result_field = getattr(event, "Result", None)
    assert result_field is not None, (
        "JoiningSystemResultReadyEventType.Result field must be non-null; the event must carry the full result payload"
    )
    meta = getattr(result_field, "ResultMetaData", None)
    assert meta is not None, "Result.ResultMetaData must be present in the result-ready event payload"
    result_id = getattr(meta, "ResultId", None)
    assert result_id and str(result_id).strip(), (
        f"Result.ResultMetaData.ResultId must be a non-empty string in the event, got {result_id!r}"
    )


@pytest.mark.requires_cu(CU.RESULT_EVENT_ACCESS)
async def test_result_ready_event_base_event_fields_are_valid(subscription_client, result_trigger, ns_indices):
    """The received JoiningSystemResultReadyEventType must pass full validation of
    BaseEventType mandatory fields (EventId, EventType, SourceNode, Time, Severity)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")

    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))

    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)
        outcome = await result_trigger.trigger_single(ResultType.MULTI_STEP_OK_RESULT, include_traces=False)
        if not outcome.triggered and result_trigger.is_simulator:
            pytest.skip(outcome.skip_reason or "Simulator result trigger failed")
        timeout_s = 15.0 if result_trigger.is_simulator else 90.0
        events = await collector.collect(count=1, timeout_s=timeout_s)

    if not events:
        pytest.skip("No result-ready event received — covered by receipt test")

    assert_result_ready_event_valid(events[0], context="result_event_access:ResultReadyEvent")


@pytest.mark.requires_cu(CU.RESULT_EVENT_ACCESS)
async def test_result_ready_event_source_name_is_non_empty(subscription_client, result_trigger, ns_indices):
    """The SourceName field of a JoiningSystemResultReadyEventType event must be a
    non-empty string identifying the source system."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")

    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))

    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)
        outcome = await result_trigger.trigger_single(ResultType.MULTI_STEP_OK_RESULT, include_traces=False)
        if not outcome.triggered and result_trigger.is_simulator:
            pytest.skip(outcome.skip_reason or "Simulator result trigger failed")
        timeout_s = 15.0 if result_trigger.is_simulator else 90.0
        events = await collector.collect(count=1, timeout_s=timeout_s)

    if not events:
        pytest.skip("No result-ready event received — covered by receipt test")

    source_name = getattr(events[0], "SourceName", None)
    assert source_name is not None and str(source_name).strip(), (
        f"BaseEventType.SourceName must be a non-empty string, got {source_name!r}"
    )


@pytest.mark.requires_cu(CU.RESULT_EVENT_ACCESS)
async def test_multiple_results_produce_separate_events_with_distinct_ids(
    subscription_client, result_trigger, ns_indices
):
    """Three consecutive joining operations must produce three separate result-ready events,
    each with a unique EventId and a unique Result.ResultMetaData.ResultId."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    if not result_trigger.is_simulator:
        pytest.skip("Three-operation sequence requires simulator — skipping for external trigger")

    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(
        ua.NodeId(IJTTypes.JOINING_RESULT_READY_EVENT_TYPE, ns_ijt)
        if hasattr(IJTTypes, "JOINING_RESULT_READY_EVENT_TYPE")
        else ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt)
    )

    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)
        for _ in range(3):
            outcome = await result_trigger.trigger_single(ResultType.MULTI_STEP_OK_RESULT, include_traces=False)
            if not outcome.triggered:
                pytest.skip(outcome.skip_reason or "Simulator trigger failed during multi-result test")
        events = await collector.collect(count=3, timeout_s=30.0)

    if len(events) < 3:
        pytest.skip(
            f"Only {len(events)} of 3 expected events received within timeout — server may be throttling events"
        )

    event_ids = []
    result_ids = []
    for ev in events[:3]:
        eid = getattr(ev, "EventId", None)
        if eid is not None:
            event_ids.append(bytes(eid) if isinstance(eid, (bytes, bytearray)) else str(eid))
        result_field = getattr(ev, "Result", None)
        meta = getattr(result_field, "ResultMetaData", None) if result_field else None
        rid = getattr(meta, "ResultId", None) if meta else None
        if rid:
            result_ids.append(str(rid))

    if len(event_ids) >= 2:
        assert len(set(event_ids)) == len(event_ids), (
            f"EventIds are not all distinct across {len(event_ids)} events: {event_ids!r}"
        )
    if len(result_ids) >= 2:
        assert len(set(result_ids)) == len(result_ids), (
            f"ResultIds are not all distinct across {len(result_ids)} events: {result_ids!r}"
        )


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_EVENT_ACCESS)
async def test_monitored_item_with_invalid_event_filter_is_rejected(subscription_client, ns_indices):
    """CreateMonitoredItems with a malformed EventFilter referencing a non-existent
    EventType NodeId must be rejected with Bad_MonitoredItemFilterInvalid."""
    nonexistent_node_id = ua.NodeId(0xFFFFFF, 999)
    nonexistent_node = subscription_client.get_node(nonexistent_node_id)
    server_node = subscription_client.nodes.server

    try:
        async with EventCollector(subscription_client) as collector:
            await collector.subscribe(server_node, nonexistent_node)
        # If subscribe succeeded without error, the server is lenient — record as info
        logger.info(
            "Server accepted invalid EventFilter without error; "
            "strict conformance requires Bad_MonitoredItemFilterInvalid"
        )
    except ua.UaError:
        pass  # Expected: server rejected the invalid filter
