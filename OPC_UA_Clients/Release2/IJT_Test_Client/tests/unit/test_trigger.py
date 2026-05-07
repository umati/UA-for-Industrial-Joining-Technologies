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

from helpers.trigger import (
    ExternalEventTrigger,
    ExternalResultTrigger,
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
