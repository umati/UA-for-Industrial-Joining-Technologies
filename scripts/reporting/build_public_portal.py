#!/usr/bin/env python3
"""Build and update the IJT Public CI/CD Observability Portal static site."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def main(argv: list[str] | None = None) -> int:
    from reporting.public_portal import (
        DEFAULT_MAX_RUNS,
        DEFAULT_MAX_TOTAL_MB,
        WORKFLOW_LABELS,
        publish_run_to_portal,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site-dir",
        default=os.environ.get("PORTAL_SITE_DIR", "site-state"),
        help="Target directory for the static GitHub Pages portal.",
    )
    parser.add_argument(
        "--workflow-slug",
        default=os.environ.get("PORTAL_WORKFLOW_SLUG", "ci"),
        help="Canonical workflow slug ('ci' or 'integration').",
    )
    parser.add_argument(
        "--workflow-name",
        default=os.environ.get("PORTAL_WORKFLOW_NAME", ""),
        help="Human-readable workflow title.",
    )
    parser.add_argument(
        "--artifacts-dir",
        default=os.environ.get("PORTAL_ARTIFACTS_DIR", "all-results"),
        help="Directory containing downloaded workflow artifacts.",
    )
    parser.add_argument(
        "--summary-file",
        default=os.environ.get("PORTAL_SUMMARY_FILE", ""),
        help="Optional explicit path to summary.md.",
    )
    parser.add_argument(
        "--timing-dir",
        default=os.environ.get("PORTAL_TIMING_DIR", "timing-results"),
        help="Directory containing timing-latest.json and summary.md.",
    )
    parser.add_argument(
        "--conclusion",
        default=os.environ.get("PORTAL_CONCLUSION", "auto"),
        help="Run conclusion override; 'auto' derives it from jobs/timing/summary.",
    )
    args = parser.parse_args(argv)

    slug = args.workflow_slug.strip().lower()
    workflow_name = args.workflow_name.strip() or WORKFLOW_LABELS.get(slug, slug)
    run_id = os.environ.get("GH_RUN_ID", "0").strip() or "0"
    run_number = _env_int("GH_RUN_NUMBER", 0)
    conclusion = (args.conclusion or "auto").strip()
    commit_sha = os.environ.get("GH_SHA", "").strip()
    branch = os.environ.get("GH_BRANCH", "main").strip() or "main"
    event_name = os.environ.get("GH_EVENT_NAME", "push").strip() or "push"
    html_url = os.environ.get("GH_RUN_URL", "").strip()
    api_url = os.environ.get("GH_API_URL", "https://api.github.com").strip()
    repository = os.environ.get("GH_REPOSITORY", "").strip()
    token = os.environ.get("GH_TOKEN", "").strip()
    is_release = os.environ.get("PORTAL_IS_RELEASE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    } or branch.startswith(("v", "release"))

    artifacts_dir = Path(args.artifacts_dir) if args.artifacts_dir else None
    summary_file = Path(args.summary_file) if args.summary_file else None
    timing_dir = Path(args.timing_dir) if args.timing_dir else None

    meta = publish_run_to_portal(
        site_dir=Path(args.site_dir),
        workflow_slug=slug,
        workflow_name=workflow_name,
        run_id=run_id,
        run_number=run_number,
        conclusion=conclusion,
        commit_sha=commit_sha,
        branch=branch,
        event_name=event_name,
        html_url=html_url,
        is_release=is_release,
        artifacts_dir=artifacts_dir,
        summary_file=summary_file,
        timing_dir=timing_dir,
        api_url=api_url,
        repository=repository,
        token=token,
        max_runs=_env_int("PORTAL_MAX_RUNS", DEFAULT_MAX_RUNS),
        max_total_mb=_env_int("PORTAL_MAX_TOTAL_MB", DEFAULT_MAX_TOTAL_MB),
    )
    print(
        f"published public portal run: slug={meta.workflow_slug} "
        f"run_id={meta.run_id} conclusion={meta.conclusion} jobs={meta.job_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
