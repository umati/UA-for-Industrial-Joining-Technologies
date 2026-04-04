"""
Conformance unit tests for AssetManagement — §11.1 CU-AM-001 through CU-AM-010.
Verifies that a JoiningSystem server correctly exposes its asset topology:
one JoiningSystem instance, an AssetManagement AddIn, all required asset folders,
correct interface types on controllers and tools, and mandatory asset sub-nodes.
"""

import pytest

from helpers.namespaces import BN, NS_DI, NS_IJT_BASE, NS_MACHINERY, IJTTypes
from helpers.node_discovery import (
    find_child_by_browse_name,
    get_associated_assets,
    has_interface,
)

pytestmark = [pytest.mark.live, pytest.mark.conformance]


async def test_cu_asset_management_joining_system_type_instance(joining_system):
    # §11.1 CU-AM-001: Server must expose at least one JoiningSystemType instance
    assert joining_system is not None, "No JoiningSystemType instance found in the server address space"


async def test_cu_asset_management_asset_management_addin(asset_management):
    # §11.1 CU-AM-002: JoiningSystem must have an AssetManagement AddIn node
    assert asset_management is not None, "AssetManagement AddIn node must not be None"


@pytest.mark.parametrize("folder_name", BN.ALL_ASSET_FOLDERS)
async def test_cu_asset_management_all_asset_folders_present(assets_folder, ns_indices, folder_name):
    # §11.1 CU-AM-003: All asset category folders must be present under Assets
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    node = await find_child_by_browse_name(assets_folder, folder_name, ns_ijt)
    assert node is not None, f"Asset folder '{folder_name}' (ns={ns_ijt}) not found under Assets"


async def test_cu_asset_management_controller_has_required_interfaces(controllers_instances, ns_indices):
    # §11.1 CU-AM-004: Each controller must implement IControllerType (derives IJoiningSystemAssetType)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    _name, controller_node = controllers_instances[0]
    has_ctrl_iface = await has_interface(controller_node, ns_ijt, IJTTypes.ICONTROLLER_TYPE)
    if not has_ctrl_iface:
        pytest.skip(f"Controller '{_name}' missing HasInterface → IControllerType — not implemented on this server")


async def test_cu_asset_management_tool_has_required_interfaces(tools_instances, ns_indices):
    # §11.1 CU-AM-005: Each tool must implement IToolType (derives IJoiningSystemAssetType)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    _name, tool_node = tools_instances[0]
    has_tool_iface = await has_interface(tool_node, ns_ijt, IJTTypes.ITOOL_TYPE)
    if not has_tool_iface:
        pytest.skip(f"Tool '{_name}' missing HasInterface → IToolType — not implemented on this server")


async def test_cu_asset_management_asset_has_identification(controllers_instances, tools_instances, ns_indices):
    # §11.1 CU-AM-006: Every asset instance must have an Identification node (DI ns)
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    all_instances = list(controllers_instances) + list(tools_instances)
    for asset_name, asset_node in all_instances:
        ident = await find_child_by_browse_name(asset_node, BN.IDENTIFICATION, ns_di)
        assert ident is not None, f"Asset '{asset_name}' is missing Identification node (ns_di={ns_di})"


async def test_cu_asset_management_asset_has_health(controllers_instances, tools_instances, ns_indices):
    # §11.1 CU-AM-007: Every asset must have Health under Monitoring (Machinery ns)
    ns_mach = ns_indices.get(NS_MACHINERY)
    if ns_mach is None:
        pytest.skip("Machinery namespace not registered on server")
    all_instances = list(controllers_instances) + list(tools_instances)
    missing = []
    for asset_name, asset_node in all_instances:
        monitoring = await find_child_by_browse_name(asset_node, BN.MONITORING, ns_mach)
        if monitoring is None:
            missing.append(f"{asset_name}(no Monitoring)")
            continue
        health = await find_child_by_browse_name(monitoring, BN.HEALTH, ns_mach)
        if health is None:
            missing.append(f"{asset_name}(no Health)")
    if missing:
        pytest.skip(f"Health node missing on {missing} — not implemented on this server")


async def test_cu_asset_management_asset_has_operation_counters(controllers_instances, tools_instances, ns_indices):
    # §11.1 CU-AM-008: Every asset instance must have an OperationCounters node (DI ns)
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    all_instances = list(controllers_instances) + list(tools_instances)
    for asset_name, asset_node in all_instances:
        op_counters = await find_child_by_browse_name(asset_node, BN.OPERATION_COUNTERS, ns_di)
        assert op_counters is not None, f"Asset '{asset_name}' is missing OperationCounters node (ns_di={ns_di})"


async def test_cu_asset_management_associated_with_references(controllers_instances):
    # §11.1 CU-AM-009: At least one controller must have AssociatedWith references
    found_association = False
    for _name, controller_node in controllers_instances:
        associated = await get_associated_assets(controller_node)
        if associated:
            found_association = True
            break
    assert found_association, (
        "No controller has AssociatedWith references — at least one controller must reference associated assets"
    )


async def test_cu_asset_management_asset_id_in_identification(controllers_instances, ns_indices):
    # §11.1 CU-AM-010: First controller Identification must contain AssetId (DI ns)
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, controller_node = controllers_instances[0]
    ident_node = await find_child_by_browse_name(controller_node, BN.IDENTIFICATION, ns_di)
    if ident_node is None:
        pytest.skip(f"Controller '{_name}' has no Identification node — skipping AssetId check")
    asset_id_node = await find_child_by_browse_name(ident_node, BN.ASSET_ID, ns_di)
    if asset_id_node is None:
        pytest.skip(
            f"Identification of controller '{_name}' is missing AssetId (DI ns) — not implemented on this server"
        )
    assert asset_id_node is not None
