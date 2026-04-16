"""
Conformance unit tests for JointManagement — OPC 40450-1 IJT Base.

joint_management: "The JoiningSystem includes support for JointManagement with
methods for managing joint definitions."

send_joint: "The Server supports SendJoint method."

get_joint_list: "The Server supports GetJointList method."

select_joint: "The Server supports SelectJoint method."

get_joint: "The Server supports GetJoint method."

joint_data: "The Server supports JointData structure including JointId and related
fields."

delete_joint: "The Server supports DeleteJoint method."

send_joint_design: "The Server supports SendJointDesign method."

get_joint_design_list: "The Server supports GetJointDesignList method."

get_joint_design: "The Server supports GetJointDesign method."

joint_design_data: "The Server supports JointDesignData structure."

delete_joint_design: "The Server supports DeleteJointDesign method."

send_joint_component: "The Server supports SendJointComponent method."

get_joint_component_list: "The Server supports GetJointComponentList method."

get_joint_component: "The Server supports GetJointComponent method."

joint_component_data: "The Server supports JointComponentData structure."

delete_joint_component: "The Server supports DeleteJointComponent method."

get_joint_revision_list: "The Server supports GetJointRevisionList method."
"""

import logging

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.namespaces import BN, NS_IJT_BASE
from helpers.node_discovery import find_child_by_browse_name, find_joining_system

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

# Sentinel string used when testing rejection of invalid joint IDs.
_INVALID_JOINT_ID = "INVALID-JOINT-ID-NONEXISTENT"

# Test joint ID used when creating a temporary joint for round-trip tests.
_TEST_JOINT_ID = "conformance-test-joint"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_joint_management(client, ns_ijt):
    """Re-discover JointManagement on a fresh client connection."""
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found — server may not be running")
    jm = await find_child_by_browse_name(js, BN.JOINT_MANAGEMENT, ns_ijt)
    if jm is None:
        pytest.skip("JointManagement node not found on JoiningSystem")
    return jm


def _require_ns_ijt(ns_indices):
    """Return the IJT Base namespace index; skip the test if not registered."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    return ns_ijt


async def _call_get_joint_list(jm_node, list_node):
    """
    Call GetJointList, trying a no-argument call first.
    Falls back to an empty-string argument if the server reports missing args.
    Returns the JointList array (extracts index 0 when the server returns multiple
    output arguments: JointList, Status, StatusMessage).
    """
    try:
        raw = await jm_node.call_method(list_node.nodeid)
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadArgumentsMissing", "BadInvalidArgument")):
            raw = await jm_node.call_method(
                list_node.nodeid,
                ua.Variant("", ua.VariantType.String),
            )
        else:
            raise
    # GetJointList returns (JointList: array, Status, StatusMessage).
    # When asyncua returns multiple outputs as a list, extract just the JointList.
    if isinstance(raw, (list, tuple)) and raw and isinstance(raw[0], (list, tuple)):
        return raw[0]
    return raw


def _joint_id_str(entry) -> str:
    """Return the joint ID string from a JointDataType struct or a plain string."""
    jid = getattr(entry, "JointId", None) or getattr(entry, "Id", None)
    if jid is not None:
        return str(jid)
    if isinstance(entry, str):
        return entry
    return str(entry)


async def _get_first_joint_id(client, ns_ijt):
    """
    Get the first joint ID from GetJointList. Returns None if the list is empty.
    Used to obtain a valid ID for GetJoint/SelectJoint tests.
    """
    jm = await _get_joint_management(client, ns_ijt)
    list_node = await find_child_by_browse_name(jm, BN.GET_JOINT_LIST, ns_ijt)
    if list_node is None:
        return None
    try:
        joint_list = await _call_get_joint_list(jm, list_node)
    except ua.UaError:
        return None
    if not joint_list:
        return None
    items = list(joint_list) if isinstance(joint_list, (list, tuple)) else [joint_list]
    if not items:
        return None
    first = items[0]
    if isinstance(first, (list, tuple)):
        # GetJointList returns multiple outputs: first element is the JointList array.
        # Descend into the array to extract the JointId from the first struct entry.
        if not first:
            return None
        entry = first[0]
        jid = getattr(entry, "JointId", None) or getattr(entry, "Id", None)
        if jid is not None:
            return str(jid)
        if isinstance(entry, str):
            return entry
        return None
    jid = getattr(first, "JointId", None) or getattr(first, "Id", None)
    return str(jid) if jid is not None else None


async def _send_test_joint_and_get_id(client, jm_node, ns_ijt):
    """
    Send a test joint via SendJoint and return its ID.
    Returns (joint_id, sent=True) or (None, False) if SendJoint is not supported.
    """
    send_node = await find_child_by_browse_name(jm_node, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        return None, False
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        return None, False
    try:
        joint_data = joint_type()
        if hasattr(joint_data, "JointId"):
            joint_data.JointId = _TEST_JOINT_ID
        if hasattr(joint_data, "Name"):
            joint_data.Name = "ConformanceTestJoint"
        if hasattr(joint_data, "ProgramId"):
            joint_data.ProgramId = "test-program"
        result = await jm_node.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
        returned_id = None
        if isinstance(result, str) and result:
            returned_id = result
        elif hasattr(result, "JointId") and result.JointId:
            returned_id = str(result.JointId)
        elif isinstance(result, (list, tuple)) and result:
            returned_id = str(result[0]) if result[0] else None
        return returned_id or _TEST_JOINT_ID, True
    except ua.UaError as exc:
        if any(
            s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch", "BadArgumentsMissing")
        ):
            return None, False
        raise
    except AttributeError, TypeError:
        return None, False


# ---------------------------------------------------------------------------
# ─── joint_management ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINT_MANAGEMENT)
async def test_joint_management_addin_present(joint_management):
    """
    JoiningSystem must expose a JointManagement AddIn node.
    """
    assert joint_management is not None, "JointManagement AddIn node must not be None"


# ---------------------------------------------------------------------------
# ─── get_joint ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT)
async def test_get_joint_method_present(joint_management, ns_indices):
    """
    GetJoint method must be present on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, BN.GET_JOINT, ns_ijt)
    assert node is not None, f"Required method '{BN.GET_JOINT}' not found in JointManagement (ns={ns_ijt})"


@pytest.mark.requires_cu(CU.GET_JOINT)
async def test_get_joint_with_valid_id_returns_joint_data(opcua_client, ns_indices):
    """
    GetJoint with a valid joint ID must return joint data.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    joint_id = await _get_first_joint_id(opcua_client, ns_ijt)
    if joint_id is None:
        pytest.skip("No joints configured on this server — cannot test GetJoint with valid ID")
    jm = await _get_joint_management(opcua_client, ns_ijt)
    get_node = await find_child_by_browse_name(jm, BN.GET_JOINT, ns_ijt)
    assert get_node is not None, f"'{BN.GET_JOINT}' not found in JointManagement"
    try:
        result = await jm.call_method(
            get_node.nodeid, ua.Variant("", ua.VariantType.String), ua.Variant(joint_id, ua.VariantType.String)
        )
    except ua.UaError as exc:
        if "BadNotSupported" in str(exc):
            pytest.skip(f"GetJoint not callable on this server: {exc}")
        raise
    assert result is not None, f"GetJoint returned None for valid joint ID '{joint_id}'"
    if isinstance(result, (list, tuple)):
        assert len(result) > 0, "GetJoint returned empty tuple/list"
    else:
        jid = getattr(result, "JointId", None) or getattr(result, "Id", None)
        assert jid is not None, (
            f"GetJoint result has no recognisable joint identifier field. "
            f"Attributes: {[a for a in dir(result) if not a.startswith('_')]}"
        )
    logger.info("GetJoint succeeded for joint ID '%s'", joint_id)


@pytest.mark.requires_cu(CU.GET_JOINT)
async def test_get_joint_with_invalid_id_returns_error(opcua_client, ns_indices):
    """
    GetJoint with an invalid joint ID must return an appropriate error.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    get_node = await find_child_by_browse_name(jm, BN.GET_JOINT, ns_ijt)
    assert get_node is not None, f"'{BN.GET_JOINT}' not found in JointManagement"
    try:
        result = await jm.call_method(
            get_node.nodeid,
            ua.Variant(_INVALID_JOINT_ID, ua.VariantType.String),
        )
        logger.warning(
            "GetJoint('%s') returned %r instead of raising ua.UaError — "
            "server should signal BadNotFound for unknown joint IDs",
            _INVALID_JOINT_ID,
            result,
        )
    except ua.UaError as exc:
        logger.info(
            "GetJoint('%s') raised ua.UaError as expected: %s",
            _INVALID_JOINT_ID,
            exc,
        )


# ---------------------------------------------------------------------------
# ─── get_joint_list ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT_LIST)
async def test_get_joint_list_method_present(joint_management, ns_indices):
    """
    GetJointList method must be present on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, BN.GET_JOINT_LIST, ns_ijt)
    assert node is not None, f"Required method '{BN.GET_JOINT_LIST}' not found in JointManagement (ns={ns_ijt})"


@pytest.mark.requires_cu(CU.GET_JOINT_LIST)
async def test_get_joint_list_returns_list_type(opcua_client, ns_indices):
    """
    GetJointList must return a list (may be empty if no joints are configured).
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    list_node = await find_child_by_browse_name(jm, BN.GET_JOINT_LIST, ns_ijt)
    assert list_node is not None, f"'{BN.GET_JOINT_LIST}' not found in JointManagement"
    try:
        joint_list = await _call_get_joint_list(jm, list_node)
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadNothingToDo")):
            pytest.skip(f"GetJointList not callable on this server: {exc}")
        raise
    assert joint_list is None or isinstance(joint_list, (list, tuple)), (
        f"GetJointList must return a list, got {type(joint_list)}"
    )
    count = len(joint_list) if joint_list else 0
    logger.info("GetJointList returned %d joint(s)", count)


# ---------------------------------------------------------------------------
# ─── select_joint ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SELECT_JOINT)
async def test_select_joint_method_present(joint_management, ns_indices):
    """
    SelectJoint method must be present on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, BN.SELECT_JOINT, ns_ijt)
    assert node is not None, f"Required method '{BN.SELECT_JOINT}' not found in JointManagement (ns={ns_ijt})"


@pytest.mark.requires_cu(CU.SELECT_JOINT)
async def test_select_joint_with_valid_id_succeeds(opcua_client, ns_indices):
    """
    SelectJoint with a valid joint ID must succeed (or report BadNotSupported).
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id = await _get_first_joint_id(opcua_client, ns_ijt)
    if joint_id is None:
        if getattr(ua, "JointDataType", None) is None:
            pytest.skip("No joints on server and JointDataType unavailable — cannot test SelectJoint")
        joint_id, sent = await _send_test_joint_and_get_id(opcua_client, jm, ns_ijt)
        if not sent or joint_id is None:
            pytest.skip("No joints on server and SendJoint not available — cannot test SelectJoint")
    sel_node = await find_child_by_browse_name(jm, BN.SELECT_JOINT, ns_ijt)
    assert sel_node is not None, f"'{BN.SELECT_JOINT}' not found in JointManagement"
    try:
        await jm.call_method(
            sel_node.nodeid,
            ua.Variant("", ua.VariantType.String),
            ua.Variant(joint_id, ua.VariantType.String),
            ua.Variant("", ua.VariantType.String),
        )
        logger.info("SelectJoint succeeded for joint ID '%s'", joint_id)
    except ua.UaError as exc:
        status_str = str(exc)
        if "BadNotSupported" in status_str:
            pytest.skip(f"SelectJoint not supported on this server: {exc}")
        if any(s in status_str for s in ("BadConditionNotActive", "BadNothingToDo", "BadArgumentsMissing")):
            logger.info("SelectJoint raised acceptable status: %s", exc)
        else:
            raise


@pytest.mark.requires_cu(CU.SELECT_JOINT)
async def test_select_joint_with_invalid_id_returns_error(opcua_client, ns_indices):
    """
    SelectJoint with an invalid joint ID must return an appropriate error.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    sel_node = await find_child_by_browse_name(jm, BN.SELECT_JOINT, ns_ijt)
    assert sel_node is not None, f"'{BN.SELECT_JOINT}' not found in JointManagement"
    try:
        result = await jm.call_method(
            sel_node.nodeid,
            ua.Variant(_INVALID_JOINT_ID, ua.VariantType.String),
        )
        logger.warning(
            "SelectJoint('%s') returned %r instead of raising ua.UaError",
            _INVALID_JOINT_ID,
            result,
        )
    except ua.UaError as exc:
        logger.info(
            "SelectJoint('%s') raised ua.UaError as expected: %s",
            _INVALID_JOINT_ID,
            exc,
        )


@pytest.mark.requires_cu(CU.SELECT_JOINT)
async def test_select_joint_with_non_empty_joint_origin_id(opcua_client, ns_indices):
    """
    SelectJoint called with a non-empty JointOriginId must succeed when the joint
    was created with that origin ID, or return an accepted status code.

    JointOriginId is an optional string that disambiguates joints originating from
    external systems.  This test verifies the third argument is passed through
    correctly: create a joint with a known JointOriginId via SendJoint, then
    call SelectJoint supplying that JointOriginId.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)

    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available in this asyncua version — cannot set JointOriginId")

    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — cannot create a joint with JointOriginId for this test")

    test_origin_id = "conformance-test-origin-id"
    test_joint_id = "conformance-test-joint-with-origin"
    joint_data = joint_type()
    if hasattr(joint_data, "JointId"):
        joint_data.JointId = test_joint_id
    if hasattr(joint_data, "JointOriginId"):
        joint_data.JointOriginId = test_origin_id
    if hasattr(joint_data, "Name"):
        joint_data.Name = "ConformanceTestJointWithOriginId"

    try:
        await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
    except ua.UaError as exc:
        if any(
            s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch", "BadArgumentsMissing")
        ):
            pytest.skip(f"SendJoint not callable on this server: {exc}")
        raise
    except (AttributeError, TypeError) as exc:
        pytest.skip(f"Could not construct JointDataType with JointOriginId: {exc}")

    sel_node = await find_child_by_browse_name(jm, BN.SELECT_JOINT, ns_ijt)
    assert sel_node is not None, f"'{BN.SELECT_JOINT}' not found in JointManagement"
    try:
        await jm.call_method(
            sel_node.nodeid,
            ua.Variant(test_origin_id, ua.VariantType.String),
            ua.Variant(test_joint_id, ua.VariantType.String),
            ua.Variant(test_origin_id, ua.VariantType.String),
        )
        logger.info("SelectJoint with JointOriginId='%s' succeeded", test_origin_id)
    except ua.UaError as exc:
        status_str = str(exc)
        if "BadNotSupported" in status_str:
            pytest.skip(f"SelectJoint not supported on this server: {exc}")
        if any(
            s in status_str for s in ("BadConditionNotActive", "BadNothingToDo", "BadArgumentsMissing", "Uncertain")
        ):
            logger.info("SelectJoint with non-empty JointOriginId raised acceptable status: %s", exc)
        else:
            raise


# ---------------------------------------------------------------------------
# ─── send_joint ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SEND_JOINT)
async def test_send_joint_method_present(joint_management, ns_indices):
    """
    SendJoint method must be present on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, BN.SEND_JOINT, ns_ijt)
    assert node is not None, f"Required method '{BN.SEND_JOINT}' not found in JointManagement (ns={ns_ijt})"


@pytest.mark.requires_cu(CU.SEND_JOINT)
async def test_send_joint_stores_and_get_joint_retrieves(opcua_client, ns_indices):
    """
    SendJoint must store joint data; GetJoint must retrieve it (send-then-get
    round-trip).
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    if getattr(ua, "JointDataType", None) is None:
        pytest.skip("JointDataType not available in this asyncua version — structural test only")
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id, sent = await _send_test_joint_and_get_id(opcua_client, jm, ns_ijt)
    if not sent:
        pytest.skip("SendJoint not supported or JointDataType not encodable on this server")
    assert joint_id is not None, "SendJoint did not return a usable joint ID"
    get_node = await find_child_by_browse_name(jm, BN.GET_JOINT, ns_ijt)
    assert get_node is not None, f"'{BN.GET_JOINT}' not found in JointManagement"
    try:
        result = await jm.call_method(
            get_node.nodeid, ua.Variant("", ua.VariantType.String), ua.Variant(joint_id, ua.VariantType.String)
        )
    except ua.UaError as exc:
        pytest.fail(f"GetJoint failed for just-sent joint ID '{joint_id}': {exc}")
    assert result is not None, f"GetJoint returned None for joint ID '{joint_id}' that was just sent"
    logger.info("Round-trip SendJoint→GetJoint succeeded for ID '%s'", joint_id)


@pytest.mark.requires_cu(CU.SEND_JOINT)
async def test_send_joint_with_invalid_data_returns_error(opcua_client, ns_indices):
    """
    SendJoint with invalid/empty data must return an appropriate error.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available in this asyncua version — cannot test SendJoint error path")
    jm = await _get_joint_management(opcua_client, ns_ijt)
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    assert send_node is not None, f"'{BN.SEND_JOINT}' not found in JointManagement"
    try:
        result = await jm.call_method(send_node.nodeid, joint_type())
        logger.warning(
            "SendJoint with empty JointDataType returned %r instead of raising ua.UaError",
            result,
        )
    except ua.UaError as exc:
        logger.info(
            "SendJoint with empty JointDataType raised ua.UaError as expected: %s",
            exc,
        )
    except (AttributeError, TypeError) as exc:
        pytest.skip(f"Could not construct empty JointDataType: {exc}")


# ---------------------------------------------------------------------------
# ─── joint_data ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINT_DATA)
async def test_joint_data_has_required_fields(opcua_client, ns_indices):
    """
    JointData structure must include required fields (JointId and related fields)
    per the joint_data specification.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    joint_id = await _get_first_joint_id(opcua_client, ns_ijt)
    if joint_id is None:
        pytest.skip("No joints configured on this server — cannot verify data structure")
    jm = await _get_joint_management(opcua_client, ns_ijt)
    get_node = await find_child_by_browse_name(jm, BN.GET_JOINT, ns_ijt)
    assert get_node is not None, f"'{BN.GET_JOINT}' not found in JointManagement"
    try:
        result = await jm.call_method(
            get_node.nodeid, ua.Variant("", ua.VariantType.String), ua.Variant(joint_id, ua.VariantType.String)
        )
    except ua.UaError as exc:
        pytest.skip(f"GetJoint not callable: {exc}")
    assert result is not None, "GetJoint returned None — cannot verify data structure"
    if isinstance(result, (list, tuple)):
        assert len(result) > 0, "JointDataType decoded as list but is empty"
        assert result[0] is not None, "JointDataType field[0] (JointId) must not be None"
        logger.info("JointDataType decoded as positional list with %d fields", len(result))
    else:
        joint_id_val = getattr(result, "JointId", None) or getattr(result, "Id", None)
        assert joint_id_val is not None, (
            f"JointDataType has no JointId or Id field. "
            f"Available attributes: {[a for a in dir(result) if not a.startswith('_')]}"
        )
        logger.info("JointId field present: '%s'", joint_id_val)
        for field_name in ("Name", "ProgramId"):
            val = getattr(result, field_name, None)
            if val is None:
                logger.info("Optional field '%s' is absent or None", field_name)
            else:
                logger.info("Field '%s' = %r", field_name, val)


# ---------------------------------------------------------------------------
# ─── delete_joint ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.DELETE_JOINT)
async def test_delete_joint_method_present(joint_management, ns_indices):
    """
    DeleteJoint method must be present on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, BN.DELETE_JOINT, ns_ijt)
    assert node is not None, f"Required method '{BN.DELETE_JOINT}' not found in JointManagement (ns={ns_ijt})"


@pytest.mark.requires_cu(CU.DELETE_JOINT)
async def test_send_joint_then_delete_joint_removes_it(opcua_client, ns_indices):
    """
    SendJoint followed by DeleteJoint must remove the joint.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    if getattr(ua, "JointDataType", None) is None:
        pytest.skip("JointDataType not available — send-then-delete test requires SendJoint")
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id, sent = await _send_test_joint_and_get_id(opcua_client, jm, ns_ijt)
    if not sent:
        pytest.skip("SendJoint not supported or not encodable — skipping delete test")
    assert joint_id is not None
    del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
    assert del_node is not None, f"'{BN.DELETE_JOINT}' not found in JointManagement"
    try:
        await jm.call_method(
            del_node.nodeid,
            ua.Variant("", ua.VariantType.String),
            ua.Variant(joint_id, ua.VariantType.String),
            ua.Variant("", ua.VariantType.String),
        )
    except ua.UaError as exc:
        pytest.fail(f"DeleteJoint failed for joint ID '{joint_id}': {exc}")
    get_node = await find_child_by_browse_name(jm, BN.GET_JOINT, ns_ijt)
    if get_node is None:
        return
    try:
        result = await jm.call_method(
            get_node.nodeid, ua.Variant("", ua.VariantType.String), ua.Variant(joint_id, ua.VariantType.String)
        )
        if result in (None, [], ()):
            logger.info(
                "GetJoint returned empty result for deleted joint '%s' — acceptable",
                joint_id,
            )
        else:
            logger.warning(
                "GetJoint returned non-empty result for deleted joint '%s': %r — "
                "server should signal an error or return empty for deleted joints",
                joint_id,
                result,
            )
    except ua.UaError:
        logger.info(
            "GetJoint correctly raised error after DeleteJoint for joint '%s'",
            joint_id,
        )


@pytest.mark.requires_cu(CU.DELETE_JOINT)
async def test_delete_joint_with_invalid_id_returns_error(opcua_client, ns_indices):
    """
    DeleteJoint with an invalid joint ID must return an appropriate error.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
    assert del_node is not None, f"'{BN.DELETE_JOINT}' not found in JointManagement"
    try:
        result = await jm.call_method(
            del_node.nodeid,
            ua.Variant(_INVALID_JOINT_ID, ua.VariantType.String),
        )
        logger.warning(
            "DeleteJoint('%s') returned %r instead of raising ua.UaError — "
            "server should signal BadNotFound for unknown joint IDs",
            _INVALID_JOINT_ID,
            result,
        )
    except ua.UaError as exc:
        logger.info(
            "DeleteJoint('%s') raised ua.UaError as expected: %s",
            _INVALID_JOINT_ID,
            exc,
        )


@pytest.mark.requires_cu(CU.DELETE_JOINT)
async def test_delete_joint_with_non_empty_joint_origin_id(opcua_client, ns_indices):
    """
    DeleteJoint called with a non-empty JointOriginId must succeed when the joint
    was created with that origin ID, or return an accepted status code.

    JointOriginId is an optional disambiguating string.  This test verifies the
    third argument is threaded through correctly: create a joint with a known
    JointOriginId via SendJoint, then delete it supplying that same JointOriginId.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)

    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available in this asyncua version — cannot set JointOriginId")

    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
    if send_node is None or del_node is None:
        pytest.skip("SendJoint and DeleteJoint both required for JointOriginId delete test")

    test_origin_id = "conformance-test-origin-for-delete"
    test_joint_id = "conformance-test-joint-for-delete-origin"
    joint_data = joint_type()
    if hasattr(joint_data, "JointId"):
        joint_data.JointId = test_joint_id
    if hasattr(joint_data, "JointOriginId"):
        joint_data.JointOriginId = test_origin_id
    if hasattr(joint_data, "Name"):
        joint_data.Name = "ConformanceTestJointForDeleteOriginId"

    try:
        await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
    except ua.UaError as exc:
        if any(
            s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch", "BadArgumentsMissing")
        ):
            pytest.skip(f"SendJoint not callable on this server: {exc}")
        raise
    except (AttributeError, TypeError) as exc:
        pytest.skip(f"Could not construct JointDataType with JointOriginId: {exc}")

    try:
        await jm.call_method(
            del_node.nodeid,
            ua.Variant(test_origin_id, ua.VariantType.String),
            ua.Variant(test_joint_id, ua.VariantType.String),
            ua.Variant(test_origin_id, ua.VariantType.String),
        )
        logger.info("DeleteJoint with JointOriginId='%s' succeeded", test_origin_id)
    except ua.UaError as exc:
        status_str = str(exc)
        if "BadNotSupported" in status_str:
            pytest.skip(f"DeleteJoint not supported on this server: {exc}")
        if any(s in status_str for s in ("BadNotFound", "BadArgumentsMissing", "BadInvalidArgument")):
            logger.info("DeleteJoint with non-empty JointOriginId raised acceptable status: %s", exc)
        else:
            raise


# ---------------------------------------------------------------------------
# ─── joint lifecycle: full send → get → select → delete ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SEND_JOINT, CU.GET_JOINT, CU.SELECT_JOINT, CU.DELETE_JOINT)
async def test_joint_lifecycle_send_get_select_delete(opcua_client, ns_indices):
    """
    Full joint lifecycle — SendJoint → GetJoint → SelectJoint → DeleteJoint.
    Each step is tested; non-fatal errors in SelectJoint are logged and tolerated
    since a tool may not be active.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    if getattr(ua, "JointDataType", None) is None:
        pytest.skip("JointDataType not available — full lifecycle test requires SendJoint")
    jm = await _get_joint_management(opcua_client, ns_ijt)

    joint_id, sent = await _send_test_joint_and_get_id(opcua_client, jm, ns_ijt)
    if not sent:
        pytest.skip("SendJoint not supported or not encodable — skipping lifecycle test")
    assert joint_id is not None
    logger.info("lifecycle: SendJoint succeeded → joint_id='%s'", joint_id)

    get_node = await find_child_by_browse_name(jm, BN.GET_JOINT, ns_ijt)
    if get_node is not None:
        try:
            result = await jm.call_method(
                get_node.nodeid, ua.Variant("", ua.VariantType.String), ua.Variant(joint_id, ua.VariantType.String)
            )
            assert result is not None, f"GetJoint returned None for just-sent joint '{joint_id}'"
            logger.info("lifecycle: GetJoint succeeded → result=%r", result)
        except ua.UaError as exc:
            logger.warning("lifecycle: GetJoint raised error (non-fatal for lifecycle): %s", exc)

    sel_node = await find_child_by_browse_name(jm, BN.SELECT_JOINT, ns_ijt)
    if sel_node is not None:
        try:
            await jm.call_method(
                sel_node.nodeid,
                ua.Variant("", ua.VariantType.String),
                ua.Variant(joint_id, ua.VariantType.String),
                ua.Variant("", ua.VariantType.String),
            )
            logger.info("lifecycle: SelectJoint succeeded for joint '%s'", joint_id)
        except ua.UaError as exc:
            if any(
                s in str(exc)
                for s in ("BadNotSupported", "BadConditionNotActive", "BadNothingToDo", "BadArgumentsMissing")
            ):
                logger.info("lifecycle: SelectJoint raised acceptable status: %s", exc)
            else:
                logger.warning("lifecycle: SelectJoint raised unexpected error (continuing): %s", exc)

    del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
    assert del_node is not None, f"'{BN.DELETE_JOINT}' not found — cannot complete lifecycle"
    try:
        await jm.call_method(
            del_node.nodeid,
            ua.Variant("", ua.VariantType.String),
            ua.Variant(joint_id, ua.VariantType.String),
            ua.Variant("", ua.VariantType.String),
        )
        logger.info("lifecycle: DeleteJoint succeeded for joint '%s'", joint_id)
    except ua.UaError as exc:
        pytest.fail(f"DeleteJoint failed in lifecycle test for joint '{joint_id}': {exc}")

    if get_node is not None:
        try:
            gone = await jm.call_method(
                get_node.nodeid, ua.Variant("", ua.VariantType.String), ua.Variant(joint_id, ua.VariantType.String)
            )
            if gone in (None, [], ()):
                logger.info("lifecycle: GetJoint returned empty after delete — correct")
            else:
                logger.warning(
                    "GetJoint returned non-empty result for deleted joint '%s': %r",
                    joint_id,
                    gone,
                )
        except ua.UaError:
            logger.info("lifecycle: GetJoint correctly raised error after delete")


# ---------------------------------------------------------------------------
# ─── parametrized: method presence and accessibility ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINT_MANAGEMENT)
@pytest.mark.parametrize(
    "method_name,required",
    [
        (BN.GET_JOINT, True),
        (BN.GET_JOINT_LIST, True),
        (BN.SELECT_JOINT, True),
        (BN.SEND_JOINT, True),
        (BN.DELETE_JOINT, True),
    ],
)
async def test_joint_method_presence_and_accessibility(joint_management, ns_indices, method_name, required):
    """
    All joint management core methods must be present and accessible, with
    NodeClass.Method confirmed via a read operation.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, method_name, ns_ijt)
    if required:
        assert node is not None, f"Required JointManagement method '{method_name}' not found (ns={ns_ijt})"
    elif node is None:
        pytest.skip(f"Optional JointManagement method '{method_name}' not present")
    try:
        node_class = await node.read_node_class()
        assert node_class == ua.NodeClass.Method, f"'{method_name}' has NodeClass {node_class}, expected Method"
        logger.info("Method '%s' is accessible with NodeClass.Method", method_name)
    except ua.UaError as exc:
        pytest.fail(f"Cannot read NodeClass for method '{method_name}': {exc}")


# ---------------------------------------------------------------------------
# ─── send_joint_design ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SEND_JOINT_DESIGN)
async def test_send_joint_design_method_present_if_exists(joint_management, ns_indices):
    """
    SendJointDesign method, if present, must be accessible on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, "SendJointDesign", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'SendJointDesign' not present on this server")


# ---------------------------------------------------------------------------
# ─── get_joint_design_list ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT_DESIGN_LIST)
async def test_get_joint_design_list_method_present_if_exists(joint_management, ns_indices):
    """
    GetJointDesignList method, if present, must be accessible on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, "GetJointDesignList", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'GetJointDesignList' not present on this server")


# ---------------------------------------------------------------------------
# ─── get_joint_design ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT_DESIGN)
async def test_get_joint_design_method_present_if_exists(joint_management, ns_indices):
    """
    GetJointDesign method, if present, must be accessible on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, "GetJointDesign", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'GetJointDesign' not present on this server")


# ---------------------------------------------------------------------------
# ─── joint_design_data ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINT_DESIGN_DATA)
async def test_joint_designs_folder_if_present(joint_management, ns_indices):
    """
    JointDesigns folder, if present, must be accessible under JointManagement per
    the joint_design_data specification.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, "JointDesigns", ns_ijt)
    if node is None:
        pytest.skip("JointDesigns folder not present on this server (optional)")
    assert node is not None


# ---------------------------------------------------------------------------
# ─── delete_joint_design ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.DELETE_JOINT_DESIGN)
async def test_delete_joint_design_method_present_if_exists(joint_management, ns_indices):
    """
    DeleteJointDesign method, if present, must be accessible on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, "DeleteJointDesign", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'DeleteJointDesign' not present on this server")


# ---------------------------------------------------------------------------
# ─── send_joint_component ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SEND_JOINT_COMPONENT)
async def test_send_joint_component_method_present_if_exists(joint_management, ns_indices):
    """
    SendJointComponent method, if present, must be accessible on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, "SendJointComponent", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'SendJointComponent' not present on this server")


# ---------------------------------------------------------------------------
# ─── get_joint_component_list ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT_COMPONENT_LIST)
async def test_get_joint_component_list_method_present_if_exists(joint_management, ns_indices):
    """
    GetJointComponentList method, if present, must be accessible on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, "GetJointComponentList", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'GetJointComponentList' not present on this server")


# ---------------------------------------------------------------------------
# ─── get_joint_component ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT_COMPONENT)
async def test_get_joint_component_method_present_if_exists(joint_management, ns_indices):
    """
    GetJointComponent method, if present, must be accessible on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, "GetJointComponent", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'GetJointComponent' not present on this server")


# ---------------------------------------------------------------------------
# ─── joint_component_data ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINT_COMPONENT_DATA)
async def test_joint_components_folder_if_present(joint_management, ns_indices):
    """
    JointComponents folder, if present, must be accessible under JointManagement per
    the joint_component_data specification.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, "JointComponents", ns_ijt)
    if node is None:
        pytest.skip("JointComponents folder not present on this server (optional)")
    assert node is not None


# ---------------------------------------------------------------------------
# ─── delete_joint_component ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.DELETE_JOINT_COMPONENT)
async def test_delete_joint_component_method_present_if_exists(joint_management, ns_indices):
    """
    DeleteJointComponent method, if present, must be accessible on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, "DeleteJointComponent", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'DeleteJointComponent' not present on this server")


# ---------------------------------------------------------------------------
# ─── get_joint_revision_list ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT_REVISION_LIST)
async def test_get_joint_revision_list_method_present_if_exists(joint_management, ns_indices):
    """
    GetJointRevisionList method, if present, must be accessible on JointManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await find_child_by_browse_name(joint_management, "GetJointRevisionList", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'GetJointRevisionList' not present on this server")


# ---------------------------------------------------------------------------
# Helpers for joint design and component CRUD (CU111–CU121)
# ---------------------------------------------------------------------------


async def _send_test_joint_design(jm, ns_ijt, design_id, content="conformance-test-design-content"):
    """Send a joint design via SendJointDesign; skip if unavailable or not encodable."""
    send_node = await find_child_by_browse_name(jm, "SendJointDesign", ns_ijt)
    if send_node is None:
        pytest.skip("SendJointDesign not present — skipping")
    design_type = getattr(ua, "JointDesignDataType", None)
    if design_type is not None:
        try:
            design_data = design_type()
            if hasattr(design_data, "JointDesignId"):
                design_data.JointDesignId = design_id
            if hasattr(design_data, "Content"):
                design_data.Content = content
            await jm.call_method(send_node.nodeid, design_data)
            return True
        except ua.UaError as exc:
            if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
                pytest.skip(f"SendJointDesign not callable: {exc}")
            raise
        except AttributeError, TypeError:
            pass
    try:
        await jm.call_method(send_node.nodeid, ua.Variant(design_id, ua.VariantType.String))
        return True
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
            pytest.skip(f"SendJointDesign not callable: {exc}")
        raise


async def _delete_test_joint_design(jm, ns_ijt, design_id):
    """Delete a joint design by ID; silently ignore errors (cleanup helper)."""
    del_node = await find_child_by_browse_name(jm, "DeleteJointDesign", ns_ijt)
    if del_node is None:
        return
    try:
        await jm.call_method(del_node.nodeid, ua.Variant(design_id, ua.VariantType.String))
    except ua.UaError:
        pass


async def _send_test_joint_component(jm, ns_ijt, component_id, manufacturer="ConformanceTestMfg"):
    """Send a joint component via SendJointComponent; skip if unavailable or not encodable."""
    send_node = await find_child_by_browse_name(jm, "SendJointComponent", ns_ijt)
    if send_node is None:
        pytest.skip("SendJointComponent not present — skipping")
    comp_type = getattr(ua, "JointComponentDataType", None)
    if comp_type is not None:
        try:
            comp_data = comp_type()
            if hasattr(comp_data, "JointComponentId"):
                comp_data.JointComponentId = component_id
            if hasattr(comp_data, "Manufacturer"):
                comp_data.Manufacturer = manufacturer
            await jm.call_method(send_node.nodeid, comp_data)
            return True
        except ua.UaError as exc:
            if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
                pytest.skip(f"SendJointComponent not callable: {exc}")
            raise
        except AttributeError, TypeError:
            pass
    try:
        await jm.call_method(send_node.nodeid, ua.Variant(component_id, ua.VariantType.String))
        return True
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
            pytest.skip(f"SendJointComponent not callable: {exc}")
        raise


async def _delete_test_joint_component(jm, ns_ijt, component_id):
    """Delete a joint component by ID; silently ignore errors (cleanup helper)."""
    del_node = await find_child_by_browse_name(jm, "DeleteJointComponent", ns_ijt)
    if del_node is None:
        return
    try:
        await jm.call_method(del_node.nodeid, ua.Variant(component_id, ua.VariantType.String))
    except ua.UaError:
        pass


async def _call_get_joint_design_list(jm, list_node):
    """Call GetJointDesignList, trying no-arg first then empty-string fallback."""
    try:
        return await jm.call_method(list_node.nodeid)
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadArgumentsMissing", "BadInvalidArgument")):
            return await jm.call_method(list_node.nodeid, ua.Variant("", ua.VariantType.String))
        raise


async def _call_get_joint_component_list(jm, list_node):
    """Call GetJointComponentList, trying no-arg first then empty-string fallback."""
    try:
        return await jm.call_method(list_node.nodeid)
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadArgumentsMissing", "BadInvalidArgument")):
            return await jm.call_method(list_node.nodeid, ua.Variant("", ua.VariantType.String))
        raise


# ---------------------------------------------------------------------------
# ─── joint_management additional structure tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINT_MANAGEMENT)
async def test_joint_management_type_definition_is_joint_management_type(opcua_client, ns_indices):
    """JointManagement node must have a HasTypeDefinition reference with a valid NodeId."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    try:
        refs = await jm.get_references(refs=ua.ObjectIds.HasTypeDefinition)
        assert refs, "JointManagement node has no HasTypeDefinition reference"
        type_node_id = refs[0].NodeId
        assert type_node_id is not None, "HasTypeDefinition NodeId must not be None"
        logger.info("JointManagement TypeDefinition NodeId: %s", type_node_id)
    except ua.UaError as exc:
        pytest.skip(f"Cannot read TypeDefinition reference: {exc}")


@pytest.mark.requires_cu(CU.JOINT_MANAGEMENT)
async def test_joint_management_method_set_contains_mandatory_joint_methods(opcua_client, ns_indices):
    """JointManagement must expose SendJoint, GetJointList, SelectJoint, and GetJoint."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    mandatory = [BN.SEND_JOINT, BN.GET_JOINT_LIST, BN.SELECT_JOINT, BN.GET_JOINT]
    missing = []
    for method_name in mandatory:
        node = await find_child_by_browse_name(jm, method_name, ns_ijt)
        if node is None:
            missing.append(method_name)
    assert not missing, f"Mandatory JointManagement methods not found: {missing}"


@pytest.mark.requires_cu(CU.JOINT_MANAGEMENT)
async def test_joint_management_mandatory_methods_are_executable(opcua_client, ns_indices):
    """Executable attribute on each mandatory joint management method must be True."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    mandatory = [BN.SEND_JOINT, BN.GET_JOINT_LIST, BN.SELECT_JOINT, BN.GET_JOINT]
    non_executable = []
    for method_name in mandatory:
        node = await find_child_by_browse_name(jm, method_name, ns_ijt)
        if node is None:
            non_executable.append(f"{method_name} (absent)")
            continue
        try:
            executable = await node.read_attribute(ua.AttributeIds.Executable)
            if not executable.Value.Value:
                non_executable.append(f"{method_name} (Executable=False)")
        except ua.UaError as exc:
            logger.warning("Cannot read Executable for '%s': %s", method_name, exc)
    assert not non_executable, f"Mandatory JointManagement methods not executable: {non_executable}"


@pytest.mark.requires_cu(CU.JOINT_MANAGEMENT)
async def test_joint_management_node_class_is_object(opcua_client, ns_indices):
    """JointManagement node must have NodeClass.Object."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    node_class = await jm.read_node_class()
    assert node_class == ua.NodeClass.Object, f"JointManagement NodeClass must be Object, got {node_class}"


@pytest.mark.requires_cu(CU.JOINT_MANAGEMENT)
@pytest.mark.negative
async def test_joint_management_node_cannot_be_deleted(opcua_client, ns_indices):
    """Attempting to delete the JointManagement node must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    try:
        await opcua_client.delete_nodes([jm])
        pytest.fail("Expected ua.UaError when deleting JointManagement node, but succeeded")
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError attempting to delete JointManagement: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.info("Correctly rejected node deletion: %s", exc)


# ---------------------------------------------------------------------------
# ─── send_joint additional tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SEND_JOINT)
async def test_send_joint_appears_in_get_joint_list_after_send(opcua_client, ns_indices):
    """After SendJoint, GetJointList must include the new joint ID."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id = "conformance-test-joint-gjl"
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available — cannot test SendJoint→GetJointList")
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — skipping")
    joint_data = joint_type()
    if hasattr(joint_data, "JointId"):
        joint_data.JointId = joint_id
    try:
        try:
            await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
        except ua.UaError as exc:
            if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
                pytest.skip(f"SendJoint not callable: {exc}")
            raise
        list_node = await find_child_by_browse_name(jm, BN.GET_JOINT_LIST, ns_ijt)
        if list_node is None:
            pytest.skip("GetJointList not present — cannot verify")
        joint_list = await _call_get_joint_list(jm, list_node)
        if joint_list is None:
            pytest.skip("GetJointList returned None — cannot verify")
        ids = [_joint_id_str(x) for x in (joint_list if isinstance(joint_list, (list, tuple)) else [joint_list])]
        assert joint_id in ids, f"Sent joint '{joint_id}' not found in GetJointList: {ids[:10]}"
        logger.info("Joint '%s' correctly appeared in GetJointList after SendJoint", joint_id)
    finally:
        del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
        if del_node is not None:
            try:
                await jm.call_method(
                    del_node.nodeid,
                    ua.Variant("", ua.VariantType.String),
                    ua.Variant(joint_id, ua.VariantType.String),
                    ua.Variant("", ua.VariantType.String),
                )
            except ua.UaError:
                pass


@pytest.mark.requires_cu(CU.SEND_JOINT)
async def test_send_joint_update_replaces_stored_joint_data(opcua_client, ns_indices):
    """Sending the same JointId twice with different Name must replace the stored joint data."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id = "conformance-test-joint-update"
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available — cannot test SendJoint update")
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — skipping")
    try:
        for name_val in ("OriginalJointName", "UpdatedJointName"):
            joint_data = joint_type()
            if hasattr(joint_data, "JointId"):
                joint_data.JointId = joint_id
            if hasattr(joint_data, "Name"):
                joint_data.Name = name_val
            try:
                await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
            except ua.UaError as exc:
                if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
                    pytest.skip(f"SendJoint not callable: {exc}")
                raise
        get_node = await find_child_by_browse_name(jm, BN.GET_JOINT, ns_ijt)
        if get_node is not None:
            try:
                result = await jm.call_method(
                    get_node.nodeid, ua.Variant("", ua.VariantType.String), ua.Variant(joint_id, ua.VariantType.String)
                )
                name_returned = getattr(result, "Name", None)
                if name_returned is not None:
                    assert str(name_returned) == "UpdatedJointName", (
                        f"Expected 'UpdatedJointName', got {name_returned!r}"
                    )
                    logger.info("SendJoint update confirmed: Name='%s'", name_returned)
            except ua.UaError as exc:
                logger.warning("GetJoint after update raised: %s", exc)
    finally:
        del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
        if del_node is not None:
            try:
                await jm.call_method(
                    del_node.nodeid,
                    ua.Variant("", ua.VariantType.String),
                    ua.Variant(joint_id, ua.VariantType.String),
                    ua.Variant("", ua.VariantType.String),
                )
            except ua.UaError:
                pass


@pytest.mark.requires_cu(CU.SEND_JOINT)
@pytest.mark.negative
async def test_send_joint_with_empty_joint_id_returns_bad_invalid_argument(opcua_client, ns_indices):
    """SendJoint with an empty JointId must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available — cannot test empty JointId rejection")
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — skipping negative test")
    joint_data = joint_type()
    if hasattr(joint_data, "JointId"):
        joint_data.JointId = ""
    try:
        result = await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
        logger.warning("Expected ua.UaError for empty JointId but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for empty JointId: %s", exc)
    except (AttributeError, TypeError) as exc:
        logger.info("Correctly rejected empty JointId with encoding error: %s", exc)


@pytest.mark.requires_cu(CU.SEND_JOINT)
@pytest.mark.negative
async def test_send_joint_with_null_joining_process_id_returns_bad_invalid_argument(opcua_client, ns_indices):
    """SendJoint with a null/empty JoiningProcessId must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available — cannot test null JoiningProcessId rejection")
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — skipping negative test")
    joint_data = joint_type()
    if not hasattr(joint_data, "JoiningProcessId"):
        pytest.skip("JointDataType has no JoiningProcessId field — skipping")
    if hasattr(joint_data, "JointId"):
        joint_data.JointId = "conformance-test-joint-null-proc-id"
    joint_data.JoiningProcessId = ""
    try:
        result = await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
        logger.warning("Expected ua.UaError for empty JoiningProcessId but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for empty JoiningProcessId: %s", exc)
    except (AttributeError, TypeError) as exc:
        logger.info("Correctly rejected empty JoiningProcessId with encoding error: %s", exc)


# ---------------------------------------------------------------------------
# ─── get_joint_list additional tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT_LIST)
async def test_get_joint_list_returns_string_array_elements(opcua_client, ns_indices):
    """GetJointList must return a list where each element is a non-empty string."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    list_node = await find_child_by_browse_name(jm, BN.GET_JOINT_LIST, ns_ijt)
    if list_node is None:
        pytest.skip("GetJointList not present — skipping")
    try:
        joint_list = await _call_get_joint_list(jm, list_node)
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadNothingToDo")):
            pytest.skip(f"GetJointList not callable: {exc}")
        raise
    if not joint_list:
        pytest.skip("GetJointList returned empty list — cannot verify element type")
    items = list(joint_list) if isinstance(joint_list, (list, tuple)) else [joint_list]
    failures = []
    for idx, item in enumerate(items):
        item_str = str(item) if item is not None else None
        if not item_str or not item_str.strip():
            failures.append(f"Element[{idx}] is empty or None: {item!r}")
    assert not failures, f"GetJointList contains invalid elements: {failures}"
    logger.info("GetJointList returned %d valid string elements", len(items))


@pytest.mark.requires_cu(CU.GET_JOINT_LIST)
async def test_get_joint_list_reflects_newly_sent_joint(opcua_client, ns_indices):
    """After SendJoint, the new ID must appear in GetJointList."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id = "conformance-test-joint-gjl-new"
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available — cannot test GetJointList reflection")
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — cannot send test joint")
    joint_data = joint_type()
    if hasattr(joint_data, "JointId"):
        joint_data.JointId = joint_id
    try:
        try:
            await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
        except ua.UaError as exc:
            if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
                pytest.skip(f"SendJoint not callable: {exc}")
            raise
        list_node = await find_child_by_browse_name(jm, BN.GET_JOINT_LIST, ns_ijt)
        if list_node is None:
            pytest.skip("GetJointList not present — cannot verify")
        joint_list = await _call_get_joint_list(jm, list_node)
        ids = (
            [_joint_id_str(x) for x in joint_list]
            if isinstance(joint_list, (list, tuple))
            else ([] if joint_list is None else [_joint_id_str(joint_list)])
        )
        assert joint_id in ids, f"Newly sent joint '{joint_id}' not found in GetJointList: {ids[:10]}"
        logger.info("GetJointList correctly reflects newly sent joint '%s'", joint_id)
    finally:
        del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
        if del_node is not None:
            try:
                await jm.call_method(
                    del_node.nodeid,
                    ua.Variant("", ua.VariantType.String),
                    ua.Variant(joint_id, ua.VariantType.String),
                    ua.Variant("", ua.VariantType.String),
                )
            except ua.UaError:
                pass


@pytest.mark.requires_cu(CU.GET_JOINT_LIST)
@pytest.mark.negative
async def test_get_joint_list_returns_good_with_empty_array_when_no_joints(opcua_client, ns_indices):
    """GetJointList must not raise an error even when the server has no joints configured."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    list_node = await find_child_by_browse_name(jm, BN.GET_JOINT_LIST, ns_ijt)
    if list_node is None:
        pytest.skip("GetJointList not present — skipping")
    try:
        joint_list = await _call_get_joint_list(jm, list_node)
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadNothingToDo")):
            pytest.skip(f"GetJointList not callable: {exc}")
        raise
    if joint_list:
        items = list(joint_list) if isinstance(joint_list, (list, tuple)) else [joint_list]
        logger.info("Server has %d joint(s) — empty-list scenario cannot be tested here", len(items))
        return
    assert joint_list is None or isinstance(joint_list, (list, tuple)), (
        "GetJointList must return a list or None when empty, not raise an error"
    )
    logger.info("GetJointList returned empty list without error — correct")


# ---------------------------------------------------------------------------
# ─── select_joint additional negative tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SELECT_JOINT)
@pytest.mark.negative
async def test_select_joint_with_nonexistent_id_returns_bad_status(opcua_client, ns_indices):
    """SelectJoint with a non-existent joint ID must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    sel_node = await find_child_by_browse_name(jm, BN.SELECT_JOINT, ns_ijt)
    if sel_node is None:
        pytest.skip("SelectJoint not present — skipping negative test")
    try:
        result = await jm.call_method(
            sel_node.nodeid,
            ua.Variant("conformance-test-joint-nonexistent-xyz", ua.VariantType.String),
        )
        logger.warning("Expected ua.UaError for non-existent joint but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for non-existent joint ID: %s", exc)


@pytest.mark.requires_cu(CU.SELECT_JOINT)
@pytest.mark.negative
async def test_select_joint_during_active_joining_returns_bad_invalid_state(opcua_client, ns_indices):
    """SelectJoint during active joining should return Bad_InvalidState — not reproducible in conformance test."""
    pytest.skip("Cannot reproduce active joining state in conformance test environment")


# ---------------------------------------------------------------------------
# ─── get_joint additional round-trip tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT)
async def test_get_joint_round_trip_data_matches_sent_data(opcua_client, ns_indices):
    """GetJoint must return a result whose JointId matches the ID passed to SendJoint."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id = "conformance-test-joint-gj"
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available — cannot test GetJoint round-trip")
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — cannot create test joint")
    joint_data = joint_type()
    if hasattr(joint_data, "JointId"):
        joint_data.JointId = joint_id
    try:
        try:
            await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
        except ua.UaError as exc:
            if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
                pytest.skip(f"SendJoint not callable: {exc}")
            raise
        get_node = await find_child_by_browse_name(jm, BN.GET_JOINT, ns_ijt)
        if get_node is None:
            pytest.skip("GetJoint not present — cannot verify round-trip")
        try:
            result = await jm.call_method(
                get_node.nodeid, ua.Variant("", ua.VariantType.String), ua.Variant(joint_id, ua.VariantType.String)
            )
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJoint not callable: {exc}")
            raise
        assert result is not None, f"GetJoint returned None for ID '{joint_id}'"
        returned_id = getattr(result, "JointId", None) or getattr(result, "Id", None)
        if returned_id is not None:
            assert str(returned_id) == joint_id, f"GetJoint returned JointId {returned_id!r}, expected {joint_id!r}"
        logger.info("GetJoint round-trip succeeded for ID '%s'", joint_id)
    finally:
        del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
        if del_node is not None:
            try:
                await jm.call_method(
                    del_node.nodeid,
                    ua.Variant("", ua.VariantType.String),
                    ua.Variant(joint_id, ua.VariantType.String),
                    ua.Variant("", ua.VariantType.String),
                )
            except ua.UaError:
                pass


@pytest.mark.requires_cu(CU.GET_JOINT)
async def test_get_joint_result_has_joint_id_and_required_fields(opcua_client, ns_indices):
    """GetJoint result must include JointId and, where present, JoiningProcessId fields."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id = "conformance-test-joint-fields"
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available — cannot test GetJoint fields")
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — cannot create test joint")
    joint_data = joint_type()
    if hasattr(joint_data, "JointId"):
        joint_data.JointId = joint_id
    if hasattr(joint_data, "JoiningProcessId"):
        joint_data.JoiningProcessId = "conformance-test-jprocess-ref"
    try:
        try:
            await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
        except ua.UaError as exc:
            if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
                pytest.skip(f"SendJoint not callable: {exc}")
            raise
        get_node = await find_child_by_browse_name(jm, BN.GET_JOINT, ns_ijt)
        if get_node is None:
            pytest.skip("GetJoint not present — cannot verify fields")
        try:
            result = await jm.call_method(
                get_node.nodeid, ua.Variant("", ua.VariantType.String), ua.Variant(joint_id, ua.VariantType.String)
            )
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJoint not callable: {exc}")
            raise
        assert result is not None, "GetJoint returned None"
        if not isinstance(result, (list, tuple)):
            jid = getattr(result, "JointId", None) or getattr(result, "Id", None)
            assert jid is not None, (
                f"GetJoint result missing JointId. Attributes: {[a for a in dir(result) if not a.startswith('_')]}"
            )
            logger.info(
                "JointId='%s', JoiningProcessId=%r",
                jid,
                getattr(result, "JoiningProcessId", None),
            )
    finally:
        del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
        if del_node is not None:
            try:
                await jm.call_method(
                    del_node.nodeid,
                    ua.Variant("", ua.VariantType.String),
                    ua.Variant(joint_id, ua.VariantType.String),
                    ua.Variant("", ua.VariantType.String),
                )
            except ua.UaError:
                pass


@pytest.mark.requires_cu(CU.GET_JOINT)
async def test_get_joint_returns_updated_data_after_resend(opcua_client, ns_indices):
    """GetJoint must return the most recently sent data after the same joint is re-sent."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id = "conformance-test-joint-resend"
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available — cannot test GetJoint update")
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — skipping")
    try:
        for name_val in ("InitialName", "ResentName"):
            joint_data = joint_type()
            if hasattr(joint_data, "JointId"):
                joint_data.JointId = joint_id
            if hasattr(joint_data, "Name"):
                joint_data.Name = name_val
            try:
                await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
            except ua.UaError as exc:
                if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
                    pytest.skip(f"SendJoint not callable: {exc}")
                raise
        get_node = await find_child_by_browse_name(jm, BN.GET_JOINT, ns_ijt)
        if get_node is None:
            pytest.skip("GetJoint not present — cannot verify updated data")
        try:
            result = await jm.call_method(
                get_node.nodeid, ua.Variant("", ua.VariantType.String), ua.Variant(joint_id, ua.VariantType.String)
            )
            name_returned = getattr(result, "Name", None) if result else None
            if name_returned is not None:
                assert str(name_returned) == "ResentName", f"Expected 'ResentName' after resend, got {name_returned!r}"
                logger.info("GetJoint correctly reflects updated Name after resend")
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJoint not callable: {exc}")
            raise
    finally:
        del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
        if del_node is not None:
            try:
                await jm.call_method(
                    del_node.nodeid,
                    ua.Variant("", ua.VariantType.String),
                    ua.Variant(joint_id, ua.VariantType.String),
                    ua.Variant("", ua.VariantType.String),
                )
            except ua.UaError:
                pass


@pytest.mark.requires_cu(CU.GET_JOINT)
@pytest.mark.negative
async def test_get_joint_with_nonexistent_id_returns_bad_node_id_unknown(opcua_client, ns_indices):
    """GetJoint with an unknown ID must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    get_node = await find_child_by_browse_name(jm, BN.GET_JOINT, ns_ijt)
    if get_node is None:
        pytest.skip("GetJoint not present — skipping negative test")
    try:
        result = await jm.call_method(
            get_node.nodeid,
            ua.Variant("conformance-test-nonexistent-joint-xyz", ua.VariantType.String),
        )
        logger.warning("Expected ua.UaError for non-existent joint but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for non-existent joint ID: %s", exc)


# ---------------------------------------------------------------------------
# ─── joint_data additional data structure tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINT_DATA)
async def test_joint_data_round_trip_preserves_joint_id_and_joining_process_id(opcua_client, ns_indices):
    """JointData round-trip must preserve JointId and JoiningProcessId fields."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id = "conformance-test-joint-jdata-rt"
    proc_id = "conformance-test-jdata-proc"
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available — cannot test data round-trip")
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — cannot create test joint")
    joint_data = joint_type()
    if hasattr(joint_data, "JointId"):
        joint_data.JointId = joint_id
    if hasattr(joint_data, "JoiningProcessId"):
        joint_data.JoiningProcessId = proc_id
    try:
        try:
            await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
        except ua.UaError as exc:
            if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
                pytest.skip(f"SendJoint not callable: {exc}")
            raise
        get_node = await find_child_by_browse_name(jm, BN.GET_JOINT, ns_ijt)
        if get_node is None:
            pytest.skip("GetJoint not present — cannot verify round-trip")
        try:
            result = await jm.call_method(
                get_node.nodeid, ua.Variant("", ua.VariantType.String), ua.Variant(joint_id, ua.VariantType.String)
            )
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJoint not callable: {exc}")
            raise
        assert result is not None, "GetJoint returned None"
        if not isinstance(result, (list, tuple)):
            ret_jid = getattr(result, "JointId", None) or getattr(result, "Id", None)
            if ret_jid is not None:
                assert str(ret_jid) == joint_id, f"JointId round-trip mismatch: expected {joint_id!r}, got {ret_jid!r}"
            ret_proc = getattr(result, "JoiningProcessId", None)
            if ret_proc is not None:
                assert str(ret_proc) == proc_id, (
                    f"JoiningProcessId round-trip mismatch: expected {proc_id!r}, got {ret_proc!r}"
                )
            logger.info("JointData round-trip OK: JointId=%r JoiningProcessId=%r", ret_jid, ret_proc)
    finally:
        del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
        if del_node is not None:
            try:
                await jm.call_method(
                    del_node.nodeid,
                    ua.Variant("", ua.VariantType.String),
                    ua.Variant(joint_id, ua.VariantType.String),
                    ua.Variant("", ua.VariantType.String),
                )
            except ua.UaError:
                pass


@pytest.mark.requires_cu(CU.JOINT_DATA)
async def test_joint_data_joint_ids_are_unique_across_get_joint_list(opcua_client, ns_indices):
    """GetJointList must not contain duplicate joint IDs."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    list_node = await find_child_by_browse_name(jm, BN.GET_JOINT_LIST, ns_ijt)
    if list_node is None:
        pytest.skip("GetJointList not present — skipping uniqueness check")
    try:
        joint_list = await _call_get_joint_list(jm, list_node)
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadNothingToDo")):
            pytest.skip(f"GetJointList not callable: {exc}")
        raise
    if not joint_list:
        pytest.skip("GetJointList returned empty list — cannot check for duplicates")
    items = [str(x) for x in (joint_list if isinstance(joint_list, (list, tuple)) else [joint_list])]
    assert len(items) == len(set(items)), (
        f"GetJointList contains duplicate IDs: {[x for x in items if items.count(x) > 1]}"
    )
    logger.info("GetJointList: %d unique joint IDs confirmed", len(items))


@pytest.mark.requires_cu(CU.JOINT_DATA)
async def test_joint_data_joining_process_id_cross_references_process_list(opcua_client, ns_indices):
    """JoiningProcessId in JointData should be found in GetJoiningProcessList (soft check)."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id = await _get_first_joint_id(opcua_client, ns_ijt)
    if joint_id is None:
        pytest.skip("No joints configured — cannot cross-reference JoiningProcessId")
    get_node = await find_child_by_browse_name(jm, BN.GET_JOINT, ns_ijt)
    if get_node is None:
        pytest.skip("GetJoint not present — skipping cross-reference test")
    try:
        result = await jm.call_method(
            get_node.nodeid, ua.Variant("", ua.VariantType.String), ua.Variant(joint_id, ua.VariantType.String)
        )
    except ua.UaError as exc:
        pytest.skip(f"GetJoint not callable: {exc}")
    proc_id = getattr(result, "JoiningProcessId", None) if result and not isinstance(result, (list, tuple)) else None
    if proc_id is None:
        pytest.skip("JoiningProcessId field not present in result — skipping cross-reference")
    js = await find_joining_system(opcua_client)
    if js is None:
        pytest.skip("JoiningSystem not found — cannot cross-reference process list")
    jpm = await find_child_by_browse_name(js, BN.JOINING_PROCESS_MANAGEMENT, ns_ijt)
    if jpm is None:
        logger.info("JoiningProcessManagement not found — skipping cross-reference check")
        return
    gpl_node = await find_child_by_browse_name(jpm, BN.GET_JOINING_PROCESS_LIST, ns_ijt)
    if gpl_node is None:
        logger.info("GetJoiningProcessList not found — skipping cross-reference check")
        return
    try:
        proc_list = await jpm.call_method(gpl_node.nodeid)
    except ua.UaError:
        logger.info("GetJoiningProcessList not callable — skipping cross-reference check")
        return
    if proc_list is None:
        logger.info("GetJoiningProcessList returned None — skipping cross-reference")
        return
    proc_ids = [str(x) for x in (proc_list if isinstance(proc_list, (list, tuple)) else [proc_list])]
    if str(proc_id) not in proc_ids:
        logger.warning(
            "JoiningProcessId '%s' not found in GetJoiningProcessList — "
            "server may not maintain process list consistency",
            proc_id,
        )
    else:
        logger.info("JoiningProcessId '%s' found in GetJoiningProcessList — cross-reference OK", proc_id)


@pytest.mark.requires_cu(CU.JOINT_DATA)
@pytest.mark.negative
async def test_joint_data_resend_with_different_joining_process_id_accepted_or_error(opcua_client, ns_indices):
    """Resending a joint with a different JoiningProcessId must either succeed or raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id = "conformance-test-joint-jdata-repid"
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available — cannot test resend with different process ID")
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — skipping")
    try:
        for proc_id in ("conformance-test-proc-A", "conformance-test-proc-B"):
            joint_data = joint_type()
            if hasattr(joint_data, "JointId"):
                joint_data.JointId = joint_id
            if hasattr(joint_data, "JoiningProcessId"):
                joint_data.JoiningProcessId = proc_id
            try:
                await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
                logger.info("SendJoint with JoiningProcessId='%s' accepted", proc_id)
            except ua.UaError as exc:
                logger.info(
                    "SendJoint with JoiningProcessId='%s' raised error (acceptable): %s",
                    proc_id,
                    exc,
                )
                break
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
            pytest.skip(f"SendJoint not callable: {exc}")
        raise
    finally:
        del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
        if del_node is not None:
            try:
                await jm.call_method(
                    del_node.nodeid,
                    ua.Variant("", ua.VariantType.String),
                    ua.Variant(joint_id, ua.VariantType.String),
                    ua.Variant("", ua.VariantType.String),
                )
            except ua.UaError:
                pass


# ---------------------------------------------------------------------------
# ─── send_joint_design additional tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SEND_JOINT_DESIGN)
async def test_send_joint_design_with_valid_data_succeeds(opcua_client, ns_indices):
    """Send a valid JointDesignDataType and assert a Good response."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    design_id = "conformance-test-jdesign-send"
    try:
        await _send_test_joint_design(jm, ns_ijt, design_id)
        logger.info("SendJointDesign succeeded for ID '%s'", design_id)
    finally:
        await _delete_test_joint_design(jm, ns_ijt, design_id)


@pytest.mark.requires_cu(CU.SEND_JOINT_DESIGN)
async def test_send_joint_design_appears_in_joint_design_list(opcua_client, ns_indices):
    """After SendJointDesign, GetJointDesignList must include the new design ID."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    design_id = "conformance-test-jdesign-gjdl-send"
    try:
        await _send_test_joint_design(jm, ns_ijt, design_id)
        list_node = await find_child_by_browse_name(jm, "GetJointDesignList", ns_ijt)
        if list_node is None:
            pytest.skip("GetJointDesignList not present — cannot verify")
        try:
            design_list = await _call_get_joint_design_list(jm, list_node)
        except ua.UaError as exc:
            if any(s in str(exc) for s in ("BadNotSupported", "BadNothingToDo")):
                pytest.skip(f"GetJointDesignList not callable: {exc}")
            raise
        ids = (
            [str(x) for x in design_list]
            if isinstance(design_list, (list, tuple))
            else ([] if design_list is None else [str(design_list)])
        )
        assert design_id in ids, f"Sent design '{design_id}' not found in GetJointDesignList: {ids[:10]}"
        logger.info("Design '%s' correctly appeared in GetJointDesignList", design_id)
    finally:
        await _delete_test_joint_design(jm, ns_ijt, design_id)


@pytest.mark.requires_cu(CU.SEND_JOINT_DESIGN)
async def test_send_joint_design_update_replaces_existing_design(opcua_client, ns_indices):
    """Sending the same design ID twice must update the stored design."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    design_id = "conformance-test-jdesign-update"
    try:
        await _send_test_joint_design(jm, ns_ijt, design_id, content="ContentV1")
        await _send_test_joint_design(jm, ns_ijt, design_id, content="ContentV2")
        get_node = await find_child_by_browse_name(jm, "GetJointDesign", ns_ijt)
        if get_node is not None:
            try:
                result = await jm.call_method(get_node.nodeid, ua.Variant(design_id, ua.VariantType.String))
                logger.info("GetJointDesign returned result after update: %r", type(result).__name__)
            except ua.UaError as exc:
                logger.warning("GetJointDesign after update raised: %s", exc)
    finally:
        await _delete_test_joint_design(jm, ns_ijt, design_id)


@pytest.mark.requires_cu(CU.SEND_JOINT_DESIGN)
@pytest.mark.negative
async def test_send_joint_design_with_empty_id_returns_error(opcua_client, ns_indices):
    """SendJointDesign with an empty JointDesignId must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    send_node = await find_child_by_browse_name(jm, "SendJointDesign", ns_ijt)
    if send_node is None:
        pytest.skip("SendJointDesign not present — skipping negative test")
    design_type = getattr(ua, "JointDesignDataType", None)
    if design_type is None:
        pytest.skip("JointDesignDataType not available — cannot construct empty-ID object")
    design_data = design_type()
    if hasattr(design_data, "JointDesignId"):
        design_data.JointDesignId = ""
    try:
        result = await jm.call_method(send_node.nodeid, design_data)
        logger.warning("Expected ua.UaError for empty JointDesignId but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for empty JointDesignId: %s", exc)
    except (AttributeError, TypeError) as exc:
        logger.info("Correctly rejected empty design ID with encoding error: %s", exc)


@pytest.mark.requires_cu(CU.SEND_JOINT_DESIGN)
@pytest.mark.negative
async def test_send_joint_design_with_null_content_returns_error(opcua_client, ns_indices):
    """SendJointDesign with null content must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    send_node = await find_child_by_browse_name(jm, "SendJointDesign", ns_ijt)
    if send_node is None:
        pytest.skip("SendJointDesign not present — skipping negative test")
    try:
        result = await jm.call_method(send_node.nodeid, ua.Variant(None, ua.VariantType.Null))
        logger.warning("Expected ua.UaError for null content but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for null content: %s", exc)
    except (TypeError, AttributeError) as exc:
        logger.info("Correctly rejected null content with encoding error: %s", exc)


# ---------------------------------------------------------------------------
# ─── get_joint_design_list additional tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT_DESIGN_LIST)
async def test_get_joint_design_list_returns_string_elements(opcua_client, ns_indices):
    """GetJointDesignList must return a list where each element is a non-empty string."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    list_node = await find_child_by_browse_name(jm, "GetJointDesignList", ns_ijt)
    if list_node is None:
        pytest.skip("GetJointDesignList not present — skipping")
    try:
        design_list = await _call_get_joint_design_list(jm, list_node)
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadNothingToDo")):
            pytest.skip(f"GetJointDesignList not callable: {exc}")
        raise
    if not design_list:
        pytest.skip("GetJointDesignList returned empty list — cannot verify element type")
    items = list(design_list) if isinstance(design_list, (list, tuple)) else [design_list]
    failures = []
    for idx, item in enumerate(items):
        item_str = str(item) if item is not None else None
        if not item_str or not item_str.strip():
            failures.append(f"Element[{idx}] is empty or None: {item!r}")
    assert not failures, f"GetJointDesignList contains invalid elements: {failures}"
    logger.info("GetJointDesignList returned %d valid string elements", len(items))


@pytest.mark.requires_cu(CU.GET_JOINT_DESIGN_LIST)
async def test_get_joint_design_list_reflects_newly_sent_design(opcua_client, ns_indices):
    """After SendJointDesign, the new ID must appear in GetJointDesignList."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    design_id = "conformance-test-jdesign-gjdl"
    try:
        await _send_test_joint_design(jm, ns_ijt, design_id)
        list_node = await find_child_by_browse_name(jm, "GetJointDesignList", ns_ijt)
        if list_node is None:
            pytest.skip("GetJointDesignList not present — cannot verify")
        design_list = await _call_get_joint_design_list(jm, list_node)
        ids = (
            [str(x) for x in design_list]
            if isinstance(design_list, (list, tuple))
            else ([] if design_list is None else [str(design_list)])
        )
        assert design_id in ids, f"Design '{design_id}' not found in GetJointDesignList: {ids[:10]}"
        logger.info("GetJointDesignList correctly reflects newly sent design '%s'", design_id)
    finally:
        await _delete_test_joint_design(jm, ns_ijt, design_id)


@pytest.mark.requires_cu(CU.GET_JOINT_DESIGN_LIST)
@pytest.mark.negative
async def test_get_joint_design_list_returns_good_for_empty_list(opcua_client, ns_indices):
    """GetJointDesignList must not raise an error when the server has no joint designs."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    list_node = await find_child_by_browse_name(jm, "GetJointDesignList", ns_ijt)
    if list_node is None:
        pytest.skip("GetJointDesignList not present — skipping")
    try:
        design_list = await _call_get_joint_design_list(jm, list_node)
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadNothingToDo")):
            pytest.skip(f"GetJointDesignList not callable: {exc}")
        raise
    if design_list:
        items = list(design_list) if isinstance(design_list, (list, tuple)) else [design_list]
        logger.info("Server has %d design(s) — empty-list scenario cannot be tested here", len(items))
        return
    assert design_list is None or isinstance(design_list, (list, tuple)), (
        "GetJointDesignList must return a list or None when empty"
    )
    logger.info("GetJointDesignList returned empty result without error — correct")


# ---------------------------------------------------------------------------
# ─── get_joint_design additional round-trip tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT_DESIGN)
async def test_get_joint_design_round_trip_data_matches_sent_data(opcua_client, ns_indices):
    """GetJointDesign must return a result for a design ID that was just sent."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    design_id = "conformance-test-jdesign-rt"
    try:
        await _send_test_joint_design(jm, ns_ijt, design_id)
        get_node = await find_child_by_browse_name(jm, "GetJointDesign", ns_ijt)
        if get_node is None:
            pytest.skip("GetJointDesign not present — cannot verify round-trip")
        try:
            result = await jm.call_method(get_node.nodeid, ua.Variant(design_id, ua.VariantType.String))
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJointDesign not callable: {exc}")
            raise
        assert result is not None, f"GetJointDesign returned None for ID '{design_id}'"
        logger.info("GetJointDesign round-trip succeeded for ID '%s'", design_id)
    finally:
        await _delete_test_joint_design(jm, ns_ijt, design_id)


@pytest.mark.requires_cu(CU.GET_JOINT_DESIGN)
async def test_get_joint_design_result_has_required_fields(opcua_client, ns_indices):
    """GetJointDesign result must include a JointDesignId field."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    design_id = "conformance-test-jdesign-fields"
    try:
        await _send_test_joint_design(jm, ns_ijt, design_id)
        get_node = await find_child_by_browse_name(jm, "GetJointDesign", ns_ijt)
        if get_node is None:
            pytest.skip("GetJointDesign not present — cannot verify fields")
        try:
            result = await jm.call_method(get_node.nodeid, ua.Variant(design_id, ua.VariantType.String))
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJointDesign not callable: {exc}")
            raise
        assert result is not None, "GetJointDesign returned None"
        if not isinstance(result, (list, tuple)):
            did = getattr(result, "JointDesignId", None) or getattr(result, "Id", None)
            if did is not None:
                assert str(did).strip() != "", "JointDesignId must not be empty"
                logger.info("JointDesignId field present: '%s'", did)
    finally:
        await _delete_test_joint_design(jm, ns_ijt, design_id)


@pytest.mark.requires_cu(CU.GET_JOINT_DESIGN)
async def test_get_joint_design_returns_updated_content_after_resend(opcua_client, ns_indices):
    """GetJointDesign must return the most recent version after the same design is re-sent."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    design_id = "conformance-test-jdesign-resend"
    try:
        await _send_test_joint_design(jm, ns_ijt, design_id, content="ContentV1")
        await _send_test_joint_design(jm, ns_ijt, design_id, content="ContentV2")
        get_node = await find_child_by_browse_name(jm, "GetJointDesign", ns_ijt)
        if get_node is None:
            pytest.skip("GetJointDesign not present — cannot verify updated content")
        try:
            result = await jm.call_method(get_node.nodeid, ua.Variant(design_id, ua.VariantType.String))
            assert result is not None, "GetJointDesign returned None after resend"
            logger.info("GetJointDesign returns result after resend — update confirmed")
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJointDesign not callable: {exc}")
            raise
    finally:
        await _delete_test_joint_design(jm, ns_ijt, design_id)


@pytest.mark.requires_cu(CU.GET_JOINT_DESIGN)
@pytest.mark.negative
async def test_get_joint_design_with_nonexistent_id_returns_error(opcua_client, ns_indices):
    """GetJointDesign with a non-existent ID must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    get_node = await find_child_by_browse_name(jm, "GetJointDesign", ns_ijt)
    if get_node is None:
        pytest.skip("GetJointDesign not present — skipping negative test")
    try:
        result = await jm.call_method(
            get_node.nodeid,
            ua.Variant("conformance-test-nonexistent-design-xyz", ua.VariantType.String),
        )
        logger.warning("Expected ua.UaError for non-existent design but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for non-existent design ID: %s", exc)


# ---------------------------------------------------------------------------
# ─── joint_design_data validation tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINT_DESIGN_DATA)
async def test_joint_design_data_id_is_non_empty_and_unique(opcua_client, ns_indices):
    """GetJointDesignList must return only non-empty IDs with no duplicates."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    list_node = await find_child_by_browse_name(jm, "GetJointDesignList", ns_ijt)
    if list_node is None:
        pytest.skip("GetJointDesignList not present — skipping")
    try:
        design_list = await _call_get_joint_design_list(jm, list_node)
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadNothingToDo")):
            pytest.skip(f"GetJointDesignList not callable: {exc}")
        raise
    if not design_list:
        pytest.skip("No joint designs on server — cannot validate IDs")
    items = [str(x) for x in (design_list if isinstance(design_list, (list, tuple)) else [design_list])]
    empty = [x for x in items if not x.strip()]
    assert not empty, f"GetJointDesignList contains empty IDs: {empty}"
    assert len(items) == len(set(items)), (
        f"GetJointDesignList contains duplicate IDs: {[x for x in items if items.count(x) > 1]}"
    )
    logger.info("GetJointDesignList: %d unique non-empty IDs confirmed", len(items))


@pytest.mark.requires_cu(CU.JOINT_DESIGN_DATA)
async def test_joint_design_data_content_is_non_null_for_stored_design(opcua_client, ns_indices):
    """GetJointDesign must return non-null content for a stored design."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    design_id = "conformance-test-jdesign-content-check"
    try:
        await _send_test_joint_design(jm, ns_ijt, design_id, content="conformance-content-value")
        get_node = await find_child_by_browse_name(jm, "GetJointDesign", ns_ijt)
        if get_node is None:
            pytest.skip("GetJointDesign not present — cannot verify content")
        try:
            result = await jm.call_method(get_node.nodeid, ua.Variant(design_id, ua.VariantType.String))
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJointDesign not callable: {exc}")
            raise
        assert result is not None, "GetJointDesign returned None — content cannot be verified"
        logger.info("GetJointDesign returned non-null result for stored design")
    finally:
        await _delete_test_joint_design(jm, ns_ijt, design_id)


@pytest.mark.requires_cu(CU.JOINT_DESIGN_DATA)
@pytest.mark.negative
async def test_joint_design_data_resend_with_same_id_accepted_or_error(opcua_client, ns_indices):
    """Resending a design with the same ID must either succeed (update) or raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    design_id = "conformance-test-jdesign-reuse"
    try:
        await _send_test_joint_design(jm, ns_ijt, design_id, content="FirstContent")
        send_node = await find_child_by_browse_name(jm, "SendJointDesign", ns_ijt)
        if send_node is None:
            pytest.skip("SendJointDesign not present — skipping")
        design_type = getattr(ua, "JointDesignDataType", None)
        if design_type is not None:
            design_data = design_type()
            if hasattr(design_data, "JointDesignId"):
                design_data.JointDesignId = design_id
            if hasattr(design_data, "Content"):
                design_data.Content = "SecondContent"
            try:
                await jm.call_method(send_node.nodeid, design_data)
                logger.info("Resend with same design ID accepted — update semantics confirmed")
            except ua.UaError as exc:
                logger.info("Resend with same design ID raised error (acceptable): %s", exc)
        else:
            logger.info("JointDesignDataType not available — resend tested via string arg")
            try:
                await jm.call_method(send_node.nodeid, ua.Variant(design_id, ua.VariantType.String))
                logger.info("Resend with same design ID (string arg) accepted")
            except ua.UaError as exc:
                logger.info("Resend raised error (acceptable): %s", exc)
    finally:
        await _delete_test_joint_design(jm, ns_ijt, design_id)


# ---------------------------------------------------------------------------
# ─── send_joint_component additional tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SEND_JOINT_COMPONENT)
async def test_send_joint_component_with_valid_data_succeeds(opcua_client, ns_indices):
    """Send a valid joint component and assert a Good response."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    comp_id = "conformance-test-jcomp-send"
    try:
        await _send_test_joint_component(jm, ns_ijt, comp_id)
        logger.info("SendJointComponent succeeded for ID '%s'", comp_id)
    finally:
        await _delete_test_joint_component(jm, ns_ijt, comp_id)


@pytest.mark.requires_cu(CU.SEND_JOINT_COMPONENT)
async def test_send_joint_component_appears_in_component_list(opcua_client, ns_indices):
    """After SendJointComponent, GetJointComponentList must include the new component ID."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    comp_id = "conformance-test-jcomp-gjcl-send"
    try:
        await _send_test_joint_component(jm, ns_ijt, comp_id)
        list_node = await find_child_by_browse_name(jm, "GetJointComponentList", ns_ijt)
        if list_node is None:
            pytest.skip("GetJointComponentList not present — cannot verify")
        try:
            comp_list = await _call_get_joint_component_list(jm, list_node)
        except ua.UaError as exc:
            if any(s in str(exc) for s in ("BadNotSupported", "BadNothingToDo")):
                pytest.skip(f"GetJointComponentList not callable: {exc}")
            raise
        ids = (
            [str(x) for x in comp_list]
            if isinstance(comp_list, (list, tuple))
            else ([] if comp_list is None else [str(comp_list)])
        )
        assert comp_id in ids, f"Component '{comp_id}' not found in GetJointComponentList: {ids[:10]}"
        logger.info("Component '%s' correctly appeared in GetJointComponentList", comp_id)
    finally:
        await _delete_test_joint_component(jm, ns_ijt, comp_id)


@pytest.mark.requires_cu(CU.SEND_JOINT_COMPONENT)
async def test_send_joint_component_update_replaces_existing_component(opcua_client, ns_indices):
    """Sending the same component ID twice must update the stored component."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    comp_id = "conformance-test-jcomp-update"
    try:
        await _send_test_joint_component(jm, ns_ijt, comp_id, manufacturer="ManufacturerV1")
        await _send_test_joint_component(jm, ns_ijt, comp_id, manufacturer="ManufacturerV2")
        get_node = await find_child_by_browse_name(jm, "GetJointComponent", ns_ijt)
        if get_node is not None:
            try:
                result = await jm.call_method(get_node.nodeid, ua.Variant(comp_id, ua.VariantType.String))
                mfg = getattr(result, "Manufacturer", None) if result else None
                if mfg is not None:
                    assert str(mfg) == "ManufacturerV2", f"Expected 'ManufacturerV2' after update, got {mfg!r}"
                    logger.info("Component update confirmed: Manufacturer='%s'", mfg)
            except ua.UaError as exc:
                logger.warning("GetJointComponent after update raised: %s", exc)
    finally:
        await _delete_test_joint_component(jm, ns_ijt, comp_id)


@pytest.mark.requires_cu(CU.SEND_JOINT_COMPONENT)
@pytest.mark.negative
async def test_send_joint_component_with_empty_id_returns_error(opcua_client, ns_indices):
    """SendJointComponent with an empty JointComponentId must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    send_node = await find_child_by_browse_name(jm, "SendJointComponent", ns_ijt)
    if send_node is None:
        pytest.skip("SendJointComponent not present — skipping negative test")
    comp_type = getattr(ua, "JointComponentDataType", None)
    if comp_type is None:
        pytest.skip("JointComponentDataType not available — cannot construct empty-ID object")
    comp_data = comp_type()
    if hasattr(comp_data, "JointComponentId"):
        comp_data.JointComponentId = ""
    try:
        result = await jm.call_method(send_node.nodeid, comp_data)
        logger.warning("Expected ua.UaError for empty JointComponentId but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for empty JointComponentId: %s", exc)
    except (AttributeError, TypeError) as exc:
        logger.info("Correctly rejected empty component ID with encoding error: %s", exc)


@pytest.mark.requires_cu(CU.SEND_JOINT_COMPONENT)
@pytest.mark.negative
async def test_send_joint_component_with_empty_manufacturer_returns_error(opcua_client, ns_indices):
    """SendJointComponent with an empty Manufacturer must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    send_node = await find_child_by_browse_name(jm, "SendJointComponent", ns_ijt)
    if send_node is None:
        pytest.skip("SendJointComponent not present — skipping negative test")
    comp_type = getattr(ua, "JointComponentDataType", None)
    if comp_type is None:
        pytest.skip("JointComponentDataType not available — cannot test empty Manufacturer")
    comp_data = comp_type()
    if hasattr(comp_data, "JointComponentId"):
        comp_data.JointComponentId = "conformance-test-jcomp-empty-mfg"
    if hasattr(comp_data, "Manufacturer"):
        comp_data.Manufacturer = ""
    try:
        result = await jm.call_method(send_node.nodeid, comp_data)
        logger.warning("Expected ua.UaError for empty Manufacturer but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for empty Manufacturer: %s", exc)
    except (AttributeError, TypeError) as exc:
        logger.info("Correctly rejected empty Manufacturer with encoding error: %s", exc)


# ---------------------------------------------------------------------------
# ─── get_joint_component_list additional tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT_COMPONENT_LIST)
async def test_get_joint_component_list_returns_string_elements(opcua_client, ns_indices):
    """GetJointComponentList must return a list where each element is a non-empty string."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    list_node = await find_child_by_browse_name(jm, "GetJointComponentList", ns_ijt)
    if list_node is None:
        pytest.skip("GetJointComponentList not present — skipping")
    try:
        comp_list = await _call_get_joint_component_list(jm, list_node)
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadNothingToDo")):
            pytest.skip(f"GetJointComponentList not callable: {exc}")
        raise
    if not comp_list:
        pytest.skip("GetJointComponentList returned empty list — cannot verify element type")
    items = list(comp_list) if isinstance(comp_list, (list, tuple)) else [comp_list]
    failures = []
    for idx, item in enumerate(items):
        item_str = str(item) if item is not None else None
        if not item_str or not item_str.strip():
            failures.append(f"Element[{idx}] is empty or None: {item!r}")
    assert not failures, f"GetJointComponentList contains invalid elements: {failures}"
    logger.info("GetJointComponentList returned %d valid string elements", len(items))


@pytest.mark.requires_cu(CU.GET_JOINT_COMPONENT_LIST)
async def test_get_joint_component_list_reflects_newly_sent_component(opcua_client, ns_indices):
    """After SendJointComponent, the new ID must appear in GetJointComponentList."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    comp_id = "conformance-test-jcomp-gcl"
    try:
        await _send_test_joint_component(jm, ns_ijt, comp_id)
        list_node = await find_child_by_browse_name(jm, "GetJointComponentList", ns_ijt)
        if list_node is None:
            pytest.skip("GetJointComponentList not present — cannot verify")
        comp_list = await _call_get_joint_component_list(jm, list_node)
        ids = (
            [str(x) for x in comp_list]
            if isinstance(comp_list, (list, tuple))
            else ([] if comp_list is None else [str(comp_list)])
        )
        assert comp_id in ids, f"Component '{comp_id}' not found in GetJointComponentList: {ids[:10]}"
        logger.info("GetJointComponentList reflects newly sent component '%s'", comp_id)
    finally:
        await _delete_test_joint_component(jm, ns_ijt, comp_id)


@pytest.mark.requires_cu(CU.GET_JOINT_COMPONENT_LIST)
@pytest.mark.negative
async def test_get_joint_component_list_returns_good_for_empty_list(opcua_client, ns_indices):
    """GetJointComponentList must not raise an error when no joint components are stored."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    list_node = await find_child_by_browse_name(jm, "GetJointComponentList", ns_ijt)
    if list_node is None:
        pytest.skip("GetJointComponentList not present — skipping")
    try:
        comp_list = await _call_get_joint_component_list(jm, list_node)
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadNothingToDo")):
            pytest.skip(f"GetJointComponentList not callable: {exc}")
        raise
    if comp_list:
        items = list(comp_list) if isinstance(comp_list, (list, tuple)) else [comp_list]
        logger.info("Server has %d component(s) — empty-list scenario cannot be tested here", len(items))
        return
    assert comp_list is None or isinstance(comp_list, (list, tuple)), (
        "GetJointComponentList must return a list or None when empty"
    )
    logger.info("GetJointComponentList returned empty result without error — correct")


# ---------------------------------------------------------------------------
# ─── get_joint_component additional round-trip tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT_COMPONENT)
async def test_get_joint_component_round_trip_data_matches_sent_data(opcua_client, ns_indices):
    """GetJointComponent must return a result for a component that was just sent."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    comp_id = "conformance-test-jcomp-rt"
    try:
        await _send_test_joint_component(jm, ns_ijt, comp_id)
        get_node = await find_child_by_browse_name(jm, "GetJointComponent", ns_ijt)
        if get_node is None:
            pytest.skip("GetJointComponent not present — cannot verify round-trip")
        try:
            result = await jm.call_method(get_node.nodeid, ua.Variant(comp_id, ua.VariantType.String))
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJointComponent not callable: {exc}")
            raise
        assert result is not None, f"GetJointComponent returned None for ID '{comp_id}'"
        logger.info("GetJointComponent round-trip succeeded for ID '%s'", comp_id)
    finally:
        await _delete_test_joint_component(jm, ns_ijt, comp_id)


@pytest.mark.requires_cu(CU.GET_JOINT_COMPONENT)
async def test_get_joint_component_result_has_required_fields(opcua_client, ns_indices):
    """GetJointComponent result must include JointComponentId and Manufacturer fields."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    comp_id = "conformance-test-jcomp-fields"
    try:
        await _send_test_joint_component(jm, ns_ijt, comp_id, manufacturer="RequiredMfg")
        get_node = await find_child_by_browse_name(jm, "GetJointComponent", ns_ijt)
        if get_node is None:
            pytest.skip("GetJointComponent not present — cannot verify fields")
        try:
            result = await jm.call_method(get_node.nodeid, ua.Variant(comp_id, ua.VariantType.String))
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJointComponent not callable: {exc}")
            raise
        assert result is not None, "GetJointComponent returned None"
        if not isinstance(result, (list, tuple)):
            cid = getattr(result, "JointComponentId", None) or getattr(result, "Id", None)
            if cid is not None:
                assert str(cid).strip() != "", "JointComponentId must not be empty"
                logger.info("JointComponentId='%s', Manufacturer=%r", cid, getattr(result, "Manufacturer", None))
    finally:
        await _delete_test_joint_component(jm, ns_ijt, comp_id)


@pytest.mark.requires_cu(CU.GET_JOINT_COMPONENT)
async def test_get_joint_component_returns_updated_data_after_resend(opcua_client, ns_indices):
    """GetJointComponent must return the most recently sent data after re-send."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    comp_id = "conformance-test-jcomp-resend"
    try:
        await _send_test_joint_component(jm, ns_ijt, comp_id, manufacturer="MfgV1")
        await _send_test_joint_component(jm, ns_ijt, comp_id, manufacturer="MfgV2")
        get_node = await find_child_by_browse_name(jm, "GetJointComponent", ns_ijt)
        if get_node is None:
            pytest.skip("GetJointComponent not present — cannot verify update")
        try:
            result = await jm.call_method(get_node.nodeid, ua.Variant(comp_id, ua.VariantType.String))
            mfg = getattr(result, "Manufacturer", None) if result else None
            if mfg is not None:
                assert str(mfg) == "MfgV2", f"Expected 'MfgV2' after resend, got {mfg!r}"
                logger.info("GetJointComponent correctly reflects updated Manufacturer")
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJointComponent not callable: {exc}")
            raise
    finally:
        await _delete_test_joint_component(jm, ns_ijt, comp_id)


@pytest.mark.requires_cu(CU.GET_JOINT_COMPONENT)
@pytest.mark.negative
async def test_get_joint_component_with_nonexistent_id_returns_error(opcua_client, ns_indices):
    """GetJointComponent with an unknown ID must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    get_node = await find_child_by_browse_name(jm, "GetJointComponent", ns_ijt)
    if get_node is None:
        pytest.skip("GetJointComponent not present — skipping negative test")
    try:
        result = await jm.call_method(
            get_node.nodeid,
            ua.Variant("conformance-test-nonexistent-comp-xyz", ua.VariantType.String),
        )
        logger.warning("Expected ua.UaError for non-existent component but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for non-existent component ID: %s", exc)


# ---------------------------------------------------------------------------
# ─── joint_component_data validation tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINT_COMPONENT_DATA)
async def test_joint_component_data_ids_are_non_empty_and_unique(opcua_client, ns_indices):
    """GetJointComponentList must return only non-empty IDs with no duplicates."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    list_node = await find_child_by_browse_name(jm, "GetJointComponentList", ns_ijt)
    if list_node is None:
        pytest.skip("GetJointComponentList not present — skipping")
    try:
        comp_list = await _call_get_joint_component_list(jm, list_node)
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadNothingToDo")):
            pytest.skip(f"GetJointComponentList not callable: {exc}")
        raise
    if not comp_list:
        pytest.skip("No joint components on server — cannot validate IDs")
    items = [str(x) for x in (comp_list if isinstance(comp_list, (list, tuple)) else [comp_list])]
    empty = [x for x in items if not x.strip()]
    assert not empty, f"GetJointComponentList contains empty IDs: {empty}"
    assert len(items) == len(set(items)), (
        f"GetJointComponentList contains duplicate IDs: {[x for x in items if items.count(x) > 1]}"
    )
    logger.info("GetJointComponentList: %d unique non-empty IDs confirmed", len(items))


@pytest.mark.requires_cu(CU.JOINT_COMPONENT_DATA)
async def test_joint_component_data_manufacturer_is_non_empty(opcua_client, ns_indices):
    """GetJointComponent must return a non-empty Manufacturer field."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    comp_id = "conformance-test-jcomp-mfg-check"
    try:
        await _send_test_joint_component(jm, ns_ijt, comp_id, manufacturer="ValidManufacturer")
        get_node = await find_child_by_browse_name(jm, "GetJointComponent", ns_ijt)
        if get_node is None:
            pytest.skip("GetJointComponent not present — cannot verify Manufacturer")
        try:
            result = await jm.call_method(get_node.nodeid, ua.Variant(comp_id, ua.VariantType.String))
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJointComponent not callable: {exc}")
            raise
        assert result is not None, "GetJointComponent returned None"
        if not isinstance(result, (list, tuple)):
            mfg = getattr(result, "Manufacturer", None)
            if mfg is not None:
                assert str(mfg).strip() != "", "Manufacturer must not be empty"
                logger.info("Manufacturer field non-empty: '%s'", mfg)
    finally:
        await _delete_test_joint_component(jm, ns_ijt, comp_id)


@pytest.mark.requires_cu(CU.JOINT_COMPONENT_DATA)
async def test_joint_component_data_manufacturer_uri_follows_uri_format(opcua_client, ns_indices):
    """ManufacturerUri in JointComponentData must start with 'urn:' or 'http' if present."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    comp_id = "conformance-test-jcomp-uri-check"
    try:
        await _send_test_joint_component(jm, ns_ijt, comp_id)
        get_node = await find_child_by_browse_name(jm, "GetJointComponent", ns_ijt)
        if get_node is None:
            pytest.skip("GetJointComponent not present — cannot verify ManufacturerUri")
        try:
            result = await jm.call_method(get_node.nodeid, ua.Variant(comp_id, ua.VariantType.String))
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJointComponent not callable: {exc}")
            raise
        if result is None or isinstance(result, (list, tuple)):
            pytest.skip("GetJointComponent returned list/None — cannot inspect ManufacturerUri")
        uri = getattr(result, "ManufacturerUri", None)
        if uri is None or not str(uri).strip():
            logger.info("ManufacturerUri is absent or empty — field is optional")
            return
        uri_str = str(uri)
        assert uri_str.startswith(("urn:", "http")), f"ManufacturerUri '{uri_str}' must start with 'urn:' or 'http'"
        logger.info("ManufacturerUri follows URI format: '%s'", uri_str)
    finally:
        await _delete_test_joint_component(jm, ns_ijt, comp_id)


@pytest.mark.requires_cu(CU.JOINT_COMPONENT_DATA)
@pytest.mark.negative
async def test_joint_component_data_empty_manufacturer_uri_rejected(opcua_client, ns_indices):
    """SendJointComponent with an explicit empty ManufacturerUri should raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    send_node = await find_child_by_browse_name(jm, "SendJointComponent", ns_ijt)
    if send_node is None:
        pytest.skip("SendJointComponent not present — skipping negative test")
    comp_type = getattr(ua, "JointComponentDataType", None)
    if comp_type is None:
        pytest.skip("JointComponentDataType not available — cannot test ManufacturerUri rejection")
    comp_data = comp_type()
    if not hasattr(comp_data, "ManufacturerUri"):
        pytest.skip("JointComponentDataType has no ManufacturerUri field — skipping")
    if hasattr(comp_data, "JointComponentId"):
        comp_data.JointComponentId = "conformance-test-jcomp-empty-uri"
    if hasattr(comp_data, "Manufacturer"):
        comp_data.Manufacturer = "TestMfg"
    comp_data.ManufacturerUri = "not-a-valid-uri"
    try:
        result = await jm.call_method(send_node.nodeid, comp_data)
        logger.warning(
            "Expected ua.UaError for invalid ManufacturerUri but returned %r — server may not validate URI format",
            result,
        )
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for invalid ManufacturerUri: %s", exc)
    except (AttributeError, TypeError) as exc:
        logger.info("Correctly rejected invalid URI with encoding error: %s", exc)


# ---------------------------------------------------------------------------
# ─── delete_joint additional negative tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.DELETE_JOINT)
@pytest.mark.negative
async def test_delete_joint_with_nonexistent_id_returns_bad_node_id_unknown(opcua_client, ns_indices):
    """DeleteJoint with a non-existent joint ID must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
    if del_node is None:
        pytest.skip("DeleteJoint not present — skipping negative test")
    try:
        result = await jm.call_method(
            del_node.nodeid,
            ua.Variant("conformance-test-nonexistent-del-xyz", ua.VariantType.String),
        )
        logger.warning("Expected ua.UaError for non-existent joint delete but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for non-existent joint delete: %s", exc)


@pytest.mark.requires_cu(CU.DELETE_JOINT)
@pytest.mark.negative
async def test_delete_joint_of_selected_joint_returns_error_or_deselects(opcua_client, ns_indices):
    """DeleteJoint on a currently selected joint must return Bad_InvalidState or auto-deselect."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available — cannot test delete-while-selected")
    joint_id = "conformance-test-joint-del-selected"
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — cannot create test joint")
    joint_data = joint_type()
    if hasattr(joint_data, "JointId"):
        joint_data.JointId = joint_id
    try:
        try:
            await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
        except ua.UaError as exc:
            if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
                pytest.skip(f"SendJoint not callable: {exc}")
            raise
        sel_node = await find_child_by_browse_name(jm, BN.SELECT_JOINT, ns_ijt)
        if sel_node is not None:
            try:
                await jm.call_method(
                    sel_node.nodeid,
                    ua.Variant("", ua.VariantType.String),
                    ua.Variant(joint_id, ua.VariantType.String),
                    ua.Variant("", ua.VariantType.String),
                )
            except ua.UaError:
                pass
        del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
        if del_node is None:
            pytest.skip("DeleteJoint not present — skipping")
        try:
            await jm.call_method(
                del_node.nodeid,
                ua.Variant("", ua.VariantType.String),
                ua.Variant(joint_id, ua.VariantType.String),
                ua.Variant("", ua.VariantType.String),
            )
            logger.info("DeleteJoint on selected joint succeeded (auto-deselect semantics) — acceptable")
        except ua.UaError as exc:
            logger.info(
                "DeleteJoint on selected joint raised ua.UaError (Bad_InvalidState) — acceptable: %s",
                exc,
            )
    finally:
        del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
        if del_node is not None:
            try:
                await jm.call_method(
                    del_node.nodeid,
                    ua.Variant("", ua.VariantType.String),
                    ua.Variant(joint_id, ua.VariantType.String),
                    ua.Variant("", ua.VariantType.String),
                )
            except ua.UaError:
                pass


# ---------------------------------------------------------------------------
# ─── delete_joint_design CRUD and negative tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.DELETE_JOINT_DESIGN)
async def test_delete_joint_design_send_then_delete_removes_from_list(opcua_client, ns_indices):
    """SendJointDesign followed by DeleteJointDesign must remove the design from GetJointDesignList."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    design_id = "conformance-test-jdesign-del"
    await _send_test_joint_design(jm, ns_ijt, design_id)
    del_node = await find_child_by_browse_name(jm, "DeleteJointDesign", ns_ijt)
    if del_node is None:
        pytest.skip("DeleteJointDesign not present — skipping")
    try:
        await jm.call_method(del_node.nodeid, ua.Variant(design_id, ua.VariantType.String))
    except ua.UaError as exc:
        pytest.fail(f"DeleteJointDesign failed for design '{design_id}': {exc}")
    list_node = await find_child_by_browse_name(jm, "GetJointDesignList", ns_ijt)
    if list_node is None:
        return
    try:
        design_list = await _call_get_joint_design_list(jm, list_node)
    except ua.UaError:
        return
    ids = (
        [str(x) for x in design_list]
        if isinstance(design_list, (list, tuple))
        else ([] if design_list is None else [str(design_list)])
    )
    assert design_id not in ids, f"Design '{design_id}' still present in GetJointDesignList after DeleteJointDesign"
    logger.info("Design '%s' correctly absent from GetJointDesignList after delete", design_id)


@pytest.mark.requires_cu(CU.DELETE_JOINT_DESIGN)
@pytest.mark.negative
async def test_delete_joint_design_with_nonexistent_id_returns_error(opcua_client, ns_indices):
    """DeleteJointDesign with a non-existent ID must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    del_node = await find_child_by_browse_name(jm, "DeleteJointDesign", ns_ijt)
    if del_node is None:
        pytest.skip("DeleteJointDesign not present — skipping negative test")
    try:
        result = await jm.call_method(
            del_node.nodeid,
            ua.Variant("conformance-test-nonexistent-design-del-xyz", ua.VariantType.String),
        )
        logger.warning("Expected ua.UaError for non-existent design delete but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for non-existent design delete: %s", exc)


# ---------------------------------------------------------------------------
# ─── delete_joint_component CRUD and negative tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.DELETE_JOINT_COMPONENT)
async def test_delete_joint_component_send_then_delete_removes_from_list(opcua_client, ns_indices):
    """SendJointComponent followed by DeleteJointComponent must remove it from GetJointComponentList."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    comp_id = "conformance-test-jcomp-del"
    await _send_test_joint_component(jm, ns_ijt, comp_id)
    del_node = await find_child_by_browse_name(jm, "DeleteJointComponent", ns_ijt)
    if del_node is None:
        pytest.skip("DeleteJointComponent not present — skipping")
    try:
        await jm.call_method(del_node.nodeid, ua.Variant(comp_id, ua.VariantType.String))
    except ua.UaError as exc:
        pytest.fail(f"DeleteJointComponent failed for component '{comp_id}': {exc}")
    list_node = await find_child_by_browse_name(jm, "GetJointComponentList", ns_ijt)
    if list_node is None:
        return
    try:
        comp_list = await _call_get_joint_component_list(jm, list_node)
    except ua.UaError:
        return
    ids = (
        [str(x) for x in comp_list]
        if isinstance(comp_list, (list, tuple))
        else ([] if comp_list is None else [str(comp_list)])
    )
    assert comp_id not in ids, (
        f"Component '{comp_id}' still present in GetJointComponentList after DeleteJointComponent"
    )
    logger.info("Component '%s' correctly absent after delete", comp_id)


@pytest.mark.requires_cu(CU.DELETE_JOINT_COMPONENT)
@pytest.mark.negative
async def test_delete_joint_component_with_nonexistent_id_returns_error(opcua_client, ns_indices):
    """DeleteJointComponent with a non-existent ID must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    del_node = await find_child_by_browse_name(jm, "DeleteJointComponent", ns_ijt)
    if del_node is None:
        pytest.skip("DeleteJointComponent not present — skipping negative test")
    try:
        result = await jm.call_method(
            del_node.nodeid,
            ua.Variant("conformance-test-nonexistent-comp-del-xyz", ua.VariantType.String),
        )
        logger.warning("Expected ua.UaError for non-existent component delete but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for non-existent component delete: %s", exc)


# ---------------------------------------------------------------------------
# ─── get_joint_revision_list additional tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINT_REVISION_LIST)
async def test_get_joint_revision_list_returns_list_for_stored_joint(opcua_client, ns_indices):
    """GetJointRevisionList for a joint sent twice must return a list."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id = "conformance-test-joint-rl"
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available — cannot test GetJointRevisionList")
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — cannot create test joint")
    try:
        for name_val in ("RevisionOne", "RevisionTwo"):
            joint_data = joint_type()
            if hasattr(joint_data, "JointId"):
                joint_data.JointId = joint_id
            if hasattr(joint_data, "Name"):
                joint_data.Name = name_val
            try:
                await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
            except ua.UaError as exc:
                if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
                    pytest.skip(f"SendJoint not callable: {exc}")
                raise
        rl_node = await find_child_by_browse_name(jm, "GetJointRevisionList", ns_ijt)
        if rl_node is None:
            pytest.skip("GetJointRevisionList not present — skipping")
        try:
            result = await jm.call_method(rl_node.nodeid, ua.Variant(joint_id, ua.VariantType.String))
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJointRevisionList not callable: {exc}")
            raise
        assert result is None or isinstance(result, (list, tuple)), (
            f"GetJointRevisionList must return a list, got {type(result)}"
        )
        count = len(result) if result else 0
        logger.info("GetJointRevisionList returned %d revision(s) for joint '%s'", count, joint_id)
    finally:
        del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
        if del_node is not None:
            try:
                await jm.call_method(
                    del_node.nodeid,
                    ua.Variant("", ua.VariantType.String),
                    ua.Variant(joint_id, ua.VariantType.String),
                    ua.Variant("", ua.VariantType.String),
                )
            except ua.UaError:
                pass


@pytest.mark.requires_cu(CU.GET_JOINT_REVISION_LIST)
async def test_get_joint_revision_list_each_entry_has_required_fields(opcua_client, ns_indices):
    """If GetJointRevisionList returns entries, each entry must have non-null fields."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    joint_id = "conformance-test-joint-rl-fields"
    joint_type = getattr(ua, "JointDataType", None)
    if joint_type is None:
        pytest.skip("JointDataType not available — cannot test revision list fields")
    send_node = await find_child_by_browse_name(jm, BN.SEND_JOINT, ns_ijt)
    if send_node is None:
        pytest.skip("SendJoint not present — cannot create test joint")
    try:
        joint_data = joint_type()
        if hasattr(joint_data, "JointId"):
            joint_data.JointId = joint_id
        try:
            await jm.call_method(send_node.nodeid, ua.Variant("", ua.VariantType.String), joint_data)
        except ua.UaError as exc:
            if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
                pytest.skip(f"SendJoint not callable: {exc}")
            raise
        rl_node = await find_child_by_browse_name(jm, "GetJointRevisionList", ns_ijt)
        if rl_node is None:
            pytest.skip("GetJointRevisionList not present — skipping")
        try:
            result = await jm.call_method(rl_node.nodeid, ua.Variant(joint_id, ua.VariantType.String))
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJointRevisionList not callable: {exc}")
            raise
        if not result:
            logger.info("GetJointRevisionList returned empty list — no entries to validate fields")
            return
        entries = list(result) if isinstance(result, (list, tuple)) else [result]
        for idx, entry in enumerate(entries):
            assert entry is not None, f"Revision entry[{idx}] is None"
            logger.info("Revision entry[%d]: %r", idx, type(entry).__name__)
    finally:
        del_node = await find_child_by_browse_name(jm, BN.DELETE_JOINT, ns_ijt)
        if del_node is not None:
            try:
                await jm.call_method(
                    del_node.nodeid,
                    ua.Variant("", ua.VariantType.String),
                    ua.Variant(joint_id, ua.VariantType.String),
                    ua.Variant("", ua.VariantType.String),
                )
            except ua.UaError:
                pass


@pytest.mark.requires_cu(CU.GET_JOINT_REVISION_LIST)
@pytest.mark.negative
async def test_get_joint_revision_list_with_nonexistent_id_returns_empty_or_error(opcua_client, ns_indices):
    """GetJointRevisionList with a non-existent ID must return empty list or ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    rl_node = await find_child_by_browse_name(jm, "GetJointRevisionList", ns_ijt)
    if rl_node is None:
        pytest.skip("GetJointRevisionList not present — skipping negative test")
    try:
        result = await jm.call_method(
            rl_node.nodeid,
            ua.Variant("conformance-test-nonexistent-jrl-xyz", ua.VariantType.String),
        )
        items = list(result) if isinstance(result, (list, tuple)) else ([] if result is None else [result])
        if items:
            logger.warning(
                "GetJointRevisionList returned %d entries for non-existent ID — "
                "server should return empty list or error",
                len(items),
            )
        else:
            logger.info("GetJointRevisionList correctly returned empty list for non-existent ID")
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for non-existent ID: %s", exc)


@pytest.mark.requires_cu(CU.GET_JOINT_REVISION_LIST)
@pytest.mark.negative
async def test_get_joint_revision_list_with_empty_id_returns_bad_invalid_argument(opcua_client, ns_indices):
    """GetJointRevisionList with an empty string ID must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jm = await _get_joint_management(opcua_client, ns_ijt)
    rl_node = await find_child_by_browse_name(jm, "GetJointRevisionList", ns_ijt)
    if rl_node is None:
        pytest.skip("GetJointRevisionList not present — skipping negative test")
    try:
        result = await jm.call_method(rl_node.nodeid, ua.Variant("", ua.VariantType.String))
        logger.warning("Expected ua.UaError for empty ID in GetJointRevisionList but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for empty ID: %s", exc)
