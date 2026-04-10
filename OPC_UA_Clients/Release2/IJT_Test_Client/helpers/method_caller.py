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
import time
from dataclasses import dataclass

from asyncua import ua

from helpers.node_discovery import find_child_by_browse_name

logger = logging.getLogger(__name__)


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

    @property
    def output_list(self) -> list:
        """Always return the output as a list, wrapping scalars if necessary."""
        if self.output is None:
            return []
        if isinstance(self.output, (list, tuple)):
            return list(self.output)
        return [self.output]


async def call_method(
    parent_node,
    method_node_id,
    *args,
    timeout: float = 15.0,
    method_name: str = "",
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
    logger.debug("call_method: invoking '%s' with %d arg(s)", label, len(args))
    start = time.monotonic()
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
        logger.debug(
            "call_method: '%s' raised UaError after %.3fs: %s",
            label,
            elapsed,
            OpcUaStatusHelper.format_status(exc),
        )
        return MethodCallResult(success=False, error=exc, method_name=label)
    except asyncio.TimeoutError as exc:
        elapsed = time.monotonic() - start
        logger.debug("call_method: '%s' timed out after %.3fs", label, elapsed)
        return MethodCallResult(success=False, error=exc, method_name=label)


async def call_method_expect_bad_status(
    parent_node,
    method_node_id,
    *args,
    expected_status_codes: list[int] | None = None,
    timeout: float = 15.0,
    method_name: str = "",
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
    logger.debug("call_method_expect_bad_status: invoking '%s'", label)
    start = time.monotonic()
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
        return MethodCallResult(success=True, error=exc, status_code=status_int, method_name=label)
    except asyncio.TimeoutError as exc:
        elapsed = time.monotonic() - start
        logger.debug("call_method_expect_bad_status: '%s' timed out after %.3fs", label, elapsed)
        return MethodCallResult(success=False, error=exc, method_name=label)


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
    )
