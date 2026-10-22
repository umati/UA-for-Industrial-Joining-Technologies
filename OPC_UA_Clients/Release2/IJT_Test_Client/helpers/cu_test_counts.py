"""Per-Conformance-Unit test counts for console, text and Markdown reports.

Single aggregation used by the target-server evidence summaries, the
``run_all_tests.py`` console output and the specification test Markdown
summary (GitHub Actions). Inputs are existing artifacts only:

* ``cu-coverage-report.json`` (schema ``ijt-cu-coverage-report/v1``) for
  per-test outcomes and their CU attribution;
* the pytest JUnit XML for the authoritative unique live test totals,
  including tests that carry no ``requires_cu`` marker.

Counting rules:

* Global totals count every test once. A test linked to several CUs adds one
  to each of those CU rows, so CU rows must never be summed into a total.
* A CU is *exercised* only when at least one linked test passed, failed or
  errored. Skip-type outcomes (not supported, blocked, accepted policy,
  environment, skipped) never count as exercised.
* ``failed`` is an assertion failure in the test call; ``error`` is a
  setup/teardown failure. Both are reported separately.

Output lines use ``key=value`` pairs on purpose: the repository root runner
parses child output with ``"<N> passed"`` / ``Checks:`` / ``Result:`` regexes,
and these lines must not change its aggregated test totals.
"""

from __future__ import annotations

import ast
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

from helpers.cu_registry import cu_display_name

EXECUTED_OUTCOMES: tuple[str, ...] = ("passed", "failed", "error")
SKIP_OUTCOMES: tuple[str, ...] = ("not_supported", "blocked", "accepted_policy", "environment", "skipped")
OUTCOME_KEYS: tuple[str, ...] = (*EXECUTED_OUTCOMES, *SKIP_OUTCOMES, "untested")

CATEGORY_EXERCISED = "exercised"
CATEGORY_SKIPPED_ONLY = "skipped_only"
CATEGORY_NOT_RUN = "not_run"
CATEGORY_NO_TESTS = "no_tests"
CATEGORY_ORDER: tuple[str, ...] = (CATEGORY_EXERCISED, CATEGORY_SKIPPED_ONLY, CATEGORY_NOT_RUN, CATEGORY_NO_TESTS)
CATEGORY_LABELS: dict[str, str] = {
    CATEGORY_EXERCISED: "Exercised",
    CATEGORY_SKIPPED_ONLY: "Skipped only",
    CATEGORY_NOT_RUN: "Not run",
    CATEGORY_NO_TESTS: "No tests",
}
OUTCOME_LABELS: dict[str, str] = {
    "passed": "Passed",
    "failed": "Failed",
    "error": "Error",
    "not_supported": "Not Supported",
    "blocked": "Blocked",
    "accepted_policy": "Accepted Policy",
    "environment": "Environment",
    "skipped": "Skipped",
    "untested": "Untested",
}
_REASON_MAX_LEN = 120
_REASONS_PER_CU = 2


@dataclass(frozen=True)
class CuTestCounts:
    """Test outcome counts for one CU; a test linked to several CUs appears in each."""

    cu_key: str
    name: str
    official: bool
    counts: dict[str, int]
    reasons: tuple[tuple[str, str, int], ...] = ()

    @property
    def tests(self) -> int:
        return sum(self.counts.values())

    @property
    def executed(self) -> int:
        return sum(self.counts[key] for key in EXECUTED_OUTCOMES)

    @property
    def skipped_total(self) -> int:
        return sum(self.counts[key] for key in SKIP_OUTCOMES)

    @property
    def failing(self) -> bool:
        return bool(self.counts["failed"] or self.counts["error"])

    @property
    def category(self) -> str:
        if self.tests == 0:
            return CATEGORY_NO_TESTS
        if self.executed:
            return CATEGORY_EXERCISED
        if self.skipped_total:
            return CATEGORY_SKIPPED_ONLY
        return CATEGORY_NOT_RUN


@dataclass(frozen=True)
class TestCountSummary:
    """Unique live test totals plus the per-CU breakdown for one run."""

    __test__ = False  # not a pytest test class

    junit: dict[str, int] | None
    cu_marked: dict[str, int]
    official_cu_count: int
    rows: tuple[CuTestCounts, ...] = field(default_factory=tuple)

    @property
    def cu_marked_tests(self) -> int:
        return sum(self.cu_marked.values())

    @property
    def cu_links(self) -> int:
        return sum(row.tests for row in self.rows)

    @property
    def unmarked_tests(self) -> int | None:
        if self.junit is None:
            return None
        return max(0, self.junit["tests"] - self.cu_marked_tests)

    def category_counts(self, *, official_only: bool = True) -> dict[str, int]:
        counts = dict.fromkeys(CATEGORY_ORDER, 0)
        for row in self.rows:
            if official_only and not row.official:
                continue
            counts[row.category] += 1
        return counts

    def rows_in(self, category: str) -> list[CuTestCounts]:
        return [row for row in self.rows if row.category == category]

    @property
    def failing_rows(self) -> list[CuTestCounts]:
        return [row for row in self.rows if row.failing]

    @property
    def extension_rows(self) -> list[CuTestCounts]:
        return [row for row in self.rows if not row.official]


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def parse_junit_totals(path: Path | str | None) -> dict[str, int] | None:
    """Return unique live test totals from a pytest JUnit XML, or ``None``.

    Each ``testcase`` element is one test; a test listed twice (for example a
    passing call followed by a teardown error) is counted once with its worst
    outcome (failed > error > skipped/xfailed > passed).
    """
    if path is None:
        return None
    xml_path = Path(path)
    if not xml_path.is_file():
        return None
    try:
        root = ET.parse(xml_path).getroot()
    except (ET.ParseError, DefusedXmlException, OSError):
        return None
    rank = {"failed": 0, "error": 1, "skipped": 2, "xfailed": 3, "passed": 4}
    worst: dict[tuple[str, str], str] = {}
    for testcase in root.iter("testcase"):
        if testcase.find("failure") is not None:
            outcome = "failed"
        elif testcase.find("error") is not None:
            outcome = "error"
        elif (skip := testcase.find("skipped")) is not None:
            outcome = "xfailed" if (skip.get("type") or "").lower() == "pytest.xfail" else "skipped"
        else:
            outcome = "passed"
        key = (testcase.get("classname", ""), testcase.get("name", ""))
        previous = worst.get(key)
        if previous is None or rank[outcome] < rank[previous]:
            worst[key] = outcome
    totals = Counter(worst.values())
    return {
        "tests": len(worst),
        "passed": totals["passed"],
        "failed": totals["failed"],
        "error": totals["error"],
        "skipped": totals["skipped"],
        "xfailed": totals["xfailed"],
    }


def junit_totals_from_parsed(data: dict[str, Any]) -> dict[str, int]:
    """Adapt ``make_specification_test_summary._parse`` output to junit totals."""
    totals = {
        "passed": int(data.get("passed", 0) or 0),
        "failed": int(data.get("failed", 0) or 0),
        "error": int(data.get("errors", 0) or 0),
        "skipped": int(data.get("skipped", 0) or 0),
        "xfailed": int(data.get("xfailed", 0) or 0),
    }
    return {"tests": sum(totals.values()), **totals}


def normalize_reason(text: str) -> str:
    """Return a compact one-line skip reason from a CU report ``reason`` field.

    Setup-phase skips are stored as ``str((path, lineno, "Skipped: ..."))``;
    only the message part is kept.
    """
    reason = str(text or "").strip()
    if reason.startswith("(") and reason.endswith(")"):
        try:
            parsed = ast.literal_eval(reason)
        except (ValueError, SyntaxError):
            parsed = None
        if isinstance(parsed, tuple) and parsed:
            reason = str(parsed[-1]).strip()
    reason = reason.removeprefix("Skipped: ").strip()
    reason = " ".join(reason.split())
    if len(reason) > _REASON_MAX_LEN:
        reason = reason[: _REASON_MAX_LEN - 1] + "…"
    return reason


def _outcome_of(test: dict[str, Any]) -> str:
    outcome = str(test.get("outcome") or "untested")
    return outcome if outcome in OUTCOME_KEYS else "untested"


def build_test_count_summary(
    cu_payload: dict[str, Any] | None,
    junit_totals: dict[str, int] | None = None,
) -> TestCountSummary | None:
    """Aggregate a ``cu-coverage-report.json`` payload into a :class:`TestCountSummary`."""
    if not isinstance(cu_payload, dict):
        return None
    tests = cu_payload.get("tests")
    by_cu = cu_payload.get("by_cu")
    if not isinstance(tests, list) or not isinstance(by_cu, dict):
        return None
    summary_block = cu_payload.get("summary") if isinstance(cu_payload.get("summary"), dict) else {}
    extension_keys = {str(key) for key in summary_block.get("extension_cus") or []}

    cu_marked: Counter[str] = Counter()
    per_cu: dict[str, Counter[str]] = {str(key): Counter() for key in by_cu}
    reasons: dict[str, Counter[tuple[str, str]]] = {str(key): Counter() for key in by_cu}
    seen: set[str] = set()
    for test in tests:
        if not isinstance(test, dict):
            continue
        nodeid = str(test.get("nodeid") or "")
        outcome = _outcome_of(test)
        if nodeid not in seen:
            seen.add(nodeid)
            cu_marked[outcome] += 1
        reason = normalize_reason(str(test.get("reason") or "")) if outcome in SKIP_OUTCOMES else ""
        for cu_key in test.get("cus") or []:
            key = str(cu_key)
            per_cu.setdefault(key, Counter())[outcome] += 1
            if reason:
                reasons.setdefault(key, Counter())[(outcome, reason)] += 1

    rows = [
        CuTestCounts(
            cu_key=key,
            name=cu_display_name(key),
            official=key not in extension_keys,
            counts={outcome: int(counter.get(outcome, 0)) for outcome in OUTCOME_KEYS},
            reasons=tuple(
                (outcome, reason, count)
                for (outcome, reason), count in reasons.get(key, Counter()).most_common(_REASONS_PER_CU)
            ),
        )
        for key, counter in per_cu.items()
    ]
    rows.sort(key=lambda row: (not row.official, row.name.lower(), row.cu_key))
    official_count = int(summary_block.get("official_cu_count") or sum(1 for row in rows if row.official))
    return TestCountSummary(
        junit=junit_totals,
        cu_marked={outcome: int(cu_marked.get(outcome, 0)) for outcome in OUTCOME_KEYS},
        official_cu_count=official_count,
        rows=tuple(rows),
    )


def load_test_count_summary(
    cu_json: Path | str | None,
    junit_xml: Path | str | None = None,
) -> TestCountSummary | None:
    """Load and aggregate run artifacts; returns ``None`` when the CU report is unusable."""
    if cu_json is None:
        return None
    path = Path(cu_json)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return build_test_count_summary(payload, parse_junit_totals(junit_xml))


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _pairs(values: dict[str, int], keys: tuple[str, ...], *, keep_zero: tuple[str, ...] = ()) -> str:
    return " ".join(f"{key}={values[key]}" for key in keys if values.get(key) or key in keep_zero)


def _junit_line(summary: TestCountSummary) -> str:
    junit = summary.junit
    if junit is None:
        return "Live tests (unique): unavailable (no JUnit XML)"
    keys = ("passed", "failed", "error", "skipped", "xfailed")
    return f"Live tests (unique): total={junit['tests']} " + _pairs(
        junit, keys, keep_zero=("passed", "failed", "error", "skipped")
    )


def _cu_marked_line(summary: TestCountSummary) -> str:
    unmarked = summary.unmarked_tests
    scope = f" (no CU marker: {unmarked})" if unmarked is not None else ""
    counts = _pairs(summary.cu_marked, OUTCOME_KEYS, keep_zero=("passed", "failed", "error"))
    return f"CU-marked tests: total={summary.cu_marked_tests}{scope} {counts}"


def _cu_category_line(summary: TestCountSummary) -> str:
    counts = summary.category_counts()
    line = f"CUs ({summary.official_cu_count} official): " + " ".join(
        f"{category}={counts[category]}" for category in CATEGORY_ORDER
    )
    extensions = summary.extension_rows
    if extensions:
        line += f" extension_cus={len(extensions)}"
    return line


def _cu_links_line(summary: TestCountSummary) -> str:
    return (
        f"CU test links: {summary.cu_links} (a test linked to several CUs is counted in each CU row; do not sum rows)"
    )


def _row_counts_text(row: CuTestCounts) -> str:
    return f"tests={row.tests} " + _pairs(row.counts, OUTCOME_KEYS, keep_zero=("passed",))


def _reason_text(row: CuTestCounts) -> str:
    return "; ".join(f"{OUTCOME_LABELS[outcome]} ({count}): {reason}" for outcome, reason, count in row.reasons)


def render_console_lines(summary: TestCountSummary, *, indent: str = "  ", failing_limit: int = 10) -> list[str]:
    """Compact console block: unique totals, CU-marked subset and CU categories."""
    lines = [
        _junit_line(summary),
        _cu_marked_line(summary),
        _cu_category_line(summary),
        _cu_links_line(summary),
    ]
    failing = summary.failing_rows
    if failing:
        lines.append(f"CUs with failed/error tests: {len(failing)}")
        for row in failing[:failing_limit]:
            lines.append(f"  {row.name}: tests={row.tests} failed={row.counts['failed']} error={row.counts['error']}")
        if len(failing) > failing_limit:
            lines.append(f"  … {len(failing) - failing_limit} more (see saved summary)")
    return [f"{indent}{line}" for line in lines]


def render_text_lines(summary: TestCountSummary) -> list[str]:
    """Full plain-text breakdown for saved reports."""
    lines = ["Test Counts", *render_console_lines(summary, failing_limit=len(summary.rows) or 1), ""]
    lines.append("Per-CU test counts (CU rows overlap; do not sum):")
    for row in summary.rows:
        suffix = "" if row.official else " [extension]"
        lines.append(f"  {row.name}{suffix} [{CATEGORY_LABELS[row.category]}]: {_row_counts_text(row)}")
    skipped_only = summary.rows_in(CATEGORY_SKIPPED_ONLY)
    lines.append("")
    lines.append(f"Skipped-only CUs ({len(skipped_only)}):")
    for row in skipped_only:
        lines.append(f"  {row.name}: {_reason_text(row) or 'no reason recorded'}")
    for category in (CATEGORY_NOT_RUN, CATEGORY_NO_TESTS):
        rows = summary.rows_in(category)
        if rows:
            lines.append("")
            lines.append(f"{CATEGORY_LABELS[category]} CUs ({len(rows)}): " + ", ".join(row.name for row in rows))
    lines.append("")
    return lines


def _md(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_markdown_overview_line(summary: TestCountSummary) -> str:
    """One-line Markdown digest separating unique tests from CU coverage."""
    junit = summary.junit
    if junit is None:
        tests_part = "**Live tests:** unavailable"
    else:
        tests_part = (
            f"**Live tests (unique):** {junit['tests']} — {junit['passed']} passed · "
            f"{junit['failed']} failed · {junit['error']} errors · {junit['skipped']} skipped"
        )
        if junit.get("xfailed"):
            tests_part += f" · {junit['xfailed']} xfailed"
    unmarked = summary.unmarked_tests
    marked_part = f"**CU-marked:** {summary.cu_marked_tests}"
    if unmarked:
        marked_part += f" ({unmarked} without CU marker)"
    counts = summary.category_counts()
    cu_part = (
        f"**CUs ({summary.official_cu_count}):** {counts[CATEGORY_EXERCISED]} exercised · "
        f"{counts[CATEGORY_SKIPPED_ONLY]} skipped only · {counts[CATEGORY_NOT_RUN]} not run · "
        f"{counts[CATEGORY_NO_TESTS]} without tests"
    )
    return f"{tests_part} · {marked_part} · {cu_part}"


def render_markdown_details(summary: TestCountSummary, *, open_details: bool = False) -> list[str]:
    """Collapsible per-CU Markdown table plus skipped-only CU reasons (no headings)."""
    lines = [
        "<details open>" if open_details else "<details>",
        f"<summary><b>Per-CU test counts</b> — {len(summary.rows)} CUs, "
        f"{summary.cu_marked_tests} CU-marked tests, {summary.cu_links} CU test links</summary>",
        "",
        "_A test linked to several CUs is counted in each CU row, so rows overlap and must not be summed. "
        "Exercised = at least one test passed, failed or errored; skips never count as exercised. "
        "Failed = test assertion failure; Error = setup/teardown failure._",
        "",
        "| CU | Status | Tests | Passed | Failed | Error | Not Supported | Blocked | Accepted Policy "
        "| Environment | Skipped | Untested |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.rows:
        name = row.name if row.official else f"{row.name} (extension)"
        counts = " | ".join(str(row.counts[key]) for key in OUTCOME_KEYS)
        lines.append(f"| {_md(name)} | {CATEGORY_LABELS[row.category]} | {row.tests} | {counts} |")
    skipped_only = summary.rows_in(CATEGORY_SKIPPED_ONLY)
    lines.extend(["", f"**Skipped-only CUs ({len(skipped_only)})**", ""])
    if skipped_only:
        lines.extend(["| CU | Tests | Main reasons |", "|---|---:|---|"])
        for row in skipped_only:
            lines.append(f"| {_md(row.name)} | {row.tests} | {_md(_reason_text(row) or 'no reason recorded')} |")
    else:
        lines.append("_None._")
    lines.extend(["", "</details>", ""])
    return lines
