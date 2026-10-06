"""Read-only Machinery companion-model checks, not IJT conformance units."""

import asyncio

import pytest
import pytest_asyncio
from asyncua import ua
from asyncua.common.node import Node

from helpers.namespaces import BN, NS_MACHINERY, MachineryStates, MachineryTypes, RefTypes
from helpers.node_discovery import _browse_refs, _node_from_ref

pytestmark = [pytest.mark.live]
_TIMEOUT = 15


async def _child(parent, name, namespace, reference, node_class, *, required=True, validate=True):
    matches = [ref for ref in await _browse_refs(parent) if ref.BrowseName.Name == name]
    if not matches and not required:
        return None
    assert len(matches) == 1, f"{parent.nodeid}: expected one {name}, found {len(matches)}"
    ref = matches[0]
    if validate:
        assert ref.BrowseName.NamespaceIndex == namespace, f"{name}: wrong BrowseName namespace"
        assert ref.ReferenceTypeId == ua.NodeId(reference), f"{name}: wrong reference type"
        assert ref.NodeClass == node_class, f"{name}: wrong node class"
    return _node_from_ref(parent, ref.NodeId)


async def _assert_type(node, expected):
    actual = await asyncio.wait_for(node.read_type_definition(), _TIMEOUT)
    seen = set()
    while actual != expected:
        assert actual is not None and actual not in seen, f"{node.nodeid}: type is not {expected} or a subtype"
        seen.add(actual)
        refs = await asyncio.wait_for(
            Node(node.session, actual).get_references(
                refs=ua.ObjectIds.HasSubtype,
                direction=ua.BrowseDirection.Inverse,
                includesubtypes=False,
            ),
            _TIMEOUT,
        )
        assert len(refs) == 1, f"{node.nodeid}: type is not {expected} or a subtype"
        actual = refs[0].NodeId


async def _discover_tool_states(tools_instances, ns_indices):
    namespace = ns_indices.get(NS_MACHINERY)
    states = []
    for name, tool in tools_instances:
        add_in = await _child(
            tool,
            BN.MACHINERY_ITEM_STATE,
            namespace,
            RefTypes.HAS_ADD_IN,
            ua.NodeClass.Object,
            required=False,
        )
        monitoring = await _child(
            tool,
            BN.MONITORING,
            namespace,
            RefTypes.HAS_ADD_IN,
            ua.NodeClass.Object,
            required=False,
            validate=False,
        )
        if monitoring is None:
            if add_in is not None:
                states.append((name, add_in))
            continue
        status = await _child(
            monitoring,
            BN.STATUS,
            namespace,
            RefTypes.HAS_COMPONENT,
            ua.NodeClass.Object,
            required=False,
            validate=False,
        )
        if status is None:
            if add_in is not None:
                states.append((name, add_in))
            continue
        state = await _child(
            status,
            BN.MACHINERY_ITEM_STATE,
            namespace,
            RefTypes.HAS_COMPONENT,
            ua.NodeClass.Object,
            required=False,
        )
        if state is not None:
            await _child(tool, BN.MONITORING, namespace, RefTypes.HAS_ADD_IN, ua.NodeClass.Object)
            await _child(monitoring, BN.STATUS, namespace, RefTypes.HAS_COMPONENT, ua.NodeClass.Object)
            if add_in is not None:
                assert state.nodeid == add_in.nodeid, "Status and add-in must reference the same state machine"
            states.append((name, state))
        elif add_in is not None:
            pytest.fail(f"{name}: exposed Status must reference the MachineryItemState add-in")
    if not states:
        pytest.skip("Optional Tool MachineryItemState not exposed; not an IJT conformance unit")
    assert namespace is not None, "Exposed MachineryItemState requires the Machinery namespace"
    return states, namespace


@pytest_asyncio.fixture
async def optional_tool_states(tools_instances, ns_indices):
    return await _discover_tool_states(tools_instances, ns_indices)


async def _state_variables(state):
    current = await _child(state, "CurrentState", 0, RefTypes.HAS_COMPONENT, ua.NodeClass.Variable)
    identifier = await _child(current, "Id", 0, RefTypes.HAS_PROPERTY, ua.NodeClass.Variable)
    return current, identifier


async def test_optional_tool_state_structure(optional_tool_states):
    states, namespace = optional_tool_states
    for _name, state in states:
        await _assert_type(state, ua.NodeId(ua.Int32(MachineryTypes.MACHINERY_ITEM_STATE_TYPE), namespace))
        current, identifier = await _state_variables(state)
        await _assert_type(current, ua.NodeId(ua.Int32(ua.ObjectIds.FiniteStateVariableType)))
        await _assert_type(identifier, ua.NodeId(ua.Int32(ua.ObjectIds.PropertyType)))
        for node, data_type in ((current, ua.ObjectIds.LocalizedText), (identifier, ua.ObjectIds.NodeId)):
            assert await asyncio.wait_for(node.read_data_type(), _TIMEOUT) == ua.NodeId(ua.Int32(data_type))
            assert await asyncio.wait_for(node.read_value_rank(), _TIMEOUT) == -1


async def test_optional_tool_state_values(optional_tool_states):
    states, namespace = optional_tool_states
    checked = 0
    for _name, state in states:
        current, identifier = await _state_variables(state)
        text = await asyncio.wait_for(current.read_data_value(raise_on_bad_status=False), _TIMEOUT)
        state_id = await asyncio.wait_for(identifier.read_data_value(raise_on_bad_status=False), _TIMEOUT)
        # Independent node reads are not an atomic snapshot. Check Good values
        # individually without comparing localized labels or requiring idle state.
        if text.StatusCode.is_good():
            assert text.Value is not None
            assert isinstance(text.Value.Value, ua.LocalizedText) and text.Value.Value.Text
            checked += 1
        if state_id.StatusCode.is_good():
            assert state_id.Value is not None
            assert isinstance(state_id.Value.Value, ua.NodeId)
            assert state_id.Value.Value in {
                ua.NodeId(ua.Int32(value), namespace)
                for value in (
                    MachineryStates.NOT_AVAILABLE,
                    MachineryStates.OUT_OF_SERVICE,
                    MachineryStates.NOT_EXECUTING,
                    MachineryStates.EXECUTING,
                )
            }, "Good CurrentState.Id must identify a standard Machinery state"
            checked += 1
    if not checked:
        pytest.skip("Optional MachineryItemState values have non-Good quality")


async def _validate_optional_state_property(node, property_name, namespace):
    await _assert_type(node, ua.NodeId(ua.Int32(ua.ObjectIds.PropertyType)))
    data_type = ua.ObjectIds.QualifiedName if property_name == "Name" else ua.ObjectIds.UInt32
    assert await asyncio.wait_for(node.read_data_type(), _TIMEOUT) == ua.NodeId(ua.Int32(data_type))
    assert await asyncio.wait_for(node.read_value_rank(), _TIMEOUT) == -1
    data = await asyncio.wait_for(node.read_data_value(raise_on_bad_status=False), _TIMEOUT)
    if not data.StatusCode.is_good():
        return
    assert data.Value is not None
    value = data.Value.Value
    # Validate each value independently: controllers can transition between reads.
    if property_name == "Name":
        assert isinstance(value, ua.QualifiedName)
        assert value.NamespaceIndex == namespace
        assert value.Name in {"NotAvailable", "OutOfService", "NotExecuting", "Executing"}
    else:
        assert data.Value.VariantType == ua.VariantType.UInt32
        assert type(value) is int and value in {0, 1, 2, 3}, "Number must be a standard Machinery StateNumber"


async def test_optional_tool_state_name_and_number(optional_tool_states):
    states, namespace = optional_tool_states
    exposed = 0
    for _name, state in states:
        current, _identifier = await _state_variables(state)
        for property_name in ("Name", "Number"):
            node = await _child(current, property_name, 0, RefTypes.HAS_PROPERTY, ua.NodeClass.Variable, required=False)
            if node is not None:
                await _validate_optional_state_property(node, property_name, namespace)
                exposed += 1
    if not exposed:
        pytest.skip("Optional CurrentState.Name and Number not exposed")


async def _validate_available_states(node, namespace):
    await _assert_type(node, ua.NodeId(ua.Int32(ua.ObjectIds.BaseDataVariableType)))
    assert await asyncio.wait_for(node.read_data_type(), _TIMEOUT) == ua.NodeId(ua.Int32(ua.ObjectIds.NodeId))
    assert await asyncio.wait_for(node.read_value_rank(), _TIMEOUT) == 1
    data = await asyncio.wait_for(node.read_data_value(raise_on_bad_status=False), _TIMEOUT)
    if not data.StatusCode.is_good():
        return
    assert data.Value is not None and data.Value.is_array
    values = data.Value.Value
    assert isinstance(values, list) and values, "AvailableStates must contain supported states"
    assert all(isinstance(value, ua.NodeId) for value in values)
    assert len(set(values)) == len(values), "AvailableStates must not contain duplicates"
    supported = {
        ua.NodeId(ua.Int32(identifier), namespace)
        for identifier in (
            MachineryStates.NOT_AVAILABLE,
            MachineryStates.OUT_OF_SERVICE,
            MachineryStates.NOT_EXECUTING,
            MachineryStates.EXECUTING,
        )
    }
    assert set(values) <= supported, "AvailableStates must reference standard Machinery states"


async def test_optional_tool_available_states(optional_tool_states):
    states, namespace = optional_tool_states
    exposed = 0
    for _name, state in states:
        node = await _child(state, "AvailableStates", 0, RefTypes.HAS_COMPONENT, ua.NodeClass.Variable, required=False)
        if node is not None:
            await _validate_available_states(node, namespace)
            exposed += 1
    if not exposed:
        pytest.skip("Optional MachineryItemState.AvailableStates not exposed")
