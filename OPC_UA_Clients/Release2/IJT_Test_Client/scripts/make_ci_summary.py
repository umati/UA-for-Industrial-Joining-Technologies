#!/usr/bin/env python3
"""
make_ci_summary.py — Write a GitHub Actions Step Summary from JUnit XML test results.

Reads:  test-results/pytest.xml   (or --xml=FILE)
        test-results/cu-compliance-report.json, when present
Writes: $GITHUB_STEP_SUMMARY      (GitHub markdown step summary, if env var is set)
        test-results/summary.md   (always, as a local copy)

Called automatically by the CI workflow after the test run. Safe to run locally too.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import xml.etree.ElementTree as ET  # nosec B405
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Bandit B405/B314 suppressions are limited to trusted JUnit XML from pytest.

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    yaml = None  # type: ignore[assignment]

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_PROFILES_DIR = _PROJECT_ROOT / "profiles"
_DEFAULT_CU_JSON = _PROJECT_ROOT / "test-results" / "cu-compliance-report.json"

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


# ── Markdown rendering ────────────────────────────────────────────────────────


def _md_cell(text: str) -> str:
    """Escape pipe characters so text is safe inside a markdown table cell."""
    return re.sub(r"\|", "\\|", text)


def _status_badge(passed: int, failed: int, errors: int) -> str:
    if failed + errors > 0:
        return "🔴 **FAILED**"
    return "🟢 **PASSED**"


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None or not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return loaded if isinstance(loaded, dict) else {}


def _title_from_key(key: str) -> str:
    acronyms = {"cu": "CU", "id": "ID", "io": "IO", "ijt": "IJT"}
    return " ".join(acronyms.get(token, token.capitalize()) for token in key.split("_"))


def _load_facets() -> dict[str, dict[str, Any]]:
    raw = _load_yaml(_PROFILES_DIR / "facets.yaml")
    facets: dict[str, dict[str, Any]] = {}
    for key, data in (raw.get("facets") or {}).items():
        if not isinstance(data, dict):
            continue
        facets[str(key)] = {
            "display_name": str(data.get("display_name") or _title_from_key(str(key))),
            "conformance_units": [str(cu) for cu in data.get("conformance_units", [])],
        }
    return facets


def _load_profiles() -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    for path in sorted(_PROFILES_DIR.glob("*.yaml")):
        if path.name == "facets.yaml":
            continue
        raw = _load_yaml(path)
        profile_raw = raw.get("profile")
        profile: dict[str, Any] = profile_raw if isinstance(profile_raw, dict) else {}
        profiles[path.stem] = {
            "name": str(profile.get("name") or _title_from_key(path.stem)),
            "facets": [str(facet) for facet in profile.get("facets", [])],
        }
    return profiles


def _load_capabilities() -> dict[str, Any]:
    caps_env = os.environ.get("OPCUA_CAPABILITIES_FILE")
    caps_path = Path(caps_env) if caps_env else _PROJECT_ROOT / "server_capabilities.yaml"
    return _load_yaml(caps_path)


def _active_profile_key(capabilities: dict[str, Any]) -> str:
    return str(capabilities.get("active_profile") or "")


def _profile_cus(profile: dict[str, Any], facets: dict[str, dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for facet_key in profile.get("facets", []):
        for cu_key in facets.get(str(facet_key), {}).get("conformance_units", []):
            if cu_key not in seen:
                seen.add(cu_key)
                ordered.append(cu_key)
    return ordered


def _count_outcomes(cu_keys: list[str], by_cu: dict[str, Any]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for cu_key in cu_keys:
        data_raw = by_cu.get(cu_key)
        data: dict[str, Any] = data_raw if isinstance(data_raw, dict) else {}
        counts[_cu_compliance_key(data)] += 1
    return counts


def _supported_set(cu_payload: dict[str, Any]) -> set[str] | None:
    supported = cu_payload.get("supported_cus")
    if supported is None:
        return None
    return {str(cu) for cu in supported}


def _server_profile_cu_count(cu_keys: list[str], supported: set[str] | None) -> int | str:
    if supported is None:
        return "n/a"
    return len([cu for cu in cu_keys if cu in supported])


def _in_server_profile(cu_key: str, supported: set[str] | None) -> str:
    if supported is None:
        return "n/a"
    return "Yes" if cu_key in supported else "No"


def _cu_compliance_key(data: dict[str, Any]) -> str:
    passed = int(data.get("passed", 0) or 0)
    failed = int(data.get("failed", 0) or 0) + int(data.get("error", 0) or 0)
    not_supported = int(data.get("not_supported", 0) or 0)
    blocked = int(data.get("blocked", 0) or 0)
    skipped = int(data.get("skipped", 0) or 0)
    untested = int(data.get("untested", 0) or 0)
    test_count = int(data.get("test_count", 0) or 0)

    if failed:
        return "action_needed"
    if passed and (not_supported or blocked or skipped or untested):
        return "partial"
    if not_supported:
        return "not_supported"
    if blocked:
        return "blocked"
    if passed:
        return "supported"
    if untested or test_count == 0:
        return "untested"
    return "unknown"


def _compliance_label(counts: Counter[str], total: int) -> str:
    if counts["action_needed"]:
        return "🔴 Action needed"
    if counts["blocked"]:
        return "🟠 Blocked"
    if counts["partial"] or counts["not_supported"]:
        return "🟡 Supported with notes"
    if total and counts["supported"] == total:
        return "🟢 Supported"
    if counts["supported"]:
        return "🟡 Supported with notes"
    return "⚪ No compliance result"


def _cu_display_name(cu_key: str) -> str:
    return f"IJT {_title_from_key(cu_key)}"


def _cu_facet_map(facets: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for facet in facets.values():
        for cu_key in facet.get("conformance_units", []):
            mapping.setdefault(str(cu_key), []).append(str(facet.get("display_name") or _title_from_key(str(cu_key))))
    return mapping


def _ordered_cu_keys(by_cu: dict[str, Any], facets: dict[str, dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for facet in facets.values():
        for cu_key in facet.get("conformance_units", []):
            key = str(cu_key)
            if key in by_cu and key not in seen:
                seen.add(key)
                ordered.append(key)
    ordered.extend(sorted(str(key) for key in by_cu if str(key) not in seen))
    return ordered


def _outcome_label(outcome: str) -> str:
    labels = {
        "supported": "🟢 Supported",
        "partial": "🟡 Supported with notes",
        "not_supported": "🟡 Not Supported",
        "blocked": "🟠 Blocked",
        "action_needed": "🔴 Action needed",
        "untested": "⚪ Untested",
    }
    return labels.get(outcome, outcome.replace("_", " ").title() or "Unknown")


def _skip_reason_bucket(message: str) -> str:
    msg = re.sub(r"\s+", " ", message.strip())
    if not msg:
        return "no reason"
    if msg.startswith("("):
        try:
            longrepr = ast.literal_eval(msg)
        except (SyntaxError, ValueError):
            longrepr = None
        if isinstance(longrepr, tuple) and longrepr and isinstance(longrepr[-1], str):
            msg = re.sub(r"\s+", " ", longrepr[-1].strip())
    msg = re.sub(r"^Skipped:\s*", "", msg, flags=re.IGNORECASE)
    msg = re.split(r"\s+-\s+CU:\s*", msg, maxsplit=1)[0].strip()
    msg = re.split(r"\.\s+To enable:\s*", msg, maxsplit=1)[0].strip()
    msg = re.split(r"\s+Config file:\s*", msg, maxsplit=1)[0].strip()

    not_supported = " NOT SUPPORTED"
    if not_supported in msg:
        end = msg.find(not_supported) + len(not_supported)
        return msg[:end].strip()

    if len(msg) > 140:
        return f"{msg[:137].rstrip()}..."
    return msg


def _cu_test_index(cu_payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    indexed: dict[str, list[dict[str, Any]]] = {}
    tests = cu_payload.get("tests")
    if not isinstance(tests, list):
        return indexed
    for test in tests:
        if not isinstance(test, dict):
            continue
        for cu_key in test.get("cus", []):
            indexed.setdefault(str(cu_key), []).append(test)
    return indexed


def _cu_note_summary(cu_key: str, tests_by_cu: dict[str, list[dict[str, Any]]]) -> str:
    tests = tests_by_cu.get(cu_key, [])
    priority = [
        ("failed", "Failed"),
        ("error", "Error"),
        ("blocked", "Blocked"),
        ("not_supported", "Not Supported"),
        ("skipped", "Skipped"),
        ("xfailed", "Expected Failure"),
        ("untested", "Untested"),
    ]
    notes: list[str] = []
    for outcome, label in priority:
        matching = [test for test in tests if str(test.get("outcome") or "") == outcome]
        if not matching:
            continue
        reason = next(
            (_skip_reason_bucket(str(test.get("reason") or "")) for test in matching if test.get("reason")), ""
        )
        if reason and reason != "no reason":
            notes.append(f"{label}: {reason}")
        else:
            notes.append(f"{label}: {len(matching)} test(s)")
    if not notes:
        return ""
    if len(notes) > 2:
        return "; ".join(notes[:2]) + f"; {len(notes) - 2} more"
    return "; ".join(notes)


def _render_profile_facet_summary(cu_payload: dict[str, Any] | None) -> list[str]:
    if not cu_payload:
        return []

    facets = _load_facets()
    profiles = _load_profiles()
    by_cu = cu_payload.get("by_cu", {}) if isinstance(cu_payload.get("by_cu"), dict) else {}
    supported = _supported_set(cu_payload)
    capabilities = _load_capabilities()
    active_profile = _active_profile_key(capabilities)
    active = profiles.get(active_profile)
    server_raw = capabilities.get("server")
    server: dict[str, Any] = server_raw if isinstance(server_raw, dict) else {}
    server_name = str(server.get("name") or "Server under test")
    all_cu_keys = _ordered_cu_keys(by_cu, facets)
    all_counts = _count_outcomes(all_cu_keys, by_cu)
    facet_map = _cu_facet_map(facets)
    tests_by_cu = _cu_test_index(cu_payload)

    lines: list[str] = []
    lines.append("## IJT CS Profile / Facet Coverage")
    lines.append("")
    lines.append(
        f"**Server profile source:** {server_name}  |  "
        f"**CU compliance:** {all_counts['supported']} supported, {all_counts['partial']} supported with notes, "
        f"{all_counts['not_supported']} not supported, {all_counts['blocked']} blocked, "
        f"{all_counts['action_needed']} action needed"
    )
    lines.append("")
    lines.append(
        "_Legend: Supported with notes means at least one test path passed and the remaining "
        "non-passing rows are accepted skips, Not Supported methods/CUs from the server profile, or environment/precondition notes; "
        "failures and errors are reported separately as Action needed._"
    )
    lines.append(
        "_Server Profile CUs and In Server Profile come from the active server capability file; "
        "Compliance comes from this test run._"
    )
    lines.append(
        "_How to read this section: start with the Server Profile row. Reference Only profile rows are comparison views "
        "against other IJT CS profiles; they are not additional pass/fail requirements for this server._"
    )
    lines.append("")
    if active:
        active_cus = _profile_cus(active, facets)
        active_counts = _count_outcomes(active_cus, by_cu)
        server_profile_cus = _server_profile_cu_count(active_cus, supported)
        lines.append(
            f"**Server profile:** {active['name']}  |  "
            f"**Server profile support:** {server_profile_cus}/{len(active_cus)} CUs  |  "
            f"**Compliance:** {_compliance_label(active_counts, len(active_cus))}"
        )
    else:
        lines.append("**Server profile:** no server profile found in available capabilities file")
    lines.append("")

    lines.append("### Profiles")
    lines.append("")
    lines.append(
        "| Profile | Profile Role | Facets | CUs | Server Profile CUs | Supported | With Notes | Not Supported | Blocked | Action Needed | Compliance |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for key, profile in profiles.items():
        cu_keys = _profile_cus(profile, facets)
        counts = _count_outcomes(cu_keys, by_cu)
        profile_role = "Server Profile" if key == active_profile else "Reference Only"
        lines.append(
            f"| {_md_cell(str(profile.get('name', _title_from_key(key))))} | {profile_role} | "
            f"{len(profile.get('facets', []))} | {len(cu_keys)} | {_server_profile_cu_count(cu_keys, supported)} | "
            f"{counts['supported']} | {counts['partial']} | {counts['not_supported']} | "
            f"{counts['blocked']} | {counts['action_needed']} | "
            f"{_compliance_label(counts, len(cu_keys))} |"
        )
    lines.append("")

    lines.append("### Facets")
    lines.append("")
    lines.append(
        "| Facet | CUs | Server Profile CUs | Supported | With Notes | Not Supported | Blocked | Action Needed | Compliance |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for facet in facets.values():
        cu_keys = list(facet.get("conformance_units", []))
        counts = _count_outcomes(cu_keys, by_cu)
        lines.append(
            f"| {_md_cell(str(facet.get('display_name', 'Facet')))} "
            f"| {len(cu_keys)} | {_server_profile_cu_count(cu_keys, supported)} | {counts['supported']} | "
            f"{counts['partial']} | {counts['not_supported']} | {counts['blocked']} | "
            f"{counts['action_needed']} | "
            f"{_compliance_label(counts, len(cu_keys))} |"
        )
    lines.append("")

    attention_cus: list[tuple[str, dict[str, Any]]] = []
    for cu_key in all_cu_keys:
        data_raw = by_cu.get(cu_key)
        data = data_raw if isinstance(data_raw, dict) else {}
        if _cu_compliance_key(data) in {"partial", "not_supported", "blocked", "action_needed"}:
            attention_cus.append((cu_key, data))
    if attention_cus:
        lines.append("### CUs With Notes / Not Supported")
        lines.append("")
        lines.append(
            "| CU | Facet(s) | In Server Profile | Compliance | Why Listed | Tests | Passed | Not Supported | Blocked | Failed/Error |"
        )
        lines.append("|---|---|---|---|---|---:|---:|---:|---:|---:|")
        for cu_key, data in attention_cus[:40]:
            failed = int(data.get("failed", 0) or 0) + int(data.get("error", 0) or 0)
            in_server_profile = _in_server_profile(cu_key, supported)
            lines.append(
                f"| {_md_cell(_cu_display_name(cu_key))} | {_md_cell(', '.join(facet_map.get(cu_key, [])))} | "
                f"{in_server_profile} | {_outcome_label(_cu_compliance_key(data))} | "
                f"{_md_cell(_cu_note_summary(cu_key, tests_by_cu))} | "
                f"{int(data.get('test_count', 0) or 0)} | {int(data.get('passed', 0) or 0)} | "
                f"{int(data.get('not_supported', 0) or 0)} | {int(data.get('blocked', 0) or 0)} | {failed} |"
            )
        if len(attention_cus) > 40:
            lines.append(f"| ... | ... | ... | ... | ... | ... | ... | ... | ... | {len(attention_cus) - 40} more |")
        lines.append("")

    lines.append("<details>")
    lines.append("<summary>Full CU coverage table</summary>")
    lines.append("")
    lines.append(
        "| CU | Facet(s) | In Server Profile | Compliance | Tests | Passed | Not Supported | Blocked | Failed/Error | Workbook Cases |"
    )
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|")
    for cu_key in all_cu_keys:
        data_raw = by_cu.get(cu_key)
        data = data_raw if isinstance(data_raw, dict) else {}
        failed = int(data.get("failed", 0) or 0) + int(data.get("error", 0) or 0)
        in_server_profile = _in_server_profile(cu_key, supported)
        lines.append(
            f"| {_md_cell(_cu_display_name(cu_key))} | {_md_cell(', '.join(facet_map.get(cu_key, [])))} | "
            f"{in_server_profile} | {_outcome_label(_cu_compliance_key(data))} | "
            f"{int(data.get('test_count', 0) or 0)} | {int(data.get('passed', 0) or 0)} | "
            f"{int(data.get('not_supported', 0) or 0)} | {int(data.get('blocked', 0) or 0)} | {failed} | "
            f"{int(data.get('workbook_case_count', 0) or 0)} |"
        )
    lines.append("")
    lines.append("</details>")
    lines.append("")
    return lines


def _render(data: dict, server_url: str, run_ts: str, cu_payload: dict[str, Any] | None) -> str:
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

    lines.extend(_render_profile_facet_summary(cu_payload))

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
    p.add_argument("--cu-json", default=str(_DEFAULT_CU_JSON))
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
    cu_payload = _load_json(Path(args.cu_json))

    md = _render(data, server_url, run_ts, cu_payload)

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
