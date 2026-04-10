#!/usr/bin/env python3
"""
make_ci_summary.py — Write a GitHub Actions Step Summary from JUnit XML test results.

Reads:  test-results/pytest.xml   (or --xml=FILE)
Writes: $GITHUB_STEP_SUMMARY      (GitHub markdown step summary, if env var is set)
        test-results/summary.md   (always, as a local copy)

Called automatically by the CI workflow after the test run. Safe to run locally too.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

# ── Parse JUnit XML ───────────────────────────────────────────────────────────


def _parse(xml_path: Path):
    tree = ET.parse(xml_path)  # nosec B314 — source is trusted JUnit XML written by pytest
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
                    # Bucket by first meaningful clause — split at " —", " (", or 80 chars
                    key = re.split(r"\s[—(]|\s—\s", msg)[0].strip()[:80] if msg else "no reason"
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


# ── Markdown rendering ────────────────────────────────────────────────────────


def _md_cell(text: str) -> str:
    """Escape pipe characters so text is safe inside a markdown table cell."""
    return re.sub(r"\|", "\\|", text)


def _status_badge(passed: int, failed: int, errors: int) -> str:
    if failed + errors > 0:
        return "🔴 **FAILED**"
    return "🟢 **PASSED**"


def _render(data: dict, server_url: str, run_ts: str) -> str:
    p = data["passed"]
    f = data["failed"] + data["errors"]
    s = data["skipped"]
    x = data["xfailed"]
    total = data["total"]
    mins, secs = divmod(int(data["duration_s"]), 60)

    lines: list[str] = []
    lines.append("# IJT Conformance Test Report")
    lines.append("")
    lines.append(
        f"**Result:** {_status_badge(p, f, 0)}  |  "
        f"**Server:** `{server_url}`  |  "
        f"**Run:** {run_ts}  |  "
        f"**Duration:** {mins}m {secs}s"
    )
    lines.append("")

    # ── Headline counts ──
    lines.append("## Summary")
    lines.append("")
    lines.append("| Status | Count | % |")
    lines.append("|--------|------:|--:|")
    lines.append(f"| ✅ Passed   | **{p}** | {p * 100 // total if total else 0}% |")
    lines.append(f"| ❌ Failed   | **{f}** | {f * 100 // total if total else 0}% |")
    lines.append(f"| ⏭️ Skipped  | **{s}** | {s * 100 // total if total else 0}% |")
    lines.append(f"| 🟡 Expected Fail | **{x}** | {x * 100 // total if total else 0}% |")
    lines.append(f"| **Total**   | **{total}** | 100% |")
    lines.append("")

    # ── Failures detail ──
    if data["failures"]:
        lines.append("## ❌ Failures")
        lines.append("")
        lines.append("| Test | Message |")
        lines.append("|------|---------|")
        for fl in data["failures"][:30]:
            name = fl["name"].replace("|", "\\|")
            msg = fl["message"].replace("\n", " ").replace("|", "\\|")[:200]
            lines.append(f"| `{name}` | {msg} |")
        if len(data["failures"]) > 30:
            lines.append(f"| … | *{len(data['failures']) - 30} more — see report.xlsx* |")
        lines.append("")

    # ── Skip reason buckets ──
    if data["skip_reasons"]:
        lines.append("## ⏭️ Skip Reasons (top categories)")
        lines.append("")
        lines.append("| Reason | Count |")
        lines.append("|--------|------:|")
        for reason, count in data["skip_reasons"].items():
            lines.append(f"| {_md_cell(reason)} | {count} |")
        lines.append("")

    # ── Xfail reasons ──
    if data["xfail_reasons"]:
        lines.append("## 🟡 Expected Failures")
        lines.append("")
        lines.append("These tests are marked as expected failures — known server gaps, not bugs.")
        lines.append("")
        lines.append("| Reason | Count |")
        lines.append("|--------|------:|")
        for reason, count in data["xfail_reasons"].items():
            lines.append(f"| {_md_cell(reason)} | {count} |")
        lines.append("")

    lines.append("---")
    lines.append("*Full detail: download `report.xlsx` or `report.html` from the run artifacts.*")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--xml", default="test-results/pytest.xml")
    p.add_argument("--out", default="test-results/summary.md")
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

    md = _render(data, server_url, run_ts)

    # Write local copy
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"Summary written: {out_path}")

    # Write to GitHub Step Summary if running in CI
    github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_summary:
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
