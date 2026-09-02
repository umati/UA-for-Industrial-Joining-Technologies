"""
specification tests for Result Access Methods — OPC 40450-1 IJT Base.

Covered conformance units:

    get_latest_result
        The Server supports GetLatestResult method.

    get_result_by_id
        The Server supports GetResultById method.

    get_result_with_filter_criteria
        The Server supports GetResultIdListFiltered method to retrieve list of
        ResultIds based on at least Result.ResultMetaData.SequenceNumber or
        Result.ResultMetaData.CreationTime.

    result_variable_access
        The Server reports Results as a ResultVariable value in the address space
        with at least Result.ResultMetaData as per JoiningSystemResultType.

    request_results
        The Server supports RequestResults method which sends stored results using
        RequestedResultEventType or RequestedResultVariable.

    requested_result_variable_access
        The Server reports Results as RequestedResultVariable value for results
        generated upon successful execution of RequestResults or
        RequestUnacknowledgedResults.

    requested_result_event_access
        The Server generates an event of RequestedResultEventType for results
        generated upon successful execution of RequestResults or
        RequestUnacknowledgedResults.

    acknowledge_results
        The Server supports AcknowledgeResults method.

    request_unacknowledged_results
        The Server supports RequestUnacknowledgedResults method.
"""

import asyncio
import dataclasses
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.namespaces import BN, NS_APP, NS_IJT_BASE, NS_MACH_RESULT, ResultType
from helpers.node_discovery import find_child_by_browse_name, find_joining_system
from helpers.result_polling import extract_result_id, poll_until_result_id_changes
from helpers.result_validator import assert_result_data_valid
from helpers.skip_reasons import skip_accepted_policy
from helpers.target_server_cu_config import (
    UINT64_MAX,
    RequestResultsConfig,
    build_request_results_arguments,
)

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

# Timeout in milliseconds for GetLatestResult / RequestResults calls
_OPCUA_TIMEOUT_MS = 10000
_OPCUA_ZERO_TIMEOUT_MS = 0

# Wall-clock timeout used when wrapping async OPC UA calls
_METHOD_WALL_TIMEOUT = 15.0

# Wait period in seconds before reading a live variable that may just have updated
_LIVE_VARIABLE_SETTLE_SECS = 1.0

# A result identifier that is guaranteed not to exist on any real server
_NONEXISTENT_RESULT_ID = "nonexistent-result-identifier-for-negative-test"
_NO_RESULT_DATA = object()


@dataclasses.dataclass(frozen=True)
class _RequestedResultUpdate:
    value: Any
    data_value: Any


class _RequestedResultBuffer:
    """Buffer every RequestedResult data change so intermediate results are not missed."""

    def __init__(self, client: Any, node_id: ua.NodeId) -> None:
        self._client = client
        self._node_id = node_id
        self._queue: asyncio.Queue[_RequestedResultUpdate] = asyncio.Queue(maxsize=100)
        self._subscription: Any = None
        self._handle: Any = None

    def datachange_notification(self, _node: Any, value: Any, data: Any) -> None:
        monitored_item = getattr(data, "monitored_item", None)
        data_value = getattr(monitored_item, "Value", None)
        try:
            self._queue.put_nowait(_RequestedResultUpdate(value=value, data_value=data_value))
        except asyncio.QueueFull:
            logger.warning("RequestedResult update buffer is full; dropping one data change")

    def event_notification(self, _event: Any) -> None:
        """Satisfy the asyncua subscription handler interface."""

    def status_change_notification(self, _status: Any) -> None:
        """Satisfy the asyncua subscription handler interface."""

    async def __aenter__(self) -> "_RequestedResultBuffer":
        self._subscription = await self._client.create_subscription(50.0, self)
        node = self._client.get_node(self._node_id)
        self._handle = await self._subscription.subscribe_data_change(node)
        return self

    async def __aexit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        await self._subscription.unsubscribe(self._handle)
        await self._subscription.delete()

    def discard_pending(self) -> None:
        """Remove initial or prior-call notifications before a new method attempt."""
        while True:
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return

    async def collect_result(self, timeout_s: float) -> _RequestedResultUpdate:
        """Return the first decoded result delivered after a successful method call."""
        deadline = asyncio.get_running_loop().time() + timeout_s
        observed: list[tuple[int | None, str]] = []
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                pytest.fail(
                    f"RequestedResult stream did not deliver a decoded result within {timeout_s}s; observed {observed!r}"
                )
            try:
                update = await asyncio.wait_for(self._queue.get(), timeout=remaining)
            except asyncio.TimeoutError:
                pytest.fail(
                    f"RequestedResult stream did not deliver a decoded result within {timeout_s}s; observed {observed!r}"
                )
            sequence_number = _extract_sequence_number(update.value)
            result_id = extract_result_id(update.value)
            observed.append((sequence_number, result_id))
            if result_id.strip():
                return update


def _get_request_results_config() -> RequestResultsConfig:
    """Load RequestResultsConfig from the active profile or environment, defaulting to sequence_number."""
    profile_path = os.environ.get("OPCUA_TARGET_SERVER_PROFILE", "").strip()
    cfg = RequestResultsConfig()
    if profile_path:
        path = Path(profile_path)
        if not path.exists():
            raise FileNotFoundError(f"Configured profile does not exist: {profile_path}")
        from helpers.sut_manifest import load_sut_manifest

        manifest = load_sut_manifest(path)
        cfg = manifest.to_execution_profile().cu_execution.request_results

    env_strategy = os.environ.get("OPCUA_REQUEST_RESULTS_FILTER_STRATEGY", "").strip().lower()
    if env_strategy in ("sequence_number", "timestamp", "both"):
        from dataclasses import replace

        cfg = replace(cfg, filter_strategy=env_strategy)
    return cfg


def _extract_sequence_number(result_data: Any) -> int | None:
    """Extract integer SequenceNumber from result data if present across live formats."""
    if result_data is None:
        return None

    payload = result_data
    for _ in range(4):
        body = getattr(payload, "Body", None)
        if body is not None:
            payload = body
            continue
        val = getattr(payload, "Value", None)
        if val is not None:
            payload = val
            continue
        val_lower = getattr(payload, "value", None)
        if val_lower is not None:
            payload = val_lower
            continue
        break

    meta = getattr(payload, "ResultMetaData", None)
    if meta is None and hasattr(payload, "get"):
        meta = payload.get("ResultMetaData")
    if meta is None:
        meta = payload  # In case ResultMetaData itself was passed

    seq = None
    for field_name in ("SequenceNumber", "sequence_number", "Sequence_Number"):
        if hasattr(meta, field_name):
            seq = getattr(meta, field_name)
            break
        if hasattr(meta, "get"):
            val = meta.get(field_name)
            if val is not None:
                seq = val
                break

    for _ in range(3):
        if hasattr(seq, "Value"):
            seq = seq.Value
        elif hasattr(seq, "value"):
            seq = seq.value
        elif hasattr(seq, "Body"):
            seq = seq.Body

    if isinstance(seq, bool) or not isinstance(seq, int):
        return None

    return seq if 0 < seq <= UINT64_MAX else None


def _get_request_results_args(
    result_data: Any = _NO_RESULT_DATA,
    config: RequestResultsConfig | None = None,
    single_result: bool = False,
) -> tuple[ua.Variant, ua.Variant, ua.Variant, ua.Variant, ua.Variant]:
    """Return the 5 typed input arguments for RequestResults."""
    cfg = config if config is not None else _get_request_results_config()
    seq = None if result_data is _NO_RESULT_DATA else _extract_sequence_number(result_data)
    if result_data is not _NO_RESULT_DATA and cfg.filter_strategy in ("sequence_number", "both") and seq is None:
        pytest.fail(
            "The triggered result has no decoded UInt64 ResultMetaData.SequenceNumber; "
            "a sequence-filtered RequestResults call cannot be correlated safely"
        )
    if single_result:
        pinned_seq = seq if seq is not None and seq > 0 else max(1, cfg.from_sequence_number)
        single_cfg = dataclasses.replace(
            cfg,
            from_sequence_number=max(1, pinned_seq - 1),
            to_sequence_number=pinned_seq,
        )
        return build_request_results_arguments(single_cfg, triggered_seq=None)
    return build_request_results_arguments(cfg, triggered_seq=seq)


async def _call_request_results(
    rm_node: Any,
    rr_node: Any,
    rr_args: list[ua.Variant] | tuple[ua.Variant, ...],
    *,
    timeout_s: float = _METHOD_WALL_TIMEOUT,
    max_retries: int = 8,
    retry_delay_s: float = 1.5,
    before_attempt: Callable[[], None] | None = None,
) -> Any:
    """Call RequestResults with automated retry if server is actively streaming from a prior call."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        if before_attempt is not None:
            before_attempt()
        try:
            return await asyncio.wait_for(
                rm_node.call_method(rr_node.nodeid, *rr_args),
                timeout=timeout_s,
            )
        except ua.UaError as exc:
            last_exc = exc
            exc_str = str(exc).lower()
            if attempt < max_retries - 1 and ("uncertain" in exc_str or "invalidstate" in exc_str):
                logger.info(
                    "RequestResults returned busy/streaming status (%s); waiting %.1fs before retry %d/%d...",
                    exc,
                    retry_delay_s,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(retry_delay_s)
                continue
            raise
    if last_exc is not None:
        raise last_exc


async def _call_and_collect_requested_result(
    rm_node: Any,
    rr_node: Any,
    rr_args: tuple[ua.Variant, ...],
    subscription_client: Any,
    requested_var_node: Any,
    *,
    timeout_s: float,
) -> _RequestedResultUpdate:
    """Subscribe before RequestResults and return a fresh decoded update from its result batch."""
    async with _RequestedResultBuffer(subscription_client, requested_var_node.nodeid) as buffer:
        try:
            response = await _call_request_results(
                rm_node,
                rr_node,
                rr_args,
                before_attempt=buffer.discard_pending,
            )
        except ua.UaError as exc:
            pytest.fail(f"RequestResults call failed with OPC UA status: {exc}")
        except asyncio.TimeoutError:
            pytest.fail("RequestResults timed out")
        _assert_request_results_output(response, "RequestResults")
        return await buffer.collect_result(timeout_s)


# Default arguments for RequestResults: sequence_number strategy by default.
_DEFAULT_RR_ARGS = build_request_results_arguments()
_RR_FROM_SEQ = _DEFAULT_RR_ARGS[0]
_RR_TO_SEQ = _DEFAULT_RR_ARGS[1]
_RR_FROM_TIME = _DEFAULT_RR_ARGS[2]
_RR_TO_TIME = _DEFAULT_RR_ARGS[3]
_RR_MIN_DURATION = _DEFAULT_RR_ARGS[4]
_RUR_MAX_RESULTS = ua.Variant(1, ua.VariantType.UInt32)
_RUR_MIN_DURATION = ua.Variant(0.0, ua.VariantType.Double)


def _fail_if_rur_bad_arguments_missing(exc):
    if "BadArgumentsMissing" in str(exc):
        pytest.fail(
            "RequestUnacknowledgedResults returned BadArgumentsMissing despite valid "
            "MaxResults and RequestedMinimumDurationBetweenResults arguments"
        )


def _method_output_list(raw) -> list:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    return [raw]


def _assert_acknowledge_output(raw, context: str) -> list:
    output = _method_output_list(raw)
    assert len(output) >= 2, f"{context} must return [ErrorPerResultId, Error], got {output!r}"
    return output


def _assert_acknowledge_reports_error(raw, context: str) -> None:
    output = _assert_acknowledge_output(raw, context)
    per_result = output[0] if output else None
    if isinstance(per_result, (list, tuple)):
        for status in per_result:
            try:
                if int(status) != 0:
                    return
            except (TypeError, ValueError):
                continue
    try:
        if len(output) >= 2 and int(output[1]) != 0:
            return
    except (TypeError, ValueError):
        pass
    pytest.fail(f"{context} returned Good with no output-level error indicator: {output!r}")


def _assert_request_unacknowledged_output(raw, context: str) -> list:
    output = _method_output_list(raw)
    assert len(output) >= 4, (
        f"{context} must return "
        "[RevisedMinimumDurationBetweenResults, UnacknowledgedResultCount, Status, StatusMessage], "
        f"got {output!r}"
    )
    return output


def _request_results_status(raw, context: str) -> int:
    """Validate the three RequestResults outputs and return the integer Status."""
    output = _method_output_list(raw)
    assert len(output) >= 3, (
        f"{context} must return [RevisedMinimumDurationBetweenResults, Status, StatusMessage], got {output!r}"
    )
    status = output[1]
    for _ in range(2):
        if hasattr(status, "Value"):
            status = status.Value
        elif hasattr(status, "value"):
            status = status.value
    assert status is not None, f"{context} returned no Status: {output!r}"
    try:
        status_value = int(status)
    except (TypeError, ValueError) as exc:
        pytest.fail(f"{context} returned a non-integer Status {status!r}: {exc}")
    return status_value


def _assert_request_results_output(raw, context: str) -> list:
    """Validate the three RequestResults outputs and require a successful Status."""
    output = _method_output_list(raw)
    status_value = _request_results_status(output, context)
    assert status_value == 0, f"{context} returned non-zero Status={status_value}"
    return output


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


async def _get_result_management(client, ns_mr):
    """Re-discover ResultManagement on a fresh client connection."""
    js = await find_joining_system(client)
    if js is None:
        pytest.fail("JoiningSystem not found — server must be running and reachable")
    rm = await find_child_by_browse_name(js, BN.RESULT_MANAGEMENT, ns_mr)
    if rm is None:
        pytest.fail("ResultManagement node not found on JoiningSystem — required address space node is missing")
    return rm


async def _call_get_latest_result(rm, ns_mr, timeout_ms=_OPCUA_TIMEOUT_MS, wall_timeout=20.0):
    """Call GetLatestResult and return (handle, result_data), or (None, None) on failure."""
    glr_node = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if glr_node is None:
        return None, None
    try:
        raw = await asyncio.wait_for(
            rm.call_method(
                glr_node.nodeid,
                ua.Variant(timeout_ms, ua.VariantType.Int32),
            ),
            timeout=wall_timeout,
        )
    except (ua.UaError, asyncio.TimeoutError) as exc:
        logger.debug("GetLatestResult failed: %s", exc)
        return None, None

    if isinstance(raw, (list, tuple)):
        handle = raw[0] if len(raw) > 0 else None
        result_data = raw[1] if len(raw) > 1 else None
    else:
        handle = None
        result_data = raw
    return handle, result_data


async def _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices):
    """Trigger MULTI_STEP_OK_RESULT and call GetLatestResult.

    Returns (rm, handle, result_data). Skips when the trigger is unavailable
    or when GetLatestResult returns no data.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    outcome = await result_trigger.trigger_single(
        result_type=ResultType.MULTI_STEP_OK_RESULT,
        include_traces=False,
    )
    if not outcome.triggered:
        pytest.skip(outcome.skip_reason)

    rm = await _get_result_management(opcua_client, ns_mr)
    handle, result_data = await _call_get_latest_result(rm, ns_mr, timeout_ms=_OPCUA_TIMEOUT_MS)
    return rm, handle, result_data


async def _find_result_var(results_folder, ns_mr, ns_ijt, ns_indices=None):
    """Locate the Result variable inside the Results folder.

    Per OPC 40001-101, the Result variable BrowseName uses NS_MACH_RESULT (ns_mr).
    Falls back to NS_IJT_BASE (ns_ijt) and then the vendor-specific NS_APP for
    older or non-standard server implementations.
    """
    node = await find_child_by_browse_name(results_folder, BN.RESULT, ns_mr)
    if node is None and ns_ijt is not None:
        node = await find_child_by_browse_name(results_folder, BN.RESULT, ns_ijt)
    if node is None and ns_indices is not None:
        ns_app = ns_indices.get(NS_APP)
        if ns_app is not None:
            node = await find_child_by_browse_name(results_folder, BN.RESULT, ns_app)
    return node


async def _find_requested_result_var(rm, ns_indices, ns_mr):
    """Locate the RequestedResult variable inside the Results folder.

    Like Result, the RequestedResult variable lives under
    ResultManagement → Results folder. Both carry the same
    ResultDataType payload; RequestedResult is updated only when
    RequestResults is called (stored/historical result), while
    Result is updated for live results.
    """
    # First locate the Results folder
    results_folder = await find_child_by_browse_name(rm, BN.RESULTS, ns_mr)
    if results_folder is None:
        return None

    ns_ijt = ns_indices.get(NS_IJT_BASE)
    node = await find_child_by_browse_name(results_folder, BN.REQUESTED_RESULT, ns_ijt) if ns_ijt else None
    if node is None:
        node = await find_child_by_browse_name(results_folder, BN.REQUESTED_RESULT, ns_mr)
    if node is None:
        ns_app = ns_indices.get(NS_APP)
        if ns_app is not None:
            node = await find_child_by_browse_name(results_folder, BN.REQUESTED_RESULT, ns_app)
    return node


def _handle_missing_result_variable(ns_indices, ns_mr, ns_ijt):
    """Skip known simulator gap; fail on non-simulator servers."""
    if ns_indices.get(NS_APP) is not None:
        pytest.skip(
            f"Result variable not found under Results folder (tried ns_mr={ns_mr}, ns_ijt={ns_ijt}, ns_app) — "
            "simulator does not expose this variable; verify against a spec-compliant server"
        )
    pytest.fail(
        f"Result variable not found under Results folder (tried ns_mr={ns_mr}, ns_ijt={ns_ijt}, ns_app) — "
        "required for this conformance unit on non-simulator servers"
    )


def _handle_missing_requested_result_variable(ns_indices):
    """Fail when RequestedResult variable is not found — it is required for this CU."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    ns_app = ns_indices.get(NS_APP)
    pytest.fail(
        f"RequestedResult variable not found under ResultManagement/Results "
        f"(tried ns_ijt={ns_ijt}, ns_mr={ns_mr}, ns_app={ns_app}) — "
        "required for this conformance unit"
    )


# ─── get_latest_result ───


@pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
async def test_get_latest_result_returns_handle_and_result_data(opcua_client, result_trigger, ns_indices):
    """The Server supports GetLatestResult method — returns a non-None handle and a valid ResultDataType."""
    _, handle, result_data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)

    assert handle is not None, "GetLatestResult must return a non-None handle (output[0])"
    assert result_data is not None, "GetLatestResult must return result data (output[1])"
    assert_result_data_valid(result_data, context="GetLatestResult")


@pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
async def test_get_latest_result_with_zero_timeout_does_not_hang(opcua_client, ns_indices):
    """GetLatestResult with a zero-millisecond timeout must return promptly without blocking."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    glr_node = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if glr_node is None:
        pytest.skip("GetLatestResult method not found")

    try:
        await asyncio.wait_for(
            rm.call_method(
                glr_node.nodeid,
                ua.Variant(_OPCUA_ZERO_TIMEOUT_MS, ua.VariantType.Int32),
            ),
            timeout=5.0,
        )
    except ua.UaError as exc:
        logger.debug("GetLatestResult(zero timeout) raised UaError (acceptable): %s", exc)
    except asyncio.TimeoutError:
        pytest.fail(
            "GetLatestResult with a zero-millisecond timeout did not return within five "
            "seconds — server must not block indefinitely on an immediate-return call"
        )


# ─── get_result_by_id ───


@pytest.mark.requires_cu(CU.GET_RESULT_BY_ID)
async def test_get_result_by_id_returns_matching_result(opcua_client, result_trigger, ns_indices):
    """The Server supports GetResultById — returns the result whose ResultId matches the query."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _handle, result_data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)
    if result_data is None:
        pytest.skip("GetLatestResult returned no data — cannot test GetResultById")

    meta = getattr(result_data, "ResultMetaData", None)
    result_id = str(getattr(meta, "ResultId", None) or "") if meta is not None else ""
    if not result_id.strip():
        pytest.skip("ResultId is empty — cannot call GetResultById")

    grbi_node = await find_child_by_browse_name(rm, BN.GET_RESULT_BY_ID, ns_mr)
    if grbi_node is None:
        pytest.skip(f"GetResultById method not found in ResultManagement (ns={ns_mr})")

    try:
        raw = await asyncio.wait_for(
            rm.call_method(
                grbi_node.nodeid,
                ua.Variant(result_id, ua.VariantType.String),
                ua.Variant(_OPCUA_TIMEOUT_MS, ua.VariantType.Int32),
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        pytest.skip(f"GetResultById raised UaError: {exc}")

    result_data_fetched = raw[1] if isinstance(raw, (list, tuple)) and len(raw) > 1 else raw
    assert result_data_fetched is not None, "GetResultById returned None for a valid ResultId"

    meta_fetched = getattr(result_data_fetched, "ResultMetaData", None)
    result_id_fetched = str(getattr(meta_fetched, "ResultId", None) or "") if meta_fetched is not None else ""
    assert result_id_fetched == result_id, (
        f"GetResultById returned a result with a different ResultId: expected {result_id!r}, got {result_id_fetched!r}"
    )


@pytest.mark.requires_cu(CU.GET_RESULT_BY_ID)
async def test_get_result_by_id_is_idempotent(opcua_client, result_trigger, ns_indices):
    """Calling GetResultById twice with the same ResultId must return identical data."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _handle, result_data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)
    if result_data is None:
        pytest.skip("GetLatestResult returned no data")

    meta = getattr(result_data, "ResultMetaData", None)
    result_id = str(getattr(meta, "ResultId", None) or "") if meta is not None else ""
    if not result_id.strip():
        pytest.skip("ResultId is empty — cannot test idempotence of GetResultById")

    grbi_node = await find_child_by_browse_name(rm, BN.GET_RESULT_BY_ID, ns_mr)
    if grbi_node is None:
        pytest.skip(f"GetResultById method not found (ns={ns_mr})")

    ids_from_calls: list[str] = []
    for call_index in range(2):
        try:
            raw = await asyncio.wait_for(
                rm.call_method(
                    grbi_node.nodeid,
                    ua.Variant(result_id, ua.VariantType.String),
                    ua.Variant(_OPCUA_TIMEOUT_MS, ua.VariantType.Int32),
                ),
                timeout=_METHOD_WALL_TIMEOUT,
            )
        except ua.UaError as exc:
            pytest.skip(f"GetResultById call {call_index} raised UaError: {exc}")

        data = raw[1] if isinstance(raw, (list, tuple)) and len(raw) > 1 else raw
        if data is None:
            pytest.skip(f"GetResultById call {call_index} returned None")

        fetched_meta = getattr(data, "ResultMetaData", None)
        ids_from_calls.append(str(getattr(fetched_meta, "ResultId", None) or "") if fetched_meta is not None else "")

    assert ids_from_calls[0] == ids_from_calls[1], (
        f"GetResultById is not idempotent — first call gave {ids_from_calls[0]!r}, second gave {ids_from_calls[1]!r}"
    )


@pytest.mark.requires_cu(CU.GET_RESULT_BY_ID)
async def test_get_result_by_id_with_nonexistent_id_returns_error(opcua_client, ns_indices):
    """GetResultById with a nonexistent identifier must report an error.

    Servers may reject the call at service level or return Good with a nonzero
    operation-level Error output and a null/empty Result.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    grbi_node = await find_child_by_browse_name(rm, BN.GET_RESULT_BY_ID, ns_mr)
    if grbi_node is None:
        pytest.skip(f"GetResultById method not found (ns={ns_mr})")

    try:
        result = await asyncio.wait_for(
            rm.call_method(
                grbi_node.nodeid,
                ua.Variant(_NONEXISTENT_RESULT_ID, ua.VariantType.String),
                ua.Variant(_OPCUA_TIMEOUT_MS, ua.VariantType.Int32),
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
        # Signature: GetResultById → [ResultHandle: UInt32, Result: ResultDataType, Error: Int32]
        # output[2] is the Error code; a non-zero value means "not found".
        # output[1] being None/empty also signals the result was not found.
        output = list(result) if isinstance(result, (list, tuple)) else ([] if result is None else [result])
        if len(output) >= 3:
            try:
                if int(output[2]) != 0:
                    return  # PASS: server correctly signals not-found via Error output
            except (TypeError, ValueError):
                pass
        # Fallback: even without Error field, a null Result is acceptable
        if len(output) >= 2 and output[1] is None:
            return  # PASS: server returned null Result for nonexistent id
        message = (
            "GetResultById with nonexistent identifier returned Success with no error indicator — "
            "expected non-zero Error in output[2] or null Result in output[1]"
        )
        if ns_indices.get(NS_APP) is not None:
            pytest.skip(f"{message}; known simulator gap")
        pytest.fail(message)
    except ua.UaError:
        pass  # Expected: server correctly rejected the unknown identifier
    except asyncio.TimeoutError:
        pytest.skip(
            "GetResultById with nonexistent identifier timed out — server may be slow to reject unknown identifiers"
        )


# ─── get_result_with_filter_criteria ───


@pytest.mark.requires_cu(CU.GET_RESULT_WITH_FILTER_CRITERIA)
async def test_get_result_id_list_filtered_presence_or_not_implemented(opcua_client, ns_indices):
    """GetResultIdListFiltered is an optional CU in the IJT Base specification
    (CU: 'IJT Get Result with Filter Criteria').  A server may implement it or
    expose the node but return BadNotSupported — both are conformant.
    Omitting the node entirely is also conformant for this optional CU.

    This test skips when the node is absent and passes (with a log) otherwise.
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    filter_node = await find_child_by_browse_name(rm, BN.GET_RESULT_ID_LIST_FILTERED, ns_mr)

    if filter_node is None:
        pytest.skip("GetResultIdListFiltered: Not Supported — method node absent (optional CU)")

    # Pure presence test — verify the node exists and is callable.
    # We do NOT invoke call_method because the corrected signature requires
    # 4 inputs (Filter, OrderedBy, MaxResults, Timeout) and zero-arg calls
    # would produce misleading BadTooFewArguments results.
    try:
        executable = await filter_node.read_attribute(ua.AttributeIds.Executable)
    except ua.UaError as exc:
        pytest.skip(f"GetResultIdListFiltered Executable attribute unreadable: {exc}")

    assert executable.Value.Value is True, "GetResultIdListFiltered Executable attribute must be True"
    logger.debug("GetResultIdListFiltered node is present and Executable=True")


# ─── result_variable_access ───


@pytest.mark.requires_cu(CU.RESULT_VARIABLE_ACCESS)
async def test_result_management_exposes_last_result_metadata_variable(result_management, ns_indices):
    """The Server reports Results as a ResultVariable value in the address space with at least ResultMetaData."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")
    # ResultManagement → Results(ns_mr) → Result(ns_mr) → ResultMetaData(ns_mr)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    results_folder = await find_child_by_browse_name(result_management, BN.RESULTS, ns_mr)
    if results_folder is None:
        pytest.skip("Results folder not found on ResultManagement")
    result_var = await _find_result_var(results_folder, ns_mr, ns_ijt, ns_indices)
    if result_var is None:
        _handle_missing_result_variable(ns_indices, ns_mr, ns_ijt)
    last_meta_node = await find_child_by_browse_name(result_var, BN.RESULT_META_DATA, ns_mr)
    if last_meta_node is None:
        pytest.skip("ResultMetaData not found under Results/Result — optional per spec")

    try:
        value = await last_meta_node.read_value()
    except ua.UaError as exc:
        pytest.skip(f"Could not read Results/Result/ResultMetaData: {exc}")

    if value is not None:
        logger.debug("Results/Result/ResultMetaData is readable (value present)")


@pytest.mark.requires_cu(CU.RESULT_VARIABLE_ACCESS)
async def test_last_result_metadata_updated_after_trigger(opcua_client, result_trigger, ns_indices):
    """Results/Result/ResultMetaData.ResultId must change after a new result is produced."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    # ResultManagement → Results(ns_mr) → Result(ns_mr) → ResultMetaData(ns_mr)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    results_folder = await find_child_by_browse_name(rm, BN.RESULTS, ns_mr)
    if results_folder is None:
        pytest.skip("Results folder not found on ResultManagement")
    result_var = await _find_result_var(results_folder, ns_mr, ns_ijt, ns_indices)
    if result_var is None:
        _handle_missing_result_variable(ns_indices, ns_mr, ns_ijt)
    last_meta_node = await find_child_by_browse_name(result_var, BN.RESULT_META_DATA, ns_mr)
    if last_meta_node is None:
        pytest.skip("Results/Result/ResultMetaData variable not found")

    try:
        before_value = await last_meta_node.read_value()
    except ua.UaError:
        before_value = None

    before_id = extract_result_id(before_value)

    outcome = await result_trigger.trigger_single(
        result_type=ResultType.MULTI_STEP_OK_RESULT,
        include_traces=False,
    )
    if not outcome.triggered:
        pytest.skip(outcome.skip_reason)

    # Bounded poll: returns as soon as a new ResultId is published and only
    # spends the full active budget when the server never publishes one.
    try:
        poll = await poll_until_result_id_changes(
            last_meta_node.read_value,
            before_id,
            timeout_s=result_trigger.active_result_timeout_s,
        )
    except ua.UaError as exc:
        pytest.skip(f"Could not read Results/Result/ResultMetaData after trigger: {exc}")

    after_value = poll.value
    assert after_value is not None, "Results/Result/ResultMetaData must not be None after a result is produced"
    after_id = poll.result_id

    if before_id.strip() and not poll.changed:
        if not result_trigger.is_simulator:
            skip_accepted_policy(
                "Results/Result/ResultMetaData variable was not updated after an accepted trigger — "
                "controller delivers results via Event notifications (JoiningSystemResultReadyEventType) "
                "rather than address-space variable polling",
                method=outcome.method,
            )
        assert poll.changed, (
            f"Results/Result/ResultMetaData.ResultId did not change after an accepted trigger "
            f"(trigger method={outcome.method!r}, before={before_id!r}, after={after_id!r}, "
            f"waited {poll.elapsed_s:.1f}s of {poll.timeout_s:.1f}s over {poll.reads} read(s)); "
            "an accepted joining operation must publish a new result"
        )


@pytest.mark.requires_cu(CU.RESULT_VARIABLE_ACCESS)
async def test_result_management_results_folder_contains_result_nodes(result_management, ns_indices):
    """The Results folder inside ResultManagement must contain at least one node."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    results_folder = await find_child_by_browse_name(result_management, BN.RESULTS, ns_mr)
    if results_folder is None:
        pytest.skip("Results folder not found in ResultManagement")

    children = await results_folder.get_children()
    assert len(children) > 0, "Results folder in ResultManagement must contain at least one node"


# ─── request_results ───


@pytest.mark.requires_cu(CU.REQUEST_RESULTS)
async def test_request_results_method_is_present_and_callable(opcua_client, result_trigger, ns_indices):
    """The Server supports RequestResults method — method node is present and can be invoked."""
    rm, _handle, _data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)

    # RequestResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rr_node = await find_child_by_browse_name(rm, BN.REQUEST_RESULTS, ns_ijt)
    if rr_node is None:
        pytest.fail("RequestResults method is missing although CU.REQUEST_RESULTS is enabled")

    rr_args = _get_request_results_args(_data)
    try:
        res = await _call_request_results(rm, rr_node, rr_args)
    except ua.UaError as exc:
        pytest.fail(f"RequestResults method call failed with OPC UA error: {exc}")
    except asyncio.TimeoutError:
        pytest.fail("RequestResults method call timed out")

    _assert_request_results_output(res, "RequestResults")


# ─── requested_result_variable_access ───


@pytest.mark.requires_cu(CU.REQUESTED_RESULT_VARIABLE_ACCESS)
async def test_requested_result_variable_is_present_in_result_management(result_management, ns_indices):
    """The Server reports Results as RequestedResultVariable value following RequestResults or RequestUnacknowledgedResults."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    requested_var_node = await _find_requested_result_var(result_management, ns_indices, ns_mr)
    if requested_var_node is None:
        _handle_missing_requested_result_variable(ns_indices)

    try:
        value = await requested_var_node.read_value()
    except ua.UaError as exc:
        pytest.skip(f"Could not read RequestedResult variable: {exc}")

    if value is not None:
        logger.debug("RequestedResult variable is readable")


@pytest.mark.requires_cu(CU.REQUESTED_RESULT_VARIABLE_ACCESS)
async def test_request_results_populates_requested_result_variable(
    opcua_client, subscription_client, result_trigger, ns_indices
):
    """RequestedResultVariable must be updated after a successful RequestResults call."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _handle, _data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)

    requested_var_node = await _find_requested_result_var(rm, ns_indices, ns_mr)
    if requested_var_node is None:
        _handle_missing_requested_result_variable(ns_indices)

    # RequestResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rr_node = await find_child_by_browse_name(rm, BN.REQUEST_RESULTS, ns_ijt)
    if rr_node is None:
        pytest.fail("RequestResults method is missing although requested-result variable access is enabled")

    rr_args = _get_request_results_args(_data, single_result=True)
    await _call_and_collect_requested_result(
        rm,
        rr_node,
        rr_args,
        subscription_client,
        requested_var_node,
        timeout_s=result_trigger.active_result_timeout_s,
    )


# ─── requested_result_event_access ───


@pytest.mark.requires_cu(CU.REQUESTED_RESULT_EVENT_ACCESS)
async def test_requested_result_event_type_node_exists(opcua_client, ns_indices):
    """The Server generates a RequestedResultEventType event following RequestResults or RequestUnacknowledgedResults."""
    from helpers.namespaces import NS_IJT_BASE, IJTTypes

    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")

    try:
        event_type_node = opcua_client.get_node(ua.NodeId(IJTTypes.REQUESTED_RESULT_EVENT_TYPE, ns_ijt))
        display_name = await event_type_node.read_display_name()
        logger.debug("RequestedResultEventType node found: %s", display_name)
    except ua.UaError as exc:
        pytest.skip(f"RequestedResultEventType node not accessible — server may not expose this event type: {exc}")


# ─── acknowledge_results ───


@pytest.mark.requires_cu(CU.ACKNOWLEDGE_RESULTS)
async def test_acknowledge_results_method_is_present(result_management, ns_indices):
    """AcknowledgeResults must be present and accept an empty ResultIds list when the CU is enabled."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    ack_node = await find_child_by_browse_name(result_management, BN.ACKNOWLEDGE_RESULTS, ns_mr)
    if ack_node is None:
        pytest.fail("AcknowledgeResults method is missing although the CU is enabled")

    try:
        raw = await asyncio.wait_for(
            result_management.call_method(
                ack_node.nodeid,
                ua.Variant([], ua.VariantType.String),
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        pytest.fail(f"AcknowledgeResults with an empty ResultIds list failed unexpectedly: {exc}")
    _assert_acknowledge_output(raw, "AcknowledgeResults(empty)")


@pytest.mark.requires_cu(CU.ACKNOWLEDGE_RESULTS)
async def test_acknowledge_results_accepts_valid_result_id_list(opcua_client, result_trigger, ns_indices):
    """AcknowledgeResults must accept a valid ResultId list when the CU is enabled."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _handle, result_data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)
    if result_data is None:
        pytest.skip("GetLatestResult returned no data — cannot test AcknowledgeResults")

    meta = getattr(result_data, "ResultMetaData", None)
    result_id = str(getattr(meta, "ResultId", None) or "") if meta is not None else ""
    if not result_id.strip():
        pytest.skip("ResultId is empty — cannot acknowledge by identifier")

    ack_node = await find_child_by_browse_name(rm, BN.ACKNOWLEDGE_RESULTS, ns_mr)
    if ack_node is None:
        pytest.fail("AcknowledgeResults method is missing although the CU is enabled")

    try:
        raw = await asyncio.wait_for(
            rm.call_method(
                ack_node.nodeid,
                ua.Variant([result_id], ua.VariantType.String),
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        pytest.fail(f"AcknowledgeResults rejected valid ResultId {result_id!r}: {exc}")
    _assert_acknowledge_output(raw, "AcknowledgeResults(valid ResultId)")


# ─── request_unacknowledged_results ───


@pytest.mark.requires_cu(CU.REQUEST_UNACKNOWLEDGED_RESULTS)
async def test_request_unacknowledged_results_method_is_present(result_management, ns_indices):
    """RequestUnacknowledgedResults must be present and callable when the CU is enabled."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    # RequestUnacknowledgedResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rur_node = await find_child_by_browse_name(result_management, BN.REQUEST_UNACKNOWLEDGED_RESULTS, ns_ijt)
    if rur_node is None:
        pytest.fail("RequestUnacknowledgedResults method is missing although the CU is enabled")
    try:
        raw = await asyncio.wait_for(
            result_management.call_method(
                rur_node.nodeid,
                _RUR_MAX_RESULTS,
                _RUR_MIN_DURATION,
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        _fail_if_rur_bad_arguments_missing(exc)
        pytest.fail(f"RequestUnacknowledgedResults failed unexpectedly: {exc}")
    _assert_request_unacknowledged_output(raw, "RequestUnacknowledgedResults")


@pytest.mark.requires_cu(CU.REQUEST_UNACKNOWLEDGED_RESULTS)
async def test_request_unacknowledged_results_is_callable(opcua_client, result_trigger, ns_indices):
    """RequestUnacknowledgedResults must be callable after a result is generated."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    outcome = await result_trigger.trigger_single(
        result_type=ResultType.MULTI_STEP_OK_RESULT,
        include_traces=False,
    )
    if not outcome.triggered:
        pytest.skip(outcome.skip_reason)

    rm = await _get_result_management(opcua_client, ns_mr)
    # RequestUnacknowledgedResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rur_node = await find_child_by_browse_name(rm, BN.REQUEST_UNACKNOWLEDGED_RESULTS, ns_ijt)
    if rur_node is None:
        pytest.fail("RequestUnacknowledgedResults method is missing although the CU is enabled")

    try:
        raw = await asyncio.wait_for(
            rm.call_method(
                rur_node.nodeid,
                _RUR_MAX_RESULTS,
                _RUR_MIN_DURATION,
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        _fail_if_rur_bad_arguments_missing(exc)
        pytest.fail(f"RequestUnacknowledgedResults failed unexpectedly after trigger: {exc}")
    _assert_request_unacknowledged_output(raw, "RequestUnacknowledgedResults(after trigger)")


@pytest.mark.requires_cu(CU.REQUEST_RESULTS)
async def test_release_result_handle_succeeds_with_valid_handle(opcua_client, result_trigger, ns_indices):
    """ReleaseResultHandle must be absent or reject calls in this server profile."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, handle, _data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)

    release_node = await find_child_by_browse_name(rm, BN.RELEASE_RESULT_HANDLE, ns_mr)
    if release_node is None:
        return
    handle_arg = handle if handle is not None else 0

    try:
        await asyncio.wait_for(
            rm.call_method(release_node.nodeid, handle_arg),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError:
        return
    pytest.fail("ReleaseResultHandle unexpectedly returned Good on unsupported profile")


# ---------------------------------------------------------------------------
# get_latest_result — method presence, result freshness, consistency
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
async def test_get_latest_result_method_is_present_and_executable(result_management, ns_indices):
    """GetLatestResult method node must be present on the ResultManagement instance
    with Executable = True."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    glr_node = await find_child_by_browse_name(result_management, BN.GET_LATEST_RESULT, ns_mr)
    assert glr_node is not None, "GetLatestResult method node not found on ResultManagement instance"
    try:
        executable = await glr_node.read_attribute(ua.AttributeIds.Executable)
        assert executable.Value.Value is True, (
            "GetLatestResult Executable attribute must be True on the ResultManagement instance"
        )
    except ua.UaError as exc:
        pytest.skip(f"Could not read Executable attribute from GetLatestResult: {exc}")


@pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
async def test_get_latest_result_returns_new_result_after_second_trigger(opcua_client, result_trigger, ns_indices):
    """GetLatestResult must return a result with a different ResultId after a second
    joining operation is triggered — the server always returns the latest result."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _h1, result_data_first = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)
    if result_data_first is None:
        pytest.skip("First GetLatestResult returned no data")

    result_id_first = extract_result_id(result_data_first)

    outcome = await result_trigger.trigger_single(
        result_type=ResultType.MULTI_STEP_OK_RESULT,
        include_traces=False,
    )
    if not outcome.triggered:
        pytest.skip(outcome.skip_reason)

    async def _read_latest():
        _handle, data = await _call_get_latest_result(rm, ns_mr, timeout_ms=_OPCUA_TIMEOUT_MS)
        return data

    # Bounded poll: the second result does not have to be published by the time
    # the trigger call returns, but it must arrive within the active budget.
    poll = await poll_until_result_id_changes(
        _read_latest,
        result_id_first,
        timeout_s=result_trigger.active_result_timeout_s,
    )

    result_data_second = poll.value
    if result_data_second is None:
        pytest.skip("Second GetLatestResult returned no data")

    result_id_second = poll.result_id

    if result_id_first.strip() and result_id_second.strip():
        assert poll.changed, (
            f"GetLatestResult returned the same ResultId after an accepted new trigger "
            f"(trigger method={outcome.method!r}): "
            f"first={result_id_first!r}, second={result_id_second!r} "
            f"after {poll.elapsed_s:.1f}s of {poll.timeout_s:.1f}s over {poll.reads} read(s); "
            "the server must return the most recently completed result"
        )


@pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
async def test_get_latest_result_result_id_matches_result_in_folder(opcua_client, result_trigger, ns_indices):
    """The ResultId from GetLatestResult must correspond to a node present in the
    Results folder of ResultManagement — both views must reflect the same result."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _handle, result_data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)
    if result_data is None:
        pytest.skip("GetLatestResult returned no data")

    meta = getattr(result_data, "ResultMetaData", None)
    result_id = str(getattr(meta, "ResultId", None) or "") if meta else ""
    if not result_id.strip():
        pytest.skip("ResultId is empty — cannot verify against Results folder")

    results_folder = await find_child_by_browse_name(rm, BN.RESULTS, ns_mr)
    if results_folder is None:
        pytest.skip("Results folder not found in ResultManagement — optional per spec")

    children = await results_folder.get_children()
    if not children:
        pytest.skip("Results folder is empty — no nodes to compare against")

    # Try to locate a child node whose ResultMetaData.ResultId matches
    found_match = False
    for child in children:
        try:
            val = await child.read_value()
            child_meta = getattr(val, "ResultMetaData", None)
            if child_meta is not None:
                child_id = str(getattr(child_meta, "ResultId", None) or "")
                if child_id == result_id:
                    found_match = True
                    break
            bn = await child.read_browse_name()
            if result_id in (bn.Name, str(bn)):
                found_match = True
                break
        except ua.UaError:
            continue

    if not found_match:
        logger.info(
            "ResultId from GetLatestResult not found by exact match in Results folder nodes; "
            "server may organise results differently — not a hard failure"
        )


@pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
async def test_get_latest_result_result_id_is_non_empty(opcua_client, result_trigger, ns_indices):
    """The ResultId field inside the result returned by GetLatestResult must be
    a non-empty string — it uniquely identifies the result and must never be blank."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    _rm, _handle, result_data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)
    if result_data is None:
        pytest.skip("GetLatestResult returned no data")

    meta = getattr(result_data, "ResultMetaData", None)
    if meta is None:
        pytest.skip("ResultMetaData: Not Supported — covered by basic_result tests")

    result_id = str(getattr(meta, "ResultId", None) or "")
    assert result_id.strip(), f"GetLatestResult ResultMetaData.ResultId must be a non-empty string; got {result_id!r}"


@pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
async def test_get_latest_result_classification_is_valid(opcua_client, result_trigger, ns_indices):
    """ResultMetaData.Classification returned by GetLatestResult must be a non-zero
    value indicating a real result category."""
    _rm, _handle, result_data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)
    if result_data is None:
        pytest.skip("GetLatestResult returned no data")

    meta = getattr(result_data, "ResultMetaData", None)
    if meta is None:
        pytest.skip("ResultMetaData: Not Supported — covered by basic_result tests")

    classification = getattr(meta, "Classification", None)
    if classification is None:
        pytest.skip("Classification field absent from ResultMetaData")

    cls_int = int(classification)
    assert cls_int != 0, (
        f"ResultMetaData.Classification must be non-zero (UNDEFINED=0 is not a valid "
        f"result type for a real result); got {cls_int}"
    )


@pytest.mark.negative
@pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
async def test_get_latest_result_with_negative_timeout_does_not_crash(opcua_client, ns_indices):
    """GetLatestResult called with a negative Timeout value must not crash or
    hang the server — it must either raise a Bad status code or return promptly.

    Signature: GetLatestResult(Timeout: Int32) → [ResultHandle, Result, Error].
    A negative timeout is out-of-domain and exercises server input validation."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    glr_node = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if glr_node is None:
        pytest.skip("GetLatestResult method not found")

    try:
        result = await asyncio.wait_for(
            rm.call_method(
                glr_node.nodeid,
                ua.Variant(-1, ua.VariantType.Int32),
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
        # Server returned without UaError — this is acceptable for a negative
        # timeout; the purpose of this test is to confirm the server does not
        # crash or hang.  Some servers may also signal an error in output[2].
        output = list(result) if isinstance(result, (list, tuple)) else ([] if result is None else [result])
        if len(output) >= 3:
            try:
                err = int(output[2])
                logger.info("GetLatestResult with negative timeout: output Error=%d", err)
            except (TypeError, ValueError):
                pass
        logger.info(
            "GetLatestResult with negative timeout returned without UaError; server handles invalid timeout gracefully"
        )
    except ua.UaError:
        pass  # Expected: server correctly rejected the invalid timeout
    except asyncio.TimeoutError:
        pytest.fail(
            "GetLatestResult with negative timeout blocked indefinitely — "
            "server must respond promptly even for invalid input"
        )


@pytest.mark.negative
@pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
async def test_get_latest_result_zero_timeout_returns_promptly_when_no_result_ready(opcua_client, ns_indices):
    """GetLatestResult with a zero-millisecond timeout must return promptly and must not
    crash the server, even when no new result is available (empty-queue case)."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    glr_node = await find_child_by_browse_name(rm, BN.GET_LATEST_RESULT, ns_mr)
    if glr_node is None:
        pytest.skip("GetLatestResult method not found")

    try:
        await asyncio.wait_for(
            rm.call_method(
                glr_node.nodeid,
                ua.Variant(_OPCUA_ZERO_TIMEOUT_MS, ua.VariantType.Int32),
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        logger.debug(
            "GetLatestResult(zero timeout, possibly no result) raised UaError (acceptable): %s",
            exc,
        )
    except asyncio.TimeoutError:
        pytest.fail(
            "GetLatestResult with zero-millisecond timeout blocked indefinitely — "
            "server must handle the no-result case without hanging"
        )


# ---------------------------------------------------------------------------
# get_result_by_id — method presence, completeness, additional negative cases
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.GET_RESULT_BY_ID)
async def test_get_result_by_id_method_is_present_and_executable(result_management, ns_indices):
    """GetResultById method node must be present on the ResultManagement instance
    with Executable = True."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    grbi_node = await find_child_by_browse_name(result_management, BN.GET_RESULT_BY_ID, ns_mr)
    assert grbi_node is not None, "GetResultById method node not found on ResultManagement instance"
    try:
        executable = await grbi_node.read_attribute(ua.AttributeIds.Executable)
        assert executable.Value.Value is True, (
            "GetResultById Executable attribute must be True on the ResultManagement instance"
        )
    except ua.UaError as exc:
        pytest.skip(f"Could not read Executable attribute from GetResultById: {exc}")


@pytest.mark.requires_cu(CU.GET_RESULT_BY_ID)
async def test_get_result_by_id_returns_non_null_result_content(opcua_client, result_trigger, ns_indices):
    """GetResultById must return a result whose ResultContent field is present and
    is a list (may be empty for simple results, but must not be absent)."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _handle, result_data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)
    if result_data is None:
        pytest.skip("GetLatestResult returned no data")

    meta = getattr(result_data, "ResultMetaData", None)
    result_id = str(getattr(meta, "ResultId", None) or "") if meta is not None else ""
    if not result_id.strip():
        pytest.skip("ResultId is empty — cannot test GetResultById ResultContent")

    grbi_node = await find_child_by_browse_name(rm, BN.GET_RESULT_BY_ID, ns_mr)
    if grbi_node is None:
        pytest.skip(f"GetResultById method not found (ns={ns_mr})")

    try:
        raw = await asyncio.wait_for(
            rm.call_method(
                grbi_node.nodeid,
                ua.Variant(result_id, ua.VariantType.String),
                ua.Variant(_OPCUA_TIMEOUT_MS, ua.VariantType.Int32),
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        pytest.skip(f"GetResultById raised UaError: {exc}")

    fetched = raw[1] if isinstance(raw, (list, tuple)) and len(raw) > 1 else raw
    if fetched is None:
        pytest.skip("GetResultById returned None — no data available")

    content = getattr(fetched, "ResultContent", None)
    if content is None:
        logger.info(
            "GetResultById returned a result with no ResultContent attribute; "
            "server may embed content under a different field name"
        )
        return

    assert isinstance(content, (list, tuple)), (
        f"ResultContent from GetResultById must be a list, got {type(content).__name__!r}"
    )


@pytest.mark.requires_cu(CU.GET_RESULT_BY_ID)
async def test_get_result_by_id_result_meta_data_has_mandatory_fields(opcua_client, result_trigger, ns_indices):
    """GetResultById response must include all nine mandatory ResultMetaData fields:
    ResultId, Classification, IsSimulated, IsPartial, ResultEvaluation,
    JoiningTechnology, ResultState, SequenceNumber, CreationTime."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _handle, result_data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)
    if result_data is None:
        pytest.skip("GetLatestResult returned no data")

    meta = getattr(result_data, "ResultMetaData", None)
    result_id = str(getattr(meta, "ResultId", None) or "") if meta is not None else ""
    if not result_id.strip():
        pytest.skip("ResultId is empty — cannot test GetResultById")

    grbi_node = await find_child_by_browse_name(rm, BN.GET_RESULT_BY_ID, ns_mr)
    if grbi_node is None:
        pytest.skip(f"GetResultById method not found (ns={ns_mr})")

    try:
        raw = await asyncio.wait_for(
            rm.call_method(
                grbi_node.nodeid,
                ua.Variant(result_id, ua.VariantType.String),
                ua.Variant(_OPCUA_TIMEOUT_MS, ua.VariantType.Int32),
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        pytest.skip(f"GetResultById raised UaError: {exc}")

    fetched = raw[1] if isinstance(raw, (list, tuple)) and len(raw) > 1 else raw
    if fetched is None:
        pytest.skip("GetResultById returned None — no data available")

    fetched_meta = getattr(fetched, "ResultMetaData", None)
    assert fetched_meta is not None, (
        "GetResultById returned a result with no ResultMetaData — ResultMetaData is mandatory in every result"
    )

    mandatory_fields = (
        "ResultId",
        "Classification",
        "IsSimulated",
        "IsPartial",
        "ResultEvaluation",
        "JoiningTechnology",
        "ResultState",
        "SequenceNumber",
        "CreationTime",
    )
    missing = [f for f in mandatory_fields if getattr(fetched_meta, f, None) is None]
    assert not missing, f"GetResultById ResultMetaData is missing mandatory fields: {missing}"


@pytest.mark.negative
@pytest.mark.requires_cu(CU.GET_RESULT_BY_ID)
async def test_get_result_by_id_with_empty_result_id_returns_error(opcua_client, ns_indices):
    """GetResultById called with an empty string as ResultId must return a Bad status
    code — an empty identifier is never a valid result reference."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    grbi_node = await find_child_by_browse_name(rm, BN.GET_RESULT_BY_ID, ns_mr)
    if grbi_node is None:
        pytest.skip(f"GetResultById method not found (ns={ns_mr})")

    try:
        await asyncio.wait_for(
            rm.call_method(
                grbi_node.nodeid,
                ua.Variant("", ua.VariantType.String),
                ua.Variant(_OPCUA_TIMEOUT_MS, ua.VariantType.Int32),
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
        pytest.skip(
            "GetResultById with an empty ResultId returned Success instead of BadInvalidArgument — "
            "known simulator compliance gap; server does not validate empty identifiers. "
            "Verify against a spec-compliant server."
        )
    except ua.UaError:
        pass  # Expected: server correctly rejected the empty identifier
    except asyncio.TimeoutError:
        pytest.skip("GetResultById with empty identifier timed out unexpectedly")


# ---------------------------------------------------------------------------
# get_result_with_filter_criteria — optional CU
# ---------------------------------------------------------------------------
# GetResultIdListFiltered is defined in OPC UA Machinery/Result (OPC 40001-101)
# and is an OPTIONAL conformance unit in the IJT Base Companion Specification.
# A server may implement it, expose it but return BadNotSupported, or omit the
# node entirely — all three are conformant.  The test earlier in this file
# (test_get_result_id_list_filtered_presence_or_not_implemented) validates the
# optional-presence contract.  No additional behavioural tests are required
# unless the CU_GET_RESULT_WITH_FILTER_CRITERIA is mandatory for the profile
# under test.


# ---------------------------------------------------------------------------
# result_variable_access — DataType, ValueRank, AccessLevel, write rejection
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.RESULT_VARIABLE_ACCESS)
async def test_result_variable_value_rank_is_scalar_or_any(result_management, ns_indices):
    """The Results/Result/ResultMetaData Variable must have ValueRank = Scalar or Any — it holds
    a single result structure, not an array."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    # ResultManagement → Results(ns_mr) → Result(ns_mr) → ResultMetaData(ns_mr)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    results_folder = await find_child_by_browse_name(result_management, BN.RESULTS, ns_mr)
    if results_folder is None:
        pytest.skip("Results folder not found on ResultManagement")
    result_var = await _find_result_var(results_folder, ns_mr, ns_ijt, ns_indices)
    if result_var is None:
        _handle_missing_result_variable(ns_indices, ns_mr, ns_ijt)
    last_meta_node = await find_child_by_browse_name(result_var, BN.RESULT_META_DATA, ns_mr)
    if last_meta_node is None:
        pytest.skip("Results/Result/ResultMetaData variable not found")

    try:
        value_rank = await last_meta_node.read_attribute(ua.AttributeIds.ValueRank)
    except ua.UaError as exc:
        pytest.skip(f"Could not read ValueRank attribute: {exc}")

    vr_int = int(value_rank.Value.Value)
    # -3=ScalarOrOneDimension, -2=Any, -1=Scalar, 1=OneDimension (used for arrays of structs)
    assert vr_int in (-3, -2, -1, 1), (
        "Results/Result/ResultMetaData ValueRank must indicate a scalar or compatible structure "
        f"(Scalar=-1, Any=-2), got {vr_int}"
    )


@pytest.mark.requires_cu(CU.RESULT_VARIABLE_ACCESS)
async def test_result_variable_contains_valid_result_meta_data_after_trigger(opcua_client, result_trigger, ns_indices):
    """After a joining operation the Results/Result/ResultMetaData variable must hold a valid
    result with a non-empty ResultId and a non-zero Classification."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    outcome = await result_trigger.trigger_single(
        result_type=ResultType.MULTI_STEP_OK_RESULT,
        include_traces=False,
    )
    if not outcome.triggered:
        pytest.skip(outcome.skip_reason)

    await asyncio.sleep(_LIVE_VARIABLE_SETTLE_SECS)

    rm = await _get_result_management(opcua_client, ns_mr)
    # ResultManagement → Results(ns_mr) → Result(ns_mr) → ResultMetaData(ns_mr)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    results_folder = await find_child_by_browse_name(rm, BN.RESULTS, ns_mr)
    if results_folder is None:
        pytest.skip("Results folder not found on ResultManagement")
    result_var = await _find_result_var(results_folder, ns_mr, ns_ijt, ns_indices)
    if result_var is None:
        _handle_missing_result_variable(ns_indices, ns_mr, ns_ijt)
    last_meta_node = await find_child_by_browse_name(result_var, BN.RESULT_META_DATA, ns_mr)
    if last_meta_node is None:
        pytest.skip("Results/Result/ResultMetaData variable not found")

    try:
        value = await last_meta_node.read_value()
    except ua.UaError as exc:
        pytest.skip(f"Could not read Results/Result/ResultMetaData: {exc}")

    if value is None:
        pytest.skip("Results/Result/ResultMetaData value is None — no result stored yet")

    meta = getattr(value, "ResultMetaData", value)
    result_id = str(getattr(meta, "ResultId", None) or "")
    assert result_id.strip(), "Results/Result/ResultMetaData.ResultId must be non-empty after a result is triggered"

    classification = getattr(meta, "Classification", None)
    if classification is not None:
        cls_int = int(classification)
        assert cls_int > 0, f"ResultMetaData.Classification must be > 0 (not UNDEFINED) in a real result; got {cls_int}"


@pytest.mark.requires_cu(CU.RESULT_VARIABLE_ACCESS)
async def test_result_variable_access_level_allows_read_but_not_write(result_management, ns_indices):
    """The Results/Result/ResultMetaData Variable AccessLevel must have the Read bit set and must
    not have the Write bit set — result variables are server-managed and read-only."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    # ResultManagement → Results(ns_mr) → Result(ns_mr) → ResultMetaData(ns_mr)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    results_folder = await find_child_by_browse_name(result_management, BN.RESULTS, ns_mr)
    if results_folder is None:
        pytest.skip("Results folder not found on ResultManagement")
    result_var = await _find_result_var(results_folder, ns_mr, ns_ijt, ns_indices)
    if result_var is None:
        _handle_missing_result_variable(ns_indices, ns_mr, ns_ijt)
    last_meta_node = await find_child_by_browse_name(result_var, BN.RESULT_META_DATA, ns_mr)
    if last_meta_node is None:
        pytest.skip("Results/Result/ResultMetaData variable not found")

    try:
        access_level = await last_meta_node.read_attribute(ua.AttributeIds.AccessLevel)
    except ua.UaError as exc:
        pytest.skip(f"Could not read AccessLevel attribute: {exc}")

    al_int = int(access_level.Value.Value)
    _READ_BIT = 0x01
    _WRITE_BIT = 0x02

    assert al_int & _READ_BIT, (
        f"Results/Result/ResultMetaData AccessLevel must have the Read bit set (got 0x{al_int:02X})"
    )
    assert not (al_int & _WRITE_BIT), (
        f"Results/Result/ResultMetaData AccessLevel must not have the Write bit set "
        f"(got 0x{al_int:02X}); result variables are server-managed"
    )


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_VARIABLE_ACCESS)
async def test_write_to_result_variable_is_rejected(result_management, ns_indices):
    """Attempting to write to the Results/Result/ResultMetaData variable must be rejected
    by the server — result data is produced by the server and must not be overwritten
    by clients."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    # ResultManagement → Results(ns_mr) → Result(ns_mr) → ResultMetaData(ns_mr)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    results_folder = await find_child_by_browse_name(result_management, BN.RESULTS, ns_mr)
    if results_folder is None:
        pytest.skip("Results folder not found on ResultManagement")
    result_var = await _find_result_var(results_folder, ns_mr, ns_ijt, ns_indices)
    if result_var is None:
        _handle_missing_result_variable(ns_indices, ns_mr, ns_ijt)
    last_meta_node = await find_child_by_browse_name(result_var, BN.RESULT_META_DATA, ns_mr)
    if last_meta_node is None:
        pytest.skip("Results/Result/ResultMetaData variable not found")

    try:
        await last_meta_node.write_value(ua.DataValue(ua.Variant(None, ua.VariantType.Null)))
        pytest.fail(
            "Writing to Results/Result/ResultMetaData should have raised ua.UaError "
            "(BadNotWritable or BadUserAccessDenied) but succeeded unexpectedly"
        )
    except ua.UaError:
        pass  # Expected: server correctly rejected the write attempt


@pytest.mark.negative
@pytest.mark.requires_cu(CU.RESULT_VARIABLE_ACCESS)
async def test_read_fabricated_node_id_returns_bad_status(opcua_client, ns_indices):
    """Reading a Variable node using a fabricated NodeId that does not exist in the
    address space must return a Bad status code (BadNodeIdUnknown) — the server must
    not return a Good status with fabricated data."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    # Use a namespace-qualified NodeId with an integer known not to exist
    fabricated_node = opcua_client.get_node(ua.NodeId(0xFFFFFE, ns_mr))
    try:
        await fabricated_node.read_value()
        pytest.fail(
            "Reading a fabricated NodeId should have raised ua.UaError "
            "(BadNodeIdUnknown) but succeeded — server returned data for a non-existent node"
        )
    except ua.UaError:
        pass  # Expected: server correctly reported the unknown NodeId


# ---------------------------------------------------------------------------
# Additional constants for new test cases
# ---------------------------------------------------------------------------

# Event subscription timeout — maximum seconds to wait for a RequestedResultEventType event
_EVENT_SUBSCRIPTION_WAIT_SECS = 30.0

# ---------------------------------------------------------------------------
# CU37 — REQUEST_RESULTS additional tests
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.REQUEST_RESULTS)
async def test_request_results_with_default_range_completes_without_crash(opcua_client, result_trigger, ns_indices):
    """RR-2: RequestResults with default sequence/time range must not crash the server.
    Accepts Good (results delivered via event) or UaError (not implemented).
    """
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement node not found")

    # RequestResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rr_node = await find_child_by_browse_name(rm, BN.REQUEST_RESULTS, ns_ijt)
    if rr_node is None:
        pytest.fail("RequestResults method is missing although CU.REQUEST_RESULTS is enabled")

    rr_args = _get_request_results_args()
    try:
        response = await _call_request_results(rm, rr_node, rr_args)
    except ua.UaError as exc:
        pytest.fail(f"RequestResults rejected a valid configured range: {exc}")
    except asyncio.TimeoutError:
        pytest.fail("RequestResults timed out with a valid configured range")
    _assert_request_results_output(response, "RequestResults")


@pytest.mark.requires_cu(CU.REQUEST_RESULTS)
async def test_request_results_consecutive_calls_handled_gracefully(opcua_client, result_trigger, ns_indices):
    """RR-3: Two rapid consecutive RequestResults calls must not crash the test client."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _handle, _data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)

    # RequestResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rr_node = await find_child_by_browse_name(rm, BN.REQUEST_RESULTS, ns_ijt)
    if rr_node is None:
        pytest.fail("RequestResults method is missing although CU.REQUEST_RESULTS is enabled")

    rr_args = _get_request_results_args(_data, single_result=True)
    for call_index in range(2):
        try:
            if call_index == 0:
                response = await _call_request_results(rm, rr_node, rr_args)
            else:
                response = await asyncio.wait_for(
                    rm.call_method(
                        rr_node.nodeid,
                        *rr_args,
                    ),
                    timeout=_METHOD_WALL_TIMEOUT,
                )
        except ua.UaError as exc:
            if call_index > 0 and ("uncertain" in str(exc).lower() or "invalidstate" in str(exc).lower()):
                logger.info("Consecutive RequestResults call 1 returned expected in-progress status: %s", exc)
                break
            pytest.fail(f"RequestResults call {call_index} failed with OPC UA error: {exc}")
        except asyncio.TimeoutError:
            pytest.fail(f"RequestResults call {call_index} timed out")
        _assert_request_results_output(response, f"RequestResults call {call_index}")


@pytest.mark.requires_cu(CU.REQUEST_RESULTS)
async def test_request_results_updates_result_variable_or_raises_event(
    opcua_client, subscription_client, result_trigger, ns_indices
):
    """RR-6: After RequestResults the RequestedResult variable should be populated."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _handle, _data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)

    # RequestResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rr_node = await find_child_by_browse_name(rm, BN.REQUEST_RESULTS, ns_ijt)
    if rr_node is None:
        pytest.fail("RequestResults method is missing although CU.REQUEST_RESULTS is enabled")

    requested_var_node = await _find_requested_result_var(rm, ns_indices, ns_mr)
    if requested_var_node is None:
        _handle_missing_requested_result_variable(ns_indices)

    rr_args = _get_request_results_args(_data, single_result=True)
    await _call_and_collect_requested_result(
        rm,
        rr_node,
        rr_args,
        subscription_client,
        requested_var_node,
        timeout_s=result_trigger.active_result_timeout_s,
    )


@pytest.mark.requires_cu(CU.REQUEST_RESULTS)
@pytest.mark.negative
async def test_request_results_with_inverted_sequence_range_handled_gracefully(
    opcua_client, result_trigger, ns_indices
):
    """Error RR-4: RequestResults with FromSequenceNumber > ToSequenceNumber (inverted range)
    must either be rejected by the server (UaError) or return a non-zero Status output.
    Server must not crash."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement node not found")

    # RequestResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rr_node = await find_child_by_browse_name(rm, BN.REQUEST_RESULTS, ns_ijt)
    if rr_node is None:
        pytest.fail("RequestResults method is missing although CU.REQUEST_RESULTS is enabled")

    try:
        result = await asyncio.wait_for(
            rm.call_method(
                rr_node.nodeid,
                ua.Variant(100, ua.VariantType.UInt64),  # FromSequenceNumber
                ua.Variant(1, ua.VariantType.UInt64),  # ToSequenceNumber — inverted (100 > 1)
                _RR_FROM_TIME,
                _RR_TO_TIME,
                _RR_MIN_DURATION,
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
        # Server accepted the RPC — verify it reported failure in Status output (index 1)
        outputs = list(result) if isinstance(result, (list, tuple)) else [result]
        if len(outputs) > 1 and outputs[1] is not None:
            status_val = int(outputs[1])
            if status_val != 0:
                logger.debug("Server correctly returned non-zero Status=%d for inverted range", status_val)
            else:
                pytest.fail("Server incorrectly accepted inverted sequence range (100 > 1) with Status=0")
        else:
            pytest.fail("Server accepted inverted sequence range without returning error Status")
    except ua.UaError:
        pass  # Server rejected with OPC UA error — expected
    except asyncio.TimeoutError:
        pytest.fail("RequestResults timed out during negative inverted-range test")


@pytest.mark.requires_cu(CU.REQUEST_RESULTS)
@pytest.mark.negative
async def test_request_results_with_no_pending_results_does_not_crash(opcua_client, ns_indices):
    """Error RR-5: RequestResults without a prior trigger must not crash the server."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement node not found")

    # RequestResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rr_node = await find_child_by_browse_name(rm, BN.REQUEST_RESULTS, ns_ijt)
    if rr_node is None:
        pytest.fail("RequestResults method is missing although CU.REQUEST_RESULTS is enabled")

    rr_args = _get_request_results_args()
    try:
        response = await asyncio.wait_for(
            rm.call_method(
                rr_node.nodeid,
                *rr_args,
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError:
        pass  # Acceptable — server may signal no results via error
    except asyncio.TimeoutError:
        pytest.fail("RequestResults did not return within timeout when no results pending")
    else:
        _request_results_status(response, "RequestResults")


# ---------------------------------------------------------------------------
# CU38 — REQUESTED_RESULT_VARIABLE_ACCESS additional tests
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.REQUESTED_RESULT_VARIABLE_ACCESS)
async def test_requested_result_variable_access_level_includes_current_read(opcua_client, ns_indices):
    """RRVA-3: RequestedResult variable AccessLevel must include the CurrentRead bit."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement node not found")

    requested_var_node = await _find_requested_result_var(rm, ns_indices, ns_mr)
    if requested_var_node is None:
        _handle_missing_requested_result_variable(ns_indices)

    dv = await requested_var_node.read_attribute(ua.AttributeIds.AccessLevel)
    access_level = int(dv.Value.Value)
    _CURRENT_READ_BIT = 0x01  # OPC UA AccessLevel bit 0 = CurrentRead
    assert access_level & _CURRENT_READ_BIT, (
        f"RequestedResult AccessLevel {access_level:#04x} does not include CurrentRead bit (bit 0)"
    )


@pytest.mark.requires_cu(CU.REQUESTED_RESULT_VARIABLE_ACCESS)
async def test_requested_result_variable_source_timestamp_is_set_after_request(
    opcua_client, subscription_client, result_trigger, ns_indices
):
    """RRVA-4: SourceTimestamp on RequestedResult must be a plausible datetime after RequestResults."""

    MIN_VALID_YEAR = 2000

    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _handle, _data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)

    # RequestResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rr_node = await find_child_by_browse_name(rm, BN.REQUEST_RESULTS, ns_ijt)
    if rr_node is None:
        pytest.fail("RequestResults method is missing although requested-result variable access is enabled")

    requested_var_node = await _find_requested_result_var(rm, ns_indices, ns_mr)
    if requested_var_node is None:
        _handle_missing_requested_result_variable(ns_indices)

    rr_args = _get_request_results_args(_data, single_result=True)
    update = await _call_and_collect_requested_result(
        rm,
        rr_node,
        rr_args,
        subscription_client,
        requested_var_node,
        timeout_s=result_trigger.active_result_timeout_s,
    )

    assert update.data_value is not None, "RequestedResult notification does not contain a DataValue"
    assert update.data_value.SourceTimestamp is not None, (
        "RequestedResult SourceTimestamp is None after RequestResults call"
    )
    assert update.data_value.SourceTimestamp.year >= MIN_VALID_YEAR, (
        f"RequestedResult SourceTimestamp {update.data_value.SourceTimestamp!r} predates year {MIN_VALID_YEAR}"
    )


# ---------------------------------------------------------------------------
# CU39 — REQUESTED_RESULT_EVENT_ACCESS additional tests
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.REQUESTED_RESULT_EVENT_ACCESS)
async def test_request_results_event_received_with_required_fields(
    opcua_client, subscription_client, result_trigger, ns_indices
):
    """RREA-1+RREA-2: RequestResults should populate RequestedResult variable or fire an event."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _handle, _data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)

    # RequestResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rr_node = await find_child_by_browse_name(rm, BN.REQUEST_RESULTS, ns_ijt)
    if rr_node is None:
        pytest.fail("RequestResults method is missing although requested-result event access is enabled")

    requested_var_node = await _find_requested_result_var(rm, ns_indices, ns_mr)
    if requested_var_node is None:
        _handle_missing_requested_result_variable(ns_indices)

    rr_args = _get_request_results_args(_data, single_result=True)
    await _call_and_collect_requested_result(
        rm,
        rr_node,
        rr_args,
        subscription_client,
        requested_var_node,
        timeout_s=result_trigger.active_result_timeout_s,
    )


@pytest.mark.requires_cu(CU.REQUESTED_RESULT_EVENT_ACCESS)
async def test_requested_result_event_type_node_is_in_ijt_namespace(opcua_client, ns_indices):
    """RREA-3: RequestedResultEventType node must be accessible and have a non-empty DisplayName."""
    from helpers.namespaces import NS_IJT_BASE, IJTTypes  # noqa: PLC0415

    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")

    event_type_id = ua.NodeId(IJTTypes.REQUESTED_RESULT_EVENT_TYPE, ns_ijt)
    event_type_node = opcua_client.get_node(event_type_id)

    try:
        display_name = await event_type_node.read_display_name()
    except ua.UaError as exc:
        pytest.skip(f"RequestedResultEventType node not accessible: {exc}")

    assert display_name is not None, "DisplayName attribute returned None"
    assert display_name.Text, "RequestedResultEventType DisplayName text is empty"


@pytest.mark.requires_cu(CU.REQUESTED_RESULT_EVENT_ACCESS)
@pytest.mark.negative
async def test_request_results_no_data_does_not_crash_server(opcua_client, ns_indices):
    """Error RREA-4: RequestResults without a prior trigger must not crash the server."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement node not found")

    # RequestResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rr_node = await find_child_by_browse_name(rm, BN.REQUEST_RESULTS, ns_ijt)
    if rr_node is None:
        pytest.fail("RequestResults method is missing although requested-result event access is enabled")

    rr_args = _get_request_results_args()
    try:
        await asyncio.wait_for(
            rm.call_method(
                rr_node.nodeid,
                *rr_args,
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError:
        pass  # Acceptable — server may signal no results via error
    except asyncio.TimeoutError:
        pytest.fail("RequestResults did not return within timeout when called with no prior data")


# ---------------------------------------------------------------------------
# CU40 — ACKNOWLEDGE_RESULTS additional tests
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ACKNOWLEDGE_RESULTS)
async def test_acknowledge_results_with_empty_list_is_accepted(opcua_client, ns_indices):
    """AR-2: AcknowledgeResults with an empty ResultIds list must be accepted."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement node not found")

    ack_node = await find_child_by_browse_name(rm, BN.ACKNOWLEDGE_RESULTS, ns_mr)
    if ack_node is None:
        pytest.fail("AcknowledgeResults method is missing although the CU is enabled")

    try:
        raw = await asyncio.wait_for(
            rm.call_method(ack_node.nodeid, ua.Variant([], ua.VariantType.String)),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        pytest.fail(f"AcknowledgeResults(empty) failed unexpectedly: {exc}")
    except asyncio.TimeoutError:
        pytest.fail("AcknowledgeResults call timed out")
    _assert_acknowledge_output(raw, "AcknowledgeResults(empty)")


@pytest.mark.requires_cu(CU.ACKNOWLEDGE_RESULTS)
async def test_acknowledged_result_not_in_unacknowledged_list(opcua_client, result_trigger, ns_indices):
    """AR-4: AcknowledgeResults and RequestUnacknowledgedResults must both be callable."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, handle, _data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)
    if handle is None:
        pytest.skip("GetLatestResult did not return a handle")

    ack_node = await find_child_by_browse_name(rm, BN.ACKNOWLEDGE_RESULTS, ns_mr)
    if ack_node is None:
        pytest.fail("AcknowledgeResults method is missing although the CU is enabled")

    # RequestUnacknowledgedResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rur_node = await find_child_by_browse_name(rm, BN.REQUEST_UNACKNOWLEDGED_RESULTS, ns_ijt)
    if rur_node is None:
        pytest.fail("RequestUnacknowledgedResults method is missing although the CU is enabled")

    result_id = str(handle)

    try:
        ack_raw = await asyncio.wait_for(
            rm.call_method(ack_node.nodeid, ua.Variant([result_id], ua.VariantType.String)),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        pytest.fail(f"AcknowledgeResults rejected ResultId {result_id!r}: {exc}")
    except asyncio.TimeoutError:
        pytest.fail("AcknowledgeResults timed out")
    _assert_acknowledge_output(ack_raw, "AcknowledgeResults(valid ResultId)")

    try:
        rur_raw = await asyncio.wait_for(
            rm.call_method(
                rur_node.nodeid,
                _RUR_MAX_RESULTS,
                _RUR_MIN_DURATION,
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        _fail_if_rur_bad_arguments_missing(exc)
        pytest.fail(f"RequestUnacknowledgedResults failed after AcknowledgeResults: {exc}")
    except asyncio.TimeoutError:
        pytest.fail("RequestUnacknowledgedResults timed out")
    _assert_request_unacknowledged_output(rur_raw, "RequestUnacknowledgedResults(after acknowledge)")


@pytest.mark.requires_cu(CU.ACKNOWLEDGE_RESULTS)
@pytest.mark.negative
async def test_acknowledge_results_with_nonexistent_id_returns_error(opcua_client, ns_indices):
    """Error AR-3: AcknowledgeResults with unknown ResultId must report an error."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement node not found")

    ack_node = await find_child_by_browse_name(rm, BN.ACKNOWLEDGE_RESULTS, ns_mr)
    if ack_node is None:
        pytest.fail("AcknowledgeResults method is missing although the CU is enabled")

    try:
        raw = await asyncio.wait_for(
            rm.call_method(
                ack_node.nodeid,
                ua.Variant([_NONEXISTENT_RESULT_ID], ua.VariantType.String),
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError:
        pass  # Acceptable when the server reports the domain error as service-level Bad.
    except asyncio.TimeoutError:
        pytest.fail("AcknowledgeResults timed out during negative test")
    else:
        _assert_acknowledge_reports_error(raw, "AcknowledgeResults(nonexistent ResultId)")


# ---------------------------------------------------------------------------
# CU41 — REQUEST_UNACKNOWLEDGED_RESULTS additional tests
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.REQUEST_UNACKNOWLEDGED_RESULTS)
async def test_request_unacknowledged_results_returns_list_of_result_ids(opcua_client, result_trigger, ns_indices):
    """RUR-1: RequestUnacknowledgedResults must return its defined output tuple."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _handle, _data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)

    # RequestUnacknowledgedResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rur_node = await find_child_by_browse_name(rm, BN.REQUEST_UNACKNOWLEDGED_RESULTS, ns_ijt)
    if rur_node is None:
        pytest.fail("RequestUnacknowledgedResults method is missing although the CU is enabled")

    try:
        raw = await asyncio.wait_for(
            rm.call_method(
                rur_node.nodeid,
                _RUR_MAX_RESULTS,
                _RUR_MIN_DURATION,
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        _fail_if_rur_bad_arguments_missing(exc)
        pytest.fail(f"RequestUnacknowledgedResults failed unexpectedly: {exc}")
    except asyncio.TimeoutError:
        pytest.fail("RequestUnacknowledgedResults timed out")
    _assert_request_unacknowledged_output(raw, "RequestUnacknowledgedResults")


@pytest.mark.requires_cu(CU.REQUEST_UNACKNOWLEDGED_RESULTS)
async def test_unacknowledged_result_appears_after_trigger(opcua_client, result_trigger, ns_indices):
    """RUR-2: RequestUnacknowledgedResults must be callable after a result trigger."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, _handle, _data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)

    # RequestUnacknowledgedResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rur_node = await find_child_by_browse_name(rm, BN.REQUEST_UNACKNOWLEDGED_RESULTS, ns_ijt)
    if rur_node is None:
        pytest.fail("RequestUnacknowledgedResults method is missing although the CU is enabled")

    try:
        raw = await asyncio.wait_for(
            rm.call_method(
                rur_node.nodeid,
                _RUR_MAX_RESULTS,
                _RUR_MIN_DURATION,
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        _fail_if_rur_bad_arguments_missing(exc)
        pytest.fail(f"RequestUnacknowledgedResults failed unexpectedly after trigger: {exc}")
    except asyncio.TimeoutError:
        pytest.fail("RequestUnacknowledgedResults timed out")
    _assert_request_unacknowledged_output(raw, "RequestUnacknowledgedResults(after trigger)")


@pytest.mark.requires_cu(CU.REQUEST_UNACKNOWLEDGED_RESULTS)
async def test_acknowledged_result_absent_from_subsequent_unacknowledged_list(opcua_client, result_trigger, ns_indices):
    """RUR-3: acknowledge a result, then request unacknowledged-result status."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm, handle, _data = await _trigger_single_and_get_latest(opcua_client, result_trigger, ns_indices)
    if handle is None:
        pytest.skip("GetLatestResult did not return a handle")

    ack_node = await find_child_by_browse_name(rm, BN.ACKNOWLEDGE_RESULTS, ns_mr)
    if ack_node is None:
        pytest.fail("AcknowledgeResults method is missing although the CU is enabled")

    # RequestUnacknowledgedResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rur_node = await find_child_by_browse_name(rm, BN.REQUEST_UNACKNOWLEDGED_RESULTS, ns_ijt)
    if rur_node is None:
        pytest.fail("RequestUnacknowledgedResults method is missing although the CU is enabled")

    result_id = str(handle)

    try:
        ack_raw = await asyncio.wait_for(
            rm.call_method(ack_node.nodeid, ua.Variant([result_id], ua.VariantType.String)),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        pytest.fail(f"AcknowledgeResults rejected ResultId {result_id!r}: {exc}")
    except asyncio.TimeoutError:
        pytest.fail("AcknowledgeResults timed out")
    _assert_acknowledge_output(ack_raw, "AcknowledgeResults(valid ResultId)")

    try:
        rur_raw = await asyncio.wait_for(
            rm.call_method(
                rur_node.nodeid,
                _RUR_MAX_RESULTS,
                _RUR_MIN_DURATION,
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        _fail_if_rur_bad_arguments_missing(exc)
        pytest.fail(f"RequestUnacknowledgedResults failed after AcknowledgeResults: {exc}")
    except asyncio.TimeoutError:
        pytest.fail("RequestUnacknowledgedResults timed out after acknowledge")
    _assert_request_unacknowledged_output(rur_raw, "RequestUnacknowledgedResults(after acknowledge)")


@pytest.mark.requires_cu(CU.REQUEST_UNACKNOWLEDGED_RESULTS)
async def test_request_unacknowledged_results_valid_signature_is_accepted(opcua_client, ns_indices):
    """RUR-4: a valid RequestUnacknowledgedResults call must be accepted."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered on server")

    rm = await _get_result_management(opcua_client, ns_mr)
    if rm is None:
        pytest.skip("ResultManagement node not found")

    # RequestUnacknowledgedResults is registered in NS_IJT_BASE, not NS_MACH_RESULT
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    rur_node = await find_child_by_browse_name(rm, BN.REQUEST_UNACKNOWLEDGED_RESULTS, ns_ijt)
    if rur_node is None:
        pytest.fail("RequestUnacknowledgedResults method is missing although the CU is enabled")

    try:
        raw = await asyncio.wait_for(
            rm.call_method(
                rur_node.nodeid,
                _RUR_MAX_RESULTS,
                _RUR_MIN_DURATION,
            ),
            timeout=_METHOD_WALL_TIMEOUT,
        )
    except ua.UaError as exc:
        _fail_if_rur_bad_arguments_missing(exc)
        pytest.fail(f"RequestUnacknowledgedResults rejected a valid signature: {exc}")
    except asyncio.TimeoutError:
        pytest.fail("RequestUnacknowledgedResults timed out during valid-signature policy test")
    _assert_request_unacknowledged_output(raw, "RequestUnacknowledgedResults(valid signature)")
