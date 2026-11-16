"""
Result collection for IJT conformance tests — events-primary design.

ResultReadyEventType events include IJT joining results and other-domain children
referenced by consolidated results.
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
from dataclasses import dataclass, replace
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Optional

from asyncua import ua

from helpers.event_collector import EventCollector
from helpers.namespaces import NS_IJT_BASE, NS_MACH_RESULT, MachineryResultTypes, ResultClassification, ResultState

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


def parent_result_ids(result_data: Any) -> frozenset[str]:
    """Read explicit PARENT_TYPE (40) result links, not arbitrary associated entities."""
    meta = getattr(result_data, "ResultMetaData", None)
    parents = set()
    for raw in getattr(meta, "AssociatedEntities", None) or ():
        entity = unwrap_result(raw)
        entity_type = unwrap_result(getattr(entity, "EntityType", None))
        entity_id = unwrap_result(getattr(entity, "EntityId", None))
        if (
            isinstance(entity_type, int)
            and not isinstance(entity_type, bool)
            and entity_type == 40
            and isinstance(entity_id, str)
            and entity_id.strip()
        ):
            parents.add(entity_id.strip())
    return frozenset(parents)


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


def is_terminal_result(result_data: Any, target_cls: Optional[int]) -> bool:
    """Recognize termination independently of the state expected by a test."""
    return any(
        is_terminal_matching_state(result_data, target_cls, state) for state in ResultState.VALID_TERMINAL_STATES
    )


@dataclass(frozen=True)
class CorrelatedOperationOutcome:
    """Outcome of observing result events after a single StartSelectedJoining invocation."""

    operation_confirmed: bool = False
    operation_result: Optional[Any] = None
    terminal_result: Optional[Any] = None
    latest_result: Optional[Any] = None
    timed_out: bool = False
    queue_overflow_count: int = 0


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
    observed_terminal_result: Optional[Any] = None

    @property
    def terminal_result(self) -> Optional[Any]:
        return self.observed_terminal_result if self.observed_terminal_result is not None else self.final_result

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


def retained_single_result(outcome: Any) -> Any | None:
    """Preserve typed workflow failures and consume owned evidence without waiting for replay."""
    from helpers.cu_coverage_report import WorkflowEvidenceUnavailable

    if not outcome.triggered:
        reason_code = getattr(outcome, "reason_code", "")
        disposition = getattr(outcome, "execution_outcome", "")
        if disposition == "failed":
            raise AssertionError(f"{reason_code}: {outcome.skip_reason}")
        if reason_code or disposition:
            raise WorkflowEvidenceUnavailable(
                outcome.skip_reason or "Result workflow unavailable.",
                reason_code or "result_workflow_unavailable",
                "inconclusive" if getattr(outcome, "mutation_attempted", False) else "blocked",
                "single_result",
            )
        return None
    progression = getattr(outcome, "result_progression", None)
    if progression is None:
        return None
    if not progression.is_complete or not is_terminal_completed(
        progression.final_result, ResultClassification.SINGLE_RESULT
    ):
        raise WorkflowEvidenceUnavailable(
            "Owned SingleResult evidence is incomplete.", "result_evidence_incomplete", "inconclusive", "single_result"
        )
    return progression.final_result


async def collect_single_evidence(
    subscription_client: Any,
    result_trigger: Any,
    ns_indices: dict,
    result_type: int,
    *,
    include_traces: bool = False,
    fresh: bool = False,
) -> Any | None:
    """Use immutable evidence for content checks, with explicit freshness for progression checks."""
    from helpers.result_validator import check_result_expectations

    cached = getattr(result_trigger, "get_reusable_progression", None)
    if not fresh and cached is not None:
        progression = await cached(ResultClassification.SINGLE_RESULT)
        if progression is not None:
            return check_result_expectations(
                retained_single_result(SimpleNamespace(triggered=True, result_progression=progression)), result_trigger
            )
    if getattr(result_trigger, "owns_result_subscription", False):
        outcome = await result_trigger.trigger_single(result_type, include_traces=include_traces)
        result = retained_single_result(outcome)
        if result is None and outcome.triggered:
            from helpers.cu_coverage_report import WorkflowEvidenceUnavailable

            raise WorkflowEvidenceUnavailable(
                "The owning trigger returned no SingleResult capture.",
                "result_evidence_incomplete",
                "inconclusive",
                "single_result",
            )
        return check_result_expectations(result, result_trigger)
    async with ResultCollector(subscription_client, ns_indices, is_simulator=result_trigger.is_simulator) as collector:
        outcome = await result_trigger.trigger_single(result_type, include_traces=include_traces)
        return check_result_expectations(await collector.collect_triggered_single(outcome), result_trigger)


class ResultCollector:
    """
    Context manager that subscribes to Machinery ResultReadyEventType and its
    subtypes before a trigger and collects matching results afterwards.

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
        result_observer: Callable[[Any, bool], None] | None = None,
        parent_result_reader: Callable[[str], Awaitable[Any | None]] | None = None,
    ) -> None:
        self._client = subscription_client
        self._ns_indices = ns_indices
        self._is_simulator = is_simulator
        self._result_observer = result_observer
        self._parent_result_reader = parent_result_reader
        self._parent_context: dict[str, Any] = {}
        self._collector: Optional[EventCollector] = None
        self._captured_results: list[Any] = []
        self._captured_source_events: list[Any] = []
        self._captured_event_ids: set[tuple[str, Any]] = set()
        self._captured_duplicate_count = 0
        self._confirmed_operation_ids: set[str] = set()
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

        ns_result = self._ns_indices.get(NS_MACH_RESULT)
        if ns_result is None:
            ns_result = await self._client.get_namespace_index(NS_MACH_RESULT)
        server_node = self._client.nodes.server
        event_type_node = self._client.get_node(ua.NodeId(MachineryResultTypes.RESULT_READY_EVENT_TYPE, ns_result))

        self._captured_results.clear()
        self._captured_source_events.clear()
        self._captured_event_ids.clear()
        self._captured_duplicate_count = 0
        self._confirmed_operation_ids.clear()
        self._parent_context.clear()
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
        raw = getattr(event, "Result", None)
        result_data = unwrap_result(raw) if raw is not None else None
        if self._result_observer is not None:
            self._result_observer(result_data, identity in self._captured_event_ids)
        if identity in self._captured_event_ids:
            self._captured_duplicate_count += 1
            return None
        self._captured_event_ids.add(identity)
        self._captured_source_events.append(event)
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
                    child_is_resolved = is_terminal_result(child, child_classification) or (
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
                            is_terminal_result(candidate, get_classification(candidate))
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
                            is_terminal_result(candidate, get_classification(candidate))
                            or (allow_partial_results and is_partial(candidate))
                        )
                    ]
                    if candidates:
                        resolved.add(reference_id)
                        pending.extend(candidates)

        return tuple(sorted(required - resolved))

    async def collect_triggered_single(self, outcome: Any, timeout_s: Optional[float] = None) -> Any | None:
        retained = retained_single_result(outcome)
        if retained is not None or not outcome.triggered:
            return retained
        return await self.collect_single(timeout_s)

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

        return replace(self.capture(), timed_out=not satisfied)

    def capture(self) -> ResultEventCapture:
        if self._collector is None:
            raise RuntimeError("ResultCollector is not active — use as async context manager")
        dropped = getattr(self._collector, "dropped_event_count", 0)
        return ResultEventCapture(
            all_results=tuple(self._captured_results),
            source_events=tuple(self._captured_source_events),
            duplicate_event_count=self._captured_duplicate_count,
            queue_overflow_count=dropped if isinstance(dropped, int) and not isinstance(dropped, bool) else 0,
        )

    def capture_pending(self) -> ResultEventCapture:
        if self._collector is None:
            raise RuntimeError("ResultCollector is not active — use as async context manager")
        for event in self._collector.collect_pending():
            self._record_event(event)
        return self.capture()

    @classmethod
    def related_capture(cls, progression: ResultProgression) -> ResultEventCapture:
        """Expand inline child envelopes and retain only the completed parent's reference graph."""
        candidates = cls._expand_inline_results((*progression.all_results, progression.terminal_result))
        root = progression.terminal_result
        related = tuple(
            result
            for result in candidates
            if result is root or references_result_id(root, get_result_id(result), candidates)
        )
        return ResultEventCapture(
            all_results=related,
            source_events=progression.source_events,
            duplicate_event_count=progression.duplicate_event_count,
            queue_overflow_count=progression.queue_overflow_count,
        )

    @staticmethod
    def _expand_inline_results(results: tuple[Any, ...]) -> tuple[Any, ...]:
        candidates = list({id(result): result for result in results if result is not None}.values())
        pending = list(candidates)
        visited: set[int] = set()
        while pending:
            result = pending.pop()
            if id(result) in visited:
                continue
            visited.add(id(result))
            if get_result_id(result) and all(result is not candidate for candidate in candidates):
                candidates.append(result)
            for raw in getattr(result, "ResultContent", None) or ():
                child = unwrap_result(raw)
                if get_result_id(child):
                    pending.append(child)
        return tuple(candidates)

    @classmethod
    def has_owned_ancestry(
        cls,
        result_data: Any,
        classification: int | None,
        predicate: Callable[[Any], bool],
        related_results: tuple[Any, ...],
        *,
        excluded_root_ids: frozenset[str] = frozenset(),
    ) -> bool:
        """Prove ownership through observed child references or typed parent-result links."""
        ancestry = cls._expand_inline_results(related_results)
        roots = tuple(
            parent
            for parent in ancestry
            if get_result_id(parent)
            and get_result_id(parent) not in excluded_root_ids
            and get_classification(parent) == classification
        )
        parents_by_id: dict[str, list[Any]] = {}
        for parent in ancestry:
            parents_by_id.setdefault(get_result_id(parent), []).append(parent)
        pending = [result_data]
        visited: set[int] = set()
        owned = False
        foreign = False
        while pending:
            current = pending.pop()
            result_id = get_result_id(current)
            if not result_id or id(current) in visited:
                continue
            visited.add(id(current))
            for root in roots:
                if result_id == get_result_id(root) or references_result_id(root, result_id, ancestry):
                    if predicate(root):
                        owned = True
                    else:
                        foreign = True
            for parent_id in parent_result_ids(current):
                pending.extend(parents_by_id.get(parent_id, ()))
        return owned and not foreign

    async def _read_missing_parent_context(
        self,
        candidates: tuple[Any, ...],
        related_results: tuple[Any, ...],
        deadline: float,
        queried_parent_ids: set[str],
    ) -> None:
        """Read only explicitly linked ancestors; never add stored data to fresh event evidence."""
        if self._parent_result_reader is None:
            return
        by_id = {
            get_result_id(result): result
            for result in self._expand_inline_results((*self._parent_context.values(), *related_results))
        }
        pending = list(candidates)
        visited: set[str] = set()
        loop = asyncio.get_running_loop()
        while pending:
            result = pending.pop()
            result_id = get_result_id(result)
            if not result_id or result_id in visited:
                continue
            visited.add(result_id)
            for parent_id in parent_result_ids(result):
                if parent_id in visited:
                    continue
                parent = by_id.get(parent_id)
                if parent is None:
                    if parent_id in queried_parent_ids:
                        continue
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        return
                    queried_parent_ids.add(parent_id)
                    try:
                        parent = unwrap_result(
                            await asyncio.wait_for(self._parent_result_reader(parent_id), timeout=remaining)
                        )
                    except TimeoutError:
                        logger.warning(
                            "Parent result lookup for %s exceeded the operation evidence deadline", parent_id
                        )
                        return
                    if parent is None:
                        visited.add(parent_id)
                        continue
                    if get_result_id(parent) != parent_id:
                        raise ValueError(f"Parent result lookup returned a different ResultId for {parent_id}")
                    self._parent_context[parent_id] = parent
                    by_id[parent_id] = parent
                pending.append(parent)

    @classmethod
    def progression_from_capture(
        cls,
        capture: ResultEventCapture,
        classification: int,
        *,
        require_partials: bool = False,
        expected_terminal_state: int = 1,
        allow_partial_references: bool = False,
        require_reference_closure: bool = True,
        predicate: Callable[[Any], bool] | None = None,
        after_result_count: int = 0,
    ) -> ResultProgression:
        """Assess retained evidence without another subscription or physical operation."""
        if isinstance(after_result_count, bool) or after_result_count < 0:
            raise ValueError("after_result_count must be a nonnegative result offset")
        results = capture.all_results
        matching = [
            result
            for result in results[after_result_count:]
            if get_classification(result) == classification and (predicate is None or predicate(result))
        ]
        partials = tuple(result for result in matching if is_partial(result))
        finals = [
            result
            for result in matching
            if is_terminal_matching_state(result, classification, target_state=expected_terminal_state)
        ]
        final = finals[-1] if finals else None
        unexpected = next(
            (
                result
                for result in matching
                if is_terminal_result(result, classification)
                and not is_terminal_matching_state(result, classification, expected_terminal_state)
            ),
            None,
        )
        observed_terminal = unexpected if unexpected is not None else final
        if unexpected is not None:
            final = None
        unresolved = (
            cls._reference_closure(observed_terminal, list(results), allow_partial_results=allow_partial_references)
            if observed_terminal is not None and require_reference_closure
            else ()
        )
        missing_partials = require_partials and not partials
        return ResultProgression(
            classification=classification,
            partial_results=partials,
            final_result=final,
            child_results=tuple(result for result in results if get_classification(result) != classification),
            all_results=results,
            source_events=capture.source_events,
            unresolved_reference_ids=unresolved,
            duplicate_event_count=capture.duplicate_event_count,
            queue_overflow_count=capture.queue_overflow_count,
            timed_out=unexpected is None and (final is None or bool(unresolved) or bool(missing_partials)),
            missing_required_partials=bool(missing_partials),
            observed_terminal_result=observed_terminal,
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
        predicate: Callable[[Any], bool] | None = None,
        after_result_count: int = 0,
    ) -> ResultProgression:
        """Collect all fresh evidence through a terminal consolidated result and child closure."""
        if isinstance(after_result_count, bool) or after_result_count < 0:
            raise ValueError("after_result_count must be a nonnegative result offset")
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
            result
            for result in all_results[after_result_count:]
            if get_classification(result) == classification
            and is_partial(result)
            and (predicate is None or predicate(result))
        ]
        children = [result for result in all_results if get_classification(result) != classification]
        final_result: Optional[Any] = None
        unexpected_terminal: Optional[Any] = None
        for result in all_results[after_result_count:]:
            if (predicate is None or predicate(result)) and is_terminal_result(result, classification):
                if is_terminal_matching_state(result, classification, expected_terminal_state):
                    final_result = result
                else:
                    unexpected_terminal = result
                    final_result = None
                    break
        unresolved: tuple[str, ...] = ()
        if final_result is not None and require_reference_closure:
            unresolved = self._reference_closure(
                final_result,
                all_results,
                allow_partial_results=allow_partial_references,
            )

        while True:
            if unexpected_terminal is not None:
                break
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
            if (
                len(all_results) > after_result_count
                and result_classification == classification
                and (predicate is None or predicate(result_data))
            ):
                if is_partial(result_data):
                    partials.append(result_data)
                elif is_terminal_result(result_data, classification):
                    if is_terminal_matching_state(result_data, classification, expected_terminal_state):
                        final_result = result_data
                    else:
                        unexpected_terminal = result_data
                        final_result = None
                        break
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

        if unexpected_terminal is not None and require_reference_closure:
            unresolved = self._reference_closure(
                unexpected_terminal, all_results, allow_partial_results=allow_partial_references
            )
        missing_partials = require_partials and not partials
        timed_out = unexpected_terminal is None and (final_result is None or bool(unresolved) or missing_partials)
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
            observed_terminal_result=unexpected_terminal if unexpected_terminal is not None else final_result,
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
            self._require_expected_terminal(progression, 1)
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
        self._require_expected_terminal(progression, 1)
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
        operation_context_predicate: Callable[[Any], bool] | None = None,
        ownership_after_result_count: int = 0,
    ) -> CorrelatedOperationOutcome:
        """Consume correlated events from the active subscription stream.

        Observes events until operation evidence or the requested terminal result is found,
        then drains for up to terminal_drain_seconds to catch an immediate terminal result.
        """
        if self._collector is None:
            raise RuntimeError("ResultCollector is not active — use as async context manager")
        if (
            not isinstance(ownership_after_result_count, int)
            or isinstance(ownership_after_result_count, bool)
            or ownership_after_result_count < 0
        ):
            raise ValueError("ownership_after_result_count must be a nonnegative result offset")

        loop = asyncio.get_running_loop()
        deadline = loop.time() + operation_timeout_s
        operation_confirmed = False
        operation_result: Optional[Any] = None
        latest_result: Optional[Any] = None
        operation_predicate = operation_predicate or predicate
        first_candidate = len(self._captured_results)
        queried_parent_ids: set[str] = set()
        prior = self._expand_inline_results((*self._parent_context.values(), *self._captured_results))
        prior_operation_ids = {
            get_result_id(result)
            for result in prior
            if is_terminal_completed(result, ResultClassification.SINGLE_RESULT)
        }
        prior_terminal_ids = {
            get_result_id(result) for result in prior if is_terminal_result(result, requested_result_classification)
        }

        def capture_loss() -> CorrelatedOperationOutcome | None:
            dropped = getattr(self._collector, "dropped_event_count", 0)
            if isinstance(dropped, int) and dropped > 0:
                return CorrelatedOperationOutcome(timed_out=True, queue_overflow_count=dropped)
            return None

        def find_operation() -> Any | None:
            candidates = self._expand_inline_results(tuple(self._captured_results[first_candidate:]))
            for candidate in candidates:
                result_id = get_result_id(candidate)
                if (
                    not result_id
                    or result_id in prior_operation_ids
                    or result_id in self._confirmed_operation_ids
                    or not is_terminal_completed(candidate, ResultClassification.SINGLE_RESULT)
                    or (operation_context_predicate is not None and not operation_context_predicate(candidate))
                ):
                    continue
                if operation_predicate(candidate) or self.has_owned_ancestry(
                    candidate,
                    requested_result_classification,
                    predicate,
                    (*self._parent_context.values(), *self._captured_results[ownership_after_result_count:]),
                    excluded_root_ids=frozenset(prior_terminal_ids),
                ):
                    return candidate
            return None

        def find_terminal() -> Any | None:
            return next(
                (
                    result
                    for result in self._captured_results[first_candidate:]
                    if get_result_id(result)
                    and get_result_id(result) not in prior_terminal_ids
                    and predicate(result)
                    and is_terminal_result(result, requested_result_classification)
                ),
                None,
            )

        while True:
            loss = capture_loss()
            if loss is not None:
                return loss
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            events = await self._collector.collect(count=1, timeout_s=min(remaining, _INNER_POLL_S))
            loss = capture_loss()
            if loss is not None:
                return loss
            if not events:
                continue
            result_data = self._record_event(events[0])
            if result_data is None:
                continue

            latest_result = result_data
            operation_result = find_operation()
            terminal_result = find_terminal()
            if operation_result is None and terminal_result is None and self._parent_result_reader is not None:
                self.capture_pending()
                operation_result = find_operation()
                terminal_result = find_terminal()
                if operation_result is None and terminal_result is None:
                    candidates = tuple(
                        candidate
                        for candidate in self._captured_results[first_candidate:]
                        if is_terminal_completed(candidate, ResultClassification.SINGLE_RESULT)
                        and get_result_id(candidate) not in prior_operation_ids
                        and get_result_id(candidate) not in self._confirmed_operation_ids
                        and (operation_context_predicate is None or operation_context_predicate(candidate))
                    )
                    await self._read_missing_parent_context(
                        candidates,
                        tuple(self._captured_results[ownership_after_result_count:]),
                        deadline,
                        queried_parent_ids,
                    )
                    loss = capture_loss()
                    if loss is not None:
                        return loss
                    operation_result = find_operation()

            loss = capture_loss()
            if loss is not None:
                return loss
            if terminal_result is not None:
                if operation_result is not None:
                    self._confirmed_operation_ids.add(get_result_id(operation_result))
                return CorrelatedOperationOutcome(
                    operation_confirmed=True,
                    operation_result=operation_result,
                    terminal_result=terminal_result,
                    latest_result=terminal_result,
                    timed_out=False,
                )

            if operation_result is not None:
                operation_confirmed = True
                self._confirmed_operation_ids.add(get_result_id(operation_result))
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
                loss = capture_loss()
                if loss is not None:
                    return loss
                drain_rem = drain_deadline - loop.time()
                if drain_rem <= 0:
                    break
                events = await self._collector.collect(count=1, timeout_s=min(drain_rem, 0.05))
                loss = capture_loss()
                if loss is not None:
                    return loss
                if not events:
                    continue
                result_data = self._record_event(events[0])
                if result_data is None:
                    continue
                latest_result = result_data
                if (
                    get_result_id(result_data)
                    and get_result_id(result_data) not in prior_terminal_ids
                    and predicate(result_data)
                    and is_terminal_result(result_data, requested_result_classification)
                ):
                    return capture_loss() or CorrelatedOperationOutcome(
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
        """Return any owned terminal state. The workflow separately qualifies its expected state."""
        if self._collector is None:
            raise RuntimeError("ResultCollector is not active — use as async context manager")
        for event in self._collector.collect_pending():
            result_data = self._record_event(event)
            if (
                result_data is not None
                and predicate(result_data)
                and is_terminal_result(result_data, requested_result_classification)
            ):
                return result_data
        return None

    def discard_pending(self) -> int:
        """Discard queued notifications before a correlated operation starts."""
        if self._collector is None:
            raise RuntimeError("ResultCollector is not active — use as async context manager")
        return self._collector.discard_pending()

    @staticmethod
    def _require_expected_terminal(progression: ResultProgression, expected_state: int) -> None:
        terminal = progression.terminal_result
        if terminal is not None and is_terminal_result(terminal, progression.classification):
            assert is_terminal_matching_state(terminal, progression.classification, expected_state), (
                f"Result {get_result_id(terminal)} terminated in state "
                f"{unwrap_result(getattr(terminal.ResultMetaData, 'ResultState', None))}, expected {expected_state}"
            )

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
