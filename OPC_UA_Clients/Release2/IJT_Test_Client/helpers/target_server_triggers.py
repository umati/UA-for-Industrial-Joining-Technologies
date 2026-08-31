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

    @staticmethod
    def _result_matches_context(
        result_data: Any, piu: str, joining_process_id: str, joining_process_origin_id: str = ""
    ) -> bool:
        """Require result identifiers for the selected Tool and JoiningProcess."""
        from asyncua import ua

        meta = getattr(result_data, "ResultMetaData", None)
        entities = getattr(meta, "AssociatedEntities", None) or ()
        entity_ids: set[str] = set()
        for entity in entities:
            value = entity.Value if isinstance(entity, ua.Variant) else entity
            entity_id = getattr(value, "EntityId", None)
            if entity_id is not None and str(entity_id):
                entity_ids.add(str(entity_id).lower().strip())

        piu_lower = piu.lower().strip()
        jp_id_lower = joining_process_id.lower().strip()
        jp_origin_lower = joining_process_origin_id.lower().strip()

        piu_match = not piu_lower or piu_lower in entity_ids
        jp_match = (
            not jp_id_lower and not jp_origin_lower
        ) or (
            (bool(jp_id_lower) and jp_id_lower in entity_ids)
            or (bool(jp_origin_lower) and jp_origin_lower in entity_ids)
        )
        return piu_match and jp_match

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

    async def _enable_tool(self, piu: str) -> bool:
        """Enable the selected tool before starting when the profile allows it."""
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
            ua.Variant(True, ua.VariantType.Boolean),
            timeout=self._profile.cu_execution.default_timeout_seconds,
            target_server_authorized=True,
        )
        return self._method_succeeded(BN.ENABLE_ASSET, result)

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
        if isinstance(classification, int):
            from helpers.namespaces import ResultClassification

            mapping = {
                ResultClassification.SINGLE_RESULT: "single",
                ResultClassification.SYNC_RESULT: "sync",
                ResultClassification.BATCH_RESULT: "batch",
                ResultClassification.JOB_RESULT: "job",
                ResultClassification.STITCHING_RESULT: "stitching",
                ResultClassification.INTERVENTION_RESULT: "intervention",
            }
            return mapping.get(classification, "")
        return str(classification).lower().strip()

    def _get_selection_for_classification(self, classification: str | int | None = None) -> tuple[Any, str]:
        """Return the appropriate process selection config and normalized key."""
        key = self._normalize_classification(classification)
        if key and key in self._profile.selection.joining_processes:
            return self._profile.selection.joining_processes[key], key
        if key == "intervention":
            cpp = self._profile.cu_execution.extension_fields.get("counter_parent_process")
            if isinstance(cpp, dict) and (cpp.get("joining_process_id") or cpp.get("joining_process_origin_id")):
                from helpers.target_server_cu_config import JoiningProcessSelectionConfig

                return JoiningProcessSelectionConfig(
                    policy="exact_match",
                    joining_process_id=cpp.get("joining_process_id", ""),
                    joining_process_origin_id=cpp.get("joining_process_origin_id", ""),
                    selection_name=cpp.get("selection_name", ""),
                ), key
            if self._profile.selection.joining_processes:
                from helpers.target_server_cu_config import JoiningProcessSelectionConfig

                return JoiningProcessSelectionConfig(policy="exact_match"), key
        return self._profile.selection.joining_process, key

    def _choose_joining_process(self, processes: list[Any], classification: str | int | None = None) -> Any | None:
        """Choose a process according to the profile's deterministic selection policy."""
        selection, _ = self._get_selection_for_classification(classification)
        if selection.policy != "exact_match":
            return processes[0] if processes else None

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
            for process in processes:
                if read_value(process) == configured_value:
                    return process
        if selection.selection_name:
            for process in processes:
                if selection.selection_name in self._selection_names(process):
                    return process
            return None
        return None

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
        """Build the IJT process identifier required by controller methods."""
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
        identification.JoiningProcessOriginId = self._process_field(
            process,
            "JoiningProcessOriginId",
            "JoiningProcessIdentificationOrigin",
        )
        selection, _ = self._get_selection_for_classification(classification)
        configured_name = selection.selection_name
        advertised_names = self._selection_names(process)
        ids_configured = bool(selection.joining_process_id or selection.joining_process_origin_id)
        identification.SelectionName = (
            "" if ids_configured else configured_name or (sorted(advertised_names)[0] if advertised_names else "")
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
        self, operation_count: int = 1, classification: str | int | None = None
    ) -> TargetServerTriggerOutcome:
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

        target_process = self._choose_joining_process(processes, classification=classification)
        if target_process is None:
            selection, norm_key = self._get_selection_for_classification(classification)
            label = f"{norm_key} " if norm_key else ""
            return TargetServerTriggerOutcome(
                triggered=False,
                skip_reason=(
                    f"No joining process matched the configured {label}selection "
                    f"(id='{selection.joining_process_id}', "
                    f"origin='{selection.joining_process_origin_id}', "
                    f"selection_name='{selection.selection_name}'); "
                    f"available: [{self._describe_joining_processes(processes)}]"
                ),
                method="StartSelectedJoining",
                trigger_mode="start_selected_joining",
                product_instance_uri=piu,
            )

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
        from contextlib import AsyncExitStack

        from helpers.namespaces import NS_IJT_BASE
        from helpers.result_collector import ResultCollector

        async with AsyncExitStack() as stack:
            completion_collector = None
            if operation_count > 1:
                if self._subscription_client is None:
                    return TargetServerTriggerOutcome(
                        triggered=False,
                        skip_reason=(
                            "Multi-operation remote start requires a separate subscription client "
                            "for correlated operation-completion events"
                        ),
                        method="StartSelectedJoining",
                        trigger_mode="start_selected_joining",
                        product_instance_uri=piu,
                        joining_process_id=jp_id,
                        joining_process_origin_id=jp_origin,
                    )
                completion_collector = await stack.enter_async_context(
                    ResultCollector(
                        self._subscription_client,
                        {NS_IJT_BASE: await self._resolve_ijt_namespace_index()},
                        is_simulator=False,
                    )
                )

            for operation_number in range(1, operation_count + 1):
                if completion_collector is not None:
                    completion_collector.discard_pending()
                started = await self._start_selected_joining(jpm_node, piu, deselect)
                if not started:
                    return TargetServerTriggerOutcome(
                        triggered=False,
                        skip_reason=(
                            f"StartSelectedJoining failed on operation {operation_number}/{operation_count} "
                            f"for process '{jp_id}', PIU='{piu}': {self._last_method_failure}"
                        ),
                        method="StartSelectedJoining",
                        trigger_mode="start_selected_joining",
                        product_instance_uri=piu,
                        joining_process_id=jp_id,
                        joining_process_origin_id=jp_origin,
                        operation_count=operation_number - 1,
                    )
                if completion_collector is not None:
                    completed = await completion_collector.collect_single_matching(
                        lambda result: self._result_matches_context(result, piu, jp_id, jp_origin),
                        timeout_s=min(
                            self._profile.triggers.result.timeout_seconds,
                            self._profile.workflow_execution.expected_results.timeout_seconds,
                        ),
                    )
                    if completed is None:
                        return TargetServerTriggerOutcome(
                            triggered=False,
                            skip_reason=(
                                "No SingleResult correlated to the selected Tool and JoiningProcess "
                                f"confirmed operation {operation_number}/{operation_count}"
                            ),
                            method="StartSelectedJoining",
                            trigger_mode="start_selected_joining",
                            product_instance_uri=piu,
                            joining_process_id=jp_id,
                            joining_process_origin_id=jp_origin,
                            operation_count=operation_number,
                        )
                    from helpers.namespaces import ResultClassification
                    from helpers.result_collector import get_classification

                    res_cls = get_classification(completed)
                    if (
                        classification in ("job", ResultClassification.JOB_RESULT)
                        and res_cls == ResultClassification.JOB_RESULT
                    ) or (
                        classification in ("batch", ResultClassification.BATCH_RESULT)
                        and res_cls == ResultClassification.BATCH_RESULT
                    ):
                        logger.info(
                            "Terminal %s result received on operation %d/%d; workflow completed",
                            classification,
                            operation_number,
                            operation_count,
                        )
                        break

        logger.debug(
            "StartSelectedJoining succeeded: PIU=%s, process=%s, operations=%d",
            piu,
            jp_id,
            operation_count,
        )
        return TargetServerTriggerOutcome(
            triggered=True,
            method="StartSelectedJoining",
            trigger_mode="start_selected_joining",
            product_instance_uri=piu,
            joining_process_id=jp_id,
            joining_process_origin_id=jp_origin,
            operation_count=operation_count,
        )

    async def _trigger_operations(
        self, operation_count: int, classification: str | int | None = None
    ) -> TriggerOutcome:
        """Trigger one selected process for the requested operation count."""
        method_timeout = self._profile.cu_execution.default_timeout_seconds
        result_timeout = self._profile.workflow_execution.expected_results.timeout_seconds
        workflow_timeout = (4 * method_timeout) + operation_count * (method_timeout + result_timeout)
        try:
            return await asyncio.wait_for(
                self._run_workflow(operation_count, classification=classification),
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
        return await self._trigger_operations(1, classification="single")

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
        from helpers.namespaces import ResultClassification

        if classification == ResultClassification.INTERVENTION_RESULT:
            return await self._trigger_intervention()
        policy = self._profile.workflow_execution.start_invocation_policy
        cls_name = "batch" if classification == ResultClassification.BATCH_RESULT else "sync"
        if policy == "one_start_per_operation":
            count = self._profile.workflow_execution.expected_operation_count or num_children
            return await self._trigger_operations(count, classification=cls_name)
        # single_start_produces_final_result
        return await self._trigger_operations(1, classification=cls_name)

    async def trigger_job(self, send_as_refs: bool = False) -> TriggerOutcome:
        """Trigger joining workflow for job-level evidence."""
        if self._profile.workflow_execution.start_invocation_policy == "one_start_per_operation":
            return await self._trigger_operations(
                self._profile.workflow_execution.expected_operation_count,
                classification="job",
            )
        return await self._trigger_operations(1, classification="job")

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
    subscription_client: Any = None,
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
