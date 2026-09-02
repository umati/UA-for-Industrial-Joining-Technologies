"""
Result collection for IJT conformance tests — events-primary design.

JoiningSystemResultReadyEventType events are the primary result notification
mechanism for IJT clients (matching IJT Web Client and Console Client behaviour).
This module wraps EventCollector to provide high-level, filtered result retrieval
that works for both the simulator and real controllers of any batch/job size.

Key design principle — dynamic, not count-bounded:
  Events are consumed ONE AT A TIME.  Collection stops the instant a result with
  the correct classification AND IsPartial=False is found.  This means a batch
  with 3 sub-results and a batch with 300 sub-results are handled identically —
  no fixed ceiling, no unnecessary waiting.

Timeouts are tuned per trigger type (is_simulator flag):
  - Simulator: results generated in < 2 s → short timeouts keep test suite fast
  - Real controller: joining operations take seconds → longer timeouts needed
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

from asyncua import ua

from helpers.event_collector import EventCollector
from helpers.namespaces import NS_IJT_BASE, IJTTypes, ResultClassification

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Timeout constants — NO fixed event-count ceilings
# ---------------------------------------------------------------------------

# Simulator: results arrive within ~2 s; use generous-but-not-excessive timeouts
_SIM_SINGLE_TIMEOUT = 10.0
_SIM_COMBINED_TIMEOUT = 15.0  # stops as soon as IsPartial=False arrives
_SIM_JOB_TIMEOUT = 30.0  # stops as soon as final JOB_RESULT arrives

# Real controller: joining takes seconds; be generous
_CTRL_SINGLE_TIMEOUT = 60.0
_CTRL_COMBINED_TIMEOUT = 120.0
_CTRL_JOB_TIMEOUT = 300.0

# Inner poll window — how long to wait for a single event before looping back.
# Short enough to stay responsive; avoids blocking forever on one queue.get().
_INNER_POLL_S = 2.0


# ---------------------------------------------------------------------------
# Standalone helpers
# ---------------------------------------------------------------------------


def unwrap_result(item: Any) -> Any:
    """Unwrap ua.Variant wrappers from asyncua ExtensionObject deserialization.

    asyncua may return nested ExtensionObjects wrapped in ua.Variant when type
    definitions have not been fully loaded.  Unwraps up to two levels.
    Returns the inner struct, or the original item if no wrapping is detected.
    """
    try:
        if isinstance(item, ua.Variant):
            inner = item.Value
            if inner is None:
                return None
            if isinstance(inner, ua.Variant):
                inner = inner.Value
            return inner
    except Exception:  # noqa: BLE001
        return item
    return item


def get_classification(result_data: Any) -> Optional[int]:
    """Return ResultMetaData.Classification as int, or None if absent/unreadable."""
    meta = getattr(result_data, "ResultMetaData", None)
    if meta is None:
        return None
    cls = getattr(meta, "Classification", None)
    if cls is None:
        return None
    try:
        return int(cls)
    except (TypeError, ValueError):
        return None


def is_partial(result_data: Any) -> bool:
    """Return True when ResultMetaData.IsPartial is truthy."""
    meta = getattr(result_data, "ResultMetaData", None)
    if meta is None:
        return False
    partial = getattr(meta, "IsPartial", None)
    if partial is None:
        return False
    if isinstance(partial, ua.Variant):
        partial = partial.Value
    try:
        return bool(partial)
    except (TypeError, ValueError):
        return False


def is_terminal_matching_state(result_data: Any, target_cls: Optional[int], target_state: int = 1) -> bool:
    """Return True if result matches target_cls, IsPartial is False/0, and ResultState == target_state."""
    if result_data is None:
        return False
    if target_cls is not None and get_classification(result_data) != target_cls:
        return False
    meta = getattr(result_data, "ResultMetaData", None)
    if meta is None:
        return False
    partial = getattr(meta, "IsPartial", None)
    if isinstance(partial, ua.Variant):
        partial = partial.Value
    if partial not in (False, 0):
        return False
    state = getattr(meta, "ResultState", None)
    if isinstance(state, ua.Variant):
        state = state.Value
    if isinstance(state, bool):
        return False
    try:
        return state is not None and int(state) == int(target_state)
    except (TypeError, ValueError):
        return False


def is_terminal_completed(result_data: Any, target_cls: Optional[int]) -> bool:
    """Return True if result matches target_cls, IsPartial is False/0, and ResultState is 1 (COMPLETED)."""
    return is_terminal_matching_state(result_data, target_cls, target_state=1)


def is_terminal_aborted(result_data: Any, target_cls: Optional[int]) -> bool:
    """Return True if result matches target_cls, IsPartial is False/0, and ResultState is 3 (ABORTED)."""
    return is_terminal_matching_state(result_data, target_cls, target_state=3)


@dataclass(frozen=True)
class CorrelatedOperationOutcome:
    """Outcome of observing result events after a single StartSelectedJoining invocation."""

    operation_confirmed: bool = False
    operation_result: Optional[Any] = None
    terminal_result: Optional[Any] = None
    latest_result: Optional[Any] = None
    timed_out: bool = False


# ---------------------------------------------------------------------------
# ResultCollector
# ---------------------------------------------------------------------------


class ResultCollector:
    """
    Context manager that subscribes to JoiningSystemResultReadyEventType events
    before a trigger and collects matching results afterwards.

    Design: subscribe-before-trigger eliminates race conditions where the server
    fires the event before the test starts collecting.  Results are filtered in
    reverse (newest first) so partial/stale events are skipped.

    Usage::

        async with ResultCollector(subscription_client, ns_indices,
                                   is_simulator=result_trigger.is_simulator) as rc:
            outcome = await result_trigger.trigger_batch_or_sync(
                classification=classification, include_traces=False, send_as_refs=True)
            if not outcome.triggered and result_trigger.is_simulator:
                return None
            result_data = await rc.collect_combined(classification)
    """

    def __init__(
        self,
        subscription_client: Any,
        ns_indices: dict,
        *,
        is_simulator: bool = True,
    ) -> None:
        self._client = subscription_client
        self._ns_indices = ns_indices
        self._is_simulator = is_simulator
        self._collector: Optional[EventCollector] = None
        self._target_timeout = self._read_target_timeout()
        self._final_result_required = not is_simulator and os.environ.get(
            "OPCUA_TARGET_FINAL_RESULT_REQUIRED", ""
        ).strip().lower() in {"1", "true", "yes", "on"}
        self._required_result_classification = self._read_required_result_classification()

    def _read_target_timeout(self) -> Optional[float]:
        if self._is_simulator:
            return None
        raw = os.environ.get("OPCUA_TARGET_RESULT_TIMEOUT_SECONDS", "").strip()
        if not raw:
            return None
        try:
            value = float(raw)
        except ValueError:
            logger.warning("Ignoring invalid OPCUA_TARGET_RESULT_TIMEOUT_SECONDS=%r", raw)
            return None
        return value if value > 0 else None

    def _read_required_result_classification(self) -> Optional[int]:
        if self._is_simulator:
            return None
        raw = os.environ.get("OPCUA_TARGET_REQUIRED_RESULT_CLASSIFICATION", "").strip()
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            logger.warning("Ignoring invalid OPCUA_TARGET_REQUIRED_RESULT_CLASSIFICATION=%r", raw)
            return None
        return value if value in ResultClassification.VALID_VALUES else None

    # ── context manager ───────────────────────────────────────────────────

    async def __aenter__(self) -> "ResultCollector":
        ns_ijt = self._ns_indices.get(NS_IJT_BASE)
        if ns_ijt is None:
            raise RuntimeError("IJT Base namespace not registered — cannot subscribe to result events")

        server_node = self._client.nodes.server
        event_type_node = self._client.get_node(ua.NodeId(IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE, ns_ijt))

        self._collector = EventCollector(self._client)
        await self._collector.subscribe(server_node, event_type_node)
        return self

    async def __aexit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        if self._collector is not None:
            await self._collector.unsubscribe()
            self._collector = None

    # ── internal helpers ──────────────────────────────────────────────────

    def _extract(self, event: Any, target_cls: Optional[int], want_partial: bool) -> Optional[Any]:
        """Extract result_data from a single event if it matches target criteria.

        Args:
            event:        Raw event object from EventCollector.
            target_cls:   Required Classification int, or None to accept any.
            want_partial: When True, match IsPartial=True; otherwise False.
        Returns:
            Matching result_data, or None.
        """
        raw = getattr(event, "Result", None)
        if raw is None:
            return None
        result_data = unwrap_result(raw)
        if result_data is None:
            return None
        if target_cls is not None and get_classification(result_data) != target_cls:
            return None
        if is_partial(result_data) != want_partial:
            return None
        return result_data

    async def _collect_until(
        self,
        target_cls: Optional[int],
        want_partial: bool,
        timeout: float,
        predicate: Any = None,
    ) -> Optional[Any]:
        """Core event-loop: consume events one at a time until a matching result is found.

        Stops IMMEDIATELY when a result with the correct classification and
        IsPartial state is received — no fixed count ceiling.  Works for any
        batch/job size, from 2 sub-results to thousands.

        Args:
            target_cls:   Required Classification value, or None for any.
            want_partial: True → return first IsPartial=True match;
                          False → return first IsPartial=False match (the final).
            timeout:      Total wall-clock budget in seconds.
        Returns:
            Matching result_data, or None if timeout expired with no match.
        """
        if self._collector is None:
            raise RuntimeError("ResultCollector is not active — use as async context manager")

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            # Poll for one event; short inner window keeps the loop responsive
            events = await self._collector.collect(count=1, timeout_s=min(remaining, _INNER_POLL_S))
            if not events:
                # No event in this window — loop back and check deadline
                continue
            result_data = self._extract(events[0], target_cls, want_partial)
            if result_data is not None and (predicate is None or predicate(result_data)):
                return result_data  # Found it — return immediately

        return None

    # ── public collect methods ────────────────────────────────────────────

    async def collect_single(self, timeout_s: Optional[float] = None) -> Optional[Any]:
        """Collect the next SINGLE_RESULT event (IsPartial=False).

        Stops immediately when a SINGLE_RESULT arrives.  Works for simulator
        and real controller.

        Args:
            timeout_s: Override the default timeout for this call.
        Returns:
            result_data, or None if no matching event arrived within timeout.
        """
        timeout = (
            timeout_s
            if timeout_s is not None
            else (_SIM_SINGLE_TIMEOUT if self._is_simulator else self._target_timeout or _CTRL_SINGLE_TIMEOUT)
        )
        result = await self._collect_until(ResultClassification.SINGLE_RESULT, False, timeout)
        return self._require_final(result, "SingleResult", timeout, ResultClassification.SINGLE_RESULT)

    async def collect_single_matching(self, predicate: Any, timeout_s: Optional[float] = None) -> Optional[Any]:
        """Collect a SingleResult that satisfies a caller-provided correlation predicate."""
        timeout = timeout_s if timeout_s is not None else self._target_timeout or _CTRL_SINGLE_TIMEOUT
        return await self._collect_until(ResultClassification.SINGLE_RESULT, False, timeout, predicate)

    async def collect_combined(self, classification: int, timeout_s: Optional[float] = None) -> Optional[Any]:
        """Collect the final combined result event for the given classification.

        Consumes events one at a time.  Returns immediately when a result with
        matching classification AND IsPartial=False is received — so a batch
        with 3 sub-results and one with 300 sub-results are handled identically.

        Args:
            classification: Target ResultClassification (e.g. BATCH_RESULT).
            timeout_s:      Override the default timeout.
        Returns:
            result_data (IsPartial=False), or None if timeout expired.
        """
        timeout = (
            timeout_s
            if timeout_s is not None
            else (_SIM_COMBINED_TIMEOUT if self._is_simulator else self._target_timeout or _CTRL_COMBINED_TIMEOUT)
        )
        result = await self._collect_until(classification, False, timeout)
        return self._require_final(result, f"classification {classification}", timeout, classification)

    async def collect_partial(self, classification: int, timeout_s: Optional[float] = None) -> Optional[Any]:
        """Collect the first partial combined result event (IsPartial=True).

        Returns as soon as the first partial result with matching classification
        arrives — no need to wait for the final combined result.

        Args:
            classification: Target ResultClassification value.
            timeout_s:      Override the default timeout.
        Returns:
            result_data with IsPartial=True, or None if none arrived within timeout.
        """
        timeout = (
            timeout_s
            if timeout_s is not None
            else (_SIM_COMBINED_TIMEOUT if self._is_simulator else self._target_timeout or _CTRL_COMBINED_TIMEOUT)
        )
        return await self._collect_until(classification, True, timeout)

    async def collect_job(self, timeout_s: Optional[float] = None) -> Optional[Any]:
        """Collect the final JOB_RESULT event (IsPartial=False).

        Consumes events one at a time.  Returns immediately when the final job
        result arrives, regardless of how many intermediate events were generated.

        Args:
            timeout_s: Override the default timeout.
        Returns:
            result_data, or None if no matching event arrived within timeout.
        """
        timeout = (
            timeout_s
            if timeout_s is not None
            else (_SIM_JOB_TIMEOUT if self._is_simulator else self._target_timeout or _CTRL_JOB_TIMEOUT)
        )
        result = await self._collect_until(ResultClassification.JOB_RESULT, False, timeout)
        return self._require_final(result, "JobResult", timeout, ResultClassification.JOB_RESULT)

    async def collect_correlated_operation_outcome(
        self,
        requested_result_classification: Optional[int],
        predicate: Any,
        operation_timeout_s: float,
        terminal_drain_seconds: float = 0.25,
        operation_predicate: Any = None,
        expected_terminal_state: int = 1,
    ) -> CorrelatedOperationOutcome:
        """Consume correlated events from the active subscription stream.

        Observes events until operation evidence or the requested terminal result is found,
        then drains for up to terminal_drain_seconds to catch an immediate terminal result.
        """
        if self._collector is None:
            raise RuntimeError("ResultCollector is not active — use as async context manager")

        loop = asyncio.get_running_loop()
        deadline = loop.time() + operation_timeout_s
        operation_confirmed = False
        operation_result: Optional[Any] = None
        latest_result: Optional[Any] = None
        operation_predicate = operation_predicate or predicate

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            events = await self._collector.collect(count=1, timeout_s=min(remaining, _INNER_POLL_S))
            if not events:
                continue
            raw = getattr(events[0], "Result", None)
            result_data = unwrap_result(raw) if raw is not None else None
            if result_data is None:
                continue

            latest_result = result_data
            is_operation_result = (
                get_classification(result_data) == ResultClassification.SINGLE_RESULT
                and operation_predicate(result_data)
                and is_terminal_completed(result_data, ResultClassification.SINGLE_RESULT)
            )
            if predicate(result_data) and is_terminal_matching_state(
                result_data, requested_result_classification, target_state=expected_terminal_state
            ):
                return CorrelatedOperationOutcome(
                    operation_confirmed=True,
                    operation_result=result_data if is_operation_result else operation_result,
                    terminal_result=result_data,
                    latest_result=result_data,
                    timed_out=False,
                )

            if is_operation_result:
                operation_confirmed = True
                operation_result = result_data
                break

        if not operation_confirmed:
            return CorrelatedOperationOutcome(
                operation_confirmed=False,
                operation_result=None,
                terminal_result=None,
                latest_result=None,
                timed_out=True,
            )

        # Drain phase: check for terminal consolidated result arriving during the pacing window
        if terminal_drain_seconds > 0:
            drain_deadline = loop.time() + terminal_drain_seconds
            while True:
                drain_rem = drain_deadline - loop.time()
                if drain_rem <= 0:
                    break
                events = await self._collector.collect(count=1, timeout_s=min(drain_rem, 0.05))
                if not events:
                    continue
                raw = getattr(events[0], "Result", None)
                result_data = unwrap_result(raw) if raw is not None else None
                if result_data is None:
                    continue
                latest_result = result_data
                if predicate(result_data) and is_terminal_matching_state(
                    result_data, requested_result_classification, target_state=expected_terminal_state
                ):
                    return CorrelatedOperationOutcome(
                        operation_confirmed=True,
                        operation_result=operation_result,
                        terminal_result=result_data,
                        latest_result=result_data,
                        timed_out=False,
                    )

        return CorrelatedOperationOutcome(
            operation_confirmed=True,
            operation_result=operation_result,
            terminal_result=None,
            latest_result=latest_result,
            timed_out=False,
        )

    def collect_pending_terminal(
        self,
        requested_result_classification: Optional[int],
        predicate: Any,
        expected_terminal_state: int = 1,
    ) -> Optional[Any]:
        """Consume queued events and return the first matching completed terminal result."""
        if self._collector is None:
            raise RuntimeError("ResultCollector is not active — use as async context manager")
        for event in self._collector.collect_pending():
            raw = getattr(event, "Result", None)
            result_data = unwrap_result(raw) if raw is not None else None
            if (
                result_data is not None
                and predicate(result_data)
                and is_terminal_matching_state(
                    result_data, requested_result_classification, target_state=expected_terminal_state
                )
            ):
                return result_data
        return None

    def discard_pending(self) -> int:
        """Discard queued notifications before a correlated operation starts."""
        if self._collector is None:
            raise RuntimeError("ResultCollector is not active — use as async context manager")
        return self._collector.discard_pending()

    def _require_final(
        self,
        result: Optional[Any],
        label: str,
        timeout: float,
        classification: Optional[int] = None,
    ) -> Optional[Any]:
        classification_is_required = (
            self._required_result_classification is None or classification == self._required_result_classification
        )
        if result is None and self._final_result_required and classification_is_required:
            raise TimeoutError(f"Required final {label} was not received within {timeout:.1f}s")
        return result
