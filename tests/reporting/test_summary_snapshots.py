from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


CI_ENV = {
    "WEB_PY_RESULT": "success",
    "WEB_JS_RESULT": "success",
    "CONSOLE_RESULT": "success",
    "NODE_RESULT": "success",
    "DOCKER_RESULT": "success",
    "CS_UNIT_RESULT": "success",
    "CS_VULN_RESULT": "success",
    "TC_RESULT": "success",
    "SS_WIN_RESULT": "success",
    "AL_RESULT": "success",
    "ZZ_RESULT": "success",
    "PC_RESULT": "success",
    "WEB_PY_RUFF": "success",
    "WEB_PY_MYPY": "success",
    "WEB_JS_ESLINT": "success",
    "CONSOLE_RUFF": "success",
    "CONSOLE_MYPY": "success",
    "NODE_ESLINT": "success",
    "CS_BUILD": "success",
    "CS_FORMAT": "success",
    "CS_VULN": "success",
    "TC_RUFF": "success",
    "TC_MYPY": "success",
    "GH_SHA": "1234567890abcdef",
    "GH_BRANCH": "c2-phase-1b",
    "GH_RUN_NUMBER": "42",
    "GH_RUN_URL": "https://github.example/ijt/actions/runs/42",
}


INTEGRATION_ENV = {
    "SD_RESULT": "success",
    "WD_RESULT": "success",
    "TC_RESULT": "success",
    "WC_RESULT": "success",
    "WB_RESULT": "success",
    "CON_RESULT": "success",
    "CS_RESULT": "success",
    "GH_SHA": "abcdef1234567890",
    "GH_BRANCH": "c2-phase-1b",
    "GH_RUN_NUMBER": "84",
    "GH_RUN_URL": "https://github.example/ijt/actions/runs/84",
    "GH_REPOSITORY": "umati/UA-for-Industrial-Joining-Technologies",
    "GH_RUN_ID": "84",
    "GH_API_URL": "https://api.github.example",
    "GH_TOKEN": "",
    "GITHUB_TOKEN": "",
    "REPORT_JOB_NAME": "📋 System Tests Summary",
}


def _run_summary(
    script_name: str,
    fixture_name: str,
    env_overrides: dict[str, str],
    tmp_path: Path,
) -> str:
    workdir = tmp_path / fixture_name
    shutil.copytree(FIXTURES / fixture_name / "root", workdir)

    summary_path = workdir / "summary.md"
    env = os.environ.copy()
    env.update(env_overrides)
    env["GITHUB_STEP_SUMMARY"] = str(summary_path)

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "reporting" / script_name)],
        cwd=workdir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "Summary written.\n"
    assert result.stderr == ""
    return summary_path.read_text(encoding="utf-8")


def test_ci_summary_snapshot_matches_fixed_artifacts(tmp_path: Path) -> None:
    actual = _run_summary("ci_run_summary.py", "ci", CI_ENV, tmp_path)
    expected = (FIXTURES / "expected" / "ci_summary.md").read_text(encoding="utf-8")
    assert actual == expected


def test_integration_summary_snapshot_matches_fixed_artifacts(tmp_path: Path) -> None:
    actual = _run_summary(
        "system_tests_run_summary.py",
        "integration",
        INTEGRATION_ENV,
        tmp_path,
    )
    expected = (FIXTURES / "expected" / "integration_summary.md").read_text(encoding="utf-8")
    assert actual == expected
