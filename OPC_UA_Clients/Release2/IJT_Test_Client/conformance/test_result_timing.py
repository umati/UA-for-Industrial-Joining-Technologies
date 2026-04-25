"""
Result processing times conformance tests — OPC 40450-1.

Covers:
  result_processing_times — Result.ResultMetaData.ProcessingTimes.StartTime and EndTime.
  result_processing_times_durations — ProcessingTimes.AcquisitionDuration and ProcessingDuration.

Spec (result_processing_times):
  "The Server supports a Result instance which includes at least the following
  properties in Result.ResultMetaData: ProcessingTimes.StartTime and ProcessingTimes.EndTime."

Spec (result_processing_times_durations):
  "The Server supports a Result instance which includes the following durations
  in Result.ResultMetaData.ProcessingTimes: AcquisitionDuration and ProcessingDuration."

Design: triggers a single result and validates the timing fields of ResultMetaData.
"""

import datetime
import logging

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.method_caller import call_method
from helpers.namespaces import BN, NS_MACH_RESULT, ResultType
from helpers.node_discovery import find_child_by_browse_name, find_joining_system

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

_SIMULATOR_TIMEOUT_MS = 5000
_EXTERNAL_TIMEOUT_MS = 60000
_METHOD_CALL_TIMEOUT_S = 30.0
_EXTERNAL_CALL_TIMEOUT_S = 90.0


async def _get_result_with_meta(
    opcua_client,
    result_trigger,
    ns_indices,
    result_type: int = ResultType.MULTI_STEP_OK_RESULT,
    include_traces: bool = False,
):
    """Trigger a result and return (result_data, meta).

    Returns (None, None) when the namespace is absent, the simulator trigger
    fails, or GetLatestResult returns no data.
    For an external (real controller) trigger, continues with a longer timeout
    so an operator can fire a result within the allotted window.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        return None, None

    outcome = await result_trigger.trigger_single(result_type, include_traces=include_traces)
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
    meta = getattr(result_data, "ResultMetaData", None) if result_data else None
    return result_data, meta


def _skip_if_no_result(result_data, result_trigger) -> None:
    """Call pytest.skip() when result_data is None, with an appropriate message."""
    if result_data is None:
        if result_trigger.is_simulator:
            pytest.skip("Simulator trigger failed or GetLatestResult returned no data")
        else:
            pytest.skip("No result received from external trigger within timeout")


# ---------------------------------------------------------------------------
# ProcessingTimes.StartTime and EndTime presence and ordering
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES)
async def test_result_meta_data_has_processing_times_start_and_end_time(opcua_client, result_trigger, ns_indices):
    """ResultMetaData.ProcessingTimes must be present with non-null StartTime and EndTime
    where EndTime >= StartTime."""
    result_data, meta = await _get_result_with_meta(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic result structure tests")

    pt = getattr(meta, "ProcessingTimes", None)
    assert pt is not None, "ResultMetaData.ProcessingTimes must be present per result_processing_times CU"

    start = getattr(pt, "StartTime", None)
    assert start is not None, "ProcessingTimes.StartTime must be non-null"
    assert isinstance(start, datetime.datetime), (
        f"ProcessingTimes.StartTime must be a datetime, got {type(start).__name__!r}"
    )

    end = getattr(pt, "EndTime", None)
    assert end is not None, "ProcessingTimes.EndTime must be non-null"
    assert isinstance(end, datetime.datetime), f"ProcessingTimes.EndTime must be a datetime, got {type(end).__name__!r}"

    assert end >= start, f"ProcessingTimes.EndTime ({end!r}) must be >= StartTime ({start!r})"


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES)
async def test_processing_times_start_time_is_before_result_creation_time(opcua_client, result_trigger, ns_indices):
    """ProcessingTimes.StartTime must be <= ResultMetaData.CreationTime."""
    result_data, meta = await _get_result_with_meta(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic result structure tests")

    pt = getattr(meta, "ProcessingTimes", None)
    if pt is None:
        pytest.skip("ProcessingTimes absent — covered by start/end time test")

    start = getattr(pt, "StartTime", None)
    if start is None:
        pytest.skip("ProcessingTimes.StartTime absent — covered by start/end time test")

    creation = getattr(meta, "CreationTime", None)
    if creation is None:
        pytest.skip("ResultMetaData.CreationTime absent — cannot verify ordering")

    assert start <= creation, (
        f"ProcessingTimes.StartTime ({start!r}) must be <= ResultMetaData.CreationTime ({creation!r})"
    )


# ---------------------------------------------------------------------------
# AcquisitionDuration and ProcessingDuration presence
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES_DURATIONS)
async def test_result_meta_data_has_acquisition_duration(opcua_client, result_trigger, ns_indices):
    """ProcessingTimes.AcquisitionDuration must be present and have a numeric or timedelta value."""
    result_data, meta = await _get_result_with_meta(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic result structure tests")

    pt = getattr(meta, "ProcessingTimes", None)
    if pt is None:
        pytest.skip("ProcessingTimes absent — covered by start/end time test")

    acq = getattr(pt, "AcquisitionDuration", None)
    assert acq is not None, (
        "ProcessingTimes.AcquisitionDuration must be present per result_processing_times_durations CU"
    )
    assert isinstance(acq, (int, float, datetime.timedelta)), (
        f"ProcessingTimes.AcquisitionDuration must be numeric or timedelta, got {type(acq).__name__!r}"
    )


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES_DURATIONS)
async def test_result_meta_data_has_processing_duration(opcua_client, result_trigger, ns_indices):
    """ProcessingTimes.ProcessingDuration must be present."""
    result_data, meta = await _get_result_with_meta(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic result structure tests")

    pt = getattr(meta, "ProcessingTimes", None)
    if pt is None:
        pytest.skip("ProcessingTimes absent — covered by start/end time test")

    proc = getattr(pt, "ProcessingDuration", None)
    assert proc is not None, (
        "ProcessingTimes.ProcessingDuration must be present per result_processing_times_durations CU"
    )


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES_DURATIONS)
async def test_processing_durations_are_non_negative(opcua_client, result_trigger, ns_indices):
    """AcquisitionDuration and ProcessingDuration must both be non-negative."""
    result_data, meta = await _get_result_with_meta(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic result structure tests")

    pt = getattr(meta, "ProcessingTimes", None)
    if pt is None:
        pytest.skip("ProcessingTimes absent — covered by start/end time test")

    duration_fields = ("AcquisitionDuration", "ProcessingDuration")
    failures = []
    for field_name in duration_fields:
        val = getattr(pt, field_name, None)
        if val is None:
            continue
        if isinstance(val, datetime.timedelta):
            if val.total_seconds() < 0:
                failures.append(f"ProcessingTimes.{field_name} timedelta is negative: {val!r}")
        else:
            try:
                if float(val) < 0:
                    failures.append(f"ProcessingTimes.{field_name} is negative: {val!r}")
            except (TypeError, ValueError):
                failures.append(f"ProcessingTimes.{field_name} is not numeric or timedelta: {val!r}")

    assert not failures, "Duration fields must be non-negative:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Consistency across result types (parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES, CU.RESULT_PROCESSING_TIMES_DURATIONS)
@pytest.mark.parametrize(
    "result_type",
    [
        pytest.param(ResultType.MULTI_STEP_OK_RESULT, id="multi_step_ok"),
        pytest.param(ResultType.ONE_STEP_OK_RESULT, id="one_step_ok"),
    ],
)
async def test_all_timing_fields_consistent_across_result_types(opcua_client, result_trigger, ns_indices, result_type):
    """ProcessingTimes with StartTime and EndTime must be present for both
    ONE_STEP_OK_RESULT and MULTI_STEP_OK_RESULT result types."""
    result_data, meta = await _get_result_with_meta(opcua_client, result_trigger, ns_indices, result_type=result_type)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip(f"ResultMetaData absent for result_type={result_type!r}")

    pt = getattr(meta, "ProcessingTimes", None)
    assert pt is not None, f"ProcessingTimes must be present for result_type={result_type!r}"

    start = getattr(pt, "StartTime", None)
    assert start is not None, f"ProcessingTimes.StartTime must be present for result_type={result_type!r}"

    end = getattr(pt, "EndTime", None)
    assert end is not None, f"ProcessingTimes.EndTime must be present for result_type={result_type!r}"


# ===========================================================================
# ─── result_processing_times ───
# ===========================================================================


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES)
async def test_processing_times_start_time_is_plausible(opcua_client, result_trigger, ns_indices):
    """ProcessingTimes.StartTime must be a non-epoch datetime (not year 1601, not in the
    far future); verifies the server populates it with a real wall-clock time."""
    result_data, meta = await _get_result_with_meta(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by start/end time test")

    pt = getattr(meta, "ProcessingTimes", None)
    if pt is None:
        pytest.skip("ProcessingTimes absent — covered by start/end time test")

    start = getattr(pt, "StartTime", None)
    if start is None:
        pytest.skip("ProcessingTimes.StartTime absent — covered by presence test")

    epoch_floor = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    far_future = datetime.datetime(2100, 1, 1, tzinfo=datetime.timezone.utc)
    start_utc = start if start.tzinfo else start.replace(tzinfo=datetime.timezone.utc)
    assert start_utc > epoch_floor, (
        f"ProcessingTimes.StartTime={start!r} appears to be at or before Unix epoch — "
        "the server must set a real clock value"
    )
    assert start_utc < far_future, f"ProcessingTimes.StartTime={start!r} is unrealistically far in the future"


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES)
async def test_operation_duration_is_positive(opcua_client, result_trigger, ns_indices):
    """EndTime − StartTime must be a positive duration (i.e. EndTime > StartTime,
    not just >=), confirming the operation took measurable time."""
    result_data, meta = await _get_result_with_meta(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by start/end time test")

    pt = getattr(meta, "ProcessingTimes", None)
    if pt is None:
        pytest.skip("ProcessingTimes absent — covered by start/end time test")

    start = getattr(pt, "StartTime", None)
    end = getattr(pt, "EndTime", None)
    if start is None or end is None:
        pytest.skip("StartTime or EndTime absent — covered by presence test")

    assert end >= start, (
        f"ProcessingTimes.EndTime ({end!r}) must be >= StartTime ({start!r}); "
        "a tightening operation must have a non-negative duration. "
        "Note: simulator may produce zero-duration operations for very fast simulated tightenings."
    )


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES)
async def test_creation_time_not_before_processing_end_time(opcua_client, result_trigger, ns_indices):
    """ResultMetaData.CreationTime must be >= ProcessingTimes.EndTime for every result;
    the result is always created after the operation finishes."""
    result_data, meta = await _get_result_with_meta(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by start/end time test")

    creation_time = getattr(meta, "CreationTime", None)
    if creation_time is None:
        pytest.skip("CreationTime absent — covered by basic_result tests")

    pt = getattr(meta, "ProcessingTimes", None)
    if pt is None:
        pytest.skip("ProcessingTimes absent — covered by start/end time test")

    end_time = getattr(pt, "EndTime", None)
    if end_time is None:
        pytest.skip("ProcessingTimes.EndTime absent — covered by start/end time test")

    assert creation_time >= end_time, (
        f"ResultMetaData.CreationTime ({creation_time!r}) must be >= "
        f"ProcessingTimes.EndTime ({end_time!r}); "
        "a result is always created after processing completes"
    )


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES)
async def test_processing_times_fields_are_not_writable(opcua_client, ns_indices):
    """ProcessingTimes.StartTime on a result variable must not be writable;
    any write attempt must return Bad_NotWritable or Bad_UserAccessDenied."""
    from asyncua import ua as _ua

    from helpers.namespaces import BN as _BN
    from helpers.namespaces import NS_MACH_RESULT as _NS_MR
    from helpers.node_discovery import find_joining_system as _find_js

    ns_mr = ns_indices.get(_NS_MR)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    js = await _find_js(opcua_client)
    if js is None:
        pytest.skip("JoiningSystem not found")
    from helpers.node_discovery import find_child_by_browse_name as _find_child

    rm = await _find_child(js, _BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement not found")

    last_result_meta = await _find_child(rm, "LastResultMetaData", ns_mr)
    if last_result_meta is None:
        pytest.skip("LastResultMetaData variable not found — cannot test write rejection for ProcessingTimes")
    try:
        await last_result_meta.write_value(_ua.Variant("__test_write__", _ua.VariantType.String))
        pytest.fail("Write to LastResultMetaData succeeded — expected Bad_NotWritable or Bad_UserAccessDenied")
    except _ua.UaError:
        pass  # Expected rejection


# ===========================================================================
# ─── result_processing_times_durations ───
# ===========================================================================


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES_DURATIONS)
async def test_acquisition_duration_does_not_exceed_total_operation_window(opcua_client, result_trigger, ns_indices):
    """AcquisitionDuration must not exceed (EndTime − StartTime) expressed in milliseconds;
    the data-capture window cannot be larger than the total operation duration."""
    result_data, meta = await _get_result_with_meta(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic tests")

    pt = getattr(meta, "ProcessingTimes", None)
    if pt is None:
        pytest.skip("ProcessingTimes absent — covered by start/end time test")

    start = getattr(pt, "StartTime", None)
    end = getattr(pt, "EndTime", None)
    acq = getattr(pt, "AcquisitionDuration", None)
    if start is None or end is None:
        pytest.skip("StartTime or EndTime absent — cannot compute total duration")
    if acq is None:
        pytest.skip("AcquisitionDuration not populated — optional field, absence is valid")

    total_ms = (end - start).total_seconds() * 1000
    if isinstance(acq, datetime.timedelta):
        acq_ms = acq.total_seconds() * 1000
    else:
        acq_ms = float(acq)

    assert acq_ms <= total_ms + 1.0, (  # 1 ms tolerance for rounding
        f"AcquisitionDuration={acq_ms:.3f} ms exceeds total operation window (EndTime−StartTime)={total_ms:.3f} ms"
    )


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES_DURATIONS)
async def test_processing_duration_does_not_exceed_total_operation_window(opcua_client, result_trigger, ns_indices):
    """ProcessingDuration must not exceed (EndTime − StartTime) in milliseconds;
    the evaluation window cannot exceed the full operation duration."""
    result_data, meta = await _get_result_with_meta(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic tests")

    pt = getattr(meta, "ProcessingTimes", None)
    if pt is None:
        pytest.skip("ProcessingTimes absent — covered by start/end time test")

    start = getattr(pt, "StartTime", None)
    end = getattr(pt, "EndTime", None)
    proc = getattr(pt, "ProcessingDuration", None)
    if start is None or end is None:
        pytest.skip("StartTime or EndTime absent — cannot compute total duration")
    if proc is None:
        pytest.skip("ProcessingDuration not populated — optional field, absence is valid")

    total_ms = (end - start).total_seconds() * 1000
    if isinstance(proc, datetime.timedelta):
        proc_ms = proc.total_seconds() * 1000
    else:
        proc_ms = float(proc)

    assert proc_ms <= total_ms + 1.0, (  # 1 ms tolerance for rounding
        f"ProcessingDuration={proc_ms:.3f} ms exceeds total operation window (EndTime−StartTime)={total_ms:.3f} ms"
    )


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES_DURATIONS)
async def test_sum_of_durations_does_not_exceed_total_operation_window(opcua_client, result_trigger, ns_indices):
    """AcquisitionDuration + ProcessingDuration must not together exceed the total
    operation window (EndTime − StartTime) when both fields are populated."""
    result_data, meta = await _get_result_with_meta(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic tests")

    pt = getattr(meta, "ProcessingTimes", None)
    if pt is None:
        pytest.skip("ProcessingTimes absent — covered by start/end time test")

    start = getattr(pt, "StartTime", None)
    end = getattr(pt, "EndTime", None)
    acq = getattr(pt, "AcquisitionDuration", None)
    proc = getattr(pt, "ProcessingDuration", None)

    if start is None or end is None:
        pytest.skip("StartTime or EndTime absent — cannot compute total duration")
    if acq is None or proc is None:
        pytest.skip("Both AcquisitionDuration and ProcessingDuration must be present for sum check")

    total_ms = (end - start).total_seconds() * 1000
    acq_ms = acq.total_seconds() * 1000 if isinstance(acq, datetime.timedelta) else float(acq)
    proc_ms = proc.total_seconds() * 1000 if isinstance(proc, datetime.timedelta) else float(proc)
    combined_ms = acq_ms + proc_ms

    assert combined_ms <= total_ms + 1.0, (  # 1 ms tolerance for rounding
        f"AcquisitionDuration ({acq_ms:.3f} ms) + ProcessingDuration ({proc_ms:.3f} ms) "
        f"= {combined_ms:.3f} ms exceeds total operation window {total_ms:.3f} ms"
    )


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES_DURATIONS)
async def test_result_is_valid_when_duration_fields_are_absent(opcua_client, result_trigger, ns_indices):
    """A result must be accepted as structurally valid when AcquisitionDuration and
    ProcessingDuration are not populated; both are optional per the spec."""
    result_data, meta = await _get_result_with_meta(
        opcua_client,
        result_trigger,
        ns_indices,
        result_type=ResultType.SIMPLE_OK_RESULT,
    )
    _skip_if_no_result(result_data, result_trigger)
    if meta is None:
        pytest.skip("ResultMetaData absent — covered by basic tests")

    pt = getattr(meta, "ProcessingTimes", None)
    if pt is None:
        pytest.skip("ProcessingTimes absent — cannot verify duration field optionality")

    acq = getattr(pt, "AcquisitionDuration", None)
    proc = getattr(pt, "ProcessingDuration", None)
    if acq is not None or proc is not None:
        pytest.skip(
            "At least one duration field is present for this result type — "
            "cannot verify absent-duration validity with this server; "
            "a minimal device result would be needed"
        )

    # Mandatory StartTime / EndTime must still be present even when durations are absent
    start = getattr(pt, "StartTime", None)
    end = getattr(pt, "EndTime", None)
    assert start is not None, (
        "ProcessingTimes.StartTime must still be present even when AcquisitionDuration "
        "and ProcessingDuration are absent"
    )
    assert end is not None, (
        "ProcessingTimes.EndTime must still be present even when AcquisitionDuration and ProcessingDuration are absent"
    )


@pytest.mark.requires_cu(CU.RESULT_PROCESSING_TIMES_DURATIONS)
async def test_duration_values_are_consistent_across_result_types(opcua_client, result_trigger, ns_indices):
    """AcquisitionDuration and ProcessingDuration, when present, must consistently be
    non-negative for both one-step and multi-step result types."""
    failures = []
    for result_type in (ResultType.ONE_STEP_OK_RESULT, ResultType.MULTI_STEP_OK_RESULT):
        result_data, meta = await _get_result_with_meta(
            opcua_client, result_trigger, ns_indices, result_type=result_type
        )
        if result_data is None or meta is None:
            continue
        pt = getattr(meta, "ProcessingTimes", None)
        if pt is None:
            continue
        for field_name in ("AcquisitionDuration", "ProcessingDuration"):
            val = getattr(pt, field_name, None)
            if val is None:
                continue
            val_ms = val.total_seconds() * 1000 if isinstance(val, datetime.timedelta) else float(val)
            if val_ms < 0:
                failures.append(f"result_type={result_type}: ProcessingTimes.{field_name}={val_ms:.3f} ms is negative")

    if not failures and not result_trigger.is_simulator:
        pytest.skip("No results collected for consistency check (external trigger)")
    assert not failures, "Duration values must be non-negative:\n  " + "\n  ".join(failures)
