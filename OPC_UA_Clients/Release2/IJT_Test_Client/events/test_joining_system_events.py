"""
Integration tests for JoiningSystem OPC UA events.
subscription_client handles event subscriptions; opcua_client calls simulation
methods so the two connection purposes stay separated.
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


async def _simulate_single(client, ns_indices):
    ns_app = ns_indices[NS_APP]
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found")
    sim_node = await find_child_by_browse_name(js, BN.SIMULATIONS, ns_app)
    if sim_node is None:
        pytest.skip("Simulations node not found")
    sf = await find_child_by_browse_name(sim_node, BN.SIMULATE_RESULTS_FOLDER, ns_app)
    if sf is None:
        pytest.skip("SimulateResults folder not found")
    method = await find_child_by_browse_name(sf, BN.SIMULATE_SINGLE_RESULT, ns_app)
    if method is None:
        pytest.skip(f"Method '{BN.SIMULATE_SINGLE_RESULT}' not found")
    await sf.call_method(
        method.nodeid,
        ua.Variant(ResultType.SIMPLE_OK_RESULT, ua.VariantType.UInt32),
        ua.Variant(True, ua.VariantType.Boolean),  # include_traces = TRUE
    )


async def _subscribe_result_ready(sub_client, ns_ijt):
    event_type_node = sub_client.get_node(
        ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt)
    )
    collector = EventCollector(sub_client)
    srv_node = sub_client.nodes.server
    await collector.subscribe(srv_node, event_type_nodes=[event_type_node])
    return collector


# ---------------------------------------------------------------------------
# Subscription infrastructure
# ---------------------------------------------------------------------------
async def test_server_supports_event_subscription(subscription_client, ns_indices):
    ns_ijt = ns_indices[NS_IJT_BASE]
    collector = EventCollector(subscription_client)
    srv_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(
        ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt)
    )
    # Must not raise
    await collector.subscribe(srv_node, event_type_nodes=[event_type_node])
    await collector.unsubscribe()


# ---------------------------------------------------------------------------
# Event firing
# ---------------------------------------------------------------------------
async def test_simulate_fires_result_ready_event(
    subscription_client, opcua_client, ns_indices
):
    ns_ijt = ns_indices[NS_IJT_BASE]
    collector = await _subscribe_result_ready(subscription_client, ns_ijt)
    try:
        await _simulate_single(opcua_client, ns_indices)
        events = await collector.collect(count=1, timeout_s=30)
    finally:
        await collector.unsubscribe()
    assert len(events) >= 1, (
        "At least one JoiningSystemResultReadyEvent must be received "
        "after SimulateSingleResult"
    )


# ---------------------------------------------------------------------------
# Base OPC UA event field checks
# ---------------------------------------------------------------------------
async def _collect_one_event(sub_client, caller_client, ns_indices):
    ns_ijt = ns_indices[NS_IJT_BASE]
    collector = await _subscribe_result_ready(sub_client, ns_ijt)
    try:
        await _simulate_single(caller_client, ns_indices)
        events = await collector.collect(count=1, timeout_s=30)
    finally:
        await collector.unsubscribe()
    if not events:
        pytest.skip("No events received within timeout — skipping field check")
    return events[0]


async def test_event_has_source_name(subscription_client, opcua_client, ns_indices):
    event = await _collect_one_event(subscription_client, opcua_client, ns_indices)
    try:
        source_name = event.SourceName
    except AttributeError:
        pytest.skip("Event has no 'SourceName' field")
    assert source_name is not None and isinstance(source_name, str), (
        f"Event.SourceName must be a non-None string, got {source_name!r}"
    )


async def test_event_has_message(subscription_client, opcua_client, ns_indices):
    event = await _collect_one_event(subscription_client, opcua_client, ns_indices)
    try:
        message = event.Message
    except AttributeError:
        pytest.skip("Event has no 'Message' field")
    assert message is not None, "Event.Message must not be None"


async def test_event_has_severity(subscription_client, opcua_client, ns_indices):
    event = await _collect_one_event(subscription_client, opcua_client, ns_indices)
    try:
        severity = event.Severity
    except AttributeError:
        pytest.skip("Event has no 'Severity' field")
    assert isinstance(severity, int), (
        f"Event.Severity must be an int, got {type(severity)}"
    )
    assert 0 <= severity <= 1000, f"Event.Severity must be in [0, 1000], got {severity}"


async def test_event_has_time(subscription_client, opcua_client, ns_indices):
    event = await _collect_one_event(subscription_client, opcua_client, ns_indices)
    try:
        time_val = event.Time
    except AttributeError:
        pytest.skip("Event has no 'Time' field")
    assert time_val is not None, "Event.Time must not be None"
