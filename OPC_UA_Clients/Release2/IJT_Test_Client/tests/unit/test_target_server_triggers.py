"""
Unit tests for helpers/target_server_triggers.py

Tests target_server-specific trigger adapters without a live OPC UA server.
Uses mocks to simulate joining system node behavior.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helpers.method_caller import MethodCallResult
from helpers.namespaces import BN, JoiningProcessClassification, ResultClassification
from helpers.result_collector import CorrelatedOperationOutcome
from helpers.target_server_cu_config import build_default_profile, build_execution_profile
from helpers.target_server_triggers import (
    ManualEventTrigger,
    ManualResultTrigger,
    SplitEventTrigger,
    StartSelectedJoiningResultTrigger,
    TargetServerTriggerConfigurationError,
    TargetServerTriggerOutcome,
    make_target_server_event_trigger,
    make_target_server_result_trigger,
)
from helpers.trigger import (
    ExternalEventTrigger,
    ExternalResultTrigger,
    SimulatorEventTrigger,
    SimulatorResultTrigger,
    TriggerOutcome,
)

# ---------------------------------------------------------------------------
# TargetServerTriggerOutcome
# ---------------------------------------------------------------------------


class TestTargetServerTriggerOutcome:
    def test_is_subclass_of_trigger_outcome(self):
        o = TargetServerTriggerOutcome(triggered=True)
        assert isinstance(o, TriggerOutcome)

    def test_target_server_fields_default(self):
        o = TargetServerTriggerOutcome(triggered=False, skip_reason="x")
        assert o.trigger_mode == ""
        assert o.product_instance_uri == ""
        assert o.joining_process_id == ""
        assert o.operation_count == 0
        assert o.starts_issued == 0
        assert o.results_confirmed == 0
        assert o.pre_trigger_baseline == {}

    def test_starts_and_confirmations_are_reported_separately(self):
        """Started-but-unconfirmed evidence must be distinguishable."""
        o = TargetServerTriggerOutcome(
            triggered=False,
            operation_count=2,
            starts_issued=2,
            results_confirmed=1,
        )
        assert o.starts_issued == 2
        assert o.results_confirmed == 1
        assert o.operation_count == o.starts_issued

    def test_target_server_fields_set(self):
        o = TargetServerTriggerOutcome(
            triggered=True,
            trigger_mode="start_selected_joining",
            product_instance_uri="urn:tool:1",
            joining_process_id="PROG01",
            operation_count=1,
        )
        assert o.triggered is True
        assert o.trigger_mode == "start_selected_joining"
        assert o.product_instance_uri == "urn:tool:1"
        assert o.joining_process_id == "PROG01"
        assert o.operation_count == 1


# ---------------------------------------------------------------------------
# ManualResultTrigger
# ---------------------------------------------------------------------------


class TestManualResultTrigger:
    @pytest.fixture
    def profile(self):
        return build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": "manual_trigger", "timeout_seconds": 90}},
            }
        )

    @pytest.fixture
    def trigger(self, profile):
        return ManualResultTrigger(profile)

    def test_is_simulator_false(self, trigger):
        assert trigger.is_simulator is False

    async def test_trigger_single_returns_not_triggered(self, trigger):
        outcome = await trigger.trigger_single(1)
        assert outcome.triggered is False
        assert outcome.skip_reason is not None
        assert "manual" in outcome.skip_reason.lower() or "trigger" in outcome.skip_reason.lower()

    async def test_trigger_batch_or_sync_not_triggered(self, trigger):
        outcome = await trigger.trigger_batch_or_sync(2, num_children=3)
        assert outcome.triggered is False

    async def test_trigger_job_not_triggered(self, trigger):
        outcome = await trigger.trigger_job()
        assert outcome.triggered is False

    async def test_trigger_bulk_results_not_triggered(self, trigger):
        outcome = await trigger.trigger_bulk_results(1, False, 0, 10)
        assert outcome.triggered is False

    async def test_skip_reason_includes_timeout(self, trigger):
        outcome = await trigger.trigger_single(1)
        assert "90" in outcome.skip_reason or "manual" in outcome.skip_reason.lower()


# ---------------------------------------------------------------------------
# ManualEventTrigger
# ---------------------------------------------------------------------------


class TestManualEventTrigger:
    @pytest.fixture
    def profile(self):
        return build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {"event": {"mode": "manual_trigger", "timeout_seconds": 60}},
            }
        )

    @pytest.fixture
    def trigger(self, profile):
        return ManualEventTrigger(profile)

    def test_is_simulator_false(self, trigger):
        assert trigger.is_simulator is False

    async def test_trigger_event_not_triggered(self, trigger):
        outcome = await trigger.trigger_event(1)
        assert outcome.triggered is False
        assert outcome.skip_reason is not None

    async def test_trigger_bulk_events_not_triggered(self, trigger):
        outcome = await trigger.trigger_bulk_events(1, 5, 0, 5)
        assert outcome.triggered is False

    async def test_trigger_condition_not_triggered(self, trigger):
        outcome = await trigger.trigger_condition(1)
        assert outcome.triggered is False


# ---------------------------------------------------------------------------
# StartSelectedJoiningResultTrigger — isolated workflow tests with mocks
# ---------------------------------------------------------------------------


class TestStartSelectedJoiningResultTrigger:
    @pytest.fixture
    def profile(self):
        return build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": "start_selected_joining", "timeout_seconds": 30}},
                "cu_execution": {
                    "state_changing_methods": {
                        "default_policy": "require_explicit_opt_in",
                        "allowed_methods": ["SelectJoiningProcess", "StartSelectedJoining"],
                    },
                    "default_timeout_seconds": 30,
                },
            }
        )

    @pytest.fixture
    def blocked_profile(self):
        """Profile that does NOT allow state-changing methods."""
        return build_default_profile()

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_joining_system(self):
        return MagicMock()

    def _make_trigger(self, profile, mock_client, mock_joining_system):
        return StartSelectedJoiningResultTrigger(
            client=mock_client,
            joining_system_node=mock_joining_system,
            ns_app=2,
            profile=profile,
        )

    def test_is_simulator_false(self, profile, mock_client, mock_joining_system):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        assert trigger.is_simulator is False

    async def test_resolve_tool_piu_calls_discovery_with_client_and_namespaces(
        self, profile, mock_client, mock_joining_system
    ):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        mock_client.get_namespace_index = AsyncMock(side_effect=[7, 5])
        read_piu = AsyncMock(return_value="urn:tool:discovered")

        with patch("helpers.node_discovery.read_tool_product_instance_uri", new=read_piu):
            piu = await trigger._resolve_tool_piu()

        assert piu == "urn:tool:discovered"
        read_piu.assert_awaited_once_with(mock_client, 7, 5, 2)

    async def test_resolve_tool_piu_uses_provided_namespace_indices(self, profile, mock_client, mock_joining_system):
        trigger = StartSelectedJoiningResultTrigger(
            client=mock_client,
            joining_system_node=mock_joining_system,
            ns_app=2,
            profile=profile,
            ns_ijt=7,
            ns_di=5,
        )
        read_piu = AsyncMock(return_value="urn:tool:provided-ns")

        with patch("helpers.node_discovery.read_tool_product_instance_uri", new=read_piu):
            piu = await trigger._resolve_tool_piu()

        assert piu == "urn:tool:provided-ns"
        mock_client.get_namespace_index.assert_not_called()
        read_piu.assert_awaited_once_with(mock_client, 7, 5, 2)

    async def test_resolve_tool_piu_returns_empty_on_discovery_failure(self, profile, mock_client, mock_joining_system):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        mock_client.get_namespace_index = AsyncMock(side_effect=RuntimeError("namespace unavailable"))

        assert await trigger._resolve_tool_piu() == ""

    async def test_joining_process_management_uses_ijt_namespace(self, profile, mock_client, mock_joining_system):
        trigger = StartSelectedJoiningResultTrigger(
            client=mock_client,
            joining_system_node=mock_joining_system,
            ns_app=2,
            profile=profile,
            ns_ijt=7,
            ns_di=5,
        )
        find_child = AsyncMock(return_value=MagicMock())

        with patch("helpers.node_discovery.find_child_by_browse_name", new=find_child):
            await trigger._get_joining_process_management()

        assert find_child.await_args is not None
        assert find_child.await_args.args[2] == 7

    async def test_enable_tool_calls_enable_asset_with_tool_piu(self, profile, mock_client, mock_joining_system):
        trigger = StartSelectedJoiningResultTrigger(
            client=mock_client,
            joining_system_node=mock_joining_system,
            ns_app=2,
            profile=profile,
            ns_ijt=7,
            ns_di=5,
        )
        find_child = AsyncMock(return_value=MagicMock())
        find_method_set = AsyncMock(return_value=MagicMock())
        call_result = MagicMock(success=True)
        call_method = AsyncMock(return_value=call_result)

        with (
            patch("helpers.node_discovery.find_child_by_browse_name", new=find_child),
            patch("helpers.node_discovery.find_method_set", new=find_method_set),
            patch("helpers.method_caller.find_and_call_method", new=call_method),
        ):
            assert await trigger._enable_tool("urn:tool:1") is True

        call_args = call_method.await_args
        assert call_args is not None
        assert call_args.args[1] == "EnableAsset"
        assert call_args.args[2] == 7
        assert call_args.args[3].Value == "urn:tool:1"
        assert call_args.args[4].Value is True

    async def test_ensure_tool_enabled_skips_call_when_live_state_is_true(
        self, profile, mock_client, mock_joining_system
    ):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        trigger._read_tool_enabled = AsyncMock(return_value=True)
        trigger._enable_tool = AsyncMock(return_value=True)

        assert await trigger._ensure_tool_enabled("urn:tool:1") is True

        trigger._read_tool_enabled.assert_awaited_once_with("urn:tool:1")
        trigger._enable_tool.assert_not_awaited()

    @pytest.mark.parametrize("enabled_state", [False, None])
    async def test_ensure_tool_enabled_calls_enable_when_needed(
        self, profile, mock_client, mock_joining_system, enabled_state
    ):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        trigger._read_tool_enabled = AsyncMock(return_value=enabled_state)
        trigger._enable_tool = AsyncMock(return_value=True)

        assert await trigger._ensure_tool_enabled("urn:tool:1") is True

        trigger._enable_tool.assert_awaited_once_with("urn:tool:1")

    async def test_ensure_tool_enabled_can_reassert_enablement(self, profile, mock_client, mock_joining_system):
        profile.cu_execution.extension_fields["enable_asset_policy"] = "always"
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        trigger._read_tool_enabled = AsyncMock(return_value=True)
        trigger._enable_tool = AsyncMock(return_value=True)

        assert await trigger._ensure_tool_enabled("urn:tool:1") is True

        trigger._read_tool_enabled.assert_not_awaited()
        trigger._enable_tool.assert_awaited_once_with("urn:tool:1")

    async def test_trigger_intervention_uses_tool_and_process_identification(self, mock_client, mock_joining_system):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "state_changing_methods": {
                        "default_policy": "require_explicit_opt_in",
                        "allowed_methods": ["IncrementJoiningProcessCounter"],
                    },
                    "extension_fields": {"intervention_method": "IncrementJoiningProcessCounter"},
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(
            client=mock_client,
            joining_system_node=mock_joining_system,
            ns_app=2,
            profile=profile,
            ns_ijt=7,
        )
        process = MagicMock(
            JoiningProcessId="process-1",
            JoiningProcessOriginId="origin-1",
            AssociatedEntities=[],
        )
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")
        trigger._get_joining_process_list = AsyncMock(return_value=[process])
        identification = MagicMock(
            JoiningProcessId="process-1",
            JoiningProcessOriginId="origin-1",
        )
        trigger._make_process_identification = MagicMock(return_value=identification)
        call_method = AsyncMock(return_value=MagicMock(success=True, output_list=[]))

        with patch("helpers.method_caller.find_and_call_method", new=call_method):
            outcome = await trigger._trigger_intervention()

        assert outcome.triggered is True
        assert outcome.method == "IncrementJoiningProcessCounter"
        args = call_method.await_args
        assert args is not None
        assert args.args[3].Value == "urn:tool:1"
        assert args.args[4].Value is identification
        assert args.args[5].Value == 1
        assert args.kwargs["target_server_authorized"] is True

    async def test_joining_process_methods_use_ijt_namespace(self, profile, mock_client, mock_joining_system):
        trigger = StartSelectedJoiningResultTrigger(
            client=mock_client,
            joining_system_node=mock_joining_system,
            ns_app=2,
            profile=profile,
            ns_ijt=7,
            ns_di=5,
        )
        call_result = MagicMock(success=True, output_list=[])
        call_method = AsyncMock(return_value=call_result)
        jpm = MagicMock()

        with (
            patch("asyncua.ua.JoiningProcessIdentificationDataType", create=True, return_value=MagicMock()),
            patch("helpers.method_caller.find_and_call_method", new=call_method),
        ):
            await trigger._get_joining_process_list(jpm, "urn:tool:1")
            await trigger._select_joining_process(jpm, MagicMock(), "urn:tool:1")
            await trigger._start_selected_joining(jpm, "urn:tool:1", False)

        assert [call.args[2] for call in call_method.await_args_list] == [7, 7, 7]

    async def test_state_changing_not_allowed_returns_skip(self, blocked_profile, mock_client, mock_joining_system):
        trigger = self._make_trigger(blocked_profile, mock_client, mock_joining_system)
        outcome = await trigger.trigger_single(1)
        assert outcome.triggered is False
        assert "SelectJoiningProcess" in outcome.skip_reason

    async def test_no_jpm_node_returns_skip(self, profile, mock_client, mock_joining_system):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        with patch(
            "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._get_joining_process_management",
            new=AsyncMock(return_value=None),
        ):
            outcome = await trigger.trigger_single(1)
            assert outcome.triggered is False
            assert "JoiningProcessManagement" in outcome.skip_reason

    async def test_empty_process_list_returns_skip(self, profile, mock_client, mock_joining_system):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        mock_jpm = MagicMock()
        with (
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._get_joining_process_management",
                new=AsyncMock(return_value=mock_jpm),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._resolve_tool_piu",
                new=AsyncMock(return_value="urn:tool:1"),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._get_joining_process_list",
                new=AsyncMock(return_value=[]),
            ),
        ):
            outcome = await trigger.trigger_single(1)
            assert outcome.triggered is False
            assert "GetJoiningProcessList" in outcome.skip_reason

    def test_exact_match_selects_process_by_current_model_fields(self, mock_client, mock_joining_system):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "PROCESS-2",
                        "joining_process_origin_id": "ORIGIN-2",
                        "selection_name": "ProgramIndex_2",
                    }
                },
            }
        )
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        first = MagicMock(
            JoiningProcessId="PROCESS-1",
            JoiningProcessOriginId="ORIGIN-1",
            AssociatedEntities=[],
        )
        selection_entity = MagicMock(Name="SelectionName", EntityId="ProgramIndex_2")
        second = MagicMock(
            JoiningProcessId="PROCESS-2",
            JoiningProcessOriginId="ORIGIN-2",
            AssociatedEntities=[selection_entity],
        )

        assert trigger._choose_joining_process([first, second]) is second

    def test_exact_match_prefers_process_id_over_selection_name(self, mock_client, mock_joining_system):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "PROCESS-1",
                        "selection_name": "ProgramIndex_2",
                    }
                },
            }
        )
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        process = MagicMock(
            JoiningProcessId="PROCESS-1",
            JoiningProcessOriginId="ORIGIN-1",
            AssociatedEntities=[MagicMock(Name="SelectionName", EntityId="ProgramIndex_1")],
        )

        assert trigger._choose_joining_process([process]) is process

    def test_exact_match_process_id_takes_precedence_over_origin_id(self, mock_client, mock_joining_system):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "PROCESS-1",
                        "joining_process_origin_id": "STALE-ORIGIN",
                    }
                },
            }
        )
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        process = MagicMock(
            JoiningProcessId="PROCESS-1",
            JoiningProcessOriginId="CURRENT-ORIGIN",
            AssociatedEntities=[],
        )

        assert trigger._choose_joining_process([process]) is process

    def test_exact_match_falls_back_to_origin_when_process_id_is_stale(self, mock_client, mock_joining_system):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "STALE-PROCESS",
                        "joining_process_origin_id": "ORIGIN-2",
                    }
                },
            }
        )
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        process = MagicMock(
            JoiningProcessId="PROCESS-2",
            JoiningProcessOriginId="ORIGIN-2",
            AssociatedEntities=[],
        )

        assert trigger._choose_joining_process([process]) is process

    def test_name_only_exact_match_still_uses_advertised_selection_name(self, mock_client, mock_joining_system):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "selection_name": "ProgramIndex_2",
                    }
                },
            }
        )
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        process = MagicMock(
            JoiningProcessId="PROCESS-1",
            AssociatedEntities=[MagicMock(Name="SelectionName", EntityId="ProgramIndex_1")],
        )

        assert trigger._choose_joining_process([process]) is None

    def test_process_selection_diagnostics_list_available_identifiers(self, profile, mock_client, mock_joining_system):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        process = MagicMock(
            JoiningProcessId="PROCESS-1",
            JoiningProcessOriginId="ORIGIN-1",
            AssociatedEntities=[MagicMock(Name="SelectionName", EntityId="ProgramIndex_1")],
        )

        description = trigger._describe_joining_processes([process])

        assert description == "id='PROCESS-1', origin='ORIGIN-1', selection_name='ProgramIndex_1'"

    def test_process_identification_id_only_default_strategy(self, mock_client, mock_joining_system):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "PROCESS-1",
                        "joining_process_origin_id": "ORIGIN-1",
                    }
                },
            }
        )
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        process = MagicMock(
            JoiningProcessId="PROCESS-1",
            JoiningProcessOriginId="ORIGIN-1",
            AssociatedEntities=[MagicMock(Name="SelectionName", EntityId="SequenceIndex_1")],
        )

        with patch(
            "asyncua.ua.JoiningProcessIdentificationDataType",
            create=True,
            return_value=MagicMock(),
        ):
            identification = trigger._make_process_identification(process)

        assert identification.JoiningProcessId == "PROCESS-1"
        assert identification.JoiningProcessOriginId == ""
        assert identification.SelectionName == ""

    def test_process_identification_id_with_origin_strategy(self, mock_client, mock_joining_system):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "PROCESS-1",
                        "joining_process_origin_id": "ORIGIN-1",
                        "identifier_strategy": "id_with_origin",
                    }
                },
            }
        )
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        process = MagicMock(
            JoiningProcessId="PROCESS-1",
            JoiningProcessOriginId="ORIGIN-1",
            AssociatedEntities=[MagicMock(Name="SelectionName", EntityId="SequenceIndex_1")],
        )

        with patch(
            "asyncua.ua.JoiningProcessIdentificationDataType",
            create=True,
            return_value=MagicMock(),
        ):
            identification = trigger._make_process_identification(process)

        assert identification.JoiningProcessId == "PROCESS-1"
        assert identification.JoiningProcessOriginId == "ORIGIN-1"
        assert identification.SelectionName == ""

    def test_process_identification_id_with_selection_name_strategy(self, mock_client, mock_joining_system):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "PROCESS-1",
                        "joining_process_origin_id": "ORIGIN-1",
                        "identifier_strategy": "id_with_selection_name",
                    }
                },
            }
        )
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        process = MagicMock(
            JoiningProcessId="PROCESS-1",
            JoiningProcessOriginId="ORIGIN-1",
            AssociatedEntities=[MagicMock(Name="SelectionName", EntityId="SequenceIndex_1")],
        )

        with patch(
            "asyncua.ua.JoiningProcessIdentificationDataType",
            create=True,
            return_value=MagicMock(),
        ):
            identification = trigger._make_process_identification(process)

        assert identification.JoiningProcessId == "PROCESS-1"
        assert identification.JoiningProcessOriginId == ""
        assert identification.SelectionName == "SequenceIndex_1"

    def test_process_classification_extraction_helpers(self):
        from helpers.target_server_triggers import _process_classification

        assert _process_classification(None) is None

        # String digit classification
        p_str = MagicMock()
        p_str.JoiningProcessMetaData.Classification = "3"
        assert _process_classification(p_str) is JoiningProcessClassification.SYNC

        # Object with .value int
        class _EnumCls:
            value = 4

        p_enum = MagicMock()
        p_enum.JoiningProcessMetaData.Classification = _EnumCls()
        assert _process_classification(p_enum) is JoiningProcessClassification.BATCH

        # None classification
        p_none = MagicMock()
        p_none.JoiningProcessMetaData.Classification = None
        assert _process_classification(p_none) is None

        # Invalid string classification
        p_invalid = MagicMock()
        p_invalid.JoiningProcessMetaData.Classification = "invalid"
        assert _process_classification(p_invalid) is None

    def test_choose_joining_process_all_classification_types(self, profile, mock_client, mock_joining_system):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)

        p_prog = MagicMock(JoiningProcessId="PROG")
        p_prog.JoiningProcessMetaData.Classification = JoiningProcessClassification.PROGRAM
        p_sync = MagicMock(JoiningProcessId="SYNC")
        p_sync.JoiningProcessMetaData.Classification = JoiningProcessClassification.SYNC
        p_batch = MagicMock(JoiningProcessId="BATCH")
        p_batch.JoiningProcessMetaData.Classification = JoiningProcessClassification.BATCH
        p_job = MagicMock(JoiningProcessId="JOB")
        p_job.JoiningProcessMetaData.Classification = JoiningProcessClassification.JOB

        procs = [p_prog, p_sync, p_batch, p_job]

        assert trigger._choose_joining_process(procs, "single") is p_prog
        assert trigger._choose_joining_process(procs, "sync") is p_sync
        assert trigger._choose_joining_process(procs, "batch") is p_batch
        assert trigger._choose_joining_process(procs, "job") is p_job
        assert trigger._choose_joining_process(procs, "nonexistent") is None

    def test_uncertain_domain_status_is_rejected_with_message(self, profile, mock_client, mock_joining_system):
        from asyncua import ua

        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        result = MethodCallResult(
            success=True,
            output=[ua.StatusCode(0x40000000), "tool is not ready"],
        )

        assert trigger._method_succeeded("StartSelectedJoining", result) is False
        assert "tool is not ready" in trigger._last_method_failure

    def test_uncertain_service_status_can_be_observed_for_intervention_evidence(
        self, profile, mock_client, mock_joining_system
    ):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        result = MethodCallResult(
            success=False,
            error=RuntimeError("Uncertain"),
            status_code=0x40000000,
        )

        assert (
            trigger._method_succeeded(
                "IncrementJoiningProcessCounter",
                result,
                observe_uncertain=True,
            )
            is True
        )

    @pytest.mark.parametrize(
        ("result", "expected"),
        [
            (MethodCallResult(success=False, error=RuntimeError("service failure")), False),
            (MethodCallResult(success=True), True),
            (MethodCallResult(success=True, output=[0, "ok"]), True),
            (MethodCallResult(success=True, output=["vendor-specific"]), True),
        ],
    )
    def test_method_success_handles_service_and_output_shapes(
        self, profile, mock_client, mock_joining_system, result, expected
    ):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)

        assert trigger._method_succeeded("ExampleMethod", result) is expected

    async def test_namespace_index_is_discovered_once(self, profile, mock_joining_system):
        client = MagicMock()
        client.get_namespace_index = AsyncMock(return_value=7)
        trigger = self._make_trigger(profile, client, mock_joining_system)

        assert await trigger._resolve_ijt_namespace_index() == 7
        assert await trigger._resolve_ijt_namespace_index() == 7
        client.get_namespace_index.assert_awaited_once()

    def test_operation_completion_requires_tool_and_process_identifiers(
        self, profile, mock_client, mock_joining_system
    ):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        result = MagicMock(
            ResultMetaData=MagicMock(
                AssociatedEntities=[
                    MagicMock(EntityId="urn:tool:1"),
                    MagicMock(EntityId="PROCESS-1"),
                ]
            )
        )

        assert trigger._result_matches_context(result, "urn:tool:1", "PROCESS-1") is True
        assert trigger._result_matches_context(result, "urn:tool:2", "PROCESS-1") is False
        assert trigger._result_matches_context(result, "urn:tool:1", "PROCESS-2") is False

    def test_result_matches_context_is_case_and_whitespace_insensitive(self, profile, mock_client, mock_joining_system):
        """OPC UA servers frequently return GUID identifiers in a different case
        than the profile/GetJoiningProcessList value; correlation must still hold."""
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        result = MagicMock(
            ResultMetaData=MagicMock(
                AssociatedEntities=[
                    MagicMock(EntityId="123E4567-E89B-12D3-A456-426614174000"),
                    MagicMock(EntityId="ABCDEF01-2345-6789-ABCD-EF0123456789"),
                ]
            )
        )
        assert (
            trigger._result_matches_context(
                result,
                " 123e4567-e89b-12d3-a456-426614174000 ",
                "abcdef01-2345-6789-abcd-ef0123456789",
            )
            is True
        )
        assert trigger._result_matches_context(result, "123e4567-e89b-12d3-a456-426614174000", "other") is False

    def test_result_matches_context_accepts_origin_id_fallback(self, profile, mock_client, mock_joining_system):
        """Servers that only tag the result with the origin id must still correlate."""
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        result = MagicMock(
            ResultMetaData=MagicMock(
                AssociatedEntities=[
                    MagicMock(EntityId="urn:tool:1"),
                    MagicMock(EntityId="ORIGIN-1"),
                ]
            )
        )
        # Neither id alone: the configured process id is absent from the result.
        assert trigger._result_matches_context(result, "urn:tool:1", "PROCESS-1") is False
        # With the origin id supplied, the fallback matches.
        assert trigger._result_matches_context(result, "urn:tool:1", "PROCESS-1", "origin-1") is True
        # Tool correlation is still mandatory.
        assert trigger._result_matches_context(result, "urn:tool:2", "PROCESS-1", "ORIGIN-1") is False

    def test_result_matches_context_without_configured_process_ids(self, profile, mock_client, mock_joining_system):
        """When no process identifier is configured only the Tool must correlate."""
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        result = MagicMock(ResultMetaData=MagicMock(AssociatedEntities=[MagicMock(EntityId="urn:tool:1")]))
        assert trigger._result_matches_context(result, "urn:tool:1", "") is True
        assert trigger._result_matches_context(result, "urn:tool:9", "") is False

    def test_intermediate_child_program_evidence_matches_tool_not_parent_job(
        self, profile, mock_client, mock_joining_system
    ):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        result = MagicMock(
            ResultMetaData=MagicMock(
                AssociatedEntities=[
                    MagicMock(EntityId="urn:tool:1"),
                    MagicMock(EntityId="ChildProgram_1"),
                ]
            )
        )

        assert trigger._result_matches_context(result, "urn:tool:1", "ParentJob_1") is False
        assert trigger._result_matches_tool_context(result, "urn:tool:1") is True

    async def test_select_failure_returns_skip(self, profile, mock_client, mock_joining_system):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        mock_jpm = MagicMock()
        mock_process = MagicMock()
        mock_process.JoiningProcessMetaData = SimpleNamespace(Classification=2)
        with (
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._get_joining_process_management",
                new=AsyncMock(return_value=mock_jpm),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._resolve_tool_piu",
                new=AsyncMock(return_value="urn:tool:1"),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._get_joining_process_list",
                new=AsyncMock(return_value=[mock_process]),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._select_joining_process",
                new=AsyncMock(return_value=False),
            ),
        ):
            outcome = await trigger.trigger_single(1)
            assert outcome.triggered is False
            assert "SelectJoiningProcess" in outcome.skip_reason

    async def test_successful_workflow_returns_triggered(self, profile, mock_client, mock_joining_system):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        mock_jpm = MagicMock()
        mock_process = MagicMock()
        mock_process.JoiningProcessId = "PROG01"
        mock_process.JoiningProcessOriginId = "ORIGIN01"
        mock_process.JoiningProcessMetaData = SimpleNamespace(Classification=2)
        with (
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._get_joining_process_management",
                new=AsyncMock(return_value=mock_jpm),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._resolve_tool_piu",
                new=AsyncMock(return_value="urn:tool:serial:1"),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._get_joining_process_list",
                new=AsyncMock(return_value=[mock_process]),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._select_joining_process",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._start_selected_joining",
                new=AsyncMock(return_value=True),
            ),
        ):
            outcome = await trigger.trigger_single(1)
            assert outcome.triggered is True
            assert isinstance(outcome, TargetServerTriggerOutcome)
            assert outcome.trigger_mode == "start_selected_joining"
            assert outcome.product_instance_uri == "urn:tool:serial:1"
            assert outcome.operation_count == 1
            assert outcome.starts_issued == 1
            # No completion subscription on a single-operation run — the test
            # itself verifies the result, so the trigger confirms nothing.
            assert outcome.results_confirmed == 0

    async def test_multi_operation_workflow_waits_for_correlated_completion(
        self, profile, mock_client, mock_joining_system
    ):
        subscription_client = MagicMock()
        trigger = StartSelectedJoiningResultTrigger(
            client=mock_client,
            joining_system_node=mock_joining_system,
            ns_app=2,
            profile=profile,
            ns_ijt=7,
            subscription_client=subscription_client,
        )
        mock_jpm = MagicMock()
        mock_process = MagicMock()
        mock_process.JoiningProcessId = "PROG01"
        mock_process.JoiningProcessOriginId = "ORIGIN01"
        completion_collector = MagicMock()
        completion_collector.__aenter__ = AsyncMock(return_value=completion_collector)
        completion_collector.__aexit__ = AsyncMock(return_value=None)
        completion_collector.discard_pending = MagicMock(return_value=0)
        completion_collector.collect_pending_terminal = MagicMock(return_value=None)
        completion_collector.collect_correlated_operation_outcome = AsyncMock(
            return_value=CorrelatedOperationOutcome(operation_confirmed=True)
        )

        with (
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._get_joining_process_management",
                new=AsyncMock(return_value=mock_jpm),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._resolve_tool_piu",
                new=AsyncMock(return_value="urn:tool:serial:1"),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._get_joining_process_list",
                new=AsyncMock(return_value=[mock_process]),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._select_joining_process",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._start_selected_joining",
                new=AsyncMock(return_value=True),
            ) as start,
            patch("helpers.result_collector.ResultCollector", return_value=completion_collector),
        ):
            outcome = await trigger._run_workflow(operation_count=2)

        assert outcome.triggered is True
        assert outcome.operation_count == 2
        assert outcome.starts_issued == 2
        assert outcome.results_confirmed == 2
        assert start.await_count == 2
        assert completion_collector.discard_pending.call_count == 1
        assert completion_collector.collect_correlated_operation_outcome.await_count == 2

    async def test_unconfirmed_operation_reports_starts_and_confirmations_separately(
        self, profile, mock_client, mock_joining_system
    ):
        """The second start is accepted but never confirmed by a correlated result:
        the outcome must say 2 starts issued, 1 result confirmed."""
        subscription_client = MagicMock()
        trigger = StartSelectedJoiningResultTrigger(
            client=mock_client,
            joining_system_node=mock_joining_system,
            ns_app=2,
            profile=profile,
            ns_ijt=7,
            subscription_client=subscription_client,
        )
        mock_process = MagicMock()
        mock_process.JoiningProcessId = "PROG01"
        mock_process.JoiningProcessOriginId = "ORIGIN01"
        completion_collector = MagicMock()
        completion_collector.__aenter__ = AsyncMock(return_value=completion_collector)
        completion_collector.__aexit__ = AsyncMock(return_value=None)
        completion_collector.discard_pending = MagicMock(return_value=0)
        completion_collector.collect_pending_terminal = MagicMock(return_value=None)
        completion_collector.collect_correlated_operation_outcome = AsyncMock(
            side_effect=[
                CorrelatedOperationOutcome(operation_confirmed=True),
                CorrelatedOperationOutcome(operation_confirmed=False, timed_out=True),
            ]
        )

        with (
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._get_joining_process_management",
                new=AsyncMock(return_value=MagicMock()),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._resolve_tool_piu",
                new=AsyncMock(return_value="urn:tool:serial:1"),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._get_joining_process_list",
                new=AsyncMock(return_value=[mock_process]),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._select_joining_process",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._start_selected_joining",
                new=AsyncMock(return_value=True),
            ),
            patch("helpers.result_collector.ResultCollector", return_value=completion_collector),
        ):
            outcome = await trigger._run_workflow(operation_count=2)

        assert outcome.triggered is False
        assert outcome.starts_issued == 2
        assert outcome.results_confirmed == 1
        assert outcome.operation_count == outcome.starts_issued

    async def test_failed_start_counts_neither_the_start_nor_a_result(self, profile, mock_client, mock_joining_system):
        subscription_client = MagicMock()
        trigger = StartSelectedJoiningResultTrigger(
            client=mock_client,
            joining_system_node=mock_joining_system,
            ns_app=2,
            profile=profile,
            ns_ijt=7,
            subscription_client=subscription_client,
        )
        mock_process = MagicMock()
        mock_process.JoiningProcessId = "PROG01"
        mock_process.JoiningProcessOriginId = "ORIGIN01"
        completion_collector = MagicMock()
        completion_collector.__aenter__ = AsyncMock(return_value=completion_collector)
        completion_collector.__aexit__ = AsyncMock(return_value=None)
        completion_collector.discard_pending = MagicMock(return_value=0)
        completion_collector.collect_pending_terminal = MagicMock(return_value=None)
        completion_collector.collect_correlated_operation_outcome = AsyncMock(
            return_value=CorrelatedOperationOutcome(operation_confirmed=True)
        )

        with (
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._get_joining_process_management",
                new=AsyncMock(return_value=MagicMock()),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._resolve_tool_piu",
                new=AsyncMock(return_value="urn:tool:serial:1"),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._get_joining_process_list",
                new=AsyncMock(return_value=[mock_process]),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._select_joining_process",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "helpers.target_server_triggers.StartSelectedJoiningResultTrigger._start_selected_joining",
                new=AsyncMock(side_effect=[True, False]),
            ),
            patch("helpers.result_collector.ResultCollector", return_value=completion_collector),
        ):
            outcome = await trigger._run_workflow(operation_count=2)

        assert outcome.triggered is False
        assert outcome.starts_issued == 1
        assert outcome.results_confirmed == 1
        assert outcome.operation_count == 1

    async def test_batch_workflow_selects_once_and_starts_configured_count(self, mock_client, mock_joining_system):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": "start_selected_joining", "timeout_seconds": 30}},
                "cu_execution": {
                    "state_changing_methods": {
                        "default_policy": "require_explicit_opt_in",
                        "allowed_methods": ["SelectJoiningProcess", "StartSelectedJoining"],
                    }
                },
                "workflow_execution": {
                    "max_start_invocations": 3,
                },
            }
        )
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        trigger._run_workflow = AsyncMock(return_value=TargetServerTriggerOutcome(triggered=True, operation_count=3))

        outcome = await trigger.trigger_batch_or_sync(
            classification=ResultClassification.SYNC_RESULT,
            num_children=3,
        )

        trigger._run_workflow.assert_awaited_once_with(
            3,
            classification=ResultClassification.SYNC_RESULT,
        )
        assert outcome.operation_count == 3

    async def test_batch_workflow_respects_single_start_cap(self, mock_client, mock_joining_system):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": "start_selected_joining", "timeout_seconds": 30}},
                "cu_execution": {
                    "state_changing_methods": {
                        "default_policy": "require_explicit_opt_in",
                        "allowed_methods": ["SelectJoiningProcess", "StartSelectedJoining"],
                    }
                },
                "workflow_execution": {
                    "max_start_invocations": 1,
                },
            }
        )
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        trigger._run_workflow = AsyncMock(return_value=TargetServerTriggerOutcome(triggered=True, operation_count=1))

        outcome = await trigger.trigger_batch_or_sync(
            classification=ResultClassification.BATCH_RESULT,
            num_children=1,
        )
        trigger._run_workflow.assert_awaited_once_with(
            1,
            classification=ResultClassification.BATCH_RESULT,
        )
        assert outcome.operation_count == 1

    async def test_job_workflow_uses_configured_operation_count(self, mock_client, mock_joining_system):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": "start_selected_joining", "timeout_seconds": 30}},
                "cu_execution": {
                    "state_changing_methods": {
                        "default_policy": "require_explicit_opt_in",
                        "allowed_methods": ["SelectJoiningProcess", "StartSelectedJoining"],
                    }
                },
                "workflow_execution": {
                    "max_start_invocations": 6,
                },
            }
        )
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        trigger._run_workflow = AsyncMock(return_value=TargetServerTriggerOutcome(triggered=True, operation_count=6))

        outcome = await trigger.trigger_job()

        trigger._run_workflow.assert_awaited_once_with(
            6,
            classification=ResultClassification.JOB_RESULT,
        )
        assert outcome.operation_count == 6

    async def test_bulk_results_not_supported(self, profile, mock_client, mock_joining_system):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        outcome = await trigger.trigger_bulk_results(1, False, 0, 10)
        assert outcome.triggered is False
        assert "Bulk result generation is not supported" in outcome.skip_reason


# ---------------------------------------------------------------------------
# make_target_server_result_trigger factory
# ---------------------------------------------------------------------------


class TestMakeTargetServerResultTrigger:
    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_js(self):
        return MagicMock()

    def test_start_selected_joining_mode_returns_correct_trigger(self, mock_client, mock_js):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": "start_selected_joining"}},
            }
        )
        trigger = make_target_server_result_trigger(mock_client, mock_js, 2, profile)
        assert isinstance(trigger, StartSelectedJoiningResultTrigger)

    def test_start_selected_joining_receives_separate_subscription_client(self, mock_client, mock_js):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": "start_selected_joining"}},
            }
        )
        subscription_client = MagicMock()

        trigger = make_target_server_result_trigger(
            mock_client,
            mock_js,
            2,
            profile,
            subscription_client=subscription_client,
        )

        assert isinstance(trigger, StartSelectedJoiningResultTrigger)
        assert trigger._subscription_client is subscription_client

    def test_manual_trigger_mode_returns_manual_trigger(self, mock_client, mock_js):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": "manual_trigger"}},
            }
        )
        trigger = make_target_server_result_trigger(mock_client, mock_js, 2, profile)
        assert isinstance(trigger, ManualResultTrigger)

    def test_none_mode_returns_external_trigger(self, mock_client, mock_js):
        profile = build_default_profile()
        trigger = make_target_server_result_trigger(mock_client, mock_js, 2, profile)
        assert isinstance(trigger, ExternalResultTrigger)

    def test_observe_only_mode_returns_external_trigger(self, mock_client, mock_js):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": "observe_only"}},
            }
        )
        trigger = make_target_server_result_trigger(mock_client, mock_js, 2, profile)
        assert isinstance(trigger, ExternalResultTrigger)

    def test_opcua_trigger_class_override(self, mock_client, mock_js):
        profile = build_default_profile()
        import os

        # Use SimulatorResultTrigger as the override target — it accepts (client, folder, ns_app)
        # which matches the args the factory passes to override classes.
        with patch.dict(
            os.environ,
            {"OPCUA_TRIGGER_CLASS": "helpers.trigger.SimulatorResultTrigger"},
        ):
            from helpers.trigger import SimulatorResultTrigger

            trigger = make_target_server_result_trigger(mock_client, mock_js, 2, profile)
            assert isinstance(trigger, SimulatorResultTrigger)


# ---------------------------------------------------------------------------
# make_target_server_event_trigger factory
# ---------------------------------------------------------------------------


class TestMakeTargetServerEventTrigger:
    def test_manual_trigger_mode_returns_manual(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {"event": {"mode": "manual_trigger"}},
            }
        )
        trigger = make_target_server_event_trigger(profile)
        assert isinstance(trigger, ManualEventTrigger)

    def test_observe_only_mode_returns_external(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {"event": {"mode": "observe_only"}},
            }
        )
        trigger = make_target_server_event_trigger(profile)
        assert isinstance(trigger, ExternalEventTrigger)

    def test_none_mode_returns_external(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {"event": {"mode": "none"}},
            }
        )
        trigger = make_target_server_event_trigger(profile)
        assert isinstance(trigger, ExternalEventTrigger)


# ---------------------------------------------------------------------------
# simulate_methods trigger mode (SUT manifest declaring simulator helpers)
# ---------------------------------------------------------------------------


def _simulate_profile(**modes):
    triggers = {kind: {"mode": mode} for kind, mode in modes.items()}
    return build_execution_profile({"schema_version": 1, "profile_name": "Sim SUT", "triggers": triggers})


class TestSimulateMethodsResultTrigger:
    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_js(self):
        return MagicMock()

    def test_simulate_methods_returns_the_existing_simulator_trigger(self, mock_client, mock_js):
        folder = MagicMock()
        trigger = make_target_server_result_trigger(
            mock_client,
            mock_js,
            2,
            _simulate_profile(result="simulate_methods"),
            simulate_results_folder=folder,
        )
        assert isinstance(trigger, SimulatorResultTrigger)
        assert trigger.is_simulator is True

    def test_missing_helper_folder_is_a_configuration_error(self, mock_client, mock_js):
        with pytest.raises(TargetServerTriggerConfigurationError) as exc:
            make_target_server_result_trigger(mock_client, mock_js, 2, _simulate_profile(result="simulate_methods"))
        message = str(exc.value)
        assert "triggers.result.mode" in message
        assert "SimulateResults" in message

    def test_missing_helper_folder_never_degrades_to_external(self, mock_client, mock_js):
        with pytest.raises(TargetServerTriggerConfigurationError):
            make_target_server_result_trigger(mock_client, mock_js, 2, _simulate_profile(result="simulate_methods"))

    async def test_builder_locates_the_folder_like_the_simulator_fixture(self, mock_client, mock_js, monkeypatch):
        import helpers.target_server_triggers as tst

        folder = MagicMock()
        seen: list[tuple] = []

        async def fake_find(js, ns_app, child):
            seen.append((js, ns_app, child))
            return folder

        monkeypatch.setattr(tst, "find_simulation_child", fake_find)
        trigger = await tst.build_target_server_result_trigger(
            mock_client, mock_js, 2, _simulate_profile(result="simulate_methods")
        )
        assert isinstance(trigger, SimulatorResultTrigger)
        assert seen == [(mock_js, 2, BN.SIMULATE_RESULTS_FOLDER)]

    async def test_builder_skips_discovery_for_other_modes(self, mock_client, mock_js, monkeypatch):
        import helpers.target_server_triggers as tst

        async def fail_find(js, ns_app, child):  # pragma: no cover - must not run
            raise AssertionError("simulator discovery must not run for non-simulate modes")

        monkeypatch.setattr(tst, "find_simulation_child", fail_find)
        trigger = await tst.build_target_server_result_trigger(mock_client, mock_js, None, build_default_profile())
        assert isinstance(trigger, ExternalResultTrigger)

    async def test_builder_reports_absent_helpers_as_configuration_error(self, mock_client, mock_js, monkeypatch):
        import helpers.target_server_triggers as tst

        async def no_folder(js, ns_app, child):
            return None

        monkeypatch.setattr(tst, "find_simulation_child", no_folder)
        with pytest.raises(TargetServerTriggerConfigurationError):
            await tst.build_target_server_result_trigger(
                mock_client, mock_js, None, _simulate_profile(result="simulate_methods")
            )


class TestSimulateMethodsEventTrigger:
    def test_simulate_methods_returns_the_existing_simulator_event_trigger(self):
        trigger = make_target_server_event_trigger(
            _simulate_profile(event="simulate_methods", condition="simulate_methods"),
            client=MagicMock(),
            ns_app=2,
            simulate_events_folder=MagicMock(),
        )
        assert isinstance(trigger, SimulatorEventTrigger)

    def test_missing_helper_folder_is_a_configuration_error(self):
        with pytest.raises(TargetServerTriggerConfigurationError) as exc:
            make_target_server_event_trigger(
                _simulate_profile(event="simulate_methods", condition="simulate_methods"), client=MagicMock()
            )
        assert "SimulateEventsAndConditions" in str(exc.value)

    def test_simulated_conditions_can_accompany_observed_events(self):
        trigger = make_target_server_event_trigger(
            _simulate_profile(event="observe_only", condition="simulate_methods"),
            client=MagicMock(),
            ns_app=2,
            simulate_events_folder=MagicMock(),
        )
        assert isinstance(trigger, SplitEventTrigger)
        assert isinstance(trigger._events, ExternalEventTrigger)
        assert isinstance(trigger._conditions, SimulatorEventTrigger)

    def test_condition_mode_error_names_the_condition_field(self):
        with pytest.raises(TargetServerTriggerConfigurationError, match="triggers.condition.mode"):
            make_target_server_event_trigger(
                _simulate_profile(event="observe_only", condition="simulate_methods"), client=MagicMock()
            )

    async def test_split_trigger_routes_each_call_to_its_adapter(self):
        events = MagicMock()
        events.is_simulator = False
        events.active_event_timeout_s = 7.0
        events.passive_observation_timeout_s = 3.0
        events.trigger_event = AsyncMock(return_value=TriggerOutcome(triggered=True, method="events"))
        events.trigger_bulk_events = AsyncMock(return_value=TriggerOutcome(triggered=True, method="bulk"))
        conditions = MagicMock()
        conditions.trigger_condition = AsyncMock(return_value=TriggerOutcome(triggered=True, method="condition"))

        split = SplitEventTrigger(events, conditions)
        assert split.is_simulator is False
        assert split.active_event_timeout_s == 7.0
        assert split.passive_observation_timeout_s == 3.0
        assert (await split.trigger_event(1, 2)).method == "events"
        assert (await split.trigger_bulk_events(1, 2, 3, 4)).method == "bulk"
        assert (await split.trigger_condition(1)).method == "condition"
        events.trigger_event.assert_awaited_once_with(1, 2)
        conditions.trigger_condition.assert_awaited_once_with(1)

    async def test_builder_locates_the_events_folder(self, monkeypatch):
        import helpers.target_server_triggers as tst

        folder = MagicMock()
        seen: list[tuple] = []

        async def fake_find(js, ns_app, child):
            seen.append((ns_app, child))
            return folder

        monkeypatch.setattr(tst, "find_simulation_child", fake_find)
        trigger = await tst.build_target_server_event_trigger(
            MagicMock(),
            MagicMock(),
            2,
            _simulate_profile(event="simulate_methods", condition="simulate_methods"),
        )
        assert isinstance(trigger, SimulatorEventTrigger)
        assert seen == [(2, BN.SIMULATE_EVENTS_AND_CONDITIONS)]

    async def test_builder_skips_discovery_for_other_modes(self, monkeypatch):
        import helpers.target_server_triggers as tst

        async def fail_find(js, ns_app, child):  # pragma: no cover - must not run
            raise AssertionError("simulator discovery must not run for non-simulate modes")

        monkeypatch.setattr(tst, "find_simulation_child", fail_find)
        trigger = await tst.build_target_server_event_trigger(MagicMock(), MagicMock(), None, build_default_profile())
        assert isinstance(trigger, ExternalEventTrigger)

    async def test_builder_reports_absent_helpers_as_configuration_error(self, monkeypatch):
        import helpers.target_server_triggers as tst

        async def no_folder(js, ns_app, child):
            return None

        monkeypatch.setattr(tst, "find_simulation_child", no_folder)
        with pytest.raises(TargetServerTriggerConfigurationError):
            await tst.build_target_server_event_trigger(
                MagicMock(), MagicMock(), 2, _simulate_profile(event="simulate_methods")
            )


class TestSimulatorManifestUsesSimulateMethods:
    """The checked-in simulator manifest must drive the real simulator triggers."""

    def test_simulator_manifest_declares_simulate_methods(self):
        from helpers.sut_manifest import build_preset

        profile = build_preset("simulator").to_execution_profile()
        assert profile.triggers.result.mode == "simulate_methods"
        assert profile.triggers.event.mode == "simulate_methods"
        assert profile.triggers.condition.mode == "simulate_methods"

    def test_simulator_manifest_yields_simulator_triggers(self):
        from helpers.sut_manifest import build_preset

        profile = build_preset("simulator").to_execution_profile()
        result = make_target_server_result_trigger(
            MagicMock(), MagicMock(), 2, profile, simulate_results_folder=MagicMock()
        )
        events = make_target_server_event_trigger(
            profile, client=MagicMock(), ns_app=2, simulate_events_folder=MagicMock()
        )
        assert isinstance(result, SimulatorResultTrigger)
        assert isinstance(events, SimulatorEventTrigger)


# ---------------------------------------------------------------------------
# Extended branch coverage for Target Server triggers
# ---------------------------------------------------------------------------


class TestTargetServerTriggersExtendedBranches:
    @pytest.fixture
    def base_profile(self):
        return build_execution_profile(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://localhost:40451"},
                "triggers": {"result": {"mode": "start_selected_joining"}},
                "cu_execution": {
                    "state_changing_methods": {
                        "default_policy": "allow_all",
                    }
                },
            }
        )

    @pytest.mark.asyncio
    async def test_enable_tool_asset_management_none(self, base_profile):
        mock_client = MagicMock()
        mock_client.get_namespace_index = AsyncMock(return_value=2)
        trigger = StartSelectedJoiningResultTrigger(mock_client, MagicMock(), 2, base_profile)
        with patch("helpers.node_discovery.find_child_by_browse_name", AsyncMock(return_value=None)):
            res = await trigger._enable_tool("urn:tool:1")
            assert res is False

    @pytest.mark.asyncio
    async def test_enable_tool_method_set_none(self, base_profile):
        mock_client = MagicMock()
        mock_client.get_namespace_index = AsyncMock(return_value=2)
        trigger = StartSelectedJoiningResultTrigger(mock_client, MagicMock(), 2, base_profile)
        with patch("helpers.node_discovery.find_child_by_browse_name", AsyncMock(return_value=MagicMock())):
            with patch("helpers.node_discovery.find_method_set", AsyncMock(return_value=None)):
                res = await trigger._enable_tool("urn:tool:1")
                assert res is False

    @pytest.mark.asyncio
    async def test_ensure_tool_enabled_always_policy(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "extension_fields": {"enable_asset_policy": "always"},
                    "state_changing_methods": {"default_policy": "allow_all"},
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        trigger._enable_tool = AsyncMock(return_value=True)
        res = await trigger._ensure_tool_enabled("urn:tool:1")
        assert res is True
        trigger._enable_tool.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resolve_tool_piu_discovery_exception(self, base_profile):
        mock_client = MagicMock()
        mock_client.get_namespace_index = AsyncMock(side_effect=RuntimeError("Discovery error"))
        trigger = StartSelectedJoiningResultTrigger(mock_client, MagicMock(), 2, base_profile)
        piu = await trigger._resolve_tool_piu()
        assert piu == ""

    @pytest.mark.asyncio
    async def test_get_joining_process_list_failure_and_scalar(self, base_profile):
        from helpers.method_caller import MethodCallResult

        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, base_profile)
        trigger._resolve_ijt_namespace_index = AsyncMock(return_value=2)

        with patch(
            "helpers.method_caller.find_and_call_method",
            AsyncMock(return_value=MethodCallResult(success=False, error=Exception("Fail"))),
        ):
            res = await trigger._get_joining_process_list(MagicMock(), "urn:tool:1")
            assert res == []

        with patch(
            "helpers.method_caller.find_and_call_method",
            AsyncMock(return_value=MethodCallResult(success=True, output="single_process_obj")),
        ):
            res2 = await trigger._get_joining_process_list(MagicMock(), "urn:tool:1")
            assert res2 == ["single_process_obj"]

        with patch(
            "helpers.method_caller.find_and_call_method",
            AsyncMock(return_value=MethodCallResult(success=True, output=[("p1", "p2")])),
        ):
            res3 = await trigger._get_joining_process_list(MagicMock(), "urn:tool:1")
            assert res3 == ["p1", "p2"]

    def test_make_process_identification_ua_attribute_error(self, base_profile):
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, base_profile)
        with patch("asyncua.ua", spec=[]):
            res = trigger._make_process_identification(MagicMock())
            assert res is None

    @pytest.mark.asyncio
    async def test_trigger_intervention_unsupported_method(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "extension_fields": {"intervention_method": "NonExistentMethod"},
                    "state_changing_methods": {"default_policy": "allow_all"},
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        outcome = await trigger._trigger_intervention()
        assert outcome.triggered is False
        assert "Unsupported intervention_method" in (outcome.skip_reason or "")

    @pytest.mark.asyncio
    async def test_trigger_intervention_disallowed_method(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "extension_fields": {"intervention_method": "IncrementJoiningProcessCounter"},
                    "state_changing_methods": {"default_policy": "require_explicit_opt_in", "allowed_methods": []},
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        outcome = await trigger._trigger_intervention()
        assert outcome.triggered is False
        assert "not allowed" in (outcome.skip_reason or "")

    @pytest.mark.asyncio
    async def test_trigger_intervention_abort_joining_process(self, base_profile):
        from helpers.method_caller import MethodCallResult

        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "extension_fields": {
                        "intervention_method": "AbortJoiningProcess",
                        "intervention_message": "Intervention text",
                    },
                    "state_changing_methods": {"default_policy": "allow_all"},
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")
        trigger._get_joining_process_list = AsyncMock(return_value=[MagicMock(JoiningProcessId="P1")])
        trigger._resolve_ijt_namespace_index = AsyncMock(return_value=2)

        with patch("asyncua.ua.JoiningProcessIdentificationDataType", create=True, return_value=MagicMock()):
            with patch(
                "helpers.method_caller.find_and_call_method",
                AsyncMock(return_value=MethodCallResult(success=True, output=0)),
            ):
                outcome = await trigger._trigger_intervention()
                assert outcome.triggered is True

    @pytest.mark.asyncio
    async def test_trigger_intervention_increment_count(self, base_profile):
        from helpers.method_caller import MethodCallResult

        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "extension_fields": {
                        "intervention_method": "IncrementJoiningProcessCounter",
                        "intervention_count": 3,
                    },
                    "state_changing_methods": {"default_policy": "allow_all"},
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")
        trigger._get_joining_process_list = AsyncMock(return_value=[MagicMock(JoiningProcessId="P1")])
        trigger._resolve_ijt_namespace_index = AsyncMock(return_value=2)

        with patch("asyncua.ua.JoiningProcessIdentificationDataType", create=True, return_value=MagicMock()):
            with patch(
                "helpers.method_caller.find_and_call_method",
                AsyncMock(return_value=MethodCallResult(success=True, output=0)),
            ):
                outcome = await trigger._trigger_intervention()
                assert outcome.triggered is True

    @pytest.mark.asyncio
    async def test_trigger_intervention_jpm_none_or_process_none(self, base_profile):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "extension_fields": {"intervention_method": "IncrementJoiningProcessCounter"},
                    "state_changing_methods": {"default_policy": "allow_all"},
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        trigger._get_joining_process_management = AsyncMock(return_value=None)
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")
        o1 = await trigger._trigger_intervention()
        assert o1.triggered is False

        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._get_joining_process_list = AsyncMock(return_value=[])
        o2 = await trigger._trigger_intervention()
        assert o2.triggered is False

    @pytest.mark.asyncio
    async def test_read_tool_enabled_calls_discovery(self, base_profile):
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, base_profile)
        trigger._client.get_namespace_index = AsyncMock(return_value=2)
        with patch("helpers.node_discovery.read_tool_enabled", AsyncMock(return_value=True)):
            res = await trigger._read_tool_enabled("urn:tool:1")
            assert res is True

    @pytest.mark.asyncio
    async def test_resolve_tool_piu_from_profile_directly(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {"tool": {"product_instance_uri": "urn:tool:explicit"}},
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        assert await trigger._resolve_tool_piu() == "urn:tool:explicit"

    @pytest.mark.asyncio
    async def test_run_workflow_enable_tool_fails(self, base_profile):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "state_changing_methods": {
                        "default_policy": "require_explicit_opt_in",
                        "allowed_methods": ["EnableAsset", "SelectJoiningProcess", "StartSelectedJoining"],
                    }
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")
        trigger._ensure_tool_enabled = AsyncMock(return_value=False)
        outcome = await trigger._run_workflow(1)
        assert outcome.triggered is False
        assert "EnableAsset failed" in (outcome.skip_reason or "")

    @pytest.mark.asyncio
    async def test_run_workflow_no_matching_process(self, base_profile):
        mock_client = MagicMock()
        mock_client.get_namespace_index = AsyncMock(return_value=2)
        trigger = StartSelectedJoiningResultTrigger(mock_client, MagicMock(), 2, base_profile)
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")
        trigger._ensure_tool_enabled = AsyncMock(return_value=True)
        trigger._get_joining_process_list = AsyncMock(return_value=[MagicMock(JoiningProcessId="P1")])
        trigger._choose_joining_process = MagicMock(return_value=None)
        outcome = await trigger._run_workflow(1)
        assert outcome.triggered is False
        assert "No joining process matched" in (outcome.skip_reason or "")

    @pytest.mark.asyncio
    async def test_run_workflow_multi_operation_without_subscription_client(self, base_profile):
        mock_client = MagicMock()
        mock_client.get_namespace_index = AsyncMock(return_value=2)
        trigger = StartSelectedJoiningResultTrigger(mock_client, MagicMock(), 2, base_profile, subscription_client=None)
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")
        trigger._ensure_tool_enabled = AsyncMock(return_value=True)
        trigger._get_joining_process_list = AsyncMock(return_value=[MagicMock(JoiningProcessId="P1")])
        trigger._select_joining_process = AsyncMock(return_value=True)
        outcome = await trigger._run_workflow(2)
        assert outcome.triggered is False
        assert "requires a separate subscription client" in (outcome.skip_reason or "")

    @pytest.mark.asyncio
    async def test_run_workflow_start_selected_joining_fails(self, base_profile):
        mock_client = MagicMock()
        mock_client.get_namespace_index = AsyncMock(return_value=2)
        trigger = StartSelectedJoiningResultTrigger(mock_client, MagicMock(), 2, base_profile)
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")
        trigger._ensure_tool_enabled = AsyncMock(return_value=True)
        trigger._get_joining_process_list = AsyncMock(return_value=[MagicMock(JoiningProcessId="P1")])
        trigger._select_joining_process = AsyncMock(return_value=True)
        trigger._start_selected_joining = AsyncMock(return_value=False)
        outcome = await trigger._run_workflow(1)
        assert outcome.triggered is False
        assert "StartSelectedJoining failed" in (outcome.skip_reason or "")

    @pytest.mark.asyncio
    async def test_select_joining_process_none_identification(self, base_profile):
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, base_profile)
        trigger._make_process_identification = MagicMock(return_value=None)
        assert await trigger._select_joining_process(MagicMock(), MagicMock(), "urn:tool:1") is False

    @pytest.mark.asyncio
    async def test_trigger_intervention_identification_none_and_method_fail(self, base_profile):
        from helpers.method_caller import MethodCallResult

        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "extension_fields": {"intervention_method": "IncrementJoiningProcessCounter"},
                    "state_changing_methods": {"default_policy": "allow_all"},
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")
        trigger._get_joining_process_list = AsyncMock(return_value=[MagicMock(JoiningProcessId="P1")])
        trigger._make_process_identification = MagicMock(return_value=None)
        o1 = await trigger._trigger_intervention()
        assert o1.triggered is False
        assert "unavailable" in (o1.skip_reason or "")

        trigger._make_process_identification = MagicMock(return_value=MagicMock(JoiningProcessId="P1"))
        trigger._resolve_ijt_namespace_index = AsyncMock(return_value=2)
        with patch(
            "helpers.method_caller.find_and_call_method",
            AsyncMock(return_value=MethodCallResult(success=True, output=[1, "Domain Error"])),
        ):
            o2 = await trigger._trigger_intervention()
            assert o2.triggered is False
            assert "failed for process" in (o2.skip_reason or "")

    def test_method_succeeded_exception_branch(self, base_profile):
        from helpers.method_caller import MethodCallResult

        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, base_profile)

        class FaultyStatusCode:
            def is_good(self):
                raise TypeError("status code error")

        with patch("asyncua.ua.StatusCode", FaultyStatusCode):
            res = trigger._method_succeeded("Method", MethodCallResult(success=True, output=[FaultyStatusCode()]))
            assert res is True

    def test_process_field_and_selection_branches(self):
        # Empty field resolution
        res = StartSelectedJoiningResultTrigger._process_field(MagicMock(spec=[]), "field1", "field2")
        assert res == ""

        # Exact match with selection name match (line 383)
        p_name = MagicMock(AssociatedEntities=[MagicMock(Name="SelectionName", EntityId="MatchName")])
        profile_name = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {"joining_process": {"policy": "exact_match", "selection_name": "MatchName"}},
            }
        )
        t_name = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile_name)
        assert t_name._choose_joining_process([p_name]) is p_name

        # Exact match with configured IDs that match nothing (line 385)
        profile_no_match = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {"joining_process": {"policy": "exact_match", "joining_process_id": "NonExistent"}},
            }
        )
        t_no_match = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile_no_match)
        assert t_no_match._choose_joining_process([MagicMock(JoiningProcessId="Other")]) is None

    @pytest.mark.asyncio
    async def test_run_workflow_multi_operation_collector_times_out(self, base_profile):
        mock_client = MagicMock()
        mock_client.get_namespace_index = AsyncMock(return_value=2)
        mock_sub_client = MagicMock()
        mock_sub_client.get_namespace_index = AsyncMock(return_value=2)
        trigger = StartSelectedJoiningResultTrigger(
            mock_client,
            MagicMock(),
            2,
            base_profile,
            subscription_client=mock_sub_client,
        )
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")
        trigger._ensure_tool_enabled = AsyncMock(return_value=True)
        trigger._get_joining_process_list = AsyncMock(return_value=[MagicMock(JoiningProcessId="P1")])
        trigger._select_joining_process = AsyncMock(return_value=True)
        trigger._start_selected_joining = AsyncMock(return_value=True)

        mock_collector = MagicMock()
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            return_value=CorrelatedOperationOutcome(operation_confirmed=False, timed_out=True)
        )
        mock_collector.discard_pending = MagicMock()
        mock_collector.collect_pending_terminal = MagicMock(return_value=None)

        with patch("helpers.result_collector.ResultCollector", return_value=mock_collector):
            outcome = await trigger._run_workflow(2)
            assert outcome.triggered is False
            assert "No correlated result" in (outcome.skip_reason or "")

    @pytest.mark.asyncio
    async def test_trigger_operations_timeout_and_exception(self, base_profile):
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, base_profile)

        async def _timeout_workflow(*_a, **_kw):
            raise asyncio.TimeoutError()

        trigger._run_workflow = _timeout_workflow
        outcome = await trigger._trigger_operations(1)
        assert outcome.triggered is False
        assert "timed out" in (outcome.skip_reason or "")

        async def _error_workflow(*_a, **_kw):
            raise RuntimeError("Workflow failed unexpectedly")

        trigger._run_workflow = _error_workflow
        outcome2 = await trigger._trigger_operations(1)
        assert outcome2.triggered is False
        assert "Workflow failed" in (outcome2.skip_reason or "")

    @pytest.mark.asyncio
    async def test_trigger_batch_or_sync_intervention_and_job_policies(self, base_profile):
        from helpers.namespaces import ResultClassification

        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, base_profile)
        trigger._trigger_intervention = AsyncMock(return_value=TargetServerTriggerOutcome(triggered=True))
        trigger.trigger_single = AsyncMock(return_value=TargetServerTriggerOutcome(triggered=True))
        trigger._trigger_operations = AsyncMock(return_value=TargetServerTriggerOutcome(triggered=True))

        res = await trigger.trigger_batch_or_sync(ResultClassification.INTERVENTION_RESULT)
        assert res.triggered is True
        trigger._trigger_intervention.assert_awaited_once()

        res3 = await trigger.trigger_job()
        assert res3.triggered is True

    def test_normalize_classification_and_get_selection(self):
        from helpers.namespaces import ResultClassification

        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "Default_PSet",
                    },
                    "joining_processes": {
                        "job": {
                            "policy": "exact_match",
                            "joining_process_id": "Job_Process_1",
                        },
                        "batch": {
                            "policy": "exact_match",
                            "joining_process_id": "Batch_Process_1",
                        },
                    },
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)

        assert trigger._normalize_classification(None) == ""
        assert trigger._normalize_classification(ResultClassification.SINGLE_RESULT) == "single"
        assert trigger._normalize_classification(ResultClassification.JOB_RESULT) == "job"
        assert trigger._normalize_classification(ResultClassification.BATCH_RESULT) == "batch"
        assert trigger._normalize_classification(ResultClassification.SYNC_RESULT) == "sync"
        assert trigger._normalize_classification(ResultClassification.STITCHING_RESULT) == "stitching"
        assert trigger._normalize_classification(ResultClassification.INTERVENTION_RESULT) == "intervention"
        assert trigger._normalize_classification(999) == ""
        assert trigger._normalize_classification("  JOB ") == "job"

        sel_job, key_job = trigger._get_selection_for_classification("job")
        assert key_job == "job"
        assert sel_job.joining_process_id == "Job_Process_1"

        sel_batch, key_batch = trigger._get_selection_for_classification(ResultClassification.BATCH_RESULT)
        assert key_batch == "batch"
        assert sel_batch.joining_process_id == "Batch_Process_1"

        sel_default, key_default = trigger._get_selection_for_classification("single")
        assert key_default == "single"
        assert sel_default.joining_process_id == "Default_PSet"

    @pytest.mark.asyncio
    async def test_choose_joining_process_with_classification(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "Prog_1",
                    },
                    "joining_processes": {
                        "job": {
                            "policy": "exact_match",
                            "joining_process_id": "Job_1",
                        },
                    },
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)

        proc_prog = MagicMock()
        proc_prog.JoiningProcessId = "Prog_1"
        proc_prog.JoiningProcessMetaData.Classification = JoiningProcessClassification.PROGRAM
        proc_job = MagicMock()
        proc_job.JoiningProcessId = "Job_1"
        proc_job.JoiningProcessMetaData.Classification = JoiningProcessClassification.JOB
        processes = [proc_prog, proc_job]

        chosen_single = trigger._choose_joining_process(processes, classification="single")
        assert chosen_single == proc_prog

        chosen_job = trigger._choose_joining_process(processes, classification="job")
        assert chosen_job == proc_job

        chosen_unknown = trigger._choose_joining_process(processes, classification="sync")
        assert chosen_unknown is None

    def test_exact_match_rejects_process_with_wrong_or_unreadable_classification(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_processes": {
                        "job": {
                            "policy": "exact_match",
                            "joining_process_id": "ConfiguredJob",
                        }
                    }
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        wrong_class = MagicMock(JoiningProcessId="ConfiguredJob")
        wrong_class.JoiningProcessMetaData.Classification = JoiningProcessClassification.PROGRAM
        unreadable_class = MagicMock(JoiningProcessId="ConfiguredJob")
        unreadable_class.JoiningProcessMetaData.Classification = None

        assert trigger._choose_joining_process([wrong_class], classification="job") is None
        assert trigger._choose_joining_process([unreadable_class], classification="job") is None

    @pytest.mark.asyncio
    async def test_get_selection_for_intervention_with_counter_parent_process(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "extension_fields": {
                        "counter_parent_process": {
                            "joining_process_id": "PARENT-1",
                            "joining_process_origin_id": "PARENT-ORIGIN-1",
                            "selection_name": "ParentName",
                        }
                    }
                },
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "Prog_1",
                    }
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        sel, key = trigger._get_selection_for_classification("intervention")
        assert key == "intervention"
        assert sel.joining_process_id == "PARENT-1"
        assert sel.joining_process_origin_id == "PARENT-ORIGIN-1"
        assert sel.selection_name == "ParentName"

    @pytest.mark.asyncio
    async def test_get_selection_for_intervention_accepts_selection_name_only_parent(self):
        """selection_name alone is a usable selector (matching _selection_has_selector),
        so a counter_parent_process configured with only a name must be honoured."""
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {"extension_fields": {"counter_parent_process": {"selection_name": "ParentOnlyName"}}},
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "Prog_1",
                    }
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        sel, key = trigger._get_selection_for_classification("intervention")
        assert key == "intervention"
        assert sel is not profile.selection.joining_process
        assert sel.selection_name == "ParentOnlyName"
        assert sel.joining_process_id == ""
        assert trigger._selection_has_selector(sel) is True

        # ...and it must actually select the advertised parent process.
        entity = MagicMock()
        entity.Name = "SelectionName"
        entity.EntityId = "ParentOnlyName"
        parent = MagicMock()
        parent.JoiningProcessId = "SOME-OTHER-ID"
        parent.AssociatedEntities = [entity]
        other = MagicMock()
        other.JoiningProcessId = "Prog_1"
        other.AssociatedEntities = []
        assert trigger._choose_joining_process([other, parent], classification="intervention") is parent

    @pytest.mark.asyncio
    async def test_get_selection_for_intervention_ignores_selectorless_counter_parent_process(self):
        """A counter_parent_process with no selector at all must still fall back to
        the default selection instead of producing an unmatchable exact_match."""
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "extension_fields": {"counter_parent_process": {"joining_process_id": "", "selection_name": ""}}
                },
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "Prog_1",
                    }
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        sel, key = trigger._get_selection_for_classification("intervention")
        assert key == "intervention"
        assert sel is profile.selection.joining_process

    @pytest.mark.asyncio
    async def test_get_selection_for_intervention_falls_back_to_default_joining_process(self):
        """Regression: an unconfigured intervention selection must fall back to the
        documented default selection.joining_process entry, never to an empty
        exact_match selector that can never match any advertised process."""
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "Prog_1",
                    },
                    "joining_processes": {
                        "job": {
                            "policy": "exact_match",
                            "joining_process_id": "Job_1",
                        }
                    },
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        sel, key = trigger._get_selection_for_classification("intervention")
        assert key == "intervention"
        assert sel is profile.selection.joining_process
        assert sel.policy == "exact_match"
        assert sel.joining_process_id == "Prog_1"

        # The fallback must actually select a process rather than matching nothing.
        proc = MagicMock()
        proc.JoiningProcessId = "Prog_1"
        proc.AssociatedEntities = []
        assert trigger._choose_joining_process([proc], classification="intervention") is proc

    @pytest.mark.asyncio
    async def test_get_selection_for_intervention_prefers_explicit_intervention_entry(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "joining_process_id": "Prog_1",
                    },
                    "joining_processes": {
                        "intervention": {
                            "policy": "exact_match",
                            "joining_process_id": "Intervention_1",
                        }
                    },
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        sel, key = trigger._get_selection_for_classification("intervention")
        assert key == "intervention"
        assert sel.joining_process_id == "Intervention_1"

    def test_empty_exact_match_selection_is_reported_as_configuration_error(self):
        """An exact_match selection with no selectors can never match — it must be
        reported, not silently resolved to the first advertised process."""
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {"joining_process": {"policy": "exact_match"}},
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        proc = MagicMock()
        proc.JoiningProcessId = "Prog_1"
        proc.AssociatedEntities = []
        assert trigger._choose_joining_process([proc]) is None
        assert trigger._selection_has_selector(profile.selection.joining_process) is False

    @pytest.mark.asyncio
    async def test_run_workflow_reports_empty_exact_match_as_configuration_error(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "state_changing_methods": {"allowed_methods": ["SelectJoiningProcess", "StartSelectedJoining"]}
                },
                "selection": {
                    "tool": {"policy": "exact_match", "product_instance_uri": "Tool_1"},
                    "joining_process": {"policy": "exact_match"},
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile, ns_ijt=2)
        proc = MagicMock()
        proc.JoiningProcessId = "Prog_1"
        proc.AssociatedEntities = []
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._get_joining_process_list = AsyncMock(return_value=[proc])

        outcome = await trigger._run_workflow(1, classification="single")
        assert outcome.triggered is False
        assert "configuration error" in (outcome.skip_reason or "").lower()

    @pytest.mark.asyncio
    async def test_run_workflow_multi_operation_breaks_early_on_terminal_job_result(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://localhost:40451"},
                "cu_execution": {
                    "state_changing_methods": {
                        "allowed_methods": ["SelectJoiningProcess", "StartSelectedJoining", "EnableAsset"]
                    }
                },
                "selection": {
                    "tool": {"policy": "exact_match", "product_instance_uri": "Tool_1"},
                    "joining_processes": {
                        "job": {"policy": "exact_match", "joining_process_id": "Job_1"},
                    },
                },
                "workflow_execution": {
                    "max_start_invocations": 6,
                    "expected_results": {"timeout_seconds": 5},
                },
            }
        )
        mock_client = MagicMock()
        mock_sub_client = MagicMock()
        mock_js = MagicMock()
        trigger = StartSelectedJoiningResultTrigger(
            mock_client, mock_js, 2, profile, ns_ijt=2, subscription_client=mock_sub_client
        )

        mock_jpm = MagicMock()
        proc = MagicMock()
        proc.JoiningProcessId = "Job_1"
        proc.JoiningProcessOriginId = "Job_Orig_1"
        proc.JoiningProcessMetaData.Classification = JoiningProcessClassification.JOB
        proc.AssociatedEntities = []

        trigger._get_joining_process_management = AsyncMock(return_value=mock_jpm)
        trigger._get_joining_process_list = AsyncMock(return_value=[proc])
        trigger._select_joining_process = AsyncMock(return_value=True)
        trigger._ensure_tool_enabled = AsyncMock(return_value=True)
        trigger._start_selected_joining = AsyncMock(return_value=True)

        meta = MagicMock()
        meta.Classification = ResultClassification.JOB_RESULT
        meta.AssociatedEntities = [
            MagicMock(EntityId="Tool_1"),
            MagicMock(EntityId="Job_1"),
        ]
        job_result = MagicMock(ResultMetaData=meta)

        mock_collector = MagicMock()
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.__aexit__ = AsyncMock(return_value=None)
        mock_collector.discard_pending = MagicMock(return_value=None)
        mock_collector.collect_pending_terminal = MagicMock(return_value=None)
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            return_value=CorrelatedOperationOutcome(operation_confirmed=True, terminal_result=job_result)
        )

        with patch("helpers.result_collector.ResultCollector", return_value=mock_collector):
            outcome = await trigger._run_workflow(6, classification="job")

        assert outcome.triggered is True
        assert outcome.method == "StartSelectedJoining"
        # The terminal JobResult arrives on the first operation, so the workflow
        # must stop immediately instead of issuing the remaining five starts.
        assert trigger._start_selected_joining.await_count == 1
        assert mock_collector.collect_correlated_operation_outcome.await_count == 1
        assert mock_collector.discard_pending.call_count == 1
        assert outcome.operation_count == 1

    @pytest.mark.asyncio
    async def test_run_workflow_multi_operation_runs_all_starts_without_terminal_result(self):
        """Without a terminal batch/job result every configured start must be issued."""
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://localhost:40451"},
                "cu_execution": {
                    "state_changing_methods": {
                        "allowed_methods": ["SelectJoiningProcess", "StartSelectedJoining", "EnableAsset"]
                    }
                },
                "selection": {
                    "tool": {"policy": "exact_match", "product_instance_uri": "Tool_1"},
                    "joining_processes": {
                        "job": {"policy": "exact_match", "joining_process_id": "Job_1"},
                    },
                },
                "workflow_execution": {
                    "max_start_invocations": 3,
                    "expected_results": {"timeout_seconds": 5},
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(
            MagicMock(), MagicMock(), 2, profile, ns_ijt=2, subscription_client=MagicMock()
        )
        proc = MagicMock()
        proc.JoiningProcessId = "Job_1"
        proc.JoiningProcessOriginId = "Job_Orig_1"
        proc.JoiningProcessMetaData.Classification = JoiningProcessClassification.JOB
        proc.AssociatedEntities = []
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._get_joining_process_list = AsyncMock(return_value=[proc])
        trigger._select_joining_process = AsyncMock(return_value=True)
        trigger._ensure_tool_enabled = AsyncMock(return_value=True)
        trigger._start_selected_joining = AsyncMock(return_value=True)

        mock_collector = MagicMock()
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.__aexit__ = AsyncMock(return_value=None)
        mock_collector.discard_pending = MagicMock(return_value=None)
        mock_collector.collect_pending_terminal = MagicMock(return_value=None)
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            return_value=CorrelatedOperationOutcome(operation_confirmed=True, terminal_result=None)
        )

        with patch("helpers.result_collector.ResultCollector", return_value=mock_collector):
            outcome = await trigger._run_workflow(20, classification="job")

        assert outcome.triggered is True
        assert trigger._start_selected_joining.await_count == 3
        assert mock_collector.collect_correlated_operation_outcome.await_count == 3
        assert outcome.operation_count == 3

    @pytest.mark.asyncio
    async def test_run_workflow_consumes_late_queued_terminal_before_next_start(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "state_changing_methods": {"allowed_methods": ["SelectJoiningProcess", "StartSelectedJoining"]}
                },
                "selection": {
                    "tool": {"policy": "exact_match", "product_instance_uri": "Tool_1"},
                    "joining_processes": {"job": {"policy": "exact_match", "joining_process_id": "Job_1"}},
                },
                "workflow_execution": {"max_start_invocations": 6},
            }
        )
        trigger = StartSelectedJoiningResultTrigger(
            MagicMock(), MagicMock(), 2, profile, ns_ijt=2, subscription_client=MagicMock()
        )
        process = MagicMock(JoiningProcessId="Job_1", JoiningProcessOriginId="")
        process.JoiningProcessMetaData.Classification = JoiningProcessClassification.JOB
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._get_joining_process_list = AsyncMock(return_value=[process])
        trigger._select_joining_process = AsyncMock(return_value=True)
        trigger._start_selected_joining = AsyncMock(return_value=True)

        terminal = MagicMock(
            ResultMetaData=MagicMock(
                Classification=ResultClassification.JOB_RESULT,
                IsPartial=False,
                ResultState=1,
            )
        )
        collector = MagicMock()
        collector.__aenter__ = AsyncMock(return_value=collector)
        collector.__aexit__ = AsyncMock(return_value=None)
        collector.discard_pending.return_value = 0
        collector.collect_correlated_operation_outcome = AsyncMock(
            return_value=CorrelatedOperationOutcome(operation_confirmed=True)
        )
        collector.collect_pending_terminal.return_value = terminal

        with patch("helpers.result_collector.ResultCollector", return_value=collector):
            outcome = await trigger._run_workflow(6, classification="job")

        assert outcome.triggered is True
        assert outcome.starts_issued == 1
        assert trigger._start_selected_joining.await_count == 1
        collector.discard_pending.assert_called_once_with()
        collector.collect_pending_terminal.assert_called_once()

    @pytest.mark.asyncio
    async def test_multi_operation_result_wait_uses_workflow_timeout_not_passive_timeout(self):
        """Regression: an accepted remote start must be given the workflow result
        completion budget, never the short passive trigger observation budget."""
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "state_changing_methods": {"allowed_methods": ["SelectJoiningProcess", "StartSelectedJoining"]}
                },
                "selection": {
                    "tool": {"policy": "exact_match", "product_instance_uri": "Tool_1"},
                    "joining_process": {"policy": "exact_match", "joining_process_id": "Job_1"},
                },
                "triggers": {"result": {"mode": "start_selected_joining", "timeout_seconds": 5}},
                "workflow_execution": {
                    "max_start_invocations": 2,
                    "expected_results": {"timeout_seconds": 60},
                },
            }
        )
        trigger = StartSelectedJoiningResultTrigger(
            MagicMock(), MagicMock(), 2, profile, ns_ijt=2, subscription_client=MagicMock()
        )
        assert trigger.passive_observation_timeout_s == 5
        assert trigger.active_result_timeout_s == 60

        proc = MagicMock()
        proc.JoiningProcessId = "Job_1"
        proc.JoiningProcessOriginId = ""
        proc.AssociatedEntities = []
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._get_joining_process_list = AsyncMock(return_value=[proc])
        trigger._select_joining_process = AsyncMock(return_value=True)
        trigger._start_selected_joining = AsyncMock(return_value=True)

        mock_collector = MagicMock()
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.__aexit__ = AsyncMock(return_value=None)
        mock_collector.discard_pending = MagicMock(return_value=None)
        mock_collector.collect_pending_terminal = MagicMock(return_value=None)
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            return_value=CorrelatedOperationOutcome(operation_confirmed=True)
        )

        with patch("helpers.result_collector.ResultCollector", return_value=mock_collector):
            await trigger._run_workflow(2, classification="single")

        for call in mock_collector.collect_correlated_operation_outcome.await_args_list:
            assert call.kwargs["operation_timeout_s"] == 60


class TestTargetServerTriggerTimeoutBudgets:
    def _profile(self):
        return build_execution_profile(
            {
                "schema_version": 1,
                "triggers": {
                    "result": {"mode": "manual_trigger", "timeout_seconds": 12},
                    "event": {"mode": "manual_trigger", "timeout_seconds": 8},
                },
                "workflow_execution": {"expected_results": {"timeout_seconds": 90}},
            }
        )

    def test_manual_result_trigger_uses_profile_observation_budget(self):
        trigger = ManualResultTrigger(self._profile())
        assert trigger.passive_observation_timeout_s == 12
        # A manual trigger never starts anything, so it must not claim the long
        assert trigger.active_result_timeout_s == 12

    @pytest.mark.asyncio
    async def test_manual_result_trigger_abort_and_reset(self):
        trigger = ManualResultTrigger(self._profile())
        res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "Manual trigger required" in str(res_abort.skip_reason)

        res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "Manual trigger required" in str(res_reset.skip_reason)

    def test_manual_event_trigger_uses_profile_event_budget(self):
        trigger = ManualEventTrigger(self._profile())
        assert trigger.passive_observation_timeout_s == 8
        assert trigger.active_event_timeout_s == 8

    def test_start_selected_joining_trigger_separates_the_two_budgets(self):
        profile = self._profile()
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        assert trigger.passive_observation_timeout_s == 12
        assert trigger.active_result_timeout_s == 90


# ---------------------------------------------------------------------------
# Abort and Reset Workflows
# ---------------------------------------------------------------------------


class TestAbortAndResetWorkflows:
    @pytest.fixture
    def profile(self):
        return build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "state_changing_methods": {
                        "allowed_methods": [
                            "SelectJoiningProcess",
                            "StartSelectedJoining",
                            "AbortJoiningProcess",
                            "ResetJoiningProcess",
                            "EnableAsset",
                        ]
                    }
                },
                "triggers": {"result": {"mode": "start_selected_joining"}},
                "workflow_execution": {
                    "approved_workflows": ["remote_abort_job", "remote_reset_job"],
                    "expected_results": {"reject_ok_evaluation_on_abort": True},
                },
                "selection": {
                    "tool": {
                        "policy": "exact_match",
                        "product_instance_uri": "urn:tool:1",
                    },
                    "joining_process": {
                        "policy": "first_ready",
                    },
                },
            }
        )

    @pytest.fixture
    def trigger(self, profile):
        client = MagicMock()
        sub_client = MagicMock()
        return StartSelectedJoiningResultTrigger(client, MagicMock(), 2, profile, subscription_client=sub_client)

    @pytest.mark.asyncio
    async def test_abort_workflow_permission_check(self, profile):
        raw = {
            "schema_version": 1,
            "cu_execution": {"state_changing_methods": {"allowed_methods": ["SelectJoiningProcess"]}},
            "triggers": {"result": {"mode": "start_selected_joining"}},
        }
        t = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, build_execution_profile(raw))
        outcome = await t._run_abort_workflow()
        assert outcome.triggered is False
        assert "not in the allowed" in str(outcome.skip_reason)
        outcome_reset = await t._run_reset_workflow()
        assert outcome_reset.triggered is False
        assert "not in the allowed" in str(outcome_reset.skip_reason)

    @pytest.mark.asyncio
    async def test_abort_and_reset_not_in_approved_workflows(self):
        raw = {
            "schema_version": 1,
            "cu_execution": {
                "state_changing_methods": {
                    "allowed_methods": [
                        "SelectJoiningProcess",
                        "StartSelectedJoining",
                        "AbortJoiningProcess",
                        "ResetJoiningProcess",
                    ]
                }
            },
            "triggers": {"result": {"mode": "start_selected_joining"}},
            "workflow_execution": {"approved_workflows": []},
        }
        t = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, build_execution_profile(raw))
        outcome_abort = await t.trigger_abort_job()
        assert outcome_abort.triggered is False
        assert "is not listed in workflows.approved" in str(outcome_abort.skip_reason)

        outcome_reset = await t.trigger_reset_job()
        assert outcome_reset.triggered is False
        assert "is not listed in workflows.approved" in str(outcome_reset.skip_reason)

    @pytest.mark.asyncio
    async def test_abort_workflow_success(self, trigger):
        from helpers.namespaces import ResultState

        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")
        trigger._ensure_tool_enabled = AsyncMock(return_value=True)

        job_process = MagicMock()
        job_process.JoiningProcessMetaData = SimpleNamespace(Classification=5)
        job_process.JoiningProcessIdentification = SimpleNamespace(JoiningProcessId="Job_1")
        job_process.JoiningProcessIdentificationOrigin = SimpleNamespace(JoiningProcessOriginId="Job_Origin_1")
        job_process.SelectionName = []

        trigger._get_joining_process_list = AsyncMock(return_value=[job_process])
        trigger._select_joining_process = AsyncMock(return_value=True)
        trigger._make_process_identification = MagicMock(return_value=MagicMock(JoiningProcessId="Job_1"))
        trigger._start_selected_joining = AsyncMock(return_value=True)
        trigger._resolve_ijt_namespace_index = AsyncMock(return_value=2)
        trigger._method_succeeded = MagicMock(return_value=True)

        terminal_mock = MagicMock()
        terminal_mock.ResultMetaData = MagicMock(Classification=4, IsPartial=False, ResultState=ResultState.ABORTED)

        mock_collector = MagicMock()
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.__aexit__ = AsyncMock(return_value=None)
        mock_collector.discard_pending = MagicMock(return_value=None)
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            side_effect=[
                CorrelatedOperationOutcome(operation_confirmed=True, operation_result=MagicMock()),
                CorrelatedOperationOutcome(operation_confirmed=True, terminal_result=terminal_mock),
            ]
        )

        with (
            patch("helpers.result_collector.ResultCollector", return_value=mock_collector),
            patch("helpers.method_caller.find_and_call_method", return_value=MethodCallResult(success=True)),
        ):
            outcome = await trigger.trigger_abort_job()

        assert outcome.triggered is True
        assert outcome.method == "AbortJoiningProcess"

    @pytest.mark.asyncio
    async def test_abort_workflow_batch_fallback(self, trigger):
        from helpers.namespaces import ResultState

        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")
        trigger._ensure_tool_enabled = AsyncMock(return_value=True)

        batch_process = MagicMock()
        batch_process.JoiningProcessMetaData = SimpleNamespace(Classification=4)
        batch_process.JoiningProcessIdentification = SimpleNamespace(JoiningProcessId="Batch_1")
        batch_process.JoiningProcessIdentificationOrigin = SimpleNamespace(JoiningProcessOriginId="Batch_Origin_1")
        batch_process.SelectionName = []

        trigger._get_joining_process_list = AsyncMock(return_value=[batch_process])
        trigger._select_joining_process = AsyncMock(return_value=True)
        trigger._make_process_identification = MagicMock(return_value=MagicMock(JoiningProcessId="Batch_1"))
        trigger._start_selected_joining = AsyncMock(return_value=True)
        trigger._resolve_ijt_namespace_index = AsyncMock(return_value=2)
        trigger._method_succeeded = MagicMock(return_value=True)

        terminal_mock = MagicMock()
        terminal_mock.ResultMetaData = MagicMock(Classification=3, IsPartial=False, ResultState=ResultState.ABORTED)

        mock_collector = MagicMock()
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.__aexit__ = AsyncMock(return_value=None)
        mock_collector.discard_pending = MagicMock(return_value=None)
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            side_effect=[
                CorrelatedOperationOutcome(operation_confirmed=True, operation_result=MagicMock()),
                CorrelatedOperationOutcome(operation_confirmed=True, terminal_result=terminal_mock),
            ]
        )

        with (
            patch("helpers.result_collector.ResultCollector", return_value=mock_collector),
            patch("helpers.method_caller.find_and_call_method", return_value=MethodCallResult(success=True)),
        ):
            outcome = await trigger._run_abort_workflow()

        assert outcome.triggered is True
        assert outcome.method == "AbortJoiningProcess"

    @pytest.mark.asyncio
    async def test_reset_workflow_success(self, trigger):
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")

        job_process = MagicMock()
        job_process.JoiningProcessMetaData = SimpleNamespace(Classification=5)
        job_process.JoiningProcessIdentification = SimpleNamespace(JoiningProcessId="Job_1")
        job_process.JoiningProcessIdentificationOrigin = SimpleNamespace(JoiningProcessOriginId="Job_Origin_1")
        job_process.SelectionName = []

        trigger._get_joining_process_list = AsyncMock(return_value=[job_process])
        trigger._select_joining_process = AsyncMock(return_value=True)
        trigger._make_process_identification = MagicMock(return_value=MagicMock(JoiningProcessId="Job_1"))
        trigger._resolve_ijt_namespace_index = AsyncMock(return_value=2)
        trigger._start_selected_joining = AsyncMock(return_value=True)
        trigger._method_succeeded = MagicMock(return_value=True)

        mock_collector = MagicMock()
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.__aexit__ = AsyncMock(return_value=None)
        mock_collector.discard_pending = MagicMock(return_value=None)
        first_result = SimpleNamespace(
            ResultMetaData=SimpleNamespace(ResultId="result-1", SequenceNumber=1, StepId="step-1")
        )
        restarted_result = SimpleNamespace(
            ResultMetaData=SimpleNamespace(ResultId="result-2", SequenceNumber=2, StepId="step-1")
        )
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            side_effect=[
                CorrelatedOperationOutcome(operation_confirmed=True, operation_result=first_result),
                CorrelatedOperationOutcome(operation_confirmed=True, operation_result=restarted_result),
            ]
        )

        with (
            patch("helpers.result_collector.ResultCollector", return_value=mock_collector),
            patch("helpers.method_caller.find_and_call_method", return_value=MethodCallResult(success=True)),
        ):
            outcome = await trigger.trigger_reset_job()

        assert outcome.triggered is True
        assert outcome.method == "ResetJoiningProcess"
        assert outcome.operation_count == 2
        assert outcome.starts_issued == 2
        assert outcome.results_confirmed == 2

    @pytest.mark.asyncio
    async def test_trigger_job_remains_pure(self, profile):
        raw_abort = {
            "schema_version": 1,
            "cu_execution": {
                "state_changing_methods": {
                    "allowed_methods": ["SelectJoiningProcess", "StartSelectedJoining", "AbortJoiningProcess"]
                }
            },
            "triggers": {"result": {"mode": "start_selected_joining"}},
            "workflow_execution": {"approved_workflows": ["remote_abort_job", "remote_reset_job"]},
        }
        t_pure = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, build_execution_profile(raw_abort))
        t_pure._trigger_operations = AsyncMock(
            return_value=TargetServerTriggerOutcome(triggered=True, method="StartSelectedJoining")
        )
        t_pure._run_abort_workflow = AsyncMock(
            return_value=TargetServerTriggerOutcome(triggered=True, method="AbortJoiningProcess")
        )

        outcome = await t_pure.trigger_job()
        assert outcome.triggered is True
        assert t_pure._trigger_operations.await_count == 1
        assert t_pure._run_abort_workflow.await_count == 0

    @pytest.mark.asyncio
    async def test_abort_and_reset_workflow_edge_cases(self, trigger):
        from asyncua import ua

        def _result(result_id="", sequence_number=None, step_id=""):
            return SimpleNamespace(
                ResultMetaData=SimpleNamespace(
                    ResultId=result_id,
                    SequenceNumber=sequence_number,
                    StepId=step_id,
                )
            )

        valid_before = _result("before", 1, "step-1")
        valid_after = _result("after", 2, "step-1")
        assert trigger._same_reset_step_evidence(valid_before, valid_after) == (True, "", False)
        variant_before = _result(
            ua.Variant("before", ua.VariantType.String),
            ua.Variant(1, ua.VariantType.UInt32),
            ua.Variant("step-1", ua.VariantType.String),
        )
        assert trigger._same_reset_step_evidence(variant_before, valid_after) == (True, "", False)
        assert "ResultId" in trigger._same_reset_step_evidence(_result(), valid_after)[1]
        assert "repeated" in trigger._same_reset_step_evidence(valid_before, _result("before", 2, "step-1"))[1]
        missing_step = trigger._same_reset_step_evidence(valid_before, _result("after", 2))
        assert "StepId is unavailable" in missing_step[1]
        assert missing_step[2] is True
        assert "reported StepId" in trigger._same_reset_step_evidence(valid_before, _result("after", 2, "step-2"))[1]
        assert (
            "must be an integer" in trigger._same_reset_step_evidence(valid_before, _result("after", True, "step-1"))[1]
        )
        assert "did not advance" in trigger._same_reset_step_evidence(valid_before, _result("after", 1, "step-1"))[1]
        assert (
            "required to order" in trigger._same_reset_step_evidence(valid_before, _result("after", None, "step-1"))[1]
        )

        trigger._resolve_ijt_namespace_index = AsyncMock(return_value=2)
        # Case 1: jpm_node is None
        trigger._get_joining_process_management = AsyncMock(return_value=None)
        res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "JoiningProcessManagement" in str(res_abort.skip_reason)
        res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "JoiningProcessManagement" in str(res_reset.skip_reason)

        # Case 2: enable tool fails
        trigger._get_joining_process_management = AsyncMock(return_value=MagicMock())
        trigger._resolve_tool_piu = AsyncMock(return_value="urn:tool:1")
        trigger._ensure_tool_enabled = AsyncMock(return_value=False)
        trigger._last_method_failure = "Tool error"
        res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "EnableAsset failed" in str(res_abort.skip_reason)

        # Case 3: no processes returned
        trigger._ensure_tool_enabled = AsyncMock(return_value=True)
        trigger._get_joining_process_list = AsyncMock(return_value=[])
        res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "No joining processes" in str(res_abort.skip_reason)
        res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "No joining processes" in str(res_reset.skip_reason)

        # Case 4: no job/batch process found
        prog_process = MagicMock()
        prog_process.JoiningProcessMetaData = SimpleNamespace(Classification=2)
        trigger._get_joining_process_list = AsyncMock(return_value=[prog_process])
        res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "No Job or Batch" in str(res_abort.skip_reason)
        res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "No Job or Batch" in str(res_reset.skip_reason)

        # Case 5: select joining process fails
        job_process = MagicMock()
        job_process.JoiningProcessMetaData = SimpleNamespace(Classification=5)
        job_process.JoiningProcessIdentification = SimpleNamespace(JoiningProcessId="Job_1")
        job_process.JoiningProcessIdentificationOrigin = SimpleNamespace(JoiningProcessOriginId="Job_Origin_1")
        job_process.SelectionName = []
        trigger._get_joining_process_list = AsyncMock(return_value=[job_process])
        trigger._select_joining_process = AsyncMock(return_value=False)
        res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "SelectJoiningProcess failed" in str(res_abort.skip_reason)
        res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "SelectJoiningProcess failed" in str(res_reset.skip_reason)

        # Case 6: identification is None
        trigger._select_joining_process = AsyncMock(return_value=True)
        trigger._make_process_identification = MagicMock(return_value=None)
        res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "IdentificationDataType is unavailable" in str(res_abort.skip_reason)
        res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "IdentificationDataType is unavailable" in str(res_reset.skip_reason)

        # Case 7: subscription client is None
        trigger._make_process_identification = MagicMock(return_value=MagicMock())
        trigger._subscription_client = None
        res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "subscription client" in str(res_abort.skip_reason)
        res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "subscription client" in str(res_reset.skip_reason)

        # Case 8: start selected joining fails on step 1 of abort
        trigger._subscription_client = MagicMock()
        trigger._start_selected_joining = AsyncMock(return_value=False)
        mock_c = MagicMock()
        mock_c.__aenter__ = AsyncMock(return_value=mock_c)
        mock_c.__aexit__ = AsyncMock(return_value=None)
        mock_c.discard_pending = MagicMock(return_value=None)
        with patch("helpers.result_collector.ResultCollector", return_value=mock_c):
            res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "StartSelectedJoining failed on step 1" in str(res_abort.skip_reason)

        # Case 8b: start selected joining fails on step 1 of reset
        trigger._start_selected_joining = AsyncMock(return_value=False)
        with patch("helpers.result_collector.ResultCollector", return_value=mock_c):
            res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "StartSelectedJoining failed on step 1" in str(res_reset.skip_reason)

        # Case 8c: step 1 times out before abort
        trigger._start_selected_joining = AsyncMock(return_value=True)
        mock_c.collect_correlated_operation_outcome = AsyncMock(
            return_value=CorrelatedOperationOutcome(operation_confirmed=False)
        )
        with patch("helpers.result_collector.ResultCollector", return_value=mock_c):
            res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "Step 1 operation timed out" in str(res_abort.skip_reason)

        # Case 8d: parent completed before abort could be issued
        mock_c.collect_correlated_operation_outcome = AsyncMock(
            return_value=CorrelatedOperationOutcome(
                operation_confirmed=True,
                latest_result=MagicMock(),
                terminal_result=MagicMock(),
            )
        )
        with patch("helpers.result_collector.ResultCollector", return_value=mock_c):
            res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "Process completed before abort could be issued" in str(res_abort.skip_reason)

        # Case 8e: step 1 times out before reset
        mock_c.collect_correlated_operation_outcome = AsyncMock(
            return_value=CorrelatedOperationOutcome(operation_confirmed=False)
        )
        with patch("helpers.result_collector.ResultCollector", return_value=mock_c):
            res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "Step 1 operation timed out" in str(res_reset.skip_reason)

        # Case 8f: parent completed before reset could be issued
        mock_c.collect_correlated_operation_outcome = AsyncMock(
            return_value=CorrelatedOperationOutcome(
                operation_confirmed=True,
                latest_result=MagicMock(),
                terminal_result=MagicMock(),
            )
        )
        with patch("helpers.result_collector.ResultCollector", return_value=mock_c):
            res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "Process completed before reset could be issued" in str(res_reset.skip_reason)

        # Case 9: abort RPC call fails
        mock_collector = MagicMock()
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.__aexit__ = AsyncMock(return_value=None)
        mock_collector.discard_pending = MagicMock(return_value=None)
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            return_value=CorrelatedOperationOutcome(operation_confirmed=True, operation_result=MagicMock())
        )
        trigger._method_succeeded = MagicMock(return_value=False)
        with (
            patch("helpers.result_collector.ResultCollector", return_value=mock_collector),
            patch("helpers.method_caller.find_and_call_method", return_value=MethodCallResult(success=False)),
        ):
            res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "AbortJoiningProcess call failed" in str(res_abort.skip_reason)

        # Case 9b: abort terminal result times out or wrong state
        trigger._method_succeeded = MagicMock(return_value=True)
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            side_effect=[
                CorrelatedOperationOutcome(operation_confirmed=True, operation_result=MagicMock()),
                CorrelatedOperationOutcome(operation_confirmed=False, terminal_result=None),
            ]
        )
        with (
            patch("helpers.result_collector.ResultCollector", return_value=mock_collector),
            patch("helpers.method_caller.find_and_call_method", return_value=MethodCallResult(success=True)),
        ):
            res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "expected terminal aborted result" in str(res_abort.skip_reason)

        # Case 9c: aborted result was evaluated as OK (1) -> rejected
        terminal_ok = SimpleNamespace(
            ResultMetaData=SimpleNamespace(Classification=4, IsPartial=False, ResultState=3, ResultEvaluation=1)
        )
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            side_effect=[
                CorrelatedOperationOutcome(operation_confirmed=True, operation_result=MagicMock()),
                CorrelatedOperationOutcome(operation_confirmed=True, terminal_result=terminal_ok),
            ]
        )
        with (
            patch("helpers.result_collector.ResultCollector", return_value=mock_collector),
            patch("helpers.method_caller.find_and_call_method", return_value=MethodCallResult(success=True)),
        ):
            res_abort = await trigger.trigger_abort_job()
        assert res_abort.triggered is False
        assert "evaluated as OK" in str(res_abort.skip_reason)

        # Case 10: reset RPC call fails
        trigger._method_succeeded = MagicMock(return_value=False)
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            return_value=CorrelatedOperationOutcome(operation_confirmed=True, operation_result=MagicMock())
        )
        with (
            patch("helpers.result_collector.ResultCollector", return_value=mock_collector),
            patch("helpers.method_caller.find_and_call_method", return_value=MethodCallResult(success=False)),
        ):
            res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "ResetJoiningProcess call failed" in str(res_reset.skip_reason)

        # Case 10b: reset restart start fails
        trigger._method_succeeded = MagicMock(return_value=True)
        trigger._start_selected_joining = AsyncMock(side_effect=[True, False])
        with (
            patch("helpers.result_collector.ResultCollector", return_value=mock_collector),
            patch("helpers.method_caller.find_and_call_method", return_value=MethodCallResult(success=True)),
        ):
            res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "Post-reset restart failed" in str(res_reset.skip_reason)

        # Case 10c: reset restart times out
        trigger._start_selected_joining = AsyncMock(return_value=True)
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            side_effect=[
                CorrelatedOperationOutcome(operation_confirmed=True, operation_result=MagicMock()),
                CorrelatedOperationOutcome(operation_confirmed=False),
            ]
        )
        with (
            patch("helpers.result_collector.ResultCollector", return_value=mock_collector),
            patch("helpers.method_caller.find_and_call_method", return_value=MethodCallResult(success=True)),
        ):
            res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "Post-reset restart timed out" in str(res_reset.skip_reason)

        # Case 10d: reset restart completes parent prematurely
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            side_effect=[
                CorrelatedOperationOutcome(operation_confirmed=True, operation_result=MagicMock()),
                CorrelatedOperationOutcome(
                    operation_confirmed=True, latest_result=MagicMock(), terminal_result=MagicMock()
                ),
            ]
        )
        with (
            patch("helpers.result_collector.ResultCollector", return_value=mock_collector),
            patch("helpers.method_caller.find_and_call_method", return_value=MethodCallResult(success=True)),
        ):
            res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert "completed parent sequence prematurely" in str(res_reset.skip_reason)

        # Case 10e: reset succeeds but optional StepId evidence is unavailable
        mock_collector.collect_correlated_operation_outcome = AsyncMock(
            side_effect=[
                CorrelatedOperationOutcome(operation_confirmed=True, operation_result=valid_before),
                CorrelatedOperationOutcome(
                    operation_confirmed=True,
                    operation_result=_result("after", 2),
                ),
            ]
        )
        with (
            patch("helpers.result_collector.ResultCollector", return_value=mock_collector),
            patch("helpers.method_caller.find_and_call_method", return_value=MethodCallResult(success=True)),
        ):
            res_reset = await trigger.trigger_reset_job()
        assert res_reset.triggered is False
        assert res_reset.inconclusive is True
        assert "StepId is unavailable" in str(res_reset.skip_reason)
