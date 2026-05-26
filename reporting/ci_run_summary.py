"""Generate the IJT fast CI GitHub Actions summary."""

import contextlib
import datetime
import glob
import json
import os
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


# ── Parsers ──────────────────────────────────────────────────────────


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
    # Reject internal-subset DOCTYPE (the entity-injection vector); allow
    # bare external DOCTYPE such as Vitest's cobertura output.
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
    for path in glob.glob(pattern, recursive=True):
        try:
            root = parse_xml_root(path)
            suites = iter_suites(root)
            t = sum(int(s.get("tests", 0)) for s in suites)
            f = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
            sk = sum(int(s.get("skipped", 0)) for s in suites)
            return t, t - f - sk, f, sk
        except Exception as exc:
            print(f"[WARN] parse_junit({path}): {exc}")
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


def timing_status_fmt(status: str) -> str:
    """Render CI timing status as text followed by an icon."""
    if status == "success":
        return "Success ✅"
    if status == "failure":
        return "Failure ❌"
    if status == "skipped":
        return "Skipped ⏭️"
    return "Unknown ⚠️"


def seconds(value):
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def format_duration(value):
    value = seconds(value)
    if value >= 60.0:
        return f"{value / 60.0:.1f} min"
    return f"{value:.1f} s"


def parse_actions_time(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def next_link(header):
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
        "User-Agent": "ijt-ci-report",
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


def parse_coverage(pattern):
    for path in glob.glob(pattern, recursive=True):
        with contextlib.suppress(Exception):
            rate = parse_xml_root(path).get("line-rate")
            if rate is not None:
                return round(float(rate) * 100, 1)
    return None


def parse_bandit(pattern):
    for path in glob.glob(pattern, recursive=True):
        with contextlib.suppress(Exception):
            with open(path) as _f:
                r = json.load(_f).get("results", [])
            return (
                sum(1 for i in r if i["issue_severity"] == "HIGH"),
                sum(1 for i in r if i["issue_severity"] == "MEDIUM"),
            )
    return None, None


def parse_npm_audit(pattern):
    for path in glob.glob(pattern, recursive=True):
        with contextlib.suppress(Exception):
            with open(path) as _f:
                v = json.load(_f).get("metadata", {}).get("vulnerabilities", {})
            return v.get("critical", 0), v.get("high", 0)
    return None, None


def parse_pip_audit(pattern):
    for path in glob.glob(pattern, recursive=True):
        with contextlib.suppress(Exception):
            with open(path) as _f:
                data = json.load(_f)
            vulns = [
                vuln
                for dependency in data.get("dependencies", [])
                if isinstance(dependency, dict)
                for vuln in dependency.get("vulns", [])
                if isinstance(vuln, dict)
            ]
            fixable = sum(1 for vuln in vulns if vuln.get("fix_versions"))
            return len(vulns), fixable, True
    return None, None, False


def parse_eslint(pattern):
    for path in glob.glob(pattern, recursive=True):
        with contextlib.suppress(Exception):
            with open(path) as _f:
                data = json.load(_f)
            return (
                sum(r.get("errorCount", 0) for r in data),
                sum(r.get("warningCount", 0) for r in data),
            )
    return None, None


# ── Formatters ───────────────────────────────────────────────────────


def job_icon(r):
    return {"success": "✅", "failure": "❌", "cancelled": "🚫", "skipped": "⏭️"}.get(r, "⚠️")


def missing_cell(job_result=None):
    """Return explicit text for data that is not present in the report."""
    return "Not Run" if job_result == "skipped" else "Not Reported"


def tests(total, passed, failed, skipped=0, job_result=None):
    if total is None:
        return missing_cell(job_result)
    if failed:
        return f"{passed:,} / {total:,} Passed ❌"
    return f"{passed:,} Passed ✅"


def tests_cell(counts, job_result=None):
    return tests(counts[0], counts[1], counts[2], counts[3], job_result=job_result)


def skips(sk, job_result=None):
    return missing_cell(job_result) if sk is None else f"{sk:,} Skipped"


def cov(pct, threshold=None, job_result=None):
    if pct is None:
        return missing_cell(job_result)
    if threshold is None:
        icon = "✅" if pct >= 90 else ("⚠️" if pct >= 70 else "❌")
        return f"{pct:.1f}% {icon}"
    icon = "✅" if pct >= threshold else ("⚠️" if pct >= 80 else "❌")
    return f"{pct:.1f}% / {threshold:.0f}% {icon}"


def plural_label(count: int, singular: str, plural: str | None = None) -> str:
    """Return a count plus a correctly pluralized public label."""
    label = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {label}"


# ── Cell-status helpers ──────────────────────────────────────────────
# Cells in the Code Quality / Security tables lead with a status icon so that
# multi-tool cells (joined with <br>) stay visually aligned at the cell's left
# edge.  The row-level status icon column is derived from cell contents by
# scanning for these icons in priority order.

_CELL_NOT_APPLICABLE = "➖ Not Applicable"
_CELL_CSHARP_CODEQL_NOTE = "ℹ️ CodeQL source scan runs in Security workflow"
_CELL_ESLINT_SEC_OUT_OF_SCOPE = "➖ Out of scope — legacy check"


def row_status_icon(*cells: str) -> str:
    """Pick the row-level status icon by scanning cell contents.

    Priority: ❌ failure > 🚫 cancelled > ⚠️ warning/gap > ⏭️ not run / not reported > ✅ pass.
    ``ℹ️`` (informational deflection) and ``➖`` (not applicable / not measured)
    are ignored — they must never demote a passing row.
    """
    text = " ".join(c for c in cells if c)
    if "❌" in text:
        return "❌"
    if "🚫" in text:
        return "🚫"
    if "⚠️" in text:
        return "⚠️"
    if "⏭️" in text:
        return "⏭️"
    return "✅"


def _wrap(icon: str, text: str) -> str:
    return f"{icon} {text}"


def tool(r, label, job_result=None):
    if job_result == "skipped":
        return _wrap("⏭️", f"{label} (Not Run)")
    if not r or r in ("", "unknown"):
        return _wrap("⏭️", f"{label} (Not Reported)")
    if r == "skipped":
        return _wrap("⏭️", f"{label} (Not Run)")
    icon = {"success": "✅", "failure": "❌", "cancelled": "🚫", "skipped": "⏭️"}.get(r, "⚠️")
    return _wrap(icon, label)


def bandit_fmt(high, medium, job_result=None):
    if job_result == "skipped":
        return _wrap("⏭️", "bandit (Not Run)")
    if high is None:
        return _wrap("⏭️", "bandit (Not Reported)")
    if high == 0 and medium == 0:
        return _wrap("✅", "bandit (0 issues)")
    return _wrap("❌", f"bandit ({high} high, {medium} medium)")


def pip_audit_fmt(total, fixable, available, job_result=None):
    if job_result == "skipped":
        return _wrap("⏭️", "pip-audit (Not Run)")
    if not available:
        return _wrap("⏭️", "pip-audit (Not Reported)")
    if total is None or fixable is None:
        return _wrap("⏭️", "pip-audit (Not Reported)")
    if total == 0:
        return _wrap("✅", "pip-audit (0 CVEs)")
    if fixable > 0:
        return _wrap("❌", f"pip-audit ({fixable} fixable CVE{'s' if fixable != 1 else ''})")
    return _wrap("⚠️", f"pip-audit ({total} advisory CVE{'s' if total != 1 else ''})")


def npm_fmt(crit, high, job_result=None):
    if job_result == "skipped":
        return _wrap("⏭️", "npm-audit (Not Run)")
    if crit is None:
        return _wrap("⏭️", "npm-audit (Not Reported)")
    if crit == 0 and high == 0:
        return _wrap("✅", "npm-audit (0 critical)")
    return _wrap("❌", f"npm-audit ({crit} critical, {high} high)")


def nuget_fmt(result):
    if result == "success":
        return _wrap("✅", "nuget (0 vulnerable)")
    if result == "failure":
        return _wrap("❌", "nuget (vulnerable packages detected)")
    if result == "skipped":
        return _wrap("⏭️", "nuget (Not Run)")
    if not result or result == "unknown":
        return _wrap("⏭️", "nuget (Not Reported)")
    return tool(result, "nuget")


def eslint_fmt(step_r, esl_tuple, job_result=None):
    errors, warnings = esl_tuple
    warn_count = warnings or 0
    if errors is not None:
        if errors == 0 and warn_count == 0:
            return _wrap("✅", "eslint")
        if errors == 0:
            return _wrap("⚠️", f"eslint ({warn_count} warnings)")
        return _wrap("❌", f"eslint ({errors} errors, {warn_count} warnings)")
    if job_result == "skipped":
        return tool("skipped", "eslint")
    return tool(step_r, "eslint")


def lint(*items):
    """Join icon-leading cell tokens with ``<br>`` so each tool keeps its own line."""
    parts = [p for p in items if p and p != "—"]
    return "<br>".join(parts) or _wrap("⏭️", "Not Reported")


def main() -> None:
    # Reason: CLI orchestration tested via snapshot tests
    # ── Load ENV ─────────────────────────────────────────────────────────

    E = os.environ.get

    web_py_r = E("WEB_PY_RESULT", "unknown")
    web_js_r = E("WEB_JS_RESULT", "unknown")
    con_r = E("CONSOLE_RESULT", "unknown")
    nod_r = E("NODE_RESULT", "unknown")
    dck_r = E("DOCKER_RESULT", "unknown")
    cs_u_r = E("CS_UNIT_RESULT", "unknown")
    cs_v_r = E("CS_VULN_RESULT", "unknown")
    tc_r = E("TC_RESULT", "unknown")
    ss_r = E("SS_WIN_RESULT", "unknown")
    al_r = E("AL_RESULT", "unknown")
    zz_r = E("ZZ_RESULT", "unknown")
    pc_r = E("PC_RESULT", "unknown")

    web_ruff = E("WEB_PY_RUFF", "")
    web_eslint = E("WEB_JS_ESLINT", "")
    web_mypy = E("WEB_PY_MYPY", "")
    con_ruff = E("CONSOLE_RUFF", "")
    con_mypy = E("CONSOLE_MYPY", "")
    nod_eslint = E("NODE_ESLINT", "")
    cs_build = E("CS_BUILD", "")
    cs_format = E("CS_FORMAT", "")
    cs_vuln = E("CS_VULN", "")
    tc_ruff = E("TC_RUFF", "")
    tc_mypy = E("TC_MYPY", "")

    sha = (E("GH_SHA", "") or "")[:8]
    branch = E("GH_BRANCH", "main")
    run_num = E("GH_RUN_NUMBER", "")
    run_url = E("GH_RUN_URL", "")
    job_timings = job_durations(
        f"repos/{E('GH_REPOSITORY', '')}/actions/runs/{E('GH_RUN_ID', '')}/jobs"
    )

    # ── Parse artifacts ──────────────────────────────────────────────────

    web_py_t = parse_junit("all-results/results-web-client-python/pytest.xml")
    web_js_t = parse_junit("all-results/results-web-client-js/vitest.xml")
    web_esl = parse_eslint("all-results/results-web-client-js/eslint.json")
    web_ban = parse_bandit("all-results/results-web-client-python/bandit.json")
    web_pip = parse_pip_audit("all-results/results-web-client-python/pip-audit.json")
    web_npm = parse_npm_audit("all-results/results-web-client-js/npm-audit.json")
    web_cov = parse_coverage("all-results/results-web-client-python/coverage.xml")
    web_js_cov = parse_coverage("all-results/results-web-client-js/coverage/cobertura-coverage.xml")

    con_py_t = parse_junit("all-results/results-console-client/pytest.xml")
    con_ban = parse_bandit("all-results/results-console-client/bandit.json")
    con_pip = parse_pip_audit("all-results/results-console-client/pip-audit.json")
    con_cov = parse_coverage("all-results/results-console-client/coverage.xml")

    nod_js_t = parse_junit("all-results/results-node-client/vitest.xml")
    nod_esl = parse_eslint("all-results/results-node-client/eslint.json")
    nod_npm = parse_npm_audit("all-results/results-node-client/npm-audit.json")

    cs_unit_t = parse_junit("all-results/results-csharp-unit/tests.xml")
    cs_cov = parse_coverage("all-results/results-csharp-unit/coverage/cobertura.xml")

    tc_py_t = parse_junit("all-results/results-test-client/pytest.xml")
    tc_ban = parse_bandit("all-results/results-test-client/bandit.json")
    tc_pip = parse_pip_audit("all-results/results-test-client/pip-audit.json")
    tc_cov = parse_coverage("all-results/results-test-client/coverage.xml")

    nod_cov = parse_coverage("all-results/results-node-client/coverage/cobertura-coverage.xml")

    ss_smoke = parse_junit("all-results/results-server-smoke/smoke.xml")

    # ── Collect skip details from JUnit XML ──────────────────────────

    web_py_skips = collect_skips("all-results/results-web-client-python/pytest.xml")
    web_js_skips = collect_skips("all-results/results-web-client-js/vitest.xml")
    con_py_skips = collect_skips("all-results/results-console-client/pytest.xml")
    nod_js_skips = collect_skips("all-results/results-node-client/vitest.xml")
    cs_unit_skips = collect_skips("all-results/results-csharp-unit/tests.xml")
    tc_py_skips = collect_skips("all-results/results-test-client/pytest.xml")
    ss_smoke_skips = collect_skips("all-results/results-server-smoke/smoke.xml")

    # ── Artifact sanity gate ─────────────────────────────────────────────

    artifact_warnings = []

    def _warn(job_result, val, job_name, artifact):
        if job_result == "success" and val is None:
            artifact_warnings.append(
                f"⚠️ **{job_name}**: job succeeded but `{artifact}` not found — "
                "possible silent failure"
            )

    _warn(web_py_r, web_py_t[0], "web-client-python", "pytest.xml")
    _warn(web_py_r, web_cov, "web-client-python", "coverage.xml")
    _warn(web_js_r, web_js_t[0], "web-client-js", "vitest.xml")
    _warn(web_js_r, web_js_cov, "web-client-js", "coverage/cobertura-coverage.xml")
    _warn(con_r, con_py_t[0], "console-client", "pytest.xml")
    _warn(con_r, con_cov, "console-client", "coverage.xml")
    _warn(nod_r, nod_js_t[0], "node-client", "vitest.xml")
    _warn(nod_r, nod_cov, "node-client", "coverage/cobertura-coverage.xml")
    _warn(cs_u_r, cs_unit_t[0], "csharp-unit", "tests.xml")
    _warn(cs_u_r, cs_cov, "csharp-unit", "coverage/cobertura.xml")
    _warn(tc_r, tc_py_t[0], "test-client", "pytest.xml")
    _warn(tc_r, tc_ban[0], "test-client", "bandit.json")
    _warn(tc_r, tc_cov, "test-client", "coverage.xml")
    _warn(ss_r, ss_smoke[0], "server-smoke-windows", "smoke.xml")

    coverage_checks = [
        ("Web Client — Python", web_cov, 95.0),
        ("Web Client — JavaScript", web_js_cov, 95.0),
        ("Console Client — Python", con_cov, 95.0),
        ("Node Client — Legacy JavaScript", nod_cov, 95.0),
        ("C# Client — Unit", cs_cov, 95.0),
        ("Test Client — Python", tc_cov, 95.0),
    ]
    coverage_warnings = []
    for label, pct, threshold in coverage_checks:
        if pct is not None and pct < threshold:
            coverage_warnings.append(
                f"⚠️ **{label}**: {pct:.1f}% coverage is below the declared "
                f"{threshold:.0f}% threshold."
            )

    # ── Skip budget check (computed early so status line can report it) ─
    # Known expected skips per TEST_TIERS.md; any extra skip is a warning.
    skip_budget = {
        "web-client (Python)": 2,  # Split Python lane delegates JS/npm checks to web-client-js
        "web-client (JS)": 0,
        "console-client (Python)": 0,
        "node-client (JS)": 1,  # git unavailable in CI (vitest)
        "csharp-unit": 15,  # IJT_PHASE1_ONLY filter
        "test-client (Python)": 0,
        "server-smoke (Windows)": 0,
    }
    expected_skip_names = {
        "web-client (Python)": {
            "test_required_static_asset_exists[node_modules/chart.js/dist/chart.umd.js]",
            "test_eslint_passes",
        },
    }
    actual_skips = {
        "web-client (Python)": web_py_t[3],
        "web-client (JS)": web_js_t[3],
        "console-client (Python)": con_py_t[3],
        "node-client (JS)": nod_js_t[3],
        "csharp-unit": cs_unit_t[3],
        "test-client (Python)": tc_py_t[3],
        "server-smoke (Windows)": ss_smoke[3],
    }
    skip_details_by_suite = {
        "web-client (Python)": web_py_skips,
        "web-client (JS)": web_js_skips,
        "console-client (Python)": con_py_skips,
        "node-client (JS)": nod_js_skips,
        "csharp-unit": cs_unit_skips,
        "test-client (Python)": tc_py_skips,
        "server-smoke (Windows)": ss_smoke_skips,
    }
    budget_warnings = []
    for suite, budget in skip_budget.items():
        actual = actual_skips[suite]
        expected_names = expected_skip_names.get(suite)
        if actual is not None and expected_names is not None:
            actual_names = {name for name, _ in skip_details_by_suite[suite]}
            unexpected_names = sorted(actual_names - expected_names)
            missing_expected_names = sorted(expected_names - actual_names)
            if unexpected_names:
                budget_warnings.append(
                    f"⚠️ **{suite}**: unexpected skips detected: "
                    + ", ".join(f"`{name}`" for name in unexpected_names)
                )
            if missing_expected_names:
                budget_warnings.append(
                    f"⚠️ **{suite}**: expected skips not observed; remove or update the "
                    "documented skip budget if these gates no longer skip: "
                    + ", ".join(f"`{name}`" for name in missing_expected_names)
                )
            elif not unexpected_names and actual > len(expected_names):
                budget_warnings.append(
                    f"⚠️ **{suite}**: {actual} skips but only {len(expected_names)} "
                    "expected skip identities are documented"
                )
            continue
        if actual is not None and actual > budget:
            budget_warnings.append(
                f"⚠️ **{suite}**: {actual} skips (budget: {budget}) — unexpected skips detected"
            )

    # ── Overall status ────────────────────────────────────────────────────

    all_jobs = [
        web_py_r,
        web_js_r,
        con_r,
        nod_r,
        dck_r,
        cs_u_r,
        cs_v_r,
        tc_r,
        ss_r,
        al_r,
        zz_r,
        pc_r,
    ]
    n_pass = sum(1 for r in all_jobs if r == "success")
    n_fail = sum(1 for r in all_jobs if r == "failure")
    n_skipped = sum(1 for r in all_jobs if r == "skipped")
    n_total = len(all_jobs)

    if n_fail == 0:
        if n_pass == n_total:
            status_icon = "✅"
            status_msg = f"All {n_pass} / {n_total} Jobs Passed"
        elif n_pass == 0 and n_skipped == n_total:
            status_icon = "⏭️"
            status_msg = f"No CI Jobs Ran · {n_skipped} Skipped"
        else:
            status_icon = "✅"
            status_msg = f"{n_pass} / {n_total} Jobs Passed · {n_skipped} Skipped"
    else:
        status_icon = "❌"
        status_msg = f"{n_fail} / {n_total} Jobs Failed  ·  {n_pass} Passed"

    suites = [web_py_t, web_js_t, con_py_t, nod_js_t, cs_unit_t, tc_py_t, ss_smoke]
    total_t = sum(s[0] for s in suites if s[0] is not None)
    total_f = sum(s[2] for s in suites if s[2] is not None)
    total_sk = sum(s[3] for s in suites if s[3] is not None)
    total_passed = max(total_t - total_f - total_sk, 0)

    status_clean = (
        n_fail == 0 and not coverage_warnings and not budget_warnings and not artifact_warnings
    )
    status_emoji = "✅" if status_clean else "⚠️"
    status_summary = (
        f"{status_emoji} **Status:** {n_fail} Failed Jobs &nbsp;·&nbsp; "
        f"{len(coverage_warnings)} Coverage Warnings &nbsp;·&nbsp; "
        f"{len(budget_warnings)} Skip-Budget Warnings &nbsp;·&nbsp; "
        f"{len(artifact_warnings)} Artifact Warnings"
    )

    run_link = f"[#{run_num}]({run_url})" if run_url else f"#{run_num}"
    sha_str = f"`{sha}`" if sha else "Not Reported"
    web_quality = lint(
        tool(web_ruff, "ruff", web_py_r),
        eslint_fmt(web_eslint, web_esl, web_js_r),
    )
    web_dep_audit = lint(
        pip_audit_fmt(web_pip[0], web_pip[1], web_pip[2], web_py_r),
        npm_fmt(web_npm[0], web_npm[1], web_js_r),
    )
    cs_quality = lint(tool(cs_build, "build", cs_u_r), tool(cs_format, "format", cs_u_r))

    # Pre-render Code Quality cells so the leading status column can be derived.
    cq_web_lint = web_quality
    cq_web_type = tool(web_mypy, "mypy", web_py_r)
    cq_con_lint = tool(con_ruff, "ruff", con_r)
    cq_con_type = tool(con_mypy, "mypy", con_r)
    cq_nod_lint = eslint_fmt(nod_eslint, nod_esl, nod_r)
    cq_cs_lint = cs_quality
    cq_tc_lint = tool(tc_ruff, "ruff", tc_r)
    cq_tc_type = tool(tc_mypy, "mypy", tc_r)

    # Pre-render Security cells so the leading status column can be derived.
    sec_web_scan = bandit_fmt(web_ban[0], web_ban[1], web_py_r)
    sec_web_dep = web_dep_audit
    sec_con_scan = bandit_fmt(con_ban[0], con_ban[1], con_r)
    sec_con_dep = pip_audit_fmt(con_pip[0], con_pip[1], con_pip[2], con_r)
    sec_nod_dep = npm_fmt(nod_npm[0], nod_npm[1], nod_r)
    sec_cs_dep = nuget_fmt(cs_vuln)
    sec_tc_scan = bandit_fmt(tc_ban[0], tc_ban[1], tc_r)
    sec_tc_dep = pip_audit_fmt(tc_pip[0], tc_pip[1], tc_pip[2], tc_r)
    validation_check_count = len(suites)
    quality_component_count = len([web_quality, con_ruff, nod_eslint, cs_quality, tc_ruff])
    security_component_count = len([web_dep_audit, con_pip, nod_npm, cs_vuln, tc_pip])
    infrastructure_check_count = len([dck_r, al_r, zz_r, pc_r])
    quick_index_entry_count = len(
        [
            "Web Client",
            "Console Client",
            "Node Client — Legacy JavaScript",
            "C# Client",
            "Test Client",
            "OPC UA Server",
        ]
    )

    # ── Build report ──────────────────────────────────────────────────────

    out = [
        "## IJT OPC UA — CI",
        "",
        f"> {status_icon} **{status_msg}**",
        (
            f"> **Branch:** `{branch}` &nbsp;·&nbsp; **Commit:** {sha_str} "
            f"&nbsp;·&nbsp; **Run:** {run_link}"
        ),
        "",
        (
            "> Full report below: [Outcome](#ci-outcome-overview) · "
            "[Validation](#ci-validation-results) · [Code Quality](#ci-code-quality-checks) · "
            "[Security](#ci-source-dependency-security) · [Infrastructure](#ci-infrastructure) · "
            "[Timing](#ci-performance-timings) · [Skip Details](#ci-skip-details)"
        ),
        "",
        "---",
        "",
        '<a id="ci-outcome-overview"></a>',
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
        '<a id="ci-validation-results"></a>',
        "",
        f"### 🧪 Validation Results — {plural_label(validation_check_count, 'check')}",
        "",
        "| Component | Validation Scope | Test Cases | Skipped | Coverage / Threshold |",
        "|:----------|:-----------------|----------:|--------:|:---------------------:|",
        (
            f"| Web Client — Python | Ubuntu Release 2 Python unit suite | "
            f"{tests_cell(web_py_t, web_py_r)} | "
            f"{skips(web_py_t[3], web_py_r)} | {cov(web_cov, 95, web_py_r)} |"
        ),
        (
            "| Web Client — JavaScript | Ubuntu Release 2 JavaScript unit suite | "
            f"{tests_cell(web_js_t, web_js_r)} | "
            f"{skips(web_js_t[3], web_js_r)} | {cov(web_js_cov, 95, web_js_r)} |"
        ),
        (
            f"| Console Client — Python | Ubuntu Python unit suite | "
            f"{tests_cell(con_py_t, con_r)} | "
            f"{skips(con_py_t[3], con_r)} | {cov(con_cov, 95, con_r)} |"
        ),
        (
            "| Node Client — Legacy JavaScript | Ubuntu Release 1 JavaScript unit suite | "
            f"{tests_cell(nod_js_t, nod_r)} | "
            f"{skips(nod_js_t[3], nod_r)} | {cov(nod_cov, 95, nod_r)} |"
        ),
        (
            f"| C# Client — Unit (xUnit) | Windows C# xUnit unit suite | "
            f"{tests_cell(cs_unit_t, cs_u_r)} | "
            f"{skips(cs_unit_t[3], cs_u_r)} | {cov(cs_cov, 95, cs_u_r)} |"
        ),
        (
            f"| Test Client — Python (Unit) | Ubuntu Python unit suite | "
            f"{tests_cell(tc_py_t, tc_r)} | "
            f"{skips(tc_py_t[3], tc_r)} | {cov(tc_cov, 95, tc_r)} |"
        ),
        (
            f"| OPC UA Server — Smoke | Windows native server smoke check | "
            f"{tests_cell(ss_smoke, ss_r)} | "
            f"{skips(ss_smoke[3], ss_r)} | "
            f"{_CELL_NOT_APPLICABLE} |"
        ),
        "",
        "---",
        "",
        '<a id="ci-code-quality-checks"></a>',
        "",
        f"### 🧹 Code Quality Checks — {quality_component_count} components",
        "",
        "| 🚦 | Component | Validation Scope | Lint / Format | Type Check / Build |",
        "|:--:|:----------|:-----------------|:--------------|:-------------------|",
        (
            f"| {row_status_icon(cq_web_lint, cq_web_type)} "
            f"| Web Client | Python and JavaScript static quality "
            f"| {cq_web_lint} | {cq_web_type} |"
        ),
        (
            f"| {row_status_icon(cq_con_lint, cq_con_type)} "
            f"| Console Client | Python static quality "
            f"| {cq_con_lint} | {cq_con_type} |"
        ),
        (
            f"| {row_status_icon(cq_nod_lint)} "
            f"| Node Client — Legacy JavaScript | JavaScript static quality "
            f"| {cq_nod_lint} | {_CELL_NOT_APPLICABLE} |"
        ),
        (
            f"| {row_status_icon(cq_cs_lint)} "
            f"| C# Client | Build and formatting quality "
            f"| {cq_cs_lint} | {_CELL_NOT_APPLICABLE} |"
        ),
        (
            f"| {row_status_icon(cq_tc_lint, cq_tc_type)} "
            f"| Test Client | Python static quality "
            f"| {cq_tc_lint} | {cq_tc_type} |"
        ),
        "",
        "---",
        "",
        '<a id="ci-source-dependency-security"></a>',
        "",
        f"### 🔒 Source and Dependency Security — {security_component_count} components",
        "",
        "- **Audit and Code Scanning**",
        "  - Bandit scans Python source for security issues.",
        (
            "  - pip-audit, npm audit, and NuGet audit scan package dependencies "
            "for known vulnerabilities."
        ),
        "- **Related Security Checks**",
        "  - CI Infrastructure runs zizmor for GitHub Actions workflow security.",
        "  - Pre-commit Hooks runs detect-secrets for committed secret detection.",
        "  - Security — CodeQL runs semantic code analysis.",
        "",
        "| 🚦 | Component | Security Scan | Dependency Audit |",
        "|:--:|:----------|:--------------|:-----------------|",
        (
            f"| {row_status_icon(sec_web_scan, sec_web_dep)} "
            f"| Web Client | {sec_web_scan} | {sec_web_dep} |"
        ),
        (
            f"| {row_status_icon(sec_con_scan, sec_con_dep)} "
            f"| Console Client | {sec_con_scan} | {sec_con_dep} |"
        ),
        (
            f"| {row_status_icon(_CELL_ESLINT_SEC_OUT_OF_SCOPE, sec_nod_dep)} "
            f"| Node Client — Legacy JavaScript "
            f"| {_CELL_ESLINT_SEC_OUT_OF_SCOPE} | {sec_nod_dep} |"
        ),
        (
            f"| {row_status_icon(sec_cs_dep)} "
            f"| C# Client | {_CELL_CSHARP_CODEQL_NOTE} | {sec_cs_dep} |"
        ),
        (
            f"| {row_status_icon(sec_tc_scan, sec_tc_dep)} "
            f"| Test Client | {sec_tc_scan} | {sec_tc_dep} |"
        ),
        "",
        "---",
        "",
        '<a id="ci-infrastructure"></a>',
        "",
        f"### ⚙️ CI Infrastructure — {infrastructure_check_count} checks",
        "",
        "| Check | Status |",
        "|:------|:------:|",
        f"| Web Client — Docker Smoke (HTTP + WebSocket) | {job_icon(dck_r)} |",
        f"| GHA Workflow Lint (actionlint)               | {job_icon(al_r)} |",
        f"| GHA Security Audit (zizmor)                  | {job_icon(zz_r)} |",
        f"| Pre-commit Hooks                             | {job_icon(pc_r)} |",
        "",
        "---",
        "",
        '<a id="ci-performance-timings"></a>',
        "",
        "### ⏱️ Timing",
        "",
    ]
    if job_timings:
        out += [
            "| Job | Duration | Status |",
            "|:----|---------:|:-------|",
        ]
        for name, duration, conclusion in job_timings[:10]:
            out.append(
                f"| {md_cell(name)} | {format_duration(duration)} | "
                f"{timing_status_fmt(str(conclusion))} |"
            )
    else:
        out += [
            (
                "No reliable job duration source was available. Job durations require "
                "the current-run Jobs API."
            ),
        ]
    out += [
        "",
        "---",
        "",
        '<a id="ci-raw-data"></a>',
        "",
        "### Where to find raw data",
        "",
        "- JUnit XML",
        "- Coverage XML",
        "- ESLint JSON",
        "- Bandit JSON",
        "- pip-audit / npm-audit JSON",
        "- Per-test drill-down: Checks tab",
        "",
        '<a id="ci-coverage-legend"></a>',
        "",
        "### Coverage Legend",
        "",
        "| Icon | Meaning |",
        "|:-----|:--------|",
        "| ✅ | Meets the declared threshold |",
        "| ⚠️ | Below threshold but at least 80% |",
        "| ❌ | Below 80% |",
        "",
        "Thresholds come from `pyproject.toml`, `vitest.config.mjs`, and the C# coverage gate.",
    ]

    # ── Inline skip details (collapsible) ─────────────────────────────

    skip_suite_counts = [
        ("Web Client — Python", web_py_skips, web_py_t[3]),
        ("Web Client — JavaScript", web_js_skips, web_js_t[3]),
        ("Console Client — Python", con_py_skips, con_py_t[3]),
        ("Node Client — Legacy JavaScript", nod_js_skips, nod_js_t[3]),
        ("C# Client — Unit", cs_unit_skips, cs_unit_t[3]),
        ("Test Client — Python", tc_py_skips, tc_py_t[3]),
        ("OPC UA Server — Smoke", ss_smoke_skips, ss_smoke[3]),
    ]
    skip_sections = []
    for label, skips_list, suite_skip_count in skip_suite_counts:
        skip_sections += format_skip_section(label, skips_list, suite_skip_count)

    if skip_sections:
        skip_count = sum(
            max(suite_skip_count or 0, len(skips_list))
            for _, skips_list, suite_skip_count in skip_suite_counts
            if (suite_skip_count or 0) > 0 or skips_list
        )
        suite_count = sum(
            1
            for _, skips_list, suite_skip_count in skip_suite_counts
            if (suite_skip_count or 0) > 0 or skips_list
        )
        out += [
            "",
            "---",
            "",
            '<a id="ci-skip-details"></a>',
            "",
            (
                f"### ⏭️ Skip Details — {plural_label(suite_count, 'suite')}, "
                f"{plural_label(skip_count, 'skip')}"
            ),
        ]
        out += skip_sections
    else:
        out += [
            "",
            "---",
            "",
            '<a id="ci-skip-details"></a>',
            "",
            "### ⏭️ Skip Details — 0 suites, 0 skips",
            "",
            "No skipped tests reported.",
        ]

    # ── Skip budget check (computed earlier; render here) ───────────────
    if budget_warnings:
        out += ["", "---", "", "### ⏭️ Skip Budget Exceeded", ""]
        out += budget_warnings

    if coverage_warnings:
        out += ["", "---", "", "### ⚠️ Coverage Threshold Warnings", ""]
        out += coverage_warnings

    if artifact_warnings:
        out += ["", "---", "", "### ⚠️ Artifact Warnings", ""]
        out += artifact_warnings

    out += [
        "",
        "---",
        "",
        '<a id="ci-per-client-quick-index"></a>',
        "",
        f"### 📚 Per-Client Quick Index — {quick_index_entry_count} entries",
        "",
        "| Client / Component | Appears In |",
        "|:-------------------|:-----------|",
        (
            "| Web Client | [Validation Results](#ci-validation-results) · "
            "[Code Quality Checks](#ci-code-quality-checks) · "
            "[Source and Dependency Security](#ci-source-dependency-security) · "
            "[Timing](#ci-performance-timings) |"
        ),
        (
            "| Console Client | [Validation Results](#ci-validation-results) · "
            "[Code Quality Checks](#ci-code-quality-checks) · "
            "[Source and Dependency Security](#ci-source-dependency-security) · "
            "[Timing](#ci-performance-timings) |"
        ),
        (
            "| Node Client — Legacy JavaScript | [Validation Results](#ci-validation-results) · "
            "[Code Quality Checks](#ci-code-quality-checks) · "
            "[Source and Dependency Security](#ci-source-dependency-security) · "
            "[Timing](#ci-performance-timings) |"
        ),
        (
            "| C# Client | [Validation Results](#ci-validation-results) · "
            "[Code Quality Checks](#ci-code-quality-checks) · "
            "[Source and Dependency Security](#ci-source-dependency-security) · "
            "[Timing](#ci-performance-timings) |"
        ),
        (
            "| Test Client | [Validation Results](#ci-validation-results) · "
            "[Code Quality Checks](#ci-code-quality-checks) · "
            "[Source and Dependency Security](#ci-source-dependency-security) · "
            "[Timing](#ci-performance-timings) |"
        ),
        (
            "| OPC UA Server | [Validation Results](#ci-validation-results) · "
            "[CI Infrastructure](#ci-infrastructure) · [Timing](#ci-performance-timings) |"
        ),
    ]

    with open(
        os.environ.get("GITHUB_STEP_SUMMARY", "/dev/stdout"), "a", encoding="utf-8", newline="\n"
    ) as fh:
        fh.write("\n".join(out) + "\n")
    print("Summary written.")


if __name__ == "__main__":
    main()
