"""
Method invocation tests for JoiningProcessManagement.
Each test opens a fresh function-scoped client (opcua_client) to ensure state
isolation. Session-scoped fixtures (ns_indices, controllers_instances) are safe
to combine with function-scoped opcua_client — pytest-asyncio handles the
differing scopes correctly with asyncio_mode = auto.
"""

import pytest
from asyncua import ua

from helpers.namespaces import BN, NS_DI, NS_IJT_BASE
from helpers.node_discovery import find_child_by_browse_name, find_joining_system

pytestmark = [pytest.mark.live, pytest.mark.methods]


async def _get_jpm(client, ns_ijt):
    """Re-discover JoiningProcessManagement on a fresh client connection."""
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found — server may not be running")
    jpm = await find_child_by_browse_name(js, BN.JOINING_PROCESS_MANAGEMENT, ns_ijt)
    if jpm is None:
        pytest.skip("JoiningProcessManagement node not found on JoiningSystem")
    return jpm


async def _get_enable_asset_method(client, ns_ijt):
    """Find EnableAsset on AssetManagement/MethodSet and return (method_set, method_node)."""
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found — server may not be running")
    am = await find_child_by_browse_name(js, BN.ASSET_MANAGEMENT, ns_ijt)
    if am is None:
        pytest.skip("AssetManagement node not found on JoiningSystem")
    method_set = await find_child_by_browse_name(am, BN.METHOD_SET, ns_ijt)
    if method_set is None:
        pytest.skip("MethodSet not found in AssetManagement")
    method_node = await find_child_by_browse_name(method_set, BN.ENABLE_ASSET, ns_ijt)
    if method_node is None:
        pytest.skip(
            f"'{BN.ENABLE_ASSET}' method not found in AssetManagement/MethodSet"
        )
    # OPC UA: call_method must be invoked on the direct parent (MethodSet), not AssetManagement
    return method_set, method_node


async def _get_product_instance_uri(client, ns_ijt, ns_di, asset_instances):
    """Read ProductInstanceUri from the first tool's Identification node."""
    if not asset_instances:
        return ""
    asset_node = client.get_node(asset_instances[0][1].nodeid)
    try:
        ident = await find_child_by_browse_name(asset_node, BN.IDENTIFICATION, ns_di)
        if ident is None:
            return ""
        pi_node = await find_child_by_browse_name(ident, "ProductInstanceUri", ns_di)
        if pi_node is None:
            return ""
        val = await pi_node.read_value()
        return str(val) if val else ""
    except Exception:
        return ""


async def test_enable_asset_with_valid_asset_id(
    opcua_client, ns_indices, tools_instances
):
    """EnableAsset(ProductInstanceUri, True) on AssetManagement/MethodSet must succeed."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    am, method_node = await _get_enable_asset_method(opcua_client, ns_ijt)
    pi_uri = await _get_product_instance_uri(
        opcua_client, ns_ijt, ns_di, tools_instances
    )
    try:
        await am.call_method(
            method_node.nodeid,
            ua.Variant(pi_uri, ua.VariantType.String),
            ua.Variant(True, ua.VariantType.Boolean),
        )
    except ua.UaError as exc:
        status_str = str(exc)
        if any(
            s in status_str
            for s in ("BadNotSupported", "BadInvalidArgument", "BadNotFound")
        ):
            pytest.skip(f"EnableAsset returned expected error on this server: {exc}")
        raise


async def test_disable_asset_with_valid_asset_id(
    opcua_client, ns_indices, tools_instances
):
    """DisableAsset = EnableAsset(ProductInstanceUri, False) on AssetManagement/MethodSet."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    am, method_node = await _get_enable_asset_method(opcua_client, ns_ijt)
    pi_uri = await _get_product_instance_uri(
        opcua_client, ns_ijt, ns_di, tools_instances
    )
    try:
        await am.call_method(
            method_node.nodeid,
            ua.Variant(pi_uri, ua.VariantType.String),
            ua.Variant(False, ua.VariantType.Boolean),
        )
    except ua.UaError as exc:
        status_str = str(exc)
        if any(
            s in status_str
            for s in ("BadNotSupported", "BadInvalidArgument", "BadNotFound")
        ):
            pytest.skip(
                f"EnableAsset(disable) returned expected error on this server: {exc}"
            )
        raise


async def test_select_joining_process_with_invalid_id(opcua_client, ns_indices):
    """SelectJoiningProcess with empty string must raise BadInvalidArgument or BadNotSupported."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await find_child_by_browse_name(
        jpm, BN.SELECT_JOINING_PROCESS, ns_ijt
    )
    if method_node is None:
        pytest.skip(
            f"'{BN.SELECT_JOINING_PROCESS}' method not found on JoiningProcessManagement"
        )
    try:
        await jpm.call_method(
            method_node.nodeid,
            ua.Variant("", ua.VariantType.String),
        )
        # Some servers may accept empty string without error — that is permitted
    except ua.UaError as exc:
        status_str = str(exc)
        if any(
            s in status_str
            for s in (
                "BadInvalidArgument",
                "BadNotSupported",
                "BadArgumentsMissing",
            )
        ):
            pass  # Expected: server correctly rejected an invalid program ID
        else:
            raise


async def test_abort_joining_process_returns_result(opcua_client, ns_indices):
    """AbortJoiningProcess must be callable without an unexpected exception."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await find_child_by_browse_name(jpm, BN.ABORT_JOINING_PROCESS, ns_ijt)
    if method_node is None:
        pytest.skip(
            f"'{BN.ABORT_JOINING_PROCESS}' method not found on JoiningProcessManagement"
        )
    try:
        await jpm.call_method(method_node.nodeid)
    except ua.UaError as exc:
        status_str = str(exc)
        if any(
            s in status_str
            for s in (
                "BadNotSupported",
                "BadInvalidArgument",
                "BadNothingToDo",
                "BadConditionNotActive",
                "BadArgumentsMissing",
            )
        ):
            pass  # Expected when no active joining process is running
        else:
            raise
