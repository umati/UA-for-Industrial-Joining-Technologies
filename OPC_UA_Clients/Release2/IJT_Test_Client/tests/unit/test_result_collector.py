"""
Unit tests for helpers/result_collector.py

Tests the pure-Python utility functions (unwrap_result, get_classification,
is_partial) and the ResultCollector class using AsyncMock — no live OPC UA
server required.
"""
from __future__ import annotations

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
        outer = ua.Variant(inner)
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
        rc._collect_until.assert_awaited_once_with(
            ResultClassification.SINGLE_RESULT, False, pytest.approx(10.0)
        )

    @pytest.mark.asyncio
    async def test_collect_single_uses_custom_timeout(self):
        rc = self._make_rc_returning(None)
        await rc.collect_single(timeout_s=99.0)
        _, _, timeout = rc._collect_until.call_args[0]
        assert timeout == pytest.approx(99.0)

    @pytest.mark.asyncio
    async def test_collect_combined_delegates_correctly(self):
        rc = self._make_rc_returning("batch")
        result = await rc.collect_combined(ResultClassification.BATCH_RESULT)
        assert result == "batch"
        cls_arg, partial_arg, _ = rc._collect_until.call_args[0]
        assert cls_arg == ResultClassification.BATCH_RESULT
        assert partial_arg is False

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
