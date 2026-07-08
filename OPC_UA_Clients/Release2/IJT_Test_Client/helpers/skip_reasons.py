"""
Consistent pytest skip reason helpers for IJT specification test reports.

Keep skip categories machine-readable at the start of the message so raw JUnit,
Excel reports, and root-runner summaries stay useful.
"""

from __future__ import annotations

import pytest

from helpers.cu_registry import format_cu_not_supported, format_method_not_supported


def _with_detail(summary: str, detail: str | None) -> str:
    if not detail:
        return summary
    return f"{summary} - {detail.strip()}"


def not_supported_reason(cu_or_method: str, *, detail: str | None = None, is_cu: bool | None = None) -> str:
    """Return a NOT SUPPORTED reason for a CU key or OPC UA method BrowseName."""
    if is_cu is None:
        is_cu = "_" in cu_or_method
    summary = format_cu_not_supported(cu_or_method) if is_cu else format_method_not_supported(cu_or_method)
    return _with_detail(summary, detail)


def feature_not_supported_reason(feature: str, *, detail: str | None = None) -> str:
    """Return a NOT SUPPORTED reason for a named non-method server feature."""
    return _with_detail(f"IJT {feature.strip()} NOT SUPPORTED", detail)


def blocked_reason(precondition: str, *, method: str | None = None, status: str | None = None) -> str:
    """Return a BLOCKED reason for missing runtime preconditions."""
    parts = ["BLOCKED"]
    if method:
        parts.append(f"Method: {method}")
    if status:
        parts.append(f"Status: {status}")
    parts.append(precondition)
    return " - ".join(parts)


def accepted_policy_reason(policy: str, *, method: str | None = None, status: str | None = None) -> str:
    """Return an ACCEPTED POLICY reason for deliberate simulator/domain outcomes."""
    parts = ["ACCEPTED POLICY"]
    if method:
        parts.append(f"Method: {method}")
    if status:
        parts.append(f"Status: {status}")
    parts.append(policy)
    return " - ".join(parts)


def environment_reason(reason: str) -> str:
    """Return an ENVIRONMENT reason for local tooling, port, browser, or network gaps."""
    return f"ENVIRONMENT - {reason.strip()}"


def tooling_limitation_reason(reason: str) -> str:
    """Return a TOOLING LIMITATION reason for test-client coverage gaps."""
    return f"TOOLING LIMITATION - {reason.strip()}"


def companion_spec_note_reason(reason: str) -> str:
    """Return a COMPANION SPEC PROFILE NOTE reason for profile-specific companion-spec gaps."""
    return f"COMPANION SPEC PROFILE NOTE - {reason.strip()}"


def simulator_regression_limit_reason(reason: str) -> str:
    """Return a SIMULATOR REGRESSION LIMIT reason for simulator-only stability guards."""
    return f"SIMULATOR REGRESSION LIMIT - {reason.strip()}"


def skip_not_supported(cu_or_method: str, *, detail: str | None = None, is_cu: bool | None = None) -> None:
    """Skip because the server profile/address space does not support a CU or method."""
    pytest.skip(not_supported_reason(cu_or_method, detail=detail, is_cu=is_cu))


def skip_feature_not_supported(feature: str, *, detail: str | None = None) -> None:
    """Skip because the server profile/address space does not support a non-method feature."""
    pytest.skip(feature_not_supported_reason(feature, detail=detail))


def skip_blocked(precondition: str, *, method: str | None = None, status: str | None = None) -> None:
    """Skip because a runtime precondition is unavailable."""
    pytest.skip(blocked_reason(precondition, method=method, status=status))


def skip_accepted_policy(policy: str, *, method: str | None = None, status: str | None = None) -> None:
    """Skip because the outcome is an accepted simulator/domain policy."""
    pytest.skip(accepted_policy_reason(policy, method=method, status=status))


def skip_environment(reason: str) -> None:
    """Skip because of a local environment condition."""
    pytest.skip(environment_reason(reason))


def skip_tooling_limitation(reason: str) -> None:
    """Skip because the test client cannot exercise this path yet."""
    pytest.skip(tooling_limitation_reason(reason))


def skip_companion_spec_note(reason: str) -> None:
    """Skip because a companion-spec feature is outside the active profile."""
    pytest.skip(companion_spec_note_reason(reason))


def skip_simulator_regression_limit(reason: str) -> None:
    """Skip because a simulator-only regression utility hit an intentional guard."""
    pytest.skip(simulator_regression_limit_reason(reason))
