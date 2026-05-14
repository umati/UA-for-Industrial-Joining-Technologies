from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


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
