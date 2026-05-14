"""Generate the IJT fast CI GitHub Actions summary."""

import contextlib
import glob
import json
import os
import xml.etree.ElementTree as ET
from collections import Counter

# ── Parsers ──────────────────────────────────────────────────────────


def parse_xml_root(path):
    """Parse a local CI XML artifact without allowing DTD/entity declarations."""
    with open(path, "rb") as fh:
        payload = fh.read()
    header = payload[:2048].lower()
    if b"<!doctype" in header or b"<!entity" in header:
        raise ValueError("DTD/entity declarations are not supported in CI XML artifacts")
    # safe: local CI artifact parser rejects DTD/entity declarations before parsing.
    return ET.fromstring(payload)  # noqa: S314


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


def tests(total, passed, failed, skipped=0):
    if total is None:
        return "—"
    if failed == 0:
        return f"✅ {total:,}"
    return f"❌ {passed:,} / {total:,}"


def skips(sk):
    return "—" if sk is None else str(sk)


def cov(pct, threshold=None):
    if pct is None:
        return "—"
    if threshold is None:
        icon = "✅" if pct >= 90 else ("⚠️" if pct >= 70 else "❌")
        return f"{pct:.1f}% {icon}"
    icon = "✅" if pct >= threshold else ("⚠️" if pct >= 80 else "❌")
    return f"{pct:.1f}% / {threshold:.0f}% {icon}"


def tool(r, label):
    if not r or r in ("", "unknown"):
        return "—"
    icon = {"success": "✅", "failure": "❌", "cancelled": "🚫", "skipped": "⏭️"}.get(r, "⚠️")
    return f"{label} {icon}"


def bandit_fmt(high, medium):
    if high is None:
        return "—"
    if high == 0 and medium == 0:
        return "✅ No issues"
    return f"❌ {high} high, {medium} medium"


def npm_fmt(crit, high):
    if crit is None:
        return "—"
    if crit == 0 and high == 0:
        return "✅ No issues"
    return f"❌ {crit} critical, {high} high"


def eslint_fmt(step_r, esl_tuple):
    errors, warnings = esl_tuple
    warn_count = warnings or 0
    if errors is not None:
        if errors == 0 and warn_count == 0:
            return "eslint ✅"
        if errors == 0:
            return f"eslint ⚠️ ({warn_count} warnings)"
        return f"eslint ❌ ({errors} errors, {warn_count} warnings)"
    return tool(step_r, "eslint")


def lint(*items):
    parts = [p for p in items if p != "—"]
    return " · ".join(parts) or "—"


def main() -> None:
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

    # ── Parse artifacts ──────────────────────────────────────────────────

    web_py_t = parse_junit("all-results/results-web-client-python/pytest.xml")
    web_js_t = parse_junit("all-results/results-web-client-js/vitest.xml")
    web_esl = parse_eslint("all-results/results-web-client-js/eslint.json")
    web_ban = parse_bandit("all-results/results-web-client-python/bandit.json")
    web_npm = parse_npm_audit("all-results/results-web-client-js/npm-audit.json")
    web_cov = parse_coverage("all-results/results-web-client-python/coverage.xml")
    web_js_cov = parse_coverage("all-results/results-web-client-js/coverage/cobertura-coverage.xml")

    con_py_t = parse_junit("all-results/results-console-client/pytest.xml")
    con_ban = parse_bandit("all-results/results-console-client/bandit.json")
    con_cov = parse_coverage("all-results/results-console-client/coverage.xml")

    nod_js_t = parse_junit("all-results/results-node-client/vitest.xml")
    nod_esl = parse_eslint("all-results/results-node-client/eslint.json")
    nod_npm = parse_npm_audit("all-results/results-node-client/npm-audit.json")

    cs_unit_t = parse_junit("all-results/results-csharp-unit/tests.xml")
    cs_cov = parse_coverage("all-results/results-csharp-unit/coverage/cobertura.xml")

    tc_py_t = parse_junit("all-results/results-test-client/pytest.xml")
    tc_ban = parse_bandit("all-results/results-test-client/bandit.json")
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
        ("Node Client — JavaScript", nod_cov, 95.0),
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
    n_total = len(all_jobs)

    if n_fail == 0:
        status_icon = "✅"
        status_msg = f"All {n_pass} / {n_total} jobs passed"
    else:
        status_icon = "❌"
        status_msg = f"{n_fail} / {n_total} jobs failed  ·  {n_pass} passed"

    suites = [web_py_t, web_js_t, con_py_t, nod_js_t, cs_unit_t, tc_py_t, ss_smoke]
    total_t = sum(s[0] for s in suites if s[0] is not None)
    total_f = sum(s[2] for s in suites if s[2] is not None)
    total_sk = sum(s[3] for s in suites if s[3] is not None)

    if total_t > 0:
        totals = f"{total_t:,} tests  ·  {total_f} failed  ·  {total_sk} skipped"
    else:
        totals = "no test data"

    run_link = f"[#{run_num}]({run_url})" if run_url else f"#{run_num}"
    sha_str = f"`{sha}`" if sha else "—"

    # ── Build report ──────────────────────────────────────────────────────

    out = [
        "## IJT OPC UA — CI",
        "",
        f"> {status_icon} **{status_msg}** &nbsp;·&nbsp; {totals}",
        (
            f"> **Branch:** `{branch}` &nbsp;·&nbsp; **Commit:** {sha_str} "
            f"&nbsp;·&nbsp; **Run:** {run_link}"
        ),
        "",
        "---",
        "",
        "### 🧪 Test Results",
        "",
        "| Component | Platform | Tests | Skipped | Coverage / Threshold |",
        "|:----------|:--------:|------:|--------:|:--------:|",
        (
            f"| Web Client — Python      | Ubuntu  | {tests(*web_py_t)} | "
            f"{skips(web_py_t[3])} | {cov(web_cov, 95)} |"
        ),
        (
            f"| Web Client — JavaScript  | Ubuntu  | {tests(*web_js_t)} | "
            f"{skips(web_js_t[3])} | {cov(web_js_cov, 95)} |"
        ),
        (
            f"| Console Client — Python  | Ubuntu  | {tests(*con_py_t)} | "
            f"{skips(con_py_t[3])} | {cov(con_cov, 95)} |"
        ),
        (
            f"| Node Client — JavaScript | Ubuntu  | {tests(*nod_js_t)} | "
            f"{skips(nod_js_t[3])} | {cov(nod_cov, 95)} |"
        ),
        (
            f"| C# Client — Unit (xUnit) | Windows | {tests(*cs_unit_t)} | "
            f"{skips(cs_unit_t[3])} | {cov(cs_cov, 95)} |"
        ),
        (
            f"| Test Client — Python (Unit) | Ubuntu | {tests(*tc_py_t)} | "
            f"{skips(tc_py_t[3])} | {cov(tc_cov, 95)} |"
        ),
        (
            f"| OPC UA Server — Smoke    | Windows | {tests(*ss_smoke)} | "
            f"{skips(ss_smoke[3])} | Not Applicable |"
        ),
        "",
        "---",
        "",
        "### 🛡️ Code Quality",
        "",
        "| Component | Lint | Type Check | Security | Dependencies |",
        "|:----------|:-----|:----------:|:--------:|:------------:|",
        (
            "| Web Client     | "
            f"{lint(tool(web_ruff, 'ruff'), eslint_fmt(web_eslint, web_esl))} | "
            f"{tool(web_mypy, 'mypy')} | {bandit_fmt(*web_ban)} | "
            f"{npm_fmt(*web_npm)} |"
        ),
        (
            f"| Console Client | {tool(con_ruff, 'ruff')} | {tool(con_mypy, 'mypy')} | "
            f"{bandit_fmt(*con_ban)} | Not Applicable |"
        ),
        (
            f"| Node Client    | {eslint_fmt(nod_eslint, nod_esl)} | Not Applicable | "
            f"Not Configured | {npm_fmt(*nod_npm)} |"
        ),
        (
            "| C# Client      | "
            f"{lint(tool(cs_build, 'build'), tool(cs_format, 'format'))} | "
            f"Not Applicable | {tool(cs_vuln, 'nuget')} | Not Applicable |"
        ),
        (
            f"| Test Client    | {tool(tc_ruff, 'ruff')} | {tool(tc_mypy, 'mypy')} | "
            f"{bandit_fmt(*tc_ban)} | Not Applicable |"
        ),
        "",
        "---",
        "",
        "### 🏗️ Infrastructure",
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
        (
            "> 📦 **Artifacts** — JUnit XML · Coverage XML · ESLint JSON · "
            "Bandit JSON &nbsp;·&nbsp; 📋 **Checks** tab — per-test drill-down"
        ),
        (
            "> Coverage key: ✅ meets declared threshold &nbsp;·&nbsp; ⚠️ below "
            "threshold but ≥ 80% &nbsp;·&nbsp; ❌ < 80% &nbsp;·&nbsp; thresholds "
            "come from `pyproject.toml`, `vitest.config.mjs`, and the C# coverage gate"
        ),
    ]

    # ── Inline skip details (collapsible) ─────────────────────────────

    skip_sections = []
    skip_sections += format_skip_section("Web Client — Python", web_py_skips, web_py_t[3])
    skip_sections += format_skip_section("Web Client — JavaScript", web_js_skips, web_js_t[3])
    skip_sections += format_skip_section("Console Client — Python", con_py_skips, con_py_t[3])
    skip_sections += format_skip_section("Node Client — JavaScript", nod_js_skips, nod_js_t[3])
    skip_sections += format_skip_section("C# Client — Unit", cs_unit_skips, cs_unit_t[3])
    skip_sections += format_skip_section("Test Client — Python", tc_py_skips, tc_py_t[3])
    skip_sections += format_skip_section("OPC UA Server — Smoke", ss_smoke_skips, ss_smoke[3])

    if skip_sections:
        out += ["", "---", "", "### ⏭️ Skip Details"]
        out += skip_sections

    # ── Skip budget check ─────────────────────────────────────────────────
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
    if budget_warnings:
        out += ["", "---", "", "### ⏭️ Skip Budget Exceeded", ""]
        out += budget_warnings

    if coverage_warnings:
        out += ["", "---", "", "### ⚠️ Coverage Threshold Warnings", ""]
        out += coverage_warnings

    if artifact_warnings:
        out += ["", "---", "", "### ⚠️ Artifact Warnings", ""]
        out += artifact_warnings

    with open(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/stdout"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("Summary written.")


if __name__ == "__main__":
    main()
