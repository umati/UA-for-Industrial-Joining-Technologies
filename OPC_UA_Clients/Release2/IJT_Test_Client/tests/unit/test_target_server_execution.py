"""
Unit tests for helpers/target_server_execution.py — the canonical Target Server
CU execution logic used by run_all_tests.py (--profile/--endpoint).

These tests call run_preflight()/run_automated() directly (in-process).
"""

from __future__ import annotations

import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helpers import target_server_execution as tse
from helpers.target_server_cu_config import (
    OUTCOME_PASSED,
    build_default_profile,
    load_target_server_profile_from_dict,
)
from helpers.target_server_readiness import PreflightReport, ReadinessOutcome

# ---------------------------------------------------------------------------
# Colour / logging helpers
# ---------------------------------------------------------------------------


class TestColourHelpers:
    def teardown_method(self) -> None:
        tse.configure_colour(False)

    def test_c_is_plain_text_when_colour_disabled(self):
        tse.configure_colour(False)
        assert tse._c(tse._ANSI_RED, "hello") == "hello"

    def test_c_wraps_ansi_when_colour_enabled(self):
        tse.configure_colour(True)
        assert tse._c(tse._ANSI_RED, "hello") == f"{tse._ANSI_RED}hello{tse._ANSI_RESET}"

    def test_format_error_uses_red(self):
        tse.configure_colour(True)
        assert tse.format_error("bad") == f"{tse._ANSI_RED}bad{tse._ANSI_RESET}"

    def test_log_writes_to_stdout(self, capsys):
        tse._log("hello world")
        assert "hello world" in capsys.readouterr().out

    def test_section_and_divider_print_something(self, capsys):
        tse._section("My Section")
        tse._divider()
        out = capsys.readouterr().out
        assert "My Section" in out
        assert "─" in out

    def test_outcome_colour_known_outcome(self):
        assert tse._outcome_colour(OUTCOME_PASSED) == tse._ANSI_GREEN

    def test_outcome_colour_unknown_outcome_is_empty(self):
        assert tse._outcome_colour("not-a-real-outcome") == ""

    def test_print_check_includes_label_and_detail(self, capsys):
        outcome = ReadinessOutcome(outcome=OUTCOME_PASSED, detail="all good", check_name="my_check")
        tse._print_check(outcome)
        out = capsys.readouterr().out
        assert "my_check" in out
        assert "(all good)" in out

    def test_print_check_defaults_label_when_check_name_blank(self):
        buf = StringIO()
        with redirect_stdout(buf):
            tse._print_check(ReadinessOutcome(outcome="passed", check_name="", detail="ok"))
        assert "check" in buf.getvalue()

    def test_format_error(self):
        tse.configure_colour(False)
        assert tse.format_error("test error") == "test error"
        tse.configure_colour(True)
        assert "\033[91m" in tse.format_error("test error")

    def test_configure_colour(self):
        tse.configure_colour(True)
        assert tse._c(tse._ANSI_GREEN, "hello") != "hello"
        tse.configure_colour(False)
        assert tse._c(tse._ANSI_GREEN, "hello") == "hello"


class TestExcludedCusAndOverrides:
    def test_excluded_cus_any_returns_empty(self):
        assert tse._excluded_cus_for_result_scope("any") == frozenset()

    def test_apply_runtime_overrides_applies_all_fields(self, tmp_path):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://old:1"},
            }
        )
        caps = tmp_path / "custom.capabilities.yaml"
        caps.write_text("", encoding="utf-8")
        updated = tse.apply_runtime_overrides(
            profile,
            endpoint="opc.tcp://new:2",
            scoring_mode="strict_profile",
            capabilities_file=str(caps),
            tool_product_instance_uri="urn:tool:99",
            joining_process_id="PROG99",
            joining_process_origin_id="ORIGIN99",
        )
        assert updated.target.endpoint == "opc.tcp://new:2"
        assert updated.cu_execution.scoring_mode == "strict_profile"
        assert updated.selection.tool.product_instance_uri == "urn:tool:99"
        assert updated.selection.joining_process.joining_process_id == "PROG99"
        assert updated.selection.joining_process.joining_process_origin_id == "ORIGIN99"


class TestBuildSpecTestEnvDirect:
    def test_build_spec_test_env_populates_all_expected_vars(self, tmp_path):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://target:40451"},
                "selection": {
                    "tool": {"product_instance_uri": "urn:tool:123"},
                    "joining_process": {"joining_process_id": "P1", "joining_process_origin_id": "O1"},
                },
                "workflow_execution": {
                    "expected_results": {
                        "classification": "job",
                        "intermediate_classifications": ["batch"],
                    }
                },
            }
        )
        default_dir = tmp_path / "target_server_cu_profiles"
        default_dir.mkdir(parents=True, exist_ok=True)
        (default_dir / "default.capabilities.yaml").write_text("", encoding="utf-8")

        env = tse._build_spec_test_env(profile, base_dir=tmp_path)
        assert env["OPCUA_SERVER_URL"] == "opc.tcp://target:40451"
        assert env["OPCUA_TOOL_PRODUCT_INSTANCE_URI"] == "urn:tool:123"
        assert env["OPCUA_JOINING_PROCESS_ID"] == "P1"
        assert env["OPCUA_JOINING_PROCESS_ORIGIN_ID"] == "O1"
        assert env["OPCUA_TARGET_REQUIRED_RESULT_CLASSIFICATION"] == "4"
        assert "OPCUA_TARGET_EXCLUDED_CUS" in env
        assert env["OPCUA_CAPABILITIES_FILE"] == str(default_dir / "default.capabilities.yaml")

    def test_build_spec_test_env_with_explicit_existing_caps_file(self, tmp_path):
        caps_file = tmp_path / "my.capabilities.yaml"
        caps_file.write_text("schema_version: 1", encoding="utf-8")
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://target:40451"},
                "capabilities_file": str(caps_file),
                "workflow_execution": {
                    "expected_results": {
                        "classification": "any",
                    }
                },
            }
        )
        env = tse._build_spec_test_env(profile, base_dir=tmp_path)
        assert env["OPCUA_CAPABILITIES_FILE"] == str(caps_file)
        assert "OPCUA_TARGET_REQUIRED_RESULT_CLASSIFICATION" not in env
        assert "OPCUA_TARGET_EXCLUDED_CUS" not in env


# ---------------------------------------------------------------------------
# Evidence writers
# ---------------------------------------------------------------------------


def _preflight_report(endpoint: str = "opc.tcp://x:1") -> PreflightReport:
    report = PreflightReport(profile_name="P", endpoint=endpoint)
    report.add(ReadinessOutcome(outcome=OUTCOME_PASSED, check_name="c1", detail="fine"))
    return report


class TestEvidenceWriters:
    def test_write_evidence_report_contains_expected_keys(self, tmp_path):
        profile = build_default_profile(endpoint="opc.tcp://x:1")
        path = tse._write_evidence_report(
            tmp_path, profile, _preflight_report(), "preflight_only", "2024-01-01T00:00:00Z"
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["mode"] == "preflight_only"
        assert data["endpoint"] == "opc.tcp://x:1"
        assert "workflow" in data
        assert data["preflight"]["checks"][0]["check_name"] == "c1"

    def test_write_evidence_report_merges_extra_dict(self, tmp_path):
        profile = build_default_profile(endpoint="opc.tcp://x:1")
        path = tse._write_evidence_report(
            tmp_path, profile, _preflight_report(), "automated", "t", extra={"spec_tests": {"status": "skipped"}}
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["spec_tests"]["status"] == "skipped"

    def test_write_human_summary_contains_outcome_and_profile_name(self, tmp_path):
        profile = build_default_profile(endpoint="opc.tcp://x:1")
        path = tse._write_human_summary(tmp_path, profile, _preflight_report(), "preflight_only", "t", "PASSED")
        text = path.read_text(encoding="utf-8")
        assert "PASSED" in text
        assert profile.profile_name in text


# ---------------------------------------------------------------------------
# _generate_excel_report
# ---------------------------------------------------------------------------


class TestGenerateExcelReport:
    def test_skips_when_junit_or_cu_json_missing(self, tmp_path):
        profile = build_default_profile(endpoint="opc.tcp://x:1")
        result = tse._generate_excel_report(
            profile, tmp_path, tmp_path / "target-server-cu-report.json", run_result="passed"
        )
        assert result["status"] == "skipped"
        assert result["path"] is None

    def test_generated_when_subprocess_succeeds(self, tmp_path, monkeypatch):
        (tmp_path / "spec-tests.xml").write_text("<xml/>", encoding="utf-8")
        (tmp_path / "cu-coverage-report.json").write_text("{}", encoding="utf-8")
        profile = build_default_profile(endpoint="opc.tcp://x:1")

        class FakeCompleted:
            returncode = 0
            stdout = ""
            stderr = ""

        monkeypatch.setattr(tse.subprocess, "run", lambda cmd, **kw: FakeCompleted())
        result = tse._generate_excel_report(
            profile,
            tmp_path,
            tmp_path / "target-server-cu-report.json",
            run_result="passed",
            base_dir=tmp_path,
        )
        assert result["status"] == "generated"
        assert result["path"] == str(tmp_path / "report-controller.xlsx")

    def test_failed_when_subprocess_nonzero(self, tmp_path, monkeypatch):
        (tmp_path / "spec-tests.xml").write_text("<xml/>", encoding="utf-8")
        (tmp_path / "cu-coverage-report.json").write_text("{}", encoding="utf-8")
        profile = build_default_profile(endpoint="opc.tcp://x:1")

        class FakeCompleted:
            returncode = 1
            stdout = "boom"
            stderr = ""

        monkeypatch.setattr(tse.subprocess, "run", lambda cmd, **kw: FakeCompleted())
        result = tse._generate_excel_report(
            profile,
            tmp_path,
            tmp_path / "target-server-cu-report.json",
            run_result="failed",
            base_dir=tmp_path,
        )
        assert result["status"] == "failed"
        assert "boom" in result["reason"]

    def test_includes_capabilities_flag_when_capabilities_file_exists(self, tmp_path, monkeypatch):
        (tmp_path / "spec-tests.xml").write_text("<xml/>", encoding="utf-8")
        (tmp_path / "cu-coverage-report.json").write_text("{}", encoding="utf-8")
        caps = tmp_path / "caps.yaml"
        caps.write_text("schema_version: 1\n", encoding="utf-8")
        from dataclasses import replace

        profile = replace(build_default_profile(endpoint="opc.tcp://x:1"), capabilities_file=str(caps))

        captured_cmd = {}

        class FakeCompleted:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_run(cmd, **kw):
            captured_cmd["cmd"] = cmd
            return FakeCompleted()

        monkeypatch.setattr(tse.subprocess, "run", fake_run)
        tse._generate_excel_report(
            profile, tmp_path, tmp_path / "target-server-cu-report.json", run_result="passed", base_dir=tmp_path
        )
        assert "--capabilities" in captured_cmd["cmd"]


# ---------------------------------------------------------------------------
# _find_venv_python
# ---------------------------------------------------------------------------


class TestFindVenvPython:
    def test_falls_back_to_current_interpreter_when_no_venv(self, tmp_path):
        assert tse._find_venv_python(tmp_path) == sys.executable

    def test_finds_venv_test_python(self, tmp_path):
        scripts_dir = tmp_path / ".venv_test" / ("Scripts" if tse.os.name == "nt" else "bin")
        scripts_dir.mkdir(parents=True)
        py_name = "python.exe" if tse.os.name == "nt" else "python"
        (scripts_dir / py_name).write_text("", encoding="utf-8")
        assert tse._find_venv_python(tmp_path) == str(scripts_dir / py_name)

    def test_finds_venv_posix_and_windows_paths(self, tmp_path):
        original_name = tse.os.name
        try:
            for venv_name in (".venv_test", ".venv"):
                test_dir = tmp_path / venv_name
                for sub, py_name, os_name in [("Scripts", "python.exe", "nt"), ("bin", "python", "posix")]:
                    py_dir = test_dir / sub
                    py_dir.mkdir(parents=True, exist_ok=True)
                    target = py_dir / py_name
                    target.write_text("", encoding="utf-8")
                    tse.os.name = os_name
                    assert tse._find_venv_python(tmp_path) == str(target)
                    target.unlink()
        finally:
            tse.os.name = original_name


# ---------------------------------------------------------------------------
# run_preflight — direct in-process calls
# ---------------------------------------------------------------------------


class TestRunPreflightDirect:
    def test_placeholder_endpoint_is_blocking_and_writes_evidence(self, tmp_path):
        profile = build_default_profile(endpoint="")
        rc = tse.run_preflight(profile, tmp_path)
        assert rc == 1
        assert (tmp_path / "target-server-cu-report.json").exists()
        assert (tmp_path / "target-server-cu-summary.txt").exists()
        report = json.loads((tmp_path / "target-server-cu-report.json").read_text(encoding="utf-8"))
        assert report["mode"] == "preflight_only"

    def test_all_checks_pass_returns_zero(self, tmp_path, monkeypatch):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://reachable-host:1"},
                "triggers": {"result": {"mode": "simulate_methods"}},
            }
        )
        monkeypatch.setattr(
            tse,
            "check_endpoint_reachable",
            lambda endpoint, **kw: ReadinessOutcome(outcome=OUTCOME_PASSED, check_name="endpoint_reachable"),
        )
        rc = tse.run_preflight(profile, tmp_path)
        assert rc == 0
        summary = (tmp_path / "target-server-cu-summary.txt").read_text(encoding="utf-8")
        assert "PASSED" in summary

    def test_manual_required_is_non_blocking(self, tmp_path, monkeypatch):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://reachable-host:1"},
                "triggers": {"result": {"mode": "manual_trigger"}},
            }
        )
        monkeypatch.setattr(
            tse,
            "check_endpoint_reachable",
            lambda endpoint, **kw: ReadinessOutcome(outcome=OUTCOME_PASSED, check_name="endpoint_reachable"),
        )
        rc = tse.run_preflight(profile, tmp_path)
        assert rc == 0
        summary = (tmp_path / "target-server-cu-summary.txt").read_text(encoding="utf-8")
        assert "MANUAL" in summary or "manual" in summary


# ---------------------------------------------------------------------------
# run_automated — direct in-process calls
# ---------------------------------------------------------------------------


class TestRunAutomatedDirect:
    def _reachable_profile(self, *, trigger_mode: str = "simulate_methods") -> object:
        return load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://reachable-host:1"},
                "triggers": {"result": {"mode": trigger_mode}},
            }
        )

    def _mock_reachable(self, monkeypatch) -> None:
        monkeypatch.setattr(
            tse,
            "check_endpoint_reachable",
            lambda endpoint, **kw: ReadinessOutcome(outcome=OUTCOME_PASSED, check_name="endpoint_reachable"),
        )

    def test_blocking_endpoint_returns_1_without_spec_tests_key(self, tmp_path):
        profile = build_default_profile(endpoint="")
        rc = tse.run_automated(profile, tmp_path, base_dir=tmp_path)
        assert rc == 1
        report = json.loads((tmp_path / "target-server-cu-report.json").read_text(encoding="utf-8"))
        assert "spec_tests" not in report

    def test_skip_spec_tests_is_classification_only(self, tmp_path, monkeypatch):
        self._mock_reachable(monkeypatch)
        profile = self._reachable_profile()
        rc = tse.run_automated(profile, tmp_path, skip_spec_tests=True, base_dir=tmp_path)
        assert rc == 0
        report = json.loads((tmp_path / "target-server-cu-report.json").read_text(encoding="utf-8"))
        assert "spec_tests" not in report
        assert "cu_classification" in report

    def test_missing_spec_dir_is_skipped_not_a_failure(self, tmp_path, monkeypatch):
        self._mock_reachable(monkeypatch)
        profile = self._reachable_profile()
        # base_dir has no specification_tests/ directory -> run_live_spec_tests skips
        rc = tse.run_automated(profile, tmp_path, base_dir=tmp_path)
        assert rc == 0
        report = json.loads((tmp_path / "target-server-cu-report.json").read_text(encoding="utf-8"))
        assert report["spec_tests"]["status"] == "skipped"
        assert report["spec_tests"]["reason"] == "spec_dir_not_found"

    def test_manual_checks_automated_mode_warns_and_continues(self, tmp_path, monkeypatch, capsys):
        self._mock_reachable(monkeypatch)
        profile = self._reachable_profile(trigger_mode="manual_trigger")
        rc = tse.run_automated(profile, tmp_path, mode="automated", base_dir=tmp_path)
        assert rc == 0
        assert "manual action" in capsys.readouterr().out.lower()

    def test_guided_mode_interactive_prompt_confirmed(self, tmp_path, monkeypatch):
        self._mock_reachable(monkeypatch)
        profile = self._reachable_profile(trigger_mode="manual_trigger")
        monkeypatch.setattr("builtins.input", lambda *_: "")
        rc = tse.run_automated(profile, tmp_path, mode="guided", interactive_prompts=True, base_dir=tmp_path)
        assert rc == 0

    def test_guided_mode_interactive_prompt_interrupted(self, tmp_path, monkeypatch):
        self._mock_reachable(monkeypatch)
        profile = self._reachable_profile(trigger_mode="manual_trigger")

        def _raise_eof(*_a, **_kw):
            raise EOFError

        monkeypatch.setattr("builtins.input", _raise_eof)
        rc = tse.run_automated(profile, tmp_path, mode="guided", interactive_prompts=True, base_dir=tmp_path)
        assert rc == 1

    def test_completed_spec_run_generates_excel_report(self, tmp_path, monkeypatch):
        self._mock_reachable(monkeypatch)
        profile = self._reachable_profile()

        def fake_run_live_spec_tests(profile, output_dir, **kwargs):
            (output_dir / "spec-tests.xml").write_text("<xml/>", encoding="utf-8")
            (output_dir / "cu-coverage-report.json").write_text("{}", encoding="utf-8")
            return 0, {"status": "completed", "outcome": "passed", "exit_code": 0}

        monkeypatch.setattr(tse, "run_live_spec_tests", fake_run_live_spec_tests)
        monkeypatch.setattr(
            tse,
            "_generate_excel_report",
            lambda *a, **kw: {"status": "generated", "reason": "", "path": str(tmp_path / "report-controller.xlsx")},
        )
        rc = tse.run_automated(profile, tmp_path, base_dir=tmp_path)
        assert rc == 0
        report = json.loads((tmp_path / "target-server-cu-report.json").read_text(encoding="utf-8"))
        assert report["excel_report"]["status"] == "generated"

    def test_completed_spec_run_with_failing_excel_report_fails_the_run(self, tmp_path, monkeypatch):
        self._mock_reachable(monkeypatch)
        profile = self._reachable_profile()

        def fake_run_live_spec_tests(profile, output_dir, **kwargs):
            (output_dir / "spec-tests.xml").write_text("<xml/>", encoding="utf-8")
            (output_dir / "cu-coverage-report.json").write_text("{}", encoding="utf-8")
            return 0, {"status": "completed", "outcome": "passed", "exit_code": 0}

        monkeypatch.setattr(tse, "run_live_spec_tests", fake_run_live_spec_tests)
        monkeypatch.setattr(
            tse,
            "_generate_excel_report",
            lambda *a, **kw: {"status": "failed", "reason": "generator crashed", "path": None},
        )
        rc = tse.run_automated(profile, tmp_path, base_dir=tmp_path)
        assert rc == 1

    def test_failed_spec_run_fails_the_overall_run(self, tmp_path, monkeypatch):
        self._mock_reachable(monkeypatch)
        profile = self._reachable_profile()

        def fake_run_live_spec_tests(profile, output_dir, **kwargs):
            return 1, {"status": "completed", "outcome": "failed", "exit_code": 1}

        monkeypatch.setattr(tse, "run_live_spec_tests", fake_run_live_spec_tests)
        rc = tse.run_automated(profile, tmp_path, base_dir=tmp_path)
        assert rc == 1

    def test_automated_run_without_endpoint_logs_classification_only(self, tmp_path, monkeypatch):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": ""},
            }
        )
        report = tse.PreflightReport()
        report.add(tse.ReadinessOutcome(outcome="passed", check_name="mock"))
        monkeypatch.setattr(tse, "run_config_preflight", lambda *a, **kw: report)
        monkeypatch.setattr(
            tse, "check_endpoint_reachable", lambda *a, **kw: tse.ReadinessOutcome(outcome="passed", check_name="tcp")
        )
        rc = tse.run_automated(profile, tmp_path, base_dir=tmp_path, skip_spec_tests=False)
        assert rc == 0


# ---------------------------------------------------------------------------
# run_live_spec_tests — direct exception & timeout coverage
# ---------------------------------------------------------------------------


class TestRunLiveSpecTestsDirectExceptions:
    def test_timeout_expired_sets_timeout_metadata(self, tmp_path, monkeypatch):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://reachable-host:1"},
            }
        )
        spec_dir = tmp_path / "specification_tests"
        spec_dir.mkdir(parents=True, exist_ok=True)

        def _raise_timeout(*_a, **_kw):
            raise tse.subprocess.TimeoutExpired(cmd=["pytest"], timeout=10)

        monkeypatch.setattr(tse.subprocess, "run", _raise_timeout)
        rc, meta = tse.run_live_spec_tests(profile, tmp_path, base_dir=tmp_path)
        assert rc == 1
        assert meta["status"] == "timeout"
        assert meta["outcome"] == "failed"

    def test_generic_exception_sets_error_metadata(self, tmp_path, monkeypatch):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://reachable-host:1"},
            }
        )
        spec_dir = tmp_path / "specification_tests"
        spec_dir.mkdir(parents=True, exist_ok=True)

        def _raise_runtime_error(*_a, **_kw):
            raise RuntimeError("Subprocess execution blocked by host policy")

        monkeypatch.setattr(tse.subprocess, "run", _raise_runtime_error)
        rc, meta = tse.run_live_spec_tests(profile, tmp_path, base_dir=tmp_path)
        assert rc == 1
        assert meta["status"] == "error"
        assert meta["outcome"] == "failed"
        assert "Subprocess execution blocked" in meta["error"]

    def test_empty_endpoint_skipped(self, tmp_path):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": ""},
            }
        )
        rc, meta = tse.run_live_spec_tests(profile, tmp_path, base_dir=tmp_path)
        assert rc == 0
        assert meta["status"] == "skipped"
        assert meta["reason"] == "endpoint_not_configured"

    def test_normal_subprocess_run_completed(self, tmp_path, monkeypatch):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://reachable:40451"},
            }
        )
        spec_dir = tmp_path / "specification_tests"
        spec_dir.mkdir(parents=True, exist_ok=True)

        class MockResult:
            returncode = 0

        monkeypatch.setattr(tse.subprocess, "run", lambda *a, **kw: MockResult())
        rc, meta = tse.run_live_spec_tests(profile, tmp_path, base_dir=tmp_path)
        assert rc == 0
        assert meta["status"] == "completed"
        assert meta["outcome"] == "passed"

    def test_apply_runtime_overrides_per_classification(self):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "selection": {
                    "joining_process": {"joining_process_id": "Default_1"},
                    "joining_processes": {
                        "job": {"joining_process_id": "Old_Job"},
                    },
                },
            }
        )
        updated = tse.apply_runtime_overrides(
            profile,
            job_joining_process_id="New_Job_1",
            batch_joining_process_id="New_Batch_1",
        )
        assert updated.selection.joining_processes["job"].joining_process_id == "New_Job_1"
        assert updated.selection.joining_processes["batch"].joining_process_id == "New_Batch_1"

    def test_excluded_cus_with_configured_classifications(self):
        excluded = tse._excluded_cus_for_result_scope(
            "single",
            configured_classifications=("job",),
        )
        assert "job_result" not in excluded

    def test_build_spec_test_env_exports_per_classification_ids(self, tmp_path):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://localhost:40451"},
                "selection": {
                    "joining_processes": {
                        "job": {"joining_process_id": "Job_123", "joining_process_origin_id": "Job_Orig_123"},
                        "batch": {"joining_process_id": "Batch_456"},
                    }
                },
            }
        )
        env = tse._build_spec_test_env(profile, base_dir=tmp_path)
        assert env.get("OPCUA_JOB_JOINING_PROCESS_ID") == "Job_123"
        assert env.get("OPCUA_JOB_JOINING_PROCESS_ORIGIN_ID") == "Job_Orig_123"
        assert env.get("OPCUA_BATCH_JOINING_PROCESS_ID") == "Batch_456"

    def test_write_markdown_summary_generates_file_and_content(self, tmp_path):
        profile = load_target_server_profile_from_dict(
            {
                "schema_version": 1,
                "profile_name": "Test Profile",
                "target": {"endpoint": "opc.tcp://localhost:40451"},
            }
        )
        report = PreflightReport(endpoint=profile.target.endpoint)
        report.add(ReadinessOutcome(outcome=OUTCOME_PASSED, check_name="TCP_PORT", detail="Port reachable"))
        md_path = tse._write_markdown_summary(
            tmp_path,
            profile,
            report,
            mode="automated",
            run_start="2026-08-31T12:00:00Z",
            outcome_summary="SPEC_TESTS_PASSED",
            extra={
                "cu_classification": {"structure": 10, "method": 5},
                "spec_tests": {
                    "status": "completed",
                    "outcome": "passed",
                    "exit_code": 0,
                    "elapsed_seconds": 12.5,
                    "junit_xml": "spec-tests.xml",
                },
                "excel_report": {"status": "generated", "path": "report.xlsx"},
            },
        )
        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")
        assert "# Target Server Conformance Unit Run Summary" in content
        assert "🟢 **PASSED**" in content
        assert "| `TCP_PORT` | ✅ `passed` | Port reachable |" in content
        assert "| `structure` | 10 |" in content
        assert "spec-tests.xml" in content
        assert "report.xlsx" in content

    @pytest.mark.asyncio
    async def test_async_discover_target_server_full_flow(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.load_data_type_definitions = AsyncMock()
        mock_client.get_namespace_index = AsyncMock(side_effect=lambda uri: 2 if "IJT" in uri else 1)

        mock_js = MagicMock()
        mock_jpm = MagicMock()
        mock_gjpl = MagicMock()
        mock_gjpl.nodeid = "node:gjpl"

        mock_proc_single = MagicMock(
            JoiningProcessId="Prog_1",
            JoiningProcessOriginId="Prog_Orig_1",
            Name="Program1",
            Classification=1,
            AssociatedEntities=[MagicMock(Name="SelectionName", EntityId="ProgIndex_1")],
        )
        mock_proc_job = MagicMock(
            JoiningProcessId="Job_1",
            JoiningProcessOriginId="Job_Orig_1",
            Name="Sequence1",
            Classification=5,
            AssociatedEntities=[MagicMock(Name="SelectionName", EntityId="SeqIndex_1")],
        )
        mock_proc_batch = MagicMock(
            JoiningProcessId="Batch_1",
            JoiningProcessOriginId="Batch_Orig_1",
            Name="Batch1",
            Classification=2,
            AssociatedEntities=[MagicMock(Name="SelectionName", EntityId="BatchIndex_1")],
        )
        mock_jpm.call_method = AsyncMock(return_value=[[mock_proc_single, mock_proc_job, mock_proc_batch]])

        with (
            patch("asyncua.Client", return_value=mock_client),
            patch("helpers.node_discovery.find_joining_system", new=AsyncMock(return_value=mock_js)),
            patch("helpers.node_discovery.read_tool_product_instance_uri", new=AsyncMock(return_value="uri:tool1")),
            patch("helpers.node_discovery.find_child_by_browse_name", new=AsyncMock(side_effect=[mock_jpm, mock_gjpl])),
        ):
            data = await tse.async_discover_target_server("opc.tcp://localhost:40451")

        assert data["endpoint"] == "opc.tcp://localhost:40451"
        assert len(data["tools"]) == 1
        assert data["tools"][0]["product_instance_uri"] == "uri:tool1"
        assert len(data["processes"]) == 3
        assert "Prog_1" in data["suggested_yaml"]
        assert "Job_1" in data["suggested_yaml"]

    @pytest.mark.asyncio
    async def test_async_discover_target_server_no_joining_system(self):
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.load_data_type_definitions = AsyncMock()
        mock_client.get_namespace_index = AsyncMock(return_value=2)

        with (
            patch("asyncua.Client", return_value=mock_client),
            patch("helpers.node_discovery.find_joining_system", new=AsyncMock(return_value=None)),
        ):
            data = await tse.async_discover_target_server("opc.tcp://localhost:40451")

        assert "error" in data
        assert "JoiningSystem node not found" in data["error"]

    def test_run_discover_target_success(self, monkeypatch):
        async def fake_discover(endpoint, timeout=15.0):
            return {
                "endpoint": endpoint,
                "tools": [{"name": "Tool1", "product_instance_uri": "uri:test"}],
                "processes": [
                    {
                        "id": "P1",
                        "origin_id": "O1",
                        "name": "Program1",
                        "selection_name": "ProgIndex_1",
                        "classification": 1,
                    }
                ],
                "suggested_yaml": "selection:\n  tool:\n    policy: first_ready",
            }

        monkeypatch.setattr(tse, "async_discover_target_server", fake_discover)
        rc = tse.run_discover_target("opc.tcp://localhost:40451")
        assert rc == 0

    def test_run_discover_target_error_in_data(self, monkeypatch):
        async def fake_discover(endpoint, timeout=15.0):
            return {"endpoint": endpoint, "error": "Connection refused"}

        monkeypatch.setattr(tse, "async_discover_target_server", fake_discover)
        rc = tse.run_discover_target("opc.tcp://localhost:40451")
        assert rc == 1

    def test_run_discover_target_exception(self, monkeypatch):
        async def fake_discover(endpoint, timeout=15.0):
            raise RuntimeError("Network down")

        monkeypatch.setattr(tse, "async_discover_target_server", fake_discover)
        rc = tse.run_discover_target("opc.tcp://localhost:40451")
        assert rc == 1
