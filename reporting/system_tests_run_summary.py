"""Generate the IJT integration GitHub Actions summary."""

import datetime
import glob
import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter

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
    # safe: local CI artifact parser rejects entity declarations before parsing.
    return ET.fromstring(payload)  # noqa: S314


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


def md_cell(value):
    """Escape text for a GitHub markdown table cell."""
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    return text.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


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
        f"<details><summary>⏭️ <b>{label}</b> — {reported_count} skipped</summary>",
        "",
        "| Reason | Count |",
        "|:-------|------:|",
    ]
    for reason, count in reasons.most_common():
        lines.append(f"| {md_cell(reason)} | {count} |")
    lines += ["", "</details>"]
    return lines


def skip_note_inline(skips_list, skip_count=None, default="—"):
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
        if payload.get("schema_version") != 1 or not isinstance(suites, dict):
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
    for key, label, counts in suite_counts:
        entry = baseline_suite(baseline, key)
        if not entry or counts[0] is None:
            continue
        total, _passed, _failed, skipped = counts
        expected_tests = entry.get("tests")
        if expected_tests is not None:
            delta = total - int(expected_tests)
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


def non_test_client_skip_failures(suite_counts):
    """Build hard failures for skips outside IJT Test Client conformance."""
    failures = []
    for key, label, counts in suite_counts:
        if key == "tc_tests" or counts[3] is None:
            continue
        skipped = int(counts[3])
        if skipped:
            failures.append(
                f"❌ **{label}**: {skipped:,} skipped — only IJT Test Client conformance "
                "may skip Not Implemented / Not Supported coverage."
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
            # safe: GitHub Actions supplies api_url; HTTPS is enforced above.
            request = urllib.request.Request(url, headers=headers)  # noqa: S310
            # safe: GitHub Actions supplies api_url; HTTPS is enforced above.
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
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

        artifact = os.path.basename(os.path.dirname(path))
        if artifact.endswith("-shard-1of2"):
            shard = "1/2"
        elif artifact.endswith("-shard-2of2"):
            shard = "2/2"
        else:
            shard = "full"

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
    if failed == 0:
        return f"✅ {total:,}{delta}"
    return f"❌ {passed:,} / {total:,}{delta}"


def skips(sk):
    return "—" if sk is None else str(sk)


def count_test_results(counts, baseline=None):
    """Compact test-results cell for a suite's tests and skips."""
    return f"{tests(*counts, baseline=baseline)}; {skips(counts[3])} skipped"


def mermaid_label(value):
    """Keep Mermaid task labels readable and syntax-safe."""
    text = str(value or "job").replace("#", "Sharp")
    for char in "\r\n:;|":
        text = text.replace(char, " ")
    return " ".join(text.split())[:70] or "job"


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

    sha = (E("GH_SHA", "") or "")[:8]
    branch = E("GH_BRANCH", "main")
    run_num = E("GH_RUN_NUMBER", "")
    run_url = E("GH_RUN_URL", "")

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

    suite_counts = [
        ("sd_smoke", "OPC UA Server — Docker Smoke", sd_smoke),
        ("wd_py", "Web Client — Docker Python Unit", wd_py),
        ("wd_js", "Web Client — Docker JavaScript", wd_js),
        ("tc_smoke", "Test Client — Smoke Sanity", tc_smoke),
        ("tc_tests", "Test Client — Conformance", tc_tests),
        ("wc_live", "Web Client — Python/WebSocket Live", wc_live),
        ("wc_browser", "Web Client — Browser E2E", wc_browser),
        ("con_live", "Console Client — Live", con_live),
        ("cs_live", "C# Client — Live", cs_live),
    ]
    skip_policy_failures = non_test_client_skip_failures(suite_counts)
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
    ]
    total_t = sum(s[0] for s in all_suites_data if s[0] is not None)
    total_f = sum(s[2] for s in all_suites_data if s[2] is not None)
    total_sk = sum(s[3] for s in all_suites_data if s[3] is not None)
    if total_t > 0:
        totals_str = (
            f"{total_t:,} tests &nbsp;·&nbsp; {total_f} failed &nbsp;·&nbsp; {total_sk} skipped"
        )
    else:
        totals_str = "no test data"

    core_jobs = [sd_r, wd_r, tc_r, wc_r, wb_r, con_r, cs_r]
    n_pass = sum(1 for r in core_jobs if r == "success")
    n_fail = sum(1 for r in core_jobs if r == "failure")
    n_total = len(core_jobs)

    if n_fail == 0 and not skip_policy_failures:
        status_icon = "✅"
        status_msg = f"All {n_pass} / {n_total} jobs passed &nbsp;·&nbsp; {totals_str}"
    else:
        status_icon = "❌"
        if skip_policy_failures and n_fail == 0:
            status_msg = f"Skip policy gate failed &nbsp;·&nbsp; {totals_str}"
        else:
            status_msg = (
                f"{n_fail} / {n_total} jobs failed &nbsp;·&nbsp; {n_pass} passed "
                f"&nbsp;·&nbsp; {totals_str}"
            )

    run_link = f"[#{run_num}]({run_url})" if run_url else f"#{run_num}"
    sha_str = f"`{sha}`" if sha else "—"
    wc_browser_note = skip_note_inline(
        wc_browser_skips,
        wc_browser[3],
        "Headless Chromium baked into the IJT Browser CI image",
    )

    # ── Build report ──────────────────────────────────────────────────

    out = [
        "## IJT OPC UA — System Tests",
        "",
        f"> {status_icon} **{status_msg}**",
        (
            f"> **Branch:** `{branch}` &nbsp;·&nbsp; **Commit:** {sha_str} "
            f"&nbsp;·&nbsp; **Run:** {run_link}"
        ),
        (
            "> Nightly and manual system tests — live OPC UA server behavior, browser "
            "E2E suites, Docker packaging, and conformance verification."
        ),
        "",
        "---",
        "",
        '<a id="system-validation-overview"></a>',
        "",
        "### Validation Overview",
        "",
        "| Lane | Result | Test Results |",
        "|:-----|:-------|:---------|",
        f"| OPC UA Server Docker smoke | {job_icon(sd_r)} {md_cell(sd_r)} | "
        f"{count_test_results(sd_smoke, baseline_suite(integration_baseline, 'sd_smoke'))} |",
        f"| Web Client Docker tests | {job_icon(wd_r)} {md_cell(wd_r)} | "
        f"Python {count_test_results(wd_py, baseline_suite(integration_baseline, 'wd_py'))}; "
        f"JavaScript {count_test_results(wd_js, baseline_suite(integration_baseline, 'wd_js'))} |",
        f"| Test Client conformance | {job_icon(tc_r)} {md_cell(tc_r)} | "
        f"{count_test_results(tc_tests, baseline_suite(integration_baseline, 'tc_tests'))} |",
        f"| Web Client live suites | {job_icon(wc_r)} {md_cell(wc_r)} | "
        f"{count_test_results(wc_live, baseline_suite(integration_baseline, 'wc_live'))} |",
        f"| Browser E2E suites | {job_icon(wb_r)} {md_cell(wb_r)} | "
        f"{count_test_results(wc_browser, baseline_suite(integration_baseline, 'wc_browser'))} |",
        f"| Console Client live | {job_icon(con_r)} {md_cell(con_r)} | "
        f"{count_test_results(con_live, baseline_suite(integration_baseline, 'con_live'))} |",
        f"| C# Client live | {job_icon(cs_r)} {md_cell(cs_r)} | "
        f"{count_test_results(cs_live, baseline_suite(integration_baseline, 'cs_live'))} |",
        "",
        "---",
        "",
        '<a id="system-component-test-results"></a>',
        "",
        "### Component Test Results",
        "",
        (
            "| Component | Validation Scope | Container Test Results | "
            "Live/System Test Results | Notes |"
        ),
        "|:----------|:-----------------|:-------------------|:---------------------|:------|",
        (
            "| OPC UA Server | Linux container plus Windows live server processes | "
            f"{count_test_results(sd_smoke, baseline_suite(integration_baseline, 'sd_smoke'))} | "
            "Dedicated Windows ports 40461/40462/40464 feed client live suites | "
            "Docker smoke proves packaged Linux startup and namespace reachability |"
        ),
        (
            "| Web Client | Docker unit/prod checks plus live Python/WebSocket and browser E2E | "
            f"Python {count_test_results(wd_py, baseline_suite(integration_baseline, 'wd_py'))}; "
            f"JS {count_test_results(wd_js, baseline_suite(integration_baseline, 'wd_js'))} | "
            f"Live {count_test_results(wc_live, baseline_suite(integration_baseline, 'wc_live'))}; "
            "browser "
            f"{count_test_results(wc_browser, baseline_suite(integration_baseline, 'wc_browser'))} "
            "| "
            f"{wc_browser_note} |"
        ),
        (
            "| Test Client | Live conformance harness against OPC UA server | — | "
            "Smoke "
            f"{count_test_results(tc_smoke, baseline_suite(integration_baseline, 'tc_smoke'))}; "
            "conformance "
            f"{count_test_results(tc_tests, baseline_suite(integration_baseline, 'tc_tests'))} | "
            f"{skip_note_inline(tc_conf_skips, tc_tests[3])} |"
        ),
        (
            "| Console Client | Live Python client behavior against OPC UA server | — | "
            f"{count_test_results(con_live, baseline_suite(integration_baseline, 'con_live'))} | "
            f"{skip_note_inline(con_live_skips, con_live[3])} |"
        ),
        (
            "| C# Client | Nightly xUnit live behavior against OPC UA server | — | "
            f"{count_test_results(cs_live, baseline_suite(integration_baseline, 'cs_live'))} | "
            f"{skip_note_inline(cs_live_skips, cs_live[3], 'Nightly drift detection')} |"
        ),
        "",
        "---",
        "",
        '<a id="system-conformance-overview"></a>',
        "",
        "### Conformance Overview",
        "",
        "| Suite | Port | Live Tests | Skipped | Notes |",
        "|:------|-----:|----------:|--------:|:------|",
        (
            "| Test Client — Smoke sanity | 40462 | "
            f"{tests(*tc_smoke, baseline=baseline_suite(integration_baseline, 'tc_smoke'))} | "
            f"{skips(tc_smoke[3])} | Server and namespace reachability |"
        ),
        (
            "| Test Client — Conformance | 40462 | "
            f"{tests(*tc_tests, baseline=baseline_suite(integration_baseline, 'tc_tests'))} | "
            f"{skips(tc_tests[3])} | {skip_note_inline(tc_conf_skips, tc_tests[3])} |"
        ),
    ]

    timing_rows = bottleneck_candidates(job_timings, wc_feature_timings, cs_live_timings)
    out += [
        "",
        "---",
        "",
        '<a id="system-performance-hotspots"></a>',
        "",
        "### Performance Hotspots",
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
            "```mermaid",
            (
                '%%{init: {"themeVariables": {"taskBkgColor": "#9ca3af", '
                '"taskTextColor": "#111827", "critBkgColor": "#ef4444", '
                '"doneTaskBkgColor": "#22c55e"}}}%%'
            ),
            "gantt",
            "  title System Tests duration spotlight",
            "  dateFormat X",
            "  axisFormat %M:%S",
            "  section Duration sources",
        ]
        for index, (_source, name, duration, conclusion) in enumerate(timing_rows[:8]):
            tags = ["crit"] if index == 0 else []
            if conclusion in ("success", "recorded"):
                tags.append("done")
            tag_text = ", ".join(tags)
            if tag_text:
                tag_text = f"{tag_text}, "
            end_seconds = max(int(round(seconds(duration))), 1)
            out.append(f"  {mermaid_label(name)} :{tag_text}task{index}, 0, {end_seconds}")
        out += [
            "```",
            "",
            "| Source | Item | Duration | Status |",
            "|:-------|:-----|---------:|:-------|",
        ]
        for index, (source, name, duration, conclusion) in enumerate(timing_rows[:10]):
            marker = "🏁 " if index == 0 else ""
            out.append(
                f"| {md_cell(source)} | {marker}{md_cell(name)} | "
                f"{format_duration(duration)} | {job_icon(conclusion)} {md_cell(conclusion)} |"
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
                f"{md_cell(row['outcome'])} |"
            )
        out += ["", "</details>"]

    if tc_live_timings:
        out += [
            "",
            "<details><summary><b>Test Client Conformance Timing Details</b></summary>",
            "",
            "| Test | Duration | Outcome |",
            "|:-----|---------:|:--------|",
        ]
        for row in tc_live_timings["top"]:
            out.append(
                f"| {md_cell(row['method'])} | {format_duration(row['duration'])} | "
                f"{md_cell(row['outcome'])} |"
            )
        out += ["", "</details>"]
    else:
        out += [
            "",
            "<details><summary><b>Test Client Conformance Timing Details</b></summary>",
            "",
            "Per-test durations are not available in the current JUnit artifact.",
            "",
            "</details>",
        ]

    out += ["", "---", "", '<a id="system-warnings-drift"></a>', "", "### Warnings and Drift", ""]
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
        out += ["No skip policy failures, test-count drift warnings, or artifact warnings."]

    # ── Inline skip details (collapsible) ──────────────────────────

    skip_sections = []
    skip_sections += format_skip_section(
        "OPC UA Server — Docker Smoke", sd_smoke_skips, sd_smoke[3]
    )
    skip_sections += format_skip_section("Web Client — Docker Python Unit", wd_py_skips, wd_py[3])
    skip_sections += format_skip_section("Web Client — Docker JavaScript", wd_js_skips, wd_js[3])
    skip_sections += format_skip_section("Test Client — Smoke Sanity", tc_smoke_skips, tc_smoke[3])
    skip_sections += format_skip_section("Test Client — Conformance", tc_conf_skips, tc_tests[3])
    skip_sections += format_skip_section("Console Client — Live", con_live_skips, con_live[3])
    skip_sections += format_skip_section(
        "Web Client — Python/WebSocket Live", wc_live_skips, wc_live[3]
    )
    skip_sections += format_skip_section(
        "Web Client — Browser E2E", wc_browser_skips, wc_browser[3]
    )
    skip_sections += format_skip_section("C# Client — Live", cs_live_skips, cs_live[3])

    out += [
        "",
        "---",
        "",
        "### Artifacts and Drilldown",
        "",
        "> 📦 **Artifacts** — JUnit XML &nbsp;·&nbsp; 📋 **Checks** tab — per-test drill-down",
        "> 🔒 Security audit (zizmor) results are in **CI** → Security → Code Scanning",
    ]

    if skip_sections:
        out += ["", "#### Skip Details"]
        out += skip_sections

    out += [
        "",
        "---",
        "",
        '<a id="system-per-client-quick-index"></a>',
        "",
        "### Per-Client Quick Index",
        "",
        "| Client / Component | Appears In |",
        "|:-------------------|:-----------|",
        (
            "| OPC UA Server | [Validation Overview](#system-validation-overview); "
            "[Component Test Results](#system-component-test-results); "
            "[Performance Hotspots](#system-performance-hotspots) |"
        ),
        (
            "| Web Client | [Validation Overview](#system-validation-overview); "
            "[Component Test Results](#system-component-test-results); "
            "[Performance Hotspots](#system-performance-hotspots) |"
        ),
        (
            "| Test Client | [Validation Overview](#system-validation-overview); "
            "[Component Test Results](#system-component-test-results); "
            "[Conformance Overview](#system-conformance-overview); "
            "[Performance Hotspots](#system-performance-hotspots) |"
        ),
        (
            "| Console Client | [Validation Overview](#system-validation-overview); "
            "[Component Test Results](#system-component-test-results) |"
        ),
        (
            "| C# Client | [Validation Overview](#system-validation-overview); "
            "[Component Test Results](#system-component-test-results); "
            "[Performance Hotspots](#system-performance-hotspots) |"
        ),
    ]

    with open(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/stdout"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("Summary written.")
    if skip_policy_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
