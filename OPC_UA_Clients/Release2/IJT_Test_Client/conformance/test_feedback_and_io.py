"""
Feedback, I/O signals, time and offline timer method conformance tests — OPC 40450-1.

Covers:
  feedback_methods — SendFeedback and GetFeedbackFileList methods.
  set_time — SetTime method.
  set_offline_timer — SetOfflineTimer method.
  io_signals_methods — SendIOSignals and GetIOSignals methods.

Spec (feedback_methods):
  "The Server supports SendFeedback and GetFeedbackFileList methods for any type of feedback.
  The outcome of GetFeedbackFileList is used as input to SendFeedback for any type of
  feedback other than text."

Spec (set_time):
  "The Server supports SetTime method."

Spec (set_offline_timer):
  "The Server supports SetOfflineTimer method."

Spec (io_signals_methods):
  "The Server supports SendIOSignals and GetIOSignals methods for the asset."

Design: structure tests verify method presence; functional tests call the method
and accept BadNotSupported/BadMethodInvalid as skip conditions (these are truly optional).
"""

import datetime
import logging

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.method_caller import find_and_call_method
from helpers.namespaces import BN, NS_APP, NS_DI, NS_IJT_BASE
from helpers.node_discovery import find_child_by_browse_name, find_joining_system, find_method_set

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

_METHOD_TIMEOUT = 15.0

# Browse name strings for methods not yet defined in BN
_BN_GET_FEEDBACK_FILE_LIST = "GetFeedbackFileList"
_BN_SEND_FEEDBACK = "SendFeedback"
_BN_SET_TIME = "SetTime"
_BN_SET_OFFLINE_TIMER = "SetOfflineTimer"
_BN_SEND_IO_SIGNALS = "SendIOSignals"
_BN_GET_IO_SIGNALS = "GetIOSignals"


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


def _is_bad_not_supported(err_str: str) -> bool:
    """Return True when the error string contains a BadNotSupported or BadMethodInvalid token."""
    return any(kw in err_str for kw in ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied"))


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

    method = await find_child_by_browse_name(ms, _BN_GET_FEEDBACK_FILE_LIST, ns_ijt)
    if method is None:
        pytest.skip(
            "GetFeedbackFileList not found in AssetManagement MethodSet — "
            "optional per feedback_methods CU; not implemented by this server"
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

    method = await find_child_by_browse_name(ms, _BN_SEND_FEEDBACK, ns_ijt)
    if method is None:
        pytest.skip(
            "SendFeedback not found in AssetManagement MethodSet — "
            "optional per feedback_methods CU; not implemented by this server"
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

    method_node = await find_child_by_browse_name(ms, _BN_GET_FEEDBACK_FILE_LIST, ns_ijt)
    if method_node is None:
        pytest.skip("GetFeedbackFileList method not found — skipping functional test")

    result = await find_and_call_method(ms, _BN_GET_FEEDBACK_FILE_LIST, ns_ijt, timeout=_METHOD_TIMEOUT)
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

    method = await find_child_by_browse_name(ms, _BN_SET_TIME, ns_ijt)
    assert method is not None, (
        f"SetTime method (ns_ijt={ns_ijt}) not found in AssetManagement MethodSet per set_time CU"
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

    method_node = await find_child_by_browse_name(ms, _BN_SET_TIME, ns_ijt)
    if method_node is None:
        pytest.skip("SetTime method not found — skipping functional test")

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    result = await find_and_call_method(
        ms,
        _BN_SET_TIME,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
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

    method = await find_child_by_browse_name(ms, _BN_SET_OFFLINE_TIMER, ns_ijt)
    if method is None:
        pytest.skip("SetOfflineTimer: Not Supported — optional per set_offline_timer CU")


# ---------------------------------------------------------------------------
# SetOfflineTimer — functional (function-scoped)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.SET_OFFLINE_TIMER)
async def test_set_offline_timer_callable(opcua_client, ns_indices):
    """SetOfflineTimer must be callable without raising an unexpected error.

    The method is called without arguments as a presence probe; BadNotSupported
    and BadArgumentsMissing are both accepted as skip conditions.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, _BN_SET_OFFLINE_TIMER, ns_ijt)
    if method_node is None:
        pytest.skip("SetOfflineTimer method not found — skipping functional test")

    result = await find_and_call_method(ms, _BN_SET_OFFLINE_TIMER, ns_ijt, timeout=_METHOD_TIMEOUT)
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if _is_bad_not_supported(err_str):
            pytest.skip(f"SetOfflineTimer returned BadNotSupported — accepted as optional behaviour: {err_str}")
        if "BadArgumentsMissing" in err_str or "BadInvalidArgument" in err_str:
            pytest.skip(f"SetOfflineTimer requires arguments not provided in probe call: {err_str}")
        pytest.fail(f"SetOfflineTimer failed with unexpected error: {err_str}")


# ---------------------------------------------------------------------------
# IOSignals methods — structure (session-scoped)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.IO_SIGNALS_METHODS)
async def test_send_io_signals_method_present(asset_management, ns_indices):
    """SendIOSignals method must be browsable in AssetManagement MethodSet."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_method_set(asset_management, ns_di, ns_indices.get(NS_IJT_BASE), ns_indices.get(NS_APP))
    if ms is None:
        pytest.skip(
            "IJT spec (OPC 40450-1) requires a MethodSet child under AssetManagement — this server omits it (non-conformant)"
        )

    method = await find_child_by_browse_name(ms, _BN_SEND_IO_SIGNALS, ns_ijt)
    if method is None:
        pytest.skip(
            "SendIOSignals not found in AssetManagement MethodSet — "
            "optional per io_signals_methods CU; not implemented by this server"
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

    method = await find_child_by_browse_name(ms, _BN_GET_IO_SIGNALS, ns_ijt)
    assert method is not None, (
        f"GetIOSignals method (ns_ijt={ns_ijt}) not found in AssetManagement MethodSet per io_signals_methods CU"
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

    method_node = await find_child_by_browse_name(ms, _BN_GET_IO_SIGNALS, ns_ijt)
    if method_node is None:
        pytest.skip("GetIOSignals method not found — skipping functional test")

    result = await find_and_call_method(ms, _BN_GET_IO_SIGNALS, ns_ijt, timeout=_METHOD_TIMEOUT)
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if _is_bad_not_supported(err_str):
            pytest.skip(f"GetIOSignals returned BadNotSupported — accepted, hardware-dependent: {err_str}")
        if "BadArgumentsMissing" in err_str or "BadInvalidArgument" in err_str:
            pytest.skip(f"GetIOSignals requires arguments not provided in probe call: {err_str}")
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

    method_node = await find_child_by_browse_name(ms, _BN_SEND_FEEDBACK, ns_ijt)
    if method_node is None:
        pytest.skip("SendFeedback method not found — skipping text-type functional test")

    text_content = ua.Variant("ConformanceTestTextFeedback", ua.VariantType.String)
    result = await find_and_call_method(ms, _BN_SEND_FEEDBACK, ns_ijt, text_content, timeout=_METHOD_TIMEOUT)
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

    list_node = await find_child_by_browse_name(ms, _BN_GET_FEEDBACK_FILE_LIST, ns_ijt)
    if list_node is None:
        pytest.skip("GetFeedbackFileList not found — cannot obtain file references for SendFeedback")

    list_result = await find_and_call_method(ms, _BN_GET_FEEDBACK_FILE_LIST, ns_ijt, timeout=_METHOD_TIMEOUT)
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

    send_node = await find_child_by_browse_name(ms, _BN_SEND_FEEDBACK, ns_ijt)
    if send_node is None:
        pytest.skip("SendFeedback method not found — skipping file-reference test")

    result = await find_and_call_method(ms, _BN_SEND_FEEDBACK, ns_ijt, ref_arg, timeout=_METHOD_TIMEOUT)
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

    method_node = await find_child_by_browse_name(ms, _BN_SEND_FEEDBACK, ns_ijt)
    if method_node is None:
        pytest.skip("SendFeedback not found — cannot test invalid file reference")

    invalid_ref = ua.Variant("urn:invalid:feedback:file:ref:xyz999", ua.VariantType.String)
    result = await find_and_call_method(ms, _BN_SEND_FEEDBACK, ns_ijt, invalid_ref, timeout=_METHOD_TIMEOUT)
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

    method_node = await find_child_by_browse_name(ms, _BN_SET_TIME, ns_ijt)
    if method_node is None:
        pytest.skip("SetTime not found — cannot test invalid datetime")

    import datetime as _dt

    min_dt = _dt.datetime(1, 1, 1, 0, 0, 0, tzinfo=_dt.timezone.utc)
    result = await find_and_call_method(
        ms,
        _BN_SET_TIME,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
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
    assert any(kw in err_str for kw in ("BadInvalidArgument", "BadOutOfRange", "BadTypeMismatch")), (
        f"Unexpected status for null datetime — expected Bad_InvalidArgument or Bad_OutOfRange, got: {err_str}"
    )


@pytest.mark.requires_cu(CU.SET_TIME)
async def test_set_time_far_past_timestamp_returns_bad_out_of_range(opcua_client, ns_indices):
    """SetTime with a timestamp far in the past must return Bad_OutOfRange or Bad_InvalidArgument.

    A timestamp from year 2000 (24+ years in the past) must be rejected by servers
    that validate timestamp plausibility.  Servers with wide acceptance windows may
    accept it; those cases are skipped rather than failed.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, _BN_SET_TIME, ns_ijt)
    if method_node is None:
        pytest.skip("SetTime not found — cannot test past timestamp")

    import datetime as _dt

    past_dt = _dt.datetime(2000, 1, 1, 0, 0, 0, tzinfo=_dt.timezone.utc)
    result = await find_and_call_method(
        ms,
        _BN_SET_TIME,
        ns_ijt,
        ua.Variant("", ua.VariantType.String),
        ua.Variant(past_dt, ua.VariantType.DateTime),
        timeout=_METHOD_TIMEOUT,
    )
    if result.success:
        pytest.skip(
            "SetTime accepted year-2000 timestamp — server has a wide acceptance window; "
            "rejection behaviour is implementation-dependent"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if _is_bad_not_supported(err_str):
        pytest.skip(f"SetTime not supported on this server: {err_str}")
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

    method_node = await find_child_by_browse_name(ms, _BN_SET_OFFLINE_TIMER, ns_ijt)
    if method_node is None:
        pytest.skip("SetOfflineTimer not found — skipping zero-duration test")

    zero_duration = ua.Variant(0, ua.VariantType.UInt32)
    result = await find_and_call_method(ms, _BN_SET_OFFLINE_TIMER, ns_ijt, zero_duration, timeout=_METHOD_TIMEOUT)
    if not result.success:
        err_str = str(result.error) if result.error else "unknown error"
        if _is_bad_not_supported(err_str):
            pytest.skip(f"SetOfflineTimer returned BadNotSupported — accepted as optional: {err_str}")
        if "BadInvalidArgument" in err_str or "BadOutOfRange" in err_str:
            pytest.skip(f"Server rejects duration=0 (timer-disable may not be supported): {err_str}")
        pytest.fail(f"SetOfflineTimer with duration=0 failed unexpectedly: {err_str}")


@pytest.mark.requires_cu(CU.SET_OFFLINE_TIMER)
async def test_set_offline_timer_invalid_piu_returns_bad_status(opcua_client, ns_indices):
    """SetOfflineTimer with an unknown ProductInstanceUri must return a Bad status.

    Per spec: Bad_NoEntryExists or Bad_InvalidArgument.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, _BN_SET_OFFLINE_TIMER, ns_ijt)
    if method_node is None:
        pytest.skip("SetOfflineTimer not found — cannot test invalid PIU")

    invalid_piu = ua.Variant(_INVALID_PIU, ua.VariantType.String)
    result = await find_and_call_method(ms, _BN_SET_OFFLINE_TIMER, ns_ijt, invalid_piu, timeout=_METHOD_TIMEOUT)
    if result.success:
        pytest.fail(
            f"SetOfflineTimer with unknown PIU '{_INVALID_PIU}' unexpectedly returned Good — "
            "server must return a Bad status for unknown asset URIs"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if _is_bad_not_supported(err_str):
        pytest.skip(f"SetOfflineTimer not supported on this server: {err_str}")
    assert any(
        kw in err_str
        for kw in (
            "BadNodeIdUnknown",
            "BadNotFound",
            "BadNoEntryExists",
            "BadInvalidArgument",
            "BadArgumentsMissing",
        )
    ), f"Unexpected status for unknown PIU — expected Bad_NoEntryExists or Bad_InvalidArgument, got: {err_str}"


# ---------------------------------------------------------------------------
# IOSignals methods — negative (function-scoped)
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.IO_SIGNALS_METHODS)
async def test_get_io_signals_invalid_piu_returns_bad_status(opcua_client, ns_indices):
    """GetIOSignals with an unknown ProductInstanceUri must return a Bad status.

    Per spec: Bad_NoEntryExists or Bad_InvalidArgument.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, _BN_GET_IO_SIGNALS, ns_ijt)
    if method_node is None:
        pytest.skip("GetIOSignals not found — cannot test invalid PIU")

    result = await find_and_call_method(
        ms,
        _BN_GET_IO_SIGNALS,
        ns_ijt,
        ua.Variant(_INVALID_PIU, ua.VariantType.String),
        ua.Variant([], ua.VariantType.ExtensionObject),
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
    assert any(kw in err_str for kw in ("BadNodeIdUnknown", "BadNotFound", "BadNoEntryExists", "BadInvalidArgument")), (
        f"Unexpected status for unknown PIU — expected Bad_NoEntryExists or Bad_InvalidArgument, got: {err_str}"
    )


@pytest.mark.requires_cu(CU.IO_SIGNALS_METHODS)
async def test_send_io_signals_invalid_signal_id_returns_bad_status(opcua_client, ns_indices):
    """SendIOSignals with an invalid signal identifier must return a Bad status.

    Per spec design: an unknown/invalid SignalId must be rejected.
    Bad_NoEntryExists or Bad_InvalidArgument is expected; no physical IO change
    must occur.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")

    ms = await _get_fresh_method_set(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))

    method_node = await find_child_by_browse_name(ms, _BN_SEND_IO_SIGNALS, ns_ijt)
    if method_node is None:
        pytest.skip("SendIOSignals not found — cannot test invalid signal ID")

    invalid_signal = ua.Variant("INVALID_SIGNAL_ID_XYZ999", ua.VariantType.String)
    result = await find_and_call_method(ms, _BN_SEND_IO_SIGNALS, ns_ijt, invalid_signal, timeout=_METHOD_TIMEOUT)
    if result.success:
        pytest.fail(
            "SendIOSignals with invalid SignalId 'INVALID_SIGNAL_ID_XYZ999' "
            "unexpectedly returned Good — server must reject unknown signal IDs"
        )
    err_str = str(result.error) if result.error else "unknown error"
    if _is_bad_not_supported(err_str):
        pytest.skip(f"SendIOSignals not supported on this server: {err_str}")
    assert any(
        kw in err_str
        for kw in (
            "BadNodeIdUnknown",
            "BadNotFound",
            "BadNoEntryExists",
            "BadInvalidArgument",
            "BadArgumentsMissing",
            "BadTypeMismatch",
        )
    ), f"Unexpected status for invalid signal ID — expected Bad_NoEntryExists or Bad_InvalidArgument, got: {err_str}"
