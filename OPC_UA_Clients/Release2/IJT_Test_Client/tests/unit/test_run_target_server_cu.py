"""
Unit tests for run_target_server_cu.py

Tests CLI entry point, report generation, and output behavior.
No OPC UA server required — uses example profiles and in-memory config.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import run_target_server_cu module for unit-level function tests
# ---------------------------------------------------------------------------

_RUNNER_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_RUNNER_DIR))
_runner_mod = importlib.import_module("run_target_server_cu")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_runner(*args: str, cwd: Path | None = None) -> tuple[int, str]:
    """Run run_target_server_cu.py with the given args and return (returncode, output)."""
    runner = Path(__file__).resolve().parents[2] / "run_target_server_cu.py"
    result = subprocess.run(
        [sys.executable, str(runner), *args],
        cwd=str(cwd or Path(__file__).resolve().parents[2]),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.returncode, (result.stdout or "") + (result.stderr or "")


@pytest.fixture
def output_dir():
    """A temporary output directory in the project tmp/ folder."""
    path = Path(__file__).resolve().parents[2] / "tmp" / "runner_test" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def profiles_dir():
    return Path(__file__).resolve().parents[2] / "target_server_cu_profiles"


# ---------------------------------------------------------------------------
# --help flag
# ---------------------------------------------------------------------------


class TestHelpFlag:
    def test_help_exits_zero(self):
        rc, output = _run_runner("--help")
        assert rc == 0

    def test_help_mentions_profile(self):
        rc, output = _run_runner("--help")
        assert "--profile" in output

    def test_help_mentions_preflight(self):
        rc, output = _run_runner("--help")
        assert "--preflight-only" in output

    def test_help_mentions_mode(self):
        rc, output = _run_runner("--help")
        assert "--mode" in output


# ---------------------------------------------------------------------------
# Missing profile file
# ---------------------------------------------------------------------------


class TestMissingProfile:
    def test_missing_profile_exits_nonzero(self, output_dir):
        rc, output = _run_runner(
            "--profile",
            "nonexistent_profile_file.yaml",
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        assert rc != 0
        assert "not found" in output.lower() or "error" in output.lower()


# ---------------------------------------------------------------------------
# --preflight-only with example profiles
# ---------------------------------------------------------------------------


class TestPreflightOnly:
    def test_template_preflight_produces_report(self, profiles_dir, output_dir):
        template = profiles_dir / "template.yaml"
        rc, output = _run_runner(
            "--profile",
            str(template),
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        # Preflight should either pass or report blocking issues (non-zero).
        # The key check: report file must be written.
        report_file = output_dir / "target-server-cu-report.json"
        assert report_file.exists(), "Evidence report file must be written during preflight"

    def test_template_report_is_valid_json(self, profiles_dir, output_dir):
        template = profiles_dir / "template.yaml"
        _run_runner(
            "--profile",
            str(template),
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        report_file = output_dir / "target-server-cu-report.json"
        if report_file.exists():
            data = json.loads(report_file.read_text(encoding="utf-8"))
            assert "schema_version" in data
            assert "preflight" in data

    def test_template_preflight_summary_file_written(self, profiles_dir, output_dir):
        template = profiles_dir / "template.yaml"
        _run_runner(
            "--profile",
            str(template),
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        summary_file = output_dir / "target-server-cu-summary.txt"
        assert summary_file.exists(), "Human summary file must be written during preflight"

    def test_remote_start_example_preflight(self, profiles_dir, output_dir):
        example = profiles_dir / "example_remote_start.yaml"
        _run_runner(
            "--profile",
            str(example),
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        report_file = output_dir / "target-server-cu-report.json"
        assert report_file.exists(), "Evidence report must be written"

    def test_manual_trigger_example_preflight(self, profiles_dir, output_dir):
        example = profiles_dir / "example_manual_trigger.yaml"
        _run_runner(
            "--profile",
            str(example),
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        report_file = output_dir / "target-server-cu-report.json"
        assert report_file.exists(), "Evidence report must be written"


# ---------------------------------------------------------------------------
# Invalid YAML / configuration errors
# ---------------------------------------------------------------------------


class TestInvalidProfile:
    def test_invalid_yaml_exits_nonzero(self, output_dir, tmp_path):
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("{invalid yaml: [}", encoding="utf-8")
        rc, output = _run_runner(
            "--profile",
            str(bad_yaml),
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        assert rc != 0
        assert "error" in output.lower() or "configuration" in output.lower()

    def test_missing_schema_version_exits_nonzero(self, output_dir, tmp_path):
        no_schema = tmp_path / "no_schema.yaml"
        no_schema.write_text("profile_name: Test\n", encoding="utf-8")
        rc, output = _run_runner(
            "--profile",
            str(no_schema),
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        assert rc != 0

    def test_invalid_mode_exits_nonzero(self, output_dir, tmp_path):
        bad_mode = tmp_path / "bad_mode.yaml"
        bad_mode.write_text(
            "schema_version: 1\ncu_execution:\n  default_mode: turbo\n",
            encoding="utf-8",
        )
        rc, output = _run_runner(
            "--profile",
            str(bad_mode),
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        assert rc != 0


# ---------------------------------------------------------------------------
# --mode flag
# ---------------------------------------------------------------------------


class TestModeFlag:
    def test_automated_mode_runs(self, profiles_dir, output_dir):
        example = profiles_dir / "example_remote_start.yaml"
        rc, output = _run_runner(
            "--profile",
            str(example),
            "--mode",
            "automated",
            "--output-dir",
            str(output_dir),
        )
        # May exit 0 or 1 depending on preflight (placeholder endpoint → likely 1)
        # The key check: report must be written
        report_file = output_dir / "target-server-cu-report.json"
        assert report_file.exists(), "Report must be written in automated mode"

    def test_report_contains_mode_field(self, profiles_dir, output_dir):
        example = profiles_dir / "example_remote_start.yaml"
        _run_runner(
            "--profile",
            str(example),
            "--mode",
            "automated",
            "--output-dir",
            str(output_dir),
        )
        report_file = output_dir / "target-server-cu-report.json"
        if report_file.exists():
            data = json.loads(report_file.read_text(encoding="utf-8"))
            assert "mode" in data

    def test_preflight_mode_via_flag(self, profiles_dir, output_dir):
        example = profiles_dir / "template.yaml"
        rc, output = _run_runner(
            "--profile",
            str(example),
            "--mode",
            "preflight_only",
            "--output-dir",
            str(output_dir),
        )
        # This should run preflight, same as --preflight-only
        report_file = output_dir / "target-server-cu-report.json"
        assert report_file.exists()


# ---------------------------------------------------------------------------
# --scoring-mode override
# ---------------------------------------------------------------------------


class TestScoringModeOverride:
    def test_scoring_mode_override_applies(self, profiles_dir, output_dir):
        template = profiles_dir / "template.yaml"
        rc, output = _run_runner(
            "--profile",
            str(template),
            "--preflight-only",
            "--scoring-mode",
            "strict_profile",
            "--output-dir",
            str(output_dir),
        )
        report_file = output_dir / "target-server-cu-report.json"
        if report_file.exists():
            data = json.loads(report_file.read_text(encoding="utf-8"))
            assert data.get("scoring_mode") == "strict_profile"


# ---------------------------------------------------------------------------
# No --profile flag — default profile smoke test
# ---------------------------------------------------------------------------


class TestNoProfileFlag:
    def test_runs_without_profile(self, output_dir):
        rc, output = _run_runner(
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        # Default profile has empty endpoint → configuration error expected
        # But the runner should not crash
        assert isinstance(rc, int)

    def test_endpoint_override_without_profile(self, output_dir):
        rc, output = _run_runner(
            "--endpoint",
            "opc.tcp://localhost:40451",
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        # Should run preflight; may succeed or fail TCP probe
        assert isinstance(rc, int)
        report_file = output_dir / "target-server-cu-report.json"
        assert report_file.exists(), "Report must be written even without a profile"


# ---------------------------------------------------------------------------
# Endpoint overrides preserve target metadata
# ---------------------------------------------------------------------------


class TestEndpointOverride:
    def _write_profile_with_expected_server(self, tmp_path: Path) -> Path:
        profile = tmp_path / "profile.yaml"
        profile.write_text(
            """
schema_version: 1
target:
  endpoint: "opc.tcp://original:40451"
  expected_server:
    application_name: "Expected TargetServer"
    application_version: "1.2.3"
    warn_only_on_version_drift: false
""",
            encoding="utf-8",
        )
        return profile

    def test_cli_endpoint_override_preserves_expected_server(self, monkeypatch, tmp_path, output_dir):
        import run_target_server_cu

        profile_path = self._write_profile_with_expected_server(tmp_path)
        captured = {}

        def fake_run_preflight(profile, output_dir):
            captured["profile"] = profile
            return 0

        monkeypatch.setattr(run_target_server_cu, "run_preflight", fake_run_preflight)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_target_server_cu.py",
                "--profile",
                str(profile_path),
                "--preflight-only",
                "--endpoint",
                "opc.tcp://override:40451",
                "--output-dir",
                str(output_dir),
            ],
        )

        assert run_target_server_cu.main() == 0
        profile = captured["profile"]
        assert profile.target.endpoint == "opc.tcp://override:40451"
        assert profile.target.expected_server.application_name == "Expected TargetServer"
        assert profile.target.expected_server.application_version == "1.2.3"
        assert profile.target.expected_server.warn_only_on_version_drift is False

    def test_env_endpoint_override_preserves_expected_server(self, monkeypatch, tmp_path, output_dir):
        import run_target_server_cu

        profile_path = self._write_profile_with_expected_server(tmp_path)
        captured = {}

        def fake_run_preflight(profile, output_dir):
            captured["profile"] = profile
            return 0

        monkeypatch.setenv("OPCUA_SERVER_URL", "opc.tcp://env-override:40451")
        monkeypatch.setattr(run_target_server_cu, "run_preflight", fake_run_preflight)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_target_server_cu.py",
                "--profile",
                str(profile_path),
                "--preflight-only",
                "--output-dir",
                str(output_dir),
            ],
        )

        assert run_target_server_cu.main() == 0
        profile = captured["profile"]
        assert profile.target.endpoint == "opc.tcp://env-override:40451"
        assert profile.target.expected_server.application_name == "Expected TargetServer"
        assert profile.target.expected_server.application_version == "1.2.3"
        assert profile.target.expected_server.warn_only_on_version_drift is False


# ---------------------------------------------------------------------------
# Report schema / structure checks
# ---------------------------------------------------------------------------


class TestReportSchema:
    def test_report_has_required_top_level_keys(self, profiles_dir, output_dir):
        template = profiles_dir / "template.yaml"
        _run_runner(
            "--profile",
            str(template),
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        report_file = output_dir / "target-server-cu-report.json"
        if report_file.exists():
            data = json.loads(report_file.read_text(encoding="utf-8"))
            for key in ["schema_version", "mode", "profile_name", "endpoint", "preflight"]:
                assert key in data, f"Expected key '{key}' in report"

    def test_preflight_contains_checks_list(self, profiles_dir, output_dir):
        template = profiles_dir / "template.yaml"
        _run_runner(
            "--profile",
            str(template),
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        report_file = output_dir / "target-server-cu-report.json"
        if report_file.exists():
            data = json.loads(report_file.read_text(encoding="utf-8"))
            preflight = data.get("preflight", {})
            assert "checks" in preflight
            assert isinstance(preflight["checks"], list)

    def test_check_entries_have_outcome_field(self, profiles_dir, output_dir):
        template = profiles_dir / "template.yaml"
        _run_runner(
            "--profile",
            str(template),
            "--preflight-only",
            "--output-dir",
            str(output_dir),
        )
        report_file = output_dir / "target-server-cu-report.json"
        if report_file.exists():
            data = json.loads(report_file.read_text(encoding="utf-8"))
            checks = data.get("preflight", {}).get("checks", [])
            for check in checks:
                assert "outcome" in check, f"Check entry missing 'outcome': {check}"


# ---------------------------------------------------------------------------
# Live orchestration helpers unit tests (no server, no subprocess calls)
# ---------------------------------------------------------------------------


class TestBuildSpecTestEnv:
    """Unit tests for _build_spec_test_env() environment variable construction."""

    def _make_profile(self, endpoint: str = "opc.tcp://test:40451", caps_file: str = ""):
        """Build a minimal TargetServerCuProfile-like in-memory object."""
        from helpers.target_server_cu_config import build_default_profile

        profile = build_default_profile(endpoint=endpoint)
        # Override the capabilities_file to a known value for testing
        from dataclasses import replace as _replace

        return _replace(profile, capabilities_file=caps_file)

    def test_sets_opcua_server_url_from_endpoint(self):
        profile = self._make_profile(endpoint="opc.tcp://mytarget_server:40451")
        env = _runner_mod._build_spec_test_env(profile)
        assert env["OPCUA_SERVER_URL"] == "opc.tcp://mytarget_server:40451"

    def test_server_url_overrides_any_existing_env(self, monkeypatch):
        monkeypatch.setenv("OPCUA_SERVER_URL", "opc.tcp://old:40451")
        profile = self._make_profile(endpoint="opc.tcp://new:40451")
        env = _runner_mod._build_spec_test_env(profile)
        assert env["OPCUA_SERVER_URL"] == "opc.tcp://new:40451"

    def test_sets_target_server_profile_path_when_available(self, tmp_path):
        from dataclasses import replace as _replace

        profile_path = tmp_path / "target-server.yaml"
        profile_path.write_text("schema_version: 1\n", encoding="utf-8")
        profile = _replace(self._make_profile(), source_path=str(profile_path))

        env = _runner_mod._build_spec_test_env(profile)

        assert env["OPCUA_TARGET_SERVER_PROFILE"] == str(profile_path)

    def test_sets_target_server_mode_from_profile(self):
        from dataclasses import replace as _replace

        profile = self._make_profile()
        profile = _replace(profile, cu_execution=_replace(profile.cu_execution, default_mode="guided"))

        env = _runner_mod._build_spec_test_env(profile)

        assert env["OPCUA_TARGET_SERVER_MODE"] == "guided"

    def test_returns_dict(self):
        profile = self._make_profile()
        env = _runner_mod._build_spec_test_env(profile)
        assert isinstance(env, dict)

    def test_capabilities_file_set_when_profile_file_exists(self, tmp_path):
        """When the profile's capabilities_file resolves to an existing file, it is set."""
        caps = tmp_path / "caps.yaml"
        caps.write_text("schema_version: 1\n", encoding="utf-8")
        from dataclasses import replace as _replace

        from helpers.target_server_cu_config import build_default_profile

        profile = build_default_profile(endpoint="opc.tcp://x:40451")
        profile = _replace(profile, capabilities_file=str(caps))
        env = _runner_mod._build_spec_test_env(profile)
        assert env.get("OPCUA_CAPABILITIES_FILE") == str(caps)


class TestBuildSpecTestCommand:
    """Unit tests for _build_spec_test_command() pytest command construction."""

    def test_includes_spec_dir(self, tmp_path):
        spec_dir = tmp_path / "specification_tests"
        spec_dir.mkdir()
        junit = tmp_path / "results.xml"
        cmd = _runner_mod._build_spec_test_command(sys.executable, spec_dir, junit)
        assert str(spec_dir) in cmd

    def test_includes_junit_xml(self, tmp_path):
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        junit = tmp_path / "out.xml"
        cmd = _runner_mod._build_spec_test_command(sys.executable, spec_dir, junit)
        assert any(str(junit) in arg for arg in cmd)

    def test_excludes_simulation_by_default(self, tmp_path):
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        junit = tmp_path / "out.xml"
        cmd = _runner_mod._build_spec_test_command(sys.executable, spec_dir, junit)
        # The pytest marker filter "-m not simulation" should be in the command
        assert "not simulation" in cmd

    def test_no_simulation_exclusion_when_disabled(self, tmp_path):
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        junit = tmp_path / "out.xml"
        cmd = _runner_mod._build_spec_test_command(sys.executable, spec_dir, junit, exclude_simulation=False)
        assert "not simulation" not in cmd

    def test_uses_provided_python_exe(self, tmp_path):
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        junit = tmp_path / "out.xml"
        cmd = _runner_mod._build_spec_test_command("/path/to/python", spec_dir, junit)
        assert cmd[0] == "/path/to/python"

    def test_verbose_flag(self, tmp_path):
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        junit = tmp_path / "out.xml"
        cmd_v = _runner_mod._build_spec_test_command(sys.executable, spec_dir, junit, verbose=True)
        cmd_q = _runner_mod._build_spec_test_command(sys.executable, spec_dir, junit, verbose=False)
        assert "-v" in cmd_v
        assert "-q" in cmd_q


class TestRunLiveSpecTests:
    """Unit tests for run_live_spec_tests() orchestration logic (no real subprocess)."""

    def _make_profile(self, endpoint: str = "") -> object:
        from helpers.target_server_cu_config import build_default_profile

        return build_default_profile(endpoint=endpoint)

    def test_returns_skipped_for_empty_endpoint(self, output_dir):
        profile = self._make_profile(endpoint="")
        rc, meta = _runner_mod.run_live_spec_tests(profile, output_dir)
        assert rc == 0
        assert meta["status"] == "skipped"
        assert meta["reason"] == "endpoint_not_configured"

    def test_returns_skipped_for_placeholder_endpoint(self, output_dir):
        profile = self._make_profile(endpoint="opc.tcp://<host>:40451")
        rc, meta = _runner_mod.run_live_spec_tests(profile, output_dir)
        assert rc == 0
        assert meta["status"] == "skipped"
        assert meta["reason"] == "endpoint_not_configured"

    def test_returns_skipped_when_spec_dir_missing(self, output_dir, tmp_path, monkeypatch):
        """When specification_tests/ doesn't exist at _HERE, returns skipped."""
        profile = self._make_profile(endpoint="opc.tcp://real-host:40451")
        # Point _HERE at tmp_path (no specification_tests/ there)
        monkeypatch.setattr(_runner_mod, "_HERE", tmp_path)
        rc, meta = _runner_mod.run_live_spec_tests(profile, output_dir)
        assert rc == 0
        assert meta["status"] == "skipped"
        assert meta["reason"] == "spec_dir_not_found"

    def test_invokes_subprocess_when_endpoint_and_spec_dir_present(self, output_dir, monkeypatch):
        """When endpoint and spec_dir are present, a subprocess is invoked."""
        from helpers.target_server_cu_config import build_default_profile

        profile = build_default_profile(endpoint="opc.tcp://real-host:40451")

        # Create a fake spec_dir so the function doesn't return skipped
        fake_spec_dir = output_dir / "specification_tests"
        fake_spec_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(_runner_mod, "_HERE", output_dir)

        calls = []

        def fake_subprocess_run(cmd, **kwargs):
            calls.append(cmd)

            class FakeResult:
                returncode = 0

            return FakeResult()

        monkeypatch.setattr(_runner_mod.subprocess, "run", fake_subprocess_run)
        rc, meta = _runner_mod.run_live_spec_tests(profile, output_dir)
        assert len(calls) == 1
        assert rc == 0
        assert meta["status"] == "completed"
        assert meta["outcome"] == "passed"

    def test_returns_failed_rc_on_subprocess_nonzero(self, output_dir, monkeypatch):
        """When the subprocess returns non-zero, exit code is propagated."""
        from helpers.target_server_cu_config import build_default_profile

        profile = build_default_profile(endpoint="opc.tcp://real-host:40451")
        fake_spec_dir = output_dir / "specification_tests"
        fake_spec_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(_runner_mod, "_HERE", output_dir)

        def fake_run(cmd, **kwargs):
            class R:
                returncode = 2

            return R()

        monkeypatch.setattr(_runner_mod.subprocess, "run", fake_run)
        rc, meta = _runner_mod.run_live_spec_tests(profile, output_dir)
        assert rc == 2
        assert meta["outcome"] == "failed"
        assert meta["exit_code"] == 2


# ---------------------------------------------------------------------------
# --skip-spec-tests flag
# ---------------------------------------------------------------------------


class TestSkipSpecTestsFlag:
    def test_skip_spec_tests_flag_accepted(self, profiles_dir, output_dir):
        """--skip-spec-tests should be accepted without error."""
        template = profiles_dir / "template.yaml"
        rc, output = _run_runner(
            "--profile",
            str(template),
            "--mode",
            "automated",
            "--skip-spec-tests",
            "--output-dir",
            str(output_dir),
        )
        # rc=1 is expected (template has placeholder endpoint → blocking preflight)
        # Key: no "unrecognized argument" error
        assert "unrecognized" not in output.lower(), f"Flag rejected: {output}"

    def test_skip_spec_tests_mentioned_in_help(self):
        rc, output = _run_runner("--help")
        assert "--skip-spec-tests" in output

    def test_spec_tests_timeout_flag_accepted(self, profiles_dir, output_dir):
        template = profiles_dir / "template.yaml"
        rc, output = _run_runner(
            "--profile",
            str(template),
            "--mode",
            "automated",
            "--skip-spec-tests",
            "--spec-tests-timeout",
            "120",
            "--output-dir",
            str(output_dir),
        )
        assert "unrecognized" not in output.lower()


# ---------------------------------------------------------------------------
# Simulator default path / no regression
# ---------------------------------------------------------------------------


class TestSimulatorDefaultRegression:
    """Verify that --preflight-only with example profiles still works correctly.

    These tests guard against accidental breakage of the no-server, no-live-test path.
    """

    def test_preflight_with_example_profiles_always_writes_report(self, profiles_dir, output_dir):
        for example in profiles_dir.glob("example_*.yaml"):
            test_out = output_dir / example.stem
            _run_runner("--profile", str(example), "--preflight-only", "--output-dir", str(test_out))
            report = test_out / "target-server-cu-report.json"
            assert report.exists(), f"Report not written for {example.name}"

    def test_preflight_report_never_has_spec_tests_key(self, profiles_dir, output_dir):
        """--preflight-only must never include spec_tests in the report."""
        template = profiles_dir / "template.yaml"
        _run_runner("--profile", str(template), "--preflight-only", "--output-dir", str(output_dir))
        report_file = output_dir / "target-server-cu-report.json"
        if report_file.exists():
            data = json.loads(report_file.read_text(encoding="utf-8"))
            assert "spec_tests" not in data, "preflight-only must not include spec_tests"

    def test_automated_mode_with_placeholder_endpoint_exits_nonzero(self, profiles_dir, output_dir):
        """Placeholder endpoint in automated mode causes blocking preflight → rc=1."""
        template = profiles_dir / "template.yaml"
        rc, output = _run_runner(
            "--profile",
            str(template),
            "--mode",
            "automated",
            "--output-dir",
            str(output_dir),
        )
        assert rc == 1, "Placeholder endpoint should produce blocking preflight"

    def test_automated_mode_classification_only_with_skip_spec_tests(self, profiles_dir, output_dir):
        """--skip-spec-tests in automated mode with placeholder endpoint → rc=1 (blocked preflight).

        This confirms that --skip-spec-tests doesn't change preflight blocking behavior.
        """
        template = profiles_dir / "template.yaml"
        rc, output = _run_runner(
            "--profile",
            str(template),
            "--mode",
            "automated",
            "--skip-spec-tests",
            "--output-dir",
            str(output_dir),
        )
        # Template has placeholder endpoint → blocking configuration_error → rc=1
        assert rc == 1


# ---------------------------------------------------------------------------
# run_all_tests.py CLI alias compatibility
# ---------------------------------------------------------------------------


def _run_all_tests_runner_help() -> tuple[int, str]:
    """Run run_all_tests.py --help and return (rc, output)."""
    runner = Path(__file__).resolve().parents[2] / "run_all_tests.py"
    result = subprocess.run(
        [sys.executable, str(runner), "--help"],
        cwd=str(Path(__file__).resolve().parents[2]),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.returncode, (result.stdout or "") + (result.stderr or "")


class TestRunAllTestsCli:
    """Guard that run_all_tests.py exposes the final Target Server CLI flags."""

    def test_target_server_profile_in_help(self):
        rc, output = _run_all_tests_runner_help()
        assert rc == 0
        assert "--target-server-profile" in output, "New alias --target-server-profile must appear in help"

    def test_target_server_preflight_strict_in_help(self):
        rc, output = _run_all_tests_runner_help()
        assert rc == 0
        assert "--target-server-preflight-strict" in output
