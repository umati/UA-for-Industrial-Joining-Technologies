"""
Pytest plugin for CU coverage reporting.

The specification test client needs more than a pass/fail console log. This recorder
maps collected tests to official Conformance Units (CUs) and writes a generic JSON
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

import pytest

from helpers.canonical_outcomes import canonical_for_pytest_outcome, canonical_for_report_outcome
from helpers.cu_registry import format_cu_not_supported
from helpers.workbook_traceability import workbook_ref_id, workbook_traceability_report

INCOMPLETE_EXIT_CODE = 6


class WorkflowEvidenceUnavailable(pytest.skip.Exception):
    def __init__(self, reason: str, reason_code: str, outcome: str, workflow: str):
        super().__init__(reason)
        self.ijt_properties = {
            "ijt_reason_code": reason_code,
            "ijt_outcome": outcome,
            "ijt_workflow": workflow,
        }


def qualification_disposition(coverage: object) -> dict:
    """Judge claimed coverage, not merely pytest's successful execution."""
    if not isinstance(coverage, dict):
        return {"outcome": "incomplete", "issues": ["Malformed run-scoped CU coverage."]}
    rows = coverage.get("by_cu")
    if not isinstance(rows, dict) or not rows:
        return {"outcome": "incomplete", "issues": ["Missing run-scoped CU coverage."]}
    if any(not isinstance(key, str) or not isinstance(row, dict) for key, row in rows.items()):
        return {"outcome": "incomplete", "issues": ["Malformed run-scoped CU coverage."]}
    if not any(row.get("claimed") is True for row in rows.values()):
        return {"outcome": "incomplete", "issues": ["No claimed coverage was recorded."]}
    failed = []
    incomplete = []
    excluded = []
    for key, row in rows.items():
        if not row.get("claimed"):
            continue
        if row.get("scope_excluded", False):
            excluded.append(key)
        if row.get("failed", 0) or row.get("error", 0):
            failed.append(key)
        elif (
            row.get("scope_excluded", False)
            or row.get("compliance") != "supported"
            or type(row.get("passed")) is not int
            or row["passed"] < 1
        ):
            incomplete.append(key)
    for key in coverage.get("supported_cus") or ():
        if key not in rows:
            incomplete.append(key)
    pending = coverage.get("unreviewed_cus", [])
    if not isinstance(pending, list) or any(not isinstance(key, str) for key in pending):
        return {
            "outcome": "failed" if failed else "incomplete",
            "failed_cus": failed,
            "issues": ["Malformed unreviewed CU declarations."],
        }
    unreviewed = sorted(
        set(pending) | {key for key, row in rows.items() if row.get("declaration_state") == "unreviewed"}
    )
    return {
        "outcome": "failed" if failed else "incomplete" if incomplete or unreviewed else "passed",
        "failed_cus": failed,
        "incomplete_cus": incomplete,
        "scope_excluded_claimed_cus": excluded,
        "unreviewed_cus": unreviewed,
    }


_TERMINAL_OUTCOME_RANK = {
    "failed": 0,
    "error": 1,
    "passed": 2,
    "not_supported": 3,
    "blocked": 4,
    "accepted_policy": 5,
    "environment": 6,
    "skipped": 7,
    "untested": 8,
}


def _marker_cus(item) -> list[str]:
    cus: list[str] = []
    for marker in item.iter_markers("requires_cu"):
        cus.extend(str(arg) for arg in marker.args)
    return sorted(set(cus))


def _marker_dependency_cus(item) -> list[str]:
    cus: list[str] = []
    for marker in item.iter_markers("requires_dependency_cu"):
        cus.extend(str(arg) for arg in marker.args)
    return sorted(set(cus))


def _dependency_cus_for_not_supported_reason(reason: str, dependency_cus: Iterable[str]) -> list[str]:
    reason_lower = reason.lower()
    matches = [cu_key for cu_key in dependency_cus if format_cu_not_supported(cu_key).lower() in reason_lower]
    return sorted(set(matches))


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
        properties = dict(getattr(report, "user_properties", ()))
        if properties.get("ijt_outcome") in {"blocked", "untested", "environment"}:
            return properties["ijt_outcome"]
        reason = _skip_text(report)
        reason_lower = reason.lower()
        if "accepted policy" in reason_lower or "accepted as optional server behaviour" in reason_lower:
            return "accepted_policy"
        if "companion spec profile note" in reason_lower or "simulator regression limit" in reason_lower:
            return "accepted_policy"
        if (
            "environment" in reason_lower
            or "tooling limitation" in reason_lower
            or "service unavailable via this asyncua version" in reason_lower
            or "client-library limitation" in reason_lower
        ):
            return "environment"
        if "not listed as supported" in reason_lower or "not supported" in reason_lower:
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


def _rollup_compliance(outcomes: Iterable[str]) -> str:
    """Return the conservative user-facing CU compliance status.

    `outcome` stays an execution rollup for backward compatibility. `compliance`
    is the status report renderers should display: support can be present while
    still carrying notes, and unresolved blocked paths take precedence over
    Not Supported when no passing support path exists.
    """
    outcomes = list(outcomes)
    if not outcomes:
        return "untested"
    if "failed" in outcomes or "error" in outcomes:
        return "action_needed"
    if "passed" in outcomes and any(
        outcome in {"not_supported", "blocked", "skipped", "untested", "environment"} for outcome in outcomes
    ):
        return "partial"
    if "blocked" in outcomes:
        return "blocked"
    if "not_supported" in outcomes:
        return "not_supported"
    if "passed" in outcomes:
        return "supported"
    if "accepted_policy" in outcomes or "environment" in outcomes:
        return "blocked"
    if "untested" in outcomes:
        return "untested"
    return "unknown"


def _is_collect_only_session(session) -> bool:
    config = getattr(session, "config", None)
    option = getattr(config, "option", None)
    return bool(getattr(option, "collectonly", False))


class CuCoverageReportRecorder:
    """Collect pytest results as a CU coverage report and write a JSON artifact."""

    def __init__(
        self,
        *,
        root: Path,
        all_cus: Iterable[str],
        supported_cus: Iterable[str] | None,
        unreviewed_cus: Iterable[str] = (),
    ):
        self.root = root
        self.all_cus = sorted(set(all_cus))
        self.supported_cus = None if supported_cus is None else sorted(set(supported_cus))
        self.unreviewed_cus = sorted(set(unreviewed_cus))
        self.items_by_nodeid: dict[str, dict] = {}
        self.results_by_nodeid: dict[str, dict] = {}
        configured = os.environ.get("IJT_CU_COVERAGE_REPORT_FILE")
        self.output_path = Path(configured) if configured else root / "test-results" / "cu-coverage-report.json"

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
                "dependency_cus": _marker_dependency_cus(item),
                "workbook_refs": _marker_workbook_refs(item),
            }

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        result = yield
        report = result.get_result()
        properties = getattr(call.excinfo.value, "ijt_properties", None) if call.excinfo else None
        if isinstance(properties, dict):
            report.user_properties.extend(properties.items())

    def pytest_runtest_logreport(self, report):  # noqa: D401
        if report.nodeid not in self.items_by_nodeid:
            return
        if report.when not in {"setup", "call", "teardown"}:
            return
        if report.when == "setup" and report.passed:
            return
        if report.when == "teardown" and report.passed:
            return
        outcome = _classify_report(report)
        if report.when == "setup" and outcome == "passed":
            return
        previous = self.results_by_nodeid.get(report.nodeid)
        if previous and _TERMINAL_OUTCOME_RANK.get(previous["outcome"], 99) < _TERMINAL_OUTCOME_RANK.get(outcome, 99):
            return
        item = self.items_by_nodeid[report.nodeid]
        reason = _skip_text(report) if report.skipped else ""
        properties = dict(getattr(report, "user_properties", ()))
        cus = item["cus"]
        if outcome == "not_supported":
            dependency_cus = _dependency_cus_for_not_supported_reason(reason, item.get("dependency_cus", []))
            if dependency_cus:
                cus = dependency_cus
        self.results_by_nodeid[report.nodeid] = {
            **{key: value for key, value in item.items() if key != "dependency_cus"},
            "cus": cus,
            "outcome": outcome,
            "canonical_outcome": canonical_for_pytest_outcome(outcome, claimed=self._is_claimed(cus)).value,
            "phase": report.when,
            "duration_s": round(float(getattr(report, "duration", 0.0)), 6),
            "reason": reason,
            "reason_code": properties.get("ijt_reason_code", ""),
            "workflow": properties.get("ijt_workflow", ""),
            "scope_excluded": properties.get("ijt_scope_excluded") == "true",
        }

    def _is_claimed(self, cu_keys) -> bool:
        """True when the SUT manifest claims at least one of *cu_keys*."""
        if self.supported_cus is None:
            return False
        return any(cu_key in self.supported_cus for cu_key in cu_keys)

    def pytest_sessionfinish(self, session, exitstatus):  # noqa: D401
        if _is_collect_only_session(session) or not self.items_by_nodeid:
            return

        results = []
        for nodeid, item in self.items_by_nodeid.items():
            public_item = {key: value for key, value in item.items() if key != "dependency_cus"}
            results.append(
                self.results_by_nodeid.get(
                    nodeid,
                    {
                        **public_item,
                        "outcome": "untested",
                        "canonical_outcome": canonical_for_pytest_outcome(
                            "untested", claimed=self._is_claimed(public_item.get("cus", []))
                        ).value,
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
            claimed = bool(self.supported_cus is not None and cu_key in self.supported_cus)
            compliance = "untested" if cu_key in self.unreviewed_cus else _rollup_compliance(outcomes)
            workbook_cu = workbook.get("by_cu", {}).get(cu_key, {}) if isinstance(workbook.get("by_cu"), dict) else {}
            by_cu[cu_key] = {
                "outcome": _rollup_outcome(outcomes),
                "compliance": compliance,
                "canonical_outcome": canonical_for_report_outcome(compliance, claimed=claimed).value,
                "claimed": claimed,
                "declaration_state": "unreviewed" if cu_key in self.unreviewed_cus else "declared",
                "scope_excluded": bool(tests) and all(test.get("scope_excluded", False) for test in tests),
                "test_count": len(tests),
                "workbook_case_count": int(workbook_cu.get("case_count", 0) or 0),
                "workbook_positive_case_count": int(workbook_cu.get("positive_case_count", 0) or 0),
                "workbook_negative_case_count": int(workbook_cu.get("negative_case_count", 0) or 0),
                "passed": outcomes.count("passed"),
                "failed": outcomes.count("failed"),
                "error": outcomes.count("error"),
                "not_supported": outcomes.count("not_supported"),
                "blocked": outcomes.count("blocked"),
                "accepted_policy": outcomes.count("accepted_policy"),
                "environment": outcomes.count("environment"),
                "skipped": outcomes.count("skipped"),
                "untested": outcomes.count("untested"),
                "tests": [test["nodeid"] for test in tests],
            }

        payload = {
            "schema": "ijt-cu-coverage-report/v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "exitstatus": int(exitstatus),
            "supported_cus": self.supported_cus,
            "unreviewed_cus": self.unreviewed_cus,
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
        payload["qualification"] = qualification_disposition(payload)
        if os.environ.get("OPCUA_TARGET_SERVER_PROFILE") and int(exitstatus) == 0:
            disposition = payload["qualification"]["outcome"]
            if disposition != "passed":
                session.exitstatus = 1 if disposition == "failed" else INCOMPLETE_EXIT_CODE
                payload["exitstatus"] = int(session.exitstatus)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
