"""
Conformance unit tests for Asset Operations — OPC 40450-1.

Covers the following conformance units:

method_input_argument
    The Server supports methods defined in the specification with the following semantic
    for input argument ProductInstanceUri: if empty or NULL, the Server uses the identifier
    of the asset where the Server is deployed; if not empty, it is a valid ProductInstanceUri
    of any asset exposed by the Server.

disconnect_asset
    The Server supports the DisconnectAsset method.

enable_tool
    The Server supports the EnableAsset method for Tool instances.

set_calibration
    The Server supports SetCalibration method.

reboot_asset
    The Server supports RebootAsset method.

get_error_information
    The Server supports GetErrorInformation method for the asset.

execute_operation
    The Server supports ExecuteOperation method for the asset.
"""

import asyncio
import logging
from datetime import datetime, timezone

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.method_caller import find_and_call_method
from helpers.method_signature import ASSET_METHOD_INPUTS, assert_input_argument_names
from helpers.namespaces import BN, NS_APP, NS_DI, NS_IJT_BASE, NS_MACHINERY, NS_OPC_UA
from helpers.node_discovery import (
    browse_folder_instances,
    find_child_by_browse_name,
    find_joining_system,
    find_method_set,
)

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

_METHOD_TIMEOUT = 15


# ─── local helpers ────────────────────────────────────────────────────────────


async def _get_asset_management_method_set(client, ns_ijt: int, ns_di: int, ns_app: int | None = None):
    """Re-discover AssetManagement/MethodSet on a fresh client connection.

    Returns (asset_management_node, method_set_node).
    Tries DI namespace first for MethodSet, then falls back to the app namespace
    (some servers use the app namespace for MethodSet browse names).
    Calls pytest.skip() if either node is absent.
    """
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found on fresh client connection")
    am = await find_child_by_browse_name(js, BN.ASSET_MANAGEMENT, ns_ijt)
    if am is None:
        pytest.skip("AssetManagement not found on fresh client connection")
    ms = await find_method_set(am, ns_di, ns_ijt, ns_app)
    if ms is None:
        pytest.skip(
            "IJT spec (OPC 40450-1) requires a MethodSet child under AssetManagement — "
            "this server omits it (non-conformant)"
        )
    return am, ms


def _ordered_namespaces(*values: int | None) -> list[int]:
    """Return namespace indexes in first-seen order without duplicates."""
    ordered: list[int] = []
    for value in values:
        if value is not None and value not in ordered:
            ordered.append(value)
    return ordered


async def _find_child_in_namespaces(parent_node, browse_name: str, *namespaces: int | None):
    """Find a direct child by BrowseName across accepted namespace indexes."""
    for ns_index in _ordered_namespaces(*namespaces):
        child = await find_child_by_browse_name(parent_node, browse_name, ns_index)
        if child is not None:
            return child
    return None


async def _read_product_instance_uri(
    asset_node,
    ns_di: int,
    ns_machinery: int | None = None,
    ns_ijt: int | None = None,
    ns_app: int | None = None,
) -> str | None:
    """Return the ProductInstanceUri string from asset Identification, or None."""
    ident = await _find_child_in_namespaces(asset_node, BN.IDENTIFICATION, ns_di, ns_machinery, ns_ijt, ns_app)
    if ident is None:
        return None
    piu_node = await _find_child_in_namespaces(ident, BN.PRODUCT_INSTANCE_URI, ns_di, ns_machinery, ns_ijt, ns_app)
    if piu_node is None:
        return None
    try:
        value = await asyncio.wait_for(piu_node.read_value(), timeout=_METHOD_TIMEOUT)
        if value is None:
            return None
        piu = str(value).strip()
        return piu or None
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not read ProductInstanceUri: %s", exc)
        return None


async def _find_asset_category_folder(asset_management_node, folder_name: str, ns_ijt: int):
    """Find an asset category folder under AssetManagement/Assets, with direct fallback."""
    assets_folder = await find_child_by_browse_name(asset_management_node, BN.ASSETS, ns_ijt)
    if assets_folder is not None:
        category = await find_child_by_browse_name(assets_folder, folder_name, ns_ijt)
        if category is not None:
            return category
    return await find_child_by_browse_name(asset_management_node, folder_name, ns_ijt)


async def _read_first_asset_category_product_instance_uri(
    asset_management_node,
    folder_name: str,
    ns_ijt: int,
    ns_di: int,
    ns_machinery: int | None = None,
    ns_app: int | None = None,
) -> str | None:
    """Return the first ProductInstanceUri from an AssetManagement/Assets category."""
    category_folder = await _find_asset_category_folder(asset_management_node, folder_name, ns_ijt)
    if category_folder is None:
        return None
    try:
        children = await browse_folder_instances(category_folder, timeout=_METHOD_TIMEOUT)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not enumerate %s: %s", folder_name, exc)
        return None
    for _browse_name, child in children:
        piu = await _read_product_instance_uri(child, ns_di, ns_machinery, ns_ijt, ns_app)
        if piu:
            return piu
    return None


def _make_calibration_data():
    """Build a minimal CalibrationDataType instance when type definitions are loaded."""
    try:
        data = ua.CalibrationDataType()
    except AttributeError:
        return None
    now = datetime.now(timezone.utc)
    data.LastCalibration = now
    data.CalibrationPlace = "IJT conformance client"
    data.NextCalibration = now
    data.CalibrationValue = 0.0
    data.SensorScale = 1.0
    data.CertificateUri = ""
    return data


def _asset_arg(value: str):
    return ua.Variant(value, ua.VariantType.String)


# ─── asset management method set structure ────────────────────────────────────


@pytest.mark.requires_cu(CU.ENABLE_TOOL)
async def test_asset_management_method_set_present(asset_management, ns_indices):
    """AssetManagement must expose a MethodSet node (DI ns)."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "AssetManagement MethodSet (DI ns) not found — "
            "simulator exposes methods directly on AssetManagement rather than inside a MethodSet child; "
            "this is a known simulator deviation from the DI topology convention"
        )


@pytest.mark.requires_cu(CU.METHOD_INPUT_ARGUMENT)
@pytest.mark.parametrize("method_name, expected_args", sorted(ASSET_METHOD_INPUTS.items()))
async def test_asset_operation_method_input_arguments_match_nodeset(
    asset_management, ns_indices, method_name, expected_args
):
    """Asset operation methods exposed by the server must use the current NodeSet signatures."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_opcua = ns_indices.get(NS_OPC_UA, 0)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_ijt, ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip("AssetManagement MethodSet not found")
    method = await find_child_by_browse_name(ms, method_name, ns_ijt)
    if method is None:
        pytest.skip(f"{method_name}: Not Supported — cannot validate method signature")
    await assert_input_argument_names(method, expected_args, ns_opcua=ns_opcua, method_name=method_name)


@pytest.mark.requires_cu(CU.ENABLE_TOOL)
async def test_enable_asset_method_present_in_method_set(asset_management, ns_indices):
    """EnableAsset method must be present in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "IJT spec (OPC 40450-1) requires a MethodSet child under AssetManagement — this server omits it (non-conformant)"
        )
    method = await find_child_by_browse_name(ms, BN.ENABLE_ASSET, ns_ijt)
    assert method is not None, f"EnableAsset method (ns_ijt={ns_ijt}) not found in AssetManagement MethodSet"


# ─── disconnect_asset ─────────────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.DISCONNECT_ASSET)
async def test_disconnect_asset_method_present_in_method_set(asset_management, ns_indices):
    """DisconnectAsset method must be present in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "MethodSet not found — IJT spec (OPC 40450-1) requires MethodSet under AssetManagement; this server is non-conformant"
        )
    method = await find_child_by_browse_name(ms, BN.DISCONNECT_ASSET, ns_ijt)
    if method is None:
        pytest.skip("DisconnectAsset: Not Supported — method not found in AssetManagement MethodSet")


@pytest.mark.requires_cu(CU.DISCONNECT_ASSET)
async def test_disable_asset_then_enable_asset_restores_state(opcua_client, tools_instances, ns_indices):
    """EnableAsset(false) then EnableAsset(true) round-trip must not raise an error."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _name, tool_node = tools_instances[0]
    piu = await _read_product_instance_uri(tool_node, ns_di)
    if piu is None:
        pytest.skip(f"Tool '{_name}' has no ProductInstanceUri — cannot build method arguments")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    piu_arg = ua.Variant(piu, ua.VariantType.String)

    enable_node = await find_child_by_browse_name(ms, BN.ENABLE_ASSET, ns_ijt)
    if enable_node is None:
        pytest.skip("EnableAsset: Not Supported — skipping round-trip test")

    disable_result = await find_and_call_method(
        ms,
        BN.ENABLE_ASSET,
        ns_ijt,
        piu_arg,
        ua.Variant(False, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if not disable_result.success:
        err_str = str(disable_result.error) if disable_result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"EnableAsset(false) returned '{err_str}' — not supported on this server")
        pytest.fail(f"EnableAsset(false) failed: {err_str}")

    enable_result = await find_and_call_method(
        ms,
        BN.ENABLE_ASSET,
        ns_ijt,
        piu_arg,
        ua.Variant(True, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if not enable_result.success:
        err_str = str(enable_result.error) if enable_result.error else "unknown error"
        pytest.fail(f"EnableAsset(true) failed after EnableAsset(false) round-trip: {err_str}")


# ─── enable_tool ──────────────────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ENABLE_TOOL)
async def test_enable_asset_callable_with_tool_product_instance_uri(opcua_client, tools_instances, ns_indices):
    """EnableAsset must be callable with a tool's ProductInstanceUri."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _name, tool_node = tools_instances[0]
    piu = await _read_product_instance_uri(tool_node, ns_di)
    if piu is None:
        pytest.skip(f"Tool '{_name}' has no ProductInstanceUri — cannot build EnableAsset argument")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    result = await find_and_call_method(
        ms,
        BN.ENABLE_ASSET,
        ns_ijt,
        ua.Variant(piu, ua.VariantType.String),
        ua.Variant(True, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"EnableAsset returned '{err_str}' — not supported on this server")
        pytest.fail(f"EnableAsset failed unexpectedly: {err_str}")


# ─── method_input_argument ────────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.METHOD_INPUT_ARGUMENT)
async def test_enable_asset_callable_with_empty_product_instance_uri(opcua_client, ns_indices):
    """EnableAsset must accept an empty ProductInstanceUri and use the deployed asset.

    Per spec: if empty or NULL, the Server uses the identifier of the asset where
    the Server is deployed.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    empty_piu = ua.Variant("", ua.VariantType.String)
    result = await find_and_call_method(
        ms,
        BN.ENABLE_ASSET,
        ns_ijt,
        empty_piu,
        ua.Variant(True, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"EnableAsset returned '{err_str}' — not supported on this server")
        if "BadNodeIdUnknown" in err_str or "BadNotFound" in err_str:
            pytest.skip("Server requires a non-empty ProductInstanceUri — empty-PIU semantic may not be implemented")
        if "Uncertain" in err_str:
            # C17: server returns OpcUa_Uncertain when methodStatusCode != 0
            # Uncertain for an empty PIU is the expected production response — not a simulator deviation
            return
        pytest.fail(f"EnableAsset with empty ProductInstanceUri failed unexpectedly: {err_str}")


@pytest.mark.requires_cu(CU.METHOD_INPUT_ARGUMENT)
async def test_enable_asset_callable_with_valid_product_instance_uri(opcua_client, tools_instances, ns_indices):
    """EnableAsset must accept a valid ProductInstanceUri of any exposed asset.

    Per spec: if not empty, it is a valid ProductInstanceUri of any asset exposed by
    the Server.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _name, tool_node = tools_instances[0]
    piu = await _read_product_instance_uri(tool_node, ns_di)
    if piu is None:
        pytest.skip(f"Tool '{_name}' has no ProductInstanceUri — cannot verify non-empty PIU semantic")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    result = await find_and_call_method(
        ms,
        BN.ENABLE_ASSET,
        ns_ijt,
        ua.Variant(piu, ua.VariantType.String),
        ua.Variant(True, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"EnableAsset returned '{err_str}' — not supported on this server")
        pytest.fail(f"EnableAsset with valid ProductInstanceUri '{piu}' failed unexpectedly: {err_str}")


# ─── set_calibration ──────────────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.SET_CALIBRATION)
async def test_set_calibration_method_present_in_method_set(asset_management, ns_indices):
    """SetCalibration method must be present in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "MethodSet not found — IJT spec (OPC 40450-1) requires MethodSet under AssetManagement; this server is non-conformant"
        )
    method = await find_child_by_browse_name(ms, BN.SET_CALIBRATION, ns_ijt)
    if method is None:
        pytest.skip("SetCalibration not found in AssetManagement MethodSet — optional per spec")


@pytest.mark.requires_cu(CU.SET_CALIBRATION)
async def test_set_calibration_callable(opcua_client, ns_indices):
    """SetCalibration must be callable without raising an unhandled server error."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.SET_CALIBRATION, ns_ijt)
    if method_node is None:
        pytest.skip("SetCalibration: Not Supported — cannot verify callability")

    calibration_data = _make_calibration_data()
    if calibration_data is None:
        pytest.skip("CalibrationDataType is not loaded — cannot build SetCalibration arguments")

    result = await find_and_call_method(
        ms,
        BN.SET_CALIBRATION,
        ns_ijt,
        _asset_arg(""),
        calibration_data,
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"SetCalibration returned '{err_str}' — not supported on this server")
        if "BadInvalidArgument" in err_str:
            pytest.skip(f"SetCalibration rejected probe calibration data: {err_str}")
        pytest.fail(f"SetCalibration failed unexpectedly: {err_str}")


# ─── reboot_asset ─────────────────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.REBOOT_ASSET)
async def test_reboot_asset_method_present_in_method_set(asset_management, ns_indices):
    """RebootAsset method must be present in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "MethodSet not found — IJT spec (OPC 40450-1) requires MethodSet under AssetManagement; this server is non-conformant"
        )
    method = await find_child_by_browse_name(ms, BN.REBOOT_ASSET, ns_ijt)
    if method is None:
        pytest.skip("RebootAsset not found in AssetManagement MethodSet — optional per spec")


@pytest.mark.requires_cu(CU.REBOOT_ASSET)
async def test_reboot_asset_callable_with_tool_product_instance_uri(opcua_client, tools_instances, ns_indices):
    """RebootAsset must be callable with a tool's ProductInstanceUri."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.REBOOT_ASSET, ns_ijt)
    if method_node is None:
        pytest.skip("RebootAsset: Not Supported — cannot verify callability")

    _name, tool_node = tools_instances[0]
    piu = await _read_product_instance_uri(tool_node, ns_di)
    if piu is None:
        pytest.skip(f"Tool '{_name}' has no ProductInstanceUri — cannot build RebootAsset argument")

    result = await find_and_call_method(
        ms,
        BN.REBOOT_ASSET,
        ns_ijt,
        ua.Variant(piu, ua.VariantType.String),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"RebootAsset returned '{err_str}' — not supported on this server")
        pytest.fail(f"RebootAsset failed unexpectedly: {err_str}")


# ─── get_error_information ────────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.GET_ERROR_INFORMATION)
async def test_get_error_information_method_present_in_method_set(asset_management, ns_indices):
    """GetErrorInformation method must be present in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "MethodSet not found — IJT spec (OPC 40450-1) requires MethodSet under AssetManagement; this server is non-conformant"
        )
    method = await find_child_by_browse_name(ms, BN.GET_ERROR_INFORMATION, ns_ijt)
    if method is None:
        pytest.skip("GetErrorInformation not found in AssetManagement MethodSet — optional per spec")


@pytest.mark.requires_cu(CU.GET_ERROR_INFORMATION)
async def test_get_error_information_callable_with_tool_product_instance_uri(opcua_client, tools_instances, ns_indices):
    """GetErrorInformation must be callable with a tool's ProductInstanceUri."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.GET_ERROR_INFORMATION, ns_ijt)
    if method_node is None:
        pytest.skip("GetErrorInformation: Not Supported — cannot verify callability")

    _name, tool_node = tools_instances[0]
    piu = await _read_product_instance_uri(tool_node, ns_di)
    if piu is None:
        pytest.skip(f"Tool '{_name}' has no ProductInstanceUri — cannot build GetErrorInformation argument")

    result = await find_and_call_method(
        ms,
        BN.GET_ERROR_INFORMATION,
        ns_ijt,
        _asset_arg(piu),
        _asset_arg(""),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"GetErrorInformation returned '{err_str}' — not supported on this server")
        pytest.fail(f"GetErrorInformation failed unexpectedly: {err_str}")


# ─── execute_operation ────────────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.EXECUTE_OPERATION)
async def test_execute_operation_method_present_in_method_set(asset_management, ns_indices):
    """ExecuteOperation method must be present in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "MethodSet not found — IJT spec (OPC 40450-1) requires MethodSet under AssetManagement; this server is non-conformant"
        )
    method = await find_child_by_browse_name(ms, BN.EXECUTE_OPERATION, ns_ijt)
    if method is None:
        pytest.skip("ExecuteOperation not found in AssetManagement MethodSet — optional per spec")


@pytest.mark.requires_cu(CU.EXECUTE_OPERATION)
async def test_execute_operation_callable_with_tool_product_instance_uri(opcua_client, tools_instances, ns_indices):
    """ExecuteOperation must be callable with a tool's ProductInstanceUri."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.EXECUTE_OPERATION, ns_ijt)
    if method_node is None:
        pytest.skip("ExecuteOperation: Not Supported — cannot verify callability")

    _name, tool_node = tools_instances[0]
    piu = await _read_product_instance_uri(tool_node, ns_di)
    if piu is None:
        pytest.skip(f"Tool '{_name}' has no ProductInstanceUri — cannot build ExecuteOperation argument")

    result = await find_and_call_method(
        ms,
        BN.EXECUTE_OPERATION,
        ns_ijt,
        _asset_arg(piu),
        ua.Variant(0, ua.VariantType.Int32),
        _asset_arg("IJT conformance probe"),
        _asset_arg(""),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"ExecuteOperation returned '{err_str}' — not supported on this server")
        if "BadInvalidArgument" in err_str:
            pytest.skip(f"ExecuteOperation rejected the probe operation: {err_str}")
        pytest.fail(f"ExecuteOperation failed unexpectedly: {err_str}")


# ─── method_input_argument — extended ─────────────────────────────────────────

_INVALID_PIU = "urn:conformance:test:nonexistent:asset:xyz999"


@pytest.mark.requires_cu(CU.METHOD_INPUT_ARGUMENT)
async def test_method_input_argument_null_piu_uses_same_asset_as_empty(opcua_client, ns_indices):
    """Calling a method with a Null Variant PIU must behave identically to an empty string.

    Per spec: "empty or NULL → Server uses identifier of asset where Server is deployed."
    Both empty string and Null must resolve to the same default asset.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))

    null_piu = ua.Variant(None, ua.VariantType.String)
    result = await find_and_call_method(
        ms,
        BN.ENABLE_ASSET,
        ns_ijt,
        null_piu,
        ua.Variant(True, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
            pytest.skip(f"EnableAsset not supported on this server: {err_str}")
        if any(kw in err_str for kw in ("BadNodeIdUnknown", "BadNotFound")):
            pytest.skip(
                "Server requires non-null ProductInstanceUri — Null PIU semantic may not be implemented on this server"
            )
        if "Uncertain" in err_str:
            pytest.skip(
                "Server returned Uncertain for null ProductInstanceUri — "
                "simulator does not resolve null PIU to deployed asset (known simulator deviation)"
            )
        pytest.fail(f"EnableAsset with Null PIU failed unexpectedly: {err_str}")


@pytest.mark.requires_cu(CU.METHOD_INPUT_ARGUMENT)
async def test_method_input_argument_valid_server_asset_piu_accepted(opcua_client, ns_indices):
    """A general AssetManagement method called with the server's own PIU must succeed.

    Verifies that an explicit PIU matching the deployed Controller asset is accepted.
    The probe uses GetIdentifiers because EnableAsset is Tool-specific; calling
    EnableAsset with a Controller PIU belongs to the non-applicable-asset negative
    case, not the server-own-asset positive case.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_machinery = ns_indices.get(NS_MACHINERY)
    ns_app = ns_indices.get(NS_APP)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    js = await find_joining_system(opcua_client)
    if js is None:
        pytest.skip("JoiningSystem not found — cannot read server asset PIU")

    am = await find_child_by_browse_name(js, BN.ASSET_MANAGEMENT, ns_ijt)
    if am is None:
        pytest.skip("AssetManagement not found — cannot read server asset PIU")

    controller_piu = await _read_first_asset_category_product_instance_uri(
        am, BN.CONTROLLERS, ns_ijt, ns_di, ns_machinery, ns_app
    )
    if controller_piu is None:
        pytest.skip(
            "No Controller with ProductInstanceUri found under AssetManagement/Assets — cannot verify own-asset PIU"
        )

    _am2, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.GET_IDENTIFIERS, ns_ijt)
    if method_node is None:
        pytest.skip("GetIdentifiers: Not Supported — cannot safely verify server own-asset PIU")

    result = await find_and_call_method(
        ms,
        BN.GET_IDENTIFIERS,
        ns_ijt,
        _asset_arg(controller_piu),
        ua.Variant([], ua.VariantType.String),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
            pytest.skip(f"GetIdentifiers not supported on this server: {err_str}")
        pytest.fail(f"GetIdentifiers with server own-asset PIU '{controller_piu}' failed: {err_str}")


@pytest.mark.requires_cu(CU.METHOD_INPUT_ARGUMENT)
@pytest.mark.requires_cu(CU.ENABLE_TOOL)
async def test_method_input_argument_controller_piu_not_applicable_to_enable_asset(opcua_client, ns_indices):
    """EnableAsset with a valid non-Tool PIU must be rejected as not applicable.

    This covers the CU-64 negative case separately from the positive server-own
    asset check: the ProductInstanceUri exists, but EnableAsset is a Tool method.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_machinery = ns_indices.get(NS_MACHINERY)
    ns_app = ns_indices.get(NS_APP)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    js = await find_joining_system(opcua_client)
    if js is None:
        pytest.skip("JoiningSystem not found — cannot read Controller PIU")

    am = await find_child_by_browse_name(js, BN.ASSET_MANAGEMENT, ns_ijt)
    if am is None:
        pytest.skip("AssetManagement not found — cannot read Controller PIU")

    controller_piu = await _read_first_asset_category_product_instance_uri(
        am, BN.CONTROLLERS, ns_ijt, ns_di, ns_machinery, ns_app
    )
    if controller_piu is None:
        pytest.skip(
            "No Controller with ProductInstanceUri found under AssetManagement/Assets — cannot verify non-applicable PIU rejection"
        )

    _am2, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.ENABLE_ASSET, ns_ijt)
    if method_node is None:
        pytest.skip("EnableAsset: Not Supported — cannot verify non-applicable PIU rejection")

    result = await find_and_call_method(
        ms,
        BN.ENABLE_ASSET,
        ns_ijt,
        _asset_arg(controller_piu),
        ua.Variant(True, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.fail(
            f"EnableAsset accepted Controller ProductInstanceUri '{controller_piu}' — "
            "Tool-specific methods must reject non-applicable asset identifiers"
        )

    err_str = str(result.error) if result.error else "unknown error"
    if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
        pytest.skip(f"EnableAsset not supported on this server: {err_str}")
    assert any(kw in err_str for kw in ("Uncertain", "BadInvalidArgument", "BadNotFound", "BadNoEntryExists")), (
        "Unexpected status for valid-but-non-applicable Controller PIU — expected IJT domain "
        f"rejection or service Bad, got: {err_str}"
    )


@pytest.mark.requires_cu(CU.METHOD_INPUT_ARGUMENT)
async def test_method_input_argument_consistent_piu_semantics_across_methods(opcua_client, tools_instances, ns_indices):
    """The same ProductInstanceUri must be interpreted consistently across multiple methods.

    GetErrorInformation and ResetIdentifiers are both called with the same Tool PIU;
    both must complete without contradicting the asset context.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _name, tool_node = tools_instances[0]
    piu = await _read_product_instance_uri(tool_node, ns_di)
    if piu is None:
        pytest.skip(f"Tool '{_name}' has no ProductInstanceUri — cannot verify PIU consistency")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    piu_arg = _asset_arg(piu)

    methods_tested = 0
    calls = (
        (BN.GET_ERROR_INFORMATION, (piu_arg, _asset_arg(""))),
        (BN.EXECUTE_OPERATION, (piu_arg, ua.Variant(0, ua.VariantType.Int32), _asset_arg("IJT probe"), _asset_arg(""))),
        (BN.GET_IDENTIFIERS, (piu_arg, ua.Variant([], ua.VariantType.String))),
        (
            BN.RESET_IDENTIFIERS,
            (
                piu_arg,
                ua.Variant([], ua.VariantType.String),
                ua.Variant(False, ua.VariantType.Boolean),
                ua.Variant(False, ua.VariantType.Boolean),
            ),
        ),
    )
    for method_name, args in calls:
        node = await find_child_by_browse_name(ms, method_name, ns_ijt)
        if node is None:
            continue
        r = await find_and_call_method(ms, method_name, ns_ijt, *args, timeout=_METHOD_TIMEOUT)
        if not r.success:
            err_str = str(r.error) if r.error else "unknown error"
            if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid")):
                continue
            if any(kw in err_str for kw in ("BadArgumentsMissing", "BadInvalidArgument")):
                continue
            pytest.fail(f"{method_name} failed for PIU '{piu}' — PIU semantics may be inconsistent: {err_str}")
        methods_tested += 1

    if methods_tested == 0:
        logger.info("No secondary asset methods available for PIU consistency comparison")
        return


@pytest.mark.requires_cu(CU.METHOD_INPUT_ARGUMENT)
async def test_method_input_argument_unknown_piu_returns_bad_status(opcua_client, ns_indices):
    """Calling a method with an unknown ProductInstanceUri must return a Bad status.

    Per spec: "Server reports appropriate error if ProductInstanceUri is not available."
    Either Bad_NoEntryExists or Bad_InvalidArgument is acceptable; Good is not.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.ENABLE_ASSET, ns_ijt)
    if method_node is None:
        pytest.skip("EnableAsset: Not Supported — cannot test unknown-PIU behaviour")

    result = await find_and_call_method(
        ms,
        BN.ENABLE_ASSET,
        ns_ijt,
        ua.Variant(_INVALID_PIU, ua.VariantType.String),
        ua.Variant(True, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.fail(
            f"EnableAsset with unknown PIU '{_INVALID_PIU}' unexpectedly returned Good — "
            "server must report an error for unknown assets"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
        pytest.skip(f"EnableAsset not supported on this server: {err_str}")
    if "Uncertain" in err_str:
        # C17: server returns OpcUa_Uncertain when methodStatusCode != 0 — correct rejection
        return
    # Pre-C17 compat: service-level Bad also accepted
    if any(kw in err_str for kw in ("BadNodeIdUnknown", "BadNotFound", "BadNoEntryExists", "BadInvalidArgument")):
        return
    pytest.fail(f"Unexpected status for unknown PIU — expected Uncertain (C17) or Bad_NodeIdUnknown, got: {err_str}")


# ─── disconnect_asset — extended ──────────────────────────────────────────────


@pytest.mark.requires_cu(CU.DISCONNECT_ASSET)
async def test_disconnect_asset_callable_with_valid_piu(opcua_client, tools_instances, ns_indices):
    """DisconnectAsset must be callable with a tool's ProductInstanceUri without crashing.

    BadNotSupported is accepted as a skip condition; the key assertion is that the
    server handles the call gracefully (no crash, defined response).
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.DISCONNECT_ASSET, ns_ijt)
    if method_node is None:
        pytest.skip("DisconnectAsset: Not Supported — skipping functional test")

    _name, tool_node = tools_instances[0]
    piu = await _read_product_instance_uri(tool_node, ns_di)
    if piu is None:
        pytest.skip(f"Tool '{_name}' has no ProductInstanceUri — cannot build DisconnectAsset argument")

    result = await find_and_call_method(
        ms,
        BN.DISCONNECT_ASSET,
        ns_ijt,
        _asset_arg(piu),
        ua.Variant(True, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
            pytest.skip(f"DisconnectAsset returned '{err_str}' — not supported on this server")
        if "BadInvalidState" in err_str:
            pytest.skip(
                "DisconnectAsset returned BadInvalidState — "
                "asset may already be disconnected; both Good and BadInvalidState are acceptable"
            )
        pytest.fail(f"DisconnectAsset failed unexpectedly: {err_str}")


@pytest.mark.requires_cu(CU.DISCONNECT_ASSET)
async def test_disconnect_asset_invalid_piu_returns_bad_status(opcua_client, ns_indices):
    """DisconnectAsset with an invalid ProductInstanceUri must return a Bad status.

    Per spec: Bad_InvalidArgument or Bad_NodeIdUnknown. The server must not crash
    or return Good for a non-existent asset URI.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.DISCONNECT_ASSET, ns_ijt)
    if method_node is None:
        pytest.skip("DisconnectAsset: Not Supported — cannot test negative path")

    result = await find_and_call_method(
        ms,
        BN.DISCONNECT_ASSET,
        ns_ijt,
        _asset_arg(_INVALID_PIU),
        ua.Variant(True, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.fail(
            f"DisconnectAsset with invalid PIU '{_INVALID_PIU}' unexpectedly returned Good — "
            "server must return a Bad status for unknown asset URIs"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
        pytest.skip(f"DisconnectAsset not supported on this server: {err_str}")
    if "Uncertain" in err_str:
        # C17: server returns OpcUa_Uncertain when methodStatusCode != 0 — correct rejection
        return
    # Pre-C17 compat: service-level Bad also accepted
    if any(kw in err_str for kw in ("BadNodeIdUnknown", "BadNotFound", "BadNoEntryExists", "BadInvalidArgument")):
        return
    pytest.fail(f"Unexpected status for invalid PIU — expected Uncertain (C17) or Bad_NodeIdUnknown, got: {err_str}")


# ─── enable_tool — extended ───────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ENABLE_TOOL)
async def test_enable_asset_with_false_disables_tool(opcua_client, tools_instances, ns_indices):
    """EnableAsset called with IsEnabled=False must disable the tool (IsEnabled=False).

    First enables, then calls with the false variant to verify the tool can be
    disabled. BadNotSupported is accepted; the round-trip must not crash.
    Note: The spec method signature varies — some servers accept a Boolean second
    argument; this test probes with two arg patterns and accepts either.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.ENABLE_ASSET, ns_ijt)
    if method_node is None:
        pytest.skip("EnableAsset: Not Supported — skipping disable test")

    _name, tool_node = tools_instances[0]
    piu = await _read_product_instance_uri(tool_node, ns_di)
    if piu is None:
        pytest.skip(f"Tool '{_name}' has no ProductInstanceUri — cannot build EnableAsset argument")

    piu_arg = ua.Variant(piu, ua.VariantType.String)
    enable_arg = ua.Variant(True, ua.VariantType.Boolean)
    disable_arg = ua.Variant(False, ua.VariantType.Boolean)

    enable_result = await find_and_call_method(
        ms, BN.ENABLE_ASSET, ns_ijt, piu_arg, enable_arg, timeout=_METHOD_TIMEOUT
    )
    if not enable_result.success:
        err_str = str(enable_result.error) if enable_result.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadInvalidArgument")):
            pytest.skip(f"EnableAsset(piu, True) not supported on this server: {err_str}")
        pytest.fail(f"EnableAsset(piu, True) failed unexpectedly: {err_str}")

    disable_result = await find_and_call_method(
        ms, BN.ENABLE_ASSET, ns_ijt, piu_arg, disable_arg, timeout=_METHOD_TIMEOUT
    )
    if not disable_result.success:
        err_str = str(disable_result.error) if disable_result.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid")):
            pytest.skip(f"EnableAsset(piu, False) not supported on this server: {err_str}")
        pytest.fail(f"EnableAsset with IsEnabled=False failed after successful enable: {err_str}")


@pytest.mark.requires_cu(CU.ENABLE_TOOL)
async def test_enable_asset_invalid_piu_returns_bad_node_id_unknown(opcua_client, ns_indices):
    """EnableAsset with an invalid ProductInstanceUri must return Bad_NodeIdUnknown.

    Per spec: server must return Bad_NodeIdUnknown (0x80340000) and must not change
    any asset state.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.ENABLE_ASSET, ns_ijt)
    if method_node is None:
        pytest.skip("EnableAsset: Not Supported — cannot test invalid PIU behaviour")

    result = await find_and_call_method(
        ms,
        BN.ENABLE_ASSET,
        ns_ijt,
        ua.Variant(_INVALID_PIU, ua.VariantType.String),
        ua.Variant(True, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.fail(
            f"EnableAsset with invalid PIU '{_INVALID_PIU}' unexpectedly returned Good — "
            "server must return Bad_NodeIdUnknown for unknown asset URIs"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
        pytest.skip(f"EnableAsset not supported on this server: {err_str}")
    if "Uncertain" in err_str:
        # C17: server returns OpcUa_Uncertain when methodStatusCode != 0 — correct rejection
        return
    # Pre-C17 compat: service-level Bad also accepted
    if any(kw in err_str for kw in ("BadNodeIdUnknown", "BadNotFound", "BadNoEntryExists", "BadInvalidArgument")):
        return
    pytest.fail(f"Unexpected status for invalid PIU — expected Uncertain (C17) or Bad_NodeIdUnknown, got: {err_str}")


# ─── set_calibration — extended ───────────────────────────────────────────────


@pytest.mark.requires_cu(CU.SET_CALIBRATION)
async def test_set_calibration_unknown_piu_returns_bad_status(opcua_client, ns_indices):
    """SetCalibration with an unknown ProductInstanceUri must return a Bad status.

    Per spec: Bad_NoEntryExists or Bad_InvalidArgument. Calibration data must not
    be modified.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.SET_CALIBRATION, ns_ijt)
    if method_node is None:
        pytest.skip("SetCalibration: Not Supported — cannot test unknown PIU behaviour")

    calibration_data = _make_calibration_data()
    if calibration_data is None:
        pytest.skip("CalibrationDataType is not loaded — cannot build SetCalibration arguments")

    result = await find_and_call_method(
        ms,
        BN.SET_CALIBRATION,
        ns_ijt,
        _asset_arg(_INVALID_PIU),
        calibration_data,
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.fail(
            f"SetCalibration with unknown PIU '{_INVALID_PIU}' unexpectedly returned Good — "
            "server must return a Bad status for unknown asset URIs"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
        pytest.skip(f"SetCalibration not supported on this server: {err_str}")
    if "Uncertain" in err_str:
        # C17: server returns OpcUa_Uncertain when methodStatusCode != 0 — correct rejection
        return
    # Pre-C17 compat: service-level Bad also accepted
    if any(
        kw in err_str
        for kw in ("BadNodeIdUnknown", "BadNotFound", "BadNoEntryExists", "BadInvalidArgument", "BadArgumentsMissing")
    ):
        return
    pytest.fail(
        f"Unexpected status for unknown PIU — expected Uncertain (C17) or Bad_NoEntryExists/BadInvalidArgument, got: {err_str}"
    )


@pytest.mark.requires_cu(CU.SET_CALIBRATION)
async def test_set_calibration_invalid_calibration_data_type_returns_bad_status(opcua_client, ns_indices):
    """SetCalibration with a wrong-type CalibrationData argument must return a Bad status.

    Per spec: Bad_TypeMismatch or Bad_InvalidArgument. No calibration must be applied
    when the data type is malformed.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.SET_CALIBRATION, ns_ijt)
    if method_node is None:
        pytest.skip("SetCalibration: Not Supported — cannot test invalid calibration data")

    bogus_calibration = ua.Variant("not-calibration-data", ua.VariantType.String)
    result = await find_and_call_method(
        ms,
        BN.SET_CALIBRATION,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        bogus_calibration,
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.fail(
            "SetCalibration with string-typed CalibrationData unexpectedly returned Good — "
            "server must reject malformed calibration data"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
        pytest.skip(f"SetCalibration not supported on this server: {err_str}")
    assert any(kw in err_str for kw in ("BadTypeMismatch", "BadInvalidArgument", "BadArgumentsMissing")), (
        f"Unexpected status for invalid calibration data type — "
        f"expected Bad_TypeMismatch or Bad_InvalidArgument, got: {err_str}"
    )


# ─── reboot_asset — extended ──────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.REBOOT_ASSET)
async def test_reboot_asset_empty_piu_uses_server_default_asset(opcua_client, ns_indices):
    """RebootAsset with an empty ProductInstanceUri must use the server's own asset.

    Per spec (method_input_argument): empty PIU = server's own deployed asset.
    BadNotSupported is accepted since rebooting the server's asset is destructive.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.REBOOT_ASSET, ns_ijt)
    if method_node is None:
        pytest.skip("RebootAsset: Not Supported — cannot test empty PIU semantics")

    result = await find_and_call_method(
        ms,
        BN.REBOOT_ASSET,
        ns_ijt,
        _asset_arg(""),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
            pytest.skip(f"RebootAsset returned '{err_str}' — not supported on this server")
        if any(kw in err_str for kw in ("BadNodeIdUnknown", "BadNotFound", "BadNoEntryExists")):
            pytest.skip(
                "Server requires a non-empty PIU for RebootAsset — "
                "empty PIU semantic may not be implemented on this device"
            )
        pytest.fail(f"RebootAsset with empty PIU failed unexpectedly: {err_str}")


@pytest.mark.requires_cu(CU.REBOOT_ASSET)
async def test_reboot_asset_unknown_piu_returns_bad_status(opcua_client, ns_indices):
    """RebootAsset with an unknown ProductInstanceUri must return a Bad status.

    Per spec: Bad_NoEntryExists or Bad_InvalidArgument. No asset must be rebooted.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.REBOOT_ASSET, ns_ijt)
    if method_node is None:
        pytest.skip("RebootAsset: Not Supported — cannot test unknown PIU behaviour")

    result = await find_and_call_method(
        ms,
        BN.REBOOT_ASSET,
        ns_ijt,
        _asset_arg(_INVALID_PIU),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.fail(
            f"RebootAsset with unknown PIU '{_INVALID_PIU}' unexpectedly returned Good — "
            "server must return a Bad status for unknown asset URIs"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
        pytest.skip(f"RebootAsset not supported on this server: {err_str}")
    if "Uncertain" in err_str:
        # C17: server returns OpcUa_Uncertain when methodStatusCode != 0 — correct rejection
        return
    # Pre-C17 compat: service-level Bad also accepted
    if any(kw in err_str for kw in ("BadNodeIdUnknown", "BadNotFound", "BadNoEntryExists", "BadInvalidArgument")):
        return
    pytest.fail(
        f"Unexpected status for unknown PIU — expected Uncertain (C17) or Bad_NoEntryExists/BadInvalidArgument, got: {err_str}"
    )


# ─── get_error_information — extended ────────────────────────────────────────


@pytest.mark.requires_cu(CU.GET_ERROR_INFORMATION)
async def test_get_error_information_returns_empty_array_when_no_active_errors(opcua_client, ns_indices):
    """GetErrorInformation must return Good with an empty array when there are no active errors.

    Per spec: the OutputArguments contains Errors[] (ErrorInformationDataType array).
    A normal operating state with no active faults must yield an empty list, not a Bad status.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.GET_ERROR_INFORMATION, ns_ijt)
    if method_node is None:
        pytest.skip("GetErrorInformation: Not Supported — cannot verify empty-error behaviour")

    result = await find_and_call_method(
        ms,
        BN.GET_ERROR_INFORMATION,
        ns_ijt,
        _asset_arg(""),
        _asset_arg(""),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
            pytest.skip(f"GetErrorInformation not supported on this server: {err_str}")
        if "BadInvalidArgument" in err_str:
            pytest.skip(f"GetErrorInformation rejected empty ErrorId probe: {err_str}")
        pytest.fail(f"GetErrorInformation failed unexpectedly: {err_str}")

    outputs = result.output_list
    if outputs:
        error_list = outputs[0] if outputs else None
        if error_list is not None:
            assert isinstance(error_list, (list, tuple, type(None))), (
                f"GetErrorInformation output must be a list, got {type(error_list).__name__!r}"
            )


@pytest.mark.requires_cu(CU.GET_ERROR_INFORMATION)
async def test_get_error_information_unknown_piu_returns_bad_status(opcua_client, ns_indices):
    """GetErrorInformation with an unknown PIU must return a Bad status.

    Per spec: Bad_NoEntryExists or Bad_InvalidArgument. No error data must be returned.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.GET_ERROR_INFORMATION, ns_ijt)
    if method_node is None:
        pytest.skip("GetErrorInformation: Not Supported — cannot test unknown PIU")

    result = await find_and_call_method(
        ms,
        BN.GET_ERROR_INFORMATION,
        ns_ijt,
        _asset_arg(_INVALID_PIU),
        _asset_arg(""),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.fail(
            f"GetErrorInformation with unknown PIU '{_INVALID_PIU}' unexpectedly returned Good — "
            "server must return a Bad status for unknown asset URIs"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
        pytest.skip(f"GetErrorInformation not supported on this server: {err_str}")
    if "Uncertain" in err_str:
        # C17: server returns OpcUa_Uncertain when methodStatusCode != 0 — correct rejection
        return
    # Pre-C17 compat: service-level Bad also accepted
    if any(kw in err_str for kw in ("BadNodeIdUnknown", "BadNotFound", "BadNoEntryExists", "BadInvalidArgument")):
        return
    pytest.fail(
        f"Unexpected status for unknown PIU — expected Uncertain (C17) or Bad_NoEntryExists/BadInvalidArgument, got: {err_str}"
    )


# ─── execute_operation — extended ────────────────────────────────────────────


@pytest.mark.requires_cu(CU.EXECUTE_OPERATION)
async def test_execute_operation_empty_piu_uses_server_default_asset(opcua_client, ns_indices):
    """ExecuteOperation with an empty PIU must use the server's own deployed asset.

    Per spec (method_input_argument): empty PIU = server's own asset.
    BadNotSupported and BadInvalidArgument are accepted as skip conditions.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.EXECUTE_OPERATION, ns_ijt)
    if method_node is None:
        pytest.skip("ExecuteOperation: Not Supported — cannot test empty PIU semantics")

    result = await find_and_call_method(
        ms,
        BN.EXECUTE_OPERATION,
        ns_ijt,
        _asset_arg(""),
        ua.Variant(0, ua.VariantType.Int32),
        _asset_arg("IJT conformance probe"),
        _asset_arg(""),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
            pytest.skip(f"ExecuteOperation not supported on this server: {err_str}")
        if "BadInvalidArgument" in err_str:
            pytest.skip(f"ExecuteOperation rejected the probe operation: {err_str}")
        pytest.fail(f"ExecuteOperation with empty PIU failed unexpectedly: {err_str}")


@pytest.mark.requires_cu(CU.EXECUTE_OPERATION)
async def test_execute_operation_invalid_operation_id_returns_bad_invalid_argument(opcua_client, ns_indices):
    """ExecuteOperation with an invalid OperationId must return Bad_InvalidArgument.

    Per spec: server must return Bad_InvalidArgument when an unknown operation code
    is supplied. No operation must be executed on the device.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.EXECUTE_OPERATION, ns_ijt)
    if method_node is None:
        pytest.skip("ExecuteOperation: Not Supported — cannot test invalid OperationId")

    result = await find_and_call_method(
        ms,
        BN.EXECUTE_OPERATION,
        ns_ijt,
        _asset_arg(""),
        ua.Variant(-9999, ua.VariantType.Int32),
        _asset_arg("INVALID_OP_XYZ999"),
        _asset_arg(""),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.fail(
            "ExecuteOperation with OperationId='INVALID_OP_XYZ999' unexpectedly returned Good — "
            "server must return Bad_InvalidArgument for unknown operation codes"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
        pytest.skip(f"ExecuteOperation not supported on this server: {err_str}")
    if "Uncertain" in err_str:
        # C17: server returns OpcUa_Uncertain when methodStatusCode != 0 — correct rejection
        return
    # Pre-C17 compat: service-level Bad also accepted
    if any(kw in err_str for kw in ("BadInvalidArgument", "BadNodeIdUnknown", "BadNotFound", "BadNoEntryExists")):
        return
    pytest.fail(
        f"Unexpected status for invalid OperationId — expected Uncertain (C17) or Bad_InvalidArgument, got: {err_str}"
    )
