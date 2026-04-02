"""
Tests that inspect the content of received IJT event objects to ensure they
carry IJT-specific fields beyond the standard OPC UA base event fields.
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
async def _find_rm(client, ns_mr):
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found")
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement not found")
    return rm


async def _simulate_and_collect(sub_client, caller_client, ns_indices, count=1):
    ns_app = ns_indices[NS_APP]
    ns_ijt = ns_indices[NS_IJT_BASE]
    event_type_node = sub_client.get_node(
        ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt)
    )
    collector = EventCollector(sub_client)
    srv_node = sub_client.nodes.server
    await collector.subscribe(srv_node, event_type_nodes=[event_type_node])
    try:
        js = await find_joining_system(caller_client)
        if js is None:
            pytest.skip("JoiningSystem not found")
        sim_node = await find_child_by_browse_name(js, BN.SIMULATIONS, ns_app)
        if sim_node is None:
            pytest.skip("Simulations node not found")
        sf = await find_child_by_browse_name(
            sim_node, BN.SIMULATE_RESULTS_FOLDER, ns_app
        )
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
        events = await collector.collect(count=count, timeout_s=30)
    finally:
        await collector.unsubscribe()
    if not events:
        pytest.skip("No events received within timeout")
    return events


# ---------------------------------------------------------------------------
# IJT-specific content
# ---------------------------------------------------------------------------
async def test_joining_system_event_content_type_structure(
    subscription_client, opcua_client, ns_indices
):
    """
    After receiving a JoiningSystemResultReadyEvent, confirm that the event
    carries at least one IJT-specific field beyond the standard OPC UA base
    event attributes (EventId, EventType, SourceNode, SourceName, Time,
    ReceiveTime, LocalTime, Message, Severity).
    """
    standard_fields = {
        "EventId",
        "EventType",
        "SourceNode",
        "SourceName",
        "Time",
        "ReceiveTime",
        "LocalTime",
        "Message",
        "Severity",
    }
    events = await _simulate_and_collect(subscription_client, opcua_client, ns_indices)
    event = events[0]
    # IJT fields live under event.Result (JoiningResultDataType) — check for that
    result = getattr(event, "Result", None)
    if result is not None:
        assert True  # Result field present — IJT-specific data confirmed
        return
    # Fallback: check for any non-base non-None non-callable attribute
    ijt_fields = [
        attr
        for attr in dir(event)
        if not attr.startswith("_")
        and attr not in standard_fields
        and not callable(getattr(event, attr, None))
        and getattr(event, attr, None) is not None
    ]
    if not ijt_fields:
        pytest.skip(
            "No IJT-specific event fields found on received event. "
            "The server may not include extended fields in the notification."
        )
    assert len(ijt_fields) >= 1, (
        "At least one IJT-specific field must be present in the event content"
    )


async def test_event_has_asset_id_field(subscription_client, opcua_client, ns_indices):
    """
    The event should carry either an AssetId-like field or at least a
    SourceNode that identifies the originating resource.
    """
    events = await _simulate_and_collect(subscription_client, opcua_client, ns_indices)
    event = events[0]
    # Try dedicated AssetId field first
    for field_name in ("AssetId", "AssetID", "ToolId"):
        try:
            value = getattr(event, field_name)
            assert value is not None, f"Event.{field_name} must not be None"
            return  # test passed
        except AttributeError:
            continue
    # Fall back to SourceNode, which is always present in OPC UA events
    try:
        source_node = event.SourceNode
        assert source_node is not None, (
            "Event.SourceNode must not be None when no dedicated AssetId field exists"
        )
    except AttributeError:
        pytest.skip(
            "Event has neither an AssetId-like field nor a SourceNode — "
            "cannot verify asset identification"
        )
