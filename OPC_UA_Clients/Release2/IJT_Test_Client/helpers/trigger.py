"""
Trigger abstraction for the IJT OPC UA Test Framework.
Decouples test logic from the trigger mechanism, allowing the same tests to run against:
  - OPC UA Simulator servers (SimulateXxx methods called automatically)
  - Real controllers (no automatic trigger; test waits for an externally triggered result/event)
  - Custom controller adapters (subclass SimulatorTrigger or ExternalTrigger as needed)

Usage in tests::

    # Simulator - result trigger:
    outcome = await result_trigger.trigger_single(ResultType.ONE_STEP_OK_RESULT, include_traces=True)
    if not outcome.triggered:
        pytest.skip(outcome.skip_reason)

    # Simulator - event trigger:
    outcome = await event_trigger.trigger_event(SimulateEventType.TOOL_CONNECTED, count=2)
    if not outcome.triggered:
        pytest.skip(outcome.skip_reason)

    # Real controller: outcome.triggered=False, outcome.skip_reason is set -> test calls pytest.skip()

Controller teams can extend by subclassing::

    class MyControllerTrigger(ResultTrigger):
        async def trigger_single(self, result_type, include_traces=False):
            # send command to real controller
            ...
"""

from __future__ import annotations

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from asyncua import ua

from helpers.namespaces import BN
from helpers.node_discovery import find_child_by_browse_name

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 60.0  # seconds - job results can be slow
_EXTERNAL_SKIP_REASON = "External trigger required - run test with a real controller and trigger manually"

# Evidence-wait budgets.  These are deliberately split so a test never spends a
# long completion budget when nothing was actively started, and never uses a
# short passive-observation budget after a remote start was accepted.
#
#   active   - an operation was actively started by the trigger and a correlated
#              result/event MUST arrive; sized for a real joining cycle.
#   passive  - nothing was started by the test; the trigger only observes
#              whatever the server produces on its own.  Kept short so an
#              unattended run cannot stall for hours.
DEFAULT_SIMULATOR_ACTIVE_RESULT_TIMEOUT_S = 15.0
DEFAULT_SIMULATOR_PASSIVE_OBSERVATION_TIMEOUT_S = 15.0
DEFAULT_EXTERNAL_ACTIVE_RESULT_TIMEOUT_S = 90.0
DEFAULT_EXTERNAL_PASSIVE_OBSERVATION_TIMEOUT_S = 10.0

# Environment overrides used by target server runs (set by
# helpers/target_server_execution.py from the loaded profile).
ENV_ACTIVE_RESULT_TIMEOUT = "OPCUA_TARGET_ACTIVE_RESULT_TIMEOUT_SECONDS"
ENV_PASSIVE_OBSERVATION_TIMEOUT = "OPCUA_TARGET_PASSIVE_OBSERVATION_TIMEOUT_SECONDS"


def _positive_float_env(name: str) -> float | None:
    """Return a positive float from *name*, or None when unset/invalid."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        logger.warning("Ignoring invalid %s=%r", name, raw)
        return None
    return value if value > 0 else None


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
        inconclusive: True when optional server evidence is unavailable, rather than invalid.
    """

    triggered: bool
    skip_reason: str | None = field(default=None)
    method: str | None = field(default=None)
    inconclusive: bool = False


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

    @property
    def active_result_timeout_s(self) -> float:
        """Seconds to wait for a result/event after this trigger started an operation.

        Only valid after a trigger method returned ``triggered=True``.  Sized for
        a complete joining cycle on the server under test.
        """
        return _positive_float_env(ENV_ACTIVE_RESULT_TIMEOUT) or DEFAULT_EXTERNAL_ACTIVE_RESULT_TIMEOUT_S

    @property
    def passive_observation_timeout_s(self) -> float:
        """Seconds to observe server-generated evidence when nothing was started.

        Deliberately short so unattended runs cannot stall waiting for an
        operator action that will never happen.
        """
        return _positive_float_env(ENV_PASSIVE_OBSERVATION_TIMEOUT) or DEFAULT_EXTERNAL_PASSIVE_OBSERVATION_TIMEOUT_S

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

    async def trigger_abort_job(self) -> TriggerOutcome:
        """Return an unsupported outcome unless an adapter implements abort."""
        return TriggerOutcome(
            triggered=False,
            skip_reason="This result trigger does not implement an autonomous abort workflow",
            method=BN.ABORT_JOINING_PROCESS,
        )

    async def trigger_reset_job(self) -> TriggerOutcome:
        """Return an unsupported outcome unless an adapter implements reset."""
        return TriggerOutcome(
            triggered=False,
            skip_reason="This result trigger does not implement an autonomous reset workflow",
            method=BN.RESET_JOINING_PROCESS,
        )


class EventTrigger(ABC):
    """Abstract base for event-trigger implementations.

    Concrete subclasses either call SimulateXxx OPC UA methods (simulator) or
    return an "external trigger required" outcome (real controller).
    """

    @property
    @abstractmethod
    def is_simulator(self) -> bool:
        """True when this trigger drives the OPC UA simulator."""

    @property
    def active_event_timeout_s(self) -> float:
        """Seconds to wait for an event after this trigger fired one."""
        return _positive_float_env(ENV_ACTIVE_RESULT_TIMEOUT) or DEFAULT_EXTERNAL_ACTIVE_RESULT_TIMEOUT_S

    @property
    def passive_observation_timeout_s(self) -> float:
        """Seconds to observe server-generated events when nothing was triggered."""
        return _positive_float_env(ENV_PASSIVE_OBSERVATION_TIMEOUT) or DEFAULT_EXTERNAL_PASSIVE_OBSERVATION_TIMEOUT_S

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
        """True - this trigger drives the OPC UA simulator."""
        return True

    @property
    def active_result_timeout_s(self) -> float:
        """Simulator results are generated immediately; a short budget is enough."""
        return DEFAULT_SIMULATOR_ACTIVE_RESULT_TIMEOUT_S

    @property
    def passive_observation_timeout_s(self) -> float:
        """Simulator passive observation uses the same short budget."""
        return DEFAULT_SIMULATOR_PASSIVE_OBSERVATION_TIMEOUT_S

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

    async def trigger_abort_job(self) -> TriggerOutcome:
        """Call SimulateJobResult or return skip outcome."""
        return TriggerOutcome(
            triggered=False,
            skip_reason="Simulator does not implement autonomous abort workflow simulation",
            method=BN.ABORT_JOINING_PROCESS,
        )

    async def trigger_reset_job(self) -> TriggerOutcome:
        """Call SimulateJobResult or return skip outcome."""
        return TriggerOutcome(
            triggered=False,
            skip_reason="Simulator does not implement autonomous reset workflow simulation",
            method=BN.RESET_JOINING_PROCESS,
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
        """True - this trigger drives the OPC UA simulator."""
        return True

    @property
    def active_event_timeout_s(self) -> float:
        """Simulator events are fired immediately; a short budget is enough."""
        return DEFAULT_SIMULATOR_ACTIVE_RESULT_TIMEOUT_S

    @property
    def passive_observation_timeout_s(self) -> float:
        """Simulator passive observation uses the same short budget."""
        return DEFAULT_SIMULATOR_PASSIVE_OBSERVATION_TIMEOUT_S

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
    """No-op trigger for real controllers - tests must be triggered externally.

    All trigger methods immediately return a ``TriggerOutcome(triggered=False)``
    with a human-readable ``skip_reason``.  Tests should call ``pytest.skip()``
    when they receive this outcome.

    Args:
        wait_timeout_s: Explicit passive-observation budget in seconds.  When
                        greater than 0 it overrides the environment/default
                        value returned by ``passive_observation_timeout_s``.
    """

    @property
    def is_simulator(self) -> bool:
        """False - external trigger required for real controllers."""
        return False

    def __init__(self, wait_timeout_s: float = 0.0) -> None:
        self._wait_timeout_s = wait_timeout_s

    @property
    def active_result_timeout_s(self) -> float:
        """This trigger never starts an operation - observation budget only."""
        return self.passive_observation_timeout_s

    @property
    def passive_observation_timeout_s(self) -> float:
        """Explicit constructor budget, else the environment/passive default."""
        if self._wait_timeout_s > 0:
            return self._wait_timeout_s
        return _positive_float_env(ENV_PASSIVE_OBSERVATION_TIMEOUT) or DEFAULT_EXTERNAL_PASSIVE_OBSERVATION_TIMEOUT_S

    def _skip(self, method: str) -> TriggerOutcome:
        return TriggerOutcome(triggered=False, skip_reason=_EXTERNAL_SKIP_REASON, method=method)

    async def trigger_single(self, result_type: int, include_traces: bool = False) -> TriggerOutcome:
        """Return skip outcome - external trigger required."""
        return self._skip(BN.SIMULATE_SINGLE_RESULT)

    async def trigger_batch_or_sync(
        self,
        classification: int,
        num_children: int = 3,
        include_traces: bool = False,
        send_as_refs: bool = False,
    ) -> TriggerOutcome:
        """Return skip outcome - external trigger required."""
        return self._skip(BN.SIMULATE_BATCH_OR_SYNC_RESULT)

    async def trigger_job(self, send_as_refs: bool = False) -> TriggerOutcome:
        """Return skip outcome - external trigger required."""
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
        """Return skip outcome - external trigger required."""
        return self._skip(BN.SIMULATE_BULK_RESULTS)

    async def trigger_abort_job(self) -> TriggerOutcome:
        """Return skip outcome - external trigger required."""
        return self._skip(BN.ABORT_JOINING_PROCESS)

    async def trigger_reset_job(self) -> TriggerOutcome:
        """Return skip outcome - external trigger required."""
        return self._skip(BN.RESET_JOINING_PROCESS)


class ExternalEventTrigger(EventTrigger):
    """No-op trigger for real controllers - events must be triggered externally.

    All trigger methods immediately return a ``TriggerOutcome(triggered=False)``
    with a human-readable ``skip_reason``.  Tests should call ``pytest.skip()``
    when they receive this outcome.

    Args:
        wait_timeout_s: Explicit passive-observation budget in seconds.  When
                        greater than 0 it overrides the environment/default
                        value returned by ``passive_observation_timeout_s``.
    """

    @property
    def is_simulator(self) -> bool:
        """False - external trigger required for real controllers."""
        return False

    def __init__(self, wait_timeout_s: float = 0.0) -> None:
        self._wait_timeout_s = wait_timeout_s

    @property
    def active_event_timeout_s(self) -> float:
        """This trigger never fires an event - observation budget only."""
        return self.passive_observation_timeout_s

    @property
    def passive_observation_timeout_s(self) -> float:
        """Explicit constructor budget, else the environment/passive default."""
        if self._wait_timeout_s > 0:
            return self._wait_timeout_s
        return _positive_float_env(ENV_PASSIVE_OBSERVATION_TIMEOUT) or DEFAULT_EXTERNAL_PASSIVE_OBSERVATION_TIMEOUT_S

    def _skip(self, method: str) -> TriggerOutcome:
        return TriggerOutcome(triggered=False, skip_reason=_EXTERNAL_SKIP_REASON, method=method)

    async def trigger_event(self, event_type: int, count: int = 1) -> TriggerOutcome:
        """Return skip outcome - external trigger required."""
        return self._skip(BN.SIMULATE_EVENTS)

    async def trigger_bulk_events(
        self,
        event_type: int,
        count: int,
        from_seq: int,
        to_seq: int,
        min_duration_ms: int = 100,
    ) -> TriggerOutcome:
        """Return skip outcome - external trigger required."""
        return self._skip(BN.SIMULATE_BULK_EVENTS)

    async def trigger_condition(self, event_type: int) -> TriggerOutcome:
        """Return skip outcome - external trigger required."""
        return self._skip(BN.SIMULATE_CONDITIONS)


# ---------------------------------------------------------------------------
# Simulator helper-node discovery
# ---------------------------------------------------------------------------


async def find_simulation_child(joining_system_node, ns_app: int | None, child_browse_name: str):
    """Return a simulator helper folder under ``JoiningSystem/Simulations``.

    This is the one lookup path used for simulator helper nodes: the pytest
    trigger fixtures and the SUT-manifest ``simulate_methods`` trigger mode both
    call it, so a manifest-driven run locates exactly the same nodes as the
    default simulator run.

    Args:
        joining_system_node:  JoiningSystem OPC UA Node.
        ns_app:               Application namespace index, or ``None`` when the
                              application namespace is not registered.
        child_browse_name:    Browse name of the wanted folder, e.g.
                              ``BN.SIMULATE_RESULTS_FOLDER``.

    Returns:
        The folder node, or ``None`` when the server exposes no such helper.
    """
    if ns_app is None:
        return None
    simulations = await find_child_by_browse_name(joining_system_node, BN.SIMULATIONS, ns_app)
    if simulations is None:
        return None
    return await find_child_by_browse_name(simulations, child_browse_name, ns_app)


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
