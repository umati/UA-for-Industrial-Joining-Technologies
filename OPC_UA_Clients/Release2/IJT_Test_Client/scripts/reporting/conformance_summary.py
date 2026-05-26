"""Conformance summary renderer for the IJT Test Client.

This module owns the Markdown rendering pipeline that produces the
`IJT Conformance Test Report` written by `make_conformance_summary.py`. The
rendering logic lives here so it can be tested separately by
`tests/unit/reporting/test_render_conformance_summary.py`.

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
from dataclasses import dataclass
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
_NOT_APPLICABLE = "Not Applicable"
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Shared report logic lives in helpers/*.py.
# Markdown and Excel generators must use the same helpers to stay in sync.
from helpers.cu_registry import cu_display_name  # noqa: E402
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
    CAPABILITY_SUPPORT_ICONS as _CAPABILITY_SUPPORT_ICONS,
)
from helpers.report_scoring import (
    NO_COMPLIANCE_LABEL as _NO_COMPLIANCE_LABEL,
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
    action_items_context as _action_items_context,
)
from helpers.report_scoring import (
    conformance_score as _conformance_score,
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
    informational_notes_context as _informational_notes_context,
)
from helpers.report_scoring import (
    is_healthy as _is_healthy,
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


def _cell_width(s: str) -> int:
    """Approximate display width. VS-16 = 0; known emoji ranges = 2; else 1."""
    w = 0
    for ch in s:
        if ch == "\ufe0f":
            continue
        cp = ord(ch)
        if cp >= 0x1F300:
            w += 2
        elif 0x2300 <= cp <= 0x23FF:
            w += 2
        elif 0x2600 <= cp <= 0x27BF:
            w += 2
        elif cp == 0x2139:
            w += 2
        else:
            w += 1
    return w


def _pad_cell(cell: str, width: int, align: str) -> str:
    pad = width - _cell_width(cell)
    if pad <= 0:
        return cell
    if align == "right":
        return " " * pad + cell
    if align == "center":
        left = pad // 2
        right = pad - left
        return " " * left + cell + " " * right
    return cell + " " * pad


def pad_table_rows(headers: list[str], rows: list[list[str]], aligns: list[str]) -> list[str]:
    """Render padded Markdown table lines (header + separator + data rows)."""
    all_data = [headers] + rows
    # Min width 3 so the GFM separator always contains >=1 hyphen between
    # optional colons; otherwise center-align on a 2-cell icon column would
    # emit "::" which is invalid GFM.
    widths = [max(3, max(_cell_width(r[i]) for r in all_data)) for i in range(len(headers))]
    out = []
    out.append("| " + " | ".join(_pad_cell(h, widths[i], aligns[i]) for i, h in enumerate(headers)) + " |")
    sep_parts = []
    for i, a in enumerate(aligns):
        dashes = "-" * widths[i]
        if a == "right":
            sep_parts.append(dashes[:-1] + ":")
        elif a == "center":
            sep_parts.append(":" + dashes[1:-1] + ":")
        else:
            sep_parts.append(":" + dashes[1:])
    out.append("| " + " | ".join(sep_parts) + " |")
    for r in rows:
        out.append("| " + " | ".join(_pad_cell(r[i], widths[i], aligns[i]) for i in range(len(headers))) + " |")
    return out


def _status_badge(passed: int, failed: int, errors: int) -> str:
    if failed + errors > 0:
        return f"{_RUN_RESULT_ICONS['failed']} **Failed**"
    return f"{_RUN_RESULT_ICONS['passed']} **Passed**"


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
        return _NOT_APPLICABLE
    return len([cu for cu in cu_keys if cu in supported])


def _pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return _NOT_APPLICABLE
    return f"{(numerator * 100 / denominator):.1f}%"


def _server_profile_pct(server_profile_cus: int | str, total: int) -> str:
    if not isinstance(server_profile_cus, int):
        return _NOT_APPLICABLE
    return _pct(server_profile_cus, total)


def _server_supported_cu_keys(cu_keys: list[str], supported: set[str] | None) -> list[str]:
    if supported is None:
        return []
    return [cu for cu in cu_keys if cu in supported]


def _supported_cus_validated_count(cu_keys: list[str], by_cu: dict[str, Any], supported: set[str] | None) -> int | str:
    if supported is None:
        return _NOT_APPLICABLE
    counts = _count_outcomes(_server_supported_cu_keys(cu_keys, supported), by_cu)
    return counts["supported"] + counts["partial"]


def _supported_cus_validated_pct(cu_keys: list[str], by_cu: dict[str, Any], supported: set[str] | None) -> str:
    server_supported_count = _server_profile_cu_count(cu_keys, supported)
    validated_count = _supported_cus_validated_count(cu_keys, by_cu, supported)
    if not isinstance(server_supported_count, int) or not isinstance(validated_count, int):
        return _NOT_APPLICABLE
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
    return _NOT_APPLICABLE


def _package_version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "not installed"


@dataclass(frozen=True)
class ReportEnvironment:
    """Frozen execution-environment metadata for the conformance summary.

    Bundles every runtime-derived value the renderer would otherwise read
    from ``platform``, ``importlib.metadata``, the local git checkout, the
    ``GITHUB_*`` environment variables, or the system wall clock. Production
    callers should construct this from live state via :meth:`from_runtime` (which is also
    the implicit default when ``report_environment=None`` is passed to
    :func:`render_conformance_summary`). Byte-identity tests and the
    capture helper pass a frozen instance so the rendered Markdown stays
    deterministic regardless of which Python patch version, host OS,
    asyncua release, git SHA, or GitHub Actions run hosts the test — the
    project promises Python ``3.14+`` is supported, so the test contract
    must not depend on the exact patch version of any of those inputs.
    """

    git_sha: str
    python_version: str
    asyncua_version: str
    host_os: str
    run_logs_url: str
    now_utc: datetime
    glossary_url: str = "OPC_UA_Clients/Release2/IJT_Test_Client/docs/REPORT_GLOSSARY.md"
    repro_command: str = "python run_all_tests.py"

    @classmethod
    def from_runtime(cls) -> ReportEnvironment:
        """Build a :class:`ReportEnvironment` from the current process state."""
        return cls(
            git_sha=_short_git_sha(_PROJECT_ROOT),
            python_version=platform.python_version(),
            asyncua_version=_package_version("asyncua"),
            host_os=platform.platform(),
            run_logs_url=_run_logs_url(),
            now_utc=_utc_now(),
            glossary_url=_glossary_url(),
        )


def _utc_now() -> datetime:
    """Return the current UTC time as an aware ``datetime``.

    Wrapped in a helper so the renderer has exactly one entry point that
    reads the wall clock; this lets ``ReportEnvironment.from_runtime`` and
    the leak-prevention regression test agree on the same single seam.
    """
    return datetime.now(timezone.utc)


def _plural_label(count: int, singular: str, plural: str | None = None) -> str:
    """Return a count plus a correctly pluralized public label."""
    label = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {label}"


def _outcomes_cell(counts: Counter[str]) -> str:
    """Return compact Markdown for the coverage summary tables."""
    rows = [
        (_plain_outcome_label("supported"), counts["supported"]),
        (_CAPABILITY_NOTE_LABEL_ORDER[1], counts["partial"]),
        (_CAPABILITY_NOTE_LABEL_ORDER[0], counts["not_supported"]),
        (_ACTION_ITEM_LABEL_ORDER[1], counts["blocked"]),
        (_ACTION_ITEM_LABEL_ORDER[0], counts["action_needed"]),
    ]
    rendered = [f"{_format_status_label(label)}: {count}" for label, count in rows if count]
    return "<br>".join(rendered) if rendered else _NOT_APPLICABLE


def _in_server_profile(cu_key: str, supported: set[str] | None) -> str:
    if supported is None:
        return _NOT_APPLICABLE
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
    if total and counts["not_supported"] == total:
        return _format_outcome_label("not_supported")
    if counts["partial"] or counts["not_supported"]:
        return _format_outcome_label("partial")
    if total and counts["supported"] == total:
        return _format_outcome_label("supported")
    if counts["supported"]:
        return _format_outcome_label("partial")
    return _format_status_label(_NO_COMPLIANCE_LABEL)


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

    if msg.casefold().startswith("not supported:"):
        detail = msg.split(":", 1)[1].strip()
        return detail or "Not Supported"

    not_supported = " NOT SUPPORTED"
    if not_supported in msg:
        end = msg.find(not_supported) + len(not_supported)
        return msg[:end].strip()

    if len(msg) > 140:
        return f"{msg[:137].rstrip()}..."
    return msg


def _skip_reason_display(reason: str) -> str:
    """Render skip buckets with a leading category without changing raw labels."""
    display_reason = reason.strip()
    if display_reason.casefold().startswith("not supported:"):
        detail = display_reason.split(":", 1)[1].strip()
        detail = re.sub(r"\s+NOT SUPPORTED$", "", detail)
        return f"Not Supported: {detail}"

    not_supported = " NOT SUPPORTED"
    if not_supported in display_reason:
        detail = display_reason[: display_reason.find(not_supported)].strip()
        return f"Not Supported: {detail}"

    return display_reason


def _primary_reason_note(outcome: str, label: str, reason: str) -> str:
    """Render a concise end-user reason without repeating the row status."""
    display_reason = reason.strip()
    if outcome == "not_supported":
        display_reason = re.sub(
            r"^Not Supported:\s*",
            "",
            display_reason,
            flags=re.IGNORECASE,
        )
        display_reason = re.sub(r"\s+NOT SUPPORTED$", "", display_reason)
        return display_reason
    if display_reason.casefold().startswith(f"{label}:".casefold()):
        return display_reason
    return f"{label}: {display_reason}"


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
            notes.append(_primary_reason_note(outcome, label, reason))
        else:
            notes.append(f"{label}: {len(matching)} test(s)")
    if not notes:
        return ""
    if len(notes) > 2:
        return "; ".join(notes[:2]) + f"; {len(notes) - 2} more"
    return "; ".join(notes)


def _build_report_context(cu_payload: dict[str, Any] | None) -> dict[str, Any] | None:
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
                "cu": cu_display_name(cu_key),
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
            }
        )
    findings.sort(key=lambda item: (_STATUS_ORDER.get(str(item["status"]), 99), str(item["cu"])))
    findings_count = Counter(_status_count_key(str(item["status"])) for item in findings)
    is_healthy = _is_healthy(
        context_present=True,
        server_supported_count=server_supported_count,
        active_cus_len=len(active_cus),
        failed_count=int(findings_count.get("action_needed", 0) or 0),
        blocked_count=int(findings_count.get("blocked", 0) or 0),
    )

    return {
        "facets": facets,
        "profiles": profiles,
        "by_cu": by_cu,
        "supported": supported,
        "tests_by_cu": tests_by_cu,
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
        "is_healthy": is_healthy,
        "cu_outcomes": cu_outcomes,
    }


def _baseline_payload(
    context: dict[str, Any],
    run_ts_iso: str,
    env: ReportEnvironment,
) -> dict[str, Any]:
    return {
        "run_ts": run_ts_iso,
        "git_sha": env.git_sha,
        "score": context["score"],
        "validation_health_pct": context["validation_health_value"],
        "spec_coverage_pct": context["spec_coverage_value"],
        "findings_count": dict(context["findings_count"]),
        "cu_outcomes": context["cu_outcomes"],
    }


def _render_supports_block(context: dict[str, Any], limit: int = 12) -> list[str]:
    facets: dict[str, dict[str, Any]] = context["facets"]
    by_cu: dict[str, Any] = context["by_cu"]
    supported: set[str] | None = context["supported"]
    rows: list[tuple[int, str, str, str, str]] = []
    for facet in facets.values():
        if str(facet.get("kind") or "") == "rollup":
            continue
        cu_keys = list(facet.get("conformance_units", []))
        counts = _count_outcomes(cu_keys, by_cu)
        server_supported_count = _server_profile_cu_count(cu_keys, supported)
        if counts["action_needed"] or counts["blocked"] or server_supported_count == 0:
            icon, rank, label = _CAPABILITY_SUPPORT_ICONS["not_supported"], 0, "Not Supported"
        elif counts["partial"] or counts["not_supported"] or server_supported_count != len(cu_keys):
            icon, rank, label = _CAPABILITY_SUPPORT_ICONS["partial"], 1, "Partially Supported"
        else:
            icon, rank, label = _CAPABILITY_SUPPORT_ICONS["supported"], 2, "Supported"
        name = str(facet.get("display_name") or "Facet").removeprefix("IJT ").removesuffix(" Server Facet")
        description = str(facet.get("description") or "").strip().replace("\n", " ")
        rows.append((rank, name, icon, label, description))
    rows.sort(key=lambda item: (item[0], item[1]))
    summary_counts = Counter(label for _rank, _name, _icon, label, _description in rows)
    support_chip = (
        f"{summary_counts['Supported']} Supported · "
        f"{summary_counts['Partially Supported']} Partial · "
        f"{summary_counts['Not Supported']} Not Supported"
    )
    lines = [f"## 🧩 IJT Facet Support — {support_chip}", ""]
    lines.append("> 🚦 Support: ✅ Supported · ⚠️ Partially Supported · ⚪ Not Supported")
    lines.append("")
    lines.append(
        "_Auto-generated from the server profile and conformance outcomes. Full detail is in IJT Facet Breakdown._"
    )
    lines.append("")
    for _rank, name, icon, label, description in rows[:limit]:
        lines.append(f"- {icon} **{_md_cell(name)}** — {label}. {_md_cell(description)}")
    if len(rows) > limit:
        lines.append("")
        lines.append(
            "_Showing the most relevant capability areas here. Full capability detail is in IJT Facet Breakdown. "
            "Capability area counts: "
            f"{summary_counts['Supported']} Supported · "
            f"{summary_counts['Partially Supported']} Partially Supported · "
            f"{summary_counts['Not Supported']} Not Supported._"
        )
    lines.append("")
    return lines


def _append_review_table(
    lines: list[str],
    findings: list[dict[str, Any]],
    limit: int,
    more_target: str,
) -> None:
    lines.append("| Status | CU | Reason |")
    lines.append("|---|---|---|")
    for finding in findings[:limit]:
        status = _format_status_label(str(finding["status"]))
        cells = [
            status,
            _md_cell(str(finding["cu"])),
            _md_cell(str(finding["reason"]) or "See CU details"),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    if len(findings) > limit:
        remaining = len(findings) - limit
        cells = [
            "Additional rows",
            f"See full {more_target} section below",
            f"{remaining} additional items are listed in full in {more_target}",
        ]
        lines.append("| " + " | ".join(cells) + " |")


def _render_review_sections(context: dict[str, Any], limit: int = 10) -> list[str]:
    findings: list[dict[str, Any]] = context["findings"]
    counts: Counter[str] = context["findings_count"]
    action_items = [item for item in findings if str(item["status"]) in _ACTION_ITEM_LABELS]
    ai_counts = Counter(str(item["status"]) for item in action_items)
    action_chip = f"{ai_counts['Failed']} failed · {ai_counts['Blocked']} blocked"

    lines: list[str] = []
    if not bool(context.get("is_healthy")):
        lines = [f"## 📌 Conformance Action Items — {action_chip}", ""]
        lines.append(f"**{_format_status_counts(_ACTION_ITEM_LABEL_ORDER, counts)}**")
        lines.append("")
        if action_items:
            _append_review_table(lines, action_items, limit, "CUs Needing Review")
        else:
            lines.append(
                "_No failed or blocked CUs. Review the profile and server support inputs because this run "
                "does not have a healthy active CU scope._"
            )
        lines.append("")
    return lines


def _render_test_environment(*, env: ReportEnvironment) -> list[str]:
    lines = ["| Item | Value |", "|---|---|"]
    lines.append(f"| Test Client commit | `{env.git_sha}` |")
    lines.append(f"| Python | {env.python_version} |")
    lines.append(f"| asyncua | {env.asyncua_version} |")
    lines.append(f"| Host OS | {_md_cell(env.host_os)} |")
    lines.append(f"| Repro command | `{env.repro_command}` |")
    lines.append(f"| Run logs | {_md_cell(env.run_logs_url)} |")
    return lines


def _is_conformance_skip_reason(reason: str) -> bool:
    """Return True when a skip bucket is already represented in CUs Needing Review.

    Filters skip buckets whose display string starts with the literal
    ``"Not Supported:"`` prefix (case-sensitive, per spec). Those rows are
    already accounted for in the CUs Needing Review table, so listing them
    again as raw skip diagnostics is duplicate noise.
    """
    return _skip_reason_display(reason).lstrip().startswith("Not Supported:")


def _render_diagnostics(data: dict[str, Any]) -> list[str]:
    """Render the Skip & Expected-Failure Diagnostics bundle.

    Only emitted when ``skip_reasons`` or ``xfail_reasons`` is truthy. The
    ``Not Supported:`` skip-reason prefix is filtered out of the Skip
    Diagnostics sub-table because those rows are already represented in
    CUs Needing Review. The raw input is left
    untouched so Excel and other consumers still see the full bucket list.
    """
    skip_reasons = data.get("skip_reasons") or {}
    xfail_reasons = data.get("xfail_reasons") or {}
    if not skip_reasons and not xfail_reasons:
        return []

    diagnostic_skips = {
        reason: count for reason, count in skip_reasons.items() if not _is_conformance_skip_reason(reason)
    }

    lines: list[str] = ["<details>", "<summary><b>Skip &amp; Expected-Failure Diagnostics</b></summary>", ""]
    lines.append(
        '_Diagnostic skip buckets and expected failures. The "Not Supported:" reasons are intentionally '
        'filtered here — server-unsupported CUs are tracked separately in "CUs Needing Review"._'
    )
    lines.append("")
    lines.append("#### Diagnostic Skips")
    lines.append("")
    if diagnostic_skips:
        lines.append("| Reason | Count |")
        lines.append("|--------|------:|")
        for reason, count in diagnostic_skips.items():
            lines.append(f"| {_md_cell(_skip_reason_display(reason))} | {count} |")
    else:
        lines.append("_No diagnostic skips on this run._")
    lines.append("")
    if xfail_reasons:
        lines.append("#### Expected Failures")
        lines.append("")
        lines.append("| Reason | Count |")
        lines.append("|--------|------:|")
        for reason, count in xfail_reasons.items():
            lines.append(f"| {_md_cell(reason)} | {count} |")
        lines.append("")
    lines.append("</details>")
    lines.append("")
    return lines


def _render_cus_needing_review(context: dict[str, Any]) -> list[str]:
    """Render the action-first CU review table."""
    findings: list[dict[str, Any]] = context["findings"]
    all_cu_keys: list[str] = context["all_cu_keys"]
    lines = [
        '<a id="system-cus-needing-review"></a>',
        "",
        f"## 📋 CUs Needing Review — {_plural_label(len(findings), 'row')}",
        "",
        f"_Review rows only. Full {len(all_cu_keys)}-CU detail remains in `report.xlsx` and `report.html`._",
        "",
    ]
    if findings:
        lines.append(
            f"| Status | CU | Server Supported | Reason | Tests | Passed | "
            f"{_plain_outcome_label('not_supported')} | {_plain_outcome_label('blocked')} | Failures |"
        )
        lines.append("|---|---|---|---|---:|---:|---:|---:|---:|")
        for finding in findings:
            cells = [
                _format_status_label(str(finding["status"])),
                _md_cell(str(finding["cu"])),
                str(finding["server_supported"]),
                _md_cell(str(finding["reason"]) or "See test details"),
                str(finding["tests"]),
                str(finding["passed"]),
                str(finding["not_supported"]),
                str(finding["blocked"]),
                str(finding["failed"]),
            ]
            lines.append("| " + " | ".join(cells) + " |")
    else:
        lines.append("_No CUs need review._")
    lines.append("")
    return lines


def _render_profile_facet_summary(
    cu_payload: dict[str, Any] | None,
    *,
    env: ReportEnvironment | None = None,
) -> tuple[list[str], dict[str, Any] | None]:
    resolved_env = env if env is not None else ReportEnvironment.from_runtime()
    context = _build_report_context(cu_payload)
    if context is None:
        return [], None

    facets: dict[str, dict[str, Any]] = context["facets"]
    by_cu: dict[str, Any] = context["by_cu"]
    supported: set[str] | None = context["supported"]

    lines: list[str] = []
    lines.extend(_render_review_sections(context))
    lines.extend(_render_cus_needing_review(context))
    lines.extend(_render_supports_block(context))

    lines.append("## 📐 IJT Facet Breakdown")
    lines.append("")
    lines.append("<details>")
    lines.append(f"<summary><b>{_plural_label(len(facets), 'facet row')}</b></summary>")
    lines.append("")
    lines.append(
        "| Facet | Type | CUs | Server Supported CUs | Server Support % | Supported CUs Validated % | Outcome Counts | Outcome Rollup |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---|---|")
    for facet in facets.values():
        cu_keys = list(facet.get("conformance_units", []))
        counts = _count_outcomes(cu_keys, by_cu)
        facet_kind = "Facet Group" if str(facet.get("kind") or "") == "rollup" else "Facet"
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
    lines.append("<summary><b>Test Client Environment</b></summary>")
    lines.append("")
    lines.extend(_render_test_environment(env=resolved_env))
    lines.append("")
    lines.append("</details>")
    lines.append("")

    context["report_environment"] = resolved_env
    return lines, context


def _glossary_url() -> str:
    """Return an absolute URL to REPORT_GLOSSARY.md when running in GitHub Actions,
    falling back to a repo-relative path for local renders.

    GitHub Actions step summaries resolve relative links against the run page
    (https://github.com/<owner>/<repo>/actions/runs/<id>) — not the repository
    tree — so a repo-relative link 404s when clicked from the run page. When
    GITHUB_SERVER_URL, GITHUB_REPOSITORY, and GITHUB_SHA are all set, build an
    absolute blob URL pinned to the run's commit. Otherwise return the
    repo-relative path that works in local IDE previews and on github.com when
    the file is viewed directly.
    """
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    sha = os.environ.get("GITHUB_SHA")
    relpath = "OPC_UA_Clients/Release2/IJT_Test_Client/docs/REPORT_GLOSSARY.md"
    if server and repo and sha:
        return f"{server}/{repo}/blob/{sha}/{relpath}"
    return relpath


def render_conformance_summary(
    data: dict,
    server_url: str,
    run_ts: str,
    cu_payload: dict[str, Any] | None,
    baseline: dict[str, Any] | None = None,
    *,
    report_environment: ReportEnvironment | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Return the IJT Conformance Test Report Markdown plus the report context.

    Inputs are the same as the original `_render(...)` in `make_conformance_summary.py`:
    parsed JUnit XML data, the OPC UA server URL string, the formatted
    `run_ts` to print on the report, and an optional `cu_payload` from
    `cu-compliance-report.json`.

    ``baseline`` is accepted for backwards compatibility but no longer
    affects the rendered output; trend information was
    removed in favour of the current-run KPI strip. The `report-baseline.json`
    artifact continues to be written by `_baseline_payload` for any
    external trend consumers.

    Wire-shape contract: any change to the banner line, the KPI strip,
    or top-level section headings emitted here must be mirrored in the
    aggregator snapshot fixtures:
        tests/reporting/fixtures/integration/root/all-results/results-testclient/summary.md
        tests/reporting/fixtures/expected/integration_summary.md

    The keyword-only ``report_environment`` parameter bundles every
    runtime-derived value the report would otherwise read from
    ``platform``, ``importlib.metadata``, the local git checkout, or the
    ``GITHUB_*`` environment variables (see :class:`ReportEnvironment`).
    Production callers leave it as ``None`` and the renderer builds it from
    live state via :meth:`ReportEnvironment.from_runtime`. Byte-identity
    tests and the capture helper pass a frozen instance so the rendered
    Markdown stays deterministic regardless of which Python patch version,
    host OS, asyncua release, git SHA, or GitHub Actions run hosts the
    test — a property the project's ``Python 3.14+`` support promise
    requires.
    """
    del baseline  # accepted for backwards compatibility; no longer used.
    resolved_env = report_environment if report_environment is not None else ReportEnvironment.from_runtime()
    p = data["passed"]
    f = data["failed"] + data["errors"]
    mins, secs = divmod(int(data["duration_s"]), 60)
    profile_lines, context = _render_profile_facet_summary(
        cu_payload,
        env=resolved_env,
    )

    lines: list[str] = []
    lines.append("# IJT Conformance Test Report")
    lines.append("")
    result_badge = _status_badge(p, f, 0)
    server_name = str(context["server_name"]) if context else "Server under test"
    active_label = str(context["active_label"]) if context else _NOT_APPLICABLE
    supported: Any = 0
    total_active: int = 0
    validated: Any = 0
    findings_count: Counter[str] = Counter()
    if context:
        supported = context["server_supported_count"]
        total_active = len(context["active_cus"])
        validated = _supported_cus_validated_count(context["active_cus"], context["by_cu"], context["supported"])
        findings_count = context["findings_count"]
        action_total = int(findings_count.get("action_needed", 0) or 0) + int(findings_count.get("blocked", 0) or 0)
        action_label = "action item" if action_total == 1 else "action items"
        lines.append(
            f"{result_badge} · **{action_total} {action_label}** · "
            f"**Validation {_fmt_pct(context['validation_health_value'])} ({validated}/{supported})** · "
            f"**Server support {_fmt_pct(context['spec_coverage_value'])} ({supported}/{total_active})**"
        )
    else:
        lines.append(f"{result_badge} · **Conformance profile unavailable**")
    lines.append("")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| **Server** | {_md_cell(server_name)} (`{server_url}`) |")
    lines.append(f"| **Capability profile** | {_md_cell(active_label)} |")
    lines.append(f"| **Run** | {run_ts} · Duration {mins}m {secs}s |")
    lines.append(f"| **Build** | commit `{resolved_env.git_sha}` · run logs: {_md_cell(resolved_env.run_logs_url)} |")
    lines.append("")

    if context:
        lines.append("## 📊 Conformance Overview")
        lines.append("")
        lines.append("> 🚦 Review: 🔴 Failed · 🟠 Blocked · ⚪ Not Supported · ℹ️ With Notes")
        lines.append("")
        lines.append("| Server Support Coverage | Validation Health | Conformance Action Items | Server Scope Notes |")
        lines.append("|:---:|:---:|:---:|:---:|")
        lines.append(
            f"| **{_fmt_pct(context['spec_coverage_value'])}** | "
            f"**{_fmt_pct(context['validation_health_value'])}** | "
            f"**{_format_status_counts(_ACTION_ITEM_LABEL_ORDER, findings_count)}** | "
            f"**{_format_status_counts(_CAPABILITY_NOTE_LABEL_ORDER, findings_count)}** |"
        )
        lines.append(
            f"| {supported} / {total_active} CUs server-supported | "
            f"{validated} / {supported} server-supported CUs validated | "
            f"{_action_items_context(findings_count)} | {_informational_notes_context(findings_count)} |"
        )
        lines.append("")

    lines.extend(profile_lines)

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
            remaining = len(data["failures"]) - 30
            lines.append(
                f"| Additional rows | {remaining} additional failure item(s) are listed in full in `report.xlsx` |"
            )
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.extend(_render_diagnostics(data))

    lines.append("---")
    lines.append("## 📎 Report References")
    lines.append("")
    lines.append(
        f"- Term reference: see [REPORT_GLOSSARY.md]({resolved_env.glossary_url}) for definitions of report terms."
    )
    lines.append("- Full detail: download `report.xlsx` or `report.html` from the run artifacts.")
    return "\n".join(lines), context
