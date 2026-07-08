"""
Unit tests for helpers/target_server_cu_config.py

Tests profile loading, strict validation, defaults, and error conditions.
No OPC UA server required.
"""

from __future__ import annotations

import textwrap
import uuid
from pathlib import Path

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
    load_target_server_profile,
    load_target_server_profile_from_dict,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_profile(path: Path, content: str) -> Path:
    profile_path = path / f"profile_{uuid.uuid4().hex}.yaml"
    profile_path.write_text(textwrap.dedent(content), encoding="utf-8")
    return profile_path


@pytest.fixture
def tmp_profile_dir():
    """Repo-local temp directory for profile tests."""
    path = Path(__file__).resolve().parents[2] / "tmp" / "target_server_cu_config" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    yield path


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
capabilities_file: "../server_capabilities.yaml"

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
  start_invocation_policy: single_start_produces_final_result
  expected_operation_count: 1
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
# load_target_server_profile_from_dict — minimal valid
# ---------------------------------------------------------------------------


class TestMinimalValidProfile:
    def test_loads_minimal_profile(self):
        raw = {"schema_version": 1}
        profile = load_target_server_profile_from_dict(raw)
        assert isinstance(profile, TargetServerCuProfile)
        assert profile.schema_version == 1

    def test_default_mode_is_automated(self):
        profile = load_target_server_profile_from_dict({"schema_version": 1})
        assert profile.cu_execution.default_mode == "automated"

    def test_default_scoring_mode_is_diagnostic(self):
        profile = load_target_server_profile_from_dict({"schema_version": 1})
        assert profile.cu_execution.scoring_mode == "diagnostic"

    def test_default_precondition_policy_is_blocked(self):
        profile = load_target_server_profile_from_dict({"schema_version": 1})
        assert profile.cu_execution.precondition_failure_policy == "blocked"

    def test_default_result_trigger_mode_is_none(self):
        profile = load_target_server_profile_from_dict({"schema_version": 1})
        assert profile.triggers.result.mode == "none"

    def test_default_event_trigger_mode_is_observe_only(self):
        profile = load_target_server_profile_from_dict({"schema_version": 1})
        assert profile.triggers.event.mode == "observe_only"

    def test_default_state_changing_methods_blocks_all(self):
        profile = load_target_server_profile_from_dict({"schema_version": 1})
        sc = profile.cu_execution.state_changing_methods
        assert sc.allow_state_changing_method("SelectJoiningProcess") is False

    def test_frozen_profile(self):
        profile = load_target_server_profile_from_dict({"schema_version": 1})
        with pytest.raises((AttributeError, TypeError)):
            profile.schema_version = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# load_target_server_profile_from_dict — full valid
# ---------------------------------------------------------------------------


class TestFullValidProfile:
    def test_loads_full_profile(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = load_target_server_profile_from_dict(raw)
        assert profile.schema_version == 1
        assert profile.profile_name == "Full Test Profile"

    def test_endpoint_loaded(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = load_target_server_profile_from_dict(raw)
        assert profile.target.endpoint == "opc.tcp://localhost:40451"

    def test_allowed_methods_loaded(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = load_target_server_profile_from_dict(raw)
        sc = profile.cu_execution.state_changing_methods
        assert sc.allow_state_changing_method("SelectJoiningProcess") is True
        assert sc.allow_state_changing_method("StartSelectedJoining") is True
        assert sc.allow_state_changing_method("DeleteJoiningProcess") is False

    def test_result_trigger_mode(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = load_target_server_profile_from_dict(raw)
        assert profile.triggers.result.mode == "start_selected_joining"

    def test_result_timeout(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = load_target_server_profile_from_dict(raw)
        assert profile.triggers.result.timeout_seconds == 120.0

    def test_workflow_execution_policy(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = load_target_server_profile_from_dict(raw)
        assert profile.workflow_execution.start_invocation_policy == "single_start_produces_final_result"

    def test_reporting_output_dir(self):
        raw = yaml.safe_load(FULL_VALID)
        profile = load_target_server_profile_from_dict(raw)
        assert "target-server-cu" in profile.reporting.output_dir


# ---------------------------------------------------------------------------
# load_target_server_profile — filesystem
# ---------------------------------------------------------------------------


class TestLoadTargetServerProfileFile:
    def test_loads_minimal_yaml(self, tmp_profile_dir):
        path = _write_profile(tmp_profile_dir, MINIMAL_VALID)
        profile = load_target_server_profile(path)
        assert profile.schema_version == 1
        assert profile.source_path == str(path.resolve())

    def test_loads_full_yaml(self, tmp_profile_dir):
        path = _write_profile(tmp_profile_dir, FULL_VALID)
        profile = load_target_server_profile(path)
        assert profile.profile_name == "Full Test Profile"

    def test_missing_file_raises(self, tmp_profile_dir):
        with pytest.raises(FileNotFoundError):
            load_target_server_profile(tmp_profile_dir / "nonexistent.yaml")

    def test_invalid_yaml_raises_config_error(self, tmp_profile_dir):
        path = tmp_profile_dir / "bad.yaml"
        path.write_text("{invalid yaml: [}", encoding="utf-8")
        with pytest.raises(TargetServerConfigError, match="YAML parse error"):
            load_target_server_profile(path)

    def test_non_mapping_yaml_raises(self, tmp_profile_dir):
        path = _write_profile(tmp_profile_dir, "- item1\n- item2\n")
        with pytest.raises(TargetServerConfigError, match="mapping"):
            load_target_server_profile(path)

    def test_output_dir_resolves_against_runner_base_not_profile_dir(self, tmp_profile_dir):
        profile_dir = tmp_profile_dir / "target_server_cu_profiles"
        profile_dir.mkdir()
        path = _write_profile(profile_dir, FULL_VALID)
        profile = load_target_server_profile(path)
        runner_base = tmp_profile_dir / "IJT_Test_Client"

        assert (
            profile.output_dir_path(base_dir=runner_base) == (runner_base / "test-results/target-server-cu").resolve()
        )


# ---------------------------------------------------------------------------
# Schema version validation
# ---------------------------------------------------------------------------


class TestSchemaVersionValidation:
    def test_missing_schema_version_raises(self):
        with pytest.raises(TargetServerConfigError, match="schema_version"):
            load_target_server_profile_from_dict({"profile_name": "x"})

    def test_unsupported_schema_version_raises(self):
        with pytest.raises(TargetServerConfigError, match="Unsupported schema_version"):
            load_target_server_profile_from_dict({"schema_version": 99})

    def test_schema_version_not_int_raises(self):
        with pytest.raises(TargetServerConfigError, match="integer"):
            load_target_server_profile_from_dict({"schema_version": "1"})

    def test_schema_version_bool_raises(self):
        with pytest.raises(TargetServerConfigError, match="integer"):
            load_target_server_profile_from_dict({"schema_version": True})

    def test_schema_version_1_accepted(self):
        profile = load_target_server_profile_from_dict({"schema_version": 1})
        assert profile.schema_version == 1


# ---------------------------------------------------------------------------
# Invalid enum values
# ---------------------------------------------------------------------------


class TestInvalidEnumValues:
    def test_invalid_execution_mode_raises(self):
        with pytest.raises(TargetServerConfigError, match="invalid value"):
            load_target_server_profile_from_dict(
                {
                    "schema_version": 1,
                    "cu_execution": {"default_mode": "turbo"},
                }
            )

    def test_invalid_scoring_mode_raises(self):
        with pytest.raises(TargetServerConfigError, match="invalid value"):
            load_target_server_profile_from_dict(
                {
                    "schema_version": 1,
                    "cu_execution": {"scoring_mode": "magic"},
                }
            )

    def test_invalid_result_trigger_mode_raises(self):
        with pytest.raises(TargetServerConfigError, match="invalid value"):
            load_target_server_profile_from_dict(
                {
                    "schema_version": 1,
                    "triggers": {"result": {"mode": "teleport"}},
                }
            )

    def test_invalid_precondition_policy_raises(self):
        with pytest.raises(TargetServerConfigError, match="invalid value"):
            load_target_server_profile_from_dict(
                {
                    "schema_version": 1,
                    "cu_execution": {"precondition_failure_policy": "ignore"},
                }
            )

    def test_invalid_start_invocation_policy_raises(self):
        with pytest.raises(TargetServerConfigError, match="invalid value"):
            load_target_server_profile_from_dict(
                {
                    "schema_version": 1,
                    "workflow_execution": {"start_invocation_policy": "spam"},
                }
            )

    def test_invalid_tool_selection_policy_raises(self):
        with pytest.raises(TargetServerConfigError, match="invalid value"):
            load_target_server_profile_from_dict(
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
            load_target_server_profile_from_dict(
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
# Example YAML profiles from target_server_cu_profiles/ load successfully
# ---------------------------------------------------------------------------


class TestExampleProfilesLoad:
    @pytest.fixture
    def profiles_dir(self):
        return Path(__file__).resolve().parents[2] / "target_server_cu_profiles"

    def test_template_loads(self, profiles_dir):
        template = profiles_dir / "template.yaml"
        assert template.exists(), "template.yaml must exist"
        profile = load_target_server_profile(template)
        assert profile.schema_version == 1

    def test_example_remote_start_loads(self, profiles_dir):
        example = profiles_dir / "example_remote_start.yaml"
        assert example.exists(), "example_remote_start.yaml must exist"
        profile = load_target_server_profile(example)
        assert profile.triggers.result.mode == "start_selected_joining"

    def test_example_manual_trigger_loads(self, profiles_dir):
        example = profiles_dir / "example_manual_trigger.yaml"
        assert example.exists(), "example_manual_trigger.yaml must exist"
        profile = load_target_server_profile(example)
        assert profile.triggers.result.mode == "manual_trigger"

    def test_example_simulation_methods_loads(self, profiles_dir):
        example = profiles_dir / "example_simulation_methods.yaml"
        assert example.exists(), "example_simulation_methods.yaml must exist"
        profile = load_target_server_profile(example)
        assert profile.triggers.result.mode == "simulate_methods"
        assert profile.triggers.event.mode == "simulate_methods"
        assert profile.triggers.condition.mode == "simulate_methods"

    def test_example_profiles_have_no_real_endpoints(self, profiles_dir):
        for yaml_file in profiles_dir.glob("*.yaml"):
            profile = load_target_server_profile(yaml_file)
            endpoint = profile.target.endpoint
            # Endpoints in committed examples must be placeholders or empty
            assert (
                not endpoint
                or "<" in endpoint
                or endpoint == "opc.tcp://<target-server-host>:40451"
                or endpoint == "opc.tcp://<host>:40451"
                or "localhost" in endpoint
            ), (
                f"{yaml_file.name}: endpoint '{endpoint}' looks like a real address. "
                "Use a placeholder like 'opc.tcp://<target-server-host>:40451'."
            )
