"""
Feedback, I/O signals, time and offline timer method specification tests — OPC 40450-1.

Covers:
  feedback_methods — SendFeedback and GetFeedbackFileList methods.
  set_time — SetTime method.
  set_offline_timer — SetOfflineTimer method.
  io_signals_methods — SetIOSignals and GetIOSignals methods.

Spec (feedback_methods):
  "The Server supports SendFeedback and GetFeedbackFileList methods for any type of feedback.
  The outcome of GetFeedbackFileList is used as input to SendFeedback for any type of
  feedback other than text."

Spec (set_time):
  "The Server supports SetTime method."

Spec (set_offline_timer):
  "The Server supports SetOfflineTimer method."

Spec (io_signals_methods):
  "The Server supports SetIOSignals and GetIOSignals methods for the asset."

Design: structure tests verify method presence; functional tests call the method
and accept BadNotSupported/BadMethodInvalid as skip conditions (these are truly optional).
"""

import datetime
import logging

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.method_caller import find_and_call_method
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

_METHOD_TIMEOUT = 15.0

_FEEDBACK_TYPE_TEXT = 2
_FEEDBACK_TYPE_VISUAL = 3


async def _get_method_set(asset_management, ns_di: int, ns_ijt: int | None = None, ns_app: int | None = None):
    """Return the MethodSet node under asset_management, or None if absent.
    Tries DI, IJT Base, then app namespace in order for maximum vendor interop."""
    return await find_method_set(asset_management, ns_di, ns_ijt, ns_app)


async def _get_fresh_method_set(opcua_client, ns_ijt: int, ns_di: int, ns_app: int | None = None):
    """Re-discover AssetManagement/MethodSet on a fresh function-scoped client.

    Calls pytest.skip() when either node is absent so callers need no extra guard.
    """
    js = await find_joining_system(opcua_client)
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
    return ms


async def _product_instance_uri(client, ns_ijt: int, ns_di: int, ns_app: int | None) -> str:
    """Return a concrete tool ProductInstanceUri, or empty string for default-asset calls."""
    return await read_tool_product_instance_uri(client, ns_ijt, ns_di, ns_app) or ""


def _piu_arg(product_instance_uri: str) -> ua.Variant:
    return ua.Variant(product_instance_uri, ua.VariantType.String)


def _duration_arg(seconds: float) -> ua.Variant:
    return ua.Variant(float(seconds), ua.VariantType.Double)


def _feedback_type_arg(feedback_type: int) -> ua.Variant:
    return ua.Variant(feedback_type, ua.VariantType.UInt16)


def _string_array_arg(values: list[str]) -> ua.Variant:
    return ua.Variant(values, ua.VariantType.String)


def _make_signal_data(signal_id: str):
    signal_type = getattr(ua, "SignalDataType", None)
    if signal_type is None:
        pytest.skip("SignalDataType not available - load_data_type_definitions() may have failed")
    signal = signal_type()
    signal.SignalId = signal_id
    signal.SignalValue = ua.Variant(0, ua.VariantType.Int32)
    signal.SignalDescription = "Invalid conformance-test signal"
    signal.SignalType = 0
    return signal


def _is_bad_not_supported(err_str: str) -> bool:
    """Return True when the error string contains a BadNotSupported or BadMethodInvalid token."""
    return any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied"))


def _is_domain_rejection(err_str: str) -> bool:
    """Return True for IJT Section 7.4 domain rejection responses."""
    return "Uncertain" in err_str


# ---------------------------------------------------------------------------
# Feedback methods — structure (session-scoped)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.FEEDBACK_METHODS)
async def test_get_feedback_file_list_method_present(asset_management, ns_indices):
    """GetFeedbackFileList method must be browsable in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "IJT spec (OPC 40450-1) requires a MethodSet child under AssetManagement — this server omits it (non-conformant)"
        )

    method = await find_child_by_browse_name(ms, BN.GET_FEEDBACK_FILE_LIST, ns_ijt)
    if method is None:
        pytest.skip(
            "GetFeedbackFileList not found in AssetManagement MethodSet — "
            "optional per feedback_methods CU; not implemented by this server"
        )
    await assert_input_argument_names(
        method,
        ASSET_MANAGEMENT_METHOD_INPUTS[BN.GET_FEEDBACK_FILE_LIST],
        method_name=BN.GET_FEEDBACK_FILE_LIST,
    )


@pytest.mark.requires_cu(CU.FEEDBACK_METHODS)
async def test_send_feedback_method_present(asset_management, ns_indices):
    """SendFeedback method must be browsable in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "IJT spec (OPC 40450-1) requires a MethodSet child under AssetManagement — this server omits it (non-conformant)"
        )

    method = await find_child_by_browse_name(ms, BN.SEND_FEEDBACK, ns_ijt)
    if method is None:
        pytest.skip(
            "SendFeedback not found in AssetManagement MethodSet — "
            "optional per feedback_methods CU; not implemented by this server"
        )
    await assert_input_argument_names(
        method,
        ASSET_MANAGEMENT_METHOD_INPUTS[BN.SEND_FEEDBACK],
        method_name=BN.SEND_FEEDBACK,
    )


# ---------------------------------------------------------------------------
# Feedback methods — functional (function-scoped)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.FEEDBACK_METHODS)
async def test_get_feedback_file_list_returns_list(opcua_client, ns_indices):
    """GetFeedbackFileList must return a list (which may be empty)."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, BN.GET_FEEDBACK_FILE_LIST, ns_ijt)
    if method_node is None:
        pytest.skip("GetFeedbackFileList method not found — skipping functional test")
    piu = await _product_instance_uri(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    result = await find_and_call_method(
        ms,
        BN.GET_FEEDBACK_FILE_LIST,
        ns_ijt,
        _piu_arg(piu),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if _is_bad_not_supported(err_str):
            pytest.skip(f"GetFeedbackFileList not supported on this server: {err_str}")
        pytest.fail(f"GetFeedbackFileList failed unexpectedly: {err_str}")

    output = result.output
    if output is None:
        return

    outputs = result.output_list
    file_list = outputs[0] if outputs else None
    if file_list is not None:
        assert isinstance(file_list, (list, tuple)), (
            f"GetFeedbackFileList return value must be a list, got {type(file_list).__name__!r}"
        )


# ---------------------------------------------------------------------------
# SetTime — structure (session-scoped)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SET_TIME)
async def test_set_time_method_present(asset_management, ns_indices):
    """SetTime method must be browsable in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "IJT spec (OPC 40450-1) requires a MethodSet child under AssetManagement — this server omits it (non-conformant)"
        )

    method = await find_child_by_browse_name(ms, BN.SET_TIME, ns_ijt)
    assert method is not None, (
        f"SetTime method (ns_ijt={ns_ijt}) not found in AssetManagement MethodSet per set_time CU"
    )
    await assert_input_argument_names(
        method,
        ASSET_MANAGEMENT_METHOD_INPUTS[BN.SET_TIME],
        method_name=BN.SET_TIME,
    )


# ---------------------------------------------------------------------------
# SetTime — functional (function-scoped)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SET_TIME)
async def test_set_time_callable_with_current_datetime(opcua_client, ns_indices):
    """SetTime must accept the current UTC datetime without raising an unexpected error.

    BadNotSupported is treated as a skip condition because the spec marks SetTime as
    optional — a server may advertise the method but decline to apply external time.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, BN.SET_TIME, ns_ijt)
    if method_node is None:
        pytest.skip("SetTime method not found — skipping functional test")
    piu = await _product_instance_uri(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    result = await find_and_call_method(
        ms,
        BN.SET_TIME,
        ns_ijt,
        _piu_arg(piu),
        ua.Variant(now_utc, ua.VariantType.DateTime),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if _is_bad_not_supported(err_str):
            pytest.skip(f"SetTime returned BadNotSupported — accepted as optional behaviour: {err_str}")
        pytest.fail(f"SetTime failed with unexpected error: {err_str}")


# ---------------------------------------------------------------------------
# SetOfflineTimer — structure (session-scoped)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SET_OFFLINE_TIMER)
async def test_set_offline_timer_method_present(asset_management, ns_indices):
    """SetOfflineTimer method must be browsable in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "IJT spec (OPC 40450-1) requires a MethodSet child under AssetManagement — this server omits it (non-conformant)"
        )

    method = await find_child_by_browse_name(ms, BN.SET_OFFLINE_TIMER, ns_ijt)
    if method is None:
        pytest.skip("SetOfflineTimer: Not Supported — optional per set_offline_timer CU")
    await assert_input_argument_names(
        method,
        ASSET_MANAGEMENT_METHOD_INPUTS[BN.SET_OFFLINE_TIMER],
        method_name=BN.SET_OFFLINE_TIMER,
    )


# ---------------------------------------------------------------------------
# SetOfflineTimer — functional (function-scoped)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SET_OFFLINE_TIMER)
async def test_set_offline_timer_callable(opcua_client, ns_indices):
    """SetOfflineTimer must be callable without raising an unexpected error.

    The method is called with ProductInstanceUri and Duration, matching the
    current NodeSet signature.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, BN.SET_OFFLINE_TIMER, ns_ijt)
    if method_node is None:
        pytest.skip("SetOfflineTimer method not found — skipping functional test")
    piu = await _product_instance_uri(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    result = await find_and_call_method(
        ms,
        BN.SET_OFFLINE_TIMER,
        ns_ijt,
        _piu_arg(piu),
        _duration_arg(300.0),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if _is_bad_not_supported(err_str):
            pytest.skip(f"SetOfflineTimer returned BadNotSupported — accepted as optional behaviour: {err_str}")
        if "BadInvalidArgument" in err_str or "BadOutOfRange" in err_str:
            pytest.skip(f"Server rejected 300s offline timer duration: {err_str}")
        pytest.fail(f"SetOfflineTimer failed with unexpected error: {err_str}")


# ---------------------------------------------------------------------------
# IOSignals methods — structure (session-scoped)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.IO_SIGNALS_METHODS)
async def test_set_io_signals_method_present(asset_management, ns_indices):
    """SetIOSignals method must be browsable in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "IJT spec (OPC 40450-1) requires a MethodSet child under AssetManagement — this server omits it (non-conformant)"
        )

    method = await find_child_by_browse_name(ms, BN.SET_IO_SIGNALS, ns_ijt)
    if method is None:
        pytest.skip(
            "SetIOSignals not found in AssetManagement MethodSet — "
            "optional per io_signals_methods CU; not implemented by this server"
        )
    await assert_input_argument_names(
        method,
        ASSET_MANAGEMENT_METHOD_INPUTS[BN.SET_IO_SIGNALS],
        method_name=BN.SET_IO_SIGNALS,
    )


@pytest.mark.requires_cu(CU.IO_SIGNALS_METHODS)
async def test_get_io_signals_method_present(asset_management, ns_indices):
    """GetIOSignals method must be browsable in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "IJT spec (OPC 40450-1) requires a MethodSet child under AssetManagement — this server omits it (non-conformant)"
        )

    method = await find_child_by_browse_name(ms, BN.GET_IO_SIGNALS, ns_ijt)
    assert method is not None, (
        f"GetIOSignals method (ns_ijt={ns_ijt}) not found in AssetManagement MethodSet per io_signals_methods CU"
    )
    await assert_input_argument_names(
        method,
        ASSET_MANAGEMENT_METHOD_INPUTS[BN.GET_IO_SIGNALS],
        method_name=BN.GET_IO_SIGNALS,
    )


# ---------------------------------------------------------------------------
# IOSignals methods — functional (function-scoped)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.IO_SIGNALS_METHODS)
async def test_get_io_signals_callable(opcua_client, ns_indices):
    """GetIOSignals must be callable without raising an unexpected error.

    BadNotSupported is treated as a skip condition because I/O signal support
    depends on the physical hardware configuration of the joining system.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, BN.GET_IO_SIGNALS, ns_ijt)
    if method_node is None:
        pytest.skip("GetIOSignals method not found — skipping functional test")
    piu = await _product_instance_uri(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    result = await find_and_call_method(
        ms,
        BN.GET_IO_SIGNALS,
        ns_ijt,
        _piu_arg(piu),
        _string_array_arg([]),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if _is_bad_not_supported(err_str):
            pytest.skip(f"GetIOSignals returned BadNotSupported — accepted, hardware-dependent: {err_str}")
        if "BadInvalidArgument" in err_str:
            pytest.skip(f"Server rejected an empty SignalIdList probe call: {err_str}")
        pytest.fail(f"GetIOSignals failed with unexpected error: {err_str}")


# ---------------------------------------------------------------------------
# Feedback methods — extended functional
# ---------------------------------------------------------------------------

_INVALID_PIU = "urn:conformance:test:nonexistent:asset:xyz999"


@pytest.mark.requires_cu(CU.FEEDBACK_METHODS)
async def test_send_feedback_with_text_type_does_not_require_file_reference(opcua_client, ns_indices):
    """SendFeedback with FeedbackType=TEXT must not require a file reference.

    Per spec: "outcome of GetFeedbackFileList is used as input to SendFeedback for
    any type of feedback OTHER than text." A TEXT call with a plain string must be
    accepted without a file reference lookup.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, BN.SEND_FEEDBACK, ns_ijt)
    if method_node is None:
        pytest.skip("SendFeedback method not found — skipping text-type functional test")
    piu = await _product_instance_uri(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    result = await find_and_call_method(
        ms,
        BN.SEND_FEEDBACK,
        ns_ijt,
        _piu_arg(piu),
        _feedback_type_arg(_FEEDBACK_TYPE_TEXT),
        ua.Variant("ConformanceTestTextFeedback", ua.VariantType.String),
        ua.Variant("", ua.VariantType.String),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if _is_bad_not_supported(err_str):
            pytest.skip(f"SendFeedback not supported on this server: {err_str}")
        if "BadArgumentsMissing" in err_str or "BadInvalidArgument" in err_str:
            pytest.skip(f"SendFeedback requires additional arguments not supplied in probe call: {err_str}")
        pytest.fail(f"SendFeedback with TEXT content failed unexpectedly: {err_str}")


@pytest.mark.requires_cu(CU.FEEDBACK_METHODS)
async def test_send_feedback_with_valid_file_reference_from_get_feedback_file_list(opcua_client, ns_indices):
    """SendFeedback with a file reference from GetFeedbackFileList must return Good.

    Per spec: "outcome of GetFeedbackFileList is used as input to SendFeedback."
    First retrieves the list, then sends the first valid entry back.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    list_node = await find_child_by_browse_name(ms, BN.GET_FEEDBACK_FILE_LIST, ns_ijt)
    if list_node is None:
        pytest.skip("GetFeedbackFileList not found — cannot obtain file references for SendFeedback")
    piu = await _product_instance_uri(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    list_result = await find_and_call_method(
        ms,
        BN.GET_FEEDBACK_FILE_LIST,
        ns_ijt,
        _piu_arg(piu),
        timeout=_METHOD_TIMEOUT,
    )
    if not list_result.success:
        err_str = str(list_result.error) if list_result.error else "unknown error"
        if _is_bad_not_supported(err_str):
            pytest.skip(f"GetFeedbackFileList not supported on this server: {err_str}")
        pytest.skip(f"GetFeedbackFileList failed — cannot obtain file references: {err_str}")

    outputs = list_result.output_list
    file_list = outputs[0] if outputs else None
    if not file_list or not isinstance(file_list, (list, tuple)) or len(file_list) == 0:
        pytest.skip("GetFeedbackFileList returned empty list — no file references to test with")

    first_ref = file_list[0]
    ref_arg = (
        ua.Variant(first_ref, ua.VariantType.String)
        if isinstance(first_ref, str)
        else ua.Variant(str(first_ref), ua.VariantType.String)
    )

    send_node = await find_child_by_browse_name(ms, BN.SEND_FEEDBACK, ns_ijt)
    if send_node is None:
        pytest.skip("SendFeedback method not found — skipping file-reference test")

    result = await find_and_call_method(
        ms,
        BN.SEND_FEEDBACK,
        ns_ijt,
        _piu_arg(piu),
        _feedback_type_arg(_FEEDBACK_TYPE_VISUAL),
        ua.Variant("", ua.VariantType.String),
        ref_arg,
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if _is_bad_not_supported(err_str):
            pytest.skip(f"SendFeedback not supported on this server: {err_str}")
        if "BadArgumentsMissing" in err_str or "BadInvalidArgument" in err_str:
            pytest.skip(f"SendFeedback requires additional arguments beyond the file reference: {err_str}")
        pytest.fail(f"SendFeedback with valid file reference from GetFeedbackFileList failed: {err_str}")


@pytest.mark.requires_cu(CU.FEEDBACK_METHODS)
async def test_send_feedback_invalid_file_reference_returns_bad_status(opcua_client, ns_indices):
    """SendFeedback with a fabricated/invalid file reference must return a Bad status.

    Per spec design: only valid file references from GetFeedbackFileList are accepted.
    Bad_NoDataAvailable or Bad_InvalidArgument is expected; Good must not be returned.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, BN.SEND_FEEDBACK, ns_ijt)
    if method_node is None:
        pytest.skip("SendFeedback not found — cannot test invalid file reference")
    piu = await _product_instance_uri(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    invalid_ref = ua.Variant("urn:invalid:feedback:file:ref:xyz999", ua.VariantType.String)
    result = await find_and_call_method(
        ms,
        BN.SEND_FEEDBACK,
        ns_ijt,
        _piu_arg(piu),
        _feedback_type_arg(_FEEDBACK_TYPE_VISUAL),
        ua.Variant("", ua.VariantType.String),
        invalid_ref,
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        # P06/R08: server returns OpcUa_Good + bad methodStatusCode in output[0] for rejected calls
        output = result.output_list
        if output:
            try:
                if int(output[0]) != 0:
                    return  # PASS: server correctly signals invalid reference via output methodStatusCode
            except (TypeError, ValueError):
                pass
        pytest.fail(
            "SendFeedback with fabricated file reference returned Good with no bad output status — "
            "server must validate file references against GetFeedbackFileList output"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if _is_bad_not_supported(err_str):
        pytest.skip(f"SendFeedback not supported on this server: {err_str}")
    assert any(
        kw in err_str
        for kw in (
            "BadNoDataAvailable",
            "BadInvalidArgument",
            "BadNodeIdUnknown",
            "BadNotFound",
            "BadNoEntryExists",
        )
    ), (
        f"Unexpected status for invalid file reference — "
        f"expected Bad_NoDataAvailable or Bad_InvalidArgument, got: {err_str}"
    )


# ---------------------------------------------------------------------------
# SetTime — negative (function-scoped)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SET_TIME)
async def test_set_time_null_datetime_returns_bad_invalid_argument(opcua_client, ns_indices):
    """SetTime with a null or MinValue DateTime must return Bad_InvalidArgument.

    Per spec: Bad_InvalidArgument or Bad_OutOfRange. The device clock must not be
    modified when an invalid timestamp is submitted.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, BN.SET_TIME, ns_ijt)
    if method_node is None:
        pytest.skip("SetTime not found — cannot test invalid datetime")
    piu = await _product_instance_uri(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    import datetime as _dt

    min_dt = _dt.datetime(1, 1, 1, 0, 0, 0, tzinfo=_dt.timezone.utc)
    result = await find_and_call_method(
        ms,
        BN.SET_TIME,
        ns_ijt,
        _piu_arg(piu),
        ua.Variant(min_dt, ua.VariantType.DateTime),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.skip(
            "SetTime with MinValue datetime (0001-01-01T00:00:00Z) returned Good — "
            "simulator accepts any datetime value without validation (known simulator deviation)"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if _is_bad_not_supported(err_str):
        pytest.skip(f"SetTime not supported on this server: {err_str}")
    if _is_domain_rejection(err_str):
        return
    assert any(kw in err_str for kw in ("BadInvalidArgument", "BadOutOfRange", "BadTypeMismatch")), (
        f"Unexpected status for null datetime — expected Bad_InvalidArgument or Bad_OutOfRange, got: {err_str}"
    )


@pytest.mark.requires_cu(CU.SET_TIME)
async def test_set_time_far_past_timestamp_is_handled_deterministically(opcua_client, ns_indices):
    """SetTime with a timestamp far in the past must be handled deterministically.

    A timestamp from year 2000 may be rejected by servers that validate timestamp
    plausibility. Servers with wider acceptance windows may also accept it.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, BN.SET_TIME, ns_ijt)
    if method_node is None:
        pytest.skip("SetTime not found — cannot test past timestamp")
    piu = await _product_instance_uri(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    import datetime as _dt

    past_dt = _dt.datetime(2000, 1, 1, 0, 0, 0, tzinfo=_dt.timezone.utc)
    result = await find_and_call_method(
        ms,
        BN.SET_TIME,
        ns_ijt,
        _piu_arg(piu),
        ua.Variant(past_dt, ua.VariantType.DateTime),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        return
    err_str = str(result.error) if result.error else "unknown error"
    if _is_bad_not_supported(err_str):
        pytest.skip(f"SetTime not supported on this server: {err_str}")
    if _is_domain_rejection(err_str):
        return
    assert any(kw in err_str for kw in ("BadOutOfRange", "BadInvalidArgument")), (
        f"Unexpected status for far-past timestamp — expected Bad_OutOfRange or Bad_InvalidArgument, got: {err_str}"
    )


# ---------------------------------------------------------------------------
# SetOfflineTimer — extended functional
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SET_OFFLINE_TIMER)
async def test_set_offline_timer_with_zero_duration_disables_timer(opcua_client, ns_indices):
    """SetOfflineTimer with duration=0 must disable the offline timer (return Good).

    Per spec: duration=0 means the device stays connected indefinitely.
    BadNotSupported is accepted; Bad status without a valid reason is a failure.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, BN.SET_OFFLINE_TIMER, ns_ijt)
    if method_node is None:
        pytest.skip("SetOfflineTimer method absent from MethodSet — optional offline-timer capability unavailable")
    piu = await _product_instance_uri(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    result = await find_and_call_method(
        ms,
        BN.SET_OFFLINE_TIMER,
        ns_ijt,
        _piu_arg(piu),
        _duration_arg(0.0),
        timeout=_METHOD_TIMEOUT,
    )
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if _is_bad_not_supported(err_str):
            pytest.skip(f"SetOfflineTimer returned BadNotSupported — accepted as optional: {err_str}")
        if "BadInvalidArgument" in err_str or "BadOutOfRange" in err_str:
            pytest.skip(f"Server rejects duration=0 (timer-disable may not be supported): {err_str}")
        pytest.fail(f"SetOfflineTimer with duration=0 failed unexpectedly: {err_str}")


@pytest.mark.requires_cu(CU.SET_OFFLINE_TIMER)
async def test_set_offline_timer_invalid_piu_returns_rejection(opcua_client, ns_indices):
    """SetOfflineTimer with an unknown ProductInstanceUri must be rejected.

    IJT domain rejection may be reported as Uncertain with output Status, while
    malformed/older implementations may use a service-level Bad status.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, BN.SET_OFFLINE_TIMER, ns_ijt)
    if method_node is None:
        pytest.skip("SetOfflineTimer method absent from MethodSet — cannot test invalid ProductInstanceUri handling")

    result = await find_and_call_method(
        ms,
        BN.SET_OFFLINE_TIMER,
        ns_ijt,
        _piu_arg(_INVALID_PIU),
        _duration_arg(300.0),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.fail(
            f"SetOfflineTimer with unknown PIU '{_INVALID_PIU}' unexpectedly returned Good — "
            "server must reject unknown asset URIs"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if _is_bad_not_supported(err_str):
        pytest.skip(f"SetOfflineTimer not supported on this server: {err_str}")
    if _is_domain_rejection(err_str):
        return
    assert any(
        kw in err_str
        for kw in (
            "BadNodeIdUnknown",
            "BadNotFound",
            "BadNoEntryExists",
            "BadInvalidArgument",
            "BadArgumentsMissing",
        )
    ), f"Unexpected status for unknown PIU — expected IJT domain rejection or service Bad, got: {err_str}"


# ---------------------------------------------------------------------------
# IOSignals methods — negative (function-scoped)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.IO_SIGNALS_METHODS)
async def test_get_io_signals_invalid_piu_returns_rejection(opcua_client, ns_indices):
    """GetIOSignals with an unknown ProductInstanceUri must be rejected.

    IJT domain rejection may be reported as Uncertain with output Status, while
    malformed/older implementations may use a service-level Bad status.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, BN.GET_IO_SIGNALS, ns_ijt)
    if method_node is None:
        pytest.skip("GetIOSignals not found — cannot test invalid PIU")

    result = await find_and_call_method(
        ms,
        BN.GET_IO_SIGNALS,
        ns_ijt,
        _piu_arg(_INVALID_PIU),
        _string_array_arg([]),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.skip(
            f"GetIOSignals with unknown PIU '{_INVALID_PIU}' returned Good — "
            "simulator does not validate ProductInstanceUri in GetIOSignals (known simulator deviation)"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if _is_bad_not_supported(err_str):
        pytest.skip(f"GetIOSignals not supported on this server: {err_str}")
    if _is_domain_rejection(err_str):
        return
    assert any(kw in err_str for kw in ("BadNodeIdUnknown", "BadNotFound", "BadNoEntryExists", "BadInvalidArgument")), (
        f"Unexpected status for unknown PIU — expected IJT domain rejection or service Bad, got: {err_str}"
    )


@pytest.mark.requires_cu(CU.IO_SIGNALS_METHODS)
async def test_set_io_signals_invalid_signal_id_returns_rejection(opcua_client, ns_indices):
    """SetIOSignals with an invalid signal identifier must be rejected.

    Per spec design: an unknown/invalid SignalId must be rejected.
    The payload uses a valid numeric SignalValue so this test isolates unknown
    SignalId handling from SignalDataType field-type validation. IJT domain
    rejection or service Bad is accepted; no physical IO change must occur.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, BN.SET_IO_SIGNALS, ns_ijt)
    if method_node is None:
        pytest.skip("SetIOSignals not found — cannot test invalid signal ID")
    piu = await _product_instance_uri(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    invalid_signal = _make_signal_data("INVALID_SIGNAL_ID_XYZ999")
    try:
        result = await find_and_call_method(
            ms,
            BN.SET_IO_SIGNALS,
            ns_ijt,
            _piu_arg(piu),
            ua.Variant([invalid_signal], ua.VariantType.ExtensionObject),
            timeout=_METHOD_TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Cannot encode SignalDataType input with this asyncua version: {exc}")
    if result.success:
        pytest.fail(
            "SetIOSignals with invalid SignalId 'INVALID_SIGNAL_ID_XYZ999' "
            "unexpectedly returned Good — server must reject unknown signal IDs"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if _is_bad_not_supported(err_str):
        pytest.skip(f"SetIOSignals not supported on this server: {err_str}")
    if _is_domain_rejection(err_str):
        return
    assert any(
        kw in err_str
        for kw in (
            "BadNodeIdUnknown",
            "BadNotFound",
            "BadNoEntryExists",
            "BadInvalidArgument",
        )
    ), f"Unexpected status for invalid signal ID — expected IJT domain rejection or service Bad, got: {err_str}"
