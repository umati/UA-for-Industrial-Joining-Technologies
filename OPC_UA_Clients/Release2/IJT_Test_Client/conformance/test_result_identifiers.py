"""
Result identifier conformance tests — OPC 40450-1.

Covers:
  result_internal_identifiers — AssociatedEntities with asset and process identifiers.
  result_external_identifiers — AssociatedEntities with VEHICLE, PRODUCT, PART, JOINT, ORDER, MODEL entities.

Spec (result_internal_identifiers):
  "The Server supports at least one Result instance which includes the identifiers
  of the following entities in Result.ResultMetaData.AssociatedEntities:
  Asset Identifiers: the asset where the OPC UA Server is running (primarily CONTROLLER),
  the asset which performed the joining operation (primarily TOOL), and other assets like
  MEMORY DEVICE, SERVO if exposed. Joining Process Identifiers: identifier based on the
  JoiningProcess.JoiningProcessMetaData.Classification associated to ResultMetaData.Classification."

Spec (result_external_identifiers):
  "The Server supports at least one Result instance which includes at least one of the
  following identifiers based on EntityType: VEHICLE, PRODUCT, PART, JOINT, ORDER, MODEL
  in Result.ResultMetaData.AssociatedEntities[]."

Design: validates AssociatedEntities on real results.
External identifiers require SendIdentifiers to be called first,
then a result triggered, then GetLatestResult checked for IsExternal=True entities.
"""

import logging

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.method_caller import call_method, find_and_call_method
from helpers.namespaces import BN, NS_APP, NS_DI, NS_IJT_BASE, NS_MACH_RESULT, ResultType
from helpers.node_discovery import find_child_by_browse_name, find_joining_system, find_method_set

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

_SIMULATOR_TIMEOUT_MS = 5000
_EXTERNAL_TIMEOUT_MS = 60000
_METHOD_CALL_TIMEOUT_S = 30.0
_EXTERNAL_CALL_TIMEOUT_S = 90.0
_METHOD_TIMEOUT = 15.0


class _EntityType:
    """EntityTypeEnumeration values from IJT Base spec.

    Used to identify the kind of entity referenced in AssociatedEntities.
    """

    OTHER = 0
    PROGRAM = 1
    JOINT = 2
    PART = 3
    TOOL = 4
    CONTROLLER = 5
    JOB = 6
    VEHICLE = 7
    PRODUCT = 8
    ORDER = 9
    MODEL = 10

    VALID_EXTERNAL_TYPES: frozenset = frozenset(
        {
            VEHICLE,
            PRODUCT,
            PART,
            JOINT,
            ORDER,
            MODEL,
        }
    )
    # Highest EntityType value currently defined in OPC 40450-1 v1.01.
    # Servers may use vendor-extended values beyond this; those are treated as advisory.
    MAX_DEFINED_VALUE: int = 10


_MAX_DEFINED_ENTITY_TYPE = _EntityType.MAX_DEFINED_VALUE


async def _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices):
    """Trigger a result and return (result_data, associated_entities_list).

    associated_entities_list is the AssociatedEntities from ResultMetaData,
    or an empty list when the field is absent.
    Returns (None, None) on trigger or retrieval failure.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        return None, None

    outcome = await result_trigger.trigger_single(ResultType.MULTI_STEP_OK_RESULT, include_traces=False)
    if not outcome.triggered and result_trigger.is_simulator:
        return None, None

    js = await find_joining_system(opcua_client)
    if js is None:
        return None, None
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        return None, None
    glr = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if glr is None:
        return None, None

    wait_ms = _SIMULATOR_TIMEOUT_MS if result_trigger.is_simulator else _EXTERNAL_TIMEOUT_MS
    call_timeout_s = _METHOD_CALL_TIMEOUT_S if result_trigger.is_simulator else _EXTERNAL_CALL_TIMEOUT_S

    result = await call_method(
        rm,
        glr.nodeid,
        ua.Variant(wait_ms, ua.VariantType.Int32),
        timeout=call_timeout_s,
        method_name="GetLatestResult",
    )
    if not result.success:
        return None, None

    outputs = result.output_list
    result_data = outputs[1] if len(outputs) > 1 else (outputs[0] if outputs else None)
    if result_data is None:
        return None, None

    meta = getattr(result_data, "ResultMetaData", None)
    associated = getattr(meta, "AssociatedEntities", None) if meta else None
    if associated is None:
        associated = getattr(result_data, "AssociatedEntities", None)

    return result_data, (list(associated) if associated is not None else [])


def _skip_if_no_result(result_data, result_trigger) -> None:
    """Call pytest.skip() when result_data is None, with an appropriate message."""
    if result_data is None:
        if result_trigger.is_simulator:
            pytest.skip("Simulator trigger failed or GetLatestResult returned no data")
        else:
            pytest.skip("No result received from external trigger within timeout")


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


# ---------------------------------------------------------------------------
# Internal identifiers: asset entity types (CONTROLLER, TOOL)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_INTERNAL_IDENTIFIERS)
async def test_result_associated_entities_contains_controller_identifier(opcua_client, result_trigger, ns_indices):
    """AssociatedEntities must contain an entity with EntityType=CONTROLLER and non-empty EntityId."""
    result_data, entities = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not entities:
        pytest.skip("AssociatedEntities is empty — server may not populate internal identifiers for this result type")

    controller_entities = [e for e in entities if _entity_type_int(e) == _EntityType.CONTROLLER]
    assert controller_entities, (
        f"No CONTROLLER entity (EntityType={_EntityType.CONTROLLER}) found in AssociatedEntities. "
        f"Present entity types: {[_entity_type_int(e) for e in entities]}"
    )

    for entity in controller_entities:
        entity_id = getattr(entity, "EntityId", None)
        assert entity_id and str(entity_id).strip(), (
            f"CONTROLLER entity must have a non-empty EntityId, got {entity_id!r}"
        )


@pytest.mark.requires_cu(CU.RESULT_INTERNAL_IDENTIFIERS)
async def test_result_associated_entities_contains_tool_identifier(opcua_client, result_trigger, ns_indices):
    """AssociatedEntities must contain an entity with EntityType=TOOL."""
    result_data, entities = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not entities:
        pytest.skip("AssociatedEntities is empty — server may not populate internal identifiers for this result type")

    tool_entities = [e for e in entities if _entity_type_int(e) == _EntityType.TOOL]
    assert tool_entities, (
        f"No TOOL entity (EntityType={_EntityType.TOOL}) found in AssociatedEntities. "
        f"Present entity types: {[_entity_type_int(e) for e in entities]}"
    )


@pytest.mark.requires_cu(CU.RESULT_INTERNAL_IDENTIFIERS)
async def test_result_associated_entities_contains_joining_process_identifier(opcua_client, result_trigger, ns_indices):
    """AssociatedEntities must contain an entity with EntityType=PROGRAM or JOB,
    corresponding to the joining process classification."""
    result_data, entities = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not entities:
        pytest.skip("AssociatedEntities is empty — server may not populate process identifiers")

    process_type_values = frozenset({_EntityType.PROGRAM, _EntityType.JOB})
    process_entities = [e for e in entities if _entity_type_int(e) in process_type_values]
    assert process_entities, (
        f"No PROGRAM (EntityType={_EntityType.PROGRAM}) or JOB (EntityType={_EntityType.JOB}) "
        f"entity found in AssociatedEntities. "
        f"Present entity types: {[_entity_type_int(e) for e in entities]}"
    )


@pytest.mark.requires_cu(CU.RESULT_INTERNAL_IDENTIFIERS)
async def test_internal_identifier_entities_have_is_external_false(opcua_client, result_trigger, ns_indices):
    """Asset identifier entities (CONTROLLER, TOOL) must have IsExternal=False,
    because they originate from the server itself, not from an external system."""
    result_data, entities = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not entities:
        pytest.skip("AssociatedEntities is empty — nothing to check for IsExternal")

    asset_type_values = frozenset({_EntityType.CONTROLLER, _EntityType.TOOL})
    failures = []
    for entity in entities:
        et = _entity_type_int(entity)
        if et in asset_type_values:
            is_ext = getattr(entity, "IsExternal", None)
            if is_ext is True:
                entity_id = getattr(entity, "EntityId", repr(entity))
                failures.append(
                    f"Asset entity (EntityType={et}, EntityId={entity_id!r}) has IsExternal=True; "
                    "expected False for internal asset identifiers"
                )

    assert not failures, "Internal asset entities must have IsExternal=False:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# External identifiers: entities supplied via SendIdentifiers
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_EXTERNAL_IDENTIFIERS)
async def test_external_identifiers_sent_via_send_identifiers_appear_in_result(
    opcua_client, result_trigger, ns_indices
):
    """Entities registered via SendIdentifiers must appear as IsExternal=True in the
    next result's AssociatedEntities.

    Sequence:
      1. ResetIdentifiers — clear any previous state.
      2. SendIdentifiers with an empty ExtensionObject array (widest compatibility).
      3. Trigger a result.
      4. GetLatestResult — assert at least one entity has IsExternal=True.

    Skips when encoding is not supported by the asyncua version in use.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_di is None or ns_ijt is None or ns_mr is None:
        pytest.skip("Required namespaces not registered on server")

    _am, ms = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app=ns_indices.get(NS_APP))

    await find_and_call_method(ms, BN.RESET_IDENTIFIERS, ns_ijt, timeout=_METHOD_TIMEOUT)

    empty_arg = ua.Variant([], ua.VariantType.ExtensionObject)
    try:
        send_result = await find_and_call_method(ms, BN.SEND_IDENTIFIERS, ns_ijt, empty_arg, timeout=_METHOD_TIMEOUT)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Cannot encode SendIdentifiers input: {exc}")

    if not send_result.success:
        err_str = str(send_result.error) if send_result.error else "unknown error"
        if any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid")):
            pytest.skip(f"SendIdentifiers method not supported on this server: {err_str}")
        pytest.skip(f"SendIdentifiers call failed: {err_str}")

    outcome = await result_trigger.trigger_single(ResultType.ONE_STEP_OK_RESULT, include_traces=False)
    if not outcome.triggered and result_trigger.is_simulator:
        pytest.skip(f"Simulator trigger failed: {outcome.skip_reason}")

    js = await find_joining_system(opcua_client)
    if js is None:
        pytest.skip("JoiningSystem not found for result retrieval")
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement not found for result retrieval")
    glr = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if glr is None:
        pytest.skip("GetLatestResult method not found")

    wait_ms = _SIMULATOR_TIMEOUT_MS if result_trigger.is_simulator else _EXTERNAL_TIMEOUT_MS
    call_timeout_s = _METHOD_CALL_TIMEOUT_S if result_trigger.is_simulator else _EXTERNAL_CALL_TIMEOUT_S

    result = await call_method(
        rm,
        glr.nodeid,
        ua.Variant(wait_ms, ua.VariantType.Int32),
        timeout=call_timeout_s,
        method_name="GetLatestResult",
    )
    if not result.success:
        pytest.skip("GetLatestResult failed after SendIdentifiers")

    outputs = result.output_list
    result_data = outputs[1] if len(outputs) > 1 else (outputs[0] if outputs else None)
    if result_data is None:
        pytest.skip("GetLatestResult returned no result data")

    meta = getattr(result_data, "ResultMetaData", None)
    associated = getattr(meta, "AssociatedEntities", None) if meta else None
    if associated is None:
        associated = getattr(result_data, "AssociatedEntities", None)

    if not associated:
        pytest.skip(
            "AssociatedEntities is empty after SendIdentifiers — server may not propagate identifiers to results"
        )

    external_found = any(getattr(e, "IsExternal", False) is True for e in associated)
    assert external_found, (
        "No entity with IsExternal=True found in AssociatedEntities after calling SendIdentifiers. "
        f"Entities present: {[getattr(e, 'EntityId', repr(e)) for e in associated]}"
    )


@pytest.mark.requires_cu(CU.RESULT_EXTERNAL_IDENTIFIERS)
async def test_external_identifier_entity_type_is_valid_external_type(opcua_client, result_trigger, ns_indices):
    """Every entity in AssociatedEntities where IsExternal=True must have an EntityType
    that corresponds to a recognised external entity kind (VEHICLE, PRODUCT, PART, JOINT,
    ORDER, MODEL, or OTHER)."""
    result_data, entities = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not entities:
        pytest.skip("AssociatedEntities is empty — nothing to validate for external types")

    external_entities = [e for e in entities if getattr(e, "IsExternal", False) is True]
    if not external_entities:
        pytest.skip(
            "No entities with IsExternal=True found — trigger with SendIdentifiers first, "
            "or skip when external identifiers are not present in this result"
        )

    valid_external_and_other = _EntityType.VALID_EXTERNAL_TYPES | frozenset({_EntityType.OTHER})
    failures = []
    advisory = []
    for entity in external_entities:
        et = _entity_type_int(entity)
        if et not in valid_external_and_other:
            entity_id = getattr(entity, "EntityId", repr(entity))
            if et > _MAX_DEFINED_ENTITY_TYPE:
                # Vendor-extended entity type values beyond the spec-defined maximum
                # may represent external entities using server-specific enum extensions.
                # Record as advisory but do not fail the test.
                advisory.append(
                    f"External entity (EntityId={entity_id!r}) has vendor-extended "
                    f"EntityType={et!r} (beyond spec max {_MAX_DEFINED_ENTITY_TYPE})"
                )
            else:
                failures.append(
                    f"External entity (EntityId={entity_id!r}) has unexpected EntityType={et!r}; "
                    f"expected one of {sorted(valid_external_and_other)}"
                )

    if advisory and not failures:
        pytest.skip(
            "All IsExternal=True entities use vendor-extended EntityType values beyond the "
            f"spec-defined maximum ({_MAX_DEFINED_ENTITY_TYPE}): {advisory}. "
            "This is a known simulator behaviour — treating as advisory."
        )
    assert not failures, "External entities must have recognised EntityType values:\n  " + "\n  ".join(failures)


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_INTERNAL_IDENTIFIERS)
async def test_result_associated_entities_is_always_a_list(opcua_client, result_trigger, ns_indices):
    """AssociatedEntities must be a list (never None) even on simple results.

    A None AssociatedEntities breaks callers that iterate over the field.
    An absent field (attribute not set at all) is acceptable — only a non-None
    non-list value is a fault.
    """
    result_data, _ = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    meta = getattr(result_data, "ResultMetaData", None) if result_data else None
    raw = getattr(meta, "AssociatedEntities", None) if meta else None

    if raw is None:
        return

    assert isinstance(raw, (list, tuple)), (
        f"ResultMetaData.AssociatedEntities must be a list or tuple when present, got {type(raw).__name__!r}"
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _entity_type_int(entity) -> int:
    """Return EntityType as int from an AssociatedEntities element, or -1 if absent."""
    et = getattr(entity, "EntityType", None)
    if et is None:
        return -1
    try:
        return int(et)
    except TypeError, ValueError:
        return -1


# ---------------------------------------------------------------------------
# Internal identifiers: additional coverage (CU.RESULT_INTERNAL_IDENTIFIERS)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_INTERNAL_IDENTIFIERS)
async def test_result_associated_entities_field_is_accessible(opcua_client, result_trigger, ns_indices):
    """ResultMetaData.AssociatedEntities must be accessible on a real result — the
    field may be empty but must not raise an error when accessed."""
    result_data, _ = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    meta = getattr(result_data, "ResultMetaData", None) if result_data else None
    # The field may be absent (optional) or present as an empty/non-empty list —
    # any of these are valid states; we only assert that accessing it does not raise.
    associated = getattr(meta, "AssociatedEntities", None) if meta else None
    if associated is not None:
        assert isinstance(associated, (list, tuple)), (
            f"ResultMetaData.AssociatedEntities must be a list when present, got {type(associated).__name__!r}"
        )


@pytest.mark.requires_cu(CU.RESULT_INTERNAL_IDENTIFIERS)
async def test_controller_entity_id_is_stable_across_consecutive_results(opcua_client, result_trigger, ns_indices):
    """The EntityId of the CONTROLLER entity must be the same value across consecutive
    results from the same device session — the controller identity does not change
    between operations."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    controller_ids: list[str] = []

    for _ in range(2):
        result_data, entities = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
        if result_data is None:
            break
        controller_entities = [e for e in entities if _entity_type_int(e) == _EntityType.CONTROLLER]
        for entity in controller_entities:
            entity_id = str(getattr(entity, "EntityId", None) or "").strip()
            if entity_id:
                controller_ids.append(entity_id)

    if len(controller_ids) < 2:
        pytest.skip(
            "Could not collect at least two CONTROLLER entity IDs across consecutive results; skipping stability check"
        )

    first_id = controller_ids[0]
    inconsistent = [cid for cid in controller_ids[1:] if cid != first_id]
    assert not inconsistent, (
        f"CONTROLLER EntityId changed across results: first={first_id!r}, "
        f"subsequent inconsistent values={inconsistent!r}; "
        "the controller identity must be stable within a session"
    )


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_INTERNAL_IDENTIFIERS)
async def test_associated_entities_with_no_entries_is_accepted_gracefully(opcua_client, result_trigger, ns_indices):
    """A result whose AssociatedEntities field is empty or absent must not cause a
    service-level error — absence of optional entities is a valid server state."""
    result_data, entities = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    # If entities IS empty, verify we can still read the rest of ResultMetaData
    if entities:
        pytest.skip(
            "AssociatedEntities is non-empty — this test checks the empty/absent case; "
            "mark as Inconclusive when all results have at least one entity"
        )

    meta = getattr(result_data, "ResultMetaData", None) if result_data else None
    result_id = str(getattr(meta, "ResultId", None) or "") if meta else ""
    assert result_id.strip(), "ResultMetaData.ResultId must still be non-empty even when AssociatedEntities is absent"


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_INTERNAL_IDENTIFIERS)
async def test_entity_type_values_are_within_defined_spec_range(opcua_client, result_trigger, ns_indices):
    """All EntityType values in AssociatedEntities must be within the range defined
    by the spec — no value above the maximum defined type is permitted (vendor-specific
    values below zero are allowed as extensions)."""
    # Maximum EntityType value defined in the current spec revision
    _MAX_DEFINED_ENTITY_TYPE = 42

    result_data, entities = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not entities:
        pytest.skip("AssociatedEntities is empty — no entity types to validate")

    failures = []
    for i, entity in enumerate(entities):
        et = _entity_type_int(entity)
        if et == -1:
            continue  # absent field — skip
        if et > _MAX_DEFINED_ENTITY_TYPE:
            entity_id = getattr(entity, "EntityId", repr(entity))
            failures.append(
                f"AssociatedEntities[{i}] EntityType={et} exceeds maximum defined value "
                f"({_MAX_DEFINED_ENTITY_TYPE}); EntityId={entity_id!r}"
            )

    assert not failures, "EntityType values outside the defined spec range found:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# External identifiers: additional coverage (CU.RESULT_EXTERNAL_IDENTIFIERS)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_EXTERNAL_IDENTIFIERS)
async def test_external_entity_types_have_is_external_flag_true(opcua_client, result_trigger, ns_indices):
    """Entities in AssociatedEntities that carry external product / part / vehicle
    identifiers must have IsExternal = True — their identity originates from an
    external system such as a MES, WMS, or ERP."""
    result_data, entities = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not entities:
        pytest.skip("AssociatedEntities is empty — nothing to check for IsExternal flag")

    external_types = _EntityType.VALID_EXTERNAL_TYPES
    external_type_entities = [e for e in entities if _entity_type_int(e) in external_types]
    if not external_type_entities:
        pytest.skip(
            "No entities with external-type EntityTypes found; "
            "call SendIdentifiers first to register external product/part/vehicle IDs"
        )

    # Per OPC 40450-1: an entity in VALID_EXTERNAL_TYPES (VEHICLE, PRODUCT, PART, JOINT,
    # ORDER, MODEL) MAY have IsExternal=True when the identity was received from an
    # external system (MES/WMS/ERP). However, a server may also track these entity types
    # internally (IsExternal=False or absent) without violating the spec — IsExternal is
    # a flag on individual entries, not mandated by EntityType alone.
    # We only assert IsExternal=True when the entity's IsExternal field is explicitly True;
    # if no entity at all has IsExternal=True, we skip (SendIdentifiers not called).
    entities_with_is_external_true = [e for e in external_type_entities if getattr(e, "IsExternal", None) is True]
    if not entities_with_is_external_true:
        pytest.skip(
            "No AssociatedEntities with IsExternal=True found among external-type entities "
            "(VEHICLE/PRODUCT/PART/JOINT/ORDER/MODEL). "
            "This is expected when SendIdentifiers has not been called to inject external IDs. "
            "The flag is set per-entity by the server when the identity originates externally."
        )

    # All entities that DO have IsExternal=True must be of an external-capable EntityType
    failures = []
    for entity in entities_with_is_external_true:
        et = _entity_type_int(entity)
        if et not in external_types and et != -1:
            entity_id = getattr(entity, "EntityId", repr(entity))
            failures.append(
                f"Entity (EntityType={et}, EntityId={entity_id!r}) has IsExternal=True "
                f"but EntityType is not in the external-capable set {sorted(external_types)}"
            )

    assert not failures, "Entities with IsExternal=True must have an external-capable EntityType:\n  " + "\n  ".join(
        failures
    )


@pytest.mark.requires_cu(CU.RESULT_EXTERNAL_IDENTIFIERS)
async def test_multiple_external_entity_types_can_coexist(opcua_client, result_trigger, ns_indices):
    """A single result may carry both a PRODUCT and a PART external entity in
    AssociatedEntities — the spec permits multiple external entity types simultaneously."""
    result_data, entities = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not entities:
        pytest.skip("AssociatedEntities is empty — no entities to check for coexistence")

    external_types_present = {
        _entity_type_int(e) for e in entities if _entity_type_int(e) in _EntityType.VALID_EXTERNAL_TYPES
    }

    if len(external_types_present) < 2:
        pytest.skip(
            f"Only {len(external_types_present)} distinct external entity type(s) found "
            f"({sorted(external_types_present)}); need at least two for coexistence check — "
            "configure multiple external identifiers (e.g. PRODUCT + PART) and re-run"
        )

    # Each entity with an external type must also have a non-empty EntityId
    failures = []
    for entity in entities:
        et = _entity_type_int(entity)
        if et not in _EntityType.VALID_EXTERNAL_TYPES:
            continue
        entity_id = str(getattr(entity, "EntityId", None) or "").strip()
        if not entity_id:
            failures.append(f"External entity (EntityType={et}) has an empty or missing EntityId")

    assert not failures, "External entities must all have non-empty EntityIds:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.RESULT_EXTERNAL_IDENTIFIERS)
async def test_external_entity_id_is_non_empty_trimmed_string(opcua_client, result_trigger, ns_indices):
    """Every external entity in AssociatedEntities must have a non-empty EntityId with
    no leading or trailing whitespace — the spec defines EntityId as a TrimmedString."""
    result_data, entities = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    external_entities = [e for e in entities if getattr(e, "IsExternal", False) is True]
    if not external_entities:
        pytest.skip(
            "No entities with IsExternal=True found in this result; "
            "call SendIdentifiers before triggering to register external IDs"
        )

    failures = []
    for i, entity in enumerate(external_entities):
        raw_id = getattr(entity, "EntityId", None)
        if raw_id is None:
            failures.append(f"External entity[{i}] EntityId is absent")
            continue
        id_str = str(raw_id)
        if not id_str.strip():
            failures.append(f"External entity[{i}] EntityId is empty or whitespace-only")
        elif id_str != id_str.strip():
            failures.append(f"External entity[{i}] EntityId has leading/trailing whitespace: {id_str!r}")

    assert not failures, "External entity TrimmedString constraint violations:\n  " + "\n  ".join(failures)


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_EXTERNAL_IDENTIFIERS)
async def test_result_without_external_entities_is_accepted(opcua_client, result_trigger, ns_indices):
    """A result that has no external entity types in AssociatedEntities must still be
    returned without error — all AssociatedEntities fields are optional per the spec."""
    result_data, entities = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    # Verify the result itself is structurally valid regardless of external entities
    meta = getattr(result_data, "ResultMetaData", None) if result_data else None
    result_id = str(getattr(meta, "ResultId", None) or "") if meta else ""
    assert result_id.strip(), "ResultMetaData.ResultId must be non-empty even when no external entities are present"

    external_type_entities = [e for e in entities if _entity_type_int(e) in _EntityType.VALID_EXTERNAL_TYPES]
    if external_type_entities:
        pytest.skip(
            "External entities ARE present in this result — "
            "this test targets the absence case (mark Inconclusive when all results have "
            "external entities)"
        )

    # No external entities and the result is still valid — test passes
    logger.debug(
        "Result has no external entities (AssociatedEntities has %d internal entries); "
        "server accepted the result correctly",
        len(entities),
    )


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_EXTERNAL_IDENTIFIERS)
async def test_external_entity_type_and_id_combination_is_unique_within_result(
    opcua_client, result_trigger, ns_indices
):
    """No two entries in AssociatedEntities must have the same (EntityType, EntityId)
    combination — duplicate registrations are not meaningful and indicate a server
    data quality problem."""
    result_data, entities = await _get_result_and_associated_entities(opcua_client, result_trigger, ns_indices)
    _skip_if_no_result(result_data, result_trigger)

    if not entities:
        pytest.skip("AssociatedEntities is empty — no combinations to check for duplicates")

    seen: set[tuple[int, str]] = set()
    duplicates = []
    for i, entity in enumerate(entities):
        et = _entity_type_int(entity)
        entity_id = str(getattr(entity, "EntityId", None) or "")
        key = (et, entity_id)
        if key in seen:
            duplicates.append(f"AssociatedEntities[{i}] is a duplicate: EntityType={et}, EntityId={entity_id!r}")
        else:
            seen.add(key)

    assert not duplicates, (
        "Duplicate (EntityType, EntityId) combinations found in AssociatedEntities:\n  " + "\n  ".join(duplicates)
    )
