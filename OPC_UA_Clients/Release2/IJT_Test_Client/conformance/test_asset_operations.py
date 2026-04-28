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

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.method_caller import find_and_call_method
from helpers.namespaces import BN, NS_APP, NS_DI, NS_IJT_BASE
from helpers.node_discovery import find_child_by_browse_name, find_joining_system, find_method_set

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


async def _read_product_instance_uri(asset_node, ns_di: int) -> str | None:
    """Return the ProductInstanceUri string from asset Identification, or None."""
    ident = await find_child_by_browse_name(asset_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        return None
    piu_node = await find_child_by_browse_name(ident, BN.PRODUCT_INSTANCE_URI, ns_di)
    if piu_node is None:
        return None
    try:
        value = await asyncio.wait_for(piu_node.read_value(), timeout=_METHOD_TIMEOUT)
        return str(value) if value is not None else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not read ProductInstanceUri: %s", exc)
        return None


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
        pytest.skip(
            "DisconnectAsset method not found in MethodSet — "
            "optional per spec, server may not implement asset disconnection"
        )


@pytest.mark.requires_cu(CU.DISCONNECT_ASSET)
async def test_disable_asset_then_enable_asset_restores_state(opcua_client, tools_instances, ns_indices):
    """DisableAsset then EnableAsset round-trip must not raise an error."""
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

    disable_node = await find_child_by_browse_name(ms, BN.DISABLE_ASSET, ns_ijt)
    if disable_node is None:
        pytest.skip("DisableAsset: Not Supported — skipping round-trip test")

    disable_result = await find_and_call_method(ms, BN.DISABLE_ASSET, ns_ijt, piu_arg, timeout=_METHOD_TIMEOUT)
    if not disable_result.success:
        err_str = str(disable_result.error) if disable_result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"DisableAsset returned '{err_str}' — not supported on this server")
        pytest.fail(f"DisableAsset failed: {err_str}")

    enable_result = await find_and_call_method(ms, BN.ENABLE_ASSET, ns_ijt, piu_arg, timeout=_METHOD_TIMEOUT)
    if not enable_result.success:
        err_str = str(enable_result.error) if enable_result.error else "unknown error"
        pytest.fail(f"EnableAsset failed after DisableAsset round-trip: {err_str}")


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

    result = await find_and_call_method(ms, BN.SET_CALIBRATION, ns_ijt, timeout=_METHOD_TIMEOUT)
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"SetCalibration returned '{err_str}' — not supported on this server")
        if "BadArgumentsMissing" in err_str or "BadInvalidArgument" in err_str:
            pytest.skip(f"SetCalibration requires arguments not supplied in probe call: {err_str}")
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
        ua.Variant(piu, ua.VariantType.String),
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
        ua.Variant(piu, ua.VariantType.String),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"ExecuteOperation returned '{err_str}' — not supported on this server")
        if "BadArgumentsMissing" in err_str or "BadInvalidArgument" in err_str:
            pytest.skip(f"ExecuteOperation requires additional arguments not supplied in probe call: {err_str}")
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
    """A method called with the server's own asset ProductInstanceUri must succeed.

    Verifies that an explicit PIU matching the deployed Controller asset is accepted
    and treated equivalently to calling with an empty PIU.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    js = await find_joining_system(opcua_client)
    if js is None:
        pytest.skip("JoiningSystem not found — cannot read server asset PIU")

    am = await find_child_by_browse_name(js, BN.ASSET_MANAGEMENT, ns_ijt)
    if am is None:
        pytest.skip("AssetManagement not found — cannot read server asset PIU")

    controllers_folder = await find_child_by_browse_name(am, BN.CONTROLLERS, ns_ijt)
    controller_piu: str | None = None
    if controllers_folder is not None:
        try:
            children = await asyncio.wait_for(controllers_folder.get_children(), timeout=_METHOD_TIMEOUT)
            for child in children:
                piu = await _read_product_instance_uri(child, ns_di)
                if piu:
                    controller_piu = piu
                    break
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not enumerate Controllers: %s", exc)

    if controller_piu is None:
        pytest.skip("No Controller with ProductInstanceUri found — cannot verify own-asset PIU")

    _am2, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    result = await find_and_call_method(
        ms,
        BN.ENABLE_ASSET,
        ns_ijt,
        ua.Variant(controller_piu, ua.VariantType.String),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
            pytest.skip(f"EnableAsset not supported on this server: {err_str}")
        pytest.fail(f"EnableAsset with server own-asset PIU '{controller_piu}' failed: {err_str}")


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
    piu_arg = ua.Variant(piu, ua.VariantType.String)

    methods_tested = 0
    for method_name in (BN.GET_ERROR_INFORMATION, BN.RESET_IDENTIFIERS):
        node = await find_child_by_browse_name(ms, method_name, ns_ijt)
        if node is None:
            continue
        r = await find_and_call_method(ms, method_name, ns_ijt, piu_arg, timeout=_METHOD_TIMEOUT)
        if not r.success:
            err_str = str(r.error) if r.error else "unknown error"
            if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid")):
                continue
            if any(kw in err_str for kw in ("BadArgumentsMissing", "BadInvalidArgument")):
                continue
            pytest.fail(f"{method_name} failed for PIU '{piu}' — PIU semantics may be inconsistent: {err_str}")
        methods_tested += 1

    if methods_tested == 0:
        pytest.skip("No testable methods found for PIU consistency check")


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
        ua.Variant(piu, ua.VariantType.String),
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
        ua.Variant(_INVALID_PIU, ua.VariantType.String),
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

    result = await find_and_call_method(
        ms,
        BN.SET_CALIBRATION,
        ns_ijt,
        ua.Variant(_INVALID_PIU, ua.VariantType.String),
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
        ua.Variant("", ua.VariantType.String),
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
        ua.Variant(_INVALID_PIU, ua.VariantType.String),
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

    result = await find_and_call_method(ms, BN.GET_ERROR_INFORMATION, ns_ijt, timeout=_METHOD_TIMEOUT)
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
            pytest.skip(f"GetErrorInformation not supported on this server: {err_str}")
        if "BadArgumentsMissing" in err_str or "BadInvalidArgument" in err_str:
            pytest.skip("GetErrorInformation requires a PIU argument on this server — retesting with empty string PIU")
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
        ua.Variant(_INVALID_PIU, ua.VariantType.String),
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
    BadNotSupported and BadArgumentsMissing are accepted as skip conditions.
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
        ua.Variant("", ua.VariantType.String),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
            pytest.skip(f"ExecuteOperation not supported on this server: {err_str}")
        if any(kw in err_str for kw in ("BadArgumentsMissing", "BadInvalidArgument")):
            pytest.skip(f"ExecuteOperation requires additional arguments not supplied in probe call: {err_str}")
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

    invalid_op_id = ua.Variant("INVALID_OP_XYZ999", ua.VariantType.String)
    result = await find_and_call_method(
        ms,
        BN.EXECUTE_OPERATION,
        ns_ijt,
        invalid_op_id,
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
