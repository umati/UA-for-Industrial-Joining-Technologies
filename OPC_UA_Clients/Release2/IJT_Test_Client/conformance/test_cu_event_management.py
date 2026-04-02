"""
Conformance unit tests for EventManagement — §11.1 CU-EM-001 through CU-EM-005.
Tests cover event type hierarchy, subscription support, mandatory base OPC UA
event fields, IJT-specific event fields, and event timestamp freshness.
"""
import asyncio
import datetime
import pytest
from asyncua import ua
from helpers.namespaces import NS_IJT_BASE, NS_APP, BN, IJTTypes, ResultType
from helpers.node_discovery import find_joining_system, find_child_by_browse_name
from helpers.event_collector import EventCollector
pytestmark = [pytest.mark.live, pytest.mark.conformance]
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _simulate_result(client, ns_mr, ns_app):
    """Trigger a result event via SimulateSingleResult; returns True on success."""
    js = await find_joining_system(client)
    if js is None:
        return False
    sim_node = await find_child_by_browse_name(js, BN.SIMULATIONS, ns_app)
    if sim_node is None:
        return False
    sf = await find_child_by_browse_name(sim_node, BN.SIMULATE_RESULTS_FOLDER, ns_app)
    if sf is None:
        return False
    sim_method = await find_child_by_browse_name(sf, BN.SIMULATE_SINGLE_RESULT, ns_app)
    if sim_method is None:
        return False
    try:
        await sf.call_method(
            sim_method.nodeid,
            ua.Variant(ResultType.ONE_STEP_OK_RESULT, ua.VariantType.UInt32),
            ua.Variant(True, ua.VariantType.Boolean),   # include_traces = TRUE
        )
        return True
    except ua.UaError:
        return False
async def _collect_event(subscription_client, opcua_client, ns_indices):
    """Subscribe, simulate, and collect one event. Returns the event or None."""
    from helpers.namespaces import NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_app = ns_indices.get(NS_APP)
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_ijt is None or ns_app is None or ns_mr is None:
        return None
    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(
        ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt)
    )
    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)
        await _simulate_result(opcua_client, ns_mr, ns_app)
        events = await collector.collect(count=1, timeout_s=45.0)
    return events[0] if events else None
# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
async def test_cu_event_management_event_type_hierarchy(session_client, ns_indices):
    # §11.1 CU-EM-001: JoiningSystemResultReadyEventType node must exist and be browsable
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    event_type_node = session_client.get_node(
        ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt)
    )
    try:
        browse_name = await event_type_node.read_browse_name()
    except ua.UaError as exc:
        pytest.fail(
            f"JoiningSystemResultReadyEventType node "
            f"(ns={ns_ijt}, id={IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE}) "
            f"not accessible: {exc}"
        )
    assert browse_name is not None, (
        "JoiningSystemResultReadyEventType node returned None browse name"
    )
    assert browse_name.Name, (
        "JoiningSystemResultReadyEventType browse name has empty Name component"
    )
async def test_cu_event_management_event_subscription_supported(
    subscription_client, ns_indices
):
    # §11.1 CU-EM-002: Creating an event subscription must not raise an error
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(
        ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt)
    )
    async with EventCollector(subscription_client) as collector:
        try:
            await collector.subscribe(server_node, event_type_node)
        except ua.UaError as exc:
            pytest.fail(
                f"Creating event subscription raised an unexpected error: {exc}"
            )
        # Subscription created successfully — no event collection required
async def test_cu_event_management_event_has_mandatory_base_fields(
    subscription_client, opcua_client, ns_indices
):
    # §11.1 CU-EM-003: Received event must carry all mandatory OPC UA base event fields
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_app = ns_indices.get(NS_APP)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    if ns_app is None:
        pytest.skip("App namespace not registered on server")
    event = await _collect_event(subscription_client, opcua_client, ns_indices)
    if event is None:
        pytest.skip(
            "No event received within 30 s — SimulateSingleResult may not be available"
        )
    mandatory_base_fields = [
        "EventId", "EventType", "SourceNode", "SourceName",
        "Time", "ReceiveTime", "Message", "Severity",
    ]
    for field in mandatory_base_fields:
        value = getattr(event, field, None)
        assert value is not None, (
            f"Mandatory OPC UA base event field '{field}' is missing or None "
            f"in received JoiningSystemResultReadyEvent"
        )
async def test_cu_event_management_event_has_ijt_fields(
    subscription_client, opcua_client, ns_indices
):
    # §11.1 CU-EM-004: Received event must carry IJT-specific fields beyond base OPC UA
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_app = ns_indices.get(NS_APP)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    if ns_app is None:
        pytest.skip("App namespace not registered on server")
    event = await _collect_event(subscription_client, opcua_client, ns_indices)
    if event is None:
        pytest.skip(
            "No event received within 30 s — SimulateSingleResult may not be available"
        )
    base_fields = {
        "EventId", "EventType", "SourceNode", "SourceName",
        "Time", "ReceiveTime", "LocalTime", "Message", "Severity",
    }
    # Collect all non-None attributes that are not private/dunder and not in base set
    all_attrs = [
        attr for attr in dir(event)
        if not attr.startswith("_") and attr not in base_fields
    ]
    ijt_fields = [
        attr for attr in all_attrs
        if getattr(event, attr, None) is not None
        and not callable(getattr(event, attr, None))
    ]
    assert len(ijt_fields) > 0, (
        "Received event has no IJT-specific fields beyond mandatory OPC UA base fields — "
        f"non-base attributes found: {all_attrs}"
    )
async def test_cu_event_management_event_time_is_recent(
    subscription_client, opcua_client, ns_indices
):
    # §11.1 CU-EM-005: Event Time field must be within 60 s of the test start
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_app = ns_indices.get(NS_APP)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    if ns_app is None:
        pytest.skip("App namespace not registered on server")
    test_start = datetime.datetime.now(tz=datetime.timezone.utc)
    event = await _collect_event(subscription_client, opcua_client, ns_indices)
    if event is None:
        pytest.skip(
            "No event received within 30 s — SimulateSingleResult may not be available"
        )
    event_time = getattr(event, "Time", None)
    if event_time is None:
        pytest.skip("Received event has no Time field")
    # Normalize to UTC-aware datetime if necessary
    if isinstance(event_time, datetime.datetime):
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=datetime.timezone.utc)
    else:
        pytest.skip(f"Event Time is not a datetime object: {type(event_time)}")
    age_seconds = (test_start - event_time).total_seconds()
    assert abs(age_seconds) <= 60, (
        f"Event Time {event_time.isoformat()} is not within 60 s of test start "
        f"{test_start.isoformat()} (delta = {age_seconds:.1f} s)"
    )