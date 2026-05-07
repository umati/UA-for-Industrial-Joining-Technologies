"""
Trigger abstraction for the IJT OPC UA Test Framework.
Decouples test logic from the trigger mechanism, allowing the same tests to run against:
  - OPC UA Simulator servers (SimulateXxx methods called automatically)
  - Real controllers (no automatic trigger; test waits for an externally triggered result/event)
  - Custom controller adapters (subclass SimulatorTrigger or ExternalTrigger as needed)

Usage in tests::

    # Simulator — result trigger:
    outcome = await result_trigger.trigger_single(ResultType.ONE_STEP_OK_RESULT, include_traces=True)
    if not outcome.triggered:
        pytest.skip(outcome.skip_reason)

    # Simulator — event trigger:
    outcome = await event_trigger.trigger_event(SimulateEventType.TOOL_CONNECTED, count=2)
    if not outcome.triggered:
        pytest.skip(outcome.skip_reason)

    # Real controller: outcome.triggered=False, outcome.skip_reason is set → test calls pytest.skip()

Controller teams can extend by subclassing::

    class MyControllerTrigger(ResultTrigger):
        async def trigger_single(self, result_type, include_traces=False):
            # send command to real controller
            ...
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from asyncua import ua

from helpers.namespaces import BN
from helpers.node_discovery import find_child_by_browse_name

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 60.0  # seconds — job results can be slow
_EXTERNAL_SKIP_REASON = "External trigger required — run test with a real controller and trigger manually"


# ---------------------------------------------------------------------------
# TriggerOutcome
# ---------------------------------------------------------------------------


@dataclass
class TriggerOutcome:
    """Result returned by every trigger method.

    Attributes:
        triggered:   True when the trigger method was called successfully.
        skip_reason: Human-readable reason to pass to pytest.skip() when triggered=False.
        method:      Name of the OPC UA method that was invoked (for logging/debugging).
    """

    triggered: bool
    skip_reason: str | None = field(default=None)
    method: str | None = field(default=None)


# ---------------------------------------------------------------------------
# Abstract base classes
# ---------------------------------------------------------------------------


class ResultTrigger(ABC):
    """Abstract base for result-trigger implementations.

    Concrete subclasses either call SimulateXxx OPC UA methods (simulator) or
    return an "external trigger required" outcome (real controller).
    """

    @property
    @abstractmethod
    def is_simulator(self) -> bool:
        """True when this trigger drives the OPC UA simulator."""

    @abstractmethod
    async def trigger_single(self, result_type: int, include_traces: bool = False) -> TriggerOutcome:
        """Trigger a single tightening result.

        Args:
            result_type:    ResultType enum value (UInt32).
            include_traces: Whether to include step traces in the result.

        Returns:
            TriggerOutcome with triggered=True on success.
        """

    @abstractmethod
    async def trigger_batch_or_sync(
        self,
        classification: int,
        num_children: int = 3,
        include_traces: bool = False,
        send_as_refs: bool = False,
    ) -> TriggerOutcome:
        """Trigger a batch or synchronised tightening result.

        Args:
            classification: ResultClassification Byte value (e.g. 2=Sync, 3=Batch).
            num_children:   Number of child results to generate.
            include_traces: Whether to include step traces.
            send_as_refs:   Whether child results are sent as node references.

        Returns:
            TriggerOutcome with triggered=True on success.
        """

    @abstractmethod
    async def trigger_job(self, send_as_refs: bool = False) -> TriggerOutcome:
        """Trigger a job result (collection of tightening results).

        Args:
            send_as_refs: Whether child results are sent as node references.

        Returns:
            TriggerOutcome with triggered=True on success.
        """

    @abstractmethod
    async def trigger_bulk_results(
        self,
        result_type: int,
        include_traces: bool,
        from_seq: int,
        to_seq: int,
        min_duration_ms: int = 100,
        update_vars: bool = True,
    ) -> TriggerOutcome:
        """Trigger a bulk sequence of tightening results.

        Args:
            result_type:      ResultType enum value (UInt32).
            include_traces:   Whether to include step traces in each result.
            from_seq:         Starting sequence number (UInt64).
            to_seq:           Ending sequence number (UInt64).
            min_duration_ms:  Minimum time between results in milliseconds (Int64).
            update_vars:      Whether to update live variables after each result.

        Returns:
            TriggerOutcome with triggered=True on success.
        """


class EventTrigger(ABC):
    """Abstract base for event-trigger implementations.

    Concrete subclasses either call SimulateXxx OPC UA methods (simulator) or
    return an "external trigger required" outcome (real controller).
    """

    @property
    @abstractmethod
    def is_simulator(self) -> bool:
        """True when this trigger drives the OPC UA simulator."""

    @abstractmethod
    async def trigger_event(self, event_type: int, count: int = 1) -> TriggerOutcome:
        """Trigger one or more events of the given type.

        Args:
            event_type: SimulateEventType enum value (UInt32).
            count:      Number of events to fire (UInt32).

        Returns:
            TriggerOutcome with triggered=True on success.
        """

    @abstractmethod
    async def trigger_bulk_events(
        self,
        event_type: int,
        count: int,
        from_seq: int,
        to_seq: int,
        min_duration_ms: int = 100,
    ) -> TriggerOutcome:
        """Trigger a bulk sequence of events.

        Args:
            event_type:      SimulateEventType enum value (UInt32).
            count:           Total number of events to fire (UInt32).
            from_seq:        Starting sequence number (UInt32).
            to_seq:          Ending sequence number (UInt32).
            min_duration_ms: Minimum time between events in milliseconds (UInt32).

        Returns:
            TriggerOutcome with triggered=True on success.
        """

    @abstractmethod
    async def trigger_condition(self, event_type: int) -> TriggerOutcome:
        """Trigger a retained condition for the given event type.

        Args:
            event_type: SimulateEventType enum value (UInt32).

        Returns:
            TriggerOutcome with triggered=True on success.
        """


# ---------------------------------------------------------------------------
# Simulator implementations
# ---------------------------------------------------------------------------


class SimulatorResultTrigger(ResultTrigger):
    """Drives the OPC UA simulator by calling SimulateXxx methods on the server.

    Locates each method node under *simulate_results_folder_node* using
    ``find_child_by_browse_name``, then calls it via ``folder_node.call_method``.
    All calls are wrapped in ``asyncio.wait_for`` with a generous timeout because
    job results in particular can be slow to generate.

    On ``ua.UaError`` or ``asyncio.TimeoutError`` the call is treated as a
    non-fatal failure: a ``TriggerOutcome(triggered=False)`` is returned so
    that tests can call ``pytest.skip()`` rather than failing hard.

    Args:
        client:                        Active asyncua ``Client`` instance.
        simulate_results_folder_node:  The ``SimulateResults`` folder ``Node``.
        ns_app:                        Namespace index for the application namespace.
    """

    @property
    def is_simulator(self) -> bool:
        """True — this trigger drives the OPC UA simulator."""
        return True

    def __init__(self, client, simulate_results_folder_node, ns_app: int) -> None:
        self._client = client
        self._folder = simulate_results_folder_node
        self._ns_app = ns_app

    async def _find_method(self, browse_name: str):
        """Locate a method node under the SimulateResults folder by BrowseName."""
        node = await find_child_by_browse_name(self._folder, browse_name, self._ns_app)
        return node

    async def _call(self, method_name: str, *args) -> TriggerOutcome:
        """Find and call a method node, returning a TriggerOutcome."""
        method_node = await self._find_method(method_name)
        if method_node is None:
            reason = f"Method node not found: {method_name}"
            logger.warning(reason)
            return TriggerOutcome(triggered=False, skip_reason=reason, method=method_name)
        logger.debug("Calling %s", method_name)
        try:
            await asyncio.wait_for(
                self._folder.call_method(method_node.nodeid, *args),
                timeout=_DEFAULT_TIMEOUT,
            )
        except (ua.UaError, asyncio.TimeoutError) as exc:
            reason = f"{method_name} failed: {exc}"
            logger.warning(reason)
            return TriggerOutcome(triggered=False, skip_reason=reason, method=method_name)
        return TriggerOutcome(triggered=True, method=method_name)

    async def trigger_single(self, result_type: int, include_traces: bool = False) -> TriggerOutcome:
        """Call SimulateSingleResult(result_type, include_traces)."""
        return await self._call(
            BN.SIMULATE_SINGLE_RESULT,
            ua.Variant(result_type, ua.VariantType.UInt32),
            ua.Variant(include_traces, ua.VariantType.Boolean),
        )

    async def trigger_batch_or_sync(
        self,
        classification: int,
        num_children: int = 3,
        include_traces: bool = False,
        send_as_refs: bool = False,
    ) -> TriggerOutcome:
        """Call SimulateBatch_Or_Sync_Result(classification, num_children, include_traces, send_as_refs)."""
        return await self._call(
            BN.SIMULATE_BATCH_OR_SYNC_RESULT,
            ua.Variant(classification, ua.VariantType.Byte),
            ua.Variant(num_children, ua.VariantType.UInt32),
            ua.Variant(include_traces, ua.VariantType.Boolean),
            ua.Variant(send_as_refs, ua.VariantType.Boolean),
        )

    async def trigger_job(self, send_as_refs: bool = False) -> TriggerOutcome:
        """Call SimulateJobResult(send_as_refs)."""
        return await self._call(
            BN.SIMULATE_JOB_RESULT,
            ua.Variant(send_as_refs, ua.VariantType.Boolean),
        )

    async def trigger_bulk_results(
        self,
        result_type: int,
        include_traces: bool,
        from_seq: int,
        to_seq: int,
        min_duration_ms: int = 100,
        update_vars: bool = True,
    ) -> TriggerOutcome:
        """Call SimulateBulkResults(result_type, include_traces, from_seq, to_seq, min_duration_ms, update_vars)."""
        return await self._call(
            BN.SIMULATE_BULK_RESULTS,
            ua.Variant(result_type, ua.VariantType.UInt32),
            ua.Variant(include_traces, ua.VariantType.Boolean),
            ua.Variant(from_seq, ua.VariantType.UInt64),
            ua.Variant(to_seq, ua.VariantType.UInt64),
            ua.Variant(min_duration_ms, ua.VariantType.Int64),
            ua.Variant(update_vars, ua.VariantType.Boolean),
        )


class SimulatorEventTrigger(EventTrigger):
    """Drives the OPC UA simulator by calling SimulateEvents and SimulateBulkEvents.

    Locates each method node under *simulate_events_folder_node* using
    ``find_child_by_browse_name``, then calls it via ``folder_node.call_method``.
    All calls are wrapped in ``asyncio.wait_for`` with a generous timeout.

    On ``ua.UaError`` or ``asyncio.TimeoutError`` the call is treated as a
    non-fatal failure: a ``TriggerOutcome(triggered=False)`` is returned so
    that tests can call ``pytest.skip()`` rather than failing hard.

    Args:
        client:                       Active asyncua ``Client`` instance.
        simulate_events_folder_node:  The ``SimulateEventsAndConditions`` folder ``Node``.
        ns_app:                       Namespace index for the application namespace.
    """

    @property
    def is_simulator(self) -> bool:
        """True — this trigger drives the OPC UA simulator."""
        return True

    def __init__(self, client, simulate_events_folder_node, ns_app: int) -> None:
        self._client = client
        self._folder = simulate_events_folder_node
        self._ns_app = ns_app

    async def _find_method(self, browse_name: str):
        """Locate a method node under the SimulateEventsAndConditions folder by BrowseName."""
        return await find_child_by_browse_name(self._folder, browse_name, self._ns_app)

    async def _call(self, method_name: str, *args) -> TriggerOutcome:
        """Find and call a method node, returning a TriggerOutcome."""
        method_node = await self._find_method(method_name)
        if method_node is None:
            reason = f"Method node not found: {method_name}"
            logger.warning(reason)
            return TriggerOutcome(triggered=False, skip_reason=reason, method=method_name)
        logger.debug("Calling %s", method_name)
        try:
            await asyncio.wait_for(
                self._folder.call_method(method_node.nodeid, *args),
                timeout=_DEFAULT_TIMEOUT,
            )
        except (ua.UaError, asyncio.TimeoutError) as exc:
            reason = f"{method_name} failed: {exc}"
            logger.warning(reason)
            return TriggerOutcome(triggered=False, skip_reason=reason, method=method_name)
        return TriggerOutcome(triggered=True, method=method_name)

    async def trigger_event(self, event_type: int, count: int = 1) -> TriggerOutcome:
        """Call SimulateEvents(event_type).

        The simulator's SimulateEvents method takes only one argument (Event Type).
        The ``count`` parameter is retained in the Python interface for API symmetry
        with ExternalEventTrigger but is not forwarded to the server; the method
        fires a single event per call.  Call it ``count`` times for multiple events.
        """
        if count <= 1:
            return await self._call(
                BN.SIMULATE_EVENTS,
                ua.Variant(event_type, ua.VariantType.UInt32),
            )
        # Fire count individual events sequentially when count > 1
        for _ in range(count):
            outcome = await self._call(
                BN.SIMULATE_EVENTS,
                ua.Variant(event_type, ua.VariantType.UInt32),
            )
            if not outcome.triggered:
                return outcome
        return TriggerOutcome(triggered=True, method=BN.SIMULATE_EVENTS)

    async def trigger_bulk_events(
        self,
        event_type: int,
        count: int,
        from_seq: int,
        to_seq: int,
        min_duration_ms: int = 100,
    ) -> TriggerOutcome:
        """Call SimulateBulkEvents(event_type, count).

        The simulator's SimulateBulkEvents method takes two arguments:
        ``Event Type`` (UInt32) and ``SimulatedEventsCount`` (UInt32).
        The ``from_seq``, ``to_seq``, and ``min_duration_ms`` parameters are
        retained in the Python interface for API symmetry but are not supported
        by the simulator and are not forwarded to the server.
        """
        return await self._call(
            BN.SIMULATE_BULK_EVENTS,
            ua.Variant(event_type, ua.VariantType.UInt32),
            ua.Variant(count, ua.VariantType.UInt32),
        )

    async def trigger_condition(self, event_type: int) -> TriggerOutcome:
        """Call SimulateConditions(event_type)."""
        return await self._call(
            BN.SIMULATE_CONDITIONS,
            ua.Variant(event_type, ua.VariantType.UInt32),
        )


# ---------------------------------------------------------------------------
# External (real controller) implementations
# ---------------------------------------------------------------------------


class ExternalResultTrigger(ResultTrigger):
    """No-op trigger for real controllers — tests must be triggered externally.

    All trigger methods immediately return a ``TriggerOutcome(triggered=False)``
    with a human-readable ``skip_reason``.  Tests should call ``pytest.skip()``
    when they receive this outcome.

    Args:
        wait_timeout_s: Reserved for future use (e.g. polling with a real controller
                        adapter).  Not used by this base implementation.
    """

    @property
    def is_simulator(self) -> bool:
        """False — external trigger required for real controllers."""
        return False

    def __init__(self, wait_timeout_s: float = 0.0) -> None:
        self._wait_timeout_s = wait_timeout_s

    def _skip(self, method: str) -> TriggerOutcome:
        return TriggerOutcome(triggered=False, skip_reason=_EXTERNAL_SKIP_REASON, method=method)

    async def trigger_single(self, result_type: int, include_traces: bool = False) -> TriggerOutcome:
        """Return skip outcome — external trigger required."""
        return self._skip(BN.SIMULATE_SINGLE_RESULT)

    async def trigger_batch_or_sync(
        self,
        classification: int,
        num_children: int = 3,
        include_traces: bool = False,
        send_as_refs: bool = False,
    ) -> TriggerOutcome:
        """Return skip outcome — external trigger required."""
        return self._skip(BN.SIMULATE_BATCH_OR_SYNC_RESULT)

    async def trigger_job(self, send_as_refs: bool = False) -> TriggerOutcome:
        """Return skip outcome — external trigger required."""
        return self._skip(BN.SIMULATE_JOB_RESULT)

    async def trigger_bulk_results(
        self,
        result_type: int,
        include_traces: bool,
        from_seq: int,
        to_seq: int,
        min_duration_ms: int = 100,
        update_vars: bool = True,
    ) -> TriggerOutcome:
        """Return skip outcome — external trigger required."""
        return self._skip(BN.SIMULATE_BULK_RESULTS)


class ExternalEventTrigger(EventTrigger):
    """No-op trigger for real controllers — events must be triggered externally.

    All trigger methods immediately return a ``TriggerOutcome(triggered=False)``
    with a human-readable ``skip_reason``.  Tests should call ``pytest.skip()``
    when they receive this outcome.

    Args:
        wait_timeout_s: Reserved for future use (e.g. polling with a real controller
                        adapter).  Not used by this base implementation.
    """

    @property
    def is_simulator(self) -> bool:
        """False — external trigger required for real controllers."""
        return False

    def __init__(self, wait_timeout_s: float = 0.0) -> None:
        self._wait_timeout_s = wait_timeout_s

    def _skip(self, method: str) -> TriggerOutcome:
        return TriggerOutcome(triggered=False, skip_reason=_EXTERNAL_SKIP_REASON, method=method)

    async def trigger_event(self, event_type: int, count: int = 1) -> TriggerOutcome:
        """Return skip outcome — external trigger required."""
        return self._skip(BN.SIMULATE_EVENTS)

    async def trigger_bulk_events(
        self,
        event_type: int,
        count: int,
        from_seq: int,
        to_seq: int,
        min_duration_ms: int = 100,
    ) -> TriggerOutcome:
        """Return skip outcome — external trigger required."""
        return self._skip(BN.SIMULATE_BULK_EVENTS)

    async def trigger_condition(self, event_type: int) -> TriggerOutcome:
        """Return skip outcome — external trigger required."""
        return self._skip(BN.SIMULATE_CONDITIONS)


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def make_result_trigger(client, simulate_results_folder, ns_app: int) -> ResultTrigger:
    """Return a :class:`SimulatorResultTrigger` or :class:`ExternalResultTrigger`.

    Args:
        client:                   Active asyncua ``Client`` instance.
        simulate_results_folder:  The ``SimulateResults`` folder node, or ``None``
                                  when targeting a real (non-simulated) controller.
        ns_app:                   Namespace index for the application namespace.

    Returns:
        :class:`SimulatorResultTrigger` when *simulate_results_folder* is not ``None``,
        otherwise :class:`ExternalResultTrigger`.
    """
    if simulate_results_folder is not None:
        return SimulatorResultTrigger(client, simulate_results_folder, ns_app)
    return ExternalResultTrigger()


def make_event_trigger(client, simulate_events_folder, ns_app: int) -> EventTrigger:
    """Return a :class:`SimulatorEventTrigger` or :class:`ExternalEventTrigger`.

    Args:
        client:                  Active asyncua ``Client`` instance.
        simulate_events_folder:  The ``SimulateEventsAndConditions`` folder node, or
                                 ``None`` when targeting a real (non-simulated) controller.
        ns_app:                  Namespace index for the application namespace.

    Returns:
        :class:`SimulatorEventTrigger` when *simulate_events_folder* is not ``None``,
        otherwise :class:`ExternalEventTrigger`.
    """
    if simulate_events_folder is not None:
        return SimulatorEventTrigger(client, simulate_events_folder, ns_app)
    return ExternalEventTrigger()
