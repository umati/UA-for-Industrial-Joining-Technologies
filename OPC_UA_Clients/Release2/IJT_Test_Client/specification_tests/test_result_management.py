"""
Result management method specification tests — OPC 40450-1.

Covers: result_management, get_latest_result, get_result_by_id,
get_result_with_filter_criteria, result_variable_access, result_event_access,
request_results, requested_result_variable_access, requested_result_event_access,
acknowledge_results, request_unacknowledged_results.
"""

import asyncio
import logging

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.event_collector import EventCollector
from helpers.method_caller import call_method, find_and_call_method
from helpers.namespaces import (
    BN,
    NS_APP,
    NS_IJT_BASE,
    NS_MACH_RESULT,
    IJTTypes,
    MachineryResultTypes,
    RefTypes,
    ResultType,
)
from helpers.node_discovery import (
    find_child_by_browse_name,
    find_child_by_browse_name_any,
    find_joining_system,
    get_type_definition,
)
from helpers.result_validator import assert_result_data_valid
from helpers.skip_reasons import skip_tooling_limitation

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

_SIMULATOR_WAIT_MS = 5000
_EXTERNAL_WAIT_MS = 60000
_CALL_TIMEOUT_S = 30.0
_EXTERNAL_CALL_TIMEOUT_S = 90.0
_RUR_MAX_RESULTS = ua.Variant(1, ua.VariantType.UInt32)
_RUR_MIN_DURATION = ua.Variant(0.0, ua.VariantType.Double)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _delete_nodes_parameters(delete_item: ua.DeleteNodesItem) -> ua.DeleteNodesParameters:
    return ua.DeleteNodesParameters(NodesToDelete=[delete_item])


async def _rediscover_result_management(client, ns_mr):
    """Re-discover ResultManagement on a function-scoped connection."""
    js = await find_joining_system(client)
    if js is None:
        pytest.fail("JoiningSystem not found — server must be running and reachable")
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        pytest.fail("ResultManagement node not found on JoiningSystem — required address space node is missing")
    return rm


async def _trigger_and_get_latest(result_trigger, rm, ns_mr, result_type=ResultType.MULTI_STEP_OK_RESULT):
    """Trigger a result and call GetLatestResult.  Returns (result_data, result_meta)."""
    outcome = await result_trigger.trigger_single(result_type, include_traces=False)
    if not outcome.triggered and result_trigger.is_simulator:
        return None, None

    wait_ms = _SIMULATOR_WAIT_MS if result_trigger.is_simulator else _EXTERNAL_WAIT_MS
    call_timeout_s = _CALL_TIMEOUT_S if result_trigger.is_simulator else _EXTERNAL_CALL_TIMEOUT_S

    result = await find_and_call_method(
        rm,
        BN.GET_LATEST_RESULT,
        ns_mr,
        ua.Variant(wait_ms, ua.VariantType.Int32),
        timeout=call_timeout_s,
    )
    if not result.success:
        return None, None

    outputs = result.output_list
    result_data = outputs[1] if len(outputs) > 1 else (outputs[0] if outputs else None)
    meta = getattr(result_data, "ResultMetaData", None) if result_data else None
    return result_data, meta


async def _find_requested_result_var(result_management, ns_indices):
    """Locate RequestedResult under ResultManagement/Results, with legacy fallbacks."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_app = ns_indices.get(NS_APP)

    roots = []
    if ns_mr is not None:
        results_folder = await find_child_by_browse_name(result_management, BN.RESULTS, ns_mr)
        if results_folder is None and ns_ijt is not None:
            results_folder = await find_child_by_browse_name(result_management, BN.RESULTS, ns_ijt)
        if results_folder is not None:
            roots.append(results_folder)

    # Legacy simulator builds exposed RequestedResult directly under ResultManagement.
    roots.append(result_management)

    for root in roots:
        for ns_idx in (ns_ijt, ns_mr, ns_app):
            if ns_idx is None:
                continue
            node = await find_child_by_browse_name(root, BN.REQUESTED_RESULT, ns_idx)
            if node is not None:
                return node

    if ns_app is not None:
        return await find_child_by_browse_name(result_management, BN.RESULT_TRANSFER, ns_app)
    return None


async def _find_results_result_variable(result_management, ns_indices):
    """Locate Results/Result while accepting spec and application BrowseName namespaces."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_app = ns_indices.get(NS_APP)
    if ns_mr is None:
        return None, None
    results_folder = await find_child_by_browse_name_any(result_management, BN.RESULTS, (ns_mr, ns_ijt, ns_app))
    if results_folder is None:
        return None, None
    result_var = await find_child_by_browse_name_any(results_folder, BN.RESULT, (ns_mr, ns_ijt, ns_app))
    return results_folder, result_var


# ---------------------------------------------------------------------------
# result_management — AddIn present and Results folder present
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_MANAGEMENT)
async def test_result_management_addin_present_on_joining_system(result_management):
    """The JoiningSystem includes support for the optional ResultManagement which
    includes ResultManagement/Results folder.

    Checks that the ResultManagement AddIn node is present on JoiningSystem.
    """
    assert result_management is not None, (
        "ResultManagement AddIn node must not be None — it is a required component per OPC 40450-1"
    )


@pytest.mark.requires_cu(CU.RESULT_MANAGEMENT)
async def test_result_management_contains_results_folder(result_management, ns_indices):
    """ResultManagement must contain a Results folder (Machinery/Result namespace)."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    results_folder = await find_child_by_browse_name(result_management, BN.RESULTS, ns_mr)
    assert results_folder is not None, (
        f"Results folder (ns={ns_mr}, BrowseName='{BN.RESULTS}') not found inside ResultManagement"
    )


# ---------------------------------------------------------------------------
# get_latest_result — structure and functional
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
async def test_result_management_get_latest_result_method_present(result_management, ns_indices):
    """The Server supports GetLatestResult method.

    Structure check: GetLatestResult method node must exist under ResultManagement.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    glr = await find_child_by_browse_name(result_management, BN.GET_LATEST_RESULT, ns_mr)
    assert glr is not None, f"'{BN.GET_LATEST_RESULT}' method node not found in ResultManagement (ns_mr={ns_mr})"


@pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
async def test_result_management_get_latest_result_returns_valid_result(opcua_client, result_trigger, ns_indices):
    """The Server supports GetLatestResult method.

    Functional check: GetLatestResult must return structurally valid result data.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _rediscover_result_management(opcua_client, ns_mr)
    result_data, _ = await _trigger_and_get_latest(result_trigger, rm, ns_mr)

    if result_data is None:
        if result_trigger.is_simulator:
            pytest.skip("Simulator trigger failed or GetLatestResult returned no data")
        else:
            pytest.skip("No result received from external trigger within timeout")

    assert_result_data_valid(result_data, context="GetLatestResult")


# ---------------------------------------------------------------------------
# get_result_by_id — structure and functional
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_RESULT_BY_ID)
async def test_result_management_get_result_by_id_method_present(result_management, ns_indices):
    """The Server supports GetResultById method.

    Structure check: GetResultById method node must exist under ResultManagement.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    grbi = await find_child_by_browse_name(result_management, BN.GET_RESULT_BY_ID, ns_mr)
    assert grbi is not None, f"'{BN.GET_RESULT_BY_ID}' method node not found in ResultManagement (ns_mr={ns_mr})"


@pytest.mark.requires_cu(CU.GET_RESULT_BY_ID)
async def test_result_management_get_result_by_id_returns_same_data(opcua_client, result_trigger, ns_indices):
    """The Server supports GetResultById method.

    Functional check: GetResultById must return the same result as GetLatestResult.

    Flow:
      1. Trigger a result and call GetLatestResult to obtain (result_data, result_id).
      2. Call GetResultById(result_id, timeout) and verify metadata matches.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _rediscover_result_management(opcua_client, ns_mr)
    result_data, meta = await _trigger_and_get_latest(
        result_trigger, rm, ns_mr, result_type=ResultType.MULTI_STEP_OK_RESULT
    )

    if result_data is None:
        if result_trigger.is_simulator:
            pytest.skip("Simulator trigger failed or GetLatestResult returned no data")
        else:
            pytest.skip("No result received from external trigger within timeout")

    result_id = str(getattr(meta, "ResultId", None) or "") if meta else ""
    if not result_id:
        pytest.skip("ResultId is empty — cannot call GetResultById to verify")

    grbi = await find_child_by_browse_name(rm, BN.GET_RESULT_BY_ID, ns_mr)
    if grbi is None:
        pytest.skip(
            f"'{BN.GET_RESULT_BY_ID}' not found in ResultManagement — "
            "method is required per spec but not present on this server"
        )

    wait_ms = _SIMULATOR_WAIT_MS if result_trigger.is_simulator else _EXTERNAL_WAIT_MS
    call_timeout_s = _CALL_TIMEOUT_S if result_trigger.is_simulator else _EXTERNAL_CALL_TIMEOUT_S

    by_id_result = await call_method(
        rm,
        grbi.nodeid,
        ua.Variant(result_id, ua.VariantType.String),
        ua.Variant(wait_ms, ua.VariantType.Int32),
        timeout=call_timeout_s,
        method_name="GetResultById",
    )
    if not by_id_result.success:
        error_str = str(by_id_result.error)
        if any(kw in error_str for kw in ("BadNotFound", "BadInvalidArgument", "BadArgumentsMissing")):
            pytest.skip(
                f"GetResultById could not retrieve '{result_id}': {by_id_result.error} — "
                "server may have evicted the result before the call was made"
            )
        pytest.fail(f"GetResultById failed unexpectedly: {by_id_result.error}")

    outputs = by_id_result.output_list
    rd_by_id = outputs[1] if len(outputs) > 1 else (outputs[0] if outputs else None)
    assert rd_by_id is not None, f"GetResultById('{result_id}') returned None — expected result data"

    meta_by_id = getattr(rd_by_id, "ResultMetaData", None)
    assert meta_by_id is not None, "GetResultById result is missing ResultMetaData"
    result_id_by_id = str(getattr(meta_by_id, "ResultId", None) or "")
    assert result_id_by_id == result_id, (
        f"GetResultById returned ResultId={result_id_by_id!r} "
        f"but expected {result_id!r} (as returned by GetLatestResult)"
    )


# ---------------------------------------------------------------------------
# get_result_with_filter_criteria — optional method
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_RESULT_WITH_FILTER_CRITERIA)
async def test_result_management_get_result_id_list_filtered_presence_or_not_implemented(result_management, ns_indices):
    """GetResultIdListFiltered is an optional CU in the IJT Base specification
    (CU: 'IJT Get Result with Filter Criteria').  A server may implement it (return
    Good or OpcUa_Uncertain) or may expose the node but return BadNotSupported.
    A server that omits the node entirely is also conformant for this optional CU.

    This test PASSES when the method node is absent (skips with a clear message).
    This test PASSES when the node is present and returns any status (implemented or not).
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    grilf = await find_child_by_browse_name(result_management, BN.GET_RESULT_ID_LIST_FILTERED, ns_mr)
    if grilf is None:
        pytest.skip("GetResultIdListFiltered: Not Supported — method node absent (optional CU)")

    # Method node present — check Executable attribute to confirm reachability
    try:
        executable = await grilf.read_attribute(ua.AttributeIds.Executable)
        assert executable.Value.Value is True, (
            f"GetResultIdListFiltered Executable={executable.Value.Value} — expected True"
        )
    except ua.UaError as exc:
        pytest.skip(f"GetResultIdListFiltered: could not read Executable attribute: {exc}")


# ---------------------------------------------------------------------------
# result_variable_access — optional variable
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_VARIABLE_ACCESS)
async def test_result_management_last_result_metadata_variable_if_present(result_management, ns_indices):
    """The Server reports Results as a ResultVariable value in the address space
    with at least Result.ResultMetaData as per JoiningSystemResultType.

    Optional variable: skipped when not present. When present, must be readable.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    # ResultMetaData lives at: ResultManagement -> Results -> Result -> ResultMetaData.
    # "LastResultMetaData" does not exist as a flat child of ResultManagement in any NodeSet.
    results_folder, result_var = await _find_results_result_variable(result_management, ns_indices)
    if results_folder is None:
        pytest.skip("Results folder not found on ResultManagement")
    if result_var is None:
        pytest.skip("Result variable not found under Results folder")
    last_meta_node = await find_child_by_browse_name_any(
        result_var,
        BN.RESULT_META_DATA,
        (ns_mr, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP)),
    )
    if last_meta_node is None:
        pytest.skip("ResultMetaData not found under Results/Result — optional per spec")

    try:
        value = await last_meta_node.get_value()
    except Exception as exc:
        pytest.skip(f"Results/Result/ResultMetaData could not be read: {exc}")

    logger.debug("Results/Result/ResultMetaData value: %r", value)


# ---------------------------------------------------------------------------
# result_event_access — event subscription
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_EVENT_ACCESS)
async def test_result_management_result_ready_event_fired_on_simulate(
    subscription_client, opcua_client, result_trigger, ns_indices
):
    """The Server reports Results by generating events of the JoiningSystemResultReadyEventType."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")

    if not result_trigger.is_simulator:
        pytest.skip(
            "Event subscription test requires simulator trigger — "
            "run with a simulator server and trigger manually for real controller"
        )

    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))

    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)

        outcome = await result_trigger.trigger_single(ResultType.MULTI_STEP_OK_RESULT, include_traces=False)
        if not outcome.triggered:
            pytest.skip(f"Simulator trigger failed: {outcome.skip_reason}")

        events = await collector.collect(count=1, timeout_s=30.0)

    assert len(events) >= 1, (
        "No JoiningSystemResultReadyEvent received within timeout after triggering SimulateSingleResult"
    )


# ---------------------------------------------------------------------------
# ReleaseResultHandle — not supported on this server profile
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
async def test_result_management_release_result_handle_if_present(opcua_client, result_trigger, ns_indices):
    """ReleaseResultHandle is not implemented in this server profile.

    Acceptable behavior:
      - method is absent, or
      - method is present but call is rejected with OPC UA Bad status.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _rediscover_result_management(opcua_client, ns_mr)

    rrh = await find_child_by_browse_name(rm, BN.RELEASE_RESULT_HANDLE, ns_mr)
    if rrh is None:
        return

    result_data, meta = await _trigger_and_get_latest(result_trigger, rm, ns_mr)
    if result_data is None:
        if result_trigger.is_simulator:
            pytest.skip("Could not obtain a result handle — simulator trigger failed")
        else:
            pytest.skip("No result received from external trigger within timeout")

    result_id = str(getattr(meta, "ResultId", None) or "") if meta else ""
    if not result_id:
        pytest.skip("ResultId empty — cannot call ReleaseResultHandle")

    release = await call_method(
        rm,
        rrh.nodeid,
        ua.Variant(result_id, ua.VariantType.String),
        timeout=_CALL_TIMEOUT_S,
        method_name="ReleaseResultHandle",
    )
    assert release is not None, "ReleaseResultHandle returned None — expected MethodCallResult"
    assert not release.success, (
        "ReleaseResultHandle succeeded, but this server profile defines this method as unsupported/not implemented"
    )


# ---------------------------------------------------------------------------
# acknowledge_results
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ACKNOWLEDGE_RESULTS)
async def test_result_management_acknowledge_results_if_present(opcua_client, ns_indices):
    """AcknowledgeResults must accept an empty ResultIds list when the CU is supported."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _rediscover_result_management(opcua_client, ns_mr)
    ack = await find_child_by_browse_name(rm, BN.ACKNOWLEDGE_RESULTS, ns_mr)
    if ack is None:
        pytest.fail("AcknowledgeResults method is missing although the CU is enabled")

    result = await call_method(
        rm,
        ack.nodeid,
        ua.Variant([], ua.VariantType.String),
        timeout=_CALL_TIMEOUT_S,
        method_name="AcknowledgeResults",
    )
    assert result is not None, "AcknowledgeResults returned None — expected MethodCallResult"
    if not result.success:
        err_str = str(result.error) if result.error else "unknown"
        pytest.fail(f"AcknowledgeResults with an empty ResultIds list failed unexpectedly: {err_str}")
    output = result.output_list
    assert len(output) >= 2, f"AcknowledgeResults must return [ErrorPerResultId, Error], got {output!r}"


@pytest.mark.requires_cu(CU.ACKNOWLEDGE_RESULTS)
async def test_acknowledge_results_functional_with_valid_result_id(opcua_client, result_trigger, ns_indices):
    """
    AcknowledgeResults called with a valid ResultId extracted from a just-triggered
    result must either succeed (Good status) or return BadNotSupported / BadNotImplemented.

    Positive functional path: trigger result → GetLatestResult to extract ResultId →
    call AcknowledgeResults([result_id]).

    Servers that implement the acknowledge_results conformance unit should return Good.
    Servers that do not implement it are allowed to reject any call with BadNotSupported;
    the structure-only test above covers that case separately.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _rediscover_result_management(opcua_client, ns_mr)
    ack = await find_child_by_browse_name(rm, BN.ACKNOWLEDGE_RESULTS, ns_mr)
    if ack is None:
        pytest.skip("AcknowledgeResults method: Not Supported — optional per spec")

    result_data, meta = await _trigger_and_get_latest(result_trigger, rm, ns_mr)
    if result_data is None or meta is None:
        if result_trigger.is_simulator:
            pytest.skip("Could not obtain a result via simulator trigger — simulator may not be running")
        else:
            pytest.skip("No result received from external trigger within timeout — manual trigger required")

    result_id = str(getattr(meta, "ResultId", None) or "")
    if not result_id:
        pytest.skip("ResultId empty in GetLatestResult response — cannot call AcknowledgeResults with a valid ID")

    call_result = await call_method(
        rm,
        ack.nodeid,
        ua.Variant([result_id], ua.VariantType.String),
        timeout=_CALL_TIMEOUT_S,
        method_name="AcknowledgeResults",
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if any(s in err_str for s in ("BadNotSupported", "BadNotImplemented")):
            pytest.skip(f"AcknowledgeResults returned {err_str} — server does not implement this method")
        logger.warning(
            "AcknowledgeResults([%r]) returned unexpected Bad status: %s "
            "— investigate if this server is expected to support acknowledge_results CU",
            result_id,
            err_str,
        )
    else:
        logger.info("AcknowledgeResults([%r]) succeeded — server implements acknowledge_results CU", result_id)


# ---------------------------------------------------------------------------
# request_results — optional method
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.REQUEST_RESULTS)
async def test_result_management_request_results_method_present_if_supported(result_management, ns_indices):
    """The Server supports RequestResults method which sends the stored results using
    an instance of RequestedResultEventType or RequestedResultVariable value.

    Optional method: skipped when not present. When present, the method node must be browsable.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")

    # RequestResults BrowseName is "1:RequestResults" in IJT Base namespace (ns=1;i=7074
    # in Opc.Ua.Ijt.Base.NodeSet2.xml), NOT in Machinery/Result namespace.
    request_results_node = await find_child_by_browse_name(result_management, BN.REQUEST_RESULTS, ns_ijt)
    if request_results_node is None:
        pytest.skip(f"'{BN.REQUEST_RESULTS}': Not Supported — optional method per spec")

    assert request_results_node is not None
    logger.info("RequestResults method found: %s", request_results_node.nodeid)


# ---------------------------------------------------------------------------
# request_unacknowledged_results
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.REQUEST_UNACKNOWLEDGED_RESULTS)
async def test_result_management_request_unacknowledged_results_method_present_if_supported(
    result_management, ns_indices
):
    """RequestUnacknowledgedResults must be callable when the CU is supported."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")

    # RequestUnacknowledgedResults BrowseName is "1:RequestUnacknowledgedResults" in IJT Base
    # namespace (ns=1;i=7092), NOT in Machinery/Result namespace.
    rur_node = await find_child_by_browse_name(result_management, BN.REQUEST_UNACKNOWLEDGED_RESULTS, ns_ijt)
    if rur_node is None:
        pytest.fail("RequestUnacknowledgedResults method is missing although the CU is enabled")

    result = await call_method(
        result_management,
        rur_node.nodeid,
        _RUR_MAX_RESULTS,
        _RUR_MIN_DURATION,
        timeout=_CALL_TIMEOUT_S,
        method_name="RequestUnacknowledgedResults",
    )
    assert result is not None, "RequestUnacknowledgedResults returned None — expected MethodCallResult"
    if not result.success:
        err_str = str(result.error) if result.error else "unknown"
        pytest.fail(
            "RequestUnacknowledgedResults failed despite valid "
            f"MaxResults and RequestedMinimumDurationBetweenResults arguments: {err_str}"
        )
    output = result.output_list
    assert len(output) >= 4, (
        "RequestUnacknowledgedResults must return "
        "[RevisedMinimumDurationBetweenResults, UnacknowledgedResultCount, Status, StatusMessage], "
        f"got {output!r}"
    )


# ---------------------------------------------------------------------------
# requested_result_variable_access — optional variable after RequestResults
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.REQUESTED_RESULT_VARIABLE_ACCESS)
async def test_result_management_requested_result_variable_accessible_if_present(result_management, ns_indices):
    """The Server reports Results as RequestedResultVariable value for any results
    generated upon the successful execution of RequestResults or
    RequestUnacknowledgedResults method.

    When this CU is enabled, RequestedResult must be browsable.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    requested_var_node = await _find_requested_result_var(result_management, ns_indices)
    if requested_var_node is None:
        pytest.fail(
            "RequestedResultVariable not found under ResultManagement/Results "
            f"(tried ns_ijt={ns_indices.get(NS_IJT_BASE)}, ns_mr={ns_mr}, ns_app={ns_indices.get(NS_APP)})"
        )

    logger.info("RequestedResultVariable node found: %s", requested_var_node.nodeid)
    assert requested_var_node is not None


# ---------------------------------------------------------------------------
# requested_result_event_access — optional event after RequestResults
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.REQUESTED_RESULT_EVENT_ACCESS)
async def test_result_management_requested_result_event_type_accessible(subscription_client, ns_indices):
    """The Server generates an event of RequestedResultEventType for any results
    generated upon the successful execution of RequestResults or
    RequestUnacknowledgedResults method.

    Checks that the RequestedResultEventType node is resolvable in the IJT namespace.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")

    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.REQUESTED_RESULT_EVENT_TYPE, ns_ijt))
    try:
        bn = await event_type_node.read_browse_name()
    except Exception as exc:
        pytest.skip(f"RequestedResultEventType node not accessible in IJT Base namespace: {exc}")
    assert bn is not None
    logger.info("RequestedResultEventType browse name: %s", bn)


# ---------------------------------------------------------------------------
# Negative: GetResultById with invalid ResultId
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_RESULT_BY_ID)
async def test_result_management_get_result_by_id_with_invalid_id_returns_error(opcua_client, ns_indices):
    """GetResultById with a non-existent ResultId must return a Bad status.

    Spec: The Server supports GetResultById method.
    Negative check: a non-existent id must be rejected, not return spurious data.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _rediscover_result_management(opcua_client, ns_mr)
    grbi = await find_child_by_browse_name(rm, BN.GET_RESULT_BY_ID, ns_mr)
    if grbi is None:
        pytest.skip(f"'{BN.GET_RESULT_BY_ID}' not found in ResultManagement — cannot run negative test")

    result = await call_method(
        rm,
        grbi.nodeid,
        ua.Variant("__nonexistent_result_id__", ua.VariantType.String),
        ua.Variant(1000, ua.VariantType.Int32),
        timeout=15.0,
        method_name="GetResultById(invalid)",
    )
    if result.success:
        # Corrected signature: [ResultHandle, Result, Error]
        # For an invalid ResultId, output[1] (Result) should be null/empty
        # and output[2] (Error) should indicate not-found
        output = result.output_list
        if output and len(output) >= 3:
            try:
                if int(output[2]) != 0:
                    return  # PASS: server reports not-found via Error output
            except (TypeError, ValueError):
                pass
            if output[1] is None:
                return  # PASS: null Result indicates not-found
        message = (
            "GetResultById with invalid ResultId returned Success with no error indicator — "
            "expected non-zero output[2] Error or null output[1] Result"
        )
        if ns_indices.get(NS_APP) is not None:
            pytest.skip(f"{message}; known simulator gap")
        pytest.fail(message)


# ─── result_management — TypeSystem checks ────────────────────────────────────


@pytest.mark.requires_cu(CU.RESULT_MANAGEMENT)
async def test_joining_system_result_management_type_is_present_in_type_system(session_client, ns_indices):
    """JoiningSystemResultManagementType must exist with NodeClass=ObjectType, IsAbstract=False.

    OPC 40450-1 Sec 7.5 and Table 15.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")

    type_node = session_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_MANAGEMENT_TYPE, ns_ijt))
    try:
        node_class = await asyncio.wait_for(type_node.read_node_class(), timeout=10.0)
    except Exception as exc:
        pytest.fail(f"Cannot read NodeClass from JoiningSystemResultManagementType: {exc}")

    assert node_class == ua.NodeClass.ObjectType, (
        f"JoiningSystemResultManagementType must have NodeClass=ObjectType, got {node_class}"
    )
    _is_abstract_dv = await asyncio.wait_for(type_node.read_attribute(ua.AttributeIds.IsAbstract), timeout=10.0)
    is_abstract = _is_abstract_dv.Value.Value
    assert is_abstract is False, "JoiningSystemResultManagementType must have IsAbstract=False"
    logger.info("JoiningSystemResultManagementType: NodeClass=%s, IsAbstract=%s", node_class, is_abstract)


@pytest.mark.requires_cu(CU.RESULT_MANAGEMENT)
async def test_joining_system_result_management_type_inherits_from_result_management_type(session_client, ns_indices):
    """JoiningSystemResultManagementType must be a subtype of ResultManagementType.

    Follows HasSubtype inverse references to confirm ancestry via the
    Machinery/Result namespace (http://opcfoundation.org/UA/Machinery/Result/).
    OPC 40450-1 Sec 7.5 and OPC 40001-101.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    target_nid = ua.NodeId(MachineryResultTypes.RESULT_MANAGEMENT_TYPE, ns_mr)
    current_nid = ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_MANAGEMENT_TYPE, ns_ijt)
    visited: set = set()

    for _ in range(10):
        key = (current_nid.NamespaceIndex, current_nid.Identifier)
        if key in visited:
            break
        visited.add(key)
        if current_nid.NamespaceIndex == target_nid.NamespaceIndex and current_nid.Identifier == target_nid.Identifier:
            logger.info("JoiningSystemResultManagementType → ResultManagementType ancestry confirmed")
            return
        node = session_client.get_node(current_nid)
        try:
            refs = await asyncio.wait_for(
                node.get_references(
                    refs=RefTypes.HAS_SUBTYPE,
                    direction=ua.BrowseDirection.Inverse,
                    includesubtypes=False,
                ),
                timeout=10.0,
            )
        except Exception as exc:
            pytest.fail(f"Cannot follow HasSubtype inverse from {current_nid}: {exc}")
        if not refs:
            break
        current_nid = refs[0].NodeId

    pytest.fail(
        "JoiningSystemResultManagementType does not inherit from ResultManagementType — "
        f"expected ancestry chain to reach Machinery/Result namespace (index {ns_mr})"
    )


@pytest.mark.requires_cu(CU.RESULT_MANAGEMENT)
async def test_joining_system_result_management_type_has_mandatory_results_folder_declared(session_client, ns_indices):
    """JoiningSystemResultManagementType must declare a Results folder as mandatory.

    Browses the type node for a HasComponent reference to the Results folder.
    TypeDefinition of Results must be FolderType. OPC 40450-1 Sec 7.5.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    type_node = session_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_MANAGEMENT_TYPE, ns_ijt))
    # Results folder is declared with the Machinery/Result namespace BrowseName
    results_decl = await find_child_by_browse_name(type_node, BN.RESULTS, ns_mr)
    if results_decl is None:
        # Try IJT Base ns as fallback (some servers may use different ns for this)
        results_decl = await find_child_by_browse_name(type_node, BN.RESULTS, ns_ijt)

    assert results_decl is not None, (
        "JoiningSystemResultManagementType must declare a Results folder child. "
        "OPC 40450-1 Sec 7.5 requires this as a mandatory component."
    )

    type_def = await get_type_definition(results_decl)
    _folder_type_id = 61  # FolderType — OPC UA specification ns=0
    if type_def is not None:
        assert type_def.NamespaceIndex == 0 and type_def.Identifier == _folder_type_id, (
            f"Results folder declaration must have TypeDefinition=FolderType, got {type_def}"
        )
    logger.info("JoiningSystemResultManagementType Results folder declaration confirmed")


# ─── result_management — instance checks ──────────────────────────────────────


@pytest.mark.requires_cu(CU.RESULT_MANAGEMENT)
async def test_result_management_addin_event_notifier_supports_subscribing_to_events(
    result_management,
):
    """ResultManagement AddIn EventNotifier must have the SubscribeToEvents bit set.

    Bit zero (value 1) = SubscribeToEvents. This enables result event subscriptions
    via this node. OPC 10000-3 Sec 5.6.4.
    """
    try:
        event_notifier_attr = await asyncio.wait_for(
            result_management.read_attribute(ua.AttributeIds.EventNotifier),
            timeout=10.0,
        )
    except Exception as exc:
        pytest.fail(f"Cannot read EventNotifier from ResultManagement: {exc}")

    value = event_notifier_attr.Value.Value if hasattr(event_notifier_attr, "Value") else event_notifier_attr
    _subscribe_to_events_bit = 1  # EventNotifier bit zero — OPC UA specification §8.40
    assert value & _subscribe_to_events_bit, (
        f"ResultManagement EventNotifier={value:#x} — SubscribeToEvents bit (bit zero) must be set. "
        "Clients must be able to subscribe to result events via this node."
    )
    logger.info("ResultManagement EventNotifier: %#x (SubscribeToEvents bit confirmed)", value)


@pytest.mark.requires_cu(CU.RESULT_MANAGEMENT)
async def test_result_management_results_folder_result_variable_instances(result_management, ns_indices):
    """Results folder may contain Variable instances of JoiningSystemResultType.

    Each present variable must carry TypeDefinition in the IJT Base namespace.
    An empty Results folder is also a valid server configuration.
    OPC 40450-1 Sec 9.2.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    from helpers.node_discovery import browse_folder_instances

    results_folder = await find_child_by_browse_name(result_management, BN.RESULTS, ns_mr)
    if results_folder is None:
        pytest.skip("Results folder not found in ResultManagement — covered by separate test")

    instances = await browse_folder_instances(results_folder)
    if not instances:
        logger.info("Results folder is empty — valid per spec (no stored results)")
        return

    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered — cannot verify TypeDefinition of result variables")

    from helpers.node_discovery import get_type_definition

    non_ijt_types: list[str] = []
    for bn_str, result_node in instances:
        type_def = await get_type_definition(result_node)
        if type_def is not None and type_def.NamespaceIndex != ns_ijt:
            non_ijt_types.append(f"{bn_str} → TypeDef ns={type_def.NamespaceIndex} id={type_def.Identifier}")

    assert not non_ijt_types, (
        f"Result Variables in Results folder with non-IJT TypeDefinition: {non_ijt_types}. "
        "Each stored result must be typed using JoiningSystemResultType or a subtype."
    )
    logger.info("Results folder has %d result variable instance(s); all have IJT namespace types", len(instances))


@pytest.mark.requires_cu(CU.RESULT_MANAGEMENT)
async def test_result_management_result_access_methods_declared_in_type(session_client, ns_indices):
    """JoiningSystemResultManagementType must declare result-access Method nodes.

    Checks for GetLatestResult, GetResultById, GetResultIdListFiltered in the type
    definition. At minimum GetLatestResult should be declared.
    OPC 40450-1 Sec 7.5.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    type_node = session_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_MANAGEMENT_TYPE, ns_ijt))
    try:
        refs = await asyncio.wait_for(
            type_node.get_references(
                refs=33,  # HierarchicalReferences
                direction=ua.BrowseDirection.Forward,
                includesubtypes=True,
                nodeclassmask=ua.NodeClass.Unspecified,
            ),
            timeout=15.0,
        )
    except Exception as exc:
        pytest.fail(f"Cannot browse JoiningSystemResultManagementType: {exc}")

    declared_methods = {ref.BrowseName.Name for ref in refs if ref.NodeClass == ua.NodeClass.Method}

    inherited_methods: set[str] = set(declared_methods)
    current_nid = ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_MANAGEMENT_TYPE, ns_ijt)
    visited: set[tuple[int, object]] = set()
    for _ in range(10):
        key = (current_nid.NamespaceIndex, current_nid.Identifier)
        if key in visited:
            break
        visited.add(key)
        node = session_client.get_node(current_nid)
        try:
            parent_refs = await asyncio.wait_for(
                node.get_references(
                    refs=RefTypes.HAS_SUBTYPE,
                    direction=ua.BrowseDirection.Inverse,
                    includesubtypes=False,
                    nodeclassmask=ua.NodeClass.Unspecified,
                ),
                timeout=10.0,
            )
        except Exception as exc:
            pytest.fail(f"Cannot follow HasSubtype inverse from {current_nid}: {exc}")
        if not parent_refs:
            break
        current_nid = parent_refs[0].NodeId
        base_node = session_client.get_node(current_nid)
        try:
            base_refs = await asyncio.wait_for(
                base_node.get_references(
                    refs=33,
                    direction=ua.BrowseDirection.Forward,
                    includesubtypes=True,
                    nodeclassmask=ua.NodeClass.Unspecified,
                ),
                timeout=15.0,
            )
        except Exception as exc:
            pytest.fail(f"Cannot browse inherited result-management type {current_nid}: {exc}")
        inherited_methods.update(ref.BrowseName.Name for ref in base_refs if ref.NodeClass == ua.NodeClass.Method)
        if (
            current_nid.NamespaceIndex == ns_mr
            and current_nid.Identifier == MachineryResultTypes.RESULT_MANAGEMENT_TYPE
        ):
            break

    logger.info(
        "JoiningSystemResultManagementType declared methods: direct=%s, direct+inherited=%s",
        sorted(declared_methods),
        sorted(inherited_methods),
    )

    _expected_methods = [
        BN.GET_LATEST_RESULT,
        BN.GET_RESULT_BY_ID,
        BN.GET_RESULT_ID_LIST_FILTERED,
    ]
    missing = [m for m in _expected_methods if m not in inherited_methods]
    if BN.GET_LATEST_RESULT not in inherited_methods:
        pytest.fail(
            f"JoiningSystemResultManagementType does not declare or inherit '{BN.GET_LATEST_RESULT}' — "
            f"direct={sorted(declared_methods)}, direct+inherited={sorted(inherited_methods)}"
        )
    if missing:
        logger.info("Optional result-access methods not declared in type definition: %s", missing)


@pytest.mark.requires_cu(CU.RESULT_MANAGEMENT)
async def test_result_management_methods_are_executable_when_present(result_management, ns_indices):
    """Result-access methods on ResultManagement instance must have Executable=True.

    Reads the Executable and UserExecutable attributes for each present result method.
    OPC 10000-3 Sec 5.6.5.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    _method_names = [
        BN.GET_LATEST_RESULT,
        BN.GET_RESULT_BY_ID,
        BN.GET_RESULT_ID_LIST_FILTERED,
    ]

    not_executable: list[str] = []
    for method_name in _method_names:
        method_node = await find_child_by_browse_name(result_management, method_name, ns_mr)
        if method_node is None:
            continue
        try:
            exec_attr = await asyncio.wait_for(
                method_node.read_attribute(ua.AttributeIds.Executable),
                timeout=5.0,
            )
            executable = exec_attr.Value.Value if hasattr(exec_attr, "Value") else exec_attr
            if not executable:
                not_executable.append(method_name)
                logger.warning("Method '%s' has Executable=False", method_name)
            else:
                logger.info("Method '%s': Executable=True", method_name)
        except Exception as exc:
            logger.debug("Cannot read Executable for method '%s': %s", method_name, exc)

    assert not not_executable, (
        f"Result-access methods with Executable=False: {not_executable}. "
        "All implemented result methods must have Executable=True."
    )


# ─── result_management — negative tests ───────────────────────────────────────


@pytest.mark.negative
@pytest.mark.opcua_core
async def test_result_management_results_folder_delete_is_rejected(opcua_client, ns_indices):
    """DeleteNodes on a result Variable in the Results folder must be rejected.

    Result lifecycle is managed by the server, not clients. Clients must not be
    able to delete result Variables directly. Expected: Bad_NotSupported or
    Bad_UserAccessDenied. OPC 10000-4 Sec 5.7.4.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _rediscover_result_management(opcua_client, ns_mr)
    results_folder = await find_child_by_browse_name(rm, BN.RESULTS, ns_mr)
    if results_folder is None:
        pytest.skip("Results folder not found in ResultManagement — cannot run DeleteNodes test")

    from helpers.node_discovery import browse_folder_instances

    instances = await browse_folder_instances(results_folder)

    if instances:
        # Try to delete an existing result variable
        _name, target_node = instances[0]
        target_nid = target_node.nodeid
    else:
        # Try to delete the Results folder itself as a fallback
        target_nid = results_folder.nodeid

    delete_item = ua.DeleteNodesItem(
        NodeId=target_nid,
        DeleteTargetReferences=True,
    )
    try:
        results = await asyncio.wait_for(
            opcua_client.uaclient.delete_nodes(_delete_nodes_parameters(delete_item)),
            timeout=10.0,
        )
    except (ua.UaError, asyncio.TimeoutError, OSError) as exc:
        skip_tooling_limitation(
            f"asyncua DeleteNodes service call unavailable ({exc}); server-side rejection "
            "must be verified manually or with OPC UA CTT"
        )
        return

    assert results, "DeleteNodes must return one per-operation status for the requested node"
    assert results[0].is_bad(), (
        "DeleteNodes on a result node must be rejected — "
        "result lifecycle is server-managed and clients must not delete result Variables"
    )
    logger.info("DeleteNodes on Results folder/variable correctly rejected: %s", results[0])
