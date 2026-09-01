"""
Canonical final-report outcome model — the single vocabulary source.

Every layer of the test client produces its own low-level status string:

  * pytest / JUnit             ``passed``, ``failed``, ``error``, ``skipped``, ``xfailed`` …
  * CU coverage rollup         ``supported``, ``partial``, ``blocked``, ``action_needed`` …
  * Target Server readiness    ``blocked``, ``unsupported``, ``manual_required`` …

Those vocabularies stay exactly as they are: they carry useful detail and raw
pytest/JUnit semantics must not be rewritten. This module adds one small typed
vocabulary on top that every *final* report (JSON, Markdown, Excel) uses:

  ``Passed``        the claimed behaviour was exercised and accepted
  ``Failed``        claimed behaviour is missing, rejected, or wrong
  ``NotSupported``  behaviour is absent and was never claimed (informational)
  ``Blocked``       a runtime prerequisite was absent, so nothing could be judged
  ``NotTested``     applicable, executable, but not executed in this run
  ``Inconclusive``  evidence was unreadable or ambiguous — no verdict is possible

Detailed reason codes are preserved separately from the outcome. A canonical
outcome answers *"what does the final report say"*; the reason code and its
category answer *"why"*.

Mapping rules (deterministic, see :func:`canonical_for_pytest_outcome` and
:func:`canonical_for_legacy_outcome`):

  * claimed behaviour missing or failing        -> ``Failed``
  * unclaimed, absent, optional behaviour       -> ``NotSupported`` (informational)
  * runtime prerequisite absent                 -> ``Blocked``
  * applicable but not executed                 -> ``NotTested``
  * unreadable, ambiguous, or suppressed result -> ``Inconclusive``

This module deliberately makes no OPC Foundation certification claim: the
outcomes describe what this client observed, not a certified conformance grade.

Usage::

    from helpers.canonical_outcomes import CanonicalOutcome, canonical_for_pytest_outcome

    outcome = canonical_for_pytest_outcome("skipped", claimed=False)
    assert outcome is CanonicalOutcome.NOT_SUPPORTED
    assert outcome.label == "Not Supported"
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any

# ---------------------------------------------------------------------------
# Canonical outcomes
# ---------------------------------------------------------------------------


class CanonicalOutcome(str, Enum):
    """Canonical final-report outcome for one conformance unit, check, or test."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_SUPPORTED = "not_supported"
    BLOCKED = "blocked"
    NOT_TESTED = "not_tested"
    INCONCLUSIVE = "inconclusive"

    @property
    def label(self) -> str:
        """Return the public report label for this outcome."""
        return CANONICAL_OUTCOME_LABELS[self]

    @property
    def is_actionable(self) -> bool:
        """True when the outcome needs an action from the server or test owner."""
        return self in _ACTIONABLE_OUTCOMES

    @property
    def is_informational(self) -> bool:
        """True when the outcome is scope information rather than a defect."""
        return self in _INFORMATIONAL_OUTCOMES


CANONICAL_OUTCOME_LABELS: Mapping[CanonicalOutcome, str] = MappingProxyType(
    {
        CanonicalOutcome.PASSED: "Passed",
        CanonicalOutcome.FAILED: "Failed",
        CanonicalOutcome.NOT_SUPPORTED: "Not Supported",
        CanonicalOutcome.BLOCKED: "Blocked",
        CanonicalOutcome.NOT_TESTED: "Not Tested",
        CanonicalOutcome.INCONCLUSIVE: "Inconclusive",
    }
)

#: Report order: worst/most actionable first, informational last.
CANONICAL_OUTCOME_ORDER: tuple[CanonicalOutcome, ...] = (
    CanonicalOutcome.FAILED,
    CanonicalOutcome.BLOCKED,
    CanonicalOutcome.INCONCLUSIVE,
    CanonicalOutcome.NOT_TESTED,
    CanonicalOutcome.NOT_SUPPORTED,
    CanonicalOutcome.PASSED,
)

_ACTIONABLE_OUTCOMES: frozenset[CanonicalOutcome] = frozenset(
    {CanonicalOutcome.FAILED, CanonicalOutcome.BLOCKED, CanonicalOutcome.INCONCLUSIVE}
)
_INFORMATIONAL_OUTCOMES: frozenset[CanonicalOutcome] = frozenset(
    {CanonicalOutcome.NOT_SUPPORTED, CanonicalOutcome.NOT_TESTED}
)


def canonical_outcome(value: str | CanonicalOutcome) -> CanonicalOutcome:
    """Coerce *value* to a :class:`CanonicalOutcome`, or raise ``ValueError``."""
    if isinstance(value, CanonicalOutcome):
        return value
    return CanonicalOutcome(str(value).strip().lower())


def canonical_label(value: str | CanonicalOutcome) -> str:
    """Return the public label for *value*, or ``Inconclusive`` when unknown."""
    try:
        return canonical_outcome(value).label
    except ValueError:
        return CanonicalOutcome.INCONCLUSIVE.label


def worst_canonical_outcome(outcomes: object) -> CanonicalOutcome:
    """Return the most severe outcome in *outcomes* (empty -> ``NotTested``)."""
    ranked = [canonical_outcome(item) for item in outcomes or ()]  # type: ignore[union-attr]
    if not ranked:
        return CanonicalOutcome.NOT_TESTED
    return min(ranked, key=CANONICAL_OUTCOME_ORDER.index)


# ---------------------------------------------------------------------------
# Reason categories (detail preserved separately from the outcome)
# ---------------------------------------------------------------------------

CATEGORY_CONNECTIVITY = "connectivity"
CATEGORY_CONFIGURATION = "configuration"
CATEGORY_CLAIM = "claim"
CATEGORY_CAPABILITY = "capability"
CATEGORY_SAFETY_POLICY = "safety_policy"
CATEGORY_RUNTIME_PREREQUISITE = "runtime_prerequisite"
CATEGORY_OPERATOR_ACTION = "operator_action"
CATEGORY_TOOLING = "tooling"
CATEGORY_EVIDENCE = "evidence"
CATEGORY_UNKNOWN = "unknown"

ALL_REASON_CATEGORIES: frozenset[str] = frozenset(
    {
        CATEGORY_CONNECTIVITY,
        CATEGORY_CONFIGURATION,
        CATEGORY_CLAIM,
        CATEGORY_CAPABILITY,
        CATEGORY_SAFETY_POLICY,
        CATEGORY_RUNTIME_PREREQUISITE,
        CATEGORY_OPERATOR_ACTION,
        CATEGORY_TOOLING,
        CATEGORY_EVIDENCE,
        CATEGORY_UNKNOWN,
    }
)

# ---------------------------------------------------------------------------
# Legacy execution/readiness outcome vocabulary (defined here, re-exported by
# helpers.target_server_cu_config so existing imports keep working).
# ---------------------------------------------------------------------------

OUTCOME_PASSED = "passed"
OUTCOME_FAILED = "failed"
OUTCOME_BLOCKED = "blocked"
OUTCOME_UNSUPPORTED = "unsupported"
OUTCOME_MANUAL_REQUIRED = "manual_required"
OUTCOME_CLAIM_MISMATCH = "claim_mismatch"
OUTCOME_CONFIGURATION_ERROR = "configuration_error"

ALL_OUTCOMES: frozenset[str] = frozenset(
    {
        OUTCOME_PASSED,
        OUTCOME_FAILED,
        OUTCOME_BLOCKED,
        OUTCOME_UNSUPPORTED,
        OUTCOME_MANUAL_REQUIRED,
        OUTCOME_CLAIM_MISMATCH,
        OUTCOME_CONFIGURATION_ERROR,
    }
)

# Stable reason code vocabulary for blocked/failed outcomes.
REASON_TOOL_DISCONNECTED = "tool_disconnected"
REASON_NO_PROCESS_CONFIGURED = "no_process_configured"
REASON_MANUAL_TRIGGER_REQUIRED = "manual_trigger_required"
REASON_UNSAFE_METHOD_NOT_ENABLED = "unsafe_method_not_enabled"
REASON_CLAIM_METHOD_MISSING = "claim_method_missing"
REASON_CLAIM_STATUS_NOT_SUPPORTED = "claim_status_not_supported"
REASON_STATUS_NOT_SUPPORTED = "status_not_supported"
REASON_CONFIGURATION_INVALID = "configuration_invalid"
REASON_TARGET_SERVER_NOT_READY = "target_server_not_ready"
REASON_MISSING_RUNTIME_PRECONDITION = "missing_runtime_precondition"
REASON_SAFETY_INTERLOCK_ACTIVE = "safety_interlock_active"
REASON_NAMESPACE_UNAVAILABLE = "namespace_unavailable"
REASON_JOINING_SYSTEM_NOT_FOUND = "joining_system_not_found"
REASON_ENDPOINT_UNREACHABLE = "endpoint_unreachable"

REASON_CATEGORIES: Mapping[str, str] = MappingProxyType(
    {
        REASON_TOOL_DISCONNECTED: CATEGORY_RUNTIME_PREREQUISITE,
        REASON_NO_PROCESS_CONFIGURED: CATEGORY_CONFIGURATION,
        REASON_MANUAL_TRIGGER_REQUIRED: CATEGORY_OPERATOR_ACTION,
        REASON_UNSAFE_METHOD_NOT_ENABLED: CATEGORY_SAFETY_POLICY,
        REASON_CLAIM_METHOD_MISSING: CATEGORY_CLAIM,
        REASON_CLAIM_STATUS_NOT_SUPPORTED: CATEGORY_CLAIM,
        REASON_STATUS_NOT_SUPPORTED: CATEGORY_CAPABILITY,
        REASON_CONFIGURATION_INVALID: CATEGORY_CONFIGURATION,
        REASON_TARGET_SERVER_NOT_READY: CATEGORY_RUNTIME_PREREQUISITE,
        REASON_MISSING_RUNTIME_PRECONDITION: CATEGORY_RUNTIME_PREREQUISITE,
        REASON_SAFETY_INTERLOCK_ACTIVE: CATEGORY_SAFETY_POLICY,
        REASON_NAMESPACE_UNAVAILABLE: CATEGORY_CONNECTIVITY,
        REASON_JOINING_SYSTEM_NOT_FOUND: CATEGORY_RUNTIME_PREREQUISITE,
        REASON_ENDPOINT_UNREACHABLE: CATEGORY_CONNECTIVITY,
    }
)


def reason_category(reason_code: str) -> str:
    """Return the stable category for *reason_code* (``unknown`` when unmapped)."""
    return REASON_CATEGORIES.get(reason_code, CATEGORY_UNKNOWN)


# ---------------------------------------------------------------------------
# Mappings into the canonical vocabulary
# ---------------------------------------------------------------------------

#: Readiness/execution outcome -> canonical outcome. ``unsupported`` depends on
#: whether the behaviour was claimed, so it is resolved in the function below.
_LEGACY_OUTCOME_MAP: Mapping[str, CanonicalOutcome] = MappingProxyType(
    {
        OUTCOME_PASSED: CanonicalOutcome.PASSED,
        OUTCOME_FAILED: CanonicalOutcome.FAILED,
        OUTCOME_BLOCKED: CanonicalOutcome.BLOCKED,
        OUTCOME_MANUAL_REQUIRED: CanonicalOutcome.BLOCKED,
        OUTCOME_CLAIM_MISMATCH: CanonicalOutcome.FAILED,
        OUTCOME_CONFIGURATION_ERROR: CanonicalOutcome.INCONCLUSIVE,
    }
)

#: Raw pytest / JUnit outcome -> canonical outcome. ``not_supported`` depends on
#: the claim, so it is resolved in the function below.
_PYTEST_OUTCOME_MAP: Mapping[str, CanonicalOutcome] = MappingProxyType(
    {
        "passed": CanonicalOutcome.PASSED,
        "failed": CanonicalOutcome.FAILED,
        "error": CanonicalOutcome.FAILED,
        "blocked": CanonicalOutcome.BLOCKED,
        "environment": CanonicalOutcome.BLOCKED,
        "accepted_policy": CanonicalOutcome.NOT_SUPPORTED,
        "skipped": CanonicalOutcome.NOT_TESTED,
        "untested": CanonicalOutcome.NOT_TESTED,
        "deselected": CanonicalOutcome.NOT_TESTED,
        "xfailed": CanonicalOutcome.INCONCLUSIVE,
        "xpassed": CanonicalOutcome.INCONCLUSIVE,
    }
)

#: CU compliance rollup -> canonical outcome (``not_supported`` resolved below).
_REPORT_OUTCOME_MAP: Mapping[str, CanonicalOutcome] = MappingProxyType(
    {
        "supported": CanonicalOutcome.PASSED,
        "partial": CanonicalOutcome.INCONCLUSIVE,
        "blocked": CanonicalOutcome.BLOCKED,
        "action_needed": CanonicalOutcome.FAILED,
        "untested": CanonicalOutcome.NOT_TESTED,
        "unknown": CanonicalOutcome.INCONCLUSIVE,
    }
)


def _resolve_absent(claimed: bool) -> CanonicalOutcome:
    """Absent behaviour is a failure only when the manifest claimed it."""
    return CanonicalOutcome.FAILED if claimed else CanonicalOutcome.NOT_SUPPORTED


def canonical_for_legacy_outcome(outcome: str, *, claimed: bool = False) -> CanonicalOutcome:
    """Map a readiness/execution outcome string to a canonical outcome.

    Parameters
    ----------
    outcome:
        One of the ``OUTCOME_*`` values in this module.
    claimed:
        True when the SUT manifest claims the behaviour. A claimed but
        unsupported capability is a ``Failed``; an unclaimed one is
        ``NotSupported`` (informational).
    """
    key = str(outcome).strip().lower()
    if key == OUTCOME_UNSUPPORTED:
        return _resolve_absent(claimed)
    return _LEGACY_OUTCOME_MAP.get(key, CanonicalOutcome.INCONCLUSIVE)


def canonical_for_pytest_outcome(outcome: str, *, claimed: bool = False) -> CanonicalOutcome:
    """Map a raw pytest/JUnit outcome (or CU test classification) to a canonical outcome.

    Raw pytest semantics are untouched — this only decides what the final
    report shows. ``xfailed``/``xpassed`` are ``Inconclusive`` because an
    expected-failure marker suppresses a real verdict about the server.
    """
    key = str(outcome).strip().lower()
    if key == "not_supported":
        return _resolve_absent(claimed)
    return _PYTEST_OUTCOME_MAP.get(key, CanonicalOutcome.INCONCLUSIVE)


def canonical_for_report_outcome(outcome: str, *, claimed: bool = False) -> CanonicalOutcome:
    """Map a CU compliance rollup value to a canonical outcome."""
    key = str(outcome).strip().lower()
    if key == "not_supported":
        return _resolve_absent(claimed)
    return _REPORT_OUTCOME_MAP.get(key, CanonicalOutcome.INCONCLUSIVE)


# ---------------------------------------------------------------------------
# Canonical finding: outcome + preserved detail
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CanonicalFinding:
    """One canonical outcome plus the detailed reason it was derived from.

    The canonical outcome drives the final report; ``source_outcome``,
    ``reason_code``, and ``reason_category`` preserve the detail that produced it.
    """

    outcome: CanonicalOutcome
    source_outcome: str = ""
    reason_code: str = ""
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        """Public report label for the canonical outcome."""
        return self.outcome.label

    @property
    def reason_category(self) -> str:
        """Stable category for :attr:`reason_code`."""
        return reason_category(self.reason_code)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation for final reports."""
        payload: dict[str, Any] = {
            "canonical_outcome": self.outcome.value,
            "canonical_label": self.label,
            "source_outcome": self.source_outcome,
            "reason_code": self.reason_code,
            "reason_category": self.reason_category,
            "detail": self.detail,
        }
        if self.evidence:
            payload["evidence"] = dict(self.evidence)
        return payload


def finding_from_legacy(
    outcome: str,
    *,
    reason_code: str = "",
    detail: str = "",
    claimed: bool = False,
    evidence: dict[str, Any] | None = None,
) -> CanonicalFinding:
    """Build a :class:`CanonicalFinding` from a readiness/execution outcome."""
    return CanonicalFinding(
        outcome=canonical_for_legacy_outcome(outcome, claimed=claimed),
        source_outcome=str(outcome),
        reason_code=reason_code,
        detail=detail,
        evidence=dict(evidence or {}),
    )
