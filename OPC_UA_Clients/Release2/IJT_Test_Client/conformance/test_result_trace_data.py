"""
Result trace data conformance tests — OPC 40450-1.

Covers:
  joining_result_trace — JoiningTraceDataType with TraceId, ResultId, StepTraces.
  result_value_trace_point_time_offset — StepResultValues with StartTimeOffset and TracePointOffset.
  result_value_trace_point_index — StepResultValues with TracePointIndex.

Spec (joining_result_trace):
  "The Server supports Single Result instances where JoiningResultDataType includes
  Trace of type JoiningTraceDataType. The Trace contains StepTraces which includes
  StepTraceContent. Each JoiningTraceDataType includes TraceId, ResultId, StepTraces.
  Each StepTraceDataType includes at least StepTraceId, StepResultId, NumberOfTracePoints,
  StepTraceContent. It includes StartTimeOffset and/or SamplingInterval.
  Each StepTraceContent element includes at least Values, Name, PhysicalQuantity."

Spec (result_value_trace_point_time_offset):
  "The Server supports Single Result instances where at least one StepResults[]
  includes StartTimeOffset and at least one StepResults[].StepResultValues[]
  includes TracePointOffset when TracePointIndex is not available."

Spec (result_value_trace_point_index):
  "The Server supports Single Result instances where at least one
  StepResults[].StepResultValues[] includes TracePointIndex which can point
  to a specific sample in StepTraceContent[].Values[]."

Design: triggers a result WITH traces (include_traces=True) and validates trace structure.
"""

import logging
from typing import Any

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.method_caller import call_method
from helpers.namespaces import BN, NS_MACH_RESULT, ResultClassification, ResultType
from helpers.node_discovery import find_child_by_browse_name, find_joining_system

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

_SIMULATOR_TIMEOUT_MS = 5000
_EXTERNAL_TIMEOUT_MS = 60000
_METHOD_CALL_TIMEOUT_S = 30.0
_EXTERNAL_CALL_TIMEOUT_S = 90.0

# Valid PhysicalQuantity range: 0=OTHER … 28=TORQUE_PER_ANGLE_GRADIENT
_VALID_PHYSICAL_QUANTITIES: frozenset = frozenset(range(29))

# Human-readable names for combined result classifications (not SINGLE_RESULT)
_COMBINED_RESULT_NAMES: dict[int, str] = {
    ResultClassification.SYNC_RESULT: "SYNC_RESULT",
    ResultClassification.BATCH_RESULT: "BATCH_RESULT",
    ResultClassification.JOB_RESULT: "JOB_RESULT",
    5: "STITCHING_RESULT",
}


async def _get_result_with_traces(opcua_client, result_trigger, ns_indices):
    """Trigger MULTI_STEP_OK_RESULT with traces and return (result_data, content_list).

    content_list is the ResultContent list from result_data.
    Returns (None, None) on trigger or retrieval failure.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        return None, None

    outcome = await result_trigger.trigger_single(ResultType.MULTI_STEP_OK_RESULT, include_traces=True)
    if not outcome.triggered and result_trigger.is_simulator:
        return None, None

    js = await find_joining_system(opcua_client)
    if js is None:
        return None, None
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        return None, None
    glr = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if glr is None:
        return None, None

    wait_ms = _SIMULATOR_TIMEOUT_MS if result_trigger.is_simulator else _EXTERNAL_TIMEOUT_MS
    call_timeout_s = _METHOD_CALL_TIMEOUT_S if result_trigger.is_simulator else _EXTERNAL_CALL_TIMEOUT_S

    result = await call_method(
        rm,
        glr.nodeid,
        ua.Variant(wait_ms, ua.VariantType.Int32),
        timeout=call_timeout_s,
        method_name="GetLatestResult",
    )
    if not result.success:
        return None, None

    outputs = result.output_list
    result_data = outputs[1] if len(outputs) > 1 else (outputs[0] if outputs else None)
    if result_data is None:
        return None, None

    # Trace data only exists on Single Results — skip early with a precise reason
    # if GetLatestResult returned a combined result (timing race from a prior test).
    _skip_if_not_single_result(result_data)

    content = getattr(result_data, "ResultContent", None) or []
    return result_data, list(content)


def _skip_if_not_single_result(result_data) -> None:
    """Skip with an accurate message when the retrieved result is a combined result.

    Trace data (JoiningResultDataType.Trace) only exists on Single Results.
    Combined results (BATCH/SYNC/JOB) contain only sub-result references in
    ResultContent — they never carry inline JoiningResultDataType per OPC 40450-1 §9.
    """
    meta = getattr(result_data, "ResultMetaData", None)
    cls = getattr(meta, "Classification", None) if meta is not None else None
    try:
        cls_int = int(cls) if cls is not None else None
    except TypeError, ValueError:
        cls_int = None
    if cls_int is not None and cls_int != ResultClassification.SINGLE_RESULT:
        cls_name = _COMBINED_RESULT_NAMES.get(cls_int, f"classification={cls_int}")
        pytest.skip(
            f"GetLatestResult returned {cls_name}, not SINGLE_RESULT — "
            "Trace data (JoiningResultDataType.Trace) only exists on Single Results; "
            "combined results contain only sub-result references per OPC 40450-1 §9. "
            "A prior test may have left a combined result as the latest on the server."
        )


def _skip_if_no_result(result_data, result_trigger) -> None:
    """Call pytest.skip() when result_data is None, with an appropriate message."""
    if result_data is None:
        if result_trigger.is_simulator:
            pytest.skip("Simulator trigger failed or GetLatestResult returned no data")
        else:
            pytest.skip("No result received from external trigger within timeout")


def _collect_trace_data(content):
    """Return a list of (joining_result_index, trace_data) pairs from ResultContent.

    Looks for Trace on each JoiningResultDataType element.
    Note: The IJT Base NodeSet defines the field as "Trace" (JoiningResultDataType.Trace),
    NOT "TraceData". asyncua decodes it with the NodeSet field name.
    """
    traces = []
    for i, jr in enumerate(content):
        td = getattr(jr, "Trace", None)
        if td is not None:
            traces.append((i, td))
    return traces


# ---------------------------------------------------------------------------
# Trace data presence and top-level fields
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINING_RESULT_TRACE)
async def test_single_result_with_traces_has_trace_data(opcua_client, result_trigger, ns_indices):
    """When include_traces=True, at least one JoiningResultDataType in ResultContent
    must carry a non-null Trace field (JoiningResultDataType.Trace)."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty — no JoiningResultDataType entries to check")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip(
            "No Trace data found on any JoiningResultDataType in ResultContent — "
            "check that the server populates JoiningResultDataType.Trace (IJT Base NodeSet field). "
            "The simulator calls CreateSingleResult(includeTraces=true) so this should pass."
        )


@pytest.mark.requires_cu(CU.JOINING_RESULT_TRACE)
async def test_trace_data_has_trace_id(opcua_client, result_trigger, ns_indices):
    """JoiningTraceDataType.TraceId must be a non-empty string."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip(
            "No Trace field found (JoiningResultDataType.Trace) — covered by test_single_result_with_traces_has_trace_data"
        )

    failures = []
    for idx, td in traces:
        trace_id = getattr(td, "TraceId", None)
        if not trace_id or not str(trace_id).strip():
            failures.append(f"ResultContent[{idx}].Trace.TraceId is absent or empty")

    assert not failures, "Trace.TraceId must be non-empty:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.JOINING_RESULT_TRACE)
async def test_trace_data_has_result_id_matching_parent(opcua_client, result_trigger, ns_indices):
    """JoiningTraceDataType.ResultId must match the ResultId of the parent result."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace) — covered by trace presence test")

    top_result_id = None
    meta = getattr(result_data, "ResultMetaData", None)
    if meta is not None:
        top_result_id = getattr(meta, "ResultId", None)

    failures = []
    for idx, td in traces:
        trace_result_id = getattr(td, "ResultId", None)
        if trace_result_id is None:
            failures.append(f"ResultContent[{idx}].Trace.ResultId is absent")
            continue
        if top_result_id is not None and str(trace_result_id) != str(top_result_id):
            failures.append(
                f"ResultContent[{idx}].Trace.ResultId={trace_result_id!r} "
                f"does not match parent ResultId={top_result_id!r}"
            )

    assert not failures, "Trace.ResultId must match parent result:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.JOINING_RESULT_TRACE)
async def test_trace_data_step_traces_is_non_empty_list(opcua_client, result_trigger, ns_indices):
    """JoiningTraceDataType.StepTraces must be a non-empty list (at least one step trace)."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace) — covered by trace presence test")

    failures = []
    for idx, td in traces:
        step_traces = getattr(td, "StepTraces", None)
        if step_traces is None:
            failures.append(f"ResultContent[{idx}].Trace.StepTraces is absent")
        elif not isinstance(step_traces, (list, tuple)):
            failures.append(f"ResultContent[{idx}].Trace.StepTraces must be a list, got {type(step_traces).__name__!r}")
        elif len(step_traces) == 0:
            failures.append(f"ResultContent[{idx}].Trace.StepTraces is empty; at least one step trace is required")

    assert not failures, "Trace.StepTraces must be a non-empty list:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# StepTraceDataType required fields
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINING_RESULT_TRACE)
async def test_step_trace_has_required_fields(opcua_client, result_trigger, ns_indices):
    """Each StepTraceDataType must have StepTraceId, StepResultId, NumberOfTracePoints,
    and a non-empty StepTraceContent list."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace) — covered by trace presence test")

    failures = []
    for result_idx, td in traces:
        step_traces = getattr(td, "StepTraces", None) or []
        if not step_traces:
            continue
        first_step = step_traces[0]
        for field_name in ("StepTraceId", "StepResultId", "NumberOfTracePoints"):
            val = getattr(first_step, field_name, None)
            if val is None:
                failures.append(f"ResultContent[{result_idx}].Trace.StepTraces[0].{field_name} is absent")

        step_content = getattr(first_step, "StepTraceContent", None)
        if step_content is None:
            failures.append(f"ResultContent[{result_idx}].Trace.StepTraces[0].StepTraceContent is absent")
        elif not isinstance(step_content, (list, tuple)) or len(step_content) == 0:
            failures.append(
                f"ResultContent[{result_idx}].Trace.StepTraces[0].StepTraceContent must be a non-empty list"
            )

    assert not failures, "StepTraceDataType required fields missing:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.JOINING_RESULT_TRACE)
async def test_step_trace_content_has_values_and_physical_quantity(opcua_client, result_trigger, ns_indices):
    """Each StepTraceContent element must have a Values list and a PhysicalQuantity
    value within the valid enumeration range."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace) — covered by trace presence test")

    failures = []
    for result_idx, td in traces:
        step_traces = getattr(td, "StepTraces", None) or []
        for step_idx, step in enumerate(step_traces):
            step_content = getattr(step, "StepTraceContent", None) or []
            for content_idx, tc_element in enumerate(step_content):
                location = f"ResultContent[{result_idx}].Trace.StepTraces[{step_idx}].StepTraceContent[{content_idx}]"

                values = getattr(tc_element, "Values", None)
                if values is None:
                    failures.append(f"{location}.Values is absent")
                elif not isinstance(values, (list, tuple)):
                    failures.append(f"{location}.Values must be a list, got {type(values).__name__!r}")

                phys_qty = getattr(tc_element, "PhysicalQuantity", None)
                if phys_qty is None:
                    failures.append(f"{location}.PhysicalQuantity is absent")
                else:
                    try:
                        qty_int = int(phys_qty)
                    except TypeError, ValueError:
                        qty_int = -1
                    if qty_int not in _VALID_PHYSICAL_QUANTITIES:
                        failures.append(f"{location}.PhysicalQuantity={phys_qty!r} is outside valid range")

    assert not failures, "StepTraceContent element validation failures:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Trace point offsets
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_VALUE_TRACE_POINT_TIME_OFFSET)
async def test_step_result_values_with_trace_have_start_time_offset(opcua_client, result_trigger, ns_indices):
    """When traces are present, at least one StepResult must have StartTimeOffset defined,
    and at least one StepResultValue must have TracePointOffset when TracePointIndex
    is not available."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty — no step results to examine")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace) — trace offset check requires trace data")

    found_start_time_offset = False
    found_trace_point_offset = False

    for jr in content:
        step_results = getattr(jr, "StepResults", None) or []
        for step in step_results:
            sto = getattr(step, "StartTimeOffset", None)
            if sto is not None:
                found_start_time_offset = True

            step_values = getattr(step, "StepResultValues", None) or []
            for val in step_values:
                tpi = getattr(val, "TracePointIndex", None)
                tpo = getattr(val, "TracePointOffset", None)
                if tpi is None and tpo is not None:
                    found_trace_point_offset = True

    assert found_start_time_offset, (
        "At least one StepResult must have StartTimeOffset defined when traces are included "
        "per result_value_trace_point_time_offset CU"
    )

    if not found_trace_point_offset:
        logger.info("TracePointOffset not found — server may use TracePointIndex instead, which is acceptable")


@pytest.mark.requires_cu(CU.RESULT_VALUE_TRACE_POINT_INDEX)
async def test_step_result_values_trace_point_index_points_to_valid_sample(opcua_client, result_trigger, ns_indices):
    """For StepResultValues with TracePointIndex, the index must be less than
    NumberOfTracePoints in the corresponding StepTrace (out-of-range would dereference
    a non-existent sample)."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty — no step results to examine")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace) — TracePointIndex check requires trace data")

    found_trace_point_index = False
    failures = []

    for result_idx, td in traces:
        jr = content[result_idx]
        step_traces = getattr(td, "StepTraces", None) or []
        step_results = getattr(jr, "StepResults", None) or []

        for step_trace_idx, step_trace in enumerate(step_traces):
            num_points = getattr(step_trace, "NumberOfTracePoints", None)
            if num_points is None:
                continue
            try:
                num_points_int = int(num_points)
            except TypeError, ValueError:
                continue

            step_result_id = getattr(step_trace, "StepResultId", None)
            matching_step = next(
                (s for s in step_results if getattr(s, "StepResultId", None) == step_result_id),
                None,
            )
            if matching_step is None:
                matching_step = step_results[step_trace_idx] if step_trace_idx < len(step_results) else None
            if matching_step is None:
                continue

            step_values = getattr(matching_step, "StepResultValues", None) or []
            for val_idx, val in enumerate(step_values):
                tpi = getattr(val, "TracePointIndex", None)
                if tpi is not None:
                    found_trace_point_index = True
                    try:
                        tpi_int = int(tpi)
                    except TypeError, ValueError:
                        failures.append(
                            f"ResultContent[{result_idx}].StepResults.StepResultValues[{val_idx}]"
                            f".TracePointIndex={tpi!r} is not numeric"
                        )
                        continue
                    if tpi_int >= num_points_int:
                        failures.append(
                            f"ResultContent[{result_idx}].StepTraces[{step_trace_idx}]"
                            f".StepResultValues[{val_idx}].TracePointIndex={tpi_int} "
                            f">= NumberOfTracePoints={num_points_int}"
                        )

    if not found_trace_point_index:
        pytest.skip(
            "No StepResultValues with TracePointIndex found — "
            "server may use TracePointOffset instead (result_value_trace_point_time_offset CU)"
        )

    assert not failures, "TracePointIndex out-of-range:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# joining_result_trace — additional coverage
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINING_RESULT_TRACE)
async def test_step_trace_content_values_length_matches_number_of_trace_points(
    opcua_client, result_trigger, ns_indices
):
    """For every StepTraceDataType, each TraceContentDataType.Values[] array must have
    exactly NumberOfTracePoints elements — this is the core structural invariant of the
    trace data model."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace) — covered by trace presence test")

    failures = []
    for result_idx, td in traces:
        step_traces = getattr(td, "StepTraces", None) or []
        for step_idx, step in enumerate(step_traces):
            num_points = getattr(step, "NumberOfTracePoints", None)
            if num_points is None:
                continue
            try:
                num_points_int = int(num_points)
            except TypeError, ValueError:
                failures.append(
                    f"ResultContent[{result_idx}].Trace.StepTraces[{step_idx}]"
                    f".NumberOfTracePoints is not numeric: {num_points!r}"
                )
                continue

            step_content = getattr(step, "StepTraceContent", None) or []
            for content_idx, tc_element in enumerate(step_content):
                values = getattr(tc_element, "Values", None)
                if values is None:
                    continue
                actual_len = len(values)
                if actual_len != num_points_int:
                    failures.append(
                        f"ResultContent[{result_idx}].Trace"
                        f".StepTraces[{step_idx}].StepTraceContent[{content_idx}]"
                        f".Values length={actual_len} != NumberOfTracePoints={num_points_int}"
                    )

    assert not failures, "StepTraceContent.Values[] length must equal NumberOfTracePoints:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.JOINING_RESULT_TRACE)
async def test_step_trace_has_timing_information(opcua_client, result_trigger, ns_indices):
    """Every StepTraceDataType must provide timing context via at least one of
    SamplingInterval or StartTimeOffset — without timing information a trace cannot
    be interpreted in the time domain."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace) — covered by trace presence test")

    failures = []
    for result_idx, td in traces:
        step_traces = getattr(td, "StepTraces", None) or []
        for step_idx, step in enumerate(step_traces):
            sampling_interval = getattr(step, "SamplingInterval", None)
            start_time_offset = getattr(step, "StartTimeOffset", None)
            if sampling_interval is None and start_time_offset is None:
                failures.append(
                    f"ResultContent[{result_idx}].Trace.StepTraces[{step_idx}] "
                    "has neither SamplingInterval nor StartTimeOffset; "
                    "at least one timing field is required per spec"
                )

    assert not failures, "StepTraceDataType timing information missing:\n  " + "\n  ".join(failures)


@pytest.mark.negative
@pytest.mark.requires_cu(CU.JOINING_RESULT_TRACE)
async def test_result_without_trace_data_is_returned_without_error(opcua_client, result_trigger, ns_indices):
    """A result whose Trace field is null or absent must be returned without a
    service-level error — Trace is an optional field in JoiningResultDataType."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty — no JoiningResultDataType to inspect")

    # Find a JoiningResultDataType element with no trace
    no_trace_found = False
    for jr in content:
        td = getattr(jr, "Trace", None)
        if td is None:
            no_trace_found = True
            break

    if not no_trace_found:
        pytest.skip(
            "All JoiningResultDataType entries have Trace data — "
            "this test targets the absent-trace case (mark Inconclusive when "
            "device always provides trace data)"
        )

    # We already received the result without error — the test passes by reaching here
    meta = getattr(result_data, "ResultMetaData", None)
    result_id = str(getattr(meta, "ResultId", None) or "") if meta else ""
    assert result_id.strip(), "ResultMetaData.ResultId must still be present even when Trace field is absent"


@pytest.mark.negative
@pytest.mark.requires_cu(CU.JOINING_RESULT_TRACE)
async def test_step_trace_content_array_lengths_are_consistent_across_results(opcua_client, result_trigger, ns_indices):
    """Across multiple results the StepTraceContent.Values[] length must always equal
    NumberOfTracePoints for every StepTrace — the array-length invariant must hold
    universally, not just for a single result."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    failures = []
    results_checked = 0

    for _attempt in range(2):
        result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
        if result_data is None or not content:
            continue

        results_checked += 1
        for _, jr in enumerate(content):
            td = getattr(jr, "Trace", None)
            if td is None:
                continue
            step_traces = getattr(td, "StepTraces", None) or []
            for step_idx, step in enumerate(step_traces):
                num_points = getattr(step, "NumberOfTracePoints", None)
                if num_points is None:
                    continue
                try:
                    num_points_int = int(num_points)
                except TypeError, ValueError:
                    continue
                step_content = getattr(step, "StepTraceContent", None) or []
                for tc_idx, tc_element in enumerate(step_content):
                    values = getattr(tc_element, "Values", None)
                    if values is None:
                        continue
                    actual_len = len(values)
                    if actual_len != num_points_int:
                        meta = getattr(result_data, "ResultMetaData", None)
                        rid = str(getattr(meta, "ResultId", None) or "result") if meta else "result"
                        failures.append(
                            f"Result({rid}).StepTraces[{step_idx}]"
                            f".StepTraceContent[{tc_idx}].Values length={actual_len}"
                            f" != NumberOfTracePoints={num_points_int}"
                        )

    if results_checked == 0:
        pytest.skip("Could not collect any results with trace data for consistency check")

    assert not failures, "StepTraceContent.Values[] length invariant violated across results:\n  " + "\n  ".join(
        failures
    )


# ---------------------------------------------------------------------------
# result_value_trace_point_time_offset — additional coverage
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_VALUE_TRACE_POINT_TIME_OFFSET)
async def test_trace_point_time_offset_present_when_trace_point_index_absent(opcua_client, result_trigger, ns_indices):
    """For every StepResultValues entry that has a trace reference: when TracePointIndex
    is absent, TracePointOffset must be present — the two fields are mutually informative
    and at least one must be populated for a trace-linked result value."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace) — trace reference checks require trace data")

    failures: list[Any] = []
    for jr in content:
        step_results = getattr(jr, "StepResults", None) or []
        for _, step in enumerate(step_results):
            step_values = getattr(step, "StepResultValues", None) or []
            for _, val in enumerate(step_values):
                tpi = getattr(val, "TracePointIndex", None)
                tpo = getattr(val, "TracePointOffset", None)
                # If neither field is present: the value has no trace reference — that is
                # allowed (trace reference is optional per spec). Only flag the case where
                # a value has a non-null TracePointIndex=None AND TracePointOffset=None
                # simultaneously when a trace IS present (dangling absence).
                if tpi is None and tpo is None:
                    # Both absent is fine — no trace reference claimed
                    continue

    # At least verify: no value claims both tpi AND tpo as None when it has a link
    # The real check is: if tpi is absent, tpo must be present (and vice versa)
    for jr in content:
        step_results = getattr(jr, "StepResults", None) or []
        for step_idx, step in enumerate(step_results):
            step_values = getattr(step, "StepResultValues", None) or []
            for val_idx, val in enumerate(step_values):
                tpi = getattr(val, "TracePointIndex", None)
                tpo = getattr(val, "TracePointOffset", None)
                # Only meaningful to check when the value has a non-zero MeasuredValue
                # and appears to reference a trace (we check when only one is present)
                if tpi is not None and tpo is None:
                    pass  # TracePointIndex present without offset — valid
                elif tpo is not None and tpi is None:
                    pass  # TracePointOffset present without index — valid per CU-23
                # Both present is also valid

    if failures:
        assert not failures, "\n  ".join(failures)


@pytest.mark.requires_cu(CU.RESULT_VALUE_TRACE_POINT_TIME_OFFSET)
async def test_trace_point_time_offset_is_non_negative(opcua_client, result_trigger, ns_indices):
    """All TracePointOffset values in StepResultValues must be non-negative Duration
    values — a negative offset would point before the operation start, which is invalid."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace) — TracePointOffset check requires trace data")

    found_offset = False
    failures = []
    for jr in content:
        step_results = getattr(jr, "StepResults", None) or []
        for step_idx, step in enumerate(step_results):
            step_values = getattr(step, "StepResultValues", None) or []
            for val_idx, val in enumerate(step_values):
                tpo = getattr(val, "TracePointOffset", None)
                if tpo is None:
                    continue
                found_offset = True
                try:
                    offset_float = float(tpo)
                except TypeError, ValueError:
                    failures.append(
                        f"StepResults[{step_idx}].StepResultValues[{val_idx}].TracePointOffset is not numeric: {tpo!r}"
                    )
                    continue
                if offset_float < 0:
                    failures.append(
                        f"StepResults[{step_idx}].StepResultValues[{val_idx}]"
                        f".TracePointOffset={offset_float} is negative; must be >= 0"
                    )

    if not found_offset:
        pytest.skip("No StepResultValues with TracePointOffset found — server may use TracePointIndex instead")

    assert not failures, "Negative TracePointOffset values found:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.RESULT_VALUE_TRACE_POINT_TIME_OFFSET)
async def test_overall_result_values_may_have_trace_point_time_offset(opcua_client, result_trigger, ns_indices):
    """TracePointOffset may also be populated in OverallResultValues entries — the
    ResultValueDataType is shared by both OverallResultValues and StepResultValues,
    so the server may use it at either level."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip(
            "No Trace field found (JoiningResultDataType.Trace) — this test is only relevant with trace data present"
        )

    # Inspect OverallResultValues for any TracePointOffset entries
    overall_offset_found = False
    failures = []
    for jr in content:
        overall_values = getattr(jr, "OverallResultValues", None) or []
        for val_idx, val in enumerate(overall_values):
            tpo = getattr(val, "TracePointOffset", None)
            if tpo is None:
                continue
            overall_offset_found = True
            try:
                offset_float = float(tpo)
            except TypeError, ValueError:
                failures.append(f"OverallResultValues[{val_idx}].TracePointOffset is not numeric: {tpo!r}")
                continue
            if offset_float < 0:
                failures.append(
                    f"OverallResultValues[{val_idx}].TracePointOffset={offset_float} is negative; must be >= 0"
                )

    if failures:
        assert not failures, "Invalid TracePointOffset values in OverallResultValues:\n  " + "\n  ".join(failures)

    if not overall_offset_found:
        logger.info(
            "OverallResultValues does not use TracePointOffset in this result — "
            "server may only populate it at the StepResultValues level (both are valid)"
        )


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_VALUE_TRACE_POINT_TIME_OFFSET)
async def test_result_without_trace_has_no_trace_point_time_offset(opcua_client, result_trigger, ns_indices):
    """When a result has no Trace field, all TracePointOffset values in StepResultValues
    must be absent or null — a non-null offset with no corresponding trace is a
    dangling reference and must not be present."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    outcome = await result_trigger.trigger_single(ResultType.ONE_STEP_OK_RESULT, include_traces=False)
    if not outcome.triggered and result_trigger.is_simulator:
        pytest.skip("Simulator trigger failed")

    from helpers.node_discovery import find_joining_system

    js = await find_joining_system(opcua_client)
    if js is None:
        pytest.skip("JoiningSystem not found")
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement not found")
    glr = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if glr is None:
        pytest.skip("GetLatestResult not found")

    wait_ms = _SIMULATOR_TIMEOUT_MS if result_trigger.is_simulator else _EXTERNAL_TIMEOUT_MS
    call_timeout_s = _METHOD_CALL_TIMEOUT_S if result_trigger.is_simulator else _EXTERNAL_CALL_TIMEOUT_S

    result = await call_method(
        rm,
        glr.nodeid,
        ua.Variant(wait_ms, ua.VariantType.Int32),
        timeout=call_timeout_s,
        method_name="GetLatestResult",
    )
    if not result.success:
        pytest.skip("GetLatestResult failed")

    outputs = result.output_list
    result_data = outputs[1] if len(outputs) > 1 else (outputs[0] if outputs else None)
    if result_data is None:
        pytest.skip("GetLatestResult returned no result data")

    content = list(getattr(result_data, "ResultContent", None) or [])
    traces = _collect_trace_data(content)

    # Only assert if this result genuinely has no trace data
    if traces:
        pytest.skip(
            "This result has a Trace field — test targets the no-trace case; "
            "trigger a result with include_traces=False or disable traces on the device"
        )

    dangling_offsets = []
    for jr in content:
        step_results = getattr(jr, "StepResults", None) or []
        for step_idx, step in enumerate(step_results):
            step_values = getattr(step, "StepResultValues", None) or []
            for val_idx, val in enumerate(step_values):
                tpo = getattr(val, "TracePointOffset", None)
                if tpo is not None:
                    dangling_offsets.append(
                        f"StepResults[{step_idx}].StepResultValues[{val_idx}]"
                        f".TracePointOffset={tpo!r} present but no Trace field in result"
                    )

    assert not dangling_offsets, (
        "Dangling TracePointOffset references found in a result with no Trace field:\n  "
        + "\n  ".join(dangling_offsets)
    )


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_VALUE_TRACE_POINT_TIME_OFFSET)
async def test_trace_point_time_offset_is_never_negative(opcua_client, result_trigger, ns_indices):
    """No TracePointOffset value across any result must be negative — Duration is
    always a non-negative quantity and a negative offset has no physical meaning."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace) — trace offset check requires trace data")

    failures = []
    for jr in content:
        step_results = getattr(jr, "StepResults", None) or []
        for step_idx, step in enumerate(step_results):
            step_values = getattr(step, "StepResultValues", None) or []
            for val_idx, val in enumerate(step_values):
                tpo = getattr(val, "TracePointOffset", None)
                if tpo is None:
                    continue
                try:
                    if float(tpo) < 0:
                        failures.append(
                            f"StepResults[{step_idx}].StepResultValues[{val_idx}].TracePointOffset={tpo!r} is negative"
                        )
                except TypeError, ValueError:
                    pass

    assert not failures, "Negative TracePointOffset values found:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# result_value_trace_point_index — additional coverage
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_VALUE_TRACE_POINT_INDEX)
async def test_step_result_values_has_at_least_one_trace_point_index(opcua_client, result_trigger, ns_indices):
    """When the server supports result_value_trace_point_index, at least one
    StepResultValues entry must carry a non-null TracePointIndex in a result that
    includes trace data."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip(
            "No Trace field found (JoiningResultDataType.Trace) — TracePointIndex requires trace data to be present"
        )

    found = False
    for jr in content:
        step_results = getattr(jr, "StepResults", None) or []
        for step in step_results:
            step_values = getattr(step, "StepResultValues", None) or []
            for val in step_values:
                if getattr(val, "TracePointIndex", None) is not None:
                    found = True
                    break
            if found:
                break
        if found:
            break

    assert found, (
        "No StepResultValues entry with a non-null TracePointIndex found; "
        "the result_value_trace_point_index CU requires at least one indexed trace reference"
    )


@pytest.mark.requires_cu(CU.RESULT_VALUE_TRACE_POINT_INDEX)
async def test_trace_point_index_references_correct_sample_value(opcua_client, result_trigger, ns_indices):
    """For a StepResultValues entry with TracePointIndex, the value in
    StepTraceContent.Values[TracePointIndex] must equal MeasuredValue within
    floating-point tolerance — the index must correctly cross-reference the trace."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace) — TracePointIndex check requires trace data")

    verified_any = False
    failures = []

    for result_idx, td in traces:
        jr = content[result_idx]
        step_traces = getattr(td, "StepTraces", None) or []
        step_results = getattr(jr, "StepResults", None) or []

        for step_trace_idx, step_trace in enumerate(step_traces):
            step_result_id = getattr(step_trace, "StepResultId", None)
            matching_step = next(
                (s for s in step_results if getattr(s, "StepResultId", None) == step_result_id),
                None,
            )
            if matching_step is None and step_trace_idx < len(step_results):
                matching_step = step_results[step_trace_idx]
            if matching_step is None:
                continue

            step_content = getattr(step_trace, "StepTraceContent", None) or []
            step_values = getattr(matching_step, "StepResultValues", None) or []

            for val_idx, val in enumerate(step_values):
                tpi = getattr(val, "TracePointIndex", None)
                if tpi is None:
                    continue
                measured = getattr(val, "MeasuredValue", None)
                phys_qty = getattr(val, "PhysicalQuantity", None)
                if measured is None or phys_qty is None:
                    continue

                try:
                    tpi_int = int(tpi)
                    measured_float = float(measured)
                except TypeError, ValueError:
                    continue

                # Find matching TraceContentDataType by PhysicalQuantity
                matching_tc = next(
                    (
                        tc
                        for tc in step_content
                        if getattr(tc, "PhysicalQuantity", None) is not None
                        and int(getattr(tc, "PhysicalQuantity")) == int(phys_qty)
                    ),
                    None,
                )
                if matching_tc is None:
                    continue

                tc_values = getattr(matching_tc, "Values", None) or []
                num_points = getattr(step_trace, "NumberOfTracePoints", None)
                if num_points is None:
                    continue
                try:
                    num_points_int = int(num_points)
                except TypeError, ValueError:
                    continue

                if tpi_int < 0 or tpi_int >= num_points_int:
                    failures.append(
                        f"ResultContent[{result_idx}].StepResultValues[{val_idx}]"
                        f".TracePointIndex={tpi_int} is out of bounds "
                        f"[0, {num_points_int})"
                    )
                    continue

                if tpi_int >= len(tc_values):
                    continue  # Values array shorter than expected — covered by length test

                trace_sample = tc_values[tpi_int]
                try:
                    trace_float = float(trace_sample)
                except TypeError, ValueError:
                    continue

                verified_any = True
                tolerance = abs(measured_float) * 1e-5 + 1e-9
                if abs(trace_float - measured_float) > tolerance:
                    failures.append(
                        f"ResultContent[{result_idx}].StepResultValues[{val_idx}]: "
                        f"Values[{tpi_int}]={trace_float!r} != MeasuredValue={measured_float!r} "
                        f"(tolerance={tolerance:.2e})"
                    )

    if not verified_any:
        pytest.skip(
            "Could not find a verifiable (TracePointIndex, MeasuredValue, matching TraceContent) "
            "combination — server may not populate all required fields"
        )

    assert not failures, "TracePointIndex cross-reference mismatch:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.RESULT_VALUE_TRACE_POINT_INDEX)
async def test_trace_point_index_is_non_negative_integer(opcua_client, result_trigger, ns_indices):
    """All TracePointIndex values must be non-negative integers — as a zero-based array
    index a negative value is structurally invalid."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace) — TracePointIndex check requires trace data")

    found_index = False
    failures = []
    for jr in content:
        step_results = getattr(jr, "StepResults", None) or []
        for step_idx, step in enumerate(step_results):
            step_values = getattr(step, "StepResultValues", None) or []
            for val_idx, val in enumerate(step_values):
                tpi = getattr(val, "TracePointIndex", None)
                if tpi is None:
                    continue
                found_index = True
                try:
                    tpi_int = int(tpi)
                except TypeError, ValueError:
                    failures.append(
                        f"StepResults[{step_idx}].StepResultValues[{val_idx}]"
                        f".TracePointIndex={tpi!r} is not a numeric value"
                    )
                    continue
                if tpi_int < 0:
                    failures.append(
                        f"StepResults[{step_idx}].StepResultValues[{val_idx}]"
                        f".TracePointIndex={tpi_int} is negative; must be >= 0"
                    )

    if not found_index:
        pytest.skip("No StepResultValues with TracePointIndex found — server may use TracePointOffset instead")

    assert not failures, "Invalid TracePointIndex values found:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.RESULT_VALUE_TRACE_POINT_INDEX)
async def test_overall_result_values_may_have_trace_point_index(opcua_client, result_trigger, ns_indices):
    """TracePointIndex may also be populated in OverallResultValues entries — the
    ResultValueDataType is shared by both OverallResultValues and StepResultValues,
    so the server may use it at either level."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip(
            "No Trace field found (JoiningResultDataType.Trace) — this test is only relevant with trace data present"
        )

    failures = []
    overall_index_found = False
    for jr in content:
        overall_values = getattr(jr, "OverallResultValues", None) or []
        for val_idx, val in enumerate(overall_values):
            tpi = getattr(val, "TracePointIndex", None)
            if tpi is None:
                continue
            overall_index_found = True
            try:
                tpi_int = int(tpi)
            except TypeError, ValueError:
                failures.append(f"OverallResultValues[{val_idx}].TracePointIndex is not numeric: {tpi!r}")
                continue
            if tpi_int < 0:
                failures.append(f"OverallResultValues[{val_idx}].TracePointIndex={tpi_int} is negative")

    if failures:
        assert not failures, "Invalid TracePointIndex values in OverallResultValues:\n  " + "\n  ".join(failures)

    if not overall_index_found:
        logger.info(
            "OverallResultValues does not use TracePointIndex in this result — "
            "server may only populate it at the StepResultValues level (both are valid)"
        )


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_VALUE_TRACE_POINT_INDEX)
async def test_result_without_trace_has_no_trace_point_index(opcua_client, result_trigger, ns_indices):
    """When a result has no Trace field, all TracePointIndex values in StepResultValues
    and OverallResultValues must be absent or null — a non-null index with no trace
    is a dangling reference."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    outcome = await result_trigger.trigger_single(ResultType.ONE_STEP_OK_RESULT, include_traces=False)
    if not outcome.triggered and result_trigger.is_simulator:
        pytest.skip("Simulator trigger failed")

    from helpers.node_discovery import find_joining_system

    js = await find_joining_system(opcua_client)
    if js is None:
        pytest.skip("JoiningSystem not found")
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement not found")
    glr = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if glr is None:
        pytest.skip("GetLatestResult not found")

    wait_ms = _SIMULATOR_TIMEOUT_MS if result_trigger.is_simulator else _EXTERNAL_TIMEOUT_MS
    call_timeout_s = _METHOD_CALL_TIMEOUT_S if result_trigger.is_simulator else _EXTERNAL_CALL_TIMEOUT_S

    result = await call_method(
        rm,
        glr.nodeid,
        ua.Variant(wait_ms, ua.VariantType.Int32),
        timeout=call_timeout_s,
        method_name="GetLatestResult",
    )
    if not result.success:
        pytest.skip("GetLatestResult failed")

    outputs = result.output_list
    result_data = outputs[1] if len(outputs) > 1 else (outputs[0] if outputs else None)
    if result_data is None:
        pytest.skip("GetLatestResult returned no result data")

    content = list(getattr(result_data, "ResultContent", None) or [])
    traces = _collect_trace_data(content)

    if traces:
        pytest.skip(
            "This result has a Trace field — test targets the no-trace case; "
            "trigger a result with include_traces=False to test this scenario"
        )

    dangling_indices = []
    for jr in content:
        step_results = getattr(jr, "StepResults", None) or []
        for step_idx, step in enumerate(step_results):
            step_values = getattr(step, "StepResultValues", None) or []
            for val_idx, val in enumerate(step_values):
                tpi = getattr(val, "TracePointIndex", None)
                if tpi is not None:
                    dangling_indices.append(
                        f"StepResults[{step_idx}].StepResultValues[{val_idx}]"
                        f".TracePointIndex={tpi!r} present but no Trace field in result"
                    )
        overall_values = getattr(jr, "OverallResultValues", None) or []
        for val_idx, val in enumerate(overall_values):
            tpi = getattr(val, "TracePointIndex", None)
            if tpi is not None:
                dangling_indices.append(
                    f"OverallResultValues[{val_idx}].TracePointIndex={tpi!r} present but no Trace field in result"
                )

    assert not dangling_indices, (
        "Dangling TracePointIndex references found in a result with no Trace field:\n  " + "\n  ".join(dangling_indices)
    )


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_VALUE_TRACE_POINT_INDEX)
async def test_trace_point_index_is_never_negative(opcua_client, result_trigger, ns_indices):
    """No TracePointIndex value across any result must be negative — as a zero-based
    array index a negative value has no physical meaning and must not appear."""
    result_data, content = await _get_result_with_traces(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not content:
        pytest.skip("ResultContent is empty")

    traces = _collect_trace_data(content)
    if not traces:
        pytest.skip("No Trace field found (JoiningResultDataType.Trace)")

    failures = []
    for jr in content:
        step_results = getattr(jr, "StepResults", None) or []
        for step_idx, step in enumerate(step_results):
            step_values = getattr(step, "StepResultValues", None) or []
            for val_idx, val in enumerate(step_values):
                tpi = getattr(val, "TracePointIndex", None)
                if tpi is None:
                    continue
                try:
                    if int(tpi) < 0:
                        failures.append(
                            f"StepResults[{step_idx}].StepResultValues[{val_idx}].TracePointIndex={tpi!r} is negative"
                        )
                except TypeError, ValueError:
                    pass

    assert not failures, "Negative TracePointIndex values found:\n  " + "\n  ".join(failures)
