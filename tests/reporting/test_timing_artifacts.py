from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

from reporting.timing_artifacts import (
    actions_payload_from_jobs,
    duration_seconds,
    local_runner_timing_payload,
    write_timing_bundle,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_duration_seconds_parses_actions_timestamps() -> None:
    assert duration_seconds("2026-05-17T10:00:00Z", "2026-05-17T10:01:30Z") == 90.0


def test_actions_payload_excludes_report_job_and_keeps_step_timings() -> None:
    payload = actions_payload_from_jobs(
        workflow_name="CI",
        report_job_name="Report",
        generated_utc="2026-05-17T10:00:00Z",
        env={
            "GH_REPOSITORY": "umati/UA-for-Industrial-Joining-Technologies",
            "GH_RUN_ID": "123",
            "GH_RUN_NUMBER": "45",
            "GH_SHA": "abcdef",
            "GH_BRANCH": "main",
            "GH_RUN_URL": "https://example.test/run",
        },
        jobs=[
            {
                "id": 1,
                "name": "C# Unit",
                "status": "completed",
                "conclusion": "success",
                "started_at": "2026-05-17T10:00:00Z",
                "completed_at": "2026-05-17T10:02:00Z",
                "steps": [
                    {
                        "name": "Restore",
                        "status": "completed",
                        "conclusion": "success",
                        "started_at": "2026-05-17T10:00:00Z",
                        "completed_at": "2026-05-17T10:00:30Z",
                    }
                ],
            },
            {
                "id": 2,
                "name": "Report",
                "status": "completed",
                "conclusion": "success",
                "started_at": "2026-05-17T10:00:00Z",
                "completed_at": "2026-05-17T10:00:05Z",
            },
        ],
    )

    assert payload["schema_version"] == 1
    assert [job["name"] for job in payload["jobs"]] == ["C# Unit"]
    assert payload["jobs"][0]["duration_seconds"] == 120.0
    assert payload["jobs"][0]["stages"][0]["duration_seconds"] == 30.0
    assert payload["summary"]["longest_job_name"] == "C# Unit"


def test_local_runner_payload_records_suite_results() -> None:
    result = SimpleNamespace(
        name="repo-static-gitignore-check",
        ok=True,
        skipped=False,
        duration=1.2345,
        notes=["ok"],
        counts="",
    )

    payload = local_runner_timing_payload(
        results=[result],
        total_seconds=2.0,
        mode="suite:repo-static-gitignore-check",
        generated_utc="2026-05-17T10:00:00Z",
    )

    assert payload["source"]["kind"] == "local-runner"
    assert payload["source"]["mode"] == "suite:repo-static-gitignore-check"
    assert payload["jobs"][0]["duration_seconds"] == 2.0
    assert payload["jobs"][0]["stages"][0]["duration_seconds"] == 1.234


def test_write_timing_bundle_writes_aggregate_latest_and_per_job() -> None:
    payload = actions_payload_from_jobs(
        workflow_name="CI",
        generated_utc="2026-05-17T10:00:00Z",
        env={},
        jobs=[
            {
                "id": 1,
                "name": "Job One",
                "status": "completed",
                "conclusion": "success",
                "started_at": "2026-05-17T10:00:00Z",
                "completed_at": "2026-05-17T10:00:01Z",
            }
        ],
    )

    scratch = REPO_ROOT / "test-results" / "timing-artifacts-unit"
    if scratch.exists():
        shutil.rmtree(scratch)
    try:
        paths = write_timing_bundle(payload, scratch)

        assert paths["aggregate"].is_file()
        assert paths["latest"].is_file()
        assert paths["jobs"][0].is_file()
        aggregate = json.loads(paths["aggregate"].read_text(encoding="utf-8"))
        job_payload = json.loads(paths["jobs"][0].read_text(encoding="utf-8"))
        assert aggregate["schema_version"] == 1
        assert job_payload["jobs"][0]["name"] == "Job One"
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)
