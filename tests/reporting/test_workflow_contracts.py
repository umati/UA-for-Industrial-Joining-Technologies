from __future__ import annotations

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


def test_ci_summary_step_invokes_extracted_module() -> None:
    step = _summary_step("ci.yml")

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
    }


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


def test_integration_summary_step_invokes_extracted_module() -> None:
    step = _summary_step("integration.yml")

    assert step["run"].strip() == "python3 reporting/system_tests_run_summary.py"
    assert "PYEOF" not in step["run"]
    assert set(step["env"]) == {
        "SD_RESULT",
        "WD_RESULT",
        "TC_RESULT",
        "WC_RESULT",
        "WB_RESULT",
        "CON_RESULT",
        "CS_RESULT",
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


def test_integration_paths_include_reporting_modules() -> None:
    workflow = _workflow("integration.yml")
    triggers = workflow.get("on", workflow.get(True, {}))

    assert "reporting/**" in triggers["push"]["paths"]
    assert "reporting/**" in triggers["pull_request"]["paths"]
