"""Timing artifact helpers for IJT CI, Integration, and local runs."""

from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import re
import urllib.parse
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any

try:
    from reporting._http import https_only_opener
except ImportError:  # pragma: no cover - standalone: python3 reporting/X.py
    from _http import https_only_opener  # type: ignore[no-redef]


def _urlopen(request, timeout):
    """HTTPS-only urlopen wrapper; tests can monkeypatch this seam."""
    return https_only_opener().open(request, timeout=timeout)


SCHEMA_VERSION = 1


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp with stable second precision."""
    return _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_actions_time(value: object) -> _dt.datetime | None:
    """Parse a GitHub Actions timestamp into a timezone-aware datetime."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return _dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def next_link(header: object) -> str | None:
    """Return the next pagination URL from a GitHub Link header."""
    for part in str(header or "").split(","):
        pieces = [piece.strip() for piece in part.split(";")]
        if len(pieces) < 2 or pieces[1] != 'rel="next"':
            continue
        target = pieces[0]
        if target.startswith("<") and target.endswith(">"):
            return target[1:-1]
    return None


def duration_seconds(started_at: object, completed_at: object) -> float | None:
    """Return non-negative seconds between two Actions timestamps."""
    started = parse_actions_time(started_at)
    completed = parse_actions_time(completed_at)
    if not started or not completed:
        return None
    return max((completed - started).total_seconds(), 0.0)


def _text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-").lower()
    return slug or "job"


def _duration_for_job(job: dict[str, Any]) -> float | None:
    return duration_seconds(job.get("started_at"), job.get("completed_at"))


def _stage_from_actions_step(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": _text(step.get("name"), f"step-{step.get('number', '')}".rstrip("-")),
        "status": _text(step.get("status"), "unknown"),
        "conclusion": _text(step.get("conclusion"), "unknown"),
        "started_at": _text(step.get("started_at")),
        "completed_at": _text(step.get("completed_at")),
        "duration_seconds": duration_seconds(step.get("started_at"), step.get("completed_at")),
    }


def actions_payload_from_jobs(
    *,
    jobs: list[dict[str, Any]],
    workflow_name: str,
    env: Mapping[str, str] = os.environ,
    report_job_name: str = "",
    generated_utc: str | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Build a schema-v1 timing payload from GitHub Actions jobs API rows."""
    report_name = report_job_name.strip()
    job_records: list[dict[str, Any]] = []
    for job in jobs:
        name = _text(job.get("name"), "unknown")
        if report_name and name == report_name:
            continue
        job_records.append(
            {
                "id": job.get("id"),
                "name": name,
                "status": _text(job.get("status"), "unknown"),
                "conclusion": _text(job.get("conclusion"), "unknown"),
                "started_at": _text(job.get("started_at")),
                "completed_at": _text(job.get("completed_at")),
                "duration_seconds": _duration_for_job(job),
                "runner_name": _text(job.get("runner_name")),
                "runner_group_name": _text(job.get("runner_group_name")),
                "html_url": _text(job.get("html_url")),
                "stages": [
                    _stage_from_actions_step(step)
                    for step in job.get("steps", [])
                    if isinstance(step, dict)
                ],
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": generated_utc or utc_now(),
        "source": {
            "kind": "github-actions",
            "workflow_name": workflow_name,
            "measurement": "jobs-api",
        },
        "run": {
            "repository": _text(env.get("GH_REPOSITORY") or env.get("GITHUB_REPOSITORY")),
            "run_id": _text(env.get("GH_RUN_ID") or env.get("GITHUB_RUN_ID")),
            "run_number": _text(env.get("GH_RUN_NUMBER") or env.get("GITHUB_RUN_NUMBER")),
            "sha": _text(env.get("GH_SHA") or env.get("GITHUB_SHA")),
            "branch": _text(env.get("GH_BRANCH") or env.get("GITHUB_REF_NAME")),
            "url": _text(env.get("GH_RUN_URL")),
        },
        "summary": _summary(job_records),
        "jobs": job_records,
        "warnings": warnings or [],
    }


def github_actions_timing_payload(
    *,
    workflow_name: str,
    env: Mapping[str, str] = os.environ,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    """Fetch GitHub Actions job metadata and return a timing payload.

    The collector is best-effort: missing token/API context yields a valid
    payload with warnings so report generation does not change test results.
    """
    token = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    repository = env.get("GH_REPOSITORY") or env.get("GITHUB_REPOSITORY")
    run_id = env.get("GH_RUN_ID") or env.get("GITHUB_RUN_ID")
    report_job_name = env.get("REPORT_JOB_NAME", "")
    warnings: list[str] = []
    if not token or not repository or not run_id:
        missing = [
            name
            for name, value in (
                ("GH_TOKEN", token),
                ("GH_REPOSITORY", repository),
                ("GH_RUN_ID", run_id),
            )
            if not value
        ]
        warnings.append(f"missing GitHub Actions context: {', '.join(missing)}")
        return actions_payload_from_jobs(
            jobs=[],
            workflow_name=workflow_name,
            env=env,
            report_job_name=report_job_name,
            generated_utc=generated_utc,
            warnings=warnings,
        )

    api_root = (
        env.get("GH_API_URL") or env.get("GITHUB_API_URL") or "https://api.github.com"
    ).rstrip("/")
    url = f"{api_root}/repos/{repository}/actions/runs/{run_id}/jobs?per_page=100"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "ijt-timing-artifacts",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    jobs: list[dict[str, Any]] = []
    try:
        while url:
            parsed_url = urllib.parse.urlparse(url)
            if parsed_url.scheme != "https":
                raise ValueError(f"GitHub API URL must use https: {url}")
            # Request is a passive struct (no I/O). `_urlopen` dispatches
            # via https_only_opener() so any non-https URL raises URLError
            # at the protocol layer before any byte is sent. ruff S310 is
            # suppressed centrally via per-file-ignore in root pyproject.toml.
            request = urllib.request.Request(url, headers=headers)
            with _urlopen(request, timeout=20) as response:
                payload = json.load(response)
                jobs.extend(job for job in payload.get("jobs", []) if isinstance(job, dict))
                url = next_link(response.headers.get("Link"))
    except Exception as exc:
        warnings.append(f"GitHub Actions jobs API unavailable: {exc}")

    return actions_payload_from_jobs(
        jobs=jobs,
        workflow_name=workflow_name,
        env=env,
        report_job_name=report_job_name,
        generated_utc=generated_utc,
        warnings=warnings,
    )


def local_runner_timing_payload(
    *,
    results: list[Any],
    total_seconds: float,
    mode: str,
    env: Mapping[str, str] = os.environ,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    """Build a schema-v1 payload from root-runner SuiteResult objects."""
    stages: list[dict[str, Any]] = []
    for result in results:
        if getattr(result, "skipped", False):
            status = "skipped"
            conclusion = "skipped"
        elif getattr(result, "ok", False):
            status = "completed"
            conclusion = "success"
        else:
            status = "completed"
            conclusion = "failure"
        stages.append(
            {
                "name": _text(getattr(result, "name", ""), "unknown"),
                "status": status,
                "conclusion": conclusion,
                "started_at": "",
                "completed_at": "",
                "duration_seconds": round(float(getattr(result, "duration", 0.0) or 0.0), 3),
                "notes": list(getattr(result, "notes", []) or []),
                "counts": _text(getattr(result, "counts", "")),
            }
        )

    job = {
        "id": None,
        "name": "Local Root Runner",
        "status": "completed",
        "conclusion": "success"
        if all(stage["conclusion"] in {"success", "skipped"} for stage in stages)
        else "failure",
        "started_at": "",
        "completed_at": "",
        "duration_seconds": round(float(total_seconds or 0.0), 3),
        "runner_name": platform.node(),
        "runner_group_name": "local",
        "html_url": "",
        "stages": stages,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": generated_utc or utc_now(),
        "source": {
            "kind": "local-runner",
            "workflow_name": "IJT Repository Test Runner",
            "measurement": "suite-results",
            "mode": mode,
        },
        "run": {
            "repository": _text(env.get("GITHUB_REPOSITORY"), "local"),
            "run_id": _text(env.get("GITHUB_RUN_ID"), "local"),
            "run_number": _text(env.get("GITHUB_RUN_NUMBER"), "local"),
            "sha": _text(env.get("GITHUB_SHA")),
            "branch": _text(env.get("GITHUB_REF_NAME")),
            "url": "",
        },
        "summary": _summary([job]),
        "jobs": [job],
        "warnings": [],
    }


def write_timing_bundle(payload: dict[str, Any], output_dir: str | Path) -> dict[str, Path]:
    """Write aggregate and per-job timing JSON files and return their paths."""
    target = Path(output_dir)
    jobs_dir = target / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    aggregate_path = target / "timing-aggregate.json"
    latest_path = target / "timing-latest.json"

    encoded_payload = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    aggregate_path.write_text(encoded_payload, encoding="utf-8")
    latest_path.write_text(encoded_payload, encoding="utf-8")

    job_paths: list[Path] = []
    for index, job in enumerate(payload.get("jobs", []), start=1):
        if not isinstance(job, dict):
            continue
        job_payload = {
            "schema_version": payload.get("schema_version", SCHEMA_VERSION),
            "generated_utc": payload.get("generated_utc", ""),
            "source": payload.get("source", {}),
            "run": payload.get("run", {}),
            "summary": _summary([job]),
            "jobs": [job],
            "warnings": payload.get("warnings", []),
        }
        job_path = jobs_dir / f"{index:02d}-{_slug(_text(job.get('name'), 'job'))}.json"
        job_path.write_text(
            json.dumps(job_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        job_paths.append(job_path)

    return {
        "aggregate": aggregate_path,
        "latest": latest_path,
        "jobs_dir": jobs_dir,
        "jobs": job_paths,
    }


def _summary(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [job for job in jobs if isinstance(job.get("duration_seconds"), (int, float))]
    total = round(sum(float(job["duration_seconds"]) for job in completed), 3)
    longest = max(completed, key=lambda job: float(job["duration_seconds"]), default=None)
    return {
        "job_count": len(jobs),
        "completed_job_count": len(completed),
        "total_job_seconds": total,
        "longest_job_name": _text(longest.get("name")) if longest else "",
        "longest_job_seconds": round(float(longest["duration_seconds"]), 3) if longest else 0.0,
    }
