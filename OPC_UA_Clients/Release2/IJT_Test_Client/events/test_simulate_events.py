"""
Tests for event simulation via the Simulations/SimulateEventsAndConditions/ methods.
Covers SimulateEvents (fire one event of given type) and SimulateBulkEvents
(fire N events of given type). Tests span representative event categories and
verify: no-exception (method accepted), event notification received via subscription,
and bulk count produces more events than single-fire.

Method signatures (from live server InputArguments):
  SimulateEvents(event_type: UInt32)              — fires 1 event
  SimulateBulkEvents(event_type: UInt32, count: UInt32)  — fires N events

Event types 1-60: see SimulateEventType class in helpers/namespaces.py
A fresh function-scoped opcua_client / subscription_client is used per test.
Layer: methods + events (triggers server state changes).
"""

import asyncio

import pytest
from asyncua import ua

from helpers.event_collector import EventCollector
from helpers.namespaces import BN, NS_APP, NS_IJT_BASE, IJTTypes, SimulateEventType
from helpers.node_discovery import find_child_by_browse_name

pytestmark = [pytest.mark.live, pytest.mark.events]

_METHOD_TIMEOUT = 15  # seconds


def _events_folder(opcua_client, simulate_events_folder):
    """Re-bind simulate_events_folder to the function-scoped client."""
    return opcua_client.get_node(simulate_events_folder.nodeid)


async def _find_method(folder, name, ns_app):
    return await find_child_by_browse_name(folder, name, ns_app)


async def _call(node, method, *args):
    return await asyncio.wait_for(
        node.call_method(method.nodeid, *args),
        timeout=_METHOD_TIMEOUT,
    )


# ─── SimulateEvents — no-exception (representative event types) ──────────────


@pytest.mark.parametrize("event_type,label", SimulateEventType.REPRESENTATIVE)
async def test_simulate_event_representative_types(
    event_type, label, opcua_client, simulate_events_folder, ns_indices
):
    """SimulateEvents must accept representative event types from each category."""
    ns_app = ns_indices.get(NS_APP)
    if ns_app is None:
        pytest.skip("App namespace not registered")
    ef = _events_folder(opcua_client, simulate_events_folder)
    method = await _find_method(ef, BN.SIMULATE_EVENTS, ns_app)
    if method is None:
        pytest.skip("SimulateEvents method not found")
    await _call(ef, method, ua.Variant(event_type, ua.VariantType.UInt32))


# ─── SimulateBulkEvents — no-exception ───────────────────────────────────────


@pytest.mark.parametrize(
    "event_type,count,label",
    [
        (SimulateEventType.TOOL_CONNECTED, 3, "tool_connected_x3"),
        (SimulateEventType.TOOL_STARTED, 5, "tool_started_x5"),
        (SimulateEventType.PROGRAM_SELECTED, 3, "program_selected_x3"),
    ],
)
async def test_simulate_bulk_events_no_exception(
    event_type, count, label, opcua_client, simulate_events_folder, ns_indices
):
    """SimulateBulkEvents must complete without exception for various types and counts."""
    ns_app = ns_indices.get(NS_APP)
    if ns_app is None:
        pytest.skip("App namespace not registered")
    ef = _events_folder(opcua_client, simulate_events_folder)
    method = await _find_method(ef, BN.SIMULATE_BULK_EVENTS, ns_app)
    if method is None:
        pytest.skip("SimulateBulkEvents method not found")
    await _call(
        ef,
        method,
        ua.Variant(event_type, ua.VariantType.UInt32),
        ua.Variant(count, ua.VariantType.UInt32),
    )


# ─── SimulateEvents — subscription-based verification ───────────────────────


async def test_simulate_event_fires_notification(
    opcua_client, subscription_client, simulate_events_folder, ns_indices
):
    """SimulateEvents must result in at least one JoiningSystemEventType notification."""
    ns_app = ns_indices.get(NS_APP)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_app is None or ns_ijt is None:
        pytest.skip("Required namespace(s) not registered")
    event_type_node = subscription_client.get_node(
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt)
    )
    server_node = subscription_client.nodes.server
    ef = _events_folder(opcua_client, simulate_events_folder)
    method = await _find_method(ef, BN.SIMULATE_EVENTS, ns_app)
    if method is None:
        pytest.skip("SimulateEvents method not found")
    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, [event_type_node])
        await _call(
            ef,
            method,
            ua.Variant(SimulateEventType.TOOL_CONNECTED, ua.VariantType.UInt32),
        )
        events = await collector.collect(count=1, timeout_s=20.0)
    assert len(events) >= 1, (
        "No JoiningSystemEventType notification received after SimulateEvents(TOOL_CONNECTED)"
    )


# ─── SimulateBulkEvents — verify count matches expected ─────────────────────


@pytest.mark.parametrize("count", [3, 5])
async def test_simulate_bulk_events_fires_expected_count(
    count, opcua_client, subscription_client, simulate_events_folder, ns_indices
):
    """SimulateBulkEvents(type, N) must produce at least N events on subscription."""
    ns_app = ns_indices.get(NS_APP)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_app is None or ns_ijt is None:
        pytest.skip("Required namespace(s) not registered")
    event_type_node = subscription_client.get_node(
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt)
    )
    server_node = subscription_client.nodes.server
    ef = _events_folder(opcua_client, simulate_events_folder)
    method = await _find_method(ef, BN.SIMULATE_BULK_EVENTS, ns_app)
    if method is None:
        pytest.skip("SimulateBulkEvents method not found")
    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, [event_type_node])
        await _call(
            ef,
            method,
            ua.Variant(SimulateEventType.TOOL_STARTED, ua.VariantType.UInt32),
            ua.Variant(count, ua.VariantType.UInt32),
        )
        events = await collector.collect(count=count, timeout_s=30.0)
    assert len(events) >= count, (
        f"SimulateBulkEvents(TOOL_STARTED, {count}) produced only "
        f"{len(events)} events, expected >= {count}"
    )


# ─── Comparison: bulk > single ───────────────────────────────────────────────


async def test_bulk_events_exceeds_single_event_count(
    opcua_client, subscription_client, simulate_events_folder, ns_indices
):
    """SimulateBulkEvents(count=5) must produce more events than SimulateEvents(count=1)."""
    ns_app = ns_indices.get(NS_APP)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_app is None or ns_ijt is None:
        pytest.skip("Required namespace(s) not registered")
    event_type_node = subscription_client.get_node(
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt)
    )
    server_node = subscription_client.nodes.server
    ef = _events_folder(opcua_client, simulate_events_folder)
    single_method = await _find_method(ef, BN.SIMULATE_EVENTS, ns_app)
    bulk_method = await _find_method(ef, BN.SIMULATE_BULK_EVENTS, ns_app)
    if single_method is None or bulk_method is None:
        pytest.skip("Simulate methods not found")

    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, [event_type_node])
        await _call(
            ef,
            single_method,
            ua.Variant(SimulateEventType.TOOL_STARTED, ua.VariantType.UInt32),
        )
        single_events = await collector.collect(count=10, timeout_s=10.0)

    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, [event_type_node])
        await _call(
            ef,
            bulk_method,
            ua.Variant(SimulateEventType.TOOL_STARTED, ua.VariantType.UInt32),
            ua.Variant(5, ua.VariantType.UInt32),
        )
        bulk_events = await collector.collect(count=10, timeout_s=20.0)

    # If single_events is already at the collection ceiling (10), we can't distinguish
    # actual counts — skip to avoid flaky failures caused by leftover events.
    if len(single_events) >= 10:
        pytest.skip(
            f"Single-event collection hit the ceiling ({len(single_events)}) — "
            "cannot reliably compare single vs bulk in this environment"
        )
    assert len(bulk_events) > len(single_events), (
        f"Bulk (count=5) produced {len(bulk_events)} events, "
        f"single produced {len(single_events)} — bulk should exceed single"
    )
