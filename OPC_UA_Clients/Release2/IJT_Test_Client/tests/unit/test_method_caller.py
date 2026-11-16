"""
Unit tests for helpers/method_caller.py

Tests the pure-Python components that do not require a live OPC UA server:
  - OpcUaStatusHelper static methods
  - MethodCallResult dataclass and output_list property
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from asyncua import ua

from helpers.method_caller import MethodCallResult, OpcUaStatusHelper
from helpers.sut_manifest import manifest_file_sha256


async def test_public_method_wrapper_forwards_raw_status_and_dispatch_contract(monkeypatch):
    import helpers.method_caller as module

    raw = MethodCallResult(success=False, rpc_dispatched=True, method_status_code=ua.StatusCodes.Uncertain, output=[2])
    route = AsyncMock(return_value=raw)
    monkeypatch.setattr(module, "find_and_call_method_preserving_status", route)
    parent = object()
    before_dispatch = MagicMock()
    result = await module.find_and_call_method(
        parent,
        "IncrementJoiningProcessCounter",
        7,
        "tool",
        timeout=3,
        target_server_authorized=True,
        preserve_status=True,
        before_dispatch=before_dispatch,
    )
    assert result is raw
    route.assert_awaited_once_with(
        parent,
        "IncrementJoiningProcessCounter",
        7,
        "tool",
        timeout=3,
        target_server_authorized=True,
        before_dispatch=before_dispatch,
    )


async def test_dispatch_hook_is_rejected_on_legacy_call_route_before_discovery(monkeypatch):
    import helpers.method_caller as module

    lookup = AsyncMock()
    monkeypatch.setattr(module, "find_child_by_browse_name", lookup)
    with pytest.raises(ValueError, match="status-preserving"):
        await module.find_and_call_method(object(), "SelectJoiningProcess", 7, before_dispatch=MagicMock())
    lookup.assert_not_awaited()


@pytest.mark.parametrize(
    "method_status,business_status",
    [
        (ua.StatusCodes.Good, 0),
        (ua.StatusCodes.Uncertain, 2),
        (ua.StatusCodes.Uncertain, 4),
        (ua.StatusCodes.BadInvalidArgument, 2),
    ],
)
async def test_raw_method_call_retains_uncertain_and_bad_outputs(monkeypatch, method_status, business_status):
    from helpers.method_caller import call_method_preserving_status, is_target_method_call_authorized

    monkeypatch.delenv("OPCUA_TARGET_SERVER_PROFILE", raising=False)
    parent = MagicMock(nodeid=ua.NodeId(1, 2))
    method = MagicMock(nodeid=ua.NodeId(2, 2))
    method.read_browse_name = AsyncMock(return_value=ua.QualifiedName("IncrementJoiningProcessCounter", 2))

    async def service_call(requests):
        assert is_target_method_call_authorized()
        assert requests[0].InputArguments[0].Value == "tool"
        return [
            ua.CallMethodResult(
                StatusCode=ua.StatusCode(method_status),
                InputArgumentResults=[ua.StatusCode(ua.StatusCodes.Good)],
                OutputArguments=[ua.Variant(business_status, ua.VariantType.Int64), ua.Variant("message")],
            )
        ]

    parent.session.call = AsyncMock(side_effect=service_call)
    result = await call_method_preserving_status(parent, method, "tool", target_server_authorized=True)
    assert result.service_good_confirmed
    assert result.rpc_dispatched
    assert result.method_status_code == method_status
    assert result.output_list == [business_status, "message"]
    assert result.success == (method_status == ua.StatusCodes.Good)
    assert result.input_argument_status_codes == (ua.StatusCodes.Good,)
    assert not is_target_method_call_authorized()
    parent.call_method.assert_not_called()


@pytest.mark.parametrize("failure", [TimeoutError(), ua.UaStatusCodeError(ua.StatusCodes.BadSessionClosed)])
async def test_raw_method_service_failure_does_not_invent_confirmed_outputs(monkeypatch, failure):
    from helpers.method_caller import call_method_preserving_status, is_target_method_call_authorized

    monkeypatch.delenv("OPCUA_TARGET_SERVER_PROFILE", raising=False)
    parent = MagicMock(nodeid=ua.NodeId(1, 2))
    method = MagicMock(nodeid=ua.NodeId(2, 2))
    method.read_browse_name = AsyncMock(return_value=ua.QualifiedName("IncrementJoiningProcessCounter", 2))
    parent.session.call = AsyncMock(side_effect=failure)
    result = await call_method_preserving_status(parent, method, target_server_authorized=True)
    assert not result.service_good_confirmed
    assert result.method_status_code is None
    assert result.output_list == []
    assert result.rpc_dispatched
    assert result.error is failure
    assert not is_target_method_call_authorized()


async def test_raw_state_changing_call_enforces_actual_browse_name(monkeypatch, tmp_path):
    from helpers.method_caller import call_method_preserving_status

    path = tmp_path / "reviewed.yaml"
    path.write_text("reviewed", encoding="utf-8")
    monkeypatch.setenv("OPCUA_TARGET_SERVER_PROFILE", str(path))
    monkeypatch.setenv("OPCUA_TARGET_MANIFEST_SHA256", manifest_file_sha256(path))
    parent = MagicMock(nodeid=ua.NodeId(1, 2))
    parent.session.call = AsyncMock()
    method = MagicMock(nodeid=ua.NodeId(2, 2))
    method.read_browse_name = AsyncMock(return_value=ua.QualifiedName("IncrementJoiningProcessCounter", 2))
    with pytest.raises(pytest.skip.Exception, match="explicitly configured target workflow"):
        await call_method_preserving_status(parent, method)
    parent.session.call.assert_not_awaited()


@pytest.mark.parametrize("response_count", [0, 2])
async def test_raw_call_rejects_invalid_response_cardinality(monkeypatch, response_count):
    from helpers.method_caller import call_method_preserving_status

    monkeypatch.delenv("OPCUA_TARGET_SERVER_PROFILE", raising=False)
    parent = MagicMock(nodeid=ua.NodeId(1, 2))
    method = MagicMock(nodeid=ua.NodeId(2, 2))
    method.read_browse_name = AsyncMock(return_value=ua.QualifiedName("IncrementJoiningProcessCounter", 2))
    parent.session.call = AsyncMock(return_value=[ua.CallMethodResult()] * response_count)
    result = await call_method_preserving_status(parent, method, target_server_authorized=True)
    assert not result.success
    assert isinstance(result.error, ValueError)
    assert result.method_status_code is None
    assert result.output_list == []


@pytest.mark.parametrize("exists", [False, True])
async def test_raw_discovery_does_not_claim_rpc_dispatch_when_method_is_missing(monkeypatch, exists):
    from helpers.method_caller import find_and_call_method_preserving_status

    monkeypatch.delenv("OPCUA_TARGET_SERVER_PROFILE", raising=False)
    method = MagicMock()
    find = AsyncMock(return_value=method if exists else None)
    call = AsyncMock(return_value=MethodCallResult(success=True, rpc_dispatched=True))
    monkeypatch.setattr("helpers.method_caller.find_child_by_browse_name", find)
    monkeypatch.setattr("helpers.method_caller.call_method_preserving_status", call)
    result = await find_and_call_method_preserving_status(
        MagicMock(), "IncrementJoiningProcessCounter", 7, target_server_authorized=True
    )
    assert result.rpc_dispatched == exists
    if exists:
        call.assert_awaited_once()
    else:
        call.assert_not_called()
        assert isinstance(result.error, LookupError)


async def test_raw_identity_lookup_failure_is_not_an_attempted_mutation(monkeypatch):
    from helpers.method_caller import call_method_preserving_status

    monkeypatch.delenv("OPCUA_TARGET_SERVER_PROFILE", raising=False)
    parent = MagicMock()
    parent.session.call = AsyncMock()
    method = MagicMock()
    method.read_browse_name = AsyncMock(side_effect=TimeoutError())
    result = await call_method_preserving_status(parent, method, target_server_authorized=True)
    assert result.rpc_dispatched is False
    assert not result.success
    assert isinstance(result.error, TimeoutError)
    parent.session.call.assert_not_awaited()


async def test_dispatch_intent_is_written_only_after_discovery_and_before_rpc(monkeypatch):
    from helpers.method_caller import call_method_preserving_status

    monkeypatch.delenv("OPCUA_TARGET_SERVER_PROFILE", raising=False)
    parent = MagicMock()
    method = MagicMock()
    method.read_browse_name = AsyncMock(return_value=ua.QualifiedName("IncrementJoiningProcessCounter", 2))
    intent: list[str] = []

    async def rpc(requests):
        assert intent == ["durable intent"]
        return [
            ua.CallMethodResult(
                StatusCode=ua.StatusCode(ua.StatusCodes.Good),
                OutputArguments=[ua.Variant(0), ua.Variant(ua.LocalizedText("Accepted"))],
            )
        ]

    parent.session.call = AsyncMock(side_effect=rpc)
    result = await call_method_preserving_status(
        parent,
        method,
        target_server_authorized=True,
        before_dispatch=lambda: intent.append("durable intent"),
    )
    assert result.success
    parent.session.call.assert_awaited_once()
    method.read_browse_name.side_effect = TimeoutError()
    callback = MagicMock()
    result = await call_method_preserving_status(parent, method, before_dispatch=callback)
    assert result.rpc_dispatched is False
    callback.assert_not_called()


async def test_authorized_target_mutation_is_blocked_after_manifest_edit(monkeypatch, tmp_path):
    from helpers.cu_coverage_report import WorkflowEvidenceUnavailable
    from helpers.method_caller import call_method

    path = tmp_path / "reviewed.yaml"
    path.write_bytes(b"reviewed")
    monkeypatch.setenv("OPCUA_TARGET_SERVER_PROFILE", str(path))
    monkeypatch.setenv("OPCUA_TARGET_MANIFEST_SHA256", manifest_file_sha256(path))
    path.write_bytes(b"changed")
    parent = MagicMock()
    parent.call_method = AsyncMock()
    with pytest.raises(WorkflowEvidenceUnavailable) as result:
        await call_method(parent, "method", method_name="StartSelectedJoining", target_server_authorized=True)
    assert result.value.ijt_properties["ijt_outcome"] == "blocked"
    assert result.value.ijt_properties["ijt_reason_code"] == "manifest_changed"
    parent.call_method.assert_not_awaited()


class TestOpcUaStatusHelperIsBad:
    def test_bad_status_code_returns_true(self):
        assert OpcUaStatusHelper.is_bad(0x80340000) is True

    def test_bad_not_found_returns_true(self):
        assert OpcUaStatusHelper.is_bad(OpcUaStatusHelper.BAD_NOT_FOUND) is True

    def test_bad_invalid_argument_returns_true(self):
        assert OpcUaStatusHelper.is_bad(OpcUaStatusHelper.BAD_INVALID_ARGUMENT) is True

    def test_good_status_returns_false(self):
        assert OpcUaStatusHelper.is_bad(0x00000000) is False

    def test_uncertain_status_returns_false(self):
        assert OpcUaStatusHelper.is_bad(0x40000000) is False

    def test_all_known_bad_codes(self):
        bad_codes = [
            OpcUaStatusHelper.BAD_NOT_FOUND,
            OpcUaStatusHelper.BAD_INVALID_ARGUMENT,
            OpcUaStatusHelper.BAD_NODE_ID_UNKNOWN,
            OpcUaStatusHelper.BAD_NOT_SUPPORTED,
            OpcUaStatusHelper.BAD_ARGUMENTS_MISSING,
        ]
        for code in bad_codes:
            assert OpcUaStatusHelper.is_bad(code) is True, f"Expected bad: 0x{code:08X}"


class TestOpcUaStatusHelperIsGood:
    def test_zero_is_good(self):
        assert OpcUaStatusHelper.is_good(0x00000000) is True

    def test_bad_code_is_not_good(self):
        assert OpcUaStatusHelper.is_good(0x80340000) is False

    def test_uncertain_is_not_good(self):
        assert OpcUaStatusHelper.is_good(0x40000000) is False

    def test_good_with_info_bits(self):
        assert OpcUaStatusHelper.is_good(0x00FF0000) is True


class TestOpcUaStatusHelperIsUncertain:
    def test_uncertain_base_is_uncertain(self):
        assert OpcUaStatusHelper.is_uncertain(0x40000000) is True

    def test_uncertain_with_bits(self):
        assert OpcUaStatusHelper.is_uncertain(0x40FF0000) is True

    def test_bad_is_not_uncertain(self):
        assert OpcUaStatusHelper.is_uncertain(0x80340000) is False

    def test_good_is_not_uncertain(self):
        assert OpcUaStatusHelper.is_uncertain(0x00000000) is False


class TestOpcUaStatusHelperClassify:
    def test_classify_good(self):
        assert OpcUaStatusHelper.classify(0x00000000) == "Good"

    def test_classify_bad(self):
        assert OpcUaStatusHelper.classify(0x80340000) == "Bad"

    def test_classify_uncertain(self):
        assert OpcUaStatusHelper.classify(0x40000000) == "Uncertain"

    def test_classify_good_with_code(self):
        assert OpcUaStatusHelper.classify(0x00FF0000) == "Good"

    def test_classify_bad_all_known(self):
        for code in [
            OpcUaStatusHelper.BAD_NOT_FOUND,
            OpcUaStatusHelper.BAD_INVALID_ARGUMENT,
            OpcUaStatusHelper.BAD_NODE_ID_UNKNOWN,
            OpcUaStatusHelper.BAD_NOT_SUPPORTED,
            OpcUaStatusHelper.BAD_ARGUMENTS_MISSING,
        ]:
            assert OpcUaStatusHelper.classify(code) == "Bad"


class TestOpcUaStatusHelperFormatStatus:
    def test_format_non_ua_error_falls_back_to_str(self):
        exc = ValueError("something went wrong")
        result = OpcUaStatusHelper.format_status(exc)
        assert result == "something went wrong"

    def test_format_runtime_error(self):
        exc = RuntimeError("timeout")
        result = OpcUaStatusHelper.format_status(exc)
        assert "timeout" in result

    def test_format_ua_error_without_code_falls_back_to_str(self):
        exc = ua.UaError("ua error without code")
        result = OpcUaStatusHelper.format_status(exc)
        assert isinstance(result, str)

    def test_format_ua_status_code_error_formats_hex(self):
        # ua.UaStatusCodeError naturally has a .code attribute
        exc = ua.UaStatusCodeError(0x80340000)
        result = OpcUaStatusHelper.format_status(exc)
        assert isinstance(result, str)
        assert len(result) > 0


class TestMethodCallResult:
    def test_success_result(self):
        r = MethodCallResult(success=True, output=[1, 2, 3], method_name="TestMethod")
        assert r.success is True
        assert r.output == [1, 2, 3]
        assert r.error is None

    def test_failure_result(self):
        err = Exception("OPC UA error")
        r = MethodCallResult(success=False, error=err, method_name="TestMethod")
        assert r.success is False
        assert r.error is err
        assert r.output is None

    def test_default_method_name_is_empty(self):
        r = MethodCallResult(success=True)
        assert r.method_name == ""

    def test_output_list_with_none(self):
        r = MethodCallResult(success=True, output=None)
        assert r.output_list == []

    def test_output_list_with_list(self):
        r = MethodCallResult(success=True, output=[10, 20, 30])
        assert r.output_list == [10, 20, 30]

    def test_output_list_with_tuple(self):
        r = MethodCallResult(success=True, output=(1, 2))
        assert r.output_list == [1, 2]

    def test_output_list_with_scalar(self):
        r = MethodCallResult(success=True, output=42)
        assert r.output_list == [42]

    def test_output_list_with_string_scalar(self):
        r = MethodCallResult(success=True, output="hello")
        assert r.output_list == ["hello"]

    def test_status_code_field(self):
        r = MethodCallResult(success=False, status_code=0x80340000)
        assert r.status_code == 0x80340000


class TestCallMethodExpectBadStatus:
    @pytest.mark.asyncio
    async def test_call_method_expect_bad_status_with_authorization_reset(self):
        from helpers.method_caller import call_method_expect_bad_status

        mock_parent = MagicMock()
        mock_parent.call_method = AsyncMock(side_effect=ua.UaError("BadInvalidArgument"))

        res = await call_method_expect_bad_status(
            mock_parent,
            "ns=1;i=1001",
            target_server_authorized=True,
            method_name="TestBadMethod",
        )
        assert res.success is True
        assert res.method_name == "TestBadMethod"
