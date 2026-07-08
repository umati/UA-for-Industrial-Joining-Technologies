"""Generate the IJT integration GitHub Actions summary."""

import datetime
import glob
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter

# defusedxml hardens xml.etree.ElementTree against XXE / billion-laughs even
# though stdlib expat does not fetch external DTDs by default. parse_xml_root
# below ALSO performs a manual byte-level DOCTYPE/entity rejection — defense
# in depth, validated by tests/reporting/test_xml_parser_xxe_guard.py.
from defusedxml import ElementTree as ET

try:
    from reporting._http import https_only_opener
    from reporting._table_padding import pad_table_rows
except ImportError:  # pragma: no cover - standalone: python3 reporting/X.py
    from _http import https_only_opener  # type: ignore[no-redef]
    from _table_padding import pad_table_rows  # type: ignore[no-redef]


def _urlopen(request, timeout):
    """HTTPS-only urlopen wrapper; tests can monkeypatch this seam.

    Goes through ``https_only_opener()`` so any non-https URL raises
    ``urllib.error.URLError`` at the protocol layer (no http/file handler).
    """
    return https_only_opener().open(request, timeout=timeout)


_HEADING_RE = re.compile(r"^(#{1,5})(\s)")


def shift_markdown_headings(markdown: str, by: int = 1) -> str:
    """Shift every Markdown heading down by ``by`` levels (clamped at H6).

    Used when embedding a standalone Markdown document (such as the Test
    Client specification test summary, whose top-level heading is ``# IJT
    Specification Test Report``) inside the System Tests run summary so its
    headings nest beneath the outer document. Fenced code blocks (``` ... ```
    or ~~~ ... ~~~) are left untouched.
    """
    out_lines: list[str] = []
    in_fence = False
    fence_marker = ""
    for line in markdown.splitlines(keepends=True):
        stripped = line.lstrip()
        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_fence = True
            fence_marker = stripped[:3]
            out_lines.append(line)
            continue
        if in_fence:
            if stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = ""
            out_lines.append(line)
            continue
        match = _HEADING_RE.match(line)
        if match:
            new_level = "#" * min(6, len(match.group(1)) + by)
            line = new_level + match.group(2) + line[match.end() :]
        out_lines.append(line)
    return "".join(out_lines)


def ensure_system_cus_anchor(markdown: str) -> str:
    """Inject the System Tests CUs anchor when the embedded artifact lacks it."""
    anchor = '<a id="system-cus-needing-review"></a>'
    if anchor in markdown:
        return markdown
    lines = markdown.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if re.match(r"^#{1,6}\s+📋\s+CUs Needing Review\b", line):
            lines.insert(index, anchor + "\n\n")
            return "".join(lines)
    return markdown


def load_test_client_conformance_summary(path: str) -> list[str]:
    """Return the embedded Test Client specification test summary as Markdown lines.

    Reads ``path`` (typically
    ``all-results/results-testclient/summary.md``), shifts every heading
    down by one level so the artifact's ``# IJT Specification Test Report``
    nests beneath the System Tests H1, and returns the result split into
    lines (no trailing newlines). Returns an empty list when the file is
    missing or empty.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, FileNotFoundError):
        return []
    if not text.strip():
        return []
    return shift_markdown_headings(ensure_system_cus_anchor(text)).splitlines()


def tc_conformance_artifact_warning(
    tc_result: str, summary_lines: list[str], path: str
) -> str | None:
    """Return a warning when test-client succeeded but the spec-test artifact is missing.

    The Test Client `summary.md` is the only path for the specification test block
    to reach the aggregated System Tests summary when the test-client step
    runs with ``--github-summary=never``. A silent drop on success therefore
    hides regressions; surface it as an artifact warning. When the lane
    itself failed the failure status is the signal, so no warning is emitted.
    """
    if tc_result != "success":
        return None
    if summary_lines:
        return None
    return (
        f"⚠️ **Test Client specification test summary**: artifact missing or empty at "
        f"`{path}` — specification test block omitted from the rendered summary"
    )


# ── Parsers ──────────────────────────────────────────────────────


def parse_xml_root(path):
    """Parse a local CI XML artifact without allowing entity injection.

    Vitest's cobertura coverage emitter writes a bare external DOCTYPE pointing
    at ``http://cobertura.sourceforge.net/xml/coverage-04.dtd``. The Python
    standard-library ``xml.etree.ElementTree`` parser does **not** fetch
    external DTDs and does **not** expand external entity references, so a
    bare ``<!DOCTYPE name SYSTEM "url">`` carries no XXE risk. We therefore
    accept that shape and reject only the actual injection vectors:

    * ``<!ENTITY ...>`` declarations (entity-expansion / billion-laughs).
    * Internal-subset DOCTYPE forms (``<!DOCTYPE name [ ... ]>``) which are
      the standard place to declare entities.
    """
    with open(path, "rb") as fh:
        payload = fh.read()
    lowered_payload = payload.lower()
    if b"<!entity" in lowered_payload:
        raise ValueError("DTD/entity declarations are not supported in CI XML artifacts")
    doctype_index = lowered_payload.find(b"<!doctype")
    while doctype_index != -1:
        end_index = lowered_payload.find(b">", doctype_index)
        bracket_index = lowered_payload.find(b"[", doctype_index)
        if end_index == -1:
            raise ValueError("Unterminated DOCTYPE is not supported in CI XML artifacts")
        if bracket_index != -1 and (end_index == -1 or bracket_index < end_index):
            raise ValueError("DTD/entity declarations are not supported in CI XML artifacts")
        doctype_index = lowered_payload.find(b"<!doctype", end_index + 1)
    # defusedxml's fromstring rejects entity declarations and external DTD
    # refs at the parser level; the byte-level guard above catches them
    # before parsing for an unambiguous error message and as a second layer.
    return ET.fromstring(payload)


def iter_suites(root):
    """Return all testsuite nodes for both bare and nested JUnit XML."""
    return [root] if root.tag == "testsuite" else root.findall(".//testsuite")


def parse_junit(pattern):
    total = passed = failed = skipped = 0
    found = False
    for path in glob.glob(pattern, recursive=True):
        try:
            root = parse_xml_root(path)
            suites = iter_suites(root)
            t = sum(int(s.get("tests", 0)) for s in suites)
            f = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
            sk = sum(int(s.get("skipped", 0)) for s in suites)
            total += t
            passed += t - f - sk
            failed += f
            skipped += sk
            found = True
        except Exception as exc:
            print(f"[WARN] parse_junit({path}): {exc}")
    if found:
        return total, passed, failed, skipped
    return None, None, None, None


def collect_skips(pattern):
    """Extract skipped test names and reasons from JUnit XML."""
    skips_list = []
    for path in glob.glob(pattern, recursive=True):
        try:
            root = parse_xml_root(path)
            for tc in root.findall(".//testcase"):
                el = tc.find("skipped")
                if el is not None:
                    name = tc.get("name", "unknown")
                    msg = (el.get("message") or el.text or "").split("\n")[0][:200]
                    skips_list.append((name, msg or "no reason given"))
        except Exception as exc:
            print(f"[WARN] collect_skips({path}): {exc}")
    return skips_list


# Numeric perf properties produced by the live perf tests. Required fields
# must all be present for a lane to be rendered. Threshold fields are
# optional — when absent the renderer hides the target/Pass-Fail column.
_PERF_REQUIRED_FIELDS = (
    "perf_sample_count",
    "perf_mean_total_ms",
    "perf_p90_total_ms",
    "perf_min_total_ms",
    "perf_max_total_ms",
)
_PERF_OPTIONAL_FIELDS = ("perf_threshold_mean_ms", "perf_threshold_p90_ms")


def plural_label(count: int, singular: str, plural: str | None = None) -> str:
    """Return a count plus a correctly pluralized public label."""
    label = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {label}"


def load_perf_benchmarks(pattern: str) -> dict[str, float] | None:
    """Return aggregated `perf_*` JUnit properties for the lane matched by ``pattern``.

    The live perf tests publish their result-transfer benchmark via
    ``record_property("perf_*", ...)``. JUnit XML stores these as
    ``<properties><property name="perf_…" value="…"/></properties>`` either
    at the ``<testsuite>`` level (when ``junit_family=xunit2``) or inside an
    individual ``<testcase>``. We accept both shapes and return the first
    file whose properties cover every required field. Returns ``None`` when
    no matching file or no complete property set is found, so the renderer
    can simply omit the lane row.

    Values are returned as ``float`` (the JUnit XML payload is a string in
    every case). ``perf_sample_count`` is integral by contract but typed as
    ``float`` here so a single mapping shape can carry every metric — the
    renderer formats it back to an integer string.
    """
    for path in sorted(glob.glob(pattern, recursive=True)):
        try:
            root = parse_xml_root(path)
        except Exception as exc:
            print(f"[WARN] load_perf_benchmarks({path}): {exc}")
            continue
        for property_holder in (*root.findall(".//testcase"), *iter_suites(root), root):
            properties = property_holder.find("properties")
            if properties is None:
                continue
            collected: dict[str, float] = {}
            for prop in properties.findall("property"):
                name = prop.get("name", "")
                value = prop.get("value", "")
                if name in _PERF_REQUIRED_FIELDS or name in _PERF_OPTIONAL_FIELDS:
                    try:
                        collected[name] = float(value)
                    except (TypeError, ValueError):
                        continue
            if all(field in collected for field in _PERF_REQUIRED_FIELDS):
                return collected
    return None


def render_perf_section(lanes: list[tuple[str, dict[str, float]]]) -> list[str]:
    """Render the compact `⏱️ Performance Benchmarks` block as Markdown lines.

    ``lanes`` is a list of ``(label, metrics)`` pairs where ``metrics`` is
    the mapping returned by :func:`load_perf_benchmarks`. Returns an empty
    list when no lane has metrics, so the caller can splat the result into
    the outer document without an extra ``if`` branch.

    Layout:

    * One H3 + a one-row header summarising what is measured.
    * One row per benchmark with sample count and min/average/max in milliseconds.
    * A trailing Pass/Fail pill when both ``perf_threshold_mean_ms`` and
      ``perf_threshold_p90_ms`` are present; the target column stays compact
      while the internal gate still checks both average and the 90% sample bound.

    The renderer never writes free-form prose — the specification test block above
    already explains how to read latency tables. Keeping this section
    tight is what lets it live inside the single System Tests Report step
    summary without re-creating the fragmented layout this change fixes.
    """
    present = [(label, metrics) for label, metrics in lanes if metrics]
    if not present:
        return []
    out: list[str] = [
        '<a id="system-performance-benchmarks"></a>',
        "",
        f"### ⏱️ Performance Benchmarks — {plural_label(len(present), 'benchmark')}",
        "",
        "| Benchmark | Samples | min (ms) | average (ms) | max (ms) | Target | Result |",
        "|:----------|--------:|---------:|-------------:|---------:|:-------|:------:|",
    ]
    for label, metrics in present:
        samples = int(metrics["perf_sample_count"])
        mean_ms = metrics["perf_mean_total_ms"]
        p90_ms = metrics["perf_p90_total_ms"]
        min_ms = metrics["perf_min_total_ms"]
        max_ms = metrics["perf_max_total_ms"]
        threshold_mean = metrics.get("perf_threshold_mean_ms")
        threshold_p90 = metrics.get("perf_threshold_p90_ms")
        if threshold_mean is not None and threshold_p90 is not None:
            target_cell = (
                f"Average &lt; {threshold_mean:.0f} ms · 90% of samples &lt; {threshold_p90:.0f} ms"
            )
            target_met = mean_ms < threshold_mean and p90_ms < threshold_p90
            result_cell = "✅ Pass" if target_met else "❌ Fail"
        else:
            target_cell = "—"
            result_cell = "—"
        out.append(
            f"| {md_cell(label)} | {samples} | {min_ms:.2f} | {mean_ms:.2f} | "
            f"{max_ms:.2f} | {target_cell} | {result_cell} |"
        )
    out.append("")
    out.append(
        "_TOTAL = end of joining operation → client callback. The visible table shows "
        "min, average, and max latency. The Pass/Fail gate also requires at least "
        "90% of samples to stay below the target. Per-sample timing pipeline details "
        "are recorded in JUnit XML test artifacts._"
    )
    return out


def md_cell(value):
    """Escape text for a GitHub markdown table cell."""
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    return text.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def lane_status_fmt(status: str) -> str:
    """Render lane status as text followed by an icon (legacy callers)."""
    if status == "success":
        return "Success ✅"
    if status == "failure":
        return "Failure ❌"
    if status == "skipped":
        return "Skipped ⏭️"
    return "Unknown ⚠️"


# Reusable cell constants for "not relevant for this lane" semantics.
_CELL_NOT_APPLICABLE_INT = "➖ Not Applicable"


_STATUS_TEXT = {
    "success": "Success",
    "failure": "Failure",
    "failed": "Failed",
    "skipped": "Skipped",
    "cancelled": "Cancelled",
    "recorded": "Recorded",
    "missing": "Missing",
    "unknown": "Unknown",
}


def status_text(status: str) -> str:
    """Return the user-facing title-case label for a workflow/test status."""
    text = str(status or "unknown")
    return _STATUS_TEXT.get(
        text,
        " ".join(part.capitalize() for part in text.replace("_", " ").split()) or "Unknown",
    )


def lane_status_icon(status: str) -> str:
    """Lane status icon for the leading status column of Lane Results."""
    return {
        "success": "✅",
        "failure": "❌",
        "skipped": "⏭️",
        "cancelled": "🚫",
    }.get(status, "⚠️")


def lane_status_text(status: str) -> str:
    """Plain-text lane outcome (no icon) for the Result column of Lane Results."""
    return status_text(
        status if status in {"success", "failure", "skipped", "cancelled"} else "unknown"
    )


def component_row_icon(*sources) -> str:
    """Derive the leading status icon for a Component Test Results row.

    Priority: ❌ failures > 🚫 cancelled > ⚠️ explicit gap flag in notes > ⏭️ any skips > ✅.

    A row that ran cleanly with no skips gets ✅. Any skipped sub-tests
    demote the row to ⏭️ so the reader sees the gap at a glance; the
    Skipped/Notes columns carry the detail. ⚠️ is reserved for explicit
    gap flags inside a notes string (e.g., missing artifact, advisory).

    Accepted sources:
      * counts tuple ``(total, passed, failed, skipped)``
      * notes string — substring ``❌`` ⇒ ❌, ``🚫`` ⇒ 🚫, ``⚠️`` ⇒ ⚠️, ``⏭️`` ⇒ ⏭️
      * ``None`` — ignored (no data point in this column)
    """
    has_fail = False
    has_cancel = False
    has_warn = False
    has_skip = False
    for src in sources:
        if src is None:
            continue
        if isinstance(src, (tuple, list)) and len(src) >= 4:
            failed = src[2]
            skipped = src[3]
            if failed and failed > 0:
                has_fail = True
            if skipped and skipped > 0:
                has_skip = True
        elif isinstance(src, str):
            if "❌" in src:
                has_fail = True
            elif "🚫" in src:
                has_cancel = True
            elif "⚠️" in src:
                has_warn = True
            elif "⏭️" in src:
                has_skip = True
    if has_fail:
        return "❌"
    if has_cancel:
        return "🚫"
    if has_warn:
        return "⚠️"
    if has_skip:
        return "⏭️"
    return "✅"


def perf_status_fmt(status: str) -> str:
    """Render performance timing status as text followed by an icon.

    Accepts both GitHub workflow-job conclusions (``success``, ``failure``,
    ``skipped``, ``cancelled``) and synthetic markers used for non-job timing
    sources (``recorded``, ``missing``).
    """
    if status == "success":
        return "Passed ✅"
    if status == "failure":
        return "Failed ❌"
    if status == "cancelled":
        return "Cancelled ⚪"
    if status == "skipped":
        return "Skipped ⏭️"
    if status == "recorded":
        return "Recorded 📊"
    if status == "missing":
        return "Missing ⚠️"
    return "Unknown ⚠️"


def format_skip_section(label, skips_list, skip_count=None):
    """Collapsible markdown section with skip reasons grouped by count."""
    reported_count = skip_count if skip_count is not None else len(skips_list)
    if reported_count is not None:
        reported_count = max(reported_count, len(skips_list))
    if not skips_list and (reported_count is None or reported_count <= 0):
        return []
    reasons = Counter(msg for _, msg in skips_list)
    if reported_count is not None and reported_count > len(skips_list):
        reasons["Skip details unavailable in JUnit XML"] += reported_count - len(skips_list)
    lines = [
        "",
        f"<details><summary>⏭️ <b>{label}</b> — {reported_count} Skipped</summary>",
        "",
        "| Reason | Count |",
        "|:-------|------:|",
    ]
    for reason, count in reasons.most_common():
        lines.append(f"| {md_cell(reason)} | {count} |")
    lines += ["", "</details>"]
    return lines


def _test_client_diagnostic_category(reason: str) -> str:
    """Classify Test Client skip reasons for public grouped diagnostics."""
    normalized = str(reason or "").strip()
    reason_lower = normalized.lower()
    if reason_lower.startswith("companion spec profile note -") or reason_lower.startswith(
        "monitoring."
    ):
        return "companion"
    if "lifetimecounters" in reason_lower:
        return "companion"
    if reason_lower.startswith("tooling limitation -"):
        return "tooling"
    if (
        "asyncua addnodes service call unavailable" in reason_lower
        or "asyncua deletenodes service call unavailable" in reason_lower
    ):
        return "tooling"
    if reason_lower.startswith("simulator regression limit -"):
        return "simulator"
    if "simulatebulkresults" in reason_lower and (
        "badtoomanyoperations" in reason_lower or "concurrent access limit" in reason_lower
    ):
        return "simulator"
    if "simulatebulkevents" in reason_lower and (
        "badtoomanyoperations" in reason_lower or "subscription limit" in reason_lower
    ):
        return "simulator"
    if "present as a stub" in reason_lower and "compliant" in reason_lower:
        return "server_gap"
    if "not listed as supported by active server capability profile" in reason_lower:
        return "server_gap"
    if "not supported" in reason_lower:
        return "server_gap"
    if "optional method" in reason_lower and "absent" in reason_lower:
        return "server_gap"
    return "other"


def _diagnostic_details(title: str, reasons: Counter) -> list[str]:
    """Render one grouped diagnostic reason table."""
    if not reasons:
        return []
    skip_total = sum(reasons.values())
    lines = [
        "",
        f"<details><summary><b>{title}</b> — {plural_label(skip_total, 'skip')}</summary>",
        "",
        "| Reason | Count |",
        "|:-------|------:|",
    ]
    for reason, count in reasons.most_common():
        lines.append(f"| {md_cell(reason)} | {count} |")
    lines += ["", "</details>"]
    return lines


def format_test_client_diagnostic_sections(
    skips_list, skip_count=None
) -> tuple[list[str], list[str]]:
    """Return public Test Client diagnostic sections and separate companion-spec notes."""
    reported_count = skip_count if skip_count is not None else len(skips_list)
    if reported_count is not None:
        reported_count = max(reported_count, len(skips_list))
    if not skips_list and (reported_count is None or reported_count <= 0):
        return [], []

    grouped: dict[str, Counter] = {
        "tooling": Counter(),
        "simulator": Counter(),
        "companion": Counter(),
        "other": Counter(),
    }
    server_gap_count = 0
    for reason, count in Counter(msg for _, msg in skips_list).items():
        category = _test_client_diagnostic_category(reason)
        if category == "server_gap":
            server_gap_count += count
        else:
            grouped[category][reason] += count

    detailed_count = len(skips_list)
    if reported_count is not None and reported_count > detailed_count:
        grouped["other"]["Skip details unavailable in JUnit XML"] += reported_count - detailed_count

    diagnostic_lines: list[str] = []
    if server_gap_count:
        diagnostic_lines += [
            "",
            (
                "Server capability gaps are listed in "
                "[CUs Needing Review](#system-cus-needing-review) "
                f"above ({plural_label(server_gap_count, 'skip')} folded out of diagnostics)."
            ),
        ]
    diagnostic_lines += _diagnostic_details("Test Tooling Limitations", grouped["tooling"])
    diagnostic_lines += _diagnostic_details("Simulator Regression Limits", grouped["simulator"])
    diagnostic_lines += _diagnostic_details("Other Diagnostics", grouped["other"])

    companion_lines = _diagnostic_details("Companion Spec Profile Notes", grouped["companion"])
    return diagnostic_lines, companion_lines


def test_client_diagnostic_note(skips_list, skip_count=None, default="No additional notes"):
    """Short table note for grouped Test Client diagnostics."""
    if skips_list or (skip_count is not None and skip_count > 0):
        return "Capability and diagnostic notes grouped below"
    return default


def skip_note_inline(skips_list, skip_count=None, default="No additional notes"):
    """Short inline note for table Notes column."""
    if skips_list:
        reasons = Counter(msg for _, msg in skips_list)
        top = reasons.most_common(1)[0][0] if reasons else ""
        if len(reasons) == 1:
            return md_cell(top[:60])
        return f"{len(reasons)} skip reasons — see below"
    if skip_count is not None and skip_count > 0:
        return "Skip details unavailable in JUnit XML"
    return default


def load_integration_baseline(path="tests/baselines/integration-test-counts.json"):
    """Load the committed Integration test-count baseline."""
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        suites = payload.get("suites", {})
        if payload.get("schema_version") not in (1, 2) or not isinstance(suites, dict):
            raise ValueError("unsupported baseline schema")
        return payload, None
    except Exception as exc:
        return {"suites": {}, "skip_tolerance_default": 0}, (
            f"⚠️ **Integration baseline unavailable**: `{path}` could not be loaded "
            f"({md_cell(exc)}). Test-count deltas and skip drift warnings are disabled."
        )


def baseline_suite(baseline, key):
    entry = baseline.get("suites", {}).get(key)
    return entry if isinstance(entry, dict) else None


def format_count_delta(total, baseline):
    """Return a compact nonzero test-count delta such as (+3) or (-2)."""
    if total is None or not baseline:
        return ""
    try:
        expected = int(baseline.get("tests"))
    except (TypeError, ValueError):
        return ""
    delta = total - expected
    return "" if delta == 0 else f" ({delta:+d})"


def integration_drift_warnings(baseline, suite_counts, run_id):
    """Build non-failing warnings for test-count and skip-count drift."""
    warnings = []
    default_tolerance = int(baseline.get("skip_tolerance_default", 0) or 0)
    drift_policy = baseline.get("drift_policy", {})
    drift_mode = drift_policy.get("mode", "exact")
    growth_warn_pct = int(drift_policy.get("growth_warn_percent", 25))
    growth_warn_abs = int(drift_policy.get("growth_warn_absolute", 50))

    for key, label, counts in suite_counts:
        entry = baseline_suite(baseline, key)
        if not entry or counts[0] is None:
            continue
        total, _passed, _failed, skipped = counts
        # Support both legacy "tests" and new "min_tests" field names
        expected_tests = entry.get("min_tests") or entry.get("tests")
        if expected_tests is not None:
            expected_tests = int(expected_tests)
            delta = total - expected_tests

            if drift_mode == "minimum":
                # Negative drift: always warn (tests disappeared)
                if delta < 0:
                    reanchor_command = (
                        f"python tests/tools/update_integration_baseline.py --run {run_id} "
                        f"--suite {key}"
                    )
                    warnings.append(
                        f"⚠️ **{label}**: {total:,} tests ({delta:+d} vs minimum "
                        f"{expected_tests:,}) — tests may have disappeared."
                        f" Investigate and re-anchor with `{reanchor_command}`."
                    )
                # Suspicious positive drift: warn if growth exceeds threshold
                elif delta > max(growth_warn_abs, expected_tests * growth_warn_pct // 100):
                    reanchor_command = (
                        f"python tests/tools/update_integration_baseline.py --run {run_id} "
                        f"--suite {key}"
                    )
                    warnings.append(
                        f"⚠️ **{label}**: {total:,} tests ({delta:+d} vs baseline "
                        f"{expected_tests:,}) — unusually large increase; check "
                        f"parametrization/discovery. Re-anchor with `{reanchor_command}`."
                    )
                # Normal positive drift: silent, no action needed
            else:
                # Legacy exact mode: any drift warns
                if delta != 0:
                    reanchor_command = (
                        f"python tests/tools/update_integration_baseline.py --run {run_id} "
                        f"--suite {key}"
                    )
                    warnings.append(
                        f"⚠️ **{label}**: {total:,} tests ({delta:+d} vs baseline "
                        f"{int(expected_tests):,}) — investigate suite collection drift."
                        f" After review, re-anchor with `{reanchor_command}`."
                    )

        expected_skips = entry.get("skipped")
        if expected_skips is None or skipped is None:
            continue
        tolerance = int(entry.get("skip_tolerance", default_tolerance) or 0)
        skip_delta = skipped - int(expected_skips)
        if skip_delta > tolerance:
            reanchor_command = (
                f"python tests/tools/update_integration_baseline.py --run {run_id} --suite {key}"
            )
            warnings.append(
                f"⚠️ **{label}**: {skipped:,} skipped ({skip_delta:+d} vs baseline "
                f"{int(expected_skips):,}; tolerance +{tolerance}) — investigate skip drift."
                f" After review, re-anchor with `{reanchor_command}`."
            )
    return warnings


# Suite keys whose JUnit XML must report zero skipped tests. Smoke and unit
# suites must always run their full case set; any skip there is a regression.
# All conformance / live / OPC UA Security suites legitimately skip cases when
# a CU, server target, or security identity is intentionally not exercised, so
# they are NOT listed here and never trip this gate.
_MUST_NOT_SKIP_SUITE_KEYS = frozenset({"sd_smoke", "wd_py", "wd_js", "tc_smoke"})


def must_not_skip_failures(suite_counts):
    """Build hard failures for skips in suites that must never skip.

    Only smoke and unit suites are gated here. Conformance, live, and OPC UA
    Security suites have legitimate conditional skips and are excluded so the
    Summary gate does not flag normal Not-Implemented / Not-Supported coverage.
    """
    failures = []
    for key, label, counts in suite_counts:
        if key not in _MUST_NOT_SKIP_SUITE_KEYS or counts[3] is None:
            continue
        skipped = int(counts[3])
        if skipped:
            failures.append(
                f"❌ **{label}**: {skipped:,} skipped — smoke and unit suites "
                "must run their full case set; conditional skips belong only "
                "in conformance, live, and OPC UA Security suites."
            )
    return failures


def seconds(value):
    """Parse a timing-artifact duration as float seconds."""
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def format_duration(value):
    """Format seconds compactly for the GitHub Actions summary."""
    value = seconds(value)
    if value >= 60.0:
        return f"{value / 60.0:.1f} min"
    return f"{value:.1f} s"


def format_optional_duration(value):
    """Format an optional duration; running jobs have no completed duration yet."""
    return "—" if value is None else format_duration(value)


def parse_actions_time(value):
    """Parse an Actions API timestamp into a timezone-aware datetime."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def next_link(header):
    """Return the next pagination URL from a GitHub Link header."""
    for part in str(header or "").split(","):
        pieces = [piece.strip() for piece in part.split(";")]
        if len(pieces) < 2 or pieces[1] != 'rel="next"':
            continue
        target = pieces[0]
        if target.startswith("<") and target.endswith(">"):
            return target[1:-1]
    return None


def job_durations(path):
    """Load completed current-run job durations, excluding this report job."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not path or not token:
        return []
    report_job_name = os.environ.get("REPORT_JOB_NAME", "").strip()
    api_root = (
        os.environ.get("GH_API_URL") or os.environ.get("GITHUB_API_URL") or "https://api.github.com"
    ).rstrip("/")
    url = f"{api_root}/{path.lstrip('/')}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "ijt-integration-report",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    rows = []
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
                for job in payload.get("jobs", []):
                    name = str(job.get("name") or "unknown")
                    if report_job_name and name == report_job_name:
                        continue
                    started = parse_actions_time(job.get("started_at"))
                    completed = parse_actions_time(job.get("completed_at"))
                    duration = None
                    if started and completed:
                        duration = max((completed - started).total_seconds(), 0.0)
                    if duration is None and job.get("status") != "completed":
                        continue
                    rows.append(
                        (
                            name,
                            duration,
                            str(job.get("conclusion") or job.get("status") or "unknown"),
                        )
                    )
                url = next_link(response.headers.get("Link"))
    except Exception as exc:
        print(f"[WARN] job_durations({path}): {exc}")
        return []
    return sorted(rows, key=lambda row: (row[1] is None, -(row[1] or 0.0), row[0]))


def browser_feature_timings(pattern):
    """Load Web Client Browser Features stage timing artifacts."""
    rows = []
    for path in sorted(glob.glob(pattern, recursive=True)):
        try:
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception as exc:
            print(f"[WARN] browser_feature_timings({path}): {exc}")
            continue

        shard = "full"
        for component in path.replace("\\", "/").split("/"):
            if component.endswith("-shard-1of2"):
                shard = "1/2"
                break
            if component.endswith("-shard-2of2"):
                shard = "2/2"
                break

        stages = {
            stage.get("name", ""): seconds(stage.get("duration_seconds"))
            for stage in payload.get("stages", [])
            if isinstance(stage, dict)
        }
        total = seconds(payload.get("total_seconds"))
        setup = sum(
            stages.get(name, 0.0) for name in ("pip-install", "npm-install", "playwright-install")
        )
        body = stages.get("playwright-features", 0.0)
        rows.append(
            {
                "shard": shard,
                "total": total,
                "pip": stages.get("pip-install", 0.0),
                "npm": stages.get("npm-install", 0.0),
                "playwright_install": stages.get("playwright-install", 0.0),
                "playwright_features": body,
                "other": max(total - setup - body, 0.0),
            }
        )
    return rows


def trx_duration_seconds(value):
    """Parse TRX duration strings such as 00:00:05.1234567."""
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        parts = text.split(":")
        if len(parts) == 3:
            hours, minutes, secs = parts
            return (int(hours) * 3600) + (int(minutes) * 60) + float(secs)
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def split_csharp_test_name(name):
    """Return class and method from a fully qualified xUnit test name."""
    text = str(name or "unknown")
    if "." not in text:
        return "unknown", text
    return text.rsplit(".", 1)


def short_csharp_class(name):
    """Keep C# timing tables compact in the Actions summary."""
    return str(name or "unknown").rsplit(".", 1)[-1]


def csharp_live_timings(pattern):
    """Load C# Live per-test timings from TRX artifacts."""
    results = []
    for path in sorted(glob.glob(pattern, recursive=True)):
        try:
            root = parse_xml_root(path)
        except Exception as exc:
            print(f"[WARN] csharp_live_timings({path}): {exc}")
            continue

        for node in root.iter():
            if not str(node.tag).endswith("UnitTestResult"):
                continue
            test_name = node.get("testName") or "unknown"
            class_name, method_name = split_csharp_test_name(test_name)
            results.append(
                {
                    "class": class_name,
                    "method": method_name,
                    "duration": trx_duration_seconds(node.get("duration")),
                    "outcome": node.get("outcome") or "unknown",
                }
            )

    if not results:
        return None

    classes = {}
    for row in results:
        bucket = classes.setdefault(
            row["class"],
            {"class": row["class"], "tests": 0, "total": 0.0, "max": 0.0},
        )
        bucket["tests"] += 1
        bucket["total"] += row["duration"]
        bucket["max"] = max(bucket["max"], row["duration"])
    class_rows = sorted(
        classes.values(),
        key=lambda row: (-row["total"], short_csharp_class(row["class"])),
    )
    top_rows = sorted(results, key=lambda row: row["duration"], reverse=True)[:10]
    return {"classes": class_rows, "top": top_rows}


def junit_case_timings(pattern, label):
    """Load per-test durations from JUnit XML artifacts when time attributes exist."""
    rows = []
    for path in sorted(glob.glob(pattern, recursive=True)):
        try:
            root = parse_xml_root(path)
        except Exception as exc:
            print(f"[WARN] junit_case_timings({path}): {exc}")
            continue

        for testcase in root.findall(".//testcase"):
            if testcase.get("time") is None:
                continue
            outcome = "success"
            if testcase.find("failure") is not None or testcase.find("error") is not None:
                outcome = "failure"
            elif testcase.find("skipped") is not None:
                outcome = "skipped"
            rows.append(
                {
                    "suite": label,
                    "class": testcase.get("classname") or "unknown",
                    "method": testcase.get("name") or "unknown",
                    "duration": seconds(testcase.get("time")),
                    "outcome": outcome,
                }
            )
    if not rows:
        return None
    return {"top": sorted(rows, key=lambda row: row["duration"], reverse=True)[:10]}


# ── Formatters ───────────────────────────────────────────────────


def job_icon(r):
    return {
        "success": "✅",
        "failure": "❌",
        "cancelled": "🚫",
        "skipped": "⏭️",
        "recorded": "📊",
    }.get(r, "⚠️")


def tests(total, passed, failed, skipped=0, baseline=None):
    if total is None:
        return "—"
    delta = format_count_delta(total, baseline)
    if failed:
        return f"{passed:,} / {total:,}{delta} ❌"
    return f"{passed:,}{delta} ✅"


def tests_cell(counts, baseline=None):
    return tests(counts[0], counts[1], counts[2], counts[3], baseline=baseline)


def skips(sk):
    return "—" if sk is None else str(sk)


def skipped_count_cell(sk) -> str:
    """Render a skipped-test count, adding the skip icon only for nonzero values."""
    if sk is None:
        return "—"
    return f"{sk} ⏭️" if sk else "0"


def count_test_results(counts, baseline=None):
    """Plain-text test-results cell for Lane Results and Component Test Results.

    No trailing pass/fail icon — the leading status icon column carries that
    signal so the cells stay tidy and left-aligned.
    """
    if counts[0] is None:
        return "Not Reported"
    total = counts[0]
    passed = counts[1] or 0
    failed = counts[2] or 0
    skipped = counts[3] if counts[3] is not None else 0
    delta = format_count_delta(total, baseline)
    if failed:
        return f"Passed: {passed:,} / {total:,}{delta}, Failed: {failed:,}, Skipped: {skipped:,}"
    return f"Passed: {passed:,}{delta}, Skipped: {skipped:,}"


def labeled_test_results(label, counts, baseline=None):
    """Single labelled test-result line for multi-lane table cells."""
    return f"{label}: {count_test_results(counts, baseline)}"


def _bulleted_count_lines(counts, baseline=None, indent: bool = False) -> list[str]:
    bullet = "&nbsp;&nbsp;&bull;" if indent else "&bull;"
    if counts[0] is None:
        return [f"{bullet} Not Reported"]
    total = counts[0]
    passed = counts[1] or 0
    failed = counts[2] or 0
    skipped = counts[3] if counts[3] is not None else 0
    delta = format_count_delta(total, baseline)
    if failed:
        return [
            f"{bullet} ✅&nbsp;Passed: {passed:,} / {total:,}{delta}",
            f"{bullet} ❌&nbsp;Failed: {failed:,}",
            f"{bullet} ⏭️&nbsp;Skipped: {skipped:,}",
        ]
    return [
        f"{bullet} ✅&nbsp;Passed: {passed:,}{delta}",
        f"{bullet} ⏭️&nbsp;Skipped: {skipped:,}",
    ]


def bulleted_test_results(counts, baseline=None) -> str:
    """Render a single-suite result cell as compact HTML bullets."""
    return "<br>".join(_bulleted_count_lines(counts, baseline))


def bulleted_multilane_test_results(*named_counts) -> str:
    """Render labelled multi-suite result cells with indented count bullets."""
    lines: list[str] = []
    for label, counts, baseline in named_counts:
        lines.append(f"&bull; {md_cell(label)}")
        lines.extend(_bulleted_count_lines(counts, baseline, indent=True))
    return "<br>".join(lines) if lines else "Not Reported"


def bottleneck_candidates(job_timings, wc_feature_timings, cs_live_timings):
    """Rank reliable timing sources without inventing missing duration data."""
    rows = []
    for name, duration, conclusion in job_timings:
        if duration is not None:
            rows.append(("Workflow job", name, duration, conclusion))
    for row in wc_feature_timings:
        rows.append(
            (
                "Browser timing artifact",
                f"Browser Features ({row['shard']})",
                row["total"],
                "recorded",
            )
        )
    if cs_live_timings:
        for row in cs_live_timings["classes"]:
            rows.append(
                (
                    "C# TRX class",
                    f"C# Live — {short_csharp_class(row['class'])}",
                    row["total"],
                    "recorded",
                )
            )
    return sorted(rows, key=lambda row: (-seconds(row[2]), row[1]))


def main() -> None:
    # Reason: CLI orchestration tested via snapshot tests
    # ── Load ENV ─────────────────────────────────────────────────────

    E = os.environ.get

    sd_r = E("SD_RESULT", "unknown")
    wd_r = E("WD_RESULT", "unknown")
    tc_r = E("TC_RESULT", "unknown")
    wc_r = E("WC_RESULT", "unknown")
    wb_r = E("WB_RESULT", "unknown")
    con_r = E("CON_RESULT", "unknown")
    cs_r = E("CS_RESULT", "unknown")
    cs_opcua_security_r = E("CS_OPCUA_SECURITY_RESULT", "unknown")
    console_opcua_security_r = E("CONSOLE_OPCUA_SECURITY_RESULT", "unknown")

    sha = (E("GH_SHA", "") or "")[:8]
    branch = E("GH_BRANCH", "main")
    run_num = E("GH_RUN_NUMBER", "")
    run_url = E("GH_RUN_URL", "")
    browser_image_plan = E("BROWSER_IMAGE_PLAN", "")
    browser_image_ref = E("BROWSER_IMAGE_REF", "")
    browser_image_inputs_fingerprint = E("BROWSER_IMAGE_INPUTS_FINGERPRINT", "")

    # ── Parse artifacts ──────────────────────────────────────────────

    sd_smoke = parse_junit("all-results/results-server-smoke-docker/smoke.xml")
    wd_py = parse_junit("all-results/results-webclient-docker/pytest-unit.xml")
    wd_js = parse_junit("all-results/results-webclient-docker/vitest.xml")
    tc_smoke = parse_junit("all-results/results-testclient/smoke-sanity.xml")
    tc_tests = parse_junit("all-results/results-testclient/pytest.xml")
    wc_live = parse_junit("all-results/results-live-webclient-web-client-live-*/**/*.xml")
    wc_browser = parse_junit("all-results/results-live-webclient-web-client-e2e-*/**/*.xml")
    con_live = parse_junit("all-results/results-live-console/**/pytest-live.xml")
    cs_live = parse_junit("all-results/results-csharp-live/tests.xml")
    csharp_opcua_security = parse_junit(
        "all-results/results-csharp-client-opcua-security-*/opcua-security-*.xml"
    )
    console_opcua_security = parse_junit(
        "all-results/results-console-client-opcua-security-*/opcua-security-*.xml"
    )
    wc_feature_timings = browser_feature_timings(
        "all-results/results-live-webclient-web-client-e2e-features*/**/timing-latest.json"
    )
    cs_live_timings = csharp_live_timings("all-results/results-csharp-live/**/*.trx")
    tc_live_timings = junit_case_timings(
        "all-results/results-testclient/pytest.xml",
        "Test Client Conformance",
    )
    job_timings = job_durations(
        f"repos/{E('GH_REPOSITORY', '')}/actions/runs/{E('GH_RUN_ID', '')}/jobs"
    )
    integration_baseline, baseline_warning = load_integration_baseline()

    # ── Collect skip details from JUnit XML ───────────────────────

    sd_smoke_skips = collect_skips("all-results/results-server-smoke-docker/smoke.xml")
    wd_py_skips = collect_skips("all-results/results-webclient-docker/pytest-unit.xml")
    wd_js_skips = collect_skips("all-results/results-webclient-docker/vitest.xml")
    tc_smoke_skips = collect_skips("all-results/results-testclient/smoke-sanity.xml")
    tc_conf_skips = collect_skips("all-results/results-testclient/pytest.xml")
    con_live_skips = collect_skips("all-results/results-live-console/**/pytest-live.xml")
    wc_live_skips = collect_skips("all-results/results-live-webclient-web-client-live-*/**/*.xml")
    wc_browser_skips = collect_skips("all-results/results-live-webclient-web-client-e2e-*/**/*.xml")
    cs_live_skips = collect_skips("all-results/results-csharp-live/tests.xml")
    csharp_opcua_security_skips = collect_skips(
        "all-results/results-csharp-client-opcua-security-*/opcua-security-*.xml"
    )
    console_opcua_security_skips = collect_skips(
        "all-results/results-console-client-opcua-security-*/opcua-security-*.xml"
    )

    # ── Artifact sanity gate ─────────────────────────────────────────

    artifact_warnings = []

    def _warn(job_result, val, job_name, artifact):
        if job_result == "success" and val is None:
            artifact_warnings.append(
                f"⚠️ **{job_name}**: job succeeded but `{artifact}` not found — "
                "possible silent failure"
            )

    _warn(sd_r, sd_smoke[0], "server-smoke-docker", "smoke.xml")
    _warn(wd_r, wd_py[0], "webclient-docker", "pytest-unit.xml")
    _warn(wd_r, wd_js[0], "webclient-docker", "vitest.xml")
    _warn(tc_r, tc_smoke[0], "int-testclient", "smoke-sanity.xml")
    _warn(tc_r, tc_tests[0], "int-testclient", "pytest.xml")
    _warn(wc_r, wc_live[0], "live-webclient", "JUnit XML")
    _warn(wb_r, wc_browser[0], "live-webclient-browser", "JUnit XML")
    _warn(con_r, con_live[0], "live-console", "pytest-live.xml")
    _warn(cs_r, cs_live[0], "csharp-live", "tests.xml")
    _warn(
        cs_opcua_security_r,
        csharp_opcua_security[0],
        "csharp-client-opcua-security",
        "opcua-security XML",
    )
    _warn(
        console_opcua_security_r,
        console_opcua_security[0],
        "console-client-opcua-security",
        "opcua-security XML",
    )

    tc_conformance_summary_path = "all-results/results-testclient/summary.md"
    tc_conformance_summary_lines = load_test_client_conformance_summary(tc_conformance_summary_path)
    tc_conformance_warning = tc_conformance_artifact_warning(
        str(tc_r), tc_conformance_summary_lines, tc_conformance_summary_path
    )
    if tc_conformance_warning:
        artifact_warnings.append(tc_conformance_warning)

    # ── Performance benchmarks ────────────────────────────────────────
    # Live perf tests publish their result-transfer latency stats as
    # `perf_*` JUnit properties. The aggregator pulls them here so the
    # single System Tests Report job summary owns the entire run-page
    # output; the live test jobs no longer write to `$GITHUB_STEP_SUMMARY`
    # directly (that previously fragmented the page in completion order).
    perf_lanes: list[tuple[str, dict[str, float]]] = []
    con_live_perf = load_perf_benchmarks("all-results/results-live-console/**/pytest-live.xml")
    if con_live_perf:
        perf_lanes.append(("Console Client — Result Transfer Time", con_live_perf))
    perf_section_lines = render_perf_section(perf_lanes)

    suite_counts = [
        ("sd_smoke", "OPC UA Server — Docker Smoke", sd_smoke),
        ("wd_py", "Web Client — Docker Python Unit", wd_py),
        ("wd_js", "Web Client — Docker JavaScript", wd_js),
        ("tc_smoke", "Test Client — Smoke Sanity", tc_smoke),
        ("tc_tests", "Test Client — Specification Tests", tc_tests),
        ("wc_live", "Web Client — Python/WebSocket Live", wc_live),
        ("wc_browser", "Web Client — Browser E2E", wc_browser),
        ("con_live", "Console Client — Live", con_live),
        ("cs_live", "C# Client — Live", cs_live),
        ("csharp_opcua_security", "C# Client — OPC UA Security", csharp_opcua_security),
        ("console_opcua_security", "Console Client — OPC UA Security", console_opcua_security),
    ]
    skip_policy_failures = must_not_skip_failures(suite_counts)
    report_warnings = integration_drift_warnings(
        integration_baseline,
        suite_counts,
        E("GH_RUN_ID", ""),
    )
    if baseline_warning:
        report_warnings.insert(0, baseline_warning)

    # ── Overall status ────────────────────────────────────────────────

    all_suites_data = [
        sd_smoke,
        wd_py,
        wd_js,
        tc_smoke,
        tc_tests,
        wc_live,
        wc_browser,
        con_live,
        cs_live,
        csharp_opcua_security,
        console_opcua_security,
    ]
    total_t = sum(s[0] for s in all_suites_data if s[0] is not None)
    total_f = sum(s[2] for s in all_suites_data if s[2] is not None)
    total_sk = sum(s[3] for s in all_suites_data if s[3] is not None)
    total_passed = max(total_t - total_f - total_sk, 0)

    core_jobs = [
        result
        for result in [
            sd_r,
            wd_r,
            tc_r,
            wc_r,
            wb_r,
            con_r,
            cs_r,
            cs_opcua_security_r,
            console_opcua_security_r,
        ]
        if result not in {"unknown", "skipped"}
    ]
    n_pass = sum(1 for r in core_jobs if r == "success")
    n_fail = sum(1 for r in core_jobs if r != "success")
    n_total = len(core_jobs)

    status_clean = (
        n_fail == 0 and not skip_policy_failures and not report_warnings and not artifact_warnings
    )
    status_emoji = "✅" if status_clean else "⚠️"
    status_summary = (
        f"{status_emoji} **Status:** {n_fail} Failed Jobs &nbsp;·&nbsp; "
        f"{len(report_warnings)} Baseline Warnings &nbsp;·&nbsp; "
        f"{len(skip_policy_failures)} Skip-Policy Failures &nbsp;·&nbsp; "
        f"{len(artifact_warnings)} Artifact Warnings"
    )

    if n_fail == 0 and not skip_policy_failures:
        status_icon = "✅"
        status_msg = f"All {n_pass} / {n_total} Jobs Passed"
    else:
        status_icon = "❌"
        if skip_policy_failures and n_fail == 0:
            status_msg = "Skip Policy Gate Failed"
        else:
            status_msg = f"{n_fail} / {n_total} Jobs Failed &nbsp;·&nbsp; {n_pass} Passed"

    run_link = f"[#{run_num}]({run_url})" if run_url else f"#{run_num}"
    sha_str = f"`{sha}`" if sha else "—"
    wc_browser_note = skip_note_inline(
        wc_browser_skips,
        wc_browser[3],
        "Headless Chromium baked into the IJT Browser CI image",
    )
    sd_smoke_base = baseline_suite(integration_baseline, "sd_smoke")
    wd_py_base = baseline_suite(integration_baseline, "wd_py")
    wd_js_base = baseline_suite(integration_baseline, "wd_js")
    tc_smoke_base = baseline_suite(integration_baseline, "tc_smoke")
    tc_tests_base = baseline_suite(integration_baseline, "tc_tests")
    wc_live_base = baseline_suite(integration_baseline, "wc_live")
    wc_browser_base = baseline_suite(integration_baseline, "wc_browser")
    con_live_base = baseline_suite(integration_baseline, "con_live")
    cs_live_base = baseline_suite(integration_baseline, "cs_live")
    csharp_opcua_security_base = baseline_suite(integration_baseline, "csharp_opcua_security")
    console_opcua_security_base = baseline_suite(integration_baseline, "console_opcua_security")

    web_docker_results = bulleted_multilane_test_results(
        ("Python", wd_py, wd_py_base),
        ("JavaScript", wd_js, wd_js_base),
    )
    web_live_results = bulleted_multilane_test_results(
        ("Python/WebSocket Live", wc_live, wc_live_base),
        ("Browser E2E", wc_browser, wc_browser_base),
    )
    test_client_live_results = bulleted_multilane_test_results(
        ("Smoke", tc_smoke, tc_smoke_base),
        ("Specification Tests", tc_tests, tc_tests_base),
    )
    tc_diagnostic_note = test_client_diagnostic_note(tc_conf_skips, tc_tests[3])
    console_security_note = skip_note_inline(
        con_live_skips + console_opcua_security_skips,
        (con_live[3] or 0) + (console_opcua_security[3] or 0),
    )
    csharp_security_note = skip_note_inline(
        cs_live_skips + csharp_opcua_security_skips,
        (cs_live[3] or 0) + (csharp_opcua_security[3] or 0),
        "Nightly baseline check",
    )
    all_lane_results = [
        sd_r,
        wd_r,
        tc_r,
        wc_r,
        wb_r,
        con_r,
        console_opcua_security_r,
        cs_r,
        cs_opcua_security_r,
    ]
    lane_result_count = len(all_lane_results)
    component_result_count = len(
        [
            "OPC UA Server",
            "Web Client",
            "Test Client",
            "Console Client",
            "C# Client",
        ]
    )
    conformance_suite_count = len([tc_smoke, tc_tests])
    quick_index_client_count = component_result_count

    # ── Build report ──────────────────────────────────────────────────

    out = [
        "## IJT OPC UA — System Tests",
        "",
        f"> {status_icon} **{status_msg}**",
        (
            f"> **Branch:** `{branch}` &nbsp;·&nbsp; **Commit:** {sha_str} "
            f"&nbsp;·&nbsp; **Run:** {run_link}"
        ),
        "",
        (
            "> Full report below: [Outcome](#system-outcome-overview) · "
            "[Test Results](#system-test-results) · "
            "[CUs Needing Review](#system-cus-needing-review) · "
            "[Specification Test Report](#system-test-client-specification-test-report) · "
            "[Components](#system-component-test-results) · "
            "[Specification Test Suites](#system-specification-test-suites) · "
            "[Diagnostics](#system-skip-details) · "
            "[Performance](#system-performance-benchmarks) · "
            "[Artifacts](#system-artifacts-and-drilldown)"
        ),
        "",
        "---",
        "",
        '<a id="system-outcome-overview"></a>',
        "",
        "### 📊 Test Outcome Overview",
        "",
        f"> {status_summary}",
        "",
        *pad_table_rows(
            ["🚦", "Outcome", "Count"],
            [
                ["✅", "Passed", f"{total_passed:,}"],
                ["❌", "Failed", f"{total_f:,}"],
                ["⏭️", "Skipped", f"{total_sk:,}"],
                ["🧮", "Total", f"{total_t:,}"],
                ["🛠️", "Jobs", f"{n_pass} / {n_total}"],
            ],
            ["center", "left", "right"],
        ),
        "",
        "---",
        "",
        '<a id="system-test-results"></a>',
        "",
        f"### 🧪 Test Results — {plural_label(lane_result_count, 'suite')}",
        "",
        "| 🚦 | Suite | Result | Test Results |",
        "|:--:|:------|:-------|:-------------|",
        f"| {lane_status_icon(str(sd_r))} | OPC UA Server Docker smoke "
        f"| {lane_status_text(str(sd_r))} "
        f"| {bulleted_test_results(sd_smoke, sd_smoke_base)} |",
        f"| {lane_status_icon(str(wd_r))} | Web Client Docker tests "
        f"| {lane_status_text(str(wd_r))} | {web_docker_results} |",
        f"| {lane_status_icon(str(tc_r))} | Test Client specification tests "
        f"| {lane_status_text(str(tc_r))} "
        f"| {bulleted_test_results(tc_tests, tc_tests_base)} |",
        f"| {lane_status_icon(str(wc_r))} | Web Client live suites "
        f"| {lane_status_text(str(wc_r))} "
        f"| {bulleted_test_results(wc_live, wc_live_base)} |",
        f"| {lane_status_icon(str(wb_r))} | Browser E2E suites "
        f"| {lane_status_text(str(wb_r))} "
        f"| {bulleted_test_results(wc_browser, wc_browser_base)} |",
        f"| {lane_status_icon(str(con_r))} | Console Client live "
        f"| {lane_status_text(str(con_r))} "
        f"| {bulleted_test_results(con_live, con_live_base)} |",
        f"| {lane_status_icon(str(console_opcua_security_r))} | Console Client OPC UA security | "
        f"{lane_status_text(str(console_opcua_security_r))} | "
        f"{bulleted_test_results(console_opcua_security, console_opcua_security_base)} |",
        f"| {lane_status_icon(str(cs_r))} | C# Client live "
        f"| {lane_status_text(str(cs_r))} "
        f"| {bulleted_test_results(cs_live, cs_live_base)} |",
        f"| {lane_status_icon(str(cs_opcua_security_r))} | C# Client OPC UA security | "
        f"{lane_status_text(str(cs_opcua_security_r))} | "
        f"{bulleted_test_results(csharp_opcua_security, csharp_opcua_security_base)} |",
        "",
        *(
            [
                "---",
                "",
                '<a id="system-test-client-specification-test-report"></a>',
                "",
                *tc_conformance_summary_lines,
                "",
            ]
            if tc_conformance_summary_lines
            else []
        ),
        "---",
        "",
        '<a id="system-component-test-results"></a>',
        "",
        f"### 🧬 Component Test Results — {component_result_count} components",
        "",
        (
            "| 🚦 | Component | Validation Scope | Container Test Results | "
            "Live/System Test Results | Notes |"
        ),
        "|:--:|:----------|:-----------------|:-------------------|:---------------------|:------|",
        (
            f"| {component_row_icon(sd_smoke)} "
            "| OPC UA Server | Linux container plus Windows live server processes | "
            f"{bulleted_test_results(sd_smoke, sd_smoke_base)} | "
            "Dedicated Windows ports 40461/40462/40464 feed client live suites | "
            "Docker smoke proves packaged Linux startup and namespace reachability |"
        ),
        (
            f"| {component_row_icon(wd_py, wd_js, wc_live, wc_browser, wc_browser_note)} "
            "| Web Client | Docker unit/prod checks plus live Python/WebSocket and browser E2E | "
            f"{web_docker_results} | "
            f"{web_live_results} | "
            f"{wc_browser_note} |"
        ),
        (
            f"| {component_row_icon(tc_tests, tc_diagnostic_note)} "
            "| Test Client | Live specification test harness against OPC UA server "
            f"| {_CELL_NOT_APPLICABLE_INT} | "
            f"{test_client_live_results} | "
            f"{tc_diagnostic_note} |"
        ),
        (
            f"| {component_row_icon(console_opcua_security, con_live, console_security_note)} "
            "| Console Client | Live Python client behavior and OPC UA security coverage "
            "against OPC UA server | "
            f"{bulleted_test_results(console_opcua_security, console_opcua_security_base)} | "
            f"{bulleted_test_results(con_live, con_live_base)} | "
            f"{console_security_note} |"
        ),
        (
            f"| {component_row_icon(csharp_opcua_security, cs_live, csharp_security_note)} "
            "| C# Client | Nightly xUnit live behavior and OPC UA security coverage "
            "against OPC UA server | "
            f"{bulleted_test_results(csharp_opcua_security, csharp_opcua_security_base)} | "
            f"{bulleted_test_results(cs_live, cs_live_base)} | "
            f"{csharp_security_note} |"
        ),
        "",
        "---",
        "",
        '<a id="system-specification-test-suites"></a>',
        "",
        f"### 📑 Specification Test Suites — {plural_label(conformance_suite_count, 'suite')}",
        "",
        "| Suite | Port | Live Tests | Skipped | Notes |",
        "|:------|-----:|----------:|--------:|:------|",
        (
            "| Test Client — Smoke sanity | 40462 | "
            f"{tests_cell(tc_smoke, tc_smoke_base)} | "
            f"{skipped_count_cell(tc_smoke[3])} | Server and namespace reachability |"
        ),
        (
            "| Test Client — Specification Tests | 40462 | "
            f"{tests_cell(tc_tests, tc_tests_base)} | "
            f"{skipped_count_cell(tc_tests[3])} | "
            f"{tc_diagnostic_note} "
            "([Skip Details](#system-skip-details)) |"
        ),
    ]

    # ── Inline skip details (collapsible per suite) ──────────────────
    # Built here so the Specification Test Suites "see below" link points to the
    # very next visual block, not 100+ lines below.

    skip_sections = []
    skip_sections += format_skip_section(
        "OPC UA Server — Docker Smoke", sd_smoke_skips, sd_smoke[3]
    )
    skip_sections += format_skip_section("Web Client — Docker Python Unit", wd_py_skips, wd_py[3])
    skip_sections += format_skip_section("Web Client — Docker JavaScript", wd_js_skips, wd_js[3])
    skip_sections += format_skip_section("Test Client — Smoke Sanity", tc_smoke_skips, tc_smoke[3])
    tc_diagnostic_sections, tc_companion_sections = format_test_client_diagnostic_sections(
        tc_conf_skips, tc_tests[3]
    )
    skip_sections += tc_diagnostic_sections
    skip_sections += format_skip_section("Console Client — Live", con_live_skips, con_live[3])
    skip_sections += format_skip_section(
        "Console Client — OPC UA Security",
        console_opcua_security_skips,
        console_opcua_security[3],
    )
    skip_sections += format_skip_section(
        "Web Client — Python/WebSocket Live", wc_live_skips, wc_live[3]
    )
    skip_sections += format_skip_section(
        "Web Client — Browser E2E", wc_browser_skips, wc_browser[3]
    )
    skip_sections += format_skip_section("C# Client — Live", cs_live_skips, cs_live[3])
    skip_sections += format_skip_section(
        "C# Client — OPC UA Security",
        csharp_opcua_security_skips,
        csharp_opcua_security[3],
    )

    if skip_sections:
        out += [
            "",
            "---",
            "",
            '<a id="system-skip-details"></a>',
            "",
            "### ⏭️ Skip Details",
            "",
            "_Each suite below is collapsed by default — click to inspect skip reasons._",
        ]
        out += skip_sections
    else:
        out += [
            "",
            "---",
            "",
            '<a id="system-skip-details"></a>',
            "",
            "### ⏭️ Skip Details",
            "",
            "No skipped tests reported.",
        ]

    if tc_companion_sections:
        out += [
            "",
            "---",
            "",
            "### 🧭 Companion Spec Profile Notes",
            "",
            (
                "_These notes cover companion-spec profile areas that are intentionally "
                "outside the active server profile._"
            ),
        ]
        out += tc_companion_sections

    timing_rows = bottleneck_candidates(job_timings, wc_feature_timings, cs_live_timings)
    if perf_section_lines:
        out += [
            "",
            "---",
            "",
            *perf_section_lines,
        ]
    out += [
        "",
        "---",
        "",
        '<a id="system-performance-hotspots"></a>',
        "",
        "### ⏱️ Performance Hotspots",
        "",
        (
            "<details><summary><b>Click to expand</b> — job, browser, C# and "
            "Test Client timing drilldown</summary>"
        ),
        "",
    ]
    if timing_rows:
        out += [
            (
                "> Source order: current workflow run jobs API first, then Web Client "
                "timing JSON, C# TRX artifacts, and Test Client JUnit durations when "
                "available. Missing timing data is omitted rather than estimated."
            ),
            "",
            "| Source | Item | Duration | Status |",
            "|:-------|:-----|---------:|:-------|",
        ]
        for index, (source, name, duration, conclusion) in enumerate(timing_rows[:10]):
            marker = "🏁 " if index == 0 else ""
            out.append(
                f"| {md_cell(source)} | {marker}{md_cell(name)} | "
                f"{format_duration(duration)} | {perf_status_fmt(str(conclusion))} |"
            )
        source, name, duration, _conclusion = timing_rows[0]
        out += [
            "",
            "#### Bottleneck Spotlight",
            "",
            (
                f"> 🏁 **{md_cell(name)}** is the current longest reliable timing source "
                f"({format_duration(duration)}, {md_cell(source)})."
            ),
        ]
    else:
        out += [
            (
                "No reliable duration source was available. Job durations require the "
                "current-run Jobs API; per-suite timing appears only when Browser timing "
                "JSON or C# TRX artifacts are present."
            )
        ]

    if wc_feature_timings:
        out += [
            "",
            "<details><summary><b>Browser Feature Stage Timing</b></summary>",
            "",
            (
                "| Shard | Total | pip-install | npm-install | Playwright install | "
                "Playwright features | Other |"
            ),
            "|:------|------:|------------:|------------:|-------------------:|--------------------:|------:|",
        ]
        for row in wc_feature_timings:
            out.append(
                f"| {row['shard']} | {format_duration(row['total'])} | "
                f"{format_duration(row['pip'])} | {format_duration(row['npm'])} | "
                f"{format_duration(row['playwright_install'])} | "
                f"{format_duration(row['playwright_features'])} | "
                f"{format_duration(row['other'])} |"
            )
        out += ["", "</details>"]

    if cs_live_timings:
        out += [
            "",
            "<details><summary><b>C# Live Timing Details</b></summary>",
            "",
            "| Class | Tests | Total | Avg | Max |",
            "|:------|------:|------:|----:|----:|",
        ]
        for row in cs_live_timings["classes"][:10]:
            avg = row["total"] / row["tests"] if row["tests"] else 0.0
            out.append(
                f"| {md_cell(short_csharp_class(row['class']))} | {row['tests']} | "
                f"{format_duration(row['total'])} | {format_duration(avg)} | "
                f"{format_duration(row['max'])} |"
            )

        out += [
            "",
            "#### Slowest C# Live Tests",
            "",
            "| Test | Duration | Outcome |",
            "|:-----|---------:|:--------|",
        ]
        for row in cs_live_timings["top"]:
            out.append(
                f"| {md_cell(row['method'])} | {format_duration(row['duration'])} | "
                f"{md_cell(status_text(str(row['outcome'])))} |"
            )
        out += ["", "</details>"]

    if tc_live_timings:
        out += [
            "",
            "<details><summary><b>Test Client Specification Test Timing Details</b></summary>",
            "",
            "| Test | Duration | Outcome |",
            "|:-----|---------:|:--------|",
        ]
        for row in tc_live_timings["top"]:
            out.append(
                f"| {md_cell(row['method'])} | {format_duration(row['duration'])} | "
                f"{md_cell(status_text(str(row['outcome'])))} |"
            )
        out += ["", "</details>"]
    else:
        out += [
            "",
            "<details><summary><b>Test Client Specification Test Timing Details</b></summary>",
            "",
            "Per-test durations are not available in the current JUnit artifact.",
            "",
            "</details>",
        ]

    out += ["", "</details>", ""]

    out += [
        "",
        "---",
        "",
        '<a id="system-warnings-baseline"></a>',
        "",
        "### ⚠️ Warnings and Baseline Checks",
        "",
        (
            "<details><summary><b>Click to expand</b> — skip policy, baseline, "
            "and artifact warnings</summary>"
        ),
        "",
    ]
    if skip_policy_failures:
        out += ["#### Skip Policy Failures", ""]
        out += skip_policy_failures
        out += [""]
    if report_warnings:
        out += ["#### Report Warnings", ""]
        out += report_warnings
        out += [""]
    if artifact_warnings:
        out += ["#### Artifact Warnings", ""]
        out += artifact_warnings
        out += [""]
    if not skip_policy_failures and not report_warnings and not artifact_warnings:
        out += ["No skip policy failures, baseline warnings, or artifact warnings."]

    out += ["", "</details>", ""]

    out += [
        "",
        "---",
        "",
        '<a id="system-artifacts-and-drilldown"></a>',
        "",
        "### 📎 Artifacts and Drilldown",
        "",
        (
            "<details><summary><b>Click to expand</b> — where to find raw "
            "JUnit, drill-down, and security results</summary>"
        ),
        "",
        "> 📦 **Artifacts** — JUnit XML &nbsp;·&nbsp; 📋 **Checks** tab — per-test drill-down",
        "> 🔒 Security audit (zizmor) results are in **CI** → Security → Code Scanning",
        "",
    ]
    if browser_image_plan or browser_image_ref or browser_image_inputs_fingerprint:
        out += [
            "<details><summary><b>Browser CI Image</b></summary>",
            "",
            "| Field | Value |",
            "|:------|:------|",
            f"| Plan | `{md_cell(browser_image_plan or 'Not Reported')}` |",
            f"| Image ref | `{md_cell(browser_image_ref or 'Not Reported')}` |",
            (
                "| Inputs fingerprint | "
                f"`{md_cell(browser_image_inputs_fingerprint or 'Not Reported')}` |"
            ),
            "",
            "</details>",
        ]
    out += ["", "</details>"]

    out += [
        "",
        "---",
        "",
        '<a id="system-per-client-quick-index"></a>',
        "",
        f"### 📚 Per-Client Quick Index — {quick_index_client_count} clients",
        "",
        "| Client / Component | Appears In |",
        "|:-------------------|:-----------|",
        (
            "| OPC UA Server | [Test Results](#system-test-results) · "
            "[Component Test Results](#system-component-test-results) · "
            "[Performance Hotspots](#system-performance-hotspots) |"
        ),
        (
            "| Web Client | [Test Results](#system-test-results) · "
            "[Component Test Results](#system-component-test-results) · "
            "[Performance Hotspots](#system-performance-hotspots) |"
        ),
        (
            "| Test Client | [Test Results](#system-test-results) · "
            "[Component Test Results](#system-component-test-results) · "
            "[Specification Test Suites](#system-specification-test-suites) · "
            + (
                "[Specification Test Report](#system-test-client-specification-test-report) · "
                if tc_conformance_summary_lines
                else ""
            )
            + "[Performance Hotspots](#system-performance-hotspots) |"
        ),
        (
            "| Console Client | [Test Results](#system-test-results) · "
            "[Component Test Results](#system-component-test-results) · "
            "[Performance Benchmarks](#system-performance-benchmarks) |"
        ),
        (
            "| C# Client | [Test Results](#system-test-results) · "
            "[Component Test Results](#system-component-test-results) · "
            "[Performance Hotspots](#system-performance-hotspots) |"
        ),
    ]

    with open(
        os.environ.get("GITHUB_STEP_SUMMARY", "/dev/stdout"), "a", encoding="utf-8", newline="\n"
    ) as fh:
        fh.write("\n".join(out) + "\n")
    print("Summary written.")
    if skip_policy_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
