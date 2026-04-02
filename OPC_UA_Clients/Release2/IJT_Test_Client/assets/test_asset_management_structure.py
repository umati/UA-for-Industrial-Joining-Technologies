"""
test_asset_management_structure.py — Asset management address-space structure tests.
Verifies the structural layout of the AssetManagement AddIn:
  - JoiningSystem is present and has the correct type definition.
  - AssetManagement and Assets folder nodes exist.
  - All 13 required asset sub-folders are present under Assets.
  - Controllers and Tools folders contain at least one instance.
  - AssetManagement exposes a MethodSet.
  - Asset instance browse names are unique within each folder.
"""
import pytest
from asyncua import ua
from helpers.namespaces import (
    NS_DI, NS_IJT_BASE,
    BN, IJTTypes,
)
from helpers.node_discovery import (
    find_child_by_browse_name,
    browse_folder_instances,
    get_type_definition,
)
pytestmark = [pytest.mark.live, pytest.mark.structure]
async def test_joining_system_found(joining_system):
    """JoiningSystem fixture must resolve to a non-None node."""
    assert joining_system is not None, "JoiningSystem node was not found in the address space"
async def test_joining_system_browse_name_is_string(joining_system):
    """JoiningSystem browse name must be a non-empty string."""
    bn = await joining_system.read_browse_name()
    assert bn is not None, "read_browse_name() returned None for JoiningSystem"
    assert bn.Name and len(bn.Name) > 0, (
        "JoiningSystem browse name must not be empty"
    )
async def test_joining_system_has_type_definition(joining_system, ns_indices):
    """JoiningSystem must have HasTypeDefinition = JoiningSystemType (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    type_def = await get_type_definition(joining_system)
    assert type_def is not None, "JoiningSystem has no HasTypeDefinition reference"
    expected = ua.NodeId(IJTTypes.JOINING_SYSTEM_TYPE, ns_ijt)
    assert type_def.Identifier == expected.Identifier, (
        f"JoiningSystem type definition Identifier: expected {expected.Identifier}, "
        f"got {type_def.Identifier}"
    )
    assert type_def.NamespaceIndex == expected.NamespaceIndex, (
        f"JoiningSystem type definition NamespaceIndex: expected {expected.NamespaceIndex}, "
        f"got {type_def.NamespaceIndex}"
    )
async def test_asset_management_exists(asset_management):
    """AssetManagement AddIn node must be present on the JoiningSystem."""
    assert asset_management is not None, "AssetManagement node not found"
async def test_assets_folder_exists(assets_folder):
    """Assets folder must be present inside AssetManagement."""
    assert assets_folder is not None, "Assets folder node not found inside AssetManagement"
@pytest.mark.parametrize("folder_name", BN.ALL_ASSET_FOLDERS)
async def test_all_13_asset_folders_exist(folder_name, assets_folder, ns_indices):
    """Each of the 13 required asset sub-folders must exist under the Assets folder."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    folder_node = await find_child_by_browse_name(assets_folder, folder_name, ns_ijt)
    assert folder_node is not None, (
        f"Required asset folder '{folder_name}' not found under Assets"
    )
async def test_controllers_folder_not_empty(controllers_instances):
    """Controllers folder must contain at least one controller instance."""
    assert len(controllers_instances) > 0, (
        "No controller instances found in Controllers folder"
    )
async def test_tools_folder_not_empty(tools_instances):
    """Tools folder must contain at least one tool instance."""
    assert len(tools_instances) > 0, (
        "No tool instances found in Tools folder"
    )
async def test_asset_management_has_method_set(asset_management, ns_indices):
    """AssetManagement must expose a MethodSet child (IJT Base namespace)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    method_set = await find_child_by_browse_name(asset_management, BN.METHOD_SET, ns_ijt)
    assert method_set is not None, (
        "MethodSet node not found under AssetManagement (IJT Base namespace)"
    )
async def test_asset_instances_have_unique_browse_names(controllers_folder):
    """Browse names of all controller instances within the folder must be unique."""
    instances = await browse_folder_instances(controllers_folder)
    names = [bn_str for bn_str, _ in instances]
    assert len(names) == len(set(names)), (
        f"Duplicate browse names detected in Controllers folder: {names}"
    )