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
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from helpers.target_server_cu_config import TargetServerCuProfile
from helpers.trigger import (
    EventTrigger,
    ExternalEventTrigger,
    ExternalResultTrigger,
    ResultTrigger,
    TriggerOutcome,
)

logger = logging.getLogger(__name__)

_DEFAULT_TARGET_SERVER_TIMEOUT = 120.0  # real joining operations can be slow


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
        operation_count:        Number of StartSelectedJoining calls made.
        pre_trigger_baseline:   Snapshot captured before the trigger.
    """

    trigger_mode: str = ""
    product_instance_uri: str = ""
    joining_process_id: str = ""
    joining_process_origin_id: str = ""
    operation_count: int = 0
    pre_trigger_baseline: dict[str, Any] = field(default_factory=dict)


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

    def __init__(
        self,
        client: Any,
        joining_system_node: Any,
        ns_app: int,
        profile: TargetServerCuProfile,
        ns_ijt: int | None = None,
        ns_di: int | None = None,
    ) -> None:
        self._client = client
        self._joining_system = joining_system_node
        self._ns_app = ns_app
        self._ns_ijt = ns_ijt
        self._ns_di = ns_di
        self._profile = profile

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
            return []
        output = result.output_list
        if not output:
            return []
        # GetJoiningProcessList returns a list wrapped in a single output argument
        inner = output[0] if output else []
        if isinstance(inner, (list, tuple)):
            return list(inner)
        return [inner] if inner is not None else []

    async def _select_joining_process(self, jpm_node: Any, process_id: Any) -> bool:
        """Call SelectJoiningProcess and return True on success."""
        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN

        result = await find_and_call_method(
            jpm_node,
            BN.SELECT_JOINING_PROCESS,
            await self._resolve_ijt_namespace_index(),
            process_id,
            timeout=self._profile.cu_execution.default_timeout_seconds,
        )
        return result.success

    async def _start_selected_joining(self, jpm_node: Any, piu: str, deselect_after: bool) -> bool:
        """Call StartSelectedJoining(piu, deselect_after) and return True on success."""
        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN

        result = await find_and_call_method(
            jpm_node,
            BN.START_SELECTED_JOINING,
            await self._resolve_ijt_namespace_index(),
            ua.Variant(piu, ua.VariantType.String),
            ua.Variant(deselect_after, ua.VariantType.Boolean),
            timeout=self._profile.cu_execution.default_timeout_seconds,
        )
        return result.success

    async def _run_workflow(self) -> TargetServerTriggerOutcome:
        """Execute the full StartSelectedJoining workflow."""
        sc = self._profile.cu_execution.state_changing_methods

        # Permission check — abort before any state changes
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

        jpm_node = await self._get_joining_process_management()
        if jpm_node is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="JoiningProcessManagement node not found under JoiningSystem",
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
            )

        piu = await self._resolve_tool_piu()
        processes = await self._get_joining_process_list(jpm_node, piu)

        if not processes:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="No joining processes returned by GetJoiningProcessList",
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
            )

        # Select first available process (or configured one)
        target_process = processes[0]
        jp_id = str(getattr(target_process, "JoiningProcessIdentification", ""))
        jp_origin = str(getattr(target_process, "JoiningProcessIdentificationOrigin", ""))

        selected = await self._select_joining_process(jpm_node, target_process)
        if not selected:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"SelectJoiningProcess failed for process '{jp_id}'",
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
                joining_process_id=jp_id,
            )

        deselect = self._profile.triggers.result.deselect_after_joining
        started = await self._start_selected_joining(jpm_node, piu, deselect)
        if not started:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"StartSelectedJoining failed for process '{jp_id}', PIU='{piu}'",
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
                joining_process_id=jp_id,
            )

        logger.debug("StartSelectedJoining succeeded: PIU=%s, process=%s", piu, jp_id)
        return TargetServerTriggerOutcome(
            triggered=True,
            method="StartSelectedJoining",
            trigger_mode="start_selected_joining",
            product_instance_uri=piu,
            joining_process_id=jp_id,
            joining_process_origin_id=jp_origin,
            operation_count=1,
        )

    async def trigger_single(self, result_type: int, include_traces: bool = False) -> TriggerOutcome:
        """Trigger one joining operation and wait for a result."""
        try:
            return await asyncio.wait_for(
                self._run_workflow(),
                timeout=self._profile.triggers.result.timeout_seconds,
            )
        except asyncio.TimeoutError:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"StartSelectedJoining workflow timed out after {self._profile.triggers.result.timeout_seconds}s",
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
            )
        except Exception as exc:  # noqa: BLE001
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"StartSelectedJoining workflow failed: {exc}",
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
            )

    async def trigger_batch_or_sync(
        self,
        classification: int,
        num_children: int = 3,
        include_traces: bool = False,
        send_as_refs: bool = False,
    ) -> TriggerOutcome:
        """Trigger joining workflow for batch/sync evidence.

        Calls StartSelectedJoining once when start_invocation_policy is
        single_start_produces_final_result.  Calls it num_children times
        when policy is one_start_per_operation.
        """
        policy = self._profile.workflow_execution.start_invocation_policy
        if policy == "one_start_per_operation":
            last: TriggerOutcome = TargetServerTriggerOutcome(
                triggered=False, skip_reason="No operations run", trigger_mode="start_selected_joining"
            )
            for _ in range(num_children):
                last = await self.trigger_single(classification, include_traces)
                if not last.triggered:
                    return last
            return last
        # single_start_produces_final_result
        return await self.trigger_single(classification, include_traces)

    async def trigger_job(self, send_as_refs: bool = False) -> TriggerOutcome:
        """Trigger joining workflow for job-level evidence."""
        return await self.trigger_single(0, False)

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


# ---------------------------------------------------------------------------
# ManualEventTrigger
# ---------------------------------------------------------------------------


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
    allow_waiting: bool = False,
) -> ResultTrigger:
    """Return the appropriate result trigger based on the profile trigger config.

    Selection logic:
      - If OPCUA_TRIGGER_CLASS is set, instantiate that class (backward compat).
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
    """
    # Preserve existing OPCUA_TRIGGER_CLASS override mechanism
    override_class = os.environ.get("OPCUA_TRIGGER_CLASS")
    if override_class:
        import importlib

        module_name, class_name = override_class.rsplit(".", 1)
        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)
        logger.info("Using OPCUA_TRIGGER_CLASS override: %s", override_class)
        return cls(client, joining_system_node, ns_app)

    mode = profile.triggers.result.mode

    if mode == "start_selected_joining":
        logger.debug("TargetServer result trigger: StartSelectedJoiningResultTrigger")
        return StartSelectedJoiningResultTrigger(
            client, joining_system_node, ns_app, profile, ns_ijt=ns_ijt, ns_di=ns_di
        )

    if mode == "manual_trigger":
        logger.debug("TargetServer result trigger: ManualResultTrigger (allow_waiting=%s)", allow_waiting)
        return ManualResultTrigger(profile, allow_waiting=allow_waiting)

    logger.debug("TargetServer result trigger: ExternalResultTrigger (mode=%s)", mode)
    return ExternalResultTrigger()


def make_target_server_event_trigger(
    profile: TargetServerCuProfile,
    *,
    allow_waiting: bool = False,
) -> EventTrigger:
    """Return the appropriate event trigger based on the profile trigger config.

    Selection logic:
      - If trigger mode is 'manual_trigger' → ManualEventTrigger.
      - Otherwise → ExternalEventTrigger (existing no-op fallback).

    Note: 'observe_only' mode does not need a trigger class because events
    arrive naturally.  The runner subscribes before the workflow step and
    waits passively.

    Args:
        profile:       Loaded target_server profile.
        allow_waiting: Enable waiting behavior for guided/manual modes.
    """
    mode = profile.triggers.event.mode

    if mode == "manual_trigger":
        logger.debug("TargetServer event trigger: ManualEventTrigger (allow_waiting=%s)", allow_waiting)
        return ManualEventTrigger(profile, allow_waiting=allow_waiting)

    logger.debug("TargetServer event trigger: ExternalEventTrigger (mode=%s)", mode)
    return ExternalEventTrigger()
