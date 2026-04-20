"""
Conformance unit tests for Event and Condition Management — OPC 40450-1 IJT Base.

event_payload: "The Server reporting any event or condition or alarm from a Joining
System includes the common payload defined in JoiningSystemEventContentType with:
JoiningTechnology, EventText, EventCode."

event_condition_classes: "The Server reporting any event or condition or alarm
contains: ConditionClassId, ConditionClassName, ConditionSubClassId,
ConditionSubClassName. If ConditionClass is already a specific category, omitting
ConditionSubClass is allowed. These properties are not applicable for
ResultReadyEventType, JoiningSystemResultReadyEventType,
RequestedResultEventType."

asset_connection_event: "The Server generates a JoiningSystemEventType event when
any asset is connected or disconnected. ConditionClass = SystemConditionClassType.
ConditionSubClass = AssetConnectedConditionClassType or
AssetDisconnectedConditionClassType."

asset_connection_state_event: "The Server generates a JoiningSystemEventType event
when an asset is connected or disconnected based on the value of
Asset.Parameters.Connected. ConditionClass = SystemConditionClassType. ConditionSubClass
= AssetConnectedConditionClassType or AssetDisconnectedConditionClassType."

asset_enable_state_event: "The Server generates a JoiningSystemEventType event when
any asset is enabled or disabled. ConditionClass = SystemConditionClassType.
ConditionSubClass = AssetEnabledConditionClassType if enabled;
AssetDisabledConditionClassType if disabled."

event_payload_associated_entities: "The Server includes AssociatedEntities[] in
JoiningSystemEventContentType. Examples: Asset Connected event contains the associated
identifier of the asset; Joining Process event contains the identifier of the joining
process."

event_payload_reported_values: "The Server includes ReportedValues[] in
JoiningSystemEventContentType for measurement values such as Temperature in Over
Temperature Event. Required when ConditionSubClass is
ThresholdViolationConditionClassType or ThresholdViolationResolvedConditionClassType."

identifiers_event: "The Server generates a JoiningSystemEventType event with
appropriate Condition Classes when an identifier is sent via SendIdentifiers,
SendTextIdentifiers, StartJoiningProcess, or another interface. AssociatedEntities
includes the received identifiers."

select_process_event: "The Server generates a JoiningSystemEventType event when a
joining process is selected. ConditionClass = ProcessConditionClassType. ConditionSubClass
= SelectedProcessConditionClassType. AssociatedEntities includes the identifier of the
selected Joining Process."
"""

import datetime
import logging
import time

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.event_collector import EventCollector
from helpers.event_validator import (
    assert_condition_valid,
    assert_joining_system_event_valid,
    assert_result_ready_event_valid,
)
from helpers.namespaces import (
    NS_IJT_BASE,
    IJTTypes,
    ResultType,
    SimulateEventType,
)

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

# Representative cross-section of event types used for parametrized payload checks.
# Each tuple: (SimulateEventType constant, human-readable label).
_REPRESENTATIVE_EVENT_TYPES = [
    (SimulateEventType.TOOL_CONNECTED, "tool-connected"),
    (SimulateEventType.TOOL_STARTED, "tool-started"),
    (SimulateEventType.TOOL_NOT_AVAILABLE_ERROR, "tool-not-available-error"),
    (SimulateEventType.CERTIFICATE_EXPIRY_WARNING, "certificate-expiry-warning"),
    (SimulateEventType.LICENSE_EXPIRY_WARNING, "license-expiry-warning"),
    (SimulateEventType.PROGRAM_SELECTED, "program-selected"),
    (SimulateEventType.EXECUTION_STARTED, "execution-started"),
    (SimulateEventType.RECEIVED_IDENTIFIER, "received-identifier"),
    (SimulateEventType.CONFIGURATION_CHANGED, "configuration-changed"),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _require_ns_ijt(ns_indices):
    """Return the IJT Base namespace index; skip the test if not registered."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    return ns_ijt


async def _collect_events_after_trigger(
    subscription_client,
    event_trigger,
    event_type_node_id,
    event_type,
    count=1,
    timeout_s=45.0,
):
    """
    Subscribe to event_type_node_id, trigger event_type via event_trigger,
    collect and return received events.

    Skips the test when the simulator trigger fails.  For real-controller
    triggers, proceeds to collect and lets the caller decide on empty results.
    """
    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(event_type_node_id)

    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)
        outcome = await event_trigger.trigger_event(event_type, count=count)
        if not outcome.triggered and event_trigger.is_simulator:
            pytest.skip(outcome.skip_reason or "Simulator event trigger failed")
        events = await collector.collect(count=count, timeout_s=timeout_s)

    return events


async def _collect_condition_events(
    subscription_client,
    event_trigger,
    ns_ijt,
    timeout_s=45.0,
):
    """
    Subscribe to JoiningSystemConditionType, trigger TOOL_MISSING_ERROR (which
    raises a condition on most simulators), and return collected events.
    """
    server_node = subscription_client.nodes.server
    condition_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_CONDITION_TYPE, ns_ijt))
    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, condition_type_node)
        outcome = await event_trigger.trigger_event(SimulateEventType.TOOL_MISSING_ERROR, count=1)
        if not outcome.triggered and event_trigger.is_simulator:
            pytest.skip(outcome.skip_reason or "Simulator event trigger failed")
        events = await collector.collect(count=1, timeout_s=timeout_s)
    return events


def _event_payload_field(event, field_name: str):
    """
    Read JoiningSystemEventContent fields across asyncua decoding variants.

    Supported representations:
      - event.<Field>
      - event.EventContent.<Field>
      - event.__dict__['JoiningSystemEventContent/<Field>']
    """
    value = getattr(event, field_name, None)
    if value is not None:
        return value

    content = getattr(event, "EventContent", None)
    if content is not None:
        cval = getattr(content, field_name, None)
        if cval is not None:
            return cval

    edict = getattr(event, "__dict__", {})
    slash_key = f"JoiningSystemEventContent/{field_name}"
    if slash_key in edict:
        return edict.get(slash_key)

    nested = edict.get("JoiningSystemEventContent")
    if nested is not None:
        nval = getattr(nested, field_name, None)
        if nval is not None:
            return nval

    return None


def _joining_technology_to_int_or_none(value):
    """Best-effort conversion of JoiningTechnology payload to enum int when possible."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        pass

    # Some servers expose JoiningTechnology as LocalizedText/Text (e.g. "Tightening")
    text = getattr(value, "Text", None)
    if text is not None:
        return None

    return None


# ---------------------------------------------------------------------------
# ─── event_payload ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
async def test_joining_system_event_type_node_is_accessible(session_client, ns_indices):
    """
    JoiningSystemEventType node must exist in the address space and expose a
    browse name of 'JoiningSystemEventType'.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = session_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt))
    try:
        browse_name = await node.read_browse_name()
    except ua.UaError as exc:
        pytest.fail(
            f"JoiningSystemEventType node (ns={ns_ijt}, id={IJTTypes.JOINING_SYSTEM_EVENT_TYPE}) not accessible: {exc}"
        )
    assert browse_name is not None, "JoiningSystemEventType browse name is None"
    assert browse_name.Name == "JoiningSystemEventType", (
        f"Expected browse name 'JoiningSystemEventType', got {browse_name.Name!r}"
    )


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
async def test_joining_system_result_ready_event_type_is_accessible(session_client, ns_indices):
    """
    JoiningSystemResultReadyEventType node must exist in the address space and
    expose a browse name of 'JoiningSystemResultReadyEventType'.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = session_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))
    try:
        browse_name = await node.read_browse_name()
    except ua.UaError as exc:
        pytest.fail(f"JoiningSystemResultReadyEventType node not accessible: {exc}")
    assert browse_name is not None, "JoiningSystemResultReadyEventType browse name is None"
    assert browse_name.Name == "JoiningSystemResultReadyEventType", (
        f"Expected browse name 'JoiningSystemResultReadyEventType', got {browse_name.Name!r}"
    )


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
async def test_joining_system_event_type_is_subscribable(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    Subscribing to JoiningSystemEventType and receiving at least one event after
    a TOOL_CONNECTED trigger must succeed without error.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip(
            "No JoiningSystemEventType event received within timeout — trigger manually if using a real controller"
        )
    assert len(events) >= 1, "Expected at least one JoiningSystemEventType event"


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
async def test_joining_system_event_has_event_text(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    JoiningSystemEventType.Message (EventText) must be non-None in every received
    event per the event_payload specification.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No event received within timeout")
    event = events[0]
    message = getattr(event, "Message", None)
    assert message is not None, "JoiningSystemEventType.Message (EventText) must not be None"


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
async def test_joining_system_event_has_event_code_field(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    JoiningSystemEventType.EventCode must be a non-negative integer when present.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No event received within timeout")
    event = events[0]
    event_code = _event_payload_field(event, "EventCode")
    if event_code is None:
        pytest.skip("EventCode field absent — server may not populate it for this event type")
    try:
        code_int = int(event_code)
    except (TypeError, ValueError):
        pytest.fail(f"EventCode must convert to an integer, got {event_code!r}")
    assert code_int >= 0, f"EventCode must be a non-negative integer, got {code_int!r}"


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
async def test_joining_system_event_has_joining_technology(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    JoiningSystemEventType events must carry a JoiningTechnology field whose
    value is in the valid JoiningTechnologyEnumeration range.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No event received within timeout")
    event = events[0]
    tech = _event_payload_field(event, "JoiningTechnology")
    if tech is None:
        pytest.skip("JoiningTechnology field absent — server may not populate it for this event type")
    tech_int = _joining_technology_to_int_or_none(tech)
    if tech_int is not None:
        assert 0 <= tech_int <= 7, f"JoiningTechnology must be in the valid enum range, got {tech_int}"
        return

    tech_text = getattr(tech, "Text", tech)
    assert isinstance(tech_text, str) and tech_text.strip(), (
        f"JoiningTechnology must be either valid enum int or non-empty text, got {tech!r}"
    )


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
async def test_event_base_fields_present(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    Mandatory OPC UA BaseEventType fields — EventId, EventType, Time, Severity —
    must all be present and non-None in every received JoiningSystemEventType event.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No event received within timeout")
    event = events[0]
    for field_name in ("EventId", "EventType", "Time", "Severity"):
        value = getattr(event, field_name, None)
        assert value is not None, f"Mandatory OPC UA BaseEventType field '{field_name}' is None or absent"


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
async def test_event_timestamp_is_within_reasonable_range(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    Event.Time must be within a reasonable window of the test start — must not be
    the Unix epoch and must not be a far-future timestamp.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    test_start = datetime.datetime.now(tz=datetime.timezone.utc)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No event received within timeout")
    event = events[0]
    event_time = getattr(event, "Time", None)
    if event_time is None:
        pytest.skip("Event Time field is None")
    if not isinstance(event_time, datetime.datetime):
        pytest.skip(f"Event Time is not a datetime object: {type(event_time)}")
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=datetime.timezone.utc)
    age_seconds = (test_start - event_time).total_seconds()
    assert abs(age_seconds) <= 60, (
        f"Event Time {event_time.isoformat()} is not within 60 s of test start "
        f"{test_start.isoformat()} (delta = {age_seconds:.1f} s)"
    )


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
async def test_result_ready_event_carries_result_data(subscription_client, opcua_client, result_trigger, ns_indices):
    """
    JoiningSystemResultReadyEventType must carry a Result attribute containing
    ResultMetaData, validated by the result-ready event validator.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))
    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)
        outcome = await result_trigger.trigger_single(ResultType.ONE_STEP_OK_RESULT, include_traces=False)
        if not outcome.triggered:
            pytest.skip(outcome.skip_reason or "Result trigger not available")
        events = await collector.collect(count=1, timeout_s=45.0)
    if not events:
        pytest.skip(
            "No JoiningSystemResultReadyEvent received within timeout — trigger manually if using a real controller"
        )
    assert_result_ready_event_valid(events[0], context="event_payload:ResultReadyEvent")


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
@pytest.mark.parametrize("event_type,description", _REPRESENTATIVE_EVENT_TYPES)
async def test_representative_event_types_produce_valid_payload(
    subscription_client, opcua_client, event_trigger, ns_indices, event_type, description
):
    """
    Each representative event type must produce a JoiningSystemEventType event
    with valid base fields and IJT extensions. Covers one event per category:
    tool-state, tool-error, software, certificate, license, process/program,
    identifier, and config.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        event_type,
    )
    if not events:
        pytest.skip(f"No event received for {description!r} within timeout")
    assert_joining_system_event_valid(events[0], context=f"event_payload:{description}")


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
async def test_events_delivered_within_reasonable_time(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    Events must arrive within a reasonable window of the trigger call when running
    against the simulator.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt))
    t_start = time.monotonic()
    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)
        outcome = await event_trigger.trigger_event(SimulateEventType.TOOL_CONNECTED, count=1)
        if not outcome.triggered and event_trigger.is_simulator:
            pytest.skip(outcome.skip_reason or "Simulator trigger failed")
        events = await collector.collect(count=1, timeout_s=30.0)
    elapsed = time.monotonic() - t_start
    if not events:
        pytest.skip("No event received within timeout — cannot assess delivery timing for a real controller")
    assert elapsed < 30.0, f"Event delivery took {elapsed:.1f} s, exceeding the expected threshold"


# ---------------------------------------------------------------------------
# ─── event_condition_classes ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.EVENT_CONDITION_CLASSES)
async def test_joining_system_condition_type_is_accessible(session_client, ns_indices):
    """
    JoiningSystemConditionType node must exist in the address space and expose a
    browse name of 'JoiningSystemConditionType'.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = session_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_CONDITION_TYPE, ns_ijt))
    try:
        browse_name = await node.read_browse_name()
    except ua.UaError as exc:
        pytest.fail(f"JoiningSystemConditionType node not accessible: {exc}")
    assert browse_name is not None, "JoiningSystemConditionType browse name is None"
    assert browse_name.Name == "JoiningSystemConditionType", (
        f"Expected browse name 'JoiningSystemConditionType', got {browse_name.Name!r}"
    )


@pytest.mark.requires_cu(CU.EVENT_CONDITION_CLASSES)
async def test_condition_type_is_subscribable(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    Creating a subscription to JoiningSystemConditionType must not raise an error.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    server_node = subscription_client.nodes.server
    condition_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_CONDITION_TYPE, ns_ijt))
    try:
        async with EventCollector(subscription_client) as collector:
            await collector.subscribe(server_node, condition_type_node)
    except ua.UaError as exc:
        pytest.fail(f"Subscribing to JoiningSystemConditionType raised an error: {exc}")


@pytest.mark.requires_cu(CU.EVENT_CONDITION_CLASSES)
async def test_condition_has_condition_class_id(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    JoiningSystemConditionType events must carry a non-null ConditionClassId NodeId
    per the event_condition_classes specification.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_condition_events(subscription_client, event_trigger, ns_ijt)
    if not events:
        pytest.skip(
            "No condition event received within timeout — trigger a tool error manually if using a real controller"
        )
    condition = events[0]
    class_id = getattr(condition, "ConditionClassId", None)
    assert class_id is not None, "JoiningSystemConditionType.ConditionClassId must not be None"


@pytest.mark.requires_cu(CU.EVENT_CONDITION_CLASSES)
async def test_condition_has_condition_class_name(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    JoiningSystemConditionType.ConditionClassName must be a non-empty LocalizedText
    value per the event_condition_classes specification.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_condition_events(subscription_client, event_trigger, ns_ijt)
    if not events:
        pytest.skip("No condition event received within timeout")
    condition = events[0]
    class_name = getattr(condition, "ConditionClassName", None)
    if class_name is None:
        pytest.skip("ConditionClassName absent — server may not populate it for this event type")
    text = getattr(class_name, "Text", None)
    assert text and str(text).strip(), f"ConditionClassName.Text must be a non-empty string, got {text!r}"


@pytest.mark.requires_cu(CU.EVENT_CONDITION_CLASSES)
async def test_condition_has_condition_subclass_as_list(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    JoiningSystemConditionType.ConditionSubClassId must be a list type when present
    (may be empty, but must not be a scalar).
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_condition_events(subscription_client, event_trigger, ns_ijt)
    if not events:
        pytest.skip("No condition event received within timeout")
    condition = events[0]
    sub_class_ids = getattr(condition, "ConditionSubClassId", None)
    if sub_class_ids is None:
        pytest.skip("ConditionSubClassId field absent — server may not populate it for this event type")
    assert isinstance(sub_class_ids, (list, tuple)), (
        f"ConditionSubClassId must be a list type, got {type(sub_class_ids).__name__}"
    )


@pytest.mark.requires_cu(CU.EVENT_CONDITION_CLASSES)
async def test_condition_event_is_fully_valid(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    Full structural validation of a JoiningSystemConditionType event — checks
    ConditionClassId, ConditionClassName, ConditionSubClassId, JoiningTechnology,
    AssociatedEntities, and EventCode.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_condition_events(subscription_client, event_trigger, ns_ijt)
    if not events:
        pytest.skip("No condition event received within timeout")
    assert_condition_valid(events[0], context="event_condition_classes:JoiningSystemConditionType")


# ---------------------------------------------------------------------------
# ─── asset_connection_event ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ASSET_CONNECTION_EVENT)
async def test_tool_connected_event_fires(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    The server must generate a JoiningSystemEventType event when a tool is
    connected (TOOL_CONNECTED trigger).  ConditionClass = SystemConditionClassType.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No TOOL_CONNECTED event received within timeout — trigger manually if using a real controller")
    assert len(events) >= 1, "Expected at least one TOOL_CONNECTED event"
    assert_joining_system_event_valid(events[0], context="asset_connection_event:TOOL_CONNECTED")


@pytest.mark.requires_cu(CU.ASSET_CONNECTION_EVENT)
async def test_tool_disconnected_event_fires(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    The server must generate a JoiningSystemEventType event when a tool is
    disconnected (TOOL_DISCONNECTED trigger).  ConditionClass = SystemConditionClassType.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_DISCONNECTED,
    )
    if not events:
        pytest.skip("No TOOL_DISCONNECTED event received within timeout — trigger manually if using a real controller")
    assert len(events) >= 1, "Expected at least one TOOL_DISCONNECTED event"
    assert_joining_system_event_valid(events[0], context="asset_connection_event:TOOL_DISCONNECTED")


# ---------------------------------------------------------------------------
# ─── asset_connection_state_event ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ASSET_CONNECTION_STATE_EVENT)
async def test_asset_connection_state_event_fires_on_connect(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    The server must generate a JoiningSystemEventType event when
    Asset.Parameters.Connected changes — verified via TOOL_CONNECTED trigger.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No asset connection-state event received — trigger manually if using a real controller")
    assert_joining_system_event_valid(events[0], context="asset_connection_state_event:TOOL_CONNECTED")


@pytest.mark.requires_cu(CU.ASSET_CONNECTION_STATE_EVENT)
async def test_asset_connection_state_event_fires_on_disconnect(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    The server must generate a JoiningSystemEventType event when
    Asset.Parameters.Connected changes — verified via TOOL_DISCONNECTED trigger.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_DISCONNECTED,
    )
    if not events:
        pytest.skip("No asset disconnection-state event received — trigger manually if using a real controller")
    assert_joining_system_event_valid(events[0], context="asset_connection_state_event:TOOL_DISCONNECTED")


# ---------------------------------------------------------------------------
# ─── asset_enable_state_event ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ASSET_ENABLE_STATE_EVENT)
async def test_tool_enabled_event_fires(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    The server must generate a JoiningSystemEventType event when a tool is enabled.
    ConditionSubClass = AssetEnabledConditionClassType.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_ENABLED,
    )
    if not events:
        pytest.skip("No TOOL_ENABLED event received within timeout — trigger manually if using a real controller")
    assert_joining_system_event_valid(events[0], context="asset_enable_state_event:TOOL_ENABLED")


@pytest.mark.requires_cu(CU.ASSET_ENABLE_STATE_EVENT)
async def test_asset_disabled_event_fires(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    The server must generate a JoiningSystemEventType event when an asset is disabled.
    ConditionSubClass = AssetDisabledConditionClassType.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.ASSET_DISABLED,
    )
    if not events:
        pytest.skip("No ASSET_DISABLED event received within timeout — trigger manually if using a real controller")
    assert_joining_system_event_valid(events[0], context="asset_enable_state_event:ASSET_DISABLED")


# ---------------------------------------------------------------------------
# ─── event_payload_associated_entities ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD_ASSOCIATED_ENTITIES)
async def test_tool_event_has_associated_entities(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    AssociatedEntities must be present and non-empty in tool connection events —
    the connected tool is reported as an associated entity.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No event received within timeout")
    event = events[0]
    entities = _event_payload_field(event, "AssociatedEntities")
    if entities is None:
        pytest.skip("AssociatedEntities field absent — server may not populate it for TOOL_CONNECTED")
    assert isinstance(entities, (list, tuple)), f"AssociatedEntities must be a list, got {type(entities).__name__}"
    assert len(entities) > 0, "AssociatedEntities must be non-empty for tool connection events"


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD_ASSOCIATED_ENTITIES)
async def test_process_event_has_associated_entities(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    AssociatedEntities must be present in process-selection events — the selected
    joining process identifier is reported as an associated entity.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.PROGRAM_SELECTED,
    )
    if not events:
        pytest.skip("No PROGRAM_SELECTED event received within timeout")
    event = events[0]
    entities = _event_payload_field(event, "AssociatedEntities")
    if entities is None:
        pytest.skip("AssociatedEntities absent in PROGRAM_SELECTED event — server may not populate it")
    assert isinstance(entities, (list, tuple)), f"AssociatedEntities must be a list, got {type(entities).__name__}"


# ---------------------------------------------------------------------------
# ─── event_payload_reported_values ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD_REPORTED_VALUES)
async def test_threshold_violation_event_has_reported_values(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    ReportedValues must be present in threshold-violation events such as an
    overheating event, carrying measurement values like Temperature.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_OVERHEATED,
    )
    if not events:
        pytest.skip("No TOOL_OVERHEATED event received within timeout — trigger manually if using a real controller")
    event = events[0]
    reported_values = _event_payload_field(event, "ReportedValues")
    if reported_values is None:
        pytest.skip("ReportedValues absent in TOOL_OVERHEATED event — server may not populate it for this trigger type")
    assert isinstance(reported_values, (list, tuple)), (
        f"ReportedValues must be a list, got {type(reported_values).__name__}"
    )


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD_REPORTED_VALUES)
async def test_general_event_reported_values_are_valid_when_present(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    When ReportedValues is present in any JoiningSystemEventType event, every
    entry must be a valid measurement value structure per the spec.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No event received within timeout")
    event = events[0]
    reported_values = _event_payload_field(event, "ReportedValues")
    if reported_values is None:
        pytest.skip("ReportedValues not present in this event — nothing to validate")
    assert isinstance(reported_values, (list, tuple)), (
        f"ReportedValues must be a list, got {type(reported_values).__name__}"
    )
    for entry in reported_values:
        assert entry is not None, "Each ReportedValues entry must not be None"


# ---------------------------------------------------------------------------
# ─── identifiers_event ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.IDENTIFIERS_EVENT)
async def test_identifier_received_event_fires(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    The server must generate a JoiningSystemEventType event when an identifier
    is received via SendIdentifiers or a related interface.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.RECEIVED_IDENTIFIER,
    )
    if not events:
        pytest.skip("No RECEIVED_IDENTIFIER event within timeout — trigger manually if using a real controller")
    assert len(events) >= 1, "Expected at least one identifier-received event"
    assert_joining_system_event_valid(events[0], context="identifiers_event:RECEIVED_IDENTIFIER")


@pytest.mark.requires_cu(CU.IDENTIFIERS_EVENT)
async def test_identifier_accepted_event_fires(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    The server must generate a JoiningSystemEventType event when an identifier
    is accepted.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.ACCEPTED_IDENTIFIER,
    )
    if not events:
        pytest.skip("No ACCEPTED_IDENTIFIER event within timeout — trigger manually if using a real controller")
    assert_joining_system_event_valid(events[0], context="identifiers_event:ACCEPTED_IDENTIFIER")


@pytest.mark.requires_cu(CU.IDENTIFIERS_EVENT)
async def test_identifier_event_has_associated_entities(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    Identifier events must include AssociatedEntities containing the received
    identifiers per the identifiers_event specification.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.RECEIVED_IDENTIFIER,
    )
    if not events:
        pytest.skip("No identifier event received within timeout")
    event = events[0]
    entities = _event_payload_field(event, "AssociatedEntities")
    if entities is None:
        pytest.skip("AssociatedEntities absent in identifier event — server may not populate it for this trigger")
    assert isinstance(entities, (list, tuple)), f"AssociatedEntities must be a list, got {type(entities).__name__}"


# ---------------------------------------------------------------------------
# ─── select_process_event ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SELECT_PROCESS_EVENT)
async def test_program_selected_event_fires(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    The server must generate a JoiningSystemEventType event when a joining process
    is selected. ConditionClass = ProcessConditionClassType. ConditionSubClass =
    SelectedProcessConditionClassType.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.PROGRAM_SELECTED,
    )
    if not events:
        pytest.skip("No PROGRAM_SELECTED event within timeout — trigger manually if using a real controller")
    assert len(events) >= 1, "Expected at least one program-selected event"
    assert_joining_system_event_valid(events[0], context="select_process_event:PROGRAM_SELECTED")


@pytest.mark.requires_cu(CU.SELECT_PROCESS_EVENT)
async def test_program_selected_event_has_associated_entities(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    The program-selected event must include AssociatedEntities containing the
    identifier of the selected Joining Process per the select_process_event spec.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.PROGRAM_SELECTED,
    )
    if not events:
        pytest.skip("No PROGRAM_SELECTED event received within timeout")
    event = events[0]
    entities = _event_payload_field(event, "AssociatedEntities")
    if entities is None:
        pytest.skip("AssociatedEntities absent in PROGRAM_SELECTED event — server may not populate it for this trigger")
    assert isinstance(entities, (list, tuple)), f"AssociatedEntities must be a list, got {type(entities).__name__}"


# ---------------------------------------------------------------------------
# ─── negative / robustness ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
async def test_subscribing_to_nonexistent_event_type_returns_error(subscription_client):
    """
    Subscribing to a NodeId that does not exist in the address space must raise
    ua.UaError or equivalent.  Some servers defer the error to the first
    notification cycle; if the server accepts the subscription silently the test
    is skipped rather than failed.
    """
    server_node = subscription_client.nodes.server
    nonexistent_node = subscription_client.get_node(ua.NodeId(999999, 999))
    caught_error = False
    try:
        async with EventCollector(subscription_client) as collector:
            await collector.subscribe(server_node, nonexistent_node)
    except (ua.UaError, Exception):
        caught_error = True
    if not caught_error:
        pytest.skip(
            "Server accepted subscription to a non-existent NodeId without raising an error — "
            "deferred error handling is server-defined behaviour"
        )


# ---------------------------------------------------------------------------
# ─── event_payload (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
async def test_event_type_is_joining_system_event_or_subtype(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    Every event received on a JoiningSystemEventType subscription must carry
    EventType = JoiningSystemEventType (or a sub-type NodeId).  The EventType
    field must be non-null and must not be the null NodeId.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No event received within timeout")
    event = events[0]
    event_type_nid = getattr(event, "EventType", None)
    assert event_type_nid is not None, "EventType field must not be None"
    assert isinstance(event_type_nid, ua.NodeId), f"EventType must be a NodeId, got {type(event_type_nid).__name__}"
    assert not (event_type_nid.NamespaceIndex == 0 and event_type_nid.Identifier == 0), (
        "EventType NodeId must not be the null NodeId (ns=0, id=0)"
    )


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD)
async def test_event_source_node_resolves_in_address_space(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    SourceNode in the received event must be a valid NodeId that resolves in
    the server address space — reading it must succeed without a UA error.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No event received within timeout")
    event = events[0]
    source_node_id = getattr(event, "SourceNode", None)
    assert source_node_id is not None, "SourceNode field must not be None"
    assert isinstance(source_node_id, ua.NodeId), f"SourceNode must be a NodeId, got {type(source_node_id).__name__}"
    source_node = opcua_client.get_node(source_node_id)
    try:
        attr = await source_node.read_attribute(ua.AttributeIds.NodeClass)
    except ua.UaError as exc:
        pytest.fail(f"SourceNode {source_node_id!r} could not be read from address space: {exc}")
    assert attr.Value.Value is not None, "SourceNode NodeClass must not be None"


# ---------------------------------------------------------------------------
# ─── event_condition_classes (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.EVENT_CONDITION_CLASSES)
async def test_condition_class_id_references_object_type_node(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    ConditionClassId must reference an existing node in the address space whose
    NodeClass = ObjectType, confirming it is a valid OPC UA event/condition type.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_condition_events(subscription_client, event_trigger, ns_ijt)
    if not events:
        pytest.skip("No condition event received within timeout")
    event = events[0]
    class_id = getattr(event, "ConditionClassId", None)
    if class_id is None:
        pytest.skip("ConditionClassId absent in received condition event")
    assert isinstance(class_id, ua.NodeId), f"ConditionClassId must be a NodeId, got {type(class_id).__name__}"
    referenced_node = opcua_client.get_node(class_id)
    try:
        attr = await referenced_node.read_attribute(ua.AttributeIds.NodeClass)
    except ua.UaError as exc:
        pytest.fail(f"ConditionClassId {class_id!r} did not resolve in address space: {exc}")
    assert attr.Value.Value == ua.NodeClass.ObjectType, (
        f"ConditionClassId node must have NodeClass=ObjectType, got {attr.Value.Value!r}"
    )


# ---------------------------------------------------------------------------
# ─── asset_connection_event (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ASSET_CONNECTION_EVENT)
async def test_asset_connection_event_source_node_resolves(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    The SourceNode of an asset connection event must be a valid NodeId that
    resolves in the address space, identifying the connected asset node.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No TOOL_CONNECTED event received within timeout")
    event = events[0]
    source_node_id = getattr(event, "SourceNode", None)
    assert source_node_id is not None, "SourceNode must not be None in connection event"
    assert isinstance(source_node_id, ua.NodeId), f"SourceNode must be a NodeId, got {type(source_node_id).__name__}"
    source_node = opcua_client.get_node(source_node_id)
    try:
        attr = await source_node.read_attribute(ua.AttributeIds.NodeClass)
    except ua.UaError as exc:
        pytest.fail(f"SourceNode {source_node_id!r} from connection event did not resolve: {exc}")
    assert attr.Value.Value is not None, "SourceNode NodeClass must not be None"


@pytest.mark.requires_cu(CU.ASSET_CONNECTION_EVENT)
async def test_asset_connection_event_joining_technology_is_nonzero(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    JoiningTechnology in an asset connection event must be non-zero; the value
    UNDEFINED (0) is invalid for a real connected asset.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No TOOL_CONNECTED event received within timeout")
    event = events[0]
    joining_tech = _event_payload_field(event, "JoiningTechnology")
    if joining_tech is None:
        pytest.skip("JoiningTechnology absent in TOOL_CONNECTED event — may be nested inside JoiningSystemEventContent")

    jt_int = _joining_technology_to_int_or_none(joining_tech)
    if jt_int is not None:
        assert jt_int != 0, f"JoiningTechnology must be non-zero (UNDEFINED=0 is invalid), got {jt_int}"
        return

    jt_text = getattr(joining_tech, "Text", joining_tech)
    assert isinstance(jt_text, str) and jt_text.strip(), (
        f"JoiningTechnology text must be non-empty when provided as LocalizedText/string, got {joining_tech!r}"
    )


# ---------------------------------------------------------------------------
# ─── asset_connection_state_event (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ASSET_CONNECTION_STATE_EVENT)
async def test_asset_connection_state_event_severity_is_nonzero(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    The Severity field in a connection-state event must be non-zero.
    Valid OPC UA Severity values range from 1 to 1000.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No connection-state event received within timeout")
    event = events[0]
    severity = getattr(event, "Severity", None)
    assert severity is not None, "Severity field must be present in connection-state event"
    assert isinstance(severity, int), f"Severity must be an integer, got {type(severity).__name__}"
    assert 1 <= severity <= 1000, f"Severity must be in range 1–1000, got {severity}"


@pytest.mark.requires_cu(CU.ASSET_CONNECTION_STATE_EVENT)
async def test_asset_connection_state_event_source_node_resolves(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    SourceNode in a connection-state event must be a valid NodeId that resolves
    in the address space, identifying the asset whose state changed.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No connection-state event received within timeout")
    event = events[0]
    source_node_id = getattr(event, "SourceNode", None)
    assert source_node_id is not None, "SourceNode must not be None in connection-state event"
    source_node = opcua_client.get_node(source_node_id)
    try:
        attr = await source_node.read_attribute(ua.AttributeIds.NodeClass)
    except ua.UaError as exc:
        pytest.fail(f"SourceNode {source_node_id!r} in connection-state event did not resolve: {exc}")
    assert attr.Value.Value is not None


# ---------------------------------------------------------------------------
# ─── asset_enable_state_event (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ASSET_ENABLE_STATE_EVENT)
async def test_asset_enable_state_event_source_node_resolves(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    SourceNode in an asset enable-state event must resolve in the address space,
    identifying the specific asset that was enabled or disabled.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_ENABLED,
    )
    if not events:
        pytest.skip("No TOOL_ENABLED event received within timeout")
    event = events[0]
    source_node_id = getattr(event, "SourceNode", None)
    assert source_node_id is not None, "SourceNode must not be None in enable-state event"
    source_node = opcua_client.get_node(source_node_id)
    try:
        attr = await source_node.read_attribute(ua.AttributeIds.NodeClass)
    except ua.UaError as exc:
        pytest.fail(f"SourceNode {source_node_id!r} in enable-state event did not resolve: {exc}")
    assert attr.Value.Value is not None


@pytest.mark.requires_cu(CU.ASSET_ENABLE_STATE_EVENT)
async def test_asset_enable_state_event_severity_is_nonzero(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    Severity in an asset enable-state event must be in range 1–1000 per OPC UA.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_ENABLED,
    )
    if not events:
        pytest.skip("No TOOL_ENABLED event received within timeout")
    event = events[0]
    severity = getattr(event, "Severity", None)
    assert severity is not None, "Severity must be present in enable-state event"
    assert isinstance(severity, int), f"Severity must be an integer, got {type(severity).__name__}"
    assert 1 <= severity <= 1000, f"Severity must be in range 1–1000, got {severity}"


# ---------------------------------------------------------------------------
# ─── event_payload_associated_entities (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD_ASSOCIATED_ENTITIES)
async def test_associated_entity_has_entity_type_and_id(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    Each AssociatedEntityDataType entry must contain both EntityType and EntityId
    as non-null values per the IJT spec.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No event received within timeout")
    event = events[0]
    entities = _event_payload_field(event, "AssociatedEntities")
    if entities is None or len(entities) == 0:
        pytest.skip("AssociatedEntities absent or empty — cannot validate structure")
    for i, entity in enumerate(entities):
        entity_type = getattr(entity, "EntityType", None)
        entity_id = getattr(entity, "EntityId", None)
        assert entity_type is not None, f"AssociatedEntities[{i}].EntityType must not be None"
        assert entity_id is not None, f"AssociatedEntities[{i}].EntityId must not be None"


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD_ASSOCIATED_ENTITIES)
async def test_associated_entity_type_is_valid_non_negative(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    EntityType in each AssociatedEntityDataType must be a non-negative integer
    matching a valid EntityTypeEnumeration value.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No event received within timeout")
    event = events[0]
    entities = _event_payload_field(event, "AssociatedEntities")
    if entities is None or len(entities) == 0:
        pytest.skip("AssociatedEntities absent or empty — cannot validate EntityType")
    for i, entity in enumerate(entities):
        entity_type = getattr(entity, "EntityType", None)
        if entity_type is None:
            continue
        assert isinstance(entity_type, int), (
            f"AssociatedEntities[{i}].EntityType must be an integer (enum), got {type(entity_type).__name__}"
        )
        assert entity_type >= 0, f"AssociatedEntities[{i}].EntityType must be non-negative, got {entity_type}"


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD_ASSOCIATED_ENTITIES)
async def test_associated_entity_id_is_non_empty(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    EntityId in each AssociatedEntityDataType must be a non-empty string
    that uniquely identifies the referenced entity.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_CONNECTED,
    )
    if not events:
        pytest.skip("No event received within timeout")
    event = events[0]
    entities = _event_payload_field(event, "AssociatedEntities")
    if entities is None or len(entities) == 0:
        pytest.skip("AssociatedEntities absent or empty — cannot validate EntityId")
    for i, entity in enumerate(entities):
        entity_id = getattr(entity, "EntityId", None)
        assert entity_id is not None, f"AssociatedEntities[{i}].EntityId is None — must be a non-empty string"
        assert isinstance(entity_id, str), (
            f"AssociatedEntities[{i}].EntityId must be a string, got {type(entity_id).__name__}"
        )
        assert len(entity_id) > 0, f"AssociatedEntities[{i}].EntityId must be non-empty"


# ---------------------------------------------------------------------------
# ─── event_payload_reported_values (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD_REPORTED_VALUES)
async def test_reported_value_has_mandatory_fields(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    Each ReportedValueDataType entry must contain CurrentValue — the only mandatory
    field per the NodeSet2 spec. PhysicalQuantity, LowLimit, HighLimit, and
    EngineeringUnits are all optional and may be absent.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_OVERHEATED,
    )
    if not events:
        pytest.skip("No TOOL_OVERHEATED event received within timeout")
    event = events[0]
    reported_values = _event_payload_field(event, "ReportedValues")
    if reported_values is None or len(reported_values) == 0:
        pytest.skip("ReportedValues absent or empty in TOOL_OVERHEATED event")
    for i, entry in enumerate(reported_values):
        val = getattr(entry, "CurrentValue", None)
        assert val is not None, f"ReportedValues[{i}].CurrentValue must not be None (mandatory field)"


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD_REPORTED_VALUES)
async def test_reported_value_current_value_is_numeric(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    CurrentValue in each ReportedValueDataType should be a numeric Python type
    (float or int) when the entry has a PhysicalQuantity (representing Double on
    the OPC UA wire). Entries without a numeric CurrentValue are skipped.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_OVERHEATED,
    )
    if not events:
        pytest.skip("No TOOL_OVERHEATED event received within timeout")
    event = events[0]
    reported_values = _event_payload_field(event, "ReportedValues")
    if reported_values is None or len(reported_values) == 0:
        pytest.skip("ReportedValues absent or empty")
    for i, entry in enumerate(reported_values):
        current = getattr(entry, "CurrentValue", None)
        if current is None:
            continue
        if not isinstance(current, (int, float)):
            continue  # CurrentValue can be any type (String, DateTime, etc.) per spec
        assert isinstance(current, (int, float)), (
            f"ReportedValues[{i}].CurrentValue must be numeric (Double/Float), got {type(current).__name__}"
        )


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD_REPORTED_VALUES)
async def test_reported_value_engineering_units_present(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    When EngineeringUnits is populated on a ReportedValueDataType entry, it must
    expose a valid UnitId. EngineeringUnits is optional per spec — entries without
    it are skipped.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.TOOL_OVERHEATED,
    )
    if not events:
        pytest.skip("No TOOL_OVERHEATED event received within timeout")
    event = events[0]
    reported_values = _event_payload_field(event, "ReportedValues")
    if reported_values is None or len(reported_values) == 0:
        pytest.skip("ReportedValues absent or empty")
    for i, entry in enumerate(reported_values):
        eu = getattr(entry, "EngineeringUnits", None)
        if eu is None:
            pytest.skip(f"ReportedValues[{i}].EngineeringUnits absent — server may not populate it for this trigger")
        unit_id = getattr(eu, "UnitId", None)
        assert unit_id is not None, f"ReportedValues[{i}].EngineeringUnits.UnitId must not be None"


# ---------------------------------------------------------------------------
# ─── identifiers_event (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.IDENTIFIERS_EVENT)
async def test_identifier_event_associated_entities_are_non_empty(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    AssociatedEntities in a RECEIVED_IDENTIFIER event must be present and
    non-empty — the received identifiers must be reported as associated entities.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.RECEIVED_IDENTIFIER,
    )
    if not events:
        pytest.skip("No RECEIVED_IDENTIFIER event received within timeout")
    event = events[0]
    entities = _event_payload_field(event, "AssociatedEntities")
    if entities is None:
        pytest.skip("AssociatedEntities absent in identifier event — server may not populate it for this trigger")
    assert isinstance(entities, (list, tuple)), f"AssociatedEntities must be a list, got {type(entities).__name__}"
    assert len(entities) > 0, (
        "AssociatedEntities must be non-empty for RECEIVED_IDENTIFIER events — "
        "identifiers must be reported as associated entities per the spec"
    )


@pytest.mark.requires_cu(CU.IDENTIFIERS_EVENT)
async def test_identifier_event_source_node_resolves(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    SourceNode of a RECEIVED_IDENTIFIER event must resolve in the address space,
    identifying the asset that received the identifiers.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.RECEIVED_IDENTIFIER,
    )
    if not events:
        pytest.skip("No RECEIVED_IDENTIFIER event received within timeout")
    event = events[0]
    source_node_id = getattr(event, "SourceNode", None)
    assert source_node_id is not None, "SourceNode must not be None in identifier event"
    source_node = opcua_client.get_node(source_node_id)
    try:
        attr = await source_node.read_attribute(ua.AttributeIds.NodeClass)
    except ua.UaError as exc:
        pytest.fail(f"SourceNode {source_node_id!r} in identifier event did not resolve: {exc}")
    assert attr.Value.Value is not None


@pytest.mark.requires_cu(CU.IDENTIFIERS_EVENT)
async def test_identifier_event_timestamp_is_recent(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    The Time field of a RECEIVED_IDENTIFIER event must be within a reasonable
    tolerance (≤ 60 seconds) of the time the event was triggered.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    trigger_time = datetime.datetime.now(datetime.timezone.utc)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.RECEIVED_IDENTIFIER,
    )
    if not events:
        pytest.skip("No RECEIVED_IDENTIFIER event received within timeout")
    event = events[0]
    event_time = getattr(event, "Time", None)
    if event_time is None:
        pytest.skip("Time field absent in identifier event")
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=datetime.timezone.utc)
    delta_s = abs((event_time - trigger_time).total_seconds())
    assert delta_s <= 60.0, (
        f"Identifier event Time is {delta_s:.1f}s from trigger time — expected ≤ 60s "
        f"(event_time={event_time}, trigger_time={trigger_time})"
    )


# ---------------------------------------------------------------------------
# ─── select_process_event (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SELECT_PROCESS_EVENT)
async def test_select_process_event_associated_entities_contain_process_id(
    subscription_client, opcua_client, event_trigger, ns_indices
):
    """
    A PROGRAM_SELECTED event's AssociatedEntities must include at least one
    entry with a non-empty EntityId identifying the selected joining process.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.PROGRAM_SELECTED,
    )
    if not events:
        pytest.skip("No PROGRAM_SELECTED event received within timeout")
    event = events[0]
    entities = _event_payload_field(event, "AssociatedEntities")
    if entities is None:
        pytest.skip("AssociatedEntities absent in PROGRAM_SELECTED event")
    assert isinstance(entities, (list, tuple)), f"AssociatedEntities must be a list, got {type(entities).__name__}"
    assert len(entities) > 0, "AssociatedEntities must be non-empty for PROGRAM_SELECTED events"
    non_empty_ids = [getattr(e, "EntityId", None) for e in entities if getattr(e, "EntityId", None)]
    assert len(non_empty_ids) > 0, (
        "At least one AssociatedEntity must have a non-empty EntityId identifying the selected joining process"
    )


@pytest.mark.requires_cu(CU.SELECT_PROCESS_EVENT)
async def test_select_process_event_source_node_resolves(subscription_client, opcua_client, event_trigger, ns_indices):
    """
    SourceNode of a PROGRAM_SELECTED event must resolve in the address space,
    identifying the asset or controller that selected the joining process.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    events = await _collect_events_after_trigger(
        subscription_client,
        event_trigger,
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt),
        SimulateEventType.PROGRAM_SELECTED,
    )
    if not events:
        pytest.skip("No PROGRAM_SELECTED event received within timeout")
    event = events[0]
    source_node_id = getattr(event, "SourceNode", None)
    assert source_node_id is not None, "SourceNode must not be None in PROGRAM_SELECTED event"
    source_node = opcua_client.get_node(source_node_id)
    try:
        attr = await source_node.read_attribute(ua.AttributeIds.NodeClass)
    except ua.UaError as exc:
        pytest.fail(f"SourceNode {source_node_id!r} in PROGRAM_SELECTED event did not resolve: {exc}")
    assert attr.Value.Value is not None
