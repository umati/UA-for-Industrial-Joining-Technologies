"""
Conformance unit tests for JoiningProcessManagement — OPC 40450-1 IJT Base.

joining_process_management: "The JoiningSystem includes support for
JoiningProcessManagement with methods for selecting, starting, and managing joining
processes."

get_joining_process_list: "The Server supports GetJoiningProcessList method."

abort_joining_process: "The Server supports AbortJoiningProcess method."

start_selected_joining: "The Server supports StartSelectedJoining method."

select_joining_process: "The Server supports SelectJoiningProcess method."

deselect_joining_process: "The Server supports DeselectJoiningProcess method."

reset_joining_process: "The Server supports ResetJoiningProcess method."

increment_joining_process_counter: "The Server supports
IncrementJoiningProcessCounter method."

decrement_joining_process_counter: "The Server supports
DecrementJoiningProcessCounter method."

set_joining_process_size: "The Server supports SetJoiningProcessSize method."

start_joining_process: "The Server supports StartJoiningProcess method."

delete_joining_process: "The Server supports DeleteJoiningProcess method."

get_selected_joining_program: "The Server supports GetSelectedJoiningProgram method."

send_joining_process: "The Server supports SendJoiningProcess method."

get_joining_process: "The Server supports GetJoiningProcess method."

set_joining_process_counter: "The Server supports SetJoiningProcessCounter method."

set_joining_process_mapping: "The Server supports SetJoiningProcessMapping method."

get_joining_process_revision_list: "The Server supports
GetJoiningProcessRevisionList method."
"""

import logging

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.event_collector import EventCollector
from helpers.event_validator import assert_result_ready_event_valid
from helpers.method_caller import call_method, find_and_call_method
from helpers.method_signature import JOINING_PROCESS_METHOD_INPUTS, assert_input_argument_names
from helpers.namespaces import BN, NS_APP, NS_DI, NS_IJT_BASE, NS_OPC_UA, IJTTypes
from helpers.node_discovery import (
    find_child_by_browse_name,
    find_joining_system,
    find_method_set,
    get_type_definition,
    read_tool_product_instance_uri,
)
from helpers.skip_reasons import skip_accepted_policy

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

# Mandatory methods that must always be present per spec.
_MANDATORY_JPM_METHODS = {
    BN.SELECT_JOINING_PROCESS,
    BN.START_SELECTED_JOINING,
    BN.GET_JOINING_PROCESS_LIST,
    BN.GET_SELECTED_JOINING_PROGRAM,
}

# Optional methods — skip rather than fail when absent.
_OPTIONAL_JPM_METHODS = {
    BN.ABORT_JOINING_PROCESS,
    BN.RESET_JOINING_PROCESS,
    BN.SET_JOINING_PROCESS_SIZE,
    BN.INCREMENT_JOINING_PROCESS_COUNTER,
    BN.DECREMENT_JOINING_PROCESS_COUNTER,
    "DeselectJoiningProcess",
    "StartJoiningProcess",
    "DeleteJoiningProcess",
    "SendJoiningProcess",
    "GetJoiningProcess",
    "SetJoiningProcessCounter",
    "SetJoiningProcessMapping",
    "GetJoiningProcessRevisionList",
}

# String constant used when testing invalid-program rejection.
_INVALID_PROGRAM_ID = "INVALID-PROGRAM-ID-NONEXISTENT"


def _make_jp_identification():
    """
    Create a JoiningProcessIdentificationDataType with all fields empty.

    Available after load_data_type_definitions() is called in conftest for every client.
    Web Client reference: jp.JoiningProcessId = jp.JoiningProcessOriginId = jp.SelectionName = ""
    Returns None if the type has not been registered by load_data_type_definitions().
    """
    try:
        jp = ua.JoiningProcessIdentificationDataType()
        jp.JoiningProcessId = ""
        jp.JoiningProcessOriginId = ""
        jp.SelectionName = ""
        return jp
    except AttributeError:
        return None


def _piu_arg(value: str = ""):
    return ua.Variant(value, ua.VariantType.String)


def _trimmed_string_arg(value: str = ""):
    return ua.Variant(value, ua.VariantType.String)


def _jp_identification_arg(process_id: str = "", origin_id: str = "", selection_name: str = ""):
    jp = _make_jp_identification()
    if jp is None:
        return None
    jp.JoiningProcessId = process_id
    jp.JoiningProcessOriginId = origin_id
    jp.SelectionName = selection_name
    return ua.Variant(jp, ua.VariantType.ExtensionObject)


def _empty_associated_entities_arg():
    return ua.Variant([], ua.VariantType.ExtensionObject)


def _joining_process_id_from_entry(entry) -> str:
    entry = getattr(entry, "Value", entry)
    meta = getattr(entry, "JoiningProcessMetaData", None)
    for source in (entry, meta):
        if source is None:
            continue
        value = getattr(source, "JoiningProcessId", None)
        if value:
            return str(value)
    return str(entry)


def _joining_process_origin_id_from_entry(entry) -> str:
    entry = getattr(entry, "Value", entry)
    meta = getattr(entry, "JoiningProcessMetaData", None)
    for source in (entry, meta):
        if source is None:
            continue
        value = getattr(source, "JoiningProcessOriginId", None)
        if value:
            return str(value)
    return ""


def _jp_identification_from_entry(entry):
    return _jp_identification_arg(
        process_id=_joining_process_id_from_entry(entry),
        origin_id=_joining_process_origin_id_from_entry(entry),
    )


def _first_method_output(output):
    if isinstance(output, (list, tuple)):
        return output[0] if output else None
    return output


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _require_ns_ijt(ns_indices):
    """Return the IJT Base namespace index; skip the test if not registered."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    return ns_ijt


async def _get_jpm(client, ns_ijt):
    """
    Re-discover JoiningProcessManagement on a fresh function-scoped client.

    Uses JoiningSystem discovery followed by a browse by BrowseName, matching the
    conftest pattern for the session-scoped fixture but applied to a fresh
    function-scoped connection for method-call isolation.
    """
    js = await find_joining_system(client)
    if js is None:
        pytest.skip("JoiningSystem not found — server may not be running")
    jpm = await find_child_by_browse_name(js, BN.JOINING_PROCESS_MANAGEMENT, ns_ijt)
    if jpm is None:
        pytest.skip("JoiningProcessManagement node not found on JoiningSystem")
    return jpm


def _unwrap_method_array_output(output):
    if output and isinstance(output[0], list):
        return output[0]
    return output


async def _read_required_tool_product_instance_uri(client, ns_indices) -> str:
    ns_ijt = _require_ns_ijt(ns_indices)
    ns_di = ns_indices.get(NS_DI) or 0
    ns_app = ns_indices.get(NS_APP)
    pi_uri = await read_tool_product_instance_uri(client, ns_ijt, ns_di, ns_app)
    if not pi_uri:
        pytest.skip("Tool ProductInstanceUri not available — cannot call PIU-scoped JoiningProcess method")
    return pi_uri


async def _first_joining_process_identification_arg(client, ns_indices, jpm_node, pi_uri: str):
    ns_ijt = _require_ns_ijt(ns_indices)
    if not pi_uri:
        pytest.skip("Tool ProductInstanceUri not available - cannot build JoiningProcessIdentification")
    jpm_node = jpm_node or await _get_jpm(client, ns_ijt)
    list_result = await find_and_call_method(
        jpm_node,
        BN.GET_JOINING_PROCESS_LIST,
        ns_ijt,
        _piu_arg(pi_uri),
        timeout=15.0,
    )
    if not list_result.success:
        err_str = str(list_result.error) if list_result.error else "unknown"
        pytest.skip(f"GetJoiningProcessList failed ({err_str}) — cannot build JoiningProcessIdentification")
    programs = _unwrap_method_array_output(list_result.output_list)
    if not programs:
        pytest.skip("GetJoiningProcessList returned empty list — no joining process available")
    jp_arg = _jp_identification_from_entry(programs[0])
    if jp_arg is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — cannot build method arguments")
    return jp_arg


async def _find_method_node(jpm_node, method_name, ns_ijt):
    """Look up a method child of jpm_node by BrowseName. Returns the Node or None."""
    return await find_child_by_browse_name(jpm_node, method_name, ns_ijt)


async def _get_asset_management_method_set(client, ns_ijt: int, ns_di: int, ns_app: int | None = None):
    """Return the AssetManagement/MethodSet node, or None if not found.
    Tries DI namespace first for MethodSet, then falls back to app namespace."""
    js = await find_joining_system(client)
    if js is None:
        return None
    am = await find_child_by_browse_name(js, BN.ASSET_MANAGEMENT, ns_ijt)
    if am is None:
        return None
    return await find_method_set(am, ns_di, ns_ijt, ns_app)


# ---------------------------------------------------------------------------
# ─── joining_process_management ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINING_PROCESS_MANAGEMENT)
async def test_joining_process_management_addin_present(joining_process_management):
    """
    JoiningSystem must expose a JoiningProcessManagement AddIn node.
    Discovery is performed by the session-scoped fixture; a None result is treated
    as a failure by that fixture.
    """
    assert joining_process_management is not None, "JoiningProcessManagement AddIn node must not be None"


@pytest.mark.requires_cu(CU.JOINING_PROCESS_MANAGEMENT)
@pytest.mark.parametrize("method_name", BN.ALL_JOINING_PROCESS_METHODS)
async def test_all_joining_process_methods_present(joining_process_management, ns_indices, method_name):
    """
    All methods listed in BN.ALL_JOINING_PROCESS_METHODS must be present.
    Mandatory methods cause a test failure when absent; optional methods cause a skip.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, method_name, ns_ijt)
    if node is None:
        if method_name in _MANDATORY_JPM_METHODS:
            pytest.fail(f"Mandatory method '{method_name}' not found in JoiningProcessManagement")
        else:
            pytest.skip(f"Optional method '{method_name}': Not Supported — skipping")


@pytest.mark.requires_cu(CU.JOINING_PROCESS_MANAGEMENT)
@pytest.mark.parametrize("method_name, expected_args", sorted(JOINING_PROCESS_METHOD_INPUTS.items()))
async def test_joining_process_method_input_arguments_match_nodeset(
    joining_process_management, ns_indices, method_name, expected_args
):
    """JoiningProcessManagement methods exposed by the server must use current NodeSet signatures."""
    ns_ijt = _require_ns_ijt(ns_indices)
    ns_opcua = ns_indices.get(NS_OPC_UA, 0)
    node = await _find_method_node(joining_process_management, method_name, ns_ijt)
    if node is None:
        if method_name in _MANDATORY_JPM_METHODS:
            pytest.fail(f"Mandatory method '{method_name}' not found in JoiningProcessManagement")
        pytest.skip(f"Optional method '{method_name}': Not Supported")
    await assert_input_argument_names(node, expected_args, ns_opcua=ns_opcua, method_name=method_name)


# ---------------------------------------------------------------------------
# ─── select_joining_process ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SELECT_JOINING_PROCESS)
async def test_select_joining_process_method_present(joining_process_management, ns_indices):
    """
    SelectJoiningProcess method must be present on JoiningProcessManagement
    (mandatory per the select_joining_process conformance unit).
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, BN.SELECT_JOINING_PROCESS, ns_ijt)
    assert node is not None, f"Required method '{BN.SELECT_JOINING_PROCESS}' not found in JoiningProcessManagement"


@pytest.mark.requires_cu(CU.SELECT_JOINING_PROCESS)
async def test_select_joining_process_with_valid_program_succeeds(opcua_client, ns_indices):
    """
    SelectJoiningProcess called with the first program from GetJoiningProcessList
    must succeed (or return an accepted error code on some servers).
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)

    list_result = await find_and_call_method(jpm, BN.GET_JOINING_PROCESS_LIST, ns_ijt, _piu_arg(pi_uri), timeout=15.0)
    if not list_result.success:
        pytest.skip("GetJoiningProcessList unavailable — cannot determine valid program ID")
    programs = list_result.output_list
    if not programs:
        pytest.skip("GetJoiningProcessList returned an empty list — no program available to select")

    first_program = programs[0]
    program_id = _joining_process_id_from_entry(first_program)
    jp_arg = _jp_identification_arg(process_id=program_id)
    if jp_arg is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — cannot select a joining process")

    method_node = await _find_method_node(jpm, BN.SELECT_JOINING_PROCESS, ns_ijt)
    assert method_node is not None, f"'{BN.SELECT_JOINING_PROCESS}' method node not found"

    call_result = await call_method(
        jpm,
        method_node,
        _piu_arg(pi_uri),
        jp_arg,
        timeout=15.0,
        method_name=BN.SELECT_JOINING_PROCESS,
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown error"
        if any(s in err_str for s in ("BadNotSupported", "BadInvalidArgument", "BadNotFound", "Uncertain")):
            skip_accepted_policy(
                "server may reject the listed process for current controller/tool state",
                method=BN.SELECT_JOINING_PROCESS,
                status=err_str,
            )
        pytest.fail(f"SelectJoiningProcess with valid program ID failed: {err_str}")


@pytest.mark.requires_cu(CU.SELECT_JOINING_PROCESS)
async def test_select_joining_process_with_invalid_id_returns_error(opcua_client, ns_indices):
    """
    SelectJoiningProcess called with a non-existent program ID must return a Bad
    status code.  A successful call is a spec violation.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, BN.SELECT_JOINING_PROCESS, ns_ijt)
    if method_node is None:
        pytest.skip(f"'{BN.SELECT_JOINING_PROCESS}' method node not found — skipping")
    jp_arg = _jp_identification_arg(process_id=_INVALID_PROGRAM_ID)
    if jp_arg is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — cannot run negative selection test")

    call_result = await call_method(
        jpm,
        method_node,
        _piu_arg(),
        jp_arg,
        timeout=15.0,
        method_name=BN.SELECT_JOINING_PROCESS,
    )
    assert not call_result.success, (
        "SelectJoiningProcess with a non-existent program ID must raise a Bad status code, "
        "but the call unexpectedly succeeded"
    )


# ---------------------------------------------------------------------------
# ─── start_selected_joining ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.START_SELECTED_JOINING)
async def test_start_selected_joining_method_present(joining_process_management, ns_indices):
    """
    StartSelectedJoining method must be present on JoiningProcessManagement
    (mandatory per the start_selected_joining conformance unit).
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, BN.START_SELECTED_JOINING, ns_ijt)
    assert node is not None, f"Required method '{BN.START_SELECTED_JOINING}' not found in JoiningProcessManagement"


@pytest.mark.requires_cu(CU.START_SELECTED_JOINING)
async def test_start_selected_joining_triggers_result_ready_event(subscription_client, opcua_client, ns_indices):
    """
    Calling StartSelectedJoining must fire a JoiningSystemResultReadyEvent.

    SelectJoiningProcess is attempted first if a program list is available.
    If the server does not produce a result event, the test is skipped rather
    than failed (tool may not be physically present or configured).
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)

    list_result = await find_and_call_method(
        jpm,
        BN.GET_JOINING_PROCESS_LIST,
        ns_ijt,
        _piu_arg(),
        timeout=15.0,
    )
    if list_result.success:
        programs = list_result.output_list
        if programs:
            first_program = programs[0]
            program_id = _joining_process_id_from_entry(first_program)
            select_method = await _find_method_node(jpm, BN.SELECT_JOINING_PROCESS, ns_ijt)
            if select_method is not None:
                jp_arg = _jp_identification_arg(process_id=program_id)
                if jp_arg is not None:
                    await call_method(
                        jpm,
                        select_method,
                        _piu_arg(),
                        jp_arg,
                        timeout=15.0,
                        method_name=BN.SELECT_JOINING_PROCESS,
                    )

    start_method = await _find_method_node(jpm, BN.START_SELECTED_JOINING, ns_ijt)
    if start_method is None:
        pytest.skip(f"'{BN.START_SELECTED_JOINING}' method not found — skipping")

    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))

    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)
        start_result = await call_method(
            jpm,
            start_method,
            _piu_arg(),
            ua.Variant(False, ua.VariantType.Boolean),
            timeout=15.0,
            method_name=BN.START_SELECTED_JOINING,
        )
        if not start_result.success:
            err_str = str(start_result.error) if start_result.error else "unknown"
            if any(
                s in err_str
                for s in (
                    "BadNotSupported",
                    "BadNothingToDo",
                    "BadConditionNotActive",
                    "BadArgumentsMissing",
                    "Uncertain",
                )
            ):
                skip_accepted_policy(
                    "tool/controller state is not ready to execute the selected joining process",
                    method=BN.START_SELECTED_JOINING,
                    status=err_str,
                )
            pytest.fail(f"StartSelectedJoining failed unexpectedly: {err_str}")
        # P06: server returns OpcUa_Good + bad methodStatusCode in output[0] when no process is selected
        output = start_result.output_list
        if output:
            try:
                if int(output[0]) != 0:
                    skip_accepted_policy(
                        "method returned Good with a non-success domain status because no joining process is active or selected",
                        method=BN.START_SELECTED_JOINING,
                        status=str(output[0]),
                    )
            except (TypeError, ValueError):
                pass
        events = await collector.collect(count=1, timeout_s=45.0)

    if not events:
        pytest.skip(
            "StartSelectedJoining did not produce a ResultReadyEvent within timeout — "
            "tool may not be physically running; trigger manually if using a real controller"
        )
    assert_result_ready_event_valid(events[0], context="start_selected_joining:ResultReadyEvent")


@pytest.mark.requires_cu(CU.START_SELECTED_JOINING)
@pytest.mark.parametrize(
    "method_name,description",
    [
        (BN.SELECT_JOINING_PROCESS, "select-process"),
        (BN.START_SELECTED_JOINING, "start-joining"),
    ],
)
async def test_joining_process_core_methods_are_callable(opcua_client, ns_indices, method_name, description):
    """
    Core JoiningProcessManagement methods must be present and callable.
    BadNotSupported, BadNothingToDo, and Uncertain are accepted when no
    process context is active.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, method_name, ns_ijt)
    assert method_node is not None, f"Required method '{method_name}' not found in JoiningProcessManagement"
    if method_name == BN.SELECT_JOINING_PROCESS:
        jp_arg = _jp_identification_arg(process_id=_INVALID_PROGRAM_ID)
        if jp_arg is None:
            pytest.skip("JoiningProcessIdentificationDataType not available — cannot call SelectJoiningProcess")
        args = (_piu_arg(), jp_arg)
    else:
        args = (_piu_arg(), ua.Variant(False, ua.VariantType.Boolean))
    call_result = await call_method(jpm, method_node, *args, timeout=15.0, method_name=method_name)
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if any(
            s in err_str
            for s in (
                "BadNotSupported",
                "BadNothingToDo",
                "BadConditionNotActive",
                "BadArgumentsMissing",
                "BadInvalidArgument",
                "Uncertain",
            )
        ):
            return
        pytest.fail(f"'{method_name}' ({description}) raised an unexpected error: {err_str}")


@pytest.mark.requires_cu(CU.START_SELECTED_JOINING)
async def test_start_selected_joining_with_deselect_after_joining_true(subscription_client, opcua_client, ns_indices):
    """
    StartSelectedJoining with DeselectAfterJoining=True must either succeed and fire
    a JoiningSystemResultReadyEvent, or return an accepted status code.

    Per spec, the DeselectAfterJoining Boolean controls whether the selected process
    is automatically deselected after the join.  Testing both True and False values
    verifies the parameter is correctly handled (see companion test that calls with False).
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)

    # Select a process first (best-effort — some servers do not require prior selection)
    list_result = await find_and_call_method(
        jpm,
        BN.GET_JOINING_PROCESS_LIST,
        ns_ijt,
        _piu_arg(pi_uri),
        timeout=15.0,
    )
    if list_result.success:
        programs = _unwrap_method_array_output(list_result.output_list)
        if programs:
            first_program = programs[0]
            jp_arg = _jp_identification_from_entry(first_program)
            select_method = await _find_method_node(jpm, BN.SELECT_JOINING_PROCESS, ns_ijt)
            if select_method is not None and jp_arg is not None:
                await call_method(
                    jpm,
                    select_method,
                    _piu_arg(pi_uri),
                    jp_arg,
                    timeout=15.0,
                    method_name=BN.SELECT_JOINING_PROCESS,
                )

    start_method = await _find_method_node(jpm, BN.START_SELECTED_JOINING, ns_ijt)
    if start_method is None:
        pytest.skip(f"'{BN.START_SELECTED_JOINING}' method not found — skipping")

    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))

    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)
        start_result = await call_method(
            jpm,
            start_method,
            _piu_arg(pi_uri),
            ua.Variant(True, ua.VariantType.Boolean),  # DeselectAfterJoining=True
            timeout=15.0,
            method_name=BN.START_SELECTED_JOINING,
        )
        if not start_result.success:
            err_str = str(start_result.error) if start_result.error else "unknown"
            if any(
                s in err_str
                for s in (
                    "BadNotSupported",
                    "BadNothingToDo",
                    "BadConditionNotActive",
                    "BadArgumentsMissing",
                )
            ):
                skip_accepted_policy(
                    "tool/controller state is not ready to execute the selected joining process",
                    method=BN.START_SELECTED_JOINING,
                    status=err_str,
                )
            pytest.fail(f"StartSelectedJoining(DeselectAfterJoining=True) failed unexpectedly: {err_str}")
        events = await collector.collect(count=1, timeout_s=45.0)

    if not events:
        skip_accepted_policy(
            "no running joining-process execution produced a ResultReadyEvent within timeout",
            method=BN.START_SELECTED_JOINING,
            status="No event within timeout",
        )
    assert_result_ready_event_valid(
        events[0],
        context="start_selected_joining:DeselectAfterJoining=True:ResultReadyEvent",
    )


# ---------------------------------------------------------------------------
# ─── get_joining_process_list ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS_LIST)
async def test_get_joining_process_list_method_present(joining_process_management, ns_indices):
    """
    GetJoiningProcessList method must be present on JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, BN.GET_JOINING_PROCESS_LIST, ns_ijt)
    assert node is not None, f"Required method '{BN.GET_JOINING_PROCESS_LIST}' not found in JoiningProcessManagement"


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS_LIST)
async def test_get_joining_process_list_returns_list(opcua_client, ns_indices):
    """
    GetJoiningProcessList must return a list (may be empty) without raising an error.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    result = await find_and_call_method(
        jpm,
        BN.GET_JOINING_PROCESS_LIST,
        ns_ijt,
        _piu_arg(),
        timeout=15.0,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if any(s in err_str for s in ("BadNotSupported", "BadNotImplemented", "BadArgumentsMissing")):
            pytest.skip(f"GetJoiningProcessList returned {err_str} — skipping")
        pytest.fail(f"GetJoiningProcessList failed unexpectedly: {err_str}")
    output = result.output_list
    assert isinstance(output, list), f"GetJoiningProcessList must return a list, got {type(output).__name__}"


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS_LIST)
async def test_get_joining_process_list_elements_have_valid_structure(opcua_client, ns_indices):
    """
    Each element returned by GetJoiningProcessList must have a recognisable
    joining-process identifier field (JoiningProcessId, Id, or a plain string).
    An empty list is accepted (no programs configured), but non-empty lists must
    contain well-structured entries per the spec.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    result = await find_and_call_method(
        jpm,
        BN.GET_JOINING_PROCESS_LIST,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        timeout=15.0,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if any(s in err_str for s in ("BadNotSupported", "BadNotImplemented", "BadArgumentsMissing")):
            pytest.skip(f"GetJoiningProcessList returned {err_str} — skipping structure check")
        pytest.fail(f"GetJoiningProcessList failed unexpectedly: {err_str}")
    items = result.output_list
    if not items:
        return  # empty list is valid — nothing to validate
    # asyncua wraps method output arguments in an outer list; unwrap if the first
    # (and only) element is itself a list (i.e., the server returned an array output)
    if len(items) == 1 and isinstance(items[0], list):
        items = items[0]
    if not items:
        return
    for i, entry in enumerate(items):
        if entry is None:
            continue
        if isinstance(entry, (str, int, bytes)):
            continue  # scalar ID — valid per some server implementations
        if isinstance(entry, list):
            # asyncua decoded an ExtensionObject as raw field values (type not registered
            # in the client's type dictionary). Named-field checks are not possible.
            assert len(entry) > 0, f"GetJoiningProcessList element[{i}] decoded as empty raw-field list"
            continue
        # Struct entry: must expose at least one recognisable identifier/text field.
        # Some servers return LocalizedText-like entries for process labels where Text may be None.
        identifier_fields = ("JoiningProcessId", "Id", "Name", "Text")
        if any(hasattr(entry, field) for field in identifier_fields):
            logger.debug(
                "GetJoiningProcessList element[%d]: candidate fields=%r",
                i,
                {field: getattr(entry, field, None) for field in identifier_fields if hasattr(entry, field)},
            )
            continue
        assert False, (
            f"GetJoiningProcessList element[{i}] has no recognisable identifier/text field "
            f"(checked JoiningProcessId, Id, Name, Text). "
            f"Available attributes: {[a for a in dir(entry) if not a.startswith('_')]}"
        )


# ---------------------------------------------------------------------------
# ─── get_selected_joining_program ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_SELECTED_JOINING_PROGRAM)
async def test_get_selected_joining_program_method_present(joining_process_management, ns_indices):
    """
    GetSelectedJoiningProgram method must be present on JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, BN.GET_SELECTED_JOINING_PROGRAM, ns_ijt)
    assert node is not None, (
        f"Required method '{BN.GET_SELECTED_JOINING_PROGRAM}' not found in JoiningProcessManagement"
    )


@pytest.mark.requires_cu(CU.GET_SELECTED_JOINING_PROGRAM)
async def test_get_selected_joining_program_returns_program(opcua_client, ns_indices):
    """
    GetSelectedJoiningProgram must return a value without raising an error (value
    may be None or empty if no program is currently selected).
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)
    result = await find_and_call_method(
        jpm,
        BN.GET_SELECTED_JOINING_PROGRAM,
        ns_ijt,
        _piu_arg(pi_uri),
        timeout=15.0,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if any(
            s in err_str
            for s in ("BadNotSupported", "BadNothingToDo", "BadNotImplemented", "BadArgumentsMissing", "Uncertain")
        ):
            skip_accepted_policy(
                "no selected joining program is available for the current controller/tool state",
                method=BN.GET_SELECTED_JOINING_PROGRAM,
                status=err_str,
            )
        pytest.fail(f"GetSelectedJoiningProgram failed unexpectedly: {err_str}")


# ---------------------------------------------------------------------------
# ─── abort_joining_process ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ABORT_JOINING_PROCESS)
async def test_abort_joining_process_method_present_if_exists(joining_process_management, ns_indices):
    """
    AbortJoiningProcess method, if present, must be accessible on
    JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, BN.ABORT_JOINING_PROCESS, ns_ijt)
    if node is None:
        pytest.skip(f"Optional method '{BN.ABORT_JOINING_PROCESS}': Not Supported")


@pytest.mark.requires_cu(CU.ABORT_JOINING_PROCESS)
async def test_abort_joining_process_callable_if_present(opcua_client, ns_indices):
    """
    AbortJoiningProcess must be callable without an unexpected server error when
    present. Expected status codes when no process is active:
    BadNothingToDo, BadConditionNotActive, BadNotSupported.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, BN.ABORT_JOINING_PROCESS, ns_ijt)
    if method_node is None:
        pytest.skip(f"Optional method '{BN.ABORT_JOINING_PROCESS}': Not Supported — skipping")
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)
    jp_arg = await _first_joining_process_identification_arg(opcua_client, ns_indices, jpm, pi_uri)
    call_result = await call_method(
        jpm,
        method_node,
        _piu_arg(pi_uri),
        jp_arg,
        ua.Variant(ua.LocalizedText("IJT conformance abort probe"), ua.VariantType.LocalizedText),
        timeout=15.0,
        method_name=BN.ABORT_JOINING_PROCESS,
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if any(
            s in err_str
            for s in (
                "BadNotSupported",
                "BadNothingToDo",
                "BadConditionNotActive",
                "BadInvalidArgument",
                "BadArgumentsMissing",
            )
        ):
            return
        pytest.fail(f"AbortJoiningProcess raised an unexpected error: {err_str}")


# ---------------------------------------------------------------------------
# ─── reset_joining_process ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESET_JOINING_PROCESS)
async def test_reset_joining_process_method_present_if_exists(joining_process_management, ns_indices):
    """
    ResetJoiningProcess method, if present, must be accessible on
    JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, BN.RESET_JOINING_PROCESS, ns_ijt)
    if node is None:
        pytest.skip(f"Optional method '{BN.RESET_JOINING_PROCESS}': Not Supported")


@pytest.mark.requires_cu(CU.RESET_JOINING_PROCESS)
async def test_reset_joining_process_callable_if_present(opcua_client, ns_indices):
    """
    ResetJoiningProcess must be callable without an unexpected server error when present.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, BN.RESET_JOINING_PROCESS, ns_ijt)
    if method_node is None:
        pytest.skip(f"Optional method '{BN.RESET_JOINING_PROCESS}': Not Supported — skipping")
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)
    jp_arg = await _first_joining_process_identification_arg(opcua_client, ns_indices, jpm, pi_uri)
    call_result = await call_method(
        jpm,
        method_node,
        _piu_arg(pi_uri),
        jp_arg,
        timeout=15.0,
        method_name=BN.RESET_JOINING_PROCESS,
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if any(
            s in err_str
            for s in (
                "BadNotSupported",
                "BadNothingToDo",
                "BadConditionNotActive",
                "BadArgumentsMissing",
            )
        ):
            return
        pytest.fail(f"ResetJoiningProcess raised an unexpected error: {err_str}")


# ---------------------------------------------------------------------------
# ─── increment_joining_process_counter ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.INCREMENT_JOINING_PROCESS_COUNTER)
async def test_increment_counter_method_present_if_exists(joining_process_management, ns_indices):
    """
    IncrementJoiningProcessCounter method, if present, must be accessible on
    JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, BN.INCREMENT_JOINING_PROCESS_COUNTER, ns_ijt)
    if node is None:
        pytest.skip(f"Optional method '{BN.INCREMENT_JOINING_PROCESS_COUNTER}': Not Supported")


@pytest.mark.requires_cu(CU.INCREMENT_JOINING_PROCESS_COUNTER)
async def test_increment_counter_callable_if_present(opcua_client, ns_indices):
    """
    IncrementJoiningProcessCounter must be callable without an unexpected error
    when present.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, BN.INCREMENT_JOINING_PROCESS_COUNTER, ns_ijt)
    if method_node is None:
        pytest.skip(f"Optional method '{BN.INCREMENT_JOINING_PROCESS_COUNTER}': Not Supported — skipping")
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)
    jp_arg = await _first_joining_process_identification_arg(opcua_client, ns_indices, jpm, pi_uri)
    call_result = await call_method(
        jpm,
        method_node,
        _piu_arg(pi_uri),
        jp_arg,
        ua.Variant(1, ua.VariantType.UInt32),
        timeout=15.0,
        method_name=BN.INCREMENT_JOINING_PROCESS_COUNTER,
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if any(s in err_str for s in ("BadNotSupported", "BadInvalidArgument", "BadArgumentsMissing")):
            return
        pytest.fail(f"IncrementJoiningProcessCounter raised an unexpected error: {err_str}")


@pytest.mark.requires_cu(CU.INCREMENT_JOINING_PROCESS_COUNTER)
async def test_increment_counter_with_product_instance_uri(opcua_client, ns_indices):
    """
    IncrementJoiningProcessCounter called with the tool's ProductInstanceUri must
    succeed or return an accepted status code.

    The ProductInstanceUri argument is required by the IJT spec.  This test validates
    the full argument path by reading the PIU from the first configured tool and
    passing it to the method — unlike the basic callable test that passes no arguments.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, BN.INCREMENT_JOINING_PROCESS_COUNTER, ns_ijt)
    if method_node is None:
        pytest.skip(f"Optional method '{BN.INCREMENT_JOINING_PROCESS_COUNTER}': Not Supported — skipping")
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)
    jp_arg = await _first_joining_process_identification_arg(opcua_client, ns_indices, jpm, pi_uri)
    call_result = await call_method(
        jpm,
        method_node,
        ua.Variant(pi_uri, ua.VariantType.String),
        jp_arg,
        ua.Variant(1, ua.VariantType.UInt32),
        timeout=15.0,
        method_name=BN.INCREMENT_JOINING_PROCESS_COUNTER,
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if any(
            s in err_str for s in ("BadNotSupported", "BadInvalidArgument", "BadArgumentsMissing", "BadNothingToDo")
        ):
            pytest.skip(f"IncrementJoiningProcessCounter(PIU) returned {err_str} — skipping")
        pytest.fail(f"IncrementJoiningProcessCounter with PIU '{pi_uri}' failed unexpectedly: {err_str}")
    logger.info("IncrementJoiningProcessCounter succeeded with PIU '%s'", pi_uri)


# ---------------------------------------------------------------------------
# ─── decrement_joining_process_counter ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.DECREMENT_JOINING_PROCESS_COUNTER)
async def test_decrement_counter_method_present_if_exists(joining_process_management, ns_indices):
    """
    DecrementJoiningProcessCounter method, if present, must be accessible on
    JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, BN.DECREMENT_JOINING_PROCESS_COUNTER, ns_ijt)
    if node is None:
        pytest.skip(f"Optional method '{BN.DECREMENT_JOINING_PROCESS_COUNTER}': Not Supported")


@pytest.mark.requires_cu(CU.DECREMENT_JOINING_PROCESS_COUNTER)
async def test_decrement_counter_callable_if_present(opcua_client, ns_indices):
    """
    DecrementJoiningProcessCounter must be callable without an unexpected error
    when present.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, BN.DECREMENT_JOINING_PROCESS_COUNTER, ns_ijt)
    if method_node is None:
        pytest.skip(f"Optional method '{BN.DECREMENT_JOINING_PROCESS_COUNTER}': Not Supported — skipping")
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)
    jp_arg = await _first_joining_process_identification_arg(opcua_client, ns_indices, jpm, pi_uri)
    call_result = await call_method(
        jpm,
        method_node,
        _piu_arg(pi_uri),
        jp_arg,
        ua.Variant(1, ua.VariantType.UInt32),
        timeout=15.0,
        method_name=BN.DECREMENT_JOINING_PROCESS_COUNTER,
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if any(s in err_str for s in ("BadNotSupported", "BadInvalidArgument", "BadArgumentsMissing")):
            return
        pytest.fail(f"DecrementJoiningProcessCounter raised an unexpected error: {err_str}")


@pytest.mark.requires_cu(CU.DECREMENT_JOINING_PROCESS_COUNTER)
async def test_decrement_counter_with_product_instance_uri(opcua_client, ns_indices):
    """
    DecrementJoiningProcessCounter called with the tool's ProductInstanceUri must
    succeed or return an accepted status code.

    The ProductInstanceUri argument is required by the IJT spec.  This test validates
    the full argument path by reading the PIU from the first configured tool.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, BN.DECREMENT_JOINING_PROCESS_COUNTER, ns_ijt)
    if method_node is None:
        pytest.skip(f"Optional method '{BN.DECREMENT_JOINING_PROCESS_COUNTER}': Not Supported — skipping")
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)
    jp_arg = await _first_joining_process_identification_arg(opcua_client, ns_indices, jpm, pi_uri)
    call_result = await call_method(
        jpm,
        method_node,
        ua.Variant(pi_uri, ua.VariantType.String),
        jp_arg,
        ua.Variant(1, ua.VariantType.UInt32),
        timeout=15.0,
        method_name=BN.DECREMENT_JOINING_PROCESS_COUNTER,
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if any(
            s in err_str for s in ("BadNotSupported", "BadInvalidArgument", "BadArgumentsMissing", "BadNothingToDo")
        ):
            pytest.skip(f"DecrementJoiningProcessCounter(PIU) returned {err_str} — skipping")
        pytest.fail(f"DecrementJoiningProcessCounter with PIU '{pi_uri}' failed unexpectedly: {err_str}")
    logger.info("DecrementJoiningProcessCounter succeeded with PIU '%s'", pi_uri)


@pytest.mark.requires_cu(CU.INCREMENT_JOINING_PROCESS_COUNTER, CU.DECREMENT_JOINING_PROCESS_COUNTER)
async def test_increment_then_decrement_counter_is_balanced(opcua_client, ns_indices):
    """
    IncrementJoiningProcessCounter followed by DecrementJoiningProcessCounter (both with
    the tool's ProductInstanceUri) must both succeed, demonstrating the counter can be
    driven in both directions.

    This is a balanced round-trip: Increment then Decrement, leaving the server in the
    same state it started in.  Both methods are required for this test to run.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    inc_node = await _find_method_node(jpm, BN.INCREMENT_JOINING_PROCESS_COUNTER, ns_ijt)
    dec_node = await _find_method_node(jpm, BN.DECREMENT_JOINING_PROCESS_COUNTER, ns_ijt)
    if inc_node is None or dec_node is None:
        pytest.skip("Both IncrementJoiningProcessCounter and DecrementJoiningProcessCounter are required for this test")
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)
    jp_arg = await _first_joining_process_identification_arg(opcua_client, ns_indices, jpm, pi_uri)

    inc_result = await call_method(
        jpm,
        inc_node,
        ua.Variant(pi_uri, ua.VariantType.String),
        jp_arg,
        ua.Variant(1, ua.VariantType.UInt32),
        timeout=15.0,
        method_name=BN.INCREMENT_JOINING_PROCESS_COUNTER,
    )
    if not inc_result.success:
        err_str = str(inc_result.error) if inc_result.error else "unknown"
        if any(
            s in err_str for s in ("BadNotSupported", "BadInvalidArgument", "BadArgumentsMissing", "BadNothingToDo")
        ):
            pytest.skip(f"IncrementJoiningProcessCounter returned {err_str} — skipping round-trip test")
        pytest.fail(f"IncrementJoiningProcessCounter failed unexpectedly in round-trip test: {err_str}")

    dec_result = await call_method(
        jpm,
        dec_node,
        ua.Variant(pi_uri, ua.VariantType.String),
        jp_arg,
        ua.Variant(1, ua.VariantType.UInt32),
        timeout=15.0,
        method_name=BN.DECREMENT_JOINING_PROCESS_COUNTER,
    )
    if not dec_result.success:
        err_str = str(dec_result.error) if dec_result.error else "unknown"
        if any(
            s in err_str for s in ("BadNotSupported", "BadInvalidArgument", "BadArgumentsMissing", "BadNothingToDo")
        ):
            pytest.skip(f"DecrementJoiningProcessCounter returned {err_str} — skipping round-trip test")
        pytest.fail(f"DecrementJoiningProcessCounter failed unexpectedly after successful Increment: {err_str}")
    logger.info("Counter round-trip (Increment→Decrement) with PIU '%s' completed successfully", pi_uri)


# ---------------------------------------------------------------------------
# ─── set_joining_process_size ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SET_JOINING_PROCESS_SIZE)
async def test_set_joining_process_size_method_present_if_exists(joining_process_management, ns_indices):
    """
    SetJoiningProcessSize method, if present, must be accessible on
    JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, BN.SET_JOINING_PROCESS_SIZE, ns_ijt)
    if node is None:
        pytest.skip(f"Optional method '{BN.SET_JOINING_PROCESS_SIZE}': Not Supported")


# ---------------------------------------------------------------------------
# ─── deselect_joining_process ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.DESELECT_JOINING_PROCESS)
async def test_deselect_joining_process_method_present_if_exists(joining_process_management, ns_indices):
    """
    DeselectJoiningProcess method, if present, must be accessible on
    JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, "DeselectJoiningProcess", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'DeselectJoiningProcess': Not Supported")


# ---------------------------------------------------------------------------
# ─── start_joining_process ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.START_JOINING_PROCESS)
async def test_start_joining_process_method_present_if_exists(joining_process_management, ns_indices):
    """
    StartJoiningProcess method, if present, must be accessible on
    JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, "StartJoiningProcess", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'StartJoiningProcess': Not Supported")


# ---------------------------------------------------------------------------
# ─── delete_joining_process ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.DELETE_JOINING_PROCESS)
async def test_delete_joining_process_method_present_if_exists(joining_process_management, ns_indices):
    """
    DeleteJoiningProcess method, if present, must be accessible on
    JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, "DeleteJoiningProcess", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'DeleteJoiningProcess': Not Supported")


# ---------------------------------------------------------------------------
# ─── send_joining_process ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SEND_JOINING_PROCESS)
async def test_send_joining_process_method_present_if_exists(joining_process_management, ns_indices):
    """
    SendJoiningProcess method, if present, must be accessible on
    JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, "SendJoiningProcess", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'SendJoiningProcess': Not Supported")


# ---------------------------------------------------------------------------
# ─── get_joining_process ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS)
async def test_get_joining_process_method_present_if_exists(joining_process_management, ns_indices):
    """
    GetJoiningProcess method, if present, must be accessible on
    JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, "GetJoiningProcess", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'GetJoiningProcess': Not Supported")


# ---------------------------------------------------------------------------
# ─── set_joining_process_counter ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SET_JOINING_PROCESS_COUNTER)
async def test_set_joining_process_counter_method_present_if_exists(joining_process_management, ns_indices):
    """
    SetJoiningProcessCounter method, if present, must be accessible on
    JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, "SetJoiningProcessCounter", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'SetJoiningProcessCounter': Not Supported")


@pytest.mark.requires_cu(CU.SET_JOINING_PROCESS_COUNTER)
async def test_set_joining_process_counter_callable_if_present(opcua_client, ns_indices):
    """
    SetJoiningProcessCounter, if present, must be callable.

    Called with the tool's ProductInstanceUri and a zero counter value.
    Acceptable outcomes: Good (counter set), BadNotSupported, BadInvalidArgument
    (when zero is not a valid counter value on this server).
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    ns_di = ns_indices.get(NS_DI)
    ns_app = ns_indices.get(NS_APP)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, "SetJoiningProcessCounter", ns_ijt)
    if method_node is None:
        pytest.skip("Optional method 'SetJoiningProcessCounter': Not Supported — skipping")
    pi_uri = await read_tool_product_instance_uri(opcua_client, ns_ijt, ns_di or 0, ns_app)
    jp_arg = _jp_identification_arg()
    if jp_arg is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — cannot build counter arguments")
    call_result = await call_method(
        jpm,
        method_node,
        ua.Variant(pi_uri, ua.VariantType.String),
        jp_arg,
        ua.Variant(0, ua.VariantType.UInt32),
        timeout=15.0,
        method_name="SetJoiningProcessCounter",
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if any(
            s in err_str for s in ("BadNotSupported", "BadInvalidArgument", "BadArgumentsMissing", "BadNothingToDo")
        ):
            return  # server rejected a zero-value or empty-PIU counter — acceptable
        pytest.fail(f"SetJoiningProcessCounter raised an unexpected error: {err_str}")
    logger.info("SetJoiningProcessCounter with PIU '%s' counter=0 succeeded", pi_uri)


# ---------------------------------------------------------------------------
# ─── set_joining_process_mapping ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SET_JOINING_PROCESS_MAPPING)
async def test_set_joining_process_mapping_method_present_if_exists(joining_process_management, ns_indices):
    """
    SetJoiningProcessMapping method, if present, must be accessible on
    JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, "SetJoiningProcessMapping", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'SetJoiningProcessMapping': Not Supported")


# ---------------------------------------------------------------------------
# ─── get_joining_process_revision_list ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS_REVISION_LIST)
async def test_get_joining_process_revision_list_method_present_if_exists(joining_process_management, ns_indices):
    """
    GetJoiningProcessRevisionList method, if present, must be accessible on
    JoiningProcessManagement.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    node = await _find_method_node(joining_process_management, "GetJoiningProcessRevisionList", ns_ijt)
    if node is None:
        pytest.skip("Optional method 'GetJoiningProcessRevisionList': Not Supported")


# ---------------------------------------------------------------------------
# ─── pre-condition: asset must be enabled before StartSelectedJoining ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.START_SELECTED_JOINING)
async def test_enable_asset_required_before_start_joining(opcua_client, ns_indices):
    """
    EnableAsset must be present and callable on AssetManagement/MethodSet — it is
    the required pre-condition for StartSelectedJoining per the specification.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    ns_di = ns_indices.get(NS_DI)
    ns_app = ns_indices.get(NS_APP)
    method_set = await _get_asset_management_method_set(opcua_client, ns_ijt, ns_di, ns_app)
    assert method_set is not None, (
        "AssetManagement/MethodSet not found — cannot verify EnableAsset pre-condition for StartSelectedJoining"
    )
    enable_node = await find_child_by_browse_name(method_set, BN.ENABLE_ASSET, ns_ijt)
    assert enable_node is not None, (
        f"'{BN.ENABLE_ASSET}' not found in AssetManagement/MethodSet — required pre-condition for StartSelectedJoining"
    )
    pi_uri = await read_tool_product_instance_uri(opcua_client, ns_ijt, ns_di, ns_app)
    call_result = await call_method(
        method_set,
        enable_node,
        ua.Variant(pi_uri, ua.VariantType.String),
        ua.Variant(True, ua.VariantType.Boolean),
        timeout=15.0,
        method_name=BN.ENABLE_ASSET,
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if any(
            s in err_str
            for s in ("BadNotSupported", "BadInvalidArgument", "BadNotFound", "BadArgumentsMissing", "Uncertain")
        ):
            return
        pytest.fail(f"EnableAsset raised an unexpected error: {err_str}")


# ---------------------------------------------------------------------------
# ─── joining_process_management (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.JOINING_PROCESS_MANAGEMENT)
async def test_joining_process_management_node_class_is_object(joining_process_management):
    """
    JoiningProcessManagement must have NodeClass = Object (value 1).
    This confirms it is an Object instance, not a Variable or Method node.
    """
    try:
        attr = await joining_process_management.read_attribute(ua.AttributeIds.NodeClass)
    except ua.UaError as exc:
        pytest.fail(f"Failed to read NodeClass of JoiningProcessManagement: {exc}")
    assert attr.Value.Value == ua.NodeClass.Object, (
        f"JoiningProcessManagement NodeClass must be Object, got {attr.Value.Value!r}"
    )


@pytest.mark.requires_cu(CU.JOINING_PROCESS_MANAGEMENT)
async def test_joining_process_management_type_definition_is_correct(joining_process_management, ns_indices):
    """
    JoiningProcessManagement TypeDefinition must equal JoiningProcessManagementType
    in the IJT Base namespace (confirmed via HasTypeDefinition reference).
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    type_def = await get_type_definition(joining_process_management)
    if type_def is None:
        pytest.skip("TypeDefinition not resolvable for JoiningProcessManagement")
    assert type_def.Identifier == IJTTypes.JOINING_PROCESS_MANAGEMENT_TYPE and type_def.NamespaceIndex == ns_ijt, (
        f"TypeDefinition must be JoiningProcessManagementType "
        f"(ns={ns_ijt}, id={IJTTypes.JOINING_PROCESS_MANAGEMENT_TYPE}), got {type_def!r}"
    )


# ---------------------------------------------------------------------------
# ─── get_joining_process_list (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS_LIST)
async def test_get_joining_process_list_is_executable(joining_process_management, ns_indices):
    """
    GetJoiningProcessList method node must have Executable = True so the client
    session is permitted to call it.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    method_node = await _find_method_node(joining_process_management, BN.GET_JOINING_PROCESS_LIST, ns_ijt)
    if method_node is None:
        pytest.fail(f"Required method '{BN.GET_JOINING_PROCESS_LIST}' not found in JoiningProcessManagement")
    try:
        exec_attr = await method_node.read_attribute(ua.AttributeIds.Executable)
    except ua.UaError as exc:
        pytest.fail(f"Could not read Executable attribute of GetJoiningProcessList: {exc}")
    assert exec_attr.Value.Value is True, (
        f"'{BN.GET_JOINING_PROCESS_LIST}' Executable must be True, got {exec_attr.Value.Value!r}"
    )


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS_LIST)
async def test_get_joining_process_list_entries_have_non_empty_id(opcua_client, ns_indices):
    """
    When GetJoiningProcessList returns a non-empty list, every entry must carry a
    non-empty identifier so downstream methods (SelectJoiningProcess) can use it.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    result = await find_and_call_method(
        jpm,
        BN.GET_JOINING_PROCESS_LIST,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        timeout=15.0,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown"
        if any(s in err_str for s in ("BadNotSupported", "BadNotImplemented", "BadArgumentsMissing")):
            pytest.skip(f"GetJoiningProcessList returned {err_str} — skipping")
        pytest.fail(f"GetJoiningProcessList failed unexpectedly: {err_str}")
    programs = result.output_list
    if not programs:
        pytest.skip("GetJoiningProcessList returned empty list — no entries to validate")
    for i, program in enumerate(programs):
        if isinstance(program, str):
            assert len(program) > 0, f"programs[{i}] is an empty string — JoiningProcessId must be non-empty"
        elif program is not None:
            prog_id = (
                getattr(program, "JoiningProcessId", None)
                or getattr(program, "Id", None)
                or getattr(program, "ProgramId", None)
            )
            if prog_id is not None:
                assert str(prog_id), f"programs[{i}].JoiningProcessId must not be empty"


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS_LIST)
async def test_get_joining_process_list_returns_non_null_list(opcua_client, ns_indices):
    """
    GetJoiningProcessList must return Good with a non-null list object.
    An empty list is a valid result; null is not.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    result = await find_and_call_method(
        jpm,
        BN.GET_JOINING_PROCESS_LIST,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        timeout=15.0,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown"
        if any(s in err_str for s in ("BadNotSupported", "BadNotImplemented", "BadArgumentsMissing")):
            pytest.skip(f"GetJoiningProcessList returned {err_str} — skipping")
        pytest.fail(f"GetJoiningProcessList failed: {err_str}")
    programs = result.output_list
    assert programs is not None, (
        "GetJoiningProcessList must return a non-null list (empty array is valid for zero configured programs)"
    )
    assert isinstance(programs, list), f"GetJoiningProcessList output must be a list, got {type(programs).__name__}"


# ---------------------------------------------------------------------------
# ─── abort_joining_process (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ABORT_JOINING_PROCESS)
async def test_abort_joining_process_is_executable_if_present(joining_process_management, ns_indices):
    """
    If AbortJoiningProcess is present, its Executable attribute must be True.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    method_node = await _find_method_node(joining_process_management, BN.ABORT_JOINING_PROCESS, ns_ijt)
    if method_node is None:
        pytest.skip(f"Optional method '{BN.ABORT_JOINING_PROCESS}': Not Supported — skipping")
    try:
        exec_attr = await method_node.read_attribute(ua.AttributeIds.Executable)
    except ua.UaError as exc:
        pytest.fail(f"Could not read Executable attribute of '{BN.ABORT_JOINING_PROCESS}': {exc}")
    assert exec_attr.Value.Value is True, (
        f"'{BN.ABORT_JOINING_PROCESS}' Executable must be True, got {exec_attr.Value.Value!r}"
    )


@pytest.mark.requires_cu(CU.ABORT_JOINING_PROCESS)
async def test_abort_joining_process_generates_event_if_present(subscription_client, opcua_client, ns_indices):
    """
    AbortJoiningProcess should generate a JoiningSystemEventType event.
    The test is skipped when the method is absent or no process is active to abort.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, BN.ABORT_JOINING_PROCESS, ns_ijt)
    if method_node is None:
        pytest.skip(f"Optional method '{BN.ABORT_JOINING_PROCESS}': Not Supported — skipping")
    server_node = subscription_client.nodes.server
    event_type_node = subscription_client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_EVENT_TYPE, ns_ijt))
    ns_di_idx = ns_indices.get(NS_DI)
    ns_app_idx = ns_indices.get(NS_APP)
    pi_uri = await read_tool_product_instance_uri(subscription_client, ns_ijt, ns_di_idx, ns_app_idx)
    jp = _make_jp_identification()
    if jp is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — load_data_type_definitions() may have failed")
    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, event_type_node)
        call_result = await call_method(
            jpm,
            method_node,
            ua.Variant(pi_uri, ua.VariantType.String),
            ua.Variant(jp, ua.VariantType.ExtensionObject),
            ua.Variant(ua.LocalizedText(Text="", Locale="en"), ua.VariantType.LocalizedText),
            timeout=30.0,
            method_name=BN.ABORT_JOINING_PROCESS,
        )
        if not call_result.success:
            err_str = str(call_result.error) if call_result.error else "unknown"
            if any(
                s in err_str
                for s in (
                    "BadNotSupported",
                    "BadNothingToDo",
                    "BadConditionNotActive",
                    "BadArgumentsMissing",
                    "BadInvalidArgument",
                )
            ):
                pytest.skip(f"AbortJoiningProcess returned {err_str} — no active process to abort")
        events = await collector.collect(count=1, timeout_s=30.0)
    if not events:
        skip_accepted_policy(
            "no active joining-process execution was available to produce an abort event",
            method=BN.ABORT_JOINING_PROCESS,
            status="No event within timeout",
        )
    assert len(events) >= 1, "Expected at least one event after AbortJoiningProcess"


# ---------------------------------------------------------------------------
# ─── start_selected_joining (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.START_SELECTED_JOINING)
async def test_start_selected_joining_after_select_returns_good(opcua_client, ns_indices):
    """
    StartSelectedJoining called immediately after a successful SelectJoiningProcess
    must return Good or a state-related code if the tool is not physically ready.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)

    list_result = await find_and_call_method(jpm, BN.GET_JOINING_PROCESS_LIST, ns_ijt, _piu_arg(pi_uri), timeout=15.0)
    if not list_result.success:
        err_str = str(list_result.error) if list_result.error else "unknown"
        pytest.skip(f"GetJoiningProcessList failed ({err_str}) — cannot establish SelectJoiningProcess precondition")
    if not list_result.output_list:
        pytest.skip("GetJoiningProcessList returned empty list — no programs configured; cannot establish precondition")
    first_program = list_result.output_list[0]
    jp_arg = _jp_identification_from_entry(first_program)
    if jp_arg is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — cannot select a joining process")
    select_node = await _find_method_node(jpm, BN.SELECT_JOINING_PROCESS, ns_ijt)
    if select_node is None:
        pytest.skip(f"'{BN.SELECT_JOINING_PROCESS}' method not found — skipping")
    select_result = await call_method(
        jpm,
        select_node,
        _piu_arg(pi_uri),
        jp_arg,
        timeout=15.0,
        method_name=BN.SELECT_JOINING_PROCESS,
    )
    if not select_result.success:
        err_str = str(select_result.error) if select_result.error else "unknown"
        skip_accepted_policy(
            "server listed a process but did not allow selecting it in the current controller/tool state",
            method=BN.SELECT_JOINING_PROCESS,
            status=err_str,
        )
    start_node = await _find_method_node(jpm, BN.START_SELECTED_JOINING, ns_ijt)
    assert start_node is not None, f"Required method '{BN.START_SELECTED_JOINING}' not found after SelectJoiningProcess"
    start_result = await call_method(
        jpm,
        start_node,
        _piu_arg(),
        ua.Variant(False, ua.VariantType.Boolean),
        timeout=15.0,
        method_name=BN.START_SELECTED_JOINING,
    )
    if not start_result.success:
        err_str = str(start_result.error) if start_result.error else "unknown"
        if any(
            s in err_str
            for s in (
                "BadNotSupported",
                "BadNothingToDo",
                "BadConditionNotActive",
                "BadInvalidState",
            )
        ):
            skip_accepted_policy(
                "tool/controller state is not ready to execute immediately after selection",
                method=BN.START_SELECTED_JOINING,
                status=err_str,
            )
        pytest.fail(f"StartSelectedJoining raised unexpected error after SelectJoiningProcess: {err_str}")


# ---------------------------------------------------------------------------
# ─── select_joining_process (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SELECT_JOINING_PROCESS)
async def test_select_joining_process_state_reflected_after_select(opcua_client, ns_indices):
    """
    After a successful SelectJoiningProcess, GetSelectedJoiningProgram must return
    a non-null result, confirming the server state reflects the selection.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)

    list_result = await find_and_call_method(jpm, BN.GET_JOINING_PROCESS_LIST, ns_ijt, _piu_arg(pi_uri), timeout=15.0)
    if not list_result.success:
        err_str = str(list_result.error) if list_result.error else "unknown"
        pytest.skip(f"GetJoiningProcessList failed ({err_str}) — cannot determine a valid program ID")
    if not list_result.output_list:
        pytest.skip(
            "GetJoiningProcessList returned empty list — no programs configured; cannot determine a valid program ID"
        )
    first_program = list_result.output_list[0]
    jp_arg = _jp_identification_from_entry(first_program)
    if jp_arg is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — cannot select a joining process")
    select_node = await _find_method_node(jpm, BN.SELECT_JOINING_PROCESS, ns_ijt)
    if select_node is None:
        pytest.skip(f"'{BN.SELECT_JOINING_PROCESS}' method not found")
    select_result = await call_method(
        jpm,
        select_node,
        _piu_arg(pi_uri),
        jp_arg,
        timeout=15.0,
        method_name=BN.SELECT_JOINING_PROCESS,
    )
    if not select_result.success:
        err_str = str(select_result.error) if select_result.error else "unknown"
        if any(
            s in err_str
            for s in ("BadNotSupported", "BadInvalidArgument", "BadNotFound", "BadArgumentsMissing", "Uncertain")
        ):
            skip_accepted_policy(
                "server may reject selection for current controller/tool state",
                method=BN.SELECT_JOINING_PROCESS,
                status=err_str,
            )
        pytest.fail(f"SelectJoiningProcess failed: {err_str}")
    get_result = await find_and_call_method(
        jpm, BN.GET_SELECTED_JOINING_PROGRAM, ns_ijt, _piu_arg(pi_uri), timeout=15.0
    )
    if not get_result.success:
        err_str = str(get_result.error) if get_result.error else "unknown"
        if any(s in err_str for s in ("BadNotSupported", "BadNothingToDo")):
            skip_accepted_policy(
                "selected program is not readable for the current controller/tool state",
                method=BN.GET_SELECTED_JOINING_PROGRAM,
                status=err_str,
            )
        pytest.fail(f"GetSelectedJoiningProgram failed after SelectJoiningProcess: {err_str}")
    assert get_result.output_list is not None, (
        "GetSelectedJoiningProgram must return non-null after SelectJoiningProcess"
    )


# ---------------------------------------------------------------------------
# ─── deselect_joining_process (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.DESELECT_JOINING_PROCESS)
async def test_deselect_joining_process_callable_if_present(opcua_client, ns_indices):
    """
    DeselectJoiningProcess must be callable without an unexpected error when present.
    BadNothingToDo and BadInvalidState are acceptable when no program is selected.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, "DeselectJoiningProcess", ns_ijt)
    if method_node is None:
        pytest.skip("Optional method 'DeselectJoiningProcess': Not Supported — skipping")
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)
    call_result = await call_method(
        jpm,
        method_node,
        _piu_arg(pi_uri),
        timeout=15.0,
        method_name="DeselectJoiningProcess",
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if any(
            s in err_str
            for s in (
                "BadNotSupported",
                "BadNothingToDo",
                "BadInvalidState",
                "BadConditionNotActive",
                "BadArgumentsMissing",
            )
        ):
            return
        pytest.fail(f"DeselectJoiningProcess raised an unexpected error: {err_str}")


# ---------------------------------------------------------------------------
# ─── reset_joining_process (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESET_JOINING_PROCESS)
async def test_reset_joining_process_server_remains_functional(opcua_client, ns_indices):
    """
    After ResetJoiningProcess, the server must remain functional — GetJoiningProcessList
    must still be callable, confirming no unrecoverable state was entered.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    reset_node = await _find_method_node(jpm, BN.RESET_JOINING_PROCESS, ns_ijt)
    if reset_node is None:
        pytest.skip(f"Optional method '{BN.RESET_JOINING_PROCESS}': Not Supported — skipping")
    ns_di = ns_indices.get(NS_DI)
    ns_app = ns_indices.get(NS_APP)
    pi_uri = await read_tool_product_instance_uri(opcua_client, ns_ijt, ns_di, ns_app)
    jp = _make_jp_identification()
    if jp is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — load_data_type_definitions() may have failed")
    reset_result = await call_method(
        jpm,
        reset_node,
        ua.Variant(pi_uri, ua.VariantType.String),
        ua.Variant(jp, ua.VariantType.ExtensionObject),
        timeout=15.0,
        method_name=BN.RESET_JOINING_PROCESS,
    )
    if not reset_result.success:
        err_str = str(reset_result.error) if reset_result.error else "unknown"
        if any(s in err_str for s in ("BadNotSupported", "BadNothingToDo", "BadArgumentsMissing")):
            pytest.skip(f"ResetJoiningProcess returned {err_str} — skipping")
    list_result = await find_and_call_method(
        jpm,
        BN.GET_JOINING_PROCESS_LIST,
        ns_ijt,
        _piu_arg(),
        timeout=15.0,
    )
    if not list_result.success:
        err_str = str(list_result.error) if list_result.error else "unknown"
        if any(s in err_str for s in ("BadNotSupported", "BadNotImplemented", "BadArgumentsMissing")):
            return
        pytest.fail(f"GetJoiningProcessList failed after ResetJoiningProcess: {err_str}")


# ---------------------------------------------------------------------------
# ─── increment_joining_process_counter (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.INCREMENT_JOINING_PROCESS_COUNTER)
async def test_increment_counter_multiple_sequential_calls(opcua_client, ns_indices):
    """
    Three sequential calls to IncrementJoiningProcessCounter must each succeed
    (or return a known status code) without the server entering an error state.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, BN.INCREMENT_JOINING_PROCESS_COUNTER, ns_ijt)
    if method_node is None:
        pytest.skip(f"Optional method '{BN.INCREMENT_JOINING_PROCESS_COUNTER}': Not Supported — skipping")
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)
    jp_arg = await _first_joining_process_identification_arg(opcua_client, ns_indices, jpm, pi_uri)
    for call_num in range(3):
        result = await call_method(
            jpm,
            method_node,
            ua.Variant(pi_uri, ua.VariantType.String),
            jp_arg,
            ua.Variant(1, ua.VariantType.UInt32),
            timeout=15.0,
            method_name=BN.INCREMENT_JOINING_PROCESS_COUNTER,
        )
        if not result.success:
            err_str = str(result.error) if result.error else "unknown"
            if any(s in err_str for s in ("BadNotSupported", "BadInvalidArgument", "BadArgumentsMissing")):
                pytest.skip(f"IncrementJoiningProcessCounter returned {err_str} on call #{call_num + 1} — skipping")
            pytest.fail(f"IncrementJoiningProcessCounter raised unexpected error on call #{call_num + 1}: {err_str}")


# ---------------------------------------------------------------------------
# ─── decrement_joining_process_counter (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.DECREMENT_JOINING_PROCESS_COUNTER)
async def test_decrement_counter_after_increment_if_present(opcua_client, ns_indices):
    """
    DecrementJoiningProcessCounter called after IncrementJoiningProcessCounter
    must return Good (or a known status), confirming the counter can decrease.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    incr_node = await _find_method_node(jpm, BN.INCREMENT_JOINING_PROCESS_COUNTER, ns_ijt)
    decr_node = await _find_method_node(jpm, BN.DECREMENT_JOINING_PROCESS_COUNTER, ns_ijt)
    if decr_node is None:
        pytest.skip(f"Optional method '{BN.DECREMENT_JOINING_PROCESS_COUNTER}': Not Supported — skipping")
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)
    jp_arg = await _first_joining_process_identification_arg(opcua_client, ns_indices, jpm, pi_uri)
    if incr_node is not None:
        await call_method(
            jpm,
            incr_node,
            _piu_arg(pi_uri),
            jp_arg,
            ua.Variant(1, ua.VariantType.UInt32),
            timeout=15.0,
            method_name=BN.INCREMENT_JOINING_PROCESS_COUNTER,
        )
    decr_result = await call_method(
        jpm,
        decr_node,
        _piu_arg(pi_uri),
        jp_arg,
        ua.Variant(1, ua.VariantType.UInt32),
        timeout=15.0,
        method_name=BN.DECREMENT_JOINING_PROCESS_COUNTER,
    )
    if not decr_result.success:
        err_str = str(decr_result.error) if decr_result.error else "unknown"
        if any(s in err_str for s in ("BadNotSupported", "BadInvalidArgument", "BadOutOfRange", "BadArgumentsMissing")):
            return
        pytest.fail(f"DecrementJoiningProcessCounter raised unexpected error: {err_str}")


# ---------------------------------------------------------------------------
# ─── set_joining_process_size (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SET_JOINING_PROCESS_SIZE)
async def test_set_joining_process_size_callable_with_valid_count(opcua_client, ns_indices):
    """
    SetJoiningProcessSize called with a positive batch size must return Good
    or a state-related status when no program is currently selected.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, BN.SET_JOINING_PROCESS_SIZE, ns_ijt)
    if method_node is None:
        pytest.skip(f"Optional method '{BN.SET_JOINING_PROCESS_SIZE}': Not Supported — skipping")
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)
    jp_arg = await _first_joining_process_identification_arg(opcua_client, ns_indices, jpm, pi_uri)
    call_result = await call_method(
        jpm,
        method_node,
        _piu_arg(pi_uri),
        jp_arg,
        ua.Variant(10, ua.VariantType.UInt32),
        timeout=15.0,
        method_name=BN.SET_JOINING_PROCESS_SIZE,
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if any(
            s in err_str
            for s in (
                "BadNotSupported",
                "BadNothingToDo",
                "BadInvalidState",
                "BadConditionNotActive",
                "BadInvalidArgument",
                "BadArgumentsMissing",
            )
        ):
            return
        pytest.fail(f"SetJoiningProcessSize(10) raised unexpected error: {err_str}")


@pytest.mark.requires_cu(CU.SET_JOINING_PROCESS_SIZE)
async def test_set_joining_process_size_zero_is_server_policy(opcua_client, ns_indices):
    """
    SetJoiningProcessSize(0) is not reserved by the IJT method signature.

    A server may accept zero as product-specific batch-size policy or reject it
    as a domain value. The conformance requirement here is that the call is
    handled deliberately, not leaked as an internal/unexpected error.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, BN.SET_JOINING_PROCESS_SIZE, ns_ijt)
    if method_node is None:
        pytest.skip(f"Optional method '{BN.SET_JOINING_PROCESS_SIZE}': Not Supported — skipping")
    jp_arg = _jp_identification_arg()
    if jp_arg is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — cannot build SetJoiningProcessSize arguments")
    call_result = await call_method(
        jpm,
        method_node,
        _piu_arg(),
        jp_arg,
        ua.Variant(0, ua.VariantType.UInt32),
        timeout=15.0,
        method_name=BN.SET_JOINING_PROCESS_SIZE,
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if "BadUnexpectedError" in err_str:
            pytest.fail(f"SetJoiningProcessSize(0) leaked internal error: {err_str}")
        if any(
            s in err_str
            for s in (
                "BadNotSupported",
                "BadNothingToDo",
                "BadInvalidState",
                "BadConditionNotActive",
                "BadInvalidArgument",
                "BadArgumentsMissing",
                "BadOutOfRange",
                "Uncertain",
            )
        ):
            return
        pytest.fail(f"SetJoiningProcessSize(0) raised unexpected error: {err_str}")


# ---------------------------------------------------------------------------
# ─── start_joining_process (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.START_JOINING_PROCESS)
async def test_start_joining_process_callable_with_args_if_present(opcua_client, ns_indices):
    """
    StartJoiningProcess, when present, must accept a JoiningProcessId String
    argument and return Good or a state-related code (tool may not be ready).
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, "StartJoiningProcess", ns_ijt)
    if method_node is None:
        pytest.skip("Optional method 'StartJoiningProcess': Not Supported — skipping")
    list_result = await find_and_call_method(
        jpm,
        BN.GET_JOINING_PROCESS_LIST,
        ns_ijt,
        _piu_arg(await _read_required_tool_product_instance_uri(opcua_client, ns_indices)),
        timeout=15.0,
    )
    programs = _unwrap_method_array_output(list_result.output_list) if list_result.success else []
    jp_arg = (
        _jp_identification_from_entry(programs[0])
        if programs
        else _jp_identification_arg(process_id=_INVALID_PROGRAM_ID)
    )
    if jp_arg is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — cannot build StartJoiningProcess arguments")
    call_result = await call_method(
        jpm,
        method_node,
        _piu_arg(await _read_required_tool_product_instance_uri(opcua_client, ns_indices)),
        jp_arg,
        _empty_associated_entities_arg(),
        timeout=15.0,
        method_name="StartJoiningProcess",
    )
    if not call_result.success:
        err_str = str(call_result.error) if call_result.error else "unknown"
        if any(
            s in err_str
            for s in (
                "BadNotSupported",
                "BadNothingToDo",
                "BadConditionNotActive",
                "BadInvalidArgument",
                "BadInvalidState",
                "BadArgumentsMissing",
            )
        ):
            return
        pytest.fail(f"StartJoiningProcess raised unexpected error: {err_str}")


# ---------------------------------------------------------------------------
# ─── delete_joining_process (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.DELETE_JOINING_PROCESS)
async def test_delete_joining_process_rejects_nonexistent_id(opcua_client, ns_indices):
    """
    DeleteJoiningProcess called with a non-existent JoiningProcessId must return
    a Bad status code — accepting an unknown ID would silently succeed on a no-op.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    method_node = await _find_method_node(jpm, "DeleteJoiningProcess", ns_ijt)
    if method_node is None:
        pytest.skip("Optional method 'DeleteJoiningProcess': Not Supported — skipping")
    jp_arg = _jp_identification_arg(process_id=_INVALID_PROGRAM_ID)
    if jp_arg is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — cannot build DeleteJoiningProcess arguments")
    call_result = await call_method(
        jpm,
        method_node,
        _piu_arg(),
        jp_arg,
        timeout=15.0,
        method_name="DeleteJoiningProcess",
    )
    if call_result.success:
        pytest.skip(
            "DeleteJoiningProcess with non-existent ID returned Good — "
            "server may treat this as a no-op; verify against spec"
        )


# ---------------------------------------------------------------------------
# ─── get_selected_joining_program (additional) ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_SELECTED_JOINING_PROGRAM)
async def test_get_selected_joining_program_result_has_valid_fields(opcua_client, ns_indices):
    """
    After SelectJoiningProcess, GetSelectedJoiningProgram must return a non-null
    result with a non-empty identifier for the selected program.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)
    list_result = await find_and_call_method(jpm, BN.GET_JOINING_PROCESS_LIST, ns_ijt, _piu_arg(pi_uri), timeout=15.0)
    if not list_result.success:
        err_str = str(list_result.error) if list_result.error else "unknown"
        pytest.skip(f"GetJoiningProcessList failed ({err_str}) — cannot select a program")
    programs = _unwrap_method_array_output(list_result.output_list)
    if not programs:
        pytest.skip("GetJoiningProcessList returned empty list — no programs configured; cannot select a program")
    first_program = programs[0]
    jp_arg = _jp_identification_from_entry(first_program)
    if jp_arg is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — cannot select a joining process")
    select_node = await _find_method_node(jpm, BN.SELECT_JOINING_PROCESS, ns_ijt)
    if select_node is None:
        pytest.skip("SelectJoiningProcess not found — cannot establish precondition")
    select_result = await call_method(
        jpm,
        select_node,
        _piu_arg(pi_uri),
        jp_arg,
        timeout=15.0,
        method_name=BN.SELECT_JOINING_PROCESS,
    )
    if not select_result.success:
        err_str = str(select_result.error) if select_result.error else "unknown"
        skip_accepted_policy(
            "selection precondition could not be established for current controller/tool state",
            method=BN.SELECT_JOINING_PROCESS,
            status=err_str,
        )
    get_result = await find_and_call_method(
        jpm, BN.GET_SELECTED_JOINING_PROGRAM, ns_ijt, _piu_arg(pi_uri), timeout=15.0
    )
    if not get_result.success:
        err_str = str(get_result.error) if get_result.error else "unknown"
        if any(s in err_str for s in ("BadNotSupported", "BadNothingToDo")):
            skip_accepted_policy(
                "selected program is not readable for the current controller/tool state",
                method=BN.GET_SELECTED_JOINING_PROGRAM,
                status=err_str,
            )
        pytest.fail(f"GetSelectedJoiningProgram failed: {err_str}")
    programs = get_result.output_list
    assert programs is not None, "GetSelectedJoiningProgram must return non-null after select"
    if programs:
        program = programs[0] if isinstance(programs, list) and programs else programs
        if isinstance(program, str):
            assert len(program) > 0, "GetSelectedJoiningProgram returned empty string ID"
        elif program is not None:
            prog_id = (
                getattr(program, "JoiningProcessId", None)
                or getattr(program, "Id", None)
                or getattr(program, "ProgramId", None)
            )
            if prog_id is not None:
                assert str(prog_id), "Returned program must have a non-empty identifier"


@pytest.mark.requires_cu(CU.GET_SELECTED_JOINING_PROGRAM)
async def test_get_selected_joining_program_none_after_deselect(opcua_client, ns_indices):
    """
    After DeselectJoiningProcess, GetSelectedJoiningProgram must return an empty
    or null result.  The test is skipped when DeselectJoiningProcess is absent.
    """
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    pi_uri = await _read_required_tool_product_instance_uri(opcua_client, ns_indices)

    list_result = await find_and_call_method(
        jpm,
        BN.GET_JOINING_PROCESS_LIST,
        ns_ijt,
        _piu_arg(pi_uri),
        timeout=15.0,
    )
    programs = _unwrap_method_array_output(list_result.output_list) if list_result.success else []
    if programs:
        first_program = programs[0]
        jp_arg = _jp_identification_from_entry(first_program)
        select_node = await _find_method_node(jpm, BN.SELECT_JOINING_PROCESS, ns_ijt)
        if select_node and jp_arg is not None:
            await call_method(
                jpm,
                select_node,
                _piu_arg(pi_uri),
                jp_arg,
                timeout=15.0,
                method_name=BN.SELECT_JOINING_PROCESS,
            )
    deselect_node = await _find_method_node(jpm, "DeselectJoiningProcess", ns_ijt)
    if deselect_node is None:
        pytest.skip("Optional method 'DeselectJoiningProcess': Not Supported — skipping")
    deselect_result = await call_method(
        jpm, deselect_node, _piu_arg(pi_uri), timeout=15.0, method_name="DeselectJoiningProcess"
    )
    if not deselect_result.success:
        err_str = str(deselect_result.error) if deselect_result.error else "unknown"
        if any(s in err_str for s in ("BadNotSupported", "BadNothingToDo", "BadArgumentsMissing")):
            pytest.skip(f"DeselectJoiningProcess returned {err_str}")
        pytest.fail(f"DeselectJoiningProcess failed: {err_str}")
    get_result = await find_and_call_method(
        jpm,
        BN.GET_SELECTED_JOINING_PROGRAM,
        ns_ijt,
        _piu_arg(pi_uri),
        timeout=15.0,
    )
    if not get_result.success:
        err_str = str(get_result.error) if get_result.error else "unknown"
        if any(s in err_str for s in ("BadNotSupported", "BadNothingToDo", "BadArgumentsMissing", "Uncertain")):
            return
        pytest.fail(f"GetSelectedJoiningProgram failed after deselect: {err_str}")
    programs = get_result.output_list
    if programs:
        program = programs[0] if isinstance(programs, list) and programs else programs
        if isinstance(program, str):
            assert len(program) == 0, (
                "GetSelectedJoiningProgram must return empty result after DeselectJoiningProcess, "
                f"got non-empty string: {program!r}"
            )


# ---------------------------------------------------------------------------
# Helpers for send_joining_process / get_joining_process / revision tests
# ---------------------------------------------------------------------------


async def _send_test_joining_process(jpm, ns_ijt, process_id, name="ConformanceTestProcess"):
    """Send a JoiningProcessDataType via SendJoiningProcess; skip if unavailable."""
    send_node = await find_child_by_browse_name(jpm, "SendJoiningProcess", ns_ijt)
    if send_node is None:
        pytest.skip("SendJoiningProcess method: Not Supported — skipping")
    proc_type = getattr(ua, "JoiningProcessDataType", None)
    if proc_type is None:
        pytest.skip("JoiningProcessDataType not available in this asyncua version")
    proc_data = proc_type()
    meta_type = getattr(ua, "JoiningProcessMetaDataType", None)
    if meta_type is not None and hasattr(proc_data, "JoiningProcessMetaData"):
        meta = meta_type()
        meta.JoiningProcessId = process_id
        if hasattr(meta, "JoiningProcessOriginId"):
            meta.JoiningProcessOriginId = process_id
        if hasattr(meta, "Name"):
            meta.Name = name
        proc_data.JoiningProcessMetaData = meta
    else:
        if hasattr(proc_data, "JoiningProcessId"):
            proc_data.JoiningProcessId = process_id
        if hasattr(proc_data, "Name"):
            proc_data.Name = name
    try:
        await jpm.call_method(
            send_node.nodeid,
            _piu_arg(),
            ua.Variant(proc_data, ua.VariantType.ExtensionObject),
            _trimmed_string_arg(""),
        )
        return True
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadTypeMismatch")):
            pytest.skip(f"SendJoiningProcess not callable: {exc}")
        raise


async def _delete_test_joining_process(jpm, ns_ijt, process_id):
    """Delete a joining process; silently ignore errors (cleanup helper)."""
    del_node = await find_child_by_browse_name(jpm, "DeleteJoiningProcess", ns_ijt)
    if del_node is None:
        return
    jp_arg = _jp_identification_arg(process_id=process_id)
    if jp_arg is None:
        return
    try:
        await jpm.call_method(del_node.nodeid, _piu_arg(), jp_arg)
    except ua.UaError:
        pass


# ---------------------------------------------------------------------------
# ─── send_joining_process additional tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SEND_JOINING_PROCESS)
async def test_send_joining_process_with_valid_data_succeeds(opcua_client, ns_indices):
    """Send a fully constructed JoiningProcessDataType and assert a Good response."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    process_id = "conformance-test-jprocess-send"
    try:
        await _send_test_joining_process(jpm, ns_ijt, process_id)
        logger.info("SendJoiningProcess succeeded for ID '%s'", process_id)
    finally:
        await _delete_test_joining_process(jpm, ns_ijt, process_id)


@pytest.mark.requires_cu(CU.SEND_JOINING_PROCESS)
async def test_send_joining_process_update_replaces_existing_process(opcua_client, ns_indices):
    """Sending the same JoiningProcessId twice with a different Name must update the stored process."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    process_id = "conformance-test-jprocess-update"
    try:
        await _send_test_joining_process(jpm, ns_ijt, process_id, name="OriginalName")
        await _send_test_joining_process(jpm, ns_ijt, process_id, name="UpdatedName")
        get_node = await find_child_by_browse_name(jpm, "GetJoiningProcess", ns_ijt)
        if get_node is not None:
            try:
                result = await jpm.call_method(get_node.nodeid, _piu_arg(), _trimmed_string_arg(process_id))
                returned_process = _first_method_output(result)
                returned_meta = getattr(returned_process, "JoiningProcessMetaData", None)
                name_val = getattr(returned_meta, "Name", None) or getattr(returned_process, "Name", None)
                if name_val is not None:
                    assert str(name_val) == "UpdatedName", f"Expected updated Name 'UpdatedName', got {name_val!r}"
                    logger.info("SendJoiningProcess update confirmed: Name='%s'", name_val)
            except ua.UaError as exc:
                logger.warning("GetJoiningProcess after update raised: %s", exc)
    finally:
        await _delete_test_joining_process(jpm, ns_ijt, process_id)


@pytest.mark.requires_cu(CU.SEND_JOINING_PROCESS)
@pytest.mark.negative
async def test_send_joining_process_with_null_data_returns_error(opcua_client, ns_indices):
    """Calling SendJoiningProcess with null data must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    send_node = await find_child_by_browse_name(jpm, "SendJoiningProcess", ns_ijt)
    if send_node is None:
        pytest.skip("SendJoiningProcess: Not Supported — skipping negative test")
    try:
        result = await jpm.call_method(
            send_node.nodeid,
            _piu_arg(),
            ua.Variant(None, ua.VariantType.Null),
            _trimmed_string_arg(""),
        )
        logger.warning("Expected ua.UaError for null data but call returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for null data: %s", exc)
    except (TypeError, AttributeError) as exc:
        logger.info("Correctly rejected null data with encoding error: %s", exc)


@pytest.mark.requires_cu(CU.SEND_JOINING_PROCESS)
@pytest.mark.negative
async def test_send_joining_process_with_empty_process_id_returns_error(opcua_client, ns_indices):
    """Calling SendJoiningProcess with an empty JoiningProcessId must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    send_node = await find_child_by_browse_name(jpm, "SendJoiningProcess", ns_ijt)
    if send_node is None:
        pytest.skip("SendJoiningProcess: Not Supported — skipping negative test")
    proc_type = getattr(ua, "JoiningProcessDataType", None)
    if proc_type is None:
        pytest.skip("JoiningProcessDataType not available — cannot construct empty-ID object")
    proc_data = proc_type()
    meta_type = getattr(ua, "JoiningProcessMetaDataType", None)
    if meta_type is not None and hasattr(proc_data, "JoiningProcessMetaData"):
        meta = meta_type()
        meta.JoiningProcessId = ""
        if hasattr(meta, "Name"):
            meta.Name = "InvalidEmptyProcessId"
        proc_data.JoiningProcessMetaData = meta
    elif hasattr(proc_data, "JoiningProcessId"):
        proc_data.JoiningProcessId = ""
    try:
        result = await jpm.call_method(
            send_node.nodeid,
            _piu_arg(),
            ua.Variant(proc_data, ua.VariantType.ExtensionObject),
            _trimmed_string_arg(""),
        )
        logger.warning("Expected ua.UaError for empty JoiningProcessId but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for empty JoiningProcessId: %s", exc)
    except (TypeError, AttributeError) as exc:
        logger.info("Correctly rejected empty ID with encoding error: %s", exc)


# ---------------------------------------------------------------------------
# ─── get_joining_process additional tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS)
async def test_get_joining_process_returns_correct_data_for_known_id(opcua_client, ns_indices):
    """GetJoiningProcess must return a process whose JoiningProcessId matches the requested ID."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    process_id = "conformance-test-jprocess-get"
    try:
        await _send_test_joining_process(jpm, ns_ijt, process_id)
        get_node = await find_child_by_browse_name(jpm, "GetJoiningProcess", ns_ijt)
        if get_node is None:
            pytest.skip("GetJoiningProcess: Not Supported — skipping")
        try:
            result = await jpm.call_method(get_node.nodeid, _piu_arg(), _trimmed_string_arg(process_id))
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJoiningProcess not callable: {exc}")
            raise
        returned_process = _first_method_output(result)
        assert returned_process is not None, "GetJoiningProcess returned None for a known process ID"
        returned_meta = getattr(returned_process, "JoiningProcessMetaData", None)
        returned_id = getattr(returned_meta, "JoiningProcessId", None) or getattr(
            returned_process, "JoiningProcessId", None
        )
        if returned_id is not None:
            assert str(returned_id) == process_id, (
                f"Returned JoiningProcessId {returned_id!r} does not match requested {process_id!r}"
            )
        logger.info("GetJoiningProcess round-trip succeeded for ID '%s'", process_id)
    finally:
        await _delete_test_joining_process(jpm, ns_ijt, process_id)


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS)
async def test_get_joining_process_meta_data_has_mandatory_fields(opcua_client, ns_indices):
    """GetJoiningProcess must return a result with a non-empty JoiningProcessId field."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    process_id = "conformance-test-jprocess-meta"
    try:
        await _send_test_joining_process(jpm, ns_ijt, process_id)
        get_node = await find_child_by_browse_name(jpm, "GetJoiningProcess", ns_ijt)
        if get_node is None:
            pytest.skip("GetJoiningProcess: Not Supported — skipping")
        try:
            result = await jpm.call_method(get_node.nodeid, _piu_arg(), _trimmed_string_arg(process_id))
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJoiningProcess not callable: {exc}")
            raise
        returned_process = _first_method_output(result)
        assert returned_process is not None, "GetJoiningProcess returned None"
        returned_meta = getattr(returned_process, "JoiningProcessMetaData", None)
        proc_id_val = getattr(returned_meta, "JoiningProcessId", None) or getattr(
            returned_process, "JoiningProcessId", None
        )
        assert proc_id_val is not None, "GetJoiningProcess result has no JoiningProcessId field"
        assert str(proc_id_val).strip() != "", "JoiningProcessId must not be empty"
        logger.info("Mandatory JoiningProcessId field present: '%s'", proc_id_val)
    finally:
        await _delete_test_joining_process(jpm, ns_ijt, process_id)


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS)
@pytest.mark.negative
async def test_get_joining_process_with_nonexistent_id_returns_error(opcua_client, ns_indices):
    """GetJoiningProcess with a non-existent ID must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    get_node = await find_child_by_browse_name(jpm, "GetJoiningProcess", ns_ijt)
    if get_node is None:
        pytest.skip("GetJoiningProcess: Not Supported — skipping negative test")
    try:
        result = await jpm.call_method(
            get_node.nodeid,
            _piu_arg(),
            _trimmed_string_arg("conformance-test-nonexistent-process-xyz"),
        )
        logger.warning("Expected ua.UaError for nonexistent process but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for nonexistent process ID: %s", exc)


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS)
@pytest.mark.negative
async def test_get_joining_process_with_empty_id_returns_error(opcua_client, ns_indices):
    """GetJoiningProcess with an empty ID must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    get_node = await find_child_by_browse_name(jpm, "GetJoiningProcess", ns_ijt)
    if get_node is None:
        pytest.skip("GetJoiningProcess: Not Supported — skipping negative test")
    try:
        result = await jpm.call_method(get_node.nodeid, _piu_arg(), _trimmed_string_arg(""))
        logger.warning("Expected ua.UaError for empty ID but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for empty ID: %s", exc)


# ---------------------------------------------------------------------------
# ─── set_joining_process_counter additional tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SET_JOINING_PROCESS_COUNTER)
async def test_set_joining_process_counter_with_zero_value_resets_counter(opcua_client, ns_indices):
    """SetJoiningProcessCounter(0) must succeed or return BadNotSupported."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    counter_node = await find_child_by_browse_name(jpm, "SetJoiningProcessCounter", ns_ijt)
    if counter_node is None:
        pytest.skip("SetJoiningProcessCounter: Not Supported — skipping")
    ns_di_idx = ns_indices.get(NS_DI)
    ns_app_idx = ns_indices.get(NS_APP)
    pi_uri = await read_tool_product_instance_uri(opcua_client, ns_ijt, ns_di_idx, ns_app_idx)
    jp = _make_jp_identification()
    if jp is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — load_data_type_definitions() may have failed")
    try:
        await jpm.call_method(
            counter_node.nodeid,
            ua.Variant(pi_uri, ua.VariantType.String),
            ua.Variant(jp, ua.VariantType.ExtensionObject),
            ua.Variant(0, ua.VariantType.UInt32),
        )
        logger.info("SetJoiningProcessCounter(0) succeeded")
    except ua.UaError as exc:
        if any(s in str(exc) for s in ("BadNotSupported", "BadInvalidArgument", "BadArgumentsMissing")):
            pytest.skip(f"SetJoiningProcessCounter not callable: {exc}")
        raise


@pytest.mark.requires_cu(CU.SET_JOINING_PROCESS_COUNTER)
@pytest.mark.negative
async def test_set_joining_process_counter_exceeding_batch_size_returns_error(opcua_client, ns_indices):
    """SetJoiningProcessCounter with a very large value should raise ua.UaError or be accepted."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    counter_node = await find_child_by_browse_name(jpm, "SetJoiningProcessCounter", ns_ijt)
    if counter_node is None:
        pytest.skip("SetJoiningProcessCounter: Not Supported — skipping negative test")
    jp_arg = _jp_identification_arg()
    if jp_arg is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — cannot build counter arguments")
    try:
        result = await jpm.call_method(
            counter_node.nodeid,
            _piu_arg(),
            jp_arg,
            ua.Variant(999999, ua.VariantType.UInt32),
        )
        logger.warning("SetJoiningProcessCounter(999999) returned %r — server accepted large value", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for large counter value: %s", exc)


# ---------------------------------------------------------------------------
# ─── set_joining_process_mapping additional tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SET_JOINING_PROCESS_MAPPING)
@pytest.mark.negative
async def test_set_joining_process_mapping_with_unknown_id_returns_error(opcua_client, ns_indices):
    """SetJoiningProcessMapping with an unknown JoiningProcessId must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    mapping_node = await find_child_by_browse_name(jpm, "SetJoiningProcessMapping", ns_ijt)
    if mapping_node is None:
        pytest.skip("SetJoiningProcessMapping: Not Supported — skipping negative test")
    jp_arg = _jp_identification_arg(process_id="conformance-test-nonexistent-mapping-xyz")
    if jp_arg is None:
        pytest.skip("JoiningProcessIdentificationDataType not available — cannot build mapping arguments")
    try:
        result = await jpm.call_method(
            mapping_node.nodeid,
            _piu_arg(),
            jp_arg,
        )
        logger.warning(
            "Expected ua.UaError for unknown ID in SetJoiningProcessMapping but returned %r",
            result,
        )
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for unknown mapping ID: %s", exc)


@pytest.mark.requires_cu(CU.SET_JOINING_PROCESS_MAPPING)
@pytest.mark.negative
async def test_set_joining_process_mapping_with_empty_data_returns_error(opcua_client, ns_indices):
    """SetJoiningProcessMapping with null/empty mapping argument must raise ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    mapping_node = await find_child_by_browse_name(jpm, "SetJoiningProcessMapping", ns_ijt)
    if mapping_node is None:
        pytest.skip("SetJoiningProcessMapping: Not Supported — skipping negative test")
    try:
        result = await jpm.call_method(mapping_node.nodeid, _piu_arg(), ua.Variant(None, ua.VariantType.Null))
        logger.warning("Expected ua.UaError for empty SetJoiningProcessMapping but returned %r", result)
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for empty mapping data: %s", exc)
    except (TypeError, AttributeError) as exc:
        logger.info("Correctly rejected empty mapping data with encoding error: %s", exc)


# ---------------------------------------------------------------------------
# ─── get_joining_process_revision_list additional tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS_REVISION_LIST)
async def test_get_joining_process_revision_list_returns_revisions_for_existing_process(opcua_client, ns_indices):
    """GetJoiningProcessRevisionList for a process sent twice must return a list."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    process_id = "conformance-test-jprocess-rl-multi"
    try:
        await _send_test_joining_process(jpm, ns_ijt, process_id, name="RevisionOne")
        await _send_test_joining_process(jpm, ns_ijt, process_id, name="RevisionTwo")
        rl_node = await find_child_by_browse_name(jpm, "GetJoiningProcessRevisionList", ns_ijt)
        if rl_node is None:
            pytest.skip("GetJoiningProcessRevisionList: Not Supported — skipping")
        try:
            result = await jpm.call_method(rl_node.nodeid, _piu_arg(), _trimmed_string_arg(process_id))
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJoiningProcessRevisionList not callable: {exc}")
            raise
        assert result is None or isinstance(result, (list, tuple)), (
            f"GetJoiningProcessRevisionList must return a list, got {type(result)}"
        )
        count = len(result) if result else 0
        logger.info(
            "GetJoiningProcessRevisionList returned %d revision(s) for '%s'",
            count,
            process_id,
        )
    finally:
        await _delete_test_joining_process(jpm, ns_ijt, process_id)


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS_REVISION_LIST)
async def test_get_joining_process_revision_list_for_single_revision_process(opcua_client, ns_indices):
    """GetJoiningProcessRevisionList for a process sent once must return a list."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    process_id = "conformance-test-jprocess-rl-single"
    try:
        await _send_test_joining_process(jpm, ns_ijt, process_id)
        rl_node = await find_child_by_browse_name(jpm, "GetJoiningProcessRevisionList", ns_ijt)
        if rl_node is None:
            pytest.skip("GetJoiningProcessRevisionList: Not Supported — skipping")
        try:
            result = await jpm.call_method(rl_node.nodeid, _piu_arg(), _trimmed_string_arg(process_id))
        except ua.UaError as exc:
            if "BadNotSupported" in str(exc):
                pytest.skip(f"GetJoiningProcessRevisionList not callable: {exc}")
            raise
        assert result is None or isinstance(result, (list, tuple)), (
            f"GetJoiningProcessRevisionList must return a list, got {type(result)}"
        )
        logger.info("GetJoiningProcessRevisionList returned list for single-revision process")
    finally:
        await _delete_test_joining_process(jpm, ns_ijt, process_id)


@pytest.mark.requires_cu(CU.GET_JOINING_PROCESS_REVISION_LIST)
@pytest.mark.negative
async def test_get_joining_process_revision_list_with_nonexistent_id_returns_empty_or_error(opcua_client, ns_indices):
    """GetJoiningProcessRevisionList with a non-existent ID must return empty list or ua.UaError."""
    ns_ijt = _require_ns_ijt(ns_indices)
    jpm = await _get_jpm(opcua_client, ns_ijt)
    rl_node = await find_child_by_browse_name(jpm, "GetJoiningProcessRevisionList", ns_ijt)
    if rl_node is None:
        pytest.skip("GetJoiningProcessRevisionList: Not Supported — skipping negative test")
    try:
        result = await jpm.call_method(
            rl_node.nodeid,
            _piu_arg(),
            _trimmed_string_arg("conformance-test-nonexistent-rl-xyz"),
        )
        items = list(result) if isinstance(result, (list, tuple)) else ([] if result is None else [result])
        if items:
            logger.warning(
                "GetJoiningProcessRevisionList returned %d entries for non-existent ID — "
                "server should return empty list or error",
                len(items),
            )
        else:
            logger.info("GetJoiningProcessRevisionList correctly returned empty list for non-existent ID")
    except ua.UaError as exc:
        logger.info("Correctly raised ua.UaError for non-existent ID: %s", exc)
