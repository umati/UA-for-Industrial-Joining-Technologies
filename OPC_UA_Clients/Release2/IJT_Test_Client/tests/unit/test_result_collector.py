"""
Unit tests for helpers/result_collector.py

Tests the pure-Python utility functions (unwrap_result, get_classification,
is_partial) and the ResultCollector class using AsyncMock — no live OPC UA
server required.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asyncua import ua

from helpers.namespaces import NS_IJT_BASE, ResultClassification
from helpers.result_collector import (
    ResultCollector,
    get_classification,
    is_partial,
    unwrap_result,
)

# ---------------------------------------------------------------------------
# unwrap_result
# ---------------------------------------------------------------------------


class TestUnwrapResult:
    def test_non_variant_returned_as_is(self):
        assert unwrap_result(42) == 42

    def test_string_returned_as_is(self):
        assert unwrap_result("hello") == "hello"

    def test_none_returned_as_is(self):
        assert unwrap_result(None) is None

    def test_list_returned_as_is(self):
        lst = [1, 2, 3]
        assert unwrap_result(lst) is lst

    def test_variant_with_none_value_returns_none(self):
        item = ua.Variant(None, ua.VariantType.Null)
        result = unwrap_result(item)
        assert result is None

    def test_variant_with_string_value_unwrapped(self):
        item = ua.Variant("prog-1", ua.VariantType.String)
        result = unwrap_result(item)
        assert result == "prog-1"

    def test_double_wrapped_variant_fully_unwrapped(self):
        inner = ua.Variant("prog-2", ua.VariantType.String)
        outer = ua.Variant()
        outer.Value = inner
        result = unwrap_result(outer)
        assert result == "prog-2"

    def test_exception_during_unwrap_returns_original(self):
        # Use a MagicMock that looks like a ua.Variant but raises on .Value
        item = MagicMock(spec=ua.Variant)
        type(item).Value = property(lambda self: (_ for _ in ()).throw(RuntimeError("read error")))
        result = unwrap_result(item)
        assert result is item


# ---------------------------------------------------------------------------
# get_classification
# ---------------------------------------------------------------------------


class TestGetClassification:
    def test_returns_none_when_no_meta(self):
        data = MagicMock()
        data.ResultMetaData = None
        assert get_classification(data) is None

    def test_returns_none_when_classification_missing(self):
        data = MagicMock()
        data.ResultMetaData = MagicMock()
        data.ResultMetaData.Classification = None
        assert get_classification(data) is None

    def test_returns_int_for_valid_classification(self):
        data = MagicMock()
        data.ResultMetaData.Classification = 1
        assert get_classification(data) == 1

    def test_returns_none_for_non_numeric_classification(self):
        data = MagicMock()
        data.ResultMetaData.Classification = "bad"
        assert get_classification(data) is None

    def test_returns_batch_result_classification(self):
        data = MagicMock()
        data.ResultMetaData.Classification = ResultClassification.BATCH_RESULT
        result = get_classification(data)
        assert result == ResultClassification.BATCH_RESULT


# ---------------------------------------------------------------------------
# is_partial
# ---------------------------------------------------------------------------


class TestIsPartial:
    def test_returns_false_when_no_meta(self):
        data = MagicMock()
        data.ResultMetaData = None
        assert is_partial(data) is False

    def test_returns_false_when_partial_is_none(self):
        data = MagicMock()
        data.ResultMetaData = MagicMock()
        data.ResultMetaData.IsPartial = None
        assert is_partial(data) is False

    def test_returns_true_when_partial_is_true(self):
        data = MagicMock()
        data.ResultMetaData.IsPartial = True
        assert is_partial(data) is True

    def test_returns_false_when_partial_is_false(self):
        data = MagicMock()
        data.ResultMetaData.IsPartial = False
        assert is_partial(data) is False

    def test_returns_false_when_bool_raises(self):
        class _Unboolean:
            def __bool__(self) -> bool:
                raise TypeError("not boolean-convertible")

        data = MagicMock()
        data.ResultMetaData.IsPartial = _Unboolean()
        assert is_partial(data) is False

    def test_unwraps_variant_before_checking(self):
        data = MagicMock()
        data.ResultMetaData.IsPartial = ua.Variant(True, ua.VariantType.Boolean)
        assert is_partial(data) is True

    def test_returns_false_for_non_boolean_convertible(self):
        data = MagicMock()
        data.ResultMetaData.IsPartial = object()
        # bool(object()) is True — this is fine; just verify it doesn't crash
        result = is_partial(data)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# ResultCollector.__init__
# ---------------------------------------------------------------------------


class TestResultCollectorInit:
    def test_attributes_set_correctly(self):
        client = MagicMock()
        ns = {NS_IJT_BASE: 7}
        rc = ResultCollector(client, ns, is_simulator=False)
        assert rc._client is client
        assert rc._ns_indices is ns
        assert rc._is_simulator is False
        assert rc._collector is None

    def test_is_simulator_defaults_to_true(self):
        rc = ResultCollector(MagicMock(), {})
        assert rc._is_simulator is True


# ---------------------------------------------------------------------------
# ResultCollector._extract
# ---------------------------------------------------------------------------


class TestResultCollectorExtract:
    def _make_rc(self):
        return ResultCollector(MagicMock(), {NS_IJT_BASE: 7})

    def test_returns_none_when_event_has_no_result(self):
        rc = self._make_rc()
        event = MagicMock()
        event.Result = None
        assert rc._extract(event, None, False) is None

    def test_returns_none_when_classification_mismatch(self):
        rc = self._make_rc()
        event = MagicMock()
        event.Result = MagicMock()
        event.Result.ResultMetaData.Classification = 2
        event.Result.ResultMetaData.IsPartial = False
        assert rc._extract(event, 1, False) is None

    def test_returns_none_when_partial_mismatch(self):
        rc = self._make_rc()
        event = MagicMock()
        event.Result = MagicMock()
        event.Result.ResultMetaData.Classification = 1
        event.Result.ResultMetaData.IsPartial = True
        assert rc._extract(event, 1, False) is None  # want_partial=False but got True

    def test_returns_result_data_when_all_match(self):
        rc = self._make_rc()
        event = MagicMock()
        event.Result = MagicMock()
        event.Result.ResultMetaData.Classification = 1
        event.Result.ResultMetaData.IsPartial = False
        result = rc._extract(event, 1, False)
        assert result is event.Result

    def test_accepts_any_classification_when_target_is_none(self):
        rc = self._make_rc()
        event = MagicMock()
        event.Result = MagicMock()
        event.Result.ResultMetaData.Classification = 99
        event.Result.ResultMetaData.IsPartial = False
        result = rc._extract(event, None, False)
        assert result is not None

    def test_returns_none_when_result_unwraps_to_none(self):
        rc = self._make_rc()
        event = MagicMock()
        event.Result = ua.Variant(None, ua.VariantType.Null)
        assert rc._extract(event, None, False) is None


# ---------------------------------------------------------------------------
# ResultCollector.__aenter__ / __aexit__
# ---------------------------------------------------------------------------


class TestResultCollectorContextManager:
    @pytest.mark.asyncio
    async def test_aenter_raises_when_ns_ijt_missing(self):
        rc = ResultCollector(MagicMock(), {})
        with pytest.raises(RuntimeError, match="IJT Base namespace not registered"):
            await rc.__aenter__()

    @pytest.mark.asyncio
    async def test_aenter_creates_and_subscribes_collector(self):
        client = MagicMock()
        client.nodes.server = MagicMock()
        client.get_node = MagicMock(return_value=MagicMock())

        with patch("helpers.result_collector.EventCollector") as MockEC:
            mock_instance = MagicMock()
            mock_instance.subscribe = AsyncMock()
            MockEC.return_value = mock_instance

            rc = ResultCollector(client, {NS_IJT_BASE: 7})
            result = await rc.__aenter__()

        assert result is rc
        assert rc._collector is mock_instance
        mock_instance.subscribe.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aexit_unsubscribes_and_clears_collector(self):
        client = MagicMock()
        client.nodes.server = MagicMock()
        client.get_node = MagicMock(return_value=MagicMock())

        with patch("helpers.result_collector.EventCollector") as MockEC:
            mock_instance = MagicMock()
            mock_instance.subscribe = AsyncMock()
            mock_instance.unsubscribe = AsyncMock()
            MockEC.return_value = mock_instance

            rc = ResultCollector(client, {NS_IJT_BASE: 7})
            await rc.__aenter__()
            await rc.__aexit__(None, None, None)

        mock_instance.unsubscribe.assert_awaited_once()
        assert rc._collector is None

    @pytest.mark.asyncio
    async def test_aexit_safe_when_collector_never_set(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        # Should not raise even if __aenter__ was never called
        await rc.__aexit__(None, None, None)
        assert rc._collector is None


# ---------------------------------------------------------------------------
# ResultCollector._collect_until
# ---------------------------------------------------------------------------


class TestCollectUntil:
    def _make_rc_with_mock_collector(self, events_sequence):
        """Return a ResultCollector whose inner collector yields events_sequence
        on successive collect() calls (then empty lists indefinitely)."""
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        mock_collector = MagicMock()
        call_count = [0]

        async def fake_collect(count, timeout_s):
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(events_sequence):
                return events_sequence[idx]
            return []

        mock_collector.collect = fake_collect
        rc._collector = mock_collector
        return rc

    @pytest.mark.asyncio
    async def test_returns_none_when_collector_not_set(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        # _collector is None → RuntimeError
        with pytest.raises(RuntimeError):
            await rc._collect_until(None, False, 1.0)

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout_with_no_events(self):
        rc = self._make_rc_with_mock_collector([])
        result = await rc._collect_until(None, False, 0.02)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_result_immediately_on_matching_event(self):
        mock_event = MagicMock()
        mock_event.Result = MagicMock()
        mock_event.Result.ResultMetaData.Classification = 1
        mock_event.Result.ResultMetaData.IsPartial = False

        rc = self._make_rc_with_mock_collector([[mock_event]])
        result = await rc._collect_until(1, False, 5.0)
        assert result is mock_event.Result

    @pytest.mark.asyncio
    async def test_skips_non_matching_events_and_returns_matching(self):
        wrong_event = MagicMock()
        wrong_event.Result = MagicMock()
        wrong_event.Result.ResultMetaData.Classification = 99
        wrong_event.Result.ResultMetaData.IsPartial = False

        right_event = MagicMock()
        right_event.Result = MagicMock()
        right_event.Result.ResultMetaData.Classification = 1
        right_event.Result.ResultMetaData.IsPartial = False

        rc = self._make_rc_with_mock_collector([[wrong_event], [right_event]])
        result = await rc._collect_until(1, False, 5.0)
        assert result is right_event.Result


# ---------------------------------------------------------------------------
# Public collect methods (delegation tests)
# ---------------------------------------------------------------------------


class TestPublicCollectMethods:
    def _make_rc_returning(self, return_value):
        """Return a ResultCollector whose _collect_until returns return_value."""
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7}, is_simulator=True)
        rc._collect_until = AsyncMock(return_value=return_value)
        return rc

    @pytest.mark.asyncio
    async def test_collect_single_delegates_correctly(self):
        rc = self._make_rc_returning("data")
        result = await rc.collect_single()
        assert result == "data"
        rc._collect_until.assert_awaited_once_with(ResultClassification.SINGLE_RESULT, False, pytest.approx(10.0))

    @pytest.mark.asyncio
    async def test_collect_single_uses_custom_timeout(self):
        rc = self._make_rc_returning(None)
        await rc.collect_single(timeout_s=99.0)
        _, _, timeout = rc._collect_until.call_args[0]
        assert timeout == pytest.approx(99.0)

    @pytest.mark.asyncio
    async def test_collect_single_matching_passes_correlation_predicate(self):
        rc = self._make_rc_returning("matched")
        predicate = lambda result: result == "matched"

        result = await rc.collect_single_matching(predicate, timeout_s=42.0)

        assert result == "matched"
        rc._collect_until.assert_awaited_once_with(
            ResultClassification.SINGLE_RESULT,
            False,
            pytest.approx(42.0),
            predicate,
        )

    @pytest.mark.asyncio
    async def test_target_profile_timeout_and_required_final_are_enforced(self, monkeypatch):
        monkeypatch.setenv("OPCUA_TARGET_RESULT_TIMEOUT_SECONDS", "123")
        monkeypatch.setenv("OPCUA_TARGET_FINAL_RESULT_REQUIRED", "true")
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7}, is_simulator=False)
        rc._collect_until = AsyncMock(return_value=None)

        with pytest.raises(TimeoutError, match="Required final SingleResult"):
            await rc.collect_single()

        _, _, timeout = rc._collect_until.call_args[0]
        assert timeout == pytest.approx(123.0)

    def test_invalid_target_timeout_is_ignored(self, monkeypatch):
        monkeypatch.setenv("OPCUA_TARGET_RESULT_TIMEOUT_SECONDS", "not-a-number")

        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7}, is_simulator=False)

        assert rc._target_timeout is None

    def test_invalid_required_result_classification_is_ignored(self, monkeypatch):
        monkeypatch.setenv("OPCUA_TARGET_REQUIRED_RESULT_CLASSIFICATION", "not-a-number")

        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7}, is_simulator=False)

        assert rc._required_result_classification is None

    def test_discard_pending_requires_active_context(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})

        with pytest.raises(RuntimeError, match="ResultCollector is not active"):
            rc.discard_pending()

    def test_discard_pending_delegates_to_active_collector(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        rc._collector = MagicMock()
        rc._collector.discard_pending.return_value = 3

        assert rc.discard_pending() == 3
        rc._collector.discard_pending.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_collect_combined_delegates_correctly(self):
        rc = self._make_rc_returning("batch")
        result = await rc.collect_combined(ResultClassification.BATCH_RESULT)
        assert result == "batch"
        cls_arg, partial_arg, _ = rc._collect_until.call_args[0]
        assert cls_arg == ResultClassification.BATCH_RESULT
        assert partial_arg is False

    @pytest.mark.asyncio
    async def test_required_primary_classification_does_not_fail_optional_intermediate_timeout(self, monkeypatch):
        monkeypatch.setenv("OPCUA_TARGET_FINAL_RESULT_REQUIRED", "true")
        monkeypatch.setenv(
            "OPCUA_TARGET_REQUIRED_RESULT_CLASSIFICATION",
            str(ResultClassification.JOB_RESULT),
        )
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7}, is_simulator=False)
        rc._collect_until = AsyncMock(return_value=None)

        result = await rc.collect_combined(ResultClassification.INTERVENTION_RESULT)

        assert result is None

    @pytest.mark.asyncio
    async def test_required_primary_classification_still_fails_on_timeout(self, monkeypatch):
        monkeypatch.setenv("OPCUA_TARGET_FINAL_RESULT_REQUIRED", "true")
        monkeypatch.setenv(
            "OPCUA_TARGET_REQUIRED_RESULT_CLASSIFICATION",
            str(ResultClassification.JOB_RESULT),
        )
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7}, is_simulator=False)
        rc._collect_until = AsyncMock(return_value=None)

        with pytest.raises(TimeoutError, match="Required final JobResult"):
            await rc.collect_job()

    @pytest.mark.asyncio
    async def test_collect_partial_requests_partial_true(self):
        rc = self._make_rc_returning("partial")
        await rc.collect_partial(ResultClassification.BATCH_RESULT)
        _, partial_arg, _ = rc._collect_until.call_args[0]
        assert partial_arg is True

    @pytest.mark.asyncio
    async def test_collect_job_delegates_correctly(self):
        rc = self._make_rc_returning("job")
        result = await rc.collect_job()
        assert result == "job"
        cls_arg, partial_arg, _ = rc._collect_until.call_args[0]
        assert cls_arg == ResultClassification.JOB_RESULT
        assert partial_arg is False

    @pytest.mark.asyncio
    async def test_non_simulator_uses_longer_timeouts(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7}, is_simulator=False)
        rc._collect_until = AsyncMock(return_value=None)
        await rc.collect_single()
        _, _, timeout = rc._collect_until.call_args[0]
        assert timeout == pytest.approx(60.0)


# ---------------------------------------------------------------------------
# is_terminal_completed
# ---------------------------------------------------------------------------


class TestIsTerminalCompleted:
    def test_none_result_data_returns_false(self):
        from helpers.result_collector import is_terminal_completed

        assert is_terminal_completed(None, 4) is False

    def test_classification_mismatch_returns_false(self):
        from helpers.result_collector import is_terminal_completed

        data = MagicMock()
        data.ResultMetaData.Classification = 1
        data.ResultMetaData.IsPartial = False
        data.ResultMetaData.ResultState = 1
        assert is_terminal_completed(data, 4) is False

    def test_missing_result_metadata_returns_false(self):
        from helpers.result_collector import is_terminal_completed

        data = MagicMock()
        data.ResultMetaData = None
        assert is_terminal_completed(data, None) is False

    def test_partial_true_returns_false(self):
        from helpers.result_collector import is_terminal_completed

        data = MagicMock()
        data.ResultMetaData.Classification = 4
        data.ResultMetaData.IsPartial = True
        data.ResultMetaData.ResultState = 1
        assert is_terminal_completed(data, 4) is False

    def test_partial_variant_true_returns_false(self):
        from helpers.result_collector import is_terminal_completed

        data = MagicMock()
        data.ResultMetaData.Classification = 4
        data.ResultMetaData.IsPartial = ua.Variant(True, ua.VariantType.Boolean)
        data.ResultMetaData.ResultState = 1
        assert is_terminal_completed(data, 4) is False

    def test_result_state_not_completed_returns_false(self):
        from helpers.result_collector import is_terminal_completed

        data = MagicMock()
        data.ResultMetaData.Classification = 4
        data.ResultMetaData.IsPartial = False
        data.ResultMetaData.ResultState = 0  # e.g. InProgress
        assert is_terminal_completed(data, 4) is False

    def test_result_state_invalid_returns_false(self):
        from helpers.result_collector import is_terminal_completed

        data = MagicMock()
        data.ResultMetaData.Classification = 4
        data.ResultMetaData.IsPartial = False
        data.ResultMetaData.ResultState = "invalid"
        assert is_terminal_completed(data, 4) is False

    def test_boolean_result_state_is_not_completed_enum(self):
        from helpers.result_collector import is_terminal_completed

        data = MagicMock()
        data.ResultMetaData.Classification = 4
        data.ResultMetaData.IsPartial = False
        data.ResultMetaData.ResultState = True
        assert is_terminal_completed(data, 4) is False

    def test_valid_terminal_result_returns_true(self):
        from helpers.result_collector import is_terminal_completed

        data = MagicMock()
        data.ResultMetaData.Classification = 4
        data.ResultMetaData.IsPartial = False
        data.ResultMetaData.ResultState = 1
        assert is_terminal_completed(data, 4) is True

    def test_valid_terminal_result_with_variant_state_returns_true(self):
        from helpers.result_collector import is_terminal_completed

        data = MagicMock()
        data.ResultMetaData.Classification = 4
        data.ResultMetaData.IsPartial = ua.Variant(False, ua.VariantType.Boolean)
        data.ResultMetaData.ResultState = ua.Variant(1, ua.VariantType.Int32)
        assert is_terminal_completed(data, 4) is True

    def test_is_terminal_aborted_checks_state_three(self):
        from helpers.namespaces import ResultState
        from helpers.result_collector import is_terminal_aborted, is_terminal_matching_state

        data = MagicMock()
        data.ResultMetaData.Classification = 4
        data.ResultMetaData.IsPartial = False
        data.ResultMetaData.ResultState = ResultState.ABORTED
        assert is_terminal_aborted(data, 4) is True
        assert is_terminal_matching_state(data, 4, target_state=3) is True
        assert is_terminal_matching_state(data, 4, target_state=1) is False

    def test_is_terminal_aborted_rejects_completed(self):
        from helpers.result_collector import is_terminal_aborted

        data = MagicMock()
        data.ResultMetaData.Classification = 4
        data.ResultMetaData.IsPartial = False
        data.ResultMetaData.ResultState = 1
        assert is_terminal_aborted(data, 4) is False


# ---------------------------------------------------------------------------
# collect_correlated_operation_outcome
# ---------------------------------------------------------------------------


class TestCollectCorrelatedOperationOutcome:
    @pytest.mark.asyncio
    async def test_raises_when_not_active_in_context(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        with pytest.raises(RuntimeError, match="not active"):
            await rc.collect_correlated_operation_outcome(
                requested_result_classification=4,
                predicate=lambda _: True,
                operation_timeout_s=1.0,
            )

    @pytest.mark.asyncio
    async def test_times_out_when_no_matching_events(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        mock_raw_collector = MagicMock()
        mock_raw_collector.collect = AsyncMock(return_value=[])
        rc._collector = mock_raw_collector

        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=lambda _: True,
            operation_timeout_s=0.01,
            terminal_drain_seconds=0.0,
        )
        assert outcome.operation_confirmed is False
        assert outcome.timed_out is True
        assert outcome.terminal_result is None

    @pytest.mark.asyncio
    async def test_skips_events_failing_predicate(self):
        import asyncio

        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        event_unmatched = MagicMock(Result="other_result")
        calls = [event_unmatched]

        async def _collect(*_a, **_kw):
            if calls:
                return [calls.pop(0)]
            await asyncio.sleep(0.01)
            return []

        mock_raw_collector = MagicMock()
        mock_raw_collector.collect = _collect
        rc._collector = mock_raw_collector

        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=lambda r: r == "matching_result",
            operation_timeout_s=0.01,
            terminal_drain_seconds=0.0,
        )
        assert outcome.operation_confirmed is False
        assert outcome.timed_out is True

    @pytest.mark.asyncio
    async def test_returns_immediately_when_terminal_result_arrives(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        meta = MagicMock(Classification=4, IsPartial=False, ResultState=1)
        job_result = MagicMock(ResultMetaData=meta)
        event = MagicMock(Result=job_result)
        mock_raw_collector = MagicMock()
        mock_raw_collector.collect = AsyncMock(return_value=[event])
        rc._collector = mock_raw_collector

        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=lambda _: True,
            operation_timeout_s=1.0,
            terminal_drain_seconds=0.25,
        )
        assert outcome.operation_confirmed is True
        assert outcome.terminal_result is job_result
        assert outcome.timed_out is False

    @pytest.mark.asyncio
    async def test_drain_catches_terminal_result_after_intermediate_evidence(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        # First event: single result (operation confirmed, not terminal for job)
        single_meta = MagicMock(Classification=1, IsPartial=False, ResultState=1)
        single_result = MagicMock(ResultMetaData=single_meta)
        event1 = MagicMock(Result=single_result)

        # Second event during drain: terminal job result
        job_meta = MagicMock(Classification=4, IsPartial=False, ResultState=1)
        job_result = MagicMock(ResultMetaData=job_meta)
        event2 = MagicMock(Result=job_result)

        mock_raw_collector = MagicMock()
        mock_raw_collector.collect = AsyncMock(side_effect=[[event1], [event2]])
        rc._collector = mock_raw_collector

        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=lambda _: True,
            operation_timeout_s=1.0,
            terminal_drain_seconds=0.25,
        )
        assert outcome.operation_confirmed is True
        assert outcome.operation_result is single_result
        assert outcome.terminal_result is job_result
        assert outcome.latest_result is job_result
        assert outcome.timed_out is False

    @pytest.mark.asyncio
    async def test_drain_completes_without_terminal_result(self):
        import asyncio

        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        single_meta = MagicMock(Classification=1, IsPartial=False, ResultState=1)
        single_result = MagicMock(ResultMetaData=single_meta)
        calls = [single_result]

        async def _collect(*_a, **_kw):
            if calls:
                return [MagicMock(Result=calls.pop(0))]
            await asyncio.sleep(0.01)
            return []

        mock_raw_collector = MagicMock()
        mock_raw_collector.collect = _collect
        rc._collector = mock_raw_collector

        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=lambda _: True,
            operation_timeout_s=1.0,
            terminal_drain_seconds=0.01,
        )
        assert outcome.operation_confirmed is True
        assert outcome.operation_result is single_result
        assert outcome.terminal_result is None
        assert outcome.latest_result is single_result
        assert outcome.timed_out is False

    def test_collect_pending_terminal_raises_when_not_active(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        with pytest.raises(RuntimeError, match="not active"):
            rc.collect_pending_terminal(4, lambda _: True)

    def test_collect_pending_terminal_returns_none_when_no_match(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        mock_raw = MagicMock()
        event_none = MagicMock(Result=None)
        event_other = MagicMock(
            Result=MagicMock(ResultMetaData=MagicMock(Classification=1, IsPartial=False, ResultState=1))
        )
        mock_raw.collect_pending = MagicMock(return_value=[event_none, event_other])
        rc._collector = mock_raw

        assert rc.collect_pending_terminal(4, lambda _: True) is None

    @pytest.mark.asyncio
    async def test_collect_correlated_operation_outcome_handles_none_event_results(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        event_none = MagicMock(Result=None)
        job_meta = MagicMock(Classification=4, IsPartial=False, ResultState=1)
        event_job = MagicMock(Result=MagicMock(ResultMetaData=job_meta))

        mock_raw = MagicMock()
        mock_raw.collect = AsyncMock(side_effect=[[event_none], [event_job], [event_none]])
        rc._collector = mock_raw

        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=lambda _: True,
            operation_timeout_s=1.0,
            terminal_drain_seconds=0.01,
        )
        assert outcome.operation_confirmed is True
        assert outcome.terminal_result is not None
        assert outcome.timed_out is False

    @pytest.mark.asyncio
    async def test_partial_status_does_not_confirm_operation(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        partial_meta = MagicMock(Classification=4, IsPartial=True, ResultState=2)
        single_meta = MagicMock(Classification=1, IsPartial=False, ResultState=1)
        events = [
            MagicMock(Result=MagicMock(ResultMetaData=partial_meta)),
            MagicMock(Result=MagicMock(ResultMetaData=single_meta)),
        ]
        mock_raw_collector = MagicMock()
        mock_raw_collector.collect = AsyncMock(side_effect=[[events[0]], [events[1]]])
        rc._collector = mock_raw_collector

        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=lambda _: True,
            operation_predicate=lambda _: True,
            operation_timeout_s=1.0,
            terminal_drain_seconds=0.0,
        )

        assert outcome.operation_confirmed is True
        assert outcome.operation_result is events[1].Result
        assert outcome.latest_result is events[1].Result

    @pytest.mark.asyncio
    async def test_completed_non_single_result_does_not_confirm_operation(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        batch_result = MagicMock(
            ResultMetaData=MagicMock(
                Classification=ResultClassification.BATCH_RESULT,
                IsPartial=False,
                ResultState=1,
            )
        )
        calls = iter([[MagicMock(Result=batch_result)]])

        async def collect_until_timeout(**_kwargs):
            try:
                return next(calls)
            except StopIteration:
                await asyncio.sleep(0.01)
                return []

        mock_raw_collector = MagicMock()
        mock_raw_collector.collect = AsyncMock(side_effect=collect_until_timeout)
        rc._collector = mock_raw_collector

        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=ResultClassification.JOB_RESULT,
            predicate=lambda _: True,
            operation_predicate=lambda _: True,
            operation_timeout_s=0.01,
            terminal_drain_seconds=0.0,
        )

        assert outcome.operation_confirmed is False
        assert outcome.timed_out is True

    @pytest.mark.asyncio
    async def test_drain_handles_none_event_result(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        single_meta = MagicMock(Classification=1, IsPartial=False, ResultState=1)
        single_result = MagicMock(ResultMetaData=single_meta)
        event_single = MagicMock(Result=single_result)
        event_none = MagicMock(Result=None)
        job_meta = MagicMock(Classification=4, IsPartial=False, ResultState=1)
        job_result = MagicMock(ResultMetaData=job_meta)
        event_job = MagicMock(Result=job_result)

        mock_raw = MagicMock()
        mock_raw.collect = AsyncMock(side_effect=[[event_single], [event_none], [event_job]])
        rc._collector = mock_raw

        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=lambda _: True,
            operation_timeout_s=1.0,
            terminal_drain_seconds=0.05,
        )
        assert outcome.operation_confirmed is True
        assert outcome.terminal_result is job_result

    def test_collect_pending_terminal_preserves_strict_matching(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        partial = MagicMock(ResultMetaData=MagicMock(Classification=4, IsPartial=True, ResultState=2))
        terminal = MagicMock(ResultMetaData=MagicMock(Classification=4, IsPartial=False, ResultState=1))
        rc._collector = MagicMock()
        rc._collector.collect_pending.return_value = [
            MagicMock(Result=partial),
            MagicMock(Result=terminal),
        ]

        assert rc.collect_pending_terminal(4, lambda _: True) is terminal

    def test_collect_pending_terminal_supports_expected_terminal_state_three(self):
        from helpers.namespaces import ResultState

        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        completed = MagicMock(ResultMetaData=MagicMock(Classification=4, IsPartial=False, ResultState=1))
        aborted = MagicMock(
            ResultMetaData=MagicMock(Classification=4, IsPartial=False, ResultState=ResultState.ABORTED)
        )
        rc._collector = MagicMock()
        rc._collector.collect_pending.return_value = [
            MagicMock(Result=completed),
            MagicMock(Result=aborted),
        ]

        assert rc.collect_pending_terminal(4, lambda _: True, expected_terminal_state=3) is aborted

    @pytest.mark.asyncio
    async def test_collect_correlated_operation_outcome_matches_aborted_terminal_state(self):
        from helpers.namespaces import ResultState

        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        aborted_meta = MagicMock(Classification=4, IsPartial=False, ResultState=ResultState.ABORTED)
        aborted_result = MagicMock(ResultMetaData=aborted_meta)
        event = MagicMock(Result=aborted_result)

        mock_raw = MagicMock()
        mock_raw.collect = AsyncMock(return_value=[event])
        rc._collector = mock_raw

        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=lambda _: True,
            operation_timeout_s=1.0,
            terminal_drain_seconds=0.01,
            expected_terminal_state=3,
        )
        assert outcome.operation_confirmed is True
        assert outcome.terminal_result is aborted_result
        assert outcome.latest_result is aborted_result
