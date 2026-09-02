"""
Unit tests for helpers/target_server_cu_config.py

Tests the internal typed execution config: strict validation, defaults, and
error conditions. The tester-facing file schema lives in helpers/sut_manifest.py
and is covered by tests/unit/test_sut_manifest.py.
No OPC UA server required.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from helpers.target_server_cu_config import (
    OUTCOME_BLOCKED,
    OUTCOME_CONFIGURATION_ERROR,
    OUTCOME_FAILED,
    OUTCOME_MANUAL_REQUIRED,
    OUTCOME_PASSED,
    OUTCOME_UNSUPPORTED,
    StateChangingMethodsConfig,
    TargetServerConfigError,
    TargetServerCuProfile,
    build_default_profile,
    build_execution_profile,
)


def test_expected_results_accepts_intermediate_classifications():
    profile = build_execution_profile(
        {
            "schema_version": 1,
            "workflow_execution": {
                "expected_results": {
                    "classification": "job",
                    "intermediate_classifications": ["batch"],
                }
            },
        }
    )

    assert profile.workflow_execution.expected_results.intermediate_classifications == ("batch",)


def test_expected_results_rejects_invalid_intermediate_classification():
    with pytest.raises(TargetServerConfigError, match="intermediate_classifications"):
        build_execution_profile(
            {
                "schema_version": 1,
                "workflow_execution": {
                    "expected_results": {
                        "classification": "job",
                        "intermediate_classifications": ["vendor-sequence"],
                    }
                },
            }
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


MINIMAL_VALID = """
schema_version: 1
profile_name: "Test Profile"
description: "Unit test profile"
capabilities_file: ""
"""

FULL_VALID = """
schema_version: 1
profile_name: "Full Test Profile"
description: "Complete valid profile for unit tests"
capabilities_file: "my_controller.sut.yaml"

target:
  endpoint: "opc.tcp://localhost:40451"
  expected_server:
    application_name: "TestApp"
    application_version: "1.0.0"
    warn_only_on_version_drift: true

cu_execution:
  default_mode: automated
  scoring_mode: diagnostic
  precondition_failure_policy: blocked
  allow_manual_steps: false
  default_timeout_seconds: 60
  state_changing_methods:
    default_policy: require_explicit_opt_in
    allowed_methods:
      - SelectJoiningProcess
      - StartSelectedJoining
  method_status_policies: {}
  extension_fields: {}

selection:
  tool:
    policy: first_ready
    product_instance_uri: ""
    capability_tags: []
  joining_process:
    policy: first_compatible
    joining_process_id: ""
    joining_process_origin_id: ""
    selection_name: ""
    capability_tags: []

triggers:
  result:
    mode: start_selected_joining
    timeout_seconds: 120
    deselect_after_joining: false
  event:
    mode: observe_only
    timeout_seconds: 60
  condition:
    mode: observe_only
    timeout_seconds: 60

workflow_execution:
  max_start_invocations: 6
  consecutive_start_delay_seconds: 0.25
  expected_results:
    classification: single
    final_result_required: true
    timeout_seconds: 120
  cleanup:
    policy: best_effort_with_evidence
    deselect_process: true
    reset_identifiers: false

reporting:
  output_dir: "test-results/target-server-cu"
  sanitize_shared_artifacts: true
  keep_local_exact_debug_artifacts: false
"""


# ---------------------------------------------------------------------------
# build_execution_profile — minimal valid
# ---------------------------------------------------------------------------


class TestMinimalValidProfile:
    def test_loads_minimal_profile(self):
        raw = {"schema_version": 1}
        profile = build_execution_profile(raw)
        assert isinstance(profile, TargetServerCuProfile)
        assert profile.schema_version == 1

    def test_default_mode_is_automated(self):
        profile = build_execution_profile({"schema_version": 1})
        assert profile.cu_execution.default_mode == "automated"

    def test_default_scoring_mode_is_diagnostic(self):
        profile = build_execution_profile({"schema_version": 1})
        assert profile.cu_execution.scoring_mode == "diagnostic"

    def test_default_precondition_policy_is_blocked(self):
        profile = build_execution_profile({"schema_version": 1})
        assert profile.cu_execution.precondition_failure_policy == "blocked"

    def test_default_result_trigger_mode_is_none(self):
        profile = build_execution_profile({"schema_version": 1})
        assert profile.triggers.result.mode == "none"

    def test_default_event_trigger_mode_is_observe_only(self):
        profile = build_execution_profile({"schema_version": 1})
        assert profile.triggers.event.mode == "observe_only"

    def test_default_state_changing_methods_blocks_all(self):
        profile = build_execution_profile({"schema_version": 1})
        sc = profile.cu_execution.state_changing_methods
        assert sc.allow_state_changing_method("SelectJoiningProcess") is False

    def test_frozen_profile(self):
        profile = build_execution_profile({"schema_version": 1})
        with pytest.raises((AttributeError, TypeError)):
            profile.schema_version = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# build_execution_profile — full valid
# ---------------------------------------------------------------------------


class TestFullValidProfile:
    def test_loads_full_profile(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = build_execution_profile(raw)
        assert profile.schema_version == 1
        assert profile.profile_name == "Full Test Profile"

    def test_endpoint_loaded(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = build_execution_profile(raw)
        assert profile.target.endpoint == "opc.tcp://localhost:40451"

    def test_allowed_methods_loaded(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = build_execution_profile(raw)
        sc = profile.cu_execution.state_changing_methods
        assert sc.allow_state_changing_method("SelectJoiningProcess") is True
        assert sc.allow_state_changing_method("StartSelectedJoining") is True
        assert sc.allow_state_changing_method("DeleteJoiningProcess") is False

    def test_result_trigger_mode(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = build_execution_profile(raw)
        assert profile.triggers.result.mode == "start_selected_joining"

    def test_result_timeout(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = build_execution_profile(raw)
        assert profile.triggers.result.timeout_seconds == 120.0

    def test_workflow_execution_policy(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = build_execution_profile(raw)
        assert profile.workflow_execution.max_start_invocations == 6
        assert profile.workflow_execution.consecutive_start_delay_seconds == 0.25
        assert profile.workflow_execution.expected_results.expected_terminal_result_state == 1

    def test_reporting_output_dir(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = build_execution_profile(raw)
        assert "target-server-cu" in profile.reporting.output_dir

    def test_custom_expected_terminal_result_state(self):
        raw = yaml.safe_load(FULL_VALID)
        raw["workflow_execution"]["expected_results"]["expected_terminal_result_state"] = 3
        profile = build_execution_profile(raw)
        assert profile.workflow_execution.expected_results.expected_terminal_result_state == 3

    def test_invalid_expected_terminal_result_state_is_rejected(self):
        raw = yaml.safe_load(FULL_VALID)
        for invalid in (0, 2, 5, -1):
            raw["workflow_execution"]["expected_results"]["expected_terminal_result_state"] = invalid
            with pytest.raises(TargetServerConfigError, match="expected_terminal_result_state must be one of"):
                build_execution_profile(raw)


# ---------------------------------------------------------------------------
# Schema version validation
# ---------------------------------------------------------------------------


class TestSchemaVersionValidation:
    def test_missing_schema_version_raises(self):
        with pytest.raises(TargetServerConfigError, match="schema_version"):
            build_execution_profile({"profile_name": "x"})

    def test_unsupported_schema_version_raises(self):
        with pytest.raises(TargetServerConfigError, match="Unsupported schema_version"):
            build_execution_profile({"schema_version": 99})

    def test_schema_version_not_int_raises(self):
        with pytest.raises(TargetServerConfigError, match="integer"):
            build_execution_profile({"schema_version": "1"})

    def test_schema_version_bool_raises(self):
        with pytest.raises(TargetServerConfigError, match="integer"):
            build_execution_profile({"schema_version": True})

    def test_schema_version_1_accepted(self):
        profile = build_execution_profile({"schema_version": 1})
        assert profile.schema_version == 1


# ---------------------------------------------------------------------------
# Invalid enum values
# ---------------------------------------------------------------------------


class TestInvalidEnumValues:
    def test_invalid_execution_mode_raises(self):
        with pytest.raises(TargetServerConfigError, match="invalid value"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {"default_mode": "turbo"},
                }
            )

    def test_invalid_scoring_mode_raises(self):
        with pytest.raises(TargetServerConfigError, match="invalid value"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {"scoring_mode": "magic"},
                }
            )

    def test_invalid_result_trigger_mode_raises(self):
        with pytest.raises(TargetServerConfigError, match="invalid value"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "triggers": {"result": {"mode": "teleport"}},
                }
            )

    def test_invalid_precondition_policy_raises(self):
        with pytest.raises(TargetServerConfigError, match="invalid value"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {"precondition_failure_policy": "ignore"},
                }
            )

    def test_invalid_identifier_strategy_raises(self):
        with pytest.raises(TargetServerConfigError, match="invalid value"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "selection": {"joining_process": {"identifier_strategy": "spam"}},
                }
            )

    def test_invalid_tool_selection_policy_raises(self):
        with pytest.raises(TargetServerConfigError, match="invalid value"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "selection": {"tool": {"policy": "random"}},
                }
            )


# ---------------------------------------------------------------------------
# State-changing methods config
# ---------------------------------------------------------------------------


class TestStateChangingMethodsConfig:
    def test_require_opt_in_blocks_unlisted(self):
        sc = StateChangingMethodsConfig(
            default_policy="require_explicit_opt_in",
            allowed_methods=("SelectJoiningProcess",),
        )
        assert sc.allow_state_changing_method("SelectJoiningProcess") is True
        assert sc.allow_state_changing_method("DeleteJoiningProcess") is False

    def test_allow_all_allows_any(self):
        sc = StateChangingMethodsConfig(default_policy="allow_all")
        assert sc.allow_state_changing_method("AnyMethod") is True
        assert sc.allow_state_changing_method("DeleteJoiningProcess") is True

    def test_deny_all_blocks_any(self):
        sc = StateChangingMethodsConfig(default_policy="deny_all")
        assert sc.allow_state_changing_method("SelectJoiningProcess") is False

    def test_empty_allowed_list_with_opt_in_blocks_all(self):
        sc = StateChangingMethodsConfig(
            default_policy="require_explicit_opt_in",
            allowed_methods=(),
        )
        assert sc.allow_state_changing_method("AnyMethod") is False

    def test_invalid_policy_from_dict(self):
        with pytest.raises(TargetServerConfigError, match="invalid value"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {"state_changing_methods": {"default_policy": "sometimes"}},
                }
            )


# ---------------------------------------------------------------------------
# build_default_profile
# ---------------------------------------------------------------------------


class TestBuildDefaultProfile:
    def test_returns_valid_profile(self):
        profile = build_default_profile()
        assert isinstance(profile, TargetServerCuProfile)
        assert profile.schema_version == 1

    def test_no_state_changing_by_default(self):
        profile = build_default_profile()
        sc = profile.cu_execution.state_changing_methods
        assert sc.allow_state_changing_method("SelectJoiningProcess") is False

    def test_endpoint_set(self):
        profile = build_default_profile(endpoint="opc.tcp://test:40451")
        assert profile.target.endpoint == "opc.tcp://test:40451"

    def test_empty_endpoint_by_default(self):
        profile = build_default_profile()
        assert profile.target.endpoint == ""


# ---------------------------------------------------------------------------
# Outcome vocabulary constants are stable strings
# ---------------------------------------------------------------------------


class TestOutcomeVocabulary:
    def test_outcome_constants_are_strings(self):
        for outcome in [
            OUTCOME_PASSED,
            OUTCOME_FAILED,
            OUTCOME_BLOCKED,
            OUTCOME_CONFIGURATION_ERROR,
            OUTCOME_MANUAL_REQUIRED,
            OUTCOME_UNSUPPORTED,
        ]:
            assert isinstance(outcome, str)
            assert len(outcome) > 0

    def test_outcomes_are_unique(self):
        outcomes = [
            OUTCOME_PASSED,
            OUTCOME_FAILED,
            OUTCOME_BLOCKED,
            OUTCOME_CONFIGURATION_ERROR,
            OUTCOME_MANUAL_REQUIRED,
            OUTCOME_UNSUPPORTED,
        ]
        assert len(set(outcomes)) == len(outcomes), "Outcome constants must be unique"


# ---------------------------------------------------------------------------
# Parser helpers and strict validation


# ---------------------------------------------------------------------------
# Parser helpers and strict validation
# ---------------------------------------------------------------------------


class TestParserHelpersAndValidation:
    def test_output_dir_resolves_relative_paths_against_the_runner_base(self, tmp_path):
        profile = build_execution_profile(
            {"schema_version": 1, "reporting": {"output_dir": "test-results/target-server-cu"}}
        )
        runner_base = tmp_path / "IJT_Test_Client"
        assert (
            profile.output_dir_path(base_dir=runner_base) == (runner_base / "test-results/target-server-cu").resolve()
        )

    def test_relative_capabilities_file_resolves_against_the_manifest_directory(self, tmp_path):
        source = tmp_path / "manifests" / "my_controller.sut.yaml"
        profile = build_execution_profile(
            {"schema_version": 1, "capabilities_file": "other.sut.yaml"},
            source_path=str(source),
        )
        assert profile.capabilities_file_path() == (source.parent / "other.sut.yaml").resolve()

    def test_output_dir_absolute(self, tmp_path):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "reporting": {"output_dir": str(tmp_path / "abs_out")},
            }
        )
        assert profile.output_dir_path() == (tmp_path / "abs_out").resolve()

    def test_capabilities_file_paths(self, tmp_path):
        p1 = build_execution_profile({"schema_version": 1, "capabilities_file": ""})
        assert p1.capabilities_file_path() is None

        abs_caps = (tmp_path / "caps.yaml").resolve()
        p2 = build_execution_profile({"schema_version": 1, "capabilities_file": str(abs_caps)})
        assert p2.capabilities_file_path() == abs_caps

        p3 = build_execution_profile({"schema_version": 1, "capabilities_file": "rel.yaml"}, source_path="")
        assert p3.capabilities_file_path() == Path("rel.yaml")

    def testrequire_str_rejects_non_string(self):
        from helpers.target_server_cu_config import require_str

        with pytest.raises(TargetServerConfigError, match="must be a string"):
            require_str({"key": 123}, "key", "ctx")

    def testrequire_bool_rejects_non_bool(self):
        from helpers.target_server_cu_config import require_bool

        with pytest.raises(TargetServerConfigError, match="must be a boolean"):
            require_bool({"key": "true"}, "key", False, "ctx")

    def testrequire_number_validations(self):
        from helpers.target_server_cu_config import require_number

        with pytest.raises(TargetServerConfigError, match="must be a number"):
            require_number({"key": "abc"}, "key", 1.0, "ctx")
        with pytest.raises(TargetServerConfigError, match="must be >="):
            require_number({"key": -5}, "key", 1.0, "ctx", min_val=0.0)

    def testrequire_int_validations(self):
        from helpers.target_server_cu_config import require_int

        with pytest.raises(TargetServerConfigError, match="must be an integer"):
            require_int({"key": "123"}, "key", 1, "ctx")
        with pytest.raises(TargetServerConfigError, match="must be >="):
            require_int({"key": -1}, "key", 1, "ctx", min_val=0)

    def testrequire_enum_rejects_non_str(self):
        from helpers.target_server_cu_config import require_enum

        with pytest.raises(TargetServerConfigError, match="must be a string"):
            require_enum({"key": 123}, "key", "val", frozenset({"val"}), "ctx")

    def testrequire_str_list_validations(self):
        from helpers.target_server_cu_config import require_str_list

        with pytest.raises(TargetServerConfigError, match="must be a list"):
            require_str_list({"key": "not-a-list"}, "key", "ctx")
        with pytest.raises(TargetServerConfigError, match="must be a string"):
            require_str_list({"key": [123]}, "key", "ctx")

    def test_non_mapping_sections_rejected(self):
        sections: list[tuple[str, dict[str, Any]]] = [
            ("target", {"target": "invalid"}),
            ("expected_server", {"target": {"expected_server": "invalid"}}),
            ("cu_execution", {"cu_execution": "invalid"}),
            ("state_changing_methods", {"cu_execution": {"state_changing_methods": "invalid"}}),
            ("method_status_policies", {"cu_execution": {"method_status_policies": "invalid"}}),
            ("extension_fields", {"cu_execution": {"extension_fields": "invalid"}}),
            ("selection", {"selection": "invalid"}),
            ("tool", {"selection": {"tool": "invalid"}}),
            ("joining_process", {"selection": {"joining_process": "invalid"}}),
            ("triggers", {"triggers": "invalid"}),
            ("result", {"triggers": {"result": "invalid"}}),
            ("event", {"triggers": {"event": "invalid"}}),
            ("condition", {"triggers": {"condition": "invalid"}}),
            ("workflow_execution", {"workflow_execution": "invalid"}),
            ("expected_results", {"workflow_execution": {"expected_results": "invalid"}}),
            ("cleanup", {"workflow_execution": {"cleanup": "invalid"}}),
            ("reporting", {"reporting": "invalid"}),
        ]
        for name, payload in sections:
            with pytest.raises(TargetServerConfigError, match="must be a mapping"):
                build_execution_profile({"schema_version": 1, **payload})

    def test_method_status_policies_non_string_keys_or_values(self):
        with pytest.raises(TargetServerConfigError, match="method_status_policies"):
            build_execution_profile({"schema_version": 1, "cu_execution": {"method_status_policies": {123: "val"}}})

    def test_load_from_dict_non_dict_rejected(self):
        with pytest.raises(TargetServerConfigError, match="must be a mapping"):
            build_execution_profile("not-a-dict")  # type: ignore[arg-type]

    def test_cu_execution_timeouts_validation(self):
        with pytest.raises(TargetServerConfigError, match="default_timeout_seconds"):
            build_execution_profile({"schema_version": 1, "cu_execution": {"default_timeout_seconds": -1}})
        with pytest.raises(TargetServerConfigError, match="timeout_seconds"):
            build_execution_profile({"schema_version": 1, "triggers": {"result": {"timeout_seconds": 0.5}}})
        with pytest.raises(TargetServerConfigError, match="timeout_seconds"):
            build_execution_profile(
                {"schema_version": 1, "workflow_execution": {"expected_results": {"timeout_seconds": 0.5}}}
            )

    def test_joining_processes_valid_mapping(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "joining_processes": {
                        "single": {
                            "policy": "exact_match",
                            "joining_process_id": "Prog_1",
                            "joining_process_origin_id": "Prog_Origin_1",
                        },
                        "job": {
                            "policy": "exact_match",
                            "joining_process_id": "Job_1",
                        },
                    }
                },
            }
        )
        assert "single" in profile.selection.joining_processes
        assert profile.selection.joining_processes["single"].joining_process_id == "Prog_1"
        assert profile.selection.joining_processes["single"].joining_process_origin_id == "Prog_Origin_1"
        assert "job" in profile.selection.joining_processes
        assert profile.selection.joining_processes["job"].joining_process_id == "Job_1"

    def test_joining_processes_invalid_not_mapping(self):
        with pytest.raises(TargetServerConfigError, match="joining_processes"):
            build_execution_profile({"schema_version": 1, "selection": {"joining_processes": "invalid"}})

    def test_joining_processes_invalid_sub_mapping(self):
        with pytest.raises(TargetServerConfigError, match="joining_processes.job"):
            build_execution_profile({"schema_version": 1, "selection": {"joining_processes": {"job": "invalid"}}})

    def test_joining_processes_invalid_key_type(self):
        with pytest.raises(TargetServerConfigError, match="keys must be strings"):
            build_execution_profile({"schema_version": 1, "selection": {"joining_processes": {123: {}}}})

    def test_expected_results_reject_ok_evaluation_on_abort(self):
        profile_default = build_execution_profile({"schema_version": 1})
        assert profile_default.workflow_execution.expected_results.reject_ok_evaluation_on_abort is False

        profile_enabled = build_execution_profile(
            {
                "schema_version": 1,
                "workflow_execution": {
                    "expected_results": {
                        "reject_ok_evaluation_on_abort": True,
                    }
                },
            }
        )
        assert profile_enabled.workflow_execution.expected_results.reject_ok_evaluation_on_abort is True
