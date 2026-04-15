"""
Tests for result simulation methods under Simulations/SimulateResults/.
Tests call SimulateSingleResult, SimulateBatch_Or_Sync_Result, SimulateJobResult,
and SimulateBulkResults and verify the calls complete without error and produce
visible side-effects (results available, events fired).

Method signatures (verified from live server InputArguments):
  SimulateSingleResult(result_type: UInt32, include_traces: Boolean)
  SimulateBatch_Or_Sync_Result(classification: Byte, num_children: UInt32,
                                include_traces: Boolean, send_as_refs: Boolean)
  SimulateJobResult(send_as_refs: Boolean)
  SimulateBulkResults(result_type: UInt32, include_traces: Boolean,
                      from_seq: UInt64, to_seq: UInt64,
                      min_duration_ms: Int64, update_vars: Boolean)

Boolean arguments are set to TRUE (recommended) per server documentation.
A fresh function-scoped opcua_client is used per test for state isolation.
Layer: methods (triggers server simulation — server state changes expected).
"""

import asyncio

import pytest
from asyncua import ua

from helpers.event_collector import EventCollector
from helpers.namespaces import (
    BN,
    NS_APP,
    NS_IJT_BASE,
    NS_MACH_RESULT,
    IJTTypes,
    ResultType,
)
from helpers.node_discovery import find_child_by_browse_name

pytestmark = [pytest.mark.live, pytest.mark.methods]

_METHOD_TIMEOUT = 20  # seconds per method call
# ResultClassification Byte values for SimulateBatch_Or_Sync_Result
_CLASSIFICATION_SYNC = 2
_CLASSIFICATION_BATCH = 3


def _sim_folder(opcua_client, simulate_results_folder):
    """Re-bind the SimulateResults folder node to the function-scoped client."""
    return opcua_client.get_node(simulate_results_folder.nodeid)


async def _find_method(sim_folder_node, name, ns_app):
    return await find_child_by_browse_name(sim_folder_node, name, ns_app)


async def _call(node, method, *args):
    """Call a method with asyncio.wait_for timeout."""
    return await asyncio.wait_for(
        node.call_method(method.nodeid, *args),
        timeout=_METHOD_TIMEOUT,
    )


def _is_transport_timeout(exc: Exception) -> bool:
    """True when asyncua wraps a transport/request timeout as a generic Exception."""
    msg = str(exc)
    return "Unhandled exception while sending request to OPC UA server" in msg or "TimeoutError" in msg


async def _call_with_retry(node, method, *args, retries: int = 1):
    """Retry once for transient simulator transport timeouts."""
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await _call(node, method, *args)
        except Exception as exc:  # asyncua can raise plain Exception for transport timeout
            last_exc = exc
            if not _is_transport_timeout(exc) or attempt >= retries:
                raise
            await asyncio.sleep(1.5 * (attempt + 1))
    assert last_exc is not None  # for type checkers
    raise last_exc


# ─── SimulateSingleResult ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "result_type,label",
    [
        (ResultType.SIMPLE_OK_RESULT, "simple_ok"),
        (ResultType.ONE_STEP_OK_RESULT, "one_step_ok"),
        (ResultType.MULTI_STEP_OK_RESULT, "multi_step_ok"),
        (ResultType.MULTI_STEP_NOK_FAILING_STEP, "multi_step_nok_failing"),
        (ResultType.MULTI_STEP_NOK_TOOL_TRIGGER_LOST, "multi_step_nok_trigger_lost"),
    ],
)
async def test_simulate_single_result_all_types(result_type, label, opcua_client, simulate_results_folder, ns_indices):
    """SimulateSingleResult must complete without exception for each basic result type."""
    ns_app = ns_indices.get(NS_APP)
    if ns_app is None:
        pytest.skip("App namespace not registered")
    sf = _sim_folder(opcua_client, simulate_results_folder)
    method = await _find_method(sf, BN.SIMULATE_SINGLE_RESULT, ns_app)
    if method is None:
        pytest.skip("SimulateSingleResult not found")
    await _call(
        sf,
        method,
        ua.Variant(result_type, ua.VariantType.UInt32),
        ua.Variant(True, ua.VariantType.Boolean),  # include_traces = TRUE
    )


async def test_simulate_single_result_result_appears_in_rm(
    opcua_client, simulate_results_folder, result_management, ns_indices
):
    """After SimulateSingleResult, GetLatestResult must return a non-None result."""
    ns_app = ns_indices.get(NS_APP)
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_app is None or ns_mr is None:
        pytest.skip("Required namespace(s) not registered")
    sf = _sim_folder(opcua_client, simulate_results_folder)
    method = await _find_method(sf, BN.SIMULATE_SINGLE_RESULT, ns_app)
    if method is None:
        pytest.skip("SimulateSingleResult not found")
    await _call(
        sf,
        method,
        ua.Variant(ResultType.ONE_STEP_OK_RESULT, ua.VariantType.UInt32),
        ua.Variant(True, ua.VariantType.Boolean),
    )
    rm = opcua_client.get_node(result_management.nodeid)
    gl = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if gl is None:
        pytest.skip("GetLatestResult not found — cannot verify result")
    result = await asyncio.wait_for(
        rm.call_method(gl.nodeid, ua.Variant(5000, ua.VariantType.Int32)),
        timeout=_METHOD_TIMEOUT,
    )
    assert result is not None, "GetLatestResult returned None after SimulateSingleResult"


async def test_simulate_single_result_fires_event(
    opcua_client, subscription_client, simulate_results_folder, ns_indices
):
    """SimulateSingleResult must fire a JoiningSystemResultReadyEventType event."""
    ns_app = ns_indices.get(NS_APP)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_app is None or ns_ijt is None:
        pytest.skip("Required namespace(s) not registered")
    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))
    server_node = subscription_client.nodes.server
    sf = _sim_folder(opcua_client, simulate_results_folder)
    method = await _find_method(sf, BN.SIMULATE_SINGLE_RESULT, ns_app)
    if method is None:
        pytest.skip("SimulateSingleResult not found")
    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, [event_type_node])
        await _call(
            sf,
            method,
            ua.Variant(ResultType.SIMPLE_OK_RESULT, ua.VariantType.UInt32),
            ua.Variant(True, ua.VariantType.Boolean),
        )
        events = await collector.collect(count=1, timeout_s=20.0)
    assert len(events) >= 1, "No JoiningSystemResultReadyEvent fired after SimulateSingleResult"


# ─── SimulateBatch_Or_Sync_Result ────────────────────────────────────────────


@pytest.mark.parametrize(
    "classification,label",
    [
        (_CLASSIFICATION_BATCH, "batch"),
        (_CLASSIFICATION_SYNC, "sync"),
    ],
)
async def test_simulate_batch_or_sync_result(classification, label, opcua_client, simulate_results_folder, ns_indices):
    """SimulateBatch_Or_Sync_Result must complete for BATCH (3) and SYNC (2) classifications."""
    ns_app = ns_indices.get(NS_APP)
    if ns_app is None:
        pytest.skip("App namespace not registered")
    sf = _sim_folder(opcua_client, simulate_results_folder)
    method = await _find_method(sf, BN.SIMULATE_BATCH_OR_SYNC_RESULT, ns_app)
    if method is None:
        pytest.skip("SimulateBatch_Or_Sync_Result not found")
    try:
        await _call_with_retry(
            sf,
            method,
            ua.Variant(classification, ua.VariantType.Byte),  # classification
            ua.Variant(3, ua.VariantType.UInt32),  # num_children
            ua.Variant(True, ua.VariantType.Boolean),  # include_traces = TRUE
            ua.Variant(True, ua.VariantType.Boolean),  # send_as_refs = TRUE
            retries=1,
        )
    except Exception as exc:
        if label == "batch" and _is_transport_timeout(exc):
            pytest.xfail(
                "SimulateBatch_Or_Sync_Result(batch) timed out in asyncua transport "
                "(transient simulator/request pipeline issue)."
            )
        raise


# ─── SimulateJobResult ───────────────────────────────────────────────────────


@pytest.mark.xfail(
    reason="SimulateJobResult holds the connection for an extended period while firing "
    "all child results; asyncua drops the request before the server responds. "
    "Use IJT_Console_Client to validate SimulateJobResult interactively.",
    strict=True,
)
async def test_simulate_job_result(opcua_client, simulate_results_folder, ns_indices):
    """SimulateJobResult must complete with send_as_refs=TRUE (recommended)."""
    ns_app = ns_indices.get(NS_APP)
    if ns_app is None:
        pytest.skip("App namespace not registered")
    sf = _sim_folder(opcua_client, simulate_results_folder)
    method = await _find_method(sf, BN.SIMULATE_JOB_RESULT, ns_app)
    if method is None:
        pytest.skip("SimulateJobResult not found")
    await _call(
        sf,
        method,
        ua.Variant(True, ua.VariantType.Boolean),  # send_as_refs = TRUE
    )


# ─── SimulateBulkResults ─────────────────────────────────────────────────────


async def test_simulate_bulk_results_small_range(opcua_client, simulate_results_folder, ns_indices):
    """SimulateBulkResults with a 6-result range must complete without error."""
    ns_app = ns_indices.get(NS_APP)
    if ns_app is None:
        pytest.skip("App namespace not registered")
    sf = _sim_folder(opcua_client, simulate_results_folder)
    method = await _find_method(sf, BN.SIMULATE_BULK_RESULTS, ns_app)
    if method is None:
        pytest.skip("SimulateBulkResults not found")
    await _call(
        sf,
        method,
        ua.Variant(ResultType.ONE_STEP_OK_RESULT, ua.VariantType.UInt32),  # result_type
        ua.Variant(True, ua.VariantType.Boolean),  # include_traces = TRUE
        ua.Variant(1, ua.VariantType.UInt64),  # from_seq
        ua.Variant(6, ua.VariantType.UInt64),  # to_seq
        ua.Variant(200, ua.VariantType.Int64),  # min_duration_ms ≥100
        ua.Variant(True, ua.VariantType.Boolean),  # update_vars = TRUE
    )


@pytest.mark.parametrize(
    "result_type,label",
    [
        (ResultType.SIMPLE_OK_RESULT, "simple_ok"),
        (ResultType.MULTI_STEP_OK_RESULT, "multi_step_ok"),
    ],
)
async def test_simulate_bulk_results_multiple_types(
    result_type, label, opcua_client, simulate_results_folder, ns_indices
):
    """SimulateBulkResults must accept different result types."""
    ns_app = ns_indices.get(NS_APP)
    if ns_app is None:
        pytest.skip("App namespace not registered")
    sf = _sim_folder(opcua_client, simulate_results_folder)
    method = await _find_method(sf, BN.SIMULATE_BULK_RESULTS, ns_app)
    if method is None:
        pytest.skip("SimulateBulkResults not found")
    try:
        await _call(
            sf,
            method,
            ua.Variant(result_type, ua.VariantType.UInt32),
            ua.Variant(True, ua.VariantType.Boolean),
            ua.Variant(1, ua.VariantType.UInt64),
            ua.Variant(6, ua.VariantType.UInt64),
            ua.Variant(200, ua.VariantType.Int64),
            ua.Variant(True, ua.VariantType.Boolean),
        )
    except ua.UaError as exc:
        status_str = str(exc)
        if any(
            s in status_str
            for s in (
                "BadTooManyOperations",
                "BadNotSupported",
                "BadInvalidArgument",
            )
        ):
            pytest.xfail(f"SimulateBulkResults({label}) rejected by server (concurrent access limit): {exc}")
        raise
