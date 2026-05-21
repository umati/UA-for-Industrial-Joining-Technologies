"""Contracts for low-level OPC UA negative-service request helpers."""

from asyncua import ua

from conformance.test_joining_system_base import _expanded_nodeid
from conformance.test_result_management import _delete_nodes_parameters


def test_expanded_nodeid_preserves_nodeid_components() -> None:
    nodeid = ua.NodeId("ResultManagement", 2, ua.NodeIdType.String)

    expanded = _expanded_nodeid(nodeid)

    assert expanded.Identifier == "ResultManagement"
    assert expanded.NamespaceIndex == 2
    assert expanded.NodeIdType == ua.NodeIdType.String


def test_delete_nodes_parameters_wraps_delete_item() -> None:
    item = ua.DeleteNodesItem(
        NodeId=ua.NodeId(1001, 2),
        DeleteTargetReferences=True,
    )

    params = _delete_nodes_parameters(item)

    assert isinstance(params, ua.DeleteNodesParameters)
    assert params.NodesToDelete == [item]
