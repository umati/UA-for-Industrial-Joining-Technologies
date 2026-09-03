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
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Any

from helpers.namespaces import (
    BN,
    JoiningProcessClassification,
    ResultClassification,
    joining_process_classification_value,
    parse_joining_process_classification,
    result_classification_value,
)
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
    candidate_process_ids: tuple[str, ...] = ()
    proven_process_ids: tuple[str, ...] = ()
    rejected_process_ids: tuple[str, ...] = ()
    result_progression: Any | None = None
    claim_mismatch: bool = False
    expected_event_entity_ids: tuple[str, ...] = ()


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


@dataclass(frozen=True)
class WorkflowEvidenceRecord:
    """Immutable run-scoped result progression with capture provenance."""

    key: WorkflowEvidenceKey
    progression: Any
    captured_monotonic: float


class RunScopedEvidenceStore:
    """In-memory evidence store; records never cross a Python test run."""

    def __init__(self) -> None:
        self._records: dict[WorkflowEvidenceKey, WorkflowEvidenceRecord] = {}

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
        self._subscription_client = subscription_client
        self._last_method_failure = ""
        self._pending_evidence_key: WorkflowEvidenceKey | None = None

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
            self._last_method_failure = str(result.error or "OPC UA service call failed")
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
        )
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
        policy = self._profile.cu_execution.extension_fields.get(
            "enable_asset_policy",
            "when_disabled",
        )
        if policy == "always":
            return await self._enable_tool(piu)
        if await self._read_tool_enabled(piu) is True:
            return True
        return await self._enable_tool(piu)

    async def trigger_select_process_event(self) -> TargetServerTriggerOutcome:
        """Invoke exactly one SelectJoiningProcess action after the caller subscribes."""
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
        process = self._choose_joining_process(processes)
        if process is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="No joining process matched the configured event action selection.",
                method="SelectJoiningProcess",
                trigger_mode="workflow_actions",
                product_instance_uri=piu,
            )
        selected = await self._select_joining_process(jpm_node, process, piu)
        process_id = self._process_field(
            process,
            "JoiningProcessId",
            "JoiningProcessIdentification",
            "Id",
        )
        return TargetServerTriggerOutcome(
            triggered=selected,
            skip_reason=None if selected else f"SelectJoiningProcess failed: {self._last_method_failure}",
            method="SelectJoiningProcess",
            trigger_mode="workflow_actions",
            product_instance_uri=piu,
            joining_process_id=process_id,
            expected_event_entity_ids=(process_id,) if selected and process_id else (),
        )

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
        changed = False
        failure = ""
        try:
            changed = await self._set_tool_enabled(piu, enabled)
            failure = self._last_method_failure
        finally:
            restored = await self._set_tool_enabled(piu, True)
            restore_failure = self._last_method_failure

        if not restored:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"CRITICAL: final EnableAsset(true) restoration failed: {restore_failure}",
                method="EnableAsset",
                trigger_mode="workflow_actions",
                product_instance_uri=piu,
            )
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

        method_set = await self._get_asset_method_set()
        piu = await self._resolve_tool_piu()
        if method_set is None or not piu:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="AssetManagement MethodSet or Tool ProductInstanceUri is unavailable.",
                method=method_name,
                trigger_mode="identifier_round_trip",
            )

        owned_value = f"IJT-TEST-{uuid.uuid4().hex.upper()}"
        identifier_name = owned_value
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
            entity.Description = "Run-owned IJT conformance identifier"
            entity.EntityId = owned_value
            entity.EntityOriginId = ""
            entity.IsExternal = True
            entity.EntityType = 20
            send_payload = ua.Variant([entity], ua.VariantType.ExtensionObject)
        else:
            send_payload = ua.Variant([owned_value], ua.VariantType.String)

        piu_arg = ua.Variant(piu, ua.VariantType.String)
        names_arg = ua.Variant([identifier_name], ua.VariantType.String)
        cleanup_verified = False
        execution_started = False
        failure = ""
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
            )
            if not self._method_succeeded(method_name, sent):
                failure = f"{method_name} failed: {self._last_method_failure}"
            if not failure:
                read_back = await find_and_call_method(
                    method_set,
                    BN.GET_IDENTIFIERS,
                    await self._resolve_ijt_namespace_index(),
                    piu_arg,
                    names_arg,
                    timeout=self._profile.cu_execution.default_timeout_seconds,
                )
                if not read_back.success or not contains_identifier(read_back.output_list, owned_value):
                    failure = f"GetIdentifiers did not return the run-owned value {owned_value!r}."
            if not failure:
                reset = await find_and_call_method(
                    method_set,
                    BN.RESET_IDENTIFIERS,
                    await self._resolve_ijt_namespace_index(),
                    piu_arg,
                    names_arg,
                    ua.Variant(False, ua.VariantType.Boolean),
                    ua.Variant(False, ua.VariantType.Boolean),
                    timeout=self._profile.cu_execution.default_timeout_seconds,
                    target_server_authorized=True,
                )
                if not self._method_succeeded(BN.RESET_IDENTIFIERS, reset):
                    failure = f"Selective ResetIdentifiers failed: {self._last_method_failure}"
            if not failure:
                after = await find_and_call_method(
                    method_set,
                    BN.GET_IDENTIFIERS,
                    await self._resolve_ijt_namespace_index(),
                    piu_arg,
                    names_arg,
                    timeout=self._profile.cu_execution.default_timeout_seconds,
                )
                cleanup_verified = after.success and not contains_identifier(after.output_list, owned_value)
                if not cleanup_verified:
                    failure = f"Run-owned identifier {owned_value!r} remained after selective cleanup."
        finally:
            if not cleanup_verified:
                final_reset = await find_and_call_method(
                    method_set,
                    BN.RESET_IDENTIFIERS,
                    await self._resolve_ijt_namespace_index(),
                    piu_arg,
                    names_arg,
                    ua.Variant(False, ua.VariantType.Boolean),
                    ua.Variant(False, ua.VariantType.Boolean),
                    timeout=self._profile.cu_execution.default_timeout_seconds,
                    target_server_authorized=True,
                )
                reset_succeeded = self._method_succeeded(BN.RESET_IDENTIFIERS, final_reset)
                if reset_succeeded:
                    final_after = await find_and_call_method(
                        method_set,
                        BN.GET_IDENTIFIERS,
                        await self._resolve_ijt_namespace_index(),
                        piu_arg,
                        names_arg,
                        timeout=self._profile.cu_execution.default_timeout_seconds,
                    )
                    cleanup_verified = final_after.success and not contains_identifier(
                        final_after.output_list,
                        owned_value,
                    )
                if not reset_succeeded:
                    failure = f"{failure} Final selective cleanup failed: {self._last_method_failure}".strip()
                elif not cleanup_verified:
                    failure = f"{failure} Final selective cleanup could not be verified.".strip()

        return TargetServerTriggerOutcome(
            triggered=not failure and cleanup_verified,
            skip_reason=failure or None,
            method=method_name,
            trigger_mode="identifier_round_trip",
            product_instance_uri=piu,
            claim_mismatch=execution_started and bool(failure),
            expected_event_entity_ids=(owned_value,) if not failure and cleanup_verified else (),
        )

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

        ns_ijt = await self._resolve_ijt_namespace_index()
        piu_arg = ua.Variant(piu, ua.VariantType.String)
        empty_names = ua.Variant([], ua.VariantType.String)
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
        )
        if not self._method_succeeded(BN.RESET_IDENTIFIERS, reset):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"ResetAll ResetIdentifiers failed: {self._last_method_failure}",
                method=BN.RESET_IDENTIFIERS,
                trigger_mode="reset_all_identifiers",
                product_instance_uri=piu,
                claim_mismatch=True,
            )

        after = await find_and_call_method(
            method_set,
            BN.GET_IDENTIFIERS,
            ns_ijt,
            piu_arg,
            empty_names,
            timeout=self._profile.cu_execution.default_timeout_seconds,
        )
        if not after.success or any(after.output_list):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="ResetAll completed, but GetIdentifiers did not verify an empty identifier state.",
                method=BN.RESET_IDENTIFIERS,
                trigger_mode="reset_all_identifiers",
                product_instance_uri=piu,
                claim_mismatch=True,
            )
        return TargetServerTriggerOutcome(
            triggered=True,
            method=BN.RESET_IDENTIFIERS,
            trigger_mode="reset_all_identifiers",
            product_instance_uri=piu,
        )

    async def trigger_counter_effect(self, effect_index: int = 0) -> TargetServerTriggerOutcome:
        """Invoke one counter mutation and correlate its InterventionResult with the affected parent."""
        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import NS_IJT_BASE
        from helpers.result_collector import (
            ResultCollector,
            get_classification,
            get_result_id,
            is_terminal_completed,
            references_result_id,
        )

        effects = self._profile.cu_execution.counter_effects
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
        if not self._profile.cu_execution.state_changing_methods.allow_state_changing_method(effect.method):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"{effect.method} is not authorized by the SUT manifest.",
                method=effect.method,
                trigger_mode="counter_effect",
            )
        if self._subscription_client is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="Counter-effect workflows require a separate subscription client.",
                method=effect.method,
                trigger_mode="counter_effect",
            )

        jpm_node = await self._get_joining_process_management()
        piu = await self._resolve_tool_piu()
        processes = await self._get_joining_process_list(jpm_node, piu) if jpm_node is not None else []
        candidates = [
            process
            for process in processes
            if self._process_field(
                process,
                "JoiningProcessId",
                "JoiningProcessIdentification",
                "Id",
            ).lower()
            == effect.joining_process_id.lower()
        ]
        if not candidates:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="No current process matched the configured counter-effect scenario.",
                method=effect.method,
                trigger_mode="counter_effect",
                product_instance_uri=piu,
            )

        process = candidates[0]
        process_id = self._process_field(
            process,
            "JoiningProcessId",
            "JoiningProcessIdentification",
            "Id",
        )
        if not await self._select_joining_process(jpm_node, process, piu):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"SelectJoiningProcess failed for counter candidate '{process_id}'.",
                method=effect.method,
                trigger_mode="counter_effect",
                product_instance_uri=piu,
                joining_process_id=process_id,
            )
        identification = self._make_process_identification(process)
        if identification is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="JoiningProcessIdentificationDataType is unavailable.",
                method=effect.method,
                trigger_mode="counter_effect",
                product_instance_uri=piu,
                joining_process_id=process_id,
            )

        expected_classification = self._result_classification_value(effect.expected_result_classification)
        ns_indices = {NS_IJT_BASE: await self._resolve_ijt_namespace_index()}

        def find_evidence(results: tuple[Any, ...]) -> tuple[Any | None, Any | None]:
            interventions = [
                candidate
                for candidate in results
                if is_terminal_completed(candidate, ResultClassification.INTERVENTION_RESULT)
            ]
            for intervention_candidate in reversed(interventions):
                if expected_classification is None:
                    return intervention_candidate, None
                intervention_id = get_result_id(intervention_candidate)
                if not intervention_id:
                    continue
                for affected_candidate in reversed(results):
                    if get_classification(affected_candidate) == expected_classification and references_result_id(
                        affected_candidate, intervention_id, results
                    ):
                        return intervention_candidate, affected_candidate
            return (interventions[-1], None) if interventions else (None, None)

        def evidence_ready(results: tuple[Any, ...]) -> bool:
            intervention_candidate, affected_candidate = find_evidence(results)
            return intervention_candidate is not None and (
                expected_classification is None or affected_candidate is not None
            )

        async with ResultCollector(self._subscription_client, ns_indices, is_simulator=False) as collector:
            result = await find_and_call_method(
                jpm_node,
                effect.method,
                await self._resolve_ijt_namespace_index(),
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant(identification, ua.VariantType.ExtensionObject),
                ua.Variant(effect.count, ua.VariantType.UInt32),
                timeout=self._profile.cu_execution.default_timeout_seconds,
                target_server_authorized=True,
            )
            if not self._method_succeeded(effect.method, result, observe_uncertain=True):
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"{effect.method} failed: {self._last_method_failure}",
                    method=effect.method,
                    trigger_mode="counter_effect",
                    product_instance_uri=piu,
                    joining_process_id=process_id,
                )
            capture = await collector.collect_evidence(
                evidence_ready,
                self.active_result_timeout_s,
            )
        intervention, affected = find_evidence(capture.all_results)

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
            )
        if intervention is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"{effect.method} produced no complete InterventionResult evidence.",
                method=effect.method,
                trigger_mode="counter_effect",
                product_instance_uri=piu,
                joining_process_id=process_id,
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
            )
        return TargetServerTriggerOutcome(
            triggered=True,
            method=effect.method,
            trigger_mode="counter_effect",
            product_instance_uri=piu,
            joining_process_id=process_id,
            results_confirmed=1 + int(affected is not None),
        )

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
        for name in names:
            value = getattr(process, name, None)
            if value is not None and str(value):
                return str(value)
        return ""

    @staticmethod
    def _selection_names(process: Any) -> set[str]:
        """Return SelectionName entity IDs advertised by a process."""
        names: set[str] = set()
        entities = getattr(process, "AssociatedEntities", None) or ()
        for entity in entities:
            if getattr(entity, "Name", None) == "SelectionName":
                entity_id = getattr(entity, "EntityId", None)
                if entity_id is not None and str(entity_id):
                    names.add(str(entity_id))
        return names

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
        """Return True when an exact_match selection carries at least one selector."""
        return bool(
            getattr(selection, "joining_process_id", "")
            or getattr(selection, "joining_process_origin_id", "")
            or getattr(selection, "selection_name", "")
        )

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

            selectors = (
                (
                    selection.joining_process_id,
                    lambda process: self._process_field(
                        process,
                        "JoiningProcessId",
                        "JoiningProcessIdentification",
                        "Id",
                    ),
                ),
                (
                    selection.joining_process_origin_id,
                    lambda process: self._process_field(
                        process,
                        "JoiningProcessOriginId",
                        "JoiningProcessIdentificationOrigin",
                    ),
                ),
            )
            for configured_value, read_value in selectors:
                if not configured_value:
                    continue
                matches = [
                    process
                    for process in processes
                    if read_value(process).strip().lower() == configured_value.strip().lower()
                ]
                if matches:
                    return self._validate_exact_candidates(
                        matches,
                        norm_key,
                        matches_requested_classification,
                    )
            if selection.selection_name:
                matches = [
                    process
                    for process in processes
                    if any(
                        selection.selection_name.strip().lower() == name.strip().lower()
                        for name in self._selection_names(process)
                    )
                ]
                return self._validate_exact_candidates(
                    matches,
                    norm_key,
                    matches_requested_classification,
                )
            return []

        if not norm_key or norm_key == "intervention":
            return list(processes) if selection.policy == "all_compatible" else [processes[0]]

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
        return direct + compound

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
                _process_classification(process),
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
        )

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
        jpm_node = await self._get_joining_process_management()
        if jpm_node is None:
            return None
        piu = await self._resolve_tool_piu()
        processes = await self._get_joining_process_list(jpm_node, piu)
        selection, _ = self._get_selection_for_classification(classification)
        classification_key = self._normalize_classification(classification)
        if operation_count is None:
            operation_count = self._profile.workflow_execution.max_start_invocations_by_result_classification.get(
                classification_key,
                self._profile.workflow_execution.max_start_invocations,
            )
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
            if progression is not None:
                return progression
        return None

    def remember_result_progression(self, progression: Any) -> bool:
        """Store complete progression captured immediately after this trigger."""
        key = self._pending_evidence_key
        if (
            not self._profile.workflow_execution.evidence_reuse.enabled
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

    def _make_process_identification(self, process: Any, classification: str | int | None = None) -> Any:
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
        strategy = getattr(selection, "identifier_strategy", "id_only")
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
            selection.selection_name or (advertised_names[0] if advertised_names else "")
            if strategy in {"id_with_selection_name", "all_available"}
            else ""
        )
        return identification

    async def _select_joining_process(
        self, jpm_node: Any, process: Any, piu: str, classification: str | int | None = None
    ) -> bool:
        """Call SelectJoiningProcess and return True on success."""
        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN

        identification = self._make_process_identification(process, classification=classification)
        if identification is None:
            return False

        result = await find_and_call_method(
            jpm_node,
            BN.SELECT_JOINING_PROCESS,
            await self._resolve_ijt_namespace_index(),
            ua.Variant(piu, ua.VariantType.String),
            ua.Variant(identification, ua.VariantType.ExtensionObject),
            timeout=self._profile.cu_execution.default_timeout_seconds,
            target_server_authorized=True,
        )
        return self._method_succeeded(BN.SELECT_JOINING_PROCESS, result)

    async def _trigger_intervention(self) -> TargetServerTriggerOutcome:
        """Generate an InterventionResult using a configured process action."""
        from asyncua import ua

        from helpers.method_caller import find_and_call_method

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

        result = await find_and_call_method(
            jpm_node,
            method_name,
            await self._resolve_ijt_namespace_index(),
            *method_args,
            timeout=self._profile.cu_execution.default_timeout_seconds,
            target_server_authorized=True,
        )
        process_id = str(identification.JoiningProcessId)
        if not self._method_succeeded(
            method_name,
            result,
            observe_uncertain=True,
        ):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"{method_name} failed for process '{process_id}': {self._last_method_failure}",
                method=method_name,
                trigger_mode="joining_process_intervention",
                product_instance_uri=piu,
                joining_process_id=process_id,
            )
        return TargetServerTriggerOutcome(
            triggered=True,
            method=method_name,
            trigger_mode="joining_process_intervention",
            product_instance_uri=piu,
            joining_process_id=process_id,
            joining_process_origin_id=str(identification.JoiningProcessOriginId),
        )

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
            target_server_authorized=True,
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
        if sc.allow_state_changing_method("EnableAsset") and not await self._ensure_tool_enabled(piu):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"EnableAsset failed for tool PIU='{piu}': {self._last_method_failure}",
                method="EnableAsset",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
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
            attempted_ids.append(candidate_id)
            outcome = await self._run_candidate_workflow(
                jpm_node,
                piu,
                candidate,
                operation_count=operation_count,
                classification=classification,
                require_partials=require_partials,
            )
            outcomes.append(outcome)
            if outcome.triggered:
                proven_ids.append(candidate_id)
                if selection.policy != "all_compatible":
                    break
            else:
                rejected_ids.append(candidate_id)

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

    async def _run_candidate_workflow(
        self,
        jpm_node: Any,
        piu: str,
        target_process: Any,
        *,
        operation_count: int,
        classification: str | int | None,
        require_partials: bool = False,
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

        selected = await self._select_joining_process(jpm_node, target_process, piu, classification=classification)
        if not selected:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"SelectJoiningProcess failed for process '{jp_id}': {self._last_method_failure}",
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
                joining_process_id=jp_id,
            )

        deselect = self._profile.triggers.result.deselect_after_joining
        target_process_cls = _process_classification(target_process)
        requested_result_cls = self._result_classification_value(classification)
        if target_process_cls == JoiningProcessClassification.PROGRAM:
            max_starts = 1
        else:
            classification_key = self._normalize_classification(classification)
            configured_limit = self._profile.workflow_execution.max_start_invocations_by_result_classification.get(
                classification_key,
                max(operation_count, 1),
            )
            max_starts = min(configured_limit, self._profile.workflow_execution.max_start_invocations)

        from contextlib import AsyncExitStack

        from helpers.namespaces import NS_IJT_BASE
        from helpers.result_collector import ResultCollector

        async with AsyncExitStack() as stack:
            completed_operations = 0
            confirmed_operations = 0
            terminal_result_confirmed = False
            result_progression = None
            completion_collector = None
            if self._subscription_client is not None:
                completion_collector = await stack.enter_async_context(
                    ResultCollector(
                        self._subscription_client,
                        {NS_IJT_BASE: await self._resolve_ijt_namespace_index()},
                        is_simulator=False,
                    )
                )
            elif max_starts > 1 or requested_result_cls not in {
                None,
                ResultClassification.SINGLE_RESULT,
            }:
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
                )

            pacing = float(getattr(self._profile.workflow_execution, "consecutive_start_delay_seconds", 0.25))
            expected_state = int(
                getattr(
                    self._profile.workflow_execution.expected_results,
                    "expected_terminal_result_state",
                    1,
                )
            )
            terminal_predicate = lambda result: self._result_matches_context(result, piu, jp_id, jp_origin)
            operation_predicate = lambda result: self._result_matches_tool_context(result, piu)

            if completion_collector is not None:
                completion_collector.discard_pending()

            for operation_number in range(1, max_starts + 1):
                if completion_collector is not None and operation_number > 1:
                    pending_terminal = completion_collector.collect_pending_terminal(
                        requested_result_cls,
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
                    )
                completed_operations = operation_number
                if completion_collector is not None:
                    obs = await completion_collector.collect_correlated_operation_outcome(
                        requested_result_classification=requested_result_cls,
                        predicate=terminal_predicate,
                        operation_timeout_s=self.active_result_timeout_s,
                        terminal_drain_seconds=pacing,
                        operation_predicate=operation_predicate,
                        expected_terminal_state=expected_state,
                    )
                    if obs.timed_out:
                        # This start was accepted but produced no correlated result
                        return TargetServerTriggerOutcome(
                            triggered=False,
                            skip_reason=(
                                "No correlated result confirming the selected Tool and JoiningProcess "
                                f"arrived on operation {operation_number}/{max_starts} within "
                                f"{self.active_result_timeout_s:.1f}s (requires physical operator action or auto-cycle)"
                            ),
                            method="StartSelectedJoining",
                            trigger_mode="start_selected_joining",
                            product_instance_uri=piu,
                            joining_process_id=jp_id,
                            joining_process_origin_id=jp_origin,
                            operation_count=operation_number,
                            starts_issued=operation_number,
                            results_confirmed=confirmed_operations,
                        )
                    confirmed_operations = operation_number
                    if obs.terminal_result is not None:
                        terminal_result_confirmed = True
                        logger.info(
                            "Terminal result (classification %s) confirmed on operation %d/%d; workflow completed",
                            requested_result_cls,
                            operation_number,
                            max_starts,
                        )
                        completed_operations = operation_number
                        break

            if completion_collector is not None and requested_result_cls is not None and terminal_result_confirmed:
                result_progression = await completion_collector.collect_progression(
                    requested_result_cls,
                    timeout_s=self.active_result_timeout_s,
                    require_partials=require_partials,
                    expected_terminal_state=expected_state,
                    allow_partial_references=self.allow_partial_referenced_children,
                )
                terminal_result_confirmed = result_progression.is_complete

        if (
            completion_collector is not None
            and requested_result_cls
            in {
                ResultClassification.BATCH_RESULT,
                ResultClassification.SYNC_RESULT,
                ResultClassification.JOB_RESULT,
            }
            and not terminal_result_confirmed
        ):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=(
                    f"Process '{jp_id}' accepted {completed_operations} start(s), but no completed "
                    f"result with requested classification {requested_result_cls} was observed; "
                    "process metadata alone does not prove result capability"
                ),
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
                joining_process_id=jp_id,
                joining_process_origin_id=jp_origin,
                operation_count=completed_operations,
                starts_issued=completed_operations,
                results_confirmed=confirmed_operations,
                result_progression=result_progression,
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
        )

    async def _trigger_operations(
        self,
        operation_count: int,
        classification: str | int | None = None,
        *,
        require_partials: bool = False,
    ) -> TriggerOutcome:
        """Trigger one selected process for the requested operation count."""
        method_timeout = self._profile.cu_execution.default_timeout_seconds
        result_timeout = self._profile.workflow_execution.expected_results.timeout_seconds
        classification_key = self._normalize_classification(classification)
        max_starts = self._profile.workflow_execution.max_start_invocations_by_result_classification.get(
            classification_key,
            self._profile.workflow_execution.max_start_invocations,
        )
        max_starts = min(max_starts, self._profile.workflow_execution.max_start_invocations)
        workflow_timeout = (4 * method_timeout) + max_starts * (method_timeout + result_timeout)
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
            )
        except Exception as exc:  # noqa: BLE001
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"StartSelectedJoining workflow failed: {exc}",
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
            )

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

    async def _run_abort_workflow(self) -> TargetServerTriggerOutcome:
        """Execute a multi-step Job/Batch, start step 1, issue AbortJoiningProcess, and verify ResultState=3."""
        from contextlib import AsyncExitStack

        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN, NS_IJT_BASE, ResultEvaluation, ResultState
        from helpers.result_collector import ResultCollector, is_terminal_aborted

        sc = self._profile.cu_execution.state_changing_methods
        for method in ("SelectJoiningProcess", "StartSelectedJoining", "AbortJoiningProcess"):
            if not sc.allow_state_changing_method(method):
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"{method} is not in the allowed state-changing methods list.",
                    method=method,
                    trigger_mode="start_selected_joining",
                )

        jpm_node = await self._get_joining_process_management()
        if jpm_node is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="JoiningProcessManagement node not found under JoiningSystem",
                method="AbortJoiningProcess",
                trigger_mode="start_selected_joining",
            )

        piu = await self._resolve_tool_piu()
        if sc.allow_state_changing_method("EnableAsset") and not await self._ensure_tool_enabled(piu):
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=f"EnableAsset failed for tool PIU='{piu}': {self._last_method_failure}",
                method="EnableAsset",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
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
        if target_process is None:
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

        async with AsyncExitStack() as stack:
            collector = await stack.enter_async_context(
                ResultCollector(
                    self._subscription_client,
                    {NS_IJT_BASE: await self._resolve_ijt_namespace_index()},
                    is_simulator=False,
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
                operation_predicate=lambda result: self._result_matches_tool_context(result, piu),
            )
            if not obs.operation_confirmed or obs.operation_result is None or obs.terminal_result is not None:
                if obs.terminal_result is not None:
                    return TargetServerTriggerOutcome(
                        triggered=False,
                        skip_reason="Process completed before abort could be issued (cannot abort an already-completed sequence)",
                        method="AbortJoiningProcess",
                        trigger_mode="start_selected_joining",
                        product_instance_uri=piu,
                        joining_process_id=jp_id,
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

            # Step 2: Issue AbortJoiningProcess
            message = str(
                self._profile.cu_execution.extension_fields.get(
                    "abort_message",
                    "IJT target-server automated abort test",
                )
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
            )
            if not self._method_succeeded(BN.ABORT_JOINING_PROCESS, abort_result):
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"AbortJoiningProcess call failed for process '{jp_id}': {self._last_method_failure}",
                    method="AbortJoiningProcess",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                )

            # Step 3: Wait for terminal result with ResultState == 3 (ABORTED)
            abort_obs = await collector.collect_correlated_operation_outcome(
                requested_result_classification=res_cls,
                predicate=lambda result: self._result_matches_context(result, piu, jp_id, jp_origin),
                operation_timeout_s=self.active_result_timeout_s,
                terminal_drain_seconds=0.25,
                expected_terminal_state=ResultState.ABORTED,
            )
            if abort_obs.terminal_result is None or not is_terminal_aborted(abort_obs.terminal_result, res_cls):
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
                    )

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
        )

    async def _run_reset_workflow(self) -> TargetServerTriggerOutcome:
        """Execute ResetJoiningProcess on an active Job/Batch sequence and verify restart to step 1."""
        from contextlib import AsyncExitStack

        from asyncua import ua

        from helpers.method_caller import find_and_call_method
        from helpers.namespaces import BN, NS_IJT_BASE
        from helpers.result_collector import ResultCollector

        sc = self._profile.cu_execution.state_changing_methods
        for method in ("SelectJoiningProcess", "StartSelectedJoining", "ResetJoiningProcess"):
            if not sc.allow_state_changing_method(method):
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"{method} is not in the allowed state-changing methods list.",
                    method=method,
                    trigger_mode="start_selected_joining",
                )

        jpm_node = await self._get_joining_process_management()
        if jpm_node is None:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="JoiningProcessManagement node not found under JoiningSystem",
                method="ResetJoiningProcess",
                trigger_mode="start_selected_joining",
            )

        piu = await self._resolve_tool_piu()
        processes = await self._get_joining_process_list(jpm_node, piu)
        if not processes:
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason="No joining processes returned by GetJoiningProcessList",
                method="ResetJoiningProcess",
                trigger_mode="start_selected_joining",
            )

        target_process = self._choose_joining_process(processes, classification="job")
        if target_process is None:
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

        async with AsyncExitStack() as stack:
            collector = await stack.enter_async_context(
                ResultCollector(
                    self._subscription_client,
                    {NS_IJT_BASE: await self._resolve_ijt_namespace_index()},
                    is_simulator=False,
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
                operation_predicate=lambda result: self._result_matches_tool_context(result, piu),
            )
            if not obs.operation_confirmed or obs.operation_result is None or obs.terminal_result is not None:
                if obs.terminal_result is not None:
                    return TargetServerTriggerOutcome(
                        triggered=False,
                        skip_reason="Process completed before reset could be issued (cannot reset an already-completed sequence)",
                        method="ResetJoiningProcess",
                        trigger_mode="start_selected_joining",
                        product_instance_uri=piu,
                        joining_process_id=jp_id,
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
            reset_result = await find_and_call_method(
                jpm_node,
                BN.RESET_JOINING_PROCESS,
                await self._resolve_ijt_namespace_index(),
                ua.Variant(piu, ua.VariantType.String),
                ua.Variant(identification, ua.VariantType.ExtensionObject),
                timeout=self._profile.cu_execution.default_timeout_seconds,
                target_server_authorized=True,
            )
            if not self._method_succeeded(BN.RESET_JOINING_PROCESS, reset_result):
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"ResetJoiningProcess call failed for process '{jp_id}': {self._last_method_failure}",
                    method="ResetJoiningProcess",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                )

            # Step 3: Clear queue and restart step 1 to verify sequence returned to step 1
            collector.discard_pending()
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
                operation_predicate=lambda result: self._result_matches_tool_context(result, piu),
            )
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
            if not same_step:
                return TargetServerTriggerOutcome(
                    triggered=False,
                    skip_reason=f"Post-reset step-1 verification failed: {evidence_error}",
                    method="ResetJoiningProcess",
                    trigger_mode="start_selected_joining",
                    product_instance_uri=piu,
                    joining_process_id=jp_id,
                    inconclusive=inconclusive,
                )

        return TargetServerTriggerOutcome(
            triggered=True,
            method="ResetJoiningProcess",
            trigger_mode="start_selected_joining",
            product_instance_uri=piu,
            joining_process_id=jp_id,
            joining_process_origin_id=jp_origin,
            operation_count=2,
            starts_issued=2,
            results_confirmed=2,
        )

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
        return await self._run_abort_workflow()

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
        return await self._run_reset_workflow()

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
    ) -> None:
        self._profile = profile
        self._driver = StartSelectedJoiningResultTrigger(
            client,
            joining_system_node,
            ns_app,
            profile,
            ns_ijt=ns_ijt,
            ns_di=ns_di,
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
    override_class = os.environ.get("OPCUA_TRIGGER_CLASS")
    if override_class:
        import importlib

        module_name, class_name = override_class.rsplit(".", 1)
        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)
        logger.info("Using OPCUA_TRIGGER_CLASS override: %s", override_class)
        return cls(client, joining_system_node, ns_app)

    mode = profile.triggers.result.mode

    if mode == SIMULATE_METHODS_MODE:
        folder = _require_simulator_folder(
            simulate_results_folder,
            browse_name=BN.SIMULATE_RESULTS_FOLDER,
            mode_path="triggers.result.mode",
            profile=profile,
        )
        logger.debug("TargetServer result trigger: SimulatorResultTrigger")
        return SimulatorResultTrigger(client, folder, ns_app)

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
        return ManualResultTrigger(profile, allow_waiting=allow_waiting)

    logger.debug("TargetServer result trigger: ExternalResultTrigger (mode=%s)", mode)
    return ExternalResultTrigger()


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
    )
