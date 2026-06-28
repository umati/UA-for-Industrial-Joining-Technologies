"""Shared scoring, status, KPI formatting, and delta helpers for IJT reports.

Single source of truth for user-facing report logic shared by the Markdown
generator (``scripts/make_specification_test_summary.py``) and the Excel generator
(``scripts/make_excel_report.py``).

Architecture rules:
- Both generators import and call these helpers. They do not rebuild the KPI
  strip, duplicate icon mappings, or hard-code status label order locally.
- Report tests use identity checks to ensure both generators bind to the same
  function objects defined here. Add the same guard for any new shared helper.
- Public report wording, icons, status groups, Excel status colours, delta
  wording, and the KPI separator live here only.
- Internal outcome keys such as ``action_needed`` and ``partial`` are runner
  identifiers, not public wording. Map them with :func:`status_for`.
- The conformance score is retained as an internal trend index for existing
  baselines. Public reports should show Validation Health and Server Support
  Coverage instead of a composite score.
- Icons are scoped by semantic class. KPI icons are unique within the KPI
  strip; cross-class overlap is intentional where the meaning aligns.

When adding a public status label, update ``KPI_LABELS``, ``KPI_ICONS``,
``STATUS_ORDER``, status group constants, ``STATUS_COLORS_EXCEL``,
:func:`status_for`, and the KPI regex in the report tests. The generators
should not need label-specific edits.

Public helpers include :func:`format_kpi_strip`, :func:`format_status_count`,
:func:`format_status_label`, :func:`format_status_counts`,
:func:`format_primary_reason_note`, :func:`format_delta_summary`, :func:`outcome_label`,
:func:`format_outcome_label`, :func:`status_color_excel`, and
:func:`is_healthy`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

# ``partial`` is produced when a CU has support coverage plus accepted policy,
# environment, skipped, untested, blocked, or not-supported detail rows.
OUTCOME_RANK: Mapping[str, int] = MappingProxyType(
    {
        "action_needed": 0,
        "blocked": 1,
        "not_supported": 2,
        "partial": 3,
        "supported": 4,
    }
)

OUTCOME_LABELS: Mapping[str, str] = MappingProxyType(
    {
        "supported": "Supported",
        "partial": "Supported with Notes",
        "not_supported": "Not Supported",
        "blocked": "Blocked",
        "action_needed": "Failed",
        "untested": "Untested",
    }
)
NO_COMPLIANCE_LABEL = "No test result"
NON_KPI_ICONS: Mapping[str, str] = MappingProxyType(
    {
        "Supported": "🟢",
        "Supported with Notes": "🟩",
        "Untested": "⚪",
        NO_COMPLIANCE_LABEL: "⚪",
    }
)

KPI_LABELS: tuple[str, ...] = (
    "Failed",
    "Blocked",
    "Not Supported",
    "With Notes",
)
KPI_ICONS: Mapping[str, str] = MappingProxyType(
    {
        "Failed": "🔴",
        "Blocked": "🟠",
        "Not Supported": "⚪",
        "With Notes": "ℹ️",
    }
)
KPI_SEPARATOR: str = " · "
STATUS_ORDER: Mapping[str, int] = MappingProxyType({label: index for index, label in enumerate(KPI_LABELS)})
ACTION_ITEM_LABEL_ORDER: tuple[str, ...] = ("Failed", "Blocked")
CAPABILITY_NOTE_LABEL_ORDER: tuple[str, ...] = ("Not Supported", "With Notes")
ACTION_ITEM_LABELS: frozenset[str] = frozenset(ACTION_ITEM_LABEL_ORDER)
CAPABILITY_NOTE_LABELS: frozenset[str] = frozenset(CAPABILITY_NOTE_LABEL_ORDER)
STATUS_COLORS_EXCEL: Mapping[str, str] = MappingProxyType(
    {
        "Failed": "FFFFE5E5",
        "Blocked": "FFFCE4D6",
        "Not Supported": "FFF2F2F2",
        "With Notes": "FFDDEBF7",
    }
)
STATUS_COUNT_KEYS: Mapping[str, str] = MappingProxyType(
    {
        "Failed": "action_needed",
        "Blocked": "blocked",
        "Not Supported": "not_supported",
        "With Notes": "with_notes",
    }
)
DELTA_LABELS: tuple[str, ...] = ("new", "resolved", "regressed")
DELTA_ICONS: Mapping[str, str] = MappingProxyType(
    {
        "new": "🆕",
        "resolved": "✅",
        "regressed": "⚠️",
    }
)
RUN_RESULT_ICONS: Mapping[str, str] = MappingProxyType({"passed": "🟢", "failed": "🔴"})
TEST_RESULT_ICONS: Mapping[str, str] = MappingProxyType({"passed": "✅", "failed": "❌"})
CAPABILITY_SUPPORT_ICONS: Mapping[str, str] = MappingProxyType(
    {
        "supported": "✅",
        "partial": "⚠️",
        "not_supported": "⚪",
    }
)


def pct_value(numerator: int, denominator: int) -> float | None:
    """Return a safe percentage value, or ``None`` when the denominator is zero."""
    if denominator <= 0:
        return None
    return numerator * 100 / denominator


def format_pct(value: object) -> str:
    """Format a percentage value for reports, using ``Not Applicable`` for non-numeric values."""
    if isinstance(value, (int, float)):
        return f"{value:.1f}%"
    return "Not Applicable"


def conformance_score(
    counts: Mapping[str, int], server_supported_count: int | str, total_active_profile_cus: int
) -> int:
    """Return the internal 0-100 conformance trend index for baselines.

    Formula: ``0.7 * validation_health + 0.3 * spec_coverage``. The score is
    capped at 50 when action items exist, capped at 75 when blocked items
    exist, and returns 0 for an empty or invalid active profile. The value is
    kept for baseline compatibility and is not rendered as a compliance grade.

    Internal trend metric only — no longer surfaced in the report header. The
    visible KPI strip uses Validation Health and Server Support Coverage
    directly.
    """
    if not isinstance(server_supported_count, int) or server_supported_count <= 0 or total_active_profile_cus <= 0:
        return 0
    validation_health = (counts["supported"] + counts["partial"]) / max(server_supported_count, 1)
    spec_coverage = server_supported_count / max(total_active_profile_cus, 1)
    base = round(100 * ((0.7 * validation_health) + (0.3 * spec_coverage)))
    if counts["action_needed"] > 0:
        base = min(base, 50)
    elif counts["blocked"] > 0:
        base = min(base, 75)
    return max(0, min(100, base))


def is_healthy(
    *,
    context_present: bool,
    server_supported_count: object,
    active_cus_len: int,
    failed_count: int,
    blocked_count: int,
) -> bool:
    """Return True only when the run can credibly be called Passed.

    Healthy means: we actually built the report context (CU payload present),
    the server profile declared at least one supported CU, the active profile
    is non-empty, and the run produced zero failed and zero blocked items.
    Missing payload, ``server_supported_count == 0``, or an empty active
    profile all count as UNHEALTHY so a setup/profile problem cannot hide
    behind a clean Action Items section.
    """
    if not context_present:
        return False
    if not isinstance(server_supported_count, int) or server_supported_count <= 0:
        return False
    if active_cus_len <= 0:
        return False
    return failed_count == 0 and blocked_count == 0


def status_for(cu_key: str, outcome: str, active_cus: set[str]) -> tuple[str, str]:
    """Map an internal CU outcome to its public ``(status label, icon)`` pair."""
    if outcome == "supported":
        return "", ""
    if outcome == "action_needed":
        return "Failed", KPI_ICONS["Failed"]
    if outcome == "blocked":
        return "Blocked", KPI_ICONS["Blocked"]
    if outcome == "not_supported" and cu_key in active_cus:
        return "Not Supported", KPI_ICONS["Not Supported"]
    return "With Notes", KPI_ICONS["With Notes"]


def status_count_key(status: str) -> str:
    """Convert a public status label to the internal count key."""
    return STATUS_COUNT_KEYS.get(status, status.lower().replace(" ", "_"))


def format_status_count(label: str, count: int) -> str:
    """Render one status count with the canonical icon and public label."""
    return f"{KPI_ICONS[label]} {count} {label}"


def format_status_label(label: str) -> str:
    """Render one public label with its canonical icon."""
    icon = KPI_ICONS.get(label, NON_KPI_ICONS.get(label, ""))
    safe_label = label.replace(" ", "&nbsp;")
    return f"{icon}&nbsp;{safe_label}" if icon else safe_label


def outcome_label(outcome: str) -> str:
    """Return the public label for one internal CU outcome."""
    return OUTCOME_LABELS.get(outcome, outcome.replace("_", " ").title() or "Unknown")


def format_outcome_label(outcome: str) -> str:
    """Render one internal CU outcome as an icon+label pair."""
    return format_status_label(outcome_label(outcome))


def format_status_counts(labels: tuple[str, ...], counts: Mapping[str, int]) -> str:
    """Render multiple status counts using the canonical KPI separator."""
    return KPI_SEPARATOR.join(format_status_count(label, _status_count(counts, label)) for label in labels)


def format_primary_reason_note(outcome: str, label: str, reason: str) -> str:
    """Render one concise user-facing reason without repeating the row status."""
    display_reason = reason.strip()
    if outcome == "not_supported":
        display_reason = re.sub(
            r"^Not Supported:\s*",
            "",
            display_reason,
            flags=re.IGNORECASE,
        )
        display_reason = re.sub(r"\s+NOT SUPPORTED$", "", display_reason)
        return _unsupported_reason_sentence(display_reason)
    if display_reason.casefold().startswith(f"{label}:".casefold()):
        return display_reason
    return f"{label}: {display_reason}"


def _unsupported_reason_sentence(display_reason: str) -> str:
    single_method = re.fullmatch(r".+\s+-\s+Method:\s*([^:]+)", display_reason)
    if single_method:
        return f"Method '{single_method.group(1).strip()}' is not supported"

    multi_method = re.fullmatch(r".+\s+-\s+Methods:\s*(.+)", display_reason)
    if multi_method:
        methods = [method.strip() for method in multi_method.group(1).split(",") if method.strip()]
        quoted = "', '".join(methods)
        return f"Methods '{quoted}' are not supported"

    optional_method = re.fullmatch(
        r"Optional method\s+'([^']+)':\s*Not Supported(?:\s+[—-]\s*(.+))?",
        display_reason,
        flags=re.IGNORECASE,
    )
    if optional_method:
        detail = optional_method.group(2)
        suffix = f" - {detail.strip()}" if detail else ""
        return f"Method '{optional_method.group(1).strip()}' is not supported{suffix}"

    if display_reason.startswith("IJT ") and ":" not in display_reason:
        return f"Conformance unit '{display_reason}' is not supported"

    return display_reason


def action_items_context(counts: Mapping[str, int]) -> str:
    """Render the Specification Test Overview note for actionable findings."""
    total = sum(_status_count(counts, label) for label in ACTION_ITEM_LABEL_ORDER)
    return "Investigate failed or blocked CUs" if total else "No action needed"


def informational_notes_context(counts: Mapping[str, int]) -> str:
    """Render the Specification Test Overview note for non-actionable findings."""
    total = sum(_status_count(counts, label) for label in CAPABILITY_NOTE_LABEL_ORDER)
    return "Information only. Review scope and caveats" if total else "No informational notes"


def format_kpi_strip(counts: Mapping[str, int], separator: str = KPI_SEPARATOR) -> str:
    """Render the headline KPI strip used by both Markdown and Excel.

    ``counts`` may be keyed by public labels (``"Failed"``) or by the
    internal count keys already used by report contexts (``"action_needed"``).
    If both are present, the internal key takes precedence. Missing values
    render as 0. Production callers use the default separator so Markdown and
    Excel remain visually identical.
    """
    return separator.join(format_status_count(label, _status_count(counts, label)) for label in KPI_LABELS)


def _status_count(counts: Mapping[str, int], label: str) -> int:
    internal_key = status_count_key(label)
    if internal_key in counts:
        return int(counts.get(internal_key) or 0)
    return int(counts.get(label, 0) or 0)


def format_delta_summary(delta: Mapping[str, int]) -> str:
    """Render the review-item delta summary with a distinct icon vocabulary."""
    return KPI_SEPARATOR.join(f"{DELTA_ICONS[key]} {int(delta.get(key, 0) or 0)} {key}" for key in DELTA_LABELS)


def status_color_excel(label: str) -> str:
    """Return the Excel fill colour for a public status label."""
    return STATUS_COLORS_EXCEL[label]


def delta_symbol(cu_key: str, outcome: str, baseline: dict[str, Any] | None) -> str:
    """Return the per-CU delta marker compared with the previous baseline."""
    cu_outcomes = (baseline or {}).get("cu_outcomes")
    if not cu_outcomes:
        return ""
    previous = cu_outcomes.get(cu_key)
    if previous is None:
        return "New"
    if previous == "untested" or outcome == "untested":
        return ""
    if previous == outcome:
        return "✓"
    current_rank = OUTCOME_RANK.get(outcome)
    previous_rank = OUTCOME_RANK.get(str(previous))
    if current_rank is None or previous_rank is None:
        return ""
    return "↑" if current_rank > previous_rank else "↓"


def change_marker(cu_key: str, outcome: str, baseline: dict[str, Any] | None) -> str:
    """Return only actionable row-level change markers for reader-facing tables."""
    marker = delta_symbol(cu_key, outcome, baseline)
    return "" if marker == "✓" else marker
