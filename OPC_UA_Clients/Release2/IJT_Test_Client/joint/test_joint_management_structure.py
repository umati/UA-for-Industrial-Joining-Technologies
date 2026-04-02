"""
Structural tests for JointManagement — verifies the AddIn node exists,
has the correct type definition, and exposes all required method nodes.
"""
import pytest
from asyncua import ua
from helpers.namespaces import NS_IJT_BASE, BN, IJTTypes
from helpers.node_discovery import find_child_by_browse_name, get_type_definition
pytestmark = [pytest.mark.live, pytest.mark.structure]
async def test_joint_management_exists(joint_management):
    # §11.1 JointManagement AddIn must be discoverable on JoiningSystem
    assert joint_management is not None, (
        "JointManagement node must not be None"
    )
async def test_joint_management_type_correct(joint_management, ns_indices):
    # §11.1 HasTypeDefinition must point to JointManagementType
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    type_def = await get_type_definition(joint_management)
    expected = ua.NodeId(IJTTypes.JOINT_MANAGEMENT_TYPE, ns_ijt)
    assert type_def is not None, (
        "JointManagement node has no HasTypeDefinition reference"
    )
    assert type_def.Identifier == expected.Identifier and \
           type_def.NamespaceIndex == expected.NamespaceIndex, (
        f"Expected JointManagementType "
        f"(ns={ns_ijt}, id={IJTTypes.JOINT_MANAGEMENT_TYPE}), "
        f"got ns={type_def.NamespaceIndex} id={type_def.Identifier}"
    )
async def test_get_joint_method_exists(joint_management, ns_indices):
    # §11.1 GetJoint method must be present (IJT Base ns)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    node = await find_child_by_browse_name(joint_management, BN.GET_JOINT, ns_ijt)
    assert node is not None, (
        f"Method '{BN.GET_JOINT}' not found in JointManagement (ns={ns_ijt})"
    )
async def test_get_joint_list_method_exists(joint_management, ns_indices):
    # §11.1 GetJointList method must be present (IJT Base ns)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    node = await find_child_by_browse_name(joint_management, BN.GET_JOINT_LIST, ns_ijt)
    assert node is not None, (
        f"Method '{BN.GET_JOINT_LIST}' not found in JointManagement (ns={ns_ijt})"
    )
async def test_select_joint_method_exists(joint_management, ns_indices):
    # §11.1 SelectJoint method must be present (IJT Base ns)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    node = await find_child_by_browse_name(joint_management, BN.SELECT_JOINT, ns_ijt)
    assert node is not None, (
        f"Method '{BN.SELECT_JOINT}' not found in JointManagement (ns={ns_ijt})"
    )
async def test_send_joint_method_exists(joint_management, ns_indices):
    # §11.1 SendJoint method must be present (IJT Base ns)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    node = await find_child_by_browse_name(joint_management, BN.SEND_JOINT, ns_ijt)
    assert node is not None, (
        f"Method '{BN.SEND_JOINT}' not found in JointManagement (ns={ns_ijt})"
    )
async def test_delete_joint_method_exists(joint_management, ns_indices):
    # §11.1 DeleteJoint method must be present (IJT Base ns)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    node = await find_child_by_browse_name(joint_management, BN.DELETE_JOINT, ns_ijt)
    assert node is not None, (
        f"Method '{BN.DELETE_JOINT}' not found in JointManagement (ns={ns_ijt})"
    )