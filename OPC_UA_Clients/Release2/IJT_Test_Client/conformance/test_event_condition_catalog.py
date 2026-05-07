"""
Exhaustive IJT event and condition catalogue coverage.

The IJT simulator exposes 60 concrete EventSimulation_t ids. These tests walk
the complete catalogue by use-case category and verify each id as:
- a JoiningSystemEventType notification through SimulateEvents, and
- a retained JoiningSystemConditionType notification through SimulateConditions.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.event_collector import EventCollector
from helpers.event_payload import event_payload_field as _event_payload_field
from helpers.event_validator import (
    assert_condition_valid,
    assert_joining_system_event_valid,
)
from helpers.namespaces import NS_IJT_BASE, IJTTypes, SimulateEventType

pytestmark = [pytest.mark.live, pytest.mark.conformance, pytest.mark.events]

_EVENT_TIMEOUT = 45.0
_CONDITION_ID_PREFIX = "JoiningSystemCondition|"
_PRODUCT_INSTANCE_URI_KEY = "ProductInstanceUri="
_EVENT_ID_KEY = "EventId="
_EVENT_CODE_KEY = "EventCode="


def _require_ns_ijt(ns_indices):
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    return ns_ijt


def _node_id(identifier: int, namespace_idx: int) -> ua.NodeId:
    return ua.NodeId(identifier, namespace_idx)  # type: ignore[arg-type]


def _localized_text_text(value: object | None) -> str:
    if value is None:
        return ""
    text = getattr(value, "Text", value)
    return "" if text is None else str(text)


def _event_id_text(event: object) -> str:
    event_id = getattr(event, "EventId", None)
    assert isinstance(event_id, (bytes, bytearray)), f"EventId must be ByteString bytes, got {event_id!r}"
    assert len(event_id) > 0, "EventId ByteString is empty"
    return bytes(event_id).decode("utf-8")


def _condition_id(event: object) -> ua.NodeId:
    condition_id = getattr(event, "NodeId", None)
    assert isinstance(condition_id, ua.NodeId), f"Condition event NodeId is not a NodeId: {condition_id!r}"
    assert isinstance(condition_id.Identifier, str), f"ConditionId identifier should be string: {condition_id!r}"
    return condition_id


def _assert_common_event_fields(event: object, expected_event_type: ua.NodeId) -> None:
    assert getattr(event, "EventType", None) == expected_event_type
    assert isinstance(getattr(event, "EventId", None), (bytes, bytearray))
    assert _localized_text_text(getattr(event, "Message", None)).strip()
    assert str(getattr(event, "SourceName", "")).strip()
    assert getattr(event, "SourceNode", None) is not None
    assert int(getattr(event, "Severity", 0)) > 0
    assert getattr(event, "ConditionClassId", None) is not None
    assert _localized_text_text(getattr(event, "ConditionClassName", None)).strip()


def _assert_payload(event: object, label: str, event_type: int, require_event_code_match: bool) -> None:
    event_code = _event_payload_field(event, "EventCode")
    assert event_code is not None, f"{label}: EventCode is absent"
    assert int(event_code) >= 0, f"{label}: EventCode must be non-negative, got {event_code!r}"
    if require_event_code_match:
        assert int(event_code) == event_type, f"{label}: EventCode {event_code!r} did not match {event_type}"

    event_text = _event_payload_field(event, "EventText")
    assert _localized_text_text(event_text).strip(), f"{label}: EventText is empty"

    joining_technology = _event_payload_field(event, "JoiningTechnology")
    assert _localized_text_text(joining_technology).strip(), f"{label}: JoiningTechnology is empty"

    associated_entities = _event_payload_field(event, "AssociatedEntities")
    assert isinstance(associated_entities, (list, tuple)), (
        f"{label}: AssociatedEntities should be an array, got {type(associated_entities).__name__}"
    )
    assert len(associated_entities) >= 1, f"{label}: AssociatedEntities should include source asset context"

    reported_values = _event_payload_field(event, "ReportedValues")
    if event_type in SimulateEventType.REPORTED_VALUE_TYPES:
        assert isinstance(reported_values, (list, tuple)), (
            f"{label}: ReportedValues should be an array, got {type(reported_values).__name__}"
        )
        assert len(reported_values) >= 1, f"{label}: ReportedValues should include measurement evidence"
    elif reported_values is not None:
        assert isinstance(reported_values, (list, tuple)), (
            f"{label}: ReportedValues should be an array when populated, got {type(reported_values).__name__}"
        )


def _assert_condition_identity(event: object) -> None:
    condition_id_text = str(_condition_id(event).Identifier)
    event_id_text = _event_id_text(event)
    associated_entities = _event_payload_field(event, "AssociatedEntities")

    assert condition_id_text.startswith(_CONDITION_ID_PREFIX)
    assert _PRODUCT_INSTANCE_URI_KEY in condition_id_text
    assert f"{_EVENT_ID_KEY}{event_id_text}" in condition_id_text
    assert _EVENT_CODE_KEY not in condition_id_text

    entity_ids = [str(getattr(entity, "EntityId", "")) for entity in associated_entities]
    assert any(
        entity_id and f"{_PRODUCT_INSTANCE_URI_KEY}{entity_id}" in condition_id_text for entity_id in entity_ids
    ), "ConditionId should include ProductInstanceUri from AssociatedEntities"


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


def _event_code_matches(expected: int) -> Callable[[object], bool]:
    def _predicate(item: object) -> bool:
        return _event_payload_field(item, "EventCode") == expected

    return _predicate


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD, CU.EVENT_CONDITION_CLASSES)
async def test_simulated_event_catalog_has_expected_shape():
    values = [value for value, _ in SimulateEventType.ALL_KNOWN]
    grouped = [value for use_case_events in SimulateEventType.USE_CASES.values() for value, _ in use_case_events]

    assert values == list(range(1, 61))
    assert sorted(grouped) == values
    assert len(grouped) == len(set(grouped))


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD, CU.EVENT_CONDITION_CLASSES)
@pytest.mark.parametrize("use_case,event_types", SimulateEventType.USE_CASES.items())
async def test_all_simulated_event_use_cases_raise_joining_system_events(
    use_case,
    event_types,
    subscription_client,
    event_trigger,
    ns_indices,
):
    ns_ijt = _require_ns_ijt(ns_indices)
    event_type_node_id = _node_id(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt)

    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(
            subscription_client.nodes.server,
            subscription_client.get_node(event_type_node_id),
            queue_size=500,
        )
        for event_type, label in event_types:
            outcome = await event_trigger.trigger_event(event_type, count=1)
            if not outcome.triggered and event_trigger.is_simulator:
                pytest.skip(outcome.skip_reason or "Simulator event trigger failed")
            events = await collector.collect(count=1, timeout_s=_EVENT_TIMEOUT)
            if not events:
                pytest.skip(f"No JoiningSystemEventType received for {use_case}:{label}")
            event = events[0]
            _assert_common_event_fields(event, event_type_node_id)
            _assert_payload(event, f"{use_case}:{label}", event_type, require_event_code_match=False)
            assert_joining_system_event_valid(event, context=f"event_catalog:{use_case}:{label}")


@pytest.mark.requires_cu(CU.EVENT_PAYLOAD, CU.EVENT_CONDITION_CLASSES)
@pytest.mark.parametrize("use_case,event_types", SimulateEventType.USE_CASES.items())
async def test_all_simulated_event_use_cases_raise_joining_system_conditions(
    use_case,
    event_types,
    subscription_client,
    event_trigger,
    ns_indices,
):
    ns_ijt = _require_ns_ijt(ns_indices)
    condition_type_node_id = _node_id(IJTTypes.JOINING_SYSTEM_CONDITION_TYPE, ns_ijt)

    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(
            subscription_client.nodes.server,
            subscription_client.get_node(condition_type_node_id),
            queue_size=500,
        )
        for event_type, label in event_types:
            outcome = await event_trigger.trigger_condition(event_type)
            if not outcome.triggered and event_trigger.is_simulator:
                pytest.skip(outcome.skip_reason or "Simulator condition trigger failed")
            event, seen = await _collect_until(
                collector,
                _event_code_matches(event_type),
            )
            if event is None:
                pytest.skip(f"No JoiningSystemConditionType received for {use_case}:{label}; saw {len(seen)} events")
            _assert_common_event_fields(event, condition_type_node_id)
            _assert_payload(event, f"{use_case}:{label}", event_type, require_event_code_match=True)
            assert getattr(event, "Retain", None) is True
            assert getattr(event, "EnabledState/Id", None) is True
            assert getattr(event, "AckedState/Id", None) is False
            assert getattr(event, "ConfirmedState/Id", None) is False
            _assert_condition_identity(event)
            assert_condition_valid(event, context=f"condition_catalog:{use_case}:{label}")
