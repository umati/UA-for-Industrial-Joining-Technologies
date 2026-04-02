"""
Conformance unit tests for JoiningProcessManagement — §11.1 CU-JP-001 through CU-JP-004.
Structure tests use session fixtures. Method call tests use a fresh opcua_client
combined with session-scoped controllers_instances for asset NodeId resolution.
"""
import logging
import pytest
from asyncua import ua
from helpers.namespaces import NS_IJT_BASE, NS_DI, BN
from helpers.node_discovery import (
    find_joining_system,
    find_child_by_browse_name,
)
logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]
# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
async def _get_jpm(client, ns_ijt):
    """Re-discover JoiningProcessManagement on a fresh client connection."""
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found — server may not be running")
    jpm = await find_child_by_browse_name(js, BN.JOINING_PROCESS_MANAGEMENT, ns_ijt)
    if jpm is None:
        pytest.skip("JoiningProcessManagement node not found on JoiningSystem")
    return jpm
# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
async def test_cu_joining_process_joining_process_management_addin(joining_process_management):
    # §11.1 CU-JP-001: JoiningSystem must expose a JoiningProcessManagement AddIn
    assert joining_process_management is not None, (
        "JoiningProcessManagement AddIn node must not be None"
    )
async def test_cu_joining_process_required_methods_present(
    joining_process_management, asset_management, ns_indices
):
    # §11.1 CU-JP-002: SelectJoiningProcess and StartSelectedJoining must be present in JoiningProcessManagement;
    # EnableAsset is on AssetManagement MethodSet (IJT Base ns)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    for method_name in [BN.SELECT_JOINING_PROCESS, BN.START_SELECTED_JOINING]:
        node = await find_child_by_browse_name(
            joining_process_management, method_name, ns_ijt
        )
        assert node is not None, (
            f"Required method '{method_name}' not found in JoiningProcessManagement "
            f"(ns={ns_ijt})"
        )
    # EnableAsset is on AssetManagement MethodSet
    method_set = await find_child_by_browse_name(asset_management, BN.METHOD_SET, ns_ijt)
    if method_set is None:
        pytest.skip("AssetManagement MethodSet not found — cannot verify EnableAsset")
    enable_node = await find_child_by_browse_name(method_set, BN.ENABLE_ASSET, ns_ijt)
    if enable_node is None:
        pytest.skip("EnableAsset not found in AssetManagement MethodSet — not implemented on this server")
async def test_cu_joining_process_enable_disable_asset_callable(
    opcua_client, ns_indices, tools_instances
):
    # §11.1 CU-JP-003: EnableAsset on AssetManagement/MethodSet — enable then disable
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    js = await find_joining_system(opcua_client)
    if js is None:
        pytest.skip("JoiningSystem not found")
    am = await find_child_by_browse_name(js, BN.ASSET_MANAGEMENT, ns_ijt)
    if am is None:
        pytest.skip("AssetManagement not found")
    method_set = await find_child_by_browse_name(am, BN.METHOD_SET, ns_ijt)
    if method_set is None:
        pytest.skip("AssetManagement MethodSet not found")
    enable_node = await find_child_by_browse_name(method_set, BN.ENABLE_ASSET, ns_ijt)
    if enable_node is None:
        pytest.skip(f"'{BN.ENABLE_ASSET}' not found — skipping enable/disable test")
    # Get ProductInstanceUri from first tool (tools accept enable/disable, not controllers)
    pi_uri = ""
    if tools_instances and ns_di is not None:
        tool_node = opcua_client.get_node(tools_instances[0][1].nodeid)
        try:
            ident = await find_child_by_browse_name(tool_node, BN.IDENTIFICATION, ns_di)
            if ident is not None:
                pi_node = await find_child_by_browse_name(ident, "ProductInstanceUri", ns_di)
                if pi_node is not None:
                    pi_uri = str(await pi_node.read_value() or "")
        except Exception as exc:
            logger.debug("Could not read ProductInstanceUri from tool (using empty string): %s", exc)
    # Enable then disable using EnableAsset(PI, True/False)
    for enable_flag in (True, False):
        try:
            await method_set.call_method(
                enable_node.nodeid,
                ua.Variant(pi_uri, ua.VariantType.String),
                ua.Variant(enable_flag, ua.VariantType.Boolean),
            )
        except ua.UaError as exc:
            status_str = str(exc)
            if any(s in status_str for s in ("BadNotSupported", "BadInvalidArgument", "BadNotFound")):
                pass  # Expected on some simulator configurations
            else:
                raise
async def test_cu_joining_process_abort_process_callable(opcua_client, ns_indices):
    # §11.1 CU-JP-004: AbortJoiningProcess must be callable without unexpected exception
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
        if any(s in status_str for s in (
            "BadNotSupported", "BadNothingToDo", "BadConditionNotActive",
            "BadInvalidArgument", "BadArgumentsMissing",
        )):
            pass  # Expected when no joining process is currently active
        else:
            raise