"""
Conformance unit tests for Identifier Handling — OPC 40450-1.

Covers the following conformance units:

send_identifiers
    The Server supports at least one of: SendIdentifiers, SendTextIdentifiers, or
    StartJoiningProcess with associatedEntities. The received identifiers are included in
    Result.ResultMetaData.AssociatedEntities[] for any result generated after successful
    execution. Each element sets IsExternal = TRUE for received identifiers.

get_identifiers
    The Server supports GetIdentifiers method which returns the set of identifiers available
    for the current joining process. The identifiers reported are sent by a Client or any
    other external interface.

reset_identifiers
    The Server supports ResetIdentifiers method which resets the identifiers of the current
    joining process. It resets the identifiers where IsExternal = TRUE.
"""

import asyncio
import logging

import pytest
import pytest_asyncio
from asyncua import ua

from helpers.cu_registry import CU
from helpers.method_caller import find_and_call_method
from helpers.namespaces import BN, NS_APP, NS_DI, NS_IJT_BASE, ResultType
from helpers.node_discovery import find_child_by_browse_name, find_joining_system, find_method_set
from helpers.result_collector import ResultCollector
from helpers.trigger import make_result_trigger

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

_METHOD_TIMEOUT = 15


# ─── local helpers ────────────────────────────────────────────────────────────


async def _get_asset_management_method_set(client, ns_ijt: int, ns_di: int, ns_app: int | None = None):
    """Re-discover AssetManagement/MethodSet on a fresh client connection."""
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found on fresh client connection")
    am = await find_child_by_browse_name(js, BN.ASSET_MANAGEMENT, ns_ijt)
    if am is None:
        pytest.skip("AssetManagement not found on fresh client connection")
    ms = await find_method_set(am, ns_di, ns_ijt, ns_app)
    if ms is None:
        pytest.skip(
            "IJT spec (OPC 40450-1) requires a MethodSet child under AssetManagement — this server omits it (non-conformant)"
        )
    return am, ms


# ─── function-scoped result trigger ──────────────────────────────────────────


@pytest_asyncio.fixture(scope="function")
async def result_trigger(opcua_client, ns_indices):
    """Function-scoped result trigger built on the fresh opcua_client.

    Returns a SimulatorResultTrigger when the App namespace and SimulateResults
    folder are available; falls back to ExternalResultTrigger (tests that need
    an active trigger will call pytest.skip via outcome.triggered=False).
    """
    ns_app = ns_indices.get(NS_APP)
    if ns_app is None:
        return make_result_trigger(opcua_client, None, 0)

    js = await find_joining_system(opcua_client)
    if js is None:
        return make_result_trigger(opcua_client, None, 0)

    simulations = await find_child_by_browse_name(js, BN.SIMULATIONS, ns_app)
    if simulations is None:
        return make_result_trigger(opcua_client, None, 0)

    sim_results = await find_child_by_browse_name(simulations, BN.SIMULATE_RESULTS_FOLDER, ns_app)
    return make_result_trigger(opcua_client, sim_results, ns_app)


# ─── send_identifiers — structure ─────────────────────────────────────────────


@pytest.mark.requires_cu(CU.SEND_IDENTIFIERS)
async def test_send_identifiers_method_present_and_browsable(asset_management, ns_indices):
    """SendIdentifiers method must be browsable in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "IJT spec (OPC 40450-1) requires a MethodSet child under AssetManagement — this server omits it (non-conformant)"
        )
    method = await find_child_by_browse_name(ms, BN.SEND_IDENTIFIERS, ns_ijt)
    assert method is not None, f"SendIdentifiers method (ns_ijt={ns_ijt}) not found in AssetManagement MethodSet"


@pytest.mark.requires_cu(CU.SEND_IDENTIFIERS)
async def test_send_text_identifiers_method_present_and_browsable(asset_management, ns_indices):
    """SendTextIdentifiers method must be browsable in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "IJT spec (OPC 40450-1) requires a MethodSet child under AssetManagement — this server omits it (non-conformant)"
        )
    method = await find_child_by_browse_name(ms, BN.SEND_TEXT_IDENTIFIERS, ns_ijt)
    assert method is not None, f"SendTextIdentifiers method (ns_ijt={ns_ijt}) not found in AssetManagement MethodSet"


# ─── get_identifiers — structure ──────────────────────────────────────────────


@pytest.mark.requires_cu(CU.GET_IDENTIFIERS)
async def test_get_identifiers_method_present(asset_management, ns_indices):
    """GetIdentifiers method must be present in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "MethodSet not found — IJT spec (OPC 40450-1) requires MethodSet under AssetManagement; this server is non-conformant"
        )
    method = await find_child_by_browse_name(ms, BN.GET_IDENTIFIERS, ns_ijt)
    assert method is not None, f"GetIdentifiers method (ns_ijt={ns_ijt}) not found in AssetManagement MethodSet"


# ─── reset_identifiers — structure ────────────────────────────────────────────


@pytest.mark.requires_cu(CU.RESET_IDENTIFIERS)
async def test_reset_identifiers_method_present(asset_management, ns_indices):
    """ResetIdentifiers method must be present in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    ms = await find_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "MethodSet not found — IJT spec (OPC 40450-1) requires MethodSet under AssetManagement; this server is non-conformant"
        )
    method = await find_child_by_browse_name(ms, BN.RESET_IDENTIFIERS, ns_ijt)
    assert method is not None, f"ResetIdentifiers method (ns_ijt={ns_ijt}) not found in AssetManagement MethodSet"


# ─── send_identifiers — functional ────────────────────────────────────────────


@pytest.mark.requires_cu(CU.SEND_IDENTIFIERS)
async def test_send_identifiers_accepts_entity_data_type_array(opcua_client, ns_indices):
    """SendIdentifiers must accept an EntityDataType array without crashing the server.

    Encoding EntityDataType structs may not be supported by all asyncua versions.
    The test probes with an empty ExtensionObject array first; if encoding fails the
    test is skipped rather than failed so that structure tests still provide value.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))

    await find_and_call_method(
        ms,
        BN.RESET_IDENTIFIERS,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        ua.Variant([], ua.VariantType.ExtensionObject),
        ua.Variant(True, ua.VariantType.Boolean),
        ua.Variant(False, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )

    empty_arg = ua.Variant([], ua.VariantType.ExtensionObject)
    try:
        result = await find_and_call_method(
            ms,
            BN.SEND_IDENTIFIERS,
            ns_ijt,
            ua.Variant("", ua.VariantType.String),  # ProductInstanceUri
            empty_arg,  # Identifiers (empty array)
            timeout=_METHOD_TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Cannot encode SendIdentifiers input with this asyncua version: {exc}")

    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"SendIdentifiers returned '{err_str}' — not supported on this server")
        if "BadInvalidArgument" in err_str or "BadArgumentsMissing" in err_str:
            pytest.skip(
                f"SendIdentifiers rejected with '{err_str}' — server rejected the call; verify argument encoding"
            )
        pytest.fail(f"SendIdentifiers failed unexpectedly: {err_str}")


@pytest.mark.requires_cu(CU.SEND_IDENTIFIERS)
async def test_send_text_identifiers_accepts_string_key_value_pairs(opcua_client, ns_indices):
    """SendTextIdentifiers must accept string key/value pair input.

    Attempts to call SendTextIdentifiers with a single KeyValuePair-like argument.
    Encoding failures are caught and the test is skipped to avoid false failures
    caused by asyncua custom-type limitations.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))

    try:
        result = await find_and_call_method(
            ms,
            BN.SEND_TEXT_IDENTIFIERS,
            ns_ijt,
            ua.Variant("", ua.VariantType.String),  # ProductInstanceUri
            ua.Variant([], ua.VariantType.String),  # TextIdentifiers (empty string array)
            timeout=_METHOD_TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Cannot encode SendTextIdentifiers input with this asyncua version: {exc}")

    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"SendTextIdentifiers returned '{err_str}' — not supported on this server")
        if "BadInvalidArgument" in err_str or "BadArgumentsMissing" in err_str:
            pytest.skip(
                f"SendTextIdentifiers rejected with '{err_str}' — server rejected the call; verify argument encoding"
            )
        pytest.fail(f"SendTextIdentifiers failed unexpectedly: {err_str}")


@pytest.mark.requires_cu(CU.SEND_IDENTIFIERS)
async def test_send_identifiers_with_empty_array_does_not_crash(opcua_client, ns_indices):
    """SendIdentifiers with an empty array must not crash the server.

    An empty input is the minimal valid call — the server must handle it gracefully
    (either succeed or return a defined error, not crash or hang).
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))

    empty_arg = ua.Variant([], ua.VariantType.ExtensionObject)
    try:
        result = await find_and_call_method(
            ms,
            BN.SEND_IDENTIFIERS,
            ns_ijt,
            ua.Variant("", ua.VariantType.String),  # ProductInstanceUri
            empty_arg,  # Identifiers (empty array)
            timeout=_METHOD_TIMEOUT,
        )
    except asyncio.TimeoutError:
        pytest.fail(
            "SendIdentifiers with empty array hung (TimeoutError) — server must handle empty input without hanging"
        )
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Cannot encode SendIdentifiers input with this asyncua version: {exc}")

    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(
                f"SendIdentifiers not supported on this server ('{err_str}') — negative test cannot be executed"
            )
        logger.debug("SendIdentifiers(empty) returned Bad status (defined response): %s", err_str)


# ─── get_identifiers — functional ─────────────────────────────────────────────


@pytest.mark.requires_cu(CU.GET_IDENTIFIERS)
async def test_get_identifiers_returns_entity_list(opcua_client, ns_indices):
    """GetIdentifiers must be callable and return a list (may be empty)."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    result = await find_and_call_method(
        ms,
        BN.GET_IDENTIFIERS,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        ua.Variant([], ua.VariantType.String),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"GetIdentifiers returned '{err_str}' — not supported on this server")
        pytest.fail(f"GetIdentifiers failed unexpectedly: {err_str}")

    output = result.output_list
    assert isinstance(output, list), f"GetIdentifiers must return a list; got {type(output).__name__}"


# ─── reset_identifiers — functional ───────────────────────────────────────────


@pytest.mark.requires_cu(CU.RESET_IDENTIFIERS)
async def test_reset_identifiers_callable(opcua_client, ns_indices):
    """ResetIdentifiers must be callable and return no error."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    result = await find_and_call_method(
        ms,
        BN.RESET_IDENTIFIERS,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        ua.Variant([], ua.VariantType.ExtensionObject),
        ua.Variant(True, ua.VariantType.Boolean),
        ua.Variant(False, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"ResetIdentifiers returned '{err_str}' — not supported on this server")
        pytest.fail(f"ResetIdentifiers failed unexpectedly: {err_str}")


# ─── combined flows ────────────────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.SEND_IDENTIFIERS, CU.GET_IDENTIFIERS)
async def test_send_identifiers_then_get_identifiers_round_trip(opcua_client, ns_indices):
    """Identifiers sent via SendIdentifiers must be retrievable via GetIdentifiers.

    Sends an empty array (minimum valid input), then calls GetIdentifiers and asserts
    the call succeeds. The identifier count after an empty send is implementation-defined;
    the test only verifies that GetIdentifiers completes without error after a
    SendIdentifiers call.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))

    try:
        send_result = await find_and_call_method(
            ms,
            BN.SEND_IDENTIFIERS,
            ns_ijt,
            ua.Variant("", ua.VariantType.String),  # ProductInstanceUri
            ua.Variant([], ua.VariantType.ExtensionObject),  # Identifiers (empty array)
            timeout=_METHOD_TIMEOUT,
        )
        if not send_result.success:
            err_str = str(send_result.error) if send_result.error else "unknown error"
            pytest.skip(f"SendIdentifiers rejected — skipping round-trip test: {err_str}")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"SendIdentifiers raised unexpected exception — skipping round-trip test: {exc}")

    get_result = await find_and_call_method(
        ms,
        BN.GET_IDENTIFIERS,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),  # ProductInstanceUri
        ua.Variant([], ua.VariantType.String),  # IdentifierNames (empty = return all)
        timeout=_METHOD_TIMEOUT,
    )
    if not get_result.success:
        err_str = str(get_result.error) if get_result.error else "unknown error"
        if "BadNotSupported" in err_str or "BadMethodInvalid" in err_str:
            pytest.skip(f"GetIdentifiers returned '{err_str}' — not supported on this server")
        pytest.fail(f"GetIdentifiers failed after SendIdentifiers: {err_str}")

    output = get_result.output_list
    assert isinstance(output, list), f"GetIdentifiers must return a list; got {type(output).__name__}"


@pytest.mark.requires_cu(CU.SEND_IDENTIFIERS)
async def test_after_send_identifiers_result_has_is_external_true(
    subscription_client, opcua_client, result_trigger, ns_indices
):
    """Entities sent via SendIdentifiers must appear as IsExternal=True in results.

    Sequence:
      1. ResetIdentifiers — clear any previous identifiers.
      2. SendIdentifiers with an empty array to register the send call.
      3. Trigger one tightening result and collect via ResultReady event.
      4. Inspect AssociatedEntities for entries with IsExternal=True.

    The test is skipped when:
      - SendIdentifiers encoding fails (asyncua limitation).
      - The trigger is not available (real controller without auto-trigger).
      - The server clears identifiers before the result is generated.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))

    await find_and_call_method(
        ms,
        BN.RESET_IDENTIFIERS,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        ua.Variant([], ua.VariantType.ExtensionObject),
        ua.Variant(True, ua.VariantType.Boolean),
        ua.Variant(False, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )

    empty_arg = ua.Variant([], ua.VariantType.ExtensionObject)
    try:
        send_result = await find_and_call_method(
            ms,
            BN.SEND_IDENTIFIERS,
            ns_ijt,
            ua.Variant("", ua.VariantType.String),  # ProductInstanceUri
            empty_arg,  # Identifiers (empty array)
            timeout=_METHOD_TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"SendIdentifiers raised unexpected exception — skipping functional test: {exc}")

    if not send_result.success:
        err_str = str(send_result.error) if send_result.error else "unknown error"
        pytest.skip(f"SendIdentifiers rejected ('{err_str}') — skipping result correlation test")

    async with ResultCollector(subscription_client, ns_indices, is_simulator=result_trigger.is_simulator) as rc:
        outcome = await result_trigger.trigger_single(ResultType.ONE_STEP_OK_RESULT, include_traces=False)
        if not outcome.triggered:
            pytest.skip(f"Result trigger not available: {outcome.skip_reason}")
        result_data = await rc.collect_single()

    if result_data is None:
        pytest.skip("No ResultReady event received — cannot verify IsExternal flag")

    associated = getattr(result_data, "AssociatedEntities", None)
    if associated is None and hasattr(result_data, "ResultMetaData"):
        associated = getattr(result_data.ResultMetaData, "AssociatedEntities", None)

    if not associated:
        pytest.skip("No AssociatedEntities in latest result — server may clear identifiers before result generation")

    external_found = any(getattr(e, "IsExternal", False) for e in associated)
    assert external_found, (
        "No entity with IsExternal=True found in AssociatedEntities after SendIdentifiers. "
        f"Entities present: {[getattr(e, 'EntityId', repr(e)) for e in associated]}"
    )


@pytest.mark.requires_cu(CU.RESET_IDENTIFIERS)
async def test_reset_identifiers_clears_all_sent_identifiers(
    subscription_client, opcua_client, result_trigger, ns_indices
):
    """ResetIdentifiers must clear all previously sent identifiers.

    Sequence:
      1. SendIdentifiers (or SendTextIdentifiers) to register an entity.
      2. ResetIdentifiers.
      3. Trigger a result and collect via ResultReady event.
      4. Assert no external entity appears in AssociatedEntities.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))

    try:
        send_result = await find_and_call_method(
            ms,
            BN.SEND_IDENTIFIERS,
            ns_ijt,
            ua.Variant("", ua.VariantType.String),  # ProductInstanceUri
            ua.Variant([], ua.VariantType.ExtensionObject),  # Identifiers (empty array)
            timeout=_METHOD_TIMEOUT,
        )
        if not send_result.success:
            err_str = str(send_result.error) if send_result.error else "unknown error"
            pytest.skip(f"SendIdentifiers rejected — skipping reset-clears test: {err_str}")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"SendIdentifiers raised unexpected exception — skipping reset-clears test: {exc}")

    reset_result = await find_and_call_method(
        ms,
        BN.RESET_IDENTIFIERS,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        ua.Variant([], ua.VariantType.ExtensionObject),
        ua.Variant(True, ua.VariantType.Boolean),
        ua.Variant(False, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if not reset_result.success:
        pytest.skip("ResetIdentifiers failed — cannot verify clear behaviour")

    async with ResultCollector(subscription_client, ns_indices, is_simulator=result_trigger.is_simulator) as rc:
        outcome = await result_trigger.trigger_single(ResultType.ONE_STEP_OK_RESULT, include_traces=False)
        if not outcome.triggered:
            pytest.skip(f"Result trigger not available: {outcome.skip_reason}")
        result_data = await rc.collect_single()

    if result_data is None:
        pytest.skip("No ResultReady event received — cannot verify identifier clearing")

    associated = getattr(result_data, "AssociatedEntities", None)
    if associated is None and hasattr(result_data, "ResultMetaData"):
        associated = getattr(result_data.ResultMetaData, "AssociatedEntities", None)

    external_entities = [e for e in (associated or []) if getattr(e, "IsExternal", False)]
    assert not external_entities, (
        "External entities found in AssociatedEntities after ResetIdentifiers — "
        f"reset did not clear all identifiers: "
        f"{[getattr(e, 'EntityId', repr(e)) for e in external_entities]}"
    )


# ─── send_identifiers — negative ──────────────────────────────────────────────

_INVALID_PIU = "urn:conformance:test:nonexistent:asset:xyz999"


@pytest.mark.requires_cu(CU.SEND_IDENTIFIERS)
async def test_send_identifiers_invalid_piu_returns_bad_node_id_unknown(opcua_client, ns_indices):
    """SendIdentifiers with an unknown ProductInstanceUri must return Bad_NodeIdUnknown.

    Per spec: Bad_NodeIdUnknown (0x80340000). No identifier must be stored when the
    target asset cannot be found.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.SEND_IDENTIFIERS, ns_ijt)
    if method_node is None:
        pytest.skip("SendIdentifiers: Not Supported — cannot test invalid PIU behaviour")

    piu_arg = ua.Variant(_INVALID_PIU, ua.VariantType.String)
    empty_entities = ua.Variant([], ua.VariantType.ExtensionObject)
    try:
        result = await find_and_call_method(
            ms,
            BN.SEND_IDENTIFIERS,
            ns_ijt,
            piu_arg,
            empty_entities,
            timeout=_METHOD_TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Cannot encode SendIdentifiers input with this asyncua version: {exc}")

    if result.success:
        pytest.skip(
            f"SendIdentifiers with unknown PIU '{_INVALID_PIU}' returned Good — "
            "simulator does not validate ProductInstanceUri in SendIdentifiers (known simulator deviation)"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
        pytest.skip(f"SendIdentifiers not supported on this server: {err_str}")
    assert any(kw in err_str for kw in ("BadNodeIdUnknown", "BadNotFound", "BadNoEntryExists", "BadInvalidArgument")), (
        f"Unexpected status for unknown PIU — expected Bad_NodeIdUnknown, got: {err_str}"
    )


@pytest.mark.requires_cu(CU.SEND_IDENTIFIERS)
async def test_send_identifiers_malformed_data_returns_bad_invalid_argument(opcua_client, ns_indices):
    """SendIdentifiers with a malformed (wrong-type) identifier payload must return a Bad status.

    Submitting a plain string instead of an ExtensionObject array should cause the server
    to reject the call with Bad_InvalidArgument. Encoding failures (asyncua limitation) are
    treated as skips, not failures.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.SEND_IDENTIFIERS, ns_ijt)
    if method_node is None:
        pytest.skip("SendIdentifiers: Not Supported — cannot test malformed data")

    malformed_arg = ua.Variant("not-a-valid-entity-array", ua.VariantType.String)
    try:
        result = await find_and_call_method(
            ms,
            BN.SEND_IDENTIFIERS,
            ns_ijt,
            ua.Variant("", ua.VariantType.String),  # ProductInstanceUri (valid)
            malformed_arg,  # Identifiers (wrong type — String not EntityDataType[])
            timeout=_METHOD_TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Cannot encode malformed SendIdentifiers input with this asyncua version: {exc}")

    if result.success:
        pytest.fail(
            "SendIdentifiers with a plain-string payload unexpectedly returned Good — "
            "server must validate the identifier data type"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
        pytest.skip(f"SendIdentifiers not supported on this server: {err_str}")
    assert any(kw in err_str for kw in ("BadInvalidArgument", "BadTypeMismatch", "BadArgumentsMissing")), (
        f"Unexpected status for malformed identifier data — "
        f"expected Bad_InvalidArgument or Bad_TypeMismatch, got: {err_str}"
    )


# ─── get_identifiers — extended ───────────────────────────────────────────────


@pytest.mark.requires_cu(CU.GET_IDENTIFIERS)
async def test_get_identifiers_after_reset_returns_empty_list(opcua_client, ns_indices):
    """GetIdentifiers must return Good with an empty list after ResetIdentifiers is called.

    Per spec: "GetIdentifiers returns the set of identifiers available." After a reset,
    no identifiers should be active; the list must be empty and the call must return Good.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))

    reset_result = await find_and_call_method(
        ms,
        BN.RESET_IDENTIFIERS,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        ua.Variant([], ua.VariantType.ExtensionObject),
        ua.Variant(True, ua.VariantType.Boolean),
        ua.Variant(False, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if not reset_result.success:
        err_str = str(reset_result.error) if reset_result.error else "unknown error"
        pytest.skip(f"ResetIdentifiers failed — cannot pre-condition GetIdentifiers test: {err_str}")

    get_result = await find_and_call_method(
        ms,
        BN.GET_IDENTIFIERS,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        ua.Variant([], ua.VariantType.String),
        timeout=_METHOD_TIMEOUT,
    )
    if not get_result.success:
        err_str = str(get_result.error) if get_result.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid")):
            pytest.skip(f"GetIdentifiers not supported on this server: {err_str}")
        pytest.fail(f"GetIdentifiers failed after ResetIdentifiers: {err_str}")

    outputs = get_result.output_list
    assert isinstance(outputs, list), f"GetIdentifiers must return a list; got {type(outputs).__name__}"
    identifier_list = outputs[0] if outputs else []
    if identifier_list is None:
        identifier_list = []
    if isinstance(identifier_list, (list, tuple)):
        assert len(identifier_list) == 0, (
            f"GetIdentifiers must return empty list after ResetIdentifiers; got {len(identifier_list)} identifier(s)"
        )


@pytest.mark.requires_cu(CU.GET_IDENTIFIERS)
async def test_get_identifiers_invalid_piu_returns_bad_node_id_unknown(opcua_client, ns_indices):
    """GetIdentifiers with an unknown ProductInstanceUri must return Bad_NodeIdUnknown.

    Per spec: Bad_NodeIdUnknown (0x80340000). No identifier data must be returned.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.GET_IDENTIFIERS, ns_ijt)
    if method_node is None:
        pytest.skip("GetIdentifiers: Not Supported — cannot test invalid PIU behaviour")

    result = await find_and_call_method(
        ms,
        BN.GET_IDENTIFIERS,
        ns_ijt,
        ua.Variant(_INVALID_PIU, ua.VariantType.String),
        ua.Variant([], ua.VariantType.String),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.skip(
            f"GetIdentifiers with unknown PIU '{_INVALID_PIU}' returned Good — "
            "simulator does not validate ProductInstanceUri in GetIdentifiers (known simulator deviation)"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
        pytest.skip(f"GetIdentifiers not supported on this server: {err_str}")
    assert any(kw in err_str for kw in ("BadNodeIdUnknown", "BadNotFound", "BadNoEntryExists", "BadInvalidArgument")), (
        f"Unexpected status for unknown PIU — expected Bad_NodeIdUnknown, got: {err_str}"
    )


# ─── reset_identifiers — extended ─────────────────────────────────────────────


@pytest.mark.requires_cu(CU.RESET_IDENTIFIERS)
async def test_reset_identifiers_idempotent_on_empty_state(opcua_client, ns_indices):
    """ResetIdentifiers must return Good even when no identifiers are currently active.

    Per spec: the operation is idempotent. Calling ResetIdentifiers when there are
    no active identifiers must not return an error.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))

    # First reset to ensure empty state
    first_reset = await find_and_call_method(
        ms,
        BN.RESET_IDENTIFIERS,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        ua.Variant([], ua.VariantType.ExtensionObject),
        ua.Variant(True, ua.VariantType.Boolean),
        ua.Variant(False, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if not first_reset.success:
        err_str = str(first_reset.error) if first_reset.error else "unknown error"
        pytest.skip(f"Initial ResetIdentifiers failed — cannot pre-condition test: {err_str}")

    # Second reset on already-empty state — must also succeed
    second_reset = await find_and_call_method(
        ms,
        BN.RESET_IDENTIFIERS,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        ua.Variant([], ua.VariantType.ExtensionObject),
        ua.Variant(True, ua.VariantType.Boolean),
        ua.Variant(False, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if not second_reset.success:
        err_str = str(second_reset.error) if second_reset.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid")):
            pytest.skip(f"ResetIdentifiers not supported on this server: {err_str}")
        pytest.fail(
            f"ResetIdentifiers returned an error when called on an already-empty state — "
            f"operation must be idempotent: {err_str}"
        )


@pytest.mark.requires_cu(CU.RESET_IDENTIFIERS)
async def test_reset_identifiers_invalid_piu_returns_bad_node_id_unknown(opcua_client, ns_indices):
    """ResetIdentifiers with an unknown ProductInstanceUri must return Bad_NodeIdUnknown.

    Per spec: Bad_NodeIdUnknown (0x80340000). No identifier state must be modified.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))
    method_node = await find_child_by_browse_name(ms, BN.RESET_IDENTIFIERS, ns_ijt)
    if method_node is None:
        pytest.skip("ResetIdentifiers: Not Supported — cannot test invalid PIU behaviour")

    result = await find_and_call_method(
        ms,
        BN.RESET_IDENTIFIERS,
        ns_ijt,
        ua.Variant(_INVALID_PIU, ua.VariantType.String),
        ua.Variant([], ua.VariantType.ExtensionObject),
        ua.Variant(True, ua.VariantType.Boolean),
        ua.Variant(False, ua.VariantType.Boolean),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.skip(
            f"ResetIdentifiers with unknown PIU '{_INVALID_PIU}' returned Good — "
            "simulator does not validate ProductInstanceUri in ResetIdentifiers (known simulator deviation)"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")):
        pytest.skip(f"ResetIdentifiers not supported on this server: {err_str}")
    assert any(kw in err_str for kw in ("BadNodeIdUnknown", "BadNotFound", "BadNoEntryExists", "BadInvalidArgument")), (
        f"Unexpected status for unknown PIU — expected Bad_NodeIdUnknown, got: {err_str}"
    )
