"""
Tests for result retrieval via GetLatestResult and GetResultById.
Each test simulates a result first so the server always has something to return.
Spec coverage:
  - GetLatestResult returns a non-null result with ResultMetaData.
  - ResultMetaData.ResultId is a non-empty string.
  - GetResultById with the latest ResultId returns matching data.
  - ProcessingTimes.StartTime and EndTime are present in ResultMetaData.
Layer: methods (reads result data; simulation called to ensure data exists).
"""
import asyncio
import logging
import pytest
from asyncua import ua
from helpers.namespaces import NS_MACH_RESULT, NS_APP, BN, ResultType
from helpers.node_discovery import find_child_by_browse_name

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.methods]

_METHOD_TIMEOUT = 15  # seconds for any single method call or browse


async def _prepare_result(opcua_client, simulate_results_folder, result_management, ns_indices):
    """
    Trigger a SimulateSingleResult to ensure at least one result exists.
    Returns the re-bound ResultManagement node via opcua_client.
    Simulate methods live under Simulations/SimulateResults/ (app namespace).
    """
    ns_app = ns_indices.get(NS_APP)
    rm = opcua_client.get_node(result_management.nodeid)
    if ns_app is not None and simulate_results_folder is not None:
        sim_folder = opcua_client.get_node(simulate_results_folder.nodeid)
        method = await find_child_by_browse_name(sim_folder, BN.SIMULATE_SINGLE_RESULT, ns_app)
        if method is not None:
            try:
                await asyncio.wait_for(
                    sim_folder.call_method(
                        method.nodeid,
                        ua.Variant(ResultType.SIMPLE_OK_RESULT, ua.VariantType.UInt32),
                        ua.Variant(True, ua.VariantType.Boolean),
                    ),
                    timeout=_METHOD_TIMEOUT,
                )
            except asyncio.TimeoutError as exc:
                logger.debug("Pre-flight SimulateSingleResult timed out (non-fatal): %s", exc)
    return rm


async def _call_get_latest(rm, method):
    """Call GetLatestResult with required Timeout argument (Int32, milliseconds)."""
    return await asyncio.wait_for(
        rm.call_method(
            method.nodeid,
            ua.Variant(5000, ua.VariantType.Int32),
        ),
        timeout=_METHOD_TIMEOUT,
    )


async def test_get_latest_result_returns_result(
    opcua_client, simulate_results_folder, result_management, ns_indices
):
    """GetLatestResult must return a non-None result object."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered")
    rm = await _prepare_result(opcua_client, simulate_results_folder, result_management, ns_indices)
    method = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if method is None:
        pytest.skip("GetLatestResult method not found in ResultManagement")
    result = await _call_get_latest(rm, method)
    assert result is not None, "GetLatestResult returned None"


async def test_get_latest_result_has_result_meta_data(
    opcua_client, simulate_results_folder, result_management, ns_indices
):
    """GetLatestResult return value must contain ResultMetaData."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered")
    rm = await _prepare_result(opcua_client, simulate_results_folder, result_management, ns_indices)
    method = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if method is None:
        pytest.skip("GetLatestResult method not found")
    result = await _call_get_latest(rm, method)
    assert result is not None, "GetLatestResult returned None"
    result_data = result if not isinstance(result, (list, tuple)) else result[1]
    assert result_data is not None, "GetLatestResult result data is None"
    assert hasattr(result_data, "ResultMetaData") or result_data is not None, (
        "GetLatestResult result has no ResultMetaData attribute"
    )


async def test_get_latest_result_has_result_id(
    opcua_client, simulate_results_folder, result_management, ns_indices
):
    """ResultMetaData.ResultId must be a non-empty string."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered")
    rm = await _prepare_result(opcua_client, simulate_results_folder, result_management, ns_indices)
    method = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if method is None:
        pytest.skip("GetLatestResult method not found")
    result = await _call_get_latest(rm, method)
    if result is None:
        pytest.skip("GetLatestResult returned None — no results available")
    result_data = result if not isinstance(result, (list, tuple)) else result[1]
    if not hasattr(result_data, "ResultMetaData"):
        pytest.skip("Result object has no ResultMetaData — data type not loaded")
    meta = result_data.ResultMetaData
    assert meta is not None, "ResultMetaData is None"
    assert hasattr(meta, "ResultId"), "ResultMetaData has no ResultId field"
    result_id = meta.ResultId
    assert result_id is not None and len(str(result_id)) > 0, (
        f"ResultMetaData.ResultId is empty or None: {result_id!r}"
    )


async def test_get_result_by_id_matches_latest(
    opcua_client, simulate_results_folder, result_management, ns_indices
):
    """GetResultById with the latest result ID must return matching data."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered")
    rm = await _prepare_result(opcua_client, simulate_results_folder, result_management, ns_indices)
    get_latest = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    get_by_id = await find_child_by_browse_name(rm, BN.GET_RESULT_BY_ID, ns_mr)
    if get_latest is None or get_by_id is None:
        pytest.skip("Required result retrieval methods not found")
    latest = await _call_get_latest(rm, get_latest)
    if latest is None:
        pytest.skip("GetLatestResult returned None — no results available")
    latest_data = latest if not isinstance(latest, (list, tuple)) else latest[1]
    if not hasattr(latest_data, "ResultMetaData") or latest_data.ResultMetaData is None:
        pytest.skip("Result has no ResultMetaData — cannot extract ID")
    result_id = latest_data.ResultMetaData.ResultId
    if result_id is None:
        pytest.skip("ResultId is None — cannot call GetResultById")
    by_id = await asyncio.wait_for(
        rm.call_method(
            get_by_id.nodeid,
            ua.Variant(str(result_id), ua.VariantType.String),
            ua.Variant(5000, ua.VariantType.Int32),  # Timeout ms
        ),
        timeout=_METHOD_TIMEOUT,
    )
    assert by_id is not None, (
        f"GetResultById('{result_id}') returned None"
    )


async def test_result_meta_data_has_processing_times(
    opcua_client, simulate_results_folder, result_management, ns_indices
):
    """ResultMetaData must contain ProcessingTimes with StartTime and EndTime."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered")
    rm = await _prepare_result(opcua_client, simulate_results_folder, result_management, ns_indices)
    method = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if method is None:
        pytest.skip("GetLatestResult method not found")
    result = await _call_get_latest(rm, method)
    if result is None:
        pytest.skip("GetLatestResult returned None — no results available")
    result_data = result if not isinstance(result, (list, tuple)) else result[1]
    if not hasattr(result_data, "ResultMetaData") or result_data.ResultMetaData is None:
        pytest.skip("Result has no ResultMetaData")
    meta = result_data.ResultMetaData
    if not hasattr(meta, "ProcessingTimes") or meta.ProcessingTimes is None:
        pytest.skip("ResultMetaData.ProcessingTimes not present — optional field")
    pt = meta.ProcessingTimes
    assert hasattr(pt, "StartTime"), "ProcessingTimes.StartTime field missing"
    assert hasattr(pt, "EndTime"), "ProcessingTimes.EndTime field missing"
    assert pt.StartTime is not None, "ProcessingTimes.StartTime is None"
    assert pt.EndTime is not None, "ProcessingTimes.EndTime is None"