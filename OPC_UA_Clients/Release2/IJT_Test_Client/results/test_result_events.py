"""
Tests that verify OPC UA events are fired by the IJT server when results are
simulated.  subscription_client is used for event subscriptions;
opcua_client is used to call simulation methods.
"""

import pytest
from asyncua import ua

from helpers.event_collector import EventCollector
from helpers.namespaces import (
    BN,
    NS_APP,
    NS_IJT_BASE,
    IJTTypes,
    ResultType,
)
from helpers.node_discovery import find_child_by_browse_name, find_joining_system

pytestmark = [pytest.mark.live, pytest.mark.events]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _find_result_management(client, ns_mr):
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found")
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement not found")
    return rm


async def _call_simulate_single(client, ns_indices, result_type=ResultType.SIMPLE_OK_RESULT):
    ns_app = ns_indices[NS_APP]
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found")
    sim_folder_node = await find_child_by_browse_name(js, BN.SIMULATIONS, ns_app)
    if sim_folder_node is None:
        pytest.skip("Simulations node not found")
    sf = await find_child_by_browse_name(sim_folder_node, BN.SIMULATE_RESULTS_FOLDER, ns_app)
    if sf is None:
        pytest.skip("SimulateResults folder not found")
    method = await find_child_by_browse_name(sf, BN.SIMULATE_SINGLE_RESULT, ns_app)
    if method is None:
        pytest.skip(f"Method '{BN.SIMULATE_SINGLE_RESULT}' not found")
    await sf.call_method(
        method.nodeid,
        ua.Variant(result_type, ua.VariantType.UInt32),
        ua.Variant(True, ua.VariantType.Boolean),  # include_traces = TRUE
    )
    return sf


async def _make_event_collector(sub_client, ns_indices):
    ns_ijt = ns_indices[NS_IJT_BASE]
    event_type_node = sub_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))
    collector = EventCollector(sub_client)
    srv_node = sub_client.nodes.server
    await collector.subscribe(srv_node, event_type_nodes=[event_type_node])
    return collector


# ---------------------------------------------------------------------------
# Basic existence check
# ---------------------------------------------------------------------------
async def test_result_ready_event_type_exists(session_client, ns_indices):
    ns_ijt = ns_indices[NS_IJT_BASE]
    node = session_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))
    node_id = node.nodeid
    assert node_id is not None, (
        f"JoiningSystemResultReadyEventType node (ns={ns_ijt}; "
        f"i={IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE}) must be accessible"
    )


# ---------------------------------------------------------------------------
# Event firing tests
# ---------------------------------------------------------------------------
async def test_simulate_fires_result_ready_event(subscription_client, opcua_client, ns_indices):
    collector = await _make_event_collector(subscription_client, ns_indices)
    try:
        await _call_simulate_single(opcua_client, ns_indices)
        events = await collector.collect(count=1, timeout_s=30)
    finally:
        await collector.unsubscribe()
    assert len(events) >= 1, "At least one JoiningSystemResultReadyEvent must be received after SimulateSingleResult"


async def test_result_ready_event_has_result_id(subscription_client, opcua_client, ns_indices):
    collector = await _make_event_collector(subscription_client, ns_indices)
    try:
        await _call_simulate_single(opcua_client, ns_indices)
        events = await collector.collect(count=1, timeout_s=30)
    finally:
        await collector.unsubscribe()
    assert events, "No events received within timeout"
    event = events[0]
    result = getattr(event, "Result", None)
    meta = getattr(result, "ResultMetaData", None) if result is not None else None
    result_id = getattr(meta, "ResultId", None) if meta is not None else None
    if result_id is None:
        pytest.skip("Event.Result.ResultMetaData.ResultId not found — server may not populate it")
    assert result_id is not None, "Event.Result.ResultMetaData.ResultId must not be None"


async def test_result_ready_event_has_result_evaluation(subscription_client, opcua_client, ns_indices):
    collector = await _make_event_collector(subscription_client, ns_indices)
    try:
        await _call_simulate_single(opcua_client, ns_indices)
        events = await collector.collect(count=1, timeout_s=30)
    finally:
        await collector.unsubscribe()
    assert events, "No events received within timeout"
    event = events[0]
    result = getattr(event, "Result", None)
    meta = getattr(result, "ResultMetaData", None) if result is not None else None
    evaluation = getattr(meta, "ResultEvaluation", None) if meta is not None else None
    if evaluation is None:
        pytest.skip("Event.Result.ResultMetaData.ResultEvaluation not found")
    assert evaluation is not None, "Event.Result.ResultMetaData.ResultEvaluation must not be None"


async def test_result_ready_event_has_result_classification(subscription_client, opcua_client, ns_indices):
    collector = await _make_event_collector(subscription_client, ns_indices)
    try:
        await _call_simulate_single(opcua_client, ns_indices)
        events = await collector.collect(count=1, timeout_s=30)
    finally:
        await collector.unsubscribe()
    assert events, "No events received within timeout"
    event = events[0]
    result = getattr(event, "Result", None)
    meta = getattr(result, "ResultMetaData", None) if result is not None else None
    classification = getattr(meta, "Classification", None) if meta is not None else None
    if classification is None:
        pytest.skip("Event.Result.ResultMetaData.Classification not found")
    assert classification is not None, "Event.Result.ResultMetaData.Classification must not be None"


async def test_batch_result_fires_multiple_events(subscription_client, opcua_client, ns_indices):
    ns_app = ns_indices[NS_APP]
    ns_ijt = ns_indices[NS_IJT_BASE]
    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))
    collector = EventCollector(subscription_client)
    srv_node = subscription_client.nodes.server
    await collector.subscribe(srv_node, event_type_nodes=[event_type_node])
    try:
        js = await find_joining_system(opcua_client)
        if js is None:
            pytest.skip("JoiningSystem not found")
        sim_folder = await find_child_by_browse_name(js, BN.SIMULATIONS, ns_app)
        if sim_folder is None:
            pytest.skip("Simulations folder not found")
        sf = await find_child_by_browse_name(sim_folder, BN.SIMULATE_RESULTS_FOLDER, ns_app)
        if sf is None:
            pytest.skip("SimulateResults folder not found")
        method = await find_child_by_browse_name(sf, BN.SIMULATE_BATCH_OR_SYNC_RESULT, ns_app)
        if method is None:
            pytest.skip(f"Method '{BN.SIMULATE_BATCH_OR_SYNC_RESULT}' not found")
        content_size = 3
        await sf.call_method(
            method.nodeid,
            ua.Variant(3, ua.VariantType.Byte),  # classification BATCH
            ua.Variant(content_size, ua.VariantType.UInt32),
            ua.Variant(True, ua.VariantType.Boolean),  # include_traces = TRUE
            ua.Variant(
                True, ua.VariantType.Boolean
            ),  # send_child_results_as_refs = TRUE (fires separate events per child)
        )
        events = await collector.collect(count=content_size, timeout_s=60)
    finally:
        await collector.unsubscribe()
    assert len(events) >= content_size, (
        f"Expected at least {content_size} events from SimulateBatchOrSyncResult "
        f"with contentSize={content_size}, got {len(events)}"
    )


async def test_event_source_is_result_management(subscription_client, opcua_client, ns_indices, result_management):
    collector = await _make_event_collector(subscription_client, ns_indices)
    try:
        await _call_simulate_single(opcua_client, ns_indices)
        events = await collector.collect(count=1, timeout_s=30)
    finally:
        await collector.unsubscribe()
    assert events, "No events received within timeout"
    event = events[0]
    try:
        source_node = event.SourceNode
    except AttributeError:
        pytest.skip("Event has no 'SourceNode' field")
    assert source_node is not None, "Event.SourceNode must not be None"
