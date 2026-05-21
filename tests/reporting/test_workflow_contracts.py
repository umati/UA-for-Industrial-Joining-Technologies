from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DORNY_ACTION = "dorny/test-reporter@a43b3a5f7366b97d083190328d2c652e1a8b6aa2"


def _workflow(name: str):
    path = REPO_ROOT / ".github" / "workflows" / name
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _summary_step(workflow_name: str):
    workflow = _workflow(workflow_name)
    steps = workflow["jobs"]["report"]["steps"]
    return next(step for step in steps if step.get("name") == "Generate Summary Table")


def _report_step(workflow_name: str, step_name: str):
    workflow = _workflow(workflow_name)
    steps = workflow["jobs"]["report"]["steps"]
    return next(step for step in steps if step.get("name") == step_name)


def test_ci_summary_step_invokes_extracted_module() -> None:
    step = _summary_step("ci.yml")
    workflow = _workflow("ci.yml")

    assert workflow["jobs"]["report"]["permissions"]["actions"] == "read"
    assert step["run"].strip() == "python3 reporting/ci_run_summary.py"
    assert "PYEOF" not in step["run"]
    assert set(step["env"]) == {
        "WEB_PY_RESULT",
        "WEB_JS_RESULT",
        "CONSOLE_RESULT",
        "NODE_RESULT",
        "DOCKER_RESULT",
        "CS_UNIT_RESULT",
        "CS_VULN_RESULT",
        "TC_RESULT",
        "SS_WIN_RESULT",
        "AL_RESULT",
        "ZZ_RESULT",
        "PC_RESULT",
        "WEB_PY_RUFF",
        "WEB_PY_MYPY",
        "WEB_JS_ESLINT",
        "CONSOLE_RUFF",
        "CONSOLE_MYPY",
        "NODE_ESLINT",
        "CS_BUILD",
        "CS_FORMAT",
        "CS_VULN",
        "TC_RUFF",
        "TC_MYPY",
        "GH_SHA",
        "GH_BRANCH",
        "GH_RUN_NUMBER",
        "GH_RUN_URL",
        "GH_REPOSITORY",
        "GH_RUN_ID",
        "GH_API_URL",
        "GH_TOKEN",
        "REPORT_JOB_NAME",
    }


def test_ci_timing_artifacts_are_collected_from_report_job() -> None:
    collect_step = _report_step("ci.yml", "Collect Timing JSON")
    upload_step = _report_step("ci.yml", "Upload Timing Artifacts")

    assert collect_step["run"].strip() == "python3 scripts/reporting/collect_timing.py"
    assert collect_step["env"]["TIMING_WORKFLOW_NAME"] == "CI — Fast Checks"
    assert collect_step["env"]["TIMING_OUTPUT_DIR"] == "timing-results"
    assert collect_step["env"]["REPORT_JOB_NAME"] == "📋 Test Report"
    assert upload_step["with"]["name"] == "timing-ci"
    assert upload_step["with"]["path"] == "timing-results/"


def test_ci_dorny_actions_keep_check_runs_but_suppress_step_summaries() -> None:
    workflow = _workflow("ci.yml")
    expected_names = [
        "Web Client — Python Tests",
        "Web Client — JS Tests (Vitest)",
        "Console Client — Tests",
        "Node Client — Tests",
        "Web Client — Python Tests",
        "Web Client — JS Tests (Vitest)",
        "Console Client — Python Tests",
        "Node Client — JS Tests (Vitest)",
        "Test Client — Python Tests (Unit)",
        "C# Client — Unit Tests (xUnit)",
        "OPC UA Server — Smoke Tests (Windows)",
    ]

    dorny_steps = [
        step
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if step.get("uses") == DORNY_ACTION
    ]

    assert [step["with"]["name"] for step in dorny_steps] == expected_names
    assert all(step["with"]["use-actions-summary"] is False for step in dorny_steps)


def test_ci_outcome_pie_chart_removed_q11() -> None:
    report_script = (REPO_ROOT / "reporting" / "ci_run_summary.py").read_text(encoding="utf-8")

    assert '"pie1"' not in report_script
    assert '"pie2"' not in report_script
    assert '"pie3"' not in report_script
    assert "pie showData" not in report_script
    assert "✅ Passed:" in report_script
    assert "⏭️ Skipped:" in report_script


def test_ci_expected_summary_has_no_dash_only_cells() -> None:
    expected_summary = (
        REPO_ROOT / "tests" / "reporting" / "fixtures" / "expected" / "ci_summary.md"
    ).read_text(encoding="utf-8")

    assert not re.search(r"\|\s*—\s*(?=\|)", expected_summary)


def test_ci_docker_smoke_suppresses_docker_build_summary_noise() -> None:
    workflow = _workflow("ci.yml")
    docker_smoke = workflow["jobs"]["docker-smoke"]
    build_steps = [
        step
        for step in docker_smoke["steps"]
        if step.get("uses") == "docker/build-push-action@bcafcacb16a39f128d818304e6c9c0c18556b85f"
    ]

    assert build_steps and len(build_steps) == 1
    assert docker_smoke["env"]["DOCKER_BUILD_SUMMARY"] == "false"
    assert docker_smoke["env"]["DOCKER_BUILD_RECORD_UPLOAD"] == "false"


def test_ci_all_checks_comment_matches_current_ruleset_truth() -> None:
    workflow_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    old_comment = 'Rule: configure branch protection to require only "All checks passed".'

    assert "Ruleset 15294123 currently requires only the CodeQL Analyze contexts" in workflow_text
    assert old_comment not in workflow_text


def test_ci_csharp_unit_excludes_dedicated_live_and_security_suites() -> None:
    workflow = _workflow("ci.yml")
    csharp_unit = workflow["jobs"]["csharp-unit"]
    test_step = next(
        step for step in csharp_unit["steps"] if step.get("name") == "Run xUnit Unit Tests"
    )

    assert '--filter "Category!=Live&Category!=OpcUaSecurity"' in test_step["run"]


def test_integration_summary_step_invokes_extracted_module() -> None:
    workflow = _workflow("integration.yml")
    step = _summary_step("integration.yml")

    assert workflow["name"] == "System Tests — Live OPC UA, Browser, Docker, Conformance"
    assert workflow["jobs"]["report"]["name"] == "📋 System Tests Summary"
    assert step["run"].strip() == "python3 reporting/system_tests_run_summary.py"
    assert "PYEOF" not in step["run"]
    assert step["env"]["REPORT_JOB_NAME"] == "📋 System Tests Summary"
    assert set(step["env"]) == {
        "SD_RESULT",
        "WD_RESULT",
        "TC_RESULT",
        "WC_RESULT",
        "WB_RESULT",
        "CON_RESULT",
        "CS_RESULT",
        "CS_OPCUA_SECURITY_RESULT",
        "CONSOLE_OPCUA_SECURITY_RESULT",
        "GH_SHA",
        "GH_BRANCH",
        "GH_RUN_NUMBER",
        "GH_RUN_URL",
        "GH_REPOSITORY",
        "GH_RUN_ID",
        "GH_API_URL",
        "GH_TOKEN",
        "REPORT_JOB_NAME",
    }


def test_integration_timing_artifacts_are_collected_from_report_job() -> None:
    collect_step = _report_step("integration.yml", "Collect Timing JSON")
    upload_step = _report_step("integration.yml", "Upload Timing Artifacts")

    assert collect_step["run"].strip() == "python3 scripts/reporting/collect_timing.py"
    assert (
        collect_step["env"]["TIMING_WORKFLOW_NAME"]
        == "System Tests — Live OPC UA, Browser, Docker, Conformance"
    )
    assert collect_step["env"]["TIMING_OUTPUT_DIR"] == "timing-results"
    assert collect_step["env"]["REPORT_JOB_NAME"] == "📋 System Tests Summary"
    assert upload_step["with"]["name"] == "timing-system-tests"
    assert upload_step["with"]["path"] == "timing-results/"


def test_integration_dorny_actions_keep_check_runs_but_suppress_step_summaries() -> None:
    workflow = _workflow("integration.yml")
    expected_names = [
        "OPC UA Server — Smoke Tests (Docker Linux)",
        "Web Client Docker — Python Tests",
        "Web Client Docker — JS Tests (Vitest)",
        "Test Client — Conformance Tests (Live)",
        "Web Client — Local Live Suites",
        "Console Client — Live Tests",
        "C# Client — Live Tests (xUnit)",
        "C# Client — OPC UA Security",
        "Console Client — OPC UA Security",
    ]

    dorny_steps = [
        step for step in workflow["jobs"]["report"]["steps"] if step.get("uses") == DORNY_ACTION
    ]

    assert [step["with"]["name"] for step in dorny_steps] == expected_names
    assert all(step["with"]["use-actions-summary"] is False for step in dorny_steps)


def test_integration_docker_jobs_suppress_build_summary_noise() -> None:
    workflow = _workflow("integration.yml")
    build_action = "docker/build-push-action@bcafcacb16a39f128d818304e6c9c0c18556b85f"
    for job_name in ("server-smoke-docker", "webclient-docker"):
        job = workflow["jobs"][job_name]
        build_steps = [step for step in job["steps"] if step.get("uses") == build_action]

        assert build_steps and len(build_steps) == 2
        assert job["env"]["DOCKER_BUILD_SUMMARY"] == "false"
        assert job["env"]["DOCKER_BUILD_RECORD_UPLOAD"] == "false"
        assert "DOCKERHUB_USERNAME" in job["env"]


def test_integration_performance_hotspots_uses_table_not_mermaid() -> None:
    report_script = (REPO_ROOT / "reporting" / "system_tests_run_summary.py").read_text(
        encoding="utf-8"
    )

    assert "```mermaid" not in report_script
    assert "gantt" not in report_script
    assert "| Source | Item | Duration | Status |" in report_script
    assert "Bottleneck Spotlight" in report_script


def test_integration_paths_include_reporting_modules() -> None:
    workflow = _workflow("integration.yml")
    triggers = workflow.get("on", workflow.get(True, {}))

    assert "reporting/**" in triggers["push"]["paths"]
    assert "reporting/**" in triggers["pull_request"]["paths"]
    assert "scripts/reporting/**" in triggers["push"]["paths"]
    assert "scripts/reporting/**" in triggers["pull_request"]["paths"]
