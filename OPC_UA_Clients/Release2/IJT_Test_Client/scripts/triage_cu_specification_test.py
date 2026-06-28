#!/usr/bin/env python3
"""
Summarize IJT CU coverage JSON and optional JUnit XML after a live run.

This script is intentionally read-only with respect to test artifacts: it reads
the CU coverage JSON/JUnit XML and writes a separate Markdown triage summary.
Use it after simulator or real-server runs to classify failures, blocked tests,
Not Supported CUs, and suspicious skip reasons before deciding whether an issue
belongs to the server, the server capability profile, or the Test Client.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import xml.etree.ElementTree as ET  # nosec B405
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_NOT_APPLICABLE = "Not Applicable"

# Bandit B405/B314 suppressions are limited to trusted pytest JUnit XML.

_REVIEW_REASON_PATTERNS = [
    re.compile(r"\bmethod not found\b", re.IGNORECASE),
    re.compile(r"\bnot found\b", re.IGNORECASE),
    re.compile(r"\bno .*found\b", re.IGNORECASE),
    re.compile(r"\bnot registered\b", re.IGNORECASE),
    re.compile(r"\buaerror\b", re.IGNORECASE),
    re.compile(r"\btimed out\b|\btimeout\b", re.IGNORECASE),
    re.compile(r"\bcannot test\b", re.IGNORECASE),
    re.compile(r"\bskipping\b", re.IGNORECASE),
]


@dataclass(frozen=True)
class JUnitCase:
    name: str
    classname: str
    status: str
    message: str

    @property
    def display_name(self) -> str:
        return f"{self.classname}.{self.name}" if self.classname else self.name


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: CU compliance JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: CU compliance JSON is not valid JSON: {path}: {exc}") from exc


def _text(elem: ET.Element | None) -> str:
    if elem is None:
        return ""
    parts = []
    if elem.text:
        parts.append(elem.text.strip())
    for child in elem:
        if child.text:
            parts.append(child.text.strip())
        if child.tail:
            parts.append(child.tail.strip())
    return "\n".join(part for part in parts if part)


def _parse_junit(path: Path | None) -> list[JUnitCase]:
    if path is None or not path.exists():
        return []
    tree = ET.parse(path)  # nosec B314
    root = tree.getroot()
    suites = root.findall(".//testsuite") if root.tag == "testsuites" else [root]

    cases: list[JUnitCase] = []
    for suite in suites:
        for tc in suite.findall("testcase"):
            name = tc.get("name", "")
            classname = tc.get("classname", "")
            failure = tc.find("failure")
            error = tc.find("error")
            skipped = tc.find("skipped")
            if failure is not None:
                status = "failed"
                message = failure.get("message") or _text(failure)
            elif error is not None:
                status = "error"
                message = error.get("message") or _text(error)
            elif skipped is not None:
                status = "xfailed" if (skipped.get("type") or "").lower() == "pytest.xfail" else "skipped"
                message = skipped.get("message") or _text(skipped)
            else:
                status = "passed"
                message = ""
            cases.append(JUnitCase(name=name, classname=classname, status=status, message=message.strip()))
    return cases


def _bucket_reason(reason: str) -> str:
    if not reason:
        return "no reason"
    first_line = reason.strip().splitlines()[0]
    if first_line.startswith("("):
        try:
            parsed = ast.literal_eval(first_line)
        except (SyntaxError, ValueError):
            parsed = None
        if isinstance(parsed, tuple) and len(parsed) >= 3:
            first_line = str(parsed[2])
    first_line = re.sub(r"^Skipped:\s*", "", first_line, flags=re.IGNORECASE)
    first_line = re.split(r"\s+[—(]", first_line, maxsplit=1)[0].strip()
    return first_line[:120] or "no reason"


def _md_cell(value: object) -> str:
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")[:240]


def _test_lookup(tests: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(test.get("nodeid", "")): test for test in tests}


def _cu_rows(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    by_cu = payload.get("by_cu", {})
    if not isinstance(by_cu, dict):
        return []
    return sorted((str(cu), data) for cu, data in by_cu.items() if isinstance(data, dict))


def _cu_compliance(data: dict[str, Any]) -> str:
    return str(data.get("compliance") or data.get("outcome") or "unknown")


def _compliance_counts(rows: list[tuple[str, dict[str, Any]]]) -> Counter[str]:
    return Counter(_cu_compliance(data) for _cu, data in rows)


def _tests_by_outcome(tests: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for test in tests:
        grouped[str(test.get("outcome", "unknown"))].append(test)
    return grouped


def _tests_for_cu(data: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    tests = []
    for nodeid in data.get("tests", []) or []:
        entry = lookup.get(str(nodeid))
        if entry is not None:
            tests.append(entry)
    return tests


def _review_flags(payload: dict[str, Any]) -> list[tuple[str, str, str]]:
    lookup = _test_lookup(payload.get("tests", []) if isinstance(payload.get("tests"), list) else [])
    flags: list[tuple[str, str, str]] = []
    supported = set(payload.get("supported_cus") or [])

    for cu_key, data in _cu_rows(payload):
        compliance = _cu_compliance(data)
        passed = int(data.get("passed", 0) or 0)
        blocked = int(data.get("blocked", 0) or 0)
        not_supported = int(data.get("not_supported", 0) or 0)
        test_count = int(data.get("test_count", 0) or 0)

        if compliance == "untested" or test_count == 0:
            flags.append((cu_key, "missing-test", "No collected test path for this CU."))
        if passed and blocked:
            flags.append((cu_key, "mixed-pass-blocked", f"{passed} passed and {blocked} blocked tests."))
        if passed and not_supported:
            flags.append(
                (cu_key, "mixed-pass-not-supported", f"{passed} passed and {not_supported} Not Supported tests.")
            )
        if cu_key in supported and compliance == "not_supported":
            flags.append(
                (cu_key, "supported-but-not-supported", "CU is listed as supported but reports Not Supported.")
            )
        if cu_key in supported and compliance == "blocked":
            flags.append((cu_key, "supported-but-blocked", "CU is listed as supported but reports Blocked."))

        for test in _tests_for_cu(data, lookup):
            outcome = str(test.get("outcome", ""))
            reason = str(test.get("reason", ""))
            if outcome in {"blocked", "not_supported"} and any(
                pattern.search(reason) for pattern in _REVIEW_REASON_PATTERNS
            ):
                flags.append((cu_key, f"{outcome}-reason-review", f"{test.get('nodeid')}: {_bucket_reason(reason)}"))

    return flags


def _render(payload: dict[str, Any], junit_cases: list[JUnitCase], source: Path, junit: Path | None) -> str:
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    tests = payload.get("tests", []) if isinstance(payload.get("tests"), list) else []
    grouped_tests = _tests_by_outcome(tests)
    cu_rows = _cu_rows(payload)
    cu_compliance = _compliance_counts(cu_rows)
    flags = _review_flags(payload)

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []
    lines.append("# IJT CU Compliance Triage")
    lines.append("")
    lines.append(f"- Generated: {generated}")
    lines.append(f"- CU JSON: `{source}`")
    if junit is not None:
        lines.append(f"- JUnit XML: `{junit}`" if junit.exists() else f"- JUnit XML: `{junit}` (not found)")
    lines.append(f"- Schema: `{payload.get('schema', 'unknown')}`")
    lines.append(f"- Test run exitstatus: `{payload.get('exitstatus', 'unknown')}`")
    lines.append("")

    lines.append("## Headline")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    for key in (
        "official_cu_count",
        "extension_cu_count",
        "collected_cu_test_count",
        "executed_cu_test_count",
        "workbook_case_count",
        "workbook_expected_case_count",
        "workbook_exact_case_count",
    ):
        lines.append(f"| `{key}` | {summary.get(key, _NOT_APPLICABLE)} |")
    missing = summary.get("missing_test_cus", [])
    lines.append(f"| `missing_test_cus` | {len(missing) if isinstance(missing, list) else _NOT_APPLICABLE} |")
    missing_workbook = summary.get("workbook_missing_case_cus", [])
    if isinstance(missing_workbook, list):
        lines.append(f"| `workbook_missing_case_cus` | {len(missing_workbook)} |")
    lines.append("")

    if int(summary.get("collected_cu_test_count", 0) or 0) == 0:
        lines.append(
            "> Review warning: this CU report has zero collected CU tests. It was probably produced by a unit-only run,"
        )
        lines.append("> a failed collection, or a pytest invocation that did not include `conformance`.")
        lines.append("")

    lines.append("## CU Compliance")
    lines.append("")
    lines.append("| Compliance | CU Count |")
    lines.append("|---|---:|")
    for compliance, count in sorted(cu_compliance.items()):
        lines.append(f"| `{compliance}` | {count} |")
    lines.append("")

    lines.append("## Test Outcomes")
    lines.append("")

    workbook = payload.get("workbook", {}) if isinstance(payload.get("workbook"), dict) else {}
    if workbook:
        lines.append("## Workbook Traceability")
        lines.append("")
        if workbook.get("error"):
            lines.append(f"- Error: `{_md_cell(workbook.get('error'))}`")
            lines.append("")
        else:
            lines.append("| Metric | Value |")
            lines.append("|---|---:|")
            for key in (
                "official_cu_count",
                "case_count",
                "expected_case_count",
                "exact_case_count",
            ):
                lines.append(f"| `{key}` | {workbook.get(key, _NOT_APPLICABLE)} |")
            lines.append(f"| `missing_case_cus` | {len(workbook.get('missing_case_cus', []) or [])} |")
            lines.append(f"| `mapping_precision` | {_md_cell(workbook.get('mapping_precision', 'Unknown'))} |")
            lines.append("")
            lines.append(
                "Workbook rows are linked to CU-marked tests by CU key. Tests can add "
                "`@pytest.mark.workbook_ref(sheet, rows)` for exact row-to-test mappings where needed."
            )
            lines.append("")
    lines.append("| Outcome | Test Count |")
    lines.append("|---|---:|")
    for outcome, entries in sorted(grouped_tests.items()):
        lines.append(f"| `{outcome}` | {len(entries)} |")
    lines.append("")

    if junit_cases:
        junit_counts = Counter(case.status for case in junit_cases)
        lines.append("## JUnit Outcomes")
        lines.append("")
        lines.append("| Outcome | Test Count |")
        lines.append("|---|---:|")
        for outcome, count in sorted(junit_counts.items()):
            lines.append(f"| `{outcome}` | {count} |")
        lines.append("")

    failure_tests = [*grouped_tests.get("failed", []), *grouped_tests.get("error", [])]
    if failure_tests:
        lines.append("## Failures And Errors")
        lines.append("")
        lines.append("| Outcome | Test | CUs |")
        lines.append("|---|---|---|")
        for test in failure_tests[:50]:
            lines.append(
                f"| `{_md_cell(test.get('outcome'))}` | `{_md_cell(test.get('nodeid'))}` | "
                f"{_md_cell(', '.join(test.get('cus', []) or []))} |"
            )
        if len(failure_tests) > 50:
            lines.append(f"| ... | {len(failure_tests) - 50} more | |")
        lines.append("")

    blocked_tests = grouped_tests.get("blocked", [])
    not_supported_tests = grouped_tests.get("not_supported", [])
    for title, entries in (("Blocked Tests", blocked_tests), ("Not Supported Tests", not_supported_tests)):
        if not entries:
            continue
        buckets = Counter(_bucket_reason(str(entry.get("reason", ""))) for entry in entries)
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Reason Bucket | Count |")
        lines.append("|---|---:|")
        for reason, count in buckets.most_common(25):
            lines.append(f"| {_md_cell(reason)} | {count} |")
        lines.append("")

    if flags:
        lines.append("## Strict Review Flags")
        lines.append("")
        lines.append("| CU | Flag | Detail |")
        lines.append("|---|---|---|")
        for cu_key, flag, detail in flags[:100]:
            lines.append(f"| `{_md_cell(cu_key)}` | `{_md_cell(flag)}` | {_md_cell(detail)} |")
        if len(flags) > 100:
            lines.append(f"| ... | ... | {len(flags) - 100} more flags not shown |")
        lines.append("")

    if missing:
        lines.append("## Missing Test CUs")
        lines.append("")
        for cu_key in missing[:200]:
            lines.append(f"- `{cu_key}`")
        lines.append("")

    lines.append("## Triage Policy")
    lines.append("")
    lines.append(
        "- `failed` / `error`: inspect first; classify as server defect, Test Client bug, or profile/config error."
    )
    lines.append("- `not_supported`: acceptable only for optional CUs not listed as supported by the active profile.")
    lines.append(
        "- `blocked`: acceptable only when a trigger, prerequisite, data source, or simulator capability is unavailable."
    )
    lines.append(
        "- `mixed-pass-blocked`: review manually because raw execution can include passing support coverage while "
        "one or more row intents still need a precondition or trigger."
    )
    lines.append("- `missing-test`: not acceptable for official CUs in the final compliance client.")
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cu-json", default="test-results/cu-coverage-report.json")
    parser.add_argument("--junit", default="test-results/pytest-live.xml")
    parser.add_argument("--out", default="test-results/cu-compliance-triage.md")
    parser.add_argument("--no-junit", action="store_true", help="Do not attempt to read JUnit XML")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    cu_json = Path(args.cu_json)
    junit = None if args.no_junit else Path(args.junit)
    payload = _load_json(cu_json)
    junit_cases = _parse_junit(junit)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_render(payload, junit_cases, cu_json, junit), encoding="utf-8")
    print(f"CU compliance triage written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
