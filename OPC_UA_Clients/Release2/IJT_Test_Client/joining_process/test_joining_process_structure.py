"""
Structural tests for JoiningProcessManagement — verifies the AddIn node exists,
has the correct type definition, and exposes all required method nodes.
"""

import pytest
from asyncua import ua

from helpers.namespaces import BN, NS_IJT_BASE, IJTTypes
from helpers.node_discovery import find_child_by_browse_name, get_type_definition

pytestmark = [pytest.mark.live, pytest.mark.structure]


async def test_joining_process_management_exists(joining_process_management):
    # §11.1 JoiningProcessManagement AddIn must be discoverable on JoiningSystem
    assert joining_process_management is not None, (
        "JoiningProcessManagement node must not be None"
    )


async def test_joining_process_management_type_correct(
    joining_process_management, ns_indices
):
    # §11.1 HasTypeDefinition must point to JoiningProcessManagementType
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    type_def = await get_type_definition(joining_process_management)
    expected = ua.NodeId(IJTTypes.JOINING_PROCESS_MANAGEMENT_TYPE, ns_ijt)
    assert type_def is not None, (
        "JoiningProcessManagement node has no HasTypeDefinition reference"
    )
    assert (
        type_def.Identifier == expected.Identifier
        and type_def.NamespaceIndex == expected.NamespaceIndex
    ), (
        f"Expected JoiningProcessManagementType "
        f"(ns={ns_ijt}, id={IJTTypes.JOINING_PROCESS_MANAGEMENT_TYPE}), "
        f"got ns={type_def.NamespaceIndex} id={type_def.Identifier}"
    )


async def test_select_joining_process_method_exists(
    joining_process_management, ns_indices
):
    # §11.1 SelectJoiningProcess method must be present (IJT Base ns)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    node = await find_child_by_browse_name(
        joining_process_management, BN.SELECT_JOINING_PROCESS, ns_ijt
    )
    assert node is not None, (
        f"Method '{BN.SELECT_JOINING_PROCESS}' not found in JoiningProcessManagement "
        f"(ns={ns_ijt})"
    )


async def test_start_selected_joining_method_exists(
    joining_process_management, ns_indices
):
    # §11.1 StartSelectedJoining method must be present (IJT Base ns)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    node = await find_child_by_browse_name(
        joining_process_management, BN.START_SELECTED_JOINING, ns_ijt
    )
    assert node is not None, (
        f"Method '{BN.START_SELECTED_JOINING}' not found in JoiningProcessManagement "
        f"(ns={ns_ijt})"
    )


async def test_enable_asset_method_exists(asset_management, ns_indices):
    # §11.1 EnableAsset method is on AssetManagement MethodSet (IJT Base ns)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    method_set = await find_child_by_browse_name(
        asset_management, BN.METHOD_SET, ns_ijt
    )
    if method_set is None:
        pytest.skip("AssetManagement MethodSet not found")
    node = await find_child_by_browse_name(method_set, BN.ENABLE_ASSET, ns_ijt)
    assert node is not None, (
        f"Method '{BN.ENABLE_ASSET}' not found in AssetManagement MethodSet (ns={ns_ijt})"
    )


async def test_disable_asset_method_exists(asset_management, ns_indices):
    # §11.1 DisableAsset = EnableAsset(ProductInstanceUri, False) per IJT spec.
    # There is no separate DisableAsset node; the same EnableAsset method handles both.
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    method_set = await find_child_by_browse_name(
        asset_management, BN.METHOD_SET, ns_ijt
    )
    if method_set is None:
        pytest.skip("AssetManagement MethodSet not found")
    enable_node = await find_child_by_browse_name(method_set, BN.ENABLE_ASSET, ns_ijt)
    assert enable_node is not None, (
        "EnableAsset method not found in AssetManagement MethodSet — "
        "required for both enable and disable (DisableAsset = EnableAsset with False)"
    )


async def test_abort_joining_process_method_exists(
    joining_process_management, ns_indices
):
    # §11.1 AbortJoiningProcess method must be present (IJT Base ns)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    node = await find_child_by_browse_name(
        joining_process_management, BN.ABORT_JOINING_PROCESS, ns_ijt
    )
    assert node is not None, (
        f"Method '{BN.ABORT_JOINING_PROCESS}' not found in JoiningProcessManagement "
        f"(ns={ns_ijt})"
    )
