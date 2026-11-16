"""
Unit tests for helpers/result_collector.py

Tests the pure-Python utility functions (unwrap_result, get_classification,
is_partial) and the ResultCollector class using AsyncMock — no live OPC UA
server required.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asyncua import ua

from helpers.namespaces import NS_IJT_BASE, NS_MACH_RESULT, MachineryResultTypes, ResultClassification
from helpers.result_collector import (
    ResultCollector,
    ResultEventCapture,
    ResultProgression,
    collect_single_evidence,
    get_classification,
    get_result_id,
    is_partial,
    parent_result_ids,
    references_result_id,
    retained_single_result,
    unwrap_result,
)


def _owned_single_progression(*, complete=True, classification=1):
    result = SimpleNamespace(
        ResultMetaData=SimpleNamespace(
            ResultId="owned-single",
            Classification=classification,
            IsPartial=False,
            ResultState=1,
        )
    )
    return ResultProgression(
        classification=classification,
        final_result=result,
        unresolved_reference_ids=() if complete else ("missing-child",),
        all_results=(result,),
    )


def test_inline_child_reference_cycle_is_bounded_without_losing_owned_root():
    root = SimpleNamespace(ResultMetaData=SimpleNamespace(ResultId="root"), ResultContent=[], References=[])
    child = SimpleNamespace(ResultMetaData=SimpleNamespace(ResultId="child"), ResultContent=[root], References=[])
    root.ResultContent = [child, child]
    capture = ResultCollector.related_capture(
        ResultProgression(classification=4, final_result=root, all_results=(root, child))
    )
    assert capture.all_results == (root, child)


@pytest.mark.asyncio
async def test_action_window_cannot_use_preceding_parent_terminal_for_new_experiment():
    old = SimpleNamespace(
        ResultMetaData=SimpleNamespace(ResultId="old-parent", Classification=4, IsPartial=False, ResultState=1),
        ResultContent=[],
        References=[],
    )
    current = SimpleNamespace(
        ResultMetaData=SimpleNamespace(ResultId="current-parent", Classification=4, IsPartial=True, ResultState=2),
        ResultContent=[],
        References=[],
    )
    capture = ResultEventCapture(all_results=(old, current))
    assessment = ResultCollector.progression_from_capture(capture, 4, after_result_count=1)
    assert assessment.final_result is None
    assert assessment.partial_results == (current,)
    collector = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
    collector._collector = MagicMock(dropped_event_count=0)
    collector._captured_results = [old, current]
    observed = await collector.collect_progression(4, timeout_s=0, after_result_count=1)
    assert observed.final_result is None


def test_capture_pending_archives_notifications_before_a_new_action():
    result = SimpleNamespace(ResultMetaData=SimpleNamespace(ResultId="before-action"))
    collector = ResultCollector(MagicMock(), {})
    collector._collector = MagicMock(
        collect_pending=MagicMock(return_value=[SimpleNamespace(EventId=b"before", Result=result)]),
        dropped_event_count=0,
    )
    capture = collector.capture_pending()
    assert capture.all_results == (result,)
    assert len(capture.source_events) == 1


@pytest.mark.parametrize("operation", ["capture", "capture_pending"])
def test_capture_requires_active_observer(operation):
    collector = ResultCollector(MagicMock(), {})
    with pytest.raises(RuntimeError, match="not active"):
        getattr(collector, operation)()


@pytest.mark.asyncio
async def test_invalid_action_window_offset_cannot_select_old_evidence():
    with pytest.raises(ValueError, match="nonnegative"):
        ResultCollector.progression_from_capture(ResultEventCapture(), 4, after_result_count=-1)
    collector = ResultCollector(MagicMock(), {})
    with pytest.raises(ValueError, match="nonnegative"):
        await collector.collect_progression(4, after_result_count=-1)


@pytest.mark.parametrize("disposition", ["failed", "inconclusive", "legacy"])
def test_retained_single_preserves_observed_failure_unavailability_and_legacy_noop(disposition):
    from helpers.cu_coverage_report import WorkflowEvidenceUnavailable

    outcome = SimpleNamespace(
        triggered=False,
        execution_outcome="" if disposition == "legacy" else disposition,
        reason_code="" if disposition == "legacy" else "original-cause",
        skip_reason="original diagnostic",
        mutation_attempted=disposition == "inconclusive",
    )
    if disposition == "legacy":
        assert retained_single_result(outcome) is None
    elif disposition == "failed":
        with pytest.raises(AssertionError, match="original-cause"):
            retained_single_result(outcome)
    else:
        with pytest.raises(WorkflowEvidenceUnavailable) as error:
            retained_single_result(outcome)
        assert error.value.ijt_properties["ijt_canonical_outcome"] == "inconclusive"


@pytest.mark.asyncio
@pytest.mark.parametrize("evidence", ["complete", "missing", "partial", "wrong_class"])
async def test_owned_single_consumer_does_not_wait_for_replay_or_accept_wrong_evidence(evidence):
    from helpers.cu_coverage_report import WorkflowEvidenceUnavailable

    progression = (
        None
        if evidence == "missing"
        else _owned_single_progression(
            complete=evidence != "partial",
            classification=4 if evidence == "wrong_class" else 1,
        )
    )
    trigger = SimpleNamespace(
        owns_result_subscription=True,
        trigger_single=AsyncMock(return_value=SimpleNamespace(triggered=True, result_progression=progression)),
    )
    with patch("helpers.result_collector.ResultCollector") as factory:
        if evidence == "complete":
            assert progression is not None
            assert await collect_single_evidence(object(), trigger, {}, 1, fresh=True) is progression.final_result
        else:
            with pytest.raises(WorkflowEvidenceUnavailable):
                await collect_single_evidence(object(), trigger, {}, 1, fresh=True)
    factory.assert_not_called()
    trigger.trigger_single.assert_awaited_once()


@pytest.mark.asyncio
async def test_content_reuse_is_allowed_but_fresh_experiment_bypasses_cache():
    progression = _owned_single_progression()
    cached = AsyncMock(return_value=progression)
    trigger = SimpleNamespace(
        owns_result_subscription=True,
        get_reusable_progression=cached,
        trigger_single=AsyncMock(return_value=SimpleNamespace(triggered=True, result_progression=progression)),
    )
    assert await collect_single_evidence(object(), trigger, {}, 1) is progression.final_result
    trigger.trigger_single.assert_not_awaited()
    assert await collect_single_evidence(object(), trigger, {}, 1, fresh=True) is progression.final_result
    cached.assert_awaited_once()
    trigger.trigger_single.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("owned", [False, True])
async def test_nonowning_adapter_subscribes_first_and_collects_retained_or_live_result(owned):
    progression = _owned_single_progression() if owned else None
    outcome = SimpleNamespace(triggered=True, result_progression=progression)
    trigger = SimpleNamespace(
        owns_result_subscription=False,
        is_simulator=True,
        trigger_single=AsyncMock(return_value=outcome),
    )
    collector = ResultCollector(MagicMock(), {})
    collector.collect_single = AsyncMock(return_value="live-single")
    with (
        patch("helpers.result_collector.ResultCollector.__aenter__", new=AsyncMock(return_value=collector)) as enter,
        patch("helpers.result_collector.ResultCollector.__aexit__", new=AsyncMock(return_value=None)),
    ):
        result = await collect_single_evidence(object(), trigger, {}, 1)
    enter.assert_awaited_once()
    if owned:
        assert progression is not None
        assert result is progression.final_result
        collector.collect_single.assert_not_awaited()
    else:
        assert result == "live-single"
        collector.collect_single.assert_awaited_once()


@pytest.mark.asyncio
async def test_progression_never_adopts_an_unrelated_terminal_or_partial():
    def result(identity, partial=False):
        return SimpleNamespace(
            ResultMetaData=SimpleNamespace(
                Classification=ResultClassification.JOB_RESULT,
                ResultId=identity,
                IsPartial=partial,
                ResultState=0 if partial else 1,
            ),
            ResultContent=[],
            References=[],
        )

    foreign = result("foreign")
    foreign_partial = result("foreign-partial", True)
    terminal = result("selected")
    collector = ResultCollector(MagicMock(), {})
    collector._record_event(SimpleNamespace(Result=foreign))
    collector._record_event(SimpleNamespace(Result=foreign_partial))
    stream = MagicMock()
    stream.collect = AsyncMock(return_value=[SimpleNamespace(Result=terminal)])
    stream.dropped_event_count = 0
    collector._collector = stream
    progression = await collector.collect_progression(
        ResultClassification.JOB_RESULT,
        predicate=lambda value: value.ResultMetaData.ResultId == "selected",
    )
    assert progression.final_result is terminal
    assert progression.partial_results == ()
    assert foreign in progression.all_results
    assert stream.collect.await_count == 1


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
        client.get_namespace_index = AsyncMock(return_value=6)

        with patch("helpers.result_collector.EventCollector") as MockEC:
            mock_instance = MagicMock()
            mock_instance.subscribe = AsyncMock()
            MockEC.return_value = mock_instance

            rc = ResultCollector(client, {NS_IJT_BASE: 7})
            result = await rc.__aenter__()

        assert result is rc
        assert rc._collector is mock_instance
        client.get_namespace_index.assert_awaited_once_with(NS_MACH_RESULT)
        client.get_node.assert_called_once_with(ua.NodeId(MachineryResultTypes.RESULT_READY_EVENT_TYPE, 6))
        mock_instance.subscribe.assert_awaited_once_with(client.nodes.server, client.get_node.return_value)

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

            rc = ResultCollector(client, {NS_IJT_BASE: 7, NS_MACH_RESULT: 6})
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

    def test_event_identity_normalizes_bytearray_and_uses_object_fallback(self):
        event = MagicMock(EventId=bytearray(b"event-1"))
        assert ResultCollector._event_identity(event) == ("event_id", b"event-1")

        event.EventId = ua.Variant(b"event-2", ua.VariantType.ByteString)
        assert ResultCollector._event_identity(event) == ("event_id", b"event-2")

        event.EventId = ""
        assert ResultCollector._event_identity(event) == ("object", id(event))

        event.EventId = 42
        assert ResultCollector._event_identity(event) == ("object", id(event))

    def test_result_id_and_reference_helpers_support_both_reference_shapes(self):
        metadata_reference = MagicMock()
        metadata_reference.ResultId = ""
        metadata_reference.ResultMetaData.ResultId = "intervention-1"
        direct_reference = MagicMock(ResultId="intervention-2")
        parent = MagicMock(ResultContent=[metadata_reference], References=[direct_reference])

        assert get_result_id(metadata_reference) == "intervention-1"
        assert references_result_id(parent, "intervention-1") is True
        assert references_result_id(parent, "intervention-2") is True
        assert references_result_id(parent, "missing") is False
        assert references_result_id(parent, "") is False

        metadata_reference.ResultMetaData.ResultId = ua.Variant("intervention-1", ua.VariantType.String)
        assert get_result_id(metadata_reference) == "intervention-1"
        direct_reference.ResultId = ua.Variant("intervention-2", ua.VariantType.String)
        assert get_result_id(direct_reference) == "intervention-2"

        batch_without_intervention = MagicMock(ResultId="batch-1", ResultContent=[], References=[])
        batch = MagicMock(ResultId="batch-1", ResultContent=[metadata_reference, None], References=[])
        job = MagicMock(ResultContent=[], References=[MagicMock(ResultId="batch-1")])
        assert references_result_id(job, "intervention-1", (batch, batch_without_intervention)) is True

    def test_reference_helper_handles_cycles_empty_entries_and_non_list_fields(self):
        root = SimpleNamespace(ResultId="", ResultContent=[], References="not-a-list")
        child = SimpleNamespace(ResultId="", ResultContent=[root], References=[None])
        root.ResultContent = [None, child]

        assert references_result_id(root, "missing") is False


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
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7}, is_simulator=True)
        rc.collect_progression = AsyncMock(
            return_value=ResultProgression(
                classification=ResultClassification.BATCH_RESULT,
                final_result="batch",
            )
        )
        result = await rc.collect_combined(ResultClassification.BATCH_RESULT)
        assert result == "batch"
        rc.collect_progression.assert_awaited_once_with(ResultClassification.BATCH_RESULT, pytest.approx(15.0))

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
        rc.collect_progression = AsyncMock(
            return_value=ResultProgression(
                classification=ResultClassification.JOB_RESULT,
                timed_out=True,
            )
        )

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
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7}, is_simulator=True)
        rc.collect_progression = AsyncMock(
            return_value=ResultProgression(
                classification=ResultClassification.JOB_RESULT,
                final_result="job",
            )
        )
        result = await rc.collect_job()
        assert result == "job"
        rc.collect_progression.assert_awaited_once_with(ResultClassification.JOB_RESULT, pytest.approx(30.0))

    @pytest.mark.asyncio
    async def test_non_simulator_uses_longer_timeouts(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7}, is_simulator=False)
        rc._collect_until = AsyncMock(return_value=None)
        await rc.collect_single()
        _, _, timeout = rc._collect_until.call_args[0]
        assert timeout == pytest.approx(60.0)


class TestCollectProgression:
    @staticmethod
    def _result(
        classification,
        *,
        result_id,
        partial,
        state,
        content=None,
        references=None,
    ):
        return MagicMock(
            ResultMetaData=MagicMock(
                Classification=classification,
                ResultId=result_id,
                IsPartial=partial,
                ResultState=state,
            ),
            ResultContent=[] if content is None else content,
            References=[] if references is None else references,
        )

    @staticmethod
    def _active_collector(events):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        rc._collector = MagicMock()
        pending = list(events)

        async def collect(**_kwargs):
            if pending:
                return [pending.pop(0)]
            await asyncio.sleep(0.01)
            return []

        rc._collector.collect = AsyncMock(side_effect=collect)
        return rc

    @pytest.mark.asyncio
    @pytest.mark.parametrize("completed", [True, False])
    async def test_mixed_domain_child_closes_reference_only_when_completed(self, completed):
        child = SimpleNamespace(
            ResultMetaData=SimpleNamespace(
                ResultId="quality-child", IsPartial=False, ResultState=1 if completed else 2
            ),
            ResultContent=[],
        )
        stub = SimpleNamespace(ResultMetaData=SimpleNamespace(ResultId="quality-child"), ResultContent=[])
        final = self._result(4, result_id="job", partial=False, state=1, content=[stub])
        rc = self._active_collector(
            [SimpleNamespace(EventId=b"quality", Result=child), SimpleNamespace(EventId=b"job", Result=final)]
        )

        progression = await rc.collect_progression(4, timeout_s=0.02)

        assert progression.is_complete is completed
        assert progression.unresolved_reference_ids == (() if completed else ("quality-child",))
        assert get_classification(child) is None

    @pytest.mark.asyncio
    async def test_collects_partial_children_and_completed_final(self):
        partial = self._result(3, result_id="batch-1", partial=True, state=2)
        child = self._result(1, result_id="single-1", partial=False, state=1)
        stub = self._result(1, result_id="single-1", partial=False, state=1)
        final = self._result(3, result_id="batch-1", partial=False, state=1, content=[stub])
        rc = self._active_collector(
            [
                MagicMock(EventId=b"1", Result=partial),
                MagicMock(EventId=b"2", Result=child),
                MagicMock(EventId=b"3", Result=final),
            ]
        )

        progression = await rc.collect_progression(3, timeout_s=1.0, require_partials=True)

        assert progression.partial_results == (partial,)
        assert progression.child_results == (child,)
        assert progression.final_result is final
        assert progression.source_events
        assert progression.unresolved_reference_ids == ()
        assert progression.is_complete is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [3, 4])
    async def test_retains_unexpected_terminal_without_qualifying_or_timing_out(self, state):
        failed = self._result(3, result_id="batch-1", partial=False, state=state)
        rc = self._active_collector([MagicMock(EventId=b"1", Result=failed)])

        progression = await rc.collect_progression(3, timeout_s=0.01)

        assert progression.final_result is None
        assert progression.terminal_result is failed
        assert progression.timed_out is False
        assert progression.is_complete is False

    @pytest.mark.parametrize("state", [3, 4])
    def test_retained_unexpected_terminal_keeps_children_and_reference_diagnostics(self, state):
        child = self._result(1, result_id="single-1", partial=False, state=1)
        terminal = self._result(
            3,
            result_id="batch-1",
            partial=False,
            state=state,
            references=[SimpleNamespace(ResultId="single-1"), SimpleNamespace(ResultId="missing-child")],
        )
        progression = ResultCollector.progression_from_capture(ResultEventCapture(all_results=(child, terminal)), 3)

        assert progression.final_result is None
        assert progression.terminal_result is terminal
        assert not progression.timed_out
        assert not progression.is_complete
        assert progression.unresolved_reference_ids == ("missing-child",)
        assert child in ResultCollector.related_capture(progression).all_results

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [3, 4])
    async def test_explicit_expected_terminal_still_qualifies(self, state):
        terminal = self._result(3, result_id="batch-1", partial=False, state=state)
        rc = self._active_collector([MagicMock(EventId=b"1", Result=terminal)])
        progression = await rc.collect_progression(3, timeout_s=0.01, expected_terminal_state=state)
        assert progression.final_result is terminal
        assert progression.is_complete

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", ["collect_combined", "collect_job"])
    async def test_raw_consumers_report_wrong_terminal_state_instead_of_missing_result(self, method):
        classification = 3 if method == "collect_combined" else 4
        terminal = self._result(classification, result_id="failed-result", partial=False, state=4)
        rc = self._active_collector([MagicMock(EventId=b"failed", Result=terminal)])
        rc._is_simulator = False
        with pytest.raises(AssertionError, match="failed-result.*state 4, expected 1"):
            if method == "collect_combined":
                await rc.collect_combined(classification, timeout_s=0.01)
            else:
                await rc.collect_job(timeout_s=0.01)

    @pytest.mark.asyncio
    async def test_collects_required_partial_that_arrives_after_final(self):
        final = self._result(3, result_id="batch-1", partial=False, state=1)
        partial = self._result(3, result_id="batch-1", partial=True, state=2)
        rc = self._active_collector(
            [
                MagicMock(EventId=b"1", Result=final),
                MagicMock(EventId=b"2", Result=partial),
            ]
        )

        progression = await rc.collect_progression(3, timeout_s=1.0, require_partials=True)

        assert progression.final_result is final
        assert progression.partial_results == (partial,)
        assert progression.timed_out is False
        assert progression.is_complete is True

    @pytest.mark.asyncio
    async def test_reports_missing_required_partials(self):
        final = self._result(3, result_id="batch-1", partial=False, state=1, content=[MagicMock()])
        final.ResultContent[0].ResultMetaData = MagicMock(
            ResultId="single-1",
            Classification=1,
        )
        final.ResultContent[0].ResultContent = [MagicMock()]
        rc = self._active_collector([MagicMock(EventId=b"1", Result=final)])

        progression = await rc.collect_progression(3, timeout_s=0.01, require_partials=True)

        assert progression.missing_required_partials is True
        assert progression.timed_out is True
        assert progression.is_complete is False

    @pytest.mark.asyncio
    async def test_reports_unresolved_reference_stub(self):
        stub = self._result(1, result_id="missing-child", partial=False, state=1)
        final = self._result(3, result_id="batch-1", partial=False, state=1, content=[stub])
        rc = self._active_collector([MagicMock(EventId=b"1", Result=final)])

        progression = await rc.collect_progression(3, timeout_s=0.01)

        assert progression.unresolved_reference_ids == ("missing-child",)
        assert progression.timed_out is True
        assert progression.is_complete is False

    @pytest.mark.asyncio
    async def test_partial_referenced_child_does_not_close_progression(self):
        partial_child = self._result(1, result_id="single-1", partial=True, state=2)
        stub = self._result(1, result_id="single-1", partial=False, state=1)
        final = self._result(3, result_id="batch-1", partial=False, state=1, content=[stub])
        rc = self._active_collector(
            [
                MagicMock(EventId=b"1", Result=partial_child),
                MagicMock(EventId=b"2", Result=final),
            ]
        )

        progression = await rc.collect_progression(3, timeout_s=0.01)

        assert progression.unresolved_reference_ids == ("single-1",)
        assert progression.timed_out is True
        assert progression.is_complete is False

    @pytest.mark.asyncio
    async def test_child_arriving_after_final_closes_reference(self):
        stub = self._result(1, result_id="single-1", partial=False, state=1)
        final = self._result(3, result_id="batch-1", partial=False, state=1, content=[stub])
        child = self._result(1, result_id="single-1", partial=False, state=1, content=[MagicMock()])
        rc = self._active_collector(
            [
                MagicMock(EventId=b"final", Result=final),
                MagicMock(EventId=b"child", Result=child),
            ]
        )

        progression = await rc.collect_progression(3, timeout_s=1.0)

        assert progression.final_result is final
        assert progression.child_results == (child,)
        assert progression.unresolved_reference_ids == ()
        assert progression.is_complete is True

    @pytest.mark.asyncio
    async def test_references_array_is_resolved_by_captured_child(self):
        reference = MagicMock(ResultId="single-1")
        final = self._result(
            3,
            result_id="batch-1",
            partial=False,
            state=1,
            references=[reference],
        )
        child = self._result(1, result_id="single-1", partial=False, state=1, content=[MagicMock()])
        rc = self._active_collector(
            [
                MagicMock(EventId=b"child", Result=child),
                MagicMock(EventId=b"final", Result=final),
            ]
        )

        progression = await rc.collect_progression(3, timeout_s=1.0)

        assert progression.unresolved_reference_ids == ()
        assert progression.is_complete is True

    @pytest.mark.asyncio
    async def test_inline_child_closes_without_separate_event(self):
        inline_child = self._result(
            1,
            result_id="single-1",
            partial=False,
            state=1,
            content=[MagicMock()],
        )
        final = self._result(3, result_id="batch-1", partial=False, state=1, content=[inline_child])
        rc = self._active_collector([MagicMock(EventId=b"1", Result=final)])

        progression = await rc.collect_progression(3, timeout_s=1.0)

        assert progression.unresolved_reference_ids == ()
        assert progression.is_complete is True

    @pytest.mark.asyncio
    async def test_duplicate_event_id_is_counted_once(self):
        partial = self._result(3, result_id="batch-1", partial=True, state=2)
        final = self._result(3, result_id="batch-1", partial=False, state=1)
        rc = self._active_collector(
            [
                MagicMock(EventId=b"same", Result=partial),
                MagicMock(EventId=b"same", Result=partial),
                MagicMock(EventId=b"final", Result=final),
            ]
        )

        progression = await rc.collect_progression(3, timeout_s=1.0)

        assert progression.partial_results == (partial,)
        assert progression.duplicate_event_count == 1

    @pytest.mark.asyncio
    async def test_queue_overflow_prevents_complete_evidence(self):
        inline_child = self._result(
            1,
            result_id="single-1",
            partial=False,
            state=1,
            content=[MagicMock()],
        )
        final = self._result(3, result_id="batch-1", partial=False, state=1, content=[inline_child])
        rc = self._active_collector([MagicMock(EventId=b"1", Result=final)])
        rc._collector.dropped_event_count = 2

        progression = await rc.collect_progression(3, timeout_s=1.0)

        assert progression.queue_overflow_count == 2
        assert progression.is_complete is False

    @pytest.mark.asyncio
    async def test_collect_evidence_retains_one_deduplicated_lossless_stream(self):
        first = self._result(6, result_id="intervention-1", partial=False, state=1)
        second = self._result(3, result_id="batch-1", partial=True, state=2)
        rc = self._active_collector(
            [
                MagicMock(EventId=bytearray(b"1"), Result=first),
                MagicMock(EventId=bytearray(b"1"), Result=first),
                MagicMock(EventId=b"2", Result=second),
            ]
        )

        capture = await rc.collect_evidence(lambda results: len(results) == 2, timeout_s=1.0)

        assert isinstance(capture, ResultEventCapture)
        assert capture.all_results == (first, second)
        assert capture.duplicate_event_count == 1
        assert capture.timed_out is False
        assert capture.is_lossless is True

    @pytest.mark.asyncio
    async def test_collect_evidence_reports_timeout_and_queue_loss(self):
        rc = self._active_collector([])
        rc._collector.dropped_event_count = 1

        capture = await rc.collect_evidence(lambda _results: False, timeout_s=0.01)

        assert capture.timed_out is True
        assert capture.queue_overflow_count == 1
        assert capture.is_lossless is False

    @pytest.mark.asyncio
    async def test_collect_evidence_requires_active_context(self):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})

        with pytest.raises(RuntimeError, match="async context manager"):
            await rc.collect_evidence(lambda _results: True, timeout_s=0.01)

        with pytest.raises(RuntimeError, match="async context manager"):
            await rc.collect_progression(3, timeout_s=0.01)

    def test_same_result_id_cannot_falsely_resolve_parent_reference(self):
        child_stub = self._result(1, result_id="shared-id", partial=False, state=1)
        final = self._result(3, result_id="shared-id", partial=False, state=1, content=[child_stub])
        duplicate_id_result = self._result(1, result_id="shared-id", partial=False, state=1, content=[MagicMock()])

        assert ResultCollector._reference_closure(final, [duplicate_id_result, final]) == ("shared-id",)

    def test_reference_closure_follows_nested_job_batch_child_graph(self):
        intervention = self._result(6, result_id="intervention-1", partial=False, state=1)
        intervention_stub = self._result(6, result_id="intervention-1", partial=False, state=1)
        batch = self._result(3, result_id="batch-1", partial=True, state=2, content=[intervention_stub])
        batch_stub = self._result(3, result_id="batch-1", partial=True, state=2)
        job = self._result(4, result_id="job-1", partial=False, state=1, content=[batch_stub])

        assert ResultCollector._reference_closure(job, [batch, job], allow_partial_results=True) == ("intervention-1",)
        assert ResultCollector._reference_closure(job, [intervention, batch, job], allow_partial_results=True) == ()

    def test_reference_closure_merges_reordered_updates_with_same_parent_id(self):
        intervention = self._result(6, result_id="intervention-1", partial=False, state=1)
        single = self._result(1, result_id="single-1", partial=False, state=1, content=[MagicMock()])
        old_batch = self._result(
            3,
            result_id="batch-1",
            partial=True,
            state=2,
            content=[self._result(6, result_id="intervention-1", partial=False, state=1)],
        )
        new_batch = self._result(
            3,
            result_id="batch-1",
            partial=True,
            state=2,
            content=[self._result(1, result_id="single-1", partial=False, state=1)],
        )
        job = self._result(
            4,
            result_id="job-1",
            partial=False,
            state=1,
            references=[MagicMock(ResultId="batch-1")],
        )

        assert (
            ResultCollector._reference_closure(
                job,
                [new_batch, old_batch, single, intervention, job],
                allow_partial_results=True,
            )
            == ()
        )

    def test_reference_closure_ignores_empty_ids_and_rejects_parent_self_reference(self):
        parent = self._result(
            4,
            result_id="job-1",
            partial=False,
            state=1,
            content=[SimpleNamespace(ResultId="", ResultContent=[])],
            references=[SimpleNamespace(ResultId=""), SimpleNamespace(ResultId="job-1")],
        )

        assert ResultCollector._reference_closure(parent, [parent]) == ("job-1",)

    def test_reference_closure_terminates_inline_cycles(self):
        parent = self._result(4, result_id="job-1", partial=False, state=1)
        child = self._result(3, result_id="batch-1", partial=False, state=1, content=[parent])
        parent.ResultContent = [child]

        assert ResultCollector._reference_closure(parent, [parent, child]) == ()

    @pytest.mark.asyncio
    async def test_collect_progression_ignores_event_without_result(self):
        final = self._result(3, result_id="batch-1", partial=False, state=1)
        rc = self._active_collector(
            [
                MagicMock(EventId=b"empty", Result=None),
                MagicMock(EventId=b"final", Result=final),
            ]
        )

        progression = await rc.collect_progression(3, timeout_s=1.0)

        assert progression.final_result is final
        assert len(progression.source_events) == 2

    @pytest.mark.asyncio
    async def test_collect_progression_with_completed_initial_results(self):
        final = self._result(3, result_id="batch-1", partial=False, state=1)
        rc = self._active_collector([])
        rc._captured_results.append(final)
        progression = await rc.collect_progression(3, timeout_s=1.0)
        assert progression.final_result is final
        assert progression.is_complete is True


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
    @staticmethod
    def result(result_id, classification, *, process="", parent="", references=(), partial=False, tool="tool"):
        return SimpleNamespace(
            ResultMetaData=SimpleNamespace(
                ResultId=result_id,
                Classification=classification,
                IsPartial=partial,
                ResultState=2 if partial else 1,
                AssociatedEntities=[
                    SimpleNamespace(EntityId=tool),
                    SimpleNamespace(EntityId=process),
                    SimpleNamespace(EntityId=parent, EntityType=40),
                ],
            ),
            ResultContent=[],
            References=[SimpleNamespace(ResultId=value) for value in references],
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("parent_partial", [True, False])
    async def test_reported_parent_lookup_proves_operation_without_fabricating_fresh_completion(self, parent_partial):
        single = self.result("fresh-single", 1, process="program", parent="batch")
        batch = self.result("batch", 3, parent="job-result")
        job = self.result("job-result", 4, process="job", partial=parent_partial)
        old = self.result("old-single", 1, process="program", parent="batch")
        batch.ResultContent = [old, single]
        job.ResultContent = [batch]
        reader = AsyncMock(side_effect=lambda result_id: {"batch": batch, "job-result": job}[result_id])
        rc = TestCollectProgression._active_collector([SimpleNamespace(EventId=b"single", Result=single)])
        rc._collector.collect_pending = MagicMock(return_value=[])
        rc._parent_result_reader = reader

        outcome = await rc.collect_correlated_operation_outcome(
            4,
            lambda result: any(entity.EntityId == "job" for entity in result.ResultMetaData.AssociatedEntities),
            0.1,
            terminal_drain_seconds=0,
            operation_context_predicate=lambda result: any(
                entity.EntityId == "tool" for entity in result.ResultMetaData.AssociatedEntities
            ),
        )

        assert outcome.operation_confirmed
        assert outcome.operation_result is single
        assert outcome.terminal_result is None
        assert rc._confirmed_operation_ids == {"fresh-single"}
        assert rc.capture().all_results == (single,)
        assert len(rc.capture().source_events) == 1
        assert [call.args[0] for call in reader.await_args_list] == ["batch", "job-result"]
        assert not ResultCollector.progression_from_capture(rc.capture(), 4).is_complete

        pending = [SimpleNamespace(EventId=b"later-batch", Result=batch)]

        async def collect(**_kwargs):
            if pending:
                return [pending.pop(0)]
            await asyncio.sleep(0.01)
            return []

        rc._collector.collect = AsyncMock(side_effect=collect)
        later = await rc.collect_correlated_operation_outcome(
            4,
            lambda result: any(entity.EntityId == "job" for entity in result.ResultMetaData.AssociatedEntities),
            0.03,
            terminal_drain_seconds=0,
        )
        assert later.timed_out
        assert later.operation_result is None
        assert rc._confirmed_operation_ids == {"fresh-single"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize("problem", ["foreign", "missing", "cycle", "wrong_tool"])
    async def test_parent_lookup_does_not_relax_ownership_or_loop(self, problem):
        single = self.result(
            "single", 1, process="program", parent="batch", tool="other" if problem == "wrong_tool" else "tool"
        )
        batch = self.result("batch", 3, parent="job-result")
        job = self.result("job-result", 4, process="foreign" if problem == "foreign" else "job", partial=True)
        if problem == "cycle":
            batch = self.result("batch", 3, parent="batch")
        reader = AsyncMock(
            side_effect=lambda result_id: {"batch": batch, "job-result": None if problem == "missing" else job}[
                result_id
            ]
        )
        rc = TestCollectProgression._active_collector([SimpleNamespace(EventId=b"single", Result=single)])
        rc._collector.collect_pending = MagicMock(return_value=[])
        rc._parent_result_reader = reader

        outcome = await rc.collect_correlated_operation_outcome(
            4,
            lambda result: any(entity.EntityId == "job" for entity in result.ResultMetaData.AssociatedEntities),
            0.04,
            terminal_drain_seconds=0,
            operation_context_predicate=lambda result: any(
                entity.EntityId == "tool" for entity in result.ResultMetaData.AssociatedEntities
            ),
        )

        assert outcome.timed_out
        assert not outcome.operation_confirmed
        assert outcome.terminal_result is None
        requested = [call.args[0] for call in reader.await_args_list]
        assert len(requested) == len(set(requested))
        assert len(requested) <= 2

    @pytest.mark.asyncio
    async def test_queued_parent_event_is_used_before_lookup_without_issuing_another_start(self):
        single = self.result("single", 1, process="program", parent="job-result")
        job = self.result("job-result", 4, process="job", references=["single"])
        reader = AsyncMock()
        rc = TestCollectProgression._active_collector([SimpleNamespace(EventId=b"single", Result=single)])
        rc._collector.collect_pending = MagicMock(return_value=[SimpleNamespace(EventId=b"job", Result=job)])
        rc._parent_result_reader = reader

        outcome = await rc.collect_correlated_operation_outcome(
            4,
            lambda result: any(entity.EntityId == "job" for entity in result.ResultMetaData.AssociatedEntities),
            0.1,
            terminal_drain_seconds=0,
        )

        assert outcome.operation_confirmed
        assert outcome.operation_result is single
        assert outcome.terminal_result is job
        reader.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_other_domain_result_cannot_confirm_joining_operation_or_job(self):
        quality = self.result("quality", None, process="job")
        del quality.ResultMetaData.Classification
        rc = TestCollectProgression._active_collector([SimpleNamespace(EventId=b"quality", Result=quality)])

        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=lambda _: True,
            operation_timeout_s=0.02,
            terminal_drain_seconds=0,
        )

        assert not outcome.operation_confirmed
        assert outcome.operation_result is None
        assert outcome.terminal_result is None
        assert outcome.timed_out

    @pytest.mark.asyncio
    @pytest.mark.parametrize("links", ["references", "inline", "parent_entities"])
    @pytest.mark.parametrize("inline_single", [False, True])
    async def test_sparse_job_retains_owner_ancestry_but_counts_only_new_operations(self, links, inline_single):
        first = self.result("single-1", 1, process="program", parent="batch")
        batch = self.result("batch", 3, parent="job-result", partial=True)
        job = self.result("job-result", 4, process="job", partial=True)
        if links == "references":
            batch.References = [SimpleNamespace(ResultId="single-1")]
            job.References = [SimpleNamespace(ResultId="batch")]
        elif links == "inline":
            batch.ResultContent = [first]
            job.ResultContent = [batch]
        events = [first, batch, job]

        async def collect(**kwargs):
            if events:
                return [SimpleNamespace(Result=events.pop(0))]
            await asyncio.sleep(kwargs["timeout_s"])
            return []

        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        rc._collector = MagicMock(collect=collect, dropped_event_count=0)
        options = dict(
            requested_result_classification=4,
            predicate=lambda result: any(e.EntityId == "job" for e in result.ResultMetaData.AssociatedEntities),
            operation_predicate=lambda result: any(
                e.EntityId == "job" for e in result.ResultMetaData.AssociatedEntities
            ),
            operation_context_predicate=lambda result: any(
                e.EntityId == "tool" for e in result.ResultMetaData.AssociatedEntities
            ),
            operation_timeout_s=0.02,
            terminal_drain_seconds=0,
        )
        assert (await rc.collect_correlated_operation_outcome(**options)).operation_result is first
        second = self.result("single-2", 1, process="program", parent="batch")
        updated = self.result("batch", 3, parent="job-result", partial=True)
        if inline_single:
            updated.ResultContent = [second]
        else:
            updated.References = [SimpleNamespace(ResultId="single-2")]
            events.append(second)
        events.append(updated)
        outcome = await rc.collect_correlated_operation_outcome(**options)
        assert outcome.operation_result is second
        assert outcome.operation_confirmed
        assert not outcome.timed_out
        assert rc._confirmed_operation_ids == {"single-1", "single-2"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "problem",
        [
            "old_operation",
            "completed_owner",
            "aborted_owner",
            "conflicting_owner",
            "missing_owner",
            "foreign_owner",
            "wrong_tool",
            "wrong_parent_type",
            "cycle",
            "pre_reset_owner",
        ],
    )
    async def test_retained_parent_cannot_bypass_freshness_tool_or_phase_ownership(self, problem):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        root = self.result(
            "job-result",
            4,
            process="foreign-job" if problem == "foreign_owner" else "job",
            partial=problem not in {"completed_owner", "aborted_owner"},
        )
        if problem == "aborted_owner":
            root.ResultMetaData.ResultState = 3
        if problem != "missing_owner":
            rc._record_event(SimpleNamespace(Result=root))
        if problem == "conflicting_owner":
            foreign = self.result("foreign-root", 4, process="foreign-job", references=("single",), partial=True)
            rc._record_event(SimpleNamespace(Result=foreign))
        single = self.result(
            "single",
            1,
            process="program",
            parent="job-result",
            tool="foreign-tool" if problem == "wrong_tool" else "tool",
        )
        events = [single]
        if problem == "old_operation":
            rc._record_event(SimpleNamespace(Result=single))
        elif problem == "wrong_parent_type":
            single.ResultMetaData.AssociatedEntities[-1].EntityType = 27
        elif problem == "cycle":
            single.ResultMetaData.AssociatedEntities[-1].EntityId = "cycle-parent"
            events.append(self.result("cycle-parent", 3, parent="single", partial=True))
        elif problem == "completed_owner":
            events.append(root)

        async def collect(**kwargs):
            if events:
                return [SimpleNamespace(Result=events.pop(0))]
            await asyncio.sleep(kwargs["timeout_s"])
            return []

        rc._collector = MagicMock(collect=collect, dropped_event_count=0)
        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=lambda result: any(e.EntityId == "job" for e in result.ResultMetaData.AssociatedEntities),
            operation_predicate=lambda _: False,
            operation_context_predicate=lambda result: any(
                e.EntityId == "tool" for e in result.ResultMetaData.AssociatedEntities
            ),
            ownership_after_result_count=len(rc._captured_results) if problem == "pre_reset_owner" else 0,
            operation_timeout_s=0.02,
            terminal_drain_seconds=0,
        )
        assert outcome.timed_out
        assert not outcome.operation_confirmed
        assert outcome.terminal_result is None

    def test_parent_links_require_typed_nonempty_result_identity(self):
        result = self.result("child", 1)
        result.ResultMetaData.AssociatedEntities = [
            ua.Variant(SimpleNamespace(EntityId=ua.Variant(" parent "), EntityType=ua.Variant(40))),
            SimpleNamespace(EntityId="not-a-parent", EntityType=27),
            SimpleNamespace(EntityId="not-a-parent", EntityType=True),
            SimpleNamespace(EntityId="", EntityType=40),
        ]
        assert parent_result_ids(result) == frozenset({"parent"})

    @pytest.mark.asyncio
    @pytest.mark.parametrize("offset", [True, -1, "0"])
    async def test_invalid_ownership_boundary_is_rejected_before_collection(self, offset):
        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        rc._collector = MagicMock()
        with pytest.raises(ValueError, match="nonnegative"):
            await rc.collect_correlated_operation_outcome(4, lambda _: True, 0.01, ownership_after_result_count=offset)
        rc._collector.collect.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("phase", ["collection", "before_pacing"])
    async def test_loss_detected_after_poll_or_before_pacing_returns_unsettled_outcome(self, phase):
        result = SimpleNamespace(
            ResultMetaData=SimpleNamespace(
                ResultId="operation",
                Classification=1,
                IsPartial=False,
                ResultState=1,
            )
        )
        raw = MagicMock(dropped_event_count=0)

        async def collect(**kwargs):
            if phase == "collection":
                raw.dropped_event_count = 1
                return []
            return [SimpleNamespace(Result=result)]

        def match(candidate):
            if phase == "before_pacing":
                raw.dropped_event_count = 1
            return True

        raw.collect = collect
        collector = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        collector._collector = raw
        outcome = await collector.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=match,
            operation_timeout_s=0.01,
            terminal_drain_seconds=0.01,
        )
        assert outcome.timed_out
        assert outcome.queue_overflow_count == 1
        assert not outcome.operation_confirmed

    @pytest.mark.asyncio
    async def test_completed_program_terminal_retains_its_unique_operation_identity(self):
        result = SimpleNamespace(
            ResultMetaData=SimpleNamespace(
                ResultId="program-operation",
                Classification=1,
                IsPartial=False,
                ResultState=1,
            )
        )
        collector = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        collector._collector = MagicMock(
            collect=AsyncMock(return_value=[SimpleNamespace(Result=result)]),
            dropped_event_count=0,
        )
        outcome = await collector.collect_correlated_operation_outcome(
            requested_result_classification=1,
            predicate=lambda item: item is result,
            operation_timeout_s=0.01,
        )
        assert outcome.operation_result is result
        assert outcome.terminal_result is result
        assert "program-operation" in collector._confirmed_operation_ids

    @pytest.mark.asyncio
    @pytest.mark.parametrize("during_drain", [False, True])
    async def test_capture_loss_including_pacing_cannot_authorize_another_start(self, during_drain):
        from types import SimpleNamespace

        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        result = SimpleNamespace(
            ResultMetaData=SimpleNamespace(Classification=1, IsPartial=False, ResultState=1, ResultId="operation")
        )
        events = [SimpleNamespace(Result=result)]
        raw = MagicMock(dropped_event_count=0 if during_drain else 1)

        async def collect(**_kwargs):
            if events:
                return [events.pop(0)]
            raw.dropped_event_count = 1
            return []

        raw.collect = collect
        rc._collector = raw
        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=lambda _: True,
            operation_timeout_s=0.02,
            terminal_drain_seconds=0.01,
        )
        assert not outcome.operation_confirmed
        assert outcome.timed_out
        assert outcome.queue_overflow_count == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize("linked", [False, True])
    @pytest.mark.parametrize("inline", [False, True])
    async def test_tool_only_child_requires_observed_parent_relationship(self, linked, inline):
        from types import SimpleNamespace

        child = SimpleNamespace(
            ResultMetaData=SimpleNamespace(Classification=1, IsPartial=False, ResultState=1, ResultId="child"),
        )
        parent = SimpleNamespace(
            ResultMetaData=SimpleNamespace(Classification=4, IsPartial=True, ResultState=2, ResultId="parent"),
            References=[SimpleNamespace(ResultId="child")] if linked and not inline else [],
            ResultContent=[child] if linked and inline else [],
        )
        events = ([] if inline else [SimpleNamespace(Result=child)]) + [SimpleNamespace(Result=parent)]

        async def collect(**_kwargs):
            if events:
                return [events.pop(0)]
            await asyncio.sleep(0.001)
            return []

        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        rc._collector = MagicMock(collect=collect, dropped_event_count=0)
        outcome = await rc.collect_correlated_operation_outcome(
            requested_result_classification=4,
            predicate=lambda result: result is parent,
            operation_timeout_s=0.02,
            terminal_drain_seconds=0,
        )
        assert outcome.operation_confirmed is linked
        assert outcome.timed_out is not linked

    @pytest.mark.asyncio
    async def test_repeated_result_id_with_new_event_id_cannot_confirm_another_start(self):
        from types import SimpleNamespace

        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        result = SimpleNamespace(
            ResultMetaData=SimpleNamespace(Classification=1, IsPartial=False, ResultState=1, ResultId="same-result"),
        )
        events = [SimpleNamespace(EventId=b"first", Result=result)]

        async def collect(**_kwargs):
            if events:
                return [events.pop(0)]
            await asyncio.sleep(0.001)
            return []

        rc._collector = MagicMock(collect=collect, dropped_event_count=0)
        kwargs = dict(
            requested_result_classification=4,
            predicate=lambda _: True,
            operation_timeout_s=0.02,
            terminal_drain_seconds=0,
        )
        assert (await rc.collect_correlated_operation_outcome(**kwargs)).operation_confirmed
        events.append(SimpleNamespace(EventId=b"second", Result=result))
        assert (await rc.collect_correlated_operation_outcome(**kwargs)).timed_out

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
        meta = MagicMock(Classification=4, IsPartial=False, ResultState=1, ResultId="job-terminal")
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
        single_meta = MagicMock(Classification=1, IsPartial=False, ResultState=1, ResultId="operation")
        single_result = MagicMock(ResultMetaData=single_meta)
        event1 = MagicMock(Result=single_result)

        # Second event during drain: terminal job result
        job_meta = MagicMock(Classification=4, IsPartial=False, ResultState=1, ResultId="job-terminal")
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
        single_meta = MagicMock(Classification=1, IsPartial=False, ResultState=1, ResultId="operation")
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
        job_meta = MagicMock(Classification=4, IsPartial=False, ResultState=1, ResultId="job-terminal")
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
        single_meta = MagicMock(Classification=1, IsPartial=False, ResultState=1, ResultId="operation")
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
        single_meta = MagicMock(Classification=1, IsPartial=False, ResultState=1, ResultId="operation")
        single_result = MagicMock(ResultMetaData=single_meta)
        event_single = MagicMock(Result=single_result)
        event_none = MagicMock(Result=None)
        job_meta = MagicMock(Classification=4, IsPartial=False, ResultState=1, ResultId="job-terminal")
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

    def test_collect_pending_terminal_reports_first_terminal_even_when_another_state_is_expected(self):
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

        assert rc.collect_pending_terminal(4, lambda _: True, expected_terminal_state=3) is completed

    @pytest.mark.asyncio
    async def test_collect_correlated_operation_outcome_matches_aborted_terminal_state(self):
        from helpers.namespaces import ResultState

        rc = ResultCollector(MagicMock(), {NS_IJT_BASE: 7})
        aborted_meta = MagicMock(
            Classification=4, IsPartial=False, ResultState=ResultState.ABORTED, ResultId="aborted-terminal"
        )
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
