"""
Unit tests for helpers/runner_plan.py — the typed immutable run-plan
resolution used by run_all_tests.py.

These tests build real argparse.Namespace objects via run_all_tests.py's own
_build_parser() so the tests stay honest about the actual CLI contract
(dest names, defaults) instead of hand-rolling a namespace that could drift
out of sync with the parser.
"""

from __future__ import annotations

import importlib
import sys
import uuid
from pathlib import Path

import pytest

_RUNNER_DIR = Path(__file__).resolve().parents[2]  # = IJT_Test_Client/
sys.path.insert(0, str(_RUNNER_DIR))
_run_all_tests = importlib.import_module("run_all_tests")

from helpers.runner_plan import (
    RunnerConfigError,
    resolve_run_plan,
    validate_flag_combinations,
    with_resolved_endpoint,
)
from helpers.sut_manifest import LegacyPairedFileError


def _parse(*argv: str):
    return _run_all_tests._build_parser().parse_args(list(argv))


@pytest.fixture
def profiles_dir() -> Path:
    return _RUNNER_DIR / "target_server_cu_profiles"


@pytest.fixture
def profile_dir(tmp_path) -> Path:
    return tmp_path


def _write_profile(
    path: Path,
    endpoint: str = "opc.tcp://<target-server-host>:40451",
    *,
    claims: str = "",
) -> Path:
    """Write one minimal SUT manifest and return its path."""
    manifest_path = path / f"sut_{uuid.uuid4().hex}.sut.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        'name: "Test SUT"\n'
        "lifecycle:\n  mode: external\n"
        "authentication:\n  source: anonymous\n"
        f'connection:\n  endpoint: "{endpoint}"\n' + claims,
        encoding="utf-8",
    )
    return manifest_path


# ---------------------------------------------------------------------------
# validate_flag_combinations — fast, dependency-free rejection
# ---------------------------------------------------------------------------


class TestValidateFlagCombinations:
    def test_default_no_flags_is_valid(self):
        validate_flag_combinations(_parse())

    def test_phase1_alone_is_valid(self):
        validate_flag_combinations(_parse("--phase1"))

    def test_phase2_alone_is_valid(self):
        validate_flag_combinations(_parse("--phase2"))

    def test_phase1_with_profile_is_rejected(self, tmp_path):
        profile = _write_profile(tmp_path)
        with pytest.raises(RunnerConfigError, match="--phase1"):
            validate_flag_combinations(_parse("--phase1", "--profile", str(profile)))

    def test_phase1_with_endpoint_is_rejected(self):
        with pytest.raises(RunnerConfigError, match="--phase1"):
            validate_flag_combinations(_parse("--phase1", "--endpoint", "opc.tcp://x:1"))

    def test_preflight_only_without_target_is_rejected(self, monkeypatch):
        monkeypatch.delenv("OPCUA_SERVER_URL", raising=False)
        with pytest.raises(RunnerConfigError, match="--preflight-only"):
            validate_flag_combinations(_parse("--preflight-only"))

    def test_preflight_only_with_endpoint_is_valid(self):
        validate_flag_combinations(_parse("--preflight-only", "--endpoint", "opc.tcp://x:1"))

    def test_preflight_only_with_env_endpoint_is_valid(self, monkeypatch):
        monkeypatch.setenv("OPCUA_SERVER_URL", "opc.tcp://x:1")
        validate_flag_combinations(_parse("--preflight-only"))

    def test_conflicting_profile_and_deprecated_alias_is_rejected(self, tmp_path):
        profile_a = _write_profile(tmp_path)
        profile_b = _write_profile(tmp_path)
        with pytest.raises(RunnerConfigError, match="both given"):
            validate_flag_combinations(_parse("--profile", str(profile_a), "--target-server-profile", str(profile_b)))

    def test_matching_profile_and_deprecated_alias_is_valid(self, tmp_path):
        profile = _write_profile(tmp_path)
        validate_flag_combinations(_parse("--profile", str(profile), "--target-server-profile", str(profile)))

    def test_negative_timeout_is_rejected(self):
        with pytest.raises(RunnerConfigError, match="--spec-tests-timeout"):
            validate_flag_combinations(_parse("--spec-tests-timeout", "-5"))

    def test_zero_timeout_is_rejected(self):
        with pytest.raises(RunnerConfigError, match="--spec-tests-timeout"):
            validate_flag_combinations(_parse("--spec-tests-timeout", "0"))

    def test_valid_positive_timeout_is_accepted(self):
        validate_flag_combinations(_parse("--spec-tests-timeout", "120"))


# ---------------------------------------------------------------------------
# resolve_run_plan — phase selection
# ---------------------------------------------------------------------------


class TestResolveRunPlanPhaseSelection:
    def test_default_runs_both_phases_no_target_evidence(self, monkeypatch):
        monkeypatch.delenv("OPCUA_SERVER_URL", raising=False)
        plan = resolve_run_plan(_parse())
        assert plan.run_phase1 is True
        assert plan.run_target is True
        assert plan.preflight_only is False
        assert plan.target_evidence_mode is False
        assert plan.launch_simulator is True
        assert plan.endpoint_source == "unset"

    def test_phase1_only_skips_target(self):
        plan = resolve_run_plan(_parse("--phase1"))
        assert plan.run_phase1 is True
        assert plan.run_target is False

    def test_phase2_only_skips_phase1(self, monkeypatch):
        monkeypatch.delenv("OPCUA_SERVER_URL", raising=False)
        plan = resolve_run_plan(_parse("--phase2"))
        assert plan.run_phase1 is False
        assert plan.run_target is True
        assert plan.launch_simulator is True

    def test_phase2_with_env_endpoint_suppresses_simulator(self, monkeypatch):
        monkeypatch.setenv("OPCUA_SERVER_URL", "opc.tcp://externally-managed:40462")
        plan = resolve_run_plan(_parse("--phase2"))
        assert plan.launch_simulator is False
        assert plan.target_evidence_mode is False
        assert plan.endpoint == "opc.tcp://externally-managed:40462"
        assert plan.endpoint_source == "env"

    def test_preflight_only_with_profile_runs_only_target(self, tmp_path):
        profile = _write_profile(tmp_path, endpoint="opc.tcp://real:40451")
        plan = resolve_run_plan(_parse("--preflight-only", "--profile", str(profile)))
        assert plan.run_phase1 is False
        assert plan.run_target is True
        assert plan.preflight_only is True
        assert plan.target_evidence_mode is True

    def test_preflight_only_with_env_server_url_resolves_default_profile(self, monkeypatch):
        monkeypatch.setenv("OPCUA_SERVER_URL", "opc.tcp://env-host:40451")
        plan = resolve_run_plan(_parse("--preflight-only"))
        assert plan.preflight_only is True
        assert plan.endpoint == "opc.tcp://env-host:40451"
        assert plan.profile is not None

    def test_relative_profile_path_is_resolved_against_cwd(self, tmp_path, monkeypatch):
        profile = _write_profile(tmp_path, endpoint="opc.tcp://relative-target:40451")
        monkeypatch.chdir(tmp_path)
        plan = resolve_run_plan(_parse("--profile", profile.name))
        assert plan.profile is not None
        assert plan.endpoint == "opc.tcp://relative-target:40451"


# ---------------------------------------------------------------------------
# resolve_run_plan — endpoint / capabilities precedence
# ---------------------------------------------------------------------------


class TestResolveRunPlanPrecedence:
    def test_profile_alone_runs_full_validation(self, tmp_path):
        profile = _write_profile(tmp_path, endpoint="opc.tcp://real:40451")
        plan = resolve_run_plan(_parse("--profile", str(profile)))
        assert plan.run_phase1 is True
        assert plan.run_target is True
        assert plan.preflight_only is False
        assert plan.target_evidence_mode is True
        assert plan.endpoint == "opc.tcp://real:40451"
        assert plan.endpoint_source == "profile"
        assert plan.launch_simulator is False

    def test_cli_endpoint_overrides_profile_endpoint(self, tmp_path):
        profile = _write_profile(tmp_path, endpoint="opc.tcp://from-profile:40451")
        plan = resolve_run_plan(_parse("--profile", str(profile), "--endpoint", "opc.tcp://from-cli:40451"))
        assert plan.endpoint == "opc.tcp://from-cli:40451"
        assert plan.endpoint_source == "cli"
        assert plan.profile is not None
        assert plan.profile.target.endpoint == "opc.tcp://from-cli:40451"

    def test_placeholder_manifest_endpoint_fails_fast(self, tmp_path, monkeypatch):
        """An external SUT manifest with placeholders must not start a run."""
        monkeypatch.delenv("OPCUA_SERVER_URL", raising=False)
        profile = _write_profile(tmp_path, endpoint="opc.tcp://<target-server-host>:40451")
        with pytest.raises(RunnerConfigError, match="not ready for a live run"):
            resolve_run_plan(_parse("--profile", str(profile)))

    def test_placeholder_manifest_endpoint_never_falls_back_to_simulator(self, tmp_path, monkeypatch):
        """With --endpoint supplied the run proceeds, but never via the simulator."""
        monkeypatch.delenv("OPCUA_SERVER_URL", raising=False)
        profile = _write_profile(tmp_path, endpoint="opc.tcp://<target-server-host>:40451")
        plan = resolve_run_plan(_parse("--profile", str(profile), "--endpoint", "opc.tcp://real:40451"))
        assert plan.target_evidence_mode is True
        assert plan.launch_simulator is False  # never silently falls back to the simulator

    def test_legacy_paired_profile_file_is_rejected(self, tmp_path):
        legacy = tmp_path / "old.profile.yaml"
        legacy.write_text(
            'schema_version: 1\nprofile_name: "Old"\ncapabilities_file: "old.capabilities.yaml"\n',
            encoding="utf-8",
        )
        with pytest.raises(LegacyPairedFileError, match="sut.yaml"):
            resolve_run_plan(_parse("--profile", str(legacy)))

    def test_endpoint_without_profile_builds_default_profile(self):
        plan = resolve_run_plan(_parse("--endpoint", "opc.tcp://ad-hoc:40451"))
        assert plan.target_evidence_mode is True
        assert plan.profile is not None
        assert plan.profile.target.endpoint == "opc.tcp://ad-hoc:40451"
        assert plan.launch_simulator is False

    def test_claims_cli_overrides_manifest_and_env(self, tmp_path, monkeypatch):
        caps_cli = _write_profile(tmp_path, endpoint="opc.tcp://cli-claims:1")
        caps_env = _write_profile(tmp_path, endpoint="opc.tcp://env-claims:1")
        manifest_path = _write_profile(tmp_path, endpoint="opc.tcp://real:1")
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(caps_env))
        plan = resolve_run_plan(_parse("--profile", str(manifest_path), "--capabilities-file", str(caps_cli)))
        assert plan.capabilities_source == "cli"
        assert plan.capabilities_file == str(Path(caps_cli).resolve())

    def test_manifest_is_its_own_claim_source_over_env(self, tmp_path, monkeypatch):
        """One manifest carries its own claims: env never silently replaces them."""
        caps_env = _write_profile(tmp_path, endpoint="opc.tcp://env-claims:1")
        manifest_path = _write_profile(tmp_path, endpoint="opc.tcp://real:1")
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(caps_env))
        plan = resolve_run_plan(_parse("--profile", str(manifest_path)))
        assert plan.capabilities_source == "profile"
        assert plan.capabilities_file == str(manifest_path.resolve())

    def test_claims_env_used_when_no_manifest_is_given(self, tmp_path, monkeypatch):
        caps_env = _write_profile(tmp_path, endpoint="opc.tcp://env-claims:1")
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(caps_env))
        plan = resolve_run_plan(_parse("--endpoint", "opc.tcp://ad-hoc:40451"))
        assert plan.capabilities_source == "env"
        assert plan.capabilities_file == str(caps_env)


# ---------------------------------------------------------------------------
# resolve_run_plan — deprecated alias, tool/process overrides, timeouts
# ---------------------------------------------------------------------------


class TestResolveRunPlanOverridesAndAlias:
    def test_deprecated_target_server_profile_alias_is_flagged(self, tmp_path):
        profile = _write_profile(tmp_path, endpoint="opc.tcp://real:1")
        plan = resolve_run_plan(_parse("--target-server-profile", str(profile)))
        assert plan.used_deprecated_profile_flag is True
        assert plan.profile is not None
        assert plan.target_evidence_mode is True

    def test_profile_flag_is_not_flagged_as_deprecated(self, tmp_path):
        profile = _write_profile(tmp_path, endpoint="opc.tcp://real:1")
        plan = resolve_run_plan(_parse("--profile", str(profile)))
        assert plan.used_deprecated_profile_flag is False

    def test_tool_and_process_overrides_forwarded_from_cli(self, tmp_path):
        profile = _write_profile(tmp_path, endpoint="opc.tcp://real:1")
        plan = resolve_run_plan(
            _parse(
                "--profile",
                str(profile),
                "--tool-product-instance-uri",
                "urn:tool:1",
                "--joining-process-id",
                "jp-1",
                "--joining-process-origin-id",
                "origin-1",
            )
        )
        assert plan.tool_product_instance_uri == "urn:tool:1"
        assert plan.joining_process_id == "jp-1"
        assert plan.joining_process_origin_id == "origin-1"
        assert plan.profile is not None
        assert plan.profile.selection.tool.product_instance_uri == "urn:tool:1"
        assert plan.profile.selection.joining_process.joining_process_id == "jp-1"

    def test_tool_and_process_overrides_forwarded_from_env(self, tmp_path, monkeypatch):
        profile = _write_profile(tmp_path, endpoint="opc.tcp://real:1")
        monkeypatch.setenv("OPCUA_TOOL_PRODUCT_INSTANCE_URI", "urn:tool:env")
        monkeypatch.setenv("OPCUA_JOINING_PROCESS_ID", "jp-env")
        plan = resolve_run_plan(_parse("--profile", str(profile)))
        assert plan.tool_product_instance_uri == "urn:tool:env"
        assert plan.joining_process_id == "jp-env"

    def test_scoring_mode_output_dir_and_timeout_propagated(self, tmp_path):
        profile = _write_profile(tmp_path, endpoint="opc.tcp://real:1")
        out_dir = tmp_path / "custom-output"
        plan = resolve_run_plan(
            _parse(
                "--profile",
                str(profile),
                "--scoring-mode",
                "strict_profile",
                "--output-dir",
                str(out_dir),
                "--spec-tests-timeout",
                "42",
                "--mode",
                "guided",
                "--interactive-prompts",
                "--skip-spec-tests",
            )
        )
        assert plan.scoring_mode == "strict_profile"
        assert plan.output_dir == out_dir
        assert plan.spec_tests_timeout == 42
        assert plan.mode == "guided"
        assert plan.interactive_prompts is True
        assert plan.skip_spec_tests is True
        assert plan.profile is not None
        assert plan.profile.cu_execution.scoring_mode == "strict_profile"

    def test_pytest_args_are_passed_through(self):
        plan = resolve_run_plan(_parse("--phase2", "--", "-k", "smoke"))
        assert plan.pytest_args == ["--", "-k", "smoke"]

    def test_missing_profile_file_raises_file_not_found(self, tmp_path):
        missing = tmp_path / "does-not-exist.yaml"
        with pytest.raises(FileNotFoundError):
            resolve_run_plan(_parse("--profile", str(missing)))


# ---------------------------------------------------------------------------
# lifecycle: auto_simulator manifests own the server process
# ---------------------------------------------------------------------------


class TestSimulatorLifecycle:
    def _simulator_manifest(self, path: Path) -> Path:
        manifest = path / "sim.sut.yaml"
        manifest.write_text(
            "schema_version: 1\n"
            'name: "Sim"\n'
            "lifecycle:\n  mode: auto_simulator\n"
            "authentication:\n  source: anonymous\n"
            'connection:\n  endpoint: ""\n',
            encoding="utf-8",
        )
        return manifest

    def test_auto_simulator_manifest_requests_a_launch(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPCUA_SERVER_URL", raising=False)
        plan = resolve_run_plan(_parse("--profile", str(self._simulator_manifest(tmp_path))), env={})
        assert plan.target_evidence_mode is True
        assert plan.launch_simulator is True
        assert plan.manifest is not None
        assert plan.manifest.is_auto_simulator is True

    def test_auto_simulator_manifest_does_not_fail_on_placeholders(self, tmp_path):
        # An auto_simulator manifest has no endpoint to fill in, so it is always live-ready.
        plan = resolve_run_plan(_parse("--profile", str(self._simulator_manifest(tmp_path))), env={})
        assert plan.endpoint == ""

    def test_external_manifest_never_launches_the_simulator(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPCUA_SERVER_URL", raising=False)
        manifest = _write_profile(tmp_path, endpoint="opc.tcp://real:40451")
        plan = resolve_run_plan(_parse("--profile", str(manifest)), env={})
        assert plan.launch_simulator is False

    def test_with_resolved_endpoint_updates_plan_and_profile(self, tmp_path):
        plan = resolve_run_plan(_parse("--profile", str(self._simulator_manifest(tmp_path))), env={})
        resolved = with_resolved_endpoint(plan, "opc.tcp://localhost:41234")
        assert resolved.endpoint == "opc.tcp://localhost:41234"
        assert resolved.endpoint_source == "simulator"
        assert resolved.profile is not None
        assert resolved.profile.target.endpoint == "opc.tcp://localhost:41234"

    def test_with_resolved_endpoint_is_a_no_op_without_an_endpoint(self, tmp_path):
        plan = resolve_run_plan(_parse("--profile", str(self._simulator_manifest(tmp_path))), env={})
        assert with_resolved_endpoint(plan, "") is plan

    def test_with_resolved_endpoint_is_a_no_op_without_a_profile(self):
        plan = resolve_run_plan(_parse("--phase2"), env={})
        assert plan.profile is None
        assert with_resolved_endpoint(plan, "opc.tcp://localhost:1") is plan
