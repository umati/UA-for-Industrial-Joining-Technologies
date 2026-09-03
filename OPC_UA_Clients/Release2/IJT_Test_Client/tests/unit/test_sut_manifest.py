"""
Unit tests for helpers/sut_manifest.py - the one tester-facing schema.

Covers schema round-trip, secret rejection, every authentication source,
placeholder handling for live runs, timeout separation, capability/workflow
claims, risk policy, legacy paired-file rejection, and the preserved CU claims
of the committed manifests.
No OPC UA server required.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from helpers.sut_manifest import (
    CURRENT_MANIFEST_SCHEMA_VERSION,
    MANIFEST_SCHEMA,
    MANIFEST_SUFFIX,
    UINT64_MAX,
    LegacyPairedFileError,
    SutManifest,
    SutManifestError,
    _validate_consistency,
    build_preset,
    iter_field_specs,
    load_capability_claims,
    load_sut_manifest,
    operational_placeholder_issues,
    parse_sut_manifest,
    preset_data,
    preset_names,
    prose_field_paths,
    reject_secret_values,
    render_field_reference,
    render_manifest_yaml,
    validate_live_ready,
)

_MANIFEST_DIR = Path(__file__).resolve().parents[2] / "target_server_cu_profiles"


def _minimal(**overrides) -> dict:
    """Return the smallest valid manifest mapping, with *overrides* merged in."""
    data = {
        "schema_version": 1,
        "name": "Unit test SUT",
        "lifecycle": {"mode": "external"},
        "authentication": {"source": "anonymous"},
        "connection": {"endpoint": "opc.tcp://localhost:40451"},
    }
    data.update(copy.deepcopy(overrides))
    return data


def _write(tmp_path: Path, data: dict, name: str = "unit") -> Path:
    path = tmp_path / f"{name}{MANIFEST_SUFFIX}"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Schema shape and round-trip
# ---------------------------------------------------------------------------


class TestSchemaAndRoundTrip:
    def test_schema_declares_every_required_area(self):
        section_names = {section.name for section in MANIFEST_SCHEMA}
        assert {
            "lifecycle",
            "connection",
            "authentication",
            "capability_claims",
            "workflows",
            "triggers",
            "execution_policy",
            "timeouts",
            "scoring",
            "reporting",
        } <= section_names

    def test_every_field_is_documented_and_typed(self):
        paths = [path for path, _ in iter_field_specs()]
        assert len(paths) == len(set(paths)), "duplicate field paths in the schema"
        for path, spec in iter_field_specs():
            assert spec.description.strip(), f"{path} has no description"
            assert spec.kind in {
                "str",
                "bool",
                "int",
                "number",
                "str_list",
                "str_map",
                "int_map",
                "mapping_list",
            }

    def test_minimal_manifest_round_trips_through_yaml(self, tmp_path):
        path = _write(tmp_path, _minimal())
        manifest = load_sut_manifest(path)
        assert isinstance(manifest, SutManifest)
        assert manifest.schema_version == CURRENT_MANIFEST_SCHEMA_VERSION
        assert manifest.name == "Unit test SUT"
        assert manifest.endpoint == "opc.tcp://localhost:40451"

        reparsed = parse_sut_manifest(manifest.to_dict(), source_path=str(path))
        assert reparsed.to_dict() == manifest.to_dict()

    def test_to_dict_is_a_defensive_copy(self, tmp_path):
        manifest = load_sut_manifest(_write(tmp_path, _minimal()))
        snapshot = manifest.to_dict()
        snapshot["connection"]["endpoint"] = "opc.tcp://tampered:1"
        assert manifest.endpoint == "opc.tcp://localhost:40451"

    def test_missing_schema_version_is_rejected(self):
        data = _minimal()
        del data["schema_version"]
        with pytest.raises(SutManifestError, match="schema_version"):
            parse_sut_manifest(data)

    @pytest.mark.parametrize("bad", ["1", True, 1.5])
    def test_non_integer_schema_version_is_rejected(self, bad):
        with pytest.raises(SutManifestError, match="schema_version"):
            parse_sut_manifest(_minimal(schema_version=bad))

    def test_unsupported_schema_version_is_rejected(self):
        with pytest.raises(SutManifestError, match="Unsupported manifest schema_version"):
            parse_sut_manifest(_minimal(schema_version=99))

    def test_required_fields_are_enforced(self):
        data = _minimal()
        del data["name"]
        with pytest.raises(SutManifestError, match="name: required field is missing"):
            parse_sut_manifest(data)

    def test_unknown_field_is_rejected_with_guidance(self):
        with pytest.raises(SutManifestError, match="unknown field"):
            parse_sut_manifest(_minimal(lifecycle={"mode": "external", "typo_field": 1}))

    def test_non_mapping_manifest_is_rejected(self):
        with pytest.raises(SutManifestError, match="must be a YAML mapping"):
            parse_sut_manifest(["not", "a", "mapping"])  # type: ignore[arg-type]

    def test_non_mapping_section_is_rejected(self):
        with pytest.raises(SutManifestError, match="must be a mapping"):
            parse_sut_manifest(_minimal(timeouts="fast"))

    def test_invalid_enum_lists_the_valid_values(self):
        with pytest.raises(SutManifestError, match="Valid values"):
            parse_sut_manifest(_minimal(lifecycle={"mode": "sometimes"}))

    @pytest.mark.parametrize(
        ("section", "payload", "match"),
        [
            ("timeouts", {"workflow_seconds": "soon"}, "must be a number"),
            ("timeouts", {"workflow_seconds": 0}, "must be >="),
            ("workflows", {"max_start_invocations": 0}, "must be >="),
            ("workflows", {"max_start_invocations": "six"}, "must be an integer"),
            ("workflows", {"consecutive_start_delay_seconds": "soon"}, "must be a number"),
            ("workflows", {"consecutive_start_delay_seconds": -1.0}, "must be >="),
            ("workflows", {"approved": "one"}, "must be a list"),
            ("workflows", {"approved": [1]}, "must be a string"),
            ("capability_claims", {"cu_overrides": {"a": 1}}, "string keys to string values"),
            ("capability_claims", {"claims_are_authoritative": "yes"}, "must be a boolean"),
            ("connection", {"endpoint": 42}, "must be a string"),
        ],
    )
    def test_type_errors_name_the_field(self, section, payload, match):
        with pytest.raises(SutManifestError, match=match):
            parse_sut_manifest(_minimal(**{section: payload}))

    def test_yaml_parse_error_is_reported(self, tmp_path):
        path = tmp_path / f"bad{MANIFEST_SUFFIX}"
        path.write_text("{invalid: [", encoding="utf-8")
        with pytest.raises(SutManifestError, match="YAML parse error"):
            load_sut_manifest(path)

    def test_non_mapping_file_is_reported(self, tmp_path):
        path = tmp_path / f"list{MANIFEST_SUFFIX}"
        path.write_text("- a\n- b\n", encoding="utf-8")
        with pytest.raises(SutManifestError, match="must be a YAML mapping"):
            load_sut_manifest(path)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="SUT manifest not found"):
            load_sut_manifest(tmp_path / f"nope{MANIFEST_SUFFIX}")


# ---------------------------------------------------------------------------
# Legacy paired files are rejected with a clear migration error
# ---------------------------------------------------------------------------


class TestLegacyPairedFileRejection:
    def test_legacy_capabilities_file_is_rejected(self, tmp_path):
        path = tmp_path / "server.capabilities.yaml"
        path.write_text("active_profile: full_specification_coverage\n", encoding="utf-8")
        with pytest.raises(LegacyPairedFileError, match="capability_claims"):
            load_sut_manifest(path)

    def test_legacy_profile_file_is_rejected(self, tmp_path):
        path = tmp_path / "server.profile.yaml"
        path.write_text('schema_version: 1\nprofile_name: "Old"\n', encoding="utf-8")
        with pytest.raises(LegacyPairedFileError, match=r"\*.sut.yaml"):
            load_sut_manifest(path)

    def test_legacy_layout_detected_by_keys_even_with_a_new_name(self, tmp_path):
        path = tmp_path / f"looks_new{MANIFEST_SUFFIX}"
        path.write_text(
            'schema_version: 1\nname: "x"\nprofile_name: "Old"\ncapabilities_file: "x.capabilities.yaml"\n',
            encoding="utf-8",
        )
        with pytest.raises(LegacyPairedFileError):
            load_sut_manifest(path)

    def test_capability_style_keys_without_claims_are_rejected(self):
        with pytest.raises(LegacyPairedFileError, match="legacy capability declaration"):
            parse_sut_manifest({"schema_version": 1, "name": "x", "active_profile": "basic_joining_system"})


# ---------------------------------------------------------------------------
# Authentication: references only, never secrets
# ---------------------------------------------------------------------------


class TestAuthentication:
    def test_anonymous_needs_no_reference(self):
        manifest = parse_sut_manifest(_minimal())
        assert manifest.authentication.source == "anonymous"
        assert manifest.authentication.missing_references() == []
        assert manifest.authentication.requires_operator_prompt is False

    def test_prompt_needs_no_stored_reference(self):
        manifest = parse_sut_manifest(_minimal(authentication={"source": "prompt", "username": "operator"}))
        assert manifest.authentication.requires_operator_prompt is True
        assert manifest.authentication.missing_references() == []

    def test_file_source_requires_a_credentials_file_reference(self):
        with pytest.raises(SutManifestError, match="authentication.credentials_file"):
            parse_sut_manifest(_minimal(authentication={"source": "file"}))

    def test_file_source_accepts_an_ignored_local_reference(self):
        manifest = parse_sut_manifest(
            _minimal(authentication={"source": "file", "credentials_file": "~/.ijt/my_controller.credentials.yaml"})
        )
        assert manifest.authentication.credentials_file.endswith("my_controller.credentials.yaml")

    def test_environment_source_requires_a_password_variable_name(self):
        with pytest.raises(SutManifestError, match="authentication.password_env_var"):
            parse_sut_manifest(_minimal(authentication={"source": "environment", "username_env_var": "IJT_USER"}))

    def test_environment_source_reports_unset_variables(self, monkeypatch):
        manifest = parse_sut_manifest(
            _minimal(
                authentication={
                    "source": "environment",
                    "username_env_var": "IJT_TEST_USER",
                    "password_env_var": "IJT_TEST_PASSWORD",
                }
            )
        )
        monkeypatch.delenv("IJT_TEST_USER", raising=False)
        monkeypatch.delenv("IJT_TEST_PASSWORD", raising=False)
        assert manifest.authentication.unresolved_environment_vars() == ["IJT_TEST_USER", "IJT_TEST_PASSWORD"]
        assert (
            manifest.authentication.unresolved_environment_vars({"IJT_TEST_USER": "u", "IJT_TEST_PASSWORD": "p"}) == []
        )

    def test_non_environment_source_never_reports_env_vars(self):
        manifest = parse_sut_manifest(_minimal())
        assert manifest.authentication.unresolved_environment_vars({}) == []

    def test_anonymous_source_rejects_a_user_name(self):
        with pytest.raises(SutManifestError, match="must be empty when"):
            parse_sut_manifest(_minimal(authentication={"source": "anonymous", "username": "operator"}))

    @pytest.mark.parametrize(
        "payload",
        [
            {"authentication": {"source": "anonymous", "password": "hunter2"}},
            {"authentication": {"source": "anonymous", "token": "abc"}},
            {"connection": {"endpoint": "opc.tcp://h:1", "private_key": "-----BEGIN"}},
            {"vendor": {"api_key": "k"}},
        ],
    )
    def test_secret_bearing_keys_are_rejected(self, payload):
        with pytest.raises(SutManifestError, match="never contain secret values"):
            parse_sut_manifest(_minimal(**payload))

    def test_inline_password_style_key_is_rejected(self):
        with pytest.raises(SutManifestError, match="inline passwords are not allowed"):
            reject_secret_values({"connection": {"keystore_password": "abc"}})

    def test_secret_rejection_scans_nested_lists(self):
        with pytest.raises(SutManifestError, match="never contain secret values"):
            reject_secret_values({"vendors": [{"name": "x", "secret": "s"}]})


# ---------------------------------------------------------------------------
# Capability and workflow claims
# ---------------------------------------------------------------------------


class TestClaimsAndWorkflows:
    def test_claims_default_to_authoritative_and_non_relaxable(self):
        claims = parse_sut_manifest(_minimal()).capability_claims
        assert claims.claims_are_authoritative is True
        assert claims.allow_discovery_to_relax_claims is False

    def test_claims_carry_profile_facets_and_overrides(self):
        manifest = parse_sut_manifest(
            _minimal(
                capability_claims={
                    "active_profile": "general_joining_system",
                    "supported_facets": ["sync_result_server_facet"],
                    "cu_overrides": {"single_result": "supported", "reboot_asset": "unsupported"},
                }
            )
        )
        claims = manifest.capability_claims
        assert claims.active_profile == "general_joining_system"
        assert claims.supported_facets == ("sync_result_server_facet",)
        assert claims.cu_overrides["reboot_asset"] == "unsupported"

    def test_unknown_claim_disposition_is_rejected(self):
        with pytest.raises(SutManifestError, match="invalid value 'probably'"):
            parse_sut_manifest(_minimal(capability_claims={"cu_overrides": {"single_result": "probably"}}))

    def test_approved_workflows_are_recorded(self):
        manifest = parse_sut_manifest(_minimal(workflows={"approved": ["remote_start", "counter_intervention"]}))
        assert manifest.approved_workflows == ("remote_start", "counter_intervention")

    def test_start_invocation_limits_have_portable_defaults(self):
        manifest = parse_sut_manifest(_minimal())
        limits = manifest.data["workflows"]["max_start_invocations_by_result_classification"]
        assert limits == {"single": 1, "batch": 3, "sync": 3, "job": 6}

    @pytest.mark.parametrize(
        ("limits", "message"),
        [
            ({"batch": 0}, "must be >= 1"),
            ({"batch": True}, "integer values"),
            ({"intervention": 1}, "unsupported keys"),
        ],
    )
    def test_start_invocation_limits_are_validated(self, limits, message):
        with pytest.raises(SutManifestError, match=message):
            parse_sut_manifest(
                _minimal(
                    workflows={
                        "max_start_invocations_by_result_classification": limits,
                    }
                )
            )

    def test_per_classification_selectors_are_validated(self):
        manifest = parse_sut_manifest(
            _minimal(
                workflows={
                    "process_selectors_by_classification": {
                        "Job": {"policy": "exact_match", "joining_process_id": "job-1"}
                    }
                }
            )
        )
        profile = manifest.to_execution_profile()
        assert profile.selection.joining_processes["job"].joining_process_id == "job-1"

    def test_adaptive_workflow_fields_are_forwarded(self):
        manifest = parse_sut_manifest(
            _minimal(
                workflows={
                    "approved": [
                        "counter_intervention",
                        "select_process_event",
                        "structured_identifier_round_trip",
                        "text_identifier_round_trip",
                    ],
                    "process_selector": {"policy": "all_compatible"},
                    "evidence_reuse": {"enabled": True, "scope": "current_run"},
                },
                triggers={
                    "event": {
                        "mode": "workflow_actions",
                        "actions": {"select_process_event": "select_process_event"},
                    }
                },
                execution_policy={
                    "state_changing_methods": {
                        "allowed_methods": [
                            "SendIdentifiers",
                            "SendTextIdentifiers",
                            "ResetIdentifiers",
                            "IncrementJoiningProcessCounter",
                        ]
                    },
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
            )
        )

        profile = manifest.to_execution_profile()
        assert profile.selection.joining_process.policy == "all_compatible"
        assert profile.workflow_execution.evidence_reuse.enabled is True
        assert profile.triggers.event.actions == {"select_process_event": "select_process_event"}
        assert profile.cu_execution.identifier_workflows.enabled is True
        assert profile.cu_execution.counter_effects[0].joining_process_id == "job-1"

    def test_workflow_event_action_must_be_approved(self):
        with pytest.raises(SutManifestError, match="unapproved workflows"):
            parse_sut_manifest(
                _minimal(
                    triggers={
                        "event": {
                            "mode": "workflow_actions",
                            "actions": {"select_process_event": "select_process_event"},
                        }
                    }
                )
            )

    def test_enabled_identifier_workflows_require_methods_and_workflow_approvals(self):
        with pytest.raises(SutManifestError, match="allowed_methods"):
            parse_sut_manifest(
                _minimal(
                    workflows={
                        "approved": [
                            "structured_identifier_round_trip",
                            "text_identifier_round_trip",
                        ]
                    },
                    execution_policy={"identifier_workflows": {"enabled": True}},
                )
            )

    def test_counter_effect_requires_allowed_method_and_exact_process_id(self):
        effect = {
            "method": "IncrementJoiningProcessCounter",
            "process_policy": "exact_match",
        }
        with pytest.raises(SutManifestError, match="allowed_methods"):
            parse_sut_manifest(_minimal(execution_policy={"counter_effects": [effect]}))

        with pytest.raises(SutManifestError, match="joining_process_id"):
            parse_sut_manifest(
                _minimal(
                    execution_policy={
                        "state_changing_methods": {"allowed_methods": ["IncrementJoiningProcessCounter"]},
                        "counter_effects": [effect],
                    }
                )
            )

    def test_counter_effect_requires_workflow_approval(self):
        effect = {
            "method": "IncrementJoiningProcessCounter",
            "process_policy": "exact_match",
            "joining_process_id": "job-1",
        }
        with pytest.raises(SutManifestError, match="counter_intervention"):
            parse_sut_manifest(
                _minimal(
                    execution_policy={
                        "state_changing_methods": {"allowed_methods": ["IncrementJoiningProcessCounter"]},
                        "counter_effects": [effect],
                    }
                )
            )

    def test_identifier_contract_requires_dedicated_reset_all_workflow(self):
        with pytest.raises(SutManifestError, match="reset_all_identifiers"):
            parse_sut_manifest(_minimal(execution_policy={"identifier_workflows": {"allow_reset_all": True}}))

        manifest = parse_sut_manifest(
            _minimal(
                workflows={"approved": ["reset_all_identifiers"]},
                execution_policy={
                    "state_changing_methods": {"allowed_methods": ["ResetIdentifiers"]},
                    "identifier_workflows": {"allow_reset_all": True},
                },
            )
        )
        assert manifest.risk_approvals is not None

    def test_destructive_workflow_requires_risk_approval(self):
        with pytest.raises(SutManifestError, match="allow_destructive_methods must be true"):
            parse_sut_manifest(_minimal(workflows={"approved": ["remote_abort_job"]}))

    @pytest.mark.parametrize(
        ("override", "message"),
        [
            ({"count": 0}, "positive integer"),
            ({"process_policy": "random"}, "process_policy"),
            ({"process_policy": "first_compatible"}, "exact_match"),
            ({"expected_result_classification": "vendor"}, "expected_result_classification"),
            ({"unexpected": True}, "unknown field"),
        ],
    )
    def test_counter_effect_fields_are_strictly_validated(self, override, message):
        effect = {
            "method": "IncrementJoiningProcessCounter",
            "count": 1,
            "process_policy": "exact_match",
            "joining_process_id": "job-1",
            **override,
        }
        with pytest.raises(SutManifestError, match=message):
            parse_sut_manifest(
                _minimal(
                    execution_policy={
                        "state_changing_methods": {"allowed_methods": ["IncrementJoiningProcessCounter"]},
                        "counter_effects": [effect],
                    }
                )
            )

    @pytest.mark.parametrize(
        ("counter_effects", "message"),
        [
            ({}, "must be a list"),
            (["bad"], "must be a mapping"),
        ],
    )
    def test_counter_effect_collection_shape_is_validated(self, counter_effects, message):
        with pytest.raises(SutManifestError, match=message):
            parse_sut_manifest(_minimal(execution_policy={"counter_effects": counter_effects}))

    def test_workflow_actions_require_at_least_one_mapping(self):
        with pytest.raises(SutManifestError, match="must not be empty"):
            parse_sut_manifest(
                _minimal(
                    triggers={"event": {"mode": "workflow_actions", "actions": {}}},
                )
            )

    def test_identifier_workflows_require_both_approved_round_trips(self):
        with pytest.raises(SutManifestError, match="approved workflows"):
            parse_sut_manifest(
                _minimal(
                    workflows={"approved": ["structured_identifier_round_trip"]},
                    execution_policy={
                        "state_changing_methods": {
                            "allowed_methods": ["SendIdentifiers", "SendTextIdentifiers", "ResetIdentifiers"],
                        },
                        "identifier_workflows": {"enabled": True},
                    },
                )
            )

    @pytest.mark.parametrize(
        ("override", "message"),
        [
            ({"method": ""}, "method must not be empty"),
            ({"joining_process_id": 42}, "joining_process_id must be a string"),
        ],
    )
    def test_counter_effect_requires_string_identity_fields(self, override, message):
        effect = {
            "method": "IncrementJoiningProcessCounter",
            "process_policy": "exact_match",
            "joining_process_id": "job-1",
            **override,
        }
        with pytest.raises(SutManifestError, match=message):
            parse_sut_manifest(
                _minimal(
                    execution_policy={
                        "state_changing_methods": {"allowed_methods": ["IncrementJoiningProcessCounter"]},
                        "counter_effects": [effect],
                    }
                )
            )

    def test_unknown_classification_selector_is_rejected(self):
        with pytest.raises(SutManifestError, match="unknown classification"):
            parse_sut_manifest(_minimal(workflows={"process_selectors_by_classification": {"widget": {}}}))

    def test_selector_mapping_must_be_a_mapping(self):
        with pytest.raises(SutManifestError, match="must be a mapping"):
            parse_sut_manifest(_minimal(workflows={"process_selectors_by_classification": ["job"]}))

    def test_selector_keys_must_be_strings(self):
        with pytest.raises(SutManifestError, match="keys must be strings"):
            parse_sut_manifest(_minimal(workflows={"process_selectors_by_classification": {123: {}}}))

    def test_cu_overrides_must_be_a_mapping(self):
        with pytest.raises(SutManifestError, match="cu_overrides: must be a mapping"):
            parse_sut_manifest(_minimal(capability_claims={"cu_overrides": "single_result"}))

    def test_primary_classification_cannot_repeat_as_intermediate(self):
        with pytest.raises(SutManifestError, match="must not repeat"):
            parse_sut_manifest(
                _minimal(
                    workflows={"expected_results": {"classification": "job", "intermediate_classifications": ["job"]}}
                )
            )

    def test_invalid_intermediate_classification_is_rejected(self):
        with pytest.raises(SutManifestError, match="intermediate_classifications"):
            parse_sut_manifest(
                _minimal(
                    workflows={
                        "expected_results": {
                            "classification": "job",
                            "intermediate_classifications": ["vendor-sequence"],
                        }
                    }
                )
            )


# ---------------------------------------------------------------------------
# Execution policy and risk approvals
# ---------------------------------------------------------------------------


class TestExecutionPolicyAndRisk:
    def test_state_changing_methods_default_to_opt_in(self):
        profile = parse_sut_manifest(_minimal()).to_execution_profile()
        assert profile.cu_execution.state_changing_methods.default_policy == "require_explicit_opt_in"
        assert profile.cu_execution.state_changing_methods.allow_state_changing_method("StartSelectedJoining") is False

    def test_allowed_methods_are_permissions_not_tests(self):
        profile = parse_sut_manifest(
            _minimal(execution_policy={"state_changing_methods": {"allowed_methods": ["StartSelectedJoining"]}})
        ).to_execution_profile()
        assert profile.cu_execution.state_changing_methods.allow_state_changing_method("StartSelectedJoining") is True
        assert profile.cu_execution.state_changing_methods.allow_state_changing_method("AbortJoiningProcess") is False

    def test_risk_approvals_default_to_safe(self):
        risk = parse_sut_manifest(_minimal()).risk_approvals
        assert risk.allow_disable_asset is False
        assert risk.allow_destructive_methods is False
        assert risk.enable_asset_policy == "when_disabled"
        assert risk.has_elevated_risk is False

    def test_elevated_risk_is_flagged_and_forwarded(self):
        manifest = parse_sut_manifest(
            _minimal(
                execution_policy={
                    "risk_approvals": {
                        "allow_disable_asset": True,
                        "allow_destructive_methods": True,
                        "enable_asset_policy": "always",
                        "approved_by": "Test Lead",
                        "approval_reference": "CR-42",
                    }
                }
            )
        )
        assert manifest.risk_approvals.has_elevated_risk is True
        extension = manifest.to_execution_profile().cu_execution.extension_fields
        assert extension["allow_disable_asset"] is True
        assert extension["enable_asset_policy"] == "always"
        assert extension["allow_destructive_methods"] is True

    def test_intervention_method_must_be_explicitly_allowed(self):
        with pytest.raises(SutManifestError, match="allowed_methods"):
            parse_sut_manifest(
                _minimal(execution_policy={"intervention": {"method": "IncrementJoiningProcessCounter"}})
            )

    def test_allowed_intervention_method_is_forwarded(self):
        manifest = parse_sut_manifest(
            _minimal(
                execution_policy={
                    "intervention": {
                        "method": "IncrementJoiningProcessCounter",
                        "count": 2,
                        "message": "unit test",
                        "parent_process": {"joining_process_id": "parent-1"},
                    },
                    "state_changing_methods": {"allowed_methods": ["IncrementJoiningProcessCounter"]},
                }
            )
        )
        extension = manifest.to_execution_profile().cu_execution.extension_fields
        assert extension["intervention_method"] == "IncrementJoiningProcessCounter"
        assert extension["intervention_count"] == 2
        assert extension["counter_parent_process"]["joining_process_id"] == "parent-1"

    def test_request_results_defaults_to_sequence_number(self):
        manifest = parse_sut_manifest(_minimal())
        rr = manifest.data["execution_policy"]["request_results"]
        assert rr["filter_strategy"] == "sequence_number"
        assert rr["from_sequence_number"] == 1
        assert rr["to_sequence_number"] == 50
        assert rr["min_duration_ms"] == 100.0

        profile = manifest.to_execution_profile()
        assert profile.cu_execution.request_results.filter_strategy == "sequence_number"
        assert profile.cu_execution.request_results.from_sequence_number == 1
        assert profile.cu_execution.request_results.to_sequence_number == 50

    def test_request_results_inverted_sequence_range_rejected(self):
        with pytest.raises(SutManifestError, match="must be >= from_sequence_number"):
            parse_sut_manifest(
                _minimal(
                    execution_policy={
                        "request_results": {
                            "filter_strategy": "sequence_number",
                            "from_sequence_number": 100,
                            "to_sequence_number": 10,
                        }
                    }
                )
            )

    def test_request_results_sequence_mode_rejects_zero(self):
        with pytest.raises(SutManifestError, match="must be >= 1"):
            parse_sut_manifest(
                _minimal(
                    execution_policy={
                        "request_results": {
                            "filter_strategy": "sequence_number",
                            "from_sequence_number": 0,
                            "to_sequence_number": 100,
                        }
                    }
                )
            )

    def test_request_results_uint64_bounds(self):
        # Valid uint64 max
        manifest = parse_sut_manifest(
            _minimal(
                execution_policy={
                    "request_results": {
                        "filter_strategy": "sequence_number",
                        "from_sequence_number": 1,
                        "to_sequence_number": UINT64_MAX,
                    }
                }
            )
        )
        assert manifest.data["execution_policy"]["request_results"]["to_sequence_number"] == UINT64_MAX

        # Out of bounds uint64
        with pytest.raises(SutManifestError, match="must be <="):
            parse_sut_manifest(
                _minimal(
                    execution_policy={
                        "request_results": {
                            "filter_strategy": "sequence_number",
                            "from_sequence_number": 1,
                            "to_sequence_number": UINT64_MAX + 1,
                        }
                    }
                )
            )

    def test_request_results_inverted_timestamps_rejected(self):
        with pytest.raises(SutManifestError, match="must be <= to_time"):
            parse_sut_manifest(
                _minimal(
                    execution_policy={
                        "request_results": {
                            "filter_strategy": "timestamp",
                            "from_time": "2025-01-01T00:00:00Z",
                            "to_time": "2024-01-01T00:00:00Z",
                        }
                    }
                )
            )

    def test_request_results_nan_or_negative_duration_rejected(self):
        with pytest.raises(SutManifestError, match="must be >= 0.0"):
            parse_sut_manifest(
                _minimal(
                    execution_policy={
                        "request_results": {
                            "min_duration_ms": -5.0,
                        }
                    }
                )
            )
        with pytest.raises(SutManifestError, match="must be a finite number"):
            parse_sut_manifest(
                _minimal(
                    execution_policy={
                        "request_results": {
                            "min_duration_ms": float("nan"),
                        }
                    }
                )
            )


# ---------------------------------------------------------------------------
# Timeout separation
# ---------------------------------------------------------------------------


class TestTimeoutSeparation:
    def test_defaults_keep_each_budget_independent(self):
        timeouts = parse_sut_manifest(_minimal()).timeouts
        assert timeouts.passive_observation_seconds == 5.0
        assert timeouts.active_result_seconds == 60.0
        assert timeouts.workflow_seconds == 120.0
        assert timeouts.operator_seconds == 300.0
        assert timeouts.method_call_seconds == 15.0

    @pytest.mark.parametrize(
        ("trigger_mode", "expected"),
        [
            ("observe_only", 5.0),
            ("none", 5.0),
            # A client-started result completes within active_result_seconds; the
            # trigger budget stays the short passive-observation window.
            ("start_selected_joining", 5.0),
            ("simulate_methods", 5.0),
            ("manual_trigger", 300.0),
        ],
    )
    def test_result_budget_depends_on_the_trigger_mode(self, trigger_mode, expected):
        assert parse_sut_manifest(_minimal()).timeouts.result_trigger_seconds(trigger_mode) == expected

    def test_passive_budget_is_used_for_observed_evidence(self):
        profile = parse_sut_manifest(
            _minimal(
                triggers={"result": {"mode": "observe_only"}},
                timeouts={"passive_observation_seconds": 7.0, "active_result_seconds": 90.0},
            )
        ).to_execution_profile()
        assert profile.triggers.result.timeout_seconds == 7.0
        assert profile.triggers.event.timeout_seconds == 7.0
        assert profile.workflow_execution.expected_results.timeout_seconds == 90.0

    def test_operator_budget_is_used_for_manual_triggers(self):
        profile = parse_sut_manifest(
            _minimal(
                triggers={"result": {"mode": "manual_trigger"}},
                timeouts={"operator_seconds": 240.0, "passive_observation_seconds": 5.0},
            )
        ).to_execution_profile()
        assert profile.triggers.result.timeout_seconds == 240.0

    def test_workflow_and_method_budgets_are_forwarded_separately(self):
        profile = parse_sut_manifest(
            _minimal(timeouts={"workflow_seconds": 400.0, "method_call_seconds": 9.0})
        ).to_execution_profile()
        assert profile.cu_execution.extension_fields["workflow_timeout_seconds"] == 400.0
        assert profile.cu_execution.default_timeout_seconds == 9.0


# ---------------------------------------------------------------------------
# Scoring, reporting, and lifecycle defaults
# ---------------------------------------------------------------------------


class TestScoringAndReporting:
    def test_strict_claimed_scope_is_the_default(self):
        manifest = parse_sut_manifest(_minimal())
        assert manifest.scoring_mode == "strict_profile"
        assert manifest.claimed_scope_only is True
        assert manifest.to_execution_profile().cu_execution.scoring_mode == "strict_profile"

    def test_scoring_mode_can_be_relaxed_explicitly(self):
        manifest = parse_sut_manifest(_minimal(scoring={"mode": "diagnostic", "claimed_scope_only": False}))
        assert manifest.scoring_mode == "diagnostic"
        assert manifest.claimed_scope_only is False

    def test_redaction_defaults_protect_installation_values(self):
        manifest = parse_sut_manifest(_minimal())
        assert "endpoint" in manifest.redact_fields
        assert "product_instance_uri" in manifest.redact_fields
        profile = manifest.to_execution_profile()
        assert profile.reporting.sanitize_shared_artifacts is True
        assert profile.reporting.keep_local_exact_debug_artifacts is False

    def test_manifest_is_its_own_claim_source(self, tmp_path):
        path = _write(tmp_path, _minimal())
        profile = load_sut_manifest(path).to_execution_profile()
        assert profile.capabilities_file == str(path.resolve())

    def test_auto_simulator_lifecycle_is_recognised(self):
        manifest = parse_sut_manifest(_minimal(lifecycle={"mode": "auto_simulator"}, connection={"endpoint": ""}))
        assert manifest.is_auto_simulator is True


# ---------------------------------------------------------------------------
# Live readiness and placeholders
# ---------------------------------------------------------------------------


class TestLiveReadiness:
    def test_complete_external_manifest_is_ready(self):
        assert validate_live_ready(parse_sut_manifest(_minimal())) == []

    def test_placeholders_block_a_live_external_run(self):
        manifest = parse_sut_manifest(_minimal(connection={"endpoint": "opc.tcp://<host>:40451"}))
        issues = validate_live_ready(manifest)
        assert any("connection.endpoint" in issue for issue in issues)

    def test_descriptive_prose_containing_a_placeholder_word_is_not_an_issue(self):
        """Documentation prose is not an unresolved value."""
        manifest = parse_sut_manifest(
            _minimal(
                name="Controller <under test>",
                description="Copy this file and replace every <placeholder> before running.",
            )
        )
        assert validate_live_ready(manifest) == []

    def test_a_filled_example_becomes_live_ready(self):
        """The committed example stops blocking once its operational fields are filled."""
        data = build_preset("manual_trigger").to_dict()
        data["connection"]["endpoint"] = "opc.tcp://controller.example:40451"
        manifest = parse_sut_manifest(data)
        assert "<" in manifest.description  # the prose still documents placeholders
        assert validate_live_ready(manifest) == []

    def test_unresolved_operational_placeholder_is_rejected(self):
        data = build_preset("manual_trigger").to_dict()
        data["connection"]["endpoint"] = "opc.tcp://controller.example:40451"
        data["workflows"]["process_selector"]["joining_process_id"] = "<joining-process-id>"
        issues = validate_live_ready(parse_sut_manifest(data))
        assert issues == [
            "workflows.process_selector.joining_process_id: replace the placeholder '<joining-process-id>'"
        ]

    def test_placeholder_inside_a_list_entry_is_rejected(self):
        manifest = parse_sut_manifest(_minimal(workflows={"approved": ["<workflow-name>"]}))
        assert any("workflows.approved[0]" in issue for issue in validate_live_ready(manifest))

    def test_comparison_text_is_not_mistaken_for_a_placeholder(self):
        manifest = parse_sut_manifest(_minimal(workflows={"approved": ["a < b and c > d"]}))
        assert validate_live_ready(manifest) == []

    def test_prose_field_paths_are_the_documented_free_text_fields(self):
        assert prose_field_paths() == frozenset({"name", "description"})

    def test_operational_placeholder_scan_skips_prose(self):
        issues = operational_placeholder_issues(
            {
                "description": "replace every <placeholder>",
                "connection": {"endpoint": "opc.tcp://<host>:40451"},
            }
        )
        assert issues == ["connection.endpoint: replace the placeholder 'opc.tcp://<host>:40451'"]

    def test_empty_endpoint_blocks_a_live_external_run(self):
        issues = validate_live_ready(parse_sut_manifest(_minimal(connection={"endpoint": ""})))
        assert any("required for an external SUT" in issue for issue in issues)

    def test_unset_environment_secret_blocks_a_live_run(self, monkeypatch):
        monkeypatch.delenv("IJT_MISSING_PASSWORD", raising=False)
        manifest = parse_sut_manifest(
            _minimal(authentication={"source": "environment", "password_env_var": "IJT_MISSING_PASSWORD"})
        )
        issues = validate_live_ready(manifest)
        assert any("IJT_MISSING_PASSWORD" in issue for issue in issues)

    def test_simulator_lifecycle_is_always_ready(self):
        assert validate_live_ready(build_preset("simulator")) == []


# ---------------------------------------------------------------------------
# Built-in presets and committed manifests
# ---------------------------------------------------------------------------


class TestPresetsAndCommittedManifests:
    def test_presets_are_code_not_companion_files(self):
        assert set(preset_names()) == {"template", "simulator", "remote_start_multi_operation", "manual_trigger"}
        for name in preset_names():
            assert isinstance(build_preset(name), SutManifest)

    def test_unknown_preset_is_rejected(self):
        with pytest.raises(SutManifestError, match="Unknown preset"):
            preset_data("does_not_exist")

    def test_simulator_preset_is_complete_without_placeholders(self):
        manifest = build_preset("simulator")
        assert manifest.is_auto_simulator is True
        assert validate_live_ready(manifest) == []
        assert "<" not in yaml.safe_dump(manifest.to_dict())

    def test_template_preset_uses_placeholders_and_fails_live_validation(self):
        manifest = build_preset("template")
        assert manifest.lifecycle_mode == "external"
        assert validate_live_ready(manifest)

    def test_simulator_preset_preserves_the_simulator_cu_claims(self):
        overrides = build_preset("simulator").capability_claims.cu_overrides
        assert len(overrides) == 25
        assert all(value == "unsupported" for value in overrides.values())
        for key in ("acknowledge_results", "set_offline_timer", "get_joint_design_list", "execute_operation"):
            assert overrides[key] == "unsupported"

    def test_remote_start_preset_preserves_the_generic_controller_claims(self):
        claims = build_preset("remote_start_multi_operation").capability_claims
        assert claims.active_profile == "general_joining_system"
        assert len(claims.supported_facets) == 8
        assert len(claims.cu_overrides) == 62
        assert claims.cu_overrides["job_result"] == "supported"
        assert claims.cu_overrides["intervention_result"] == "supported"
        assert claims.cu_overrides["sync_result"] == "unsupported"

    def test_manual_trigger_preset_keeps_full_coverage_claims(self):
        claims = build_preset("manual_trigger").capability_claims
        assert claims.active_profile == "full_specification_coverage"
        assert claims.cu_overrides == {"start_selected_joining": "manual_required"}

    def test_remote_start_preset_matches_its_documented_workflow(self):
        profile = build_preset("remote_start_multi_operation").to_execution_profile()
        expected = profile.workflow_execution.expected_results
        assert profile.triggers.result.mode == "start_selected_joining"
        assert profile.workflow_execution.max_start_invocations == 6
        assert profile.workflow_execution.consecutive_start_delay_seconds == 0.25
        assert expected.classification == "job"
        assert expected.final_result_required is False
        assert "job" in profile.selection.joining_processes
        # Passive observation budget stays short; result completion budget stays long.
        assert profile.triggers.result.timeout_seconds < expected.timeout_seconds

    def test_manual_trigger_preset_waits_for_the_operator(self):
        profile = build_preset("manual_trigger").to_execution_profile()
        assert profile.triggers.result.mode == "manual_trigger"
        assert profile.workflow_execution.max_start_invocations == 1
        assert profile.workflow_execution.consecutive_start_delay_seconds == 0.25
        assert profile.cu_execution.allow_manual_steps is True

    @pytest.mark.parametrize(
        "manifest_path",
        sorted(_MANIFEST_DIR.glob(f"*{MANIFEST_SUFFIX}")),
        ids=lambda path: path.name,
    )
    def test_committed_manifest_loads_and_is_sanitized(self, manifest_path: Path):
        manifest = load_sut_manifest(manifest_path)
        endpoint = manifest.endpoint
        assert not endpoint or "<" in endpoint or "localhost" in endpoint, (
            f"{manifest_path.name}: endpoint '{endpoint}' looks like a real address"
        )
        expected = manifest.to_execution_profile().workflow_execution.expected_results
        if expected.classification == "any":
            assert expected.final_result_required is False
        assert expected.classification not in expected.intermediate_classifications

    def test_no_legacy_paired_files_remain(self):
        assert not list(_MANIFEST_DIR.glob("*.profile.yaml"))
        assert not list(_MANIFEST_DIR.glob("*.capabilities.yaml"))

    def test_load_capability_claims_reads_only_the_claims(self):
        claims = load_capability_claims(_MANIFEST_DIR / f"simulator{MANIFEST_SUFFIX}")
        assert claims.active_profile == "full_specification_coverage"
        assert claims.claims_are_authoritative is True


# ---------------------------------------------------------------------------
# Generation from schema metadata
# ---------------------------------------------------------------------------


class TestGeneration:
    @pytest.mark.parametrize("preset", preset_names())
    def test_generated_manifest_round_trips(self, preset):
        text = render_manifest_yaml(preset)
        manifest = parse_sut_manifest(yaml.safe_load(text), source_path=f"<generated:{preset}>")
        assert manifest.name == build_preset(preset).name

    def test_generated_manifest_documents_every_field(self):
        text = render_manifest_yaml("template")
        for path, spec in iter_field_specs():
            leaf = path.split(".")[-1]
            assert f"{leaf}:" in text, f"{path} missing from the generated template"
            assert spec.description.split()[0] in text or spec.description[:20] in text

    def test_generated_manifest_warns_about_secrets_and_certification(self):
        text = render_manifest_yaml("template")
        assert "Never put a password, token, or key in this file" in text
        assert "not an OPC Foundation" in text

    def test_field_reference_is_generated_from_the_schema(self):
        reference = render_field_reference()
        assert "# SUT Manifest Field Reference" in reference
        for path, _ in iter_field_specs():
            assert f"`{path}`" in reference
        for name in preset_names():
            assert f"`{name}`" in reference

    def test_field_reference_states_the_report_contract(self):
        reference = render_field_reference()
        assert "Passed, Failed, Not Supported, Blocked, Not Tested, Inconclusive" in reference
        assert "no OPC Foundation certification claim" in reference


class TestSutManifestValidationCoverage:
    def test_parse_number_overflow_error(self):
        from helpers.sut_manifest import FieldSpec, _validate_scalar

        spec = FieldSpec("test_num", "number", "test")
        with pytest.raises(SutManifestError, match="must be a finite number"):
            _validate_scalar(10**1000, spec, "test_path")

    def test_parse_number_max_value(self):
        from helpers.sut_manifest import FieldSpec, _validate_scalar

        spec = FieldSpec("test_num", "number", "test", max_value=10.0)
        with pytest.raises(SutManifestError, match="must be <= 10.0"):
            _validate_scalar(20.0, spec, "test_path")

    def test_request_results_consistency_sequence_types(self):
        # bool from_sequence_number
        manifest = build_preset("simulator")
        manifest.data["execution_policy"]["request_results"]["from_sequence_number"] = True
        with pytest.raises(SutManifestError, match="from_sequence_number must be an integer"):
            _validate_consistency(manifest)

        # bool to_sequence_number
        manifest = build_preset("simulator")
        manifest.data["execution_policy"]["request_results"]["to_sequence_number"] = True
        with pytest.raises(SutManifestError, match="to_sequence_number must be an integer"):
            _validate_consistency(manifest)

    def test_request_results_consistency_naive_and_invalid_timestamps(self):
        # Naive datetime strings (no offset/Z) are normalized to UTC in consistency check
        manifest = build_preset("simulator")
        manifest.data["execution_policy"]["request_results"]["from_time"] = "2024-01-01T10:00:00"
        manifest.data["execution_policy"]["request_results"]["to_time"] = "2024-01-01T11:00:00"
        _validate_consistency(manifest)

        # Invalid timestamp string falls through gracefully in consistency check
        manifest.data["execution_policy"]["request_results"]["from_time"] = "invalid-date"
        _validate_consistency(manifest)

    def test_request_results_consistency_min_duration_validation(self):
        manifest = build_preset("simulator")
        manifest.data["execution_policy"]["request_results"]["min_duration_ms"] = True
        with pytest.raises(SutManifestError, match="min_duration_ms must be a finite non-negative number"):
            _validate_consistency(manifest)

        manifest.data["execution_policy"]["request_results"]["min_duration_ms"] = -5.0
        with pytest.raises(SutManifestError, match="min_duration_ms must be a finite non-negative number"):
            _validate_consistency(manifest)

    def test_int_map_and_identifier_validation_defensive_branches(self):
        from helpers.sut_manifest import FieldSpec, _validate_scalar

        # 1. spec.kind == "int_map" with non-dict
        manifest = build_preset("simulator")
        manifest.data["workflows"]["max_start_invocations_by_result_classification"] = "not_a_dict"
        with pytest.raises(SutManifestError, match="must be a mapping"):
            parse_sut_manifest(manifest.data)

        # 2. spec.kind == "int_map" with item > spec.max_value
        spec = FieldSpec("test_map", "int_map", "doc", max_value=5)
        with pytest.raises(SutManifestError, match="must be <= 5, got 10"):
            _validate_scalar({"single": 10}, spec, "workflows.test_map")

        # 3. allow_reset_all with ResetIdentifiers not in allowed_methods
        manifest = build_preset("simulator")
        manifest.data["execution_policy"]["identifier_workflows"]["allow_reset_all"] = True
        manifest.data["workflows"]["approved"].append("reset_all_identifiers")
        intervention_method = manifest.data["execution_policy"]["intervention"]["method"]
        manifest.data["execution_policy"]["state_changing_methods"]["allowed_methods"] = [
            intervention_method,
            "SendIdentifiers",
        ]
        with pytest.raises(SutManifestError, match="ResetIdentifiers in execution_policy"):
            _validate_consistency(manifest)

        # 4. max_start_invocations_by_result_classification non-positive limit
        manifest = build_preset("simulator")
        manifest.data["workflows"]["max_start_invocations_by_result_classification"]["single"] = 0
        with pytest.raises(SutManifestError, match="must be a positive integer"):
            _validate_consistency(manifest)
