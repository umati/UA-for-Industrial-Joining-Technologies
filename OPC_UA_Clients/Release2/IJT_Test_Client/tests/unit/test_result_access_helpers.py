"""
Unit tests for specification_tests/test_result_access.py helper functions.

Validates:
- _extract_sequence_number across all OPC UA live payload shapes (Variant, ExtensionObject, dict, object)
- Rejection of invalid types (bool, string, negative, out-of-range UInt64)
- _get_request_results_config error propagation on non-existent profile files
- Environment variable overrides for filter strategy
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asyncua import ua

from helpers.target_server_cu_config import UINT64_MAX, RequestResultsConfig
from specification_tests.test_result_access import (
    _assert_request_results_output,
    _call_get_latest_result,
    _call_request_results,
    _collect_matching_requested_event,
    _extract_is_simulated,
    _extract_sequence_number,
    _get_request_results_args,
    _get_request_results_config,
    _RequestedResultBuffer,
    _resolve_requested_event_correlation_policy,
    _trigger_single_and_get_latest,
)


def _requested_event(sequence=42, result_id="EXPECTED", is_simulated=None, subvariables=True):
    meta = SimpleNamespace(ResultId=result_id, SequenceNumber=sequence)
    if is_simulated is not None:
        meta.IsSimulated = is_simulated
    event = SimpleNamespace(EventType=ua.NodeId(1035, 7), Result=SimpleNamespace(ResultMetaData=meta))
    if subvariables:
        # asyncua names ResultType sub-variable event fields by their browse path.
        setattr(event, "Result/ResultMetaData/ResultId", result_id)
        setattr(event, "Result/ResultMetaData/SequenceNumber", sequence)
    return event


def _single_result_args(sequence=42):
    return _get_request_results_args(
        SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=sequence)),
        RequestResultsConfig(),
        single_result=True,
    )


async def test_requested_event_skips_out_of_range_sequence():
    collector = SimpleNamespace(
        collect=AsyncMock(side_effect=[[_requested_event(99, "A")], [_requested_event(42, "B")]])
    )
    event = await _collect_matching_requested_event(
        collector, ua.NodeId(1035, 7), _single_result_args(), expected_result_id=None, timeout_s=0.1
    )
    assert event.Result.ResultMetaData.SequenceNumber == 42
    assert collector.collect.await_count == 2


async def test_requested_event_rejects_previous_sequence_when_expected_sequence_specified():
    """Regression test for Finding 4: Replay must not accept N-1 as proof of N.

    When querying [41..42] for triggered sequence 42 with synthetic/simulated identity
    (expected_result_id=None), sequence 41 (N-1) must be skipped, and sequence 42 (N)
    must be matched and returned.
    """
    collector = SimpleNamespace(
        collect=AsyncMock(
            side_effect=[
                [_requested_event(41, "SYNTHETIC_PREV")],
                [_requested_event(42, "SYNTHETIC_TRIGGERED")],
            ]
        )
    )
    event = await _collect_matching_requested_event(
        collector,
        ua.NodeId(1035, 7),
        _single_result_args(sequence=42),
        expected_result_id=None,
        timeout_s=0.1,
        expected_sequence=42,
    )
    assert event.Result.ResultMetaData.SequenceNumber == 42
    assert event.Result.ResultMetaData.ResultId == "SYNTHETIC_TRIGGERED"
    assert collector.collect.await_count == 2


async def test_requested_event_fails_when_only_previous_sequence_is_replayed():
    """Regression test for Finding 4: If only N-1 arrives, the collector must fail rather than accept it."""
    collector = SimpleNamespace(collect=AsyncMock(side_effect=[[_requested_event(41, "SYNTHETIC_PREV")], []]))
    with pytest.raises(pytest.fail.Exception, match="No matching RequestedResultEvent"):
        await _collect_matching_requested_event(
            collector,
            ua.NodeId(1035, 7),
            _single_result_args(sequence=42),
            expected_result_id=None,
            timeout_s=0.1,
            expected_sequence=42,
        )


async def test_requested_event_simulated_trigger_accepts_simulated_replay():
    collector = SimpleNamespace(
        collect=AsyncMock(side_effect=[[_requested_event(42, "REAL", False)], [_requested_event(42, "SYN", True)]])
    )
    event = await _collect_matching_requested_event(
        collector,
        ua.NodeId(1035, 7),
        _single_result_args(),
        expected_result_id=None,
        timeout_s=0.1,
        require_simulated_replay=True,
    )
    assert event.Result.ResultMetaData.ResultId == "SYN"


async def test_requested_event_simulated_trigger_skips_when_only_real_results_replayed():
    collector = SimpleNamespace(collect=AsyncMock(side_effect=[[_requested_event(42, "REAL", False)], []]))
    with pytest.raises(pytest.skip.Exception, match="does not replay simulated results"):
        await _collect_matching_requested_event(
            collector,
            ua.NodeId(1035, 7),
            _single_result_args(),
            expected_result_id=None,
            timeout_s=0.1,
            require_simulated_replay=True,
        )


@pytest.mark.parametrize(
    ("meta", "expected"),
    [({"IsSimulated": True}, True), ({"IsSimulated": False}, False), ({}, None), ({"IsSimulated": 1}, None)],
)
def test_extract_is_simulated(meta, expected):
    assert _extract_is_simulated({"ResultMetaData": meta}) is expected
    assert _extract_is_simulated(None) is None


async def test_requested_event_skips_unrelated_identity_and_matches_controller_result():
    collector = SimpleNamespace(collect=AsyncMock(side_effect=[[_requested_event(41, "OTHER")], [_requested_event()]]))
    args = _get_request_results_args(
        SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=42)), RequestResultsConfig(), single_result=True
    )
    event = await _collect_matching_requested_event(
        collector, ua.NodeId(1035, 7), args, expected_result_id="EXPECTED", timeout_s=0.1
    )
    assert event.Result.ResultMetaData.ResultId == "EXPECTED"
    assert collector.collect.await_count == 2


@pytest.mark.parametrize("field", ["ResultId", "SequenceNumber"])
async def test_requested_event_rejects_inconsistent_payload(field):
    event = _requested_event()
    setattr(event, f"Result/ResultMetaData/{field}", "WRONG" if field == "ResultId" else 41)
    collector = SimpleNamespace(collect=AsyncMock(return_value=[event]))
    with pytest.raises(AssertionError, match="disagrees"):
        await _collect_matching_requested_event(
            collector, ua.NodeId(1035, 7), _get_request_results_args(), expected_result_id=None, timeout_s=0.1
        )


async def test_requested_event_without_metadata_subvariables_matches_on_payload():
    event = _requested_event(subvariables=False)
    collector = SimpleNamespace(collect=AsyncMock(return_value=[event]))
    assert (
        await _collect_matching_requested_event(
            collector, ua.NodeId(1035, 7), _get_request_results_args(), expected_result_id="EXPECTED", timeout_s=0.1
        )
        is event
    )


async def test_requested_event_missing_delivery_fails():
    collector = SimpleNamespace(collect=AsyncMock(return_value=[]))
    with pytest.raises(pytest.fail.Exception, match="No matching RequestedResultEvent"):
        await _collect_matching_requested_event(
            collector, ua.NodeId(1035, 7), _get_request_results_args(), expected_result_id=None, timeout_s=0.1
        )


async def test_requested_event_accepts_synthetic_identity_within_requested_range():
    event = _requested_event(42, "SYNTHETIC")
    collector = SimpleNamespace(collect=AsyncMock(return_value=[event]))
    assert (
        await _collect_matching_requested_event(
            collector, ua.NodeId(1035, 7), _get_request_results_args(), expected_result_id=None, timeout_s=0.1
        )
        is event
    )


@pytest.mark.parametrize(
    "meta",
    [
        {"ResultId": "TRIGGERED_UUID", "IsSimulated": False},
        {"ResultId": "TRIGGERED_UUID", "IsSimulated": True},
        {"ResultId": "TRIGGERED_UUID"},
    ],
)
def test_resolve_requested_event_correlation_policy_simulator(meta):
    """Simulator trigger accepts synthetic replay identity regardless of IsSimulated value."""
    sim_trigger = SimpleNamespace(is_simulator=True)
    payload = SimpleNamespace(ResultMetaData=SimpleNamespace(**meta))
    expected_id, require_simulated = _resolve_requested_event_correlation_policy(sim_trigger, payload)
    assert expected_id is None
    assert require_simulated is False


def test_resolve_requested_event_correlation_policy_controller_production():
    """Controller production result requires strict ResultId correlation and rejects missing IDs."""
    ctrl_trigger = SimpleNamespace(is_simulator=False)

    payload_valid = SimpleNamespace(ResultMetaData=SimpleNamespace(ResultId="CTRL_RESULT_123", IsSimulated=False))
    expected_id, require_simulated = _resolve_requested_event_correlation_policy(ctrl_trigger, payload_valid)
    assert expected_id == "CTRL_RESULT_123"
    assert require_simulated is False

    payload_empty = SimpleNamespace(ResultMetaData=SimpleNamespace(ResultId="", IsSimulated=False))
    with pytest.raises(AssertionError, match="Triggered controller result has no ResultId"):
        _resolve_requested_event_correlation_policy(ctrl_trigger, payload_empty)

    payload_none = SimpleNamespace(ResultMetaData=SimpleNamespace(ResultId=None, IsSimulated=False))
    with pytest.raises(AssertionError, match="Triggered controller result has no ResultId"):
        _resolve_requested_event_correlation_policy(ctrl_trigger, payload_none)


def test_resolve_requested_event_correlation_policy_controller_simulated():
    """Controller simulated result enables simulated replay check."""
    ctrl_trigger = SimpleNamespace(is_simulator=False)
    payload_sim = SimpleNamespace(ResultMetaData=SimpleNamespace(ResultId="SIM_RESULT_123", IsSimulated=True))
    expected_id, require_simulated = _resolve_requested_event_correlation_policy(ctrl_trigger, payload_sim)
    assert expected_id is None
    assert require_simulated is True


@pytest.mark.parametrize("exc", [TimeoutError(), ua.UaStatusCodeError(ua.StatusCodes.BadTimeout)])
async def test_latest_result_failure_reports_retrieval_error(monkeypatch, exc):
    monkeypatch.setattr(
        "specification_tests.test_result_access.find_child_by_browse_name",
        AsyncMock(return_value=SimpleNamespace(nodeid=ua.NodeId(1, 2))),
    )
    rm = SimpleNamespace(call_method=AsyncMock(side_effect=exc))
    with pytest.raises(pytest.fail.Exception, match="failed before result data could be checked"):
        await _call_get_latest_result(rm, 2)


async def test_missing_triggered_result_does_not_report_missing_sequence_number(monkeypatch):
    from helpers.namespaces import NS_MACH_RESULT

    monkeypatch.setattr("specification_tests.test_result_access._get_result_management", AsyncMock())
    monkeypatch.setattr(
        "specification_tests.test_result_access._call_get_latest_result", AsyncMock(return_value=(None, None))
    )
    trigger = SimpleNamespace(trigger_single=AsyncMock(return_value=SimpleNamespace(triggered=True)))
    with pytest.raises(pytest.fail.Exception, match="no result data after a successful trigger"):
        await _trigger_single_and_get_latest(object(), trigger, {NS_MACH_RESULT: 2})


class TestExtractSequenceNumber:
    def test_extract_none_returns_none(self):
        assert _extract_sequence_number(None) is None

    def test_extract_from_object_with_result_metadata(self):
        obj = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=42))
        assert _extract_sequence_number(obj) == 42

    def test_extract_from_dict_with_result_metadata(self):
        data = {"ResultMetaData": {"SequenceNumber": 123}}
        assert _extract_sequence_number(data) == 123

    def test_extract_from_direct_result_metadata(self):
        data = {"SequenceNumber": 999}
        assert _extract_sequence_number(data) == 999

    def test_extract_case_variants(self):
        assert _extract_sequence_number({"ResultMetaData": {"sequence_number": 55}}) == 55
        assert _extract_sequence_number({"ResultMetaData": {"Sequence_Number": 77}}) == 77

    def test_extract_from_variant_wrapper(self):
        variant = ua.Variant(500, ua.VariantType.UInt64)
        obj = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=variant))
        assert _extract_sequence_number(obj) == 500

    def test_extract_from_extension_object_body(self):
        body = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=789))
        ext = SimpleNamespace(Body=body)
        assert _extract_sequence_number(ext) == 789

    def test_extract_from_nested_variant_and_extension_object(self):
        inner = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=ua.Variant(1001, ua.VariantType.UInt64)))
        ext = SimpleNamespace(Body=inner)
        outer_variant = ua.Variant(ext, ua.VariantType.ExtensionObject)
        assert _extract_sequence_number(outer_variant) == 1001

    def test_extract_rejects_bool(self):
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": True}}) is None
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": False}}) is None

    def test_extract_rejects_zero_or_negative(self):
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": 0}}) is None
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": -10}}) is None

    def test_extract_rejects_overflow(self):
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": UINT64_MAX + 1}}) is None

    def test_extract_accepts_uint64_max(self):
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": UINT64_MAX}}) == UINT64_MAX

    def test_extract_rejects_non_numeric_string(self):
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": "not-a-number"}}) is None

    @pytest.mark.parametrize("value", ["42", b"42", 42.5])
    def test_extract_rejects_non_integer_values(self, value):
        assert _extract_sequence_number({"ResultMetaData": {"SequenceNumber": value}}) is None

    def test_sequence_filtered_args_require_decoded_trigger_sequence(self):
        with pytest.raises(pytest.fail.Exception, match="cannot be correlated safely"):
            _get_request_results_args(None, RequestResultsConfig())
        with pytest.raises(pytest.fail.Exception, match="cannot be correlated safely"):
            _get_request_results_args(b"opaque-extension-object", RequestResultsConfig())

    def test_timestamp_args_do_not_require_trigger_sequence(self):
        args = _get_request_results_args(None, RequestResultsConfig(filter_strategy="timestamp"))
        assert args[0].Value == 0
        assert args[1].Value == 0

    def test_request_results_output_requires_three_fields_and_good_status(self):
        assert _assert_request_results_output([0.0, 0, "OK"], "RequestResults")[1] == 0
        with pytest.raises(AssertionError, match="must return"):
            _assert_request_results_output([0.0, 0], "RequestResults")
        with pytest.raises(AssertionError, match="non-zero Status"):
            _assert_request_results_output([0.0, 1, "Failed"], "RequestResults")


class TestGetRequestResultsConfig:
    def test_default_when_no_env(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = _get_request_results_config()
            assert cfg.filter_strategy == "sequence_number"
            assert cfg.from_sequence_number == 1
            assert cfg.to_sequence_number == 50

    def test_missing_profile_raises_file_not_found(self):
        with patch.dict(os.environ, {"OPCUA_TARGET_SERVER_PROFILE": "nonexistent_profile_path.sut.yaml"}):
            with pytest.raises(FileNotFoundError, match="Configured profile does not exist"):
                _get_request_results_config()

    def test_env_strategy_override(self):
        with patch.dict(os.environ, {"OPCUA_REQUEST_RESULTS_FILTER_STRATEGY": "timestamp"}):
            cfg = _get_request_results_config()
            assert cfg.filter_strategy == "timestamp"

    def test_env_strategy_both(self):
        with patch.dict(os.environ, {"OPCUA_REQUEST_RESULTS_FILTER_STRATEGY": "both"}):
            cfg = _get_request_results_config()
            assert cfg.filter_strategy == "both"


class TestSingleResultAndCallRequestResults:
    def test_single_result_with_known_sequence(self):
        import datetime

        from asyncua.ua.ua_binary import variant_to_binary

        obj = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=142))
        args = _get_request_results_args(
            obj, RequestResultsConfig(from_sequence_number=10, to_sequence_number=50), single_result=True
        )
        assert args[0].Value == 141
        assert args[1].Value == 142
        assert isinstance(args[2].Value, datetime.datetime)
        assert isinstance(args[3].Value, datetime.datetime)
        assert args[2].Value.tzinfo is not None
        assert all(variant_to_binary(arg) for arg in args)

    def test_single_result_without_triggered_sequence_uses_configured_from(self):
        from specification_tests.test_result_access import _NO_RESULT_DATA

        args = _get_request_results_args(
            _NO_RESULT_DATA, RequestResultsConfig(from_sequence_number=100, to_sequence_number=150), single_result=True
        )
        assert args[0].Value == 99
        assert args[1].Value == 100

    def test_single_result_with_timestamp_strategy_zeros_sequences(self):
        obj = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=142))
        args = _get_request_results_args(obj, RequestResultsConfig(filter_strategy="timestamp"), single_result=True)
        assert args[0].Value == 0
        assert args[1].Value == 0

    def test_single_result_window_clamps_at_uint64_lower_bound(self):
        obj = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=1))
        args = _get_request_results_args(obj, RequestResultsConfig(), single_result=True)
        assert args[0].Value == 1
        assert args[1].Value == 1

    async def test_result_buffer_accepts_single_matching_update(self):
        buffer = _RequestedResultBuffer(MagicMock(), ua.NodeId(1, 1))
        expected = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=42, ResultId="EXPECTED"))
        buffer.datachange_notification(None, expected, None)
        update = await buffer.collect_result(timeout_s=0.1)
        assert update.value is expected

    async def test_result_buffer_accepts_vendor_batch_with_new_ids(self):
        buffer = _RequestedResultBuffer(MagicMock(), ua.NodeId(1, 1))
        for sequence_number in range(40, 45):
            value = SimpleNamespace(
                ResultMetaData=SimpleNamespace(
                    SequenceNumber=sequence_number,
                    ResultId=f"REPLAY-{sequence_number}",
                )
            )
            buffer.datachange_notification(None, value, None)
        update = await buffer.collect_result(timeout_s=0.1)
        assert update.value.ResultMetaData.SequenceNumber == 40
        assert update.value.ResultMetaData.ResultId == "REPLAY-40"

    async def test_result_buffer_discards_stale_initial_update(self):
        buffer = _RequestedResultBuffer(MagicMock(), ua.NodeId(1, 1))
        stale = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=41, ResultId="STALE"))
        fresh = SimpleNamespace(ResultMetaData=SimpleNamespace(SequenceNumber=42, ResultId="FRESH"))
        buffer.datachange_notification(None, stale, None)
        buffer.discard_pending()
        buffer.datachange_notification(None, fresh, None)
        update = await buffer.collect_result(timeout_s=0.1)
        assert update.value is fresh

    async def test_call_request_results_success_first_attempt(self):
        rm_node = MagicMock()
        rm_node.call_method = AsyncMock(return_value=[0.0, 0, "OK"])
        rr_node = MagicMock(nodeid=ua.NodeId(1234, 1))
        before_attempt = MagicMock()

        res = await _call_request_results(
            rm_node,
            rr_node,
            [ua.Variant(1, ua.VariantType.UInt64)],
            before_attempt=before_attempt,
        )
        assert res == [0.0, 0, "OK"]
        assert rm_node.call_method.await_count == 1
        before_attempt.assert_called_once_with()

    async def test_call_request_results_retries_on_uncertain_and_succeeds(self):
        rm_node = MagicMock()
        uncertain_error = ua.UaError("The operation was uncertain.(Uncertain)")
        rm_node.call_method = AsyncMock(side_effect=[uncertain_error, [0.0, 0, "OK"]])
        rr_node = MagicMock(nodeid=ua.NodeId(1234, 1))

        res = await _call_request_results(rm_node, rr_node, [], max_retries=2, retry_delay_s=0.01)
        assert res == [0.0, 0, "OK"]
        assert rm_node.call_method.await_count == 2

    async def test_call_request_results_default_retry_window_outlasts_prior_stream(self):
        rm_node = MagicMock()
        uncertain_error = ua.UaError("The operation was uncertain.(Uncertain)")
        rm_node.call_method = AsyncMock(side_effect=[uncertain_error] * 4 + [[0.0, 0, "OK"]])
        rr_node = MagicMock(nodeid=ua.NodeId(1234, 1))

        with patch("specification_tests.test_result_access.asyncio.sleep", new=AsyncMock()):
            res = await _call_request_results(rm_node, rr_node, [])

        assert res == [0.0, 0, "OK"]
        assert rm_node.call_method.await_count == 5

    async def test_call_request_results_exhausts_retries_and_raises(self):
        rm_node = MagicMock()
        uncertain_error = ua.UaError("The operation was uncertain.(Uncertain)")
        rm_node.call_method = AsyncMock(side_effect=uncertain_error)
        rr_node = MagicMock(nodeid=ua.NodeId(1234, 1))

        with pytest.raises(ua.UaError, match="uncertain"):
            await _call_request_results(rm_node, rr_node, [], max_retries=2, retry_delay_s=0.01)
        assert rm_node.call_method.await_count == 2

    async def test_call_request_results_raises_immediately_on_non_retryable_error(self):
        rm_node = MagicMock()
        bad_syntax_error = ua.UaError("Bad syntax error")
        rm_node.call_method = AsyncMock(side_effect=bad_syntax_error)
        rr_node = MagicMock(nodeid=ua.NodeId(1234, 1))

        with pytest.raises(ua.UaError, match="Bad syntax error"):
            await _call_request_results(rm_node, rr_node, [], max_retries=3, retry_delay_s=0.01)
        assert rm_node.call_method.await_count == 1
