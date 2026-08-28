"""
Unit tests for helpers/target_server_execution.py — the canonical Target Server
CU execution logic shared by run_all_tests.py (--profile/--endpoint) and the
deprecated run_target_server_cu.py compatibility shim.

These tests call run_preflight()/run_automated() directly (in-process) rather
than through a subprocess, so coverage.py can attribute the executed lines —
subprocess-based CLI tests (tests/unit/test_run_target_server_cu.py) exercise
the same code but coverage cannot see across a process boundary.
"""

from __future__ import annotations

import json
import sys
from contextlib import redirect_stdout
from io import StringIO

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
