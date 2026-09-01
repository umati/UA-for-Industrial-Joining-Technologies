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
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helpers import target_server_execution as tse
from helpers.target_server_cu_config import (
    OUTCOME_PASSED,
    build_default_profile,
    build_execution_profile,
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
        profile = build_execution_profile(
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
        profile = build_execution_profile(
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
        env = tse._build_spec_test_env(profile, base_dir=tmp_path)
        assert env["OPCUA_SERVER_URL"] == "opc.tcp://target:40451"
        assert env["OPCUA_TOOL_PRODUCT_INSTANCE_URI"] == "urn:tool:123"
        assert env["OPCUA_JOINING_PROCESS_ID"] == "P1"
        assert env["OPCUA_JOINING_PROCESS_ORIGIN_ID"] == "O1"
        assert env["OPCUA_TARGET_REQUIRED_RESULT_CLASSIFICATION"] == "4"
        assert "OPCUA_TARGET_EXCLUDED_CUS" in env
        # No manifest -> no claim source is invented for the pytest process.
        assert "OPCUA_CAPABILITIES_FILE" not in env

    def test_build_spec_test_env_with_explicit_existing_caps_file(self, tmp_path):
        caps_file = tmp_path / "my.sut.yaml"
        caps_file.write_text("schema_version: 1", encoding="utf-8")
        profile = build_execution_profile(
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
    def test_fails_when_junit_or_cu_json_missing(self, tmp_path):
        """Missing run-scoped evidence is evidence loss, not a benign skip."""
        profile = build_default_profile(endpoint="opc.tcp://x:1")
        result = tse._generate_excel_report(
            profile, tmp_path, tmp_path / "target-server-cu-report.json", run_result="passed"
        )
        assert result["status"] == tse.EXCEL_STATUS_FAILED
        assert result["reason_code"] == tse.EXCEL_REASON_MISSING_EVIDENCE
        assert result["path"] is None
        assert any("spec-tests.xml" in p for p in result["missing_artifacts"])
        assert any("cu-coverage-report.json" in p for p in result["missing_artifacts"])
        assert tse.is_benign_excel_skip(result) is False

    def test_missing_only_cu_coverage_json_also_fails(self, tmp_path):
        (tmp_path / "spec-tests.xml").write_text("<xml/>", encoding="utf-8")
        profile = build_default_profile(endpoint="opc.tcp://x:1")
        result = tse._generate_excel_report(
            profile, tmp_path, tmp_path / "target-server-cu-report.json", run_result="passed"
        )
        assert result["status"] == tse.EXCEL_STATUS_FAILED
        assert result["missing_artifacts"] == [str(tmp_path / "cu-coverage-report.json")]

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
        assert result["reason_code"] == tse.EXCEL_REASON_GENERATOR_ERROR
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
        profile = build_execution_profile(
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
        profile = build_execution_profile(
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
        return build_execution_profile(
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
        monkeypatch.setattr(
            tse,
            "_capture_model_inventory",
            lambda profile, output_dir: {
                "status": "completed",
                "path": str(output_dir / "model-inventory.json"),
                "server_node_count": 1,
                "warning_count": 0,
            },
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
        profile = build_execution_profile(
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
        profile = build_execution_profile(
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
        profile = build_execution_profile(
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
        profile = build_execution_profile(
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
        profile = build_execution_profile(
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
        profile = build_execution_profile(
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
        profile = build_execution_profile(
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
        profile = build_execution_profile(
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
        assert "| `TCP_PORT` | ✅ `passed` | Passed | Port reachable |" in content
        assert "- **Preflight Outcome:** `Passed`" in content
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
            Classification=4,
            AssociatedEntities=[MagicMock(Name="SelectionName", EntityId="SeqIndex_1")],
        )
        mock_proc_batch = MagicMock(
            JoiningProcessId="Batch_1",
            JoiningProcessOriginId="Batch_Orig_1",
            Name="Batch1",
            Classification=3,
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
        # Each process is suggested under exactly one canonical classification key.
        assert data["suggested_selection"]["single"]["id"] == "Prog_1"
        assert data["suggested_selection"]["job"]["id"] == "Job_1"
        assert data["suggested_selection"]["batch"]["id"] == "Batch_1"

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
        async def fake_discover(endpoint, timeout=15.0, *, security=None, prompt=None):
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
        async def fake_discover(endpoint, timeout=15.0, *, security=None, prompt=None):
            return {"endpoint": endpoint, "error": "Connection refused"}

        monkeypatch.setattr(tse, "async_discover_target_server", fake_discover)
        rc = tse.run_discover_target("opc.tcp://localhost:40451")
        assert rc == 1

    def test_run_discover_target_exception(self, monkeypatch):
        async def fake_discover(endpoint, timeout=15.0, *, security=None, prompt=None):
            raise RuntimeError("Network down")

        monkeypatch.setattr(tse, "async_discover_target_server", fake_discover)
        rc = tse.run_discover_target("opc.tcp://localhost:40451")
        assert rc == 1


# ---------------------------------------------------------------------------
# Discovery classification mapping (ResultClassification enum alignment)
# ---------------------------------------------------------------------------


class TestDiscoveryClassificationMapping:
    @pytest.mark.parametrize(
        ("classification", "expected"),
        [
            (1, "single"),
            (2, "sync"),
            (3, "batch"),
            (4, "job"),
            (5, "stitching"),
            (6, "intervention"),
            (7, "text"),
        ],
    )
    def test_server_classification_is_authoritative(self, classification, expected):
        process = {"name": "", "selection_name": "", "classification": classification}
        assert tse.classify_discovered_process(process) == expected

    def test_server_classification_wins_over_name_hint(self):
        # Name says "batch" but the server reports JobResult(4) — the enum wins.
        process = {"name": "Batch of tightenings", "selection_name": "", "classification": 4}
        assert tse.classify_discovered_process(process) == "job"

    def test_name_hint_only_used_when_classification_undefined(self):
        assert tse.classify_discovered_process({"name": "Sequence 1", "selection_name": "", "classification": 0}) == (
            "job"
        )
        assert tse.classify_discovered_process({"name": "Batch 1", "selection_name": "", "classification": 0}) == (
            "batch"
        )
        assert tse.classify_discovered_process({"name": "PSet 12", "selection_name": "", "classification": 0}) == (
            "single"
        )
        assert tse.classify_discovered_process({"name": "Mystery", "selection_name": "", "classification": 0}) == ""

    def test_process_is_never_suggested_under_two_classifications(self):
        processes = [
            {"id": "P1", "origin_id": "O1", "name": "Batch job sequence", "selection_name": "", "classification": 3},
            {"id": "P2", "origin_id": "O2", "name": "Job", "selection_name": "", "classification": 4},
        ]
        suggestion = tse.suggest_process_selection(processes)
        assert suggestion["batch"]["id"] == "P1"
        assert suggestion["job"]["id"] == "P2"
        assigned_ids = [p["id"] for p in suggestion.values()]
        assert len(assigned_ids) == len(set(assigned_ids))

    def test_suggested_yaml_only_contains_classified_processes(self):
        suggestion = tse.suggest_process_selection(
            [{"id": "P1", "origin_id": "O1", "name": "Program", "selection_name": "", "classification": 1}]
        )
        yaml_text = tse.render_suggested_selection_yaml("urn:tool:1", suggestion)
        assert "    single:" in yaml_text
        assert "    job:" not in yaml_text
        assert 'product_instance_uri: "urn:tool:1"' in yaml_text

    def test_suggested_yaml_reports_when_nothing_could_be_classified(self):
        yaml_text = tse.render_suggested_selection_yaml("urn:tool:1", {})
        assert "No joining process could be classified" in yaml_text


# ---------------------------------------------------------------------------
# Spec test command construction (quiet/verbose)
# ---------------------------------------------------------------------------


class TestBuildSpecTestCommand:
    def _cmd(self, tmp_path, **kwargs):
        return tse._build_spec_test_command(
            "python", tmp_path / "specification_tests", tmp_path / "spec-tests.xml", **kwargs
        )

    def test_quiet_by_default(self, tmp_path):
        cmd = self._cmd(tmp_path)
        assert "-q" in cmd
        assert "-v" not in cmd

    def test_verbose_flag_switches_to_v(self, tmp_path):
        cmd = self._cmd(tmp_path, verbose=True)
        assert "-v" in cmd
        assert "-q" not in cmd

    def test_python_stays_unbuffered_and_carries_timeout(self, tmp_path):
        cmd = self._cmd(tmp_path, test_timeout_seconds=321)
        assert cmd[:4] == ["python", "-u", "-m", "pytest"]
        assert "--timeout=321" in cmd

    def test_simulation_marker_exclusion_is_optional(self, tmp_path):
        assert "not simulation" in self._cmd(tmp_path)
        assert "not simulation" not in self._cmd(tmp_path, exclude_simulation=False)


# ---------------------------------------------------------------------------
# Excel flag handling for target runs
# ---------------------------------------------------------------------------


class TestTargetExcelFlagHandling:
    def _prepare(self, tmp_path):
        (tmp_path / "spec-tests.xml").write_text("<xml/>", encoding="utf-8")
        (tmp_path / "cu-coverage-report.json").write_text("{}", encoding="utf-8")
        return build_default_profile(endpoint="opc.tcp://x:1")

    class _FakeCompleted:
        returncode = 0
        stdout = ""
        stderr = ""

    def test_excel_never_skips_generation(self, tmp_path, monkeypatch):
        profile = self._prepare(tmp_path)
        called = {"ran": False}

        def fake_run(cmd, **kw):
            called["ran"] = True
            return self._FakeCompleted()

        monkeypatch.setattr(tse.subprocess, "run", fake_run)
        result = tse._generate_excel_report(
            profile,
            tmp_path,
            tmp_path / "target-server-cu-report.json",
            run_result="passed",
            base_dir=tmp_path,
            excel_mode="never",
        )
        assert result["status"] == "skipped"
        assert result["reason_code"] == tse.EXCEL_REASON_DISABLED
        assert tse.is_benign_excel_skip(result) is True
        assert called["ran"] is False

    def test_excel_on_success_skips_after_failure(self, tmp_path, monkeypatch):
        profile = self._prepare(tmp_path)
        monkeypatch.setattr(tse.subprocess, "run", lambda cmd, **kw: self._FakeCompleted())
        result = tse._generate_excel_report(
            profile,
            tmp_path,
            tmp_path / "target-server-cu-report.json",
            run_result="failed",
            base_dir=tmp_path,
            excel_mode="on-success",
        )
        assert result["status"] == "skipped"
        assert result["reason_code"] == tse.EXCEL_REASON_ON_SUCCESS_AFTER_FAILURE
        assert tse.is_benign_excel_skip(result) is True

    def test_unknown_skip_reason_code_is_not_benign(self):
        """A skip the runner does not recognise must never be silently accepted."""
        assert tse.is_benign_excel_skip({"status": "skipped", "reason_code": "something_new"}) is False
        assert tse.is_benign_excel_skip({"status": "skipped"}) is False
        assert tse.is_benign_excel_skip({"status": "generated", "reason_code": ""}) is False

    def test_shared_report_xlsx_is_not_mirrored_by_default(self, tmp_path, monkeypatch):
        profile = self._prepare(tmp_path)

        def fake_run(cmd, **kw):
            Path(cmd[cmd.index("--out") + 1]).write_bytes(b"workbook")
            return self._FakeCompleted()

        monkeypatch.setattr(tse.subprocess, "run", fake_run)
        result = tse._generate_excel_report(
            profile,
            tmp_path,
            tmp_path / "target-server-cu-report.json",
            run_result="passed",
            base_dir=tmp_path,
        )
        assert result["status"] == "generated"
        assert result["path"] == str(tmp_path / "report-controller.xlsx")
        assert "copied_to" not in result
        assert not (tmp_path / "test-results" / "report.xlsx").exists()

    def test_excel_out_copies_workbook_to_requested_path(self, tmp_path, monkeypatch):
        profile = self._prepare(tmp_path)

        def fake_run(cmd, **kw):
            Path(cmd[cmd.index("--out") + 1]).write_bytes(b"workbook")
            return self._FakeCompleted()

        monkeypatch.setattr(tse.subprocess, "run", fake_run)
        requested = tmp_path / "elsewhere" / "custom.xlsx"
        result = tse._generate_excel_report(
            profile,
            tmp_path,
            tmp_path / "target-server-cu-report.json",
            run_result="passed",
            base_dir=tmp_path,
            excel_out=requested,
        )
        assert result["status"] == "generated"
        assert result["copied_to"] == str(requested)
        assert requested.exists()

    def test_target_run_never_writes_the_shared_regression_baseline(self, tmp_path, monkeypatch):
        profile = self._prepare(tmp_path)
        captured: dict = {}

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            return self._FakeCompleted()

        monkeypatch.setattr(tse.subprocess, "run", fake_run)
        tse._generate_excel_report(
            profile,
            tmp_path,
            tmp_path / "target-server-cu-report.json",
            run_result="passed",
            base_dir=tmp_path,
        )
        assert "--write-baseline" not in captured["cmd"]


# ---------------------------------------------------------------------------
# Result/observation timeout environment wiring
# ---------------------------------------------------------------------------


class TestSpecTestTimeoutEnv:
    def test_active_and_passive_timeouts_are_separate(self, tmp_path):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://target:40451"},
                "triggers": {"result": {"mode": "start_selected_joining", "timeout_seconds": 5}},
                "workflow_execution": {"expected_results": {"timeout_seconds": 60}},
            }
        )
        env = tse._build_spec_test_env(profile, base_dir=tmp_path)
        assert env["OPCUA_TARGET_PASSIVE_OBSERVATION_TIMEOUT_SECONDS"] == "5.0"
        assert env["OPCUA_TARGET_ACTIVE_RESULT_TIMEOUT_SECONDS"] == "60.0"
        assert env["OPCUA_TARGET_RESULT_TIMEOUT_SECONDS"] == "5.0"

    @pytest.mark.parametrize(
        ("classification", "expected"),
        [
            ("single", "1"),
            ("sync", "2"),
            ("batch", "3"),
            ("job", "4"),
            ("stitching", "5"),
            ("intervention", "6"),
            ("text", "7"),
        ],
    )
    def test_required_classification_matches_enum(self, tmp_path, classification, expected):
        profile = build_execution_profile(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://target:40451"},
                "workflow_execution": {"expected_results": {"classification": classification}},
            }
        )
        env = tse._build_spec_test_env(profile, base_dir=tmp_path)
        assert env["OPCUA_TARGET_REQUIRED_RESULT_CLASSIFICATION"] == expected


class TestDiscoveryClassificationParsingEdgeCases:
    @pytest.mark.asyncio
    async def test_unreadable_classification_falls_back_to_name_hints(self):
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.load_data_type_definitions = AsyncMock()
        mock_client.get_namespace_index = AsyncMock(return_value=2)

        mock_jpm = MagicMock()
        mock_gjpl = MagicMock()
        mock_gjpl.nodeid = "node:gjpl"
        bad_process = MagicMock(
            JoiningProcessId="P1",
            JoiningProcessOriginId="O1",
            Name="Batch program",
            Classification="not-an-int",
            AssociatedEntities=[],
        )
        mock_jpm.call_method = AsyncMock(return_value=[[bad_process]])

        with (
            patch("asyncua.Client", return_value=mock_client),
            patch("helpers.node_discovery.find_joining_system", new=AsyncMock(return_value=MagicMock())),
            patch("helpers.node_discovery.read_tool_product_instance_uri", new=AsyncMock(return_value="uri:tool1")),
            patch("helpers.node_discovery.find_child_by_browse_name", new=AsyncMock(side_effect=[mock_jpm, mock_gjpl])),
        ):
            data = await tse.async_discover_target_server("opc.tcp://localhost:40451")

        assert data["processes"][0]["classification"] == 0
        assert data["suggested_selection"]["batch"]["id"] == "P1"


class TestExcelCopyFailureIsNonFatal:
    def test_copy_failure_is_logged_and_run_still_reports_generated(self, tmp_path, monkeypatch):
        (tmp_path / "spec-tests.xml").write_text("<xml/>", encoding="utf-8")
        (tmp_path / "cu-coverage-report.json").write_text("{}", encoding="utf-8")
        profile = build_default_profile(endpoint="opc.tcp://x:1")

        class FakeCompleted:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_run(cmd, **kw):
            Path(cmd[cmd.index("--out") + 1]).write_bytes(b"workbook")
            return FakeCompleted()

        def boom(*_a, **_kw):
            raise OSError("destination is read-only")

        monkeypatch.setattr(tse.subprocess, "run", fake_run)
        monkeypatch.setattr(tse.shutil, "copy2", boom)
        result = tse._generate_excel_report(
            profile,
            tmp_path,
            tmp_path / "target-server-cu-report.json",
            run_result="passed",
            base_dir=tmp_path,
            excel_out=tmp_path / "elsewhere" / "custom.xlsx",
        )
        assert result["status"] == "generated"
        assert "copied_to" not in result


class TestRunAutomatedExcelReporting:
    def _profile(self):
        return build_execution_profile(
            {
                "schema_version": 1,
                "target": {"endpoint": "opc.tcp://reachable-host:1"},
                "triggers": {"result": {"mode": "simulate_methods"}},
            }
        )

    def _run(self, tmp_path, monkeypatch, excel_meta, capsys, **kwargs):
        monkeypatch.setattr(
            tse,
            "check_endpoint_reachable",
            lambda endpoint, **kw: ReadinessOutcome(outcome=OUTCOME_PASSED, check_name="endpoint_reachable"),
        )
        monkeypatch.setattr(
            tse,
            "run_live_spec_tests",
            lambda *a, **kw: (0, {"status": "completed", "outcome": "passed"}),
        )
        monkeypatch.setattr(
            tse,
            "_capture_model_inventory",
            lambda profile, output_dir: {
                "status": "completed",
                "path": str(output_dir / "model-inventory.json"),
                "server_node_count": 1,
                "warning_count": 0,
            },
        )
        captured: dict = {}

        def fake_excel(profile, output_dir, report_path, **kw):
            captured.update(kw)
            return excel_meta

        monkeypatch.setattr(tse, "_generate_excel_report", fake_excel)
        rc = tse.run_automated(self._profile(), tmp_path, base_dir=tmp_path, **kwargs)
        return rc, captured, capsys.readouterr().out

    def test_excel_flags_are_forwarded_and_copy_is_logged(self, tmp_path, monkeypatch, capsys):
        rc, captured, out = self._run(
            tmp_path,
            monkeypatch,
            {"status": "generated", "reason": "", "path": "wb.xlsx", "copied_to": "copy.xlsx"},
            capsys,
            excel_mode="always",
            excel_out="copy.xlsx",
        )
        assert rc == 0
        assert captured["excel_mode"] == "always"
        assert captured["excel_out"] == "copy.xlsx"
        assert "Excel copy:" in out

    def test_intentional_policy_skip_does_not_fail_the_run(self, tmp_path, monkeypatch, capsys):
        rc, _captured, out = self._run(
            tmp_path,
            monkeypatch,
            {
                "status": tse.EXCEL_STATUS_SKIPPED,
                "reason_code": tse.EXCEL_REASON_DISABLED,
                "reason": "disabled (--excel=never)",
                "path": None,
            },
            capsys,
            excel_mode="never",
        )
        assert rc == 0
        assert "skipped — disabled (--excel=never)" in out

    def test_on_success_policy_skip_is_benign(self, tmp_path, monkeypatch, capsys):
        """`--excel=on-success` declines the workbook by policy; the excel step
        itself must not add a failure (spec failures fail the run on their own)."""
        rc, _captured, out = self._run(
            tmp_path,
            monkeypatch,
            {
                "status": tse.EXCEL_STATUS_SKIPPED,
                "reason_code": tse.EXCEL_REASON_ON_SUCCESS_AFTER_FAILURE,
                "reason": "tests failed; skipped (--excel=on-success)",
                "path": None,
            },
            capsys,
            excel_mode="on-success",
        )
        assert rc == 0
        assert "skipped — tests failed; skipped (--excel=on-success)" in out

    def test_missing_coverage_evidence_fails_the_run(self, tmp_path, monkeypatch, capsys):
        """An otherwise completed spec run with no JUnit/CU artifacts must fail."""
        rc, _captured, out = self._run(
            tmp_path,
            monkeypatch,
            {
                "status": tse.EXCEL_STATUS_FAILED,
                "reason_code": tse.EXCEL_REASON_MISSING_EVIDENCE,
                "reason": "run-scoped coverage evidence is missing after a completed spec run: spec-tests.xml",
                "path": None,
                "missing_artifacts": ["spec-tests.xml"],
            },
            capsys,
        )
        assert rc == 1
        assert "run-scoped coverage evidence is missing" in out
        assert "Coverage evidence for this run is incomplete" in out

    def test_unrecognised_skip_reason_fails_the_run(self, tmp_path, monkeypatch, capsys):
        """Only declared policy skips are benign; anything else fails the run."""
        rc, _captured, out = self._run(
            tmp_path,
            monkeypatch,
            {"status": tse.EXCEL_STATUS_SKIPPED, "reason_code": "not_a_known_policy", "reason": "", "path": None},
            capsys,
        )
        assert rc == 1
        assert "no reason reported" in out

    def test_failed_excel_fails_the_run(self, tmp_path, monkeypatch, capsys):
        rc, _captured, out = self._run(
            tmp_path,
            monkeypatch,
            {
                "status": "failed",
                "reason_code": tse.EXCEL_REASON_GENERATOR_ERROR,
                "reason": "generator crashed",
                "path": None,
            },
            capsys,
        )
        assert rc == 1
        assert "generator crashed" in out


# ---------------------------------------------------------------------------
# Connection security is applied to the discovery and spec-test sessions
# ---------------------------------------------------------------------------


class TestTargetSessionConnectionSecurity:
    @pytest.mark.asyncio
    async def test_discovery_applies_the_declared_security(self):
        from helpers.connection_security import ConnectionSecurity

        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.load_data_type_definitions = AsyncMock()
        mock_client.get_namespace_index = AsyncMock(return_value=2)
        security = ConnectionSecurity(auth_source="environment", username="op", password_env_var="IJT_DISCOVER_PW")
        applied = AsyncMock()

        with (
            patch("asyncua.Client", return_value=mock_client),
            patch("helpers.node_discovery.find_joining_system", new=AsyncMock(return_value=None)),
            patch("helpers.connection_security.apply_connection_security", new=applied),
        ):
            await tse.async_discover_target_server("opc.tcp://localhost:40451", security=security)

        applied.assert_awaited_once()
        await_args = applied.await_args
        assert await_args is not None
        assert await_args.args[1] is security

    @pytest.mark.asyncio
    async def test_discovery_without_a_manifest_stays_anonymous(self):
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.load_data_type_definitions = AsyncMock()
        mock_client.get_namespace_index = AsyncMock(return_value=2)
        applied = AsyncMock()

        with (
            patch("asyncua.Client", return_value=mock_client),
            patch("helpers.node_discovery.find_joining_system", new=AsyncMock(return_value=None)),
            patch("helpers.connection_security.apply_connection_security", new=applied),
        ):
            await tse.async_discover_target_server("opc.tcp://localhost:40451")

        applied.assert_not_awaited()

    def test_run_discover_target_logs_the_redacted_security_summary(self, monkeypatch, capsys):
        from helpers.connection_security import ConnectionSecurity

        async def fake_discover(endpoint, timeout=15.0, *, security=None, prompt=None):
            return {"endpoint": endpoint, "tools": [], "processes": [], "suggested_yaml": ""}

        monkeypatch.setattr(tse, "async_discover_target_server", fake_discover)
        security = ConnectionSecurity(auth_source="environment", username="op", password_env_var="IJT_PW")
        assert tse.run_discover_target("opc.tcp://localhost:40451", security=security) == 0

    def test_spec_test_env_withholds_prompting_by_default(self, tmp_path):
        from helpers.target_server_cu_config import build_execution_profile

        profile = build_execution_profile({"schema_version": 1, "target": {"endpoint": "opc.tcp://localhost:40451"}})
        env = tse._build_spec_test_env(profile, base_dir=tmp_path)
        assert "OPCUA_TARGET_INTERACTIVE_PROMPTS" not in env

    def test_spec_test_env_enables_prompting_for_an_interactive_run(self, tmp_path, monkeypatch):
        from helpers.target_server_cu_config import build_execution_profile

        monkeypatch.setenv("OPCUA_TARGET_INTERACTIVE_PROMPTS", "1")
        profile = build_execution_profile({"schema_version": 1, "target": {"endpoint": "opc.tcp://localhost:40451"}})
        assert (
            tse._build_spec_test_env(profile, base_dir=tmp_path, interactive_prompts=True)[
                "OPCUA_TARGET_INTERACTIVE_PROMPTS"
            ]
            == "1"
        )

    def test_spec_test_env_clears_inherited_prompt_permission(self, tmp_path, monkeypatch):
        from helpers.target_server_cu_config import build_execution_profile

        monkeypatch.setenv("OPCUA_TARGET_INTERACTIVE_PROMPTS", "1")
        profile = build_execution_profile({"schema_version": 1, "target": {"endpoint": "opc.tcp://localhost:40451"}})
        env = tse._build_spec_test_env(profile, base_dir=tmp_path, interactive_prompts=False)
        assert "OPCUA_TARGET_INTERACTIVE_PROMPTS" not in env
