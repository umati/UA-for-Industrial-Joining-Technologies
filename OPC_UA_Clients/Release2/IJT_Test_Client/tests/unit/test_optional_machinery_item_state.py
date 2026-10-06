"""Regression coverage for optional, read-only Machinery checks."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from asyncua import ua

from helpers.namespaces import NS_MACHINERY, MachineryStates, RefTypes
from specification_tests import test_optional_machinery_item_state as checks


async def test_absent_feature_skips_without_cu_claim(monkeypatch):
    monkeypatch.setattr(checks, "_browse_refs", AsyncMock(return_value=[]))
    with pytest.raises(pytest.skip.Exception, match="not an IJT conformance unit"):
        await checks._discover_tool_states([("tool", object())], {})
    assert [marker.name for marker in checks.pytestmark] == ["live"]


@pytest.mark.parametrize("defect", ["namespace", "reference", "class", "missing", "duplicate"])
async def test_malformed_exposed_child_fails(monkeypatch, defect):
    ref = SimpleNamespace(
        BrowseName=ua.QualifiedName("CurrentState", 0),
        ReferenceTypeId=ua.NodeId(RefTypes.HAS_COMPONENT),
        NodeClass=ua.NodeClass.Variable,
    )
    if defect == "namespace":
        ref.BrowseName.NamespaceIndex = 12
    elif defect == "reference":
        ref.ReferenceTypeId = ua.NodeId(RefTypes.HAS_PROPERTY)
    elif defect == "class":
        ref.NodeClass = ua.NodeClass.Object
    refs = [] if defect == "missing" else [ref, ref] if defect == "duplicate" else [ref]
    monkeypatch.setattr(checks, "_browse_refs", AsyncMock(return_value=refs))
    with pytest.raises(AssertionError):
        await checks._child(
            SimpleNamespace(nodeid="state"),
            "CurrentState",
            0,
            RefTypes.HAS_COMPONENT,
            ua.NodeClass.Variable,
        )


@pytest.mark.parametrize(
    "identifier",
    [
        MachineryStates.NOT_AVAILABLE,
        MachineryStates.OUT_OF_SERVICE,
        MachineryStates.NOT_EXECUTING,
        MachineryStates.EXECUTING,
    ],
)
async def test_good_standard_states_and_localized_labels_pass(monkeypatch, identifier):
    text = ua.DataValue(ua.Variant(ua.LocalizedText("Zustand", "de")))
    value = ua.DataValue(ua.Variant(ua.NodeId(identifier, 12)))
    nodes = [SimpleNamespace(read_data_value=AsyncMock(return_value=data)) for data in (text, value)]
    monkeypatch.setattr(checks, "_state_variables", AsyncMock(return_value=nodes))
    await checks.test_optional_tool_state_values(([("tool", object())], 12))


async def test_bad_quality_is_not_a_conformance_failure(monkeypatch):
    data = ua.DataValue(StatusCode=ua.StatusCode(ua.StatusCodes.BadNoCommunication))
    node = SimpleNamespace(read_data_value=AsyncMock(return_value=data))
    monkeypatch.setattr(checks, "_state_variables", AsyncMock(return_value=(node, node)))
    with pytest.raises(pytest.skip.Exception, match="non-Good"):
        await checks.test_optional_tool_state_values(([("tool", object())], 12))


async def test_good_invalid_state_id_fails(monkeypatch):
    text = ua.DataValue(ua.Variant(ua.LocalizedText("Executing")))
    wrong = ua.DataValue(ua.Variant(ua.NodeId(MachineryStates.EXECUTING, 99)))
    nodes = [SimpleNamespace(read_data_value=AsyncMock(return_value=data)) for data in (text, wrong)]
    monkeypatch.setattr(checks, "_state_variables", AsyncMock(return_value=nodes))
    with pytest.raises(AssertionError, match="standard Machinery state"):
        await checks.test_optional_tool_state_values(([("tool", object())], 12))


async def test_all_tools_with_exposed_state_are_collected(monkeypatch):
    state = object()
    monkeypatch.setattr(
        checks, "_child", AsyncMock(side_effect=[None, None, None, object(), object(), state, object(), object()])
    )
    states, namespace = await checks._discover_tool_states(
        [("absent", object()), ("present", object())], {NS_MACHINERY: 12}
    )
    assert states == [("present", state)]
    assert namespace == 12


async def test_direct_add_in_without_monitoring_is_collected(monkeypatch):
    state = object()
    monkeypatch.setattr(checks, "_child", AsyncMock(side_effect=[state, None]))
    states, _namespace = await checks._discover_tool_states([("tool", object())], {NS_MACHINERY: 12})
    assert states == [("tool", state)]


async def test_browse_errors_are_not_absence_skips(monkeypatch):
    monkeypatch.setattr(checks, "_browse_refs", AsyncMock(side_effect=TimeoutError("browse failed")))
    with pytest.raises(TimeoutError):
        await checks._child(
            object(),
            "MachineryItemState",
            12,
            RefTypes.HAS_ADD_IN,
            ua.NodeClass.Object,
            required=False,
        )


async def test_expected_type_and_derived_type_are_accepted(monkeypatch):
    expected = ua.NodeId(1002, 12)
    derived = ua.NodeId("CustomStateMachine", 14)
    node = SimpleNamespace(session=object(), nodeid="instance", read_type_definition=AsyncMock(return_value=expected))
    await checks._assert_type(node, expected)
    node.read_type_definition.return_value = derived
    get_references = AsyncMock(return_value=[SimpleNamespace(NodeId=expected)])
    monkeypatch.setattr(checks, "Node", lambda *_args: SimpleNamespace(get_references=get_references))
    await checks._assert_type(node, expected)
    get_references.assert_awaited_once()


@pytest.mark.parametrize("parents", [[], [SimpleNamespace(NodeId=ua.NodeId(999, 12))]])
async def test_wrong_or_cyclic_type_fails(monkeypatch, parents):
    actual = ua.NodeId(999, 12)
    node = SimpleNamespace(session=object(), nodeid="instance", read_type_definition=AsyncMock(return_value=actual))
    monkeypatch.setattr(
        checks,
        "Node",
        lambda *_args: SimpleNamespace(get_references=AsyncMock(return_value=parents)),
    )
    with pytest.raises(AssertionError, match="or a subtype"):
        await checks._assert_type(node, ua.NodeId(1002, 12))


@pytest.mark.parametrize(
    "property_name,value,variant_type,valid",
    [
        ("Name", ua.QualifiedName("Executing", 12), ua.VariantType.QualifiedName, True),
        ("Name", ua.QualifiedName("Executing", 99), ua.VariantType.QualifiedName, False),
        ("Name", ua.QualifiedName("Unknown", 12), ua.VariantType.QualifiedName, False),
        ("Name", "Executing", ua.VariantType.String, False),
        *[("Number", value, ua.VariantType.UInt32, True) for value in range(4)],
        ("Number", 5006, ua.VariantType.UInt32, False),
        ("Number", 3, ua.VariantType.Int32, False),
    ],
)
async def test_optional_property_values(monkeypatch, property_name, value, variant_type, valid):
    data_type = ua.ObjectIds.QualifiedName if property_name == "Name" else ua.ObjectIds.UInt32
    node = SimpleNamespace(
        read_data_type=AsyncMock(return_value=ua.NodeId(data_type)),
        read_value_rank=AsyncMock(return_value=-1),
        read_data_value=AsyncMock(return_value=ua.DataValue(ua.Variant(value, variant_type))),
    )
    monkeypatch.setattr(checks, "_assert_type", AsyncMock())
    if valid:
        await checks._validate_optional_state_property(node, property_name, 12)
    else:
        with pytest.raises(AssertionError):
            await checks._validate_optional_state_property(node, property_name, 12)


async def test_missing_optional_properties_skip(monkeypatch):
    monkeypatch.setattr(checks, "_state_variables", AsyncMock(return_value=(object(), object())))
    monkeypatch.setattr(checks, "_child", AsyncMock(return_value=None))
    with pytest.raises(pytest.skip.Exception, match="Name and Number not exposed"):
        await checks.test_optional_tool_state_name_and_number(([("tool", object())], 12))


@pytest.mark.parametrize("property_name", ["Name", "Number"])
async def test_non_good_optional_property_values_are_accepted(monkeypatch, property_name):
    data_type = ua.ObjectIds.QualifiedName if property_name == "Name" else ua.ObjectIds.UInt32
    node = SimpleNamespace(
        read_data_type=AsyncMock(return_value=ua.NodeId(data_type)),
        read_value_rank=AsyncMock(return_value=-1),
        read_data_value=AsyncMock(
            return_value=ua.DataValue(StatusCode=ua.StatusCode(ua.StatusCodes.BadNoCommunication))
        ),
    )
    monkeypatch.setattr(checks, "_assert_type", AsyncMock())
    await checks._validate_optional_state_property(node, property_name, 12)


@pytest.mark.parametrize(
    "values,valid",
    [
        ([ua.NodeId(i, 12) for i in (5006, 5005, 5007, 5004)], True),
        ([ua.NodeId(5007, 12)], True),
        ([], False),
        ([ua.NodeId(5007, 12), ua.NodeId(5007, 12)], False),
        ([ua.NodeId(5007, 99)], False),
        ([ua.NodeId(9999, 12)], False),
        (["Executing"], False),
    ],
)
async def test_available_states_values(monkeypatch, values, valid):
    node = SimpleNamespace(
        read_data_type=AsyncMock(return_value=ua.NodeId(ua.ObjectIds.NodeId)),
        read_value_rank=AsyncMock(return_value=1),
        read_data_value=AsyncMock(return_value=ua.DataValue(ua.Variant(values, ua.VariantType.NodeId))),
    )
    monkeypatch.setattr(checks, "_assert_type", AsyncMock())
    if valid:
        await checks._validate_available_states(node, 12)
    else:
        with pytest.raises(AssertionError):
            await checks._validate_available_states(node, 12)


async def test_missing_available_states_skips(monkeypatch):
    monkeypatch.setattr(checks, "_child", AsyncMock(return_value=None))
    with pytest.raises(pytest.skip.Exception, match="AvailableStates not exposed"):
        await checks.test_optional_tool_available_states(([("tool", object())], 12))


@pytest.mark.parametrize("rank,quality,valid", [(1, ua.StatusCodes.BadNoCommunication, True), (-1, 0, False)])
async def test_available_states_rank_and_quality(monkeypatch, rank, quality, valid):
    node = SimpleNamespace(
        read_data_type=AsyncMock(return_value=ua.NodeId(ua.ObjectIds.NodeId)),
        read_value_rank=AsyncMock(return_value=rank),
        read_data_value=AsyncMock(return_value=ua.DataValue(StatusCode=ua.StatusCode(quality))),
    )
    monkeypatch.setattr(checks, "_assert_type", AsyncMock())
    if valid:
        await checks._validate_available_states(node, 12)
    else:
        with pytest.raises(AssertionError):
            await checks._validate_available_states(node, 12)
