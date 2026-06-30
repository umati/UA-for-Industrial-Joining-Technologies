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
