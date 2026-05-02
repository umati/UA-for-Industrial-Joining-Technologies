"""
Pytest plugin for CU compliance reporting.

The conformance client needs more than a pass/fail console log. This recorder
maps collected tests to official conformance units and writes a generic JSON
artifact that downstream tooling can roll up by CU, facet, profile, controller,
device family, or vendor extension.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from helpers.workbook_traceability import workbook_ref_id, workbook_traceability_report

_TERMINAL_OUTCOME_RANK = {
    "failed": 0,
    "error": 1,
    "passed": 2,
    "not_supported": 3,
    "blocked": 4,
    "skipped": 5,
    "untested": 6,
}


def _marker_cus(item) -> list[str]:
    cus: list[str] = []
    for marker in item.iter_markers("requires_cu"):
        cus.extend(str(arg) for arg in marker.args)
    return sorted(set(cus))


def _normalize_rows(value) -> list[int]:
    if value is None:
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        rows: list[int] = []
        for part in value.split(","):
            token = part.strip()
            if not token:
                continue
            if "-" in token:
                start_text, end_text = token.split("-", 1)
                start = int(start_text.strip())
                end = int(end_text.strip())
                rows.extend(range(start, end + 1))
            else:
                rows.append(int(token))
        return rows
    return [int(row) for row in value]


def _marker_workbook_refs(item) -> list[dict[str, object]]:
    refs: list[dict[str, object]] = []
    for marker in item.iter_markers("workbook_ref"):
        sheet = marker.kwargs.get("sheet")
        rows = marker.kwargs.get("rows", marker.kwargs.get("row"))
        if marker.args:
            sheet = sheet or marker.args[0]
        if len(marker.args) > 1:
            rows = rows if rows is not None else marker.args[1]
        if not sheet:
            continue
        for row in _normalize_rows(rows):
            refs.append({"sheet": str(sheet), "row": row, "ref": workbook_ref_id(str(sheet), row)})
    return refs


def _skip_text(report) -> str:
    text = getattr(report, "longreprtext", "")
    if text:
        return str(text)
    longrepr = getattr(report, "longrepr", "")
    if isinstance(longrepr, (tuple, list)) and len(longrepr) >= 3:
        return str(longrepr[2])
    return str(longrepr)


def _classify_report(report) -> str:
    if report.failed:
        return "error" if report.when != "call" else "failed"
    if report.passed:
        return "passed"
    if report.skipped:
        reason = _skip_text(report)
        if "not declared supported" in reason or "Not Supported" in reason:
            return "not_supported"
        return "blocked"
    return "skipped"


def _rollup_outcome(outcomes: Iterable[str]) -> str:
    outcomes = list(outcomes)
    if not outcomes:
        return "untested"
    if "failed" in outcomes:
        return "failed"
    if "error" in outcomes:
        return "error"
    if "passed" in outcomes:
        return "passed"
    if all(outcome == "not_supported" for outcome in outcomes):
        return "not_supported"
    if "blocked" in outcomes:
        return "blocked"
    return min(outcomes, key=lambda outcome: _TERMINAL_OUTCOME_RANK.get(outcome, 99))


def _is_collect_only_session(session) -> bool:
    config = getattr(session, "config", None)
    option = getattr(config, "option", None)
    return bool(getattr(option, "collectonly", False))


class CuComplianceReportRecorder:
    """Collect pytest results as a CU compliance report and write a JSON artifact."""

    def __init__(self, *, root: Path, all_cus: Iterable[str], supported_cus: Iterable[str] | None):
        self.root = root
        self.all_cus = sorted(set(all_cus))
        self.supported_cus = None if supported_cus is None else sorted(set(supported_cus))
        self.items_by_nodeid: dict[str, dict] = {}
        self.results_by_nodeid: dict[str, dict] = {}
        configured = os.environ.get("IJT_CU_COMPLIANCE_REPORT_FILE")
        self.output_path = Path(configured) if configured else root / "test-results" / "cu-compliance-report.json"

    def pytest_collection_modifyitems(self, session, config, items):  # noqa: D401
        for item in items:
            cus = _marker_cus(item)
            if not cus:
                continue
            self.items_by_nodeid[item.nodeid] = {
                "nodeid": item.nodeid,
                "path": str(Path(str(item.fspath)).relative_to(self.root)),
                "name": item.name,
                "cus": cus,
                "workbook_refs": _marker_workbook_refs(item),
            }

    def pytest_runtest_logreport(self, report):  # noqa: D401
        if report.nodeid not in self.items_by_nodeid:
            return
        if report.when not in {"setup", "call", "teardown"}:
            return
        if report.when == "setup" and report.passed:
            return
        if report.when == "teardown" and report.passed:
            return
        if report.when == "teardown" and report.nodeid in self.results_by_nodeid:
            return

        outcome = _classify_report(report)
        if report.when == "setup" and outcome == "passed":
            return
        self.results_by_nodeid[report.nodeid] = {
            **self.items_by_nodeid[report.nodeid],
            "outcome": outcome,
            "phase": report.when,
            "duration_s": round(float(getattr(report, "duration", 0.0)), 6),
            "reason": _skip_text(report) if outcome in {"not_supported", "blocked"} else "",
        }

    def pytest_sessionfinish(self, session, exitstatus):  # noqa: D401
        if _is_collect_only_session(session) or not self.items_by_nodeid:
            return

        results = []
        for nodeid, item in self.items_by_nodeid.items():
            results.append(
                self.results_by_nodeid.get(
                    nodeid,
                    {
                        **item,
                        "outcome": "untested",
                        "phase": "collection",
                        "duration_s": 0.0,
                        "reason": "No pytest report was emitted for this collected CU test.",
                    },
                )
            )
        results.sort(key=lambda entry: entry["nodeid"])

        by_cu: dict[str, dict] = {}
        tests_by_cu: dict[str, list[dict]] = defaultdict(list)
        for entry in results:
            for cu_key in entry["cus"]:
                tests_by_cu[cu_key].append(entry)

        exact_refs_by_row: dict[str, set[str]] = defaultdict(set)
        for item in self.items_by_nodeid.values():
            for ref in item.get("workbook_refs", []):
                ref_id = str(ref.get("ref", ""))
                if ref_id:
                    exact_refs_by_row[ref_id].add(item["nodeid"])

        try:
            workbook = workbook_traceability_report(tests_by_cu=tests_by_cu, exact_refs_by_row=exact_refs_by_row)
        except Exception as exc:  # noqa: BLE001
            workbook = {
                "schema": "ijt-workbook-traceability/v1",
                "error": str(exc),
            }

        extension_cus = sorted(set(tests_by_cu) - set(self.all_cus))
        for cu_key in [*self.all_cus, *extension_cus]:
            tests = tests_by_cu.get(cu_key, [])
            outcomes = [test["outcome"] for test in tests]
            workbook_cu = workbook.get("by_cu", {}).get(cu_key, {}) if isinstance(workbook.get("by_cu"), dict) else {}
            by_cu[cu_key] = {
                "outcome": _rollup_outcome(outcomes),
                "test_count": len(tests),
                "workbook_case_count": int(workbook_cu.get("case_count", 0) or 0),
                "workbook_positive_case_count": int(workbook_cu.get("positive_case_count", 0) or 0),
                "workbook_negative_case_count": int(workbook_cu.get("negative_case_count", 0) or 0),
                "passed": outcomes.count("passed"),
                "failed": outcomes.count("failed"),
                "error": outcomes.count("error"),
                "not_supported": outcomes.count("not_supported"),
                "blocked": outcomes.count("blocked"),
                "skipped": outcomes.count("skipped"),
                "untested": outcomes.count("untested"),
                "tests": [test["nodeid"] for test in tests],
            }

        payload = {
            "schema": "ijt-cu-compliance-report/v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "exitstatus": int(exitstatus),
            "supported_cus": self.supported_cus,
            "summary": {
                "official_cu_count": len(self.all_cus),
                "extension_cu_count": len(extension_cus),
                "extension_cus": extension_cus,
                "collected_cu_test_count": len(self.items_by_nodeid),
                "executed_cu_test_count": len(self.results_by_nodeid),
                "missing_test_cus": [cu for cu, data in by_cu.items() if data["test_count"] == 0],
                "workbook_case_count": workbook.get("case_count"),
                "workbook_expected_case_count": workbook.get("expected_case_count"),
                "workbook_exact_case_count": workbook.get("exact_case_count"),
                "workbook_missing_case_cus": workbook.get("missing_case_cus"),
            },
            "workbook": workbook,
            "by_cu": by_cu,
            "tests": results,
        }
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
