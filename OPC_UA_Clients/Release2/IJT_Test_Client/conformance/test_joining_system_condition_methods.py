"""
Client method tests for IJT JoiningSystemConditionType.

Simple JoiningSystemEventType notifications are fire-and-forget and do not
support condition methods. These tests raise retained JoiningSystemConditionType
notifications and then call the standard OPC UA AcknowledgeableConditionType /
ConditionType methods using the received condition NodeId and EventId.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.event_collector import EventCollector
from helpers.event_payload import event_payload_field as _event_payload_field
from helpers.event_validator import assert_condition_valid
from helpers.namespaces import NS_IJT_BASE, IJTTypes, SimulateEventType

pytestmark = [pytest.mark.live, pytest.mark.conformance, pytest.mark.events, pytest.mark.methods]

_METHOD_TIMEOUT = 20.0
_EVENT_TIMEOUT = 45.0


def _node_id(identifier: int, namespace_idx: int) -> ua.NodeId:
    return ua.NodeId(identifier, namespace_idx)  # type: ignore[arg-type]


_ACKNOWLEDGE_METHOD = _node_id(ua.ObjectIds.AcknowledgeableConditionType_Acknowledge, 0)
_CONFIRM_METHOD = _node_id(ua.ObjectIds.AcknowledgeableConditionType_Confirm, 0)
_ADD_COMMENT_METHOD = _node_id(ua.ObjectIds.ConditionType_AddComment, 0)
_ENABLE_METHOD = _node_id(ua.ObjectIds.ConditionType_Enable, 0)
_DISABLE_METHOD = _node_id(ua.ObjectIds.ConditionType_Disable, 0)
_CONDITION_REFRESH_METHOD = _node_id(ua.ObjectIds.ConditionType_ConditionRefresh, 0)


def _require_ns_ijt(ns_indices):
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    return ns_ijt


def _localized_text_text(value: object | None) -> str:
    if value is None:
        return ""
    text = getattr(value, "Text", value)
    return "" if text is None else str(text)


def _condition_id(event: object) -> ua.NodeId:
    condition_id = getattr(event, "NodeId", None)
    assert isinstance(condition_id, ua.NodeId), f"Condition event NodeId is not a NodeId: {condition_id!r}"
    return condition_id


def _event_id_arg(event: object) -> ua.Variant:
    event_id = getattr(event, "EventId", None)
    assert isinstance(event_id, (bytes, bytearray)), f"EventId must be ByteString bytes, got {event_id!r}"
    return ua.Variant(event_id, ua.VariantType.ByteString)


def _localized_text_arg(text: str) -> ua.Variant:
    return ua.Variant(ua.LocalizedText(text, "en"), ua.VariantType.LocalizedText)


def _assert_state_id(event: object, state_name: str, expected: bool) -> None:
    state_id = getattr(event, f"{state_name}/Id", None)
    assert state_id is expected, f"{state_name}/Id expected {expected}, got {state_id!r}"


async def _collect_until(
    collector: EventCollector,
    predicate: Callable[[object], bool],
    timeout_s: float = _EVENT_TIMEOUT,
    max_events: int = 500,
) -> tuple[object | None, list[object]]:
    seen: list[object] = []
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while len(seen) < max_events:
        remaining = deadline - loop.time()
        if remaining <= 0:
            break
        events = await collector.collect(count=1, timeout_s=remaining)
        if not events:
            break
        event = events[0]
        seen.append(event)
        if predicate(event):
            return event, seen
    return None, seen


async def _subscribe_to_conditions(collector: EventCollector, subscription_client, ns_ijt: int) -> None:
    condition_type_node = subscription_client.get_node(_node_id(IJTTypes.JOINING_SYSTEM_CONDITION_TYPE, ns_ijt))
    await collector.subscribe(subscription_client.nodes.server, condition_type_node, queue_size=500)


async def _raise_condition_and_collect(subscription_client, event_trigger, ns_ijt: int, event_type: int) -> object:
    async with EventCollector(subscription_client) as collector:
        await _subscribe_to_conditions(collector, subscription_client, ns_ijt)
        outcome = await event_trigger.trigger_condition(event_type)
        if not outcome.triggered and event_trigger.is_simulator:
            pytest.skip(outcome.skip_reason or "Simulator condition trigger failed")
        event, seen = await _collect_until(
            collector,
            lambda item: _event_payload_field(item, "EventCode") == event_type,
        )

    if event is None:
        pytest.skip(f"No JoiningSystemConditionType received for event type {event_type}; saw {len(seen)} events")
    assert_condition_valid(event, context=f"condition_method:event_type_{event_type}")
    return event


async def _call_condition_method(condition_node, method_id: ua.NodeId, *args) -> object:
    return await asyncio.wait_for(condition_node.call_method(method_id, *args), timeout=_METHOD_TIMEOUT)


@pytest.mark.requires_cu(CU.EVENT_CONDITION_CLASSES)
async def test_condition_acknowledge_sets_acked_state(opcua_client, subscription_client, event_trigger, ns_indices):
    ns_ijt = _require_ns_ijt(ns_indices)
    raised = await _raise_condition_and_collect(
        subscription_client,
        event_trigger,
        ns_ijt,
        SimulateEventType.TOOL_MISSING_ERROR,
    )
    condition_node = opcua_client.get_node(_condition_id(raised))

    async with EventCollector(subscription_client) as collector:
        await _subscribe_to_conditions(collector, subscription_client, ns_ijt)
        await _call_condition_method(
            condition_node,
            _ACKNOWLEDGE_METHOD,
            _event_id_arg(raised),
            _localized_text_arg("acknowledged by IJT Test Client"),
        )
        update, seen = await _collect_until(collector, lambda item: _condition_id(item) == _condition_id(raised))

    assert update is not None, f"No acknowledge update received; saw {len(seen)} condition events"
    _assert_state_id(update, "AckedState", True)
    _assert_state_id(update, "ConfirmedState", False)
    assert getattr(update, "Retain", None) is True
    assert _localized_text_text(getattr(update, "Comment", None)) == "acknowledged by IJT Test Client"


@pytest.mark.requires_cu(CU.EVENT_CONDITION_CLASSES)
async def test_condition_confirm_sets_confirmed_state_after_acknowledge(
    opcua_client,
    subscription_client,
    event_trigger,
    ns_indices,
):
    ns_ijt = _require_ns_ijt(ns_indices)
    raised = await _raise_condition_and_collect(
        subscription_client,
        event_trigger,
        ns_ijt,
        SimulateEventType.TOOL_INVALID_ERROR,
    )
    condition_node = opcua_client.get_node(_condition_id(raised))

    async with EventCollector(subscription_client) as collector:
        await _subscribe_to_conditions(collector, subscription_client, ns_ijt)
        await _call_condition_method(
            condition_node,
            _ACKNOWLEDGE_METHOD,
            _event_id_arg(raised),
            _localized_text_arg("ack before confirm"),
        )
        await _collect_until(collector, lambda item: _condition_id(item) == _condition_id(raised))
        await _call_condition_method(
            condition_node,
            _CONFIRM_METHOD,
            _event_id_arg(raised),
            _localized_text_arg("confirmed by IJT Test Client"),
        )
        update, seen = await _collect_until(collector, lambda item: _condition_id(item) == _condition_id(raised))

    assert update is not None, f"No confirm update received; saw {len(seen)} condition events"
    _assert_state_id(update, "AckedState", True)
    _assert_state_id(update, "ConfirmedState", True)
    assert getattr(update, "Retain", None) is True
    assert _localized_text_text(getattr(update, "Comment", None)) == "confirmed by IJT Test Client"


@pytest.mark.requires_cu(CU.EVENT_CONDITION_CLASSES)
async def test_condition_add_comment_does_not_ack_or_confirm(
    opcua_client,
    subscription_client,
    event_trigger,
    ns_indices,
):
    ns_ijt = _require_ns_ijt(ns_indices)
    raised = await _raise_condition_and_collect(
        subscription_client,
        event_trigger,
        ns_ijt,
        SimulateEventType.TOOL_INCOMPATIBLE_ERROR,
    )
    condition_node = opcua_client.get_node(_condition_id(raised))

    async with EventCollector(subscription_client) as collector:
        await _subscribe_to_conditions(collector, subscription_client, ns_ijt)
        await _call_condition_method(
            condition_node,
            _ADD_COMMENT_METHOD,
            _event_id_arg(raised),
            _localized_text_arg("comment from IJT Test Client"),
        )
        update, seen = await _collect_until(collector, lambda item: _condition_id(item) == _condition_id(raised))

    assert update is not None, f"No AddComment update received; saw {len(seen)} condition events"
    _assert_state_id(update, "AckedState", False)
    _assert_state_id(update, "ConfirmedState", False)
    assert getattr(update, "Retain", None) is True
    assert _localized_text_text(getattr(update, "Comment", None)) == "comment from IJT Test Client"


@pytest.mark.requires_cu(CU.EVENT_CONDITION_CLASSES)
async def test_condition_rejects_acknowledge_with_wrong_event_id(
    opcua_client,
    subscription_client,
    event_trigger,
    ns_indices,
):
    ns_ijt = _require_ns_ijt(ns_indices)
    raised = await _raise_condition_and_collect(
        subscription_client,
        event_trigger,
        ns_ijt,
        SimulateEventType.TOOL_NOT_AVAILABLE_ERROR,
    )
    condition_node = opcua_client.get_node(_condition_id(raised))

    with pytest.raises(ua.UaStatusCodeError) as exc_info:
        await _call_condition_method(
            condition_node,
            _ACKNOWLEDGE_METHOD,
            ua.Variant(b"not-the-current-event-id", ua.VariantType.ByteString),
            _localized_text_arg("should be rejected"),
        )
    assert "BadEventIdUnknown" in str(exc_info.value)


@pytest.mark.requires_cu(CU.EVENT_CONDITION_CLASSES)
async def test_condition_disable_and_enable_methods_are_callable(
    opcua_client,
    subscription_client,
    event_trigger,
    ns_indices,
):
    ns_ijt = _require_ns_ijt(ns_indices)
    raised = await _raise_condition_and_collect(
        subscription_client,
        event_trigger,
        ns_ijt,
        SimulateEventType.TOOL_SOFTWARE_INVALID,
    )
    condition_node = opcua_client.get_node(_condition_id(raised))

    async with EventCollector(subscription_client) as collector:
        await _subscribe_to_conditions(collector, subscription_client, ns_ijt)
        await _call_condition_method(condition_node, _DISABLE_METHOD)
        disabled_update, _ = await _collect_until(
            collector,
            lambda item: _condition_id(item) == _condition_id(raised),
            timeout_s=10.0,
        )
        if disabled_update is not None:
            _assert_state_id(disabled_update, "EnabledState", False)

        await _call_condition_method(condition_node, _ENABLE_METHOD)
        enabled_update, seen = await _collect_until(
            collector,
            lambda item: _condition_id(item) == _condition_id(raised),
        )

    assert enabled_update is not None, f"No Enable update received; saw {len(seen)} condition events"
    _assert_state_id(enabled_update, "EnabledState", True)
    assert getattr(enabled_update, "Retain", None) is True


@pytest.mark.requires_cu(CU.EVENT_CONDITION_CLASSES)
async def test_condition_refresh_replays_retained_condition(
    opcua_client,
    subscription_client,
    event_trigger,
    ns_indices,
):
    ns_ijt = _require_ns_ijt(ns_indices)
    raised = await _raise_condition_and_collect(
        subscription_client,
        event_trigger,
        ns_ijt,
        SimulateEventType.LICENSE_EXPIRY_WARNING,
    )

    async with EventCollector(subscription_client) as collector:
        await _subscribe_to_conditions(collector, subscription_client, ns_ijt)
        assert collector.subscription_id is not None
        refresh_object = opcua_client.get_node(_node_id(ua.ObjectIds.ConditionType, 0))
        await _call_condition_method(
            refresh_object,
            _CONDITION_REFRESH_METHOD,
            ua.Variant(collector.subscription_id, ua.VariantType.UInt32),
        )
        replay, seen = await _collect_until(
            collector,
            lambda item: (
                _condition_id(item) == _condition_id(raised)
                and getattr(item, "EventId", None) == getattr(raised, "EventId", None)
            ),
        )

    assert replay is not None, f"ConditionRefresh did not replay retained condition; saw {len(seen)} events"
    assert getattr(replay, "Retain", None) is True
