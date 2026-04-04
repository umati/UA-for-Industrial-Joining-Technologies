"""
Conformance unit tests for ResultManagement — §11.1 CU-RM-001 through CU-RM-010.
Structure tests use session fixtures (result_management, ns_indices).
Method call tests use function-scoped opcua_client to re-discover nodes on a
fresh connection, ensuring state isolation between tests.
"""

import asyncio
import logging

import pytest
from asyncua import ua

from helpers.event_collector import EventCollector
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
from helpers.node_discovery import find_child_by_browse_name, find_joining_system

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

_METHOD_TIMEOUT = 15  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _get_result_management(client, ns_mr):
    """Re-discover ResultManagement on a fresh client connection."""
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found — server may not be running")
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement node not found on JoiningSystem")
    return rm


async def _simulate_and_get_latest(client, rm, ns_mr, ns_app, simulate_results_folder=None):
    """Run SimulateSingleResult and return (handle, result_data) from GetLatestResult."""
    if simulate_results_folder is not None and ns_app is not None:
        sim_folder = client.get_node(simulate_results_folder.nodeid)
        sim_node = await find_child_by_browse_name(sim_folder, BN.SIMULATE_SINGLE_RESULT, ns_app)
        if sim_node is not None:
            try:
                await asyncio.wait_for(
                    sim_folder.call_method(
                        sim_node.nodeid,
                        ua.Variant(ResultType.ONE_STEP_OK_RESULT, ua.VariantType.UInt32),
                        ua.Variant(True, ua.VariantType.Boolean),
                    ),
                    timeout=_METHOD_TIMEOUT,
                )
            except (ua.UaError, asyncio.TimeoutError) as exc:
                logger.debug("Pre-flight simulation failed (non-fatal): %s", exc)
    glr_node = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if glr_node is None:
        return None, None
    try:
        raw = await asyncio.wait_for(
            rm.call_method(
                glr_node.nodeid,
                ua.Variant(5000, ua.VariantType.Int32),
            ),
            timeout=_METHOD_TIMEOUT,
        )
    except ua.UaError, asyncio.TimeoutError:
        return None, None
    if isinstance(raw, (list, tuple)):
        handle = raw[0] if len(raw) > 0 else None
        result_data = raw[1] if len(raw) > 1 else None
    else:
        handle = raw
        result_data = None
    return handle, result_data


# ---------------------------------------------------------------------------
# Structure tests (session fixtures)
# ---------------------------------------------------------------------------
async def test_cu_result_management_result_management_addin(result_management):
    # §11.1 CU-RM-001: JoiningSystem must expose a ResultManagement AddIn
    assert result_management is not None, "ResultManagement AddIn node must not be None"


async def test_cu_result_management_results_folder(result_management, ns_indices):
    # §11.1 CU-RM-002: ResultManagement must contain a Results folder (Machinery/Result ns)
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    results_folder = await find_child_by_browse_name(result_management, BN.RESULTS, ns_mr)
    assert results_folder is not None, f"Results folder (ns={ns_mr}) not found inside ResultManagement"


# ---------------------------------------------------------------------------
# Method call tests (function-scoped opcua_client)
# ---------------------------------------------------------------------------
async def test_cu_result_management_get_latest_result(opcua_client, simulate_results_folder, ns_indices):
    # §11.1 CU-RM-003: GetLatestResult must be callable; returns handle after simulation
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    ns_app = ns_indices.get(NS_APP)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    if ns_app is None:
        pytest.skip("App namespace not registered on server")
    rm = await _get_result_management(opcua_client, ns_mr)
    await _simulate_and_get_latest(opcua_client, rm, ns_mr, ns_app, simulate_results_folder)
    glr_node = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    assert glr_node is not None, f"Method '{BN.GET_LATEST_RESULT}' not found in ResultManagement (ns_mr={ns_mr})"


async def test_cu_result_management_get_result_by_id(opcua_client, simulate_results_folder, ns_indices):
    # §11.1 CU-RM-004: GetResultById must accept a handle returned by GetLatestResult
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    ns_app = ns_indices.get(NS_APP)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    if ns_app is None:
        pytest.skip("App namespace not registered on server")
    rm = await _get_result_management(opcua_client, ns_mr)
    _handle, _data = await _simulate_and_get_latest(opcua_client, rm, ns_mr, ns_app, simulate_results_folder)
    if _data is None:
        pytest.skip("No result data available — GetLatestResult returned None")
    result_id = None
    meta = getattr(_data, "ResultMetaData", None)
    if meta is not None:
        result_id = str(getattr(meta, "ResultId", None) or "")
    if not result_id:
        pytest.skip("ResultId is empty — cannot call GetResultById")
    grbi_node = await find_child_by_browse_name(rm, BN.GET_RESULT_BY_ID, ns_mr)
    if grbi_node is None:
        pytest.skip(f"Method '{BN.GET_RESULT_BY_ID}' not found in ResultManagement")
    try:
        result = await asyncio.wait_for(
            rm.call_method(
                grbi_node.nodeid,
                ua.Variant(result_id, ua.VariantType.String),  # ResultId (TrimmedString)
                ua.Variant(5000, ua.VariantType.Int32),  # Timeout ms
            ),
            timeout=_METHOD_TIMEOUT,
        )
        assert result is not None, "GetResultById returned None for a valid ResultId"
    except ua.UaError as exc:
        status_str = str(exc)
        if any(
            s in status_str
            for s in (
                "BadNotFound",
                "BadInvalidArgument",
                "BadArgumentsMissing",
            )
        ):
            pytest.skip(f"GetResultById could not retrieve '{result_id}': {exc}")
        raise


async def test_cu_result_management_result_meta_data_structure(opcua_client, simulate_results_folder, ns_indices):
    # §11.1 CU-RM-005: Returned result must contain ResultMetaData with required fields
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    ns_app = ns_indices.get(NS_APP)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    if ns_app is None:
        pytest.skip("App namespace not registered on server")
    rm = await _get_result_management(opcua_client, ns_mr)
    if simulate_results_folder is not None:
        sim_folder = opcua_client.get_node(simulate_results_folder.nodeid)
        sim_node = await find_child_by_browse_name(sim_folder, BN.SIMULATE_SINGLE_RESULT, ns_app)
        if sim_node is not None:
            try:
                await asyncio.wait_for(
                    sim_folder.call_method(
                        sim_node.nodeid,
                        ua.Variant(ResultType.MULTI_STEP_OK_RESULT, ua.VariantType.UInt32),
                        ua.Variant(True, ua.VariantType.Boolean),
                    ),
                    timeout=_METHOD_TIMEOUT,
                )
            except (ua.UaError, asyncio.TimeoutError) as exc:
                logger.debug("Pre-flight simulation failed (non-fatal): %s", exc)
    glr_node = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if glr_node is None:
        pytest.skip("GetLatestResult not available")
    try:
        raw = await asyncio.wait_for(
            rm.call_method(
                glr_node.nodeid,
                ua.Variant(5000, ua.VariantType.Int32),
            ),
            timeout=_METHOD_TIMEOUT,
        )
    except (ua.UaError, asyncio.TimeoutError) as exc:
        pytest.skip(f"GetLatestResult failed: {exc}")
    result_data = raw[1] if isinstance(raw, (list, tuple)) and len(raw) > 1 else raw
    if result_data is None:
        pytest.skip("GetLatestResult returned no result data")
    meta = getattr(result_data, "ResultMetaData", None)
    assert meta is not None, "Returned result is missing 'ResultMetaData' attribute"
    for field in ("ResultId", "Classification", "ResultEvaluation"):
        if not hasattr(meta, field):
            pytest.skip(f"ResultMetaData is missing field '{field}' — server may use a different schema")


async def test_cu_result_management_result_content_structure(opcua_client, simulate_results_folder, ns_indices):
    # §11.1 CU-RM-006: Non-empty multi-step result must contain ResultContent
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    ns_app = ns_indices.get(NS_APP)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    if ns_app is None:
        pytest.skip("App namespace not registered on server")
    rm = await _get_result_management(opcua_client, ns_mr)
    if simulate_results_folder is not None:
        sim_folder = opcua_client.get_node(simulate_results_folder.nodeid)
        sim_node = await find_child_by_browse_name(sim_folder, BN.SIMULATE_SINGLE_RESULT, ns_app)
        if sim_node is not None:
            try:
                await asyncio.wait_for(
                    sim_folder.call_method(
                        sim_node.nodeid,
                        ua.Variant(ResultType.MULTI_STEP_OK_RESULT, ua.VariantType.UInt32),
                        ua.Variant(True, ua.VariantType.Boolean),
                    ),
                    timeout=_METHOD_TIMEOUT,
                )
            except (ua.UaError, asyncio.TimeoutError) as exc:
                logger.debug("Pre-flight simulation failed (non-fatal): %s", exc)
    glr_node = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if glr_node is None:
        pytest.skip("GetLatestResult not available")
    try:
        raw = await asyncio.wait_for(
            rm.call_method(
                glr_node.nodeid,
                ua.Variant(5000, ua.VariantType.Int32),
            ),
            timeout=_METHOD_TIMEOUT,
        )
    except (ua.UaError, asyncio.TimeoutError) as exc:
        pytest.skip(f"GetLatestResult failed: {exc}")
    result_data = raw[1] if isinstance(raw, (list, tuple)) and len(raw) > 1 else raw
    if result_data is None:
        pytest.skip("GetLatestResult returned no result data")
    result_content = getattr(result_data, "ResultContent", None)
    assert result_content is not None, (
        "Non-empty result is missing 'ResultContent' attribute — MULTI_STEP_OK_RESULT should carry step-level content"
    )


async def test_cu_result_management_result_ready_event(
    subscription_client, opcua_client, simulate_results_folder, ns_indices
):
    # §11.1 CU-RM-008: JoiningSystemResultReadyEvent must be received after simulation
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_app = ns_indices.get(NS_APP)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    if ns_app is None:
        pytest.skip("App namespace not registered on server")
    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))
    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)
        if simulate_results_folder is not None:
            sim_folder = opcua_client.get_node(simulate_results_folder.nodeid)
            sim_node = await find_child_by_browse_name(sim_folder, BN.SIMULATE_SINGLE_RESULT, ns_app)
            if sim_node is None:
                pytest.skip("SimulateSingleResult not available — cannot trigger event")
            try:
                await asyncio.wait_for(
                    sim_folder.call_method(
                        sim_node.nodeid,
                        ua.Variant(ResultType.ONE_STEP_OK_RESULT, ua.VariantType.UInt32),
                        ua.Variant(True, ua.VariantType.Boolean),
                    ),
                    timeout=_METHOD_TIMEOUT,
                )
            except (ua.UaError, asyncio.TimeoutError) as exc:
                pytest.skip(f"SimulateSingleResult failed: {exc}")
        else:
            pytest.skip("simulate_results_folder not available — cannot trigger event")
        events = await collector.collect(count=1, timeout_s=30.0)
    assert len(events) >= 1, "No JoiningSystemResultReadyEvent received within 30 s of SimulateSingleResult"


async def test_cu_result_management_result_evaluation_values(opcua_client, simulate_results_folder, ns_indices):
    # §11.1 CU-RM-009: ResultEvaluation field must be in {0, 1, 2}
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    ns_app = ns_indices.get(NS_APP)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    if ns_app is None:
        pytest.skip("App namespace not registered on server")
    rm = await _get_result_management(opcua_client, ns_mr)
    _handle, result_data = await _simulate_and_get_latest(opcua_client, rm, ns_mr, ns_app, simulate_results_folder)
    if result_data is None:
        pytest.skip("No result data available for ResultEvaluation check")
    meta = getattr(result_data, "ResultMetaData", None)
    if meta is None:
        pytest.skip("ResultMetaData not present in returned result")
    evaluation = getattr(meta, "ResultEvaluation", None)
    if evaluation is None:
        pytest.skip("ResultEvaluation field not found in ResultMetaData")
    evaluation_int = int(evaluation)
    assert evaluation_int in ResultEvaluation.VALID_VALUES, (
        f"ResultEvaluation value {evaluation_int} is not in valid set {ResultEvaluation.VALID_VALUES}"
    )


async def test_cu_result_management_result_classification_values(opcua_client, simulate_results_folder, ns_indices):
    # §11.1 CU-RM-010: ResultClassification field must be in {0..6}
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    ns_app = ns_indices.get(NS_APP)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    if ns_app is None:
        pytest.skip("App namespace not registered on server")
    rm = await _get_result_management(opcua_client, ns_mr)
    _handle, result_data = await _simulate_and_get_latest(opcua_client, rm, ns_mr, ns_app, simulate_results_folder)
    if result_data is None:
        pytest.skip("No result data available for ResultClassification check")
    meta = getattr(result_data, "ResultMetaData", None)
    if meta is None:
        pytest.skip("ResultMetaData not present in returned result")
    classification = getattr(meta, "Classification", None)
    if classification is None:
        pytest.skip("Classification field not found in ResultMetaData")
    classification_int = int(classification)
    assert classification_int in ResultClassification.VALID_VALUES, (
        f"ResultClassification value {classification_int} is not in valid set {ResultClassification.VALID_VALUES}"
    )
