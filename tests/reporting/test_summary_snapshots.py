from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"

_ICON_SIGNAL = "\U0001f6a6"
_ICON_PASSED = "\u2705"
_ICON_FAILED = "\u274c"
_ICON_SKIPPED = "\u23ed\ufe0f"
_ICON_TOTAL = "\U0001f9ee"
_ICON_JOBS = "\U0001f6e0\ufe0f"


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
    "GH_REPOSITORY": "umati/UA-for-Industrial-Joining-Technologies",
    "GH_RUN_ID": "42",
    "GH_API_URL": "https://api.github.example",
    "GH_TOKEN": "",
    "REPORT_JOB_NAME": "📋 CI Report",
}


INTEGRATION_ENV = {
    "SD_RESULT": "success",
    "WD_RESULT": "success",
    "TC_RESULT": "success",
    "WC_RESULT": "success",
    "WB_RESULT": "success",
    "CON_RESULT": "success",
    "CS_RESULT": "success",
    "CS_OPCUA_SECURITY_RESULT": "skipped",
    "CONSOLE_OPCUA_SECURITY_RESULT": "skipped",
    "GH_SHA": "abcdef1234567890",
    "GH_BRANCH": "c2-phase-1b",
    "GH_RUN_NUMBER": "84",
    "GH_RUN_URL": "https://github.example/ijt/actions/runs/84",
    "GH_REPOSITORY": "umati/UA-for-Industrial-Joining-Technologies",
    "GH_RUN_ID": "84",
    "GH_API_URL": "https://api.github.example",
    "GH_TOKEN": "",
    "GITHUB_TOKEN": "",
    "REPORT_JOB_NAME": "📋 System Tests Report",
    "BROWSER_IMAGE_PLAN": "cached",
    "BROWSER_IMAGE_REF": (
        "ghcr.io/umati/ua-for-industrial-joining-technologies/"
        "ijt-browser-ci@sha256:4910c3014c87914a9b041edcd05ea018ab13db65461707602d18c5f33e0ece87"
    ),
    "BROWSER_IMAGE_INPUTS_FINGERPRINT": (
        "e569f8a7754eb9a1979bd341e274167c43d2b1985e96238270cc7140ec89aa31"
    ),
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


def test_ci_outcome_overview_exact_block() -> None:
    text = (FIXTURES / "expected" / "ci_summary.md").read_text(encoding="utf-8")
    expected = (
        f"| {_ICON_SIGNAL}  | Outcome |   Count |\n"
        "| :-: | :------ | ------: |\n"
        f"| {_ICON_PASSED}  | Passed  |      21 |\n"
        f"| {_ICON_FAILED}  | Failed  |       0 |\n"
        f"| {_ICON_SKIPPED}  | Skipped |      18 |\n"
        f"| {_ICON_TOTAL}  | Total   |      39 |\n"
        f"| {_ICON_JOBS}  | Jobs    | 12 / 12 |\n"
    )
    assert expected in text, (
        "CI Outcome Overview pin mismatch.\n"
        f"Expected:\n{expected}\nFixture contains:\n{text[:1500]}"
    )


def test_integration_outcome_overview_exact_block() -> None:
    text = (FIXTURES / "expected" / "integration_summary.md").read_text(encoding="utf-8")
    expected = (
        f"| {_ICON_SIGNAL}  | Outcome | Count |\n"
        "| :-: | :------ | ----: |\n"
        f"| {_ICON_PASSED}  | Passed  | 2,432 |\n"
        f"| {_ICON_FAILED}  | Failed  |     0 |\n"
        f"| {_ICON_SKIPPED}  | Skipped |   154 |\n"
        f"| {_ICON_TOTAL}  | Total   | 2,586 |\n"
        f"| {_ICON_JOBS}  | Jobs    | 7 / 7 |\n"
    )
    assert expected in text, (
        "Integration Outcome Overview pin mismatch.\n"
        f"Expected:\n{expected}\nFixture contains:\n{text[:1500]}"
    )
