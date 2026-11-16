"""
Target Server-specific trigger adapters for IJT Target Server CU execution.

Extends the trigger abstraction in helpers/trigger.py without modifying the
simulator trigger behaviour.  Provides:

  StartSelectedJoiningResultTrigger
    Automates result generation via SelectJoiningProcess + StartSelectedJoining.
    Suitable for automated Target Server CU runs.

  ManualResultTrigger
    Subscribes before the joining operation, then waits for a result generated
    by a physical/operator tool trigger.  Used in guided/manual Target Server runs.

  ManualEventTrigger
    Observe-only event adapter for guided/manual runs where events are generated
    by target server state changes rather than simulator helper methods.

Factory functions:

  make_target_server_result_trigger()  — choose adapter based on profile trigger config
  make_target_server_event_trigger()   — choose event adapter based on profile config
  build_target_server_result_trigger() — async: discover simulator helper nodes first
  build_target_server_event_trigger()  — async: discover simulator helper nodes first

A manifest may also declare ``simulate_methods``; the factories then return the
existing :class:`helpers.trigger.SimulatorResultTrigger` /
:class:`helpers.trigger.SimulatorEventTrigger` on the helper nodes discovered by
:func:`helpers.trigger.find_simulation_child` — the same lookup the default
simulator fixtures use. When the helper nodes are absent the factories raise
:class:`TargetServerTriggerConfigurationError` instead of degrading to an
External (no-op) trigger.

These factories preserve the OPCUA_TRIGGER_CLASS override mechanism so that
custom adapter classes can be injected via environment variable, matching the
existing simulator trigger override pattern.

Usage::

    from helpers.target_server_triggers import make_target_server_result_trigger

    trigger = make_target_server_result_trigger(
        client=client,
        joining_system_node=joining_system,
        ns_app=ns_indices[NS_APP],
        profile=target_server_profile,
    )
    outcome = await trigger.trigger_single(result_type, include_traces=False)
    if not outcome.triggered:
        pytest.skip(outcome.skip_reason)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from collections.abc import Awaitable, Callable, Coroutine, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, replace
from functools import wraps
from pathlib import Path
from typing import Any, Concatenate, ParamSpec, TypeVar

from helpers.namespaces import (
    BN,
    ENTITY_TYPE_VALUES,
    JoiningProcessClassification,
    ResultClassification,
    joining_process_classification_value,
    parse_joining_process_classification,
    result_classification_value,
)
from helpers.process_selectors import counter_candidates, matching_processes, selection_names
from helpers.target_server_cu_config import TargetServerCuProfile
from helpers.trigger import (
    EventTrigger,
    ExternalEventTrigger,
    ExternalResultTrigger,
    ResultTrigger,
    SimulatorEventTrigger,
    SimulatorResultTrigger,
    TriggerOutcome,
    find_simulation_child,
)

logger = logging.getLogger(__name__)

_DEFAULT_TARGET_SERVER_TIMEOUT = 120.0  # real joining operations can be slow


def _process_classification(process: Any) -> JoiningProcessClassification | None:
    """Extract JoiningProcessMetaData.Classification without using result enums."""
    from asyncua import ua

    if process is None:
        return None
    entry = process.Value if isinstance(process, ua.Variant) else process
    metadata = getattr(entry, "JoiningProcessMetaData", entry)
    value = getattr(metadata, "Classification", None)
    if value is None:
        return None
    if hasattr(value, "_mock_name") or type(value).__name__ == "MagicMock":
        return None
    raw = value.Value if isinstance(value, ua.Variant) else value
    return parse_joining_process_classification(raw)


class TargetServerTriggerConfigurationError(RuntimeError):
    """Raised when a manifest's trigger configuration cannot be honoured.

    Raised instead of degrading to a no-op trigger, so a manifest that claims a
    capability the server does not expose fails as a configuration error rather
    than as a run full of unexplained skips.
    """


# ---------------------------------------------------------------------------
# Extended TriggerOutcome with target_server-specific metadata
# ---------------------------------------------------------------------------


@dataclass
class TargetServerTriggerOutcome(TriggerOutcome):
    """TriggerOutcome extended with target_server-execution metadata.

    All existing TriggerOutcome fields are preserved for backward compatibility.
    TargetServer-specific metadata fields are additive and optional so that
    existing tests using TriggerOutcome are unaffected.

    Attributes:
        trigger_mode:           Which trigger strategy was used.
        product_instance_uri:   Tool PIU used for the joining operation.
        joining_process_id:     Joining process ID selected.
        joining_process_origin_id: Joining process origin ID selected.
        operation_count:        Alias of ``starts_issued``, kept for backward
                                compatibility with existing callers/reports.
        starts_issued:          StartSelectedJoining calls the server accepted.
        results_confirmed:      Correlated results this trigger actually observed.
                                0 when the trigger did not subscribe for
                                completion evidence (single-operation runs leave
                                that verification to the test itself), so
                                ``starts_issued > results_confirmed`` means
                                "started but not confirmed".
        pre_trigger_baseline:   Snapshot captured before the trigger.
        candidate_process_ids:  Ordered process IDs actually attempted.
        proven_process_ids:     Candidates that emitted the requested evidence.
        rejected_process_ids:   Attempted candidates that did not prove capability.
    """

    trigger_mode: str = ""
    product_instance_uri: str = ""
    joining_process_id: str = ""
    joining_process_origin_id: str = ""
    operation_count: int = 0
    starts_issued: int = 0
    results_confirmed: int = 0
    pre_trigger_baseline: dict[str, Any] = field(default_factory=dict)
    mutation_attempted: bool = False
    prior_unresolved_action: dict[str, Any] = field(default_factory=dict)
    execution_outcome: str = ""
    reason_code: str = ""
    evidence_reused: bool = False
    candidate_process_ids: tuple[str, ...] = ()
    proven_process_ids: tuple[str, ...] = ()
    rejected_process_ids: tuple[str, ...] = ()
    result_progression: Any | None = None
    claim_mismatch: bool = False
    expected_event_entity_ids: tuple[str, ...] = ()
    process_progression: Any | None = None
    method_call_result: Any | None = None
    process_settled: bool = False


@dataclass(frozen=True)
class WorkflowEvidenceKey:
    """Inputs that make captured result evidence safe to reuse within this process."""

    endpoint: str
    application_name: str
    application_version: str
    client_identity: int
    product_instance_uri: str
    joining_process_id: str
    joining_process_origin_id: str
    process_list_fingerprint: tuple[tuple[str, str, int | None], ...]
    result_classification: int
    selection_policy: str
    operation_count: int
    require_partials: bool
    referenced_child_completion_policy: str
    max_start_invocations: int
    consecutive_start_delay_seconds: float
    observed_server_epoch: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowEvidenceRecord:
    """Immutable run-scoped result progression with capture provenance."""

    key: WorkflowEvidenceKey
    progression: Any
    captured_monotonic: float


_COUNTER_ATTEMPTS: dict[tuple, TargetServerTriggerOutcome | None] = {}


@dataclass
class ControlledWorkflowScope:
    claims: set[str] = field(default_factory=set)
    dispatches: list[tuple[str, str, str]] = field(default_factory=list)
    depth: int = 0
    adapters: set[int] = field(default_factory=set)


_WorkflowArgs = ParamSpec("_WorkflowArgs")
_WorkflowResult = TypeVar("_WorkflowResult")
_WorkflowReceiver = TypeVar("_WorkflowReceiver")


def _owned_workflow(
    action: Callable[Concatenate[_WorkflowReceiver, _WorkflowArgs], Awaitable[_WorkflowResult]],
) -> Callable[Concatenate[_WorkflowReceiver, _WorkflowArgs], Coroutine[Any, Any, _WorkflowResult]]:
    @wraps(action)
    async def invoke(
        receiver: _WorkflowReceiver, *args: _WorkflowArgs.args, **kwargs: _WorkflowArgs.kwargs
    ) -> _WorkflowResult:
        with _RUN_SCOPED_EVIDENCE.workflow(receiver):
            return await action(receiver, *args, **kwargs)

    return invoke


class RunScopedEvidenceStore:
    """In-memory evidence store; records never cross a Python test run."""

    def __init__(self) -> None:
        self._records: dict[WorkflowEvidenceKey, WorkflowEvidenceRecord] = {}
        self._unfinished: dict[str, TargetServerTriggerOutcome] = {}
        self._prepared: dict[str, tuple[str, str]] = {}
        self._preparation_attempts: set[tuple[str, str]] = set()
        self._terminal_failures: dict[tuple[str, str], TargetServerTriggerOutcome] = {}
        self._owners: dict[str, asyncio.Task] = {}
        self._workflows: dict[asyncio.Task, ControlledWorkflowScope] = {}
        self._adapter_owners: dict[int, asyncio.Task] = {}
        self._identifier_baseline_cleaned: set[tuple[str, str]] = set()
        self._external_identifier_results: dict[tuple[str, str, str], Any] = {}
        self._intervention_workflow_outcomes: dict[tuple[str, str, str], TargetServerTriggerOutcome] = {}
        self._last_selected_process: dict[tuple[str, str], str] = {}

    def current_workflow(self) -> ControlledWorkflowScope | None:
        task = asyncio.current_task()
        return self._workflows.get(task) if task is not None else None

    @contextmanager
    def workflow(self, adapter: object | None = None) -> Iterator[ControlledWorkflowScope]:
        task = asyncio.current_task()
        if task is None:
            raise RuntimeError("Controlled execution requires an asyncio task owner.")
        if adapter is not None:
            identity = id(adapter)
            previous = self._adapter_owners.get(identity)
            if previous is not None and previous is not task and not previous.done():
                from helpers.cu_coverage_report import WorkflowEvidenceUnavailable

                raise WorkflowEvidenceUnavailable(
                    "Another task owns this adapter's active workflow state.",
                    "concurrent_adapter_execution",
                    "blocked",
                    "controlled_workflow",
                )
            self._adapter_owners[identity] = task
        scope = self._workflows.setdefault(task, ControlledWorkflowScope())
        if adapter is not None:
            scope.adapters.add(id(adapter))
        scope.depth += 1
        try:
            yield scope
        except BaseException as primary:
            if scope.depth == 1:
                visited: set[str] = set()
                for endpoint, piu, _ in reversed(scope.dispatches):
                    if piu in visited:
                        continue
                    visited.add(piu)
                    unresolved = self.unfinished(endpoint, piu)
                    if unresolved is not None:
                        self.mark_unfinished(
                            endpoint,
                            piu,
                            replace(
                                unresolved,
                                skip_reason=f"{unresolved.skip_reason} Original exception: "
                                f"{type(primary).__name__}: {primary}",
                            ),
                        )
            raise
        finally:
            scope.depth -= 1
            if scope.depth == 0:
                for piu in scope.claims:
                    if self._owners.get(piu) is task:
                        self._owners.pop(piu, None)
                self._workflows.pop(task, None)
                for identity in scope.adapters:
                    if self._adapter_owners.get(identity) is task:
                        self._adapter_owners.pop(identity, None)

    def claim_scope(self, piu: str) -> bool:
        task = asyncio.current_task()
        if task is None:
            raise RuntimeError("Controlled execution requires an asyncio task owner.")
        previous = self._owners.get(piu)
        if previous is not None and previous is not task and not previous.done():
            return False
        scope = self.current_workflow()
        if scope is not None:
            scope.claims.add(piu)
        if previous is task:
            return True
        self._owners[piu] = task

        def release(completed):
            if self._owners.get(piu) is completed:
                self._owners.pop(piu, None)

        if scope is None:
            task.add_done_callback(release)
        return True

    def unfinished(self, endpoint: str, piu: str) -> TargetServerTriggerOutcome | None:
        return self._unfinished.get(piu)

    def mark_unfinished(self, endpoint: str, piu: str, outcome: TargetServerTriggerOutcome) -> None:
        self._unfinished[piu] = outcome

    def mark_completed(self, endpoint: str, piu: str) -> None:
        self._unfinished.pop(piu, None)

    def terminal_failure(self, endpoint: str, piu: str) -> TargetServerTriggerOutcome | None:
        return self._terminal_failures.get((endpoint, piu))

    def mark_terminal_failure(self, endpoint: str, piu: str, outcome: TargetServerTriggerOutcome) -> None:
        self._terminal_failures[(endpoint, piu)] = outcome

    def last_selected_process(self, endpoint: str, piu: str) -> str:
        return self._last_selected_process.get((endpoint, piu), "")

    def set_last_selected_process(self, endpoint: str, piu: str, process_id: str) -> None:
        if process_id:
            self._last_selected_process[(endpoint, piu)] = process_id
        else:
            self._last_selected_process.pop((endpoint, piu), None)

    def related(self, key: WorkflowEvidenceKey) -> Any | None:
        from helpers.result_collector import (
            ResultCollector,
            ResultProgression,
        )

        for record in self._records.values():
            if not isinstance(record.progression, ResultProgression):
                continue
            if (
                replace(
                    record.key,
                    result_classification=key.result_classification,
                    operation_count=key.operation_count,
                    require_partials=key.require_partials,
                )
                != key
            ):
                continue
            progression = ResultCollector.progression_from_capture(
                ResultCollector.related_capture(record.progression),
                key.result_classification,
                require_partials=key.require_partials,
                allow_partial_references=key.referenced_child_completion_policy == "partial_allowed",
            )
            if progression.is_complete:
                return progression
        return None

    def get(self, key: WorkflowEvidenceKey) -> Any | None:
        record = self._records.get(key)
        return record.progression if record is not None else None

    def put(self, key: WorkflowEvidenceKey, progression: Any) -> bool:
        if not getattr(progression, "is_complete", False):
            return False
        if getattr(progression, "queue_overflow_count", 0):
            return False
        self._records[key] = WorkflowEvidenceRecord(
            key=key,
            progression=progression,
            captured_monotonic=time.monotonic(),
        )
        return True

    def clear(self) -> None:
        self._records.clear()
        self._unfinished.clear()
        self._prepared.clear()
        self._preparation_attempts.clear()
        self._terminal_failures.clear()
        self._owners.clear()
        self._workflows.clear()
        self._adapter_owners.clear()
        self._identifier_baseline_cleaned.clear()
        self._external_identifier_results.clear()
        self._intervention_workflow_outcomes.clear()
        self._last_selected_process.clear()


_RUN_SCOPED_EVIDENCE = RunScopedEvidenceStore()


# ---------------------------------------------------------------------------
# StartSelectedJoiningResultTrigger
# ---------------------------------------------------------------------------


class StartSelectedJoiningResultTrigger(ResultTrigger):
    """Drive result generation via SelectJoiningProcess + StartSelectedJoining.

    Workflow:
      1. Browse to JoiningProcessManagement under JoiningSystem.
      2. Call GetJoiningProcessList to enumerate available processes.
      3. Select the target process (from profile or first available).
      4. Optionally call SetJoiningProcessSize if configured.
      5. Call StartSelectedJoining(ProductInstanceUri, DeselectAfterJoining).
      6. Return a TargetServerTriggerOutcome with full evidence metadata.

    All state-changing calls must be declared in the target_server profile under
    cu_execution.state_changing_methods.allowed_methods.

    Args:
        client:               Active asyncua Client instance.
        joining_system_node:  JoiningSystem OPC UA Node.
        ns_app:               Application namespace index.
        ns_ijt:               IJT Base namespace index, resolved lazily when omitted.
        ns_di:                DI namespace index, resolved lazily when omitted.
        profile:              Loaded target_server profile.
    """

    @property
    def is_simulator(self) -> bool:
        return False

    @property
    def active_result_timeout_s(self) -> float:
        """Result-completion budget for an operation this trigger actually started.

        Uses the profile's workflow/result completion timeout, never the short
        passive ``triggers.result.timeout_seconds`` observation budget: a remote
        StartSelectedJoining has to be given the time a real joining cycle needs.
        """
        return self._profile.workflow_execution.expected_results.timeout_seconds

    @property
    def passive_observation_timeout_s(self) -> float:
        """Observation budget when no operation was started by this trigger."""
        return self._profile.triggers.result.timeout_seconds

    @property
    def allow_partial_referenced_children(self) -> bool:
        """Return whether open-batch partials may resolve referenced child IDs."""
        policy = self._profile.workflow_execution.expected_results.referenced_child_completion_policy
        return policy == "partial_allowed"

    @property
    def owns_result_subscription(self) -> bool:
        """Return True because this trigger captures and returns its own result evidence."""
        return True

    def __init__(
        self,
        client: Any,
        joining_system_node: Any,
        ns_app: int,
        profile: TargetServerCuProfile,
        ns_ijt: int | None = None,
        ns_di: int | None = None,
        subscription_client: Any = None,
    ) -> None:
        self._client = client
        self._joining_system = joining_system_node
        self._ns_app = ns_app
        self._ns_ijt = ns_ijt
        self._ns_di = ns_di
        self._profile = profile
        self.associated_entity_expectations = profile.workflow_execution.expected_results.associated_entities
        self._subscription_client = subscription_client
        self._last_method_failure = ""
        self._pending_evidence_key: WorkflowEvidenceKey | None = None
        self._start_attempts = 0
        self._current_process_id = ""
        self._current_tool_piu = ""
        self._counter_attempts: set[int] = set()
        self._counter_attempt_key: tuple | None = None
        self._workflow_deadline: float | None = None
        self._scenario_id = uuid.uuid4().hex
        self._last_method_result: Any | None = None
        self._observed_server_epoch: tuple[str, ...] = ()
        self._preparation_failures: dict[str, TargetServerTriggerOutcome] = {}

    async def _ensure_baseline(
        self, jpm: Any, piu: str, process: Any, fingerprint: tuple
    ) -> TargetServerTriggerOutcome | None:
        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import NS_IJT_BASE
        from helpers.result_collector import ResultCollector, is_terminal_completed, unwrap_result

        blocked = self._claim_controlled_scope(piu)
        if blocked is not None:
            return blocked
        if self._profile.workflow_execution.evidence_reuse.enabled:
            self._observed_server_epoch = await self._read_observed_server_epoch() or ()
        process_id = self._process_field(process, "JoiningProcessId", "JoiningProcessIdentification", "Id")
        catalog = json.dumps(fingerprint)
        if not self._profile.workflow_execution.preparation.enabled:
            # Existing workflow prerequisites remain the caller's responsibility.
            # Absence of recorded uncertainty is not a counter-baseline proof.
            return None
        prepared_key = f"{process_id}:{self._process_field(process, 'JoiningProcessOriginId')}"
        if _RUN_SCOPED_EVIDENCE._prepared.get(piu) == (prepared_key, catalog):
            return None
        if process_id in self._preparation_failures:
            return self._preparation_failures[process_id]
        if (piu, prepared_key) in _RUN_SCOPED_EVIDENCE._preparation_attempts:
            return TargetServerTriggerOutcome(
                triggered=False,
                method="ResetJoiningProcess",
                execution_outcome="blocked",
                reason_code="preparation_retry_prohibited",
                skip_reason="Reset preparation was already attempted for this process. No implicit retry is permitted.",
            )
        if not self._profile.cu_execution.state_changing_methods.allow_state_changing_method(
            "ResetJoiningProcess"
        ) or not self._profile.cu_execution.extension_fields.get("allow_destructive_methods", False):
            return TargetServerTriggerOutcome(
                triggered=False,
                method="ResetJoiningProcess",
                execution_outcome="blocked",
                reason_code="unsafe_method_not_enabled",
                skip_reason="Reset preparation requires ResetJoiningProcess permission and destructive-method approval.",
            )
        if self._subscription_client is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                method="ResetJoiningProcess",
                execution_outcome="blocked",
                reason_code="preparation_subscription_required",
                skip_reason="Reset preparation requires its own subscription.",
            )
        identification = self._make_process_identification(process)
        if identification is None or not await self._target_context_current(jpm, piu, process, fingerprint):
            return TargetServerTriggerOutcome(
                triggered=False,
                method="ResetJoiningProcess",
                execution_outcome="blocked",
                reason_code="target_changed",
                skip_reason="Preparation identity is unavailable or catalog changed.",
            )
        unknown = TargetServerTriggerOutcome(
            triggered=False,
            method="ResetJoiningProcess",
            product_instance_uri=piu,
            joining_process_id=process_id,
            mutation_attempted=True,
            execution_outcome="inconclusive",
            reason_code="mutation_outcome_unknown",
            skip_reason="Reset preparation was not confirmed. Do not retry implicitly.",
        )

        def reset_observed(results):
            return any(
                self._result_matches_context(result, piu, process_id)
                and is_terminal_completed(result, ResultClassification.INTERVENTION_RESULT)
                and unwrap_result(getattr(result.ResultMetaData, "InterventionType", None)) == 6
                for result in results
            )

        async with ResultCollector(
            self._subscription_client,
            {NS_IJT_BASE: await self._resolve_ijt_namespace_index()},
            is_simulator=False,
            result_observer=lambda result, duplicate: self._observe_result(piu, process_id, "", result, duplicate),
        ) as collector:
            collector.discard_pending()
            self._record_workflow_action("preparation_attempt", piu, process_id)

            def dispatch_preparation():
                self._dispatch_mutation("ResetJoiningProcess", piu, process_id)
                _RUN_SCOPED_EVIDENCE._preparation_attempts.add((piu, prepared_key))
                self._preparation_failures[process_id] = unknown

            call = await find_and_call_method(
                jpm,
                "ResetJoiningProcess",
                await self._resolve_ijt_namespace_index(),
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant(identification, ua.VariantType.ExtensionObject),
                timeout=self._profile.cu_execution.default_timeout_seconds,
                target_server_authorized=True,
                preserve_status=True,
                before_dispatch=dispatch_preparation,
            )
            if not self._method_succeeded("ResetJoiningProcess", call):
                failure = replace(
                    unknown,
                    method_call_result=call,
                    skip_reason=f"Reset preparation failed: {self._last_method_failure}",
                    mutation_attempted=call.rpc_dispatched is not False,
                )
                if process_id in self._preparation_failures:
                    self._preparation_failures[process_id] = failure
                if self._method_call_rejected(call):
                    _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
                return failure

            capture = await collector.collect_evidence(reset_observed, self.active_result_timeout_s)
        if not capture.is_lossless or not reset_observed(capture.all_results):
            return unknown
        _RUN_SCOPED_EVIDENCE._prepared[piu] = (prepared_key, catalog)
        _RUN_SCOPED_EVIDENCE._preparation_attempts.discard((piu, prepared_key))
        _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
        self._preparation_failures.pop(process_id)
        self._record_workflow_action("preparation_confirmed", piu, process_id)
        return None

    def _claim_controlled_scope(self, piu: str) -> TargetServerTriggerOutcome | None:
        if not piu:
            return TargetServerTriggerOutcome(
                triggered=False,
                execution_outcome="blocked",
                reason_code="tool_identity_unbound",
                skip_reason="A unique Tool identity is required before any controlled execution.",
            )
        if not _RUN_SCOPED_EVIDENCE.claim_scope(piu):
            return TargetServerTriggerOutcome(
                triggered=False,
                execution_outcome="blocked",
                reason_code="concurrent_scope_execution",
                skip_reason="Another task owns the controlled Tool scope.",
            )
        return self._unfinished_process_outcome(piu)

    def _unfinished_process_outcome(self, piu: str) -> TargetServerTriggerOutcome | None:
        terminal = _RUN_SCOPED_EVIDENCE.terminal_failure(self._profile.target.endpoint, piu)
        if terminal is not None:
            return replace(
                terminal,
                triggered=False,
                mutation_attempted=False,
                starts_issued=0,
                operation_count=0,
                results_confirmed=0,
                execution_outcome="blocked",
                reason_code="prior_terminal_workflow_failure",
                skip_reason=f"This run already captured a terminal workflow failure. "
                f"No automatic repeat is issued. Original cause: {terminal.skip_reason}",
            )
        previous = _RUN_SCOPED_EVIDENCE.unfinished(self._profile.target.endpoint, piu)
        if previous is None:
            return None
        return replace(
            previous,
            triggered=False,
            mutation_attempted=False,
            starts_issued=0,
            operation_count=0,
            results_confirmed=0,
            prior_unresolved_action={
                "method": previous.method,
                "joining_process_id": previous.joining_process_id,
                "reason_code": previous.reason_code,
                "detail": previous.skip_reason,
            },
            execution_outcome="blocked",
            reason_code="unfinished_compound_process_state",
            skip_reason=(
                f"Tool '{piu}' has an unfinished or unknown process state from "
                f"'{previous.joining_process_id}' in this run. Further automatic mutation is stopped. "
                "The operator must establish readiness before starting a new run. "
                f"Original cause: {previous.reason_code}: {previous.skip_reason}"
            ),
        )

    async def _read_parent_result(self, result_id: str) -> Any | None:
        """Retrieve an observed ancestor for ownership, not for fresh operation/completion evidence."""
        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN, NS_MACH_RESULT
        from helpers.node_discovery import find_child_by_browse_name
        from helpers.result_collector import get_classification, get_result_id, unwrap_result

        ns_result = await self._client.get_namespace_index(NS_MACH_RESULT)
        budget = min(self._profile.cu_execution.default_timeout_seconds, self.active_result_timeout_s)
        management = await find_child_by_browse_name(
            self._joining_system, BN.RESULT_MANAGEMENT, ns_result, timeout=budget
        )
        if management is None:
            logger.warning("Cannot retrieve parent %s: ResultManagement is absent", result_id)
            return None
        call = await find_and_call_method(
            management,
            BN.GET_RESULT_BY_ID,
            ns_result,
            ua.Variant(result_id, ua.VariantType.String),
            ua.Variant(int(budget * 1000), ua.VariantType.Int32),
            timeout=budget,
        )
        if not call.success:
            logger.warning("GetResultById(%s) could not retrieve ownership context: %s", result_id, call.error)
            return None
        output = call.output_list
        if len(output) != 3:
            raise ValueError(f"GetResultById({result_id}) returned an invalid output shape")
        error = unwrap_result(output[2])
        if not isinstance(error, int):
            raise ValueError(f"GetResultById({result_id}) returned an invalid Error value")
        if error:
            logger.warning("GetResultById(%s) returned Error=%s; ownership remains unproven", result_id, error)
            return None
        result = unwrap_result(output[1])
        if get_result_id(result) != result_id:
            raise ValueError(f"GetResultById({result_id}) returned a different or missing ResultId")
        self._record_workflow_action(
            "parent_result_retrieved",
            self._current_tool_piu,
            self._current_process_id,
            result_id=result_id,
            classification=get_classification(result),
            evidence_role="ownership_context_only",
        )
        return result

    def _dispatch_mutation(self, method: str, piu: str, process_id: str) -> None:
        if not _RUN_SCOPED_EVIDENCE.claim_scope(piu):
            raise RuntimeError("Another task owns the Tool scope. No RPC was dispatched.")
        self._current_tool_piu = piu
        self._record_workflow_action("method_dispatch", piu, process_id, method=method)
        _RUN_SCOPED_EVIDENCE.mark_unfinished(
            self._profile.target.endpoint,
            piu,
            TargetServerTriggerOutcome(
                triggered=False,
                method=method,
                product_instance_uri=piu,
                joining_process_id=process_id,
                mutation_attempted=True,
                execution_outcome="inconclusive",
                reason_code="mutation_outcome_unknown",
                skip_reason=f"{method} was dispatched without confirmed process completion.",
            ),
        )
        scope = _RUN_SCOPED_EVIDENCE.current_workflow()
        if scope is not None:
            scope.dispatches.append((self._profile.target.endpoint, piu, method))

    def _mutation_attempted(self) -> bool:
        scope = _RUN_SCOPED_EVIDENCE.current_workflow()
        if scope is not None:
            return bool(scope.dispatches)
        return self._start_attempts > 0 or bool(
            self._current_tool_piu
            and _RUN_SCOPED_EVIDENCE.unfinished(self._profile.target.endpoint, self._current_tool_piu) is not None
        )

    def _unexpected_terminal_outcome(
        self,
        terminal: Any,
        expected_state: int,
        piu: str,
        process_id: str,
        *,
        method: str = "StartSelectedJoining",
        starts_issued: int = 0,
        results_confirmed: int = 0,
        process_progression: Any = None,
        result_progression: Any = None,
        result_capture: Any = None,
        process_settled: bool = True,
    ) -> TargetServerTriggerOutcome | None:
        from helpers.namespaces import ResultState
        from helpers.result_collector import (
            ResultCollector,
            get_classification,
            get_result_id,
            is_terminal_matching_state,
            is_terminal_result,
        )

        classification = get_classification(terminal)
        if (
            classification is None
            or not is_terminal_result(terminal, classification)
            or is_terminal_matching_state(terminal, classification, expected_state)
        ):
            return None
        if process_progression is None and result_capture is not None:
            process_progression = ResultCollector.progression_from_capture(
                result_capture,
                classification,
                expected_terminal_state=expected_state,
                predicate=lambda result: get_result_id(result) == get_result_id(terminal),
            )
        state = int(self._result_metadata_value(terminal, "ResultState"))
        lost_events = process_progression.queue_overflow_count if process_progression is not None else 0
        if lost_events:
            process_settled = False
        names = {ResultState.COMPLETED: "COMPLETED", ResultState.ABORTED: "ABORTED", ResultState.FAILED: "FAILED"}
        detail = (
            f"Process '{process_id}' produced terminal result '{get_result_id(terminal)}' "
            f"(classification {classification}) with ResultState={names[state]} ({state}), "
            f"expected {names[expected_state]} ({expected_state}). "
            "Termination was observed, not a missing-result timeout. No further starts are issued."
        )
        if not process_settled:
            detail += (
                f" Result capture lost {lost_events} event(s); action settlement remains unproven."
                if lost_events
                else " Settlement of the selected process and its accepted starts remains unproven."
            )
        outcome = TargetServerTriggerOutcome(
            triggered=False,
            method=method,
            product_instance_uri=piu,
            joining_process_id=process_id,
            starts_issued=starts_issued,
            operation_count=starts_issued,
            results_confirmed=results_confirmed,
            process_progression=process_progression,
            result_progression=result_progression,
            mutation_attempted=True,
            execution_outcome="failed" if process_settled else "inconclusive",
            reason_code="unexpected_terminal_result_state",
            skip_reason=detail,
            process_settled=process_settled,
        )
        self._record_workflow_action(
            "unexpected_terminal_result",
            piu,
            process_id,
            result_id=get_result_id(terminal),
            classification=classification,
            observed_state=state,
            expected_state=expected_state,
            process_settled=process_settled,
        )
        logger.warning(detail)
        if process_settled:
            _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
            _RUN_SCOPED_EVIDENCE.mark_terminal_failure(self._profile.target.endpoint, piu, outcome)
        return outcome

    def _process_result_classification(self, process: Any) -> int | None:
        return {
            JoiningProcessClassification.PROGRAM: ResultClassification.SINGLE_RESULT,
            JoiningProcessClassification.SYNC: ResultClassification.SYNC_RESULT,
            JoiningProcessClassification.BATCH: ResultClassification.BATCH_RESULT,
            JoiningProcessClassification.JOB: ResultClassification.JOB_RESULT,
        }.get(_process_classification(process))

    def _process_start_limit(self, process: Any) -> int:
        classification = self._process_result_classification(process)
        if classification is None:
            return 0
        return min(
            1
            if _process_classification(process) == JoiningProcessClassification.PROGRAM
            else self._profile.workflow_execution.max_start_invocations_by_result_classification.get(
                self._normalize_classification(classification),
                self._profile.workflow_execution.max_start_invocations,
            ),
            self._profile.workflow_execution.max_start_invocations,
        )

    async def _continue_owned_process(
        self,
        collector: Any,
        jpm: Any,
        piu: str,
        process: Any,
        fingerprint: tuple,
        *,
        starts_issued: int,
        results_confirmed: int,
        after_result_count: int = 0,
        ownership_after_result_count: int = 0,
        required_result_ids: frozenset[str] = frozenset(),
        counter_virtual_station_uri: str = "",
        expected_terminal_state: int = 0,
    ) -> TargetServerTriggerOutcome:
        """Finish an already-owned process without selection, reset, counter retry or a larger budget."""
        from helpers.result_collector import get_result_id, references_result_id

        classification = self._process_result_classification(process)
        process_id = self._process_field(process, "JoiningProcessId", "JoiningProcessIdentification", "Id")
        origin = self._process_field(process, "JoiningProcessOriginId")
        predicate = lambda result: (
            self._counter_result_matches_context(result, piu, process_id, counter_virtual_station_uri, origin)
            if counter_virtual_station_uri
            else self._result_matches_context(result, piu, process_id, origin)
        )
        workflow_expected_state = self._profile.workflow_execution.expected_results.expected_terminal_result_state
        expected_state = expected_terminal_state or workflow_expected_state
        limit = min(self._process_start_limit(process), self._profile.workflow_execution.max_total_start_invocations)
        required = set(required_result_ids)

        def failure(code: str, detail: str, progression: Any = None) -> TargetServerTriggerOutcome:
            return TargetServerTriggerOutcome(
                triggered=False,
                method="StartSelectedJoining",
                product_instance_uri=piu,
                joining_process_id=process_id,
                joining_process_origin_id=origin,
                starts_issued=starts_issued,
                operation_count=starts_issued,
                results_confirmed=results_confirmed,
                mutation_attempted=True,
                execution_outcome="inconclusive",
                reason_code=code,
                skip_reason=detail,
                process_progression=progression,
            )

        async def observe(timeout: float):
            collector.capture_pending()
            return await collector.collect_progression(
                classification,
                timeout_s=timeout,
                expected_terminal_state=expected_state,
                allow_partial_references=self.allow_partial_referenced_children,
                predicate=predicate,
                after_result_count=after_result_count,
            )

        if classification is None:
            return failure(
                "process_completion_contract_unavailable", "The owned process has no completion classification."
            )
        progression = await observe(0.0)
        while progression.terminal_result is None and self._start_attempts < limit:
            if not await self._target_context_current(jpm, piu, process, fingerprint):
                return failure("target_changed", "Owned process identity changed before completion.")
            progression = await observe(0.0)
            if progression.terminal_result is not None:
                break
            if not await self._start_selected_joining(jpm, piu, self._profile.triggers.result.deselect_after_joining):
                return failure("parent_completion_start_unconfirmed", self._last_method_failure)
            prior_starts = starts_issued
            starts_issued += 1
            observation = await collector.collect_correlated_operation_outcome(
                requested_result_classification=classification,
                predicate=predicate,
                operation_predicate=predicate,
                operation_context_predicate=lambda result: self._result_matches_tool_context(result, piu),
                ownership_after_result_count=ownership_after_result_count,
                operation_timeout_s=self.active_result_timeout_s,
                terminal_drain_seconds=self._profile.workflow_execution.consecutive_start_delay_seconds,
                expected_terminal_state=expected_state,
            )
            if observation.timed_out or not observation.operation_confirmed:
                return failure(
                    "result_capture_overflow" if observation.queue_overflow_count else "operation_evidence_timeout",
                    "The accepted completion start has no lossless owned operation evidence.",
                )
            mismatch = self._unexpected_terminal_outcome(
                observation.terminal_result,
                expected_state,
                piu,
                process_id,
                starts_issued=starts_issued,
                results_confirmed=results_confirmed + int(observation.operation_result is not None),
                process_progression=await observe(0.0) if observation.terminal_result is not None else None,
                process_settled=not (observation.operation_result is None and prior_starts),
            )
            if mismatch is not None:
                return mismatch
            if observation.terminal_result is not None and observation.operation_result is None and prior_starts:
                return failure(
                    "accepted_start_settlement_unproven",
                    "A terminal result cannot settle the extra accepted start without its owned operation result.",
                )
            if observation.operation_result is not None:
                result_id = get_result_id(observation.operation_result)
                if not result_id:
                    return failure("operation_identity_unproven", "The completion operation has no ResultId.")
                required.add(result_id)
            results_confirmed += 1
            progression = await observe(0.0)

        if progression.terminal_result is None:
            timeout = self.active_result_timeout_s
            if self._workflow_deadline is not None:
                timeout = min(timeout, max(0.0, self._workflow_deadline - asyncio.get_running_loop().time()))
            progression = await observe(timeout)
        mismatch = self._unexpected_terminal_outcome(
            progression.terminal_result,
            expected_state,
            piu,
            process_id,
            starts_issued=starts_issued,
            results_confirmed=results_confirmed,
            process_progression=progression,
        )
        if mismatch is not None:
            return mismatch
        final = progression.final_result
        if (
            final is None
            or progression.queue_overflow_count
            or not get_result_id(final)
            or any(
                result_id != get_result_id(final)
                and not references_result_id(final, result_id, progression.all_results)
                for result_id in required
            )
        ):
            return failure(
                "owned_process_completion_unproven",
                "The owned parent did not terminate with attributable lossless evidence within the unchanged ceilings.",
                progression,
            )
        _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
        if (
            self._profile.workflow_execution.evidence_reuse.enabled
            and self._observed_server_epoch
            and expected_state == workflow_expected_state
        ):
            key = self._workflow_evidence_key(
                piu=piu,
                process_id=process_id,
                process_origin_id=origin,
                processes=[process],
                classification=classification,
                selection_policy=self._get_selection_for_classification(classification)[0].policy,
                operation_count=self._profile.workflow_execution.max_start_invocations,
                require_partials=False,
            )
            _RUN_SCOPED_EVIDENCE.put(replace(key, process_list_fingerprint=fingerprint), progression)
        return TargetServerTriggerOutcome(
            triggered=True,
            method="StartSelectedJoining",
            product_instance_uri=piu,
            joining_process_id=process_id,
            joining_process_origin_id=origin,
            operation_count=starts_issued,
            starts_issued=starts_issued,
            results_confirmed=results_confirmed,
            mutation_attempted=True,
            execution_outcome="passed",
            process_progression=progression,
            process_settled=True,
        )

    async def _run_sequence_workflow(
        self, operation: Callable[[], Awaitable[TargetServerTriggerOutcome]]
    ) -> TargetServerTriggerOutcome:
        scope = _RUN_SCOPED_EVIDENCE.current_workflow()
        first_dispatch = len(scope.dispatches) if scope is not None else 0
        outcome = await operation()
        dispatches = scope.dispatches[first_dispatch:] if scope is not None else []
        attempted = bool(dispatches) or outcome.mutation_attempted
        unresolved = (
            _RUN_SCOPED_EVIDENCE.unfinished(self._profile.target.endpoint, outcome.product_instance_uri)
            if outcome.product_instance_uri
            else None
        )
        if outcome.triggered and unresolved is not None:
            outcome = replace(
                outcome,
                triggered=False,
                execution_outcome="inconclusive",
                reason_code="owned_process_completion_unproven",
                skip_reason="The experiment passed its local check, but its owned process is not settled.",
            )
        if not outcome.execution_outcome:
            rejected = (
                bool(dispatches)
                and self._last_method_result is not None
                and self._last_method_result.rpc_dispatched is not False
                and self._method_call_rejected(self._last_method_result)
            )
            outcome = replace(
                outcome,
                execution_outcome="passed"
                if outcome.triggered
                else "failed"
                if rejected
                else "inconclusive"
                if unresolved
                else "blocked",
                reason_code=""
                if outcome.triggered
                else "method_rejected"
                if rejected
                else "mutation_outcome_unknown"
                if unresolved
                else "workflow_prerequisite_unavailable",
            )
        outcome = replace(outcome, mutation_attempted=attempted, process_settled=attempted and unresolved is None)
        if unresolved is not None and dispatches and not outcome.triggered:
            _RUN_SCOPED_EVIDENCE.mark_unfinished(
                self._profile.target.endpoint,
                outcome.product_instance_uri,
                replace(outcome, skip_reason=f"{unresolved.skip_reason} {outcome.skip_reason}"),
            )
        return outcome

    def _observe_result(
        self,
        piu: str,
        process_id: str,
        origin: str,
        result: Any,
        duplicate: bool,
        *,
        counter_virtual_station_uri: str = "",
    ) -> None:
        from helpers.result_collector import get_classification, get_result_id, parent_result_ids, unwrap_result

        meta = getattr(result, "ResultMetaData", None)
        tool_match = result is not None and (
            self._counter_result_matches_asset_context(result, piu, counter_virtual_station_uri)
            if counter_virtual_station_uri
            else self._result_matches_tool_context(result, piu)
        )
        context_match = result is not None and (
            self._counter_result_matches_context(result, piu, process_id, counter_virtual_station_uri, origin)
            if counter_virtual_station_uri
            else self._result_matches_context(result, piu, process_id, origin)
        )
        entities = []
        for entity in getattr(meta, "AssociatedEntities", None) or ():
            entity = unwrap_result(entity)
            entities.append(
                {
                    "EntityId": str(getattr(entity, "EntityId", "") or ""),
                    "EntityOriginId": str(getattr(entity, "EntityOriginId", "") or ""),
                    "EntityType": str(unwrap_result(getattr(entity, "EntityType", None))),
                }
            )
        self._record_workflow_action(
            "result_observed",
            piu,
            process_id,
            result_id=get_result_id(result),
            classification=get_classification(result),
            is_partial=(
                bool(unwrap_result(getattr(meta, "IsPartial", None)))
                if getattr(meta, "IsPartial", None) is not None
                else None
            ),
            result_state=str(unwrap_result(getattr(meta, "ResultState", None))),
            associated_entities=entities,
            parent_result_ids=sorted(parent_result_ids(result)),
            context_match_scope="direct_counter_process_identity"
            if counter_virtual_station_uri
            else "direct_process_identity",
            content_result_ids=[
                get_result_id(unwrap_result(child))
                for child in getattr(result, "ResultContent", None) or ()
                if get_result_id(unwrap_result(child))
            ],
            references=[
                {
                    "ResultId": get_result_id(unwrap_result(ref)),
                    "ReferenceType": str(getattr(unwrap_result(ref), "ReferenceType", "")),
                }
                for ref in getattr(result, "References", None) or ()
            ],
            duplicate=duplicate,
            context_match=context_match,
            rejection_reason=(
                "missing_result_payload"
                if result is None
                else ("selected_asset_identity_mismatch" if counter_virtual_station_uri else "tool_identity_mismatch")
                if not tool_match
                else "process_identity_mismatch"
                if not context_match
                else ""
            ),
        )

    @staticmethod
    def _result_matches_context(
        result_data: Any, piu: str, joining_process_id: str, joining_process_origin_id: str = ""
    ) -> bool:
        """Require result identifiers for the selected Tool and JoiningProcess."""
        from asyncua import ua

        meta = getattr(result_data, "ResultMetaData", None)
        entities = getattr(meta, "AssociatedEntities", None) or ()
        entity_identities: set[tuple[str, str]] = set()
        for entity in entities:
            value = entity.Value if isinstance(entity, ua.Variant) else entity
            entity_id = getattr(value, "EntityId", None)
            if entity_id is not None and str(entity_id):
                entity_origin_id = getattr(value, "EntityOriginId", None)
                entity_identities.add(
                    (
                        str(entity_id).lower().strip(),
                        str(entity_origin_id or "").lower().strip(),
                    )
                )

        piu_lower = piu.lower().strip()
        jp_id_lower = joining_process_id.lower().strip()
        jp_origin_lower = joining_process_origin_id.lower().strip()
        entity_ids = {entity_id for entity_id, _ in entity_identities}

        piu_match = not piu_lower or piu_lower in entity_ids
        if not jp_id_lower and not jp_origin_lower:
            jp_match = True
        elif jp_id_lower and jp_origin_lower:
            jp_match = (jp_id_lower, jp_origin_lower) in entity_identities
        elif jp_id_lower:
            jp_match = jp_id_lower in entity_ids
        else:
            jp_match = any(origin_id == jp_origin_lower for _, origin_id in entity_identities)
        return piu_match and jp_match

    @staticmethod
    def _result_matches_tool_context(result_data: Any, piu: str) -> bool:
        """Match intermediate operation evidence to the selected Tool."""
        from asyncua import ua

        meta = getattr(result_data, "ResultMetaData", None)
        entities = getattr(meta, "AssociatedEntities", None) or ()
        entity_ids = {
            str(entity_id).lower().strip()
            for entity in entities
            if (entity_id := getattr(entity.Value if isinstance(entity, ua.Variant) else entity, "EntityId", None))
            is not None
            and str(entity_id)
        }
        return not piu.strip() or piu.lower().strip() in entity_ids

    @staticmethod
    def _result_entity_ids(result_data: Any, entity_type: str) -> frozenset[str]:
        from asyncua import ua

        ids = set()
        for entity in getattr(getattr(result_data, "ResultMetaData", None), "AssociatedEntities", None) or ():
            value = entity.Value if isinstance(entity, ua.Variant) else entity
            kind = getattr(value, "EntityType", None)
            kind = kind.Value if isinstance(kind, ua.Variant) else kind
            identity = getattr(value, "EntityId", None)
            if kind == ENTITY_TYPE_VALUES[entity_type] and identity is not None and str(identity).strip():
                ids.add(str(identity).strip().lower())
        return frozenset(ids)

    @classmethod
    def _counter_result_matches_asset_context(cls, result_data: Any, piu: str, station: str) -> bool:
        tools = cls._result_entity_ids(result_data, "TOOL")
        if tools:
            return piu.strip().lower() in tools
        if cls._result_matches_tool_context(result_data, piu):
            return True
        return bool(station.strip()) and cls._result_entity_ids(result_data, "VIRTUAL_STATION") == {
            station.strip().lower()
        }

    @classmethod
    def _counter_result_matches_context(
        cls, result_data: Any, piu: str, process_id: str, station: str, origin: str = ""
    ) -> bool:
        if not cls._counter_result_matches_asset_context(result_data, piu, station):
            return False
        return cls._result_matches_context(result_data, piu, process_id, origin) or (
            bool(station.strip()) and cls._result_matches_context(result_data, station, process_id, origin)
        )

    @classmethod
    def _counter_station_from_joining_results(cls, results: tuple[Any, ...], piu: str, process_id: str) -> str:
        stations = {
            station
            for result in results
            if piu.strip().lower() in cls._result_entity_ids(result, "TOOL")
            if cls._result_matches_context(result, piu, process_id)
            for station in cls._result_entity_ids(result, "VIRTUAL_STATION")
        }
        if len(stations) > 1:
            logger.warning(
                "Owned joining results identify several VirtualStations for Tool %s and process %s", piu, process_id
            )
        return next(iter(stations)) if len(stations) == 1 else ""

    @staticmethod
    def _result_metadata_value(result_data: Any, field_name: str) -> Any:
        """Return one unwrapped ResultMetaData field."""
        from asyncua import ua

        meta = getattr(result_data, "ResultMetaData", None)
        value = getattr(meta, field_name, None) if meta is not None else None
        if isinstance(value, ua.Variant):
            value = value.Value
        if hasattr(value, "value"):
            value = value.value
        return value

    @classmethod
    def _same_reset_step_evidence(cls, before: Any, after: Any) -> tuple[bool, str, bool]:
        """Validate that a new result reports the same explicit process step."""
        before_result_id = str(cls._result_metadata_value(before, "ResultId") or "").strip()
        after_result_id = str(cls._result_metadata_value(after, "ResultId") or "").strip()
        if not before_result_id or not after_result_id:
            return False, "ResultMetaData.ResultId is required to distinguish pre-reset and post-reset results", False
        if before_result_id == after_result_id:
            return False, "Post-reset result repeated the pre-reset ResultId", False

        before_step_id = str(cls._result_metadata_value(before, "StepId") or "").strip()
        after_step_id = str(cls._result_metadata_value(after, "StepId") or "").strip()
        if not before_step_id or not after_step_id:
            return (
                False,
                "ResultMetaData.StepId is unavailable, so restart at the same step cannot be proven",
                True,
            )
        if before_step_id != after_step_id:
            return False, f"Post-reset result reported StepId '{after_step_id}', expected '{before_step_id}'", False

        before_sequence = cls._result_metadata_value(before, "SequenceNumber")
        after_sequence = cls._result_metadata_value(after, "SequenceNumber")
        if isinstance(before_sequence, bool) or isinstance(after_sequence, bool):
            return False, "ResultMetaData.SequenceNumber must be an integer", False
        try:
            if int(after_sequence) <= int(before_sequence):
                return False, "Post-reset SequenceNumber did not advance beyond the pre-reset result", False
        except (TypeError, ValueError):
            return False, "ResultMetaData.SequenceNumber is required to order reset evidence", False
        return True, "", False

    def _method_succeeded(
        self,
        method_name: str,
        result: Any,
        *,
        observe_uncertain: bool = False,
    ) -> bool:
        """Return whether both the OPC UA call and IJT method status succeeded."""
        if not result.success:
            if result.error:
                detail = str(result.error)
            else:
                parts: list[str] = []
                if result.status_code is not None:
                    try:
                        from asyncua import ua

                        sc = ua.StatusCode(result.status_code)
                        parts.append(f"{sc.name} (0x{int(result.status_code):08X})")
                    except Exception:  # noqa: BLE001
                        parts.append(f"status_code=0x{int(result.status_code):08X}")
                out = result.output_list
                if len(out) >= 2 and isinstance(out[0], (int, bool)):
                    msg = str(out[1]) if out[1] is not None else ""
                    dom = f"domain status={out[0]!s}"
                    if msg:
                        dom += f", message={msg}"
                    parts.append(dom)
                detail = ": ".join(parts) if parts else "OPC UA service call failed"
            self._last_method_failure = detail
            if observe_uncertain and result.status_code is not None and 0x40000000 <= result.status_code < 0x80000000:
                logger.warning(
                    "%s returned Uncertain; observing for correlated result evidence",
                    method_name,
                )
                return True
            return False

        output = result.output_list
        if not output:
            self._last_method_failure = ""
            return True

        raw_status = output[0]
        try:
            from asyncua import ua

            if isinstance(raw_status, ua.StatusCode):
                succeeded = raw_status.is_good()
            elif isinstance(raw_status, (int, bool)):
                succeeded = int(raw_status) == 0
            else:
                return True
        except (TypeError, ValueError):
            return True

        if succeeded:
            self._last_method_failure = ""
            return True

        status_message = str(output[1]) if len(output) > 1 else ""
        self._last_method_failure = f"domain status={raw_status!s}"
        if status_message:
            self._last_method_failure += f", message={status_message}"
        logger.warning("%s rejected by controller: %s", method_name, self._last_method_failure)
        return False

    async def _resolve_ijt_namespace_index(self) -> int:
        from helpers.namespaces import NS_IJT_BASE

        if self._ns_ijt is not None:
            return self._ns_ijt
        self._ns_ijt = await self._client.get_namespace_index(NS_IJT_BASE)
        return self._ns_ijt

    async def _get_joining_process_management(self) -> Any:
        from helpers.namespaces import BN
        from helpers.node_discovery import find_child_by_browse_name

        ns_ijt = await self._resolve_ijt_namespace_index()
        return await find_child_by_browse_name(self._joining_system, BN.JOINING_PROCESS_MANAGEMENT, ns_ijt)

    async def _set_tool_enabled(self, piu: str, enabled: bool) -> bool:
        """Set the selected Tool state through the authorized EnableAsset method."""
        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN, NS_DI
        from helpers.node_discovery import find_child_by_browse_name, find_method_set

        ns_ijt = await self._resolve_ijt_namespace_index()
        asset_management = await find_child_by_browse_name(self._joining_system, BN.ASSET_MANAGEMENT, ns_ijt)
        if asset_management is None:
            return False

        ns_di = self._ns_di
        if ns_di is None:
            ns_di = await self._client.get_namespace_index(NS_DI)
            self._ns_di = ns_di
        method_set = await find_method_set(asset_management, ns_di, ns_ijt, self._ns_app)
        if method_set is None:
            return False

        result = await find_and_call_method(
            method_set,
            BN.ENABLE_ASSET,
            ns_ijt,
            ua.Variant(piu, ua.VariantType.String),
            ua.Variant(enabled, ua.VariantType.Boolean),
            timeout=self._profile.cu_execution.default_timeout_seconds,
            target_server_authorized=True,
            preserve_status=True,
            before_dispatch=lambda: self._dispatch_mutation(BN.ENABLE_ASSET, piu, ""),
        )
        self._last_method_result = result
        return self._method_succeeded(BN.ENABLE_ASSET, result)

    async def _enable_tool(self, piu: str) -> bool:
        """Enable the selected tool before starting when the profile allows it."""
        return await self._set_tool_enabled(piu, True)

    async def _read_tool_enabled(self, piu: str) -> bool | None:
        """Read the current persistent Tool enabled state."""
        from helpers.node_discovery import read_tool_enabled

        ns_ijt = await self._resolve_ijt_namespace_index()
        ns_di = self._ns_di
        if ns_di is None:
            from helpers.namespaces import NS_DI

            ns_di = await self._client.get_namespace_index(NS_DI)
            self._ns_di = ns_di
        return await read_tool_enabled(self._client, ns_ijt, ns_di, piu, self._ns_app)

    async def _ensure_tool_enabled(self, piu: str) -> bool:
        """Ensure the Tool is enabled according to the target profile policy."""
        blocked = self._claim_controlled_scope(piu)
        if blocked is not None:
            self._last_method_failure = f"{blocked.reason_code}: {blocked.skip_reason}"
            return False
        policy = self._profile.cu_execution.extension_fields.get(
            "enable_asset_policy",
            "when_disabled",
        )
        if policy != "always" and await self._read_tool_enabled(piu) is True:
            return True
        enabled = await self._enable_tool(piu)
        if enabled and await self._read_tool_enabled(piu) is True:
            _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
            return True
        if self._last_method_result is not None and self._method_call_rejected(self._last_method_result):
            _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
        self._last_method_failure = (
            self._last_method_failure or "Tool enabled state was not confirmed after EnableAsset."
        )
        return False

    @_owned_workflow
    async def trigger_select_process_event(self) -> TargetServerTriggerOutcome:
        return await self._run_sequence_workflow(self._execute_select_process_event)

    async def _execute_select_process_event(self) -> TargetServerTriggerOutcome:
        """Invoke SelectJoiningProcess after the caller subscribes, preferring a state change from the active program."""
        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN
        from helpers.result_collector import unwrap_result

        blocked = self._physical_selection_blocker(method="SelectJoiningProcess")
        if blocked:
            return blocked
        if not self._profile.cu_execution.state_changing_methods.allow_state_changing_method("SelectJoiningProcess"):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="SelectJoiningProcess is not authorized by the SUT manifest.",
                method="SelectJoiningProcess",
                trigger_mode="workflow_actions",
            )
        jpm_node = await self._get_joining_process_management()
        piu = await self._resolve_tool_piu()
        processes = await self._get_joining_process_list(jpm_node, piu) if jpm_node is not None else []
        active_id = ""
        if jpm_node is not None and piu:
            try:
                active_call = await find_and_call_method(
                    jpm_node,
                    BN.GET_SELECTED_JOINING_PROGRAM,
                    await self._resolve_ijt_namespace_index(),
                    ua.Variant(piu, ua.VariantType.String),
                    timeout=min(5.0, self._profile.cu_execution.default_timeout_seconds),
                    preserve_status=True,
                )
                if active_call.service_good_confirmed and active_call.success and len(active_call.output_list) >= 2:
                    raw_status = active_call.output_list[1]
                    if isinstance(raw_status, int) and not isinstance(raw_status, bool) and raw_status == 0:
                        metadata = unwrap_result(active_call.output_list[0])
                        active_id = self._process_field(
                            metadata,
                            "JoiningProcessId",
                            "JoiningProcessIdentification",
                            "Id",
                        )
            except Exception:  # noqa: BLE001
                active_id = ""
        if not active_id:
            active_id = (
                _RUN_SCOPED_EVIDENCE.last_selected_process(self._profile.target.endpoint, piu)
                or self._current_process_id
                or ""
            )

        if self._profile.selection.joining_process.policy == "exact_match":
            candidates = self._choose_joining_processes(processes)
        else:
            programs = [p for p in processes if _process_classification(p) == JoiningProcessClassification.PROGRAM]
            others = [p for p in processes if _process_classification(p) != JoiningProcessClassification.PROGRAM]
            candidates = (programs + others)[: max(2, self._profile.workflow_execution.max_candidates)]

        active_norm = active_id.strip().lower()
        process = None
        for cand in candidates:
            cand_id = self._process_field(cand, "JoiningProcessId", "JoiningProcessIdentification", "Id")
            if not active_norm or cand_id.strip().lower() != active_norm:
                process = cand
                break
        if process is None and candidates:
            process = candidates[0]
        if process is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="No joining process matched the configured event action selection.",
                method="SelectJoiningProcess",
                trigger_mode="workflow_actions",
                product_instance_uri=piu,
            )

        process_id = self._process_field(
            process,
            "JoiningProcessId",
            "JoiningProcessIdentification",
            "Id",
        )
        if (
            jpm_node is not None
            and active_norm
            and process_id.strip().lower() == active_norm
            and self._profile.cu_execution.state_changing_methods.allow_state_changing_method("DeselectJoiningProcess")
        ):
            previous = _RUN_SCOPED_EVIDENCE.unfinished(self._profile.target.endpoint, piu)
            deselect_call = await find_and_call_method(
                jpm_node,
                BN.DESELECT_JOINING_PROCESS,
                await self._resolve_ijt_namespace_index(),
                ua.Variant(piu, ua.VariantType.String),
                timeout=self._profile.cu_execution.default_timeout_seconds,
                target_server_authorized=True,
                preserve_status=True,
                before_dispatch=lambda: self._dispatch_mutation(BN.DESELECT_JOINING_PROCESS, piu, process_id),
            )
            self._settle_rejected_call(piu, deselect_call, previous)
            if self._method_succeeded(BN.DESELECT_JOINING_PROCESS, deselect_call):
                _RUN_SCOPED_EVIDENCE.set_last_selected_process(self._profile.target.endpoint, piu, "")
                _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)

        selected = await self._select_joining_process(jpm_node, process, piu)
        origin_id = self._process_field(
            process,
            "JoiningProcessOriginId",
            "JoiningProcessIdentificationOrigin",
            "OriginId",
        )
        expected_ids = tuple(dict.fromkeys(val for val in (process_id, origin_id) if val)) if selected else ()
        return TargetServerTriggerOutcome(
            triggered=selected,
            skip_reason=None if selected else f"SelectJoiningProcess failed: {self._last_method_failure}",
            method="SelectJoiningProcess",
            trigger_mode="workflow_actions",
            product_instance_uri=piu,
            joining_process_id=process_id,
            joining_process_origin_id=origin_id,
            expected_event_entity_ids=expected_ids,
        )

    @_owned_workflow
    async def get_selected_program_evidence(self) -> TargetServerTriggerOutcome:
        """Use the current selected Program, or one approved Program selection, never a joining start."""
        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.result_collector import unwrap_result

        method = "GetSelectedJoiningProgram"
        jpm = await self._get_joining_process_management()
        piu = await self._resolve_tool_piu()
        if jpm is None or not piu:
            return TargetServerTriggerOutcome(
                triggered=False,
                method=method,
                execution_outcome="blocked",
                reason_code="selected_program_scope_unavailable",
                skip_reason="The Tool or JoiningProcessManagement is unavailable.",
            )
        processes = await self._get_joining_process_list(jpm, piu)
        known_programs = {
            self._process_field(process, "JoiningProcessId", "JoiningProcessIdentification", "Id")
            for process in processes
            if _process_classification(process) == JoiningProcessClassification.PROGRAM
        }

        async def observe(timeout: float) -> TargetServerTriggerOutcome:
            call = await find_and_call_method(
                jpm,
                method,
                await self._resolve_ijt_namespace_index(),
                ua.Variant(piu, ua.VariantType.String),
                timeout=timeout,
                preserve_status=True,
            )
            if not call.service_good_confirmed:
                if call.error is not None and not isinstance(call.error, LookupError):
                    raise call.error
                return TargetServerTriggerOutcome(
                    triggered=False,
                    method=method,
                    product_instance_uri=piu,
                    execution_outcome="blocked",
                    reason_code="selected_program_observation_unavailable",
                    skip_reason=str(call.error or "No service response"),
                    method_call_result=call,
                )
            if not call.success:
                return TargetServerTriggerOutcome(
                    triggered=False,
                    method=method,
                    product_instance_uri=piu,
                    execution_outcome="blocked"
                    if call.method_status_code is not None and ua.StatusCode(call.method_status_code).is_uncertain()
                    else "failed",
                    reason_code="selected_program_unavailable",
                    skip_reason="The Server did not return an available selected Program.",
                    method_call_result=call,
                )
            outputs = call.output_list
            metadata = unwrap_result(outputs[0]) if outputs else None
            process_id = self._process_field(metadata, "JoiningProcessId")
            valid = (
                len(outputs) == 3
                and isinstance(outputs[1], int)
                and not isinstance(outputs[1], bool)
                and outputs[1] == 0
                and isinstance(outputs[2], ua.LocalizedText)
                and _process_classification(metadata) == JoiningProcessClassification.PROGRAM
                and bool(process_id)
            )
            bound = valid and process_id in known_programs
            return TargetServerTriggerOutcome(
                triggered=bound,
                method=method,
                product_instance_uri=piu,
                joining_process_id=process_id,
                execution_outcome="passed" if bound else "blocked" if valid else "failed",
                reason_code=""
                if bound
                else "selected_program_scope_unconfirmed"
                if valid
                else "selected_program_response_invalid",
                skip_reason=None
                if bound
                else "GetSelectedJoiningProgram could not be bound to an advertised Program with valid outputs.",
                method_call_result=call,
            )

        current = await observe(self._profile.cu_execution.default_timeout_seconds)
        if (
            current.triggered
            or current.reason_code != "selected_program_unavailable"
            or current.execution_outcome == "failed"
        ):
            return current
        if not self._profile.cu_execution.state_changing_methods.allow_state_changing_method("SelectJoiningProcess"):
            return replace(current, reason_code="selected_program_selection_not_authorized")
        blocked = self._physical_selection_blocker("single", method="SelectJoiningProcess")
        if blocked is not None:
            return blocked
        candidates = self._choose_joining_processes(processes, "single")
        if not candidates:
            return replace(current, reason_code="selected_program_candidate_unavailable")
        process = candidates[0]
        process_id = self._process_field(process, "JoiningProcessId", "JoiningProcessIdentification", "Id")
        if not await self._select_joining_process(jpm, process, piu, classification="single"):
            unresolved = _RUN_SCOPED_EVIDENCE.unfinished(self._profile.target.endpoint, piu)
            return replace(
                current,
                method="SelectJoiningProcess",
                reason_code="selected_program_selection_unconfirmed",
                skip_reason=self._last_method_failure,
                mutation_attempted=unresolved is not None,
                execution_outcome="inconclusive" if unresolved is not None else "blocked",
                method_call_result=self._last_method_result,
            )
        deadline = asyncio.get_running_loop().time() + self._profile.cu_execution.default_timeout_seconds
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                failed = replace(
                    current,
                    triggered=False,
                    mutation_attempted=True,
                    execution_outcome="inconclusive",
                    reason_code="selected_program_identity_unconfirmed",
                    skip_reason="The selected Program was not confirmed after the authorized selection.",
                )
                _RUN_SCOPED_EVIDENCE.mark_unfinished(self._profile.target.endpoint, piu, failed)
                return failed
            try:
                current = await observe(remaining)
            except BaseException as exc:
                _RUN_SCOPED_EVIDENCE.mark_unfinished(
                    self._profile.target.endpoint,
                    piu,
                    TargetServerTriggerOutcome(
                        triggered=False,
                        method="SelectJoiningProcess",
                        joining_process_id=process_id,
                        product_instance_uri=piu,
                        mutation_attempted=True,
                        execution_outcome="inconclusive",
                        reason_code="selected_program_observation_interrupted",
                        skip_reason=f"Selection could not be confirmed: {type(exc).__name__}: {exc}",
                    ),
                )
                raise
            if current.triggered and current.joining_process_id == process_id:
                return replace(current, mutation_attempted=True, process_settled=True)
            if current.execution_outcome == "failed":
                failed = replace(current, mutation_attempted=True, joining_process_id=process_id)
                _RUN_SCOPED_EVIDENCE.mark_unfinished(self._profile.target.endpoint, piu, failed)
                return failed
            await asyncio.sleep(min(0.1, max(0.0, deadline - asyncio.get_running_loop().time())))

    @_owned_workflow
    async def trigger_asset_enable_event(self, enabled: bool) -> TargetServerTriggerOutcome:
        """Cause one asset-enable transition and always leave the persistent Tool enabled."""
        if not self._profile.cu_execution.state_changing_methods.allow_state_changing_method("EnableAsset"):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="EnableAsset is not authorized by the SUT manifest.",
                method="EnableAsset",
                trigger_mode="workflow_actions",
            )
        if not enabled and not self._profile.cu_execution.extension_fields.get("allow_disable_asset", False):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="EnableAsset(false) requires risk_approvals.allow_disable_asset=true.",
                method="EnableAsset",
                trigger_mode="workflow_actions",
            )

        piu = await self._resolve_tool_piu()
        blocked = self._claim_controlled_scope(piu)
        if blocked is not None:
            return blocked
        changed = False
        action_settled = False
        failure = ""
        restored = False
        restore_failure = ""
        original_error: BaseException | None = None
        try:
            if enabled and self._profile.cu_execution.extension_fields.get("allow_disable_asset", False):
                await self._set_tool_enabled(piu, False)
            changed = await self._set_tool_enabled(piu, enabled)
            failure = self._last_method_failure
            action_settled = changed or (
                self._last_method_result is not None and self._method_call_rejected(self._last_method_result)
            )
        except BaseException as exc:
            original_error = exc
            raise
        finally:
            try:
                restored = await self._set_tool_enabled(piu, True)
                restore_failure = self._last_method_failure
            except BaseException as restore_error:
                logger.error("Tool enabled-state restoration failed: %s", restore_error, exc_info=True)
                if original_error is None:
                    raise
            finally:
                if original_error is not None:
                    _RUN_SCOPED_EVIDENCE.mark_unfinished(
                        self._profile.target.endpoint,
                        piu,
                        TargetServerTriggerOutcome(
                            triggered=False,
                            method="EnableAsset",
                            product_instance_uri=piu,
                            mutation_attempted=True,
                            execution_outcome="inconclusive",
                            reason_code="asset_restoration_unproven",
                            skip_reason=f"Original EnableAsset error: {original_error}. "
                            "Further automatic mutation is stopped for this run.",
                        ),
                    )

        if not restored or not action_settled:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"CRITICAL: EnableAsset action settlement or restoration is unproven: {failure or restore_failure}",
                method="EnableAsset",
                trigger_mode="workflow_actions",
                product_instance_uri=piu,
                mutation_attempted=True,
                execution_outcome="inconclusive",
                reason_code="asset_restoration_unproven",
            )
        if await self._read_tool_enabled(piu) is not True:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="EnableAsset restoration returned success, but the enabled Tool state was not observed.",
                method="EnableAsset",
                product_instance_uri=piu,
                mutation_attempted=True,
                execution_outcome="inconclusive",
                reason_code="asset_restoration_unproven",
            )
        _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
        return TargetServerTriggerOutcome(
            triggered=changed,
            skip_reason=None if changed else f"EnableAsset({enabled}) failed: {failure}",
            method="EnableAsset",
            trigger_mode="workflow_actions",
            product_instance_uri=piu,
            expected_event_entity_ids=(piu,) if changed and piu else (),
        )

    async def _get_asset_method_set(self) -> Any | None:
        from helpers.namespaces import BN, NS_DI
        from helpers.node_discovery import find_child_by_browse_name, find_method_set

        ns_ijt = await self._resolve_ijt_namespace_index()
        asset_management = await find_child_by_browse_name(self._joining_system, BN.ASSET_MANAGEMENT, ns_ijt)
        if asset_management is None:
            return None
        if self._ns_di is None:
            self._ns_di = await self._client.get_namespace_index(NS_DI)
        return await find_method_set(asset_management, self._ns_di, ns_ijt, self._ns_app)

    @staticmethod
    def _extract_get_identifiers_entities(output_list: Any) -> list[Any]:
        """Extract the Entities list (output[0]) from GetIdentifiers 3-arg IJT output or mock output."""
        if not output_list:
            return []
        if isinstance(output_list, (list, tuple)):
            first = output_list[0]
            if first is None:
                return []
            if isinstance(first, (list, tuple)):
                return list(first)
            if len(output_list) >= 2 and isinstance(output_list[1], int) and not isinstance(output_list[1], bool):
                return [first]
            return list(output_list)
        return [output_list]

    @staticmethod
    def _get_identifiers_succeeded(result: Any) -> bool:
        """Return whether GetIdentifiers succeeded at both OPC UA service and IJT Status levels."""
        if not result.success:
            return False
        out = result.output_list
        if len(out) >= 2 and isinstance(out[1], int) and not isinstance(out[1], bool):
            return out[1] == 0
        return True

    @classmethod
    def _resolve_readback_names(cls, output_list: Any, target_values: set[str]) -> list[str]:
        """Extract server-assigned Entity.Name values matching target EntityId values."""
        from helpers.identifier_utils import contains_identifier

        if not output_list or not target_values:
            return []
        candidates = cls._extract_get_identifiers_entities(output_list)

        resolved: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            name = getattr(item, "Name", None)
            if not isinstance(name, str) or not name.strip():
                continue
            clean_name = name.strip()
            if clean_name in seen:
                continue
            if any(contains_identifier(item, val) for val in target_values):
                seen.add(clean_name)
                resolved.append(clean_name)
        return resolved

    @_owned_workflow
    async def run_identifier_round_trip(self, *, structured: bool) -> TargetServerTriggerOutcome:
        """Send one run-owned identifier, verify it, and selectively clean it in all paths."""
        from asyncua import ua

        from helpers.identifier_utils import contains_identifier
        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN

        config = self._profile.cu_execution.identifier_workflows
        workflow = "structured_identifier_round_trip" if structured else "text_identifier_round_trip"
        method_name = BN.SEND_IDENTIFIERS if structured else BN.SEND_TEXT_IDENTIFIERS
        required_methods = {method_name, BN.RESET_IDENTIFIERS}
        allowed = self._profile.cu_execution.state_changing_methods
        if not config.enabled or workflow not in self._profile.workflow_execution.approved_workflows:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"Workflow '{workflow}' is not enabled and approved.",
                method=method_name,
                trigger_mode="identifier_round_trip",
            )
        if any(not allowed.allow_state_changing_method(name) for name in required_methods):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"Workflow '{workflow}' is missing method authorization.",
                method=method_name,
                trigger_mode="identifier_round_trip",
            )

        baseline_err = await self.ensure_clean_identifier_baseline()
        if baseline_err is not None:
            return baseline_err

        method_set = await self._get_asset_method_set()
        piu = await self._resolve_tool_piu()
        if method_set is None or not piu:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="AssetManagement MethodSet or Tool ProductInstanceUri is unavailable.",
                method=method_name,
                trigger_mode="identifier_round_trip",
            )
        blocked = self._claim_controlled_scope(piu)
        if blocked is not None:
            return blocked

        token = uuid.uuid4().hex[:12].upper()
        owned_value = f"IJT-TEST-{token}"
        identifier_name = f"IJT_ID_{token[:8]}"
        if structured:
            entity_type = getattr(ua, "EntityDataType", None)
            if entity_type is None:
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason="EntityDataType is unavailable after type-definition loading.",
                    method=method_name,
                    trigger_mode="identifier_round_trip",
                )
            entity = entity_type()
            entity.Name = identifier_name
            entity.Description = "IJT test identifier"
            entity.EntityId = owned_value
            entity.EntityOriginId = ""
            entity.IsExternal = True
            entity.EntityType = 22
            send_payload = ua.Variant([entity], ua.VariantType.ExtensionObject, is_array=True)
        else:
            send_payload = ua.Variant([owned_value], ua.VariantType.String, is_array=True)

        piu_arg = ua.Variant(piu, ua.VariantType.String)
        empty_names_arg = ua.Variant([], ua.VariantType.String, is_array=True)
        query_names_arg = ua.Variant([identifier_name] if structured else [], ua.VariantType.String, is_array=True)
        cleanup_names = [identifier_name]
        cleanup_verified = False
        execution_started = False
        send_settled = False
        sent: Any = None
        failure = ""
        final_reset = None
        original_error: BaseException | None = None
        try:
            execution_started = True
            sent = await find_and_call_method(
                method_set,
                method_name,
                await self._resolve_ijt_namespace_index(),
                piu_arg,
                send_payload,
                timeout=self._profile.cu_execution.default_timeout_seconds,
                target_server_authorized=True,
                preserve_status=True,
                before_dispatch=lambda: self._dispatch_mutation(method_name, piu, ""),
            )
            send_settled = self._method_succeeded(method_name, sent)
            if not send_settled:
                send_settled = self._method_call_rejected(sent)
                failure = f"{method_name} failed: {self._last_method_failure}"
            if not failure:
                read_back = await find_and_call_method(
                    method_set,
                    BN.GET_IDENTIFIERS,
                    await self._resolve_ijt_namespace_index(),
                    piu_arg,
                    query_names_arg,
                    timeout=self._profile.cu_execution.default_timeout_seconds,
                )
                read_entities = self._extract_get_identifiers_entities(read_back.output_list)
                if not self._get_identifiers_succeeded(read_back) or not contains_identifier(
                    read_entities, owned_value
                ):
                    failure = f"GetIdentifiers did not return the run-owned value {owned_value!r}."
                elif not structured:
                    resolved_names = self._resolve_readback_names(read_back.output_list, {owned_value})
                    if resolved_names:
                        cleanup_names = resolved_names
        except BaseException as exc:
            original_error = exc
            raise
        finally:
            try:
                cleanup_names_arg = ua.Variant(cleanup_names, ua.VariantType.String, is_array=True)
                final_reset = await find_and_call_method(
                    method_set,
                    BN.RESET_IDENTIFIERS,
                    await self._resolve_ijt_namespace_index(),
                    piu_arg,
                    cleanup_names_arg,
                    ua.Variant(False, ua.VariantType.Boolean),
                    ua.Variant(False, ua.VariantType.Boolean),
                    timeout=self._profile.cu_execution.default_timeout_seconds,
                    target_server_authorized=True,
                    preserve_status=True,
                    before_dispatch=lambda: self._dispatch_mutation(BN.RESET_IDENTIFIERS, piu, ""),
                )
                reset_succeeded = self._method_succeeded(BN.RESET_IDENTIFIERS, final_reset)
                reset_err = self._last_method_failure
                if reset_succeeded or (
                    sent is not None and not sent.success and getattr(final_reset, "status_code", None) is not None
                ):
                    final_after = await find_and_call_method(
                        method_set,
                        BN.GET_IDENTIFIERS,
                        await self._resolve_ijt_namespace_index(),
                        piu_arg,
                        empty_names_arg,
                        timeout=self._profile.cu_execution.default_timeout_seconds,
                    )
                    after_entities = self._extract_get_identifiers_entities(final_after.output_list)
                    cleanup_verified = self._get_identifiers_succeeded(final_after) and not contains_identifier(
                        after_entities,
                        owned_value,
                    )
                    if cleanup_verified and not reset_succeeded:
                        reset_succeeded = True
                    if cleanup_verified and not send_settled and sent is not None and sent.status_code is not None:
                        send_settled = True
                if (
                    cleanup_verified
                    and not structured
                    and config.allow_reset_all
                    and "reset_all_identifiers" in self._profile.workflow_execution.approved_workflows
                ):
                    broad_cleanup = await find_and_call_method(
                        method_set,
                        BN.RESET_IDENTIFIERS,
                        await self._resolve_ijt_namespace_index(),
                        piu_arg,
                        empty_names_arg,
                        ua.Variant(True, ua.VariantType.Boolean),
                        ua.Variant(False, ua.VariantType.Boolean),
                        timeout=self._profile.cu_execution.default_timeout_seconds,
                        target_server_authorized=True,
                        preserve_status=True,
                        before_dispatch=lambda: self._dispatch_mutation(BN.RESET_IDENTIFIERS, piu, ""),
                    )
                    if not self._method_succeeded(BN.RESET_IDENTIFIERS, broad_cleanup):
                        cleanup_verified = False
                        reset_succeeded = False
                        reset_err = self._last_method_failure
                if not reset_succeeded:
                    failure = f"{failure} Final selective cleanup failed: {reset_err}".strip()
                elif not cleanup_verified:
                    failure = f"{failure} Final selective cleanup could not be verified.".strip()
                if cleanup_verified and send_settled:
                    _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
            except BaseException as cleanup_error:
                logger.error("Selective identifier cleanup failed: %s", cleanup_error, exc_info=True)
                if original_error is None:
                    raise
            if not cleanup_verified or not send_settled:
                _RUN_SCOPED_EVIDENCE.mark_unfinished(
                    self._profile.target.endpoint,
                    piu,
                    TargetServerTriggerOutcome(
                        triggered=False,
                        method=method_name,
                        product_instance_uri=piu,
                        mutation_attempted=True,
                        execution_outcome="inconclusive",
                        reason_code="identifier_cleanup_unproven",
                        skip_reason=f"{original_error or failure or 'Identifier send did not settle.'} "
                        f"Reconcile run-owned identifier {owned_value!r} before further mutation.",
                    ),
                )

        return TargetServerTriggerOutcome(
            triggered=not failure and cleanup_verified,
            skip_reason=failure or None,
            method=method_name,
            trigger_mode="identifier_round_trip",
            product_instance_uri=piu,
            claim_mismatch=execution_started and bool(failure),
            mutation_attempted=execution_started,
            execution_outcome="inconclusive" if not cleanup_verified or not send_settled else "",
            reason_code="identifier_cleanup_unproven" if not cleanup_verified or not send_settled else "",
            expected_event_entity_ids=(owned_value,) if not failure and cleanup_verified else (),
            method_call_result=final_reset,
        )

    @_owned_workflow
    async def reset_all_identifiers(self) -> TargetServerTriggerOutcome:
        """Run the separately approved broad identifier reset and verify empty state."""
        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN

        config = self._profile.cu_execution.identifier_workflows
        approved = set(self._profile.workflow_execution.approved_workflows)
        allowed = self._profile.cu_execution.state_changing_methods
        if not config.allow_reset_all or "reset_all_identifiers" not in approved:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="Dedicated workflow 'reset_all_identifiers' is not explicitly approved.",
                method=BN.RESET_IDENTIFIERS,
                trigger_mode="reset_all_identifiers",
            )
        if not allowed.allow_state_changing_method(BN.RESET_IDENTIFIERS):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="ResetIdentifiers is not authorized by the SUT manifest.",
                method=BN.RESET_IDENTIFIERS,
                trigger_mode="reset_all_identifiers",
            )

        method_set = await self._get_asset_method_set()
        piu = await self._resolve_tool_piu()
        if method_set is None or not piu:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="AssetManagement MethodSet or Tool ProductInstanceUri is unavailable.",
                method=BN.RESET_IDENTIFIERS,
                trigger_mode="reset_all_identifiers",
            )
        blocked = self._claim_controlled_scope(piu)
        if blocked is not None:
            return blocked

        ns_ijt = await self._resolve_ijt_namespace_index()
        piu_arg = ua.Variant(piu, ua.VariantType.String)
        empty_names = ua.Variant([], ua.VariantType.String, is_array=True)
        reset = await find_and_call_method(
            method_set,
            BN.RESET_IDENTIFIERS,
            ns_ijt,
            piu_arg,
            empty_names,
            ua.Variant(True, ua.VariantType.Boolean),
            ua.Variant(False, ua.VariantType.Boolean),
            timeout=self._profile.cu_execution.default_timeout_seconds,
            target_server_authorized=True,
            preserve_status=True,
            before_dispatch=lambda: self._dispatch_mutation(BN.RESET_IDENTIFIERS, piu, ""),
        )
        if not self._method_succeeded(BN.RESET_IDENTIFIERS, reset):
            rejected = self._method_call_rejected(reset)
            if rejected:
                _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"ResetAll ResetIdentifiers failed: {self._last_method_failure}",
                method=BN.RESET_IDENTIFIERS,
                trigger_mode="reset_all_identifiers",
                product_instance_uri=piu,
                claim_mismatch=True,
                mutation_attempted=reset.rpc_dispatched is not False,
                execution_outcome="blocked"
                if reset.rpc_dispatched is False
                else "failed"
                if rejected
                else "inconclusive",
                reason_code="identifier_reset_unconfirmed",
            )

        _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
        after = await find_and_call_method(
            method_set,
            BN.GET_IDENTIFIERS,
            ns_ijt,
            piu_arg,
            empty_names,
            timeout=self._profile.cu_execution.default_timeout_seconds,
        )
        after_entities = self._extract_get_identifiers_entities(after.output_list)
        if not self._get_identifiers_succeeded(after) or bool(after_entities):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="ResetAll completed, but GetIdentifiers did not verify an empty identifier state.",
                method=BN.RESET_IDENTIFIERS,
                trigger_mode="reset_all_identifiers",
                product_instance_uri=piu,
                claim_mismatch=True,
                mutation_attempted=True,
                execution_outcome="failed" if after.success else "inconclusive",
                reason_code="identifier_reset_not_verified",
            )
        _RUN_SCOPED_EVIDENCE._identifier_baseline_cleaned.add((self._profile.target.endpoint, piu))
        return TargetServerTriggerOutcome(
            triggered=True,
            method=BN.RESET_IDENTIFIERS,
            trigger_mode="reset_all_identifiers",
            product_instance_uri=piu,
            method_call_result=reset,
        )

    async def ensure_clean_identifier_baseline(self) -> TargetServerTriggerOutcome | None:
        """Clear pre-existing controller identifiers once per run when ResetAll is approved."""
        from helpers.namespaces import BN

        config = self._profile.cu_execution.identifier_workflows
        approved = set(self._profile.workflow_execution.approved_workflows)
        allowed = self._profile.cu_execution.state_changing_methods
        if (
            not config.allow_reset_all
            or "reset_all_identifiers" not in approved
            or not allowed.allow_state_changing_method(BN.RESET_IDENTIFIERS)
        ):
            return None
        piu = await self._resolve_tool_piu()
        if not piu:
            return None
        if (self._profile.target.endpoint, piu) in _RUN_SCOPED_EVIDENCE._identifier_baseline_cleaned:
            return None
        outcome = await self.reset_all_identifiers()
        return None if outcome.triggered else outcome

    @_owned_workflow
    async def call_authorized_identifier_method(
        self,
        method_name: str,
        *args: Any,
        piu_override: str | None = None,
    ) -> tuple[TargetServerTriggerOutcome | None, Any]:
        """Execute a non-leaking identifier method check when authorized by the SUT manifest."""
        from dataclasses import replace

        from asyncua import ua

        from helpers.method_caller import find_and_call_method

        config = self._profile.cu_execution.identifier_workflows
        allowed = self._profile.cu_execution.state_changing_methods
        if not config.enabled or not allowed.allow_state_changing_method(method_name):
            return (
                TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"Identifier method '{method_name}' is not enabled and authorized.",
                    method=method_name,
                    trigger_mode="identifier_method_probe",
                ),
                None,
            )
        if piu_override is None:
            baseline_err = await self.ensure_clean_identifier_baseline()
            if baseline_err is not None:
                return baseline_err, None

        method_set = await self._get_asset_method_set()
        tool_piu = await self._resolve_tool_piu()
        target_piu = piu_override if piu_override is not None else tool_piu
        if method_set is None or not target_piu:
            return (
                TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason="AssetManagement MethodSet or Tool ProductInstanceUri is unavailable.",
                    method=method_name,
                    trigger_mode="identifier_method_probe",
                ),
                None,
            )
        scope_piu = tool_piu or target_piu
        blocked = self._claim_controlled_scope(scope_piu)
        if blocked is not None:
            return blocked, None

        try:
            call_result = await find_and_call_method(
                method_set,
                method_name,
                await self._resolve_ijt_namespace_index(),
                ua.Variant(target_piu, ua.VariantType.String),
                *args,
                timeout=self._profile.cu_execution.default_timeout_seconds,
                target_server_authorized=True,
                preserve_status=True,
                before_dispatch=lambda: self._dispatch_mutation(method_name, scope_piu, ""),
            )
            if not call_result.success and call_result.error is None:
                status_to_wrap = call_result.status_code
                if status_to_wrap is None and call_result.input_argument_status_codes:
                    status_to_wrap = next((c for c in call_result.input_argument_status_codes if c != 0), None)
                if status_to_wrap is not None:
                    call_result = replace(call_result, error=ua.UaStatusCodeError(status_to_wrap))
        finally:
            _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, scope_piu)
        return None, call_result

    @_owned_workflow
    async def run_identifier_result_workflow(
        self,
        subscription_client: Any,
        ns_indices: dict[str, int],
        *,
        structured: bool = True,
        entities_spec: list[tuple[str, str, int, bool]] | None = None,
        text_values: list[str] | None = None,
        reset_values_before_result: list[str] | None = None,
        reset_all_before_result: bool = False,
        cache_key: str = "",
    ) -> tuple[TargetServerTriggerOutcome, Any]:
        """Send test-owned identifier(s), optionally reset subset, collect 1 fresh SingleResult, and clean up."""
        from asyncua import ua

        from helpers.identifier_utils import contains_identifier
        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN, ResultType
        from helpers.result_collector import collect_single_evidence

        config = self._profile.cu_execution.identifier_workflows
        approved = set(self._profile.workflow_execution.approved_workflows)
        workflow = "structured_identifier_round_trip" if structured else "text_identifier_round_trip"
        method_name = BN.SEND_IDENTIFIERS if structured else BN.SEND_TEXT_IDENTIFIERS
        allowed = self._profile.cu_execution.state_changing_methods
        if not config.enabled or workflow not in approved:
            return (
                TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"Workflow '{workflow}' is not enabled and approved.",
                    method=method_name,
                    trigger_mode="identifier_result_workflow",
                ),
                None,
            )
        if any(not allowed.allow_state_changing_method(name) for name in (method_name, BN.RESET_IDENTIFIERS)):
            return (
                TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"Workflow '{workflow}' is missing method authorization.",
                    method=method_name,
                    trigger_mode="identifier_result_workflow",
                ),
                None,
            )

        method_set = await self._get_asset_method_set()
        piu = await self._resolve_tool_piu()
        if method_set is None or not piu:
            return (
                TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason="AssetManagement MethodSet or Tool ProductInstanceUri is unavailable.",
                    method=method_name,
                    trigger_mode="identifier_result_workflow",
                ),
                None,
            )

        cache_lookup_key = (self._profile.target.endpoint, piu, cache_key)
        if cache_key and cache_lookup_key in _RUN_SCOPED_EVIDENCE._external_identifier_results:
            return (
                TargetServerTriggerOutcome(
                    triggered=True,
                    method=method_name,
                    trigger_mode="identifier_result_workflow",
                    product_instance_uri=piu,
                    evidence_reused=True,
                ),
                _RUN_SCOPED_EVIDENCE._external_identifier_results[cache_lookup_key],
            )

        baseline_err = await self.ensure_clean_identifier_baseline()
        if baseline_err is not None:
            return baseline_err, None

        blocked = self._claim_controlled_scope(piu)
        if blocked is not None:
            return blocked, None

        all_sent_values: set[str] = set()
        cleanup_names: list[str] = []
        if structured:
            entity_cls = getattr(ua, "EntityDataType", None)
            if entity_cls is None:
                return (
                    TargetServerTriggerOutcome(
                        triggered=False,
                        skip_reason="EntityDataType is unavailable after type-definition loading.",
                        method=method_name,
                        trigger_mode="identifier_result_workflow",
                    ),
                    None,
                )
            specs = list(entities_spec or [])
            entity_objs = []
            for name, entity_id, entity_type_code, is_external in specs:
                ent = entity_cls()
                ent.Name = name
                ent.Description = "IJT test entity"
                ent.EntityId = entity_id
                ent.EntityOriginId = ""
                ent.EntityType = entity_type_code
                ent.IsExternal = is_external
                entity_objs.append(ent)
                all_sent_values.add(entity_id)
                cleanup_names.append(name)
            send_payload = ua.Variant(entity_objs, ua.VariantType.ExtensionObject, is_array=True)
        else:
            vals = list(text_values or [])
            all_sent_values.update(vals)
            cleanup_names.extend(vals)
            send_payload = ua.Variant(vals, ua.VariantType.String, is_array=True)

        ns_ijt = await self._resolve_ijt_namespace_index()
        piu_arg = ua.Variant(piu, ua.VariantType.String)
        empty_names_arg = ua.Variant([], ua.VariantType.String, is_array=True)
        cleanup_verified = False
        execution_started = False
        send_settled = False
        sent: Any = None
        failure = ""
        result_data: Any = None
        read_back: Any = None
        original_error: BaseException | None = None
        try:
            execution_started = True
            sent = await find_and_call_method(
                method_set,
                method_name,
                ns_ijt,
                piu_arg,
                send_payload,
                timeout=self._profile.cu_execution.default_timeout_seconds,
                target_server_authorized=True,
                preserve_status=True,
                before_dispatch=lambda: self._dispatch_mutation(method_name, piu, ""),
            )
            send_settled = self._method_succeeded(method_name, sent)
            if send_settled:
                _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
            else:
                send_settled = self._method_call_rejected(sent)
                if send_settled:
                    _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
                failure = f"{method_name} failed: {self._last_method_failure}"
            if not failure:
                read_back = await find_and_call_method(
                    method_set,
                    BN.GET_IDENTIFIERS,
                    ns_ijt,
                    piu_arg,
                    empty_names_arg,
                    timeout=self._profile.cu_execution.default_timeout_seconds,
                )
                read_entities = self._extract_get_identifiers_entities(read_back.output_list)
                missing_sent = [v for v in all_sent_values if not contains_identifier(read_entities, v)]
                if not self._get_identifiers_succeeded(read_back) or missing_sent:
                    failure = f"GetIdentifiers did not return sent identifier(s): {missing_sent}."
                else:
                    resolved_all = self._resolve_readback_names(read_back.output_list, all_sent_values)
                    if resolved_all:
                        cleanup_names = resolved_all

            if (
                not failure
                and reset_all_before_result
                and config.allow_reset_all
                and "reset_all_identifiers" in approved
            ):
                pre_reset_all = await find_and_call_method(
                    method_set,
                    BN.RESET_IDENTIFIERS,
                    ns_ijt,
                    piu_arg,
                    empty_names_arg,
                    ua.Variant(True, ua.VariantType.Boolean),
                    ua.Variant(False, ua.VariantType.Boolean),
                    timeout=self._profile.cu_execution.default_timeout_seconds,
                    target_server_authorized=True,
                    preserve_status=True,
                    before_dispatch=lambda: self._dispatch_mutation(BN.RESET_IDENTIFIERS, piu, ""),
                )
                if self._method_succeeded(BN.RESET_IDENTIFIERS, pre_reset_all):
                    _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
                    after_pre = await find_and_call_method(
                        method_set,
                        BN.GET_IDENTIFIERS,
                        ns_ijt,
                        piu_arg,
                        empty_names_arg,
                        timeout=self._profile.cu_execution.default_timeout_seconds,
                    )
                    after_pre_entities = self._extract_get_identifiers_entities(after_pre.output_list)
                    check_vals = set(reset_values_before_result) if reset_values_before_result else all_sent_values
                    still_present = [v for v in check_vals if contains_identifier(after_pre_entities, v)]
                    if not self._get_identifiers_succeeded(after_pre) or still_present:
                        failure = f"Pre-result ResetIdentifiers(ResetAll=True) left value(s) active: {still_present}."
                    else:
                        cleanup_names = []
                else:
                    if self._method_call_rejected(pre_reset_all):
                        _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
                    failure = f"Pre-result ResetIdentifiers(ResetAll=True) failed: {self._last_method_failure}"
            elif not failure and reset_values_before_result:
                target_vals = set(reset_values_before_result)
                pre_reset_names = self._resolve_readback_names(read_back.output_list, target_vals)
                if not pre_reset_names:
                    pre_reset_names = list(reset_values_before_result)
                pre_reset = await find_and_call_method(
                    method_set,
                    BN.RESET_IDENTIFIERS,
                    ns_ijt,
                    piu_arg,
                    ua.Variant(pre_reset_names, ua.VariantType.String, is_array=True),
                    ua.Variant(False, ua.VariantType.Boolean),
                    ua.Variant(False, ua.VariantType.Boolean),
                    timeout=self._profile.cu_execution.default_timeout_seconds,
                    target_server_authorized=True,
                    preserve_status=True,
                    before_dispatch=lambda: self._dispatch_mutation(BN.RESET_IDENTIFIERS, piu, ""),
                )
                if self._method_succeeded(BN.RESET_IDENTIFIERS, pre_reset):
                    _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
                    after_pre = await find_and_call_method(
                        method_set,
                        BN.GET_IDENTIFIERS,
                        ns_ijt,
                        piu_arg,
                        empty_names_arg,
                        timeout=self._profile.cu_execution.default_timeout_seconds,
                    )
                    after_pre_entities = self._extract_get_identifiers_entities(after_pre.output_list)
                    still_present = [v for v in target_vals if contains_identifier(after_pre_entities, v)]
                    if not self._get_identifiers_succeeded(after_pre) or still_present:
                        failure = f"Pre-result ResetIdentifiers left value(s) active: {still_present}."
                    else:
                        cleanup_names = [n for n in cleanup_names if n not in set(pre_reset_names)]
                else:
                    if self._method_call_rejected(pre_reset):
                        _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
                    failure = f"Selective pre-result ResetIdentifiers failed: {self._last_method_failure}"

            if not failure:
                saved_records = dict(_RUN_SCOPED_EVIDENCE._records)
                try:
                    result_data = await collect_single_evidence(
                        subscription_client,
                        self,
                        ns_indices,
                        ResultType.MULTI_STEP_OK_RESULT,
                        fresh=True,
                    )
                finally:
                    _RUN_SCOPED_EVIDENCE._records.clear()
                    _RUN_SCOPED_EVIDENCE._records.update(saved_records)
        except BaseException as exc:
            original_error = exc
            raise
        finally:
            try:
                reset_ok = True
                reset_err = ""
                if cleanup_names and sent is not None and sent.success:
                    selective_reset = await find_and_call_method(
                        method_set,
                        BN.RESET_IDENTIFIERS,
                        ns_ijt,
                        piu_arg,
                        ua.Variant(cleanup_names, ua.VariantType.String, is_array=True),
                        ua.Variant(False, ua.VariantType.Boolean),
                        ua.Variant(False, ua.VariantType.Boolean),
                        timeout=self._profile.cu_execution.default_timeout_seconds,
                        target_server_authorized=True,
                        preserve_status=True,
                        before_dispatch=lambda: self._dispatch_mutation(BN.RESET_IDENTIFIERS, piu, ""),
                    )
                    reset_ok = self._method_succeeded(BN.RESET_IDENTIFIERS, selective_reset)
                    reset_err = self._last_method_failure
                if config.allow_reset_all and "reset_all_identifiers" in approved:
                    broad_reset = await find_and_call_method(
                        method_set,
                        BN.RESET_IDENTIFIERS,
                        ns_ijt,
                        piu_arg,
                        empty_names_arg,
                        ua.Variant(True, ua.VariantType.Boolean),
                        ua.Variant(False, ua.VariantType.Boolean),
                        timeout=self._profile.cu_execution.default_timeout_seconds,
                        target_server_authorized=True,
                        preserve_status=True,
                        before_dispatch=lambda: self._dispatch_mutation(BN.RESET_IDENTIFIERS, piu, ""),
                    )
                    reset_ok = self._method_succeeded(BN.RESET_IDENTIFIERS, broad_reset)
                    if not reset_ok:
                        reset_err = self._last_method_failure
                elif cleanup_names and (sent is None or not sent.success):
                    selective_reset = await find_and_call_method(
                        method_set,
                        BN.RESET_IDENTIFIERS,
                        ns_ijt,
                        piu_arg,
                        ua.Variant(cleanup_names, ua.VariantType.String, is_array=True),
                        ua.Variant(False, ua.VariantType.Boolean),
                        ua.Variant(False, ua.VariantType.Boolean),
                        timeout=self._profile.cu_execution.default_timeout_seconds,
                        target_server_authorized=True,
                        preserve_status=True,
                        before_dispatch=lambda: self._dispatch_mutation(BN.RESET_IDENTIFIERS, piu, ""),
                    )
                    reset_ok = self._method_succeeded(BN.RESET_IDENTIFIERS, selective_reset)
                    reset_err = self._last_method_failure
                if reset_ok or (sent is not None and not sent.success):
                    final_after = await find_and_call_method(
                        method_set,
                        BN.GET_IDENTIFIERS,
                        ns_ijt,
                        piu_arg,
                        empty_names_arg,
                        timeout=self._profile.cu_execution.default_timeout_seconds,
                    )
                    final_entities = self._extract_get_identifiers_entities(final_after.output_list)
                    cleanup_verified = self._get_identifiers_succeeded(final_after) and not any(
                        contains_identifier(final_entities, v) for v in all_sent_values
                    )
                    if cleanup_verified and not reset_ok:
                        reset_ok = True
                    if cleanup_verified and not send_settled and sent is not None and sent.status_code is not None:
                        send_settled = True
                if not reset_ok:
                    failure = f"{failure} Final identifier cleanup failed: {reset_err}".strip()
                elif not cleanup_verified:
                    failure = f"{failure} Final identifier cleanup could not be verified.".strip()
                if cleanup_verified and send_settled:
                    _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
            except BaseException as cleanup_error:
                logger.error("Identifier result workflow cleanup failed: %s", cleanup_error, exc_info=True)
                if original_error is None:
                    raise
            if not cleanup_verified or not send_settled:
                _RUN_SCOPED_EVIDENCE.mark_unfinished(
                    self._profile.target.endpoint,
                    piu,
                    TargetServerTriggerOutcome(
                        triggered=False,
                        method=method_name,
                        product_instance_uri=piu,
                        mutation_attempted=True,
                        execution_outcome="inconclusive",
                        reason_code="identifier_cleanup_unproven",
                        skip_reason=f"{original_error or failure or 'Identifier workflow did not settle.'} "
                        f"Reconcile run-owned identifiers {sorted(all_sent_values)!r} before further mutation.",
                    ),
                )

        triggered_ok = not failure and cleanup_verified and result_data is not None
        if triggered_ok and cache_key:
            _RUN_SCOPED_EVIDENCE._external_identifier_results[cache_lookup_key] = result_data
        return (
            TargetServerTriggerOutcome(
                triggered=triggered_ok,
                skip_reason=failure
                or ("No result received after identifier injection." if result_data is None else None),
                method=method_name,
                trigger_mode="identifier_result_workflow",
                product_instance_uri=piu,
                claim_mismatch=execution_started and bool(failure),
                mutation_attempted=execution_started,
                execution_outcome="inconclusive" if not cleanup_verified or not send_settled else "",
                reason_code="identifier_cleanup_unproven" if not cleanup_verified or not send_settled else "",
            ),
            result_data,
        )

    @_owned_workflow
    async def trigger_counter_effect(
        self, effect_index: int = 0, *, verify_delta: bool = False
    ) -> TargetServerTriggerOutcome:
        self._counter_attempt_key = None
        scope = _RUN_SCOPED_EVIDENCE.current_workflow()
        if scope is not None and not scope.dispatches:
            self._start_attempts = 0
        try:
            outcome = await self._execute_counter_effect(effect_index, verify_delta=verify_delta)
        except (Exception, asyncio.CancelledError) as exc:
            key = self._counter_attempt_key
            if key is not None and key in _COUNTER_ATTEMPTS and _COUNTER_ATTEMPTS[key] is None:
                unknown = TargetServerTriggerOutcome(
                    triggered=False,
                    mutation_attempted=True,
                    execution_outcome="inconclusive",
                    reason_code="mutation_outcome_unknown",
                    skip_reason=f"Counter observation interrupted by {type(exc).__name__}: {exc}",
                    product_instance_uri=key[1],
                )
                _COUNTER_ATTEMPTS[key] = unknown
                _RUN_SCOPED_EVIDENCE.mark_unfinished(key[0], key[1], unknown)
            raise
        key = self._counter_attempt_key
        if (
            key is not None
            and key not in _COUNTER_ATTEMPTS
            and outcome.method_call_result is not None
            and outcome.method_call_result.rpc_dispatched is not False
            and outcome.method == self._profile.cu_execution.counter_effects[effect_index].method
        ):
            _COUNTER_ATTEMPTS[key] = None
        if key is not None and key in _COUNTER_ATTEMPTS and _COUNTER_ATTEMPTS[key] is None:
            _COUNTER_ATTEMPTS[key] = outcome
            rejected = outcome.method_call_result is not None and self._method_call_rejected(outcome.method_call_result)
            if (
                outcome.mutation_attempted
                and not rejected
                and not outcome.process_settled
                and (not outcome.triggered or _RUN_SCOPED_EVIDENCE.unfinished(key[0], key[1]) is not None)
            ):
                boundary = (
                    replace(
                        outcome,
                        triggered=False,
                        execution_outcome="inconclusive",
                        reason_code="compound_process_completion_unproven",
                        skip_reason="Counter evidence was captured, but the selected compound process remains unfinished.",
                    )
                    if outcome.triggered
                    else outcome
                )
                _RUN_SCOPED_EVIDENCE.mark_unfinished(key[0], key[1], boundary)
        self._record_workflow_action(
            "scenario_outcome",
            outcome.product_instance_uri,
            outcome.joining_process_id,
            triggered=outcome.triggered,
            reason_code=outcome.reason_code,
            mutation_attempted=outcome.mutation_attempted,
            prior_unresolved_action=outcome.prior_unresolved_action,
        )
        return outcome

    async def trigger_counter_method(self, method: str) -> TargetServerTriggerOutcome:
        for index, effect in enumerate(self._profile.cu_execution.counter_effects):
            if effect.method == method:
                return await self.trigger_counter_effect(index)
        return TargetServerTriggerOutcome(
            triggered=False,
            method=method,
            execution_outcome="blocked",
            reason_code="counter_method_route_unavailable",
            skip_reason=f"No approved counter-effect scenario is configured for {method}.",
        )

    async def _execute_counter_effect(
        self, effect_index: int = 0, *, verify_delta: bool = False
    ) -> TargetServerTriggerOutcome:
        """Invoke one counter mutation and correlate its InterventionResult with the affected parent."""
        from asyncua import ua

        from helpers.counter_obligations import CounterEvidenceUnavailable, counter_snapshot, require_counter_delta
        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import NS_IJT_BASE
        from helpers.result_collector import (
            ResultCollector,
            ResultProgression,
            get_classification,
            get_result_id,
            is_partial,
            is_terminal_completed,
            is_terminal_matching_state,
            is_terminal_result,
            references_result_id,
        )

        effects = self._profile.cu_execution.counter_effects
        if os.environ.get("PYTEST_XDIST_WORKER"):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="Physical counter workflows require serial execution.",
                method="CounterEffect",
                reason_code="parallel_physical_workflow",
            )
        if "counter_intervention" not in self._profile.workflow_execution.approved_workflows:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="Workflow 'counter_intervention' is not approved at runtime.",
                method="CounterEffect",
                trigger_mode="counter_effect",
            )
        if effect_index < 0 or effect_index >= len(effects):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"No counter-effect scenario exists at index {effect_index}.",
                method="CounterEffect",
                trigger_mode="counter_effect",
            )
        effect = effects[effect_index]
        verify_delta = verify_delta or effect.verify_delta
        if verify_delta and self._result_classification_value(effect.expected_result_classification) is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                method=effect.method,
                execution_outcome="blocked",
                reason_code="counter_delta_source_unavailable",
                skip_reason="Counter delta requires an affected-result source before selection or mutation.",
            )
        if (
            effect.process_policy == "discover_unique"
            and not self._profile.workflow_execution.allow_discovered_processes
        ):
            return TargetServerTriggerOutcome(
                triggered=False,
                method=effect.method,
                trigger_mode="counter_effect",
                skip_reason="Discovered counter candidates are not approved.",
                reason_code="candidate_scope_not_approved",
            )
        if not self._profile.cu_execution.state_changing_methods.allow_state_changing_method(effect.method):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"{effect.method} is not authorized by the SUT manifest.",
                method=effect.method,
                trigger_mode="counter_effect",
            )
        if not self._profile.cu_execution.state_changing_methods.allow_state_changing_method("SelectJoiningProcess"):
            return TargetServerTriggerOutcome(
                triggered=False,
                method=effect.method,
                trigger_mode="counter_effect",
                skip_reason="SelectJoiningProcess is not authorized for counter setup.",
                reason_code="unsafe_method_not_enabled",
            )
        cached_capture_possible = self._profile.workflow_execution.evidence_reuse.enabled and any(
            key[0] == self._profile.target.endpoint and key[2] == self._profile.source_path and key[3] == effect_index
            for key, previous in _COUNTER_ATTEMPTS.items()
        )
        if self._subscription_client is None and not cached_capture_possible:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="Counter-effect workflows require a separate subscription client.",
                method=effect.method,
                trigger_mode="counter_effect",
            )

        jpm_node = await self._get_joining_process_management()
        piu = await self._resolve_tool_piu()
        attempt_key = (self._profile.target.endpoint, piu, self._profile.source_path, effect_index)
        if any(key[0] == attempt_key[0] and key[2:] == attempt_key[2:] and key[1] != piu for key in _COUNTER_ATTEMPTS):
            return TargetServerTriggerOutcome(
                triggered=False,
                method=effect.method,
                execution_outcome="inconclusive",
                mutation_attempted=True,
                reason_code="mutation_retry_prohibited",
                skip_reason="This configured counter experiment is already bound to another Tool in this run.",
            )
        previous = _COUNTER_ATTEMPTS.get(attempt_key)
        if previous is not None and not previous.triggered:
            return replace(
                previous,
                skip_reason=f"{previous.skip_reason} This run will not repeat the counter mutation.",
            )
        processes = await self._get_joining_process_list(jpm_node, piu) if jpm_node is not None else []
        selection = self._profile.selection.joining_processes.get(
            effect.process_classification, self._profile.selection.joining_process
        )
        candidates = counter_candidates(processes, effect, selection)
        if len(candidates) != 1:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=(
                    f"Counter-effect selector '{effect.match_by}' matched "
                    f"{len(candidates)} current processes; exactly one is required."
                ),
                method=effect.method,
                trigger_mode="counter_effect",
                product_instance_uri=piu,
            )

        process = candidates[0]
        fingerprint = self._process_list_fingerprint(processes)
        process_id = self._process_field(
            process,
            "JoiningProcessId",
            "JoiningProcessIdentification",
            "Id",
        )
        attempt_key = (self._profile.target.endpoint, piu, self._profile.source_path, effect_index)
        self._counter_attempt_key = attempt_key
        if self._profile.workflow_execution.evidence_reuse.enabled:
            self._observed_server_epoch = await self._read_observed_server_epoch() or ()
        if attempt_key in _COUNTER_ATTEMPTS:
            previous = _COUNTER_ATTEMPTS[attempt_key]
            if previous is not None and not previous.triggered:
                return replace(
                    previous,
                    skip_reason=f"{previous.skip_reason} This run will not repeat the counter mutation.",
                )
            if (
                previous is not None
                and previous.triggered
                and self._profile.workflow_execution.evidence_reuse.enabled
                and bool(self._observed_server_epoch)
                and previous.pre_trigger_baseline.get("observed_server_epoch") == self._observed_server_epoch
                and previous.joining_process_id == process_id
                and previous.pre_trigger_baseline.get("catalog_fingerprint") == fingerprint
                and previous.pre_trigger_baseline.get("selection_names") == sorted(selection_names(process))
                and previous.pre_trigger_baseline.get("counter_config") == asdict(effect)
                and previous.pre_trigger_baseline.get("selection_config") == asdict(selection)
                and previous.pre_trigger_baseline.get("configured_virtual_station_uri", "")
                == self._profile.selection.tool.virtual_station_product_instance_uri
                and previous.pre_trigger_baseline.get("associated_entity_expectations", [])
                == [asdict(rule) for rule in self.associated_entity_expectations]
            ):
                if verify_delta and not previous.pre_trigger_baseline.get("counter_delta_verified"):
                    return replace(
                        previous,
                        triggered=False,
                        execution_outcome="inconclusive",
                        reason_code="counter_delta_baseline_unavailable",
                        skip_reason="The retained counter attempt did not prove a before/after delta. It will not be repeated.",
                    )
                reused = replace(previous, evidence_reused=True)
                self._record_workflow_action("counter_evidence_reused", piu, process_id, method=effect.method)
                return reused
            return TargetServerTriggerOutcome(
                triggered=False,
                method=effect.method,
                trigger_mode="counter_effect",
                skip_reason="This run already attempted the counter effect; no additional mutation is permitted.",
                execution_outcome="inconclusive",
                mutation_attempted=True,
                reason_code="mutation_retry_prohibited",
            )
        if effect_index in self._counter_attempts:
            return TargetServerTriggerOutcome(
                triggered=False,
                method=effect.method,
                skip_reason="Counter mutation already attempted; retargeting or retry is prohibited.",
                mutation_attempted=True,
                execution_outcome="inconclusive",
                reason_code="mutation_retry_prohibited",
            )
        blocked = await self._ensure_baseline(jpm_node, piu, process, fingerprint)
        if blocked is not None:
            return blocked
        if self._subscription_client is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                method=effect.method,
                skip_reason="New counter mutation requires a separate subscription client.",
                execution_outcome="blocked",
                reason_code="counter_subscription_required",
            )
        if not process_id or not await self._target_context_current(jpm_node, piu, process, fingerprint):
            return TargetServerTriggerOutcome(
                triggered=False,
                method=effect.method,
                trigger_mode="counter_effect",
                skip_reason="Counter target is missing or changed before selection.",
                reason_code="target_changed",
            )
        if not await self._select_joining_process(
            jpm_node,
            process,
            piu,
            identifier_strategy=effect.identifier_strategy,
            selection_name=effect.selection_name,
        ):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"SelectJoiningProcess failed for counter candidate '{process_id}'.",
                method=effect.method,
                trigger_mode="counter_effect",
                product_instance_uri=piu,
                joining_process_id=process_id,
            )
        await self._wait_for_process_selection_settle()
        identification = self._make_process_identification(
            process,
            identifier_strategy=effect.identifier_strategy,
            selection_name=effect.selection_name,
        )
        if identification is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="JoiningProcessIdentificationDataType is unavailable.",
                method=effect.method,
                trigger_mode="counter_effect",
                product_instance_uri=piu,
                joining_process_id=process_id,
            )
        if not await self._target_context_current(jpm_node, piu, process, fingerprint):
            return TargetServerTriggerOutcome(
                triggered=False,
                method=effect.method,
                trigger_mode="counter_effect",
                skip_reason="Counter catalog or bound identity changed before mutation.",
                reason_code="target_changed",
                product_instance_uri=piu,
                joining_process_id=process_id,
            )

        expected_classification = self._result_classification_value(effect.expected_result_classification)
        expected_state = self._profile.workflow_execution.expected_results.expected_terminal_result_state
        counter_expected_state = effect.expected_terminal_result_state or expected_state
        ns_indices = {NS_IJT_BASE: await self._resolve_ijt_namespace_index()}
        counter_station = self._profile.selection.tool.virtual_station_product_instance_uri

        def matches_counter_context(candidate: Any, results: tuple[Any, ...]) -> bool:
            return self._counter_result_matches_asset_context(candidate, piu, counter_station) and (
                self._counter_result_matches_context(candidate, piu, process_id, counter_station)
                or ResultCollector.has_owned_ancestry(
                    candidate,
                    self._process_result_classification(process),
                    lambda parent: self._counter_result_matches_context(parent, piu, process_id, counter_station),
                    results,
                )
            )

        def _post_counter_offset(results: tuple[Any, ...]) -> int:
            if (
                counter_boundary
                and len(results) >= counter_boundary
                and all(id(results[idx]) in before_counter_objects for idx in range(counter_boundary))
            ):
                return counter_boundary
            return 0

        def find_evidence(results: tuple[Any, ...]) -> tuple[Any | None, Any | None]:
            post_counter_results = [
                candidate
                for candidate in results[_post_counter_offset(results) :]
                if id(candidate) not in before_counter_objects
            ]
            interventions = [
                candidate
                for candidate in post_counter_results
                if is_terminal_completed(candidate, ResultClassification.INTERVENTION_RESULT)
                and matches_counter_context(candidate, results)
                and bool(get_result_id(candidate))
                and get_result_id(candidate) not in before_counter_ids
            ]
            for intervention_candidate in reversed(interventions):
                if expected_classification is None:
                    return intervention_candidate, None
                intervention_id = get_result_id(intervention_candidate)
                if not intervention_id:
                    continue
                for affected_candidate in reversed(post_counter_results):
                    candidate_id = get_result_id(affected_candidate)
                    if (
                        matches_counter_context(affected_candidate, results)
                        and get_classification(affected_candidate) == expected_classification
                        and bool(candidate_id)
                        and (candidate_id not in before_counter_ids or candidate_id in before_partial_ids)
                        and references_result_id(affected_candidate, intervention_id, results)
                    ):
                        return intervention_candidate, affected_candidate
            return (interventions[-1], None) if interventions else (None, None)

        def evidence_ready(results: tuple[Any, ...]) -> bool:
            intervention_candidate, affected_candidate = find_evidence(results)
            return (
                intervention_candidate is not None
                and (expected_classification is None or affected_candidate is not None)
            ) or any(
                is_terminal_result(candidate, ResultClassification.INTERVENTION_RESULT)
                and not is_terminal_completed(candidate, ResultClassification.INTERVENTION_RESULT)
                and matches_counter_context(candidate, results)
                and get_result_id(candidate)
                and get_result_id(candidate) not in before_counter_ids
                for candidate in results
            )

        async with ResultCollector(
            self._subscription_client,
            ns_indices,
            is_simulator=False,
            parent_result_reader=self._read_parent_result,
            result_observer=lambda result, duplicate: self._observe_result(
                piu, process_id, "", result, duplicate, counter_virtual_station_uri=counter_station
            ),
        ) as collector:
            collector.discard_pending()
            baseline = None
            baseline_starts = 0
            baseline_operation_id = ""
            before_counter_objects: set[int] = set()
            before_counter_ids: set[str] = set()
            before_partial_ids: set[str] = set()
            counter_boundary = 0
            process_settled = False
            process_progression = None
            joining_results_confirmed = 0
            delta_verified = False
            delta_error: Exception | None = None
            completion_issue = ""
            if verify_delta:

                def baseline_ready(results):
                    return any(
                        matches_counter_context(candidate, results)
                        and get_classification(candidate) == expected_classification
                        and bool(getattr(candidate.ResultMetaData, "ResultCounters", None))
                        for candidate in results
                    )

                baseline_capture = await collector.collect_evidence(baseline_ready, self.passive_observation_timeout_s)
                if not baseline_ready(baseline_capture.all_results) and baseline_capture.is_lossless:
                    can_start = (
                        self._profile.triggers.result.mode == "start_selected_joining"
                        and "remote_start_multi_operation_job" in self._profile.workflow_execution.approved_workflows
                        and self._profile.cu_execution.state_changing_methods.allow_state_changing_method(
                            "StartSelectedJoining"
                        )
                        and self._process_start_limit(process) > self._start_attempts
                        and self._profile.workflow_execution.max_total_start_invocations > self._start_attempts
                    )
                    if can_start:
                        if not await self._target_context_current(jpm_node, piu, process, fingerprint):
                            return TargetServerTriggerOutcome(
                                triggered=False,
                                method=effect.method,
                                execution_outcome="blocked",
                                reason_code="target_changed",
                                skip_reason="Counter target changed before baseline acquisition.",
                            )
                        if not await self._start_selected_joining(
                            jpm_node, piu, self._profile.triggers.result.deselect_after_joining
                        ):
                            return TargetServerTriggerOutcome(
                                triggered=False,
                                method="StartSelectedJoining",
                                product_instance_uri=piu,
                                joining_process_id=process_id,
                                mutation_attempted=self._mutation_attempted(),
                                execution_outcome="inconclusive",
                                reason_code="counter_baseline_start_unconfirmed",
                                skip_reason=self._last_method_failure,
                            )
                        baseline_starts = 1
                        process_classification = self._process_result_classification(process)
                        context = lambda candidate: self._result_matches_context(candidate, piu, process_id)
                        operation = await collector.collect_correlated_operation_outcome(
                            requested_result_classification=process_classification,
                            predicate=context,
                            operation_predicate=context,
                            operation_context_predicate=lambda result: self._result_matches_tool_context(result, piu),
                            operation_timeout_s=self.active_result_timeout_s,
                            terminal_drain_seconds=self._profile.workflow_execution.consecutive_start_delay_seconds,
                            expected_terminal_state=expected_state,
                        )
                        if operation.timed_out or not operation.operation_confirmed:
                            return TargetServerTriggerOutcome(
                                triggered=False,
                                method="StartSelectedJoining",
                                product_instance_uri=piu,
                                joining_process_id=process_id,
                                mutation_attempted=True,
                                execution_outcome="inconclusive",
                                starts_issued=1,
                                operation_count=1,
                                reason_code="counter_baseline_operation_unproven",
                                skip_reason="The baseline start has no lossless owned operation evidence.",
                            )
                        if operation.operation_result is not None:
                            baseline_operation_id = get_result_id(operation.operation_result)
                        mismatch = self._unexpected_terminal_outcome(
                            operation.terminal_result,
                            expected_state,
                            piu,
                            process_id,
                            starts_issued=baseline_starts,
                            results_confirmed=int(operation.operation_result is not None),
                            process_progression=ResultCollector.progression_from_capture(
                                collector.capture_pending(),
                                process_classification,
                                expected_terminal_state=expected_state,
                                predicate=context,
                            ),
                        )
                        if mismatch is not None:
                            return mismatch
                        baseline_capture = await collector.collect_evidence(
                            lambda results: (
                                baseline_ready(results)
                                or any(
                                    context(candidate) and is_terminal_result(candidate, process_classification)
                                    for candidate in results
                                )
                            ),
                            self.active_result_timeout_s,
                        )
                if baseline_capture.is_lossless:
                    baseline = next(
                        (
                            candidate
                            for candidate in reversed(baseline_capture.all_results)
                            if matches_counter_context(candidate, baseline_capture.all_results)
                            and get_classification(candidate) == expected_classification
                            and bool(getattr(candidate.ResultMetaData, "ResultCounters", None))
                        ),
                        None,
                    )
                baseline_issue = None
                try:
                    if baseline is None:
                        raise CounterEvidenceUnavailable(
                            "counter_delta_baseline_unavailable",
                            "No fresh joining-process counter baseline was observed. No counter call was dispatched.",
                        )
                    baseline_values = counter_snapshot(
                        baseline, counter_name=effect.counter_name, counter_type=effect.counter_type
                    )
                    if len(baseline_values) != 1 or not get_result_id(baseline):
                        raise CounterEvidenceUnavailable(
                            "counter_delta_baseline_ambiguous",
                            "The selector does not identify one counter with a fresh ResultId. No counter call was dispatched.",
                        )
                except CounterEvidenceUnavailable as exc:
                    baseline_issue = TargetServerTriggerOutcome(
                        triggered=False,
                        method=effect.method,
                        execution_outcome="blocked",
                        reason_code=exc.reason_code,
                        skip_reason=str(exc),
                    )
                except ValueError as exc:
                    baseline_issue = TargetServerTriggerOutcome(
                        triggered=False,
                        method=effect.method,
                        execution_outcome="failed",
                        reason_code="counter_baseline_data_invalid",
                        skip_reason=str(exc),
                    )
                if baseline_issue is not None:
                    if baseline_starts and baseline_capture.is_lossless and baseline_operation_id:
                        completion = await self._continue_owned_process(
                            collector,
                            jpm_node,
                            piu,
                            process,
                            fingerprint,
                            starts_issued=baseline_starts,
                            results_confirmed=baseline_starts,
                            required_result_ids=frozenset({baseline_operation_id}),
                        )
                        if completion.reason_code == "unexpected_terminal_result_state":
                            return replace(completion, method=effect.method)
                        return replace(
                            baseline_issue,
                            product_instance_uri=piu,
                            joining_process_id=process_id,
                            mutation_attempted=True,
                            starts_issued=completion.starts_issued,
                            operation_count=completion.operation_count,
                            results_confirmed=completion.results_confirmed,
                            process_settled=completion.process_settled,
                            process_progression=completion.process_progression,
                            execution_outcome=baseline_issue.execution_outcome
                            if completion.process_settled
                            else "inconclusive",
                            skip_reason=f"{baseline_issue.skip_reason} {completion.skip_reason or ''}".strip(),
                        )
                    return replace(
                        baseline_issue,
                        product_instance_uri=piu,
                        joining_process_id=process_id,
                        mutation_attempted=bool(baseline_starts),
                        starts_issued=baseline_starts,
                        execution_outcome="inconclusive" if baseline_starts else baseline_issue.execution_outcome,
                    )
                action_boundary = collector.capture_pending()
                if not action_boundary.is_lossless:
                    return TargetServerTriggerOutcome(
                        triggered=False,
                        method=effect.method,
                        product_instance_uri=piu,
                        joining_process_id=process_id,
                        mutation_attempted=bool(baseline_starts),
                        execution_outcome="inconclusive" if baseline_starts else "blocked",
                        reason_code="counter_baseline_capture_overflow",
                        skip_reason="Baseline acquisition lost events. No counter call was dispatched.",
                    )
                parent = ResultCollector.progression_from_capture(
                    action_boundary,
                    self._process_result_classification(process),
                    expected_terminal_state=expected_state,
                    predicate=lambda candidate: self._result_matches_context(candidate, piu, process_id),
                )
                mismatch = self._unexpected_terminal_outcome(
                    parent.terminal_result,
                    expected_state,
                    piu,
                    process_id,
                    starts_issued=baseline_starts,
                    results_confirmed=baseline_starts,
                    process_progression=parent,
                )
                if mismatch is not None:
                    return mismatch
                if baseline_starts:
                    if parent.terminal_result is not None:
                        completion = await self._continue_owned_process(
                            collector,
                            jpm_node,
                            piu,
                            process,
                            fingerprint,
                            starts_issued=baseline_starts,
                            results_confirmed=baseline_starts,
                            required_result_ids=frozenset({baseline_operation_id}),
                        )
                        return replace(
                            completion,
                            triggered=False,
                            method=effect.method,
                            execution_outcome="blocked" if completion.process_settled else "inconclusive",
                            reason_code="counter_parent_completed_before_mutation",
                            skip_reason="Baseline acquisition completed the parent before the counter experiment. "
                            "No counter call or additional joining start was issued.",
                        )
                counter_boundary = len(action_boundary.all_results)
                before_counter_objects = {id(candidate) for candidate in action_boundary.all_results}
                before_counter_ids = {
                    get_result_id(candidate) for candidate in action_boundary.all_results if get_result_id(candidate)
                }
                before_partial_ids = {
                    get_result_id(candidate)
                    for candidate in action_boundary.all_results
                    if is_partial(candidate) and get_result_id(candidate)
                }
            else:
                action_boundary = collector.capture_pending()
                if not action_boundary.is_lossless:
                    return TargetServerTriggerOutcome(
                        triggered=False,
                        method=effect.method,
                        execution_outcome="blocked",
                        reason_code="counter_baseline_capture_overflow",
                        skip_reason="Pre-counter capture lost events. No counter call was dispatched.",
                    )
                counter_boundary = len(action_boundary.all_results)
                before_counter_objects = {id(candidate) for candidate in action_boundary.all_results}
                before_counter_ids = {
                    get_result_id(candidate) for candidate in action_boundary.all_results if get_result_id(candidate)
                }
                before_partial_ids = {
                    get_result_id(candidate)
                    for candidate in action_boundary.all_results
                    if is_partial(candidate) and get_result_id(candidate)
                }
            if not counter_station:
                counter_station = self._counter_station_from_joining_results(
                    action_boundary.all_results, piu, process_id
                )
            if not counter_station:
                counter_station = await self._discover_counter_station_fallback(piu, process_id)
            self._record_workflow_action(
                "counter_attempt",
                piu,
                process_id,
                method=effect.method,
                count=effect.count,
                catalog_fingerprint=fingerprint,
                process_policy=effect.process_policy,
                virtual_station_product_instance_uri=counter_station,
            )

            def dispatch_counter():
                self._dispatch_mutation(effect.method, piu, process_id)
                self._counter_attempts.add(effect_index)
                _COUNTER_ATTEMPTS[attempt_key] = None

            previous = _RUN_SCOPED_EVIDENCE.unfinished(self._profile.target.endpoint, piu)
            result = await find_and_call_method(
                jpm_node,
                effect.method,
                await self._resolve_ijt_namespace_index(),
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant(identification, ua.VariantType.ExtensionObject),
                ua.Variant(effect.count, ua.VariantType.UInt32),
                timeout=self._profile.cu_execution.default_timeout_seconds,
                target_server_authorized=True,
                preserve_status=True,
                before_dispatch=dispatch_counter,
            )
            if result.rpc_dispatched is not False:
                self._counter_attempts.add(effect_index)
                _COUNTER_ATTEMPTS.setdefault(attempt_key, None)
            if not self._method_succeeded(effect.method, result, observe_uncertain=True):
                definite_failure = self._settle_rejected_call(piu, result, previous)
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"{effect.method} failed: {self._last_method_failure}",
                    method=effect.method,
                    trigger_mode="counter_effect",
                    product_instance_uri=piu,
                    joining_process_id=process_id,
                    mutation_attempted=result.rpc_dispatched is not False,
                    execution_outcome="failed" if definite_failure else "inconclusive",
                    reason_code="method_rejected" if definite_failure else "mutation_outcome_unknown",
                    method_call_result=result,
                )
            capture = await collector.collect_evidence(
                evidence_ready,
                self.active_result_timeout_s,
            )
            intervention, affected = find_evidence(capture.all_results)
            post_counter_offset = _post_counter_offset(capture.all_results)
            parent_progression = ResultCollector.progression_from_capture(
                capture,
                self._process_result_classification(process),
                after_result_count=post_counter_offset,
                expected_terminal_state=counter_expected_state,
                predicate=lambda candidate: self._counter_result_matches_context(
                    candidate, piu, process_id, counter_station
                ),
            )
            mismatch = self._unexpected_terminal_outcome(
                parent_progression.terminal_result,
                counter_expected_state,
                piu,
                process_id,
                method=effect.method,
                starts_issued=baseline_starts,
                results_confirmed=baseline_starts,
                process_progression=parent_progression,
            )
            if mismatch is not None:
                return replace(mismatch, method_call_result=result)
            if capture.is_lossless:
                for candidate in capture.all_results[post_counter_offset:]:
                    if not matches_counter_context(candidate, capture.all_results):
                        continue
                    if get_classification(candidate) != ResultClassification.INTERVENTION_RESULT:
                        continue
                    mismatch = self._unexpected_terminal_outcome(
                        candidate,
                        1,
                        piu,
                        process_id,
                        method=effect.method,
                        starts_issued=baseline_starts,
                        results_confirmed=baseline_starts,
                        process_settled=False,
                        process_progression=parent_progression,
                        result_progression=ResultCollector.progression_from_capture(
                            capture, ResultClassification.INTERVENTION_RESULT, after_result_count=counter_boundary
                        ),
                    )
                    if mismatch is not None:
                        return replace(mismatch, execution_outcome="failed", method_call_result=result)
            if intervention is not None:
                self.validate_result_expectations(intervention, context="counter_intervention")
            if affected is not None:
                self.validate_result_expectations(affected, context="counter_intervention")
            if intervention is not None:
                self._record_workflow_action(
                    "counter_result_context_confirmed",
                    piu,
                    process_id,
                    virtual_station_product_instance_uri=counter_station,
                    intervention_result_id=get_result_id(intervention),
                    affected_result_id=get_result_id(affected) if affected is not None else "",
                )
            parent_classification = self._process_result_classification(process)
            if (
                capture.is_lossless
                and affected is not None
                and result.success
                and result.service_good_confirmed
                and matches_counter_context(affected, capture.all_results)
                and is_terminal_matching_state(affected, parent_classification, counter_expected_state)
            ):
                _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
                process_settled = True
            if verify_delta and capture.is_lossless and intervention is not None and affected is not None:
                try:
                    if not result.service_good_confirmed:
                        raise CounterEvidenceUnavailable(
                            "counter_response_unavailable",
                            "The positive counter Call service response was not confirmed Good.",
                        )
                    assert result.success, "Positive counter method must return Good"
                    assert result.output_list and result.output_list[0] == 0, "Positive business Status must be zero"
                    expected_delta = (
                        -effect.count if effect.method == "DecrementJoiningProcessCounter" else effect.count
                    )
                    require_counter_delta(
                        baseline,
                        affected,
                        expected_delta,
                        counter_name=effect.counter_name,
                        counter_type=effect.counter_type,
                    )
                except (CounterEvidenceUnavailable, AssertionError, ValueError) as exc:
                    delta_error = exc
                else:
                    delta_verified = True
            if (
                baseline_starts
                and capture.is_lossless
                and intervention is not None
                and affected is not None
                and result.service_good_confirmed
                and result.success
                and result.output_list
                and result.output_list[0] == 0
            ):
                completion = await self._continue_owned_process(
                    collector,
                    jpm_node,
                    piu,
                    process,
                    fingerprint,
                    starts_issued=baseline_starts,
                    results_confirmed=baseline_starts,
                    after_result_count=counter_boundary,
                    required_result_ids=frozenset({get_result_id(intervention)}),
                    counter_virtual_station_uri=counter_station,
                    expected_terminal_state=counter_expected_state,
                )
                process_settled = completion.process_settled
                process_progression = completion.process_progression
                joining_results_confirmed = completion.results_confirmed
                if completion.reason_code == "unexpected_terminal_result_state":
                    return replace(completion, method=effect.method, method_call_result=result)
                if not process_settled:
                    if delta_error is None:
                        return replace(completion, method=effect.method, method_call_result=result)
                    completion_issue = completion.skip_reason or ""
            elif (
                baseline_starts
                and capture.is_lossless
                and intervention is not None
                and affected is None
                and result.service_good_confirmed
                and result.success
                and result.output_list
                and result.output_list[0] == 0
            ):
                completion = await self._continue_owned_process(
                    collector,
                    jpm_node,
                    piu,
                    process,
                    fingerprint,
                    starts_issued=baseline_starts,
                    results_confirmed=baseline_starts,
                    after_result_count=counter_boundary,
                    required_result_ids=frozenset({get_result_id(intervention)}),
                    counter_virtual_station_uri=counter_station,
                    expected_terminal_state=counter_expected_state,
                )
                if completion.reason_code == "unexpected_terminal_result_state":
                    return replace(completion, method=effect.method, method_call_result=result)
                return TargetServerTriggerOutcome(
                    triggered=False,
                    method=effect.method,
                    product_instance_uri=piu,
                    joining_process_id=process_id,
                    mutation_attempted=True,
                    execution_outcome="inconclusive",
                    reason_code="counter_delta_update_unavailable",
                    skip_reason="No isolated post-counter update was available before continuation. "
                    "Completion results cannot substitute for the missing delta experiment.",
                    starts_issued=completion.starts_issued,
                    operation_count=completion.operation_count,
                    results_confirmed=completion.results_confirmed,
                    method_call_result=result,
                    process_settled=completion.process_settled,
                    process_progression=completion.process_progression,
                )

        if capture.queue_overflow_count:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=(
                    f"{effect.method} result evidence is incomplete because "
                    f"{capture.queue_overflow_count} subscribed event(s) were dropped."
                ),
                method=effect.method,
                trigger_mode="counter_effect",
                product_instance_uri=piu,
                joining_process_id=process_id,
                mutation_attempted=True,
                execution_outcome="inconclusive",
                reason_code="result_evidence_incomplete",
                method_call_result=result,
            )
        if intervention is None:
            unowned_ids = sorted(
                {
                    get_result_id(candidate)
                    for candidate in capture.all_results
                    if is_terminal_completed(candidate, ResultClassification.INTERVENTION_RESULT)
                    and get_result_id(candidate)
                    and get_result_id(candidate) not in before_counter_ids
                }
            )
            if unowned_ids:
                detail = (
                    f"{effect.method} received complete InterventionResult(s) {unowned_ids}, but their reported "
                    f"identities and parent links do not prove ownership by Tool '{piu}' and process '{process_id}'. "
                    "The counter call will not be retried."
                )
                logger.warning(detail)
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=detail,
                    method=effect.method,
                    trigger_mode="counter_effect",
                    product_instance_uri=piu,
                    joining_process_id=process_id,
                    mutation_attempted=True,
                    execution_outcome="inconclusive",
                    reason_code="counter_result_context_mismatch",
                    method_call_result=result,
                )
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"{effect.method} produced no complete InterventionResult evidence.",
                method=effect.method,
                trigger_mode="counter_effect",
                product_instance_uri=piu,
                joining_process_id=process_id,
                mutation_attempted=True,
                execution_outcome="inconclusive",
                reason_code="result_evidence_incomplete",
                method_call_result=result,
            )
        if expected_classification is not None and affected is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=(
                    f"{effect.method} produced no {expected_classification} result update "
                    "referencing the observed InterventionResult."
                ),
                method=effect.method,
                trigger_mode="counter_effect",
                product_instance_uri=piu,
                joining_process_id=process_id,
                results_confirmed=1,
                mutation_attempted=True,
                execution_outcome="inconclusive",
                reason_code="result_evidence_incomplete",
                method_call_result=result,
            )
        if delta_error is not None:
            return TargetServerTriggerOutcome(
                triggered=False,
                method=effect.method,
                product_instance_uri=piu,
                joining_process_id=process_id,
                mutation_attempted=True,
                execution_outcome="inconclusive" if isinstance(delta_error, CounterEvidenceUnavailable) else "failed",
                reason_code=delta_error.reason_code
                if isinstance(delta_error, CounterEvidenceUnavailable)
                else "counter_delta_invalid",
                skip_reason=f"{delta_error} {completion_issue}".strip(),
                method_call_result=result,
                process_settled=process_settled,
                process_progression=process_progression,
                starts_issued=self._start_attempts if baseline_starts else 0,
                results_confirmed=joining_results_confirmed,
            )
        process_result_cls = {
            JoiningProcessClassification.BATCH: ResultClassification.BATCH_RESULT,
            JoiningProcessClassification.SYNC: ResultClassification.SYNC_RESULT,
            JoiningProcessClassification.JOB: ResultClassification.JOB_RESULT,
        }.get(_process_classification(process))
        if (
            affected is not None
            and process_result_cls is not None
            and is_terminal_matching_state(affected, process_result_cls, counter_expected_state)
        ):
            _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
        elif process_result_cls is not None and not process_settled:
            _RUN_SCOPED_EVIDENCE.mark_unfinished(
                self._profile.target.endpoint,
                piu,
                TargetServerTriggerOutcome(
                    triggered=False,
                    method=effect.method,
                    product_instance_uri=piu,
                    joining_process_id=process_id,
                    mutation_attempted=True,
                    execution_outcome="inconclusive",
                    reason_code="compound_process_completion_unproven",
                    skip_reason="The counter intervention did not complete the selected compound process.",
                ),
            )
        outcome = TargetServerTriggerOutcome(
            triggered=True,
            method=effect.method,
            trigger_mode="counter_effect",
            product_instance_uri=piu,
            joining_process_id=process_id,
            results_confirmed=1 + int(affected is not None) + joining_results_confirmed,
            mutation_attempted=True,
            execution_outcome="passed",
            pre_trigger_baseline={
                "observed_server_epoch": self._observed_server_epoch,
                "catalog_fingerprint": fingerprint,
                "selection_names": sorted(selection_names(process)),
                "counter_config": asdict(effect),
                "configured_virtual_station_uri": self._profile.selection.tool.virtual_station_product_instance_uri,
                "associated_entity_expectations": [asdict(rule) for rule in self.associated_entity_expectations],
                "virtual_station_product_instance_uri": counter_station,
                "selection_config": asdict(selection),
                "counter_delta_verified": delta_verified,
            },
            result_progression=ResultProgression(
                classification=ResultClassification.INTERVENTION_RESULT,
                final_result=intervention,
                all_results=capture.all_results,
                source_events=capture.source_events,
            ),
            method_call_result=result,
            starts_issued=self._start_attempts if baseline_starts else 0,
            operation_count=self._start_attempts if baseline_starts else 0,
            process_settled=process_settled,
            process_progression=process_progression,
        )
        if (
            process_progression is not None
            and self._profile.workflow_execution.evidence_reuse.enabled
            and counter_expected_state == expected_state
        ):
            key = self._workflow_evidence_key(
                piu=piu,
                process_id=process_id,
                process_origin_id=self._process_field(process, "JoiningProcessOriginId"),
                processes=processes,
                classification=process_progression.classification,
                selection_policy=selection.policy,
                operation_count=self._profile.workflow_execution.max_start_invocations,
                require_partials=False,
            )
            if self._observed_server_epoch:
                _RUN_SCOPED_EVIDENCE.put(key, process_progression)
        _COUNTER_ATTEMPTS[attempt_key] = outcome
        self._record_workflow_action("counter_confirmed", piu, process_id, method=effect.method)
        return outcome

    @_owned_workflow
    async def trigger_counter_negative(self, kind: str) -> TargetServerTriggerOutcome:
        from helpers.counter_obligations import (
            CounterEvidenceUnavailable,
            counter_negative_arguments,
            counter_negative_rejected,
            require_negative_counter_response,
        )
        from helpers.method_caller import find_and_call_method
        from helpers.node_discovery import ProductInstanceUriExposureUnavailable, read_exposed_product_instance_uris

        method = "IncrementJoiningProcessCounter"
        if os.environ.get(
            "PYTEST_XDIST_WORKER"
        ) or not self._profile.cu_execution.state_changing_methods.allow_state_changing_method(method):
            return TargetServerTriggerOutcome(
                triggered=False,
                method=method,
                execution_outcome="blocked",
                reason_code="counter_negative_not_authorized",
                skip_reason="Counter permission and serial execution are required.",
            )
        jpm = await self._get_joining_process_management()
        piu = await self._resolve_tool_piu()
        processes = await self._get_joining_process_list(jpm, piu) if jpm is not None else []
        if self._profile.cu_execution.counter_effects:
            effect = self._profile.cu_execution.counter_effects[0]
            selection = self._profile.selection.joining_processes.get(
                effect.process_classification, self._profile.selection.joining_process
            )
            candidates = counter_candidates(processes, effect, selection)
        else:
            candidates = self._choose_joining_processes(processes, "job")
        if len(candidates) != 1:
            return TargetServerTriggerOutcome(
                triggered=False,
                method=method,
                execution_outcome="blocked",
                reason_code="counter_negative_precondition_unproven",
                skip_reason="Exactly one current valid counter-process target is required.",
            )
        process = candidates[0]
        process_id = self._process_field(process, "JoiningProcessId", "JoiningProcessIdentification", "Id")
        key = (self._profile.target.endpoint, piu, self._profile.source_path, f"negative:{kind}")
        if key in _COUNTER_ATTEMPTS:
            previous = _COUNTER_ATTEMPTS[key]
            if previous is not None and not previous.triggered:
                return replace(
                    previous,
                    skip_reason=f"{previous.skip_reason} This run will not repeat the negative counter probe.",
                )
            observed_epoch = await self._read_observed_server_epoch()
            if (
                previous is not None
                and observed_epoch is not None
                and previous.pre_trigger_baseline.get("observed_server_epoch") == observed_epoch
            ):
                return replace(previous, evidence_reused=True)
            return TargetServerTriggerOutcome(
                triggered=False,
                method=method,
                mutation_attempted=True,
                execution_outcome="inconclusive",
                reason_code="mutation_retry_prohibited",
                skip_reason="The negative counter probe was interrupted. It will not be repeated.",
            )
        blocked = self._claim_controlled_scope(piu)
        if blocked is not None:
            return blocked
        identification = self._make_process_identification(process)
        if identification is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                method=method,
                execution_outcome="blocked",
                reason_code="counter_negative_precondition_unproven",
                skip_reason="Counter identification type is unavailable.",
            )
        try:
            exposed = await read_exposed_product_instance_uris(self._client, await self._resolve_ijt_namespace_index())
        except ProductInstanceUriExposureUnavailable as exc:
            return TargetServerTriggerOutcome(
                triggered=False,
                method=method,
                execution_outcome="blocked",
                reason_code=exc.reason_code,
                skip_reason=str(exc),
                product_instance_uri=piu,
                joining_process_id=process_id,
            )
        arguments, expected = counter_negative_arguments(
            piu,
            identification,
            tuple(
                self._process_field(item, "JoiningProcessId", "JoiningProcessIdentification", "Id")
                for item in processes
            ),
            exposed,
            kind,
        )
        blocked = await self._ensure_baseline(jpm, piu, process, self._process_list_fingerprint(processes))
        if blocked is not None:
            return blocked
        if not await self._target_context_current(jpm, piu, process, self._process_list_fingerprint(processes)):
            return TargetServerTriggerOutcome(
                triggered=False,
                method=method,
                execution_outcome="blocked",
                reason_code="target_changed",
                skip_reason="Counter target changed before the negative probe.",
            )
        unknown = TargetServerTriggerOutcome(
            triggered=False,
            method=method,
            product_instance_uri=piu,
            joining_process_id=process_id,
            mutation_attempted=True,
            execution_outcome="inconclusive",
            reason_code="mutation_outcome_unknown",
            skip_reason="Negative counter call has not produced its required rejection contract.",
        )
        self._record_workflow_action("counter_negative_attempt", piu, process_id, obligation=kind)

        def dispatch_negative():
            self._dispatch_mutation(method, piu, process_id)
            _COUNTER_ATTEMPTS[key] = unknown

        result = await find_and_call_method(
            jpm,
            method,
            await self._resolve_ijt_namespace_index(),
            *arguments,
            timeout=self._profile.cu_execution.default_timeout_seconds,
            target_server_authorized=True,
            preserve_status=True,
            before_dispatch=dispatch_negative,
        )
        try:
            require_negative_counter_response(result, expected)
        except CounterEvidenceUnavailable as exc:
            if result.rpc_dispatched is False:
                _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
            outcome = replace(
                unknown,
                execution_outcome="inconclusive" if result.rpc_dispatched is not False else "blocked",
                mutation_attempted=result.rpc_dispatched is not False,
                reason_code=exc.reason_code,
                skip_reason=str(exc),
                method_call_result=result,
            )
            _COUNTER_ATTEMPTS[key] = outcome
            if outcome.mutation_attempted:
                _RUN_SCOPED_EVIDENCE.mark_unfinished(self._profile.target.endpoint, piu, outcome)
            return outcome
        except AssertionError as exc:
            outcome = replace(
                unknown,
                execution_outcome="failed",
                reason_code="counter_negative_contract_failed",
                skip_reason=str(exc),
                method_call_result=result,
            )
            _COUNTER_ATTEMPTS[key] = outcome
            if self._method_call_rejected(result) or counter_negative_rejected(result):
                _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
            else:
                _RUN_SCOPED_EVIDENCE.mark_unfinished(self._profile.target.endpoint, piu, outcome)
            return outcome
        _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
        outcome = replace(
            unknown,
            triggered=True,
            pre_trigger_baseline={"observed_server_epoch": self._observed_server_epoch},
            execution_outcome="passed",
            reason_code="",
            skip_reason=None,
            method_call_result=result,
        )
        _COUNTER_ATTEMPTS[key] = outcome
        self._record_workflow_action("counter_negative_confirmed", piu, process_id, obligation=kind)
        return outcome

    def _physical_selection_blocker(
        self,
        classification: str | int | None = None,
        *,
        method: str = "StartSelectedJoining",
        reset_budget: bool = True,
    ) -> TargetServerTriggerOutcome | None:
        if reset_budget:
            self._start_attempts = 0
            self._current_process_id = ""
            self._last_method_failure = ""
        selection, _ = self._get_selection_for_classification(classification)
        reason = ""
        code = ""
        from helpers.sut_manifest import manifest_change_reason

        issue = manifest_change_reason(self._profile.source_path, os.environ.get("OPCUA_TARGET_MANIFEST_SHA256"))
        if issue:
            reason = issue
            code = "manifest_changed"
        elif os.environ.get("PYTEST_XDIST_WORKER"):
            reason = "Physical workflows require serial execution."
            code = "parallel_physical_workflow"
        elif selection.policy != "exact_match" and not self._profile.workflow_execution.allow_discovered_processes:
            reason = "Automatic process candidates are not approved by workflows.allow_discovered_processes."
            code = "candidate_scope_not_approved"
        if not reason:
            return None
        logger.warning("%s blocked: %s", method, reason)
        return TargetServerTriggerOutcome(
            triggered=False,
            method=method,
            skip_reason=reason,
            reason_code=code,
            execution_outcome="blocked",
        )

    def _record_workflow_action(self, action: str, piu: str, process_id: str, **details: Any) -> None:
        filename = os.environ.get("IJT_WORKFLOW_ACTIONS_FILE")
        record = {
            "action": action,
            "endpoint": self._profile.target.endpoint,
            "scenario_id": self._scenario_id,
            "monotonic_seconds": time.monotonic(),
            "tool_piu": piu,
            "joining_process_id": process_id,
            **details,
        }
        logger.info("Workflow action: %s", record)
        if filename:
            with Path(filename).open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\n")
                stream.flush()
                os.fsync(stream.fileno())

    async def _target_context_current(self, jpm: Any, piu: str, process: Any, fingerprint: tuple) -> bool:
        current = await self._get_joining_process_list(jpm, piu)
        matches = matching_processes(
            current,
            {
                "joining_process_id": self._process_field(
                    process, "JoiningProcessId", "JoiningProcessIdentification", "Id"
                )
            },
        )
        return (
            self._process_list_fingerprint(current) == fingerprint
            and len(matches) == 1
            and selection_names(matches[0]) == selection_names(process)
        )

    _counter_target_current = _target_context_current

    async def _discover_counter_station_fallback(self, piu: str, process_id: str) -> str:
        """Resolve VirtualStation from prior session results for ``piu`` or a unique VirtualStation asset."""
        prior_results = tuple(
            result
            for record in _RUN_SCOPED_EVIDENCE._records.values()
            if record.key.endpoint == self._profile.target.endpoint and record.key.product_instance_uri == piu
            for result in getattr(record.progression, "all_results", ())
        )
        if prior_results:
            station = self._counter_station_from_joining_results(prior_results, piu, process_id)
            if not station:
                stations = {
                    candidate_station
                    for result in prior_results
                    if piu.strip().lower() in self._result_entity_ids(result, "TOOL")
                    for candidate_station in self._result_entity_ids(result, "VIRTUAL_STATION")
                }
                if len(stations) == 1:
                    station = next(iter(stations))
            if station:
                return station
        try:
            from helpers.namespaces import NS_DI, NS_IJT_BASE
            from helpers.node_discovery import read_virtual_station_product_instance_uri

            ns_ijt = self._ns_ijt or await self._client.get_namespace_index(NS_IJT_BASE)
            ns_di = self._ns_di or await self._client.get_namespace_index(NS_DI)
            return await read_virtual_station_product_instance_uri(self._client, ns_ijt, ns_di, self._ns_app)
        except Exception as exc:  # noqa: BLE001
            logger.debug("VirtualStation PIU fallback discovery failed: %s", exc)
            return ""

    async def _resolve_tool_piu(self) -> str:
        """Return the configured or discovered tool ProductInstanceUri."""
        piu = self._profile.selection.tool.product_instance_uri
        if piu:
            return piu
        try:
            from helpers.namespaces import NS_DI, NS_IJT_BASE
            from helpers.node_discovery import read_tool_product_instance_uri

            ns_ijt = self._ns_ijt
            if ns_ijt is None:
                ns_ijt = await self._client.get_namespace_index(NS_IJT_BASE)
            ns_di = self._ns_di
            if ns_di is None:
                ns_di = await self._client.get_namespace_index(NS_DI)
            tool_policy = self._profile.selection.tool.policy
            if tool_policy != "first_ready":
                discovered = await read_tool_product_instance_uri(
                    self._client, ns_ijt, ns_di, self._ns_app, policy=tool_policy
                )
            else:
                discovered = await read_tool_product_instance_uri(self._client, ns_ijt, ns_di, self._ns_app)
            if discovered:
                logger.debug("Discovered tool PIU: %s", discovered)
                return discovered
        except Exception as exc:  # noqa: BLE001
            logger.debug("Tool PIU auto-discovery failed: %s", exc)
        return ""

    async def _get_joining_process_list(self, jpm_node: Any, piu: str) -> list[Any]:
        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN

        result = await find_and_call_method(
            jpm_node,
            BN.GET_JOINING_PROCESS_LIST,
            await self._resolve_ijt_namespace_index(),
            ua.Variant(piu, ua.VariantType.String),
            timeout=self._profile.cu_execution.default_timeout_seconds,
        )
        if not result.success:
            self._last_method_failure = str(result.error or "OPC UA service call failed")
            return []
        output = result.output_list
        if not output:
            return []
        # GetJoiningProcessList returns a list wrapped in a single output argument
        inner = output[0] if output else []
        if isinstance(inner, (list, tuple)):
            return list(inner)
        return [inner] if inner is not None else []

    @staticmethod
    def _process_field(process: Any, *names: str) -> str:
        """Return the first non-empty process field across supported model revisions."""
        nested_attrs = ("JoiningProcessId", "JoiningProcessOriginId", "Id", "OriginId")
        for name in names:
            value = getattr(process, name, None)
            if hasattr(value, "value") and not callable(getattr(value, "value", None)):
                value = value.value
            if isinstance(value, (str, int, float)) and not isinstance(value, bool) and str(value):
                return str(value)
            if value is not None and not isinstance(value, (dict, list, tuple, set, bytes, bool)):
                for sub_name in nested_attrs:
                    sub_val = getattr(value, sub_name, None)
                    if hasattr(sub_val, "value") and not callable(getattr(sub_val, "value", None)):
                        sub_val = sub_val.value
                    if isinstance(sub_val, (str, int, float)) and not isinstance(sub_val, bool) and str(sub_val):
                        return str(sub_val)
        return ""

    @staticmethod
    def _selection_names(process: Any) -> set[str]:
        """Return SelectionName entity IDs advertised by a process."""
        return selection_names(process)

    def _normalize_classification(self, classification: str | int | None) -> str:
        """Normalize integer or string classification to a canonical profile key."""
        if classification is None:
            return ""
        if isinstance(classification, int) and not isinstance(classification, bool):
            from helpers.namespaces import result_classification_name

            return result_classification_name(classification)
        return str(classification).lower().strip()

    @staticmethod
    def _result_classification_value(classification: str | int | None) -> int | None:
        """Normalize a boundary value to the ResultClassification integer domain."""
        if classification is None or isinstance(classification, bool):
            return None
        if isinstance(classification, int):
            return classification if classification in ResultClassification.VALID_VALUES else None
        return result_classification_value(classification)

    def _get_selection_for_classification(self, classification: str | int | None = None) -> tuple[Any, str]:
        """Return the appropriate process selection config and normalized key.

        Resolution order:

        1. ``selection.joining_processes[<classification>]`` when configured.
        2. For ``intervention`` only: the explicit
           ``cu_execution.extension_fields.counter_parent_process`` entry, when
           it carries at least one selector accepted by
           ``_selection_has_selector`` (id, origin id, **or** selection_name).
        3. The legacy/default ``selection.joining_process`` entry.

        Step 3 is always reachable, so an unconfigured classification degrades
        to the documented default selection instead of an empty ``exact_match``
        selector that can never match any advertised process.
        """
        key = self._normalize_classification(classification)
        if key and key in self._profile.selection.joining_processes:
            return self._profile.selection.joining_processes[key], key
        if key == "intervention":
            cpp = self._profile.cu_execution.extension_fields.get("counter_parent_process")
            if isinstance(cpp, dict):
                from helpers.target_server_cu_config import JoiningProcessSelectionConfig

                candidate = JoiningProcessSelectionConfig(
                    policy="exact_match",
                    match_by=str(cpp.get("match_by", "joining_process_id")),
                    joining_process_id=str(cpp.get("joining_process_id", "")),
                    joining_process_origin_id=str(cpp.get("joining_process_origin_id", "")),
                    selection_name=str(cpp.get("selection_name", "")),
                )
                # selection_name is a usable selector everywhere else
                # (_selection_has_selector / _choose_joining_process), so it must
                # be accepted here too instead of falling through to the default.
                if self._selection_has_selector(candidate):
                    return candidate, key
            logger.debug(
                "No intervention-specific selection configured "
                "(selection.joining_processes.intervention / counter_parent_process); "
                "falling back to the default selection.joining_process entry"
            )
        return self._profile.selection.joining_process, key

    @staticmethod
    def _selection_has_selector(selection: Any) -> bool:
        """Return True when an exact_match selection configures its selected criterion."""
        return bool(getattr(selection, selection.match_by, ""))

    def _choose_joining_processes(
        self,
        processes: list[Any],
        classification: str | int | None = None,
    ) -> list[Any]:
        """Return ordered process candidates from fresh GetJoiningProcessList evidence."""
        if not processes:
            return []

        selection, _ = self._get_selection_for_classification(classification)
        norm_key = self._normalize_classification(classification)
        required_process_classification = joining_process_classification_value(norm_key)
        if norm_key and norm_key != "intervention" and required_process_classification is None:
            return []

        def matches_requested_classification(process: Any) -> bool:
            return (
                required_process_classification is None
                or _process_classification(process) == required_process_classification
            )

        if selection.policy == "exact_match":
            if not self._selection_has_selector(selection):
                logger.warning(
                    "Joining process selection policy is 'exact_match' but no "
                    "joining_process_id/joining_process_origin_id/selection_name is configured"
                )
                return []

            matches = matching_processes(processes, selection)
            if len(matches) > 1:
                logger.warning(
                    "Exact joining-process selector '%s' matched %d processes; refusing ambiguous selection",
                    selection.match_by,
                    len(matches),
                )
                return []
            return self._validate_exact_candidates(matches, norm_key, matches_requested_classification)

        if not norm_key or norm_key == "intervention":
            return (
                list(processes)[: self._profile.workflow_execution.max_candidates]
                if selection.policy == "all_compatible"
                else [processes[0]]
            )

        direct = [process for process in processes if matches_requested_classification(process)]
        compound = (
            [
                process
                for process in processes
                if _process_classification(process) == JoiningProcessClassification.JOB and process not in direct
            ]
            if norm_key in {"batch", "sync"}
            else []
        )
        return (direct + compound)[: self._profile.workflow_execution.max_candidates]

    def _validate_exact_candidates(
        self,
        matches: list[Any],
        norm_key: str,
        matches_requested_classification: Any,
    ) -> list[Any]:
        """Allow cross-classification exact candidates only for an explicit result-specific selector."""
        if not matches or not norm_key or norm_key == "intervention":
            return matches[:1]
        direct = [process for process in matches if matches_requested_classification(process)]
        if direct:
            return direct[:1]
        if norm_key in self._profile.selection.joining_processes:
            logger.info(
                "Trying explicitly configured %s process candidate with process classification %s; "
                "the result stream must prove the requested result classification",
                norm_key,
                _process_classification(matches[0]),
            )
            return matches[:1]
        return []

    def _choose_joining_process(self, processes: list[Any], classification: str | int | None = None) -> Any | None:
        """Return the first ordered process candidate for backward-compatible callers."""
        candidates = self._choose_joining_processes(processes, classification)
        return candidates[0] if candidates else None

    def _process_list_fingerprint(self, processes: list[Any]) -> tuple[tuple[str, str, int | None], ...]:
        """Return a stable fingerprint of the current advertised process list."""
        entries = [
            (
                self._process_field(process, "JoiningProcessId", "JoiningProcessIdentification", "Id"),
                self._process_field(
                    process,
                    "JoiningProcessOriginId",
                    "JoiningProcessIdentificationOrigin",
                ),
                cls.value if (cls := _process_classification(process)) is not None else None,
            )
            for process in processes
        ]
        return tuple(sorted(entries, key=lambda item: (item[0], item[1], -1 if item[2] is None else item[2])))

    def _workflow_evidence_key(
        self,
        *,
        piu: str,
        process_id: str,
        process_origin_id: str,
        processes: list[Any],
        classification: int,
        selection_policy: str,
        operation_count: int,
        require_partials: bool,
    ) -> WorkflowEvidenceKey:
        return WorkflowEvidenceKey(
            endpoint=self._profile.target.endpoint,
            application_name=self._profile.target.expected_server.application_name,
            application_version=self._profile.target.expected_server.application_version,
            client_identity=id(self._client),
            product_instance_uri=piu,
            joining_process_id=process_id,
            joining_process_origin_id=process_origin_id,
            process_list_fingerprint=self._process_list_fingerprint(processes),
            result_classification=classification,
            selection_policy=selection_policy,
            operation_count=operation_count,
            require_partials=require_partials,
            referenced_child_completion_policy=(
                self._profile.workflow_execution.expected_results.referenced_child_completion_policy
            ),
            max_start_invocations=self._profile.workflow_execution.max_start_invocations,
            consecutive_start_delay_seconds=self._profile.workflow_execution.consecutive_start_delay_seconds,
            observed_server_epoch=self._observed_server_epoch,
        )

    async def _read_observed_server_epoch(self) -> tuple[str, ...] | None:
        from datetime import datetime

        from asyncua import ua

        node_ids = (
            ua.ObjectIds.Server_ServerArray,
            ua.ObjectIds.Server_ServerStatus_StartTime,
            ua.ObjectIds.Server_ServerStatus_BuildInfo_SoftwareVersion,
            ua.ObjectIds.Server_ServerStatus_BuildInfo_BuildNumber,
            ua.ObjectIds.Server_NamespaceArray,
        )
        try:
            values = await asyncio.wait_for(
                self._client.read_values([self._client.get_node(ua.NodeId(node_id, 0)) for node_id in node_ids]),
                timeout=self._profile.cu_execution.default_timeout_seconds,
            )
        except (ua.UaError, OSError, TimeoutError, AttributeError, TypeError) as exc:
            logger.warning("Evidence reuse unavailable because server incarnation could not be observed: %s", exc)
            return None
        if (
            not isinstance(values, (tuple, list))
            or len(values) != 5
            or not isinstance(values[0], (tuple, list))
            or not values[0]
            or not isinstance(values[0][0], str)
            or not values[0][0]
            or not isinstance(values[1], datetime)
            or not all(isinstance(value, str) for value in values[2:4])
            or not isinstance(values[4], (tuple, list))
            or not values[4]
            or not all(isinstance(value, str) for value in values[4])
        ):
            logger.warning("Evidence reuse unavailable because observed server-incarnation metadata is incomplete.")
            return None
        return (values[0][0], values[1].isoformat(), values[2], values[3], *values[4])

    async def get_reusable_progression(
        self,
        classification: int,
        operation_count: int | None = None,
        *,
        require_partials: bool = False,
    ) -> Any | None:
        """Return complete evidence only when fresh discovery reproduces its provenance key."""
        if not self._profile.workflow_execution.evidence_reuse.enabled:
            return None
        observed_epoch = await self._read_observed_server_epoch()
        if observed_epoch is None:
            return None
        self._observed_server_epoch = observed_epoch
        jpm_node = await self._get_joining_process_management()
        if jpm_node is None:
            return None
        piu = await self._resolve_tool_piu()
        processes = await self._get_joining_process_list(jpm_node, piu)
        selection, _ = self._get_selection_for_classification(classification)
        if operation_count is None:
            operation_count = self._profile.workflow_execution.max_start_invocations
        operation_count = min(operation_count, self._profile.workflow_execution.max_start_invocations)
        for candidate in self._choose_joining_processes(processes, classification):
            process_id = self._process_field(
                candidate,
                "JoiningProcessId",
                "JoiningProcessIdentification",
                "Id",
            )
            process_origin_id = self._process_field(
                candidate,
                "JoiningProcessOriginId",
                "JoiningProcessIdentificationOrigin",
            )
            key = self._workflow_evidence_key(
                piu=piu,
                process_id=process_id,
                process_origin_id=process_origin_id,
                processes=processes,
                classification=classification,
                selection_policy=selection.policy,
                operation_count=operation_count,
                require_partials=require_partials,
            )
            progression = _RUN_SCOPED_EVIDENCE.get(key)
            if progression is None:
                progression = _RUN_SCOPED_EVIDENCE.related(key)
            if progression is not None:
                return progression
        return None

    def remember_result_progression(self, progression: Any) -> bool:
        """Store complete progression captured immediately after this trigger."""
        key = self._pending_evidence_key
        if (
            not self._profile.workflow_execution.evidence_reuse.enabled
            or not self._observed_server_epoch
            or key is None
            or getattr(progression, "classification", None) != key.result_classification
        ):
            return False
        stored = _RUN_SCOPED_EVIDENCE.put(key, progression)
        self._pending_evidence_key = None
        return stored

    def _describe_joining_processes(self, processes: list[Any]) -> str:
        """Return compact identifiers for selection diagnostics."""
        descriptions = []
        for process in processes:
            process_id = self._process_field(
                process,
                "JoiningProcessId",
                "JoiningProcessIdentification",
                "Id",
            )
            origin_id = self._process_field(
                process,
                "JoiningProcessOriginId",
                "JoiningProcessIdentificationOrigin",
            )
            names = ",".join(sorted(self._selection_names(process)))
            descriptions.append(
                f"id='{process_id or '<unreadable>'}', origin='{origin_id or '<unreadable>'}', selection_name='{names}'"
            )
        return "; ".join(descriptions)

    def _make_process_identification(
        self,
        process: Any,
        classification: str | int | None = None,
        *,
        identifier_strategy: str | None = None,
        selection_name: str | None = None,
    ) -> Any:
        """Build the IJT process identifier required by controller methods.

        JoiningProcessId is the preferred default. Optional secondary identifiers are
        populated only according to an explicit profile strategy.
        """
        from asyncua import ua

        try:
            identification = ua.JoiningProcessIdentificationDataType()
        except AttributeError:
            logger.warning("JoiningProcessIdentificationDataType is not registered")
            return None

        identification.JoiningProcessId = self._process_field(
            process,
            "JoiningProcessId",
            "JoiningProcessIdentification",
            "Id",
        )
        selection, _ = self._get_selection_for_classification(classification)
        strategy = identifier_strategy or getattr(selection, "identifier_strategy", "id_only")
        if strategy == "selection_name_only":
            advertised_names = self._selection_names(process)
            configured_name = selection.selection_name if selection_name is None else selection_name
            if configured_name:
                if configured_name not in advertised_names:
                    logger.error(
                        "Configured SelectionName '%s' is not advertised by the selected process", configured_name
                    )
                    return None
                resolved_name = configured_name
            elif len(advertised_names) == 1:
                resolved_name = next(iter(advertised_names))
            else:
                logger.error(
                    "selection_name_only requires one advertised SelectionName or an explicit advertised name; found %d",
                    len(advertised_names),
                )
                return None
            identification.JoiningProcessId = ""
            identification.JoiningProcessOriginId = ""
            identification.SelectionName = resolved_name
            return identification
        identification.JoiningProcessOriginId = (
            self._process_field(
                process,
                "JoiningProcessOriginId",
                "JoiningProcessIdentificationOrigin",
            )
            if strategy in {"id_with_origin", "all_available"}
            else ""
        )
        advertised_names = sorted(self._selection_names(process))
        identification.SelectionName = (
            selection_name or selection.selection_name or (advertised_names[0] if advertised_names else "")
            if strategy in {"id_with_selection_name", "all_available"}
            else ""
        )
        return identification

    async def _select_joining_process(
        self,
        jpm_node: Any,
        process: Any,
        piu: str,
        classification: str | int | None = None,
        *,
        identifier_strategy: str | None = None,
        selection_name: str | None = None,
    ) -> bool:
        """Call SelectJoiningProcess and return True on success."""
        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN

        identification = self._make_process_identification(
            process,
            classification=classification,
            identifier_strategy=identifier_strategy,
            selection_name=selection_name,
        )
        if identification is None:
            return False

        selection, _ = self._get_selection_for_classification(classification)
        strategy = identifier_strategy or selection.identifier_strategy
        if strategy == "selection_name_only":
            processes = await self._get_joining_process_list(jpm_node, piu)
            matches = matching_processes(processes, {"selection_name": identification.SelectionName}, "selection_name")
            if len(matches) != 1:
                logger.error(
                    "selection_name_only matched %d current processes; refusing missing or ambiguous command target",
                    len(matches),
                )
                return False
            selected_id = self._process_field(process, "JoiningProcessId", "JoiningProcessIdentification", "Id")
            current_id = self._process_field(matches[0], "JoiningProcessId", "JoiningProcessIdentification", "Id")
            if current_id != selected_id:
                logger.error("SelectionName now identifies a different process; refusing changed command target")
                return False

        logger.info(
            "Selecting process id='%s', classification='%s', policy='%s', identifier_strategy='%s'",
            self._process_field(process, "JoiningProcessId", "JoiningProcessIdentification", "Id"),
            _process_classification(process),
            selection.policy,
            strategy,
        )
        process_id = self._process_field(process, "JoiningProcessId", "JoiningProcessIdentification", "Id")
        fingerprint = self._process_list_fingerprint(await self._get_joining_process_list(jpm_node, piu))
        blocked = await self._ensure_baseline(jpm_node, piu, process, fingerprint)
        if blocked is not None:
            self._last_method_failure = f"{blocked.reason_code}: {blocked.skip_reason}"
            return False
        self._record_workflow_action("select_attempt", piu, process_id, identifier_strategy=strategy)
        result = await find_and_call_method(
            jpm_node,
            BN.SELECT_JOINING_PROCESS,
            await self._resolve_ijt_namespace_index(),
            ua.Variant(piu, ua.VariantType.String),
            ua.Variant(identification, ua.VariantType.ExtensionObject),
            timeout=self._profile.cu_execution.default_timeout_seconds,
            target_server_authorized=True,
            preserve_status=True,
            before_dispatch=lambda: self._dispatch_mutation(BN.SELECT_JOINING_PROCESS, piu, process_id),
        )
        self._last_method_result = result
        selected = self._method_succeeded(BN.SELECT_JOINING_PROCESS, result)
        self._record_workflow_action(
            "select_method_outcome",
            piu,
            process_id,
            service_good_confirmed=result.service_good_confirmed,
            method_status_code=result.method_status_code,
            rpc_dispatched=result.rpc_dispatched,
            output=[str(value) for value in result.output_list],
        )
        if selected:
            self._current_process_id = process_id
            _RUN_SCOPED_EVIDENCE.set_last_selected_process(self._profile.target.endpoint, piu, process_id)
        if selected or self._method_call_rejected(result):
            _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
        return selected

    async def _wait_for_process_selection_settle(self) -> None:
        delay = self._profile.workflow_execution.consecutive_start_delay_seconds
        if delay > 0:
            await asyncio.sleep(delay)

    @staticmethod
    def _method_call_rejected(result: Any) -> bool:
        from helpers.method_caller import call_definitely_rejected

        return call_definitely_rejected(result)

    def _settle_rejected_call(self, piu: str, result: Any, previous: TargetServerTriggerOutcome | None) -> bool:
        if not self._method_call_rejected(result):
            return False
        if previous is None:
            _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
        else:
            _RUN_SCOPED_EVIDENCE.mark_unfinished(self._profile.target.endpoint, piu, previous)
        return True

    _counter_call_rejected = _method_call_rejected

    @_owned_workflow
    async def _trigger_intervention(self) -> TargetServerTriggerOutcome:
        """Generate an InterventionResult using a configured process action."""
        from asyncua import ua

        from helpers.method_caller import find_and_call_method

        if self._profile.cu_execution.counter_effects:
            return await self.trigger_counter_effect(0)

        method_name = str(
            self._profile.cu_execution.extension_fields.get(
                "intervention_method",
                "IncrementJoiningProcessCounter",
            )
        )
        supported_methods = {
            "AbortJoiningProcess",
            "DecrementJoiningProcessCounter",
            "IncrementJoiningProcessCounter",
            "ResetJoiningProcess",
        }
        if method_name not in supported_methods:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"Unsupported intervention_method '{method_name}' in target profile",
                method=method_name,
                trigger_mode="joining_process_intervention",
            )

        state_changes = self._profile.cu_execution.state_changing_methods
        if not state_changes.allow_state_changing_method(method_name):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"{method_name} is not allowed by the target profile",
                method=method_name,
                trigger_mode="joining_process_intervention",
            )

        blocked = self._physical_selection_blocker("intervention", method=method_name)
        if blocked:
            return blocked
        selection, _ = self._get_selection_for_classification("intervention")
        if selection.policy != "exact_match":
            return TargetServerTriggerOutcome(
                triggered=False,
                method=method_name,
                skip_reason="Legacy intervention requires an exact target. Configure counter_effects for bounded discovery.",
                reason_code="explicit_intervention_target_required",
                execution_outcome="blocked",
            )
        required_workflow = {
            "AbortJoiningProcess": "remote_abort_job",
            "ResetJoiningProcess": "remote_reset_job",
        }.get(method_name, "counter_intervention")
        if required_workflow not in self._profile.workflow_execution.approved_workflows:
            return TargetServerTriggerOutcome(
                triggered=False,
                method=method_name,
                reason_code="workflow_not_approved",
                execution_outcome="blocked",
                skip_reason=f"Workflow '{required_workflow}' is not approved.",
            )
        jpm_node = await self._get_joining_process_management()
        piu = await self._resolve_tool_piu()
        if jpm_node is None or not piu:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="JoiningProcessManagement or Tool ProductInstanceUri is unavailable",
                method=method_name,
                trigger_mode="joining_process_intervention",
            )

        processes = await self._get_joining_process_list(jpm_node, piu)
        process = self._choose_joining_process(processes, classification="intervention")
        if process is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="No joining process matched the intervention workflow selection",
                method=method_name,
                trigger_mode="joining_process_intervention",
                product_instance_uri=piu,
            )
        identification = self._make_process_identification(process, classification="intervention")
        if identification is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="JoiningProcessIdentificationDataType is unavailable",
                method=method_name,
                trigger_mode="joining_process_intervention",
                product_instance_uri=piu,
            )

        method_args = [
            ua.Variant(piu, ua.VariantType.String),
            ua.Variant(identification, ua.VariantType.ExtensionObject),
        ]
        if method_name in {
            "DecrementJoiningProcessCounter",
            "IncrementJoiningProcessCounter",
        }:
            count = int(
                self._profile.cu_execution.extension_fields.get(
                    "intervention_count",
                    1,
                )
            )
            method_args.append(ua.Variant(count, ua.VariantType.UInt32))
        elif method_name == "AbortJoiningProcess":
            message = str(
                self._profile.cu_execution.extension_fields.get(
                    "intervention_message",
                    "IJT target-server intervention workflow",
                )
            )
            method_args.append(
                ua.Variant(
                    ua.LocalizedText(Text=message, Locale="en"),
                    ua.VariantType.LocalizedText,
                )
            )

        process_id = self._process_field(process, "JoiningProcessId", "JoiningProcessIdentification", "Id")
        attempt_key = (self._profile.target.endpoint, piu, self._profile.source_path, f"legacy:{method_name}")
        if attempt_key in _COUNTER_ATTEMPTS:
            return TargetServerTriggerOutcome(
                triggered=False,
                method=method_name,
                mutation_attempted=True,
                execution_outcome="inconclusive",
                reason_code="mutation_retry_prohibited",
                skip_reason="Legacy intervention was already attempted in this run. Retry prohibited.",
            )
        if not await self._target_context_current(jpm_node, piu, process, self._process_list_fingerprint(processes)):
            return TargetServerTriggerOutcome(
                triggered=False,
                method=method_name,
                reason_code="target_changed",
                skip_reason="Intervention target changed before mutation.",
                execution_outcome="blocked",
            )
        if self._subscription_client is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                method=method_name,
                execution_outcome="blocked",
                reason_code="result_subscription_required",
                skip_reason="Intervention requires an owned result subscription.",
            )
        blocked = await self._ensure_baseline(jpm_node, piu, process, self._process_list_fingerprint(processes))
        if blocked is not None:
            return blocked
        from helpers.namespaces import NS_IJT_BASE
        from helpers.result_collector import ResultCollector, ResultProgression, is_terminal_completed

        origin = str(identification.JoiningProcessOriginId)

        def intervention_observed(results):
            return any(
                is_terminal_completed(item, ResultClassification.INTERVENTION_RESULT)
                and self._result_matches_context(item, piu, process_id, origin)
                for item in results
            )

        unknown = TargetServerTriggerOutcome(
            triggered=False,
            method=method_name,
            trigger_mode="joining_process_intervention",
            product_instance_uri=piu,
            joining_process_id=process_id,
            joining_process_origin_id=origin,
            mutation_attempted=True,
            execution_outcome="inconclusive",
            reason_code="mutation_outcome_unknown",
            skip_reason="Intervention call or its owned result observation was not confirmed.",
        )
        async with ResultCollector(
            self._subscription_client,
            {NS_IJT_BASE: await self._resolve_ijt_namespace_index()},
            is_simulator=False,
            result_observer=lambda item, duplicate: self._observe_result(piu, process_id, origin, item, duplicate),
        ) as collector:
            collector.discard_pending()
            self._record_workflow_action("intervention_attempt", piu, process_id, method=method_name)

            def dispatch_intervention():
                self._dispatch_mutation(method_name, piu, process_id)
                _COUNTER_ATTEMPTS[attempt_key] = unknown

            try:
                result = await find_and_call_method(
                    jpm_node,
                    method_name,
                    await self._resolve_ijt_namespace_index(),
                    *method_args,
                    timeout=self._profile.cu_execution.default_timeout_seconds,
                    target_server_authorized=True,
                    preserve_status=True,
                    before_dispatch=dispatch_intervention,
                )
                if not self._method_succeeded(method_name, result, observe_uncertain=True):
                    rejected = self._method_call_rejected(result)
                    outcome = replace(
                        unknown,
                        method_call_result=result,
                        execution_outcome="failed" if rejected else "inconclusive",
                        reason_code="method_rejected" if rejected else "mutation_outcome_unknown",
                        skip_reason=f"{method_name} failed: {self._last_method_failure}",
                    )
                    _COUNTER_ATTEMPTS[attempt_key] = outcome
                    if rejected:
                        _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
                    return outcome
                capture = await collector.collect_evidence(intervention_observed, self.active_result_timeout_s)
            except BaseException as exc:
                dispatched = attempt_key in _COUNTER_ATTEMPTS
                interrupted = replace(
                    unknown,
                    mutation_attempted=dispatched,
                    execution_outcome="inconclusive" if dispatched else "failed",
                    reason_code="mutation_outcome_unknown" if dispatched else "workflow_execution_error",
                    skip_reason=f"Intervention interrupted by {type(exc).__name__}: {exc}",
                )
                if dispatched:
                    _COUNTER_ATTEMPTS[attempt_key] = interrupted
                    _RUN_SCOPED_EVIDENCE.mark_unfinished(self._profile.target.endpoint, piu, interrupted)
                self._record_workflow_action(
                    "scenario_outcome",
                    piu,
                    process_id,
                    reason_code=interrupted.reason_code,
                    original_cause=interrupted.skip_reason,
                    triggered=False,
                )
                raise
        if not capture.is_lossless or not intervention_observed(capture.all_results):
            outcome = replace(
                unknown,
                reason_code="result_evidence_incomplete",
                method_call_result=result,
                skip_reason="No complete lossless correlated InterventionResult was captured.",
            )
            _COUNTER_ATTEMPTS[attempt_key] = outcome
            return outcome
        final = next(
            item
            for item in reversed(capture.all_results)
            if is_terminal_completed(item, ResultClassification.INTERVENTION_RESULT)
            and self._result_matches_context(item, piu, process_id, origin)
        )
        outcome = replace(
            unknown,
            triggered=True,
            execution_outcome="passed",
            reason_code="",
            skip_reason=None,
            results_confirmed=1,
            method_call_result=result,
            result_progression=ResultProgression(
                classification=ResultClassification.INTERVENTION_RESULT,
                final_result=final,
                all_results=capture.all_results,
                source_events=capture.source_events,
            ),
        )
        _COUNTER_ATTEMPTS[attempt_key] = outcome
        self._record_workflow_action(
            "scenario_outcome",
            piu,
            process_id,
            triggered=True,
            unfinished_process=True,
            reason_code="compound_process_completion_unproven",
        )
        return outcome

    async def _start_selected_joining(self, jpm_node: Any, piu: str, deselect_after: bool) -> bool:
        """Call StartSelectedJoining(piu, deselect_after) and return True on success."""
        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN

        if self._start_attempts >= self._profile.workflow_execution.max_total_start_invocations:
            self._last_method_failure = "Total workflow start-attempt budget exhausted."
            self._last_method_result = None
            return False
        self._start_attempts += 1
        self._record_workflow_action(
            "start_attempt",
            piu,
            self._current_process_id,
            attempt=self._start_attempts,
            total_budget=self._profile.workflow_execution.max_total_start_invocations,
        )
        previous = _RUN_SCOPED_EVIDENCE.unfinished(self._profile.target.endpoint, piu)
        result = await find_and_call_method(
            jpm_node,
            BN.START_SELECTED_JOINING,
            await self._resolve_ijt_namespace_index(),
            ua.Variant(piu, ua.VariantType.String),
            ua.Variant(deselect_after, ua.VariantType.Boolean),
            timeout=self._profile.cu_execution.default_timeout_seconds,
            target_server_authorized=True,
            preserve_status=True,
            before_dispatch=lambda: self._dispatch_mutation(BN.START_SELECTED_JOINING, piu, self._current_process_id),
        )
        self._last_method_result = result
        self._settle_rejected_call(piu, result, previous)
        self._record_workflow_action(
            "start_method_outcome",
            piu,
            self._current_process_id,
            service_success=result.success,
            status_code=result.status_code,
            method_status_code=result.method_status_code,
            rpc_dispatched=result.rpc_dispatched,
            output=[str(value) for value in result.output_list],
        )
        return self._method_succeeded(BN.START_SELECTED_JOINING, result)

    async def _run_workflow(
        self,
        operation_count: int = 1,
        classification: str | int | None = None,
        *,
        require_partials: bool = False,
    ) -> TargetServerTriggerOutcome:
        """Discover and exercise ordered candidates within the configured policy."""
        self._pending_evidence_key = None
        sc = self._profile.cu_execution.state_changing_methods
        selection, _ = self._get_selection_for_classification(classification)
        if not sc.allow_state_changing_method("SelectJoiningProcess"):
            skip_reason = (
                "SelectJoiningProcess is not in the allowed state-changing methods list. "
                "Add it to cu_execution.state_changing_methods.allowed_methods in the target_server profile."
            )
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=skip_reason,
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
            )
        blocked = self._physical_selection_blocker(classification)
        if blocked:
            return blocked
        jpm_node = await self._get_joining_process_management()
        if jpm_node is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="JoiningProcessManagement node not found under JoiningSystem",
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
            )

        piu = await self._resolve_tool_piu()
        prior_failure = self._unfinished_process_outcome(piu)
        if prior_failure is not None:
            return prior_failure
        if sc.allow_state_changing_method("EnableAsset") and not await self._ensure_tool_enabled(piu):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"EnableAsset failed for tool PIU='{piu}': {self._last_method_failure}",
                method="EnableAsset",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
                mutation_attempted=self._mutation_attempted(),
                execution_outcome="inconclusive" if self._mutation_attempted() else "blocked",
                reason_code="asset_state_unconfirmed",
            )

        processes = await self._get_joining_process_list(jpm_node, piu)
        if not processes:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="No joining processes returned by GetJoiningProcessList",
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
            )

        candidates = self._choose_joining_processes(processes, classification=classification)
        if not candidates:
            selection, norm_key = self._get_selection_for_classification(classification)
            label = f"{norm_key} " if norm_key else ""
            if selection.policy == "exact_match" and not self._selection_has_selector(selection):
                skip_reason = (
                    f"Target profile configuration error: the {label}joining process selection uses "
                    "policy 'exact_match' but configures no joining_process_id, "
                    "joining_process_origin_id or selection_name; "
                    f"available: [{self._describe_joining_processes(processes)}]"
                )
            else:
                skip_reason = (
                    f"No joining process matched the configured {label}selection "
                    f"(id='{selection.joining_process_id}', "
                    f"origin='{selection.joining_process_origin_id}', "
                    f"selection_name='{selection.selection_name}'); "
                    f"available: [{self._describe_joining_processes(processes)}]"
                )
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=skip_reason,
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
            )

        selection, _ = self._get_selection_for_classification(classification)
        candidates = candidates[: self._profile.workflow_execution.max_candidates]
        self._record_workflow_action(
            "candidate_scope",
            piu,
            "",
            policy=selection.policy,
            catalog_process_count=len(processes),
            admitted_candidate_count=len(candidates),
            max_candidates=self._profile.workflow_execution.max_candidates,
        )
        candidate_ids = tuple(
            self._process_field(
                candidate,
                "JoiningProcessId",
                "JoiningProcessIdentification",
                "Id",
            )
            for candidate in candidates
        )
        attempted_ids: list[str] = []
        proven_ids: list[str] = []
        rejected_ids: list[str] = []
        outcomes: list[TargetServerTriggerOutcome] = []

        for candidate, candidate_id in zip(candidates, candidate_ids, strict=True):
            if self._start_attempts >= self._profile.workflow_execution.max_total_start_invocations:
                break
            attempted_ids.append(candidate_id)
            candidate_classification = _process_classification(candidate)
            self._record_workflow_action(
                "candidate_attempt",
                piu,
                candidate_id,
                policy=selection.policy,
                classification=candidate_classification.value if candidate_classification is not None else None,
                catalog_fingerprint=self._process_list_fingerprint(processes),
            )
            outcome = await self._run_candidate_workflow(
                jpm_node,
                piu,
                candidate,
                operation_count=operation_count,
                classification=classification,
                require_partials=require_partials,
                catalog_fingerprint=self._process_list_fingerprint(processes),
            )
            outcomes.append(outcome)
            if outcome.triggered:
                proven_ids.append(candidate_id)
                if selection.policy != "all_compatible":
                    break
            else:
                rejected_ids.append(candidate_id)
                if self._last_method_failure or outcome.starts_issued > 0:
                    break

        if not outcomes:
            return TargetServerTriggerOutcome(
                triggered=False,
                method="StartSelectedJoining",
                product_instance_uri=piu,
                reason_code="start_budget_exhausted",
                execution_outcome="blocked",
                skip_reason="No additional start attempts are authorized by the total workflow budget.",
            )
        successful = next((outcome for outcome in outcomes if outcome.triggered), None)
        final_outcome = successful or outcomes[-1]
        summarized = replace(
            final_outcome,
            operation_count=sum(outcome.operation_count for outcome in outcomes),
            starts_issued=sum(outcome.starts_issued for outcome in outcomes),
            results_confirmed=sum(outcome.results_confirmed for outcome in outcomes),
            candidate_process_ids=tuple(attempted_ids),
            proven_process_ids=tuple(proven_ids),
            rejected_process_ids=tuple(rejected_ids),
        )
        if selection.policy == "all_compatible" and (rejected_ids or len(attempted_ids) < len(candidates)):
            rejected = next((outcome for outcome in outcomes if not outcome.triggered), None)
            summarized = replace(
                summarized,
                triggered=False,
                skip_reason=(rejected.skip_reason if rejected else None)
                or "Approved candidate scope was not completed within the total start budget.",
                reason_code="candidate_evidence_incomplete" if rejected else "start_budget_exhausted",
                execution_outcome="inconclusive" if summarized.starts_issued else "blocked",
                mutation_attempted=bool(summarized.starts_issued),
                result_progression=None,
            )
        requested_classification = self._result_classification_value(classification)
        if summarized.triggered and requested_classification is not None:
            self._pending_evidence_key = self._workflow_evidence_key(
                piu=piu,
                process_id=summarized.joining_process_id,
                process_origin_id=summarized.joining_process_origin_id,
                processes=processes,
                classification=requested_classification,
                selection_policy=selection.policy,
                operation_count=min(
                    operation_count,
                    self._profile.workflow_execution.max_start_invocations_by_result_classification.get(
                        self._normalize_classification(classification),
                        self._profile.workflow_execution.max_start_invocations,
                    ),
                    self._profile.workflow_execution.max_start_invocations,
                ),
                require_partials=require_partials,
            )
        return summarized

    @_owned_workflow
    async def _run_candidate_workflow(
        self,
        jpm_node: Any,
        piu: str,
        target_process: Any,
        *,
        operation_count: int,
        classification: str | int | None,
        require_partials: bool = False,
        catalog_fingerprint: tuple | None = None,
    ) -> TargetServerTriggerOutcome:
        fingerprint = catalog_fingerprint
        if fingerprint is None:
            fingerprint = self._process_list_fingerprint(await self._get_joining_process_list(jpm_node, piu))
        blocked = await self._ensure_baseline(jpm_node, piu, target_process, fingerprint)
        if blocked is not None:
            return blocked
        self._scenario_id = uuid.uuid4().hex
        try:
            outcome = await self._execute_candidate_workflow(
                jpm_node,
                piu,
                target_process,
                operation_count=operation_count,
                classification=classification,
                require_partials=require_partials,
                catalog_fingerprint=fingerprint,
            )
        except BaseException as exc:
            previous = _RUN_SCOPED_EVIDENCE.unfinished(self._profile.target.endpoint, piu)
            interrupted = TargetServerTriggerOutcome(
                triggered=False,
                method="StartSelectedJoining",
                product_instance_uri=piu,
                joining_process_id=self._current_process_id,
                mutation_attempted=previous is not None,
                execution_outcome="inconclusive" if previous is not None else "failed",
                reason_code="mutation_outcome_unknown" if previous is not None else "workflow_execution_error",
                skip_reason=f"Scenario interrupted by {type(exc).__name__}: {exc}",
            )
            if previous is not None:
                _RUN_SCOPED_EVIDENCE.mark_unfinished(self._profile.target.endpoint, piu, interrupted)
            self._record_workflow_action(
                "scenario_outcome",
                piu,
                interrupted.joining_process_id,
                triggered=False,
                reason_code=interrupted.reason_code,
                original_cause=interrupted.skip_reason,
                mutation_attempted=interrupted.mutation_attempted,
            )
            raise
        if _RUN_SCOPED_EVIDENCE.unfinished(self._profile.target.endpoint, piu) is not None:
            _RUN_SCOPED_EVIDENCE.mark_unfinished(
                self._profile.target.endpoint,
                piu,
                replace(
                    outcome,
                    reason_code="compound_process_completion_unproven",
                    skip_reason="Requested evidence was captured, but the selected compound process did not finish.",
                )
                if outcome.triggered
                else outcome,
            )
        if outcome.process_progression is not None and outcome.process_progression.is_complete:
            process_key = self._workflow_evidence_key(
                piu=piu,
                process_id=outcome.joining_process_id,
                process_origin_id=outcome.joining_process_origin_id,
                processes=[target_process],
                classification=outcome.process_progression.classification,
                selection_policy=self._get_selection_for_classification(classification)[0].policy,
                operation_count=self._profile.workflow_execution.max_start_invocations,
                require_partials=False,
            )
            process_key = replace(process_key, process_list_fingerprint=fingerprint)
            if self._profile.workflow_execution.evidence_reuse.enabled and self._observed_server_epoch:
                _RUN_SCOPED_EVIDENCE.put(process_key, outcome.process_progression)
        self._record_workflow_action(
            "scenario_outcome",
            piu,
            outcome.joining_process_id,
            triggered=outcome.triggered,
            reason_code=outcome.reason_code,
            mutation_attempted=outcome.mutation_attempted,
            unfinished_process=_RUN_SCOPED_EVIDENCE.unfinished(self._profile.target.endpoint, piu) is not None,
            prior_unresolved_action=outcome.prior_unresolved_action,
        )
        return outcome

    async def _execute_candidate_workflow(
        self,
        jpm_node: Any,
        piu: str,
        target_process: Any,
        *,
        operation_count: int,
        classification: str | int | None,
        require_partials: bool = False,
        catalog_fingerprint: tuple | None = None,
    ) -> TargetServerTriggerOutcome:
        """Select, start, and collect capability evidence for one candidate."""
        jp_id = self._process_field(
            target_process,
            "JoiningProcessId",
            "JoiningProcessIdentification",
            "Id",
        )
        jp_origin = self._process_field(
            target_process,
            "JoiningProcessOriginId",
            "JoiningProcessIdentificationOrigin",
        )

        fingerprint = catalog_fingerprint
        if fingerprint is None:
            fingerprint = self._process_list_fingerprint(await self._get_joining_process_list(jpm_node, piu))
        if not await self._target_context_current(jpm_node, piu, target_process, fingerprint):
            return TargetServerTriggerOutcome(
                triggered=False,
                method="SelectJoiningProcess",
                product_instance_uri=piu,
                joining_process_id=jp_id,
                execution_outcome="blocked",
                reason_code="target_changed",
                skip_reason="Selected candidate no longer matches the current catalog before selection.",
            )
        deselect = self._profile.triggers.result.deselect_after_joining
        requested_result_cls = self._result_classification_value(classification)
        process_result_cls = self._process_result_classification(target_process)
        if classification is None:
            requested_result_cls = process_result_cls
        if process_result_cls is None or requested_result_cls is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                execution_outcome="blocked",
                reason_code="process_completion_contract_unavailable",
                skip_reason="The selected process or requested result has no standard completion classification.",
            )
        max_starts = self._process_start_limit(target_process)
        max_starts = min(
            max_starts, self._profile.workflow_execution.max_total_start_invocations - self._start_attempts
        )
        if max_starts <= 0:
            return TargetServerTriggerOutcome(
                triggered=False,
                execution_outcome="blocked",
                reason_code="start_budget_exhausted",
                skip_reason="No start attempts remain. Selection and actuation were not dispatched.",
            )

        from contextlib import AsyncExitStack

        from helpers.namespaces import NS_IJT_BASE
        from helpers.result_collector import ResultCollector, is_partial, is_terminal_matching_state

        async with AsyncExitStack() as stack:
            completed_operations = 0
            confirmed_operations = 0
            terminal_result_confirmed = False
            action_settlement_unproven = False
            result_progression = None
            process_progression = None
            completion_collector = None
            if self._subscription_client is not None:
                completion_collector = await stack.enter_async_context(
                    ResultCollector(
                        self._subscription_client,
                        {NS_IJT_BASE: await self._resolve_ijt_namespace_index()},
                        is_simulator=False,
                        parent_result_reader=self._read_parent_result,
                        result_observer=lambda result, duplicate: self._observe_result(
                            piu, jp_id, jp_origin, result, duplicate
                        ),
                    )
                )
            else:
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=(
                        "The requested result workflow requires a separate subscription client "
                        "to prove correlated result-classification evidence"
                    ),
                    method="StartSelectedJoining",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                    joining_process_origin_id=jp_origin,
                    reason_code="result_subscription_required",
                    execution_outcome="blocked",
                )
            selected = await self._select_joining_process(jpm_node, target_process, piu, classification=classification)
            if not selected:
                unknown = _RUN_SCOPED_EVIDENCE.unfinished(self._profile.target.endpoint, piu) is not None
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"SelectJoiningProcess failed for process '{jp_id}': {self._last_method_failure}",
                    method="SelectJoiningProcess",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                    mutation_attempted=unknown,
                    execution_outcome="inconclusive" if unknown else "blocked",
                    reason_code="mutation_outcome_unknown" if unknown else "selection_not_dispatched",
                )
            await self._wait_for_process_selection_settle()
            self._current_process_id = jp_id
            pacing = float(getattr(self._profile.workflow_execution, "consecutive_start_delay_seconds", 0.25))
            expected_state = int(
                getattr(
                    self._profile.workflow_execution.expected_results,
                    "expected_terminal_result_state",
                    1,
                )
            )
            terminal_predicate = lambda result: self._result_matches_context(result, piu, jp_id, jp_origin)
            operation_predicate = terminal_predicate

            if completion_collector is not None:
                completion_collector.discard_pending()

            for operation_number in range(1, max_starts + 1):
                if completion_collector is not None and operation_number > 1:
                    pending_terminal = completion_collector.collect_pending_terminal(
                        process_result_cls,
                        terminal_predicate,
                        expected_terminal_state=expected_state,
                    )
                    if pending_terminal is not None:
                        terminal_result_confirmed = True
                        logger.info(
                            "Queued terminal result (classification %s) confirmed before operation %d/%d",
                            requested_result_cls,
                            operation_number,
                            max_starts,
                        )
                        break
                if not await self._target_context_current(jpm_node, piu, target_process, fingerprint):
                    return TargetServerTriggerOutcome(
                        triggered=False,
                        method="StartSelectedJoining",
                        product_instance_uri=piu,
                        joining_process_id=jp_id,
                        starts_issued=completed_operations,
                        operation_count=completed_operations,
                        results_confirmed=confirmed_operations,
                        mutation_attempted=True,
                        execution_outcome="inconclusive",
                        reason_code="target_changed",
                        skip_reason="Process identity or catalog changed after selection, before the next start.",
                    )
                if completion_collector is not None and operation_number > 1:
                    pending_terminal = completion_collector.collect_pending_terminal(
                        process_result_cls, terminal_predicate, expected_terminal_state=expected_state
                    )
                    if pending_terminal is not None:
                        terminal_result_confirmed = True
                        break
                started = await self._start_selected_joining(jpm_node, piu, deselect)
                if not started:
                    # The failing start was never accepted, so neither it nor a
                    # result for it counts as evidence.
                    return TargetServerTriggerOutcome(
                        triggered=False,
                        skip_reason=(
                            f"StartSelectedJoining failed on operation {operation_number}/{max_starts} "
                            f"for process '{jp_id}', PIU='{piu}': {self._last_method_failure}"
                        ),
                        method="StartSelectedJoining",
                        trigger_mode="start_selected_joining",
                        product_instance_uri=piu,
                        joining_process_id=jp_id,
                        joining_process_origin_id=jp_origin,
                        operation_count=operation_number - 1,
                        starts_issued=operation_number - 1,
                        results_confirmed=confirmed_operations,
                        mutation_attempted=True,
                        execution_outcome="inconclusive",
                        reason_code="mutation_outcome_unknown",
                    )
                completed_operations = operation_number
                _RUN_SCOPED_EVIDENCE.mark_unfinished(
                    self._profile.target.endpoint,
                    piu,
                    TargetServerTriggerOutcome(
                        triggered=False,
                        product_instance_uri=piu,
                        joining_process_id=jp_id,
                        joining_process_origin_id=jp_origin,
                        mutation_attempted=True,
                        execution_outcome="inconclusive",
                        reason_code="compound_process_completion_unproven",
                        skip_reason="The selected process has not reached its terminal result.",
                    ),
                )
                if completion_collector is not None:
                    obs = await completion_collector.collect_correlated_operation_outcome(
                        requested_result_classification=process_result_cls,
                        predicate=terminal_predicate,
                        operation_timeout_s=self.active_result_timeout_s,
                        terminal_drain_seconds=pacing,
                        operation_predicate=operation_predicate,
                        operation_context_predicate=lambda result: self._result_matches_tool_context(result, piu),
                        expected_terminal_state=expected_state,
                    )
                    if obs.timed_out:
                        # This start was accepted but produced no correlated result
                        return TargetServerTriggerOutcome(
                            triggered=False,
                            skip_reason=(
                                f"{obs.queue_overflow_count} result event(s) were lost. "
                                "Further automatic actuation is stopped for this run. "
                                "The operator must establish readiness before starting a new run."
                                if obs.queue_overflow_count
                                else "No correlated result confirming the selected Tool and JoiningProcess "
                                f"arrived on operation {operation_number}/{max_starts} within "
                                f"{self.active_result_timeout_s:.1f}s. The accepted start remains unconfirmed; "
                                "inspect retained method and result evidence before retrying."
                            ),
                            method="StartSelectedJoining",
                            trigger_mode="start_selected_joining",
                            product_instance_uri=piu,
                            joining_process_id=jp_id,
                            joining_process_origin_id=jp_origin,
                            operation_count=operation_number,
                            starts_issued=operation_number,
                            results_confirmed=confirmed_operations,
                            mutation_attempted=True,
                            execution_outcome="inconclusive",
                            reason_code="result_capture_overflow"
                            if obs.queue_overflow_count
                            else "operation_evidence_timeout",
                        )
                    confirmed_operations = operation_number
                    if obs.terminal_result is not None:
                        action_settlement_unproven = operation_number > 1 and obs.operation_result is None
                        terminal_result_confirmed = True
                        logger.info(
                            "Terminal result (classification %s) confirmed on operation %d/%d; workflow completed",
                            requested_result_cls,
                            operation_number,
                            max_starts,
                        )
                        completed_operations = operation_number
                        break

            if completion_collector is not None and requested_result_cls is not None:
                observation_budget = self.active_result_timeout_s
                if self._workflow_deadline is not None:
                    observation_budget = min(
                        observation_budget,
                        max(0.0, self._workflow_deadline - asyncio.get_running_loop().time()),
                    )
                process_progression = await completion_collector.collect_progression(
                    process_result_cls,
                    timeout_s=observation_budget,
                    require_partials=require_partials if requested_result_cls == process_result_cls else False,
                    expected_terminal_state=expected_state,
                    allow_partial_references=self.allow_partial_referenced_children,
                    predicate=terminal_predicate,
                )
                terminal_result_confirmed = process_progression.terminal_result is not None
                result_progression = process_progression
                if terminal_result_confirmed:
                    if not action_settlement_unproven and not process_progression.queue_overflow_count:
                        _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
                    _RUN_SCOPED_EVIDENCE._prepared.pop(piu, None)
                    if requested_result_cls != process_result_cls:
                        result_progression = ResultCollector.progression_from_capture(
                            ResultCollector.related_capture(process_progression),
                            requested_result_cls,
                            require_partials=require_partials,
                            expected_terminal_state=expected_state,
                            allow_partial_references=self.allow_partial_referenced_children,
                            predicate=lambda result: (
                                is_partial(result)
                                or is_terminal_matching_state(result, requested_result_cls, expected_state)
                            ),
                        )

        if process_progression is not None:
            mismatch = self._unexpected_terminal_outcome(
                process_progression.terminal_result,
                expected_state,
                piu,
                jp_id,
                starts_issued=completed_operations,
                results_confirmed=confirmed_operations - int(action_settlement_unproven),
                process_progression=process_progression,
                result_progression=result_progression,
                process_settled=not action_settlement_unproven,
            )
            if mismatch is not None:
                return mismatch
        if action_settlement_unproven:
            return TargetServerTriggerOutcome(
                triggered=False,
                method="StartSelectedJoining",
                product_instance_uri=piu,
                joining_process_id=jp_id,
                joining_process_origin_id=jp_origin,
                operation_count=completed_operations,
                starts_issued=completed_operations,
                results_confirmed=max(0, confirmed_operations - 1),
                result_progression=result_progression,
                process_progression=process_progression,
                mutation_attempted=True,
                execution_outcome="inconclusive",
                reason_code="accepted_start_settlement_unproven",
                skip_reason="A parent terminal result arrived after an additional start, without a new owned operation "
                "result to settle that start. The terminal may belong to the preceding operation. "
                "No further automatic mutation is permitted in this run.",
            )
        if completion_collector is not None and (
            not terminal_result_confirmed or result_progression is None or not result_progression.is_complete
        ):
            if result_progression is not None and result_progression.final_result is not None:
                evidence_reason = (
                    f"A completed result with requested classification {requested_result_cls} was captured, "
                    "but required result evidence is incomplete."
                )
                if result_progression.unresolved_reference_ids:
                    evidence_reason += (
                        " Missing referenced ResultIds: " + ", ".join(result_progression.unresolved_reference_ids) + "."
                    )
                if result_progression.missing_required_partials:
                    evidence_reason += " Required partial results were not captured."
                if result_progression.queue_overflow_count:
                    evidence_reason += f" Lost result events: {result_progression.queue_overflow_count}."
            else:
                evidence_reason = (
                    f"No completed result with requested classification {requested_result_cls} was observed; "
                    "process metadata alone does not prove result capability."
                )
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"Process '{jp_id}' accepted {completed_operations} start(s). {evidence_reason}",
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
                joining_process_id=jp_id,
                joining_process_origin_id=jp_origin,
                operation_count=completed_operations,
                starts_issued=completed_operations,
                results_confirmed=confirmed_operations,
                result_progression=result_progression,
                process_progression=process_progression if terminal_result_confirmed else None,
                mutation_attempted=completed_operations > 0,
                execution_outcome="inconclusive",
                reason_code="result_evidence_incomplete",
            )

        logger.debug(
            "StartSelectedJoining succeeded: PIU=%s, process=%s, starts=%d, results confirmed=%d",
            piu,
            jp_id,
            completed_operations,
            confirmed_operations,
        )
        return TargetServerTriggerOutcome(
            triggered=True,
            method="StartSelectedJoining",
            trigger_mode="start_selected_joining",
            product_instance_uri=piu,
            joining_process_id=jp_id,
            joining_process_origin_id=jp_origin,
            operation_count=completed_operations,
            starts_issued=completed_operations,
            results_confirmed=confirmed_operations,
            result_progression=result_progression,
            process_progression=process_progression,
            mutation_attempted=completed_operations > 0,
            execution_outcome="passed",
        )

    @_owned_workflow
    async def _trigger_operations(
        self,
        operation_count: int,
        classification: str | int | None = None,
        *,
        require_partials: bool = False,
    ) -> TriggerOutcome:
        """Trigger the approved candidate scope for the requested operation count."""
        method_timeout = self._profile.cu_execution.default_timeout_seconds
        result_timeout = self._profile.workflow_execution.expected_results.timeout_seconds
        max_candidates = self._profile.workflow_execution.max_candidates
        max_starts = min(
            self._profile.workflow_execution.max_total_start_invocations,
            max_candidates * self._profile.workflow_execution.max_start_invocations,
        )
        # The deadline spans the candidate window, including each candidate's setup and final observation.
        workflow_timeout = max_candidates * ((4 * method_timeout) + result_timeout) + max_starts * (
            method_timeout + result_timeout + self._profile.workflow_execution.consecutive_start_delay_seconds
        )
        self._workflow_deadline = asyncio.get_running_loop().time() + workflow_timeout
        try:
            workflow = (
                self._run_workflow(
                    operation_count,
                    classification=classification,
                    require_partials=True,
                )
                if require_partials
                else self._run_workflow(operation_count, classification=classification)
            )
            return await asyncio.wait_for(
                workflow,
                timeout=workflow_timeout,
            )
        except asyncio.TimeoutError:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=(f"StartSelectedJoining workflow timed out after {workflow_timeout}s"),
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
                mutation_attempted=self._mutation_attempted(),
                execution_outcome="inconclusive" if self._mutation_attempted() else "blocked",
                reason_code="workflow_deadline_exhausted",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("StartSelectedJoining workflow failed")
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"StartSelectedJoining workflow failed: {exc}",
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
                mutation_attempted=self._mutation_attempted(),
                execution_outcome="inconclusive" if self._mutation_attempted() else "blocked",
                reason_code="workflow_execution_error",
            )
        finally:
            self._workflow_deadline = None

    async def trigger_single(self, result_type: int, include_traces: bool = False) -> TriggerOutcome:
        """Trigger one joining operation and wait for a result."""
        return await self._trigger_operations(1, classification=ResultClassification.SINGLE_RESULT)

    async def trigger_batch_or_sync(
        self,
        classification: int,
        num_children: int = 3,
        include_traces: bool = False,
        send_as_refs: bool = False,
        *,
        require_partials: bool = False,
    ) -> TriggerOutcome:
        """Trigger joining workflow for batch/sync evidence.

        Starts are bounded by max_start_invocations and stop early when the
        requested terminal result is observed.
        """
        if classification == ResultClassification.INTERVENTION_RESULT:
            return await self._trigger_intervention()
        return await self._trigger_operations(
            num_children,
            classification=classification,
            require_partials=require_partials,
        )

    async def trigger_job(self, send_as_refs: bool = False) -> TriggerOutcome:
        """Trigger joining workflow for job-level evidence."""
        return await self._trigger_operations(
            getattr(self._profile.workflow_execution, "max_start_invocations", 6),
            classification=ResultClassification.JOB_RESULT,
        )

    @_owned_workflow
    async def _run_abort_workflow(self) -> TargetServerTriggerOutcome:
        return await self._run_sequence_workflow(self._execute_abort_workflow)

    async def _execute_abort_workflow(self) -> TargetServerTriggerOutcome:
        """Execute a multi-step Job/Batch, start step 1, issue AbortJoiningProcess, and verify terminal abort result."""
        from contextlib import AsyncExitStack

        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN, NS_IJT_BASE, ResultEvaluation, ResultState
        from helpers.result_collector import (
            ResultCollector,
            get_classification,
            is_terminal_matching_state,
            is_terminal_result,
        )

        sc = self._profile.cu_execution.state_changing_methods
        for method in ("SelectJoiningProcess", "StartSelectedJoining", "AbortJoiningProcess"):
            if not sc.allow_state_changing_method(method):
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"{method} is not in the allowed state-changing methods list.",
                    method=method,
                    trigger_mode="start_selected_joining",
                )

        if self._subscription_client is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                method="AbortJoiningProcess",
                execution_outcome="blocked",
                reason_code="result_subscription_required",
                skip_reason="Abort requires a subscription client before selection or start.",
            )
        blocked = self._physical_selection_blocker("job", method="AbortJoiningProcess")
        if blocked:
            return blocked
        jpm_node = await self._get_joining_process_management()
        if jpm_node is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="JoiningProcessManagement node not found under JoiningSystem",
                method="AbortJoiningProcess",
                trigger_mode="start_selected_joining",
            )

        piu = await self._resolve_tool_piu()
        prior_failure = self._claim_controlled_scope(piu)
        if prior_failure is not None:
            return prior_failure
        if sc.allow_state_changing_method("EnableAsset") and not await self._ensure_tool_enabled(piu):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"EnableAsset failed for tool PIU='{piu}': {self._last_method_failure}",
                method="EnableAsset",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
                mutation_attempted=self._mutation_attempted(),
                execution_outcome="inconclusive" if self._mutation_attempted() else "blocked",
                reason_code="asset_state_unconfirmed",
            )

        processes = await self._get_joining_process_list(jpm_node, piu)
        if not processes:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="No joining processes returned by GetJoiningProcessList",
                method="AbortJoiningProcess",
                trigger_mode="start_selected_joining",
            )

        target_process = self._choose_joining_process(processes, classification="job")
        job_selection, _ = self._get_selection_for_classification("job")
        if target_process is None and job_selection.policy != "exact_match":
            blocked = self._physical_selection_blocker("batch", method="AbortJoiningProcess", reset_budget=False)
            if blocked:
                return blocked
            target_process = self._choose_joining_process(processes, classification="batch")
        if target_process is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="No Job or Batch process found to execute abort workflow",
                method="AbortJoiningProcess",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
            )

        process_cls = _process_classification(target_process)
        is_job = process_cls == JoiningProcessClassification.JOB
        cls_key = "job" if is_job else "batch"
        res_cls = ResultClassification.JOB_RESULT if is_job else ResultClassification.BATCH_RESULT

        jp_id = self._process_field(target_process, "JoiningProcessId", "JoiningProcessIdentification", "Id")
        jp_origin = self._process_field(target_process, "JoiningProcessOriginId", "JoiningProcessIdentificationOrigin")

        selected = await self._select_joining_process(jpm_node, target_process, piu, classification=cls_key)
        if not selected:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"SelectJoiningProcess failed for process '{jp_id}': {self._last_method_failure}",
                method="SelectJoiningProcess",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
                joining_process_id=jp_id,
            )
        await self._wait_for_process_selection_settle()

        identification = self._make_process_identification(target_process, classification=cls_key)
        if identification is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="JoiningProcessIdentificationDataType is unavailable",
                method="AbortJoiningProcess",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
            )

        if self._subscription_client is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="Abort workflow requires a subscription client for correlated events",
                method="AbortJoiningProcess",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
            )

        abort_station_ref = [self._profile.selection.tool.virtual_station_product_instance_uri]
        async with AsyncExitStack() as stack:
            collector = await stack.enter_async_context(
                ResultCollector(
                    self._subscription_client,
                    {NS_IJT_BASE: await self._resolve_ijt_namespace_index()},
                    is_simulator=False,
                    parent_result_reader=self._read_parent_result,
                    result_observer=lambda result, duplicate: self._observe_result(
                        piu,
                        jp_id,
                        jp_origin,
                        result,
                        duplicate,
                        counter_virtual_station_uri=abort_station_ref[0],
                    ),
                )
            )
            collector.discard_pending()

            # Step 1: Start operation 1
            deselect = self._profile.triggers.result.deselect_after_joining
            started = await self._start_selected_joining(jpm_node, piu, deselect)
            if not started:
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"StartSelectedJoining failed on step 1 of abort workflow: {self._last_method_failure}",
                    method="StartSelectedJoining",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                )

            # Wait for operation 1 SingleResult to establish active sequence state
            obs = await collector.collect_correlated_operation_outcome(
                requested_result_classification=res_cls,
                predicate=lambda result: self._result_matches_context(result, piu, jp_id, jp_origin),
                operation_timeout_s=self.active_result_timeout_s,
                terminal_drain_seconds=0.1,
                operation_predicate=lambda result: self._result_matches_context(result, piu, jp_id, jp_origin),
                operation_context_predicate=lambda result: self._result_matches_tool_context(result, piu),
            )
            if obs.terminal_result is None:
                queued = collector.collect_pending_terminal(
                    res_cls, lambda result: self._result_matches_context(result, piu, jp_id, jp_origin)
                )
                if is_terminal_result(queued, res_cls):
                    obs = replace(
                        obs,
                        terminal_result=queued,
                        timed_out=obs.timed_out or not collector.capture_pending().is_lossless,
                    )
            mismatch = self._unexpected_terminal_outcome(
                obs.terminal_result,
                1,
                piu,
                jp_id,
                starts_issued=1,
                results_confirmed=int(obs.operation_result is not None),
                result_capture=collector.capture_pending(),
                process_settled=not obs.timed_out,
            )
            if mismatch is not None:
                return mismatch
            if not obs.operation_confirmed or obs.operation_result is None or obs.terminal_result is not None:
                if obs.terminal_result is not None:
                    _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
                    return TargetServerTriggerOutcome(
                        triggered=False,
                        skip_reason="Process completed before abort could be issued (cannot abort an already-completed sequence)",
                        method="AbortJoiningProcess",
                        trigger_mode="start_selected_joining",
                        product_instance_uri=piu,
                        joining_process_id=jp_id,
                        execution_outcome="blocked",
                        reason_code="process_completed_before_intervention",
                    )
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=(
                        f"Step 1 operation timed out or produced no SingleResult before abort: "
                        f"{self._last_method_failure}"
                    ),
                    method="StartSelectedJoining",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                )

            step1_capture = collector.capture_pending()
            abort_boundary = len(step1_capture.all_results)
            step1_results = (*tuple(step1_capture.all_results or ()), obs.operation_result)
            if not abort_station_ref[0]:
                abort_station_ref[0] = self._counter_station_from_joining_results(step1_results, piu, jp_id)
            if not abort_station_ref[0]:
                abort_station_ref[0] = await self._discover_counter_station_fallback(piu, jp_id)
            abort_station = abort_station_ref[0]

            # Step 2: Issue AbortJoiningProcess
            message = str(
                self._profile.cu_execution.extension_fields.get(
                    "abort_message",
                    "IJT target-server automated abort test",
                )
            )
            previous = _RUN_SCOPED_EVIDENCE.unfinished(self._profile.target.endpoint, piu)
            self._record_workflow_action(
                "abort_attempt",
                piu,
                jp_id,
                virtual_station_product_instance_uri=abort_station,
            )
            abort_result = await find_and_call_method(
                jpm_node,
                BN.ABORT_JOINING_PROCESS,
                await self._resolve_ijt_namespace_index(),
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant(identification, ua.VariantType.ExtensionObject),
                ua.Variant(ua.LocalizedText(Text=message, Locale="en"), ua.VariantType.LocalizedText),
                timeout=self._profile.cu_execution.default_timeout_seconds,
                target_server_authorized=True,
                preserve_status=True,
                before_dispatch=lambda: self._dispatch_mutation(BN.ABORT_JOINING_PROCESS, piu, jp_id),
            )
            self._last_method_result = abort_result
            self._settle_rejected_call(piu, abort_result, previous)
            if not self._method_succeeded(BN.ABORT_JOINING_PROCESS, abort_result):
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"AbortJoiningProcess call failed for process '{jp_id}': {self._last_method_failure}",
                    method="AbortJoiningProcess",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                )

            # Step 3: Wait for terminal result matching configured expected_abort_result_states
            allowed_abort_states = tuple(
                getattr(
                    self._profile.workflow_execution.expected_results,
                    "expected_abort_result_states",
                    (ResultState.ABORTED,),
                )
            ) or (ResultState.ABORTED,)
            abort_predicate = (
                (lambda result: self._counter_result_matches_context(result, piu, jp_id, abort_station, jp_origin))
                if abort_station
                else (lambda result: self._result_matches_context(result, piu, jp_id, jp_origin))
            )
            abort_obs = await collector.collect_correlated_operation_outcome(
                requested_result_classification=res_cls,
                predicate=abort_predicate,
                operation_timeout_s=self.active_result_timeout_s,
                terminal_drain_seconds=0.25,
                expected_terminal_state=allowed_abort_states[0],
            )
            if abort_obs.terminal_result is None:
                queued_abort = collector.collect_pending_terminal(res_cls, abort_predicate)
                if is_terminal_result(queued_abort, res_cls):
                    abort_obs = replace(
                        abort_obs,
                        terminal_result=queued_abort,
                        timed_out=abort_obs.timed_out or not collector.capture_pending().is_lossless,
                    )
            matched_abort_state = next(
                (
                    state
                    for state in allowed_abort_states
                    if is_terminal_matching_state(abort_obs.terminal_result, res_cls, state)
                ),
                allowed_abort_states[0],
            )
            abort_capture = collector.capture_pending()
            mismatch = self._unexpected_terminal_outcome(
                abort_obs.terminal_result,
                matched_abort_state,
                piu,
                jp_id,
                method="AbortJoiningProcess",
                starts_issued=1,
                results_confirmed=1,
                result_capture=abort_capture,
                process_settled=not abort_obs.timed_out,
            )
            if mismatch is not None:
                return mismatch
            if abort_obs.terminal_result is None or not is_terminal_matching_state(
                abort_obs.terminal_result, res_cls, matched_abort_state
            ):
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=(
                        f"Abort workflow did not receive expected terminal aborted result: {self._last_method_failure}"
                    ),
                    method="AbortJoiningProcess",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                )

            _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
            for post_abort_res in abort_capture.all_results[abort_boundary:]:
                if get_classification(post_abort_res) == ResultClassification.INTERVENTION_RESULT and abort_predicate(
                    post_abort_res
                ):
                    self.validate_result_expectations(post_abort_res, context="counter_intervention")
            self.validate_result_expectations(abort_obs.terminal_result, context="counter_intervention")
            if getattr(self._profile.workflow_execution.expected_results, "reject_ok_evaluation_on_abort", False):
                eval_val = self._result_metadata_value(abort_obs.terminal_result, "ResultEvaluation")
                if eval_val == ResultEvaluation.OK:
                    return TargetServerTriggerOutcome(
                        triggered=False,
                        skip_reason=(
                            "Aborted result was evaluated as OK (1) and reject_ok_evaluation_on_abort is enabled"
                        ),
                        method="AbortJoiningProcess",
                        trigger_mode="start_selected_joining",
                        product_instance_uri=piu,
                        joining_process_id=jp_id,
                        execution_outcome="failed",
                        reason_code="aborted_result_evaluation_invalid",
                    )

        _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
        return TargetServerTriggerOutcome(
            triggered=True,
            method="AbortJoiningProcess",
            trigger_mode="start_selected_joining",
            product_instance_uri=piu,
            joining_process_id=jp_id,
            joining_process_origin_id=jp_origin,
            operation_count=1,
            starts_issued=1,
            results_confirmed=1,
            mutation_attempted=True,
            process_settled=True,
        )

    @_owned_workflow
    async def _run_reset_workflow(self) -> TargetServerTriggerOutcome:
        return await self._run_sequence_workflow(self._execute_reset_workflow)

    async def _execute_reset_workflow(self) -> TargetServerTriggerOutcome:
        """Execute ResetJoiningProcess on an active Job/Batch sequence and verify restart to step 1."""
        from contextlib import AsyncExitStack

        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN, NS_IJT_BASE
        from helpers.result_collector import ResultCollector, is_terminal_result

        sc = self._profile.cu_execution.state_changing_methods
        for method in ("SelectJoiningProcess", "StartSelectedJoining", "ResetJoiningProcess"):
            if not sc.allow_state_changing_method(method):
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"{method} is not in the allowed state-changing methods list.",
                    method=method,
                    trigger_mode="start_selected_joining",
                )

        if self._subscription_client is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                method="ResetJoiningProcess",
                execution_outcome="blocked",
                reason_code="result_subscription_required",
                skip_reason="Reset requires a subscription client before selection or start.",
            )
        blocked = self._physical_selection_blocker("job", method="ResetJoiningProcess")
        if blocked:
            return blocked
        jpm_node = await self._get_joining_process_management()
        if jpm_node is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="JoiningProcessManagement node not found under JoiningSystem",
                method="ResetJoiningProcess",
                trigger_mode="start_selected_joining",
            )

        piu = await self._resolve_tool_piu()
        prior_failure = self._claim_controlled_scope(piu)
        if prior_failure is not None:
            return prior_failure
        processes = await self._get_joining_process_list(jpm_node, piu)
        if not processes:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="No joining processes returned by GetJoiningProcessList",
                method="ResetJoiningProcess",
                trigger_mode="start_selected_joining",
            )

        target_process = self._choose_joining_process(processes, classification="job")
        job_selection, _ = self._get_selection_for_classification("job")
        if target_process is None and job_selection.policy != "exact_match":
            blocked = self._physical_selection_blocker("batch", method="ResetJoiningProcess", reset_budget=False)
            if blocked:
                return blocked
            target_process = self._choose_joining_process(processes, classification="batch")
        if target_process is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="No Job or Batch process found to execute reset workflow",
                method="ResetJoiningProcess",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
            )

        process_cls = _process_classification(target_process)
        is_job = process_cls == JoiningProcessClassification.JOB
        cls_key = "job" if is_job else "batch"
        res_cls = ResultClassification.JOB_RESULT if is_job else ResultClassification.BATCH_RESULT

        jp_id = self._process_field(target_process, "JoiningProcessId", "JoiningProcessIdentification", "Id")
        jp_origin = self._process_field(target_process, "JoiningProcessOriginId", "JoiningProcessIdentificationOrigin")

        if (
            min(self._process_start_limit(target_process), self._profile.workflow_execution.max_total_start_invocations)
            < 2
        ):
            return TargetServerTriggerOutcome(
                triggered=False,
                method="ResetJoiningProcess",
                product_instance_uri=piu,
                execution_outcome="blocked",
                reason_code="reset_experiment_budget_unavailable",
                skip_reason="Reset-step verification requires two starts within the existing process and total ceilings.",
            )
        selected = await self._select_joining_process(jpm_node, target_process, piu, classification=cls_key)
        if not selected:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"SelectJoiningProcess failed for process '{jp_id}': {self._last_method_failure}",
                method="SelectJoiningProcess",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
                joining_process_id=jp_id,
            )
        await self._wait_for_process_selection_settle()

        identification = self._make_process_identification(target_process, classification=cls_key)
        if identification is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="JoiningProcessIdentificationDataType is unavailable",
                method="ResetJoiningProcess",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
            )

        if self._subscription_client is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="Reset workflow requires a subscription client to observe and verify active sequence state",
                method="ResetJoiningProcess",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
            )

        reset_station_ref = [self._profile.selection.tool.virtual_station_product_instance_uri]
        async with AsyncExitStack() as stack:
            collector = await stack.enter_async_context(
                ResultCollector(
                    self._subscription_client,
                    {NS_IJT_BASE: await self._resolve_ijt_namespace_index()},
                    is_simulator=False,
                    parent_result_reader=self._read_parent_result,
                    result_observer=lambda result, duplicate: self._observe_result(
                        piu,
                        jp_id,
                        jp_origin,
                        result,
                        duplicate,
                        counter_virtual_station_uri=reset_station_ref[0],
                    ),
                )
            )
            collector.discard_pending()
            deselect = self._profile.triggers.result.deselect_after_joining

            # Step 1: Start operation 1 to establish active sequence state
            started = await self._start_selected_joining(jpm_node, piu, deselect)
            if not started:
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"StartSelectedJoining failed on step 1 of reset workflow: {self._last_method_failure}",
                    method="StartSelectedJoining",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                )
            obs = await collector.collect_correlated_operation_outcome(
                requested_result_classification=res_cls,
                predicate=lambda result: self._result_matches_context(result, piu, jp_id, jp_origin),
                operation_timeout_s=self.active_result_timeout_s,
                terminal_drain_seconds=0.1,
                operation_predicate=lambda result: self._result_matches_context(result, piu, jp_id, jp_origin),
                operation_context_predicate=lambda result: self._result_matches_tool_context(result, piu),
            )
            if obs.terminal_result is None:
                queued = collector.collect_pending_terminal(
                    res_cls, lambda result: self._result_matches_context(result, piu, jp_id, jp_origin)
                )
                if is_terminal_result(queued, res_cls):
                    obs = replace(
                        obs,
                        terminal_result=queued,
                        timed_out=obs.timed_out or not collector.capture_pending().is_lossless,
                    )
            mismatch = self._unexpected_terminal_outcome(
                obs.terminal_result,
                1,
                piu,
                jp_id,
                starts_issued=1,
                results_confirmed=int(obs.operation_result is not None),
                result_capture=collector.capture_pending(),
                process_settled=not obs.timed_out,
            )
            if mismatch is not None:
                return mismatch
            if not obs.operation_confirmed or obs.operation_result is None or obs.terminal_result is not None:
                if obs.terminal_result is not None:
                    _RUN_SCOPED_EVIDENCE.mark_completed(self._profile.target.endpoint, piu)
                    return TargetServerTriggerOutcome(
                        triggered=False,
                        skip_reason="Process completed before reset could be issued (cannot reset an already-completed sequence)",
                        method="ResetJoiningProcess",
                        trigger_mode="start_selected_joining",
                        product_instance_uri=piu,
                        joining_process_id=jp_id,
                        execution_outcome="blocked",
                        reason_code="process_completed_before_intervention",
                    )
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"Step 1 operation timed out before reset: {self._last_method_failure}",
                    method="StartSelectedJoining",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                )

            # Step 2: Issue ResetJoiningProcess
            step1_reset_capture = collector.capture_pending()
            reset_boundary = len(step1_reset_capture.all_results)
            step1_reset_results = (*tuple(step1_reset_capture.all_results or ()), obs.operation_result)
            if not reset_station_ref[0]:
                reset_station_ref[0] = self._counter_station_from_joining_results(step1_reset_results, piu, jp_id)
            if not reset_station_ref[0]:
                reset_station_ref[0] = await self._discover_counter_station_fallback(piu, jp_id)
            reset_station = reset_station_ref[0]
            previous = _RUN_SCOPED_EVIDENCE.unfinished(self._profile.target.endpoint, piu)
            self._record_workflow_action(
                "reset_attempt",
                piu,
                jp_id,
                virtual_station_product_instance_uri=reset_station,
            )
            reset_result = await find_and_call_method(
                jpm_node,
                BN.RESET_JOINING_PROCESS,
                await self._resolve_ijt_namespace_index(),
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant(identification, ua.VariantType.ExtensionObject),
                timeout=self._profile.cu_execution.default_timeout_seconds,
                target_server_authorized=True,
                preserve_status=True,
                before_dispatch=lambda: self._dispatch_mutation(BN.RESET_JOINING_PROCESS, piu, jp_id),
            )
            self._last_method_result = reset_result
            self._settle_rejected_call(piu, reset_result, previous)
            if not self._method_succeeded(BN.RESET_JOINING_PROCESS, reset_result):
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"ResetJoiningProcess call failed for process '{jp_id}': {self._last_method_failure}",
                    method="ResetJoiningProcess",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                )

            # Retain reset evidence, while draining it out of the restart action window.
            restart_boundary = len(collector.capture_pending().all_results)
            restarted = await self._start_selected_joining(jpm_node, piu, deselect)
            if not restarted:
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"Post-reset restart failed on step 1: {self._last_method_failure}",
                    method="StartSelectedJoining",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                )
            restart_obs = await collector.collect_correlated_operation_outcome(
                requested_result_classification=res_cls,
                predicate=lambda result: self._result_matches_context(result, piu, jp_id, jp_origin),
                operation_timeout_s=self.active_result_timeout_s,
                terminal_drain_seconds=0.1,
                operation_predicate=lambda result: self._result_matches_context(result, piu, jp_id, jp_origin),
                operation_context_predicate=lambda result: self._result_matches_tool_context(result, piu),
                ownership_after_result_count=restart_boundary,
            )
            mismatch = self._unexpected_terminal_outcome(
                restart_obs.terminal_result,
                1,
                piu,
                jp_id,
                starts_issued=2,
                results_confirmed=1 + int(restart_obs.operation_result is not None),
                result_capture=collector.capture_pending(),
                process_settled=not restart_obs.timed_out and restart_obs.operation_result is not None,
            )
            if mismatch is not None:
                return mismatch
            if (
                not restart_obs.operation_confirmed
                or restart_obs.operation_result is None
                or restart_obs.terminal_result is not None
            ):
                if restart_obs.terminal_result is not None:
                    return TargetServerTriggerOutcome(
                        triggered=False,
                        skip_reason="Post-reset restart completed parent sequence prematurely",
                        method="ResetJoiningProcess",
                        trigger_mode="start_selected_joining",
                        product_instance_uri=piu,
                        joining_process_id=jp_id,
                    )
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=(
                        f"Post-reset restart timed out waiting for step 1 SingleResult: {self._last_method_failure}"
                    ),
                    method="StartSelectedJoining",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                )

            same_step, evidence_error, inconclusive = self._same_reset_step_evidence(
                obs.operation_result,
                restart_obs.operation_result,
            )
            before_step_id = str(self._result_metadata_value(obs.operation_result, "StepId") or "").strip()
            after_step_id = str(self._result_metadata_value(restart_obs.operation_result, "StepId") or "").strip()
            before_seq = self._result_metadata_value(obs.operation_result, "SequenceNumber")
            after_seq = self._result_metadata_value(restart_obs.operation_result, "SequenceNumber")
            seq_advanced = False
            if not isinstance(before_seq, bool) and not isinstance(after_seq, bool):
                try:
                    seq_advanced = int(after_seq) > int(before_seq)
                except (TypeError, ValueError):
                    seq_advanced = False

            both_omit_optional_step_id = (
                inconclusive
                and "StepId is unavailable" in evidence_error
                and not before_step_id
                and not after_step_id
                and seq_advanced
            )
            if not same_step and not both_omit_optional_step_id:
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"Post-reset step-1 verification failed: {evidence_error}",
                    method="ResetJoiningProcess",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                    inconclusive=inconclusive,
                    execution_outcome="inconclusive" if inconclusive else "failed",
                    reason_code="reset_step_evidence_unavailable" if inconclusive else "reset_step_evidence_invalid",
                )

            from helpers.result_collector import get_result_id

            completion = await self._continue_owned_process(
                collector,
                jpm_node,
                piu,
                target_process,
                self._process_list_fingerprint(processes),
                starts_issued=2,
                results_confirmed=2,
                after_result_count=reset_boundary,
                ownership_after_result_count=restart_boundary,
                required_result_ids=frozenset({get_result_id(restart_obs.operation_result)}),
                counter_virtual_station_uri=reset_station,
            )
            return replace(completion, method="ResetJoiningProcess", trigger_mode="start_selected_joining")

    async def trigger_abort_job(self) -> TriggerOutcome:
        """Trigger compound multi-step job and issue AbortJoiningProcess."""
        approved = set(self._profile.workflow_execution.approved_workflows)
        if "remote_abort_job" not in approved:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="Workflow 'remote_abort_job' is not listed in workflows.approved.",
                method="AbortJoiningProcess",
                trigger_mode="start_selected_joining",
            )
        if not self._profile.cu_execution.extension_fields.get("allow_destructive_methods", False):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="Workflow 'remote_abort_job' lacks runtime destructive-operation approval.",
                method="AbortJoiningProcess",
                trigger_mode="start_selected_joining",
            )
        cache_key = (self._profile.target.endpoint, self._profile.source_path, "remote_abort_job")
        if (
            self._profile.workflow_execution.evidence_reuse.enabled
            and cache_key in _RUN_SCOPED_EVIDENCE._intervention_workflow_outcomes
        ):
            return replace(_RUN_SCOPED_EVIDENCE._intervention_workflow_outcomes[cache_key], evidence_reused=True)
        outcome = await self._run_abort_workflow()
        if outcome.triggered and self._profile.workflow_execution.evidence_reuse.enabled:
            _RUN_SCOPED_EVIDENCE._intervention_workflow_outcomes[cache_key] = outcome
        return outcome

    async def trigger_reset_job(self) -> TriggerOutcome:
        """Trigger ResetJoiningProcess on the selected compound process."""
        approved = set(self._profile.workflow_execution.approved_workflows)
        if "remote_reset_job" not in approved:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="Workflow 'remote_reset_job' is not listed in workflows.approved.",
                method="ResetJoiningProcess",
                trigger_mode="start_selected_joining",
            )
        if not self._profile.cu_execution.extension_fields.get("allow_destructive_methods", False):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="Workflow 'remote_reset_job' lacks runtime destructive-operation approval.",
                method="ResetJoiningProcess",
                trigger_mode="start_selected_joining",
            )
        cache_key = (self._profile.target.endpoint, self._profile.source_path, "remote_reset_job")
        if (
            self._profile.workflow_execution.evidence_reuse.enabled
            and cache_key in _RUN_SCOPED_EVIDENCE._intervention_workflow_outcomes
        ):
            return replace(_RUN_SCOPED_EVIDENCE._intervention_workflow_outcomes[cache_key], evidence_reused=True)
        outcome = await self._run_reset_workflow()
        if outcome.triggered and self._profile.workflow_execution.evidence_reuse.enabled:
            _RUN_SCOPED_EVIDENCE._intervention_workflow_outcomes[cache_key] = outcome
        return outcome

    async def trigger_bulk_results(
        self,
        result_type: int,
        include_traces: bool,
        from_seq: int,
        to_seq: int,
        min_duration_ms: int = 100,
        update_vars: bool = True,
    ) -> TriggerOutcome:
        """Not supported — target_server triggers do not support bulk-sequence generation."""
        return TargetServerTriggerOutcome(
            triggered=False,
            skip_reason=(
                "Bulk result generation is not supported via StartSelectedJoining. "
                "Use the simulator trigger for bulk sequence tests."
            ),
            method="StartSelectedJoining",
            trigger_mode="start_selected_joining",
        )


# ---------------------------------------------------------------------------
# ManualResultTrigger
# ---------------------------------------------------------------------------


class ManualResultTrigger(ResultTrigger):
    """Observe-and-wait result trigger for physical/operator-driven joining operations.

    Does not call any OPC UA method to start a joining operation.  Instead,
    records operator instructions in the skip_reason so guided-mode runs can
    display what action is needed.  In automated mode all calls return
    triggered=False immediately.

    Args:
        profile:         Loaded target_server profile.
        allow_waiting:   When True (guided/manual mode), a future version may
                         support prompting and waiting. Currently always returns
                         manual_required skip reason regardless.
    """

    @property
    def is_simulator(self) -> bool:
        return False

    @property
    def active_result_timeout_s(self) -> float:
        """This trigger never starts an operation — observation budget only."""
        return self._profile.triggers.result.timeout_seconds

    @property
    def passive_observation_timeout_s(self) -> float:
        """Operator-observation budget from the profile result trigger config."""
        return self._profile.triggers.result.timeout_seconds

    def __init__(self, profile: TargetServerCuProfile, allow_waiting: bool = False) -> None:
        self._profile = profile
        self._allow_waiting = allow_waiting

    def _manual_skip(self, context: str = "joining operation") -> TargetServerTriggerOutcome:
        timeout = self._profile.triggers.result.timeout_seconds
        return TargetServerTriggerOutcome(
            triggered=False,
            skip_reason=(
                f"Manual trigger required for {context}. "
                f"Please physically trigger the joining tool within {timeout:.0f}s. "
                "Run in guided mode (--mode guided) to enable operator prompts."
            ),
            method="ManualTrigger",
            trigger_mode="manual_trigger",
        )

    async def trigger_single(self, result_type: int, include_traces: bool = False) -> TriggerOutcome:
        return self._manual_skip("single result")

    async def trigger_batch_or_sync(
        self,
        classification: int,
        num_children: int = 3,
        include_traces: bool = False,
        send_as_refs: bool = False,
    ) -> TriggerOutcome:
        return self._manual_skip("batch/sync result")

    async def trigger_job(self, send_as_refs: bool = False) -> TriggerOutcome:
        return self._manual_skip("job result")

    async def trigger_bulk_results(
        self,
        result_type: int,
        include_traces: bool,
        from_seq: int,
        to_seq: int,
        min_duration_ms: int = 100,
        update_vars: bool = True,
    ) -> TriggerOutcome:
        return self._manual_skip("bulk result sequence")

    async def trigger_abort_job(self) -> TriggerOutcome:
        return self._manual_skip("abort job workflow")

    async def trigger_reset_job(self) -> TriggerOutcome:
        return self._manual_skip("reset job workflow")


# ---------------------------------------------------------------------------
# ManualEventTrigger
# ---------------------------------------------------------------------------


class WorkflowActionEventTrigger(EventTrigger):
    """Map event-test requests to explicitly approved physical causes."""

    def __init__(
        self,
        client: Any,
        joining_system_node: Any,
        ns_app: int,
        profile: TargetServerCuProfile,
        *,
        ns_ijt: int | None = None,
        ns_di: int | None = None,
        subscription_client: Any = None,
    ) -> None:
        self._profile = profile
        self._driver = StartSelectedJoiningResultTrigger(
            client,
            joining_system_node,
            ns_app,
            profile,
            ns_ijt=ns_ijt,
            ns_di=ns_di,
            subscription_client=subscription_client,
        )

    @property
    def is_simulator(self) -> bool:
        return False

    @property
    def active_event_timeout_s(self) -> float:
        return self._profile.triggers.event.timeout_seconds

    @property
    def passive_observation_timeout_s(self) -> float:
        return self._profile.triggers.event.timeout_seconds

    def _configured_action(self, cu_key: str, required_workflow: str) -> TriggerOutcome | None:
        configured = self._profile.triggers.event.actions.get(cu_key)
        if configured == required_workflow:
            return None
        return TriggerOutcome(
            triggered=False,
            skip_reason=(
                f"Event action '{cu_key}' must map to approved workflow '{required_workflow}', got {configured!r}."
            ),
            method="WorkflowActionEventTrigger",
        )

    async def trigger_event(self, event_type: int, count: int = 1) -> TriggerOutcome:
        from helpers.namespaces import SimulateEventType

        if count != 1:
            return TriggerOutcome(
                triggered=False,
                skip_reason="Physical workflow event actions support exactly one bounded cause.",
                method="WorkflowActionEventTrigger",
            )
        if event_type == SimulateEventType.PROGRAM_SELECTED:
            invalid = self._configured_action("select_process_event", "select_process_event")
            return invalid or await self._driver.trigger_select_process_event()
        if event_type in {SimulateEventType.ASSET_ENABLED, SimulateEventType.ASSET_DISABLED}:
            invalid = self._configured_action(
                "asset_enable_state_event",
                "asset_enable_state_event",
            )
            return invalid or await self._driver.trigger_asset_enable_event(
                event_type == SimulateEventType.ASSET_ENABLED
            )
        if event_type in {
            SimulateEventType.RECEIVED_ENTITY,
            SimulateEventType.ACCEPTED_ENTITY,
            SimulateEventType.RECEIVED_AND_ACCEPTED,
        }:
            workflow = self._profile.triggers.event.actions.get("identifiers_event")
            if workflow not in {
                "structured_identifier_round_trip",
                "text_identifier_round_trip",
            }:
                return TriggerOutcome(
                    triggered=False,
                    skip_reason="identifiers_event has no approved identifier round-trip action.",
                    method="WorkflowActionEventTrigger",
                )
            return await self._driver.run_identifier_round_trip(
                structured=workflow == "structured_identifier_round_trip"
            )
        return TriggerOutcome(
            triggered=False,
            skip_reason=f"No deterministic physical action is configured for event type {event_type}.",
            method="WorkflowActionEventTrigger",
        )

    async def trigger_bulk_events(
        self,
        event_type: int,
        count: int,
        from_seq: int,
        to_seq: int,
        min_duration_ms: int = 100,
    ) -> TriggerOutcome:
        return TriggerOutcome(
            triggered=False,
            skip_reason="Bulk physical event generation is not authorized.",
            method="WorkflowActionEventTrigger",
        )

    async def trigger_condition(self, event_type: int) -> TriggerOutcome:
        return TriggerOutcome(
            triggered=False,
            skip_reason="No deterministic physical condition action is configured.",
            method="WorkflowActionEventTrigger",
        )


class ManualEventTrigger(EventTrigger):
    """Observe-and-wait event trigger for target_server-natural events.

    Does not call simulator helper methods.  Returns manual_required skip
    reasons so guided-mode runners can prompt the operator appropriately.

    Args:
        profile:      Loaded target_server profile.
        allow_waiting: When True (guided mode), may support waiting in future.
    """

    @property
    def is_simulator(self) -> bool:
        return False

    @property
    def active_event_timeout_s(self) -> float:
        """This trigger never fires an event — observation budget only."""
        return self._profile.triggers.event.timeout_seconds

    @property
    def passive_observation_timeout_s(self) -> float:
        """Operator-observation budget from the profile event trigger config."""
        return self._profile.triggers.event.timeout_seconds

    def __init__(self, profile: TargetServerCuProfile, allow_waiting: bool = False) -> None:
        self._profile = profile
        self._allow_waiting = allow_waiting

    def _manual_skip(self, event_context: str = "event") -> TriggerOutcome:
        timeout = self._profile.triggers.event.timeout_seconds
        return TriggerOutcome(
            triggered=False,
            skip_reason=(
                f"Manual trigger required for {event_context}. "
                f"Expected to observe natural target_server event within {timeout:.0f}s. "
                "Run in guided mode (--mode guided) to enable operator prompts."
            ),
            method="ManualEventTrigger",
        )

    async def trigger_event(self, event_type: int, count: int = 1) -> TriggerOutcome:
        return self._manual_skip("event")

    async def trigger_bulk_events(
        self,
        event_type: int,
        count: int,
        from_seq: int,
        to_seq: int,
        min_duration_ms: int = 100,
    ) -> TriggerOutcome:
        return self._manual_skip("bulk events")

    async def trigger_condition(self, event_type: int) -> TriggerOutcome:
        return self._manual_skip("condition")


# ---------------------------------------------------------------------------
# Simulator-backed trigger composition (triggers.*.mode = simulate_methods)
# ---------------------------------------------------------------------------

SIMULATE_METHODS_MODE = "simulate_methods"


class SplitEventTrigger(EventTrigger):
    """Serve events from one adapter and conditions from another.

    Needed when a manifest declares different ``triggers.event.mode`` and
    ``triggers.condition.mode`` values - for example natural (observed) events
    but simulator-generated conditions. Each call is forwarded unchanged so the
    underlying adapters keep their own semantics and timeouts.
    """

    def __init__(self, event_trigger: EventTrigger, condition_trigger: EventTrigger) -> None:
        self._events = event_trigger
        self._conditions = condition_trigger

    @property
    def is_simulator(self) -> bool:
        return self._events.is_simulator

    @property
    def active_event_timeout_s(self) -> float:
        return self._events.active_event_timeout_s

    @property
    def passive_observation_timeout_s(self) -> float:
        return self._events.passive_observation_timeout_s

    async def trigger_event(self, event_type: int, count: int = 1) -> TriggerOutcome:
        return await self._events.trigger_event(event_type, count)

    async def trigger_bulk_events(
        self,
        event_type: int,
        count: int,
        from_seq: int,
        to_seq: int,
        min_duration_ms: int = 100,
    ) -> TriggerOutcome:
        return await self._events.trigger_bulk_events(event_type, count, from_seq, to_seq, min_duration_ms)

    async def trigger_condition(self, event_type: int) -> TriggerOutcome:
        return await self._conditions.trigger_condition(event_type)


def _require_simulator_folder(node: Any, *, browse_name: str, mode_path: str, profile: TargetServerCuProfile) -> Any:
    """Return *node*, or raise a configuration error when the helper is absent.

    A manifest claiming ``simulate_methods`` states that the SUT exposes the
    simulator helper methods. Silently degrading to an External trigger would
    turn that false claim into a pile of skips instead of a visible
    configuration error, so the run stops here instead.
    """
    if node is not None:
        return node
    raise TargetServerTriggerConfigurationError(
        f"SUT manifest '{profile.profile_name}' sets {mode_path} = '{SIMULATE_METHODS_MODE}', but the "
        f"'{browse_name}' simulator helper folder was not found under JoiningSystem/Simulations on this "
        "server. Point the manifest at the simulator, or change the trigger mode to one this server "
        "supports (start_selected_joining, manual_trigger, observe_only, or none)."
    )


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def make_target_server_result_trigger(
    client: Any,
    joining_system_node: Any,
    ns_app: int,
    profile: TargetServerCuProfile,
    *,
    ns_ijt: int | None = None,
    ns_di: int | None = None,
    subscription_client: Any = None,
    allow_waiting: bool = False,
    simulate_results_folder: Any = None,
) -> ResultTrigger:
    """Return the appropriate result trigger based on the profile trigger config.

    Selection logic:
      - If OPCUA_TRIGGER_CLASS is set, instantiate that class (backward compat).
      - If trigger mode is 'simulate_methods' → SimulatorResultTrigger, using the
        SimulateResults folder discovered through the shared simulator lookup.
      - If trigger mode is 'start_selected_joining' → StartSelectedJoiningResultTrigger.
      - If trigger mode is 'manual_trigger' → ManualResultTrigger.
      - Otherwise → ExternalResultTrigger (existing no-op fallback).

    Args:
        client:               Active asyncua Client.
        joining_system_node:  JoiningSystem OPC UA Node.
        ns_app:               Application namespace index.
        profile:              Loaded target_server profile.
        ns_ijt:               IJT Base namespace index, resolved lazily when omitted.
        ns_di:                DI namespace index, resolved lazily when omitted.
        allow_waiting:        Enable waiting behavior for guided/manual modes.
        simulate_results_folder: SimulateResults folder node, required for
                              'simulate_methods'. Use
                              :func:`build_target_server_result_trigger` to have
                              it discovered automatically.

    Raises:
        TargetServerTriggerConfigurationError: when the manifest claims
            'simulate_methods' but the simulator helper folder is unavailable.
    """

    # Preserve existing OPCUA_TRIGGER_CLASS override mechanism
    def configured(trigger: ResultTrigger) -> ResultTrigger:
        trigger.associated_entity_expectations = profile.workflow_execution.expected_results.associated_entities
        return trigger

    override_class = os.environ.get("OPCUA_TRIGGER_CLASS")
    if override_class:
        import importlib

        module_name, class_name = override_class.rsplit(".", 1)
        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)
        logger.info("Using OPCUA_TRIGGER_CLASS override: %s", override_class)
        return configured(cls(client, joining_system_node, ns_app))

    mode = profile.triggers.result.mode

    if mode == SIMULATE_METHODS_MODE:
        folder = _require_simulator_folder(
            simulate_results_folder,
            browse_name=BN.SIMULATE_RESULTS_FOLDER,
            mode_path="triggers.result.mode",
            profile=profile,
        )
        logger.debug("TargetServer result trigger: SimulatorResultTrigger")
        return configured(SimulatorResultTrigger(client, folder, ns_app))

    if mode == "start_selected_joining":
        logger.debug("TargetServer result trigger: StartSelectedJoiningResultTrigger")
        return StartSelectedJoiningResultTrigger(
            client,
            joining_system_node,
            ns_app,
            profile,
            ns_ijt=ns_ijt,
            ns_di=ns_di,
            subscription_client=subscription_client,
        )

    if mode == "manual_trigger":
        logger.debug("TargetServer result trigger: ManualResultTrigger (allow_waiting=%s)", allow_waiting)
        return configured(ManualResultTrigger(profile, allow_waiting=allow_waiting))

    logger.debug("TargetServer result trigger: ExternalResultTrigger (mode=%s)", mode)
    return configured(ExternalResultTrigger())


def make_target_server_event_trigger(
    profile: TargetServerCuProfile,
    *,
    allow_waiting: bool = False,
    client: Any = None,
    ns_app: int = 0,
    joining_system_node: Any = None,
    ns_ijt: int | None = None,
    ns_di: int | None = None,
    simulate_events_folder: Any = None,
    subscription_client: Any = None,
) -> EventTrigger:
    """Return the appropriate event trigger based on the profile trigger config.

    Selection logic (applied to ``triggers.event.mode`` and
    ``triggers.condition.mode`` independently):
      - 'simulate_methods' → SimulatorEventTrigger on the
        SimulateEventsAndConditions folder.
      - 'manual_trigger' → ManualEventTrigger.
      - Otherwise → ExternalEventTrigger (existing no-op fallback).

    When exactly one of the two modes is ``simulate_methods`` the two adapters are
    combined by :class:`SplitEventTrigger`, so conditions can be simulated while
    events are only observed (or vice versa).

    Note: 'observe_only' mode does not need a trigger class because events
    arrive naturally.  The runner subscribes before the workflow step and
    waits passively.

    Args:
        profile:       Loaded target_server profile.
        allow_waiting: Enable waiting behavior for guided/manual modes.
        client:        Active asyncua Client, required for 'simulate_methods'.
        ns_app:        Application namespace index, required for 'simulate_methods'.
        simulate_events_folder: SimulateEventsAndConditions folder node, required
                       for 'simulate_methods'. Use
                       :func:`build_target_server_event_trigger` to have it
                       discovered automatically.

    Raises:
        TargetServerTriggerConfigurationError: when the manifest claims
            'simulate_methods' but the simulator helper folder is unavailable.
    """
    event_mode = profile.triggers.event.mode
    condition_mode = profile.triggers.condition.mode

    def _adapter(mode: str, mode_path: str) -> EventTrigger:
        if mode == SIMULATE_METHODS_MODE:
            folder = _require_simulator_folder(
                simulate_events_folder,
                browse_name=BN.SIMULATE_EVENTS_AND_CONDITIONS,
                mode_path=mode_path,
                profile=profile,
            )
            logger.debug("TargetServer event trigger: SimulatorEventTrigger (%s)", mode_path)
            return SimulatorEventTrigger(client, folder, ns_app)
        if mode == "manual_trigger":
            logger.debug("TargetServer event trigger: ManualEventTrigger (allow_waiting=%s)", allow_waiting)
            return ManualEventTrigger(profile, allow_waiting=allow_waiting)
        if mode == "workflow_actions":
            logger.debug("TargetServer event trigger: WorkflowActionEventTrigger")
            return WorkflowActionEventTrigger(
                client,
                joining_system_node,
                ns_app,
                profile,
                ns_ijt=ns_ijt,
                ns_di=ns_di,
                subscription_client=subscription_client,
            )
        logger.debug("TargetServer event trigger: ExternalEventTrigger (mode=%s)", mode)
        return ExternalEventTrigger()

    events = _adapter(event_mode, "triggers.event.mode")
    # Only a simulate_methods mismatch needs splitting: the other modes all share
    # one adapter whose events and conditions behave identically.
    if (event_mode == SIMULATE_METHODS_MODE) == (condition_mode == SIMULATE_METHODS_MODE):
        return events
    return SplitEventTrigger(events, _adapter(condition_mode, "triggers.condition.mode"))


async def build_target_server_result_trigger(
    client: Any,
    joining_system_node: Any,
    ns_app: int | None,
    profile: TargetServerCuProfile,
    *,
    ns_ijt: int | None = None,
    ns_di: int | None = None,
    subscription_client: Any = None,
    allow_waiting: bool = False,
) -> ResultTrigger:
    """Discover any needed simulator helper node, then build the result trigger.

    This is the entry point used by the pytest fixtures: it resolves the
    SimulateResults folder through :func:`helpers.trigger.find_simulation_child`,
    the same lookup the default (non-manifest) simulator fixture path uses.
    """
    folder = None
    if profile.triggers.result.mode == SIMULATE_METHODS_MODE:
        folder = await find_simulation_child(joining_system_node, ns_app, BN.SIMULATE_RESULTS_FOLDER)
    return make_target_server_result_trigger(
        client,
        joining_system_node,
        ns_app or 0,
        profile,
        ns_ijt=ns_ijt,
        ns_di=ns_di,
        subscription_client=subscription_client,
        allow_waiting=allow_waiting,
        simulate_results_folder=folder,
    )


async def build_target_server_event_trigger(
    client: Any,
    joining_system_node: Any,
    ns_app: int | None,
    profile: TargetServerCuProfile,
    *,
    ns_ijt: int | None = None,
    ns_di: int | None = None,
    allow_waiting: bool = False,
    subscription_client: Any = None,
) -> EventTrigger:
    """Discover any needed simulator helper node, then build the event trigger.

    Resolves the SimulateEventsAndConditions folder through
    :func:`helpers.trigger.find_simulation_child` so a manifest-driven run finds
    exactly the nodes the default simulator fixture path finds.
    """
    folder = None
    if SIMULATE_METHODS_MODE in {profile.triggers.event.mode, profile.triggers.condition.mode}:
        folder = await find_simulation_child(joining_system_node, ns_app, BN.SIMULATE_EVENTS_AND_CONDITIONS)
    return make_target_server_event_trigger(
        profile,
        allow_waiting=allow_waiting,
        client=client,
        ns_app=ns_app or 0,
        joining_system_node=joining_system_node,
        ns_ijt=ns_ijt,
        ns_di=ns_di,
        simulate_events_folder=folder,
        subscription_client=subscription_client,
    )
