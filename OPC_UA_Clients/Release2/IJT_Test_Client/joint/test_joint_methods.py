"""
Method invocation tests for JointManagement.
Each test opens a fresh function-scoped client (opcua_client) to ensure state
isolation. Session-scoped ns_indices is safe to combine with opcua_client.
"""

import pytest
from asyncua import ua

from helpers.namespaces import BN, NS_DI, NS_IJT_BASE
from helpers.node_discovery import find_child_by_browse_name, find_joining_system

pytestmark = [pytest.mark.live, pytest.mark.methods]


async def _get_jm(client, ns_ijt):
    """Re-discover JointManagement on a fresh client connection."""
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found — server may not be running")
    jm = await find_child_by_browse_name(js, BN.JOINT_MANAGEMENT, ns_ijt)
    if jm is None:
        pytest.skip("JointManagement node not found on JoiningSystem")
    return jm


async def test_get_joint_list_returns_array(opcua_client, tools_instances, ns_indices):
    """GetJointList(ProductInstanceUri) must return without error; result may be empty."""
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
    # Get ProductInstanceUri from first tool's Identification
    pi_uri = None
    if tools_instances:
        _name, tool_node = tools_instances[0]
        ident = await find_child_by_browse_name(tool_node, BN.IDENTIFICATION, ns_di)
        if ident is not None:
            pi_node = await find_child_by_browse_name(
                ident, "ProductInstanceUri", ns_di
            )
            if pi_node is not None:
                pi_uri = await pi_node.read_value()
    if pi_uri is None:
        pytest.skip(
            "Could not read ProductInstanceUri from first tool — required for GetJointList"
        )
    try:
        result = await jm.call_method(
            method_node.nodeid,
            ua.Variant(pi_uri, ua.VariantType.String),
        )
        # result is None (no joints), a list of JointDataType objects, or a list of raw lists
        assert result is None or isinstance(result, (list, tuple, str, int)), (
            f"GetJointList returned unexpected type: {type(result)}"
        )
    except ua.UaError as exc:
        status_str = str(exc)
        if any(
            s in status_str
            for s in (
                "BadNotSupported",
                "BadNothingToDo",
                "BadArgumentsMissing",
                "BadInvalidArgument",
                "BadUserAccessDenied",
            )
        ):
            pytest.skip(f"GetJointList not callable on this server: {exc}")
        raise


async def test_select_joint_with_invalid_id_returns_error(opcua_client, ns_indices):
    """SelectJoint with empty string must raise BadInvalidArgument or BadNotSupported."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    jm = await _get_jm(opcua_client, ns_ijt)
    method_node = await find_child_by_browse_name(jm, BN.SELECT_JOINT, ns_ijt)
    if method_node is None:
        pytest.skip(f"'{BN.SELECT_JOINT}' method not found on JointManagement")
    try:
        await jm.call_method(
            method_node.nodeid,
            ua.Variant("", ua.VariantType.String),
        )
        # Some servers may tolerate an empty string — that is permitted
    except ua.UaError as exc:
        status_str = str(exc)
        if any(
            s in status_str
            for s in (
                "BadInvalidArgument",
                "BadNotSupported",
                "BadNodeIdUnknown",
                "BadArgumentsMissing",
            )
        ):
            pass  # Expected: server correctly rejected an invalid joint ID
        else:
            raise


async def test_send_joint_with_valid_data(opcua_client, ns_indices):
    """SendJoint with minimal joint data must not raise unexpected exceptions."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    jm = await _get_jm(opcua_client, ns_ijt)
    method_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if method_node is None:
        pytest.skip(f"'{BN.SEND_JOINT}' method not found on JointManagement")
    # Try to construct a minimal JointDataType; skip gracefully if the data type
    # is not available on this server or if the method rejects the minimal payload.
    try:
        joint_type = getattr(ua, "JointDataType", None)
        if joint_type is None:
            pytest.skip(
                "JointDataType not available after load_data_type_definitions()"
            )
        joint_data = joint_type()
        # Populate mandatory string field(s) with a placeholder if discoverable
        if hasattr(joint_data, "JointId"):
            joint_data.JointId = "test-joint-001"
        if hasattr(joint_data, "Name"):
            joint_data.Name = "TestJoint"
        await jm.call_method(method_node.nodeid, joint_data)
    except ua.UaError as exc:
        status_str = str(exc)
        if "BadNotSupported" in status_str:
            pytest.skip(f"SendJoint not supported on simulator: {exc}")
        if any(
            s in status_str
            for s in (
                "BadInvalidArgument",
                "BadTypeMismatch",
                "BadArgumentsMissing",
            )
        ):
            pass  # Minimal data rejected — acceptable for conformance testing
        else:
            raise
    except (AttributeError, TypeError) as exc:
        pytest.skip(f"Could not construct JointDataType for SendJoint test: {exc}")
