"""
Unit tests for helpers/trigger.py

Tests the pure-Python components that do not require a live OPC UA server:
  - TriggerOutcome dataclass
  - ExternalResultTrigger (all trigger methods return triggered=False immediately)
  - ExternalEventTrigger  (all trigger methods return triggered=False immediately)
  - SimulatorResultTrigger (calls mocked OPC UA folder methods)
  - SimulatorEventTrigger  (calls mocked OPC UA folder methods)
  - make_result_trigger factory (None folder → External)
  - make_event_trigger  factory (None folder → External)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asyncua import ua

from helpers import trigger as trigger_mod
from helpers.trigger import (
    ExternalEventTrigger,
    ExternalResultTrigger,
    ResultTrigger,
    SimulatorEventTrigger,
    SimulatorResultTrigger,
    TriggerOutcome,
    make_event_trigger,
    make_result_trigger,
)

# ---------------------------------------------------------------------------
# TriggerOutcome dataclass
# ---------------------------------------------------------------------------


class TestTriggerOutcome:
    def test_triggered_true(self):
        outcome = TriggerOutcome(triggered=True, method="SimulateSingleResult")
        assert outcome.triggered is True
        assert outcome.method == "SimulateSingleResult"
        assert outcome.skip_reason is None

    def test_triggered_false_with_reason(self):
        outcome = TriggerOutcome(
            triggered=False,
            skip_reason="External trigger required",
            method="SimulateSingleResult",
        )
        assert outcome.triggered is False
        assert outcome.skip_reason == "External trigger required"
        assert outcome.method == "SimulateSingleResult"

    def test_default_skip_reason_is_none(self):
        outcome = TriggerOutcome(triggered=True)
        assert outcome.skip_reason is None

    def test_default_method_is_none(self):
        outcome = TriggerOutcome(triggered=False)
        assert outcome.method is None


# ---------------------------------------------------------------------------
# ExternalResultTrigger
# ---------------------------------------------------------------------------


class TestExternalResultTrigger:
    @pytest.fixture
    def trigger(self):
        return ExternalResultTrigger()

    def test_is_simulator_returns_false(self, trigger):
        assert trigger.is_simulator is False

    def test_default_wait_timeout(self, trigger):
        assert trigger._wait_timeout_s == 0.0

    def test_custom_wait_timeout(self):
        t = ExternalResultTrigger(wait_timeout_s=30.0)
        assert t._wait_timeout_s == 30.0

    @pytest.mark.asyncio
    async def test_trigger_single_returns_not_triggered(self, trigger):
        outcome = await trigger.trigger_single(result_type=1)
        assert outcome.triggered is False
        assert outcome.skip_reason is not None
        assert len(outcome.skip_reason) > 0

    @pytest.mark.asyncio
    async def test_trigger_single_with_traces_still_not_triggered(self, trigger):
        outcome = await trigger.trigger_single(result_type=2, include_traces=True)
        assert outcome.triggered is False

    @pytest.mark.asyncio
    async def test_trigger_batch_or_sync_returns_not_triggered(self, trigger):
        outcome = await trigger.trigger_batch_or_sync(classification=2)
        assert outcome.triggered is False
        assert outcome.skip_reason is not None

    @pytest.mark.asyncio
    async def test_trigger_batch_or_sync_with_all_params(self, trigger):
        outcome = await trigger.trigger_batch_or_sync(
            classification=3,
            num_children=5,
            include_traces=True,
            send_as_refs=True,
        )
        assert outcome.triggered is False

    @pytest.mark.asyncio
    async def test_trigger_job_returns_not_triggered(self, trigger):
        outcome = await trigger.trigger_job()
        assert outcome.triggered is False

    @pytest.mark.asyncio
    async def test_trigger_job_with_refs(self, trigger):
        outcome = await trigger.trigger_job(send_as_refs=True)
        assert outcome.triggered is False

    @pytest.mark.asyncio
    async def test_trigger_bulk_results_returns_not_triggered(self, trigger):
        outcome = await trigger.trigger_bulk_results(
            result_type=1,
            include_traces=False,
            from_seq=1,
            to_seq=5,
        )
        assert outcome.triggered is False

    @pytest.mark.asyncio
    async def test_trigger_bulk_results_with_all_params(self, trigger):
        outcome = await trigger.trigger_bulk_results(
            result_type=1,
            include_traces=True,
            from_seq=10,
            to_seq=20,
            min_duration_ms=50,
            update_vars=False,
        )
        assert outcome.triggered is False

    @pytest.mark.asyncio
    async def test_trigger_abort_job_returns_not_triggered(self, trigger):
        outcome = await trigger.trigger_abort_job()
        assert outcome.triggered is False
        assert outcome.skip_reason is not None

    @pytest.mark.asyncio
    async def test_trigger_reset_job_returns_not_triggered(self, trigger):
        outcome = await trigger.trigger_reset_job()
        assert outcome.triggered is False
        assert outcome.skip_reason is not None


# ---------------------------------------------------------------------------
# ExternalEventTrigger
# ---------------------------------------------------------------------------


class TestExternalEventTrigger:
    @pytest.fixture
    def trigger(self):
        return ExternalEventTrigger()

    def test_is_simulator_returns_false(self, trigger):
        assert trigger.is_simulator is False

    def test_default_wait_timeout(self, trigger):
        assert trigger._wait_timeout_s == 0.0

    @pytest.mark.asyncio
    async def test_trigger_event_returns_not_triggered(self, trigger):
        outcome = await trigger.trigger_event(event_type=1)
        assert outcome.triggered is False
        assert outcome.skip_reason is not None

    @pytest.mark.asyncio
    async def test_trigger_event_with_count(self, trigger):
        outcome = await trigger.trigger_event(event_type=2, count=5)
        assert outcome.triggered is False

    @pytest.mark.asyncio
    async def test_trigger_bulk_events_returns_not_triggered(self, trigger):
        outcome = await trigger.trigger_bulk_events(
            event_type=1,
            count=10,
            from_seq=1,
            to_seq=10,
        )
        assert outcome.triggered is False

    @pytest.mark.asyncio
    async def test_trigger_bulk_events_with_all_params(self, trigger):
        outcome = await trigger.trigger_bulk_events(
            event_type=3,
            count=5,
            from_seq=100,
            to_seq=104,
            min_duration_ms=200,
        )
        assert outcome.triggered is False

    @pytest.mark.asyncio
    async def test_trigger_condition_returns_not_triggered(self, trigger):
        outcome = await trigger.trigger_condition(event_type=10)
        assert outcome.triggered is False
        assert outcome.method == "SimulateConditions"


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


class TestMakeResultTrigger:
    def test_none_folder_returns_external_trigger(self):
        t = make_result_trigger(client=None, simulate_results_folder=None, ns_app=2)
        assert isinstance(t, ExternalResultTrigger)

    def test_non_none_folder_returns_simulator_trigger(self):
        # Use a non-None object to simulate a folder node
        from helpers.trigger import SimulatorResultTrigger

        fake_folder = object()
        t = make_result_trigger(client=None, simulate_results_folder=fake_folder, ns_app=2)
        assert isinstance(t, SimulatorResultTrigger)


class TestMakeEventTrigger:
    def test_none_folder_returns_external_trigger(self):
        t = make_event_trigger(client=None, simulate_events_folder=None, ns_app=2)
        assert isinstance(t, ExternalEventTrigger)

    def test_non_none_folder_returns_simulator_trigger(self):
        fake_folder = object()
        t = make_event_trigger(client=None, simulate_events_folder=fake_folder, ns_app=2)
        assert isinstance(t, SimulatorEventTrigger)


# ---------------------------------------------------------------------------
# SimulatorResultTrigger — uses mocked folder/find_child_by_browse_name
# ---------------------------------------------------------------------------


def _make_mock_method_node():
    node = MagicMock()
    node.nodeid = "ns=2;i=1234"
    return node


class TestSimulatorResultTrigger:
    def test_is_simulator_returns_true(self):
        folder = MagicMock()
        trigger = SimulatorResultTrigger(None, folder, ns_app=2)
        assert trigger.is_simulator is True

    def test_init_stores_client_folder_ns(self):
        folder = MagicMock()
        client = MagicMock()
        trigger = SimulatorResultTrigger(client, folder, ns_app=3)
        assert trigger._client is client
        assert trigger._folder is folder
        assert trigger._ns_app == 3

    @pytest.mark.asyncio
    async def test_trigger_single_success(self):
        folder = AsyncMock()
        folder.call_method = AsyncMock(return_value=[])

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = _make_mock_method_node()
            trigger = SimulatorResultTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_single(result_type=1, include_traces=False)

        assert outcome.triggered is True

    @pytest.mark.asyncio
    async def test_trigger_single_method_not_found(self):
        folder = AsyncMock()

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            trigger = SimulatorResultTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_single(result_type=1)

        assert outcome.triggered is False
        assert outcome.skip_reason is not None

    @pytest.mark.asyncio
    async def test_trigger_single_ua_error(self):
        folder = AsyncMock()
        folder.call_method = AsyncMock(side_effect=ua.UaError("server error"))

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = _make_mock_method_node()
            trigger = SimulatorResultTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_single(result_type=1)

        assert outcome.triggered is False
        assert outcome.skip_reason is not None

    @pytest.mark.asyncio
    async def test_trigger_single_timeout_error(self):
        folder = AsyncMock()
        folder.call_method = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = _make_mock_method_node()
            trigger = SimulatorResultTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_single(result_type=1)

        assert outcome.triggered is False

    @pytest.mark.asyncio
    async def test_trigger_batch_or_sync_success(self):
        folder = AsyncMock()
        folder.call_method = AsyncMock(return_value=[])

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = _make_mock_method_node()
            trigger = SimulatorResultTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_batch_or_sync(
                classification=2, num_children=3, include_traces=False, send_as_refs=False
            )

        assert outcome.triggered is True

    @pytest.mark.asyncio
    async def test_trigger_job_success(self):
        folder = AsyncMock()
        folder.call_method = AsyncMock(return_value=[])

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = _make_mock_method_node()
            trigger = SimulatorResultTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_job(send_as_refs=False)

        assert outcome.triggered is True

    @pytest.mark.asyncio
    async def test_trigger_bulk_results_success(self):
        folder = AsyncMock()
        folder.call_method = AsyncMock(return_value=[])

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = _make_mock_method_node()
            trigger = SimulatorResultTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_bulk_results(result_type=1, include_traces=False, from_seq=1, to_seq=5)

        assert outcome.triggered is True

    @pytest.mark.asyncio
    async def test_trigger_abort_job_simulator(self):
        folder = MagicMock()
        trigger = SimulatorResultTrigger(None, folder, ns_app=2)
        outcome = await trigger.trigger_abort_job()
        assert outcome.triggered is False
        assert "autonomous abort workflow" in str(outcome.skip_reason)

    @pytest.mark.asyncio
    async def test_trigger_reset_job_simulator(self):
        folder = MagicMock()
        trigger = SimulatorResultTrigger(None, folder, ns_app=2)
        outcome = await trigger.trigger_reset_job()
        assert outcome.triggered is False
        assert "autonomous reset workflow" in str(outcome.skip_reason)


# ---------------------------------------------------------------------------
# SimulatorEventTrigger — uses mocked folder/find_child_by_browse_name
# ---------------------------------------------------------------------------


class TestSimulatorEventTrigger:
    def test_is_simulator_returns_true(self):
        folder = MagicMock()
        trigger = SimulatorEventTrigger(None, folder, ns_app=2)
        assert trigger.is_simulator is True

    def test_init_stores_client_folder_ns(self):
        folder = MagicMock()
        client = MagicMock()
        trigger = SimulatorEventTrigger(client, folder, ns_app=5)
        assert trigger._client is client
        assert trigger._folder is folder
        assert trigger._ns_app == 5

    @pytest.mark.asyncio
    async def test_trigger_event_single_success(self):
        folder = AsyncMock()
        folder.call_method = AsyncMock(return_value=[])

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = _make_mock_method_node()
            trigger = SimulatorEventTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_event(event_type=1, count=1)

        assert outcome.triggered is True

    @pytest.mark.asyncio
    async def test_trigger_event_method_not_found(self):
        folder = AsyncMock()

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            trigger = SimulatorEventTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_event(event_type=1)

        assert outcome.triggered is False
        assert outcome.skip_reason is not None

    @pytest.mark.asyncio
    async def test_trigger_event_multiple_count_all_succeed(self):
        folder = AsyncMock()
        folder.call_method = AsyncMock(return_value=[])

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = _make_mock_method_node()
            trigger = SimulatorEventTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_event(event_type=1, count=3)

        assert outcome.triggered is True
        assert folder.call_method.call_count == 3

    @pytest.mark.asyncio
    async def test_trigger_event_multiple_count_early_failure(self):
        folder = AsyncMock()
        call_count = 0

        async def call_method_side_effect(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ua.UaError("second call failed")
            return []

        folder.call_method = call_method_side_effect

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = _make_mock_method_node()
            trigger = SimulatorEventTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_event(event_type=1, count=3)

        assert outcome.triggered is False

    @pytest.mark.asyncio
    async def test_trigger_bulk_events_success(self):
        folder = AsyncMock()
        folder.call_method = AsyncMock(return_value=[])

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = _make_mock_method_node()
            trigger = SimulatorEventTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_bulk_events(event_type=1, count=10, from_seq=1, to_seq=10)

        assert outcome.triggered is True

    @pytest.mark.asyncio
    async def test_trigger_condition_success(self):
        folder = AsyncMock()
        folder.call_method = AsyncMock(return_value=[])

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = _make_mock_method_node()
            trigger = SimulatorEventTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_condition(event_type=10)

        assert outcome.triggered is True
        call_args = folder.call_method.call_args[0]
        assert call_args[1].Value == 10

    @pytest.mark.asyncio
    async def test_trigger_event_ua_error(self):
        folder = AsyncMock()
        folder.call_method = AsyncMock(side_effect=ua.UaError("event error"))

        with patch("helpers.trigger.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = _make_mock_method_node()
            trigger = SimulatorEventTrigger(None, folder, ns_app=2)
            outcome = await trigger.trigger_event(event_type=2)

        assert outcome.triggered is False


# ---------------------------------------------------------------------------
# Evidence-wait budgets (active vs passive)
# ---------------------------------------------------------------------------


class TestTriggerTimeoutBudgets:
    def test_simulator_triggers_use_short_simulator_budgets(self):
        result_trigger = SimulatorResultTrigger(None, MagicMock(), ns_app=2)
        event_trigger = SimulatorEventTrigger(None, MagicMock(), ns_app=2)
        assert result_trigger.active_result_timeout_s == trigger_mod.DEFAULT_SIMULATOR_ACTIVE_RESULT_TIMEOUT_S
        assert (
            result_trigger.passive_observation_timeout_s == trigger_mod.DEFAULT_SIMULATOR_PASSIVE_OBSERVATION_TIMEOUT_S
        )
        assert event_trigger.active_event_timeout_s == trigger_mod.DEFAULT_SIMULATOR_ACTIVE_RESULT_TIMEOUT_S

    def test_external_triggers_never_use_a_long_active_budget(self, monkeypatch):
        """An external trigger never starts anything, so it must not block a run
        for the long completion budget."""
        monkeypatch.delenv(trigger_mod.ENV_ACTIVE_RESULT_TIMEOUT, raising=False)
        monkeypatch.delenv(trigger_mod.ENV_PASSIVE_OBSERVATION_TIMEOUT, raising=False)
        result_trigger = ExternalResultTrigger()
        event_trigger = ExternalEventTrigger()
        assert (
            result_trigger.active_result_timeout_s
            == result_trigger.passive_observation_timeout_s
            == trigger_mod.DEFAULT_EXTERNAL_PASSIVE_OBSERVATION_TIMEOUT_S
        )
        assert event_trigger.active_event_timeout_s == trigger_mod.DEFAULT_EXTERNAL_PASSIVE_OBSERVATION_TIMEOUT_S

    def test_explicit_wait_timeout_overrides_default(self, monkeypatch):
        monkeypatch.delenv(trigger_mod.ENV_PASSIVE_OBSERVATION_TIMEOUT, raising=False)
        assert ExternalResultTrigger(wait_timeout_s=3.5).passive_observation_timeout_s == 3.5
        assert ExternalEventTrigger(wait_timeout_s=3.5).passive_observation_timeout_s == 3.5

    @pytest.mark.asyncio
    async def test_environment_overrides_are_honoured(self, monkeypatch):
        """A trigger that does not override the budgets picks them up from the
        environment set by helpers/target_server_execution.py."""
        monkeypatch.setenv(trigger_mod.ENV_ACTIVE_RESULT_TIMEOUT, "45")
        monkeypatch.setenv(trigger_mod.ENV_PASSIVE_OBSERVATION_TIMEOUT, "7")

        class _DefaultBudgetTrigger(ResultTrigger):
            @property
            def is_simulator(self) -> bool:
                return False

            async def trigger_single(self, result_type, include_traces=False):
                raise NotImplementedError

            async def trigger_batch_or_sync(
                self, classification, num_children=3, include_traces=False, send_as_refs=False
            ):
                raise NotImplementedError

            async def trigger_job(self, send_as_refs=False):
                raise NotImplementedError

            async def trigger_bulk_results(
                self, result_type, include_traces, from_seq, to_seq, min_duration_ms=100, update_vars=True
            ):
                raise NotImplementedError

        probe = _DefaultBudgetTrigger()
        assert probe.active_result_timeout_s == 45.0
        assert probe.passive_observation_timeout_s == 7.0
        assert ExternalResultTrigger().passive_observation_timeout_s == 7.0
        assert (await probe.trigger_abort_job()).triggered is False
        assert (await probe.trigger_reset_job()).triggered is False

    def test_invalid_or_non_positive_environment_values_are_ignored(self, monkeypatch):
        monkeypatch.setenv(trigger_mod.ENV_PASSIVE_OBSERVATION_TIMEOUT, "not-a-number")
        assert (
            ExternalResultTrigger().passive_observation_timeout_s
            == trigger_mod.DEFAULT_EXTERNAL_PASSIVE_OBSERVATION_TIMEOUT_S
        )
        monkeypatch.setenv(trigger_mod.ENV_PASSIVE_OBSERVATION_TIMEOUT, "0")
        assert (
            ExternalResultTrigger().passive_observation_timeout_s
            == trigger_mod.DEFAULT_EXTERNAL_PASSIVE_OBSERVATION_TIMEOUT_S
        )


class TestEventTriggerDefaultBudgets:
    def test_event_trigger_abc_defaults_come_from_the_environment(self, monkeypatch):
        monkeypatch.setenv(trigger_mod.ENV_ACTIVE_RESULT_TIMEOUT, "33")
        monkeypatch.setenv(trigger_mod.ENV_PASSIVE_OBSERVATION_TIMEOUT, "4")

        class _DefaultBudgetEventTrigger(trigger_mod.EventTrigger):
            @property
            def is_simulator(self) -> bool:
                return False

            async def trigger_event(self, event_type, count=1):
                raise NotImplementedError

            async def trigger_bulk_events(self, event_type, count, from_seq, to_seq, min_duration_ms=100):
                raise NotImplementedError

            async def trigger_condition(self, event_type):
                raise NotImplementedError

        probe = _DefaultBudgetEventTrigger()
        assert probe.active_event_timeout_s == 33.0
        assert probe.passive_observation_timeout_s == 4.0

    def test_simulator_event_trigger_passive_budget(self):
        trigger = SimulatorEventTrigger(None, MagicMock(), ns_app=2)
        assert trigger.passive_observation_timeout_s == trigger_mod.DEFAULT_SIMULATOR_PASSIVE_OBSERVATION_TIMEOUT_S


# ---------------------------------------------------------------------------
# find_simulation_child - the one simulator helper-node lookup
# ---------------------------------------------------------------------------


class TestFindSimulationChild:
    """Both the default fixtures and a simulate_methods manifest use this path."""

    async def test_returns_none_without_an_application_namespace(self):
        assert await trigger_mod.find_simulation_child(MagicMock(), None, "SimulateResults") is None

    async def test_returns_none_when_simulations_folder_is_absent(self, monkeypatch):
        monkeypatch.setattr(trigger_mod, "find_child_by_browse_name", AsyncMock(return_value=None))
        assert await trigger_mod.find_simulation_child(MagicMock(), 2, "SimulateResults") is None

    async def test_returns_none_when_the_child_folder_is_absent(self, monkeypatch):
        simulations = MagicMock()
        lookup = AsyncMock(side_effect=[simulations, None])
        monkeypatch.setattr(trigger_mod, "find_child_by_browse_name", lookup)
        assert await trigger_mod.find_simulation_child(MagicMock(), 2, "SimulateResults") is None

    async def test_browses_simulations_then_the_requested_child(self, monkeypatch):
        joining_system = MagicMock()
        simulations = MagicMock()
        folder = MagicMock()
        lookup = AsyncMock(side_effect=[simulations, folder])
        monkeypatch.setattr(trigger_mod, "find_child_by_browse_name", lookup)

        found = await trigger_mod.find_simulation_child(joining_system, 2, "SimulateResults")

        assert found is folder
        assert lookup.await_args_list[0].args == (joining_system, trigger_mod.BN.SIMULATIONS, 2)
        assert lookup.await_args_list[1].args == (simulations, "SimulateResults", 2)
