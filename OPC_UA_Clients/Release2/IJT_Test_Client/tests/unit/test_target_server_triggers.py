"""
Unit tests for helpers/target_server_triggers.py

Tests target_server-specific trigger adapters without a live OPC UA server.
Uses mocks to simulate joining system node behavior.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helpers.method_caller import MethodCallResult
from helpers.target_server_cu_config import build_default_profile, load_target_server_profile_from_dict
from helpers.target_server_triggers import (
    ManualEventTrigger,
    ManualResultTrigger,
    StartSelectedJoiningResultTrigger,
    TargetServerTriggerOutcome,
    make_target_server_event_trigger,
    make_target_server_result_trigger,
)
from helpers.trigger import ExternalEventTrigger, ExternalResultTrigger, TriggerOutcome

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
        assert o.pre_trigger_baseline == {}

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
        return load_target_server_profile_from_dict(
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
        return load_target_server_profile_from_dict(
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
        return load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
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

    def test_process_identification_omits_selection_name_when_ids_are_configured(
        self, mock_client, mock_joining_system
    ):
        profile = load_target_server_profile_from_dict(
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
        assert identification.JoiningProcessOriginId == "ORIGIN-1"
        assert identification.SelectionName == ""

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

    async def test_select_failure_returns_skip(self, profile, mock_client, mock_joining_system):
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        mock_jpm = MagicMock()
        mock_process = MagicMock()
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
        completion_collector.collect_single_matching = AsyncMock(return_value=MagicMock())

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
        assert start.await_count == 2
        assert completion_collector.discard_pending.call_count == 2
        assert completion_collector.collect_single_matching.await_count == 2

    async def test_batch_workflow_selects_once_and_starts_configured_count(self, mock_client, mock_joining_system):
        profile = load_target_server_profile_from_dict(
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
                    "start_invocation_policy": "one_start_per_operation",
                    "expected_operation_count": 3,
                },
            }
        )
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        trigger._run_workflow = AsyncMock(return_value=TargetServerTriggerOutcome(triggered=True, operation_count=3))

        outcome = await trigger.trigger_batch_or_sync(classification=2, num_children=9)

        trigger._run_workflow.assert_awaited_once_with(3)
        assert outcome.operation_count == 3

    async def test_job_workflow_uses_configured_operation_count(self, mock_client, mock_joining_system):
        profile = load_target_server_profile_from_dict(
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
                    "start_invocation_policy": "one_start_per_operation",
                    "expected_operation_count": 6,
                },
            }
        )
        trigger = self._make_trigger(profile, mock_client, mock_joining_system)
        trigger._run_workflow = AsyncMock(return_value=TargetServerTriggerOutcome(triggered=True, operation_count=6))

        outcome = await trigger.trigger_job()

        trigger._run_workflow.assert_awaited_once_with(6)
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
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": "start_selected_joining"}},
            }
        )
        trigger = make_target_server_result_trigger(mock_client, mock_js, 2, profile)
        assert isinstance(trigger, StartSelectedJoiningResultTrigger)

    def test_start_selected_joining_receives_separate_subscription_client(self, mock_client, mock_js):
        profile = load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "triggers": {"event": {"mode": "manual_trigger"}},
            }
        )
        trigger = make_target_server_event_trigger(profile)
        assert isinstance(trigger, ManualEventTrigger)

    def test_observe_only_mode_returns_external(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "triggers": {"event": {"mode": "observe_only"}},
            }
        )
        trigger = make_target_server_event_trigger(profile)
        assert isinstance(trigger, ExternalEventTrigger)

    def test_none_mode_returns_external(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "triggers": {"event": {"mode": "none"}},
            }
        )
        trigger = make_target_server_event_trigger(profile)
        assert isinstance(trigger, ExternalEventTrigger)


# ---------------------------------------------------------------------------
# Extended branch coverage for Target Server triggers
# ---------------------------------------------------------------------------


class TestTargetServerTriggersExtendedBranches:
    @pytest.fixture
    def base_profile(self):
        return load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
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

        profile = load_target_server_profile_from_dict(
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

        profile = load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
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
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "selection": {"tool": {"product_instance_uri": "urn:tool:explicit"}},
            }
        )
        trigger = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile)
        assert await trigger._resolve_tool_piu() == "urn:tool:explicit"

    @pytest.mark.asyncio
    async def test_run_workflow_enable_tool_fails(self, base_profile):
        profile = load_target_server_profile_from_dict(
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

        profile = load_target_server_profile_from_dict(
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
        profile_name = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "selection": {"joining_process": {"policy": "exact_match", "selection_name": "MatchName"}},
            }
        )
        t_name = StartSelectedJoiningResultTrigger(MagicMock(), MagicMock(), 2, profile_name)
        assert t_name._choose_joining_process([p_name]) is p_name

        # Exact match with configured IDs that match nothing (line 385)
        profile_no_match = load_target_server_profile_from_dict(
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
        mock_collector.__aexit__ = AsyncMock(return_value=None)
        mock_collector.collect_single_matching = AsyncMock(return_value=None)
        mock_collector.discard_pending = MagicMock()

        with patch("helpers.result_collector.ResultCollector", return_value=mock_collector):
            outcome = await trigger._run_workflow(2)
            assert outcome.triggered is False
            assert "No SingleResult correlated" in (outcome.skip_reason or "")

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

        res2 = await trigger.trigger_batch_or_sync(ResultClassification.BATCH_RESULT)
        assert res2.triggered is True

        res3 = await trigger.trigger_job()
        assert res3.triggered is True
