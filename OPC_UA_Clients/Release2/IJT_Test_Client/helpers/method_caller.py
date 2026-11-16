"""
helpers/method_caller.py — Reusable OPC UA method call helpers.

Design goals:
  - All method calls are wrapped in asyncio.wait_for with configurable timeout.
  - Provides both positive (call_method) and negative (call_method_expect_bad_status) variants.
  - Status code helpers for IJT-relevant error classification.
  - All calls log at DEBUG level for traceability.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from asyncua import ua

from helpers.node_discovery import find_child_by_browse_name

logger = logging.getLogger(__name__)

_TARGET_STATE_CHANGING_METHODS = frozenset(
    {
        "AbortJoiningProcess",
        "Acknowledge",
        "AcknowledgeResults",
        "Confirm",
        "DecrementJoiningProcessCounter",
        "DeleteJoint",
        "DeleteJointComponent",
        "DeleteJointDesign",
        "DeleteJoiningProcess",
        "DeselectJoiningProcess",
        "DisconnectAsset",
        "EnableAsset",
        "ExecuteOperation",
        "IncrementJoiningProcessCounter",
        "RebootAsset",
        "Reset",
        "ResetErrors",
        "ResetIdentifiers",
        "ResetJoiningProcess",
        "SelectJoiningProcess",
        "SelectJoint",
        "SendFeedback",
        "SendIdentifiers",
        "SendJoint",
        "SendJointComponent",
        "SendJointDesign",
        "SendJoiningProcess",
        "SendTextIdentifiers",
        "SetCalibration",
        "SetIOSignals",
        "SetJoiningProcessCounter",
        "SetJoiningProcessMapping",
        "SetJoiningProcessSize",
        "SetOfflineTimer",
        "SetTime",
        "StartJoiningProcess",
        "StartSelectedJoining",
    }
)
_TARGET_METHOD_CALL_AUTHORIZED: ContextVar[bool] = ContextVar(
    "target_method_call_authorized",
    default=False,
)


def is_target_method_call_authorized() -> bool:
    """Return whether the current async context owns an authorized workflow call."""
    return _TARGET_METHOD_CALL_AUTHORIZED.get()


def is_target_state_changing_method(method_name: str) -> bool:
    """Return whether a method can mutate target-server state."""
    return method_name in _TARGET_STATE_CHANGING_METHODS


def is_manifest_method_authorized(
    method_name: str,
    *,
    require_disable_asset: bool = False,
    require_destructive: bool = False,
) -> bool:
    """Return True if *method_name* may be called under the active SUT manifest.

    When ``OPCUA_TARGET_SERVER_PROFILE`` is unset (simulator mode), returns True.
    When set, checks ``execution_policy.state_changing_methods.allowed_methods``
    plus any requested risk approvals (`allow_disable_asset`, `allow_destructive_methods`).
    """
    if method_name not in _TARGET_STATE_CHANGING_METHODS:
        return True
    path = os.environ.get("OPCUA_TARGET_SERVER_PROFILE")
    if not path:
        return True

    from pathlib import Path

    from helpers.cu_coverage_report import WorkflowEvidenceUnavailable
    from helpers.sut_manifest import load_sut_manifest, manifest_change_reason

    issue = manifest_change_reason(path, os.environ.get("OPCUA_TARGET_MANIFEST_SHA256"))
    if issue:
        logger.warning("%s blocked: %s", method_name, issue)
        raise WorkflowEvidenceUnavailable(issue, "manifest_changed", "blocked", method_name)

    try:
        profile = load_sut_manifest(Path(path)).to_execution_profile()
    except Exception:  # noqa: BLE001
        return False

    if not profile.cu_execution.state_changing_methods.allow_state_changing_method(method_name):
        return False
    if require_disable_asset and not profile.cu_execution.extension_fields.get("allow_disable_asset", False):
        return False
    if require_destructive and not profile.cu_execution.extension_fields.get("allow_destructive_methods", False):
        return False
    return True


@contextmanager
def manifest_authorized_method_scope(
    method_name: str,
    *,
    require_disable_asset: bool = False,
    require_destructive: bool = False,
):
    """Context manager authorizing direct ``UANode.call_method`` when allowed by the SUT manifest."""
    if not is_manifest_method_authorized(
        method_name,
        require_disable_asset=require_disable_asset,
        require_destructive=require_destructive,
    ):
        yield False
        return
    token = _TARGET_METHOD_CALL_AUTHORIZED.set(True)
    try:
        yield True
    finally:
        _TARGET_METHOD_CALL_AUTHORIZED.reset(token)


def _enforce_target_method_authorization(method_name: str, authorized: bool) -> None:
    """Prevent generic specification tests from mutating a configured real target."""
    if method_name not in _TARGET_STATE_CHANGING_METHODS:
        return
    path = os.environ.get("OPCUA_TARGET_SERVER_PROFILE")
    if not path:
        return

    import pytest

    from helpers.cu_coverage_report import WorkflowEvidenceUnavailable
    from helpers.sut_manifest import manifest_change_reason

    issue = manifest_change_reason(path, os.environ.get("OPCUA_TARGET_MANIFEST_SHA256"))
    if issue:
        logger.warning("%s blocked: %s", method_name, issue)
        raise WorkflowEvidenceUnavailable(issue, "manifest_changed", "blocked", method_name)
    if authorized:
        return

    pytest.skip(
        f"{method_name} is state-changing on a real Target Server and must be "
        "invoked through an explicitly configured target workflow"
    )


class OpcUaStatusHelper:
    """Utility class for classifying and formatting OPC UA status codes."""

    # IJT-relevant Bad status codes
    BAD_NOT_FOUND = 0x80340000
    BAD_INVALID_ARGUMENT = 0x80AB0000
    BAD_NODE_ID_UNKNOWN = 0x80360000
    BAD_METHOD_INVALID = 0x8046FFFF  # approximate
    BAD_NOT_SUPPORTED = 0x803D0000
    BAD_ARGUMENTS_MISSING = 0x80700000

    @staticmethod
    def is_bad(status_code: int) -> bool:
        """Return True if status_code is in the Bad range (0x80000000–0xBFFFFFFF)."""
        return (status_code & 0xC0000000) == 0x80000000

    @staticmethod
    def is_good(status_code: int) -> bool:
        """Return True if status_code is in the Good range (0x00000000–0x3FFFFFFF)."""
        return (status_code & 0xC0000000) == 0x00000000

    @staticmethod
    def is_uncertain(status_code: int) -> bool:
        """Return True if status_code is in the Uncertain range (0x40000000–0x7FFFFFFF)."""
        return (status_code & 0xC0000000) == 0x40000000

    @staticmethod
    def classify(status_code: int) -> str:
        """Return 'Good', 'Bad', or 'Uncertain' for the given status code."""
        if OpcUaStatusHelper.is_good(status_code):
            return "Good"
        if OpcUaStatusHelper.is_bad(status_code):
            return "Bad"
        return "Uncertain"

    @staticmethod
    def format_status(exc: Exception) -> str:
        """
        Extract a human-readable StatusCode string from a ua.UaError if possible,
        otherwise fall back to str(exc).
        """
        if isinstance(exc, ua.UaError):
            # ua.UaError typically has a .code attribute (ua.StatusCode)
            code = getattr(exc, "code", None)
            if code is not None:
                return f"0x{int(code):08X} ({code!s})"
        return str(exc)


@dataclass
class MethodCallResult:
    """Result container for an OPC UA method call attempt."""

    success: bool
    output: object = None
    error: Exception | None = None
    status_code: int | None = None
    method_name: str = ""
    service_good_confirmed: bool = False
    method_status_code: int | None = None
    input_argument_status_codes: tuple[int, ...] = ()
    rpc_dispatched: bool | None = None

    @property
    def output_list(self) -> list:
        """Always return the output as a list, wrapping scalars if necessary."""
        if self.output is None:
            return []
        if isinstance(self.output, (list, tuple)):
            return list(self.output)
        return [self.output]


def call_definitely_rejected(result: MethodCallResult) -> bool:
    """Only predispatch failure or explicit structural/access rejection proves no mutation."""
    return result.rpc_dispatched is False or result.status_code in {
        ua.StatusCodes.BadInvalidArgument,
        ua.StatusCodes.BadUserAccessDenied,
        ua.StatusCodes.BadMethodInvalid,
        ua.StatusCodes.BadTypeMismatch,
    }


async def call_method(
    parent_node,
    method_node_id,
    *args,
    timeout: float = 15.0,
    method_name: str = "",
    target_server_authorized: bool = False,
) -> MethodCallResult:
    """
    Call an OPC UA method on parent_node with a timeout guard.

    Args:
        parent_node: The OPC UA Node object that owns the method.
        method_node_id: NodeId (or Node) of the method to call.
        *args: Input arguments passed to the method.
        timeout: Maximum seconds to wait for the server response.
        method_name: Human-readable label used in log messages.

    Returns:
        MethodCallResult with success=True and output set on success,
        or success=False with error set on ua.UaError / asyncio.TimeoutError.
    """
    label = method_name or str(method_node_id)
    _enforce_target_method_authorization(label, target_server_authorized)
    logger.debug("call_method: invoking '%s' with %d arg(s)", label, len(args))
    start = time.monotonic()
    authorization_token = _TARGET_METHOD_CALL_AUTHORIZED.set(True) if target_server_authorized else None
    try:
        try:
            result = await asyncio.wait_for(
                parent_node.call_method(method_node_id, *args),
                timeout=timeout,
            )
            elapsed = time.monotonic() - start
            logger.debug("call_method: '%s' succeeded in %.3fs, output=%r", label, elapsed, result)
            return MethodCallResult(success=True, output=result, method_name=label)
        except ua.UaError as exc:
            elapsed = time.monotonic() - start
            raw_code = getattr(exc, "code", None)
            status_int = int(raw_code) if raw_code is not None else None
            logger.debug(
                "call_method: '%s' raised UaError after %.3fs: %s",
                label,
                elapsed,
                OpcUaStatusHelper.format_status(exc),
            )
            return MethodCallResult(
                success=False,
                error=exc,
                status_code=status_int,
                method_name=label,
            )
        except asyncio.TimeoutError as exc:
            elapsed = time.monotonic() - start
            logger.debug("call_method: '%s' timed out after %.3fs", label, elapsed)
            return MethodCallResult(success=False, error=exc, method_name=label)
    finally:
        if authorization_token is not None:
            _TARGET_METHOD_CALL_AUTHORIZED.reset(authorization_token)


async def call_method_preserving_status(
    parent_node,
    method_node,
    *args,
    timeout: float = 15.0,
    target_server_authorized: bool = False,
    before_dispatch: Callable[[], None] | None = None,
) -> MethodCallResult:
    """Retain CallMethodResult outputs even for Uncertain or Bad method status."""
    try:
        browse_name = await asyncio.wait_for(method_node.read_browse_name(), timeout=timeout)
    except (ua.UaError, asyncio.TimeoutError) as exc:
        logger.warning("Cannot resolve method identity before raw Call: %s", exc)
        return MethodCallResult(success=False, error=exc, rpc_dispatched=False)
    label = browse_name.Name
    _enforce_target_method_authorization(label, target_server_authorized)
    request = ua.CallMethodRequest(
        ObjectId=parent_node.nodeid,
        MethodId=method_node.nodeid,
        InputArguments=[arg if isinstance(arg, ua.Variant) else ua.Variant(arg) for arg in args],
    )
    authorization_token = _TARGET_METHOD_CALL_AUTHORIZED.set(True) if target_server_authorized else None
    try:
        if before_dispatch is not None:
            before_dispatch()
        try:
            # asyncua's session.call checks the service header, but not each method status.
            responses = await asyncio.wait_for(parent_node.session.call([request]), timeout=timeout)
        except (ua.UaError, asyncio.TimeoutError) as exc:
            raw_code = getattr(exc, "code", None)
            logger.warning("Raw Call service for %s failed: %s", label, exc)
            return MethodCallResult(
                success=False,
                error=exc,
                status_code=int(raw_code) if raw_code is not None else None,
                method_name=label,
                rpc_dispatched=True,
            )
        if len(responses) != 1:
            error = ValueError(f"Call service returned {len(responses)} method results for one request")
            logger.error("%s: %s", label, error)
            return MethodCallResult(
                success=False,
                error=error,
                method_name=label,
                service_good_confirmed=True,
                rpc_dispatched=True,
            )
        response = responses[0]
        method_status = response.StatusCode.value
        outputs = [value.Value for value in response.OutputArguments or ()]
        if not response.StatusCode.is_good():
            logger.warning("%s returned method status %s, outputs=%r", label, response.StatusCode, outputs)
        return MethodCallResult(
            success=response.StatusCode.is_good(),
            output=outputs,
            status_code=method_status,
            method_name=label,
            service_good_confirmed=True,
            method_status_code=method_status,
            input_argument_status_codes=tuple(status.value for status in response.InputArgumentResults or ()),
            rpc_dispatched=True,
        )
    finally:
        if authorization_token is not None:
            _TARGET_METHOD_CALL_AUTHORIZED.reset(authorization_token)


async def find_and_call_method_preserving_status(
    parent_node,
    method_browse_name: str,
    method_ns_index: int,
    *args,
    timeout: float = 15.0,
    target_server_authorized: bool = False,
    before_dispatch: Callable[[], None] | None = None,
) -> MethodCallResult:
    """Discover one method and call it without discarding its negative-response outputs."""
    _enforce_target_method_authorization(method_browse_name, target_server_authorized)
    method_node = await find_child_by_browse_name(parent_node, method_browse_name, method_ns_index, timeout=timeout)
    if method_node is None:
        error = LookupError(f"Method '{method_browse_name}' not found under parent node")
        logger.warning("%s", error)
        return MethodCallResult(success=False, error=error, method_name=method_browse_name, rpc_dispatched=False)
    return await call_method_preserving_status(
        parent_node,
        method_node,
        *args,
        timeout=timeout,
        target_server_authorized=target_server_authorized,
        before_dispatch=before_dispatch,
    )


async def call_method_expect_bad_status(
    parent_node,
    method_node_id,
    *args,
    expected_status_codes: list[int] | None = None,
    timeout: float = 15.0,
    method_name: str = "",
    target_server_authorized: bool = False,
) -> MethodCallResult:
    """
    Call an OPC UA method expecting it to raise a ua.UaError (Bad status).

    Use this in negative-path tests to assert that the server correctly rejects
    invalid or unauthorised requests.

    Args:
        parent_node: The OPC UA Node object that owns the method.
        method_node_id: NodeId (or Node) of the method to call.
        *args: Input arguments passed to the method.
        expected_status_codes: If provided, the raised status code must be one of
            these values; otherwise any Bad status is accepted.
        timeout: Maximum seconds to wait for the server response.
        method_name: Human-readable label used in log messages.

    Returns:
        MethodCallResult with success=True when the expected error occurred,
        success=False when the call unexpectedly succeeded or raised an
        unexpected status code.
    """
    label = method_name or str(method_node_id)
    _enforce_target_method_authorization(label, target_server_authorized)
    logger.debug("call_method_expect_bad_status: invoking '%s'", label)
    start = time.monotonic()
    authorization_token = _TARGET_METHOD_CALL_AUTHORIZED.set(True) if target_server_authorized else None
    try:
        try:
            result = await asyncio.wait_for(
                parent_node.call_method(method_node_id, *args),
                timeout=timeout,
            )
            elapsed = time.monotonic() - start
            logger.debug(
                "call_method_expect_bad_status: '%s' unexpectedly succeeded in %.3fs, output=%r",
                label,
                elapsed,
                result,
            )
            return MethodCallResult(
                success=False,
                output=result,
                error=AssertionError(f"Expected BadStatus from '{label}' but call succeeded with output={result!r}"),
                method_name=label,
            )
        except ua.UaError as exc:
            elapsed = time.monotonic() - start
            raw_code = getattr(exc, "code", None)
            status_int: int | None = int(raw_code) if raw_code is not None else None
            logger.debug(
                "call_method_expect_bad_status: '%s' raised UaError after %.3fs: %s",
                label,
                elapsed,
                OpcUaStatusHelper.format_status(exc),
            )
            if expected_status_codes is not None and status_int is not None:
                if status_int not in expected_status_codes:
                    return MethodCallResult(
                        success=False,
                        error=exc,
                        status_code=status_int,
                        method_name=label,
                    )
                logger.debug(
                    "call_method_expect_bad_status: '%s' got expected status 0x%08X",
                    label,
                    status_int,
                )
            return MethodCallResult(
                success=True,
                error=exc,
                status_code=status_int,
                method_name=label,
            )
        except asyncio.TimeoutError as exc:
            elapsed = time.monotonic() - start
            logger.debug(
                "call_method_expect_bad_status: '%s' timed out after %.3fs",
                label,
                elapsed,
            )
            return MethodCallResult(success=False, error=exc, method_name=label)
    finally:
        if authorization_token is not None:
            _TARGET_METHOD_CALL_AUTHORIZED.reset(authorization_token)


async def call_method_and_assert_success(
    parent_node,
    method_node_id,
    *args,
    timeout: float = 15.0,
    method_name: str = "",
) -> object:
    """
    Call an OPC UA method and raise AssertionError if it does not succeed.

    Designed for use inside pytest test functions where a failing method call
    should immediately fail the test with a descriptive message.

    Args:
        parent_node: The OPC UA Node object that owns the method.
        method_node_id: NodeId (or Node) of the method to call.
        *args: Input arguments passed to the method.
        timeout: Maximum seconds to wait for the server response.
        method_name: Human-readable label used in log messages.

    Returns:
        The raw output from the method call on success.

    Raises:
        AssertionError: If the method call fails for any reason.
    """
    result = await call_method(parent_node, method_node_id, *args, timeout=timeout, method_name=method_name)
    if not result.success:
        label = method_name or str(method_node_id)
        status_str = OpcUaStatusHelper.format_status(result.error) if result.error is not None else "unknown error"
        raise AssertionError(f"OPC UA method '{label}' failed — {status_str}")
    return result.output


async def find_and_call_method(
    parent_node,
    method_browse_name: str,
    method_ns_index: int,
    *args,
    timeout: float = 15.0,
    target_server_authorized: bool = False,
    preserve_status: bool = False,
    before_dispatch: Callable[[], None] | None = None,
) -> MethodCallResult:
    """
    Locate a method child by browse name, then invoke it.

    Args:
        parent_node: The OPC UA Node whose children are searched.
        method_browse_name: BrowseName (local name) of the method node.
        method_ns_index: Namespace index for the method's BrowseName.
        *args: Input arguments forwarded to the method.
        timeout: Maximum seconds used for both discovery and the method call.

    Returns:
        MethodCallResult with success=True and output set on success,
        or success=False with a LookupError if the method node is not found,
        or success=False with the ua.UaError / TimeoutError on call failure.
    """
    if preserve_status:
        return await find_and_call_method_preserving_status(
            parent_node,
            method_browse_name,
            method_ns_index,
            *args,
            timeout=timeout,
            target_server_authorized=target_server_authorized,
            before_dispatch=before_dispatch,
        )
    if before_dispatch is not None:
        raise ValueError("Dispatch lifecycle hooks require the status-preserving Call route")
    method_node = await find_child_by_browse_name(parent_node, method_browse_name, method_ns_index, timeout=timeout)
    if method_node is None:
        err = LookupError(f"Method '{method_browse_name}' not found under parent node")
        logger.debug("find_and_call_method: %s", err)
        return MethodCallResult(
            success=False,
            error=err,
            method_name=method_browse_name,
        )
    return await call_method(
        parent_node,
        method_node,
        *args,
        timeout=timeout,
        method_name=method_browse_name,
        target_server_authorized=target_server_authorized,
    )
