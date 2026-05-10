"""Shared score, severity, and delta helpers for IJT report renderers.

Markdown and Excel reports both import from here. The report rendering tests
assert both generators bind to the same function objects, so do not re-define
this logic inside the generators.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

OUTCOME_RANK = {
    "action_needed": 0,
    "blocked": 1,
    "not_supported": 2,
    "partial": 3,
    "supported": 4,
}
SEVERITY_ORDER = {"Critical": 0, "Major": 1, "Minor": 2, "Info": 3}


def pct_value(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator * 100 / denominator


def format_pct(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.1f}%"
    return "n/a"


def conformance_score(
    counts: Mapping[str, int], server_supported_count: int | str, total_active_profile_cus: int
) -> int:
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


def severity_for(cu_key: str, outcome: str, active_cus: set[str]) -> tuple[str, str]:
    if outcome == "supported":
        return "", ""
    if outcome == "action_needed":
        return "Critical", "🔴"
    if outcome == "blocked":
        return "Major", "🟠"
    if outcome == "not_supported" and cu_key in active_cus:
        return "Minor", "🟡"
    return "Info", "ℹ️"


def delta_symbol(cu_key: str, outcome: str, baseline: dict[str, Any] | None) -> str:
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
