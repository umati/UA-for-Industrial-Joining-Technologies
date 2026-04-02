"""
Structural tests for IJT event types defined in the address space.
Verifies that the event type nodes exist and have the expected namespace and
inheritance hierarchy.
"""

import pytest
from asyncua import ua

from helpers.namespaces import (
    NS_IJT_BASE,
    NS_MACH_RESULT,
    NS_OPC_UA,
    IJTTypes,
    MachineryResultTypes,
    RefTypes,
)

pytestmark = [pytest.mark.live, pytest.mark.structure]


# ---------------------------------------------------------------------------
# Node existence
# ---------------------------------------------------------------------------
async def test_joining_system_event_type_exists(session_client, ns_indices):
    ns_ijt = ns_indices[NS_IJT_BASE]
    node = session_client.get_node(
        ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt)
    )
    # read_attributes raises if the node does not exist
    try:
        await node.read_browse_name()
    except Exception as exc:
        pytest.fail(
            f"JoiningSystemEventType (ns={ns_ijt}; "
            f"i={IJTTypes.JOINING_SYSTEM_EVENT_TYPE}) is not readable: {exc}"
        )


async def test_result_ready_event_type_exists(session_client, ns_indices):
    ns_ijt = ns_indices[NS_IJT_BASE]
    node = session_client.get_node(
        ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt)
    )
    try:
        await node.read_browse_name()
    except Exception as exc:
        pytest.fail(
            f"JoiningSystemResultReadyEventType (ns={ns_ijt}; "
            f"i={IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE}) is not readable: {exc}"
        )


# ---------------------------------------------------------------------------
# Namespace index check
# ---------------------------------------------------------------------------
async def test_event_type_has_correct_namespace(session_client, ns_indices):
    ns_ijt = ns_indices[NS_IJT_BASE]
    node = session_client.get_node(
        ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt)
    )
    assert node.nodeid.NamespaceIndex == ns_ijt, (
        f"JoiningSystemResultReadyEventType NamespaceIndex must be {ns_ijt} "
        f"(NS_IJT_BASE), got {node.nodeid.NamespaceIndex}"
    )


# ---------------------------------------------------------------------------
# Inheritance: ResultReadyEventType must inherit from MachineryResultReadyEventType
# ---------------------------------------------------------------------------
async def test_result_ready_inherits_from_joining_system_event(
    session_client, ns_indices
):
    """JoiningSystemResultReadyEventType must inherit from MachineryResultReadyEventType.

    Per the IJT companion spec, JoiningSystemResultReadyEventType (IJT Base ns) is a
    subtype of MachineryResultReadyEventType (Machinery/Result ns). These are
    parallel hierarchies — JoiningSystemEventType and JoiningSystemResultReadyEventType
    are NOT in a parent-child relationship.
    """
    ns_ijt = ns_indices[NS_IJT_BASE]
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip(
            "Machinery/Result namespace not registered — cannot verify parent type"
        )
    result_ready_node = session_client.get_node(
        ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt)
    )
    refs = await result_ready_node.get_references(
        refs=ua.NodeId(RefTypes.HAS_SUBTYPE, ns_indices[NS_OPC_UA]),
        direction=ua.BrowseDirection.Inverse,
    )
    if not refs:
        pytest.skip(
            "No inverse HasSubtype references found on ResultReadyEventType — "
            "cannot verify inheritance"
        )
    parent_node_ids = [ref.NodeId for ref in refs]
    expected_parent = ua.NodeId(MachineryResultTypes.RESULT_READY_EVENT_TYPE, ns_mr)
    assert expected_parent in parent_node_ids, (
        f"JoiningSystemResultReadyEventType must inherit (HasSubtype) from "
        f"MachineryResultReadyEventType ({expected_parent}); "
        f"found parents: {parent_node_ids}"
    )
