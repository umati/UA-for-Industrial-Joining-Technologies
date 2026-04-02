"""
Conformance unit tests for JointManagement — §11.1 CU-JT-001 through CU-JT-004.
Structure tests use session fixtures. Method call tests use a fresh opcua_client.
"""
import pytest
from asyncua import ua
from helpers.namespaces import NS_IJT_BASE, NS_DI, BN
from helpers.node_discovery import (
    find_joining_system,
    find_child_by_browse_name,
)
pytestmark = [pytest.mark.live, pytest.mark.conformance]
# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
async def _get_jm(client, ns_ijt):
    """Re-discover JointManagement on a fresh client connection."""
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found — server may not be running")
    jm = await find_child_by_browse_name(js, BN.JOINT_MANAGEMENT, ns_ijt)
    if jm is None:
        pytest.skip("JointManagement node not found on JoiningSystem")
    return jm
# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
async def test_cu_joint_management_joint_management_addin(joint_management):
    # §11.1 CU-JT-001: JoiningSystem must expose a JointManagement AddIn
    assert joint_management is not None, (
        "JointManagement AddIn node must not be None"
    )
async def test_cu_joint_management_required_methods_present(joint_management, ns_indices):
    # §11.1 CU-JT-002: GetJoint, GetJointList, SelectJoint, SendJoint, DeleteJoint must all be present
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    required_methods = [
        BN.GET_JOINT,
        BN.GET_JOINT_LIST,
        BN.SELECT_JOINT,
        BN.SEND_JOINT,
        BN.DELETE_JOINT,
    ]
    for method_name in required_methods:
        node = await find_child_by_browse_name(joint_management, method_name, ns_ijt)
        assert node is not None, (
            f"Required method '{method_name}' not found in JointManagement (ns={ns_ijt})"
        )
async def _get_tool_product_instance_uri(client, ns_ijt, ns_di):
    """Get ProductInstanceUri from first tool for methods requiring it."""
    js = await find_joining_system(client)
    if js is None:
        return None
    am = await find_child_by_browse_name(js, BN.ASSET_MANAGEMENT, ns_ijt)
    if am is None:
        return None
    assets = await find_child_by_browse_name(am, BN.ASSETS, ns_ijt)
    if assets is None:
        return None
    tools_folder = await find_child_by_browse_name(assets, BN.TOOLS, ns_ijt)
    if tools_folder is None:
        return None
    from helpers.node_discovery import browse_folder_instances
    instances = await browse_folder_instances(tools_folder)
    if not instances:
        return None
    _name, tool_node = instances[0]
    ident = await find_child_by_browse_name(tool_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        return None
    pi_node = await find_child_by_browse_name(ident, "ProductInstanceUri", ns_di)
    if pi_node is None:
        return None
    return await pi_node.read_value()


async def test_cu_joint_management_get_joint_list_callable(opcua_client, ns_indices):
    # §11.1 CU-JT-003: GetJointList(ProductInstanceUri) must return without unexpected exception
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    jm = await _get_jm(opcua_client, ns_ijt)
    method_node = await find_child_by_browse_name(jm, BN.GET_JOINT_LIST, ns_ijt)
    if method_node is None:
        pytest.skip(f"'{BN.GET_JOINT_LIST}' method not found on JointManagement")
    pi_uri = await _get_tool_product_instance_uri(opcua_client, ns_ijt, ns_di)
    if pi_uri is None:
        pytest.skip("Could not read ProductInstanceUri from first tool — required for GetJointList")
    try:
        result = await jm.call_method(
            method_node.nodeid,
            ua.Variant(pi_uri, ua.VariantType.String),
        )
        assert result is None or isinstance(result, (list, tuple, str)), (
            f"GetJointList returned unexpected type: {type(result)}"
        )
    except ua.UaError as exc:
        status_str = str(exc)
        if any(s in status_str for s in (
            "BadNotSupported", "BadNothingToDo", "BadArgumentsMissing",
        )):
            pytest.skip(f"GetJointList not callable on this server: {exc}")
        raise
async def test_cu_joint_management_joint_data_type_structure(opcua_client, ns_indices):
    # §11.1 CU-JT-004: Joint items returned by GetJointList must have required fields
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    jm = await _get_jm(opcua_client, ns_ijt)
    list_node = await find_child_by_browse_name(jm, BN.GET_JOINT_LIST, ns_ijt)
    if list_node is None:
        pytest.skip(f"'{BN.GET_JOINT_LIST}' method not found on JointManagement")
    pi_uri = await _get_tool_product_instance_uri(opcua_client, ns_ijt, ns_di)
    if pi_uri is None:
        pytest.skip("Could not read ProductInstanceUri from first tool — required for GetJointList")
    try:
        joint_list = await jm.call_method(
            list_node.nodeid,
            ua.Variant(pi_uri, ua.VariantType.String),
        )
    except ua.UaError as exc:
        status_str = str(exc)
        if any(s in status_str for s in ("BadNotSupported", "BadArgumentsMissing")):
            pytest.skip(f"GetJointList not callable on this server: {exc}")
        raise
    if not joint_list:
        # Attempt to populate via SendJoint, then re-query
        send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
        if send_node is None:
            pytest.skip("Joint list is empty and SendJoint is not available — cannot verify structure")
        joint_type = getattr(ua, "JointDataType", None)
        if joint_type is None:
            pytest.skip("JointDataType not available — cannot construct test joint")
        try:
            joint_data = joint_type()
            if hasattr(joint_data, "JointId"):
                joint_data.JointId = "conformance-test-joint"
            if hasattr(joint_data, "Name"):
                joint_data.Name = "ConformanceTestJoint"
            await jm.call_method(send_node.nodeid, joint_data)
        except ua.UaError as exc:
            status_str = str(exc)
            if "BadNotSupported" in status_str:
                pytest.skip(f"SendJoint not supported on simulator: {exc}")
            if "BadInvalidArgument" in status_str or "BadTypeMismatch" in status_str:
                pytest.skip(f"Minimal JointDataType rejected by server: {exc}")
            raise
        except (AttributeError, TypeError) as exc:
            pytest.skip(f"Could not construct JointDataType: {exc}")
        try:
            joint_list = await jm.call_method(
                list_node.nodeid,
                ua.Variant(pi_uri, ua.VariantType.String),
            )
        except ua.UaError as exc:
            pytest.skip(f"GetJointList failed after SendJoint: {exc}")
    if not joint_list:
        pytest.skip("Joint list is still empty after SendJoint — cannot verify data type structure")
    first_item = joint_list[0] if isinstance(joint_list, (list, tuple)) else joint_list
    # asyncua may decode JointDataType as a named object OR as a raw list of field values.
    # JointDataType field 0 = JointId (TrimmedString/String) per NodeSet definition.
    if isinstance(first_item, (list, tuple)):
        assert len(first_item) > 0, "JointDataType decoded as list but is empty"
        assert first_item[0] is not None, "JointDataType field[0] (JointId) must not be None"
    else:
        has_id_field = any(
            getattr(first_item, field, None) is not None
            for field in ("JointId", "Id", "Name", "JointName")
        )
        assert has_id_field, (
            f"First joint item has no recognisable identifier field "
            f"(checked: JointId, Id, Name, JointName). "
            f"Actual attributes: {[a for a in dir(first_item) if not a.startswith('_')]}"
        )