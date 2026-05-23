#!/usr/bin/env python3
"""
make_conformance_summary.py — Render the IJT Test Client conformance summary.

Renders a GitHub Actions Step Summary from JUnit XML and the per-CU
conformance report. Invoked from `.github/workflows/integration.yml` after
the live conformance pytest run.

Reads:  test-results/pytest.xml   (or --xml=FILE)
        test-results/cu-compliance-report.json, when present
Writes: $GITHUB_STEP_SUMMARY      (GitHub markdown step summary, when enabled)
        test-results/summary.md   (always, as a local copy)

Called automatically by the CI workflow after the test run. Safe to run locally too.

The Markdown rendering pipeline lives in
``scripts/reporting/conformance_summary.py`` so it can be tested
independently. This module is the CLI shim that parses arguments, reads test
artifacts, calls
``render_conformance_summary(...)``, and writes the result to disk and to the
GitHub step summary. The shim re-exports a ``_render`` symbol that delegates
to the new renderer purely for backward compatibility with any historical
caller; new code should import ``render_conformance_summary`` directly.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET  # nosec B405
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Bandit B405/B314 suppressions are limited to trusted JUnit XML from pytest.

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CU_JSON = _PROJECT_ROOT / "test-results" / "cu-compliance-report.json"
_DEFAULT_BASELINE_JSON = _PROJECT_ROOT / "test-results" / "report-baseline.json"
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# scripts/ is on sys.path[0] when this file is invoked as `python scripts/make_conformance_summary.py`,
# so the renderer package is importable as `reporting.conformance_summary`.
from reporting.conformance_summary import (  # noqa: E402
    _baseline_payload,
    _skip_reason_bucket,
    render_conformance_summary,
)

# Backward-compatible alias for any historical caller that imported `_render`.
_render = render_conformance_summary


# ── Parse JUnit XML ───────────────────────────────────────────────────────────


def _parse(xml_path: Path):
    tree = ET.parse(xml_path)  # nosec B314
    root = tree.getroot()
    suites = root.findall(".//testsuite") if root.tag == "testsuites" else [root]

    passed = failed = errors = skipped = xfailed = 0
    total_time = 0.0
    failures: list[dict] = []
    skip_reasons: dict[str, int] = {}
    xfail_reasons: dict[str, int] = {}

    for suite in suites:
        for tc in suite.findall("testcase"):
            duration = float(tc.get("time", "0") or "0")
            total_time += duration
            name = tc.get("name", "")
            classname = tc.get("classname", "")
            f = tc.find("failure")
            e = tc.find("error")
            s = tc.find("skipped")

            if f is not None:
                failed += 1
                failures.append(
                    {
                        "name": name,
                        "classname": classname,
                        "message": (f.get("message") or (f.text or ""))[:300],
                    }
                )
            elif e is not None:
                errors += 1
                failures.append(
                    {
                        "name": name,
                        "classname": classname,
                        "message": (e.get("message") or (e.text or ""))[:300],
                    }
                )
            elif s is not None:
                msg = (s.get("message") or "").strip()
                if (s.get("type") or "").lower() == "pytest.xfail":
                    xfailed += 1
                    # Bucket xfail reasons by first sentence
                    key = msg.split(".")[0][:80] if msg else "no reason"
                    xfail_reasons[key] = xfail_reasons.get(key, 0) + 1
                else:
                    skipped += 1
                    key = _skip_reason_bucket(msg)
                    skip_reasons[key] = skip_reasons.get(key, 0) + 1
            else:
                passed += 1

    total = passed + failed + errors + skipped + xfailed
    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "xfailed": xfailed,
        "total": total,
        "duration_s": total_time,
        "failures": failures,
        "skip_reasons": dict(sorted(skip_reasons.items(), key=lambda x: -x[1])[:20]),
        "xfail_reasons": dict(sorted(xfail_reasons.items(), key=lambda x: -x[1])),
    }


# ── I/O helpers ───────────────────────────────────────────────────────────────


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_baseline(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _write_baseline(path: Path, baseline: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--xml", default="test-results/pytest.xml")
    p.add_argument("--out", default="test-results/summary.md")
    p.add_argument("--cu-json", default=str(_DEFAULT_CU_JSON))
    p.add_argument("--baseline", default=str(_DEFAULT_BASELINE_JSON))
    p.add_argument(
        "--github-summary",
        choices=["auto", "always", "never"],
        default="auto",
        help=(
            "Control writes to GITHUB_STEP_SUMMARY. auto preserves existing behavior, "
            "always requires the env var, and never writes the step summary."
        ),
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    xml_path = Path(args.xml)

    if not xml_path.exists():
        print(f"ERROR: {xml_path} not found", file=sys.stderr)
        return 1

    data = _parse(xml_path)
    server_url = os.environ.get("OPCUA_SERVER_URL", "opc.tcp://localhost:40451")
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    run_ts_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    cu_payload = _load_json(Path(args.cu_json))
    baseline_path = Path(args.baseline)

    md, context = render_conformance_summary(data, server_url, run_ts, cu_payload)

    # Write local copy
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"Summary written: {out_path}")
    if context is not None:
        _write_baseline(
            baseline_path,
            _baseline_payload(context, run_ts_iso, context["report_environment"]),
        )
        print(f"Baseline written: {baseline_path}")

    # Write to GitHub Step Summary if requested. CI can disable this when a
    # downstream aggregator owns the visible run-page summary.
    github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    should_write_github_summary = args.github_summary == "always" or (
        args.github_summary == "auto" and bool(github_summary)
    )
    if should_write_github_summary and not github_summary:
        print("ERROR: --github-summary=always requires GITHUB_STEP_SUMMARY", file=sys.stderr)
        return 1
    if should_write_github_summary and github_summary:
        with open(github_summary, "a", encoding="utf-8") as fh:
            fh.write(md)
        print("GitHub Step Summary updated.")

    # Exit non-zero if there were failures (makes CI step fail-aware)
    total_failures = data["failed"] + data["errors"]
    if total_failures:
        print(f"\n  *** {total_failures} FAILURE(S) ***", file=sys.stderr)
    return 0  # summary script itself always exits 0; pytest exit code controls CI pass/fail


if __name__ == "__main__":
    sys.exit(main())
