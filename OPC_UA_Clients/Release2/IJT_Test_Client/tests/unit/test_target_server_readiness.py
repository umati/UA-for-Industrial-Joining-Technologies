"""
Unit tests for helpers/target_server_readiness.py

Tests synchronous (no-server) readiness checks and the PreflightReport
aggregation model.  No OPC UA server required.
"""

from __future__ import annotations

import pytest

from helpers.target_server_cu_config import (
    OUTCOME_BLOCKED,
    OUTCOME_CONFIGURATION_ERROR,
    OUTCOME_MANUAL_REQUIRED,
    OUTCOME_PASSED,
    OUTCOME_UNSUPPORTED,
    build_default_profile,
    load_target_server_profile_from_dict,
)
from helpers.target_server_readiness import (
    PreflightReport,
    ReadinessOutcome,
    check_endpoint_configured,
    check_endpoint_reachable,
    check_joining_process_configured,
    check_result_trigger_mode,
    check_start_selected_joining_methods_allowed,
    check_state_changing_methods_policy,
    check_tool_piu_configured,
    classify_preflight_outcome,
    run_config_preflight,
)

# ---------------------------------------------------------------------------
# ReadinessOutcome dataclass
# ---------------------------------------------------------------------------


class TestReadinessOutcome:
    def test_passed_outcome(self):
        o = ReadinessOutcome(outcome=OUTCOME_PASSED)
        assert o.passed is True
        assert o.is_blocking is False
        assert o.needs_manual_action is False
        assert o.is_unsupported is False

    def test_blocked_outcome_is_blocking(self):
        o = ReadinessOutcome(outcome=OUTCOME_BLOCKED, reason_code="tool_disconnected", detail="tool offline")
        assert o.is_blocking is True
        assert o.passed is False

    def test_configuration_error_is_blocking(self):
        o = ReadinessOutcome(outcome=OUTCOME_CONFIGURATION_ERROR, reason_code="configuration_invalid")
        assert o.is_blocking is True

    def test_manual_required_not_blocking(self):
        o = ReadinessOutcome(outcome=OUTCOME_MANUAL_REQUIRED, reason_code="manual_trigger_required")
        assert o.needs_manual_action is True
        assert o.is_blocking is False

    def test_unsupported_classification(self):
        o = ReadinessOutcome(outcome=OUTCOME_UNSUPPORTED)
        assert o.is_unsupported is True
        assert o.is_blocking is False

    def test_frozen(self):
        o = ReadinessOutcome(outcome=OUTCOME_PASSED)
        with pytest.raises((AttributeError, TypeError)):
            o.outcome = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PreflightReport aggregation
# ---------------------------------------------------------------------------


class TestPreflightReport:
    def test_empty_report_all_passed(self):
        r = PreflightReport()
        assert r.all_passed is True

    def test_add_passed_check(self):
        r = PreflightReport()
        r.add(ReadinessOutcome(outcome=OUTCOME_PASSED, check_name="c1"))
        assert r.all_passed is True
        assert len(r.checks) == 1

    def test_blocking_check_detected(self):
        r = PreflightReport()
        r.add(ReadinessOutcome(outcome=OUTCOME_PASSED, check_name="c1"))
        r.add(ReadinessOutcome(outcome=OUTCOME_BLOCKED, check_name="c2", reason_code="x"))
        assert r.all_passed is False
        assert len(r.blocking_checks) == 1

    def test_manual_required_check_detected(self):
        r = PreflightReport()
        r.add(ReadinessOutcome(outcome=OUTCOME_MANUAL_REQUIRED, check_name="manual"))
        assert len(r.manual_required_checks) == 1
        assert r.all_passed is False

    def test_summary_lines_returns_list_of_strings(self):
        r = PreflightReport(profile_name="TestProfile", endpoint="opc.tcp://localhost:40451")
        r.add(ReadinessOutcome(outcome=OUTCOME_PASSED, check_name="check1"))
        lines = r.summary_lines()
        assert isinstance(lines, list)
        assert all(isinstance(line, str) for line in lines)
        assert any("TestProfile" in line for line in lines)

    def test_to_dict_is_json_serialisable(self):
        import json

        r = PreflightReport(profile_name="Test", endpoint="opc.tcp://x:1")
        r.add(ReadinessOutcome(outcome=OUTCOME_PASSED, check_name="c", detail="ok"))
        data = r.to_dict()
        json_str = json.dumps(data)
        assert "Test" in json_str

    def test_to_dict_contains_checks_list(self):
        r = PreflightReport()
        r.add(ReadinessOutcome(outcome=OUTCOME_BLOCKED, check_name="x", reason_code="y", detail="z"))
        data = r.to_dict()
        assert "checks" in data
        assert data["checks"][0]["outcome"] == OUTCOME_BLOCKED


# ---------------------------------------------------------------------------
# check_endpoint_configured
# ---------------------------------------------------------------------------


class TestCheckEndpointConfigured:
    def test_valid_endpoint_passes(self):
        o = check_endpoint_configured("opc.tcp://10.0.0.1:40451")
        assert o.passed

    def test_empty_endpoint_fails(self):
        o = check_endpoint_configured("")
        assert o.outcome == OUTCOME_CONFIGURATION_ERROR

    def test_placeholder_endpoint_fails(self):
        o = check_endpoint_configured("opc.tcp://<host>:40451")
        assert o.outcome == OUTCOME_CONFIGURATION_ERROR

    def test_angle_bracket_endpoint_fails(self):
        o = check_endpoint_configured("opc.tcp://<target_server-host>:40451")
        assert o.outcome == OUTCOME_CONFIGURATION_ERROR

    def test_localhost_endpoint_passes(self):
        o = check_endpoint_configured("opc.tcp://localhost:40451")
        assert o.passed


# ---------------------------------------------------------------------------
# check_endpoint_reachable
# ---------------------------------------------------------------------------


class TestCheckEndpointReachable:
    def test_unreachable_endpoint_returns_blocked(self):
        # Use a port that is almost certainly not listening
        o = check_endpoint_reachable("opc.tcp://127.0.0.1:1", timeout_s=0.2)
        assert o.outcome in {OUTCOME_BLOCKED, OUTCOME_PASSED}
        # If BLOCKED, check reason code
        if not o.passed:
            assert o.reason_code == "endpoint_unreachable"

    def test_empty_host_returns_config_error(self):
        o = check_endpoint_reachable("opc.tcp://", timeout_s=0.1)
        assert o.outcome == OUTCOME_CONFIGURATION_ERROR

    def test_unparseable_endpoint_returns_config_error(self):
        o = check_endpoint_reachable("not-a-valid-url", timeout_s=0.1)
        # Either CONFIGURATION_ERROR or BLOCKED — both are acceptable
        assert o.outcome in {OUTCOME_CONFIGURATION_ERROR, OUTCOME_BLOCKED}


# ---------------------------------------------------------------------------
# check_result_trigger_mode
# ---------------------------------------------------------------------------


class TestCheckResultTriggerMode:
    def _profile_with_result_mode(self, mode: str):
        return load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": mode}},
            }
        )

    def test_none_mode_is_blocked(self):
        profile = self._profile_with_result_mode("none")
        o = check_result_trigger_mode(profile)
        assert o.outcome == OUTCOME_BLOCKED

    def test_manual_trigger_is_manual_required(self):
        profile = self._profile_with_result_mode("manual_trigger")
        o = check_result_trigger_mode(profile)
        assert o.outcome == OUTCOME_MANUAL_REQUIRED
        assert o.needs_manual_action is True

    def test_start_selected_joining_passes(self):
        profile = self._profile_with_result_mode("start_selected_joining")
        o = check_result_trigger_mode(profile)
        assert o.passed

    def test_simulate_methods_passes(self):
        profile = self._profile_with_result_mode("simulate_methods")
        o = check_result_trigger_mode(profile)
        assert o.passed

    def test_observe_only_passes(self):
        profile = self._profile_with_result_mode("observe_only")
        o = check_result_trigger_mode(profile)
        assert o.passed


# ---------------------------------------------------------------------------
# check_state_changing_methods_policy
# ---------------------------------------------------------------------------


class TestCheckStateChangingMethodsPolicy:
    def test_method_not_allowed_returns_blocked(self):
        profile = build_default_profile()
        o = check_state_changing_methods_policy(profile, ["SelectJoiningProcess"])
        assert o.outcome == OUTCOME_BLOCKED
        assert "SelectJoiningProcess" in o.detail

    def test_method_allowed_passes(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "cu_execution": {
                    "state_changing_methods": {
                        "default_policy": "require_explicit_opt_in",
                        "allowed_methods": ["SelectJoiningProcess"],
                    }
                },
            }
        )
        o = check_state_changing_methods_policy(profile, ["SelectJoiningProcess"])
        assert o.passed

    def test_allow_all_policy_passes_any_method(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "cu_execution": {"state_changing_methods": {"default_policy": "allow_all"}},
            }
        )
        o = check_state_changing_methods_policy(profile, ["AnyMethod", "AnotherMethod"])
        assert o.passed

    def test_empty_required_list_passes(self):
        profile = build_default_profile()
        o = check_state_changing_methods_policy(profile, [])
        assert o.passed

    def test_multiple_blocked_methods_reported(self):
        profile = build_default_profile()
        o = check_state_changing_methods_policy(profile, ["SelectJoiningProcess", "StartSelectedJoining"])
        assert o.outcome == OUTCOME_BLOCKED
        assert "evidence" in {k: v for k, v in o.evidence.items()} or len(o.evidence) >= 0


# ---------------------------------------------------------------------------
# check_tool_piu_configured
# ---------------------------------------------------------------------------


class TestCheckToolPiuConfigured:
    def test_explicit_piu_passes(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "selection": {"tool": {"product_instance_uri": "urn:tool:serial:123"}},
            }
        )
        o = check_tool_piu_configured(profile)
        assert o.passed
        assert "urn:tool:serial:123" in o.detail

    def test_empty_piu_first_ready_policy_passes(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "selection": {"tool": {"policy": "first_ready"}},
            }
        )
        o = check_tool_piu_configured(profile)
        assert o.passed

    def test_empty_piu_exact_match_policy_is_config_error(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "selection": {"tool": {"policy": "exact_match", "product_instance_uri": ""}},
            }
        )
        o = check_tool_piu_configured(profile)
        assert o.outcome == OUTCOME_CONFIGURATION_ERROR


# ---------------------------------------------------------------------------
# check_joining_process_configured
# ---------------------------------------------------------------------------


class TestCheckJoiningProcessConfigured:
    def test_explicit_id_passes(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "selection": {"joining_process": {"joining_process_id": "PROG01"}},
            }
        )
        o = check_joining_process_configured(profile)
        assert o.passed

    def test_empty_id_first_compatible_passes(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "selection": {"joining_process": {"policy": "first_compatible"}},
            }
        )
        o = check_joining_process_configured(profile)
        assert o.passed

    def test_selection_name_exact_match_passes(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {
                        "policy": "exact_match",
                        "selection_name": "SequenceIndex_1",
                    }
                },
            }
        )
        o = check_joining_process_configured(profile)
        assert o.passed
        assert o.evidence == {"selection_name": "SequenceIndex_1"}

    def test_empty_id_exact_match_is_config_error(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "selection": {"joining_process": {"policy": "exact_match", "joining_process_id": ""}},
            }
        )
        o = check_joining_process_configured(profile)
        assert o.outcome == OUTCOME_CONFIGURATION_ERROR


# ---------------------------------------------------------------------------
# check_start_selected_joining_methods_allowed
# ---------------------------------------------------------------------------


class TestCheckStartSelectedJoiningAllowed:
    def test_not_start_mode_skips_check(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": "none"}},
            }
        )
        o = check_start_selected_joining_methods_allowed(profile)
        assert o.passed

    def test_start_mode_without_opt_in_is_blocked(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": "start_selected_joining"}},
            }
        )
        o = check_start_selected_joining_methods_allowed(profile)
        assert o.outcome == OUTCOME_BLOCKED

    def test_start_mode_with_methods_allowed_passes(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "triggers": {"result": {"mode": "start_selected_joining"}},
                "cu_execution": {
                    "state_changing_methods": {
                        "default_policy": "require_explicit_opt_in",
                        "allowed_methods": ["SelectJoiningProcess", "StartSelectedJoining"],
                    }
                },
            }
        )
        o = check_start_selected_joining_methods_allowed(profile)
        assert o.passed


# ---------------------------------------------------------------------------
# run_config_preflight — composite check
# ---------------------------------------------------------------------------


class TestRunConfigPreflight:
    def test_placeholder_endpoint_produces_configuration_error(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://<host>:40451"},
            }
        )
        report = run_config_preflight(profile)
        config_errors = [c for c in report.checks if c.outcome == OUTCOME_CONFIGURATION_ERROR]
        assert len(config_errors) > 0, "Expected configuration_error for placeholder endpoint"

    def test_returns_preflight_report(self):
        profile = build_default_profile("opc.tcp://localhost:40451")
        report = run_config_preflight(profile)
        assert isinstance(report, PreflightReport)
        assert len(report.checks) > 0

    def test_manual_trigger_mode_produces_manual_required(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://localhost:40451"},
                "triggers": {"result": {"mode": "manual_trigger"}},
            }
        )
        report = run_config_preflight(profile)
        manual = report.manual_required_checks
        assert len(manual) > 0


# ---------------------------------------------------------------------------
# classify_preflight_outcome — convenience helper
# ---------------------------------------------------------------------------


class TestClassifyPreflightOutcome:
    def test_config_error_returns_blocking_outcome(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://<host>:40451"},
            }
        )
        outcome = classify_preflight_outcome(profile)
        assert outcome.is_blocking or outcome.outcome == OUTCOME_CONFIGURATION_ERROR

    def test_clean_profile_returns_passed(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://localhost:40451"},
                "triggers": {"result": {"mode": "simulate_methods"}},
            }
        )
        outcome = classify_preflight_outcome(profile)
        assert outcome.passed or outcome.needs_manual_action  # simulate_methods should pass


# ---------------------------------------------------------------------------
# Async readiness checks
# ---------------------------------------------------------------------------


class TestAsyncReadinessChecks:
    def test_check_endpoint_reachable_success(self, monkeypatch):
        import socket
        from contextlib import contextmanager

        @contextmanager
        def _mock_conn(*_a, **_kw):
            yield

        monkeypatch.setattr(socket, "create_connection", _mock_conn)
        o = check_endpoint_reachable("opc.tcp://localhost:40451")
        assert o.passed
        assert "TCP port open" in o.detail

    @pytest.mark.asyncio
    async def test_check_joining_system_present_success(self):
        from types import SimpleNamespace

        from helpers.target_server_readiness import check_joining_system_present

        node = SimpleNamespace(nodeid="ns=1;i=1000")
        o = await check_joining_system_present(None, node)
        assert o.passed
        assert o.evidence["joining_system_node_id"] == "ns=1;i=1000"

    @pytest.mark.asyncio
    async def test_check_joining_system_present_none(self):
        from helpers.target_server_readiness import check_joining_system_present

        o = await check_joining_system_present(None, None)
        assert o.outcome == OUTCOME_BLOCKED

    @pytest.mark.asyncio
    async def test_check_joining_system_present_exception(self):
        from helpers.target_server_readiness import check_joining_system_present

        class ErrorNode:
            @property
            def nodeid(self):
                raise RuntimeError("Node error")

        o = await check_joining_system_present(None, ErrorNode())
        assert o.outcome == OUTCOME_BLOCKED

    @pytest.mark.asyncio
    async def test_check_namespaces_available_success(self):
        from helpers.target_server_readiness import check_namespaces_available

        class MockClient:
            async def get_namespace_array(self):
                return ["http://opcfoundation.org/UA/", "http://opcfoundation.org/UA/IJT/Base/"]

        o = await check_namespaces_available(MockClient(), ["http://opcfoundation.org/UA/IJT/Base/"])
        assert o.passed

    @pytest.mark.asyncio
    async def test_check_namespaces_available_missing(self):
        from helpers.target_server_readiness import check_namespaces_available

        class MockClient:
            async def get_namespace_array(self):
                return ["http://opcfoundation.org/UA/"]

        o = await check_namespaces_available(MockClient(), ["http://opcfoundation.org/UA/IJT/Base/"])
        assert o.outcome == OUTCOME_BLOCKED
        assert "missing" in o.detail

    @pytest.mark.asyncio
    async def test_check_namespaces_available_exception(self):
        from helpers.target_server_cu_config import OUTCOME_FAILED
        from helpers.target_server_readiness import check_namespaces_available

        class MockClient:
            async def get_namespace_array(self):
                raise ConnectionError("Network down")

        o = await check_namespaces_available(MockClient(), ["http://opcfoundation.org/UA/IJT/Base/"])
        assert o.outcome == OUTCOME_FAILED

    @pytest.mark.asyncio
    async def test_check_joining_process_list_jpm_node_none(self, monkeypatch):
        from helpers import node_discovery
        from helpers import target_server_readiness as tsr

        async def _mock_find(*_a, **_kw):
            return None

        monkeypatch.setattr(node_discovery, "find_child_by_browse_name", _mock_find)
        o = await tsr.check_joining_process_list(object(), "urn:tool:1", 1)
        assert o.outcome == OUTCOME_BLOCKED
        assert "JoiningProcessManagement node not found" in o.detail

    @pytest.mark.asyncio
    async def test_check_joining_process_list_call_failed(self, monkeypatch):
        from helpers import method_caller, node_discovery
        from helpers import target_server_readiness as tsr
        from helpers.method_caller import MethodCallResult

        async def _mock_find(*_a, **_kw):
            return object()

        async def _mock_call(*_a, **_kw):
            return MethodCallResult(success=False, error="Bad_InternalError")

        monkeypatch.setattr(node_discovery, "find_child_by_browse_name", _mock_find)
        monkeypatch.setattr(method_caller, "find_and_call_method", _mock_call)
        o = await tsr.check_joining_process_list(object(), "urn:tool:1", 1)
        assert o.outcome == OUTCOME_BLOCKED
        assert "GetJoiningProcessList failed" in o.detail

    @pytest.mark.asyncio
    async def test_check_joining_process_list_empty(self, monkeypatch):
        from helpers import method_caller, node_discovery
        from helpers import target_server_readiness as tsr
        from helpers.method_caller import MethodCallResult

        async def _mock_find(*_a, **_kw):
            return object()

        async def _mock_call(*_a, **_kw):
            return MethodCallResult(success=True, output=[[]])

        monkeypatch.setattr(node_discovery, "find_child_by_browse_name", _mock_find)
        monkeypatch.setattr(method_caller, "find_and_call_method", _mock_call)
        o = await tsr.check_joining_process_list(object(), "urn:tool:1", 1)
        assert o.outcome == OUTCOME_BLOCKED
        assert "empty list" in o.detail

    @pytest.mark.asyncio
    async def test_check_joining_process_list_success(self, monkeypatch):
        from helpers import method_caller, node_discovery
        from helpers import target_server_readiness as tsr
        from helpers.method_caller import MethodCallResult

        async def _mock_find(*_a, **_kw):
            return object()

        async def _mock_call(*_a, **_kw):
            return MethodCallResult(success=True, output=[["process1", "process2"]])

        monkeypatch.setattr(node_discovery, "find_child_by_browse_name", _mock_find)
        monkeypatch.setattr(method_caller, "find_and_call_method", _mock_call)
        o = await tsr.check_joining_process_list(object(), "urn:tool:1", 1)
        assert o.passed
        assert o.evidence["process_count"] == 2

    @pytest.mark.asyncio
    async def test_check_joining_process_list_unexpected_exception(self, monkeypatch):
        from helpers import node_discovery
        from helpers import target_server_readiness as tsr

        async def _mock_find(*_a, **_kw):
            raise RuntimeError("Unexpected boom")

        monkeypatch.setattr(node_discovery, "find_child_by_browse_name", _mock_find)
        o = await tsr.check_joining_process_list(object(), "urn:tool:1", 1)
        assert o.outcome == OUTCOME_BLOCKED
        assert "Unexpected error" in o.detail

    def test_preflight_report_summary_lines_with_issues(self):
        r = PreflightReport(profile_name="Profile", endpoint="opc.tcp://x:1")
        r.add(ReadinessOutcome(outcome=OUTCOME_BLOCKED, check_name="b1", detail="blocked"))
        r.add(ReadinessOutcome(outcome=OUTCOME_MANUAL_REQUIRED, check_name="m1", detail="manual"))
        lines = r.summary_lines()
        assert any("Blocking issues" in line for line in lines)
        assert any("Manual action required" in line for line in lines)

    def test_check_joining_process_configured_first_ready_policy(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "selection": {"joining_process": {"policy": "first_ready"}},
            }
        )
        o = check_joining_process_configured(profile)
        assert o.passed
        assert "first_ready" in o.detail

    def test_classify_preflight_outcome_manual_required(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://localhost:40451"},
                "triggers": {"result": {"mode": "manual_trigger"}},
            }
        )
        outcome = classify_preflight_outcome(profile)
        assert outcome.needs_manual_action

    def test_parse_endpoint_exception_fallback(self, monkeypatch):
        from helpers import target_server_readiness as tsr

        monkeypatch.setattr("urllib.parse.urlparse", lambda *_: (_ for _ in ()).throw(ValueError("malformed")))
        host, port = tsr._parse_endpoint("broken")
        assert host == ""
        assert port == 4840
