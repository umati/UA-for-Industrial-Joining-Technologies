#!/usr/bin/env python3
"""Collect IJT GitHub Actions timing JSON for the current workflow run."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    from reporting.timing_artifacts import github_actions_timing_payload, write_timing_bundle

    workflow_name = os.environ.get("TIMING_WORKFLOW_NAME", "GitHub Actions")
    output_dir = Path(os.environ.get("TIMING_OUTPUT_DIR", "timing-results"))
    payload = github_actions_timing_payload(workflow_name=workflow_name)
    paths = write_timing_bundle(payload, output_dir)
    print(f"timing aggregate: {paths['aggregate']}")
    print(f"timing per-job dir: {paths['jobs_dir']}")
    for warning in payload.get("warnings", []):
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
