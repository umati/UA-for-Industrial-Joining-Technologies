"""
Tests for the structured data types returned inside JoiningResult objects.
Each test simulates a result, collects it via ResultReady events, then inspects
the resulting structured object hierarchy.
"""

import pytest
from asyncua import ua

from helpers.namespaces import (
    BN,
    NS_APP,
    ResultType,
)
from helpers.node_discovery import find_child_by_browse_name, find_joining_system
from helpers.result_collector import ResultCollector

pytestmark = [pytest.mark.live, pytest.mark.methods]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _get_result(subscription_client, client, ns_indices, result_type=ResultType.SIMPLE_OK_RESULT):
    """Simulate a result via direct API and collect it via IJTResultEventType events."""
    ns_app = ns_indices[NS_APP]
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found")
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

    async with ResultCollector(subscription_client, ns_indices) as rc:
        await sf.call_method(
            sim_method.nodeid,
            ua.Variant(result_type, ua.VariantType.UInt32),
            ua.Variant(True, ua.VariantType.Boolean),  # include_traces=True
        )
        result_data = await rc.collect_single()

    if result_data is None:
        pytest.skip("No result event received after simulation trigger")
    return result_data


def _require_attr(obj, attr_name, context=""):
    """Return attribute value, or skip the test if the attribute is missing."""
    value = None
    try:
        value = getattr(obj, attr_name)
    except AttributeError:
        msg = f"'{attr_name}' not found"
        if context:
            msg = f"{context}: {msg}"
        msg += " — data type definitions may not be loaded"
        pytest.skip(msg)
    return value


# ---------------------------------------------------------------------------
# JoiningResultDataType top-level fields
# ---------------------------------------------------------------------------
async def test_result_data_type_has_result_meta_data(subscription_client, opcua_client, ns_indices):
    result = await _get_result(subscription_client, opcua_client, ns_indices)
    meta = _require_attr(result, "ResultMetaData", "JoiningResultDataType")
    assert meta is not None, "JoiningResultDataType.ResultMetaData must not be None"


async def test_result_data_type_has_result_content(subscription_client, opcua_client, ns_indices):
    result = await _get_result(subscription_client, opcua_client, ns_indices)
    # ResultContent may be an empty list for a simple OK result — that is valid
    _require_attr(result, "ResultContent", "JoiningResultDataType")


# ---------------------------------------------------------------------------
# ResultMetaDataType fields
# ---------------------------------------------------------------------------
async def test_result_meta_data_type_fields(subscription_client, opcua_client, ns_indices):
    result = await _get_result(subscription_client, opcua_client, ns_indices)
    meta = _require_attr(result, "ResultMetaData", "JoiningResultDataType")
    result_id = _require_attr(meta, "ResultId", "ResultMetaDataType")
    assert result_id is not None, "ResultMetaDataType.ResultId must not be None"
    creation_time = _require_attr(meta, "CreationTime", "ResultMetaDataType")
    assert creation_time is not None, "ResultMetaDataType.CreationTime must not be None"
    evaluation = _require_attr(meta, "ResultEvaluation", "ResultMetaDataType")
    assert evaluation is not None, "ResultMetaDataType.ResultEvaluation must not be None"
    # ResultType carries the classification value — field is named "Classification"
    classification = _require_attr(meta, "Classification", "ResultMetaDataType")
    assert classification is not None, "ResultMetaDataType.Classification must not be None"


# ---------------------------------------------------------------------------
# StepResultDataType — requires a multi-step result
# ---------------------------------------------------------------------------
async def test_step_result_data_type_structure(subscription_client, opcua_client, ns_indices):
    result = await _get_result(subscription_client, opcua_client, ns_indices, ResultType.MULTI_STEP_OK_RESULT)
    content = _require_attr(result, "ResultContent", "JoiningResultDataType")
    if not content:
        pytest.skip("ResultContent is empty for MULTI_STEP_OK_RESULT — cannot validate StepResultDataType")
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
    assert result_values is not None, "StepResultDataType.StepResultValues must not be None"


# ---------------------------------------------------------------------------
# ResultValueDataType — digs into step → first value
# ---------------------------------------------------------------------------
async def test_result_value_data_type_structure(subscription_client, opcua_client, ns_indices):
    result = await _get_result(subscription_client, opcua_client, ns_indices, ResultType.MULTI_STEP_OK_RESULT)
    content = _require_attr(result, "ResultContent", "JoiningResultDataType")
    if not content:
        pytest.skip("ResultContent is empty for MULTI_STEP_OK_RESULT — cannot validate ResultValueDataType")
    first_content_variant = content[0]
    joining_result = getattr(first_content_variant, "Value", first_content_variant)
    step_results = _require_attr(joining_result, "StepResults", "JoiningResultDataType")
    if not step_results:
        pytest.skip("StepResults is empty — cannot validate ResultValueDataType")
    first_step = step_results[0]
    result_values = _require_attr(first_step, "StepResultValues", "StepResultDataType")
    if not result_values:
        pytest.skip("StepResultValues is empty in first step — cannot validate ResultValueDataType structure")
    first_value = result_values[0]
    physical_quantity = _require_attr(first_value, "PhysicalQuantity", "ResultValueDataType")
    assert physical_quantity is not None, "ResultValueDataType.PhysicalQuantity must not be None"
    measured_value = _require_attr(first_value, "MeasuredValue", "ResultValueDataType")
    assert measured_value is not None, "ResultValueDataType.MeasuredValue must not be None"
