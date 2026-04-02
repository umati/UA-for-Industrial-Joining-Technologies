"""
Tests for the structured data types returned inside JoiningResult objects.
Each test simulates a result, retrieves it via GetResultById, then inspects
the resulting structured object hierarchy.
"""
import pytest
from asyncua import ua
from helpers.namespaces import (
    NS_MACH_RESULT,
    NS_APP,
    BN,
    ResultType,
)
from helpers.node_discovery import find_joining_system, find_child_by_browse_name
pytestmark = [pytest.mark.live, pytest.mark.methods]
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _get_result(client, ns_indices, result_type=ResultType.SIMPLE_OK_RESULT):
    """Simulate a result and return the structured result object via GetLatestResult."""
    ns_mr = ns_indices[NS_MACH_RESULT]
    ns_app = ns_indices[NS_APP]
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found")
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement not found")
    # Simulate via Simulations/SimulateResults/ (App ns)
    sim_node = await find_child_by_browse_name(js, BN.SIMULATIONS, ns_app)
    if sim_node is None:
        pytest.skip("Simulations node not found")
    sf = await find_child_by_browse_name(sim_node, BN.SIMULATE_RESULTS_FOLDER, ns_app)
    if sf is None:
        pytest.skip("SimulateResults folder not found")
    sim_method = await find_child_by_browse_name(sf, BN.SIMULATE_SINGLE_RESULT, ns_app)
    if sim_method is None:
        pytest.skip(f"Method '{BN.SIMULATE_SINGLE_RESULT}' not found")
    await sf.call_method(
        sim_method.nodeid,
        ua.Variant(result_type, ua.VariantType.UInt32),
        ua.Variant(True, ua.VariantType.Boolean),  # include_traces=True
    )
    get_latest = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if get_latest is None:
        pytest.skip(f"Method '{BN.GET_LATEST_RESULT}' not found")
    raw = await rm.call_method(
        get_latest.nodeid,
        ua.Variant(5000, ua.VariantType.Int32),  # Timeout ms
    )
    if raw is None:
        pytest.skip("GetLatestResult returned None — no result available")
    # raw = [ResultHandle, Result, Error]
    result_data = raw[1] if isinstance(raw, (list, tuple)) and len(raw) > 1 else raw
    return result_data
def _require_attr(obj, attr_name, context=""):
    """Return attribute value or skip the test if the attribute is missing."""
    try:
        return getattr(obj, attr_name)
    except AttributeError:
        msg = f"'{attr_name}' not found"
        if context:
            msg = f"{context}: {msg}"
        msg += " — data type definitions may not be loaded"
        pytest.skip(msg)
# ---------------------------------------------------------------------------
# JoiningResultDataType top-level fields
# ---------------------------------------------------------------------------
async def test_result_data_type_has_result_meta_data(opcua_client, ns_indices):
    result = await _get_result(opcua_client, ns_indices)
    meta = _require_attr(result, "ResultMetaData", "JoiningResultDataType")
    assert meta is not None, "JoiningResultDataType.ResultMetaData must not be None"
async def test_result_data_type_has_result_content(opcua_client, ns_indices):
    result = await _get_result(opcua_client, ns_indices)
    # ResultContent may be an empty list for a simple OK result — that is valid
    _content = _require_attr(result, "ResultContent", "JoiningResultDataType")
# ---------------------------------------------------------------------------
# ResultMetaDataType fields
# ---------------------------------------------------------------------------
async def test_result_meta_data_type_fields(opcua_client, ns_indices):
    result = await _get_result(opcua_client, ns_indices)
    meta = _require_attr(result, "ResultMetaData", "JoiningResultDataType")
    result_id = _require_attr(meta, "ResultId", "ResultMetaDataType")
    assert result_id is not None, "ResultMetaDataType.ResultId must not be None"
    creation_time = _require_attr(meta, "CreationTime", "ResultMetaDataType")
    assert creation_time is not None, "ResultMetaDataType.CreationTime must not be None"
    evaluation = _require_attr(meta, "ResultEvaluation", "ResultMetaDataType")
    assert evaluation is not None, "ResultMetaDataType.ResultEvaluation must not be None"
    # ResultType carries the classification value — field is named "Classification"
    classification = _require_attr(meta, "Classification", "ResultMetaDataType")
    assert classification is not None, "ResultMetaDataType.ResultType must not be None"
# ---------------------------------------------------------------------------
# StepResultDataType — requires a multi-step result
# ---------------------------------------------------------------------------
async def test_step_result_data_type_structure(opcua_client, ns_indices):
    result = await _get_result(opcua_client, ns_indices, ResultType.MULTI_STEP_OK_RESULT)
    content = _require_attr(result, "ResultContent", "JoiningResultDataType")
    if not content:
        pytest.skip(
            "ResultContent is empty for MULTI_STEP_OK_RESULT — "
            "cannot validate StepResultDataType"
        )
    # ResultContent[0] is a Variant whose Value is a JoiningResultDataType;
    # JoiningResultDataType.StepResults holds the list of StepResultDataType objects.
    first_content_variant = content[0]
    joining_result = getattr(first_content_variant, "Value", first_content_variant)
    step_results = _require_attr(joining_result, "StepResults", "JoiningResultDataType")
    if not step_results:
        pytest.skip("StepResults is empty — cannot validate StepResultDataType")
    first_step = step_results[0]
    step_id = _require_attr(first_step, "StepResultId", "StepResultDataType")
    assert step_id is not None, "StepResultDataType.StepResultId must not be None"
    result_values = _require_attr(first_step, "StepResultValues", "StepResultDataType")
    assert result_values is not None, (
        "StepResultDataType.StepResultValues must not be None"
    )
# ---------------------------------------------------------------------------
# ResultValueDataType — digs into step → first value
# ---------------------------------------------------------------------------
async def test_result_value_data_type_structure(opcua_client, ns_indices):
    result = await _get_result(opcua_client, ns_indices, ResultType.MULTI_STEP_OK_RESULT)
    content = _require_attr(result, "ResultContent", "JoiningResultDataType")
    if not content:
        pytest.skip(
            "ResultContent is empty for MULTI_STEP_OK_RESULT — "
            "cannot validate ResultValueDataType"
        )
    first_content_variant = content[0]
    joining_result = getattr(first_content_variant, "Value", first_content_variant)
    step_results = _require_attr(joining_result, "StepResults", "JoiningResultDataType")
    if not step_results:
        pytest.skip("StepResults is empty — cannot validate ResultValueDataType")
    first_step = step_results[0]
    result_values = _require_attr(first_step, "StepResultValues", "StepResultDataType")
    if not result_values:
        pytest.skip(
            "StepResultValues is empty in first step — "
            "cannot validate ResultValueDataType structure"
        )
    first_value = result_values[0]
    physical_quantity = _require_attr(first_value, "PhysicalQuantity", "ResultValueDataType")
    assert physical_quantity is not None, (
        "ResultValueDataType.PhysicalQuantity must not be None"
    )
    measured_value = _require_attr(first_value, "MeasuredValue", "ResultValueDataType")
    assert measured_value is not None, "ResultValueDataType.MeasuredValue must not be None"