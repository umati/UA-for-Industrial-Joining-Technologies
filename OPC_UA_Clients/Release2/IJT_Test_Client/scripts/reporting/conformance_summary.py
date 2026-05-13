"""Conformance summary renderer for the IJT Test Client.

This module owns the Markdown rendering pipeline that produces the
`IJT Conformance Test Report` written by `make_conformance_summary.py`. It was
extracted from that script (then named `make_ci_summary.py`) in Phase 1 of the IJT CI / System
Tests reporting overhaul to keep the rendering logic separately
testable (`tests/unit/reporting/test_render_conformance_summary.py`).

The public entry point is `render_conformance_summary(...)`. Its
signature mirrors the original `_render(...)` so the surrounding CLI
shim in `make_conformance_summary.py` stays a one-line delegation. The output
of this function must remain byte-identical to the pre-extraction
output for the captured fixtures; do not introduce any wording or
ordering change here without updating the expected Markdown files
under `tests/unit/reporting/fixtures/expected/` in the same commit.
"""

from __future__ import annotations

import ast
import os
import platform
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    yaml = None  # type: ignore[assignment]

# scripts/reporting/conformance_summary.py is two directories deep inside
# IJT_Test_Client, so parents[2] points at the Test Client project root.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PROFILES_DIR = _PROJECT_ROOT / "profiles"
_CU_COMPLIANCE_KEYS = {"supported", "partial", "not_supported", "blocked", "action_needed", "untested"}
_FINDING_OUTCOMES = {"partial", "not_supported", "blocked", "action_needed"}
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Shared report logic lives in helpers/*.py.
# Markdown and Excel generators must use the same helpers to stay in sync.
from helpers.git_info import short_git_sha as _short_git_sha  # noqa: E402
from helpers.report_scoring import (
    ACTION_ITEM_LABEL_ORDER as _ACTION_ITEM_LABEL_ORDER,
)
from helpers.report_scoring import (
    ACTION_ITEM_LABELS as _ACTION_ITEM_LABELS,
)
from helpers.report_scoring import (
    CAPABILITY_NOTE_LABEL_ORDER as _CAPABILITY_NOTE_LABEL_ORDER,
)
from helpers.report_scoring import (
    CAPABILITY_NOTE_LABELS as _CAPABILITY_NOTE_LABELS,
)
from helpers.report_scoring import (
    CAPABILITY_SUPPORT_ICONS as _CAPABILITY_SUPPORT_ICONS,
)
from helpers.report_scoring import (
    NO_COMPLIANCE_LABEL as _NO_COMPLIANCE_LABEL,
)
from helpers.report_scoring import (  # noqa: E402,I001
    OUTCOME_RANK as _OUTCOME_RANK,
)
from helpers.report_scoring import (
    RUN_RESULT_ICONS as _RUN_RESULT_ICONS,
)
from helpers.report_scoring import (
    STATUS_ORDER as _STATUS_ORDER,
)
from helpers.report_scoring import (
    TEST_RESULT_ICONS as _TEST_RESULT_ICONS,
)
from helpers.report_scoring import (
    conformance_score as _conformance_score,
)
from helpers.report_scoring import (
    delta_symbol as _delta_symbol,
)
from helpers.report_scoring import (
    format_delta_summary as _format_delta_summary,
)
from helpers.report_scoring import (
    format_kpi_strip as _format_kpi_strip,
)
from helpers.report_scoring import (
    format_outcome_label as _format_outcome_label,
)
from helpers.report_scoring import (
    format_pct as _fmt_pct,
)
from helpers.report_scoring import (
    format_status_counts as _format_status_counts,
)
from helpers.report_scoring import (
    format_status_label as _format_status_label,
)
from helpers.report_scoring import (
    outcome_label as _plain_outcome_label,
)
from helpers.report_scoring import (
    pct_value as _pct_value,
)
from helpers.report_scoring import (
    status_count_key as _status_count_key,
)
from helpers.report_scoring import (
    status_for as _status_for,
)

# ── Markdown rendering ────────────────────────────────────────────────────────


def _md_cell(text: str) -> str:
    """Escape pipe characters so text is safe inside a markdown table cell."""
    return re.sub(r"\|", "\\|", text)


def _status_badge(passed: int, failed: int, errors: int) -> str:
    if failed + errors > 0:
        return f"{_RUN_RESULT_ICONS['failed']} **FAILED**"
    return f"{_RUN_RESULT_ICONS['passed']} **PASSED**"


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
            "description": str(data.get("description") or "").strip(),
            "spec_section": str(data.get("spec_section") or ""),
            "kind": str(data.get("kind") or "facet"),
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


def _pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "n/a"
    return f"{(numerator * 100 / denominator):.1f}%"


def _server_profile_pct(server_profile_cus: int | str, total: int) -> str:
    if not isinstance(server_profile_cus, int):
        return "n/a"
    return _pct(server_profile_cus, total)


def _server_supported_cu_keys(cu_keys: list[str], supported: set[str] | None) -> list[str]:
    if supported is None:
        return []
    return [cu for cu in cu_keys if cu in supported]


def _supported_cus_validated_count(cu_keys: list[str], by_cu: dict[str, Any], supported: set[str] | None) -> int | str:
    if supported is None:
        return "n/a"
    counts = _count_outcomes(_server_supported_cu_keys(cu_keys, supported), by_cu)
    return counts["supported"] + counts["partial"]


def _supported_cus_validated_pct(cu_keys: list[str], by_cu: dict[str, Any], supported: set[str] | None) -> str:
    server_supported_count = _server_profile_cu_count(cu_keys, supported)
    validated_count = _supported_cus_validated_count(cu_keys, by_cu, supported)
    if not isinstance(server_supported_count, int) or not isinstance(validated_count, int):
        return "n/a"
    return _pct(validated_count, server_supported_count)


def _supported_cus_validated_pct_value(
    cu_keys: list[str], by_cu: dict[str, Any], supported: set[str] | None
) -> float | None:
    server_supported_count = _server_profile_cu_count(cu_keys, supported)
    validated_count = _supported_cus_validated_count(cu_keys, by_cu, supported)
    if not isinstance(server_supported_count, int) or not isinstance(validated_count, int):
        return None
    return _pct_value(validated_count, server_supported_count)


def _run_logs_url() -> str:
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return "n/a"


def _package_version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "not installed"


def _baseline_age(baseline: dict[str, Any]) -> str:
    raw = str(baseline.get("run_ts") or "")
    try:
        previous = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return "previous run"
    delta = datetime.now(timezone.utc) - previous
    days = delta.days
    if days > 0:
        return f"{days} day{'s' if days != 1 else ''} ago"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    minutes = max(1, delta.seconds // 60)
    return f"{minutes} minute{'s' if minutes != 1 else ''} ago"


def _outcomes_cell(counts: Counter[str]) -> str:
    """Return compact Markdown for the coverage summary tables."""
    return (
        f"{counts['supported']} {_plain_outcome_label('supported')}<br>"
        f"{counts['partial']} {_CAPABILITY_NOTE_LABEL_ORDER[1]}<br>"
        f"{counts['not_supported']} {_CAPABILITY_NOTE_LABEL_ORDER[0]}<br>"
        f"{counts['blocked']} {_ACTION_ITEM_LABEL_ORDER[1]}<br>"
        f"{counts['action_needed']} {_ACTION_ITEM_LABEL_ORDER[0]}"
    )


def _in_server_profile(cu_key: str, supported: set[str] | None) -> str:
    if supported is None:
        return "n/a"
    return "Yes" if cu_key in supported else "No"


def _cu_compliance_key(data: dict[str, Any]) -> str:
    explicit = str(data.get("compliance") or "")
    if explicit in _CU_COMPLIANCE_KEYS:
        return explicit

    passed = int(data.get("passed", 0) or 0)
    failed = int(data.get("failed", 0) or 0) + int(data.get("error", 0) or 0)
    not_supported = int(data.get("not_supported", 0) or 0)
    blocked = int(data.get("blocked", 0) or 0)
    accepted_policy = int(data.get("accepted_policy", 0) or 0)
    environment = int(data.get("environment", 0) or 0)
    skipped = int(data.get("skipped", 0) or 0)
    untested = int(data.get("untested", 0) or 0)
    test_count = int(data.get("test_count", 0) or 0)

    if failed:
        return "action_needed"
    if passed and (not_supported or blocked or skipped or untested):
        return "partial"
    if blocked:
        return "blocked"
    if not_supported:
        return "not_supported"
    if passed:
        return "supported"
    if accepted_policy or environment:
        return "blocked"
    if untested or test_count == 0:
        return "untested"
    return "unknown"


def _compliance_label(counts: Counter[str], total: int) -> str:
    if counts["action_needed"]:
        return _format_outcome_label("action_needed")
    if counts["blocked"]:
        return _format_outcome_label("blocked")
    if counts["partial"] or counts["not_supported"]:
        return _format_outcome_label("partial")
    if total and counts["supported"] == total:
        return _format_outcome_label("supported")
    if counts["supported"]:
        return _format_outcome_label("partial")
    return _format_status_label(_NO_COMPLIANCE_LABEL)


def _cu_display_name(cu_key: str) -> str:
    return f"IJT {_title_from_key(cu_key)}"


def _cu_facet_map(facets: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    rollups: list[dict[str, Any]] = []
    for facet in facets.values():
        if str(facet.get("kind") or "") == "rollup":
            rollups.append(facet)
            continue
        for cu_key in facet.get("conformance_units", []):
            mapping.setdefault(str(cu_key), []).append(str(facet.get("display_name") or _title_from_key(str(cu_key))))
    for facet in rollups:
        for cu_key in facet.get("conformance_units", []):
            if str(cu_key) not in mapping:
                mapping.setdefault(str(cu_key), []).append(
                    str(facet.get("display_name") or _title_from_key(str(cu_key)))
                )
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
    return _format_outcome_label(outcome)


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
        ("blocked", _plain_outcome_label("blocked")),
        ("not_supported", _plain_outcome_label("not_supported")),
        ("accepted_policy", "Accepted Policy"),
        ("environment", "Environment"),
        ("skipped", "Skipped"),
        ("xfailed", "Expected Failure"),
        ("untested", _plain_outcome_label("untested")),
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


def _build_report_context(cu_payload: dict[str, Any] | None, baseline: dict[str, Any] | None) -> dict[str, Any] | None:
    if not cu_payload:
        return None

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
    facet_map = _cu_facet_map(facets)
    tests_by_cu = _cu_test_index(cu_payload)
    active_label = str(active.get("name") or _title_from_key(active_profile)) if active else "No active profile found"
    active_cus = _profile_cus(active, facets) if active else []
    active_cus_set = set(active_cus)
    active_counts = _count_outcomes(active_cus, by_cu) if active else Counter()
    server_supported_count = _server_profile_cu_count(active_cus, supported)
    score = _conformance_score(active_counts, server_supported_count, len(active_cus))
    validation_health_value = _supported_cus_validated_pct_value(active_cus, by_cu, supported)
    spec_coverage_value = (
        _pct_value(server_supported_count, len(active_cus)) if isinstance(server_supported_count, int) else None
    )

    findings: list[dict[str, Any]] = []
    cu_outcomes: dict[str, str] = {}
    for cu_key in all_cu_keys:
        data_raw = by_cu.get(cu_key)
        data = data_raw if isinstance(data_raw, dict) else {}
        outcome = _cu_compliance_key(data)
        cu_outcomes[cu_key] = outcome
        if outcome not in _FINDING_OUTCOMES:
            continue
        failed = int(data.get("failed", 0) or 0) + int(data.get("error", 0) or 0)
        status, status_icon = _status_for(cu_key, outcome, active_cus_set)
        findings.append(
            {
                "cu_key": cu_key,
                "cu": _cu_display_name(cu_key),
                "facets": ", ".join(facet_map.get(cu_key, [])),
                "server_supported": _in_server_profile(cu_key, supported),
                "outcome": outcome,
                "result": _outcome_label(outcome),
                "reason": _cu_note_summary(cu_key, tests_by_cu),
                "tests": int(data.get("test_count", 0) or 0),
                "passed": int(data.get("passed", 0) or 0),
                "not_supported": int(data.get("not_supported", 0) or 0),
                "blocked": int(data.get("blocked", 0) or 0),
                "failed": failed,
                "workbook_cases": int(data.get("workbook_case_count", 0) or 0),
                "status": status,
                "status_icon": status_icon,
                "delta": _delta_symbol(cu_key, outcome, baseline),
            }
        )
    findings.sort(key=lambda item: (_STATUS_ORDER.get(str(item["status"]), 99), str(item["cu_key"])))
    findings_count = Counter(_status_count_key(str(item["status"])) for item in findings)

    return {
        "facets": facets,
        "profiles": profiles,
        "by_cu": by_cu,
        "supported": supported,
        "active_profile": active_profile,
        "active": active,
        "server_name": server_name,
        "all_cu_keys": all_cu_keys,
        "facet_map": facet_map,
        "active_label": active_label,
        "active_cus": active_cus,
        "active_counts": active_counts,
        "server_supported_count": server_supported_count,
        "score": score,
        "validation_health_value": validation_health_value,
        "spec_coverage_value": spec_coverage_value,
        "findings": findings,
        "findings_count": findings_count,
        "cu_outcomes": cu_outcomes,
    }


def _baseline_payload(context: dict[str, Any], run_ts_iso: str) -> dict[str, Any]:
    return {
        "run_ts": run_ts_iso,
        "git_sha": _short_git_sha(_PROJECT_ROOT),
        "score": context["score"],
        "validation_health_pct": context["validation_health_value"],
        "spec_coverage_pct": context["spec_coverage_value"],
        "findings_count": dict(context["findings_count"]),
        "cu_outcomes": context["cu_outcomes"],
    }


def _delta_summary(context: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, int]:
    if not baseline:
        return {"new": 0, "resolved": 0, "regressed": 0}
    raw_previous_outcomes = baseline.get("cu_outcomes")
    previous_outcomes: dict[str, Any] = raw_previous_outcomes if isinstance(raw_previous_outcomes, dict) else {}
    current_outcomes: dict[str, str] = context["cu_outcomes"]
    new = resolved = regressed = 0
    for cu_key, current in current_outcomes.items():
        previous = str(previous_outcomes.get(cu_key) or "")
        if current in _FINDING_OUTCOMES and previous not in _FINDING_OUTCOMES:
            new += 1
        if previous in _FINDING_OUTCOMES and current not in _FINDING_OUTCOMES:
            resolved += 1
        current_rank = _OUTCOME_RANK.get(current)
        previous_rank = _OUTCOME_RANK.get(previous)
        if current_rank is not None and previous_rank is not None and current_rank < previous_rank:
            regressed += 1
    return {"new": new, "resolved": resolved, "regressed": regressed}


def _render_delta_block(context: dict[str, Any], baseline: dict[str, Any] | None) -> list[str]:
    lines: list[str] = []
    if not baseline:
        lines.append("### Δ Since Last Run")
        lines.append("")
        lines.append("_No baseline yet — this run becomes the baseline._")
        lines.append("")
        return lines
    previous_sha = str(baseline.get("git_sha") or "unknown")
    lines.append(f"### Δ Since Last Run (commit `{previous_sha}`, {_baseline_age(baseline)})")
    lines.append("")
    delta = _delta_summary(context, baseline)
    previous_score = baseline.get("score", "n/a")
    previous_validation = baseline.get("validation_health_pct", "n/a")
    previous_spec = baseline.get("spec_coverage_pct", "n/a")
    current_validation = context["validation_health_value"]
    current_spec = context["spec_coverage_value"]
    lines.append(f"- Score **{previous_score} → {context['score']}**")
    lines.append(f"- Validation Health {_fmt_pct(previous_validation)} → {_fmt_pct(current_validation)}")
    lines.append(f"- Spec Coverage {_fmt_pct(previous_spec)} → {_fmt_pct(current_spec)}")
    lines.append(f"- Review Items: {_format_delta_summary(delta)}")
    lines.append("")
    return lines


def _render_supports_block(context: dict[str, Any], limit: int = 12) -> list[str]:
    facets: dict[str, dict[str, Any]] = context["facets"]
    by_cu: dict[str, Any] = context["by_cu"]
    supported: set[str] | None = context["supported"]
    rows: list[tuple[int, str]] = []
    for facet in facets.values():
        if str(facet.get("kind") or "") == "rollup":
            continue
        cu_keys = list(facet.get("conformance_units", []))
        counts = _count_outcomes(cu_keys, by_cu)
        server_supported_count = _server_profile_cu_count(cu_keys, supported)
        if counts["action_needed"] or counts["blocked"] or server_supported_count == 0:
            icon, rank, label = _CAPABILITY_SUPPORT_ICONS["not_supported"], 0, "not supported by this server"
        elif counts["partial"] or counts["not_supported"] or server_supported_count != len(cu_keys):
            icon, rank, label = _CAPABILITY_SUPPORT_ICONS["partial"], 1, "partially supported"
        else:
            icon, rank, label = _CAPABILITY_SUPPORT_ICONS["supported"], 2, "supported"
        name = str(facet.get("display_name") or "Facet").removeprefix("IJT ").removesuffix(" Server Facet")
        description = str(facet.get("description") or "").strip().replace("\n", " ")
        rows.append((rank, f"{icon} **{_md_cell(name)}** — {label}. {_md_cell(description)}"))
    rows.sort(key=lambda item: (item[0], item[1]))
    lines = ["## What This Server Supports", ""]
    lines.append("_Auto-generated from facet outcomes. Full detail is in Facet Coverage._")
    lines.append("")
    for _rank, row in rows[:limit]:
        lines.append(f"- {row}")
    if len(rows) > limit:
        lines.append(f"- … {len(rows) - limit} more capability areas in Facet Coverage")
    lines.append("")
    return lines


def _append_review_table(
    lines: list[str],
    findings: list[dict[str, Any]],
    limit: int,
    more_target: str,
) -> None:
    lines.append("| Status | CU | Result | Primary Reason | Δ |")
    lines.append("|---|---|---|---|---|")
    for finding in findings[:limit]:
        status = f"{finding['status_icon']} {finding['status']}"
        lines.append(
            f"| {status} | `{_md_cell(str(finding['cu_key']))}` | {finding['result']} | "
            f"{_md_cell(str(finding['reason']) or 'See CU details')} | {finding['delta']} |"
        )
    if len(findings) > limit:
        lines.append(f"| … | … | … | {len(findings) - limit} more items in {more_target} |  |")


def _render_review_sections(context: dict[str, Any], limit: int = 10) -> list[str]:
    findings: list[dict[str, Any]] = context["findings"]
    counts: Counter[str] = context["findings_count"]
    action_items = [item for item in findings if str(item["status"]) in _ACTION_ITEM_LABELS]
    capability_notes = [item for item in findings if str(item["status"]) in _CAPABILITY_NOTE_LABELS]

    lines = ["## Action Items", ""]
    lines.append(f"**{_format_status_counts(_ACTION_ITEM_LABEL_ORDER, counts)}**")
    lines.append("")
    if not action_items:
        lines.append("_No action items — server validation passed cleanly._")
    else:
        _append_review_table(lines, action_items, limit, "Conformance Status")
    lines.append("")

    lines.append("## Capability Notes")
    lines.append("")
    lines.append("<details open>")
    lines.append("<summary><b>Show capability notes</b></summary>")
    lines.append("")
    lines.append(f"**{_format_status_counts(_CAPABILITY_NOTE_LABEL_ORDER, counts)}**")
    lines.append("")
    if not capability_notes:
        lines.append("_Server supports every CU in its server capability profile, no notes._")
    else:
        _append_review_table(lines, capability_notes, limit, "Conformance Status")
    lines.append("")
    lines.append("</details>")
    lines.append("")
    return lines


def _render_test_environment() -> list[str]:
    lines = ["| Item | Value |", "|---|---|"]
    lines.append(f"| Test Client commit | `{_short_git_sha(_PROJECT_ROOT)}` |")
    lines.append(f"| Python | {platform.python_version()} |")
    lines.append(f"| asyncua | {_package_version('asyncua')} |")
    lines.append(f"| Host OS | {_md_cell(platform.platform())} |")
    lines.append("| Repro command | `python run_all_tests.py` |")
    lines.append(f"| Run logs | {_md_cell(_run_logs_url())} |")
    return lines


def _render_profile_facet_summary(
    cu_payload: dict[str, Any] | None, baseline: dict[str, Any] | None
) -> tuple[list[str], dict[str, Any] | None]:
    context = _build_report_context(cu_payload, baseline)
    if context is None:
        return [], None

    facets: dict[str, dict[str, Any]] = context["facets"]
    by_cu: dict[str, Any] = context["by_cu"]
    supported: set[str] | None = context["supported"]
    active_profile = str(context["active_profile"])
    active = context["active"]
    all_cu_keys: list[str] = context["all_cu_keys"]
    facet_map: dict[str, list[str]] = context["facet_map"]

    lines: list[str] = []
    lines.extend(_render_delta_block(context, baseline))
    lines.extend(_render_supports_block(context))
    lines.extend(_render_review_sections(context))

    lines.append("<details>")
    lines.append("<summary><b>Coverage Overview</b></summary>")
    lines.append("")
    lines.append(
        "_These rows separate the active server capability profile from reference IJT facet rollups and the complete CU set._"
    )
    lines.append("")
    lines.append(
        "| Coverage View | Purpose | Facets | CUs | Server Supported CUs | Server Support % | Supported CUs Validated % | Outcomes | Result |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---|---|")
    view_rows: list[tuple[str, str, int, list[str]]] = []
    if active:
        view_rows.append(
            (
                str(active.get("name", _title_from_key(active_profile))),
                "Server capability profile",
                len(active.get("facets", [])),
                _profile_cus(active, facets),
            )
        )

    for facet_key in (
        "basic_joining_system_server_facet",
        "general_joining_system_server_facet",
        "joining_system_selectable_features_server_facet",
    ):
        facet = facets.get(facet_key)
        if not facet:
            continue
        view_rows.append(
            (
                str(facet.get("display_name") or _title_from_key(facet_key)),
                "Reference IJT facet",
                1,
                list(facet.get("conformance_units", [])),
            )
        )

    if active_profile != "full_conformance":
        view_rows.append(("Full IJT Base CU Set", "Reference full CU set", len(facets), all_cu_keys))

    for view_name, profile_role, facet_count, cu_keys in view_rows:
        counts = _count_outcomes(cu_keys, by_cu)
        server_profile_cus = _server_profile_cu_count(cu_keys, supported)
        lines.append(
            f"| {_md_cell(view_name)} | {profile_role} | "
            f"{facet_count} | {len(cu_keys)} | {server_profile_cus} | "
            f"{_server_profile_pct(server_profile_cus, len(cu_keys))} | "
            f"{_supported_cus_validated_pct(cu_keys, by_cu, supported)} | {_outcomes_cell(counts)} | "
            f"{_compliance_label(counts, len(cu_keys))} |"
        )
    lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("<details>")
    lines.append("<summary><b>Facet Coverage</b></summary>")
    lines.append("")
    lines.append(
        "| Facet | Type | CUs | Server Supported CUs | Server Support % | Supported CUs Validated % | Outcomes | Result |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---|---|")
    for facet in facets.values():
        cu_keys = list(facet.get("conformance_units", []))
        counts = _count_outcomes(cu_keys, by_cu)
        facet_kind = "Rollup" if str(facet.get("kind") or "") == "rollup" else "Facet"
        server_profile_cus = _server_profile_cu_count(cu_keys, supported)
        lines.append(
            f"| {_md_cell(str(facet.get('display_name', 'Facet')))} | {facet_kind} "
            f"| {len(cu_keys)} | {server_profile_cus} | {_server_profile_pct(server_profile_cus, len(cu_keys))} | "
            f"{_supported_cus_validated_pct(cu_keys, by_cu, supported)} | {_outcomes_cell(counts)} | "
            f"{_compliance_label(counts, len(cu_keys))} |"
        )
    lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("<details>")
    lines.append("<summary><b>Conformance Status</b></summary>")
    lines.append("")
    lines.append(
        f"_Support-level detail for CUs that need explanation or follow-up: {_plain_outcome_label('partial')}, "
        f"{_CAPABILITY_NOTE_LABEL_ORDER[0]}, {_ACTION_ITEM_LABEL_ORDER[1]}, or "
        f"{_ACTION_ITEM_LABEL_ORDER[0]}. Raw skip buckets below are diagnostics._"
    )
    lines.append("")
    lines.append(
        f"| Status | CU | Facet(s) | Server Supported | Result | Primary Reason | Tests | Passed | "
        f"{_plain_outcome_label('not_supported')} | {_plain_outcome_label('blocked')} | Failed/Error | Δ |"
    )
    lines.append("|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|")
    findings: list[dict[str, Any]] = context["findings"]
    if findings:
        for finding in findings:
            status = f"{finding['status_icon']} {finding['status']}"
            lines.append(
                f"| {status} | {_md_cell(str(finding['cu']))} | {_md_cell(str(finding['facets']))} | "
                f"{finding['server_supported']} | {finding['result']} | "
                f"{_md_cell(str(finding['reason']) or 'See CU details')} | "
                f"{finding['tests']} | {finding['passed']} | {finding['not_supported']} | "
                f"{finding['blocked']} | {finding['failed']} | {finding['delta']} |"
            )
    else:
        lines.append("|  | No conformance status items |  |  |  |  | 0 | 0 | 0 | 0 | 0 |  |")
    lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("<details>")
    lines.append("<summary><b>Full CU Coverage</b></summary>")
    lines.append("")
    lines.append(
        f"| CU | Facet(s) | Server Supported | Result | Tests | Passed | {_plain_outcome_label('not_supported')} | "
        f"{_plain_outcome_label('blocked')} | Failed/Error | Workbook Cases | Δ |"
    )
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|---|")
    for cu_key in all_cu_keys:
        data_raw = by_cu.get(cu_key)
        data = data_raw if isinstance(data_raw, dict) else {}
        failed = int(data.get("failed", 0) or 0) + int(data.get("error", 0) or 0)
        in_server_profile = _in_server_profile(cu_key, supported)
        outcome = _cu_compliance_key(data)
        lines.append(
            f"| {_md_cell(_cu_display_name(cu_key))} | {_md_cell(', '.join(facet_map.get(cu_key, [])))} | "
            f"{in_server_profile} | {_outcome_label(outcome)} | "
            f"{int(data.get('test_count', 0) or 0)} | {int(data.get('passed', 0) or 0)} | "
            f"{int(data.get('not_supported', 0) or 0)} | {int(data.get('blocked', 0) or 0)} | {failed} | "
            f"{int(data.get('workbook_case_count', 0) or 0)} | {_delta_symbol(cu_key, outcome, baseline)} |"
        )
    lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("<details>")
    lines.append("<summary><b>Test Environment</b></summary>")
    lines.append("")
    lines.extend(_render_test_environment())
    lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("<details>")
    lines.append("<summary><b>How to Read This Report</b></summary>")
    lines.append("")
    lines.append("- **Server capability profile** is the active profile selected by the server capability YAML.")
    lines.append(
        "- **Reference IJT facet** and **Reference full CU set** rows are comparison views only; "
        "they are not extra pass/fail requirements."
    )
    lines.append("- **Server Supported CUs** means the CUs listed as supported in the server capability file.")
    lines.append("- **Server Support %** is the share of CUs in that row that the server says it supports.")
    lines.append(
        "- **Supported CUs Validated %** is the share of server-supported CUs that this run validated as "
        f"{_plain_outcome_label('supported')} or {_plain_outcome_label('partial')}."
    )
    lines.append(
        "- **Score** is a 0–100 composite of `0.7 × Validation Health + 0.3 × Spec Coverage`, "
        f"capped at 50 if any **{_ACTION_ITEM_LABEL_ORDER[0]}** item exists and capped at 75 if any "
        f"**{_ACTION_ITEM_LABEL_ORDER[1]}** item exists."
    )
    lines.append(
        f"- **Status** is computed from the result: {_ACTION_ITEM_LABEL_ORDER[0]} = failure or error, "
        f"{_ACTION_ITEM_LABEL_ORDER[1]} = missing runtime precondition, "
        f"{_CAPABILITY_NOTE_LABEL_ORDER[0]} = server-supported CU not supported, "
        f"{_CAPABILITY_NOTE_LABEL_ORDER[1]} = supported with notes or outside server support."
    )
    lines.append("- **Δ** compares this run with `test-results/report-baseline.json` when that file exists.")
    lines.append(f"- Failures and errors are reported as **{_ACTION_ITEM_LABEL_ORDER[0]}**.")
    lines.append("- Raw skip reasons are listed later as diagnostics and may overlap with conformance status items.")
    lines.append("")
    lines.append("</details>")
    lines.append("")
    return lines, context


def render_conformance_summary(
    data: dict,
    server_url: str,
    run_ts: str,
    cu_payload: dict[str, Any] | None,
    baseline: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Return the IJT Conformance Test Report Markdown plus the report context.

    Inputs are the same as the original `_render(...)` in `make_conformance_summary.py`:
    parsed JUnit XML data, the OPC UA server URL string, the formatted
    `run_ts` to print on the report, an optional `cu_payload` from
    `cu-compliance-report.json`, and an optional `baseline` dict loaded from
    `report-baseline.json`. The caller is responsible for any baseline write
    side effect; this function never touches disk.
    """
    p = data["passed"]
    f = data["failed"] + data["errors"]
    s = data["skipped"]
    x = data["xfailed"]
    total = data["total"]
    mins, secs = divmod(int(data["duration_s"]), 60)
    profile_lines, context = _render_profile_facet_summary(cu_payload, baseline)

    lines: list[str] = []
    lines.append("# IJT Conformance Test Report")
    lines.append("")
    result_badge = _status_badge(p, f, 0)
    score_text = f"{context['score']} / 100" if context else "n/a"
    server_name = str(context["server_name"]) if context else "Server under test"
    active_label = str(context["active_label"]) if context else "n/a"
    lines.append(f"{result_badge} · **Score: {score_text}**")
    lines.append("")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| **Server** | {_md_cell(server_name)} (`{server_url}`) |")
    lines.append(f"| **Capability profile** | {_md_cell(active_label)} |")
    lines.append(f"| **Run** | {run_ts} · Duration {mins}m {secs}s |")
    lines.append(f"| **Build** | commit `{_short_git_sha(_PROJECT_ROOT)}` · run logs: {_md_cell(_run_logs_url())} |")
    lines.append("")

    if context:
        supported = context["server_supported_count"]
        total_active = len(context["active_cus"])
        validated = _supported_cus_validated_count(context["active_cus"], context["by_cu"], context["supported"])
        findings_count: Counter[str] = context["findings_count"]
        lines.append("## At a Glance")
        lines.append("")
        lines.append(f"| Spec Coverage | {_TEST_RESULT_ICONS['passed']} Validation Health | CU Status |")
        lines.append("|:---:|:---:|:---:|")
        lines.append(
            f"| **{_fmt_pct(context['spec_coverage_value'])}** | "
            f"**{_fmt_pct(context['validation_health_value'])}** | "
            f"**{_format_kpi_strip(findings_count)}** |"
        )
        lines.append(
            f"| {supported} / {total_active} CUs server-supported | "
            f"{validated} / {supported} server-supported CUs validated | Action Items and Capability Notes below |"
        )
        lines.append("")

    lines.extend(profile_lines)

    lines.append("<details>")
    lines.append("<summary><b>Test result counts</b></summary>")
    lines.append("")
    lines.append("| Status | Count | % |")
    lines.append("|--------|------:|--:|")
    lines.append(f"| {_TEST_RESULT_ICONS['passed']} Passed | **{p}** | {p * 100 // total if total else 0}% |")
    lines.append(f"| {_TEST_RESULT_ICONS['failed']} Failed | **{f}** | {f * 100 // total if total else 0}% |")
    lines.append(f"| ⏭️ Skipped | **{s}** | {s * 100 // total if total else 0}% |")
    lines.append(f"| 🟡 Expected Fail | **{x}** | {x * 100 // total if total else 0}% |")
    lines.append(f"| **Total** | **{total}** | 100% |")
    lines.append("")
    lines.append("</details>")
    lines.append("")

    # ── Failures detail ──
    if data["failures"]:
        lines.append("<details open>")
        lines.append("<summary><b>Failures</b></summary>")
        lines.append(f"## {_TEST_RESULT_ICONS['failed']} Failures")
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
        lines.append("</details>")
        lines.append("")

    # ── Skip reason buckets ──
    if data["skip_reasons"]:
        lines.append("<details>")
        lines.append("<summary><b>Raw Skip Diagnostics</b></summary>")
        lines.append("")
        lines.append(
            "Diagnostic skip buckets from pytest. These may overlap with conformance status items and do not "
            "by themselves reduce CU compliance when the CU also has passing support coverage."
        )
        lines.append("")
        lines.append("| Reason | Count |")
        lines.append("|--------|------:|")
        for reason, count in data["skip_reasons"].items():
            lines.append(f"| {_md_cell(reason)} | {count} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # ── Xfail reasons ──
    if data["xfail_reasons"]:
        lines.append("<details>")
        lines.append("<summary><b>Expected Failures</b></summary>")
        lines.append("")
        lines.append("These tests are marked as expected failures — known server gaps, not bugs.")
        lines.append("")
        lines.append("| Reason | Count |")
        lines.append("|--------|------:|")
        for reason, count in data["xfail_reasons"].items():
            lines.append(f"| {_md_cell(reason)} | {count} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("---")
    lines.append("*Full detail: download `report.xlsx` or `report.html` from the run artifacts.*")
    return "\n".join(lines), context
