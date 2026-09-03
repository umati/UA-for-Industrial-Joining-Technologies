"""
Result collection for IJT conformance tests — events-primary design.

JoiningSystemResultReadyEventType events are the primary result notification
mechanism for IJT clients (matching IJT Web Client and Console Client behaviour).
This module wraps EventCollector to provide high-level, filtered result retrieval
that works for both the simulator and real controllers of any batch/job size.

Key design principle — dynamic, not count-bounded:
  Events are consumed one at a time. Progression collection retains partial
  parents and child results until a completed final parent closes all references
  or the configured timeout expires. Batch size is learned from evidence rather
  than a fixed event-count ceiling.

Timeouts are tuned per trigger type (is_simulator flag):
  - Simulator: results generated in < 2 s → short timeouts keep test suite fast
  - Real controller: joining operations take seconds → longer timeouts needed
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Optional

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


def get_result_id(result_data: Any) -> str:
    """Return a normalized ResultId from a result envelope or reference."""
    direct = getattr(result_data, "ResultId", "")
    if isinstance(direct, ua.Variant):
        direct = direct.Value
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    meta = getattr(result_data, "ResultMetaData", None)
    value = getattr(meta, "ResultId", "") if meta is not None else ""
    if isinstance(value, ua.Variant):
        value = value.Value
    return value.strip() if isinstance(value, str) else ""


def references_result_id(
    result_data: Any,
    expected_result_id: str,
    related_results: tuple[Any, ...] = (),
) -> bool:
    """Return whether a result directly or transitively references the expected ID."""
    if not expected_result_id:
        return False
    related_by_id: dict[str, list[Any]] = {}
    for candidate in related_results:
        result_id = get_result_id(candidate)
        if result_id:
            related_by_id.setdefault(result_id, []).append(candidate)
    pending = [result_data]
    visited: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))
        for field_name in ("ResultContent", "References"):
            values = getattr(current, field_name, None)
            if not isinstance(values, (list, tuple)):
                continue
            for raw_value in values:
                value = unwrap_result(raw_value)
                if value is None:
                    continue
                result_id = get_result_id(value)
                if result_id == expected_result_id:
                    return True
                if result_id:
                    pending.extend(related_by_id.get(result_id, ()))
                child_content = getattr(value, "ResultContent", None)
                if isinstance(child_content, (list, tuple)) and child_content:
                    pending.append(value)
    return False


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


@dataclass(frozen=True)
class ResultProgression:
    """Immutable partial-to-final evidence for one consolidated classification."""

    classification: int
    partial_results: tuple[Any, ...] = ()
    final_result: Optional[Any] = None
    child_results: tuple[Any, ...] = ()
    all_results: tuple[Any, ...] = ()
    source_events: tuple[Any, ...] = ()
    unresolved_reference_ids: tuple[str, ...] = ()
    duplicate_event_count: int = 0
    queue_overflow_count: int = 0
    timed_out: bool = False
    missing_required_partials: bool = False

    @property
    def is_complete(self) -> bool:
        """Return whether a completed final parent and all referenced children were captured."""
        return (
            self.final_result is not None
            and not self.unresolved_reference_ids
            and not self.missing_required_partials
            and self.queue_overflow_count == 0
        )


@dataclass(frozen=True)
class ResultEventCapture:
    """Loss-aware result events retained until a caller-defined evidence condition is met."""

    all_results: tuple[Any, ...] = ()
    source_events: tuple[Any, ...] = ()
    duplicate_event_count: int = 0
    queue_overflow_count: int = 0
    timed_out: bool = False

    @property
    def is_lossless(self) -> bool:
        return self.queue_overflow_count == 0


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
        self._captured_results: list[Any] = []
        self._captured_source_events: list[Any] = []
        self._captured_event_ids: set[tuple[str, Any]] = set()
        self._captured_duplicate_count = 0
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

        self._captured_results.clear()
        self._captured_source_events.clear()
        self._captured_event_ids.clear()
        self._captured_duplicate_count = 0
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
        result_data = self._record_event(event)
        if result_data is None:
            return None
        if target_cls is not None and get_classification(result_data) != target_cls:
            return None
        if is_partial(result_data) != want_partial:
            return None
        return result_data

    def _record_event(self, event: Any) -> Optional[Any]:
        """Archive one unique event so trigger-owned collection can build progression evidence."""
        identity = self._event_identity(event)
        if identity in self._captured_event_ids:
            self._captured_duplicate_count += 1
            return None
        self._captured_event_ids.add(identity)
        self._captured_source_events.append(event)
        raw = getattr(event, "Result", None)
        result_data = unwrap_result(raw) if raw is not None else None
        if result_data is not None:
            self._captured_results.append(result_data)
        return result_data

    @staticmethod
    def _result_id(result_data: Any) -> str:
        """Return a normalized ResultId, or an empty string when unavailable."""
        return get_result_id(result_data)

    @staticmethod
    def _event_identity(event: Any) -> tuple[str, Any]:
        """Return a stable event identity without merging distinct progression updates."""
        event_id = getattr(event, "EventId", None)
        if isinstance(event_id, ua.Variant):
            event_id = event_id.Value
        if isinstance(event_id, bytearray):
            event_id = bytes(event_id)
        if isinstance(event_id, (bytes, str)) and event_id:
            return ("event_id", event_id)
        return ("object", id(event))

    @classmethod
    def _reference_closure(
        cls,
        final_result: Any,
        captured_results: list[Any],
        *,
        allow_partial_results: bool = False,
    ) -> tuple[str, ...]:
        """Return unresolved IDs across the final parent's complete child-reference graph."""
        required: set[str] = set()
        resolved: set[str] = set()
        captured_by_id: dict[str, list[Any]] = {}
        for result in captured_results:
            result_id = cls._result_id(result)
            if result_id:
                captured_by_id.setdefault(result_id, []).append(result)

        pending = [final_result]
        visited: set[int] = set()
        while pending:
            parent = pending.pop()
            if id(parent) in visited:
                continue
            visited.add(id(parent))
            parent_id = cls._result_id(parent)

            content = getattr(parent, "ResultContent", None)
            if isinstance(content, (list, tuple)):
                for raw_child in content:
                    child = unwrap_result(raw_child)
                    child_id = cls._result_id(child)
                    if not child_id:
                        continue
                    child_content = getattr(child, "ResultContent", None)
                    child_classification = get_classification(child)
                    child_is_resolved = is_terminal_completed(child, child_classification) or (
                        allow_partial_results and is_partial(child)
                    )
                    if isinstance(child_content, (list, tuple)) and child_content and child_is_resolved:
                        resolved.add(child_id)
                        pending.append(child)
                        continue
                    required.add(child_id)
                    if child_id == parent_id:
                        continue
                    candidates = [
                        candidate
                        for candidate in captured_by_id.get(child_id, [])
                        if candidate is not parent
                        and (
                            is_terminal_completed(candidate, get_classification(candidate))
                            or (allow_partial_results and is_partial(candidate))
                        )
                    ]
                    if candidates:
                        resolved.add(child_id)
                        pending.extend(candidates)

            references = getattr(parent, "References", None)
            if isinstance(references, (list, tuple)):
                for raw_reference in references:
                    reference = unwrap_result(raw_reference)
                    reference_id = cls._result_id(reference)
                    if not reference_id:
                        continue
                    required.add(reference_id)
                    if reference_id == parent_id:
                        continue
                    candidates = [
                        candidate
                        for candidate in captured_by_id.get(reference_id, [])
                        if candidate is not parent
                        and (
                            is_terminal_completed(candidate, get_classification(candidate))
                            or (allow_partial_results and is_partial(candidate))
                        )
                    ]
                    if candidates:
                        resolved.add(reference_id)
                        pending.extend(candidates)

        return tuple(sorted(required - resolved))

    async def collect_evidence(
        self,
        predicate: Callable[[tuple[Any, ...]], bool],
        timeout_s: float,
    ) -> ResultEventCapture:
        """Collect one loss-aware event stream until its decoded results satisfy predicate."""
        if self._collector is None:
            raise RuntimeError("ResultCollector is not active — use as async context manager")

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_s
        all_results = list(self._captured_results)
        satisfied = predicate(tuple(all_results))

        while not satisfied:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            events = await self._collector.collect(count=1, timeout_s=min(remaining, _INNER_POLL_S))
            if not events:
                continue

            event = events[0]
            result_data = self._record_event(event)
            if result_data is not None:
                all_results = list(self._captured_results)
                satisfied = predicate(tuple(all_results))

        dropped = getattr(self._collector, "dropped_event_count", 0)
        queue_overflow_count = dropped if isinstance(dropped, int) and not isinstance(dropped, bool) else 0
        return ResultEventCapture(
            all_results=tuple(self._captured_results),
            source_events=tuple(self._captured_source_events),
            duplicate_event_count=self._captured_duplicate_count,
            queue_overflow_count=queue_overflow_count,
            timed_out=not satisfied,
        )

    async def collect_progression(
        self,
        classification: int,
        timeout_s: Optional[float] = None,
        *,
        require_partials: bool = False,
        expected_terminal_state: int = 1,
        allow_partial_references: bool = False,
        require_reference_closure: bool = True,
    ) -> ResultProgression:
        """Collect all fresh evidence through a terminal consolidated result and child closure."""
        if self._collector is None:
            raise RuntimeError("ResultCollector is not active — use as async context manager")

        timeout = (
            timeout_s
            if timeout_s is not None
            else (_SIM_COMBINED_TIMEOUT if self._is_simulator else self._target_timeout or _CTRL_COMBINED_TIMEOUT)
        )
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        all_results = list(self._captured_results)
        partials = [
            result for result in all_results if get_classification(result) == classification and is_partial(result)
        ]
        children = [result for result in all_results if get_classification(result) != classification]
        final_result: Optional[Any] = None
        for result in all_results:
            if is_terminal_matching_state(result, classification, target_state=expected_terminal_state):
                final_result = result
        unresolved: tuple[str, ...] = ()
        if final_result is not None and require_reference_closure:
            unresolved = self._reference_closure(
                final_result,
                all_results,
                allow_partial_results=allow_partial_references,
            )

        while True:
            if final_result is not None and not unresolved and (not require_partials or partials):
                break
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            events = await self._collector.collect(count=1, timeout_s=min(remaining, _INNER_POLL_S))
            if not events:
                continue

            event = events[0]
            result_data = self._record_event(event)
            if result_data is None:
                continue

            all_results = list(self._captured_results)
            result_classification = get_classification(result_data)
            if result_classification == classification:
                if is_partial(result_data):
                    partials.append(result_data)
                elif is_terminal_matching_state(
                    result_data,
                    classification,
                    target_state=expected_terminal_state,
                ):
                    final_result = result_data
            else:
                children.append(result_data)

            if final_result is not None:
                if require_reference_closure:
                    unresolved = self._reference_closure(
                        final_result,
                        all_results,
                        allow_partial_results=allow_partial_references,
                    )
                if not unresolved and (not require_partials or partials):
                    break

        missing_partials = require_partials and not partials
        timed_out = final_result is None or bool(unresolved) or missing_partials
        dropped = getattr(self._collector, "dropped_event_count", 0)
        queue_overflow_count = dropped if isinstance(dropped, int) and not isinstance(dropped, bool) else 0
        return ResultProgression(
            classification=classification,
            partial_results=tuple(partials),
            final_result=final_result,
            child_results=tuple(children),
            all_results=tuple(self._captured_results),
            source_events=tuple(self._captured_source_events),
            unresolved_reference_ids=unresolved,
            duplicate_event_count=self._captured_duplicate_count,
            queue_overflow_count=queue_overflow_count,
            timed_out=timed_out,
            missing_required_partials=missing_partials,
        )

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
        if classification == ResultClassification.INTERVENTION_RESULT:
            result = await self._collect_until(classification, False, timeout)
        else:
            progression = await self.collect_progression(classification, timeout)
            result = progression.final_result
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
        progression = await self.collect_progression(ResultClassification.JOB_RESULT, timeout)
        result = progression.final_result
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
            result_data = self._record_event(events[0])
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
                result_data = self._record_event(events[0])
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
            result_data = self._record_event(event)
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
