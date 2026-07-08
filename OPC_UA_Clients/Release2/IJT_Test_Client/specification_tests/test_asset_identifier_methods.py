"""
specification tests for asset identifier methods — OPC 40450-1 IJT Base.

Covers the following conformance units:

send_identifiers
    The Server supports the SendIdentifiers method on AssetManagement.

get_identifiers
    The Server supports the GetIdentifiers method on AssetManagement.

reset_identifiers
    The Server supports the ResetIdentifiers method on AssetManagement.

(SendTextIdentifiers is a convenience variant of SendIdentifiers using plain
TrimmedString values instead of structured Identifier objects.)

All identifier methods live on AssetManagement MethodSet (IJT Base namespace),
not on individual asset MethodSets.

Call contract: the server must respond at the transport level.  OPC UA status
errors (ua.UaStatusCodeError) are acceptable — they indicate argument rejection,
not a crash or missing method.
"""

from __future__ import annotations

import asyncio
import logging

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.method_signature import ASSET_MANAGEMENT_METHOD_INPUTS, assert_input_argument_names
from helpers.namespaces import BN, NS_APP, NS_DI, NS_IJT_BASE
from helpers.node_discovery import (
    find_child_by_browse_name,
    find_joining_system,
    find_method_set,
    read_tool_product_instance_uri,
)

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

_METHOD_TIMEOUT = 15  # seconds per method call


# ─── helpers ──────────────────────────────────────────────────────────────────


async def _get_identifier_method_set(client, ns_ijt: int, ns_di: int, ns_app: int | None = None):
    """Re-discover AssetManagement MethodSet on a fresh client connection.

    Returns (asset_management_node, method_set_node).
    Skips the test if either is not present.
    """
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found")
    am = await find_child_by_browse_name(js, BN.ASSET_MANAGEMENT, ns_ijt)
    if am is None:
        pytest.skip("AssetManagement not found")
    ms = await find_method_set(am, ns_di, ns_ijt, ns_app)
    if ms is None:
        pytest.skip(
            "IJT spec (OPC 40450-1) requires a MethodSet child under AssetManagement — "
            "this server omits it (non-conformant)"
        )
    return am, ms


async def _get_tool_piu(client, ns_ijt: int, ns_di: int) -> str:
    """Return the ProductInstanceUri of the first available tool, or empty string."""
    piu = await read_tool_product_instance_uri(client, ns_ijt, ns_di)
    return piu or ""


async def _find_identifier_method(ms_node, method_name: str, ns_ijt: int):
    return await find_child_by_browse_name(ms_node, method_name, ns_ijt)


def _extract_list(result) -> list:
    if result is None:
        return []
    payload = result[0] if isinstance(result, (list, tuple)) and result else result
    if payload is None:
        return []
    if isinstance(payload, (list, tuple)):
        return list(payload)
    if hasattr(payload, "__iter__") and not isinstance(payload, (str, bytes, bytearray)):
        return list(payload)
    return [payload]


# ─── method presence (structure layer) ────────────────────────────────────────


@pytest.mark.requires_cu(CU.SEND_IDENTIFIERS)
@pytest.mark.parametrize(
    "method_name",
    [
        BN.SEND_IDENTIFIERS,
        BN.SEND_TEXT_IDENTIFIERS,
    ],
)
async def test_send_identifier_methods_present_in_method_set(method_name, asset_management, ns_indices):
    """SendIdentifiers and SendTextIdentifiers must be present in AssetManagement MethodSet."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None or ns_di is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_ijt, ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip("AssetManagement MethodSet not found")
    method = await _find_identifier_method(ms, method_name, ns_ijt)
    assert method is not None, f"Method '{method_name}' (IJT Base ns) not found in AssetManagement MethodSet"
    await assert_input_argument_names(
        method,
        ASSET_MANAGEMENT_METHOD_INPUTS[method_name],
        method_name=method_name,
    )


@pytest.mark.requires_cu(CU.GET_IDENTIFIERS)
async def test_get_identifiers_method_present_in_method_set(asset_management, ns_indices):
    """GetIdentifiers must be present in AssetManagement MethodSet."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None or ns_di is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_ijt, ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip("AssetManagement MethodSet not found")
    method = await _find_identifier_method(ms, BN.GET_IDENTIFIERS, ns_ijt)
    assert method is not None, "GetIdentifiers not found in AssetManagement MethodSet"
    await assert_input_argument_names(
        method,
        ASSET_MANAGEMENT_METHOD_INPUTS[BN.GET_IDENTIFIERS],
        method_name=BN.GET_IDENTIFIERS,
    )


@pytest.mark.requires_cu(CU.RESET_IDENTIFIERS)
async def test_reset_identifiers_method_present_in_method_set(asset_management, ns_indices):
    """ResetIdentifiers must be present in AssetManagement MethodSet."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None or ns_di is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_ijt, ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip("AssetManagement MethodSet not found")
    method = await _find_identifier_method(ms, BN.RESET_IDENTIFIERS, ns_ijt)
    assert method is not None, "ResetIdentifiers not found in AssetManagement MethodSet"
    await assert_input_argument_names(
        method,
        ASSET_MANAGEMENT_METHOD_INPUTS[BN.RESET_IDENTIFIERS],
        method_name=BN.RESET_IDENTIFIERS,
    )


# ─── GetIdentifiers ───────────────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.GET_IDENTIFIERS)
async def test_get_identifiers_callable(opcua_client, ns_indices):
    """GetIdentifiers must respond without a Python exception."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None or ns_di is None:
        pytest.skip("Required namespaces not registered")
    _, ms = await _get_identifier_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))
    method = await _find_identifier_method(ms, BN.GET_IDENTIFIERS, ns_ijt)
    if method is None:
        pytest.skip("GetIdentifiers not found in AssetManagement MethodSet")
    piu = await _get_tool_piu(opcua_client, ns_ijt, ns_di)
    if not piu:
        pytest.skip("No tool ProductInstanceUri available")
    try:
        await asyncio.wait_for(
            ms.call_method(
                method.nodeid,
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant([], ua.VariantType.String),
            ),
            timeout=_METHOD_TIMEOUT,
        )
    except ua.UaStatusCodeError as exc:
        pytest.fail(f"GetIdentifiers rejected valid-call shape unexpectedly: {exc}")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"GetIdentifiers raised unexpected exception: {type(exc).__name__}: {exc}")


@pytest.mark.requires_cu(CU.GET_IDENTIFIERS)
async def test_get_identifiers_returns_list_or_none(opcua_client, ns_indices):
    """GetIdentifiers return value must be a list, tuple, or None."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None or ns_di is None:
        pytest.skip("Required namespaces not registered")
    _, ms = await _get_identifier_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))
    method = await _find_identifier_method(ms, BN.GET_IDENTIFIERS, ns_ijt)
    if method is None:
        pytest.skip("GetIdentifiers not found in AssetManagement MethodSet")
    piu = await _get_tool_piu(opcua_client, ns_ijt, ns_di)
    if not piu:
        pytest.skip("No tool ProductInstanceUri available")
    try:
        result = await asyncio.wait_for(
            ms.call_method(
                method.nodeid,
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant([], ua.VariantType.String),
            ),
            timeout=_METHOD_TIMEOUT,
        )
        entities = _extract_list(result)
        assert isinstance(entities, list), "GetIdentifiers output must be list-like"
    except ua.UaStatusCodeError as exc:
        pytest.fail(f"GetIdentifiers rejected valid-call shape unexpectedly: {exc}")


# ─── ResetIdentifiers ─────────────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.RESET_IDENTIFIERS)
async def test_reset_identifiers_callable(opcua_client, ns_indices):
    """ResetIdentifiers must respond without a Python exception."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None or ns_di is None:
        pytest.skip("Required namespaces not registered")
    _, ms = await _get_identifier_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))
    method = await _find_identifier_method(ms, BN.RESET_IDENTIFIERS, ns_ijt)
    if method is None:
        pytest.skip("ResetIdentifiers not found in AssetManagement MethodSet")
    piu = await _get_tool_piu(opcua_client, ns_ijt, ns_di)
    if not piu:
        pytest.skip("No tool ProductInstanceUri available")
    try:
        await asyncio.wait_for(
            ms.call_method(
                method.nodeid,
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant([], ua.VariantType.String),
                ua.Variant(False, ua.VariantType.Boolean),
                ua.Variant(False, ua.VariantType.Boolean),
            ),
            timeout=_METHOD_TIMEOUT,
        )
    except ua.UaStatusCodeError as exc:
        pytest.fail(f"ResetIdentifiers rejected valid-call shape unexpectedly: {exc}")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"ResetIdentifiers raised unexpected exception: {type(exc).__name__}: {exc}")


@pytest.mark.requires_cu(CU.RESET_IDENTIFIERS)
async def test_reset_identifiers_returns_status_output(opcua_client, ns_indices):
    """ResetIdentifiers output must include at least 2 arguments (StatusCode, StatusMessage)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None or ns_di is None:
        pytest.skip("Required namespaces not registered")
    _, ms = await _get_identifier_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))
    method = await _find_identifier_method(ms, BN.RESET_IDENTIFIERS, ns_ijt)
    if method is None:
        pytest.skip("ResetIdentifiers not found in AssetManagement MethodSet")
    piu = await _get_tool_piu(opcua_client, ns_ijt, ns_di)
    if not piu:
        pytest.skip("No tool ProductInstanceUri available")
    try:
        result = await asyncio.wait_for(
            ms.call_method(
                method.nodeid,
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant([], ua.VariantType.String),
                ua.Variant(False, ua.VariantType.Boolean),
                ua.Variant(False, ua.VariantType.Boolean),
            ),
            timeout=_METHOD_TIMEOUT,
        )
        if isinstance(result, (list, tuple)):
            assert len(result) >= 2, (
                "ResetIdentifiers must return at least 2 output arguments "
                f"(StatusCode, StatusMessage), got {len(result)}"
            )
    except ua.UaStatusCodeError as exc:
        pytest.fail(f"ResetIdentifiers rejected valid-call shape unexpectedly: {exc}")


# ─── SendTextIdentifiers ──────────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.SEND_IDENTIFIERS)
async def test_send_text_identifiers_callable(opcua_client, ns_indices):
    """SendTextIdentifiers must respond without a Python exception."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None or ns_di is None:
        pytest.skip("Required namespaces not registered")
    _, ms = await _get_identifier_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))
    method = await _find_identifier_method(ms, BN.SEND_TEXT_IDENTIFIERS, ns_ijt)
    if method is None:
        pytest.skip("SendTextIdentifiers not found in AssetManagement MethodSet")
    piu = await _get_tool_piu(opcua_client, ns_ijt, ns_di)
    try:
        await asyncio.wait_for(
            ms.call_method(
                method.nodeid,
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant(["CONFORMANCE_TEST_ID"], ua.VariantType.String),
            ),
            timeout=_METHOD_TIMEOUT,
        )
    except ua.UaStatusCodeError:
        pass  # server-side rejection is acceptable; what matters is the method was reached
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"SendTextIdentifiers raised unexpected exception: {type(exc).__name__}: {exc}")


# ─── Send → Get → Reset round-trip ───────────────────────────────────────────


@pytest.mark.requires_cu(CU.SEND_IDENTIFIERS)
@pytest.mark.requires_cu(CU.GET_IDENTIFIERS)
@pytest.mark.requires_cu(CU.RESET_IDENTIFIERS)
async def test_send_text_then_get_then_reset_round_trip(opcua_client, ns_indices):
    """Round-trip: SendTextIdentifiers → GetIdentifiers → ResetIdentifiers.

    Verifies that an identifier sent via SendTextIdentifiers appears in
    GetIdentifiers and is absent after ResetIdentifiers.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None or ns_di is None:
        pytest.skip("Required namespaces not registered")
    _, ms = await _get_identifier_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    send_m = await _find_identifier_method(ms, BN.SEND_TEXT_IDENTIFIERS, ns_ijt)
    get_m = await _find_identifier_method(ms, BN.GET_IDENTIFIERS, ns_ijt)
    reset_m = await _find_identifier_method(ms, BN.RESET_IDENTIFIERS, ns_ijt)

    if not all([send_m, get_m, reset_m]):
        pytest.skip("One or more identifier methods missing — cannot run round-trip test")

    piu = await _get_tool_piu(opcua_client, ns_ijt, ns_di)
    test_id = "ROUND_TRIP_CONFORMANCE_001"

    # Send
    try:
        await asyncio.wait_for(
            ms.call_method(
                send_m.nodeid,
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant([test_id], ua.VariantType.String),
            ),
            timeout=_METHOD_TIMEOUT,
        )
    except ua.UaStatusCodeError as exc:
        pytest.fail(f"SendTextIdentifiers rejected round-trip test identifier: {exc}")
        return

    # Get — identifier should be present
    try:
        get_result = await asyncio.wait_for(
            ms.call_method(
                get_m.nodeid,
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant([test_id], ua.VariantType.String),
            ),
            timeout=_METHOD_TIMEOUT,
        )
    except ua.UaStatusCodeError as exc:
        pytest.fail(f"GetIdentifiers rejected call after SendTextIdentifiers: {exc}")
        return

    present_ids = _extract_list(get_result)

    # Server returns EntityDataType objects — extract all string fields to find the ID.
    # str(item) gives the repr; check if test_id appears in any attribute or the repr itself.
    def _id_in_item(item: object, needle: str) -> bool:
        for attr in ("Name", "EntityId", "EntityOriginId"):
            val = getattr(item, attr, None)
            if val == needle:
                return True
        return needle in str(item)

    assert any(_id_in_item(item, test_id) for item in present_ids), (
        f"GetIdentifiers after SendTextIdentifiers must return {test_id!r}; got {present_ids}"
    )

    # Reset
    try:
        await asyncio.wait_for(
            ms.call_method(
                reset_m.nodeid,
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant([test_id], ua.VariantType.String),
                ua.Variant(False, ua.VariantType.Boolean),
                ua.Variant(False, ua.VariantType.Boolean),
            ),
            timeout=_METHOD_TIMEOUT,
        )
    except ua.UaStatusCodeError as exc:
        pytest.fail(f"ResetIdentifiers rejected call during round-trip: {exc}")
        return

    # Get again — identifier must be absent
    try:
        post_result = await asyncio.wait_for(
            ms.call_method(
                get_m.nodeid,
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant([test_id], ua.VariantType.String),
            ),
            timeout=_METHOD_TIMEOUT,
        )
    except ua.UaStatusCodeError as exc:
        pytest.fail(f"GetIdentifiers rejected call after ResetIdentifiers: {exc}")
        return

    post_entities = _extract_list(post_result)
    for entity in post_entities:
        text = str(entity)
        assert test_id not in text, f"ResetIdentifiers did not clear test identifier '{test_id}'"
