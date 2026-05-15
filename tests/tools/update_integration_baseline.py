#!/usr/bin/env python3
"""Update the reviewed Integration test-count baseline from a green run.

The baseline remains an exact-match contract. This helper only removes the
manual JSON editing from an intentional re-anchor.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = "umati/UA-for-Industrial-Joining-Technologies"
REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "tests" / "baselines" / "integration-test-counts.json"
INTEGRATION_WORKFLOW = "System Tests — Live OPC UA, Browser, Docker, Conformance"

ARTIFACT_SPECS: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "sd_smoke": [("results-server-smoke-docker", ("smoke.xml",))],
    "wd_py": [("results-webclient-docker", ("pytest-unit.xml",))],
    "wd_js": [("results-webclient-docker", ("vitest.xml",))],
    "tc_smoke": [("results-testclient", ("smoke-sanity.xml",))],
    "tc_tests": [("results-testclient", ("pytest.xml",))],
    "wc_live": [
        ("results-live-webclient-web-client-live-opcua-direct", ("*.xml",)),
        ("results-live-webclient-web-client-live-websocket-api", ("*.xml",)),
        ("results-live-webclient-web-client-live-websocket-connection", ("*.xml",)),
    ],
    "wc_browser": [
        ("results-live-webclient-web-client-e2e-smoke", ("*.xml",)),
        ("results-live-webclient-web-client-e2e-features-shard-1of2", ("*.xml",)),
        ("results-live-webclient-web-client-e2e-features-shard-2of2", ("*.xml",)),
        ("results-live-webclient-web-client-e2e-regression", ("*.xml",)),
    ],
    "con_live": [("results-live-console", ("pytest-live.xml",))],
    "cs_live": [("results-csharp-live", ("tests.xml",))],
}


def _gh() -> str:
    exe = shutil.which("gh")
    if not exe:
        raise SystemExit("GitHub CLI `gh` is required to update the Integration baseline.")
    return exe


def _run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_gh(), *args],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _run_gh_json(run_id: str) -> dict:
    result = _run_gh(
        [
            "run",
            "view",
            run_id,
            "--repo",
            REPO,
            "--json",
            "conclusion,displayTitle,updatedAt,workflowName",
        ]
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"gh run view failed for run {run_id}")
    return json.loads(result.stdout)


def _download_artifact(run_id: str, artifact: str, target: Path) -> None:
    result = _run_gh(
        [
            "run",
            "download",
            run_id,
            "--repo",
            REPO,
            "--name",
            artifact,
            "--dir",
            str(target),
        ]
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"failed to download artifact {artifact!r}")


def _junit_counts(path: Path) -> tuple[int, int]:
    root = ET.parse(path).getroot()
    if root.tag == "testsuites":
        suites = root.findall("testsuite")
    elif root.tag == "testsuite":
        suites = [root]
    else:
        suites = root.findall(".//testsuite")

    if suites:
        tests = sum(int(suite.attrib.get("tests", 0) or 0) for suite in suites)
        skipped = sum(int(suite.attrib.get("skipped", 0) or 0) for suite in suites)
        return tests, skipped

    cases = root.findall(".//testcase")
    return len(cases), sum(1 for case in cases if case.find("skipped") is not None)


def _matching_files(root: Path, patterns: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        if any(char in pattern for char in "*?["):
            files.extend(root.rglob(pattern))
        else:
            files.extend(path for path in root.rglob(pattern) if path.name == pattern)
    return sorted({path for path in files if path.is_file()})


def _collect_suite_counts(run_id: str, suite: str) -> dict[str, int]:
    specs = ARTIFACT_SPECS[suite]
    temp_root = REPO_ROOT / "tmp" / f"integration-baseline-{run_id}-{suite}"
    shutil.rmtree(temp_root, ignore_errors=True)
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        tests = 0
        skipped = 0
        for artifact, patterns in specs:
            artifact_root = temp_root / artifact
            artifact_root.mkdir(parents=True, exist_ok=True)
            _download_artifact(run_id, artifact, artifact_root)
            matches = _matching_files(artifact_root, patterns)
            if not matches:
                raise SystemExit(
                    f"Artifact {artifact!r} did not contain expected JUnit file(s): "
                    f"{', '.join(patterns)}"
                )
            for path in matches:
                file_tests, file_skipped = _junit_counts(path)
                tests += file_tests
                skipped += file_skipped
        return {"tests": tests, "skipped": skipped}
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _validate_run(run_id: str) -> dict:
    payload = _run_gh_json(run_id)
    workflow_name = payload.get("workflowName") or payload.get("displayTitle")
    if workflow_name != INTEGRATION_WORKFLOW:
        raise SystemExit(f"Run {run_id} is not an Integration run.")
    if payload.get("conclusion") != "success":
        raise SystemExit(f"Run {run_id} is not green; conclusion={payload.get('conclusion')!r}.")
    return payload


def _apply_update(
    baseline: dict,
    counts: dict[str, int],
    *,
    run_id: str,
    captured_at: str,
    suite: str,
    allow_decrease: bool,
) -> dict:
    entry = baseline["suites"][suite]
    new_tests = counts["tests"]
    old_tests = int(entry["tests"])
    if new_tests < old_tests and not allow_decrease:
        raise SystemExit(
            f"{suite} would decrease from {old_tests} to {new_tests}. "
            "Re-run with --allow-decrease after reviewing the collection loss."
        )
    new_skipped = counts["skipped"]
    old_skipped = int(entry.get("skipped", 0))
    if new_skipped < old_skipped and not allow_decrease:
        raise SystemExit(
            f"{suite} skipped count would decrease from {old_skipped} to {new_skipped}. "
            "Re-run with --allow-decrease after reviewing the skip change."
        )

    entry["tests"] = new_tests
    entry["skipped"] = new_skipped
    baseline["captured_from_run"] = int(run_id)
    baseline["captured_at"] = captured_at
    return baseline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Green Integration run id to re-anchor from.")
    parser.add_argument("--suite", required=True, choices=sorted(ARTIFACT_SPECS))
    parser.add_argument(
        "--allow-decrease",
        action="store_true",
        help="Allow reviewed decreases in tests/skips instead of refusing them.",
    )
    args = parser.parse_args(argv)

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    run = _validate_run(args.run)
    counts = _collect_suite_counts(args.run, args.suite)
    updated = _apply_update(
        baseline,
        counts,
        run_id=args.run,
        captured_at=run["updatedAt"],
        suite=args.suite,
        allow_decrease=args.allow_decrease,
    )
    text = json.dumps(updated, indent=2, ensure_ascii=False) + "\n"
    BASELINE_PATH.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
