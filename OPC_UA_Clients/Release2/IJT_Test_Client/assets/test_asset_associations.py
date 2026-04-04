"""
test_asset_associations.py — AssociatedWith reference tests.
Verifies that controller and tool instances are connected via symmetric
AssociatedWith (ref type 24137) references, and that all referenced target
nodes are valid and reachable.
"""

import pytest

from helpers.node_discovery import get_associated_assets

pytestmark = [pytest.mark.live, pytest.mark.structure]


async def test_assets_have_associated_with_reference(controllers_instances):
    """First controller must have at least one AssociatedWith reference target."""
    controller_node = controllers_instances[0][1]
    associated = await get_associated_assets(controller_node)
    assert len(associated) > 0, (
        "First controller has no AssociatedWith references; expected at least one associated asset (e.g. a tool)"
    )


async def test_associated_with_is_symmetric(controllers_instances, tools_instances):
    """
    AssociatedWith must be symmetric: if controller C references tool T,
    then T must also reference C via AssociatedWith.
    """
    controller_node = controllers_instances[0][1]
    associated_from_controller = await get_associated_assets(controller_node)
    if not associated_from_controller:
        pytest.skip("First controller has no AssociatedWith targets; skipping symmetry check")
    controller_node_id = controller_node.nodeid
    for target_node in associated_from_controller:
        back_refs = await get_associated_assets(target_node)
        back_node_ids = [n.nodeid for n in back_refs]
        found_back = any(
            nid.Identifier == controller_node_id.Identifier and nid.NamespaceIndex == controller_node_id.NamespaceIndex
            for nid in back_node_ids
        )
        target_bn = await target_node.read_browse_name()
        assert found_back, (
            f"AssociatedWith is not symmetric: target '{target_bn.Name}' "
            "does not have a back-reference to the first controller"
        )


async def test_controller_associated_with_tools(controllers_instances, tools_instances):
    """At least one AssociatedWith target of the first controller must be a known tool instance."""
    controller_node = controllers_instances[0][1]
    associated = await get_associated_assets(controller_node)
    if not associated:
        pytest.skip("First controller has no AssociatedWith references")
    tool_node_ids = {(node.nodeid.Identifier, node.nodeid.NamespaceIndex) for _, node in tools_instances}
    matched = any((n.nodeid.Identifier, n.nodeid.NamespaceIndex) in tool_node_ids for n in associated)
    assert matched, (
        "None of the first controller's AssociatedWith targets match any known tool instance; "
        "expected at least one controller-to-tool association"
    )


async def test_associated_nodes_are_in_same_system(controllers_instances):
    """
    All nodes reachable via AssociatedWith from the first controller must be valid:
    read_browse_name() must succeed for each, confirming they are live nodes.
    """
    controller_node = controllers_instances[0][1]
    associated = await get_associated_assets(controller_node)
    if not associated:
        pytest.skip("First controller has no AssociatedWith references")
    for target_node in associated:
        try:
            bn = await target_node.read_browse_name()
        except Exception as exc:
            pytest.fail(f"AssociatedWith target node {target_node.nodeid} is not reachable: {exc}")
        assert bn is not None, f"read_browse_name() returned None for AssociatedWith target {target_node.nodeid}"
