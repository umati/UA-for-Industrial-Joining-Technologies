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
from asyncua import ua

from helpers.target_server_cu_config import (
    OUTCOME_BLOCKED,
    OUTCOME_CONFIGURATION_ERROR,
    OUTCOME_FAILED,
    OUTCOME_MANUAL_REQUIRED,
    OUTCOME_PASSED,
    OUTCOME_UNSUPPORTED,
    UINT64_MAX,
    RequestResultsConfig,
    StateChangingMethodsConfig,
    TargetServerConfigError,
    TargetServerCuProfile,
    _validate_request_results_config,
    build_default_profile,
    build_execution_profile,
    build_request_results_arguments,
    require_number,
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
    assert profile.workflow_execution.expected_results.referenced_child_completion_policy == "terminal_required"


def test_expected_results_accepts_partial_referenced_children_policy():
    profile = build_execution_profile(
        {
            "schema_version": 1,
            "workflow_execution": {
                "expected_results": {
                    "referenced_child_completion_policy": "partial_allowed",
                }
            },
        }
    )

    assert profile.workflow_execution.expected_results.referenced_child_completion_policy == "partial_allowed"


def test_start_limits_have_global_defaults_and_support_overrides():
    defaults = build_execution_profile({"schema_version": 1})
    assert defaults.workflow_execution.max_start_invocations_by_result_classification == {
        "single": 1,
        "batch": 3,
        "sync": 3,
        "job": 6,
    }

    overridden = build_execution_profile(
        {
            "schema_version": 1,
            "workflow_execution": {
                "max_start_invocations": 8,
                "max_start_invocations_by_result_classification": {
                    "batch": 4,
                    "job": 8,
                },
            },
        }
    )
    assert overridden.workflow_execution.max_start_invocations_by_result_classification == {
        "single": 1,
        "batch": 4,
        "sync": 3,
        "job": 8,
    }


@pytest.mark.parametrize(
    ("limits", "message"),
    [
        ([], "must be a mapping"),
        ({"batch": 0}, "positive integer"),
        ({"batch": True}, "positive integer"),
        ({"intervention": 1}, "unsupported keys"),
    ],
)
def test_start_limits_reject_invalid_configuration(limits, message):
    with pytest.raises(TargetServerConfigError, match=message):
        build_execution_profile(
            {
                "schema_version": 1,
                "workflow_execution": {
                    "max_start_invocations_by_result_classification": limits,
                },
            }
        )


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


def test_adaptive_workflow_contracts_are_typed():
    profile = build_execution_profile(
        {
            "schema_version": 1,
            "selection": {
                "joining_process": {
                    "policy": "all_compatible",
                }
            },
            "triggers": {
                "event": {
                    "mode": "workflow_actions",
                    "actions": {"select_process_event": "select_process_event"},
                }
            },
            "workflow_execution": {
                "approved_workflows": ["counter_intervention"],
                "evidence_reuse": {
                    "enabled": True,
                    "scope": "current_run",
                },
            },
            "cu_execution": {
                "identifier_workflows": {
                    "enabled": True,
                    "value_policy": "run_unique",
                    "cleanup_policy": "selective_test_owned_only",
                    "allow_reset_all": False,
                },
                "counter_effects": [
                    {
                        "method": "IncrementJoiningProcessCounter",
                        "count": 1,
                        "process_policy": "exact_match",
                        "joining_process_id": "job-1",
                        "expected_result_classification": "batch",
                    }
                ],
            },
        }
    )

    assert profile.selection.joining_process.policy == "all_compatible"
    assert profile.triggers.event.actions == {"select_process_event": "select_process_event"}
    assert profile.workflow_execution.evidence_reuse.enabled is True
    assert profile.cu_execution.identifier_workflows.allow_reset_all is False
    assert profile.cu_execution.counter_effects[0].expected_result_classification == "batch"


def test_all_compatible_is_not_valid_for_tool_selection():
    with pytest.raises(TargetServerConfigError, match="all_compatible"):
        build_execution_profile(
            {
                "schema_version": 1,
                "selection": {
                    "tool": {
                        "policy": "all_compatible",
                    }
                },
            }
        )


@pytest.mark.parametrize("policy", ["first_available", "first_ready", "first_compatible", "all_compatible"])
def test_counter_effect_requires_one_exact_process(policy):
    with pytest.raises(TargetServerConfigError, match="exact_match"):
        build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "counter_effects": [
                        {
                            "method": "IncrementJoiningProcessCounter",
                            "process_policy": policy,
                            "joining_process_id": "job-1",
                        }
                    ]
                },
            }
        )


def test_counter_effect_requires_process_id_at_typed_boundary():
    with pytest.raises(TargetServerConfigError, match="joining_process_id"):
        build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "counter_effects": [
                        {
                            "method": "IncrementJoiningProcessCounter",
                            "process_policy": "exact_match",
                        }
                    ]
                },
            }
        )


def test_identifier_contract_requires_dedicated_reset_all_workflow():
    with pytest.raises(TargetServerConfigError, match="reset_all_identifiers"):
        build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {"identifier_workflows": {"allow_reset_all": True}},
            }
        )

    profile = build_execution_profile(
        {
            "schema_version": 1,
            "cu_execution": {"identifier_workflows": {"allow_reset_all": True}},
            "workflow_execution": {"approved_workflows": ["reset_all_identifiers"]},
        }
    )
    assert profile.cu_execution.identifier_workflows.allow_reset_all is True


def test_counter_effect_requires_workflow_approval_at_typed_boundary():
    with pytest.raises(TargetServerConfigError, match="counter_intervention"):
        build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "counter_effects": [
                        {
                            "method": "IncrementJoiningProcessCounter",
                            "joining_process_id": "job-1",
                        }
                    ]
                },
            }
        )


def test_destructive_workflow_requires_risk_approval_at_typed_boundary():
    with pytest.raises(TargetServerConfigError, match="allow_destructive_methods must be true"):
        build_execution_profile(
            {
                "schema_version": 1,
                "workflow_execution": {"approved_workflows": ["remote_abort_job"]},
            }
        )


def test_allow_destructive_methods_must_be_boolean():
    with pytest.raises(TargetServerConfigError, match="allow_destructive_methods must be a boolean"):
        build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {"extension_fields": {"allow_destructive_methods": "yes"}},
            }
        )


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"cu_execution": {"identifier_workflows": []}}, "identifier_workflows"),
        ({"cu_execution": {"counter_effects": {}}}, "counter_effects"),
        ({"cu_execution": {"counter_effects": ["bad"]}}, "must be a mapping"),
        (
            {
                "cu_execution": {
                    "counter_effects": [
                        {
                            "method": "IncrementJoiningProcessCounter",
                            "joining_process_id": "job-1",
                            "expected_result_classification": "vendor",
                        }
                    ]
                }
            },
            "expected_result_classification",
        ),
        ({"triggers": {"event": {"actions": []}}}, "actions"),
        ({"workflow_execution": {"evidence_reuse": []}}, "evidence_reuse"),
    ],
)
def test_new_workflow_sections_reject_malformed_types(raw, message):
    with pytest.raises(TargetServerConfigError, match=message):
        build_execution_profile({"schema_version": 1, **raw})


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


# ---------------------------------------------------------------------------
# RequestResults config and argument builder
# ---------------------------------------------------------------------------


class TestRequestResultsConfig:
    def test_default_values(self):
        cfg = RequestResultsConfig()
        assert cfg.filter_strategy == "sequence_number"
        assert cfg.from_sequence_number == 1
        assert cfg.to_sequence_number == 50
        assert cfg.from_time == "2000-01-01T00:00:00Z"
        assert cfg.to_time == "9999-01-01T00:00:00Z"
        assert cfg.min_duration_ms == 100.0

    def test_build_arguments_sequence_number_default(self):
        cfg = RequestResultsConfig(filter_strategy="sequence_number", from_sequence_number=1, to_sequence_number=50)
        args = build_request_results_arguments(cfg)
        assert len(args) == 5
        assert args[0].VariantType == ua.VariantType.UInt64
        assert args[1].VariantType == ua.VariantType.UInt64
        assert args[2].VariantType == ua.VariantType.DateTime
        assert args[3].VariantType == ua.VariantType.DateTime
        assert args[4].VariantType == ua.VariantType.Double
        assert args[0].Value == 1
        assert args[1].Value == 50
        assert args[4].Value == 100.0

    def test_build_arguments_narrow_window_dynamic_expansion(self):
        # When triggered_seq is higher than configured window, shift safe compliance window
        # to request recent history ending at triggered_seq
        cfg = RequestResultsConfig(filter_strategy="sequence_number", from_sequence_number=1, to_sequence_number=50)
        args = build_request_results_arguments(cfg, triggered_seq=500)
        assert args[0].Value == 451  # 500 - 50 + 1 (50 results total)
        assert args[1].Value == 500

    def test_build_arguments_narrow_window_low_triggered_seq(self):
        # When triggered_seq is lower than configured from_sequence_number
        cfg = RequestResultsConfig(filter_strategy="sequence_number", from_sequence_number=50, to_sequence_number=100)
        args = build_request_results_arguments(cfg, triggered_seq=10)
        assert args[0].Value == 10
        assert args[1].Value == 60  # 10 + 51 - 1 (51 results total)

    def test_build_arguments_sequence_already_covers_triggered_seq(self):
        # When triggered_seq is already inside the range, no change to configured window
        cfg = RequestResultsConfig(filter_strategy="sequence_number", from_sequence_number=1, to_sequence_number=100)
        args = build_request_results_arguments(cfg, triggered_seq=50)
        assert args[0].Value == 1
        assert args[1].Value == 100

    def test_build_arguments_timestamp(self):
        cfg = RequestResultsConfig(
            filter_strategy="timestamp",
            from_time="2024-01-01T00:00:00Z",
            to_time="2025-01-01T00:00:00Z",
            min_duration_ms=50.0,
        )
        args = build_request_results_arguments(cfg)
        assert args[0].VariantType == ua.VariantType.UInt64
        assert args[1].VariantType == ua.VariantType.UInt64
        assert args[2].VariantType == ua.VariantType.DateTime
        assert args[3].VariantType == ua.VariantType.DateTime
        assert args[4].VariantType == ua.VariantType.Double
        assert args[0].Value == 0
        assert args[1].Value == 0
        assert args[2].Value.year == 2024
        assert args[3].Value.year == 2025
        assert args[4].Value == 50.0

    def test_build_arguments_both(self):
        cfg = RequestResultsConfig(
            filter_strategy="both",
            from_sequence_number=10,
            to_sequence_number=20,
            from_time="2024-01-01T00:00:00Z",
            to_time="2025-01-01T00:00:00Z",
        )
        args = build_request_results_arguments(cfg)
        assert args[0].Value == 10
        assert args[1].Value == 20
        assert args[2].Value.year == 2024
        assert args[3].Value.year == 2025

    def test_build_arguments_invalid_iso_falls_back(self):
        cfg = RequestResultsConfig(
            filter_strategy="timestamp",
            from_time="not-a-valid-date",
            to_time="",
        )
        args = build_request_results_arguments(cfg)
        assert args[2].Value.year == 2000
        assert args[3].Value.year == 9999

    def test_build_arguments_invalid_strategy_raises(self):
        cfg = RequestResultsConfig(filter_strategy="unknown")
        with pytest.raises(TargetServerConfigError, match="invalid filter_strategy"):
            build_request_results_arguments(cfg)

    @pytest.mark.parametrize(
        "cfg",
        [
            RequestResultsConfig(filter_strategy="sequence_number", from_sequence_number=0, to_sequence_number=0),
            RequestResultsConfig(from_sequence_number=1, to_sequence_number=UINT64_MAX + 1),
            RequestResultsConfig(min_duration_ms=float("nan")),
            RequestResultsConfig(min_duration_ms=float("inf")),
            RequestResultsConfig(min_duration_ms=10**1000),
        ],
    )
    def test_build_arguments_rejects_invalid_direct_config(self, cfg):
        with pytest.raises(TargetServerConfigError):
            build_request_results_arguments(cfg)

    def test_parse_cu_execution_compares_mixed_timezone_timestamps(self):
        with pytest.raises(TargetServerConfigError, match="must be <= to_time"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {
                        "request_results": {
                            "filter_strategy": "timestamp",
                            "from_time": "2025-01-01T00:00:00",
                            "to_time": "2024-01-01T00:00:00Z",
                        }
                    },
                }
            )

    @pytest.mark.parametrize("triggered_seq", [True, 1.5, "42", 0, UINT64_MAX + 1])
    def test_build_arguments_rejects_invalid_triggered_sequence(self, triggered_seq):
        with pytest.raises(TargetServerConfigError, match="triggered_seq"):
            build_request_results_arguments(RequestResultsConfig(), triggered_seq=triggered_seq)

    def test_parse_cu_execution_valid_request_results(self):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "request_results": {
                        "filter_strategy": "timestamp",
                        "from_sequence_number": 0,
                        "to_sequence_number": 0,
                        "from_time": "2023-01-01T00:00:00Z",
                        "to_time": "2024-01-01T00:00:00Z",
                        "min_duration_ms": 10.0,
                    }
                },
            }
        )
        rr = profile.cu_execution.request_results
        assert rr.filter_strategy == "timestamp"
        assert rr.from_sequence_number == 0
        assert rr.to_sequence_number == 0
        assert rr.from_time == "2023-01-01T00:00:00Z"
        assert rr.to_time == "2024-01-01T00:00:00Z"
        assert rr.min_duration_ms == 10.0

    def test_parse_cu_execution_sequence_mode_rejects_zero(self):
        with pytest.raises(TargetServerConfigError, match="must be >= 1"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {
                        "request_results": {
                            "filter_strategy": "sequence_number",
                            "from_sequence_number": 0,
                            "to_sequence_number": 100,
                        }
                    },
                }
            )

    def test_parse_cu_execution_uint64_bounds(self):
        # Valid uint64 max
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "cu_execution": {
                    "request_results": {
                        "filter_strategy": "sequence_number",
                        "from_sequence_number": 1,
                        "to_sequence_number": UINT64_MAX,
                    }
                },
            }
        )
        assert profile.cu_execution.request_results.to_sequence_number == UINT64_MAX

        # Out of bounds uint64
        with pytest.raises(TargetServerConfigError, match="must be <="):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {
                        "request_results": {
                            "filter_strategy": "sequence_number",
                            "from_sequence_number": 1,
                            "to_sequence_number": UINT64_MAX + 1,
                        }
                    },
                }
            )

    def test_parse_cu_execution_inverted_sequence_range_raises(self):
        with pytest.raises(TargetServerConfigError, match="must be >= from_sequence_number"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {
                        "request_results": {
                            "filter_strategy": "sequence_number",
                            "from_sequence_number": 50,
                            "to_sequence_number": 10,
                        }
                    },
                }
            )

    def test_parse_cu_execution_inverted_timestamps_raises(self):
        with pytest.raises(TargetServerConfigError, match="must be <= to_time"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {
                        "request_results": {
                            "filter_strategy": "timestamp",
                            "from_time": "2025-01-01T00:00:00Z",
                            "to_time": "2024-01-01T00:00:00Z",
                        }
                    },
                }
            )

    def test_parse_cu_execution_nan_or_inf_duration_raises(self):
        with pytest.raises(TargetServerConfigError, match="must be a finite number"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {
                        "request_results": {
                            "min_duration_ms": float("nan"),
                        }
                    },
                }
            )
        with pytest.raises(TargetServerConfigError, match="must be a finite number"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {
                        "request_results": {
                            "min_duration_ms": float("inf"),
                        }
                    },
                }
            )

    def test_parse_cu_execution_invalid_filter_strategy_raises(self):
        with pytest.raises(TargetServerConfigError, match="invalid value 'bogus'"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {
                        "request_results": {
                            "filter_strategy": "bogus",
                        }
                    },
                }
            )

    def test_parse_cu_execution_negative_sequence_number_raises(self):
        with pytest.raises(TargetServerConfigError, match="from_sequence_number"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {
                        "request_results": {
                            "from_sequence_number": -5,
                        }
                    },
                }
            )

    def test_parse_cu_execution_not_a_mapping_raises(self):
        with pytest.raises(TargetServerConfigError, match="request_results' must be a mapping"):
            build_execution_profile(
                {
                    "schema_version": 1,
                    "cu_execution": {
                        "request_results": "invalid",
                    },
                }
            )

    def test_validate_request_results_config_direct_edges(self):
        # bool sequence number
        cfg_bool_seq = RequestResultsConfig()
        object.__setattr__(cfg_bool_seq, "from_sequence_number", True)
        with pytest.raises(TargetServerConfigError, match="must be an integer"):
            _validate_request_results_config(cfg_bool_seq, "test_ctx")

        # to_sequence_number < from_sequence_number
        cfg_inverted = RequestResultsConfig(from_sequence_number=10, to_sequence_number=5)
        with pytest.raises(TargetServerConfigError, match="to_sequence_number must be >= from_sequence_number"):
            _validate_request_results_config(cfg_inverted, "test_ctx")

        # bool min_duration_ms
        cfg_bool_dur = RequestResultsConfig()
        object.__setattr__(cfg_bool_dur, "min_duration_ms", True)
        with pytest.raises(TargetServerConfigError, match="min_duration_ms must be a number"):
            _validate_request_results_config(cfg_bool_dur, "test_ctx")

        # non-string from_time
        cfg_bad_time = RequestResultsConfig()
        object.__setattr__(cfg_bad_time, "from_time", 123)
        with pytest.raises(TargetServerConfigError, match="from_time and to_time must be ISO 8601 strings"):
            _validate_request_results_config(cfg_bad_time, "test_ctx")

    def test_require_number_overflow(self):
        with pytest.raises(TargetServerConfigError, match="must be a finite number"):
            require_number({"val": 10**1000}, "val", 0.0, "test_ctx")

    def test_require_str_list_tuple(self):
        from helpers.target_server_cu_config import require_str_list

        assert require_str_list({"items": ("a", "b")}, "items", "ctx") == ["a", "b"]
